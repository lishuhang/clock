# Changelog — AI生图 Worker

所有版本变更记录。v0.x-v1.2 为多通道架构，kd-v2.0 起合并为单一 keydraw 通道，kmage-v1.0 起为 kmage 通道。

---

## kmage-1.1 (2026-09-13) — 可观测性与号池运维增强

### Added
- **运行日志控制台**（右上角「日志」）：每次生图按运行号（R+时间戳）分组记录账号选择、请求参数、上游状态码与耗时、错误响应原文（含非 JSON 响应截断，修复 body 双重读取导致原文丢失的问题）、换号/重试决策；支持导出全部/本次运行（.txt 含版本/UA/页面地址）、一键复制、只看错误、清空；持久化 localStorage（`kmage_logs_v1`，300 条环形缓冲），刷新不丢
- **号池 JSON 导入/导出**：导出含邮箱密码/会话/API Key 的完整 JSON；导入按邮箱去重、缺会话账号自动重登恢复（导入后随机间隔逐个登录）
- **浏览器原生通知**：生图成功/失败/超时系统级通知（tag+renotify，点击聚焦窗口，9s 自动关闭）；号池设置开关，首次开启请求权限，被拒绝时开关自动回退
- **`/about` 自描述接口**：版本、端点、存储键，供 AI Agent 排障入口
- **内嵌自包含文档**：右上角「文档」按钮，含 README（架构/数据模型/24h 规则/反模式化原则/排障指引）与 CHANGELOG；页面 HTML 头部注释与页脚含 AI Agent 提示（本页可整体作为 skill 调用）

- **5xx 网关错误自动重试**（debug 截图分析新增）：图生图大请求体（约 1MB 参考图）时上游偶发 504 网关超时——实测同一请求重试即成功（200，34.9s）；v1.0 对 5xx 直接报错，现改为 4s 后同号重试一次、仍失败换号再试一次，全程记日志。上游失败自动返还积分，重试无额外成本

### Changed
- **24 小时规则明确化**：24h 冷却仅限制签到（上游 403 + eligible:false），不限制生图（新生号实测可立即生图）；签到等待提示精确到「X小时Y分后开放」；号池状态列「待激活」同样精确显示；新生号生图被拒（403/400）时自动提示剩余冷却并切换其他账号重试
- **反模式化（马良 v27.2 原则）**：
  - 邮箱改为拟人化生成：姓名/形容词/名词词库 × 6 种模式 × 随机大小写；去除 v1.0 的固定 `kmg` 前缀与时间戳指纹
  - 密码改为 12~15 位完全随机，去除固定 `Zq9` 后缀；API Key 备注名从词池随机（去除固定 `pool-` 前缀）
  - 批量注册间隔 600~1500ms → 2.5~8s 随机（15% 概率再 +4s）；批量签到改为乱序 + 0.8~2.8s 随机间隔
  - Worker 端 UA 透传访客浏览器真实 UA（缺失时从 4 个常见池随机）
- **div.brand 改为「AI生图」**，版本小字 `kmage-1.1`；`<title>` 更新
- `kmageApi`/`kmageV1` 全量埋点自动入日志；`upstreamErrMsg` 支持非 JSON 响应原文
- 修复 `resp.json()` 失败后 body 已消费导致无法取响应原文的问题（先读全文再 parse）——修复后用户截图中只显示「生成失败」的 504 场景现会显示 `error code: 504` 原文

