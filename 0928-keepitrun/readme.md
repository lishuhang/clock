# keepitrun — 全天候定时任务调度系统

**当前版本：1.27（2026-09-29）**

keepitrun 是一个以 Python 实现的常驻定时任务调度器。它按 **GMT+8** 执行 RSS 抓取、摘要合并翻译、微信公众号内容处理和 Photos 同步。所有用户使用、配置、排障和版本信息均以本文件为准。

> **v1.27 发布重点：** 冷启动提速——`90_cleanup` 从逐文件 API 拉全文重建为 Git Trees 一次列全量 + raw CDN 并行拉取 + sha 增量缓存（首扫约 1 分钟，日常秒级），消除 0928 日志中三连 1800 秒超时拖慢冷启动约 90 分钟的问题；同时修正判定语义，裸 "aigc"/"早报" 文件名不再不经内容确认即判删，避免误删正经 AIGC 主题文章。

> **v1.26 发布重点：** 同日版本替换后首次运行只执行今天尚未完成的任务，不再因版本变更重做当日已完成任务；02/92 的 Gemini 与 GLM 模型升级至官方免费档最新版（`gemini-3.8-flash`、`glm-4.7-flash`）。

## 阅读与求助

需要帮助时，请直接打开 `readme.md`。不要运行或恢复 `readme.py`；该旧文件已移除，以防可执行文档和说明文档发生分歧。

```bat
notepad readme.md
python keepitrun.py
```

## 活动任务与命名规则

活动脚本均使用 **两位顺序号、下划线、kebab-case 名称**，即 `NN_name-with-hyphens.py`。编号代表每日自动任务的逻辑顺序；同一脚本在一天内可按其调度时间多次运行。

| 编号 | 脚本 | 自动时间（GMT+8） | 作用 |
|---:|---|---|---|
| 01 | `01_getrss.py` | 02:00、14:00 | 抓取 RSS、过滤关键词，并把 Google News、Techmeme 等聚合链接还原、规范化为文章原址。 |
| 02 | `02_combine-gemini.py` | 14:05 | 合并 RSS 与未取走摘要，按最终 URL 去重、翻译、分类，并留下唯一最新摘要。 |
| 03 | `03_convert-daily.py` | 10:05 | 以远程 daily 仓库日期差集抓取并发布 AIGC 早报；上传图片前读取 daily 的 `_config.yml`，自动选择图床。 |
| 04 | `04_convert-blog.py` | 10:10 | 抓取并同步微信公众号博客文章；上传图片前读取主站 `_config.yml`，自动选择图床。 |
| 05 | `05_photos-update.py` | 15:00 | 同步 Photos 图片库；每个待同步月份读取 photos 的 `_config.yml`，自动扫描对应图床并写入展示 URL。 |
| 90 | `90_cleanup-daily-from-blog.py` | 首次启动时的维护步骤 | 检查并清理历史误入主博客的 daily 内容；trees API 一次列全量、raw CDN 并行拉取、sha 增量缓存（`cleanup_scan_memory.json`）断点续扫，先预览再执行。 |
| 91 | `91_compress-images.py` | 手动 | 图片压缩维护工具；优先使用系统工具（oxipng/jpegoptim/gifsicle），任一格式缺失时回退纯 Pillow（随包 exe 已移除）。 |
| 92 | `92_model-process.py` | 手动 | 可选的模型后处理工具。 |

**Unsplash 与马良注册已从自动任务、主调度器、环境变量模板和发行包中移除。** 相关历史版本说明仅保留在下方更新日志中，不再代表可用功能。

## RSS 增量摘要规则

`01_getrss.py` 在抓取阶段会优先把聚合链接还原为文章原址：Google News 的重定向 URL 会直接解码；Techmeme 会保留 Techmeme 的标题/摘要文字，但链接替换为对应原文报道。它会去掉 URL 片段和不用于定位文章的追踪参数，并保留全部候选条目交给 02 合并器。

`02_combine-gemini.py` 使用与抓取阶段一致的最终 URL 规则。相同 URL 的多个条目只保留**文字说明最长**的一条；这条规则同时应用于当天两次 RSS 抓取、跨日积压摘要和人工传入的 RSS Markdown 文件。

主调度器会把所有子脚本的 stdout/stderr 逐行实时写入当天总日志和控制台；长时间翻译或超时时，可按 `[02_combine-gemini.py]` 前缀定位最后完成的步骤。

