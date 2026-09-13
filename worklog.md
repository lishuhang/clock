# kdr Worker 部署工作日志

本文件记录 `lishuhang/clock` 仓库中 `temp/gpt2-worker-kdr-v*.js` 系列 Worker 的部署历史与状态。

线上地址：https://ai-image.lishuhang.workers.dev/
Worker 名称：`ai-image`
Account ID：`ec44dddde866c789a9dd26f5d0cdb248`

---

## 部署历史

### 2026-08-26 09:18 UTC — v1.0
- **文件**：`temp/gpt2-worker-kdr-v1.0.js`
- **大小**：169,617 bytes
- **commit**：上游仓库已有
- **变更说明**：
  - Keydraw 通路复活（基于 kd-v2.3 完整版）
  - 恢复 Gift Key 免费通路，`giftKeyFallback = 'Gift-Key-V2EX653'`
  - `/api/gift-key` 端点支持动态轮换
- **部署结果**：HTTP 200 ✅
- **线上验证**：首页 200、`/api/gift-key` 返回 `{"key":"Gift-Key-V2EX653"}`

### 2026-08-26 09:31 UTC — v1.1
- **文件**：`temp/gpt2-worker-kdr-v1.1.js`
- **大小**：169,602 bytes
- **commit**：上游仓库已有
- **变更说明**：
  - 修复设置齿轮点击报错（移除未定义的 `renderStorageInfo` 调用）
- **部署结果**：HTTP 200 ✅
- **线上验证**：通过 CF API 拉取线上脚本，包含 `kdr-v1.1` 版本标记，文件大小完全匹配

### 2026-08-26 10:06 UTC — v1.2
- **文件**：`temp/gpt2-worker-kdr-v1.2.js`
- **大小**：175,170 bytes
- **commit**：上游仓库已有
- **变更说明**：
  - 页面加载时自动探测 gift key 真实额度（创建最小任务+轮询一次）
  - 额度用尽时右上角显示到 GMT+8 零点的倒计时
  - 用尽时 toast 提示，标签页后台保持时到点发送浏览器通知
  - 修复设置齿轮点击报错（继承 v1.1）
- **部署结果**：HTTP 200 ✅
- **线上验证**：通过 CF API 拉取线上脚本，包含 `kdr-v1.2` 版本标记，文件大小完全匹配（175,170 bytes）

---

## 工作流约定

1. **本地工作目录**：`/home/z/my-project/clock/`
2. **Worker 源文件位置**：`temp/gpt2-worker-kdr-v*.js`
3. **Cloudflare 部署方式**：通过 CF API 直接 PUT `accounts/{id}/workers/scripts/ai-image`，使用 `body_part` 格式（Service Worker 格式，非 ES Module）
4. **部署后验证**：
   - HTTP 状态码必须为 200
   - 通过 CF API GET 脚本，比对文件大小与版本标记字符串
5. **推送策略**：批量推送，避免频繁 push。每次部署完成后追加本日志，攒到 2~3 次部署再 commit & push 一次
6. **Worklog 双写**：本仓库 `worklog.md` + `/home/z/my-project/worklog.md`（本地多智能体共享）

---

## 2026-09-13 07:49 UTC — kmage-v1.0（新通道上线，kdr 停用）

### 背景与诊断
- **kdr 通道故障原因**：上游 keydraw.97api.com 九月初改版为 Draw Studio，生成 API 契约变化——`key` 与 `host` 必须放入请求 body（host 由 /api/channels 下发：www.97api.com / new.97api.com），旧版仅用 Authorization 头 → 全部生成请求 400「请求地址只能选择 www.97api.com 或 new.97api.com」。
- Gift Key 本身仍有效（新格式实测可出图），但 kdr 前端未适配新契约，通道瘫死，停止维护。

### 新通道选型
- 上游切换为 **image.dddd.zone（kmage · AI 视觉工作台）**：
  - 官方 OpenAI 兼容 API（/v1/images/generations），Bearer kmage_* 密钥，1 积分/张，失败自动返还
  - 注册仅 邮箱+密码（无验证码/无邮箱验证）；签到 +5 积分/天（注册满 24h 开放）；老虎机 RTP 95.88% 负期望，不纳入自动积分来源
- 经济模型：号池 N 账号 ≈ 每日稳定 5N 张图（注册各送 1 分）

### 实现（gpt2-worker-kmage-v1.0.js，48,600 bytes）
- 架构：单文件 Service Worker（沿袭 kdr v1.2 骨架）+ 马良 v27.2 号池模式
- 路由：`/api/kmage/*` → 上游 `/api/*`（会话代理，X-Kmage-Session 头 ↔ kmage_session Cookie）；`/kmage/v1/*` → 上游 `/v1/*`（Bearer 透传）；`/healthz`
- 号池：localStorage 存储，字段 email/password/session/apiKey/credits/lastCheckinDay/eligibleAt；轮换策略 most-credits / round-robin；自动注册（+1 分）、批量签到（+5 分/天）、补建 Key、401 自动重登、402 自动换号、429 退避重试；自动签到开关
- 生图：模型 gpt-image-2 / 2.5-flare / 2.5-sunburst；比例 1:1~3:4/auto（size 直传比例串）；质量 auto/low/medium/high；图生图 reference_images ≤10 张；AbortController 180s 终态

