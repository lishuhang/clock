# CLI Skill使用指南

> 来源：https://nadoupro.iqiyi.com/docs/cli-skill-guide
> 抓取时间：2026-09-23 08:44（离线快照，原文见链接）



# 纳逗 Pro CLI 功能介绍 [​](#纳逗-pro-cli-功能介绍)

本文面向使用纳逗 Pro CLI 的用户和 Agent，介绍安装、登录、模型发现、内容生成、任务交付、空间管理、本地媒体处理与 Canvas 操作。CLI 的具体能力会随版本、账号和场景变化，请以 `nadou capability list --json`、命令返回结果和实际产物为准。

建议

安装或升级后先运行 `nadou version --json` 和 `nadou capability list --json`，确认当前版本与可用能力。

WARNING

涉及写入、生成、删除或覆盖的操作，遵循“一次提交、不自动重试、结果不确定时查询原任务”的原则。不要分享或记录 Cookie、token、Authorization 等登录凭证。

## 1. 快速开始 [​](#_1-快速开始)

### 1.1 安装 [​](#_1-1-安装)

需要 Node.js 16 或更高版本。推荐通过 npm 公共仓库安装：

**一句话安装指令：** 请帮我安装纳逗 Pro CLI：`npm install -g @iqiyinadoupro/nadou-cli`。安装完成后可运行 `nadou version --json` 验证。

bash

```
npm exec --yes --registry=https://registry.npmjs.org/ --package=@iqiyinadoupro/nadou-cli@latest -- nadou-install
nadou version --json
nadou skill install --json
nadou skill read --json
```

也可以全局安装：

bash

```
npm install -g @iqiyinadoupro/nadou-cli
nadou version --json
```

当前支持 Windows x64、Linux x64/arm64、macOS x64/arm64。npm 会自动选择对应平台的依赖；如果安装时关闭了 optional dependencies，请使用正常安装方式重新安装。

### 1.2 检查更新并升级 [​](#_1-2-检查更新并升级)

bash

```
nadou version --check --json
nadou update --json --no-interactive
nadou version --json
```

升级完成后建议再次运行 `nadou skill install --json`，确保本机 Skill 与 CLI 版本保持一致。

### 1.3 配置并登录 [​](#_1-3-配置并登录)

登录会打开系统浏览器，由用户完成扫码或账号验证。Profile 用于保存环境和空间等非敏感配置，登录会话保存在本机系统凭证库。

bash

```
nadou auth login --profile <profile>
nadou auth status --profile <profile> --json
nadou auth whoami --profile <profile> --json
```

请将 `<profile>` 替换为本机实际使用的 Profile 名称；如果使用默认 Profile，可按 CLI 提示省略该参数。不要手工复制、粘贴或记录 Cookie、token 和 Authorization。

### 1.4 Agent 使用前检查 [​](#_1-4-agent-使用前检查)

Agent 会话与普通终端可能使用不同的 PATH、配置目录或系统凭证库。遇到“命令找不到”“配置不可读”或“身份校验失败”时，先重启 Agent，再执行：

1. `nadou version --json`
2. `nadou auth status --profile <profile> --json`
3. `nadou auth whoami --profile <profile> --json`

只有确认登录状态确实失效时，才重新登录。

## 2. 能力总览与统一约定 [​](#_2-能力总览与统一约定)

### 2.1 命令面 [​](#_2-1-命令面)

| 能力域 | 主要命令 | 作用 |
| --- | --- | --- |
| 系统与 Skill | `version`、`update`、`config`、`doctor`、`skill`、`capability` | 版本、配置、诊断、Skill 同步和能力发现 |
| 身份与空间 | `auth`、`points`、`space` | 登录、积分、空间、目录和交付目标 |
| 模型与生成 | `model`、`text`、`image`、`video`、`material` | 模型发现、文本/图片/视频任务和素材管理 |
| 任务与交付 | `task`、`schedule`、`evidence` | 估价、提交、观察、下载、定时、报告和验收证据 |
| Canvas | `canvas` | 画布、Graph、节点、连线、Timeline 和成片导出 |
| 本地媒体 | `media` | 处理本地文件，不替代服务端生成任务 |

完整命令和当前开放范围以 `nadou capability list --json` 为准；单项能力可用 `nadou capability describe <command> --json` 查看作用、限制、异步性和参考命令。

### 2.2 输出与全局参数 [​](#_2-2-输出与全局参数)

所有命令支持稳定的 `--json` 输出；长时间观察、事件流和递归目录内容可使用 `--jsonl`。常用全局参数包括 `--profile`、`--timeout`、`--trace-id`、`--no-interactive` 和 `--yes`。

