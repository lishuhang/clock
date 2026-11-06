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

---
Task ID: 7
Agent: Super Z (main)
Task: kmage-kdr-1.3（竖屏适配 + 深色模式 + 任务历史持久化 + 图标修正 + 部署）

Work Log:
- 探针实测：kmage 上游 b64 模式响应无 URL 字段；response_format=url 仅回 data URI（无持久 CDN 地址）；kdr 任务结果自带上游图床 URL——决定历史记录方案（kmage 存 canvas 缩略图，kdr 存上游 URL）
- 新发现上游风控（已入库）：数据中心 IP 直连注册的新生号生图 403 account_environment_abnormal（"账号使用环境异常"），经生产 Worker 代理路径正常
- 四批次补丁实施：CSS 全量变量化+深色（data-theme+prefers-color-scheme）+≤680px/360px 竖屏断点；header 重构（画笔+颜料盘 logo、版本号堆叠、齿轮图标、菜单按钮）；hub 合并浮窗（三面板 body 节点搬运复用，无重复 ID）；历史持久化 kmage_hist_v1（成功/失败/中断均入册、缩略图、kdr url、回看三优先级、导出导入去重）；/about ui 字段；关于弹窗新 6 节+403 排障+时间线 1.2/1.3 修正
- 修复 v1.2 harness 遗留问题：mock tinyPng base64 数据损坏（PIL 亦无法解码）导致缩略图 E2E 假阴性，换真实 64x64 PNG 后通过
- E2E（无头浏览器）：375/320px 竖屏无溢出、hub 三选项卡切换与关闭归位、注册→成功（thumb+ms 入册）→失败入册→刷新持久化→running 中断清理→回看→kdr url 记录→导入去重→深色/浅色/跟随系统 media 实时切换，全通过；发现并修复 brand-txt 被 chan-sel 遮挡（flex:none）
- 部署 CF HTTP 200；/healthz 与 /about 返回 1.3；线上与本地逐字节一致（107,256 字符）
- 生产端到端（375×812 竖屏）：kdr 免费 Gift Key 36.8s 出图，历史条目含上游 URL（公网 HTTP 200，1.69MB PNG）与缩略图

Stage Summary:
- kmage-kdr-1.3 已上线 https://ai-image.lishuhang.workers.dev/（135KB）
- 仓库备份 0913-gpt2/gpt2-worker-kmage-v1.3.js + README/CHANGELOG 时间线更新
- 积分消耗：本轮生产验证 kdr 免费 Gift Key（0 kmage 积分）；直连探针注册 3 号（上游风控研究用）

---

## 2026-09-13 14:42 UTC+8 — golden-quote 小修：头衔溢出自适应 + 全量去 emoji（齿轮 SVG 化）+ 嘉宾行内编辑持久化 + 标题改名

### 变更清单（0913-golden-quote/index.html，156+/17-）
1. **头衔溢出修复**：新增 `fitTitleSize()`——`#renderTitle.profile-title` 文本超出 980px 容宽时逐级缩小字号（45px 起、步长 1px、保底 12px），保证头衔单行完整显示；`updateCanvas()` 末尾调用 + `document.fonts.ready` 后二次校准（字体异步加载致宽度变化）。不限制最大字数（用户要求）。
2. **去 emoji + 齿轮 SVG 化**：清除全部 13 处 UI emoji（👥💬✨📸➕🎨🖼️💾⬇️⬆️⚙️⬅️ 等）；设置齿轮改 Material 齿轮 SVG（fill=currentColor），成为全应用唯一保留图标；设置开启时齿轮旋转 180° + title 切换"设置/返回"替代原 ⬅️。海报画布内的头像/二维码占位 SVG 属内容占位符，非 UI 图标，保留。
3. **现有嘉宾行内编辑**：设置→现有嘉宾 中姓名/头衔点击变文本框（focus+全选），失焦即保存；Enter 提交、Esc 取消；空姓名失焦自动回退；头像点击弹系统上传对话框（公用隐藏 file input + DataTransfer 目标绑定）。改动后就地还原 span（不重建整表），规避"编辑后立即点删除被吞点击"的时序坑。
4. **localStorage 即时持久化**：新增 `goldenQuote_guests_v1` 键（guests+currentGuestId），姓名/头衔/头像编辑、新增、删除、JSON 导入均即时写入；启动时优先恢复。配额超限 try/catch 降级 console.warn。
5. **页面标题**：`海报生成器 - Poster Generator Pro` → `金句生成器 - 娱乐资本论`。

### 验证（无头 Chromium 全流程 E2E）
- 静态：emoji 区段扫描（U+2600-27BF/2B00-2BFF/1F000-1FAFF/FE0F）零残留；内嵌 JS node --check 通过
- 功能：长头衔 25 字 45px→34px 单行完整（scrollWidth=clientWidth）；改短头衔自动恢复 45px；姓名/头衔编辑失焦即时入 LS、海报与选择器同步；Esc 取消、空名回退；编辑后紧跟删除正常；头像上传→LS+海报+选择器三处联动；刷新后嘉宾/选中项/头像完整恢复；齿轮开合状态正常
- 视觉：双视图截图确认无 emoji、齿轮 SVG 渲染正常、海报高亮金句正常
- 测试坑记录：刷新后 #viewSettings 处于 display:none，直接 eval 操作其中输入框会因"隐藏元素不可聚焦"产生假阴性，须先点开设置再测（真实用户路径）

### 部署
- 直接替换 index.html 并 push（静态文件，无 CF Worker 变更；Pages/源站随仓库自动生效）

---

## 2026-09-14 07:15 UTC+8 — golden-quote：姓名字体双选（得意黑 / 阿里妈妈东方大楷）+ 占位符引号修复

### 变更清单（0913-golden-quote/）
1. **新增字体文件** `AlimamaDongFangDaKai-Regular.woff2`（2,665,324 bytes，全量单文件）——来源 GitHub 公开镜像（MoviCloud-com/movicloud-app，官方 Version 1.006;beta）。fontTools 验证：family=阿里妈妈东方大楷、cmap 7017 字形、CJK 基本区 6763 汉字与官方描述精确一致、嘉宾姓名/长头衔/标点测试字符全覆盖。iconfont 官方下载需登录、其预览 woff2 仅 304 字节子集、npm cn-fontsource 包为切片字体（几百个小文件）均不符合"单文件最压缩 webfont"要求，故采用镜像全量 woff2（对比 ttf 5.0MB / otf 3.6MB / woff 3.0MB，woff2 最压缩）。
2. **@font-face**：`'Alimama DongFangDaKai'`，沿用现有嵌入模式：`url('./AlimamaDongFangDaKai-Regular.woff2')` + `local('阿里妈妈东方大楷')` fallback，font-display: swap。
3. **切换控件**：主视图 嘉宾选择 组内新增"姓名字体"下拉（得意黑（默认）/ 阿里妈妈东方大楷），仅作用于海报姓名（得意黑唯一使用处）；state.nameFont 入 state，导出/导入 JSON 自然携带。
4. **持久化**：`goldenQuote_nameFont_v1` 独立键，切换即存、启动恢复，配额异常降级 warn。
5. **字号自适应泛化**：fitTitleSize 重构为 fitSingleLine(el, minFs) + fitNameAndTitle()——姓名（保底50px）与头衔（保底12px）统一自适应；东方大楷为全角字形，8字姓名 85px 会超 900px 容宽，实测自动降至 78px 单行完整；document.fonts loadingdone 时二次校准（大楷异步就绪后修正度量）。
6. **顺手修复（上轮回归显性化的原始隐患）**：SVG_AVATAR_PLACEHOLDER 数据 URL 内含双引号，嵌入 src="..." 模板破坏 HTML 属性，无头像嘉宾行显示乱码文本（gq-initial 原始写法即有隐患，上轮加 title 属性后显性化）。改为 SVG 内单引号 + 外层双引号，无头像占位图标恢复正常渲染。

