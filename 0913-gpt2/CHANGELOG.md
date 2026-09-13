# Changelog — AI生图 Worker（kmage + kdr 双通道）

按**实际迭代发生日期正序**排列，整合从马良渠道至今的完整试错过程。
当前生产：`kmage-kdr-1.2`（Cloudflare Worker `ai-image`，https://ai-image.lishuhang.workers.dev/）。

> 页面内嵌「关于」文档对源站做了脱敏（以「kmage 站点 / kdr 站点」表述）；本仓库文档为维护者视角，保留真实上游地址。

---

## 阶段一：马良渠道（2026-07 上旬及以前，本地迭代 v0.x → v27.2）

项目的起点。上游为马良站点（grok.17nas.com，grok webui 中转）。在本地持续迭代了 27+ 个版本，沉淀了本项目的全部核心资产：

- **号池模式**：多账号注册/轮换（most-credits / round-robin）、签到自动化、401 重登、402 换号
- **反模式化原则**：拟人化邮箱/密码生成（去固定指纹）、批量操作随机间隔与乱序、UA 透传真实访客 UA；IP 伪造在 v26.1 实测无效后移除
- 功能资产：历史记录、提示词库、参考图（图生图）、浏览器通知、主题切换、Gemini 水印模块（v27.2 修复 alpha 强度并加入自动增益检测）
- **终局**：上游加 Cloudflare Challenge 墙，server-side 不可用，马良通道终止。单文件 Worker 内嵌模板字符串的 `\n` 转义坑、同名 const 冲突等工程教训均在同期记录

代表性文件：`gpt2-worker-v27.2.js`（留档）。

## 2026-07-22 — kd v0.x → v1.2（Keydraw 接入与多通道时期）

- **v0.1**：接入 keydraw.97api.com（V2EX 自荐帖公开 Gift Key 模式，免注册共享 Key）
- **v0.5-v0.6**：HTML_CONTENT 模板字符串内 `//` 行注释吞代码、`apiFetch` 双 `/api/` 前缀等前端 bug 修复
- **v1.0 多通道架构**：顶部通道选择器（自动/KeyDraw/马良），后端按 `X-Channel` 头分发，账号池按通道独立
- **v1.1**：gift-key 异步刷新不阻塞首屏；移除 video 模型与 `autoFallbackGpt2` 等死代码
- **v1.2**：`pollTask()` 将 `status:"error"` 视为终止态（修复「日限额已用完」被持续轮询 300s 误报超时）；`extractErrorMessage()` 上游错误原样透传；新增 custom-97api 自定义付费 Key 通道；**马良通道标记 deprecated**

## 2026-07-23 — kd-v2.0 → v2.2（单通道收敛）

- **kd-v2.0**：移除多通道架构（`CHANNELS`/`pickChannel` 等），收敛为单一 keydraw 通道；邀请面板下线
- **kd-v2.1**：日额度本地计数器（GMT+8 零点重置，右上角徽章「今日 X / 999」）；多自定义 Key 共池轮换；旧 state 自动迁移
- **kd-v2.2**：修复 v2.1 误删 5 个设置函数导致齿轮不可点；**修复 `split('\n')` 在 HTML_CONTENT 模板中被解释为真实换行导致 JS 语法错误的经典坑**（改用 `String.fromCharCode(10)`）；标题改为「AI生图」
- 部署：`ai-image.lishuhang.workers.dev` + `gpt.lishuhang.com`

## 2026-07 下旬 ～ 2026-08-19 — SQ / PM 路线试错与公开通道复核（未发布版本）

- **SQ 路线（Squido.ai，sq-v1.0）**：Turnstile 人机验证无法在 headless 容器绕过；手工配置 session 后 credits=0；KV+Cron 保活原型未完成端到端验证
- **PM 路线（Pixmind.io，pm-v1.1~v1.2）**：双 Worker 半自动方案已部署；emailPassword 登录 API 返回 500 未解决
- **2026-08-19 复核结论**：重新检索并匿名实测 V2EX 公开候选（Keydraw / Flaq / gptimage2.com / NanoBananaTool / Morphic 等），未找到同时满足「免登录、免人机验证、可稳定第三方代理、明确免费额度」的上游；该轮未发布任何版本、未覆盖生产域名（过程记录见 git 历史的 research notes）