- `--json`：返回适合程序处理的结构化结果。
- `--jsonl`：按行输出事件或递归结果，便于持续观察。
- `--no-interactive`：关闭交互提示，不代表费用确认。
- `--yes`：确认删除、覆盖等破坏性操作，不代表费用授权。
- `--trace-id`：用于关联一次工作流的排查信息，不等同于任务 ID 或幂等键。

### 2.3 Profile、空间与项目边界 [​](#_2-3-profile、空间与项目边界)

Profile 保存环境、网关地址、超时、认证模式、默认空间和默认模型等非敏感配置。空间、模型和 Canvas 上下文需要分别发现和选择；切换空间不会隐式创建或恢复其他项目绑定。

### 2.4 场景路由 [​](#_2-4-场景路由)

| 场景 | 推荐承载 | 执行要点 |
| --- | --- | --- |
| 单个文本、图片、视频或其他原子能力 | 原子任务 | 提交前确认参数、目标空间、权限和预计消耗。 |
| 多个素材、多个阶段、角色一致性、MV、广告或短片 | 目标空间/目录 + Canvas | 先明确账号、空间和目录；完成剧本或分镜后再进入高成本阶段。 |
| 修改已有 Canvas | 读取并修改原 Canvas | 写入前读取实时画布，写入后回读复验；覆盖、删除或冲突时先确认。 |
| 定时生成 | CLI 当前开放的定时模式 | 创建前确认时间、时区、账号、空间和预计消耗。 |

用户明确提到纳逗 Pro、文本、图片、视频、素材、空间、画布、节点、参考图、首尾帧等场景时，优先使用纳逗 Skill。当前 CLI 不支持的能力应明确说明，不要用相似能力代替。

## 3. 模型发现与内容生成 [​](#_3-模型发现与内容生成)

### 3.1 先发现模型和场景 [​](#_3-1-先发现模型和场景)

bash

```
nadou model family --json
nadou model scenarios --type image --json
nadou model scenarios --type video --json
nadou model list --type image --json
nadou model get <model-id> --json
nadou model schema <model-id> --json
nadou model use image <image-model> --profile <profile>
nadou model use video <video-model> --profile <profile>
```

模型显示名、参数和可用场景由服务端目录决定。不要在 Agent 或脚本中猜测模型名；先读取场景或 Schema，再提交匹配的参数。

### 3.2 生成能力与场景 [​](#_3-2-生成能力与场景)

| 命令 | 常见场景 | 关键输入 |
| --- | --- | --- |
| `nadou text` | `text2text`、`image_to_text` | 提示词、可选 HTTPS 参考图 |
| `nadou image` | `text2img`、`image_ref`、`panorama`、`three_view`、`inpaint` | 提示词、参考图、遮罩、比例、分辨率、数量 |
| `nadou video` | `text2video`、`first_last_frame`、`multi_reference`、`video_edit`、`motion_control` | 提示词、时长、比例、分辨率、参考视频/图片/音频 |

提示词可以通过位置参数、`--prompt-file` 或 `--stdin` 提供，最大 1 MiB 且必须是有效 UTF-8。`--dry-run` 只构造并校验请求，不会提交任务；图片和视频默认只提交不等待，使用 `--wait` 才会在同一条命令中观察完成。

当前 CLI 没有独立的 AI 音频生成命令。视频任务可以按场景使用参考音频、音频设置或保留原声参数，但这不等同于独立音频生成。

### 3.3 费用、确认与交付 [​](#_3-3-费用、确认与交付)

DANGER

可能产生费用的任务，建议按“dry-run → 查询积分 → 估价 → 说明预计消耗并确认 → 正式提交”的顺序执行。余额显示为空、无限或暂时无法确认时，也不能跳过估价、预算说明和最终确认。

对应命令通常为 `nadou points summary`、`nadou task estimate` 和 `nadou task submit`。估价不锁定最终价格，提交前仍需按实际返回结果确认。

独立图片/视频生成与产物交付是两个阶段。默认交付到个人根目录；团队空间、目录以及复制或转移策略需要显式指定。CLI 不默认下载产物，也不默认执行本地媒体处理。

## 4. 任务、定时、交付与证据 [​](#_4-任务、定时、交付与证据)

### 4.1 任务生命周期 [​](#_4-1-任务生命周期)

常用命令包括 `task estimate`、`task submit`、`task status`、`task wait`、`task events`、`task outputs`、`task report`、`task history`、`task download`、`task download-batch` 和 `task terminate`。

