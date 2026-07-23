# gpt2-worker-kd — GPT2 生图 Cloudflare Worker

> **版本**: kd-v2.0  ｜  **更新日期**: 2026-07-23  ｜  **上游**: [keydraw.97api.com](https://keydraw.97api.com)
>
> **部署**: `ai-image.lishuhang.workers.dev` + `gpt2.lishuhang.com`（v1.x beta 站点将下线，分支合并）

---

## 0. TL;DR

这是 v1.x 多通道架构（keydraw + maliang + custom-97api）的**分支合并版本**，统一为单一 keydraw 通道。修复了 v1.x 误报"超时(300秒)"的 bug（实际是上游"日限额已用完"被吞掉），并新增右上角日额度本地计数器。

```js
// 部署：将本文件作为 Cloudflare Worker 脚本部署即可
// 无需环境变量，无需 wrangler.toml 配置（单文件 ES Module）
```

---

## 1. kd-v2.0 核心变更

### 1.1 分支合并：单通道架构

| v1.x（多通道） | kd-v2.0（单通道） |
|---|---|
| `CHANNELS = { keydraw, custom-97api, maliang }` | `UPSTREAM = { base, origin, giftKeyFallback }` |
| `channelSelect` UI 下拉框（自动/KeyDraw/自定义Key/马良） | 移除，右上角改为日额度计数器 |
| `X-Channel` 请求头分发 | 移除，所有请求直接走 keydraw |
| `accountsByKeydraw / accountsByMaliang / accountsByCustom97api` 三个池 | 统一 `state.accounts` |
| `activeChannel / lastChannel` 状态字段 | 移除 |
| `executeTask` 包装层做通道故障切换 | 直接委托给 `executeTaskOnChannel` |
| `pickChannel()` Worker 后端 | 移除 |

### 1.2 马良通道彻底下线

删除所有 maliang 相关代码：
- `registerMaliangAccount()` —— 用户名+密码注册（马良专用）
- `loginAccount()` 中的 maliang 分支 —— Cookie 鉴权登录
- `generateUsername() / generatePassword()` —— 仅马良注册需要
- `getChainInviteCode()` —— 马良邀请系统
- `checkinAccount() / checkinAll()` —— 马良签到
- `showInvitePanel() / closeInvitePanel() / copyInviteLink()` —— 邀请好友面板
- `addManualAccount()` —— 手动添加账号
- `cleanupInsufficientAccounts()` —— 清理无余额账号（keydraw 共享 key 模式无此概念）
- 设置面板的"批量签到(已下线)"/"官网注册"按钮
- CORS 头中的 `X-Channel` 声明

### 1.3 自定义 97api API Key 合并到 keydraw 通道

v1.2 的 `custom-97api` 通道独立存在，需要用户切换通道。kd-v2.0 简化为：
- 用户在设置面板填入 `customApiKey95` 后，**自动替代共享 Gift Key**，无需切换通道
- `getEffectiveKey()` 优先级：`state.settings.customApiKey95 > UPSTREAM.giftKeyFallback`
- `isUsingCustomKey()` 用于决定日额度计数器是否显示 999 上限

### 1.4 日额度本地计数器

**问题背景**：keydraw 共享 Gift Key（`Gift-Key-V2EX999`）全 V2EX 共享 999 张/日，GMT+8 0点重置。但 keydraw 前端只有 3 个 API 端点（`/api/gift-key`, `/api/image-tasks/generations`, `/api/image-tasks/edits`），**无公开 quota 查询接口**。97api 的 `/v1/dashboard/billing/*` 也返回 404。响应头无 `X-RateLimit-*` 字段。任务响应不含 quota 字段。

**实测确认**（2026-07-23 UTC 02:54 = GMT+8 10:54）：早上提交任务状态为 `running`，下午（昨日测试）为 `error: 日限额已用完`。证实 V2EX 共享 key 在 GMT+8 凌晨重置。

**解决方案**：前端维护本地计数器：
```js
state.dailyUsage = { date: 'YYYY-MM-DD', count: N, exhausted: bool }
```
- `date`：GMT+8 当日日期字符串，跨日自动重置 `count=0, exhausted=false`
- `count`：每次任务成功提交 +1（`incrementDailyUsage()`）
- `exhausted`：遇"日限额已用完"错误立即置 true（`markDailyExhausted()`），右上角显示 0/999 红色

**UI**：右上角徽章 `今日 X / 999 张`
- 共享 Gift Key 模式：显示 `X / 999`
- 自定义 key 模式：显示 `X`（无上限，蓝色）
- 已耗尽模式：显示 `0 / 999`（红色，hover 提示重置时间）

### 1.5 错误透传（继承 v1.2 修复）

`pollTask()` 现将 `status:"error"` 视为终止状态，直接抛出 `d.error`。v1.1 只识别 `success/failed`，导致对上游"日限额已用完"错误持续轮询 300s 然后误报"超时"。

`extractErrorMessage()` 原样透传"日限额/api key/quota/额度"等关键字错误，不再替换为模糊描述。

---

## 2. 配置

### 2.1 顶部常量

```js
const UPSTREAM = {
  base: 'https://keydraw.97api.com',
  origin: 'https://keydraw.97api.com',
  giftKeyFallback: 'Gift-Key-V2EX999'
};
const DAILY_QUOTA = 999;  // 共享 Gift Key 全 V2EX 共享 999 张/日
```

### 2.2 用户设置（localStorage）

```js
state.settings = {
  rotationStrategy: 'most-credits',  // 轮换策略（保留兼容，单 key 模式下意义不大）
  autoRegister: true,                // 共享 Gift Key 额度耗尽自动刷新（实际无作用，保留 UI）
  theme: 'system',                   // system / light / dark
  notificationsEnabled: false,       // 生成完成浏览器通知
  customApiKey95: ''                 // 用户自填 97api API Key（填入后替代共享 Gift Key）
};
state.dailyUsage = { date: '2026-07-23', count: 5, exhausted: false };
```

### 2.3 旧 state 自动迁移

v1.x 的 `accountsByKeydraw / accountsByMaliang / accountsByCustom97api / activeChannel / lastChannel` 字段在 `migrateOldStateIfNeeded()` 中被删除，`accountsByKeydraw` 内容合并到统一的 `state.accounts`。

---

## 3. 部署

### 3.1 Cloudflare Workers

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com) → Workers & Pages
2. 新建 Worker（或更新现有的 `ai-image` Worker）
3. 将 `gpt2-worker-kd-v2.0.js` 内容粘贴到编辑器
4. 保存并部署