### 验证（无头 Chromium E2E）
- 静态：emoji 零残留、内嵌 JS node --check 通过、12 项改动点全部命中
- 功能：默认得意黑 85px；切大楷即时应用（document.fonts.check 确认真加载）并即时入 LS；刷新后字体偏好+下拉框+海报渲染恢复；8字姓名+大楷自动缩至 78px 单行；切回得意黑恢复 CSS 默认；控制台零报错
- 视觉：双字体海报截图对比（书法颜体质感 vs 斜切黑体），嘉宾行占位图标正常

### 部署
- index.html + 字体文件 + 本日志单次 commit 推送（静态文件，无 CF Worker 变更）

---

## 2026-09-14 08:30 UTC+8 — golden-quote v2.0：设置面板重组 + 嘉宾拖拽管理 + 双引号 logo + PWA 可安装

### 变更清单（0913-golden-quote/）
1. **主题区块重组**：「主题与色调」→「主题」；姓名字体下拉自主视图嘉宾组移入此处；「主色调」→「强调色」；删除底色 color picker，改为「黑底/白底」二选一按钮（与强调色同行不换行）——底色定义为 div.quote-box 色彩：黑底 rgba(0,0,0,.1) 白字（默认）/ 白底 rgba(255,255,255,.1) 黑字 #1A1813，均约 10% alpha；state.theme.quoteDark 入 state（JSON 导出导入携带），主题预设切换重置回黑底；Canvas 预渲染金句（renderQuoteToCanvas）同步用 quoteTextColor，避免导出图与预览不一致。
2. **全局图片配置**：四个 label 去除 (bg.png) 等括号后缀；删除 autoLoadLocalAsset 自动搜索同名文件逻辑（图片实际以 blob 形式封装在 JSON 配置中）。
3. **数据管理区块**：删除「数据管理 (JSON)」标题；两按钮移出 control-group 横排（.data-btn-row）；改名「导出配置（备份）」「导入配置（JSON）」。
4. **双态图标**：设置态齿轮换为向左箭头（icon-back SVG，CSS 按 .is-open 切换显示，替换原 180° 旋转方案）；常规态标题「编辑海报」→「金句生成器」。
5. **常规态精简**：删除「嘉宾选择」「金句内容」标题行与「高光词汇 (输入词语后按空格添加)」label；tagInput placeholder →「插入高光词，空格分隔」；选择器「添加嘉宾」+ 按钮点击改为仅打开设置（原聚焦的 newGuestName 输入框已不存在）。
6. **嘉宾管理重组**：删除「添加新嘉宾」独立表单区块；h4 →「可点击姓名、职位、头像修改，改完自动保存」；列表底部常设灰色示意行（空白头像+姓名+职位灰字+绿色「新增」按钮），点击新增即创建黑色实体行（name=姓名/title=职位 占位可直接点击修改），红色「删除」按钮按需求移除（由绿色「新增」替代其位置概念）；行内编辑「无头衔」占位统一改「无职位」。
7. **嘉宾拖拽排序**：每行头像左侧 4×24px 圆角竖条 handle（cursor:grab，hover 加深）；仅 handle mousedown 时启用 row.draggable（不干扰行内文本编辑）；HTML5 DnD dragover 按目标行上/下半区实时 insertBefore 预览，dragend 按 DOM 顺序写回 state.guests + persistGuests + 主面板选择器同步；灰色示意行不参与拖拽、常驻末尾。
8. **金色双引号 logo**：线条 SVG——左上「66」形左引号（r=4.4，圆头在下尾向右上）+ 右下「99」形右引号（r=2.2，恰为 1/2，圆头在上尾向左下），金色 #F3B64A stroke 2.2 round；同款 inline SVG 置于常规态标题最左（28px）+ data-URI favicon；首版误将左右引号形态画反（99 在左上），已按中文引号「开引号似 66、闭引号似 99」惯例修正。
9. **PWA**：新增 manifest.json（name/short_name/start_url ./、scope ./、display standalone 保留系统标题栏、theme/background #1A1813、icon-192/512 PNG + maskable）；新增 sw.js（golden-quote-v2.0 缓存，precache 9 项资产含 3 字体与 html2canvas CDN，Promise.allSettled 容错，fetch 缓存优先+后台回源刷新）；index.html 注册 SW（file:// 协议静默跳过，http(s) 本地部署/GitHub Pages 均可安装，安装实例指向当前部署地址）；图标 = logo 叠白色圆角矩形底（512 rect rx=110），cairosvg 生成 PNG。
10. **版本 v2.0**：标签页 title「金句生成器 v2.0 - 娱乐资本论」；常规态标题下方小字 v2.0（设置态隐藏）。

### 验证（无头 Chromium E2E）
- 静态：内嵌 JS node --check 通过；colorBgBase/btn-delete-small/newGuest*/autoLoadLocalAsset/「编辑海报」「输入高光词」「无头衔」零残留；emoji 扫描仅注释箭头符（非 UI 图标）
- 功能：title/版本号/logo/favicon/manifest 就位；设置态箭头切换与版本号隐藏；主视图三处标题/label 删除；强调色+底色同行（top 差 0.5px 亚像素）；黑↔白底切换背景/文字/按钮态三同步，预设切换重置黑底；新增两次→2 黑行+灰示意行常驻末尾+LS 持久化；模拟 DragEvent 双向拖拽 DOM/state/选择器三处同步、示意行不参与；行内编辑改名「曹睿」→LS→选择器同步回归通过；姓名字体下拉在设置内切换/持久化/海报应用回归通过；主面板+按钮跳转设置
- PWA：SW 注册成功 scope=localhost:8077/，9 项预缓存资产全部命中；刷新后嘉宾数据恢复
- 视觉：常规态（logo+标题+v2.0+精简表单+黑底金句框）、设置态（箭头+灰色示意行+绿色新增+拖拽竖条）、主题区块（强调色+黑/白底同行）、白底海报（10% alpha 浅框黑字金色高光）四组截图目检通过；控制台零报错

### 部署
- index.html + manifest.json + sw.js + icon-192/512.png + icon-pwa.svg（源）+ 本日志，单次 commit 推送

## 2026-09-14 10:09 UTC+8 — golden-quote 小修：姓名取消加粗（字体本就粗，去除叠加的 font-weight: bold）

### 背景
用户反馈：姓名（得意黑 / 阿里妈妈东方大楷 可切换处）如果加粗了就去掉，用普通字重即可——两款展示字体本身笔画已经很粗，浏览器再叠加 font-weight: bold 会产生「伪加粗」（synthetic bold），过粗发闷。

### 变更清单（0913-golden-quote/index.html，仅 1 行）
1. `.profile-name`（海报姓名元素 #renderName，即字体切换作用对象）删除 `font-weight: bold;` 声明，回归 normal（400）。两款 @font-face 均注册为 weight: normal，DOM 与 html2canvas 导出共用该样式，改此一处即全生效。

### 验证（无头 Chromium）
- 页面打开 computed fontWeight = 400（得意黑默认态）；切换东方大楷后仍 400；切换回默认回归通过；控制台零报错
- 未动其他任何样式/逻辑；版本号保持 v2.0 不变（按要求不 bump）

### 部署
- index.html + 本日志，单次 commit 推送（覆盖式更新）

## 2026-09-14 10:27 UTC+8 — golden-quote v2.1：嘉宾拖拽排序改 Pointer Events（触屏手指 + 鼠标统一），移除 HTML5 DnD

### 背景
用户要求：手指能按住竖条上下拖动调整嘉宾顺序（原 HTML5 DnD 在触屏上完全不触发），鼠标逻辑保持一致；替换后清理旧拖拽代码；版本升至 v2.1。

### 变更清单
1. **拖拽重写（index.html bindGuestDragEvents，35 行 → 30 行）**：HTML5 DnD 全套（mousedown/draggable 开关、dragstart、dragover 半区预览、dragend、dataTransfer）删除，改为单条 `pointerdown` 监听 + Pointer Events：
   - 手柄按下 → `setPointerCapture`（try/catch 容错）→ move/up/cancel 挂 **document 捕获阶段**（其它代码 stopPropagation 也拦不住；拖动中 DOM 挪动导致捕获被释放也不影响跟踪），按 `pointerId` 过滤防多点干扰；
   - `elementFromPoint` 命中行 + 上/下半区 `insertBefore` 实时预览（与原交互一致）；**已在目标位置时跳过挪动**（避免无谓 DOM 变动打断捕获——实测同位置空挪动曾导致后续指针事件改派他处）；灰色示意行排除、常驻末尾；
   - 松手/cancel → 按 DOM 顺序写回 state + persistGuests + 选择器同步（commitGuestOrderFromDOM 原样保留）；
   - 竖条 CSS 已有 `touch-action: none` + `user-select: none`，手指拖动不滚屏、不选字；鼠标仍限左键。
   - 净效果：每行 4 个监听 + 列表 1 个 → 每行 1 个；`draggedRow` 模块级状态、`draggable` 属性开关全部清除。