根目录中的 `YYYYMMDD-HHMMSS.md` 是**尚未被用户取走的 RSS 摘要**。如果运行合并器时发现两个或以上此类文件，或发现历史误后缀 `YYYYMMDD-HHMMSS.py`，它会将它们与新 RSS 文件一起去重、翻译并生成一个新的 `.md`。新文件以原子方式写入成功后，旧摘要才会删除。因此，不论积压多少天，目录最终只保留一个最新摘要；其内容覆盖用户上次取走摘要后至今的全部不重复条目。

用户取走摘要后，应将根目录中的该 `YYYYMMDD-HHMMSS.md` 移出或删除。若保留，下一次合并会把它视为待领取内容而继续累计。

自 v1.25 起，合并器还会把本次写入摘要的每个条目（按最终 URL，无链接项按标题文本）记入根目录 `rss_issue_memory.json`。该记忆保留 **24 小时**：即使摘要已被用户取走，过去 24 小时内已提取过的条目再次出现时也会被跳过，不会重复进入新摘要；超过 24 小时的记录在每次运行时自动修剪。因此同一条新闻在早晨与下午两批 RSS 中重复时，下午摘要不会再包含它。

## 翻译与保底策略

RSS 标题按以下顺序翻译：**Gemini → GLM HTTP API → Google Free Translate**。每个可用引擎都有重试；若整个批次的所有引擎均不可用，合并器仍会保留原始标题，确保当天摘要文件生成。

GLM 对个别内容返回拒绝性文本时，合并器会识别常见拒绝提示并直接保留该条的英语原文，而不是把拒绝提示写入摘要或丢弃条目。若 GLM HTTP API 对整批请求返回“输入或生成内容可能包含不安全或敏感内容”一类安全拦截，合并器会输出明确警告、继续尝试下一引擎；若无可用引擎，仍保留该批所有英语标题与摘要。其他正常条目仍会使用其返回的中文翻译。

## 目录结构

```text
keepitrun/
├── keepitrun.py                    常驻主调度器
├── 01_getrss.py                    RSS 抓取、URL 规范化与最长说明去重
├── 02_combine-gemini.py            RSS/积压摘要合并、翻译与分类
├── 03_convert-daily.py             AIGC 早报处理
├── 04_convert-blog.py              博客文章处理
├── 05_photos-update.py             Photos 同步
├── image_routing.py                 image_prefixes 配置解析与上传路由
├── 90_cleanup-daily-from-blog.py   手动维护清理工具
├── 91_compress-images.py           图片压缩工具
├── 92_model-process.py             可选模型后处理工具
├── readme.md                       唯一用户说明与更新日志
├── .env.example                    环境变量模板；不含实际凭据
├── keywords.json                   RSS 关键词配置
├── rss_feeds.json                  RSS 订阅源配置
├── rss_issue_memory.json           02 的 24 小时已提取条目记忆（运行时生成）
├── tmp/                            RSS 中间文件
├── logs/                           日志与任务完成记录
└── archived/                       已处理内容归档
```

发行包和 GitHub 提交中不得包含 `.env`、账号记录、日志、临时文件、用户文章、图片、令牌、Cookie 或其他凭据。只可包含 `.env.example`。

## 安装、配置与启动

需要 Python 3.9+、pip 和网络连接。使用 `.env.example` 创建本地 `.env`，并自行填入必要的值；不得将 `.env` 上传到 GitHub、聊天记录或交接文档。

```bat
pip install feedparser beautifulsoup4 google-generativeai pypinyin requests python-dotenv Pillow
python keepitrun.py
```

典型配置仅包括内容同步与 RSS 翻译所需的值。GLM 回退使用标准 HTTP API，不依赖 `zhipuai` Python 包。若需要凭据，请向配置所有者索取；不要把实际值写入代码、说明或 `todo-*.md`。

## 图床路由配置

`03_convert-daily.py`、`04_convert-blog.py` 和 `05_photos-update.py` 不再将图片仓库硬编码为唯一目标。每次需要传图或扫描图片时，它们都会使用 GitHub Contents API 读取**目标站点** `_config.yml` 的 `image_prefixes`，并按图片所属月份选择唯一规则。配置使用半开区间 `[起始月份, 截止月份)`；例如截止值 `"2026-08"` 表示该规则覆盖至 **2026-07-31**。