### 3.2 自定义域名

- `ai-image.lishuhang.workers.dev`（默认 workers.dev 子域）
- `gpt.lishuhang.com`（自定义域名，需在 Workers → 顶部"Triggers" → Custom Domains 中添加）

### 3.3 下线 v1.x beta 站点

按用户要求，`ai-image-beta.workers.dev` 和 `gpt2b.lishuhang.com` 将由用户自行下线，分支合并到本 worker。

---

## 4. API 端点

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回 HTML 前端（单文件内嵌） |
| `/api/gift-key` | GET | 代理 keydraw `/api/gift-key`，返回共享 Gift Key |
| `/api/image-tasks/generations` | POST | 文生图，body: `{client_task_id, prompt, model, size, quality}` |
| `/api/image-tasks/{id}/resume-poll` | POST | 长轮询任务状态，body: `{extra_timeout_secs:120}` |
| `/api/image-tasks/edits` | POST | 图生图（multipart），字段同上 + `image` 文件 |
| `/api/image-proxy` / `/api/media-proxy` | GET | 媒体代理，`?url=<imageUrl>` |

所有 `/api/*` 请求的 `Authorization: Bearer <key>` 头被透传到 keydraw 上游。

---

## 5. 上游错误处理

| 上游错误 | 前端表现 |
|---|---|
| `status:"error", error:"api key 日限额已用完"` | 任务标记失败，错误消息原样显示；调用 `markDailyExhausted()`，右上角计数器变红 0/999 |
| `status:"error", error:"Invalid API key"` | 任务标记失败，错误消息显示；提示用户检查自定义 key |
| `status:"failed"` | 任务标记失败，显示 `d.error` |
| `status:"success"` | 任务标记成功，提取 `d.data[].url` 或 `b64_json`；调用 `incrementDailyUsage()` |
| 网络超时（300s 内无终态） | 显示 `图片生成超时(300秒)，上游最后状态: <upstreamError>` |

---

## 6. 已知限制

1. **无公开 quota API** —— 日额度计数器是本地估算，可能与上游实际剩余有偏差（其他 V2EX 用户也在消耗同一共享 key）
2. **共享 Gift Key 全 V2EX 共享** —— 早上易出图，下午易耗尽。建议重度用户填入自定义 97api API Key（¥0.015/1K 起）
3. **仅支持 gpt-image-2 模型 1K 分辨率** —— keydraw 上游限制
4. **马良通道不可用** —— grok.17nas.com 已加 Cloudflare Challenge，server-side 代理无法访问。如需使用需浏览器自动化方案

---

## 7. 价格参考（来自 [gpt2-v2ex-availability-20260722-1100.csv](./gpt2-v2ex-availability-20260722-1100.csv)）

| 中转站 | 1K | 2K | 4K | 备注 |
|---|---|---|---|---|
| **97api.com 廉价分组** | ¥0.015 | 降级1K | 降级1K | 最便宜，但2K/4K强制降为1K |
| **97api.com 2K-4K分组** | ¥0.1 | ¥0.1 | ¥0.1 | 三档同价，2K/4K最划算 |
| keydraw 共享 Gift Key | 免费 | — | — | 999张/日，GMT+8 0点重置 |
| gptimage2.top | ¥0.30 | ¥0.50 | ¥0.80 | 按量付费 |
| atlascloud.ai | $0.009≈¥0.065 | 同 | 同 | 需注册 |

**最便宜可 server-side 代理方案**：97api.com + 用户自填 key（本 worker 已支持，设置面板填入即可）

---

## 8. 历史版本

- **kd-v2.0** (2026-07-23)：分支合并，单通道架构，马良下线，日额度本地计数器
- **v1.2** (2026-07-22)：上游错误透传 + 自定义 97api Key 通道 + 马良通道下线标记
- **v1.1** (2026-07-22)：性能优化与代码精简
- **v1.0**：多通道架构（keydraw + maliang）
- **v0.x**：早期单通道版本

详见 [CHANGELOG.md](./CHANGELOG.md)。
