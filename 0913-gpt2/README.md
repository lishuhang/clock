# 0913-gpt2 — AI生图 Worker（kmage + kdr 双通道）

> **当前生产：`kmage-kdr-1.4`，部署于 `https://ai-image.lishuhang.workers.dev/`（Cloudflare Worker 名 `ai-image`）**
>
> 本目录自包含。任何 AI Agent 访问本页/本仓库时：可将 `gpt2-worker-kmage-v1.4.js` 整体作为 skill 调用（单文件 Worker，后端代理 + 内嵌前端，无外部依赖）；排障请先读本文档与文件头部注释，线上自描述接口 `GET /about`、健康检查 `GET /healthz`；页面内右上角齿轮按钮 →「关于」选项卡含同样的自包含文档（对外脱敏版）与完整迭代时间线。

- **最后更新**：2026-09-13（GMT+8）
- **通道**：
  - **kmage**（默认）：上游 https://image.dddd.zone（kmage · AI 视觉工作台）官方 OpenAI 兼容 API。注册送 1 分；签到 +5 分/天/号（注册满 24h 开放）；1 积分 = 1 张图，失败自动返还；号池 N 号 ≈ 5N 张/天
  - **kdr**：上游 https://keydraw.97api.com（Keydraw/Draw Studio）。免费共享 Gift Key（`GET /api/gift-key` 自动轮换），2026-09 新契约：`key`/`host` 放请求 body，任务制（提交→轮询→图床 URL）；免费档固定 主线路 + gpt-image-2 + 1K；可选自定义付费 Key 解锁全部模型与 2K/4K

## 文件清单

| 文件 | 说明 |
|---|---|
| `gpt2-worker-kmage-v1.4.js` | **当前生产版本**。单文件 Cloudflare Worker（Service Worker 格式），在 1.3 基础上新增：全宽度统一单齿轮导航 + 选项卡浮窗、设置三分区（通用/kmage/kdr 常驻可跨通道调整）、创作面板选项本地记忆（kmage_form_v1）、PWA 可安装（manifest + SW + 白底圆角 logo 图标，standalone 保留系统标题栏） |
| `gpt2-worker-kmage-v1.3.js` | v1.3 留档（竖屏适配/深色模式/历史持久化） |
| `gpt2-worker-kmage-v1.2.js` | v1.2 留档（kdr 修复复活 + 双通道选择器 + UI/文档重构） |
| `gpt2-worker-kmage-v1.1.js` | v1.1 备份（日志控制台/导入导出/通知/反模式化 + 5xx 重试补丁） |
| `gpt2-worker-kmage-v1.0.js` | v1.0 备份（2026-09-13 首版上线） |
| `gpt2-worker-kdr-v1.2.js` | 旧 kdr 通道（上游改版后瘫死，已被 v1.2 修复复活取代，留档） |
| `gpt2-worker-v27.2.js` | 马良通道 v27.2（历史版本，号池模式与反模式化原则的参考实现） |
| `CHANGELOG.md` | 全部版本变更记录（按实际日期正序整合马良至今完整时间线） |
| `TODO-full.md` | 历史任务清单（0722 项目交接文档） |
| `debug/` | 用户提交的故障截图（kmage v1.0 时代「生成失败」无详情 + 24h 待激活状态） |

## 架构速览（kmage-kdr-1.4）

**路由**（Cloudflare Worker `ai-image`，无状态，无 KV 依赖）：

```
/                     页面（HTML+CSS+JS 全内嵌，无外部资源；favicon 与 logo 为内联 SVG）
/manifest.webmanifest PWA 清单（名称「AI生图」，display=standalone 保留系统标题栏）
/sw.js                Service Worker（仅缓存页面外壳与图标，版本随发布更新，不拦代理/API）
/icon-192.png 等      PWA 图标（白底圆角矩形叠加画笔颜料盘 logo；含 maskable 与 apple-touch）
/healthz              健康检查（版本/双上游/通道/时间）
/about                服务自描述 JSON（双通道端点、存储键、真实上游——AI Agent 排障入口）
/api/kmage/* -> kmage 上游 /api/*   会话类代理（注册/登录/签到/Key/额度）
               会话令牌经请求头 X-Kmage-Session 携带，
               上游 Set-Cookie 经响应头 X-Kmage-Set-Session 回传前端
/kmage/v1/*  -> kmage 上游 /v1/*    Bearer 透传（生图，官方 OpenAI 兼容）
/api/kdr/*   -> kdr 上游 /api/*     透明转发（key/host 鉴权在请求 body；multipart 兼容）
/kdr/img     kdr 结果图片拉取代理（带 Referer 回传字节，前端转 b64）
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
                 thumb 与 kdr 上游下载地址 url，支持 JSON 导出/导入跨设备回看）
```