2. **版本 v2.1**：index.html `<title>` 与常规态 `#appVersion` 小字 → v2.1；sw.js 注释与 `CACHE_NAME` → `golden-quote-v2.1`（强制 PWA 老客户端重新预缓存新 index.html）；manifest.json description → v2.1。

### 踩坑记录（拖拽调试）
- CDP 真实鼠标注入下，同位置 `insertBefore(node, node)` 空挪动 + 后续 move 改派曾造成「拖一下就断」假象；同一页面实例上多次拖拽序列的泄漏监听器互相干扰放大了现象。干净环境（清 LS + 刷新）单手势全流程无问题；捕获阶段挂 document + 跳过空挪动后，污染环境下也稳定。
- 无头环境 `mouse move --steps N` 实际每命令只派发 1 次 pointermove（合并到帧），验证拖拽需用多段 move 命令模拟轨迹。

### 验证（无头 Chromium E2E，干净环境）
- 真实鼠标（受信任事件）：末行两段上移直达顶部 [A,B,C]→[C,A,B]，两次 insertBefore 均正确
- 模拟触屏（pointerType='touch' PointerEvent 序列）：首行拖至底部，顺序精确还原，LS 同步
- 灰色示意行常驻末尾不参与；`.dragging` 无残留；行内编辑（点击改名→blur 保存）回归通过
- 刷新后顺序与改名持久化；主面板选择器顺序同步（曹睿/姓名/姓名/添加嘉宾）
- title「金句生成器 v2.1 - 娱乐资本论」、常规态小字 v2.1、SW 缓存名 golden-quote-v2.1、SW 注册 scope 正常；控制台零报错

### 部署
- index.html + sw.js + manifest.json + 本日志，单次 commit 推送

## 2026-09-14 12:06 UTC+8 — golden-quote v2.2：单文件化（PWA 资产内联 + 字体联网 fallback）+ Logo 改实心 serif 引号

### 背景
用户要求：PWA 散落资产（图标/manifest/sw）收进 html 保持单文件；字体加联网 fallback，最小套装「index.html + html2canvas.min.js」也能用；小分辨率图标可路由到大图；引号 Logo 从空心（像 66/99）改为用 serif 字体的中文引号绘制；输出 v2.2 后删除 icon png/svg、manifest.json、sw.js 等，文件夹仅保留 html2canvas.min.js + 两个字体 + index.html。

### 变更清单
1. **PWA 单文件化（sw.js/manifest.json/icon-192/512.png/icon-pwa.svg 全删）**：
   - manifest 运行时生成：http(s) 环境下用 Canvas 现画 512px 图标（白色圆角矩形底 + 金色 #F3B64A 实心 serif 双引号，左上大“0.94x/基线0.84、右下小”0.5x/基线1.19，与 Logo 同构），toDataURL 为 PNG data URI；manifest JSON（name/short_name/description v2.2/start_url=origin+pathname 指向当前实例/scope=目录/display standalone/背景主题色/icons 192+512+maskable 三项同源）经 encodeURIComponent 注入 `link[rel=manifest]` data URI；file:// 协议静默跳过。
   - 删除 SW 注册代码（无外部缓存清单可维护）。现代 Chromium（121+）无 SW 也可安装；iOS「添加到主屏幕」走截图图标（apple-touch-icon 不支持 data URI，已移除链接）。
2. **字体联网 fallback（@font-face src 链）**：得意黑/东方大楷 = 本地文件 → jsDelivr(gh@main) → raw.githubusercontent(main) → local()；阿里巴巴普惠体（本地 woff 删除）= 本地(兼容旧部署) → jsDelivr/raw **@9e8e894ec97d2df4eb0b0e78a66b6bcc88a2163a 冻结 SHA**（文件删后 URL 永久有效）→ local()。CDN 均实测 200。
3. **html2canvas 本地优先**：`<script src="./html2canvas.min.js">` + `window.html2canvas || document.write(cdnjs 1.4.1)` 兜底（原为纯 CDN，本地文件未参与）。
4. **Logo 重绘（实心 serif 中文引号）**：SVG `<text>` Georgia/'Times New Roman'/serif 加粗实心「“」(30px, x0 y27) 左上 + 「”」(16px, x24 y38) 右下，fill #F3B64A；头部 inline SVG、favicon data URI 同一坐标体系；PWA 图标 canvas 同构。彻底摆脱空心圆圈"66/99"观感。
5. **版本 v2.2**：title、#appVersion、运行时 manifest description 同步。
6. **文件删除**：icon-192.png、icon-512.png、icon-pwa.svg、manifest.json、sw.js、logo.png、poster_settings-260913.json、AlibabaPuHuiTi-3-55-Regular.woff（git rm，历史可恢复）；文件夹仅剩 index.html + html2canvas.min.js + SmileySans-Oblique.ttf.woff2 + AlimamaDongFangDaKai-Regular.woff2。

### 验证（无头 Chromium E2E）
- 完整文件夹：title/小字 v2.2；html2canvas=本地加载；manifest data URI 注入且 start_url/scope 指向当前实例；图标 PNG 512×512 解码成功（导出目检：白圆角底金引号，形态正确）；三字体 check=true（普惠体实为 CDN 兜底加载，证明 fallback 生效）；头部 logo 放大目检为实心 serif 引号
- 最小套装（临时目录仅 index.html，:8078）：html2canvas 从 cdnjs 加载、得意黑/东方大楷从 jsDelivr@main、普惠体从冻结 SHA 加载全部成功；海报截图姓名得意黑/头衔普惠体渲染正常；控制台零 JS 错误
- 回归：触屏拖拽重排、行内编辑改名均通过

---
Task ID: 7
Agent: Super Z (main)
Task: golden-quote 嘉宾管理小修（不升版本）：恢复红色删除按钮 + 文案更新 + 导入JSON定义驱动 + alert改toast

Work Log:
- 从 git 历史(59e82ed)找回原删除按钮实现：.btn-delete-small #ff4d4f + confirm 确认，按原样恢复到每行嘉宾行末
- removeGuest：确认后删除；删当前展示嘉宾自动切第一个可用；persistGuests+双列表刷新
- 文案改「拖动排序，可点击姓名、职位、头像修改，自动保存」
- 导入逻辑重写：JSON 定义哪项就覆盖哪项（guests/nameFont/highlights 合法性校验后整体覆盖，theme/images 字段级合并）；未定义/非法项不覆盖自然回退浏览器存储；定义了的项同步写回 localStorage（刷新后一致）；选中嘉宾无效回落首个
- alert 全部改右下角 toast（.toast-tip fixed right20/bottom24，成功深色/失败红色，2.6s 自动消失）
- E2E：删按钮渲染+删除流程+当前嘉宾切换；完整 JSON 导入全字段按文件生效+刷新持久化；部分 JSON fallback 本地存储；无效 JSON/非法 guests 防御不崩；拖拽回归（真实鼠标轨迹，注意 2 人时行高 62px 需拖过中线 y<193）；控制台零错误；截图目检
- 版本号未动（保持 v2.2），单次 commit push

Stage Summary:
- bb8f7d9 已推送；嘉宾管理回到「新增+删除+拖拽+行内编辑」完整形态；导入语义改为文件优先、存储兜底

## 2026-09-23 12:00-13:30 UTC+8 — 0923 教程离线抓取收尾：小云雀补齐 / TapNow 45页 / flova 7页 / 纳逗Pro PDF / AniShort 全课程 / 断链修复归零

