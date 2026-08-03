# Changelog

All notable changes to vidsync will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-08-03

### Fixed
- **B站封面上传**：file chooser 方式超时，但 fallback 到 `.cover-upload input[type=file]` 成功上传。VLM 确认封面缩略图可见。
- **B站简介填写**：找到正确 selector `.ql-editor[contenteditable=true]`（B站用 Quill 富文本编辑器，不是普通 textarea）。
- **B站分区选择**：从 HTML 快照分析发现 B站默认会根据视频内容预选分区（`.select-item-cont-inserted`），策略改为"如有预选就用默认，否则选第一个"。实测确认分区"科技数码"被正确识别。
- **B站存草稿按钮**：从 HTML 快照分析找到正确 selector `.submit-draft`（是 `<span>` 不是 `<button>`）。改进点击逻辑：不检查 is_visible，先试 click() 再 fallback 到 JavaScript el.click()。实测确认页面跳转到草稿箱 `?group=draft`。

### Verified
- **VLM（glm-5v-turbo）分析截图 11 确认**：草稿箱列表显示 2 条草稿（v0.1.0 + v0.1.1 各 1 条）。
- **完整流程**：登录态识别 → 视频上传 → 封面上传 → 标题 → 简介 → 5标签 → 分区 → 存草稿 → 跳转草稿箱。全部成功。

### Added
- `_handle_confirm_dialog()` 方法：处理保存草稿后可能出现的确认弹窗。
- B站 adapter 的 HTML 快照保存机制：失败时自动保存 page.html + dom_state.json，供 debug 分析。

## [0.1.0] - 2026-08-03

### Added
- 项目骨架与目录结构
- `processors/cookies.py`：Netscape cookies.txt 格式 parser（已实测 12 平台 cookies 全部正确解析）
- `browser/launcher.py`：使用系统 Chrome/Edge 启动浏览器（channel='chrome'，不下载 Chromium；Linux 沙盒自动 fallback 到 Playwright bundled chromium）
- `processors/logger.py`：结构化日志 + 每步截图 + 失败时 HTML 快照 + DOM 状态保存
- `adapters/base.py`：adapter 抽象基类（含 safe_click/safe_fill/safe_upload 等辅助方法）
- `adapters/bilibili.py`：B 站草稿保存 adapter
- `processors/cover.py`：封面裁剪处理器（13 种规格，从左上角对齐裁剪）
- `processors/tags.py`：标签格式归一化（plain / single_hash / double_hash）
- `processors/title.py`：标题截断（按平台字数限制）
- `web/main.py`：FastAPI Web UI 服务（端口 8765）
- `web/static/index.html`：编辑表单 UI（拖拽上传、进度显示）
- `web/static/app.js`：前端逻辑（轮询进度，平台 checkbox）
- `config.yaml`：用户配置（Chrome 路径、headless 等）
- `README.md`：自包含文档（含 10 项踩坑记录）
- `CHANGELOG.md`：本文件

### Platform Support
- ✅ **Bilibili — 草稿保存端到端实测成功**（v0.1 主测）
  - 实测：登录态识别 ✓ / 视频上传 ✓ / 标题填写 ✓ / 标签填写（5个）✓ / 存草稿 ✓
  - 草稿已出现在 B站草稿箱，标题"vidsync系统测试视频请勿发布"
  - 已知问题：封面上传 selector 不对（B站按钮文字是"添加主封面"）、简介 textarea selector 不对、分区选择未实现
  - 这些已知问题不影响草稿保存，编辑可在草稿中手动补充
- 🚧 抖音 / 小红书 / 快手 / 视频号 / 百家号 / 企鹅号 / 腾讯视频 / 微博 / 虎嗅 / 36氪 / 支付宝 — 代码骨架待填

### Tested
- Linux 沙盒环境 headless 模式下，B站 adapter 完整跑通：
  - 18 个 cookies 正确注入
  - 11 步截图全部保存
  - 草稿保存成功，URL: https://member.bilibili.com/platform/upload/video/frame
  - 草稿箱确认可见

### Security
- .gitignore 严格排除 `cookies/*.txt`、`secrets/`、`*.env`
- 加密 7z 压缩包可传 GitHub，密码仅对话中提供
- commit 前自检脚本

### Known Issues
- B站封面上传 selector 需修复（应点击"添加主封面"按钮再找 input）
- B站简介 textarea selector 需修复
- B站分区选择未实现
- 视频号 cookie 易失效（2 小时即过期），需重新扫码
- 小红书海外 GeoIP 限制（国内环境无影响）
- 36kr misopen 是 JS SPA，需实际测试 selector
- 虎嗅视频投稿必须填微信公众号文章链接（依赖视频号先发布）

### Notes
- 不使用反编译 API（如已下架的 SocialSisterYi/bilibili-API-collect），统一走浏览器自动化
- 不下载 Chromium，使用 `channel='chrome'` 驱动系统 Chrome
- Web UI 优先，编辑无需命令行
- VLM（glm-5v-turbo）用于分析截图，帮助 agent 理解页面实际状态
