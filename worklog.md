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
