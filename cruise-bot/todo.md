# cruise-bot todo（1014 全程总结 + iMessage 转进计划）

> 本文档是邮轮五日内容 Bot 项目的**唯一交接入口**。读完即可接手。
> 最后更新：2026-10-14 10:50（北京时间）· 主通道已切换：**iMessage**

---

## 一、项目目标（不变）

夫人邮轮五日游，不购船上互联网套餐，仅 iMessage 可收发文字。
目标：零新增费用，让她在船上文字交互看尽可能多的内容（早报/晚安/搜/摘要/wiki/天气/热榜/公版书/猜谜/翻译/闲聊…）。

**主通道决定史**：WhatsApp Cloud API（1013-1014 主攻）→ 因 Meta 支付方式封锁无解 → **1014 起切换 iMessage（BlueBubbles）**。WhatsApp 侧全部资产冻结保留，复活条件见第三节。

---

## 二、已完成工作总账

### 2.1 Worker（Cloudflare，生产运行中）

- URL：`https://cruise-bot.lishuhang.workers.dev`，当前版本 **v1.3.1**（1014 01:38 部署）
- 能力清单：
  - `/health` / `/cfg` / `/send` / `/state?prefix=` / `/diag`（全部 `x-agent-key` 头鉴权）
  - WhatsApp 收发全链路（webhook 验证 + 签名校验 + 指令路由 + 内容服务 + GLM）
  - iMessage 收发全链路（`/webhook/imessage?p=` + `sendIMessage` private-api + 🤖 前缀自环过滤 + fromMe→wife 判定）
  - 智能路由 `deliver()`：显式通道直走；auto=WA 窗口内走 WA，窗口外/失败走 iMessage；再不行 KV 待发队列 + 下次她发消息补送
  - 模板探测：`/send` 支持 `{"who":"owner","template":"hello_world"}`（WhatsApp 门铃/封锁探测两用）
  - 每日一字/早报/晚安 cron 在 GitHub Actions（`cruise-bot.yml`，secrets：CRUISE_WORKER_URL/CRUISE_AGENT_KEY/GLM_API_KEY）
- KV namespace：cruise-bot-KV（`seen:*` 入站时间戳、`sendlog:*` 发送日志、`wastat:*` Meta 异步回执、`pending:*` 待发队列、`cfg` 配置）

### 2.2 Meta/WhatsApp 侧（全部就绪，仅差账户级解锁）

- App「CruiseConcierge」(1151416830796942) / WABA (997168623403306) / 测试号 +1 (555) 662-3883 (phone_number_id 1357592887444734)
- webhook：callback=`…/webhook/whatsapp`，messages 字段 active ✓（**入站实测 2 秒到达 Worker**）
- 收件人白名单：夫妻两号均已验证（她 09:23:15 发"帮助"→ seen:owner 实锤入站全通）
- 59 天长效 token 在 Worker secrets（META_TOKEN 裸值已遗失，只在 CF secrets；fb_exchange 重交换通道已关闭）

### 2.3 排障终局（1014 深夜→早晨，详见 README 第九节）

| 时间 | 事实 |
|---|---|
| 多轮 sent:true 未达 | 131047 Re-engagement（24h 窗口未开）——**掩盖了更深的封锁** |
| 1014 09:23 她发"帮助" | 入站✓ → Worker 秒回 → 异步回执 **131031 Business Account locked** |
| /diag health_status | WABA=**BLOCKED(141006 支付方式缺失)** + BUSINESS=LIMITED(141010 未验证) + APP=AVAILABLE |
| hello_world 模板探测 | 同样 131031 → **模板+自由文本全挡，账户级封锁坐实** |

**两个易混号码（永久结论）**：
- +1 (646) 589-4168 = Meta 官方验证服务号（发验证码用，永不回复，别再发）
- **+1 (555) 662-3883 = 机器人测试号**（真正和它聊）

### 2.4 WhatsApp 路线为什么停

Meta 要求 WABA 挂有效支付方式（141006），**付款方式选择器不支持中国大陆**，用户无合适国际信用卡 → 无法解除 → 所有出站消息（含免费测试消息）必被 131031 打回。技术侧能做的已全部做完。

---

## 三、WhatsApp 复活条件（留档备查）

任一满足即可重启，其余资产分毫不用动：
1. 账户添加有效支付方式（如未来 Meta 放开大陆 / 拿到国际卡）→ /diag 看 WABA 变 AVAILABLE 即成
2. 换一个已完成支付/验证的 WABA（换 phone_number_id + 重配 webhook）

复活步骤：解封后 `/send` 发 hello_world 探测 → wastat 无 failed → 她在 +1 555-662-3883 会话里发任意消息 → 机器人秒回。全程预计 10 分钟。

---

## 四、iMessage 转进计划（当前主任务）

### 4.1 架构（已定稿，详见 `mac-bluebubbles/README-mac.md`）

```
她 iPhone（船上，iMessage 走卫星 Wi-Fi）
   ↕ 自聊线程（她自己的 Apple ID，消息显示为"发给自己"）
她的 Mac（家里，全程通电，BlueBubbles Server 驱动 Messages.app）
   ↕ Cloudflare Tunnel → https://imsg.lishuhang.com（域名为 lishuhang.com，README 里旧写的 .me 作废）
Cloudflare Worker（cruise-bot）
   ↕ 指令处理 / GLM / 内容源 / cron
```

