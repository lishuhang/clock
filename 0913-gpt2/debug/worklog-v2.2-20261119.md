# v2.2 工作日志（kmage-kdr-rapi-zimage-2.2）— 2026-11-19

## 任务

- 用户指令：https://zimage.run/zh 文生图界面可无需登录生成指定参数和张数（张数限制可能根据浏览器指纹）（图生图需登录），「你来把这个渠道做进来」
- 追加指令（过程中）：「一定要看看首页非登录态锁住的功能是前端限制还是后端限制」

## 调研与逆向（01:45~03:10 UTC）

- 站点结构：zimage.run 为 Next.js 站点（`/_next/static/chunks/*.js` 45 个 chunk），标题「Z-Image - 无需登录的免费AI图片生成器」，图床 files.zimage.run
- bundle 逆向命中端点：
  - `POST /api/z-image/generate`（t2i，body `{prompt,width,height,modelType,batchSize,seed?,promptModerationToken?}`）
  - `POST /api/z-image/generate-image-to-image`（img2img，另带 `sourceImageUrl`/`sourceImageModerationToken`）
  - `GET /api/z-image/task/{uuid}`（单任务轮询，`data.task.taskStatus`）与 `GET /api/z-image/batch-status/{parentTaskUuid}`（批次）
  - `POST /api/prompt-moderation/check`（token）、`POST /api/config/get-configs`（flags）、`GET /api/z-image/history`（登录）
- 前端逻辑要点：模型 8 个（`["turbo","qwen-image-2-1","ernie-image-turbo","flux2-klein-9b","flux-3-image-klein","beyond-realty","redcraft","dark-beast"]`，qwen/flux-3 受 server flag 门控）；尺寸预设含 `isFree` 标志（免费=512×512/768×512/512×768 三档）；张数 `[1,2,3,4]` 匿名 `!z&&e>1` 禁用；localStorage 6 次提交计数后弹登录框；错误分类 429 RATE_LIMIT（remaining）/429 DAILY_LIMIT（remaining/requested/resetAt）/403 VERIFICATION_REQUIRED；prompt 上限 600；指纹相关代码零命中（仅图标名）

## 实测（probe 脚本 /home/z/my-project/scripts/zimage_probe{1,2,3}.py）

- 基线：无登录直调 generate（bs=1 turbo 512×512，无 moderation token）→ 200，`data.uuid` + task 轮询 ~20s completed，结果 webp 公开直链可下载
- **前端锁 vs 后端锁（用户指示重点）**：
  - bs=4 → 400「Anonymous users can only generate 1 image at a time」→ **后端锁**
  - 1280×720 / 800×600 → 400「Anonymous users can only use sizes: 512x512, 512x768, or 768x512」→ **后端锁**
  - img2img → 401「Please sign in to use image-to-image generation」→ **后端锁**
  - qwen-image-2-1 / flux-3-image-klein → 200 且 completed 出图 → 前端 flag 门控，**后端放行（8 模型全开）**
  - history → 401（登录）→ 后端锁（本工具不依赖）
  - 匿名无 Turnstile（get-configs `turnstile_enabled:false`）、无设备指纹 Cookie（仅 `z_image_last_submit` 时间戳 Cookie，Path=/api/z-image Max-Age=60，不携带照样受理；60s 窗口内连发两单均 200，RATE_LIMIT 当前未强制）——用户感知的「指纹差异」实为登录态 + 前端 flag 门控
  - seed 参数生效（回显 "12345"）
- CORS：`POST /api/z-image/generate` 携带外部 Origin 也 200（服务端不查 Origin），但响应无 ACAO、preflight OPTIONS 204 无 CORS 头 → **浏览器直连被同源策略挡死，必须 Worker 代理**（与 rapi 同理）
- 图床：files.zimage.run 域名图床（无 CF 1003 裸 IP 问题），`Access-Control-Allow-Origin: *` → 浏览器直连取图可行，代理作兑底

## 实现（gpt2-worker-kmage-v2.2.js，3936 行）

