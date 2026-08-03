# 一键发布系统可行性评估

> 评估日期：2026-08-03 (GMT+8)
> 评估范围：13个中文内容平台视频批量发布到草稿
> 评估目标：判断"agent代填表+存草稿+编辑复核后发布"的工程可行性，为下一阶段编程做准备

---

## 一、结论：可行性 = 中等可行，分阶段交付

**总评**：构建一套"agent代为填写13个平台后台表单并保存为草稿、编辑复核后一键发布"的系统是**可行**的，但**不能一蹴而就**，必须按平台难度分4个Tier分批交付。预期总工期 6-8 周（v1 覆盖 11/13 平台，2 个平台走半自动流程）。

**核心策略**：
- **Fork** `dreammis/social-auto-upload` (14k stars, MIT, Python+Playwright) 作为底座
- **改造方向**：把"直接发布"改为"保存为草稿"，所有 adapter 默认只到草稿环节
- **新增 7 个 adapter**：微博视频、腾讯视频、喜马拉雅、虎嗅、36氪、支付宝生活号、企鹅号
- **统一抽象**：CoverImageProcessor（处理横屏/竖屏/裁剪）、TagNormalizer（处理 # 格式与数量上限）、TitleTrimmer（处理字数限制）
- **新增调度层**：一份素材 metadata JSON → 13 个平台 adapter 并行/串行调用 → 各平台返回 draft URL 汇总成报表

---

## 二、技术架构建议

### 2.1 整体技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 浏览器自动化 | **Playwright + patchright** | patchright 是 social-auto-upload 已采用的 stealth fork，绕过小红书等反爬 |
| 编程语言 | **Python 3.11+** | 与 social-auto-upload 一致，生态最成熟 |
| 任务编排 | **CLI (Click/Typer) + 后续可选 FastAPI** | 先 CLI 让编辑本地跑，后期可加 HTTP API 给远程调用 |
| 配置管理 | **YAML + JSON Schema 校验** | 编辑填一份 metadata.yaml，schema 校验后分发 |
| 凭据存储 | **本地加密 + cookie JSON 文件** | cookie 文件存本地 `~/.vidsync/cookies/<platform>.json`，**绝不上传 GitHub** |
| 日志/审计 | **结构化 JSON 日志 + 每次运行生成 markdown 报告** | 编辑能看到"哪个平台成功/失败/草稿URL" |
| 封面处理 | **Pillow + ffmpeg** | 自动从源视频截帧 + 按 13 种规格裁剪 |
| GUI（可选 v2） | **Electron 或 Web UI** | 编辑同事无需命令行；但 v1 先不做 |

### 2.2 模块拆分

```
vidsync/
├── cli/                          # CLI 入口
│   ├── publish.py                # 主命令：vidsync publish --meta meta.yaml
│   ├── login.py                  # 登录引导：vidsync login <platform>
│   └── report.py                 # 生成报告
├── adapters/                     # 13 个平台 adapter
│   ├── base.py                   # 抽象基类：login/save_draft/upload_cover/set_tags
│   ├── bilibili.py               # ← 来自 social-auto-upload
│   ├── douyin.py                 # ← 来自 social-auto-upload
│   ├── xiaohongshu.py            # ← 来自 social-auto-upload
│   ├── kuaishou.py               # ← 来自 social-auto-upload
│   ├── wechat_channels.py        # ← 来自 social-auto-upload（tencent_uploader）
│   ├── baijiahao.py              # ← 来自 social-auto-upload
│   ├── weibo.py                  # ← 新建
│   ├── tencent_video.py          # ← 新建
│   ├── ximalaya.py               # ← 新建（用 open.ximalaya.com）
│   ├── huxiu.py                  # ← 新建（半自动，提交公众号链接）
│   ├── kr36.py                   # ← 新建（半自动，需作者认证）
│   ├── alipay.py                 # ← 新建（用 opendocs.alipay.com OpenAPI）
│   └── qq_shizi.py               # ← 新建（用 RSS sync）
├── processors/
│   ├── cover.py                  # 13 种封面规格裁剪
│   ├── tags.py                   # 标签格式归一化（# / ## / 无 #）
│   ├── title.py                  # 标题字数裁剪（抖音 55字含话题 / B站 80字 / 微博 6-30字）
│   └── video.py                  # 视频转码（H.265→H.264 for Chrome 上传）
├── schema/
│   └── metadata.yaml             # 编辑填写的统一 metadata 模板
├── cookies/                      # 本地 gitignored
│   └── <platform>.json
└── reports/
    └── <timestamp>/              # 每次运行结果
```

