# vidsync v0.1

> 视频多平台草稿一键发布系统
> 为中文视频自媒体打造：编辑填一份物料，系统自动在 12 个平台后台保存为草稿，编辑复核后即可发布。

## 这是什么

vidsync 帮你把**一份视频素材**同时填到 **12 个中文内容平台**的后台表单，并保存为**草稿**。编辑点开各平台后台复核无问题即可点发布；有问题可手动修改草稿。

### 支持平台（v0.1）

| # | 平台 | 状态 |
|---|------|------|
| 1 | 哔哩哔哩 (Bilibili) | ✅ v0.1 主测 |
| 2 | 抖音创作者 | 🚧 v0.2 |
| 3 | 小红书 | 🚧 v0.2 |
| 4 | 快手 | 🚧 v0.2 |
| 5 | 微信视频号 | 🚧 v0.2（cookie 易失效） |
| 6 | 百家号 | 🚧 v0.3 |
| 7 | 企鹅号 (QQ Shizi) | 🚧 v0.3 |
| 8 | 腾讯视频 | 🚧 v0.3 |
| 9 | 微博视频 | 🚧 v0.3 |
| 10 | 虎嗅 | 🚧 v0.3（半自动） |
| 11 | 36氪 | 🚧 v0.3（半自动） |
| 12 | 支付宝生活号 | 🚧 v0.4（OpenAPI） |
| - | 喜马拉雅 | ⏸ 暂缓（无 cookie） |

### 设计原则

1. **草稿优先，不直接发布** — 编辑保留最终决定权
2. **真实浏览器，无虚假点击** — 使用 Playwright 驱动本机已安装的 Chrome/Edge，模拟真人操作
3. **不下载 Chromium** — 直接用 `channel='chrome'` 或 `channel='msedge'`，避免套娃
4. **Web UI 优先** — 编辑同事无需命令行；启动后浏览器打开 `http://localhost:8765`
5. **cookies 本地存储** — 绝不上传 GitHub；编辑用 [Get cookies.txt locally](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) 扩展导出
6. **详细 debug 探查点** — 每一步都有日志+截图+HTML 快照，出问题时编辑只需把日志文件发回

## 安装与启动

### 前置条件

