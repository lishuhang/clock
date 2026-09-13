# 0913-gpt2 — AI生图 Worker（kmage + kdr 双通道）

> **当前生产：`kmage-kdr-1.2`，部署于 `https://ai-image.lishuhang.workers.dev/`（Cloudflare Worker 名 `ai-image`）**
>
> 本目录自包含。任何 AI Agent 访问本页/本仓库时：可将 `gpt2-worker-kmage-v1.2.js` 整体作为 skill 调用（单文件 Worker，后端代理 + 内嵌前端，无外部依赖）；排障请先读本文档与文件头部注释，线上自描述接口 `GET /about`、健康检查 `GET /healthz`；页面内右上角「关于」弹窗含同样的自包含文档（对外脱敏版）与完整迭代时间线。

- **最后更新**：2026-09-13（GMT+8）
- **通道**：
  - **kmage**（默认）：上游 https://image.dddd.zone（kmage · AI 视觉工作台）官方 OpenAI 兼容 API。注册送 1 分；签到 +5 分/天/号（注册满 24h 开放）；1 积分 = 1 张图，失败自动返还；号池 N 号 ≈ 5N 张/天
  - **kdr**：上游 https://keydraw.97api.com（Keydraw/Draw Studio）。免费共享 Gift Key（`GET /api/gift-key` 自动轮换），2026-09 新契约：`key`/`host` 放请求 body，任务制（提交→轮询→图床 URL）；免费档固定 主线路 + gpt-image-2 + 1K；可选自定义付费 Key 解锁全部模型与 2K/4K

## 文件清单

| 文件 | 说明 |
|---|---|
| `gpt2-worker-kmage-v1.2.js` | **当前生产版本**。单文件 Cloudflare Worker（Service Worker 格式），kmage + kdr 双通道、内嵌前端、号池、控制台 |
| `gpt2-worker-kmage-v1.1.js` | v1.1 备份（日志控制台/导入导出/通知/反模式化 + 5xx 重试补丁） |
| `gpt2-worker-kmage-v1.0.js` | v1.0 备份（2026-09-13 首版上线） |
| `gpt2-worker-kdr-v1.2.js` | 旧 kdr 通道（上游改版后瘫死，已被 v1.2 修复复活取代，留档） |
| `gpt2-worker-v27.2.js` | 马良通道 v27.2（历史版本，号池模式与反模式化原则的参考实现） |
| `CHANGELOG.md` | 全部版本变更记录（按实际日期正序整合马良至今完整时间线） |
| `TODO-full.md` | 历史任务清单（0722 项目交接文档） |
| `debug/` | 用户提交的故障截图（kmage v1.0 时代「生成失败」无详情 + 24h 待激活状态） |

## 架构速览（kmage-kdr-1.2）

**路由**（Cloudflare Worker `ai-image`，无状态，无 KV 依赖）：

```
/            页面（HTML+CSS+JS 全内嵌，无外部资源；favicon 与 logo 为内联 SVG）
/healthz     健康检查（版本/双上游/通道/时间）
/about       服务自描述 JSON（双通道端点、存储键、真实上游——AI Agent 排障入口）
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
                 emailDomain,notificationsEnabled}
kdr_state_v1     kdr: customKeys[]（自定义付费 Key，可选）; gift{key,alias,ts}（共享 Key 缓存 10min）
kmage_channel_v1 当前通道（kmage | kdr，默认 kmage）
kmage_logs_v1    运行日志环形缓冲（最近 300 条，detail 截断 300 字符；[kmage]/[kdr] 前缀）
```

**生图**：
- kmage：模型 gpt-image-2 / 2.5-flare / 2.5-sunburst；比例 7 种；质量 auto/low/medium/high；图生图 ≤10 张；前端 180s 超时
- kdr：任务制（3s 轮询/180s 上限）；免费档锁定 gpt-image-2 + 1K；图生图 multipart edits；结果 URL 经 `/kdr/img` 转 b64

**号池行为（kmage）**：轮换 most-credits / round-robin；402 积分不足自动换号；401 自动重登重建 Key；429 退避；**5xx 网关错误 4s 同号重试 + 换号重试**；无号自动注册（可关）；打开页面自动签到（可关）。
**kdr 行为**：Gift Key 缓存 10 分钟自动轮换；401/403 Key 被拒自动刷新重试；提交 5xx 4s 重试；免费档参数自动回退（模型/1K）并记日志。

## kmage-kdr-1.2 变更摘要（相对 1.1）