### 2.3 工作流（编辑视角）

```
[编辑同事准备素材]
  ├── video.mp4 (主视频)
  ├── cover-master.png (主封面 1920×1080)
  ├── meta.yaml (标题/描述/标签/分类)
  └── (可选) cover-vertical.png (竖屏专用)

[编辑执行]
  $ vidsync login --all           # 首次：扫码登录 13 个平台
  $ vidsync publish --meta meta.yaml --dry-run   # 校验
  $ vidsync publish --meta meta.yaml             # 正式：所有平台保存草稿

[vidsync 内部]
  1. 解析 meta.yaml，schema 校验
  2. 调用 processors/cover.py 生成 13 套封面
  3. 调用 processors/tags.py 转换标签格式
  4. 并行调用 13 个 adapter 的 save_draft()
  5. 收集所有 draft URL，生成 reports/<ts>/summary.md

[编辑同事后续]
  - 打开 summary.md，逐个点击 draft URL 复核
  - 在各平台后台修改（如需要）→ 手动点发布
```

---

## 三、平台难度分层与时间估算

### Tier 1 — 自动化最成熟（已有 open-source adapter，1-2周）

| 平台 | 来源 | 工作量 | 风险 |
|------|------|--------|------|
| 抖音 | social-auto-upload | 1d（改为 draft 模式） | SMS 二次验证可能中断 |
| B站 | social-auto-upload + biliup | 2d（cover 1146×717 适配） | 草稿 10 天过期需提示编辑及时复核 |
| 快手 | social-auto-upload | 1d | 原创标签需手动 toggle |
| 小红书 | social-auto-upload | 2d（cover 3:4，GeoIP fallback） | creator.rednote.com 备用域名 |

### Tier 2 — 可适配但需额外处理（2-3周）

| 平台 | 来源 | 工作量 | 风险 |
|------|------|--------|------|
| 视频号 | social-auto-upload (tencent_uploader) | 3d | H.265 必须转 H.264；WeChat 设备指纹强 |
| 百家号 | social-auto-upload | 2d | 垂直度评分（不可乱切分类） |
| 支付宝生活号 | 新建（OpenAPI） | 4d | **官方 OpenAPI 最完善**，可不走浏览器 |
| 企鹅号 | 新建（RSS sync） | 3d | RSS 仅同步公众号文章；视频走浏览器自动化 |

### Tier 3 — 需自建 adapter，难度中（2-3周）

| 平台 | 方案 | 工作量 | 风险 |
|------|------|--------|------|
| 微博视频 | 浏览器自动化 | 3d | 双#标签转换；6字最低标题限制 |
| 腾讯视频 | 浏览器自动化 | 4d | album 结构；长期视频定位 |
| 喜马拉雅 | open.ximalaya.com OpenAPI | 4d | album 必填；1400×1400 album 封面 |

### Tier 4 — 编辑审稿平台，无法完全自动化（半自动方案）

| 平台 | 方案 | 工作量 | 说明 |
|------|------|--------|------|
| 虎嗅 | 半自动：agent 提交微信公众号链接 | 2d | 编辑审稿后会改稿，agent 只能填初始投稿表单 |
| 36氪 | 半自动：作者认证一次后，agent 填投稿表单 | 3d | misopen 是 JS SPA，需 Playwright；作者认证不可自动化 |

### 总工期

- **v1 (Tier 1+2，9个平台)**：3-4 周
- **v2 (Tier 3，3个平台)**：+2 周
- **v3 (Tier 4，半自动2个平台)**：+1 周
- **总计**：6-8 周（含调试、文档、编辑培训）

---

## 四、关键风险与对策

### 4.1 Cookie 失效问题（最大风险）

所有非 OpenAPI 平台（11/13）依赖 cookie 持久化。Cookie 失效是发布失败的最常见原因。

**对策**：
- 每个 adapter 启动时检测 cookie 是否过期，过期则引导编辑扫码登录
- 引入 `vidsync doctor` 命令：一次性检查所有平台 cookie 健康度
- cookie 文件本地存储，**绝不写入 GitHub repo**（.gitignore 强制排除）
- 编辑同事首次运行 `vidsync login --all` 时，按平台逐个扫码，预计 15-30 分钟一次性完成

### 4.2 反爬虫对抗