`task events` 可用于持续观察；批量下载使用可恢复的 manifest，适合长任务或多产物交付。提交写操作不自动重试。进程中断、网络超时或响应无法解析时，先查询原 task、request 或状态记录，不要创建新的提交再试。

### 4.2 定时任务 [​](#_4-2-定时任务)

定时能力需要显式选择 `disabled`、`local` 或 `server`，并使用 IANA 时区。创建前先确认时间、时区、账号、空间和预计消耗，再按当前 capability 选择模式。

| 模式 | 适用方式 | 主要限制 |
| --- | --- | --- |
| `server` | 图片/视频或部分 Canvas 节点生成 | 不承诺通用文本计划、计划管理或 DAG 编排。 |
| `local` | 普通图片/视频和独立文本生成 | 不包含 Canvas、项目上下文或外部引用 URL。 |

示例：`nadou schedule create --body-file request.json --scheduled-at <time> --timezone <iana-timezone>`。具体支持范围以命令返回结果为准。

### 4.3 空间、目录和素材 [​](#_4-3-空间、目录和素材)

- `space current/list/use`：查看和切换空间。
- `space directory create/list/contents`：管理目录和查看内容；递归内容可使用 `--recursive --jsonl`。
- `space file rename`：显式重命名文件。
- `space artifact deliver`：将可信任务产物复制或转移到目标空间或目录。
- `material upload`：上传本地素材，支持分片流程和可选水印参数。
- `material delete`：删除素材；永久删除需要显式使用 `--permanent` 并确认。

上传素材不等于交付任务产物，也不会自动创建 Canvas 节点。

### 4.4 验收证据 [​](#_4-4-验收证据)

`evidence generation` 可从已知 task ID 生成版本化本地证据；`evidence delivery` 可结合下载 manifest、媒体文件、技术校验结果和人工确认生成交付证据；`evidence validate` 只校验证据结构、路径、哈希和引用，不会触发重试、下载、交付或 Canvas 写入。

技术校验通过不等于创意质量审核。正式交付建议保留版本、task ID、脱敏 request ID、产物哈希、媒体检查结果和必要的人工确认，不要保存 token、Cookie 或完整 Authorization。

### 4.5 Agent 交互、产物呈现与恢复 [​](#_4-5-agent-交互、产物呈现与恢复)

提交前，如果账号、空间、目录或 Canvas 不唯一，必须先说明选项和预计保存位置；如果模型参数、首尾帧角色或批量规模不明确，必须先补齐信息；涉及批量、高成本、删除、覆盖、移动或协同冲突时，必须先说明影响并取得确认。

- 图片：说明实际数量，返回每个真实产物和空间路径。
- 视频或其他媒体：返回真实播放/下载入口和空间路径；任务页或缩略图不能代替最终产物。
- 文本：直接呈现正文；没有保存到空间时，明确说明原因。
- 复杂 Canvas：呈现最终产物、空间路径、Canvas 名称和真实入口，并区分已完成与未完成阶段。
- 部分成功：先交付成功项，再分别列出失败项和补做选项，不把整单伪装成完全成功或完全失败。

DANGER

空间路径和真实产物入口是交付信息的一部分。没有服务端真实返回值或没有完成下载时，不要把本地路径、任务页或中间状态称为最终产物。

每个写入或提交步骤只执行一次。超时、网络异常或响应无法解析时，查询原 task 或原操作状态；不要更换幂等键、重复提交或因为暂时没有结果而重新生成。生成失败、版权限制或模型拒绝时，停止下游步骤；用户取消时只执行一次取消并核对最终状态。

## 5. 本地媒体处理 [​](#_5-本地媒体处理)

`nadou media` 只处理本地文件，不调用网络生成服务，不修改输入文件，默认拒绝覆盖已有输出。支持检查、标准化、拼接、合成、抽帧、技术校验、字幕处理以及音视频混流等操作。

常用标准预设包括横屏、竖屏和正方形 1080p；常规输出为 MP4/H.264、yuv420p、30fps、AAC-LC、48kHz、立体声。`verify` 是技术检查，报告中的 `creative_review_required` 仍表示需要人工审看。

本地媒体处理与 Canvas Timeline/成片导出是两套能力：前者处理本地文件，后者读写 Canvas Graph 关联的时间轴并执行服务端成片任务。

## 6. Canvas 管理与 Graph [​](#_6-canvas-管理与-graph)

### 6.1 操作原则 [​](#_6-1-操作原则)

1. 先用 `canvas get` 读取目标画布的最新状态。
2. 根据当前节点、连线和布局构造一次写入。
3. 写入完成后再次读取，确认节点、连线和产物状态。
4. 遇到锁定、协同冲突、权限问题或结果不明确时停止继续写入，先查看原操作状态并说明影响。