1. **kdr 通道修复复活**（详见 CHANGELOG 本节）：新契约 key/host 入 body、任务轮询、`/kdr/img` 结果代理、Gift Key 免费档规则、自定义 Key 迁移（旧 `maliang_state`）
2. **通道选择器**（header ver 右侧，默认 kmage）+ 按通道隔离的状态与设置 UI
3. **UI 重构**：footer 删除；「文档」+「帮助」→「关于」；「号池」→「设置」、「日志」→「控制台」，均为线条 SVG 图标按钮（齿轮/终端/圆圈 i）
4. **favicon**（画笔+颜料盘线条 SVG）与 **「ai」字母组合 logo**（header 左上角 + 关于弹窗顶部）
5. **设置级 JSON 导入/导出**（号池+全部设置项+kdr 配置，兼容旧号池格式）
6. **对外文档脱敏**（页面不出现源站域名/品牌，统一「kmage 站点 / kdr 站点」；真实上游见 `/about`）+ **关于弹窗整合马良至今完整迭代时间线**（按实际日期正序）

## 排障指引（AI Agent 适用）

1. `GET /healthz` 确认版本与双上游；`GET /about` 确认端点、存储键、真实上游地址。
2. 打开页面「控制台」（终端图标）导出日志，按 `[kmage]`/`[kdr]` 前缀定位首个非 2xx 上游请求；日志含上游响应原文摘要与换号/重试决策。
3. kmage 常见错误：401 会话/Key 失效（自动重登重建）、402 积分不足（自动换号）、429 限流（5s 退避）、5xx 网关错误（4s 同号+换号重试，失败自动返还积分）、180s 超时。
4. kdr 常见错误：401/403 Key 被拒（自动刷新共享 Key 重试一次）、提交 5xx（4s 重试）、404 任务失效、轮询 180s 超时（免费通道失败不扣费）。
5. 上游探活：kmage——直接访问其首页（注册无验证码；签到接口对未满 24h 账号返回 403）；kdr——`GET https://keydraw.97api.com/api/gift-key` 应返回 `{alias,key}`，`GET /api/channels` 下发线路与模型列表。
6. 号池/设置可「导出全部设置」JSON 离线分析（含明文凭据，注意保管）；日志可导出 .txt。
7. 部署方式：CF API `PUT accounts/{id}/workers/scripts/ai-image`，multipart：part `metadata` = `{"body_part":"worker.js"}`，part name = `worker.js`（Service Worker 格式）；部署后 CF API GET 或页面抓取 diff 校验。
8. **工程红线（历史踩坑）**：本文件 HTML_CONTENT 为外层 JS 模板字符串——内层不得出现反引号、`${`、任何 `\` 转义序列（正则/字符串均会被外层吞掉转义，如 `/\r?\n/` 会变成含真实换行的非法正则，kd-v2.2 与 v1.2 均中过招，静态检查脚本 `scripts/check_v12.py` 已强制拦截）。

## 已知边界与合规

- 本工具仅管理用户自行注册账号的自身凭据（注册/登录/签到/API Key 均为上游官方功能），不破解、不绕过验证码、不做链式邀请（邀请奖励需充值才到账，不属于免费路径）。
- kmage 站内老虎机 RTP 95.88%（负期望），工具不纳入自动积分来源；kdr 自定义 Key 为用户自购付费凭据，工具仅代为填用。
- localStorage 保存明文会话与 API Key，属于用户自身数据的本地管理；导出文件含明文凭据，注意保管。
- 请遵守上游服务条款，控制用量，避免滥用免费产能。
- **脱敏说明**：页面对外可见文案与内嵌文档不出现源站域名/品牌名（统一「kmage 站点 / kdr 站点」）；本仓库文档与 `/about` 接口为维护者/排障视角，保留真实地址。

## 历史：kdr 通道故障与修复（2026-09-13 闭环）

- **故障**：上游 keydraw.97api.com 九月初改版为 Draw Studio，生成 API 契约变化——`key` 与 `host` 必须放入请求 body（host 由 `/api/channels` 下发：www.97api.com / new.97api.com），旧版仅用 Authorization 头 → 全部生成请求 400「请求地址只能选择 www.97api.com 或 new.97api.com」。共享 Gift Key 本身仍有效（新格式实测可出图）。
- **修复**：v1.2 全面适配新契约（body 鉴权、任务轮询、结果 URL 代理转存），kdr 通道于 kmage-kdr-1.2 复活为可选第二通道（默认仍为 kmage）。

## 历史：2026-08 公开通道研究结论（0722 项目遗留）

截至 2026-08-19 的筛选结论：未找到同时满足「免登录、免后续验证、可稳定第三方代理且获得明确授权」的免费 GPT-Image-2 上游。Keydraw 访客 Key 无第三方分发授权、Flaq 有人机验证、gptimage2.com/NanoBananaTool/Morphic 需要登录注册赠额、其余候选不可访问。该轮未发布任何版本、未覆盖生产域名。完整试错时间线见 `CHANGELOG.md`。