- Windows 10/11 或 macOS（v0.1 优先 Win）
- Python 3.10+（[下载](https://www.python.org/downloads/)，安装时勾选 "Add Python to PATH"）
- Google Chrome 或 Microsoft Edge（系统已安装即可，无需额外下载）
- 各平台已在本机浏览器登录过

### 安装步骤（Windows）

1. 解压 vidsync 到任意目录，例如 `D:\vidsync\`
2. 打开 PowerShell（开始菜单搜索 powershell），执行：
   ```powershell
   cd D:\vidsync
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   ```
3. （首次）安装 Playwright Python 驱动（**不会下载 Chromium**，只装驱动）：
   ```powershell
   playwright install --dry-run  # 这步只是确认驱动可用，不会下载浏览器
   ```

### 启动

```powershell
cd D:\vidsync
.venv\Scripts\activate
python -m vidsync.web.main
```

浏览器自动打开 `http://localhost:8765`，编辑同事看到表单。

### 首次配置 cookies

1. 在 Chrome/Edge 安装 [Get cookies.txt locally](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) 扩展
2. 逐个访问下面 12 个平台后台，确保已登录：
   - https://member.bilibili.com
   - https://creator.douyin.com
   - https://creator.xiaohongshu.com
   - https://cp.kuaishou.com
   - https://channels.weixin.qq.com
   - https://baijiahao.baidu.com
   - https://shizi.qq.com
   - https://mp.v.qq.com
   - https://weibo.com
   - https://www.huxiu.com
   - https://misopen.36kr.com
   - https://c.alipay.com
3. 每个平台页面点扩展图标 → "Export" → 保存为 `<域名>_cookies.txt`
4. 把所有 `*.txt` 文件放到 `vidsync/cookies/` 目录
5. 在 Web UI 点"刷新 cookies 缓存"按钮，系统会自动识别

### 如果是 Portable Chrome

如果你的 Chrome 是 portable 版本装在非默认路径，编辑 `vidsync/config.yaml`：

```yaml
browser:
  # 优先使用系统安装的 Chrome；如需指定 portable 路径，取消下行注释
  # executable_path: "D:/PortableApps/Chrome/chrome.exe"
  channel: "chrome"   # 或 "msedge"
  headless: false     # v0.1 必须为 false，方便观察
```

## 使用流程

1. 启动 vidsync（见上）
2. 在 Web UI 填表：
   - 视频文件（拖入）
   - 竖屏封面（视频号规格 1080×1260）
   - 横屏封面（16:9）
   - 短标题（≤12 字）
   - 长标题（≤22 字，超长自动截断）
   - 关键字（5-10 个，逗号分隔）
3. 勾选要发布的平台
4. 点"开始保存草稿"
5. 实时看进度（哪个平台成功/失败 + 草稿 URL）
6. 全部完成后，点各平台草稿链接在新标签打开复核
7. 在各平台后台手动点"发布"

## 出问题怎么办？

vidsync 在 `vidsync/logs/` 下每次运行生成一个日志目录：
```
logs/
└── 2026-08-03_15-10-00/
    ├── run.log               # 主日志（按步骤）
    ├── bilibili/
    │   ├── 01_login.png      # 每步截图
    │   ├── 02_upload.png
    │   ├── 03_form.png
    │   ├── 04_draft.png
    │   ├── page.html         # 失败时最后一页 HTML 快照
    │   └── adapter.log       # 该平台详细日志
    └── summary.json          # 各平台结果汇总
```

**编辑同事只需把 `logs/<最近一次运行>/` 整个文件夹打包发给开发即可**，无需手动 F12 或截图。

## 调试踩坑记录（给后续 agent 和维护者）

> 以下记录实际开发中遇到的问题与对策，避免重复踩坑。

### 踩坑 1：Playwright 默认下载 Chromium

- **现象**：`pip install playwright` 后通常要执行 `playwright install`，会下载 ~150MB Chromium。用户明确要求"尽量不要在程序中再次下载 chromium 套娃"。
- **对策**：使用 `launch_persistent_context(channel='chrome')` 或 `channel='msedge'`，直接驱动系统已安装的 Chrome/Edge。**不需要执行 `playwright install`**。
- **注意**：Playwright Python 包本身需要安装（pip），但浏览器驱动可以用系统 Chrome。

### 踩坑 2：cookies.txt 格式

- **现象**：Get cookies.txt locally 扩展导出的是 Netscape 格式（tab 分隔），不是 JSON。
- **对策**：`processors/cookies.py` 实现了 Netscape parser，转成 Playwright 的 `add_cookies()` 参数格式。

### 踩坑 3：跨域 cookie 注入

- **现象**：`member.bilibili.com` 的 cookies 实际包含 `.bilibili.com` 域和 `member.bilibili.com` 域两类。直接全注入会导致部分 cookie 被浏览器拒绝。
- **对策**：parser 保留原始 domain 字段；Playwright `add_cookies()` 会按 domain 自动分发。

### 踩坑 4：视频号 cookie 易失效

- **现象**：用户反馈 2 小时前登录的视频号现在又要扫码。
- **对策**：v0.1 把视频号排在 adapter 列表最后；失败时降级为"打开浏览器让用户重新扫码"。

### 踩坑 5：抖音 55 字标题含 #话题

- **现象**：抖音标题限制 55 字，**包含 #话题**，实际可用 30-40 字。
- **对策**：`processors/title.py` 对抖音单独截断，话题优先。

### 踩坑 6：B站草稿 10 天过期

- **现象**：B站视频草稿 10 天后自动删除。
- **对策**：在 summary.json 标注 `expires_at`，提醒编辑及时复核。

### 踩坑 7：小红书海外 GeoIP

- **现象**：creator.xiaohongshu.com 海外 IP 被封。
- **对策**：v0.1 国内环境无此问题；海外用 creator.rednote.com。

### 踩坑 8：反编译 API 法律风险

- **现象**：SocialSisterYi/bilibili-API-collect 已被 B 站律师函下架归档（2026-01）。
- **对策**：**不走反编译 API**，统一走浏览器自动化。B站 WBI 签名等用社区维护的 `biliup` pip 包（未被下架）。

### 踩坑 9：Workspace 崩溃导致上下文丢失

- **现象**：sandbox 环境不稳定，会话间 workspace 会被重置。
- **对策**：
  - 所有工作产物 commit 到 GitHub
  - 凭据存本地 `/home/z/my-project/secrets/credentials.env`（gitignore 排除）
  - todo-MMDD-HHMM.md 完整记录工作状态
  - 用户输入"继续"时，先 `git pull` 再读最近 todo

### 踩坑 10：明文凭据绝不能进 GitHub

- **对策**：
  - .gitignore 排除 `cookies/*.txt`、`secrets/`、`*.env`
  - 加密 7z 压缩包可以传（密码仅对话中提供）
  - commit 前自检：`git diff --cached | grep -iE 'token|password|apikey|ghp_|cfut_|_cookies\.txt'`

## 项目结构

```
vidsync/
├── README.md                      # 本文件
├── CHANGELOG.md                   # 版本历史
├── pyproject.toml
├── config.yaml                    # 用户配置（Chrome 路径等）
├── adapters/                      # 12 个平台 adapter
│   ├── base.py                    # 抽象基类
│   ├── bilibili.py                # ✅ v0.1
│   ├── douyin.py                  # 🚧
│   └── ...
├── processors/                    # 物料处理器
│   ├── cookies.py                 # Netscape cookies.txt parser
│   ├── cover.py                   # 封面裁剪
│   ├── tags.py                    # 标签归一化
│   └── title.py                   # 标题截断
├── browser/
│   └── launcher.py                # 浏览器启动器（channel=chrome）
├── web/
│   ├── main.py                    # FastAPI 入口
│   ├── static/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   └── templates/
├── cookies/                       # 本地 cookies（gitignored）
│   └── *.txt
└── logs/                          # 运行日志（gitignored）
    └── <timestamp>/
```

## 许可证

MIT

## 版本

v0.1.0 — 2026-08-03 — 首版，B 站草稿保存端到端跑通