### 验证记录
- 本地：node --check 通过；3 个内嵌 script 块分别通过语法检查；mock 服务器 + headless 浏览器 E2E（注册→建Key→生图 38s 成功，UI 截图确认）
- 生产：PUT `accounts/{id}/workers/scripts/ai-image` 部署成功（2026-09-13T07:49:39Z）
  - 线上首页 200，版本标记 kmage-v1.0，/healthz 正常
  - CF API 拉取线上脚本与本地文件 diff 完全一致
  - 生产路由端到端：注册（201+会话）→ 建 Key → 生图 HTTP 200（42s，735KB PNG，内容与提示词一致）
- 线上地址：https://ai-image.lishuhang.workers.dev/ （worker 名称 ai-image，与 kdr 同位替换）
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.0.js`

### 遗留事项
- kdr v1.2 可按新契约修复（body 传 key+host），暂留源码待定
- kmage 积分总耗用：验证期共注册 3 个探针/验证号，消耗 3 积分
---

## 2026-09-13 08:45 UTC — kmage-1.1（可观测性与号池运维增强）

### 用户反馈驱动（v1.0 上线后）
- 生图失败无详细日志 → 需要控制台与日志导出（参考 tts.lishuhang.workers.dev 形态）
- 号池签到 24h 等待提示不精确；号池需要 JSON 导入导出
- 需要浏览器原生通知；需要核对马良反模式化原则；readme/changelog 需自包含并提示 AI Agent；div.brand 改「AI生图」

### 实现（gpt2-worker-kmage-v1.1.js，81,856 bytes）
- **日志控制台**：运行号分组（R+时间戳），记录账号选择/参数/上游状态码/耗时/错误原文（含非 JSON 截断）/换号重试决策；导出全部或本次运行（.txt 含版本/UA/页面）、复制、只看错误、清空；localStorage 持久化 300 条
- **号池导入导出**：完整凭据 JSON，导入去重 + 缺会话自动重登
- **通知**：Notification API，成功/失败/超时，开关在号池设置，拒绝时自动回退
- **24h 规则**：仅限签到不影响生图（实测确认）；提示精确到时分；新生号生图被拒自动换号并提示剩余时间
- **反模式化**：拟人邮箱（词库×6模式×随机大小写）、无指纹密码/KeyName、批量注册 2.5~8s 随机间隔、签到乱序 0.8~2.8s、UA 透传
- **文档**：内嵌自包含 README+CHANGELOG（「文档」按钮）、HTML 头部 AI Agent 注释、页脚提示、/about 自描述接口
- **品牌**：div.brand=「AI生图」，kmage-1.1

### 关键坑（历史重演）
- kd-v2.2 教训再现：HTML_CONTENT 模板字符串内页面 JS 的 `\n` 转义在 Node 求值时变真实换行 → 浏览器 script 块语法错误（node --check 查不出，因为文件本身合法）。本次 logsToText 的 join('\n') 与 DOCS pre 块均改为 String.fromCharCode(10)
- resp.json() 失败后 body 已消费，resp.text() 拿不到原文 → 改为先读全文再 JSON.parse

### 验证
- node --check 整文件 + 3 个内嵌 script 块分别通过
- 本地 E2E（Node harness 跑真实 worker 代码 + mock 上游 + 无头浏览器）：成功/500 HTML/503/402 路径、日志渲染筛选导出、导入去重、通知回退、批量签到乱序自动重登、刷新日志恢复——全部通过，UI 截图确认
- 生产：PUT `accounts/{id}/workers/scripts/ai-image`（metadata body_part 格式）→ /healthz 返回 kmage-1.1，首页 72,625B，CF API GET 线上脚本与本地逐字节一致
- 生产端到端：新号注册→建Key→生图 200（46s，1MB PNG 内容正确）；/about 正常
- 积分消耗：验证期注册 2 个探针号（本地 mock 不耗分；生产 2 号各耗 1 分生图验证）

### 部署
- 线上：https://ai-image.lishuhang.workers.dev/ （worker 名 ai-image）
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.1.js`
- README.md 重写为自包含（当前生产状态/架构/排障指引/历史归档），CHANGELOG.md 增 kmage-1.1 条目

---

## 2026-09-13 08:50 UTC — kmage-1.1 补丁：5xx 网关错误自动重试（debug 截图归因）

### 用户 /debug 截图分析（commit b0a0733）
- 截图1：图生图（2 参考图 + 16:9 + sunburst + 中文长提示词）失败，状态栏仅显示「生成失败」无任何细节
- 截图2：号池 4 账号均「待激活 24h」（批量注册正常，签到因 24h 冷却被限制）