| 平台 | 反爬措施 | 对策 |
|------|---------|------|
| 小红书 | 检测 Electron/Headless | 用 patchright + 真实 Chrome 模式 |
| 视频号 | 设备指纹 | 持久化 storageState，禁止清缓存 |
| 抖音 | SMS 二次验证 | 提供 `verify_code.txt` 机制，编辑手动输入验证码 |
| 微博 | 滑块验证 | 失败时降级为半自动（打开浏览器让编辑手动滑） |
| B站 | WBI 签名 | 用 `biliup` 工具自动处理 |

### 4.3 平台 UI 变更

平台前端 UI 变更频繁，selector 容易失效。

**对策**：
- 每个 adapter 内置 health check：登录后访问发布页，验证关键 selector 是否存在
- selector 失效时，自动截图 + 失败原因写入报告
- 编辑看到失败报告后，可手动用浏览器打开各平台后台填写（fallback 方案）

### 4.4 封面规格差异

13 种平台对封面的要求差异极大（详见 research/02-platform-requirements.md）。

**对策**：建立 `CoverImageProcessor`：
- 输入：1 张主封面（推荐 1920×1080 横屏 master）+ 1 张竖屏封面（1080×1920）
- 输出：13 张按平台规格裁剪的封面
- 关键裁剪规则：
  - B站/虎嗅：横屏 1146×717 / 800×450
  - 抖音/小红书：竖屏 1080×1440 / 1080×1920
  - 视频号：6:7 = 1080×1260（朋友圈分享会裁成 1:1，需 center safe zone）
  - 36kr/腾讯：二次裁剪不可控，建议主封面主体居中
  - 喜马拉雅：1400×1400 方形（album 封面）

### 4.5 标签格式差异

| 平台 | 标签数量上限 | 格式 |
|------|-------------|------|
| B站 | 10 | 自由标签，无 # |
| 抖音 | 5 话题 | #话题（单 #） |
| 小红书 | 10 | #话题（单 #） |
| 微博 | 不限 | #话题#（双 #） |
| 视频号 | 10 | #话题# |
| 36氪 | 5 | 自由 |
| 其他 | 各异 | 各异 |

**对策**：`TagNormalizer`：
- 输入：`tags: [标签1, 标签2, ..., 标签15]`
- 输出：每个平台一份格式化后的 tag 字符串
- 截断规则：按平台优先级截断（编辑在 meta.yaml 里可标记 tag 优先级 `[*高优, 普通, 普通]`）

### 4.6 标题字数差异

| 平台 | 上限 | 注意 |
|------|------|------|
| 抖音 | 55字 | **含 #话题**，实际可用仅 30-40 字 |
| B站 | 80字 | 推荐 ≤25字 |
| 微博 | 30字 | 且 ≥6字（最低限制） |
| 视频号 | 30字 | |
| 小红书 | 20字 | 最严 |
| 虎嗅 | 60字 | |
| 其他 | 30-80字 | |

**对策**：`TitleTrimmer`：
- 输入：主标题（推荐 ≤20字）+ 副标题（可选）
- 各平台用不同截断策略
- 抖音的特殊处理：标题 + 话题总长 ≤55 字，话题优先

---

## 五、对外部依赖的处理

### 5.1 cookies 需求清单（操作员须知）

**操作员（视频编辑同事）首次配置时需要做**：

1. 在自己电脑上安装 Python 3.11+ 和 vidsync CLI（届时会提供一键安装脚本）
2. 运行 `vidsync login --all`，按提示逐个扫码登录以下 11 个平台（**支付宝生活号和喜马拉雅走 OpenAPI，不需要扫码**）：

| # | 平台 | 登录方式 | 预计耗时 | 二次验证 |
|---|------|---------|---------|---------|
| 1 | 微信视频号 | 微信扫码 | 30s | 偶尔 |
| 2 | 哔哩哔哩 | B站APP扫码 或 SMS | 30s | 偶尔 |
| 3 | 企鹅号 | QQ扫码 | 30s | 偶尔 |
| 4 | 腾讯视频 | QQ/微信扫码 | 30s | 无 |
| 5 | 微博 | 微博APP扫码 | 30s | 偶尔 |
| 6 | 百家号 | 百度APP扫码 | 30s | 偶尔 |
| 7 | 虎嗅 | 手机号 + SMS | 1min | 首次需 |
| 8 | 36氪 | 手机号 + SMS + 作者认证 | 5min（首次） | 首次需 |
| 9 | 抖音 | 抖音APP扫码 | 30s | **较频繁** |
| 10 | 快手 | 快手APP扫码 | 30s | 偶尔 |
| 11 | 小红书 | 小红书APP扫码 | 30s | 偶尔 |