### Deployment
- 部署目标：`ai-image`（ai-image.lishuhang.workers.dev），CF API PUT `body_part` 格式
- 部署验证：/healthz 返回 kmage-1.1；首页 200（72,625B）含 AI生图/kmage-1.1 标记 ×4；CF API GET 线上脚本与本地逐字节一致；/about 正常
- 生产端到端：注册新号（+1 分）→ 建 Key → 生图 HTTP 200（46s，1,027,451B PNG，内容与提示词一致）
- 本地 E2E（mock 上游 + 无头浏览器）：成功/500 HTML/503/402/限流路径、日志控制台渲染与筛选、导入导出、通知开关回退、批量签到乱序与自动重登、日志刷新恢复，全部通过
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.1.js`（81,856 bytes）

---

## kmage-v1.0 (2026-09-13) — 新通道 kmage 上线（上游 image.dddd.zone），kdr 停用

### Background
- kdr 通道故障：上游 keydraw.97api.com 改版，生成 API 契约变化（`key`/`host` 必须放 body，Authorization 头弃用），旧请求全部 400。
- 新上游选定 image.dddd.zone（kmage · AI 视觉工作台）：官方 OpenAI 兼容 API，注册无验证码，签到 +5 分/天，1 积分 = 1 张图，失败自动返还。

### Added
- 号池管理：自动注册（+1 分）、批量签到（+5 分/天/号）、补建 API Key、刷新额度、禁用/归档、删除
- 轮换策略：most-credits（积分优先）/ round-robin（轮询均衡）；402 自动换号；401 自动重登并重建 Key；429 退避重试
- 生图：gpt-image-2 / gpt-image-2.5-flare / gpt-image-2.5-sunburst；比例 1:1/3:2/2:3/16:9/9:16/4:3/3:4/auto；质量 auto/low/medium/high；图生图（reference_images ≤10 张，PNG/JPG/WebP）
- 会话代理：`/api/kmage/*` 以 X-Kmage-Session 头承载各账号 kmage_session，Set-Cookie 经 X-Kmage-Set-Session 回传前端
- Bearer 代理：`/kmage/v1/*` 透传上游官方 OpenAI 兼容接口；`/healthz` 健康检查
- 全部状态存 localStorage（Worker 无状态，无 KV 依赖）

### Deployment
- 部署目标：`ai-image`（ai-image.lishuhang.workers.dev），与 kdr-v1.2 同位替换
- 部署验证：首页 200 + 版本标记 + /healthz + CF API 脚本 diff 一致 + 生产路由端到端生图成功
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.0.js`（48,600 bytes）

---

## 2026-08-19 — 公开免费通道复核（未发布新版本）

### Researched

- 重新检索并核验 V2EX 公开 GPT-Image-2 候选及相关公开体验站，完整过程记录于 `diagnostics-20260819-research-notes.md`。
- 以匿名浏览器分别检查 Keydraw、Flaq、gptimage2.com、NanoBananaTool、Morphic 及若干历史候选的当前登录、额度、验证码和可访问状态。
- Keydraw 页面自身的最小测试任务在匿名访客流程中完成，但其访客 Key 没有第三方代理/分发授权，不能作为本项目生产上游。
- Flaq 页面接受游客输入，但提交生成后要求 Cloudflare 人机验证；其他主要候选均要求登录、注册赠额，或已不可访问。

### Changed

- 新增 `README.md`，说明项目历史、当前线上基线、候选筛选结论、合规发布边界和下一次接手顺序。
- 新增 `diagnostics-20260819-research-notes.md`，保存不含凭据的公开来源与浏览器实测结果。

### Not Released

- **未发布新的 Worker 通道，未覆盖 `gpt2.lishuhang.com`，未声明新的 slug 或版本号。**
- 原因是本轮没有发现同时满足“免登录、免后续验证、可稳定第三方代理且获得明确授权”的免费 GPT-Image-2 上游。

---

## kd-v2.2 (2026-07-23) — 修复设置面板 + 标题改名

### Fixed
- 修复 kd-v2.1 中 `loadSettingsUI`/`saveSettings`/`testCustomApiKey`/`onNotificationsToggle`/`updateNotificationsHint` 5 个函数被误删导致设置齿轮不可点的问题
- 修复 `split('\n')`/`join('\n')` 在 HTML_CONTENT 模板字符串中被解释为实际换行符导致 JS 语法错误的问题，改用 `String.fromCharCode(10)`

### Changed
- 左上角标题从 "GPT2 生图" 改为 "AI生图"
- 版本号小字从 nav-right 移到标题右侧（紧贴标题显示）
- VERSION 更新为 `kd-v2.2`

---

## kd-v2.1 (2026-07-23) — 多 key 轮换 + 水印模块恢复

### Added
- **日额度本地计数器**：`state.dailyUsage = {date, count, exhausted}`
  - `getTodayGMT8()` 返回 GMT+8 当日日期字符串
  - `checkAndResetDailyUsage()` 跨日自动重置
  - `incrementDailyUsage()` 任务成功提交后 +1
  - `markDailyExhausted()` 遇"日限额已用完"错误立即标记当日已耗尽
  - `renderDailyUsageBadge()` 右上角徽章渲染（共享 key 显示 X/999，自定义 key 显示 X，已耗尽显示 0/999 红色）
  - 常量 `DAILY_QUOTA = 999`
- **自定义 key 自动切换**：用户在设置面板填入 `customApiKey95` 后，`getEffectiveKey()` 自动优先使用，无需切换通道
- **`isUsingCustomKey()` 工具函数**：用于决定 UI 显示模式

### Changed
- **单通道架构**：`CHANNELS` 字典 → `UPSTREAM` 单一常量
- **`apiFetch / apiFetchMultipart`**：移除 `X-Channel` 头，直接用 `Authorization: Bearer <effectiveKey>`
- **`executeTask` 包装层**：移除通道故障切换逻辑，直接委托给 `executeTaskOnChannel`，并在成功后 `incrementDailyUsage()`，失败时检测日限额错误并 `markDailyExhausted()`
- **`registerAccount()`**：合并 `registerKeydrawAccount`，单一函数处理 Gift Key 刷新；若用户已配置 `customApiKey95` 则直接返回当前账号
- **`loginAccount()`**：移除 maliang 分支，单一 gift-key 模式无需登录
- **`refreshQuota()`**：简化为直接维持 credits=9999（keydraw 无 quota API）
- **`ensureChannelReady()`**：单一逻辑，根据 `getEffectiveKey()` 初始化账号池
- **`migrateOldStateIfNeeded()`**：删除 v1.x 遗留字段（`accountsByKeydraw/Maliang/Custom97api`, `activeChannel`, `lastChannel`, `defaultPassword`, `autoCheckin`, `autoFallbackGpt2`），把 `accountsByKeydraw` 合并到 `state.accounts`
- **`saveSettings() / loadSettingsUI()`**：移除 `defaultPassword/autoCheckin/autoFallbackGpt2` 字段；新增 `customApiKey95` 变化时重新初始化账号池
- **Worker 后端 `handleProxy`**：移除 `pickChannel`，直接用 `UPSTREAM` 常量
- **`corsHeaders()`**：`Access-Control-Allow-Headers` 移除 `X-Channel`，新增 `Authorization`
- **顶部导航栏**：移除 `channelSelect` 下拉框，改为 `dailyUsageBadge` 徽章
- **产品标题**：`AI生图` → `GPT2 生图`
- **设置面板按钮**：移除"注册新账号/手动添加/批量签到/清理无余额/邀请好友/官网注册"，保留"刷新 Gift Key/刷新额度/批量验证/97api 官网"
- **设置面板字段**：移除"默认密码/额度耗尽自动签到/autoFallbackGpt2"，保留"轮换策略/autoRegister/通知/自定义 97api API Key"
- **邀请好友面板**：完全移除（keydraw 共享 Gift Key 模式无邀请系统）
- **帮助面板**：更新产品简介、额度说明，移除"通道选择"章节

### Removed
- `CHANNELS` 字典（含 keydraw/custom-97api/maliang 三通道配置）
- `DEFAULT_CHANNEL`, `CHANNEL_HEADER` 常量
- `pickChannel()` Worker 后端函数
- `getActiveChannel()`, `getChannelAuthHeaders()`, `onChannelChange()`
- `syncAccountsToActiveChannel()`, `effectiveChannel()`, `persistActiveChannelAccounts()`
- `var _origSaveState = saveState; saveState = function(){...}` hook
- `generateUsername()`, `generatePassword()`
- `getChainInviteCode()`
- `registerMaliangAccount()`, `registerKeydrawAccount()`（合并到 `registerAccount()`）
- `loginAccount()` 中的 maliang 分支
- `checkinAccount()`, `checkinAll()`
- `addManualAccount()`
- `showInvitePanel()`, `closeInvitePanel()`, `copyInviteLink()`
- `cleanupInsufficientAccounts()`（keydraw 共享 key 模式下"废弃"由日限额耗尽自动触发）
- 设置面板"批量签到(已下线)"按钮、"官网注册"链接（指向 grok.17nas.com）
- 邀请好友面板 HTML
- `state.accountsByKeydraw/Maliang/Custom97api`, `state.abandonedAccountsByKeydraw/Maliang/Custom97api`
- `state.activeChannel`, `state.lastChannel`
- `state.settings.defaultPassword/autoCheckin/autoFallbackGpt2`

### Preserved
- 继承 v1.2 的核心 bug 修复：`pollTask()` 将 `status:"error"` 视为终止状态
- 继承 v1.2 的 `extractErrorMessage()` 上游错误透传逻辑
- 历史记录 / 提示词库 / 参考图 / 浏览器通知 / 主题切换 / 媒体代理 等所有用户功能
- v1.x 旧 state 自动迁移到 kd-v2.0 单一 accounts 池

### Deployment
- 部署目标：`ai-image.lishuhang.workers.dev` + `gpt.lishuhang.com`
- v1.x beta 站点（`ai-image-beta.workers.dev` + `gpt2b.lishuhang.com`）由用户自行下线

---

## v1.2 (2026-07-22) — 上游错误透传 + 自定义 97api Key 通道 + 马良通道下线标记

### Added
- `pollTask()` 将 `status:"error"` 视为终止状态（v1.1 只识别 success/failed，导致对"日限额已用完"持续轮询 300s 然后误报"超时"）
- `extractErrorMessage()` 原样透传"日限额/api key/quota/额度"等关键字错误
- 超时消息附带 `upstreamError / upstreamProgress`
- `custom-97api` 通道：用户填入自己的 97api.com API Key
- 设置面板新增 API Key 输入框 + 显示/隐藏 + 测试按钮
- `auto` 模式下，keydraw 配额耗尽时自动切换到 custom-97api 重试

### Changed
- 马良通道（grok.17nas.com）标记为 `deprecated: true`
- `channelSelect` 中马良选项加 "(已下线)" 标记并 disabled
- `ensureChannelReady()` 跳过马良的自动注册分支

---

## v1.1 (2026-07-22) — 性能优化与代码精简

- gift-key 异步刷新：先用 fallback key 渲染首屏，gift-key 异步获取不阻塞
- 移除 `autoFallbackGpt2` 整段（v0.7 起已禁用，gpt-image-2 是唯一模型）
- 移除 `refreshModelAvailability / updateModelAvailabilityUI / modelAvailHint`
- 移除 `calcGptImage2Size`（仅 fallback 路径使用）
- 移除 video 模型相关函数（`isVideoModel / VIDEO_CREDITS_PER_SEC / durationSelect` 等）
- 移除 `grok-imagine-*` 模型选项与 `MODEL_CREDITS_PER_IMAGE` 中的对应条目
- 精简 btn 系列 CSS
- 移除 changelog `<dl>`（v0.1-v0.7 历史，~3KB）

---

## v1.0 — 多通道架构

- 新增顶部通道选择器（自动 / KeyDraw / 马良）
- '自动' 模式：硬失败时自动切换到另一通道
- 后端 `handleProxy / image-proxy / gift-key` 按 `X-Channel` 头分发
- 账号池按通道独立维护：`state.accountsByKeydraw / state.accountsByMaliang`
- 旧 state 自动迁移

---

## v0.7 — 四项修复

- `addToPromptLib` 缺失 `renderPromptLib()` 调用
- `refreshModelAvailability` 改为 no-op
- `showInvitePanel` 友好降级
- `getChainInviteCode` 短路返回 null

---

## v0.5-v0.6 — 前端 JS bug 修复

- v0.5: 修复 HTML_CONTENT 模板字符串内 `//` 行注释吞掉后续代码的两个语法错误
- v0.6: 修复 `apiFetch` 双 `/api/` 前缀 bug

---

## v0.1-v0.4 — 早期版本

- v0.1: 接入 keydraw.97api.com（V2EX 帖 https://www.v2ex.com/t/1222012）
- v0.3: 版本徽章
- v0.4: `client_task_id` 格式要求 `timestamp-randomhex`
