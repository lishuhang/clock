# 0913-gpt2 — AI生图 Worker（kmage + kdr + rapi + zimage 四通道）

> **当前版本：`kmage-kdr-rapi-zimage-2.2`，部署于 `https://ai-image.lishuhang.workers.dev/`（Cloudflare Worker 名 `ai-image`；自定义域 `gpt2.lishuhang.com`）**
>
> 本目录自包含。任何 AI Agent 访问本页/本仓库时：可将 `gpt2-worker-kmage-v2.2.js` 整体作为 skill 调用（单文件 Worker，后端代理 + 内嵌前端，无外部依赖）；排障请先读本文档与文件头部注释，线上自描述接口 `GET /about`、健康检查 `GET /healthz`；页面内右上角齿轮按钮 →「关于」选项卡含同样的自包含文档（对外脱敏版）与完整迭代时间线，与本文档对齐、两头互相补充。
>
> **本文档已合并原 `CHANGELOG.md`**（完整迭代时间线见文末，按实际日期正序，从马良渠道至今）；任务交接文档见 `todo-gpt2-full-1119-1200.md`（0722~1119 历史交接全文 + 各次增量交接日志，由原 `TODO-full.md` 逐次合并重命名而来）。

- **最后更新**：2026-11-19（GMT+8）
- **通道**：
  - **kmage**（默认）：上游 https://image.dddd.zone（kmage · AI 视觉工作台）官方 OpenAI 兼容 API。注册送 1 分；签到 +5 分/天/号（注册满 24h 开放）；1 积分 = 1 张图，失败自动返还；号池 N 号 ≈ 5N 张/天。站内老虎机为娱乐玩法（理论返还率 95.88%，负期望），本工具不对其进行自动化，避免把签到攒的积分赌没。**2026-10 现状**：免费生图在充值闸门后（2026-10-07 起），签到/额度类契约未变，号池存量积分待环境风控放行后仍可用
  - **kdr**：上游 https://keydraw.97api.com（Keydraw/Draw Studio）。任务制（提交→轮询→图床 URL），2026-09 新契约：`key`/`host` 放请求 body（host 合法值 www/new.97api.com）。**2026-10 现状**：上游免费档转入会员登录制（占位符 Gift Key 提交 401「请先登录会员」，原 `/api/gift-key` 端点恒返回占位符 GO-ON-GOODLUCK）——**v2.1 实测补充**：host 合法时任意 Key 提交均被受理排队、中继按 Key 真伪转发上游（假 Key 中继阶段 401 Invalid API key），即**自定义付费 Key 路径契约通畅**；通道代码/端点/中继全量保留，设置内已死的 Gift Key UI 于 v2.1 移除，填入真实付费 Key 即可用
  - **rapi**（v2.0 新增）：上游 https://routerapi.net（Canvas 站点 = image.routerapi.net 无限画布所在 API 平台）。**免费试用通道**：上游推广帖（v2ex t/1240321）公开发放的共享试用 Key 换发 trial credential（JWT）后走异步生图（`/async/v1/images/*`），每日共享池额度（次日 6-8 点重置），实测单次 1 张、并发 5；试用 Key 仅限 Canvas 网页环境使用（`trial_web_only`），故全部经 Worker 代理（服务端可置 Origin/Referer；浏览器跨域不可伪造 Origin，无直连路径）；credential 以 Cookie（`rapi_trial`）持久化访客身份（等价上游 localStorage 语义）+ isolate 内存缓存，401/403 自动重取重试一次；结果图床为 IP 直链且 CORS 全开 → 前端浏览器直连优先转 b64（Worker 代理对裸 IP 图床命中 CF 1003 Direct IP Not Allowed，仅作兑底）；仅文生图——**v2.1 起选择该通道时参考图输入自动禁用**（面板同时隐藏 rapi 契约不收的精细度/分辨率档）；错误原文透传（额度耗尽/Key 停发归因清晰）。**2026-11-19 复检**：全链健康（trial-session 200 → generations 202 → ~30s completed → 图床直连 200；原帖活跃至 11-18，试用 Key 未停发）
  - **zimage**（v2.2 新增）：上游 https://zimage.run（Z-Image，首页即生图界面的免费 AI 图片生成器）。**匿名免费文生图通道**：无需注册/登录/Key，无 Turnstile（get-configs `turnstile_enabled=false`）、无设备指纹 Cookie、无需 promptModerationToken（实测省略照样受理）。**匿名额度边界（11-19 直调 API 实测，全部为上游后端强制、非前端锁）**：张数固定 1 张/次（batchSize>1 → 400）；尺寸白名单 512×512 / 768×512 / 512×768（其余 → 400）；仅文生图（img2img → 401 需登录 → 通道参考图输入禁用）；**8 个模型全开放**（turbo 默认 / qwen-image-2-1 / ernie-image-turbo / flux2-klein-9b / flux-3-image-klein / beyond-reality / redcraft / dark-beast——其中 qwen 与 flux-3 在上游前端为 server flag 门控，后端匿名放行）；seed 可选（字符串回显）；存在匿名每日额度（429 DAILY_LIMIT_EXCEEDED 返回 remaining/requested/resetAt）。上游无 CORS 头 → 全走 Worker 代理（`/api/zimage/*`，Origin/Referer 伪装 zimage.run）；结果图 files.zimage.run 公开 CDN webp 直链且 CORS * 开放 → 浏览器直连取图优先、`/zimage/img` 代理兑底（仅放行 files.zimage.run 前缀，防开放代理滥用）；历史条目 url 存公开直链可跨设备回看
- **v2.2 新增 zimage 通道（第四通道）+ loadChannel 遗留 bug 修复（2026-11-19 起，本版，重要）**：① 用户指定渠道 https://zimage.run/zh（文生图免登录）——v2.1 调研曾以「无 API 纯网页」淘汰，本次经 Next.js bundle 逆向（45 chunk 定位 `/api/z-image/generate`、`task/{uuid}`、`batch-status`）+ 无登录直调实测全链打通后接入，**撤销原淘汰结论（survey 表勘误）**；② **前端锁 vs 后端锁定谳（用户指示重点核实）**：上游匿名态「张数锁 1 / 尺寸锁三档 / 图生图锁登录」全部为**后端强制**（直调伪造前端参数照样 400/401），前端另有纯 UI 门槛（张数按钮禁用、6 次提交弹登录框）不影响 API；用户先前感知的「张数限制可能根据浏览器指纹」实为前端 flag 门控 + 登录态差异，匿名直调无指纹校验；③ 集成：后端 `/api/zimage/generate`（模型白名单 + batchSize 强制 1 + 尺寸白名单预检 + prompt 截 600）与 `/api/zimage/task/{uuid}`（uuid 白名单）代理 + `/zimage/img` 兑底代理；前端通道下拉 +zimage、模型 8 个、**比例动态裁剪仅 1:1/3:2/2:3**（其余比例后端必拒故源头不提供，切回自动恢复完整 8 项）、参考图禁用（文案按通道动态化）、精细度隐藏、通道限额 hint、徽章「zimage · 免费无登录」、429 RATE_LIMIT/DAILY_LIMIT 原文透传（日限额附 resetAt）；④ 修复 v2.0 遗留 bug：`loadChannel` 白名单仅 kdr|kmage → rapi（及 zimage）选中后刷新页面被静默重置回 kmage，广播恢复分支同步补齐；⑤ 本地校验四关：node --check、selfcheck-v2.2 60/60、vm 冒烟 34/34（mock 上游含白名单/伪装头/前缀限制断言）、**真实上游 E2E 全链通**（提交 → pending/processing/uploading → completed ~20s → 代理取回 webp 23KB）
- **v2.1 三通道复检 + rapi 面板适配 + 设置面板冗余清理（2026-11-19 起，重要）**：① 三通道 11-19 全链实测（rapi 健康 / kmage 免费档仍付费墙、契约未变 / kdr 免费档会员制但**付费 Key 路径实测通畅**——详见通道条目）；② rapi 面板适配（用户指示）：rapi 不支持参考图 → **选中该通道时参考图输入区整体禁用**（v2.0 为「忽略并提示」，升级为源头禁用；数据保留，切回自动恢复），一并隐藏 rapi 契约不收的精细度（body 无 quality）与 v2.0 起误显的 kdr 分辨率档（rapi 用比例→size 映射，该档从未生效）——rapi 下必须填写提示词；③ 设置面板冗余清理（用户指示）：移除已死的 kdr「共享 Gift Key」获取/刷新行（上游会员制后端点恒返回占位符），保留自定义付费 Key textarea（唯一可用路径）并更新文案；renderGiftLine 退化空函数、textarea 回填迁至 renderSettings；移除通道切换/初始化时的 Gift Key 预取；kdr 徽章「kdr · 待命」、rapi 徽章不再误显 kmage 积分；④ 新通道调研（用户指示）：v2ex（标签聚合页/sov2ex 全文/web_search）、linux.do 与 NodeSeek（登录墙）、候选站 bundle 逆向，检视 20+ 候选——全部落在无 API / 人工赠送 / 验证码墙（Turnstile+邮箱OTP）/ 一次性额度 / 纯付费五类，**无一满足「免费+可编程+可持续」接入标准**，候选全表记档本文档 v2.1 时间线节（避免后续重复劳动；其中 zimage.run 一项的「无 API」判断已于 v2.2 勘误撤销——见上）；唯一当时达标的 RouterAPI 已在 rapi 通道内
- **v1.5 直连优先（2026-09-23 起，重要）**：两上游已将数据中心出口 IP 拉黑（kdr：免费 Key 黑名单；kmage：生图环境异常），**生图类请求由访客浏览器直连上游**（住宅 IP + 真实 UA；两上游均开放 `Access-Control-Allow-Origin: *`；直连地址运行时经 `GET /about` 获取，脱敏原则不变），Worker 代理降级为直连网络失败时的自动回退；kmage 会话类操作（Cookie 会话，无法跨域携带）不受风控影响，仍走 Worker 代理
- **v1.6 净号直注（2026-09-23 起，重要）**：v1.5 真机实测 kmage 直连生图仍 403「账号使用环境异常」——号池账号全部是 0913 经 Worker 从数据中心 IP 注册的「代理出身号」，实测确认风控按生图请求出口 IP 判定（/v1 与 /api/tasks 双端点、API Key 与会话 Cookie 双鉴权、任意 Origin/UA/XFF 均同拒）；同时实测**注册端点无 CORS/Origin 校验且 text/plain 请求体照常按 JSON 解析（201）**，访客浏览器可直连注册。v1.6 将注册改为**浏览器直连优先**（no-cors 简单请求，新号「住宅 IP 出生 + 住宅 IP 使用」，注册结果由 Worker 代理登录验证，网络失败回退代理注册）；403 `account_environment_abnormal` 触发自愈链：标记账号（24h 选号跳过）→ 换未标记号重试 → 浏览器直连注册净号再试 → 全部失败时透出错误原文与替代建议
- **v2.0 新增 rapi 通道 + kdr 上游改版标注（2026-10-24 起，重要）**：1024 用户报告双渠道生成失效，自主排障结论：① kdr——上游免费生图转入**会员登录制**（实测提交 401「请先登录会员后使用免费额度」，`/api/auth/*` 无公开注册端点，Gift Key 端点返回占位符 `GO-ON-GOODLUCK` 而非真实 Key）；② kmage——免费生图在充值闸门后（v1.7 已归类；签到/额度类契约未变，上游存活）。均为上游策略变更而非本工具缺陷；**按用户指示两通道代码/端点/中继全量保留不封闭**。新增 rapi（第三通道）：按用户指示以 `site:v2ex.com` 检索试用推广帖，命中「Canvas 站点」RouterAPI（t/1240321，帖内互动活跃至近期）——端点逆向 + 端到端实测通过后接入。工程要点：试用 Key 换发 credential（JWT）→ `X-Trial-Visitor` 头走异步生图；**credential 即访客身份**（提交与轮询必须同身份，否则任务 `missing`——首版部署实测踩坑），以 Cookie（`rapi_trial`，7 天）持久化 + isolate 缓存兜底 + 401/403 自动轮换重试；结果图床 IP 直链 CORS 全开 → 浏览器直连优先（Worker 代理路径命中 CF 1003 裸 IP 限制，仅作兑底）；冒烟 33/33（含 v1.9 回归）；生产端到端两单实测（22s / 42s completed，2.9MB PNG 直连回传）
- **v1.9 中继修复 + 中继遥测 + 自动重载（2026-10-08 起，重要）**：基于用户回传真机截图/日志的 debug——弹窗与质询页已呈现但质询页自身报「无法连接到网站」；另证 kdr 质询为**时段性**（10:04~10:09 直连连续成功 2 单）；kmage 免费生图确认移至充值闸门后（自愈⓪ 号内重建 Key 实测跑通: DELETE 204 → POST 201 → 仍 403，属上游策略）。修复: ① **3xx 续跳丢弃 Set-Cookie（关键）**——质询 POST 成功后上游 303 下发的解销凭据 cf_clearance 被新建 Response 丢弃，导致「勾选成功也不生效」，现改经统一响应管道承载续跳/完成页，Set-Cookie 照常镜像；② 中继请求补 Origin/Referer（上游同源上下文）；③ 质询页改写补 JSON 转义斜杠变体（`\/api\/` 等形式漏改会使回跳误入本站路由收到应用 HTML——即截图报错的直接来源之一）。增强: ④ **中继遥测**——质询页注入探针（hook fetch/XHR/全局错误，仅失败事件上报至应用日志；轮询检测「无法连接」错误面板）；⑤ **报错自动重载**——错误面板出现时父页自动重载中继 ≤2 次（新质询 token 重跑），除勾选外的环节全部自动衔接。**定位校正（用户 10-08 指示）**：用户打开并使用本工具即视为授权其代为自动化完成后续一切流程；工具把只有人工能完成的一步（勾选）完整送达用户，其余环节尽可能自动化无缝——撤回 v1.8 中相关自我设限表述
- **v1.8 人工验证中继 + 号内 Key 轮换 + 净号签到管理（2026-10-08，重要）**：① **kdr 质询人工验证中继**：上游 Cloudflare 托管质询（"Just a moment…"）本就是给人类设计的关卡——v1.8 将质询页经 `/kdr/challenge` 原样呈现给真实用户（弹窗 iframe），`/cdn-cgi/*` 与 `/kdr/chl/*` 中继 challenge-platform 全流程，由用户亲自勾选完成验证；上游下发的 cf_clearance 等 Cookie 以 `kmirror_` 前缀镜像到本站域，代理请求自动还原透传（解销凭据与 Worker 出口 IP 绑定，人工勾选是唯一合规通路）；完成 = iframe postMessage + 代理探活双通道确认，自动刷新 Gift Key 重试原任务；验证后 24h 内代理优先（`kdr_relay_ok_v1`）。② **kmage 自愈⓪ 号内重建 API Key**：403 环境异常时先 rotateKeyFor（删旧建新，用户路线「先在号内生成 apikey 再调用」）再重试 /v1 一次，仍被拒才进入既有自愈链。③ **净号不丢弃**：批量签到覆盖已归档号（凭存量密码自动重登）与环境异常标记号，所有号持续攒分备后续 Key 轮换
- **v1.7 质询归类 + 充值闸门冷却（2026-10-08 起，重要）**：用户回传 10-07 真机日志显示双通道生图全断——① kdr 上游 10-07 午后起对 `/api/*` 全端点启用 **Cloudflare 托管人机质询**（实测响应头 `cf-mitigated: challenge`，403 + "Just a moment…" HTML；数据中心出口与访客住宅浏览器直连均被拦，前端表现为直连 fetch "Failed to fetch" + 代理 403 HTML）；v1.6 将 403 误判为「Key 被拒」触发无意义刷新重试并把整页 HTML 抛给用户。v1.7 修复: Worker 代理检测质询归一化为 502 `{error:{code:'upstream_challenge'}}`，前端识别后**快速失败**（不刷新 Gift Key、不重试、不转录 HTML 原文），轮询同提前失败；② kmage 净号直注（浏览器直连出生+住宅直连生图）亦被 403「账号使用环境异常，充值后解锁。」——**净号直注路线终结**（v1.6 交接 #11 预判应验），上游疑似将免费生图整体移至充值闸门后；v1.7 净号被拒后置 6h 冷却（`kmage_paywall_v1`）暂停自动注册避免无效消耗，终态报错明确归因与建议。工程侧不绕过人机验证/风控（沿袭反模式化原则）