**生图**：
- kmage：模型 gpt-image-2 / 2.5-flare / 2.5-sunburst；比例 7 种；质量 auto/low/medium/high；图生图 ≤10 张；前端 180s 超时
- kdr：任务制（3s 轮询/180s 上限）；免费档锁定 gpt-image-2 + 1K；图生图 multipart edits；结果 URL 经 `/kdr/img` 转 b64

**号池行为（kmage）**：轮换 most-credits / round-robin；402 积分不足自动换号；401 自动重登重建 Key；429 退避；**5xx 网关错误 4s 同号重试 + 换号重试**；无号自动注册（可关）；打开页面自动签到（可关）。
**kdr 行为**：Gift Key 缓存 10 分钟自动轮换；401/403 Key 被拒自动刷新重试；提交 5xx 4s 重试；免费档参数自动回退（模型/1K）并记日志。

## kmage-kdr-1.4 变更摘要（相对 1.3）

1. **导航统一（组件复用）**：全宽度右上角仅保留一个齿轮按钮，点开浮窗以选项卡切换设置/控制台/关于；移除桌面三图标按钮与窄屏汉堡按钮的双轨实现，三个面板 DOM 收敛为隐藏宿主 + hub 搬运复用，代码更精简
2. **设置三分区**：「通用选项（主题/通知/安装/导入导出）/ kmage 通道选项 / kdr 通道选项」全部常驻——选中任一通道均可直接调整另一通道的专属选项
3. **创作面板记忆**：模型（按通道分存）/比例/精细度/分辨率档/提示词自动记忆于 `kmage_form_v1`，下次打开自动恢复
4. **PWA 可安装**：`/manifest.webmanifest` + `/sw.js` + PNG 图标（白底圆角矩形叠加画笔颜料盘 logo，与 favicon 同款；含 maskable 与 apple-touch-icon）；应用名「AI生图」；`display=standalone` 保留系统标题栏；设置 → 通用选项提供「安装到系统」按钮（beforeinstallprompt）；SW 仅缓存外壳（`/`、manifest、图标，页面网络优先），不拦截代理/API，版本随发布更新
5. **验证**：线上 `/healthz` `/about` `/manifest.webmanifest` `/sw.js` 图标全部 200；无头浏览器 375px/1280px 无横向溢出，齿轮浮窗、选项卡切换、面板归位、跨通道模型记忆、深色模式、表单持久化全部通过；**生产 kdr 免费 Gift Key 真实出图 27.6s**，历史条目含上游 URL 与缩略图

## kmage-kdr-1.3 变更摘要（相对 1.2）

1. **竖屏手机适配**：≤680px 下触控目标、`dvh` 弹窗高度、历史条目换行、toast 布局全面适配；版本号收进标题下方堆叠；320px 实测无溢出
2. **深色模式**：CSS 全量变量化；设置内「界面主题」跟随系统（默认，实时感应）/ 浅色 / 深色；随设置包迁移
3. **任务历史持久化**：`kmage_hist_v1`（≤40 条），成功/失败/中断均入册；成功条目存 canvas 缩略图 + kdr 上游下载地址；点击回看（会话原图 → kdr 上游 URL → 本地缩略图）；`ai-image-history` JSON 导出/导入（按运行号去重），kdr 条目跨设备可在线回看上游原图
4. **图标修正**：设置按钮太阳 → 齿轮；header/关于 logo → 画笔+颜料盘（favicon 同款）
5. **排障新知**：上游对直连数据中心 IP 的新生号返回 403 `account_environment_abnormal`（Worker 代理路径正常），已写入文档与排障指引

## kmage-kdr-1.2 变更摘要（相对 1.1）

1. **kdr 通道修复复活**（详见 CHANGELOG 本节）：新契约 key/host 入 body、任务轮询、`/kdr/img` 结果代理、Gift Key 免费档规则、自定义 Key 迁移（旧 `maliang_state`）
2. **通道选择器**（header ver 右侧，默认 kmage）+ 按通道隔离的状态与设置 UI
3. **UI 重构**：footer 删除；「文档」+「帮助」→「关于」；「号池」→「设置」、「日志」→「控制台」，均为线条 SVG 图标按钮
4. **favicon**（画笔+颜料盘线条 SVG）与 logo
5. **设置级 JSON 导入/导出**（号池+全部设置项+kdr 配置，兼容旧号池格式）
6. **对外文档脱敏**（页面不出现源站域名/品牌，统一「kmage 站点 / kdr 站点」；真实上游见 `/about`）+ **关于弹窗整合马良至今完整迭代时间线**（按实际日期正序）
