# Changelog — GPT2 生图 Worker

所有版本变更记录。v0.x-v1.2 为多通道架构，kd-v2.0 起合并为单一 keydraw 通道。

---

## kd-v2.0 (2026-07-23) — 分支合并版本

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