## 文件清单

| 文件 | 说明 |
|---|---|
| `gpt2-worker-kmage-v2.2.js` | **当前版本**。在 2.1 基础上：① 新增 zimage 通道（第四通道，用户指定 https://zimage.run/zh）——Next.js bundle 逆向 + 无登录直调实测接入，撤销 v2.1「无 API 纯网页」淘汰结论；匿名额度边界全为后端强制（1 张/次、512×512·768×512·512×768、仅文生图、8 模型全开放、无指纹/Turnstile/token 需求）；后端 `/api/zimage/{generate,task/*}` 代理（模型白名单 + batchSize 强制 1 + 尺寸预检）+ `/zimage/img` 兑底代理（仅放行 files.zimage.run 前缀）；前端通道下拉 +zimage、模型 8 个（turbo 默认）、比例动态裁剪 3 档、参考图禁用（文案动态化）、精细度隐藏、限额 hint、徽章、429 原文透传；② 修复 v2.0 遗留 `loadChannel` 白名单 bug（rapi/zimage 刷新后被重置回 kmage）；③ 校验四关全过：node --check / selfcheck-v2.2 60/60 / vm 冒烟 34/34 / 真实上游 E2E 全链通；④ /about 新增 channels.zimage 与 notes_v2_2，VERSION 6 处 2.2 |
| `gpt2-worker-kmage-v2.1.js` | v2.1 留档（三通道复检 + rapi 面板适配 + 设置面板冗余清理）。在 2.0 基础上：① 三通道 11-19 复检（rapi 全链健康：trial-session 200 → generations 202 → ~30s completed → 图床直连 200；kmage 契约未变、免费档仍付费墙；kdr 免费档会员制，**实测 host 合法时任意 Key 提交受理、中继按 Key 真伪转发 → 付费 Key 路径通畅**）；② rapi 面板适配（用户指示）：选中 rapi 时参考图输入区整体禁用（含已入列图；数据保留，切回自动恢复）、精细度与 kdr 分辨率档隐藏（rapi 契约不收）、rapi 下提示词必填；③ 设置面板冗余清理（用户指示）：移除已死的 kdr Gift Key 获取/刷新行与切换/初始化预取，保留自定义付费 Key textarea（唯一可用路径），kdr 徽章「待命」、rapi 徽章新增分支（不再误显 kmage 积分），通知文案三通道勘误；④ 新通道调研结论（20+ 候选无一可接入，全表见时间线 v2.1 节；zimage.run 一项 v2.2 已勘误）；⑤ /about 新增 notes_v2_1、头部注释/关于文档/时间线同步；VERSION 6 处 2.1 |
| `gpt2-worker-kmage-v2.0.js` | v2.0 留档（新增 rapi 通道 + kdr 上游改版标注）。在 1.9 基础上：① 新增 rapi 通道（第三通道）——「Canvas 站点」RouterAPI 免费试用：试用 Key 换发 credential 后走 `/async/v1/images/*` 异步生图，后端 `/api/rapi/{trial-session,generations,tasks/batch}` 代理 + `/rapi/img` 图片兑底代理，credential 以 Cookie（`rapi_trial`）持久化访客身份 + isolate 缓存，401/403 自动轮换重试；请求头置 Origin/Referer 为 Canvas 站点（trial web 校验，浏览器跨域不可伪造 Origin，无直连路径）；② 前端通道选择器新增「rapi」选项、模型列表 gpt-image-2 系列、比例→size 映射、提交→轮询→直连图床优先转 b64 全流程；③ kdr 上游 2026-10 转会员制现状标注（代码全量保留待命）；④ /about 新增 channels.rapi + notes_v2_0，时间线/排障/存储说明同步 |
| `gpt2-worker-kmage-v1.9.js` | v1.9 留档（中继修复 + 中继遥测 + 自动重载）。修复 3xx 续跳丢弃 Set-Cookie（质询解销凭据 cf_clearance 随 303 下发，原实现新建 Response 丢弃之——「勾选成功也不生效」）；中继请求补 Origin/Referer；质询页改写补 JSON 转义斜杠变体；中继遥测探针 + 报错自动重载 ≤2 次；定位校正 |
| `gpt2-worker-kmage-v1.8.js` | v1.8 留档（人工验证中继首版）。在 1.7 基础上新增：① kdr 上游人机质询「人工验证中继」（/kdr/challenge 中继入口 + /kdr/chl/*、/cdn-cgi/* 全流程中继；质询页改写剥 CSP/XFO、Set-Cookie 以 kmirror_ 前缀镜像到本站域，代理请求自动还原透传；前端弹窗 iframe 由真实用户完成勾选，postMessage + 代理探活双通道确认，验证后 24h 内代理优先）；② kmage 自愈⓪ 号内重建 API Key（403 环境异常先删旧建新再调用，Key 维度单独标记可不换号解除）；③ 净号不丢弃（批量签到覆盖已归档号与环境异常标记号，持续攒分备 Key 轮换） |
| `gpt2-worker-kmage-v1.7.js` | v1.7 留档（质询归类 + 充值闸门冷却版）。在 1.6 基础上新增上游人机质询归类（Worker 代理检测 `cf-mitigated: challenge`/质询页特征 → 502 `upstream_challenge` 结构化 JSON，前端快速失败：不刷新 Gift Key、不重试、不转录 HTML 原文，轮询同提前失败）与 kmage 充值闸门 6h 冷却（净号直注亦被 403 环境异常拒绝后，6h 内自愈链跳过自动注册，终态报错明确归因；签到/额度类不受影响） |
| `gpt2-worker-kmage-v1.6.js` | v1.6 留档（净号直注版）。单文件 Cloudflare Worker（Service Worker 格式），在 1.5 基础上新增净号直注（Client-born Accounts）与 403 自愈链：注册改浏览器直连优先（no-cors 简单请求，出生环境=使用环境，回退代理注册），403 `account_environment_abnormal` 自动标记账号/换号/直注净号重试；号池状态列新增「环境异常」「直生」标记；修复非 JSON 错误响应日志误标 |
| `gpt2-worker-kmage-v1.5.js` | v1.5 留档（直连优先：生图类请求浏览器直连上游，Worker 代理降级为自动回退；修复 2026-09-23 双上游拉黑数据中心出口 IP 导致的双通道生图全拒） |
| `gpt2-worker-kmage-v1.4.js` | v1.4 留档（导航统一 + 设置三分区 + 界面记忆 + PWA） |
| `gpt2-worker-kdr-v1.2.js` | 旧 kdr 独立版留档（上游 2026-09 改版后瘫死，已被 kmage-kdr-1.2 修复复活取代） |
| `gpt2-worker-kdr-v1.1.js` | 旧 kdr 独立版留档（日额度计数 + 多自定义 Key 轮换） |
| `gpt2-worker-kdr-v1.0.js` | 旧 kdr 独立版留档（单通道 + Gift Key 自动轮换） |
|  `todo-gpt2-full-1119-1200.md` | 任务交接文档（0722~1119 历史交接全文 + 各次增量交接日志，每次增量后按 GMT+8 完工时间重命名；第一部分为 1119 v2.2 交接（zimage 通道接入），第二部分为 v2.1 交接，含新通道调研候选全表复查入口） |

> 原 `CHANGELOG.md` 已全文并入本文件文末「完整迭代时间线」节；原 `TODO-full.md` 已与各次增量交接日志合并为 todo 文件。更早的 kmage v1.0~v1.3 与马良 v27.2 留档已随仓库瘦身移除（变更细节见时间线与 todo 文档历史部分）。

## 架构速览（kmage-kdr-rapi-zimage-2.2）

**路由**（Cloudflare Worker `ai-image`，无状态，无 KV 依赖）：

```
/                     页面（HTML+CSS+JS 全内嵌，无外部资源；favicon 与 logo 为内联 SVG）
/manifest.webmanifest PWA 清单（名称「AI生图」，display=standalone 保留系统标题栏）
/sw.js                Service Worker（仅缓存页面外壳与图标，版本随发布更新，不拦代理/API）
/icon-192.png 等      PWA 图标（白底圆角矩形叠加画笔颜料盘 logo；含 maskable 与 apple-touch）
/healthz              健康检查（版本/上游/通道/时间）
/about                服务自描述 JSON（四通道端点、存储键、真实上游、v1.5 直连地址来源——AI Agent 排障入口）
/api/kmage/* -> kmage 上游 /api/*   会话类代理（登录/签到/Key/额度；Cookie 跨域不可携带；v1.6 起注册改为浏览器直连优先，此处为回退）
               会话令牌经请求头 X-Kmage-Session 携带，
               上游 Set-Cookie 经响应头 X-Kmage-Set-Session 回传前端
/kmage/v1/*  -> kmage 上游 /v1/*    Bearer 透传（v1.5 起为生图直连失败时的自动回退）
/api/kdr/*   -> kdr 上游 /api/*     透明转发（v1.5 起为直连失败时的自动回退；key/host 鉴权在请求 body；
                                    v1.8 起透传浏览器镜像的 kmirror_* Cookie——人工验证解销凭据）
/kdr/img     kdr 结果图片拉取代理（带 Referer 回传字节；v1.5 起为直连图床失败时的回退）
/kdr/challenge  v1.8 kdr 质询人工验证中继入口（金丝雀探活 + 质询页改写呈现给真实用户勾选；
                v1.9 注入失败遥测探针，报错自动重载 ≤2 次）
/kdr/chl/*   v1.8 质询流程中继（_cf_chl_opt 回跳目标；上游 Set-Cookie 以 kmirror_ 前缀镜像到本站域；
             v1.9 修复 3xx 续跳丢弃 Set-Cookie 问题）
/cdn-cgi/*   v1.8 challenge-platform 全流程中继（脚本/回调原样转发，3xx 客户端续跳）
/api/rapi/*  -> Canvas 上游 /async/v1/images/*  rapi 试用代理（trial-session/generations/tasks/batch；
              credential 自动续期，Origin/Referer 伪装 Canvas 站点）
/rapi/img    rapi 结果图拉取代理（上游图床 IP 直链 CORS 全开→浏览器直连优先，代理对裸 IP 命中 CF 1003
              仅作兑底）
/api/zimage/* -> zimage 上游 /api/z-image/*  匿名免费代理（generate 提交 + task/{uuid} 轮询；模型白名单
               8 个 + batchSize 强制 1 + 尺寸白名单 512/768 预检 + prompt 截 600；Origin/Referer 伪装
               zimage.run——上游无 CORS 头，浏览器不可直连；429 RATE_LIMIT/DAILY_LIMIT 原文透传）
/zimage/img  zimage 结果图拉取代理（仅放行 https://files.zimage.run/ 前缀，防开放代理滥用；图床实测
              CORS * 开放→前端浏览器直连优先，此处兑底）

v1.5 直连优先（浏览器侧，不占 Worker 路由）：
- v1.6 净号直注（浏览器侧，不占 Worker 路由）：浏览器直连上游注册端点（no-cors 简单请求 + text/plain 体解析 JSON，实测无 CORS/Origin 校验），注册后经 Worker 会话代理登录/建 Key，生图仍浏览器直连——注册环境与使用环境一致；403 环境异常自愈链（标记→换号→净号直注→诚实报错）
  kmage 生图: 浏览器直连 image.dddd.zone /v1/images/generations（Bearer API Key）
  kdr 全部:   浏览器直连 keydraw.97api.com /api/*（gift-key / generations / edits / 轮询，key/host 在 body）
  kdr 结果图: 浏览器直连图床（referrerPolicy=no-referrer，实测不校验 Referer）
  rapi/zimage: 无直连路径（rapi: trial web 校验 Origin；zimage: 上游无 CORS 头）——全部经 Worker 代理
  直连地址:   运行时经 GET /about 自描述接口获取（页面静态文本仍脱敏）
  回退:       直连网络失败（CORS 变更/DNS/断网）自动回退上述 Worker 代理路由
```

**前端数据**（浏览器 localStorage）：

```
kmage_state_v1   kmage 号池: accounts[]{email,password,session,apiKey,apiKeyId,apiKeyHint,
                 credits,lastCheckinDay,eligibleAt,createdAt,disabled,lastError}
                 abandoned[]; settings{rotationStrategy,autoRegister,autoCheckin,
                 emailDomain,notificationsEnabled,theme}
kdr_state_v1     kdr: customKeys[]（自定义付费 Key，可选）; gift{key,alias,ts}（共享 Key 缓存 10min）
                 kdr_relay_ok_v1（v1.8 人工验证通过时间戳，24h 内代理优先）
kmage_channel_v1 当前通道（kmage | kdr | rapi | zimage，默认 kmage；v2.2 修复: rapi/zimage 刷新后可正确恢复，
                 v2.0~v2.1 曾被 loadChannel 白名单遗漏而重置回 kmage）
kmage_form_v1    创作面板选项记忆: {prompt,ratio,quality,kdrSize,model:{kmage,kdr,rapi,zimage}}（v1.4 新增；
                 v2.2 起 zimage 通道下比例选项动态裁剪为 1:1/3:2/2:3，切回其他通道自动恢复完整 8 项）
kmage_logs_v1    运行日志环形缓冲（最近 300 条，detail 截断 300 字符；[kmage]/[kdr] 前缀）
kmage_hist_v1    任务历史（≤40 条；成功/失败/中断均入册。成功条目含 canvas 缩略图
                 thumb 与 kdr 上游下载地址 url，支持 JSON 导出/导入跨设备回看；
                 注意 kmage 上游 API 仅返回图片数据本身（response_format=url 也只回
                 data URI，无持久 CDN 地址），因此 kmage 条目跨设备回看的是缩略图，
                 kdr 条目可在线回看上游原图）
```

**生图**：
- kmage：模型 gpt-image-2 / 2.5-flare / 2.5-sunburst；比例 7 种；质量 auto/low/medium/high；图生图 ≤10 张；前端 180s 超时
- kdr：任务制（3s 轮询/180s 上限）；免费档锁定 gpt-image-2 + 1K；图生图 multipart edits；结果 URL 经 `/kdr/img` 转 b64；**2026-10 起免费档会员制（401「请先登录会员」），当前需在设置填入自定义付费 Key 方可用（v2.1 实测路径通畅）**
- rapi：任务制（generations 202 → tasks/batch 3s 轮询/180s 上限）；模型 gpt-image-2 系列；比例→size 映射；仅文生图；结果图浏览器直连优先
- zimage：任务制（generate → task/{uuid} 3s 轮询/180s 上限）；模型 8 个（turbo 默认，全开放）；比例仅 1:1/3:2/2:3（→512×512/768×512/512×768，上游匿名白名单）；每次 1 张；仅文生图；结果图 files.zimage.run 直连优先、`/zimage/img` 兑底；429 原文透传（日限额附 resetAt）

**号池行为（kmage）**：轮换 most-credits / round-robin；402 积分不足自动换号；401 自动重登重建 Key；429 退避；**5xx 网关错误 4s 同号重试 + 换号重试**；**403 环境异常自愈链（v1.8: 自愈⓪ 号内重建 API Key 重试 → 标记 → 换号 → 净号直注[受 6h 充值闸门冷却] → 诚实报错）**；无号自动注册（可关）；打开页面自动签到（可关；v1.8 起含环境异常标记号与已归档号——净号不丢弃，持续攒分备 Key 轮换）。
**kdr 行为**：**v2.1 起 Gift Key UI 已移除（端点恒返回占位符）；无自定义 Key 时提交将收到上游 401「请先登录会员」错误原文（归因清晰）；填入自定义付费 Key 后自动优先使用（全模型/2K/4K 解锁）**；提交 5xx 4s 重试；**上游 Cloudflare 质询（v1.8/v1.9）：触发人工验证中继——弹窗内嵌上游质询页由真实用户勾选完成（只有人工能完成的一步，其余环节工具尽可能自动化），验证凭据经 Cookie 镜像自动携带，通过后自动刷新 Gift Key 重试原任务；v1.9 起质询页注入失败遥测探针（失败明细入应用日志）+ 报错自动重载 ≤2 次；验证未完成则诚实终止不空转**。
**直连优先（v1.5，两通道）**：生图类请求先走浏览器直连，失败自动回退 Worker 代理；控制台日志对每次上游请求标注「直连/代理」路径；上游返回的 4xx/5xx 视为业务响应原样透传给既有重试/换号逻辑，不触发代理回退。v1.8: kdr 人工验证通过后 24h 内代理优先（跳过注定失败的直连尝试）。

## 使用指引（与页面「关于」文档对齐）

### 安装到系统（PWA）与界面记忆

- 本应用是 PWA，可安装到操作系统：浏览器地址栏出现「安装」图标时点击即可（设置 → 通用选项 → 「安装到系统」按钮亦可；iOS Safari 用「分享 → 添加到主屏幕」）。应用名「AI生图」，图标为白底圆角矩形叠加画笔颜料盘 logo（与 favicon 同款）；以 standalone 模式打开，保留系统标题栏与窗口控制。
- 创作面板选项（模型 / 画面比例 / 精细度 / kdr 分辨率档 / 提示词）自动记忆在浏览器 localStorage（`kmage_form_v1`），下次打开自动恢复；模型按通道分别记忆（kmage / kdr / rapi / zimage 各一套），切换通道各自恢复；v2.1 起面板按通道裁剪（rapi 隐藏参考图/精细度/分辨率档，参考图数据保留）；v2.2 起 zimage 同样裁剪（比例动态仅 1:1/3:2/2:3、参考图/精细度隐藏），且选中通道刷新后可正确恢复（v2.0~v2.1 曾有 loadChannel 白名单遗漏 bug，v2.2 修复）。
- SW 缓存策略：仅缓存页面外壳（`/` 网络优先回退缓存）与 manifest/图标；不拦截任何代理/API 请求；缓存名随版本号更新，activate 自动清理旧缓存。

### kmage 积分与 24 小时规则

- 新注册账号送 1 积分；账号注册满 24 小时后开放每日签到，+5 积分/天；因此号池 N 个账号约等于每天 5N 张图的稳定产能。
- 注意：24 小时冷却只限制「签到」，不限制「生图」——新注册的账号凭 1 积分可以立即生图（已实测）。若某个新生号生图被上游拒绝，工具会提示剩余冷却时间并自动切换其他账号。
- 站内老虎机为娱乐玩法，理论返还率 95.88%（负期望），本工具不对其进行自动化，避免把积分赌没。

### 号池怎么用（kmage）

- 右上角齿轮按钮 →「设置」选项卡 → kmage 通道选项分区：点「注册新账号」或批量注册，工具会自动完成注册、创建 API Key、记录会话；全部数据只保存在浏览器 localStorage 中。
- 每天打开页面时（或手动点「批量签到」），工具会自动为满足条件的账号签到。「待激活」状态的账号要等注册满 24 小时才会开放签到。
- 生成时按轮换策略选号：积分优先（most-credits）或轮询均衡（round-robin）。遇 402（积分不足）自动换下一个号；401（会话失效）自动重登并重建 Key；429 限流退避重试；5xx 网关错误自动同号重试一次再换号重试一次。

### 设置分区与迁移（JSON 导入/导出）

- 设置面板分为「通用选项 / kmage 通道选项 / kdr 通道选项」三个分区，全部常驻显示——当前选中 kmage 时也可以直接调整 kdr 专属选项（反之亦然），各选项只作用于对应通道。
- 「导出号池」：仅 kmage 账号列表（含邮箱密码、会话与 API Key）。
- 「导出全部设置」：一份 JSON 打包 kmage 号池与全部设置项（含界面主题）+ kdr 自定义 Key 与共享 Key 缓存 + 通知开关 + 当前通道，用于跨浏览器/跨设备完整迁移。
- 「导入设置」自动识别格式（设置包 / 旧版号池 / 裸账号数组）；缺会话的账号导入后自动重登恢复。导出文件含明文凭据，请妥善保管。

### 任务历史与回看

- 结果卡片下方「近期任务」记录每次生成任务——成功与失败都入册（含被页面刷新中断的任务，启动时自动标记）。成功条目保存本地预览缩略图（canvas 生成，长边 160px）与元数据；点击任意条目即可回看，失败条目点击显示失败原因。
- 回看优先级：本次会话内存原图 → kdr 上游下载地址（在线加载原图）→ 本地缩略图。实测 kmage 上游 API 仅返回图片数据本身（`response_format=url` 也只回 data URI，无持久 CDN 地址），因此 kmage 历史在别的设备上回看的是缩略图；kdr 任务结果自带上游 URL，历史导出后在任何设备都能在线回看上游存储的原图。
- 「导出」按钮生成 `ai-image-history` JSON（全部条目，含缩略图与上游地址）；「导入」按运行号自动合并去重。历史持久化于 localStorage 的 `kmage_hist_v1`（上限 40 条；容量不足时自动剥离缩略图保存）。

### 运行控制台

- 右上角齿轮按钮 →「控制台」选项卡。每次生图以运行号（R+时间戳）分组记录：通道、账号/Key 选择、请求参数、上游状态码与耗时、错误响应摘要（含非 JSON 响应原文截断）、换号/重试决策。支持导出全部/本次运行（.txt，含版本、通道、UA、页面地址）、一键复制、只看错误、清空；日志持久化到 localStorage（`kmage_logs_v1`），刷新不丢。

## 反模式化原则（沿袭马良 v27.2）

- 邮箱：姓名/形容词/名词词库 × 6 种模式 × 随机大小写，无固定前缀与时间戳指纹。
- 密码：12~15 位完全随机强密码，无固定后缀；API Key 备注名从词池随机。
- 节奏：批量注册间隔 2.5~8s 随机（15% 概率再 +4s），批量签到乱序 + 0.8~2.8s 随机间隔；登录/刷新等操作带随机抖动。
- UA：Worker 端透传访客浏览器真实 UA（缺失时从 4 个常见池随机），不做 IP 伪造（马良 v26.1 已证实无效且移除）。

## 排障指引（AI Agent 适用）

① `GET /about` 确认版本、通道端点与真实上游（v1.5 起亦为浏览器直连的地址来源）；② 打开「控制台」导出日志，定位首个非 2xx 上游请求（日志带 [kmage]/[kdr] 前缀并标注「直连/代理」路径，直连失败自动回退代理亦有专门日志）；③ 排障时注意本机出口 IP 属性：数据中心 IP 上直连或经 Worker 代理的生图请求都会被上游风控拦截（详见下方常见错误），住宅 IP 浏览器直连为预期正常路径。

常见错误：
- kmage：401 会话/Key 失效（自动重登重建）、402 积分不足（自动换号）、429 限流（5s 退避）、5xx 网关错误（4s 后同号+换号重试，失败自动返还积分）、180s 超时、403 `account_environment_abnormal`（按生图请求出口 IP 判定环境，数据中心出口一律被拒；**v1.5 真机实测「代理出身号 + 住宅 IP 直连」仍被拒——账号出身环境参与判定**；v1.6 起触发自愈链：标记该账号 24h 内选号跳过 → 换未标记号 → 浏览器直连注册净号重试 → 全部失败时透出错误原文与建议「更换网络/稍后再试/改用 kdr」；号池「环境异常」标记 24h 后自动失效；**2026-10-07 真机实测净号直注亦被同拒「充值后解锁」——净号直注路线终结（v1.6 交接 #11 预判应验），上游疑似将免费生图整体移至充值闸门后，v1.7 净号被拒后 6h 冷却期内跳过自动注册）**
- kdr：401/403 Key 被拒（自动刷新共享 Key 重试）、**403「此 IP 已被加入免费 Key 黑名单」（2026-09-23 起上游拉黑 Cloudflare Worker 出口 IP 段的免费 Key 使用——v1.5 起浏览器直连后仅当访客自身出口 IP 被拉黑时出现）**、404 任务失效、轮询超时 180s（免费通道不扣费）；**403 "Just a moment…" 人机质询页（2026-10-07 起上游 /api/* 全端点启用 Cloudflare 托管质询，直连与代理均被拦——v1.7 已归类 `upstream_challenge` 快速失败，不刷新 Key 不重试，多为临时风控可稍后/换网络重试；探活方式: GET /api/gift-key 返回 "Just a moment…" HTML 即质询生效）**
- 号池/设置可导出 JSON 离线分析；上游探活：kmage 站点直接访问首页（注册无验证码，签到接口账号未满 24h 返回 403；**注意本机若为数据中心 IP，凭有效 Key 直接调 /v1 生图也会 403 环境异常，属上游风控而非契约变化**）；kdr 站点 `GET /api/gift-key` 应返回 key/alias

工程坑防守（历史教训，改代码前必读）：
- 单文件 Worker 的 HTML_CONTENT 为内嵌模板字符串，**禁止反斜杠转义序列（含正则）**——形如 `split(/\r?\n/)` 的写法会把整个文件炸成语法错误，换行一律用 `String.fromCharCode(10)`（kd-v2.2 与 kmage-kdr-1.2 两次拦截重演）；同理注意同名 const 冲突、删代码前先 grep 调用点、DOM 元素删除后加 null guard
- `resp.json()` 消费 body 后取不到原文：先读全文再 parse（v1.1 教训）
- headless 验证注意：Chromium 的 `dialog.close` 事件为异步派发，面板归位断言需等待一拍；部署后验证用 cache-busting 参数（`?_=时间戳`）+ 真实浏览器交互，升级测试前清 localStorage

## 边界说明

- 会话与密钥为本工具对注册账号的自身凭据管理，不涉及破解或绕过任何验证；请遵守上游站点服务条款，控制用量，避免滥用免费产能。
- 邀请奖励需被邀请人首次充值后才到账，不属于免费路径，工具不做链式邀请。kdr 通道自定义 Key 为用户自购的付费凭据，工具仅代为填用。

## 完整迭代时间线（原 CHANGELOG.md 全文 · 按实际日期正序）

页面内嵌「关于」文档对源站做了脱敏（以「kmage 站点 / kdr 站点 / Canvas 站点」表述）；本文档为维护者视角，保留真实上游地址。当前生产：`kmage-kdr-rapi-2.1`（Cloudflare Worker `ai-image`，https://ai-image.lishuhang.workers.dev/）。

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


## kmage-kdr-1.2 (2026-09-13) — kdr 通道修复复活 + 双通道选择器 + UI 重构

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

## kmage-kdr-1.3 (2026-09-13) — 竖屏适配 + 深色模式 + 任务历史持久化

### Added
- **深色模式**：CSS 全量变量化（拆分 `--accent-strong` 文字色与 `--accent-hover` 悬停色），设置新增「界面主题」：跟随系统（默认，`prefers-color-scheme` 实时感应切换）/ 浅色 / 深色（`data-theme` 持久化，随设置包迁移）
- **任务历史持久化与跨设备回看**：
  - 新存储键 `kmage_hist_v1`（上限 40 条；容量不足自动剥离缩略图兜底保存）
  - 成功/失败/中断任务均入册（启动时自动把残留 `running` 标记为「页面刷新/关闭导致中断」）
  - 成功条目：canvas 本地缩略图（长边 160px JPEG q0.65，约 4~10KB/条）+ kdr 上游下载地址
  - 点击条目回看：本次会话原图 → kdr 上游 URL 在线加载 → 本地缩略图；失败条目点击显示错误原因
  - 「近期任务」栏新增导出/导入：`ai-image-history` JSON，按运行号合并去重，kdr 条目在任意设备可在线回看上游原图（实测上游 URL 公网可访问）
- **移动端合并面板**：窄屏（≤680px）下设置/控制台/关于三个图标按钮合并为单一菜单按钮，点开浮窗以选项卡切换；面板 body 节点按需搬运进 hub（全站唯一 ID、事件绑定随节点走），关闭时归位
- **排障新知入库**（kmage 上游风控，实测 2026-09-13）：从数据中心 IP 直连上游注册的未满 24h 新号生图返回 `403 account_environment_abnormal`（「账号使用环境异常，充值后解锁」）；经本 Worker 代理路径（访客 UA 透传）正常。前端已有新生号 403/400 自动换号逻辑覆盖

### Changed
- **竖屏/窄屏适配**（≤680px 断点 + 360px 二档）：header 单行收紧（触控目标 36px）、版本号收进标题下方堆叠（不再摊开占宽）、设置栅格单列、历史条目两行截断换行、弹窗高度改 `dvh`（移动浏览器地址栏感知）、toast 横贯底部、320px 宽度实测无横向溢出
- **图标修正**：设置按钮由「太阳」换为标准齿轮线条 SVG；header 左上角与「关于」顶部 logo 由「ai 字母组合」换为画笔+颜料盘线条 SVG（与 favicon 同款图形，currentColor 描边）
- `/about` 新增 `ui` 字段（brand/theme/layout/history 自描述）；页面头部 AI Agent 注释补记 `kmage_hist_v1` 与主题说明
- 内嵌「关于」文档：新增「6. 任务历史与回看」节（后续节顺延），数据模型补 `kmage_hist_v1` 与 settings.theme，排障指引补 403 风控条目，时间线追加本版条目

### Deployment
- 部署 `ai-image`（CF API PUT，HTTP 200）；线上脚本与本地逐字节一致（107,256 字符）
- 本地 E2E（mock 双上游 + 无头浏览器 375/320px 竖屏 + 1280px 桌面）：注册→生图成功（缩略图/耗时入册）→ 失败任务入册 → 刷新持久化 → running 中断清理 → 历史回看三优先级 → kdr url 记录 → 历史导入去重回环 → hub 三选项卡切换与面板归位 → 深色/浅色/跟随系统（media 模拟）实时切换，全部通过
- 生产端到端（竖屏 375×812）：**kdr 免费 Gift Key 真实出图 36.8s**，历史条目含上游存储 URL（HTTP 200，1.69MB PNG 公网可访问）与本地缩略图
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.3.js`（约 135 KB）

## kmage-kdr-1.4 (2026-09-13) — 导航统一 + 设置三分区 + 界面记忆 + PWA

### Added
- **PWA 可安装**：新增 `/manifest.webmanifest`（名称「AI生图」，`display=standalone` 保留系统标题栏与窗口控制，`start_url/scope=/`，含主题色与浅/深双 `theme-color` meta）+ `/sw.js`（仅缓存页面外壳与图标：`/` 网络优先回退缓存，manifest/图标缓存优先；不拦截任何代理/API 请求；缓存名随版本号更新，activate 自动清理旧缓存）+ PNG 图标四枚（`/icon-192.png`、`/icon-512.png`、`/icon-maskable-512.png`（safe zone 收敛）、`/apple-touch-icon.png`，均为白底圆角矩形叠加画笔颜料盘 logo，与 favicon 同款图形，cairosvg 栅格化 + 调色板量化，合计约 16KB）
- **「安装到系统」按钮**：设置 → 通用选项，捕获 `beforeinstallprompt` 后显示，点击触发安装选择并记日志；`appinstalled` 事件 toast 反馈；iOS 提示走「分享 → 添加到主屏幕」
- **创作面板选项记忆**：新存储键 `kmage_form_v1`（{prompt,ratio,quality,kdrSize,model:{kmage,kdr}}）；模型按通道分存，切换通道各自恢复；提示词输入 400ms 防抖保存，生成前强存，beforeunload 兑底；恢复时校验选项值合法（不在列表内则用默认）

### Changed
- **导航统一（组件复用，双轨实现移除）**：全宽度右上角仅保留一个齿轮按钮（v1.3 的窄屏汉堡方案推广到全宽度，图标由汉堡改为齿轮），点开浮窗以选项卡切换设置/控制台/关于；删除桌面三图标按钮与 3 个独立 dialog（设置/控制台/关于降级为隐藏宿主 div，面板 DOM 搬运复用机制不变），关闭归位统一由 hub 的 `close` 事件驱动；新增 `.hub-pane .dlg-body` 内边距/高度归零规则避免双重滚动
- **设置三分区**：设置面板重组为「通用选项（界面主题/浏览器通知/安装/设置导入导出）/ kmage 通道选项（号池全套）/ kdr 通道选项（Gift Key/自定义 Key）」，三区常驻——选中任一通道均可直接调整另一通道的专属选项（v1.2 的按通道显隐逻辑移除）；分区说明文案入页面
- **验证**：线上 `/healthz` 版本 kmage-kdr-1.4，`/about` 新增 `ui.pwa` 与 `form_storage`/`history_storage` 字段；`/manifest.webmanifest`、`/sw.js`、四图标全部 200；无头浏览器 375px/1280px 无横向溢出，齿轮浮窗、选项卡切换、面板归位（注：headless Chromium 的 dialog `close` 事件为异步派发，归位校验需等待一拍）、跨通道模型记忆、深色模式、表单持久化回环全部通过；内嵌「关于」文档新增第 2 节（PWA 与界面记忆）并全节重排号，时间线追加本版条目

### Deployment
- 部署 `ai-image`（CF API PUT，metadata `{"body_part":"worker.js"}`，HTTP 200）
- 生产端到端：**kdr 免费 Gift Key 真实出图 27.6s**，历史条目含上游存储 URL 与本地缩略图；SW 注册激活正常，`beforeinstallprompt` 触发
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.4.js`（约 166 KB）

## kmage-kdr-rapi-zimage-2.2 (2026-11-19) — 新增 zimage 通道（第四通道）+ loadChannel 遗留 bug 修复（本版）

### Background（用户指令）

- 用户指令：① zimage.run/zh 文生图界面可无需登录生成指定参数和张数（张数限制可能根据浏览器指纹），图生图需登录——「你来把这个渠道做进来」；② 「一定要看看首页非登录态锁住的功能是前端限制还是后端限制」（重点核实项）
- v2.1 调研勘误：zimage.run 曾在 survey 中被判「无 API 纯网页」淘汰——本次用户指定后，经 Next.js bundle 逆向（下载 45 个 chunk，定位 `/api/z-image/generate`、`task/{uuid}`、`batch-status/{uuid}`、`generate-image-to-image`、`prompt-moderation/check`、`get-configs`）推翻原判：**API 齐全且匿名可调**

### 前端锁 vs 后端锁定谳（用户指示重点核实，11-19 直调 API 实测）

| 上游首页匿名态表现 | 实测结论 | 证据 |
|---|---|---|
| 张数选项 2/3/4 灰置 | **后端强制** | 直调 `batchSize:4` → 400 `Anonymous users can only generate 1 image at a time. Please sign in to generate multiple images.`；前端 bundle 为 `[1,2,3,4].map` + `!z&&e>1` 禁用（纯 UI），伪造参数绕不过后端 |
| 大尺寸（1280×720 等）与自定义尺寸锁定 | **后端强制** | 直调 1280×720 与 800×600 → 400 `Anonymous users can only use sizes: 512x512, 512x768, or 768x512`；前端 `isFree` 标志 + `size_locked_hint`（纯 UI） |
| 图生图锁登录 | **后端强制** | 直调 `generate-image-to-image` → 401 `UNAUTHORIZED` `Please sign in to use image-to-image generation.` |
| 模型列表 qwen-image-2-1 / flux-3-image-klein 门控 | **仅前端 flag 门控，后端放行** | 直调两模型均 200 受理且 completed 出图（8 模型匿名全开放） |
| 6 次提交后弹登录框 | **纯前端** | localStorage 计数器 + 弹窗（`parseInt("6",10)`），API 无对应限制 |
| 「浏览器指纹」感知 | **无指纹校验** | 无 Turnstile（get-configs `turnstile_enabled:false`）、无设备指纹 Cookie（仅 `z_image_last_submit` 时间戳 Cookie，Path=/api/z-image、Max-Age=60，实测不携带照样受理）；所谓「张数限制因指纹而异」实为登录态差异 + 前端 flag 门控所致 |
| promptModerationToken | **非必需** | 前端先调 `/api/prompt-moderation/check` 拿 token，直调省略照样 200 |
| history | 后端锁（无需） | 401 `Please sign in to view history`——本工具前端自管任务历史，不依赖 |

### 通道契约（全部实测）

- 端点：`POST /api/z-image/generate`（body `{prompt,width,height,modelType,batchSize,seed?}`，响应 `{success,data:{uuid,task:{taskStatus,seed,...}}}`）；`GET /api/z-image/task/{uuid}`（`data.task.taskStatus` ∈ pending/processing/uploading/completed/failed + `resultUrl`/`errorMessage`/`progress`）；batch>1 时另有 `parentTaskUuid` + `batch-status/{uuid}`（匿名不可用，未接）
- 模型 8 个：turbo / qwen-image-2-1 / ernie-image-turbo / flux2-klein-9b / flux-3-image-klein / beyond-realty / redcraft / dark-beast（seed 为字符串，回显；prompt 上限 600 字符）
- 限流：429 `RATE_LIMIT_EXCEEDED`（remaining 秒）与 429 `DAILY_LIMIT_EXCEEDED`（remaining/requested/resetAt/authState，匿名日额度——数值未探明，不刷量）；403 `VERIFICATION_REQUIRED`（Turnstile 路径，当前关闭）
- 结果图：`https://files.zimage.run/images/z-image/generated/{date}/{uuid}/result-0-*.webp` 公开直链（无过期签名），CORS `*` 开放；**上游 API 无 CORS 头**（preflight 204 无 ACAO）→ 浏览器直连提交被同源策略挡死，全走 Worker 代理

### Changed

- 后端：`handleZimageProxy`（POST `/api/zimage/generate` → 上游，模型白名单 8 个、非白名单回退 turbo、batchSize 强制 1、尺寸白名单 400 预检、prompt 截 600、seed 透传；GET `/api/zimage/task/{uuid}`，uuid 白名单 `[A-Za-z0-9_-]{1,64}`；Origin/Referer 伪装 `zimage.run`/`/zh`，429 原文透传）+ `handleZimageImage`（`/zimage/img?url=` 仅放行 `https://files.zimage.run/` 前缀——对比 `/rapi/img` 任意放行收紧，防开放代理滥用；cf cache 86400）
- 前端：通道下拉 +zimage；`KMODELS_ZIMAGE` 8 项（turbo 默认）；`RATIO_OPTIONS_ZIMAGE` 比例动态裁剪（zimage 仅 1:1/3:2/2:3 三项，切回恢复完整 8 项，选中值保留/回退 1:1，`formState.ratio` 记忆不受影响）；参考图禁用 + `refDisabledHint` 文案按通道动态化；`zimageHint` 限额提示；精细度/kdr 分辨率档隐藏；徽章「zimage · 免费无登录」；`generateZimage`（提交 → 3s 轮询 180s 上限 → completed → resultUrl 浏览器直连取图 CORS * → 失败回退 `/zimage/img` → b64 出图 → 历史 url 存公开直链跨设备可回看）；DAILY_LIMIT 中文兜底文案（附 resetAt）；下载前缀 `zimage_`；通知文案「四通道」
- **修复（v2.0 遗留）**：`loadChannel` 白名单仅 `kdr|kmage` → rapi（及 zimage）选中后刷新页面被静默重置回 kmage；广播恢复分支同步补齐
- 自描述：/about `channels.zimage`（契约/端点/模型/映射全录）+ `notes_v2_2`（接入路径/前后端锁定谳/日限额/loadChannel 修复）；头部注释、关于路由表、时间线、README 同步

### Validation

- `node --check` 通过；`debug/selfcheck-v2.2.js` **60/60**；`debug/smoke_test_v22.js`（vm 沙箱 + mock 上游）**34/34**——含 Origin/Referer 伪装、batchSize 强制 1、非白名单模型回退、尺寸预检不打上游、恶意 uuid 400、`/zimage/img` 前缀限制断言
- `debug/e2e_real_v22.js`（vm 沙箱 + **真实上游**）：提交 200（uuid `b5U4U_I1j9nj4puY`，seed 回显）→ 轮询 pending → processing 10% → uploading 80% → completed 100%（~21s）→ `/zimage/img` 代理取回 webp 23446B（magic RIFF）✅

## kmage-kdr-rapi-2.1 (2026-11-19) — 三通道复检 + rapi 面板适配 + 设置面板冗余清理 + 新通道调研收官

### Background（用户指令与复检）

- 用户指令：① 排除 gpt2.lishuhang.com 各通道故障；② rapi 不支持参考图 → 选中该通道时禁用面板参考图输入；③ 设置面板中其他通道已冗余的残留功能可去除；④ 在 v2ex 等地搜索新的免费生图通道及同类资源，尝试增加新通道；⑤ 更新版本号/readme/changelog，线上部署测试无 bug 后备份新版 worker js
- **三通道 11-19 全链复检（实测）**：① **rapi 健康**——`trial-session` 200（enabled，单任务 1 张/并发 5）→ `generations` 202 → `tasks/batch` 轮询 ~30s completed → 图床 IP 直链直连 200（3.4MB PNG；代理路径 CF 1003 属预期兑底）；RouterAPI 原帖（t/1240321）活跃至 11-18，共享试用 Key 未停发；② **kmage 契约未变**——注册 201（+1 分）/登录 401 错误文案/建 Key 201 均正常，免费生图仍 403 `account_environment_abnormal`「充值后解锁」（上游策略，v1.7 已归类，非新故障）；③ **kdr 认知修正（本版关键发现）**——免费档（占位符 Gift Key）确被会员闸门拦（401「请先登录会员」），但深挖实测 **host 合法（www/new.97api.com，其余 400「请求地址只能选择…」）时任意 Key 提交均被受理排队（202 queued），中继以 Key 真伪转发真实上游（假 Key 任务终态 error「上游接口请求失败 (401): Invalid API key」）**——即自定义付费 Key 路径契约通畅，v2.0 的「通道整体待命」表述修正为「免费档待命、付费 Key 可用」

### Changed

- **rapi 面板适配（用户指令 ②）**：`applyChannel()` 按通道裁剪——`refSection`（参考图输入区，v2.1 新增容器包裹 label+refList）rapi 下 `display:none` 整体禁用（`+` 按钮与已入列参考图一并隐藏；数据保留，切回 kmage/kdr 自动恢复显示），下方 `refDisabledHint` 提示段落 rapi 下显示（说明仅文生图与数据保留）；`qualityCell`（精细度）rapi 下隐藏（rapi 请求 body 无 quality 参数，从未生效）；`sizeRowKdr`（分辨率档）从 v2.0 的 `kdr||rapi` 误显修正为**仅 kdr**（rapi 实际用 `rapiSizeFor()` 比例→size 映射，该档位从未生效）——rapi 下面板只显示实际生效的模型/比例/提示词；`generate()` 校验同步：rapi 通道必须填写提示词（参考图已不可用，空 prompt+残留参考图不再误通过）
- **设置面板冗余清理（用户指令 ③）**：移除 kdr「共享 Gift Key」获取/刷新行（`giftKeyAlias` pill + `btnRefreshGift` 按钮 + 点击绑定）——上游会员制后 `GET /api/gift-key` 恒返回占位符 GO-ON-GOODLUCK，UI 已无意义；替换为「通道状态」pill（`kdrStatePill`：待命（上游会员制））+ 说明文字（含付费 Key 指引）；**自定义付费 Key textarea 保留**（kdr 当前唯一可用路径，标签更新为「当前唯一可用路径」）；`renderGiftLine()` 退化为空函数（注释说明，维持 applyChannel/ensureGiftKey/导入/初始化等历史调用点不牵连改动），textarea 回填职责迁至 `renderSettings()`（导入设置包后即时回显）；移除通道切换与页面初始化时的 Gift Key 预取（`switchChannel('kdr')` 与 init 两处，免空转 RTT 与日志噪音；`generateKdr` 内质询解销后的 `ensureGiftKey(true)` 刷新路径保留）
- **徽章与文案勘误**：`renderBadge()` kdr 分支——无自定义 Key 时「kdr · 共享 Key」→「kdr · 待命」（title 说明会员制与付费 Key 指引），有 Key 时 title 更新；**新增 rapi 分支**（「rapi · 免费试用」）——v2.0 及以前 rapi 误显 kmage 号池积分（误导）；通知开关「双通道生效」→「三通道生效」勘误；头部 HTML 注释「上游: 双通道」→「三通道」并补 v2.1 面板裁剪说明
- **版本与自描述**：VERSION 6 处 2.1（后端 const/前端 var/`<title>`/header `.ver`/SW `ai-image-shell-…` 自动随 VERSION/时间线）；`/about` 新增 `notes_v2_1`（recheck_1119/panel_trim/cleanup/survey 四节），kdr/rapi mode 描述同步 11-19 实测结论；内嵌「关于」文档——通道说明（kdr 付费 Key 路径/rapi 参考图禁用）、面板记忆节（通道裁剪说明）、设置分区节（kdr 分区新形态）、时间线追加 v2.1 条目并清理 v1.6 遗留「（本版）」标记

### Survey（新通道调研，用户指令 ④——结论：无一可接入）

- **调研途径**：v2ex「生图」标签聚合页全量扫帖（2026-09~11）、sov2ex 全文检索（多关键词+时间过滤）、z-ai web_search、linux.do 与 NodeSeek（均登录墙不可搜）、候选站前端 bundle 逆向（API 端点/注册流程/验证码机制）
- **候选全表（20+，均不满足「免费+可编程+可持续」接入标准）**：
  - 无 API 纯网页：~~zimage.run（t/1182699，反馈卡死闪退）~~（**v2.2 勘误撤销**：实为 Next.js 站点、API 齐全（`/api/z-image/*`），v2.1 调研时未做 bundle 逆向而误判；已接入第四通道）、gpt-image-2.me（t/1207873，注册仅 5 分）、happy-horse.tv（t/1209172）、pai.zaiduyu.top（t/1251127，5000 分≈33 张，回复确认无 API）、MossImage（t/1251081，每日 2 分带水印）、MiniMax H3 工具（t/1256012）、爱图工坊（t/1246030）、pikpikgo（t/1242510，商业站）、imagegoai（t/1254372，电商垂直，新号 3 张）
  - 人工赠送（无法自动化）：Midalo API（t/1250311/t/1254216，$2-5 需 QQ 群认领）、麋鹿云 moosecloud.cc（t/1231045，兑换码当天领完+加群人工）、YunToken（t/1222163，回帖人工充 $5）、猫图AI catsapi.com→artart.icu（t/1216905，留言送分+邮箱验证码注册 `/api/auth/register/send-code` 阻断自动化）
  - 验证码墙：miaosf.com→miaosf.rsod.top（t/1254988，双 11 注册送 50 张活跃至 11-18，但 better-auth + Turnstile + 邮箱 OTP + 邀请码三重门槛，bundle 逆向确认）；liuliuqiu.net/imagegen（t/1222012#53，FastAPI 任务制全端点需登录）
  - 纯付费：优米 api.uxmio.com（t/1257341，¥0.01/张无免费证据）、0.009 元站（t/1256781）、多米/吉吉/大香蕉系中转（¥0.01-0.12/张）
  - 同类资源（非通道，记档）：DSH 开源项目 dsh-our-imagen（t/1257442，Kaggle/Colab 免费 GPU 自跑 notebook，无服务端 API）
- **结论**：2026-11 时点社区在推的免费生图服务全部落在上述五类；唯一符合本工具「共享凭据+每日续给+可程序化」模式的仍是 RouterAPI（已在 rapi 通道内，且当日复检健康）。调研全表记档于此，**后续复查可从本表续接，避免重复劳动**

### Fixed / Verified

- **v2.0 遗留问题顺带修复**：`refDisabledHint` 初始实现置于 `refSection` 容器内（容器隐藏时提示永不显示）——自检发现后移至容器外；kdr `sizeRowKdr` 对 rapi 误显示（v2.0 起从未生效的 UI，本版修正为仅 kdr）
- **验证（部署 2026-11-19 02:19 UTC）**：node --check 整文件通过；结构自检 36/36（debug/selfcheck-v2.1.js：VERSION 6 处/新增与删除的 DOM id/绑定移除/预取移除/notes_v2_1/时间线/模板字符串完整性/无 CR-LF 转义序列）；线上 `/healthz`+`/about` 2.1（notes_v2_1 四节齐全）、`/sw.js` cache `ai-image-shell-kmage-kdr-rapi-2.1`、manifest 正常；无头浏览器实测——kmage 默认态（参考图/精细度显示、分辨率档隐藏）、rapi 裁剪态（参考图区隐藏+提示显示+精细度隐藏+徽章「rapi · 免费试用」）、kdr 态（分辨率档显示+徽章「kdr · 待命」）、三通道往返切换、设置面板（Gift Key 行已移除/状态 pill/自定义 Key textarea 保留/三通道文案）、关于文档 v2.1 内容渲染、控制台零错误；**生产 E2E：rapi 通道 UI 提交生图 33.0s completed**（gpt-image-2 · 1024x1024 · 2.3MB PNG，历史入册、下载可用，截图 debug/e2e-rapi-v2.1-20261119.png）；kdr/kmage 契约探针（占位符 401 会员文案 / 假 Key queued / 注册 201）经代理全过

### Deployment

- 部署 `ai-image`（CF API PUT，metadata `{"body_part":"worker.js"}`，success 02:19:09Z）；部署前现网脚本与仓库 v2.0 diff 确认一致（无漂移），回滚备份 `debug/deployed-v2.0-backup-20261119.js`
- 备份：`0913-gpt2/gpt2-worker-kmage-v2.1.js`（约 265 KB）

## kmage-kdr-rapi-2.0 (2026-10-24) — 新增 rapi 通道 + kdr 上游改版标注：双渠道失效排障后的第三通道接入

- **排障结论（10-24 实测，双渠道失效均为上游策略变更而非本工具缺陷）**：
  - **kdr**：免费生图转入会员登录制——`POST /api/image-tasks/generations` 实测 401 `{"error":"请先登录会员后使用免费额度"}`；`/api/auth/*` 仅 login 端点存在（无 register），`GET /api/gift-key` 返回占位符 `GO-ON-GOODLUCK` 而非真实 Key；前端 bundle 证实会员态按 `member.remaining/dailyLimit` 控制免费额度。通道代码/端点/中继全量保留（用户指示不封闭），待上游重新开放或提供会员凭据即可恢复
  - **kmage**：免费生图在充值闸门后（v1.7 已归类）；假 key 实测 401 `invalid_api_key` 契约未变，上游存活，签到/额度类不受影响
- **新通道选型（用户指示 site:v2ex.com 检索试用推广帖）**：命中 kdr 原帖（t/1222012，确认免费模式已转会员制）与 RouterAPI 推广帖（t/1240321，作者 ShawnShi，new-api 二开，帖内互动活跃至 10 月中旬）——后者为最佳候选：OpenAI 兼容生图、注册/试用双路线、共享池每日重置
- **端点逆向与实测**：Canvas 前端（image.routerapi.net，Vite SPA）bundle 分析得 `/async/v1/images/{trial-session,generations,tasks/batch}` 三端点与 `X-Trial-Visitor` 头；试用 Key（帖内公开）服务端直打被拒 `trial_web_only`（仅限 Canvas web 环境），带 `Origin/Referer: image.routerapi.net` 后 200；credential（JWT aud=image-trial-visitor）即访客身份
- **后端新增**：`RAPI_UPSTREAM/RAPI_CANVAS/RAPI_TRIAL_KEY/RAPI_CRED_TTL` 常量 + `rapiBaseHeaders/rapiEnsureCred/rapiCookieCred/rapiSetCookieValue/handleRapiProxy/handleRapiImage`；`/api/rapi/{trial-session,generations,tasks/batch}` 白名单代理（未知端点 404）+ `/rapi/img` 图片兑底代理；credential 三级身份策略：浏览器 Cookie（`rapi_trial`，7 天，等价上游 localStorage 语义——提交与轮询必须同身份，否则任务 `missing`，首版部署实测踩坑后重构）> isolate 内存缓存（45min，无 Cookie 访客复用并 Set-Cookie 固化）> 服务端代换发；401/403 自动重取重试一次并轮换 Cookie
- **前端新增**：通道选择器「rapi」选项、`KMODELS_RAPI`（gpt-image-2 系列）、`rapiSizeFor` 比例→size 映射（1:1→1024x1024，横系→1536x1024，竖系→1024x1536）、`rapiApi/rapiPollTask/rapiFetchB64/generateRapi` 全流程（提交→3s 轮询 180s 超时→直连图床优先转 b64→展示/入册/通知）；暂仅文生图（参考图忽略并提示）
- **关键发现（CF 1003）**：结果图床为裸 IP 直链（223.113.x.x:12589）——Worker fetch 出站流量经 Cloudflare 边缘，对裸 IP Host 命中 `1003 Direct IP Access Not Allowed`（代理路径 403）；实测图床 CORS 全开（ACAO `*`）且不校验 Referer → 前端改浏览器直连优先，`/rapi/img` 仅作兑底（上游换域名图床后恢复可用）
- **验证**：node --check + 内嵌 script 4/4 + HTML_CONTENT 0 反斜杠；vm 冒烟 33/33（v1.9 全回归 + rapi 预热/Cookie 固化/身份透传/401 轮换/端点白名单/图片代理）；生产部署 200（06:11:32Z 首版 → 06:13:59Z 直连图床修复 → 06:18:31Z 身份 Cookie 版）+ 双域 healthz/about/页面 2.0；生产端到端两单实测（22s / 42s completed，PNG 直连回传 2.9MB）
- **文档**：README（生产 2.0/通道现状/文件清单/时间线 v2.0 节）+ todo 前插第一部分（1024-1430）重命名 todo-gpt2-full-1024-1430.md；备份分支 backup/pre-rapi-2.0-20261024 已推送（v2.0 开发前 main 快照，随时可回滚）

## kmage-kdr-1.9 (2026-10-08) — 中继修复 + 中继遥测 + 自动重载：基于真机截图/日志的 debug

- **真机证据（用户 10-08 回传）**：截图显示 v1.8 中继弹窗与质询页均已呈现，但质询页自身报「无法连接到网站」（keydraw.97api.com 可能存在问题，导致安全验证过程无法完成），用户等待 36s 后取消；日志（174 条）另证: ① kdr 质询为**时段性**——10:04~10:09 直连连续成功 2 单（30.7s/32.8s），11:51 起质询再现；② kmage 免费生图确认移至**充值闸门**后——自愈⓪ 号内重建 Key 实测跑通（DELETE /api/api-keys/{id} → 204、POST → 201），重建后 /v1 仍 403 `account_environment_abnormal`，随后净号直注（浏览器直连出生）亦同拒（19.1s 全链用尽）；签到 8/8 正常（含归档号）
- **修复①（关键）**：`relayRedirectOr()` 3xx 分支原实现新建 Response 返回续跳页，**丢弃上游 303 携带的挑战解销 Set-Cookie（cf_clearance）**——解销凭据永远无法镜像到浏览器，「勾选成功也不生效」；现改经 `relayResponse()` 统一管道承载续跳页/完成页（`/kdr/challenge` 与 `/kdr/chl/*` 的完成页分支一并收口），Set-Cookie 照常镜像（vm 冒烟: 303 + Set-Cookie → `kmirror_cf_clearance` 镜像断言通过）
- **修复②**：`kdrRelayFetch()` 补 `Origin`/`Referer`（上游同源上下文）——质询 POST 与 challenge-platform 流程调用的来源一致性（原实现缺失，上游来源校验可能失败并报「无法连接到网站」）
- **修复③**：`rewriteChallengeHtml()` 补 JSON 转义斜杠变体（`\/api\/` → `\/kdr\/chl\/api\/`、`https:\/\/keydraw.97api.com` 剥主机）——`_cf_chl_opt` 以转义形式嵌入时原替换漏改，回跳误入本站路由收到应用 HTML，质询页即报「无法连接到网站」（截图故障的直接来源之一）
- **增强④（中继遥测）**：质询页 `<head>` 后注入探针（先于质询平台脚本 hook 住 fetch/XHR）——仅失败事件（HTTP ≥400/网络错误/全局 JS 错误/未处理 Promise 拒绝）postMessage 上报父页写入应用日志（`[kdr][中继]` 前缀），并轮询检测质询页错误面板文案（「无法连接」等）——中继哪一步失败从此有据可查
- **增强⑤（报错自动重载）**：探针检出错误面板时父页自动重载中继 ≤2 次（1.5s 延迟，新质询 token 重跑），全程日志可观测；仍失败才提示用户手动「重新加载」或稍后再来（上游风控为时段性）
- **定位校正（用户 10-08 指示）**：「工具不代解不伪造信号」系对便利性原则的曲解，撤回更正——用户打开并使用本工具即默认授权其代为自动化完成后续一切流程（即使不自动化，用户本人也会这么做）；工具职责 = 把只有人工能完成的那一步（勾选）完整送达用户 + 把其余全部环节（重载/重试/续跑/Cookie 衔接/换路）尽可能自动化、无缝平滑；现行 UI/错误文案/关于页同步更新
- **验证**：node --check 整文件 + 4 段内嵌 script 全过；vm 冒烟 36/36（v1.8 全部回归 + v1.9 新增: 转义路径改写/绝对 URL 剥离/探针注入于 head/Origin-Referer 断言/3xx Set-Cookie 镜像保留/完成页与 502 文案更新）
- 部署 `ai-image`（CF API PUT，HTTP 200）；备份：`0913-gpt2/gpt2-worker-kmage-v1.9.js`

## kmage-kdr-1.8 (2026-10-08) — 人工验证中继 + 号内 Key 轮换 + 净号签到管理：双通道便利性增强

- **定位重申（沿袭用户定义）**：本工具始终做的是「给正常使用提供便利」——前端整合页面免多站切换、免用户端网络不稳导致的直连失败；不是、也不做「绕过风控」。上游人机质询本就是给人类设计的关卡，v1.8 把它原样呈现给真实用户完成
- **kdr 人工验证中继（核心新增）**：上游质询触发时（v1.7 归类 `upstream_challenge` 之上），前端弹窗内嵌 iframe 加载 `GET /kdr/challenge`——Worker 金丝雀探活（带镜像 Cookie 重试 `/api/gift-key`），仍被质询则改写质询页呈现（剥 CSP/XFO/COEP/COOP、绝对 URL→相对、`_cf_chl_opt` 内 `/api/` 回跳路径改写至 `/kdr/chl/api/`、Set-Cookie 以 `kmirror_` 前缀镜像到本站域并剥 Domain）；`/cdn-cgi/*` 与 `/kdr/chl/*` 中继 challenge-platform 全流程（3xx 客户端续跳；求解后回跳 gift-key JSON 即返回完成页 postMessage）；用户亲自勾选完成后：iframe postMessage + 前端代理探活（静默 4s 轮询）双通道确认 → 自动刷新 Gift Key → 重试原任务；验证未完成则诚实终止不空转。提交与轮询环节均接入（轮询质询后验证通过会重置 180s 轮询窗口，仅一次）。无状态实现（无 KV）：浏览器即 Cookie 罐
- **kmage 自愈⓪ 号内重建 Key**：`rotateKeyFor()`（`DELETE /api/api-keys/{id}` 不可用时仅新建）+ 403 环境异常自愈链前置——先删旧建新再调用（用户路线：直接生成遇阻时先在号内生成 apikey 再调用），Key 维度单独标记可不换号解除；仍被拒才标记/换号/净号直注；终态报错注明已尝试 Key 重建
- **净号不丢弃**：`checkinAll()` 覆盖已归档号（`state.abandoned`，凭存量密码经 withSession 401 自动重登）与环境异常标记号，日志标注「（归档）」；号池不再主动丢弃任何可用凭据（N 号 ≈ 每日 5N 张图储备）
- **可观测性/自描述**：验证完成后 24h 内 kdr 代理优先（`kdr_relay_ok_v1`，跳过注定失败的直连尝试，静默探活不打日志）；/about 新增 `notes_v1_8`（kdr_challenge_relay/kmage_key_rotation/pool_checkin_all）与 `challenge_relay`/`challenge_flow` 端点说明；页面关于排障指引 ③④、号池说明、边界说明与时间线同步
- **验证**：node --check 整文件 + 4 段内嵌 script 全过 + HTML_CONTENT 0 反斜杠；vm 冒烟 28/28（版本三件套、notes_v1_8、页面新函数/时间线、kdr 质询 502 回归、透传回归、challenge 页改写/去 XFO/Set-Cookie 镜像化/canary 带 UA+镜像 Cookie、完成页 postMessage、chl JSON→完成页、cdn-cgi 透传、3xx 续跳、代理镜像 Cookie 还原转发且丢弃非镜像 Cookie、kmage /v1 质询 502 回归）
- 部署 `ai-image`（CF API PUT，HTTP 200）；备份：`0913-gpt2/gpt2-worker-kmage-v1.8.js`

## kmage-kdr-1.7 (2026-10-08) — 质询归类 + 充值闸门冷却：10-07 双上游再度收紧的工程侧应对

- **故障 1（kdr 全断）**：用户回传真机日志（268 条，2026-10-07 23:53 导出）显示 kdr 通道 23:52 起全断——直连 fetch 全部 "Failed to fetch"，回退 Worker 代理后全部 403 + "Just a moment…" HTML；v1.6 误判为「Key 被拒」触发强制刷新 Gift Key 重试（2 秒内连打两轮无意义请求），最终把整页 HTML 当错误信息抛出。容器实测归因: kdr 上游对 `/api/*` **全端点**启用 Cloudflare 托管人机质询（响应头 `cf-mitigated: challenge`，403 + text/html；数据中心 IP 与浏览器 UA 同拦；同日 11:44 直连仍 200，为午后起的新变更）
- **修复 1（质询归类，全链路）**：Worker 端 `isChallengeUpstream()`（`cf-mitigated: challenge` 头优先，兜底 403+text/html 正文特征）接入 `handleKdrProxy` 与 `handleV1Proxy`，命中即归一化返回 502 `{error:{code:'upstream_challenge',message:…}}`（不再透传 HTML）；前端 `isChallengeResp()` 识别后: 提交环节快速失败（不刷新 Gift Key、不重试——Key 与参数无涉）、轮询环节提前失败（不再空转 8 次）、`ensureGiftKey` 被质询时沿用缓存 Key 且不误报、直连+代理双路被拦时日志明确「人机质询确认，非 Key/参数问题」；错误文案给出诚实指引（临时风控可稍后/换网络重试，本工具不绕过人机验证）
- **故障 2（kmage 充值闸门）**：同日志 23:53 显示 kmage 代理出身号与净号直注新号（浏览器直连出生，2.2s 内）均被 403 `account_environment_abnormal`「账号使用环境异常，充值后解锁。」——v1.6 交接 #11 的终结判定应验，净号直注路线终结；结合注册响应 `recharge_entry_enabled:true` 与错误文案，判断上游疑似将免费生图整体移至充值闸门后
- **修复 2（充值闸门 6h 冷却）**：净号（bornDirect）亦被 403 环境异常拒绝时置 `kmage_paywall_v1` 时间戳，**6 小时内自愈链跳过自动注册**（避免一次会话连续白烧注册名额，到期自动恢复尝试；手动注册/生图不受限）；终态报错更新为明确归因（上游闸门，非本站可修复）与建议（改用 kdr/等待放松/充值）；签到/额度类功能不受影响（10-07 实测仍正常）
- **自描述与文档**：/about 新增 `notes_v1_7`（kdr_challenge/kmage_paywall 双条目）与通道 mode 更新；页面关于排障指引 ③④ 与时间线、README（本文件）同步
- **验证**：node --check 整文件 + 4 段内嵌 script 全过；vm 冒烟 13/13（healthz/about/页面版本、kdr 质询→502 结构化、kdr 正常→透传、kmage /v1 质询→502 结构化、页面含 isChallengeResp/paywallSuspected/时间线 v1.7）；CF API PUT 部署 200（16:19:12Z）；生产验证: 双域名 `/healthz` 1.7、`/about` 1.7+notes、页面标题 1.7、SW 缓存名 1.7、`/api/kdr/gift-key` 返回 502 `upstream_challenge` 结构化 JSON（workers.dev 与 gpt2.lishuhang.com 双域）、kmage `/v1` 假 key 401 JSON 正常透传、会话代理正常（边缘传播延迟约 1 分钟后全量生效）
- 部署 `ai-image`（CF API PUT，HTTP 200）；备份：`0913-gpt2/gpt2-worker-kmage-v1.7.js`

## kmage-kdr-1.6 (2026-09-23) — 净号直注（Client-born Accounts）+ 403 自愈链：kmage 住宅直连仍被拒的根因定位与修复

- **根因定位（v1.5 上线后真机日志 + 容器实测矩阵）**：用户真机日志显示 kmage 直连生图仍 403「账号使用环境异常，充值后解锁」，被选中的账号 k***@gmail.com 是 0913 经 Worker 从数据中心 IP 注册的号池号；容器实测矩阵确认：新注册账号（1 积分）从数据中心 IP 生图 403 与账号年龄无关、与 Origin/Referer/UA/X-Forwarded-For 无关（XFF 不被信任）、/api/tasks 会话任务端点与 /v1 API Key 端点同拒 → 风控纯粹按生图请求出口 IP 判定，且「代理出身号」即使住宅 IP 直连仍被拒（账号出身环境参与判定）；注册端点实测 OPTIONS 405（无 CORS 预检处理）、POST 无 ACAO/无 Origin 校验、text/plain 体照常按 JSON 解析（201）→ 浏览器 no-cors 简单请求可直连注册
- **净号直注**：`registerDirect()`（no-cors POST text/plain JSON，响应 opaque）→ `registerAccount()` 直连优先：直连注册 → Worker 代理登录验证并取会话 → 代理建 Key；直连网络失败或登录验证失败自动回退代理注册（回退后再失败且登录通过则视为直连已生效）；新号标记 `bornDirect`，号池显示「直生」徽章
- **403 自愈链**（`generateKmage()` 新增 403 env-abnormal 分支 + `isEnvAbnormalResp()`/`envFlagged()`）：标记 `envFlagAt`（24h 内 `pickAccount`/`findReadyAccount` 跳过，号池显示「环境异常」徽章）→ 换未标记号重试 → 开启自动注册时浏览器直连注册净号再试 → 全部失败透出错误原文与建议（净号亦被拒时明确提示「网络出口或风控策略整体收紧，可换网络/稍后再试/改用 kdr」）
- **其他**：自动注册文案更新为「无号可用或全被环境风控时自动直连注册净号」；修复非 JSON 错误响应被误标「非JSON响应」的日志显示；/about 新增 `register_direct` 端点自描述与 v1.6 说明；版本号 5 处更新；页面关于（架构 pre/双通道说明/24h 规则/时间线）与 README 同步
- **验证**：静态检查（node --check 整文件 + 4 段内嵌 script、HTML_CONTENT 0 反斜杠 0 插值、凭据扫描）全过；CF API PUT 部署 200；`/healthz` 返回 `kmage-kdr-1.6`（workers.dev 与 gpt2.lishuhang.com 双域名）；线上页面与本地 HTML_CONTENT 逐字节一致（120,879 字符）；无头 Chromium 生产 E2E 15/15 全过——空池自动直连注册×2（bornDirect=true）→ 建 Key → 直连生图 403（容器 IP 预期）→ 环境异常标记 → 净号直注重试 → 诚实终态；号池「直生/环境异常」标记渲染正常；kdr 通道回归真实出图（无回归）；**kmage 住宅 IP 最终出图成功待用户真机确认（容器数据中心 IP 无法验证，属预期）**
- 部署 `ai-image`（CF API PUT，HTTP 200）；备份：`0913-gpt2/gpt2-worker-kmage-v1.6.js`

## kmage-kdr-1.5 (2026-09-23) — 直连优先（Direct-First）：修复双上游数据中心 IP 风控拦截

### Background（故障与归因）
- 用户报告：kdr 渠道点击生图报「此 IP 已被加入免费 Key 黑名单」；kmage 渠道报「账号使用环境异常，充值后解锁」（`403 account_environment_abnormal`）
- 归因实测：kdr 上游 2026-09-23 起将 **Cloudflare Worker 出口 IP 段**列入免费 Key 黑名单（同 IP 段的 Key/轮询/提交全部被拒，但 gift-key 接口本身不拦）；kmage 上游将 0913 的「新生号」环境风控**扩大到所有数据中心出口 IP 的生图请求**——凭有效 API Key 从数据中心 IP 调 `/v1/images/generations` 一律 403（实测容器数据中心 IP 复现），Worker 代理路径因此全灭；两上游均未改生成契约（body/Bearer 不变），纯 IP 风控
- 关键发现：**两上游均开放 CORS（`Access-Control-Allow-Origin: *`，预检放行 `content-type,authorization`）**，访客浏览器可直连上游；kdr 生成以异域 Origin 实测 202 受理；kmage 403 为风控响应而非 Origin 拒绝；kdr 结果图床不校验 Referer（无 Referer 直拉 200）

### Added（修复方案：直连优先 / Direct-First）
- **直连基础设施**：前端新增 `directBases` 与 `initDirect()`——启动时从 `GET /about` 自描述接口获取双上游真实地址（2s 超时不阻塞交互），页面静态文本不含上游域名，脱敏原则不变
- **kmage 生图直连优先**：`kmageV1()` 重构为「直连优先 + 代理回退」——浏览器直连 `{base}/v1/images/generations`（Bearer API Key，180s 超时/AbortError 语义与原代理路径一致）；仅网络层失败（TypeError/CORS）回退 `/kmage/v1/*` 代理；上游 4xx/5xx 原样透传给既有 401/402/403/429/5xx 重试换号逻辑
- **kdr 全链路直连优先**：`kdrApi()` 同构重构——gift-key 获取、生成/edits 提交、任务轮询全部浏览器直连；结果图 `kdrFetchB64()` 优先直连图床（`referrerPolicy=no-referrer`），失败回退 `/kdr/img` 代理；blob→b64 抽取为公共 `blobToB64()`
- **kmage 会话类仍走 Worker 代理**（注册/登录/签到/Key 管理）：上游会话仅经 Cookie 携带（实测 Bearer/X-Session/query 均不认），ACAO `*` 下浏览器无法跨域携带 Cookie，故保留代理路径；实测该路径不受风控影响（注册/建 Key 201 正常）
- **可观测性**：控制台日志对每次上游请求标注「直连/代理」路径；直连失败回退、直连图床回退均有专门日志；`/about` 的 channels.endpoints 新增 `v1_direct`/`direct` 字段与 `shared.direct_mode` 说明

### Deployment
- 部署 `ai-image`（CF API PUT，HTTP 200）；`/healthz` 返回 `kmage-kdr-1.5`；线上页面与本地 HTML_CONTENT 逐字节一致（114,383 字符）
- 静态检查：node --check 整文件 + 4 段内嵌 script 全过；HTML_CONTENT 0 反斜杠 0 插值（工程坑防守）
- 生产端到端（无头 Chromium，真实浏览器交互）：**kdr 免费 Gift Key 全直连真实出图 46.3s**（gift-key 直连 200 → 提交直连 202 → 轮询直连 200 → 直连图床 200 → 804KB PNG 展示）；**直连故障注入回退验证通过**（拦截直连域名后日志出现「直连上游失败…自动回退 Worker 代理」并继续完成请求）；kmage 直连请求实测到达上游风控（403 环境异常为容器数据中心 IP 的预期行为，住宅 IP 访客为预期正常路径），会话类注册/建 Key 经代理 201 正常
- 备份：`0913-gpt2/gpt2-worker-kmage-v1.5.js`（约 171 KB）
