# cruise-bot — 邮轮五日文字内容 Bot（交钥匙方案）

> 场景：夫人在邮轮 5 天，不购互联网套餐时只能用 **WhatsApp / iMessage 收发文字**。
> 本方案让她在这条"窄带"上尽可能多地看世界：新闻、搜索、长文阅读、维基、公版书、
> 连载小说、猜谜、翻译、家人留言——全部**零新增费用**。
> 架构约束（用户钦定）：Mac 不常驻；WhatsApp 单主通道；常驻辅助由 Windows 365 + 家中 Android pad 承担。

## 一、架构总览

```
              ┌──────────────────────────── GitHub Actions（免费 cron）──────────────────────────┐
              │  07:40 早报（RSS→GLM汇总）  21:30 晚安包  每4h突发新闻(hash去重)                   │
              └──────────────────────────────┬─────────────────────────────────────────────┘
                                             │ POST /send（AGENT_KEY）
┌ 船上（她）┐       443 文字消息              ▼
│  iPhone  │◀──── WhatsApp ───▶ Meta Cloud API ──webhook──▶ ┌─────────────────────────┐
└──────────┘                                                │  Cloudflare Worker       │
                                                            │  cruise-bot（本目录）    │
┌ 家中 Android pad ─┐ 通知监听（AutoX.js）                   │  · 指令路由/内容服务      │
│ 老婆微信登录       ├──────────────────────────────────▶ │  · GLM-4-Flash 免费摘要  │
└───────────────────┘        （微信→WhatsApp 中转）          │  · KV 状态/待发队列      │
┌ Windows365 云电脑 ──── 常驻增强（Playwright抓取/RSSHub/微信桥备选）▶ └─────────────────────────┘
└──────────────────────────────────────────────────────────┘
```

**通道设计（v1.1 修订：Mac 移出关键路径）**

| 通道 | 角色 | 主动推送 | 依赖 | 费用 |
|---|---|---|---|---|
| WhatsApp Cloud API | **唯一主通道**（她侧收发） | 窗口内；窗口外=队列+知会你 | Meta 官方 API | service 对话免费 |
| Pad 微信桥（通知监听） | **信息供给侧**：微信消息中转上船 | 上行中转 | Android pad 常开充电 | 免费（AutoX.js） |
| iMessage（BlueBubbles） | **已降级为可选**，默认不部署 | —— | Mac 常驻（已排除） | —— |

**24h 窗口外主动推送的三重保障**（没有 iMessage 后）：
1. 她每天发一个字（如「早」）解锁窗口 → 当天全部自动推送畅通
2. 窗口外推送进队列 → 你收到知会 → 你在 WhatsApp 里随手转发给她（人肉 10 秒）
3. 可选：App 建好后申请 utility 模板（如 daily_digest），免费额度内不依赖窗口直发（见 Step 6）

**为什么 WhatsApp 单主通道**：全托管、官方合规、满足"老公手机一起收消息测试"（Meta 后台
把老公号码加为白名单即可）；iMessage 需要 Mac 常驻已被排除；微信在她手机上不可用
（船上只放行 WA/iMessage），pad 桥只做**信息供给侧**中转而非对她的下行通道。

## 二、免费账本（全部零新增费用）

| 组件 | 免费依据 |
|---|---|
| WhatsApp service 对话 | 2024-11 起 Meta 对用户发起的对话窗口内回复**不收费**；bot 全部回复都发生在她发消息后的窗口内 |
| GLM-4-Flash | 智谱免费档模型，摘要/搜索归纳/连载/猜谜全部够用 |
| Cloudflare Workers + KV | 免费额度 10 万请求/天，本 bot 流量占比可忽略 |
| GitHub Actions 定时任务 | 每日 2 次 + 每 4h 一次，私有仓库分钟数充裕 |
| BlueBubbles + Cloudflare Tunnel | 均开源/免费档 |
| 内容源 | BBC 中文 RSS、36氪 RSS、Hacker News RSS、Bing RSS 搜索、DuckDuckGo Lite、Jina Reader、zh.wikipedia REST、open-meteo、Gutendex——全部免费无 key |
| Windows 365 | 已有订阅 |

## 三、她的五天体验（设计目标）

- **每天 07:40**（按船时校准）自动收到早报：要闻 6 条 + 科技 3 条 + 目的地天气 + 一句度假提示
- **白天**随手发：`搜 圣托里尼 历史`、`小红书 邮轮攻略`、把任何链接粘给我读全文、
  `wiki 爱琴海`、`天气 米克诺斯`、`热榜`、`翻译 Excuse me`
- **晚上 21:30** 晚安包：冷知识 + 谜题；睡前 `继续` 追连载小说，`新故事 悬疑` 开新书，
  `读 Pride and Prejudice` 看公版书，`游戏` 猜谜
- **想家**：`回老公 消息` 直达岸上；老公 `广播 晚上七点船长晚宴` 直达她
- 全程只需**每天至少发一条任意消息**（比如一个"早"字）——解锁当天 24h 免费窗口