- 后端：`ZIMAGE_UPSTREAM`/`ZIMAGE_FILES_PREFIX` 常量；`handleZimageProxy`（POST `/api/zimage/generate`：模型白名单 8 个（非白名单回退 turbo）、batchSize 强制 1、尺寸白名单 400 预检、prompt 截 600、seed 透传；GET `/api/zimage/task/{uuid}`：uuid 白名单 `[A-Za-z0-9_-]{1,64}`；Origin/Referer 伪装 zimage.run/zh + pickUA；上游 status/JSON 透传）+ `handleZimageImage`（`/zimage/img?url=` 仅放行 files.zimage.run 前缀 + cf cache 86400）；路由分发、/healthz（zimage_upstream + channels 四通道）、/about（name 四通道、channels.zimage 全契约、notes_v2_2）
- 前端：通道下拉 +zimage；KMODELS_ZIMAGE 8 项 + ZIMAGE_DEFAULT_MODEL；`zimageSizeFor`（1:1→512×512、3:2→768×512、2:3→512×768）；`RATIO_OPTIONS_ZIMAGE` + `applyRatioOptions`（zimage 仅 3 档、切回恢复完整 8 项、选中值保留/回退 1:1）；applyChannel 裁剪（refSection/refDisabledHint 文案动态化、zimageHint、qualityCell 隐藏、btnGenerate 文案）；renderBadge zimage 分支；`zimageApi`/`zimagePollTask`（3s/180s/连续 8 次非 2xx 放弃）/`zimageFetchB64`（直连优先代理兑底）/`generateZimage`（DAILY_LIMIT 中文兜底含 resetAt、历史 url 存公开直链）；generate 入口分派 + 提示词必填（zimage 同 rapi）；histEntry.size 含尺寸；下载前缀 zimage_；通知「四通道」；formState.model 补 rapi/zimage 键
- **修复 v2.0 遗留 bug**：`loadChannel` 白名单 `kdr|kmage` → 补 `rapi|zimage`（此前 rapi 选中后刷新被静默重置回 kmage）；广播恢复分支同步
- 文档：头部注释（通道块/架构路由/v2.2 changelog）、关于路由表、时间线 v2.2 节（v2.1 去本版标记 + survey 勘误回注）、README（标题/通道条目/v2.2 摘要/文件清单/架构速览/前端数据/生图/使用指引/survey 勘误/时间线 v2.2 节）

## 校验（本地四关全过）

1. `node --check` ✅
2. `debug/selfcheck-v2.2.js` 结构自检 **60/60** ✅
3. `debug/smoke_test_v22.js` vm 冒烟（mock 上游）**34/34** ✅——含 Origin/Referer 伪装、batchSize=99 强制 1、EVIL-MODEL 回退 turbo、1280×720 预检 400 不打上游、恶意 uuid 400、`/zimage/img` 拒绝 evil.com、seed 透传断言（中途修了测试桩两处自身 bug：mock Headers 不接受 Headers 实例、未 mock uuid 的 404 语义）
4. `debug/e2e_real_v22.js` **真实上游 E2E** ✅——vm 加载 worker + Node 真网络：提交 200（uuid `b5U4U_I1j9nj4puY`，seed 回显 1132538965）→ 轮询 pending→processing 10%→uploading 80%→completed 100%（~21s）→ `/zimage/img` 代理取回 webp 23446B（RIFF magic）✅

## 部署（阻塞）

- 沙箱无 CF 凭据：环境变量空；`scripts/.cruise_secrets.env` 不在（旧工作区文件未随克隆恢复）；worklog-v2.1 中 token 截断（`cfat_LpiT…Vciwe405d570`）；更旧 cfat_ token 已失效（todo 文档 #2057 记录 9109 Invalid）
- 已备 `debug/deploy_v22.sh`（CF API multipart PUT + 双域 /healthz 版本验证 + 部署前现网版本记录），凭据到位后一条命令完成
- 待用户提供 CF_TOKEN + CF_ACC 后执行：部署 → 双域验证 → 无头浏览器四通道交互测试 → 生产 E2E zimage 生图截图

## 环境备忘

- 逆向素材与 probe 脚本：`/home/z/my-project/scripts/zimage_probe{1,2,3}.py`（zimage bundle 在 /tmp/zim/，沙箱回收即失效，结论已全部落入本日志与 README）
- 上游匿名日额度数值未探明（不刷量探测）；DAILY_LIMIT 429 兜底文案已就位