```yaml
image_prefixes:
  - range: [null, "2026-08"]
    prefix: "https://raw.githubusercontent.com/owner/img/main/"
    upload:
      repository: "owner/img"
      branch: "main"
      path_prefix: ""
  - range: ["2026-08", null]
    prefix: "https://raw.githubusercontent.com/owner/img2/main/"
    upload:
      repository: "owner/img2"
      branch: "main"
      path_prefix: ""
```

`prefix` 是站点引用的公开 URL 前缀；`upload.repository`、`upload.branch` 和可选的 `upload.path_prefix` 是写入/扫描目标。范围不得重叠或留空档；无法匹配、配置缺失或目标仓库信息不完整时，脚本会**停止该次带图发布**，而不会静默写入旧仓库。图片相对路径保持既有命名规则：blog 为 `YYYY/MM/DD/slug/NN.ext`，daily 为 `YYYY/MM/MMDD-d.ext`，Photos 为 `YYYY/MM/DD/文件名`。

Photos 当前配置为：2026-07-31 及此前读取 `modem-56k/img@main`，2026-08-01 起读取 `modem-56k/img2@main`。`05_photos-update.py` 生成的 `data/YYYYMM.json` 会记录相应月份的公开 raw URL，因此 `index.html` 无需包含凭据也能正确展示图片。变更图床前，应先发布目标站点的 `_config.yml`，再运行 keepitrun。

## 常用手动命令

| 目的 | 命令 |
|---|---|
| 启动调度器 | `python keepitrun.py` |
| 预览 daily 清理 | `python 90_cleanup-daily-from-blog.py --dry-run` |
| 执行 daily 清理 | `python 90_cleanup-daily-from-blog.py` |
| 全量比对博客文章 | `python 04_convert-blog.py album:diff` |
| 合并一个 RSS 文件并强制免费翻译 | `python 02_combine-gemini.py tmp/rss_YYYY-MM-DD_HH-MM-SS.md -engine google_free` |
| 合并一个或多个 RSS 文件并自动回退 | `python 02_combine-gemini.py tmp/rss_YYYY-MM-DD_HH-MM-SS.md -engine auto` |
| 仅收敛根目录积压摘要 | `python 02_combine-gemini.py -engine auto` |

`90_cleanup-daily-from-blog.py` 可能删除远程仓库中的匹配文章。实际执行前必须先使用 `--dry-run` 确认结果。

## 文件清理策略

| 目录或文件 | 策略 | 注意事项 |
|---|---|---|
| `tmp/` | 超过 1 天自动删除 | RSS 中间文件。 |
| `logs/` | 超过 7 天移入 `logs/archive/` | 运行日志。 |
| `logs/archive/` | 超过 30 天自动删除 | 历史日志。 |
| `archived/` | 超过 30 天自动删除 | 已处理的本地副本。 |
| 根目录 `YYYYMMDD-HHMMSS.md` | 不自动删除 | 用户未取走的 RSS 摘要；会在下一次合并时继续累计。 |
| `last_blog_crawl.txt` | 不应手动删除 | 删除会扩大下一次博客抓取范围。 |
| `rss_issue_memory.json` | 不应手动删除 | 24 小时已提取记忆；02 每次运行自动修剪过期记录，删除会短暂失去跨批去重能力。 |
| `logs/task_completion.json` | 不应手动删除 | 保存同日任务完成状态与完成版本。 |

## 故障排查

### RSS 摘要没有生成或积压未消失

检查 `tmp/` 中是否有 `rss_*.md`，以及根目录是否有 `YYYYMMDD-HHMMSS.md` 或历史 `.py` 后缀摘要。合并器会先读取所有积压摘要，再读取传入的 RSS 文件。若合并失败，旧摘要不会删除；可查看 `logs/` 后重试。

### GLM 返回拒绝提示或翻译失败

拒绝性返回与 GLM HTTP 安全拦截都会保留英语原文，不会丢失条目。网络、限流或结构化输出失败时，脚本会继续尝试下一翻译引擎；全部失败时仍以原始标题及摘要输出摘要。

### daily 或 blog 似乎反复运行

先查看 `logs/daily_*.log`、`logs/blog_*.log` 和主日志。v1.20 的自动任务使用 `--non-interactive`：远程文件已存在时会跳过，不会显示覆盖提示或等待输入。daily 自动模式还会将专辑候选日期与远程 daily 仓库的完整发布日期集合取差集；同日已发布内容不会再抓取或提交。手动运行时不带 `--non-interactive`，仍可保留覆盖确认行为。