## 四、部署步骤（按序执行，★=需要你提供/操作）

### Step 1 · Meta/WhatsApp 开通（你的 5 分钟人工接力 + 我的自动化接管）★

> 现实约束：Meta 对所有 App/工具页强制 business 密码确认（陌生设备/机房 IP 代操作会触发
> 风控甚至锁号，代登录不可取）。所以 UI 操作需你在**自己常用浏览器**完成；产出 4 项凭据
> 给助手后，webhook 配置/收件人/测试/发送全部由助手经 Graph API 自动接管。

**你在浏览器做（约 5 分钟）：**

1. https://developers.facebook.com/apps → **创建应用**
   - 用例选 Other（其他）→ 类型 Business → 名称建议 `CruiseConcierge`
     （避免 meta/whatsapp/instagram 等商标词）→ 邮箱 lishuhang@gmail.com
2. 进入 App → **添加产品** → 选 **WhatsApp** → 进入引导
   - API Setup 页记下：**Phone number ID**（测试号自带）与 **WhatsApp Business Account ID**
   - 测试号即可运行（收件人限 5 个，两人绰绰有余）；正式号码注册需收码，如需再加
3. https://business.facebook.com → 设置 → **用户 → 系统用户** → 添加（管理员）→
   **生成令牌**：选刚才的 App，权限勾 `whatsapp_business_messaging` +
   `whatsapp_business_management` → 复制**永久 token**
4. App 设置 → 基本：复制 **App Secret**

**交给助手（4 项）：App ID、App Secret、Phone number ID、系统用户永久 token。**

**助手接手自动做：** 写入 Worker secrets → Graph API 配 webhook 订阅（不需要你碰 UI）→
收件人白名单验证（你的号你在家收码；她的号**出发前**让她收一次码）→ 测试消息全链路 →
Actions 定时任务验证。

**风险提醒（与你提的风控一致）**：全程只发 2 条验证码短信（两个号各 1 条，Meta 发出）；
之后全部走 WhatsApp 数据通道，无任何短信/语音；App 用完即弃或保留均可。

### Step 2 · 智谱 GLM key ★

https://open.bigmodel.cn 注册 → API Keys → 创建（`glm-4-flash` 免费档，无额度焦虑）

### Step 3 · 部署 Worker（约 10 分钟）

```bash
cd cruise-bot
npm i -g wrangler && wrangler login
wrangler kv namespace create CRUISE_KV        # 把返回 id 填进 wrangler.toml
wrangler deploy
wrangler secret put META_TOKEN               # Step1 的永久 token
wrangler secret put META_PHONE_NUMBER_ID     # Step1 的 Phone number ID
wrangler secret put META_APP_SECRET          # App 设置→基本→应用密钥
wrangler secret put META_VERIFY_TOKEN        # 自定随机串，Step4 要用
wrangler secret put GLM_API_KEY              # Step2
wrangler secret put AGENT_KEY                # 自定随机长串（内部 API 口令）
wrangler secret put OWNER_WA                 # +8613xxxxxxxxx（老公）
wrangler secret put WIFE_WA                  # +8613xxxxxxxxx（老婆）
curl https://cruise-bot.你的子域.workers.dev/health
```

### Step 4 · 配 Meta Webhook

App → WhatsApp → Configuration：
- Callback URL：`https://cruise-bot.你的子域.workers.dev/webhook/whatsapp`
- Verify token：Step 3 的 `META_VERIFY_TOKEN`
- Subscribe 字段：**messages**
- 点 Verify and save（Worker 返回 challenge 即通）

### Step 5 · GitHub Actions secrets ★

仓库 Settings → Secrets → Actions：

| Secret | 值 |
|---|---|
| `CRUISE_WORKER_URL` | `https://cruise-bot.你的子域.workers.dev` |
| `CRUISE_AGENT_KEY` | Step 3 的 AGENT_KEY |
| `GLM_API_KEY` | Step 2 |

仓库 Actions 页 → cruise-bot → Run workflow → task=`test`：两边应各收到一条测试消息。

### Step 6 · Utility 模板（可选：窗口外也能直发）

App 建好后可申请一个 utility 模板（如 daily_digest），Meta 免费额度内发送：
她不发消息的当天，早报仍能直接投递（不依赖 24h 窗口）。创建：App → WhatsApp →
Message Templates → Create → Utility → 提交审核（通常数分钟到数小时）。通过后告知
助手，由助手改 Actions 用模板发送。未启用此项时三重保障（她发一个字/队列+知会你/你人肉转发）已覆盖。

### Step 7 · 微信桥（Phase 2，可选）

**首选 pad 方案**：见 `pad-wechat/README-pad.md`（Android pad + AutoX.js 通知监听，
10 分钟，微信手机+平板官方共存长期在线，不受 UI 改版影响）。
备选 W365 wxauto：见 `win365-wxauto/README-win365.md`（接受 24h 扫码风控风险）。
iMessage 备选包保留在 `mac-bluebubbles/`（仅当未来 Mac 需要常驻时再启用）。

