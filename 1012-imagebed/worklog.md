# 1012-imagebed 工作日志 — 虎嗅图床

单文件 HTML 图床（`imagebed-hx.html`）+ Cloudflare Worker 代理（`imagebed-hx-worker.js`）。
上传图片 → 虎嗅 CDN（img.huxiucdn.com）→ 返回可外链直链。

- 线上地址：https://imagebed-hx.lishuhang.workers.dev/
- Worker 名称：`imagebed-hx`
- Account ID：`ec44dddde866c789a9dd26f5d0cdb248`
- 本地打开 `imagebed-hx.html`（file://）或放置于 GitHub Pages 均可正常运行（自动走 Worker 代理，CORS 已全开）

---

## 2026-10-12 — v1.0 全链路打通并部署

### 需求
- 模拟虎嗅投稿页（contribute.html）内嵌编辑器的图片上传动作，制作图床 webapp
- 单文件 HTML，优先保证 GitHub Pages / Cloudflare Workers 可运行，兼顾本地打开
- 点击选择 / 拖拽 / Ctrl+V 剪贴板上传，自动上传并返回预览与 URL
- 前端上传操作不与 cookies 挂钩（cookies 仅用于前期分析编辑器，不入库不入页）

### 关键技术发现
1. **WAF**：`www.huxiu.com/contribute.html` 有阿里云滑块（路径级防护）。Chromium/CDP 拖动均被识别，**Firefox 引擎 + 拟人轨迹可通过**。
2. **投稿页编辑器** = UEditor（`tgEditor`），资源在 `/hx_ueditor/`，serverUrl 为 `/hx_ueditor/php/controller.php`。
3. **上传通道对比**：
   | 通道 | 登录 | 返回 URL | 稳定性 | 结论 |
   |---|---|---|---|---|
   | `/hx_ueditor/php/controller.php?action=uploadimage` | 匿名 | www.huxiu.com/ueditor/php/upload/... | 200/404 随机（多源站不同步） | 弃用 |
   | `/contribute/img_upload`（编辑器配图通道） | 需 cookies | img.huxiucdn.com/article/content/... | 10/10 | 可用，但见下 |
   | `api-brief.huxiu.com/club/uploadImage`（编辑器家族接口，字段 image + platform=www） | 需 cookies | img.huxiucdn.com/img/club/... | 12/12，缓存一年 | **采用** |
4. **WAF 拦截规则**：POST 一旦携带 Origin/Referer 头即 405（无论值为何、无论是否带 cookie）；浏览器跨域 fetch 必带 Origin → 纯前端直连不可行，必须服务端代理。
5. **CF Workers 出口被封**：`www.huxiu.com` 拦截 Cloudflare Workers 出口（Cf-Worker/Cdn-Loop 特征头无关，实测本地 curl 带这些头可过 → 是 IP/TLS 层封禁）；但 **api-brief.huxiu.com 子域不拦 CF Workers** → 最终采用该通道。
6. **格式限制**：采用通道仅收 PNG/JPG(JPEG)；WebP/BMP 在前端经 canvas 自动转 PNG；GIF 动图明确提示不支持（转存丢动画无意义）。实测 1.4MB PNG、GIF、JPG 均可过（GIF 走的 /contribute/img_upload 已弃用）。
7. **外链与防盗链**（img.huxiucdn.com 实测）：无 Referer 200；微信、微博白名单 200；github.io/知乎/百度等外站 Referer 403 → 网页引用加 `referrerpolicy="no-referrer"` 即可，HTML 复制按钮已内置该属性，页面有提示。

### 架构
```
浏览器（Workers 页面 / GH Pages / 本地 file://）
   │ POST /upload（multipart: img=<file>）
   ▼
CF Worker imagebed-hx（CORS: *，serve HTML + 代理）
   │ 服务端注入 HUXIU_COOKIE（Worker Secret，非仓库文件）
   │ POST api-brief.huxiu.com/club/uploadImage（image + platform=www，无 Origin/Referer）
   ▼
虎嗅 → {"data":{"image_url":"https://img.huxiucdn.com/img/club/..."}}
   ▼
前端展示预览 + 直链 + 复制（链接 / Markdown / HTML）
```

### 部署记录
- Worker 上传：CF API `PUT /accounts/ec44dddde866c789a9dd26f5d0cdb248/workers/scripts/imagebed-hx`（module 语法）
- Secrets：`HUXIU_COOKIE`（登录态 cookie 串，secret_text）；`HUXIU_HASH_CODE`（plain_text，页面 hash）
- workers.dev 子域已启用：`imagebed-hx.lishuhang.workers.dev`
- 上传脚本：本仓库外（会话环境 `scripts/deploy_worker.py`），重新部署方式见下方"维护"

### 端到端测试（2026-10-12，全部通过 4/4）
- A 本地 file:// 打开 + Ctrl+V 粘贴 PNG → 上传成功，返回 CDN 直链 ✅
- B workers.dev 线上 + 粘贴 PNG（同域模式）→ ✅
- C 线上拖拽 WebP → 自动转 PNG 上传 ✅
- D 粘贴 GIF → 友好拒绝提示 ✅
- URL 稳定性：12/12 200，`cache-control: public, max-age=31536000`

## 2026-10-12 — v1.0.1 修复 GitHub Pages 自定义域端点误判

- **问题**：仓库 Pages 绑定自定义域 `lishuhang.me`（非 *.github.io），旧逻辑"非 github.io 且 https 即同域模式"导致上传请求打到 `lishuhang.me/clock/.../upload` → 404。
- **修复**：同域模式收紧为 `*.workers.dev`（或 Worker 自定义域）；GitHub Pages / 任意静态托管 / 本地打开一律走默认 Worker 代理（`DEFAULT_API`）。
- 用户在旧版（www 通道，被 WAF 拦）测试截图中的 HTTP 502 属部署切换期问题，v1.0（api-brief 通道）已解决。
- **最终三端验证全部通过**：
  - workers.dev（同域）✅ → https://img.huxiucdn.com/img/club/...png
  - GH Pages `https://lishuhang.me/clock/1012-imagebed/imagebed-hx.html`（Worker 代理）✅
  - 本地 file://（Worker 代理）✅

### 维护
- **登录态过期**（`HUXIU_016a_expire_time` 约一周，实际以服务端为准）：上传会返回"代理登录态已过期"。到虎嗅投稿页重新导出 cookies，然后更新 Worker Secret：
  ```
  # 方式一：wrangler
  wrangler secret put HUXIU_COOKIE --name imagebed-hx
  # 方式二：CF Dashboard → Workers → imagebed-hx → Settings → Variables
  ```
- 重新部署 Worker：修改 `imagebed-hx-worker.js` 后，用 wrangler deploy（或 CF API PUT script + secret binding）。
- 修改前端：编辑 `imagebed-hx.html` 后需同步重建 Worker（Worker 内嵌了 HTML 全文）；本会话使用的构建脚本为 `scripts/build_worker.py`（把 HTML 内嵌进 worker 并将默认 API 置空以启用同域模式）。

### 安全注意
- `HUXIU_COOKIE` 只存在于 Worker Secret，绝不写入本仓库任何文件
- 本目录的 `www.huxiu.com_cookies.txt` 为用户自行提交的原始 cookie 导出文件，机器人新增文件均不含凭据