### 图片没有上传到预期仓库或 Photos 未显示新图

先检查对应站点的 `_config.yml`：每个 `image_prefixes` 范围必须连续且无重叠，且每条规则都应有 `prefix` 与完整的 `upload.repository`、`upload.branch`。再查看子脚本日志中的“图床路由”或“扫描 owner/repo@branch”行。Photos 的图片仓库必须允许匿名读取其 `prefix` 指向的 URL；私有仓库的 raw URL 无法直接被公开网页或缩略图服务读取。

### GitHub 认证失败

确认本地 `.env` 中的同步凭据有效且拥有目标仓库所需权限。不要把凭据打印到日志、聊天、README 或交接文件。

### 用户需要帮助

直接打开 `readme.md`。不要恢复或运行 `readme.py`。

## 同日任务完成追踪

主程序将任务名、日期和完成版本保存到 `logs/task_completion.json`。任务今天已完成（无论由哪个版本完成）即不再重复执行；版本替换当日，首次运行新版只执行今天尚未完成的任务，不会把当天所有事情重来一遍。v1.25 及更早的“版本变更后重做受影响任务”机制已在 v1.26 移除；记录中的版本号仅用于审计与跳过提示。

## 更新日志

### v1.27（2026-09-29）— 90_cleanup 快速扫描重建，冷启动 90 分钟拖慢归零

- **根因定位**（依据 0928 生产日志 `logs/20260928.log`）：每日首次启动的其余任务共约 3 分钟（09:39:53–09:42:55），随后 `90_cleanup` 预览三连 1800 秒超时（09:42:55–11:14:25），合计拖慢冷启动约 91 分钟，且自上线以来从未完成过一次扫描（`task_completion.json` 无 cleanup 记录）。根因有二：① 对 `_posts/` 每个文件逐个调 Contents API 拉全文（每文件 1 次 API 调用，永不餍足）；② Contents API 对目录列表忽略 `per_page`（每页实际返回 1000 条），实际 1458 个 `.md` 被重复计数成 20000 个，且字典序第 1000 名之后的文件从未被检查。
- **重建扫描引擎**：Git Trees API 一次调用拿真实全量清单与 sha（回退旧分页）；文件内容经 `raw.githubusercontent.com` CDN 并行拉取（默认 16 线程，不占 API 限速配额，429 退避重试）；新增增量缓存 `cleanup_scan_memory.json`（path → sha → 判定，原子写、自动修剪已删文件），内容未变不重拉——首次全量扫描约 1 分钟，之后每次运行仅检查新增/变更文件，秒级完成。
- **时间预算与断点续扫**：`--time-budget`（默认 900 秒，低于外层 1800 秒时限）内未完成时保存进度并以退出码 2 结束，由调度器重试与次日运行从缓存续扫；疑似早报文件名（`YYYY-MM-DD-daily.md`，即 03 的输出命名）优先检查，即使中断也先扫最可能的文件。
- **判定语义修正**：裸 "aigc"/"早报" 文件名不再不经内容确认即判待删除（v1.9 若曾完成过一次会误删 `2024-03-22-aigc-shi-dai-de-di-yi.md` 等正经 AIGC 主题文章）；v2.0 判定 = front matter 内容匹配（categories/tags/title 模式与 v1.9 完全相同）或无歧义拼音组合文件名（`mei-ri-aigc*`/`aigc-zao-bao*`）；疑似候选仅透明化输出不删除。此类文件名候选在 v1.9 下也匹配不到真实泄漏文件（03 生成的早报文件名是 `YYYY-MM-DD-daily.md`），内容匹配才是唯一可靠判据。
- `keepitrun.py` 同日任务去重逻辑（v1.26）不变；cleanup 超时外层上限仍为 1800 秒，重试与续扫由缓存保证不重复扫描。

### v1.26（2026-09-29）— 同日任务去重与 LLM 免费档模型升级

- 同日版本替换后首次运行只执行今天尚未完成的任务：`logs/task_completion.json` 中今天已完成的任务（无论由 v1.25 或其他版本完成）在首次启动与定时调度中均直接跳过；`VERSION_TASK_CHANGES` 重做映射与 `version_changed` 重跑路径移除，`cleanup` 首次启动维护也纳入同日完成记录。
- 依据官方定价文档将 02/92 的模型升级至免费档最新版：Gemini `gemini-2.5-flash` → `gemini-3.8-flash`（ai.google.dev 定价页 Free of charge 档）；GLM `glm-4-flash` → `glm-4.7-flash`（docs.bigmodel.cn 定价页输入/输出均免费，200K 上下文）。GLM-5.3-Flash 为收费档，不属于“完全免费”要求，故不采用。
- `.env` 中的 `GEMINI_MODEL`/`GLM_MODEL` 仍可覆盖默认模型名，未设置时使用上述新默认值。