- 选"她的 Mac + 她 Apple ID + 自聊线程"的原因：夫妻正常 iMessage 会话不被 bot 占用；bot 消息带 🤖 前缀、fromMe+前缀=bot 自环过滤、fromMe 无前缀=她的输入，判定干净
- **为什么不能用老公的 Mac**：bot 会把老公在夫妻会话里手打的每句话当成她的指令

### 4.2 服务端状态

| 项 | 状态 |
|---|---|
| Worker 收发代码 | ✅ 早已就绪（v1.0 起就有，含防自环） |
| CF 域名 | ✅ lishuhang.com（zone active），规划主机名 `imsg.lishuhang.com` |
| 隧道创建 | ⚠️ CF API token 无 Tunnel 写权限（code 10000）→ **改由 Mac 端 `cloudflared tunnel login` 创建**（README-mac 步骤 3，域名照 .com 写） |
| Worker secrets（BB_BASE/BB_PASSWORD/WIFE_IGUID） | ⏳ 等 Mac 端三个值到位后一键配 |
| 防睡眠/监控 | 📄 方案在 README-mac（pmset + monitor.sh launchd） |

### 4.3 她的 Mac 端步骤（唯一剩余的人工段，约 20-25 分钟）

1. 装 BlueBubbles Server（向导：设 API 密码、给权限、记端口 1234）
2. 终端取自聊线程 chatGuid（`/chat` 列表找她本人 handle 的线程；没有就先用 API 给自己发一条再查）→ 这是 `WIFE_IGUID`
3. `brew install cloudflared` → `cloudflared tunnel login`（浏览器授权）→ `tunnel create cruise-imsg` → `route dns cruise-imsg imsg.lishuhang.com` → 写 config.yml → `sudo cloudflared service install`（README-mac 步骤 3 照抄，域名用 .com）
4. BlueBubbles Settings → Webhook → URL 填 `https://cruise-bot.lishuhang.workers.dev/webhook/imessage?p=<BB密码>`，勾 new-message
5. 防睡眠三连：pmset + 登录自启 + monitor.sh install
6. 把三个值回传助手：**BB_PASSWORD / WIFE_IGUID（chatGuid）/ 确认 `https://imsg.lishuhang.com` 通**

### 4.4 助手收到三个值后的收尾（10 分钟内完成）

- CF API 写入 BB_BASE/BB_PASSWORD/WIFE_IGUID 三个 secret（multipart metadata 重部署，注意 2.5 绑定语义）
- `/health` imessage:true → 本机 curl 经隧道向她 iPhone 发"🤖 iMessage 通道测试"
- 她手机收到 → 让她回复"帮助" → 验证指令回环 + sendlog/wastat
- 跑一次 Actions workflow_dispatch test（早报走 iMessage）

### 4.5 已知坑速查（全文见 README-mac 已知坑表）

合盖睡眠=断通道（pmset disablesleep）；private-api 被限就切 apple-script；家庭宽带断网=自动降级 KV 队列恢复自续；出发前一周重启一次 Mac 确认 iMessage 在线。

---

## 五、运维红线与恢复协议

1. **凭据红线**：一切凭据只进 (a) 对话 (b) 本地 `~/my-project/scripts/.cruise_secrets.env`(chmod600) (c) CF/GH 加密 secrets。**严禁入 git/commit/worklog/recycled**。README-mac 等仓库文档一律用占位符。
2. **沙盒重置恢复协议**（已两次实战）：开工先 `ls scripts/.cruise_secrets.env`；缺失→`cp /tmp/my-project/scripts/.cruise_secrets.env` + 从对话/worklog 重建缺失段（1014 实录：基础 8 行靠 /tmp 快照，Meta 段三个 ID 从 /diag 输出反推，META_APP_SECRET 裸值不可恢复→策略=**部署 metadata 永不携带它，CF 自动保留**）。
3. **Workers 绑定语义**（1014 实测）：metadata 列出的绑定整表替换；未列出的 secret_text 自动保留、kv_namespace/plain_text 直接丢失 → 部署脚本必须带全 CKV/DEFAULT_CITY/META_APP_ID/WABA_ID，且永不带 META_TOKEN/META_APP_SECRET。
4. 外层 `~/my-project` 是本地 git 仓库（无 remote 不推送），历史 blob 含早期凭据版本——**永不添加 remote**。

---

## 六、下一棒 Checklist（按序勾选）

- [ ] 她的 Mac 确认可用且能全程通电（若不可用→见 fallback：老公 Mac 方案需加"船上五天夫妻会话不手打"协议，先跟用户确认）
- [ ] Mac 端 4.3 六步 → 回传三值
- [ ] 助手 4.4 收尾验证
- [ ] 出发前 1 天：船时区校准（Actions cron 时区）、/cfg mirror_on 试一轮、KV pending 队列演练
- [ ] 出发前一周：Mac 重启确认 iMessage 在线、检查 cloudflared 服务状态
- [ ] WhatsApp 侧冻结件不动（worker 代码/webhook/白名单/token 全保留）
