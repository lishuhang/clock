# Changelog

All notable changes to vidsync will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.1] - 2026-08-03

### Fixed
- 36氪视频上传尝试用 `.add-file` 点击触发 file chooser（仍失败，需 v0.5 深入调试）

### Known Issues
- 36氪 kr-upload-file 组件用非标准上传方式（可能拖拽或 XHR），file chooser 不触发
- 需 v0.5 用 CDP 协议或拦截 XHR 上传

## [0.4.0] - 2026-08-03

### Added
- **企鹅号 adapter**：完整实现，草稿保存成功
  - 视频上传 ✓ / 存草稿 ✓（text=存草稿）
  - 实测：status=success，URL 保持 creation/video
- **36氪 adapter**：部分实现
  - "新建视频"按钮点击 ✓
  - 已知问题：视频上传失败（36氪用 `kr-upload-file` 自定义组件，无 input[type=file]）
  - v0.5 需用 file chooser 或点击组件触发上传
- Web UI 注册 8 个平台 adapter

### Platform Support Status (v0.4)
| 平台 | 状态 | 草稿保存 |
|------|------|---------|
| 哔哩哔哩 | ✅ 完整 | ✓ |
| 抖音 | ✅ 完整 | ✓ |
| 小红书 | ✅ 完整 | ✓ |
| 快手 | ⚠️ 部分 | 视频已上传，存草稿未找到 |
| 百家号 | ✅ 草稿按钮成功 | ✓ |
| 微博 | ⚠️ 无草稿功能 | 视频上传后自动发布 |
| 企鹅号 | ✅ 完整 | ✓ |
| 36氪 | ⚠️ 部分 | 视频上传失败（自定义组件） |
| 视频号 | 🚧 v0.5 | - |
| 腾讯视频 | ❌ cookie 失效 | - |
| 虎嗅 | ❌ 滑块验证 | - |
| 支付宝 | 🚧 v0.5 | - |

### Key Findings
- **企鹅号**：表单动态加载，但 selector 通用模式可工作，存草稿按钮 text=存草稿
- **36氪**：用 `kr-upload-file` 自定义上传组件，无标准 input[type=file]，需特殊处理
- **8 个平台已注册 Web UI**，其中 5 个完整跑通（B站/抖音/小红书/百家号/企鹅号）

### Known Issues
- 36氪视频上传需用 file chooser 或点击 kr-upload-file 组件
- 快手存草稿机制待调研
- 微博无草稿功能（平台设计）
- 腾讯视频 cookie 失效
- 虎嗅滑块验证

## [0.3.0] - 2026-08-03

### Added
- **百家号 adapter**：完整实现，草稿保存按钮点击成功
  - 视频上传 ✓ / 封面 ✓ / 简介 ✓（contenteditable）/ 存草稿 ✓（`button:has(span:has-text('存草稿'))`）
  - 关键发现：百家号 edit?type=video 会重定向到 content，需先访问主页让 cookie 生效
  - 关键发现：登录态检测不能用 selector，用 URL 判断更可靠
  - 已知问题：标题和标签 selector 不对（表单动态加载，需视频上传后才出现）
- **微博 adapter**：部分实现
  - 视频上传 ✓ / 封面 ✓
  - **重要发现：微博没有"存草稿"功能！** 视频上传完毕后会"自动发布微博"
  - 已知问题：标题/简介/话题 selector 不对（视频上传后表单未及时出现）
  - v0.3 策略：微博标记为"无草稿功能"，编辑需在视频上传前就填好所有信息
- Web UI 注册 6 个平台 adapter

### Platform Support Status (v0.3)
| 平台 | 状态 | 草稿保存 |
|------|------|---------|
| 哔哩哔哩 | ✅ 完整跑通 | ✓ |
| 抖音 | ✅ 完整跑通 | ✓ |
| 小红书 | ✅ 完整跑通 | ✓ |
| 快手 | ⚠️ 部分 | 视频已上传，存草稿未找到 |
| 百家号 | ✅ 草稿按钮点击成功 | ✓（标题/标签待修） |
| 微博 | ⚠️ 无草稿功能 | 视频上传后自动发布 |
| 企鹅号 | 🚧 v0.4 | - |
| 腾讯视频 | ❌ cookie 失效 | - |
| 虎嗅 | ❌ 需滑块验证 | - |
| 36氪 | 🚧 v0.4 | - |
| 支付宝 | 🚧 v0.4 | - |