### v1.25（2026-09-28）— RSS 24 小时已提取记忆与纯 Pillow 图片压缩

- `02_combine-gemini.py` 新增滑动窗口已提取记忆 `rss_issue_memory.json`：摘要成功写出后记录本次全部条目（按最终 URL，无链接项按标题文本），过去 24 小时内已提取的条目在后续合并中被跳过并明确计数；超过 24 小时的记录每次运行自动修剪。记忆文件写入失败仅警告，不阻断主流程。
- 移除 `piczip/oxipng.exe`：该 Windows 专用 exe 无法在非 Windows 环境验证、被杀软/SmartScreen 拦截时静默失效，且 1.1MB 二进制随仓库发行。03/04 的透明 PNG 与 91 的 PNG 压缩改用 Pillow 无损优化（`optimize=True`，仅在结果更小时替换）；JPEG/GIF 原有 Pillow 链路不变，91 在无系统工具时现在对全部格式有 Pillow 兜底。
- 后缀名转换规则（不透明 PNG→JPG、静态 GIF→PNG、透明 PNG/动图 GIF 保留原格式）与转换后 URL 回写逻辑（v1.22）保持不变。
- 版本感知任务映射：`combine`、`daily`、`blog`；`rss`、`photos_update` 不受影响。

### v1.24（2026-09-03）— 实时子脚本日志、RSS 去重边界与 Photos 空月份修复

- 主调度器改为逐行转发子脚本 stdout/stderr，并为子 Python 进程启用无缓冲输出；02 翻译卡住或超时时，总屏显日志会保留超时前最后一个进度点。
- `01_getrss.py` 只负责抓取、关键词过滤、聚合链接还原和 URL 规范化，不再在上午/下午文件形成前提前删除候选。
- `02_combine-gemini.py` 汇集当天两次 RSS、跨日积压摘要和人工输入后，按最终 URL 统一去重并保留文字说明最长的一条，再执行翻译和分类。
- `05_photos-update.py` 将图片仓库中尚未创建的月份目录视为空目录并正常跳过，不再因 GitHub Contents API 的 404 退出。
- Photos 无论在首次启动还是 15:00 调度中，只有脚本成功才写入 `task_completion.json`，失败会保留后续重试资格。
- 任务映射：`rss`、`combine`、`photos_update`。

### v1.23（2026-09-02）— Techmeme 原文还原与图片维护工具修复

- Techmeme RSS 条目优先从自带摘要 HTML 提取原始报道 URL；即使 Techmeme 聚合页对当前 IP 返回错误，也能保留聚合摘要文字并链接到原文。
- 仍按最终规范化 URL 去重；同一原文继续保留文字说明最长的一条。
- `91_compress-images.py` 现可识别发行包 `piczip/oxipng.exe`，并在 Windows 没有 jpegoptim/gifsicle 时使用 Pillow 压缩 JPEG/GIF。
- PicLite 当前提供桌面/Web 图形工作流和文件夹监控，但没有适合本任务的无交互 CLI，因此未引入其 Node/Rust/Tauri 依赖；现有 Pillow + oxipng 链路更小，并已用本次文章的 10 张图验证上传前压缩与转换。
- 任务映射：`rss`。

### v1.22（2026-08-21）— 博客图片扩展名一致性修复

- 修复 `04_convert-blog.py` 在不透明 PNG、WebP/AVIF 或静态 GIF 转换为 JPG/PNG 后，只上传新扩展名文件、却未更新已生成文章 Markdown 的缺陷。
- 转换后的公开 URL 现会同步回写正文全部图片引用和 front matter `image` 题图字段；透明 PNG 与未转换图片保持原 URL。
- 版本感知任务映射仅标记 `blog`，避免升级时重跑不受影响的 RSS、daily 或 Photos 任务。

### v1.21（2026-08-19）— 目标站配置驱动的图床路由