### Step 8 · 邮轮时区校准（出发前 1 天）

把 `.github/workflows/cruise-bot.yml` 三行 cron 按船时平移（如地中海 UTC+2：早报改
`'40 21 * * *'`），她也可发 `时区 UTC+2` 让交互类服务对齐。

## 五、她上船 Checklist（发给她的操作卡）

1. 登船连上船上 WiFi，按邮轮指引激活**免费文字消息**（Royal/公主等 2024 起对
   iMessage/WhatsApp 文字免费；激活入口在邮轮 app 或登录页）
2. 给 bot 号码发一条：`帮助` ——收到菜单即全通
3. 顺手发：`时区 UTC+3`（按船上时间）
4. 之后每天发一个 `早` 字即可解锁当天窗口；早报会自动来
5. 没信号/中断不用担心：中断期间内容进队列，她下次开口自动补发

## 六、风险与对策（全网方案踩坑对照）

| # | 风险 | 现状/网上解法 | 本方案对策 |
|---|---|---|---|
| 1 | WhatsApp 24h 窗口外**不能**主动发 | 业内通用解法=付费模板消息 | 三重保障：她每日一字解锁窗口 + 队列+知会你（你随手转发）+ 可选免费额度 utility 模板直发 |
| 2 | 船上只放行 WA/iMessage，浏览器/其他 app 全断 | 邮轮官方文档明确 | 一切内容纯文本经两通道；bot 本体在云端不受限 |
| 3 | Meta 新号需收验证码 | 船上收不到码 | 用岸上号码注册 bot 号；她只是收件人无需验证 |
| 4 | 未验证 Business 限 5 个测试收件人 | Meta 政策 | 5 个名额绰绰有余（夫妻二人）；长期可做 business 验证 |
| 5 | 卫星链路高延迟/乱序 | 常见 | 分条节流 1.2s、文本切分 ≤3800 字、幂等重试 |
| 6 | Bing/DDG 对 Worker 出口 IP 限流 | 通用爬虫问题 | 多源 fallback（Bing RSS→DDG Lite）+ GLM 离线兜底 + 明确告知降级 |
| 7 | 小红书无 API、强反爬 | 社区共识 | 特化指令尽力抓（Bing 站内搜+Jina），失败诚实降级到普通搜索 |
| 8 | Mac 不常驻（用户钦定） | — | iMessage 降级为可选；窗口外推送靠三重保障（见风险 #1）；无实体机 24h 空转 |
| 9 | 同微信风控（新设备登录、频繁异地） | 用户反馈 W365 微信可能 24h 扫码 | 微信桥首选 **pad 通知监听**（官方支持的平板共存，长期在线）；W365 wxauto 降为备选 |
| 10 | workers.dev 在境内不稳定 | 已知 | 她在境外船上无感；老公境内仅用于偶尔管理，可给 Worker 绑自定义域（CF 托管域境内基本可达） |
| 11 | wxauto 类 UI 自动化随微信更新失效 | 社区共识 | pad 用系统级通知监听（不受影响）；wxauto 仅备选 |
| 12 | 微信个人号自动化合规灰区 | 风险自担类 | 仅转发自己账号、低频、私人用途；不愿冒险可整模块不部署 |
| 13 | bot 被陌生号码骚扰烧 token | — | 白名单外一律拒答 |
| 14 | Actions 官方事件延迟（cron 可能晚几分钟） | GitHub 已知特性 | 内容类不敏感；关键指令她可手动触发 |

## 七、凭据清单（部署时你要给的，全部只进 secrets 不入库）

| 凭据 | 用途 | 放哪 |
|---|---|---|
| Meta 系统用户永久 token | 发消息 | `wrangler secret META_TOKEN` |
| Phone number ID / App secret / Verify token | webhook 与签名 | Worker secrets |
| 智谱 GLM_API_KEY | 免费模型 | Worker + Actions secrets ✅已配 |
| AGENT_KEY（自定） | 内部 API | Worker + Actions secrets ✅已配 |
| 夫妻两人 WhatsApp 号（E.164） | 收发件人 | Worker secrets ✅已配 |
| FB App 凭据（4 项，人工接力产出） | Step 1 | Worker secrets（待提供） |
| AGENT_KEY 另存于本地 scripts/.cruise_secrets.env（chmod 600，任务完可删） | — | 本地文件 |

## 八、FAQ

- **她不发消息就完全收不到早报？** 有三重保障（风险 #1）：每日一字解锁窗口为主，
  窗口外内容排队并知会你（你 10 秒人肉转发），可选 utility 模板直发。实际体验：只要她
  每天早上回一个字，当天所有推送畅通。
- **能发图吗？** 船上免费档基本只过文字（图片走 WA 也常被限）。本方案全部文字化——
  长文分节、链接给纯 URL，回港再看图。
- **流量/token 会被陌生人刷爆吗？** 白名单外一律拒答；GLM-4-Flash 免费档无额度焦虑。
- **回港后要清理吗？** 保留即长期可用（家人日常用也顺手）；停用只需 Actions 禁用 + Worker 删项目。