**总耗时**：约 15-25 分钟（首次）

3. **支付宝生活号** 和 **喜马拉雅** 走 OpenAPI，需要操作员去对应开放平台申请 API key：
   - 支付宝：https://opendocs.alipay.com → 创建小程序/应用 → 获取 app_id + private_key
   - 喜马拉雅：https://open.ximalaya.com → 创建应用 → 获取 client_id + client_secret

4. cookie 和 API key 文件会自动保存在 `~/.vidsync/`，**不会上传 GitHub**

### 5.2 cookies 过期处理

- 大部分平台 cookie 有效期 30 天左右
- 编辑每周运行一次 `vidsync doctor` 检查健康度
- 失效的平台会提示重新扫码

---

## 六、不重复造轮子的判断

### 6.1 直接复用

| 来源 | 复用部分 | 改造工作 |
|------|---------|---------|
| `dreammis/social-auto-upload` | 6 个 adapter（抖音/B站/小红书/快手/视频号/百家号） | 把 publish 改为 save_draft；增加 cover processor |
| `biliup` (pip 包) | B站 WBI 签名 | 直接 import |
| `patchright` (pip 包) | Playwright stealth fork | 直接 import |
| `social-auto-upload` 的 cookie 持久化机制 | storageState JSON 管理 | 直接复用 |

### 6.2 参考但重写

| 来源 | 参考部分 | 重写原因 |
|------|---------|---------|
| `hanliang97/MatrixMedia` | MCP server + HTTP API 设计 | GPL-2.0 不兼容 MIT |
| `leaperone/MultiPost-Extension` | 浏览器扩展模式 | 我们要的是 CLI，不是扩展 |
| `SocialSisterYi/bilibili-API-collect` | B站 API 文档 | **已 archive**（被B站律师函下架），仅作参考，实际走浏览器自动化 |

### 6.3 必须自建

7 个平台 adapter（微博、腾讯视频、喜马拉雅、虎嗅、36氪、支付宝、企鹅号）+ 封面处理 + 标签归一化 + 标题裁剪 + 报告生成。

---

## 七、下一步建议

### 阶段 0（已完成）
- [x] 调研 13 个平台后台要求（research/02-platform-requirements.md）
- [x] 调研已有开源工具（research/01-existing-tools-survey.md）
- [x] 撰写可行性评估（本文档）

### 阶段 1（建议下一步，2-3周）
- [ ] Fork social-auto-upload，剥离出 6 个 adapter 为独立包
- [ ] 实现 CoverImageProcessor + TagNormalizer + TitleTrimmer
- [ ] 实现 CLI 主命令 + meta.yaml schema
- [ ] 在 Tier 1 平台（抖音/B站/小红书/快手）端到端跑通"保存草稿"
- [ ] 编辑同事试用 v1，反馈

### 阶段 2（2-3周）
- [ ] 增加 Tier 2 平台（视频号/百家号/支付宝/企鹅号）
- [ ] 实现 `vidsync doctor` cookie 健康检查
- [ ] 实现 `vidsync report` 生成 markdown 草稿清单

### 阶段 3（2周）
- [ ] 增加 Tier 3 平台（微博/腾讯视频/喜马拉雅）
- [ ] 增加 Tier 4 半自动流程（虎嗅/36氪）

### 阶段 4（1周）
- [ ] 编辑培训 + 文档
- [ ] 上线试运行

---

## 八、需要用户决策的事项

1. **是否同意 fork social-auto-upload 作为底座**？（MIT 协议，可商用，可闭源）
2. **是否同意 v1 只覆盖 9 个平台（Tier 1+2），Tier 3+4 后续迭代**？
3. **支付宝生活号和喜马拉雅是否一定要走 OpenAPI**？还是和其它平台一样走 cookie 浏览器自动化（架构更统一但工作量增加）？
4. **编辑同事的电脑环境**：Windows / Mac / Linux？（影响打包方式）
5. **是否需要 Web UI / GUI**，还是 CLI 足够？（CLI 快，GUI 编辑同事更友好）
6. **是否需要多账号支持**？（同一平台多个账号）
7. **视频素材通常存在哪里**？本地文件 / OSS / 网盘？（影响 CLI 输入方式）
