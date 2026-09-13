# 0913-gpt2 — AI生图 Worker（kmage 通道）

> **当前生产：`kmage-1.1`，部署于 `https://ai-image.lishuhang.workers.dev/`（Cloudflare Worker 名 `ai-image`）**
>
> 本目录自包含。任何 AI Agent 访问本页/本仓库时：可将 `gpt2-worker-kmage-v1.1.js` 整体作为 skill 调用（单文件 Worker，后端代理 + 内嵌前端 + 号池，无外部依赖）；排障请先读本文档与文件头部注释，线上自描述接口 `GET /about`、健康检查 `GET /healthz`。

- **最后更新**：2026-09-13（GMT+8）
- **上游**：https://image.dddd.zone（kmage · AI 视觉工作台）官方 OpenAI 兼容 API
- **经济模型**：注册即送 1 积分；签到 +5 积分/天/号（注册满 24h 开放）；1 积分 = 1 张图，失败自动返还；号池 N 号 ≈ 5N 张/天

## 文件清单

| 文件 | 说明 |
|---|---|
| `gpt2-worker-kmage-v1.1.js` | **当前生产版本**。单文件 Cloudflare Worker（Service Worker 格式），含内嵌前端、号池管理、日志控制台 |
| `gpt2-worker-kmage-v1.0.js` | v1.0 备份（2026-09-13 首版上线） |
| `gpt2-worker-kdr-v1.2.js` | kdr 通道（已停用，上游改版导致瘫死，仅留档） |
| `gpt2-worker-v27.2.js` | 马良通道 v27.2（历史版本，号池模式与反模式化原则的参考实现） |
| `CHANGELOG.md` | 全部版本变更记录（自包含） |
| `TODO-full.md` | 历史任务清单 |

## 架构速览（kmage-1.1）

**路由**（Cloudflare Worker `ai-image`，无状态，无 KV 依赖）：

```
/            页面（HTML+CSS+JS 全内嵌，无外部资源）
/healthz     健康检查（版本/上游/时间）
/about       服务自描述 JSON（AI Agent 排障入口）
/api/kmage/* -> 上游 /api/*   会话类代理（注册/登录/签到/Key/额度）
               会话令牌经请求头 X-Kmage-Session 携带，
               上游 Set-Cookie 经响应头 X-Kmage-Set-Session 回传前端
/kmage/v1/*  -> 上游 /v1/*    Bearer 透传（生图，官方 OpenAI 兼容）
```

**前端数据**（浏览器 localStorage）：

```
kmage_state_v1  accounts[]: {email,password,session,apiKey,apiKeyId,apiKeyHint,
                credits,lastCheckinDay,eligibleAt,createdAt,disabled,lastError}
                abandoned[]: 已删除/归档账号
                settings: {rotationStrategy,autoRegister,autoCheckin,
                emailDomain,notificationsEnabled}
kmage_logs_v1   运行日志环形缓冲（最近 300 条，detail 截断 300 字符）
```

**生图**：模型 gpt-image-2 / gpt-image-2.5-flare / gpt-image-2.5-sunburst；比例 1:1/3:2/2:3/16:9/9:16/4:3/3:4/auto；质量 auto/low/medium/high；图生图 reference_images ≤10 张（PNG/JPG/WebP，≤10MB）；前端 180s 超时终态。

**号池行为**：轮换策略 most-credits / round-robin；402 积分不足自动换号；401 会话失效自动重登并重建 Key；429 限流 5s 退避；无号可用时自动注册（可关）；打开页面自动为可签账号签到（可关）。

## kmage-1.1 新增（相对 v1.0）

