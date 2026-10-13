# cruise-bot — 邮轮五日文字内容 Bot（交钥匙方案）

> 场景：夫人在邮轮 5 天，不购互联网套餐时只能用 **WhatsApp / iMessage 收发文字**。
> 本方案让她在这两条"窄带"上尽可能多地看世界：新闻、搜索、长文阅读、维基、公版书、
> 连载小说、猜谜、翻译、家人留言——全部**零新增费用**。

## 一、架构总览

```
                ┌──────────────────────────── GitHub Actions（免费 cron）────────────────────────────┐
                │  07:40 早报（RSS→GLM汇总）  21:30 晚安包  每4h突发新闻(hash去重)                     │
                └──────────────────────────────┬───────────────────────────────────────────────────┘
                                               │ POST /send（AGENT_KEY）
┌ 船上（她）┐        443 文字消息                ▼
│  iPhone  │◀──── WhatsApp ────▶ Meta Cloud API ──webhook──▶ ┌─────────────────────────┐
│          │◀──── iMessage ────▶ 家里 Mac                    │  Cloudflare Worker       │
└──────────┘   （同 Apple ID 同步）  BlueBubbles ──Tunnel──▶ │  cruise-bot（本目录）    │
                          ▲                                 │  · 指令路由/内容服务      │
        wxauto（PC微信）   │                                  │  · GLM-4-Flash 免费摘要  │
┌ Windows365 云电脑 ────────┘（Phase 2 微信桥）              │  · KV 状态/待发队列      │
└──────────────────────────────────────────────────────────┘
```

**三通道设计**

| 通道 | 角色 | 主动推送 | 依赖 | 费用 |
|---|---|---|---|---|
| WhatsApp Cloud API | **主通道** | 仅 24h 窗口内 | Meta 官方 API + Worker webhook | service 对话免费 |
| iMessage（BlueBubbles） | **备通道/主动推送兜底** | ✅ 无窗口限制 | 她 Mac 常开 + Tunnel | 免费（开源） |
| 微信桥（云电脑 wxauto） | Phase 2 增强 | 上行中转 | 云电脑常开 | 已有订阅 |

**为什么这样排**：WhatsApp 全托管、最稳、官方合规，满足"老公手机一起收消息测试"
（Meta 后台把老公号码加为测试收件人即可镜像）；iMessage 是唯一能"她不发起也推得进去"的
通道——用她自己的 Mac 通过同 Apple ID 自发闭环实现；微信在她手机上不可用（船上只放行
WA/iMessage），所以云电脑微信桥只做**信息供给侧**的中转而非对她的通道。

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

### Step 1 · Meta/WhatsApp 开通（约 30 分钟）★

1. https://developers.facebook.com 用现有 Facebook 账号 → **创建 App**（类型 Business，免费）
2. App 内添加产品 **WhatsApp** → API Setup 页自动获得：
   - **测试电话号码**（临时 token 仅 24h，忽略）
   - 记下 `Phone number ID` 和 `WhatsApp Business Account ID`
3. **添加正式电话号码**（bot 的显示号码）：需要一个能收短信/语音验证码的号——
   用老公的副号/备用号即可；她上船收不到验证码，**不要用她的号**
4. https://business.facebook.com → 设置 → **用户 → 系统用户** → 新建系统用户（管理员）→
   生成 **永久 token**（权限勾 `whatsapp_business_messaging` + `whatsapp_business_management`）
5. API Setup 页把**收件人白名单**加上两个号：老婆的号、老公的号（老公=同步收消息测试）

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

### Step 6 · iMessage 备通道（可选但强烈建议）★

见 `mac-bluebubbles/README-mac.md`（她 Mac 上 20 分钟装好；部署后补三个 Worker secret：
`BB_BASE`、`BB_PASSWORD`、`WIFE_IGUID`，重新 `wrangler deploy` 生效）。

### Step 7 · 微信桥（Phase 2，可选）

