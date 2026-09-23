# 0913-gpt2 — AI生图 Worker（kmage + kdr 双通道）

> **当前生产：`kmage-kdr-1.5`，部署于 `https://ai-image.lishuhang.workers.dev/`（Cloudflare Worker 名 `ai-image`）**
>
> 本目录自包含。任何 AI Agent 访问本页/本仓库时：可将 `gpt2-worker-kmage-v1.5.js` 整体作为 skill 调用（单文件 Worker，后端代理 + 内嵌前端，无外部依赖）；排障请先读本文档与文件头部注释，线上自描述接口 `GET /about`、健康检查 `GET /healthz`；页面内右上角齿轮按钮 →「关于」选项卡含同样的自包含文档（对外脱敏版）与完整迭代时间线，与本文档对齐、两头互相补充。
>
> **本文档已合并原 `CHANGELOG.md`**（完整迭代时间线见文末，按实际日期正序，从马良渠道至今）；任务交接文档见 `todo-gpt2-full-0923-2125.md`（0722~0819 历史交接全文 + 0913/0923 增量交接日志，由原 `TODO-full.md` 逐次合并重命名而来）。

- **最后更新**：2026-09-23（GMT+8）
- **通道**：
  - **kmage**（默认）：上游 https://image.dddd.zone（kmage · AI 视觉工作台）官方 OpenAI 兼容 API。注册送 1 分；签到 +5 分/天/号（注册满 24h 开放）；1 积分 = 1 张图，失败自动返还；号池 N 号 ≈ 5N 张/天。站内老虎机为娱乐玩法（理论返还率 95.88%，负期望），本工具不对其进行自动化，避免把签到攒的积分赌没
  - **kdr**：上游 https://keydraw.97api.com（Keydraw/Draw Studio）。免费共享 Gift Key（`GET /api/gift-key` 自动轮换），2026-09 新契约：`key`/`host` 放请求 body，任务制（提交→轮询→图床 URL）；免费档固定 主线路 + gpt-image-2 + 1K；可选自定义付费 Key 解锁全部模型与 2K/4K
- **v1.5 直连优先（2026-09-23 起，重要）**：两上游已将数据中心出口 IP 拉黑（kdr：免费 Key 黑名单；kmage：生图环境异常），**生图类请求由访客浏览器直连上游**（住宅 IP + 真实 UA；两上游均开放 `Access-Control-Allow-Origin: *`；直连地址运行时经 `GET /about` 获取，脱敏原则不变），Worker 代理降级为直连网络失败时的自动回退；kmage 会话类操作（Cookie 会话，无法跨域携带）不受风控影响，仍走 Worker 代理

## 文件清单

| 文件 | 说明 |
|---|---|
| `gpt2-worker-kmage-v1.5.js` | **当前生产版本**。单文件 Cloudflare Worker（Service Worker 格式），在 1.4 基础上新增直连优先（Direct-First）：生图类请求（kmage /v1 生图、kdr /api 全部、kdr 结果图）由访客浏览器直连上游，Worker 代理降级为网络失败时的自动回退；修复 2026-09-23 双上游拉黑数据中心出口 IP 导致的双通道生图全拒 |
| `gpt2-worker-kmage-v1.4.js` | v1.4 留档（导航统一 + 设置三分区 + 界面记忆 + PWA） |
| `gpt2-worker-kdr-v1.2.js` | 旧 kdr 独立版留档（上游 2026-09 改版后瘫死，已被 kmage-kdr-1.2 修复复活取代） |
| `gpt2-worker-kdr-v1.1.js` | 旧 kdr 独立版留档（日额度计数 + 多自定义 Key 轮换） |
| `gpt2-worker-kdr-v1.0.js` | 旧 kdr 独立版留档（单通道 + Gift Key 自动轮换） |
|  `todo-gpt2-full-0923-2125.md` | 任务交接文档（0722~0819 历史交接全文 + 0913/0923 增量交接日志，每次增量后按 GMT+8 完工时间重命名） |