## 2026-08 下旬 ～ 09 上旬 — kdr-v1.2 时期与上游改版瘫死

- **kdr-v1.2**（KeyDraw 通道独立版）：单通道 + Gift Key 自动轮换 + 自定义 97api Key + 媒体代理，部署于 `ai-image`，为 kmage 之前的线上基线
- **2026-09 上旬上游改版（Draw Studio）**：生成 API 契约变化——`key` 与 `host` 必须放入请求 body（host 由 `/api/channels` 下发：www.97api.com / new.97api.com），旧版仅用 Authorization 头 → 全部生成请求 400「请求地址只能选择 www.97api.com 或 new.97api.com」。共享 Gift Key 本身仍有效。kdr 前端未适配，通道瘫死

## kmage-v1.0 (2026-09-13) — kmage 通道上线，同位替换 kdr

### Background
- kdr 瘫死后探查新上游 image.dddd.zone（kmage · AI 视觉工作台）：官方 OpenAI 兼容 API、注册仅邮箱+密码无验证码、签到 +5 分/天（注册满 24h 开放）、1 积分 = 1 张图、失败自动返还
- 号池模式与反模式化原则继承自马良 v27.2

### Added
- 号池管理：自动注册（+1 分）、批量签到（+5 分/天/号）、补建 API Key、刷新额度、禁用/归档、删除
- 轮换策略 most-credits / round-robin；401 自动重登重建 Key；402 自动换号；429 退避重试
- 生图：gpt-image-2 / gpt-image-2.5-flare / gpt-image-2.5-sunburst；7 种比例；质量 auto/low/medium/high；图生图 ≤10 张（PNG/JPG/WebP ≤10MB）
- 会话代理 `/api/kmage/*`（X-Kmage-Session 头 ↔ Cookie 还原）、Bearer 代理 `/kmage/v1/*`、`/healthz`
- 全部状态 localStorage，Worker 无状态无 KV

### Deployment
- 部署 `ai-image`；生产端到端：注册 201 → 建 Key → 生图 HTTP 200（42s，735KB PNG）
- 备份 `0913-gpt2/gpt2-worker-kmage-v1.0.js`（48,600 bytes）

## kmage-1.1 (2026-09-13) — 可观测性与号池运维增强

### Added
- **运行日志控制台**：按运行号（R+时间戳）分组记录账号选择、请求参数、上游状态码与耗时、错误响应原文（修复 body 双重读取丢失原文）；导出全部/本次运行（.txt）、复制、只看错误、清空；localStorage 环形缓冲 300 条刷新不丢
- **号池 JSON 导入/导出**（含会话与 Key；导入按邮箱去重、缺会话自动重登）
- **浏览器原生通知**（成功/失败/超时；tag+renotify；权限拒绝自动回退开关）
- **`/about` 自描述接口** 与内嵌自包含 README/CHANGELOG（AI Agent 可将本页整体作为 skill 调用）
- **5xx 网关错误自动重试**（debug 截图归因：图生图 ~1MB 大请求体上游偶发 504，实测重试即成功）：4s 同号重试一次 → 换号再试一次

### Changed
- **24h 规则明确化**：冷却仅限制签到（上游 403 + eligible:false），不限制生图；等待提示精确到「X小时Y分」；新生号生图被拒自动提示剩余时间并换号
- **反模式化（马良原则）**：拟人邮箱池（去 v1.0 固定 `kmg` 前缀+时间戳指纹）、12~15 位随机密码（去 `Zq9` 后缀）、Key 备注名词池随机；批量注册 2.5~8s 随机间隔（15% +4s）、签到乱序 0.8~2.8s；UA 透传
- div.brand 改「AI生图」；修复 `resp.json()` 消费 body 后取不到原文的问题（先读全文再 parse）

### Deployment
- 生产端到端 46s 成功（1,027,451B PNG）；E2E mock 故障注入全路径通过
- 备份 `0913-gpt2/gpt2-worker-kmage-v1.1.js`（最终 83,812 bytes，含 5xx 补丁）