### 复现与归因（生产实测）
- 注册新号 → 1 张 736KB 参考图 + 16:9 + sunburst → **HTTP 504**（32.4s，响应体纯文本 `error code: 504`）
- 同一请求重试 → **HTTP 200 成功**（34.9s，1.6MB PNG）→ 结论：上游对图生图大请求体偶发 504，重试即成功
- v1.0 只显示「生成失败」的原因：504 响应体非 JSON，kmageV1 解析后 data={}，upstreamErrMsg 走 fallback
- 顺带发现：图生图链路本身正常（v1.1 修复原文捕获后此类失败会显示 504 原文并记日志）

### 修复（v1.1 最终版，83,812 bytes）
- 新增 5xx 网关错误分支：4s 后同号重试一次 → 仍失败自动换号重试一次，全程日志
- 本地 mock 注入「首次 504 重试成功」场景 E2E 通过
- 重新部署：/healthz kmage-1.1，线上脚本与本地 diff 一致，首页含 5xx 提示文本
- 验证期积分消耗：本轮生产验证共注册 4 探针号（各 1 分），其中 1 次生图成功消耗

---

## 2026-09-13 09:30 UTC — kmage-kdr-1.2：kdr 通道修复复活 + 双通道选择器 + UI/文档重构

### kdr 故障根因与新契约实测（curl 直连上游）
- 上游存活：`/api/gift-key` → `{"alias":"20260907-BEST-KEY","key":"20260907-BEST-KEY"}`；`/api/channels` 下发两条线路（www/new.97api.com）与模型清单
- 新契约（抓取改版后前端 bundle 分析 + 实测）：生成 `POST /api/image-tasks/generations`，body = `{client_task_id,key,host,model,prompt,quality,size,ratio,n:1}`（不再用 Authorization 头）；免费 Gift Key 固定 www.97api.com + gpt-image-2 + 1K；图生图 `POST /api/image-tasks/edits`（multipart 9 字段 + image[]）；轮询 `GET /api/image-tasks/{id}`（queued→running→success，结果 `data[].url` 为图床链接）
- 直连实测：提交 → 33s 出图成功（quality=low 快速验证）

### v1.2 实现（115.9KB，基于 v1.1 外科手术+重写混合）
- 后端：新增 `/api/kdr/*` 透明代理（UA/Origin/Referer 伪装沿用，multipart 兼容）与 `/kdr/img?url=` 结果图拉取代理；healthz/about 双通道化
- 前端：通道选择器（ver 右侧，默认 kmage，持久化 kmage_channel_v1）；kdr 状态独立存储（kdr_state_v1）+ 旧 maliang_state 自定义 Key 自动迁移；generate 拆分为统一入口 + generateKmage/generateKdr 双流程；kdr 任务轮询（3s/180s）、URL→b64（/kdr/img → FileReader）、Key 被拒自动刷新共享 Key、提交 5xx 4s 重试
- UI：footer 删除；「文档」+「帮助」→「关于」；「号池」→「设置」（齿轮 SVG）、「日志」→「控制台」（终端 SVG）、「关于」（圆圈 i SVG）；画笔+颜料盘 favicon；「ai」字母组合 logo（header + 关于顶部）；设置级 JSON 导出（号池+全部设置+kdr 配置）/导入（自动识别三种格式）
- 文档：对外脱敏（页面零源站域名，统一「kmage 站点/kdr 站点」，真实上游仅 /about）；关于弹窗整合马良→至今完整时间线（正序）；仓库 CHANGELOG/README 按实际日期重排

### 关键 bug（本地 E2E 拦截）
- **kd-v2.2 经典坑重演**：`split(/\r?\n/)` 写在 HTML_CONTENT 内，`\r\n` 被外层模板字符串吞成真实换行 → 内层正则非法、整个 script 块静默不执行（node --check 查不出，HTML 模板内容不参与语法检查）。浏览器 eval 分块定位后改 String.fromCharCode 拆行；静态检查脚本新增「HTML_CONTENT 内禁 `\` 转义」规则永久拦截
- kdrFetchB64 `'resp.ok'` 字面量笔误（恒真）→ 修正
- 部署脚本 multipart 两连坑：boundary 缺失（10021）→ part name 应为 worker.js 而非 body_part；最终 curl -F 直传成功

### 验证
- 静态：node --check + 自检脚本（id 引用 59/62、89 函数定义、34 绑定、脱敏断言、双通道路由）全过
- 本地 E2E（mock 双上游 + 无头浏览器）：kmage 注册→生图、kdr Gift Key→生图（queued→running→success→URL→b64）、kdr 图生图 edits（2 图）、kdr 任务 error 终态、kdr 503 重试（日志确认）、kmage 402、控制台 55 条分组日志、关于弹窗（logo/时间线/脱敏）、设置导出→改→导入回环（通道/kdr Key/UI 联动恢复），全过
- 部署：CF API PUT HTTP 200；/healthz kmage-kdr-1.2 + 双上游；线上页面与本地逐字节一致
- **生产双通道端到端**：kdr 免费 Gift Key 真实出图 36.6s（2,259KB PNG，橘猫画画，与提示词一致）；kmage 注册新号（+1 分）→ sunburst 生图 30.7s 成功（1 分扣减正常）
- 积分消耗：本轮注册 1 探针号（+1 分免费额度，自给自足）