> 原 `CHANGELOG.md` 已全文并入本文件文末「完整迭代时间线」节；原 `TODO-full.md` 已与各次增量交接日志合并为 todo 文件。更早的 kmage v1.0~v1.3 与马良 v27.2 留档已随仓库瘦身移除（变更细节见时间线与 todo 文档历史部分）。

## 架构速览（kmage-kdr-1.5）

**路由**（Cloudflare Worker `ai-image`，无状态，无 KV 依赖）：

```
/                     页面（HTML+CSS+JS 全内嵌，无外部资源；favicon 与 logo 为内联 SVG）
/manifest.webmanifest PWA 清单（名称「AI生图」，display=standalone 保留系统标题栏）
/sw.js                Service Worker（仅缓存页面外壳与图标，版本随发布更新，不拦代理/API）
/icon-192.png 等      PWA 图标（白底圆角矩形叠加画笔颜料盘 logo；含 maskable 与 apple-touch）
/healthz              健康检查（版本/双上游/通道/时间）
/about                服务自描述 JSON（双通道端点、存储键、真实上游、v1.5 直连地址来源——AI Agent 排障入口）
/api/kmage/* -> kmage 上游 /api/*   会话类代理（注册/登录/签到/Key/额度；v1.5 仍走代理：Cookie 跨域不可携带）
               会话令牌经请求头 X-Kmage-Session 携带，
               上游 Set-Cookie 经响应头 X-Kmage-Set-Session 回传前端
/kmage/v1/*  -> kmage 上游 /v1/*    Bearer 透传（v1.5 起为生图直连失败时的自动回退）
/api/kdr/*   -> kdr 上游 /api/*     透明转发（v1.5 起为直连失败时的自动回退；key/host 鉴权在请求 body）
/kdr/img     kdr 结果图片拉取代理（带 Referer 回传字节；v1.5 起为直连图床失败时的回退）

v1.5 直连优先（浏览器侧，不占 Worker 路由）：
  kmage 生图: 浏览器直连 image.dddd.zone /v1/images/generations（Bearer API Key）
  kdr 全部:   浏览器直连 keydraw.97api.com /api/*（gift-key / generations / edits / 轮询，key/host 在 body）
  kdr 结果图: 浏览器直连图床（referrerPolicy=no-referrer，实测不校验 Referer）
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
kmage_channel_v1 当前通道（kmage | kdr，默认 kmage）
kmage_form_v1    创作面板选项记忆: {prompt,ratio,quality,kdrSize,model:{kmage,kdr}}（v1.4 新增）
kmage_logs_v1    运行日志环形缓冲（最近 300 条，detail 截断 300 字符；[kmage]/[kdr] 前缀）
kmage_hist_v1    任务历史（≤40 条；成功/失败/中断均入册。成功条目含 canvas 缩略图
                 thumb 与 kdr 上游下载地址 url，支持 JSON 导出/导入跨设备回看；
                 注意 kmage 上游 API 仅返回图片数据本身（response_format=url 也只回
                 data URI，无持久 CDN 地址），因此 kmage 条目跨设备回看的是缩略图，
                 kdr 条目可在线回看上游原图）
```

**生图**：
- kmage：模型 gpt-image-2 / 2.5-flare / 2.5-sunburst；比例 7 种；质量 auto/low/medium/high；图生图 ≤10 张；前端 180s 超时
- kdr：任务制（3s 轮询/180s 上限）；免费档锁定 gpt-image-2 + 1K；图生图 multipart edits；结果 URL 经 `/kdr/img` 转 b64

**号池行为（kmage）**：轮换 most-credits / round-robin；402 积分不足自动换号；401 自动重登重建 Key；429 退避；**5xx 网关错误 4s 同号重试 + 换号重试**；无号自动注册（可关）；打开页面自动签到（可关）。
**kdr 行为**：Gift Key 缓存 10 分钟自动轮换；401/403 Key 被拒自动刷新重试；提交 5xx 4s 重试；免费档参数自动回退（模型/1K）并记日志。
**直连优先（v1.5，两通道）**：生图类请求先走浏览器直连，失败自动回退 Worker 代理；控制台日志对每次上游请求标注「直连/代理」路径；上游返回的 4xx/5xx 视为业务响应原样透传给既有重试/换号逻辑，不触发代理回退。