### Key Findings
- **微博无草稿功能**：视频上传后自动发布，无法保存草稿。这是平台设计，非 bug
- **百家号 cookie warmup**：需先访问主页让 cookie 生效，再导航到发布页
- **登录态检测**：用 URL 判断（不含 login/passport）比 selector 更可靠
- **腾讯视频 cookie 失效**：需用户重新导出
- **虎嗅需滑块验证**：headless 模式无法通过

### Known Issues
- 百家号标题/标签 selector 待修复（表单动态加载）
- 微博标题/简介/话题 selector 待修复
- 快手存草稿机制待调研
- 腾讯视频 cookie 失效
- 虎嗅滑块验证

## [0.2.0] - 2026-08-03

### Added
- **抖音 adapter**：完整实现，端到端实测成功
  - 视频上传 ✓ / 封面上传 ✓（含裁剪弹窗关闭）/ 标题 ✓ / 简介 ✓（Slate 富文本）/ 话题 ✓ / 暂存离开 ✓
  - 关键发现：抖音存草稿按钮文字是"暂存离开"（不是"存草稿"）
  - 关键发现：抖音简介用 Slate 富文本编辑器，wait_for_selector 超时，改用 JS evaluate focus
- **小红书 adapter**：完整实现，端到端实测成功
  - 视频上传 ✓ / 封面 ✓ / 标题 ✓ / 简介+话题 ✓（contenteditable）/ 暂存离开 ✓
  - 关键发现：小红书用 Web Component `<xhs-publish-btn>`（closed shadow DOM），普通 selector 找不到按钮
  - 解决方案：用 Playwright piercing selector `>>>` 或基于 bounding box 坐标点击
- **快手 adapter**：部分实现
  - 视频上传 ✓ / 封面 ✓ / 简介+话题 ✓（#work-description-edit contenteditable）
  - 关键发现：快手没有独立标题框，标题+简介都填到"作品描述"
  - 关键发现：快手有引导教程 tooltip（含"下一步"），需先 Skip
  - 已知问题：未找到"存草稿"按钮（快手可能无此功能或需其他方式）
- Web UI 注册 4 个平台 adapter
- 探查脚本：probe_douyin.py / probe_xhs.py / probe_ks.py
- 测试脚本：test_douyin_adapter.py / test_xhs_adapter.py / test_ks_adapter.py

### Fixed
- B站简介 selector 改进（增加 .ql-editor）
- 抖音封面裁剪弹窗自动关闭
- 小红书 shadow DOM 按钮点击
- 快手引导教程 tooltip 自动跳过

### Platform Support Status (v0.2)
| 平台 | 状态 | 草稿保存 |
|------|------|---------|
| 哔哩哔哩 | ✅ 完整跑通 | ✓ |
| 抖音 | ✅ 完整跑通 | ✓ |
| 小红书 | ✅ 完整跑通 | ✓（话题含特殊符号会被拒） |
| 快手 | ⚠️ 部分 | 视频已上传但未找到存草稿按钮 |
| 视频号 | 🚧 v0.3 | - |
| 百家号 | 🚧 v0.3 | - |
| 企鹅号 | 🚧 v0.3 | - |
| 腾讯视频 | 🚧 v0.3 | - |
| 微博 | 🚧 v0.3 | - |
| 虎嗅 | 🚧 v0.4 | - |
| 36氪 | 🚧 v0.4 | - |
| 支付宝 | 🚧 v0.4 | - |

### Known Issues
- 抖音话题添加可能不成功（需等推荐弹窗），但草稿能保存
- 小红书话题含特殊符号（如 v0.2 的点）会被拒绝
- 快手未找到存草稿按钮（可能快手无此功能，或需刷新页面）
- 视频号 cookie 易失效
- 36kr misopen 是 JS SPA
- 虎嗅视频投稿必须填微信公众号文章链接

### Notes
- 3 个平台（B站/抖音/小红书）端到端实测成功，草稿保存确认
- VLM（glm-5v-turbo）用于分析每步截图，验证页面实际状态
- HTML 快照分析是找 selector 的关键方法
- Shadow DOM 用 piercing selector 或坐标点击解决

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