- 新增 `image_routing.py`：以无额外依赖的受限 YAML 解析器读取 `image_prefixes`，校验范围、仓库、分支与路径前缀，并拒绝重叠、空档或不完整的上传规则。
- `03_convert-daily.py` 与 `04_convert-blog.py` 会在图片上传前读取各自目标博客的 `_config.yml`；图片写入由匹配月份的 `upload.repository`、`upload.branch`、`upload.path_prefix` 决定，文章仍写入原博客仓库。
- `05_photos-update.py` 会对每个月读取 photos 的 `_config.yml`，按路由扫描图片仓库，并在 `data/YYYYMM.json` 写入对应公开 `base_url`；已有 JSON 内容一致时不产生提交。
- daily 的既有展示前缀保持不变，并补充显式上传目标；其 2026-07 的原有范围空档已修正为截止 `2026-08`，不改变任何月份的展示前缀。
- Photos 配置为 2026-07-31 及以前走 `modem-56k/img@main`，2026-08-01 及以后走 `modem-56k/img2@main`。图床路径命名规则保持不变。
- `02_combine-gemini.py` 现可识别 GLM HTTP API 的内容安全拦截响应；整批拒答时记录明确警告并继续回退，所有引擎不可用时仍保留英语标题与摘要，不写入拒答文本。
- 任务映射：`daily`、`blog`、`photos_update`。

### v1.20（2026-08-18）— 后台无交互与重复发布防护

- 主调度器以关闭的空标准输入运行未显式传入输入的子脚本，避免后台任务停在人工确认提示而被误判为超时并重试。
- 自动 daily 任务传入 `--non-interactive`，以远程 daily 仓库的完整发布日期集合做差集；同日内容已发布时直接完成，不再重复抓取、备份、覆盖或提交。
- 自动 blog 任务也传入 `--non-interactive`；遇到远程已存在文章时安全跳过，不等待覆盖提示。手动命令保留原有交互覆盖行为。
- 任务映射：`daily`、`blog`。

### v1.19（2026-08-18）— 任务链整理与累计 RSS 摘要

- 移除 Unsplash 与马良注册的自动任务、脚本文件和环境变量模板内容。
- 将保留的每日任务依执行顺序重命名为 `01_getrss.py` 至 `05_photos-update.py`；维护工具使用 `90+` 编号。
- `02_combine-gemini.py` 现在会合并根目录中所有尚未取走的 `YYYYMMDD-HHMMSS.md`，并兼容历史 `.py` 后缀摘要；输出成功后删除被新摘要取代的旧文件。
- URL 去重与“相同 URL 保留最长描述”规则与 `01_getrss.py` 对齐，并覆盖积压摘要与新 RSS 输入。
- GLM 的单条拒绝性翻译结果会回显英语原文，避免遗漏或写入拒绝提示。
- 任务映射：`rss`、`combine`、`daily`、`blog`、`photos_update`。

### v1.18（2026-08-18）— RSS 恢复、可靠性与链接规范化

- 主调度器固定按 GMT+8 判断日期和任务时间；子脚本设置统一时限并重试。
- `combine-gemini.py` 支持一个或多个 RSS 中间文件，并按 Gemini、GLM HTTP API、Google Free Translate 降级。
- `getrss.py` 解码 Google 重定向、解析 Techmeme 原文链接、去除追踪参数，并按 URL 去重。

### v1.17（2026-08-18）— 版本与文档校正

- 以正式 v1.16 归档为基线校正版本元数据，删除 `readme.py`，并将说明统一至本文件。
- 历史“2.0”标识被确认为非正式版本，不构成后续程序发布。

### v1.16 及更早版本

完整历史版本信息以归档 ZIP 和 GitHub 提交记录为准。维护时应以当前 `VERSION`、`VERSION_DATE` 和本更新日志为一致性基线。

## 维护注意事项

- 修改代码前先核对版本变量、README 和发行包命名是否一致。
- 每次完成一轮工作，在提交前新建一个仅包含本轮增量的 `todo-MMDD-HHMM.md` 交接记录。
- 交接记录必须完整保留对应用户需求，并说明目的、偏好、完成项、偏差、未完成项、返工与踩坑；不得包含令牌、API Key、密码、Cookie、个人信息或任何明文凭据。如需要凭据，必须向配置所有者索取。
- 发布前确认包内不含 `.env`、日志、临时文件、账号记录、凭据或用户生成内容。

---

文档版本：**1.26**。本文是 keepitrun 的唯一用户说明与更新日志。