## 使用指引（与页面「关于」文档对齐）

### 安装到系统（PWA）与界面记忆

- 本应用是 PWA，可安装到操作系统：浏览器地址栏出现「安装」图标时点击即可（设置 → 通用选项 → 「安装到系统」按钮亦可；iOS Safari 用「分享 → 添加到主屏幕」）。应用名「AI生图」，图标为白底圆角矩形叠加画笔颜料盘 logo（与 favicon 同款）；以 standalone 模式打开，保留系统标题栏与窗口控制。
- 创作面板选项（模型 / 画面比例 / 精细度 / kdr 分辨率档 / 提示词）自动记忆在浏览器 localStorage（`kmage_form_v1`），下次打开自动恢复；模型按通道分别记忆（kmage 与 kdr 各一套），切换通道各自恢复。
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
- kmage：401 会话/Key 失效（自动重登重建）、402 积分不足（自动换号）、429 限流（5s 退避）、5xx 网关错误（4s 后同号+换号重试，失败自动返还积分）、180s 超时、403 `account_environment_abnormal`（2026-09-13 首现于数据中心 IP 直连注册的未满 24h 新号；**2026-09-23 起扩大到所有数据中心出口 IP 的生图请求，Worker 代理路径亦被拒「账号使用环境异常，充值后解锁」——v1.5 起生图由浏览器直连上游（访客网络出口），若仍被拒请更换网络环境**；前端对新生号 403/400 自动换号重试）
- kdr：401/403 Key 被拒（自动刷新共享 Key 重试）、**403「此 IP 已被加入免费 Key 黑名单」（2026-09-23 起上游拉黑 Cloudflare Worker 出口 IP 段的免费 Key 使用——v1.5 起浏览器直连后仅当访客自身出口 IP 被拉黑时出现）**、404 任务失效、轮询超时 180s（免费通道不扣费）
- 号池/设置可导出 JSON 离线分析；上游探活：kmage 站点直接访问首页（注册无验证码，签到接口账号未满 24h 返回 403；**注意本机若为数据中心 IP，凭有效 Key 直接调 /v1 生图也会 403 环境异常，属上游风控而非契约变化**）；kdr 站点 `GET /api/gift-key` 应返回 key/alias

工程坑防守（历史教训，改代码前必读）：
- 单文件 Worker 的 HTML_CONTENT 为内嵌模板字符串，**禁止反斜杠转义序列（含正则）**——形如 `split(/\r?\n/)` 的写法会把整个文件炸成语法错误，换行一律用 `String.fromCharCode(10)`（kd-v2.2 与 kmage-kdr-1.2 两次拦截重演）；同理注意同名 const 冲突、删代码前先 grep 调用点、DOM 元素删除后加 null guard
- `resp.json()` 消费 body 后取不到原文：先读全文再 parse（v1.1 教训）
- headless 验证注意：Chromium 的 `dialog.close` 事件为异步派发，面板归位断言需等待一拍；部署后验证用 cache-busting 参数（`?_=时间戳`）+ 真实浏览器交互，升级测试前清 localStorage

## 边界说明

- 会话与密钥为本工具对注册账号的自身凭据管理，不涉及破解或绕过任何验证；请遵守上游站点服务条款，控制用量，避免滥用免费产能。
- 邀请奖励需被邀请人首次充值后才到账，不属于免费路径，工具不做链式邀请。kdr 通道自定义 Key 为用户自购的付费凭据，工具仅代为填用。

## 完整迭代时间线（原 CHANGELOG.md 全文 · 按实际日期正序）

页面内嵌「关于」文档对源站做了脱敏（以「kmage 站点 / kdr 站点」表述）；本文档为维护者视角，保留真实上游地址。当前生产：`kmage-kdr-1.5`（Cloudflare Worker `ai-image`，https://ai-image.lishuhang.workers.dev/）。

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

## kmage-kdr-1.5 (2026-09-23) — 直连优先（Direct-First）：修复双上游数据中心 IP 风控拦截（本版）

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