### 背景
接续 0923-drama-agent-tutorials 交接任务（TODO.md）。本轮会话脚本目录 `/home/z/my-project/scripts/` 已丢失，全部抓取库按交接描述重建（web_scrape_lib.py：MediaPool 断点续传+pre_urls+魔数嗅探、Next.js 图片代理解码、markdownify 兼容签名；run_web_scrape.py 三站配置；另建 nadou_pdf.py、anishort_meta2.js、anishort_singles.js、anishort_download.py、anishort_mds.js 等）。

### 完成清单
1. **小云雀 11/11**：补 `短剧重制转绘使用手册`（13 媒体，断点续用既有 8 项）+ `小云雀短剧 Agent 智能预演体验指南`（5 图）。关键修复：prepare_article 只洗 DOM 不下载的 bug，新增 localize_dom（下载+改链一体）。
2. **TapNow 45/45**：h1 作标题（og:title 是站点名）；修复 join_base 对 `/` 根相对路径误拼到文档路径下的 bug（gitbook-assets 图片因此从 404 变 200）；发票页 1 张 larksuite asynccode 图源站 400（需登录），md 用占位符注明。
3. **flova 7/7**：无扩展名 CDN 视频按魔数嗅探为 .mp4；quick-guide 5 段 + in-depth 4 段全部本地化。
4. **纳逗Pro 官方 PDF**：按钮为浏览器端实时生成，Playwright expect_download 捕获 → `纳逗Pro 使用手册.pdf`（1.9MB，文件名中的零宽字符已清理）。
5. **AniShort 11/11 课程**：
   - 结构判定：3 多集课程（77 全流程 6 集 / 119 3D导演台 14 集 / 104 全环节 11 集）+ 8 单集课程（速转整部剧 43:17 / 3D世界新玩法 27:51 等）。判定依据：面包屑 nav 含 `.text-cyan-400` 集名标记；部分课程页 16 行侧栏实为「全目录推荐位」，点击即跳转其它课程（URL 变化已实测）。
   - 视频捕获：监听 `bdbcdn.../propertyvideo/*.mp4` 响应 + 等 video.src 变化，修复「点击后取到旧 src」竞态。
   - 159 集去重 = 48 唯一视频，HEAD 测得合计 5.53GB。**受 GitHub 100MB 单文件硬限制**：29 个 ≤99MB（约 1.07G）入共享池 `_anishort_videos/`（文件名=CDN UUID 原名，sources.json 清单）；17 个大视频在 md 保留在线链接并注明原因（磁盘 2× 成本 + 100MB 限制双约束）。
6. **历史断链修复**：小云雀/纳逗Pro 旧 md 的 1958 个裸 `](image_N.png)` → `](_files_<文档名>/image_N.png)`；228 个 `/xxx` 站根相对链接改完整 URL；TapNow 文内 `.md` 相对链接映射在线页。**全仓 md 相对链接 0 断链**（2366 个可解析）。

### Git 手术记录（磁盘危机处理，值得留档）
- 沙箱盘 9.9G，AniShort 阶段仅剩 ~2.5G；媒体入库成本≈2×（工作树+pack）。
- 尝试 `git repack -a -d --filter=blob:none` 释放旧 pack：需要临时双倍空间 → 磁盘 100% 满，删除 tmp_pack 恢复。
- 改用「blobless 浅克隆 + no-checkout + 工作树 mv 搬迁 + reset --mixed」换血 .git（3.2G→596K），腾出 ~3.2G。
- 换血后 porcelain `git commit` 的 diff-stat 触发旧 blob 懒加载回填 → 二次撑爆磁盘 + index 缓存树被杀进程污染。清理后改纯 plumbing（write-tree/commit-tree/update-ref），但 write-tree 仍逐个索要全部索引 blob（无 stat 缓存时 git 逐项存在性检查触发 promisor 拉取）。
- 终解：`git fetch --no-filter origin main` 全量回填 3.3G blob（删除 pack + 清空 refs 强制重协商，`--no-filter` 是关键，config 里 unset partialclonefilter 不生效）→ plumbing 提交 4f3627c → push 成功。

### 安全与收尾
- token 仅在 `.git/config` remote url；本轮所有日志/文档未含 token。
- `/home/z/my-project/.secrets/feishu_cookies.txt`：本轮会话中该路径已不存在（cookie 早前已销毁），无需再删，记录在案。
- TODO.md 已改写为「完成总账」：11 平台全部 ✅，验收清单全勾。

Stage Summary:
- origin/main = 4f3627c：AniShort 11 课程 md + 1.07G 共享媒体池已上库
- 11 平台教程全部离线可读；全仓 0 断链；保留在线的 17 个大视频均有注明

### 2026-10-13 — cruise-bot v1.0（新项目：邮轮五日文字内容 Bot）
- **背景**：夫人邮轮 5 天，不购互联网套餐时仅 WhatsApp/iMessage 可收发文字；要求交钥匙 bot 方案（CF Worker + GitHub Actions + GLM-4-Flash 免费 + 全零费用），做到"需要凭据为止"
- **目录**：`cruise-bot/`（worker.js 886 行 + wrangler.toml + actions/ 4 脚本 + mac-bluebubbles/ + win365-wxauto/ + README 交钥匙文档）+ 仓库根 `.github/workflows/cruise-bot.yml`
- **三通道**：主=WhatsApp Cloud API（service 对话 24h 窗口内免费，webhook 签名校验）；备=iMessage（她 Mac BlueBubbles + CF Tunnel，同 Apple ID 自发闭环，无窗口主动推送，🤖 前缀防自环）；Phase 2=Windows 365 wxauto 微信桥（复用 /send 与 KV outbox）
- **内容服务**：早报/晚安包（Actions cron→GLM 汇总 RSS+open-meteo）、搜（Bing RSS→DDG Lite fallback）、小红书特化（尽力抓+诚实降级）、链接摘要/全文分节、wiki、天气、热榜、古腾堡公版书分章、连载小说、猜谜、翻译、聊天兜底、广播/回老公、时区/订阅开关、KV 待发队列补发
- **安全**：白名单外拒答、HMAC-SHA256 webhook 验签、AGENT_KEY 内部 API、凭据全走 secrets（扫描 0 命中）
- **验证**：node --check（ESM）+ py_compile + bash -n 全通过；凭据扫描 0 命中
- **待办（需用户提供）**：Meta App/WABA/永久 token/能收码的 bot 号码、GLM key、部署 Worker+secrets、配 webhook、Actions secrets、（可选）她 Mac 装 BlueBubbles、邮轮时区校准 cron

### 2026-10-16 上午11点50，人工手动调整了一些文件夹的配置，接手工作在这个时间点之后的请以实际探测到的repo目录结构为准。

---
Task ID: feng-video-materials
Agent: Super Z (main)
Task: 1020-feng-video 素材爬取（B站视频/海报/韩红片段）+ 爬取指南

Work Log:
- 复盘上轮：文案/SRT/重录音/韩红音频已就绪，素材未动；YouTube(yt-dlp)因验证码死路
- 调研skill市场：dsh-plugin.org(DeepSeek Harness专用)、skills.pub(无视频下载类)、lobehub(无) → 无现成skill，自建管线
- B站API直连412（数据中心IP风控），snapany首次解析后登录墙
- 攻克极验点选验证码：geetest图布局逆向(344x384，底部左侧为目标字符条) + Canny多尺度多旋转模板匹配 + 满N次自动提交 → geetest_beat2.py（脚本含完整注释）
- 打通下载管线：agent-browser导航(验证码自动求解) → 页面__playinfo__取DASH → curl带cookie下载 → ffmpeg合并
- 搜索22个源视频(搜索API同源fetch可行)，批量下载；1/3文件CDN坏包(NAL错误)，全量解码体检后重下修复
- contact sheet + VLM批量审看22个视频内容与可用段 → trim_materials.py按留余量规范剪出41个片段(100MB)
- 海报：image-search老片命中率7/11错误 → 改用B站官方封面(search API pic字段)+预告抽帧，14张入库
- 韩红视频从filekit完整版剪3:03+余量67s，音画分离(hanhong_seg_video + hanhong_seg_audio.wav 50s)
- raw_dl原始档(240MB)验证后删除；写爬取指南readme-get-video-materials-1020-1721.md与素材清单materials-list.md