见 `win365-wxauto/README-win365.md`。

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
| 1 | WhatsApp 24h 窗口外**不能**主动发 | 业内通用解法=付费模板消息 | 引导每日一发解锁窗口 + iMessage 无窗口兜底 + 队列补发；后续可加免费额度 utility 模板 |
| 2 | 船上只放行 WA/iMessage，浏览器/其他 app 全断 | 邮轮官方文档明确 | 一切内容纯文本经两通道；bot 本体在云端不受限 |
| 3 | Meta 新号需收验证码 | 船上收不到码 | 用岸上号码注册 bot 号；她只是收件人无需验证 |
| 4 | 未验证 Business 限 5 个测试收件人 | Meta 政策 | 5 个名额绰绰有余（夫妻二人）；长期可做 business 验证 |
| 5 | 卫星链路高延迟/乱序 | 常见 | 分条节流 1.2s、文本切分 ≤3800 字、幂等重试 |
| 6 | Bing/DDG 对 Worker 出口 IP 限流 | 通用爬虫问题 | 多源 fallback（Bing RSS→DDG Lite）+ GLM 离线兜底 + 明确告知降级 |
| 7 | 小红书无 API、强反爬 | 社区共识 | 特化指令尽力抓（Bing 站内搜+Jina），失败诚实降级到普通搜索 |
| 8 | Mac 断电/合盖睡眠 → iMessage 断 | BlueBubbles 常见问题 | pmset+合盖禁睡+launchd+monitor.sh 探活；断了自动降级+队列 |
| 9 | 同 Apple ID 分不清"人发的"还是"bot 发的" | 自建 iMessage bot 特有 | bot 消息统一 🤖 前缀，webhook 过滤自环 |
| 10 | workers.dev 在境内不稳定 | 已知 | 她在境外船上无感；老公境内仅用于偶尔管理，可给 Worker 绑自定义域（CF 托管域境内基本可达） |
| 11 | wxauto 类 UI 自动化随微信更新失效 | 社区共识 | 定位 Phase 2 尽力而为，主通道零依赖；挂了只丢增强功能 |
| 12 | 微信个人号自动化合规灰区 | 风险自担类 | 仅转发自己账号、低频、私人用途；不愿冒险可整模块不部署 |
| 13 | bot 被陌生号码骚扰烧 token | — | 白名单外一律拒答 |
| 14 | Actions 官方事件延迟（cron 可能晚几分钟） | GitHub 已知特性 | 内容类不敏感；关键指令她可手动触发 |

## 七、凭据清单（部署时你要给的，全部只进 secrets 不入库）

| 凭据 | 用途 | 放哪 |
|---|---|---|
| Meta 系统用户永久 token | 发消息 | `wrangler secret META_TOKEN` |
| Phone number ID / App secret / Verify token | webhook 与签名 | Worker secrets |
| 智谱 GLM_API_KEY | 免费模型 | Worker + Actions secrets |
| AGENT_KEY（自定） | 内部 API | Worker + Actions secrets |
| 夫妻两人 WhatsApp 号（E.164） | 收发件人 | Worker secrets |
| BlueBubbles 密码 / Tunnel 域名 / chatGuid | iMessage | Worker secrets |
| 一个能收验证码的手机号 | 注册 bot 号码 | 仅 Meta 后台 |

## 八、FAQ

- **她不发消息就完全收不到早报？** WhatsApp 侧是；所以 iMessage 通道（Step 6）强烈建议部署——
  它没有窗口限制，Mac 在家开着就能推。双保险下只有"Mac 断电 + 她一天没发消息"才漏，漏的进队列补发。
- **能发图吗？** 船上免费档基本只过文字（图片走 WA 也常被限）。本方案全部文字化——
  长文分节、链接给纯 URL，回港再看图。
- **流量/token 会被陌生人刷爆吗？** 白名单外一律拒答；GLM-4-Flash 免费档无额度焦虑。
- **回港后要清理吗？** 保留即长期可用（家人日常用也顺手）；停用只需 Actions 禁用 + Worker 删项目。