1. **运行日志控制台**：右上角「日志」。每次生图按运行号（R+时间戳）分组记录——账号选择依据、请求参数、上游状态码与耗时、错误响应原文（含非 JSON 响应截断）、换号/重试决策。支持导出全部/本次运行（.txt，含版本、UA、页面地址）、一键复制、只看错误、清空；日志持久化 localStorage，刷新不丢。
2. **号池 JSON 导入/导出**：号池面板「导出号池/导入号池」。导出含邮箱密码、会话与 API Key（明文凭据，注意保管）；导入按邮箱去重，缺会话账号自动重登恢复。
3. **浏览器原生通知**：号池设置开启后，生图成功/失败/超时发系统级通知（首次开启请求权限；需页面保持打开；被拒绝时开关自动回退并提示）。
4. **24 小时规则明确化**：24h 冷却仅限制签到（上游 403 + eligible:false），**不限制生图**（新生号可立即生图，已实测）。签到提示精确到「X小时Y分后开放」；若新生号生图被拒（403/400），自动提示剩余冷却时间并切换其他账号重试。
5. **反模式化（沿袭马良 v27.2 原则）**：
   - 邮箱：姓名/形容词/名词词库 × 6 种模式 × 随机大小写，无固定前缀与时间戳指纹（v1.0 的 `kmg****x+时间戳` 已去除）
   - 密码：12~15 位完全随机强密码，无固定后缀（v1.0 的 `Zq9` 尾巴已去除）；API Key 备注名从词池随机
   - 节奏：批量注册间隔 2.5~8s 随机（15% 概率再 +4s），批量签到乱序 + 0.8~2.8s 随机间隔
   - UA：Worker 端透传访客浏览器真实 UA（缺失时从 4 个常见池随机）；不做 IP 伪造（马良 v26.1 已证实无效并移除）
6. **品牌与文档**：div.brand 改为「AI生图」；页面内嵌自包含 README 与 CHANGELOG（右上角「文档」）；页面 HTML 头部与页脚含 AI Agent 使用提示；新增 `/about` 自描述接口。

## 排障指引（AI Agent 适用）

1. `GET /healthz` 确认版本；`GET /about` 确认端点与存储键。
2. 打开页面「日志」控制台导出日志，定位第一个非 2xx 上游请求；日志含上游响应原文摘要。
3. 常见上游错误：401 会话/Key 失效（工具自动重登重建）、402 积分不足（自动换号）、429 限流（5s 退避）、180s 超时（上游失败不扣分，自动返还）。
4. 上游探活：直接访问 image.dddd.zone 首页；注册无验证码，签到接口在账号未满 24h 时返回 403。
5. 号池数据可导出 JSON 离线分析；日志可用「导出全部日志」导出 .txt。
6. 部署方式：CF API `PUT accounts/{id}/workers/scripts/ai-image`，metadata 含 `body_part`（Service Worker 格式），部署后用 CF API GET 脚本 diff 校验。

## 已知边界与合规

- 本工具仅管理用户自行注册账号的自身凭据（注册/登录/签到/API Key 均为上游官方功能），不破解、不绕过验证码、不做链式邀请（邀请奖励需充值才到账，不属于免费路径）。
- 上游老虎机 RTP 95.88%（负期望），工具不纳入自动积分来源，避免把积分赌没。
- localStorage 保存明文会话与 API Key，属于用户自身数据的本地管理；导出文件含明文凭据，注意保管。
- 请遵守上游服务条款，控制用量，避免滥用免费产能。

## 历史：kdr 通道停用原因（2026-09-13 诊断）

kdr 通道（Keydraw/97api，`gpt2-worker-kdr-v1.2.js`）瘫死原因：上游 keydraw.97api.com 九月初改版为 Draw Studio，生成 API 契约变化——`key` 与 `host` 必须放入请求 body（host 由 /api/channels 下发：www.97api.com / new.97api.com），旧版仅用 Authorization 头 → 全部生成请求 400「请求地址只能选择 www.97api.com 或 new.97api.com」。Gift Key 本身仍有效（新格式实测可出图），kdr 前端未适配，停止维护，由 kmage 通道同位替换。

## 历史：2026-08 公开通道研究结论（0722 项目遗留）

截至 2026-08-19 的筛选结论：未找到同时满足「免登录、免后续验证、可稳定第三方代理且获得明确授权」的免费 GPT-Image-2 上游。Keydraw 访客 Key 无第三方分发授权、Flaq 有人机验证、gptimage2.com/NanoBananaTool/Morphic 需要登录注册赠额、其余候选不可访问。该轮未发布任何版本、未覆盖生产域名。完整边界讨论见 git 历史中的旧版 README 与 CHANGELOG 对应条目。
