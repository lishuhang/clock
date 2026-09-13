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