Stage Summary:
- materials/：41视频片段(100MB)+14海报+韩红音画2件+指南2篇，全部对应SRT分段可查清单
- 验证码求解器、B站下载管线、审看/剪辑脚本全部持久化在scripts/可复用
- 关键经验：B站一切走真实浏览器上下文；验证码点击后等8秒再判定；CDN坏包重下即愈

---
Task ID: feng-video-edit
Agent: Super Z (main)
Task: 1020-feng-video 剪辑：配音修正+成品mp4+剪映工程

Work Log:
- 3句重录TTS替换：滑窗ASR定位主配音错读位置(46.5%读成"四十六百分之五"等)，能量极小值扫描定精切点，5ms交叉淡化拼接 -> voice_fixed.wav(174.0s)，ASR复验三处均干净
- SRT时间轴校准：silencedetect全量静音图 vs SRT边界对照(误差≤0.5s)，修正段3实际起点37.91s(原文档40.55)
- 韩红开场定位：视频自带字幕VLM读帧(非ASR，避开限流)，金句"走个面"锁定182.7-188.9s，预切开场片段
- 分镜总装：38镜头数据驱动(EDITS)，1080x1920竖屏硬切，电影片段4:3中心裁切+图表1:1居中+黑底，109条docx行级字幕(思源黑体白字黑边)烧录
- 成品：抓特务口碑反转_成品_v1.mp4(180.7s/21MB)，VLM抽帧验收5个时间点全部正常(画面/字幕/内容对应)
- 剪映工程：draft_content.json+meta(视频38段/音频2轨/文本109条，微秒时间轴，assets文件夹38文件76MB自包含)，README含导入与重链说明；JSON引用与时间轴连续性校验通过

Stage Summary:
- output/：成品mp4 + 剪映工程(自包含assets可一次性重链) + 字幕srt + 分镜json + 修正配音wav，共112MB
- 全流程脚本持久化：splice_voice.py / assemble_video.py / make_jianying.py
- 剪映工程schema为6.x兼容尽力而为版，导入若有兼容问题以成品mp4为准，素材与时间轴数据齐全可快速重建

---
Task ID: 1103-agent-downloader-research
Agent: Super Z (main)
Task: 8平台视频下载（YouTube/Instagram/X/Threads/微博/抖音/小红书/B站）可行性调研轮——只调研不实抓，摸清通路/环境/坑并建立持续性工作协议

Work Log:
- 环境探针：Debian13/2C4G，ffmpeg 7.1.5 + playwright+chromium 预装，出口=香港阿里云(8.212.10.159)，16/16关键域名网络层全通（YouTube/IG/X/Threads 无墙，微博/抖音/小红书/B站不拒境外）——难点只剩平台反爬，不是网络
- 工具落地：yt-dlp 2026.10.26 + gallery-dl 1.32.19 装入 /home/z/.venv；extractor 覆盖实测：yt-dlp 有 YouTube21/Weibo3/XiaoHongShu1/BiliBili19/Douyin1(已知失效)/Threads0；gallery-dl 有 instagram72/twitter61/weibo32/bilibili11，无 threads.net、无 douyin/xhs
- 方案调研：zyipeng/video-downloader platform-notes 全文精读（抖音走 iesdouyin 分享页 SSR 免登录免签名可拿4K原片 ratio=default、小红书必须 App 分享链接的 xsec_token、B站720p+要登录态）；TikTokDownloader 认证体系深读（a_bogus=SM3+RC4、msToken 900s自动刷新）；yt-dlp 数据中心IP triage（bot check 三层解法：player_client变体→bgutil POT provider→burner cookies，重试无效）；Threads 唯一活跃解=tribixbite/yt-dlp-threads 插件（Googlebot UA 拿 SSR 全量 post 绕登录墙）
- 仓库核查：TikTokDownloader★17.3k(当日更新)/XHS-Downloader★13.2k/MediaCrawler★70k/instaloader★13.8k 活跃；BBDown、BiliTools、bilibili-API-collect、junhoyeo/threads-api 已归档勿选；ReaJason/xhs 16个月停更
- 血泪传承：发现上轮 geetest_beat2.py 等8个脚本未推库、已随沙盒回收丢失——本轮所有脚本/日志即时入库根治；上轮B站12条踩坑（412风控/验证码延迟8s/CDN坏包1/3重下即愈等）全部并入坑清单
- 持续性协议：state.json 单一事实源 + worklog verbatim 摘录（防概括失真）+ logs/ 全文证据 + 每任务即 commit+push（防沙盒回收）+ RESUME.md 三分钟恢复协议（防上下文崩溃）+ 防token狂烧守则（脚本化/压缩输出/失败先查原始log禁止盲试）

Stage Summary:
- 产物全部在 1103-agent-downloader/：README/RESUME/state.json/todo/worklog + findings×5（环境实测/8平台可行性矩阵/分平台笔记含来源/27条坑清单/持续性协议规范）+ tools×5探针脚本 + logs×5原始输出
- 结论：8平台中7个有活跃现成通路——微博最易（yt-dlp游客4K）、抖音最难但分享页旁路免签名、Threads 靠插件；Instagram 需 sessionid cookie、小红书需带 xsec_token 的 App 分享链接（均已列入 state.json blocked_on 待用户补给）
- 下轮执行：todo.md Phase 0（装 threads 插件/选定测试URL/建 cookie 目录）→ Phase 1 按风险从低到高实抓（微博→B站→YouTube→X→Threads→小红书→Instagram→抖音，每平台先 --dump-json 验元数据再实下）


Agent: Super Z (main)
Task: 8平台视频下载实抓轮（除Instagram外7平台各1条高清视频+元信息→GitHub; 用户规则: 失败最多换法重试1次）

Work Log:
- 成绩 5/7：微博540x960/B站1280x536(免登录html5 playurl 720p档,修正调研"仅480p"结论)/X 1920x1080(SpaceX官方推文,游客免cookie)/Threads 720x1280(原创方法:Googlebot UA抓threads.com主页SSR抽帖子code→插件--simulate验证带视频→下载)/小红书720x1364(用户xsec_token链+yt-dlp匿名档)
- 微波级发现：微博"列时间线"已被访客墙挡(m.weibo.cn容器API ok=-100 + yt-dlp WeiboUser重定向passport访客流程),但"单视频提取"畅通——搜索引擎转引拿具体URL即可绕过
- YouTube❌：ytsearch发现正常,但ios,web_safari与web,android_vr,tv_downgraded两client组合均死于同一IP级bot-check("Sign in to confirm you're not a bot"),与上轮调研B1预判一致;未探索:bgutil POT provider(node版)/burner cookies
- 抖音❌：iesdouyin分享页SSR对匿名已只回壳数据(loaderData仅页面元信息,aweme_id出现0次,三目标交叉验证排除"目标已删"),yt-dlp报"Fresh cookies needed"如B13预判;未探索:ttwid注入/TikTokDownloader扫码/playwright
- 全部脚本化入库(tools/dl_*.py + lib_media.py + gh_sync.sh增量推送×7次commit),ffprobe体检5/5通过,过程留痕worklog W009-W021+logs/
- 交付物：REPORT.md(元信息总表+忠实问题记录+未探索路径表+自行检索策略三档矩阵) + skills/video-downloader(固化)

Stage Summary:
- 平台难度重排序(实测定论)：X<B站<Threads<小红书<微博<YouTube(数据中心IP)<抖音(结构性收紧)
- "自行搜索"结论：B站热门API/YouTube ytsearch/Threads主页SSR可沙盒内自发现;X/微博靠搜索引擎转引;抖音转引收录差需热榜站或用户给链;小红书必须用户给App分享链接——详见REPORT §5
- 下一步若续做：YouTube装bgutil POT、抖音ttwid注入是各自失败的对症解,预算各约半小时
- 工作目录: 1103-agent-downloader/ (REPORT.md 为总入口)

---
Task ID: 1105-canvas-test-videos-bootstrap
Agent: GLM (main)
Task: AI视频画布横评三篇文章→B站竖屏解说视频三部曲 · 前期调研轮（网盘全量盘点+时间线复原+素材地图+分镜表+skill固化）