CLI 会按节点类型校验可写字段。用户只需要关注命令、输入、输出、状态和错误处理，不需要直接拼接服务地址、资源 URL 或任务状态。

### 6.2 常用命令 [​](#_6-2-常用命令)

| 类别 | 命令 |
| --- | --- |
| 生命周期 | `canvas list/create/get/rename/move/delete/restore` |
| 读取 | `canvas get`、`canvas node list`、`canvas assets list` |
| Graph | `canvas graph mutate` |
| 节点 | `canvas node list/create/patch/delete/estimate/generate/wait` |
| 连线 | `canvas edge connect/patch/delete` |
| Timeline | `canvas media timeline validate/write/read` |
| 成片 | `canvas media export prepare/submit/observe` |

### 6.3 画布、节点与素材 [​](#_6-3-画布、节点与素材)

`canvas list` 用于发现当前可访问的画布；`canvas get` 用于读取实时 Graph；`canvas node list` 用于按类型查看节点；`canvas assets list` 用于查看历史素材或产物投影。列表结果不应被当作写入前的实时快照。

自定义媒体节点应使用公开的 Canvas 节点命令，并以素材 ID 等受支持字段作为输入。不要由 CLI 外部伪造 URL、metadata、回调或任务状态。画布冲突、锁定和部分失败应按实际错误提示处理，不要创建替代节点掩盖原问题。

### 6.4 Timeline 与成片 [​](#_6-4-timeline-与成片)

Timeline 文件先执行离线校验，再按当前 capability 选择成片流程。Timeline 写入、导出准备、提交和观察都是相互独立的操作，每一步只执行一次；状态查询遇到处理中、未找到或未知结果时，只继续查询原操作，不切换路径或重复提交。

真实成片是否可完成取决于有效的 Canvas 节点、Timeline、任务状态和当前开放能力。发布或交付时应以实际命令返回和最终产物为准。

## 7. 当前 CLI 的能力边界 [​](#_7-当前-cli-的能力边界)

CLI 的开放面可能随版本、账号和场景变化。

部分能力可能在纳逗 Pro 产品内提供，但不代表 CLI 已开放，例如导演台、图片超清、图片编辑与标注、工作台文件管理、剪辑台、音轨编辑和编剧助手。需要这些能力时，请直接使用产品入口，并以产品页面和 CLI 当前 capability 为准。

## 8. 问题定位与反馈 [​](#_8-问题定位与反馈)

### 8.1 常见问题 [​](#_8-1-常见问题)

- \*\*画布节点查不到：\*\*先用 `canvas get` 获取实时 Graph，再确认画布标识、节点类型、节点状态和关联 task 是否仍有效。
- \*\*生成命令在产生 task ID 之前退出：\*\*表示任务尚未提交，不要描述为“生成失败”，也不要重复提交。
- \*\*已经拿到 task ID 后发生超时：\*\*继续查询原 task，不要重新生成。
- \*\*Canvas 写入结果不明确：\*\*查询原操作状态，确认最终画布状态后再决定下一步。
- \*\*Agent 看不到终端登录状态：\*\*先重启 Agent，检查 PATH、配置目录和系统凭证库，再执行第 1.4 节的检查命令。

### 8.2 反馈模板 [​](#_8-2-反馈模板)

反馈至少包含：执行命令、CLI 版本、操作系统和架构、使用的模型、Canvas 标识或 task ID、脱敏 request ID/trace ID、错误码、最终状态和真实产物 URL。

不要附带 Cookie、token、Authorization、完整请求头、本地凭证或其他未脱敏的敏感信息。

### 8.3 常见问答 [​](#_8-3-常见问答)

#### 为什么 dry-run 之后还需要 estimate 和确认？ [​](#为什么-dry-run-之后还需要-estimate-和确认)

`dry-run` 只验证请求结构和参数，不代表服务端估价、余额判断或最终提交。费用相关任务仍需查询积分、估价、说明预算、取得确认并执行一次正式提交。

#### 如何让 Skill 与 CLI 保持一致？ [​](#如何让-skill-与-cli-保持一致)

升级 CLI 后同步执行 `nadou skill install --json`，并用 `nadou capability list --json` 判断当前命令是否实际开放。Agent 运行时优先使用本机同步后的官方 Skill。

#### 为什么没有看到最终产物？ [​](#为什么没有看到最终产物)

先查询原 task 的状态和 outputs，再确认交付空间和目录。不要因为入口延迟、暂时没有缩略图或一次查询失败就重新提交任务。