## kmage-kdr-1.2 (2026-09-13) — kdr 修复复活 + 双通道 + UI/文档重构（本版）

### Fixed
- **kdr 通道修复复活**：适配上游 2026-09 新契约——
  - 生成请求不再使用 Authorization 头，改为 `key`/`host` 放入请求 body（`POST /api/image-tasks/generations`，body 含 client_task_id/key/host/model/prompt/quality/size/ratio/n）
  - 图生图走 `POST /api/image-tasks/edits`（multipart：key/host/model/prompt/quality/size/ratio/n/client_task_id + image 文件数组）
  - 任务制轮询 `GET /api/image-tasks/{id}`（3s 间隔 / 180s 上限；queued→running→success/error）
  - 结果为图床 URL：新增 Worker 代理 `/kdr/img?url=` 带 Referer 拉取，前端转 base64（与 kmage 的 b64 数据流对齐）
  - 免费 Gift Key 固定「主线路 + gpt-image-2 + 1K」档；设置页可填自定义付费 Key 自动优先，解锁全部模型与 2K/4K
  - 401/403 Key 被拒自动刷新共享 Key 重试；5xx 提交 4s 重试；轮询网络异常容错
  - 真实验证：直连上游 curl 出图（queued→running→success 33s）+ 生产 Worker 全链路 36.6s 出图（2,259KB PNG）
- kdr 旧版 localStorage（maliang_state）中的自定义 Key 自动迁移

### Added
- **通道选择器**：header `.ver` 右侧下拉（kmage 默认 / kdr），持久化 `kmage_channel_v1`；切换联动模型列表、分辨率档、徽章、生成按钮文案与设置弹窗区块
- **设置级 JSON 导入/导出**：「导出全部设置」打包 kmage 号池+设置项 + kdr 自定义 Key/Gift Key + 通知开关 + 当前通道；「导入设置」自动识别设置包 / 旧号池 / 裸账号数组
- **favicon**：画笔+颜料盘线条 SVG（data URI 内联）
- **「ai」字母组合 logo**：线条 SVG，出现于 header 左上角与「关于」弹窗顶部

### Changed
- **UI 重构**：footer 区域删除；「文档」与「帮助」合并为「关于」；「号池」按钮改「设置」（齿轮线条 SVG 图标）、「日志」改「控制台」（终端线条 SVG 图标）、「关于」（圆圈 i 线条 SVG 图标），均为纯图标按钮（title/aria-label 保留）
- **对外文档脱敏**：页面可见文案与内嵌文档不再出现任何源站域名/品牌名，统一以「kmage 站点 / kdr 站点」表述；真实上游仅经 `GET /about` 自描述接口提供排障方（本仓库文档保留真实地址）
- **内嵌「关于」文档整合完整迭代时间线**：从马良渠道（v27.2 收官）→ kd 多通道 → kd-v2.x → SQ/PM 试错与 08-19 复核 → kdr 改版瘫死 → kmage v1.0/1.1 → 本版，按实际日期正序
- `/healthz`、`/about` 扩展双通道信息；日志行增加 `[kmage]`/`[kdr]` 前缀；近期任务列表增加通道标签
- **工程坑防守**：内嵌模板字符串内禁止 `\` 转义序列（含正则），静态检查脚本强制（kd-v2.2 坑重演拦截：`split(/\r?\n/)` → `String.fromCharCode` 拆行）

### Deployment
- 部署 `ai-image`（CF API PUT，metadata `{"body_part":"worker.js"}`，HTTP 200）
- 验证：/healthz 返回 kmage-kdr-1.2 + 双上游；/about 双通道；线上页面与本地逐字节一致
- 生产端到端双通道：**kdr 免费 Gift Key 真实出图 36.6s（2,259KB PNG，内容与提示词一致）**；**kmage 注册新号（+1 分）→ 生图 30.7s 成功**
- 本地 E2E：mock 双上游 + 无头浏览器，kmage 生图 / kdr 任务轮询与图生图 / 任务 error / 503 重试 / 402 换号 / 设置导入导出回环 / 控制台与关于弹窗，全部通过
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.2.js`（约 115.9 KB）