Work Log:
- 通路验证：用户提供网盘token（quota OK：账号娱乐资本论，6.1T盘）；GitHub token 261023-glm（admin权限，repo 6.8GB，blobless浅克隆+sparse检出1105-canvas-test-videos，token不落盘）
- 全量遍历：递归脚本（BFS+分页+0.35s限速+崩溃续跑）扫 /202610-AI视频画布横评 = 260目录/3368文件/7.3GB，261次API零错误；server_mtime全是11-05同步时间，真实时间线靠文件名mmdd-hhmm（47个时间戳节点）
- 关键文件拉取（batch_download.py，fs_id直连省list调用）：文案终稿1104-1800（三集全）、前期调研skill×3（1102-1626文案改编指南/1104-1800 Gemini防踩坑70KB/SKILL-video-downloader-1104-1026）、成品稿件×3、V1配音740.4s、BGM 143.8s、浮水印PNG、信息图HTML 27张（价格6/功能B版10/实测11）+source-data.csv×3
- 通读核心文档，时间线复原：0910功能对照表启动→0923十一平台教程离线库→0927-1027三篇文章生产（价格v5.3→v5.7→1007定稿；功能v5→v15定稿1015+信息图A/B；实测1016参考图V1→1022 V2修正→1027定稿+信息图1026-28）→1102-1104视频化调研（文案改编skill/8平台下载skill/防踩坑指南）→1105工作夹+V1配音，详见 01-findings/timeline.md
- 发现关键事实矛盾备忘：充值总额4556(文案V1) vs 4856(实测篇文章)——已写入timeline.md待事实门禁统一口径
- 产出：01-findings/{timeline,assets-map,netdisk-inventory}.md + scripts/{traverse_netdisk,batch_download,analyze_tree}.py + 02-storyboards/（三集分镜表）+ 03-skill/（解说视频一站式skill）

Stage Summary:
- 前期调研闭环：网盘只读通路/时间线/素材地图/文案/配音/信息图资产全部就位并入库备份
- 分镜表（02-storyboards/storyboard-trilogy.md）：三集×9:16竖屏/4:3安全框/框外字幕条，按小Lin说70%+差评/晚点30%风格，素材分【盘】【canvas】【外】三类标注——待用户批准后投产
- 投产管线（依据Gemini防踩坑指南改造）：事实核查门禁(facts_ledger)→分镜JSON→TTS分句对齐(V1用既有配音+ASR重对齐)→信息图HTML改造为canvas动效→受控时钟截帧→ffmpeg混音组装→LUFS/坏帧/水印合规质检

---
Task ID: 1105-canvas-test-videos-bootstrap（续）
Agent: GLM (main)
Task: 分镜表定稿 + 解说视频skill固化（explainer-video-studio v1.0）

Work Log:
- 分镜表生成器：台词按段/句切片直接取自文案终稿（零抄写误差），字数权重分配时间码；V1 用真实配音 740.36s 反推语速 5.02字/秒 → V1 43镜/12:20（与配音精确吻合）/V2 39镜/11:19/V3 51镜/13:55；覆盖率校验三集均为 0 未覆盖句（台词100%进分镜）
- 外部素材锚点已核：牌子=DiDi_OK B站2100万播放/郭帆点赞/23天100万；丧尸清道夫=Mx-Shell云南玉溪中专学历婚礼摄影师/10天3000元/全网破亿（B站搜BV可下）；TTS服务 tts.lishuhang.com 可达(200)
- skill 固化（skills/explainer-video-studio/ → 03-skill/ + download/explainer-video-studio.zip 187KB/29文件）：SKILL.md（一句话用法+起点决策表+十步状态机+12条铁律）+ references×5（风格配方/画面规格/管线踩坑/事实门禁/合作skill）+ scripts×7（env_check/tts_align/h5_render/ffmpeg_master/make_storyboard/netdisk/batch_download，全部py_compile通过）+ assets（vertical_master.html 母版实测渲染验收 PASS：yzCheck compliant、分区像素校验6/6、动效帧差异712点；ffmpeg合成音效×6）+ examples（timeline-ep1.json）
- 推荐 Prompt 用法说明按用户要求另附于 skill 外（download/解说视频skill_推荐Prompt用法.md）

Stage Summary:
- 交付物：三集分镜表（待批准）+ 解说视频一站式skill（可复用于任意主题）+ 推荐Prompt说明
- 分镜表批准后即可按 skill 十步状态机投产：V1 优先（配音已就绪），素材全部网盘在位

---
Task ID: 1105-ep1-price-final
Agent: Super Z (main)
Task: 第一篇「价格篇」正式剪辑成片（十步状态机 Step 5-9：截帧→总装→质检→交付）

Work Log:
- 现场恢复：浅克隆 clock 仓 + 网盘拉取 V1配音(740.36s, 44.1k单声道)/BGM(143.76s, 48k立体声)；canvas 43镜/分镜JSON/字幕JSON(385条≤14字无间隙)/素材全部在位
- 抽检：S01/S05/S10/S20/S30/S43 六镜入场+停留12格 VLM 审看全OK（无乱码/无溢出/素材齐全/构图安全框内）
- 截帧：h5_render.py v2 全量 43镜 2578帧（HUD隐藏，1fps网格+入场窗+dense窗，163MB）；后台进程曾被沙箱静默回收（nohup/setsid均~80s被杀），改前台幂等续跑完成
- 总装脚本 v2（ffmpeg_master_v2.py + 分段版 _seg.py）：白字黑边ASS字幕(普惠体68px Outline=7 单行 WrapStyle=2) + sendcmd驱动drawbox动画进度条(#e55b46 0.5s步进) + 全屏wm75.png水印顶层 + BGM闪避修正版(sidechaincompress双输入+aformat统一48k立体声) + loudnorm两遍I=-15
- 关键坑：crop/drawbox的w表达式仅初始化求值不支持t→sendcmd方案；drawbox@命名实例sendcmd不识别；sidechaincompress采样率声道不一致直接失败；多输入PNG索引错位（预览3输入vs渲染5输入）致首次全渲失败，参数化索引后过
- 成片：分段编码(0-370/370-740.36s，段B字幕cmds偏移-370s)→concat→一次性音频→混流→1080×1920×30fps 12:20.36 37MB，faststart，comment清空
- 质检：G1零坏帧/G2时长±0.04s/G3分辨率/G4响度-15.3LUFS/G5无长黑屏/G6无Remotion元数据 → BUILD_SUCCESS；strings二进制级复查0痕迹
- 双重目检：VLM 6抽帧(5/100/369/400/600/735s)字幕对位精确/水印全屏/画面无缺陷/370s拼接缝无异常；像素级测进度条6帧全部命中(7/145/539/583/875/1072px，偏差≤1px)；音频4采样点-16.9~-20.2dB健康

Stage Summary:
- 交付：成片mp4(37MB)+字幕srt(385条)已入 download/ 与 04-ep1-production/output/；帧目录163MB不入库（h5_render幂等可再生成）
- 脚本沉淀：ffmpeg_master_v2(_seg).py/spot_check.py 入库并同步 explainer-video-studio skill；production-notes.md 记录5条新坑
- 第二/三篇待用户指令后按同管线投产（canvas需按同规格重制）

---
Task ID: 1105-ep1-price-v3
Agent: Super Z (main)
Task: 第一篇「价格篇」v3 修复重制（用户三反馈：音画不同步/黑底/B站真实素材 + skill v2.0）

Work Log:
- 用户反馈归因三连坑实测确认：①字数权重估算全片漂移±27s(句3估算27.33s vs 实测开口29.38s) ②concat demuxer PNG时长量化1/25s网格每镜+0.02s累积0.9s ③h5_render v1只截1.5s窗致42/43页data-t>1.5s元素丢失(v2生产用的渲染器未入库已丢失,重建为v3)
- 实测对齐：本地faster-whisper base(hf-mirror手动下模型,PyAV冲突用f32le raw+numpy绕开,740s全片42s转写) + silencedetect(-38dB/0.22s)双校准 + SequenceMatcher脚本文本↔whisper字符流对齐 + 静音边界吸附 → 76句实测时间码(句首≤0.3s)；z-ai asr限流(13次/周期)弃用
- 帧数精确架构：n_i=round(dur×30)逐镜编码(符号链接序列物化22211帧,按max t'≤k/30映射) + concat -c copy timescale 30000 + 终渲A/B用-frames:v(修-t边界丢3帧) → vtrack/vfinal 22211帧精确命中；幂等检查加getsize>1MB(0字节残骸坑)
- B站素材通路(412时代)：pagelist拿cid→playurl html5游客720p→curl -C -断点续传(牌子81MB/丧尸30.2MB,ffprobe体检465s/214s全量)；m.bilibili.com移动页免验证码截播放量条(2152.1万/424万)；player.bilibili.com外链播放器DOM截点赞(150.1万/37.7万)；郭帆评论游客不可达→腾讯新闻段落截图留证；真浏览器桌面视频页=GeeTest验证码墙勿碰
- 黑底换肤43页：dark_convert.py(CSS变量上下文替换+background:var(--ink)深底白字块反转为浅色芯片+渐变逐一映射+rgba阴影转换)；logo修复(白底键出d<8→alpha0+裁切居中，纯黑libtv反转，暗色xiaoyunque反色副本，暗字形HSV提亮保色相)；S17数值加阴影+轨道描边；S11十格logo全可见
- S02/S03/S14/S23重做：透明叠层页(TRANSPARENT_SHOTS,scrim82%)+ffmpeg双层合成(bg_seg 1080x1920精确帧数+overlay PNG序列)；新闻蓝横幅按颜色行扫裁切(B-max(R,G)>15)；Higgsfield $129红框像素行扫定位23.2-28.2%烘进图片双图叠放淡入；S23 yzCheck溢出修复(img max-height 920)
- 字幕v3：365卡jieba词边界分卡(AI逆袭不再断词)+whisper词锚定卡内时间
- 质检：G1-G7全PASS(帧数精确/时长/分辨率/响度-15/无黑屏/无元数据)；VLM抽帧：t=29.4s字幕「这些案例很容易给人一种错觉」与句3实测开口29.38s精确对位(用户投诉点闭环)、370s A/B边界字幕连续无花屏、S02/S03视频叠底+证据卡合成自然、片尾三联卡正常
- skill v2.0：SKILL.md 17条铁律(+实测对齐/帧数精确/全动效覆盖/B站素材铁律/黑底规范)；layout-spec §二b黑底映射表；yz-infographic暗色例外措辞(黑底白字不违反规范,橙高亮黑底直用)；pipeline §7 v3新坑(5节)；scripts +6(v3渲染器/总装/对齐/字幕/换肤/B站下载),v1渲染器标记DEPRECATED

Stage Summary:
- 交付：成片v3(43MB,22211帧精确)+字幕v3.srt+qc报告 → download/ 与 04-ep1-production/output/
- 音画同步：三连坑全修,句首实测误差≤0.3s,帧级零漂移
- 视觉：全片黑底暗色系,品牌橙保留,B站证据链完整(原片叠底+网页截图裁切)
- skill v2.0 已同步本地与GitHub；第二/三篇按v3管线(黑底规格+whisper对齐+帧数精确)待用户指令投产

---

## Task: ep1 v4 验收反馈修复轮（续 63c8d63）
Agent: Z.ai (GLM)
Task: 按 2026-11-06 用户验收反馈重制价格篇：通用规则固化 skill v1.1 + 本视频特定修复 + 1.1x 提速

Work Log:
- 工作区崩溃恢复：稀疏克隆 clock/1105-canvas-test-videos 复原 43 镜 canvas/分镜数据/素材/skill v2.0；网盘重拉配音/BGM/水印/新增素材（抽卡延时 323MB、anishort t2 第一抽、AniShort智能连线.png、纳逗Pro画布总览.png）
- 通用规则落地（43 页全局）：
  - 间隔号 137 处清零（确定性映射：短语→逗号/顿号、来源行→换行、《画布横评·价格篇》→《画布横评》价格篇）
  - 括注思考剥离（（视频页截图）（取证截图）等 6 处；口径实证行删除）
  - 最小信息（B站播放量（重制版·视频页截图）→B站播放量；10家平台·三集连载·第一集 价格篇→① 价格篇）
  - 字幕位：ASS MarginV 84→180（底缘 y=1740=4:3 安全框下缘外 1 出血位）；hud 预览带 1650/90
  - 定格≤3s：Stage B 脚本对 36 镜入场时间线性拉伸（t≤0.3 钉住）+ class 级环境动效注入（float/pulse，ph0 错相）+ 证据截图 kb 缓推；新增引擎原语 float/pulse/typing + data-ambient 机制（43 页引擎块统一替换）
  - 动效统一：环境动效全片一套参数（float amp4-8/sp≤0.32、pulse amp.005-.012/sp≤0.45，2fps 网格适配红线）
  - logo 补齐 13 处：S20 TapNow/S23 Higgsfield/S25 万兴/S27 巨日禄/S30 TapNow/S32 万兴/S34 第6卡+巨日禄/S36 四卡+TapNow/S37 三卡/S39 十卡内联（pyl 212px flex 行+图标圈 50px 修溢出）/S40 巨日禄/S41 OiiOii+Flova 退款行新增
- 分镜分拆（B-roll 前景展示模式）：S02→S02a(2.8s《牌子》纯净前景)+S02b(8.48s scrim 0.6s 淡入+证据卡按台词重排 0.8/2.6/4.3/5.9s)；S03→S03a(2.8s)+S03b(9.77s)；S24→S24a(21.0s 参数 chips+16 卡牌 6.2-18.6s 逐张)+S24b(11.02s 抽卡延时 85-96s 段背景+10倍速标+问题胶囊)
- S04 重做为视频背景镜（anishort t2 金钟木偶段 offset 3.2s，scrim 0.55）；S07 重做（typing 打字 4.3-7.5s+纳逗Pro画布总览 kb+四平台 logo 按读音 14.8-17.5s）；S11 logo 墙按读音逐个弹出（11.68-24.73s 字符占比定位）；S35 重排为 1年/2年/3年 语序三列 logo 墙（min-height 640 等高）
- shots_v4：46 镜（43-3+6），Σ帧 22211 不变；h5_render_v4：解析 data-t/data-counter 自动入场窗（±0.45s@15fps/counter@12fps）+2fps 网格+DENSE，46 镜 yzCheck 全过
- assemble_v4：BG_V4 六源带偏移（坑：v3 bg 素材是预裁剪段，-ss 36 越界产 317 字节空文件→偏移改相对 0/2.8）；speed 段 setpts=PTS/1.1+atempo=1.1+fps=30+frames:v 20192 精确；srt 365 卡 ÷1.1 重定时
- 重大坑：新建透明页（S02a/S03a/S04/S24b）沿用 S01 母版 body#131110 不透明 → 灰 17 平帧盖死影片；修复 body/#bg-layer→transparent（v3 老页本就如此）
- QC：G1-G7 全 PASS（20192 帧精确/673.07s/1080×1920/-15LUFS/无黑屏/无元数据）；VLM 抽帧：S02a 街头实拍清晰、S07 对比+logo、S24b 录屏+10倍速标、片尾三联卡、字幕位于 90.6% 高度（1740px 规范位）

Stage Summary:
- 交付：成片 v4（71MB，673.07s=11:13，1.1x 提速不变调）+ 字幕 v4.srt + skill v1.1 包（explainer-video-studio-v1.1.zip，版本线统一 1.x）
- skill v1.1：铁律扩至 24 条（+禁间隔号/思考不入画/最小信息/定格≤3s/举一反三/动效统一/品牌实体用logo）；layout-spec 增 §四b 环境动效原语/§六 B-roll 模式/§七 分拆与提速；pipeline 增 §8 六节新坑；scripts +h5_render_v4/assemble_v4；本地 skills/ 已同步
- 本视频特定 vs 通用规则分类表见 04-ep1-production/production-notes.md

---

## Task: ep1 v5 修复轮（会话恢复后）

- **Agent**: Z.ai (GLM)
- **Task**: 价格篇 v5：4:3 横屏安全框全镜整改 + 抽象镜头动画化（推箱子/盖章/阶梯）+ 字幕位 Y1435~1545 + 普惠体修复 + 横屏 4:3 双版本 + skill v1.2
- **Work Log**:
  1. 崩溃恢复：sparse clone clock 仓库（1105-canvas-test-videos + skills）；网盘重拉配音/BGM/t2第一抽/抽卡延时（323MB 用 10 段并行 Range 下载 scripts/para_dl.py，~90s）
  2. 安全框正解推导：用户字幕实测位（Y1435~1545"4:3 区域外底部黑边"）反推 4:3=横屏 1080×810（Y555~1365），旧竖框（240~1680）作废；46 镜模板层批量替换 + 字号体系重排（.tt 64→48 等）
  3. 布局审计：Playwright 快进镜末量元素 rect，初轮 20 镜溢出→逐镜压缩（证据卡/表格/条形图/网格全改紧凑）→46/46 零溢出
  4. S08 重做推箱子（TRAVEL=450 顶墙不过墙，VLM 复核）；S09 重做十平台盖章（rotate wrapper 防 stamp 覆盖）；S29 错位阶梯+亮度递减；S03b 删「全网传播」；S07 logo 56→84；S10/S15 删复述胶囊
  5. 字幕根因修复：libass fontsdir 匹配失败（A/B/C 像素 diff 实验定位）→ ~/.fonts 系统注册（assemble_v5 `setup` 段断言 fc-match）；ASS MarginV=375/MarginL/R=180/动态字号 68/56/48
  6. bg 段踩坑：repo 的 paizi_bg/sss_bg.mp4 仅 14s 样本，-ss 36.0 产 317 字节空流 → dl_bili_v2.py 重下完整原片（464.8s/213.5s）后正常
  7. 组装：assemble_v5（final/final_h/mux/mux_h/speed/speed_h/qc 双版本段）；speed 段一次被 600s 超时截杀致 moov 损坏，重跑恢复；QC G2 容差 ±2→±15 帧（与 G3 ±0.5s 对齐，提速重采样固有漂移 ≤11 帧）
- **Stage Summary**: 成片 v5 双版本（竖屏 1080×1920 66MB / 横屏 1080×810 50MB，673.2s，1.1x 提速）+ 字幕 srt + skill v1.2（31 铁律，含 7 条新铁律：安全框正解/最小字号/胶囊克制/动画化推理前置/字幕位 v2/libass 字体坑/双版本交付）全部交付 download/；qc_report_v5 BUILD_SUCCESS；已 push（c8e8a34）。

---
Task ID: 1105-ep1-v6-retro
Agent: Z.ai (GLM)
Task: 老板审片三反馈复盘轮：复盘记录 + v6 三修复重制（音画同步/影片比例/进度条）+ skill v2.0 规整（防回归架构）

Work Log:
- 现场复原：全量 clone clock 仓（非稀疏，410文件），通读 README/RESUME/worklog/production-notes/skill v1.2/assemble_v3~v5 源码，复原五轮修复全链路
- 反馈归因（先想后改，证据链制）：
  ① 字幕音频不对位（竖+横）= v5 的 SUBS 指向仓库旧文件 ep1_subtitles.json（v2 时代 385 卡字数权重对齐），字符流对齐法实测漂移 -23.6~+27.8s（86% 采样点>0.5s）——v3 已修复问题的经典回归；whisper 卡 JSON（v3/v4 实际使用）从未入库随沙盒蒸发
  ② 横屏嵌入影片"拉幅/比例尺不对" = bg 链 scale=1080:1920:force_original_aspect_ratio=increase+crop 铺满 9:16：牌子(16:9) 放大 2.67×横向只露 31.7%、丧尸清道夫(2.34:1) 放大 3.50×只露 24.1%、抽卡延时"只保留水平中部 35%"（v4 已知妥协无人复审）；横屏再 crop 后等效放大 3~6 倍
  ③ 附带发现：进度条 372s 切点重置永远只走 54%（v4 重写 final 段丢失 v2_seg 的 gen_seg_cmds 段偏移 t-t0，v5 未察觉，横竖屏都中招）
- v6 修复（assemble_v6.py，全部带回归门禁）：
  R1 权威字幕源重建：make_canonical_subs.py 从 output/字幕v3.srt（老板验收过音画同步的交付物）反向重建 ep1_subtitles_whisper.json（365卡+_provenance 血缘头）入库；setup 段逐卡对账断言（文本全等/±10ms/卡数365）不过不开工；G8 复验烧录 ASS（竖366横366=365+1跨段卡）
  R2 bg 双模式：fit（S02a/S02b/S03a/S03b/S24b 展示主体，等比入 1080×810 舞台 pad #131110：16:9→1080×608、2.34:1→1080×462、16:10→1080×675）/ cover（S04 竖版源 720×1280 铺满舞台框取中段，全宽无拉伸）；G9 几何断言抽帧实测窗口矩形 vs ffprobe 推算期望 ±6px，6/6 过（最大偏差3px）
  R3 gen_seg_cmds(total,t0,t1) 段偏移恢复；G10 切点前后±2s+片尾三处抽帧量顶部橙色条宽断言单调连续+终值满格（实测 539→544→1078px，v5 逻辑会是 539→~9→~542）
- 生产重制：素材全量重拉（网盘配音/BGM/t2第一抽/抽卡延时 323MB 用重建的 para_dl.py 12 段并行；B站 paizi/sss 按文档 playurl html5 通路）+ 46 镜全量重渲 6016 帧（h5_render_v4 幂等分批）+ 双版本组装（22211 帧精确 vtrack → final/final_h 分段 → 1.1x 提速：竖屏 20205 帧/横屏 20198 帧，673.2s）
- QC：G1-G10 双版本全 PASS（BUILD_SUCCESS）；锚点式目检（先算期望再对照实读）：26.71s「这些案例很容易给人一种错觉：」/314.27s「最低需要充值多少钱？」/671.42s 片尾 等 4 锚点×2 版本 8/8 命中
- 目检误报仲裁实录：VLM 判 S02a 嵌入画面"被裁切拉伸"→ 手工同参数链生成参考帧像素 diff（窗口区平均差 5.1=编码噪声级）证明几何完全正确，VLM 把源片贴地特写镜头（脚在上地面占满的影片自身构图）误读为变形；教训=感知检查必须锚点化+像素仲裁
- 复盘记录：05-retro/RETRO.md（三问题证据链/五步根因链/深层四因：token 花在生产不花在防回归、长上下文负资产、备份纪律半吊子、QC 测技术健康不测用户感知；修复架构=单一事实源+开工对账+感知门禁+重写对账+锚点目检）
- skill v2.0 规整（explainer-video-studio）：铁律去项目化重组 A-F 六组 29 条（项目数值入 Profile 机制，防跨项目污染）；新增 references/anti-regression.md（防回归协议八节）+ SKILL.md §9 三句话版；文档优先协议（外部平台先查路由表，探索预算1次，结论回写文档）；新增铁律"真实影片素材原生比例"；scripts +assemble_v6/make_canonical_subs/para_dl；清理 03-skill/ 下过期 v1.0 SKILL.md 重复副本（血统不明文件）；推荐Prompt用法更新（whisper 对齐替换已废弃的反推语速+续作防回归条目）

Stage Summary:
- 交付：v6 成片双版本（竖屏 1080×1920 55MB / 横屏 1080×810 48.8MB，673.2s，音画同步/影片原生比例/进度条满格三修复全过 G1-G10）+ 字幕v6.srt + qc_report_v6 + 复盘记录 RETRO.md + skill v2.0 包（47文件275KB，已同步本地 skills/）→ download/ 与仓库
- 防回归基建：权威字幕源入库带血缘、setup 开工对账断言、G8-G10 感知维度门禁、锚点目检表、中间产物入库清单——三处回归今后"想错都错不了"
- 已知妥协：1.1x 提速重采样帧数漂移 +13 帧（0.43s，G2 容差内）；S02b/S03b 证据卡入场时刻仍为字符占比估算（≤1s，不在本次反馈范围）
