# keepitrun 单一工作交接文档（2026-09-02 16:30）

这是 `For_Agents/todos` 的新唯一真相源。它合并了此前全部阶段性 todo、完整时间轴报告与截至 v1.24 的修订；用户确认看到本文件后会删除其余旧 `.md`。本文件不含 token、API Key、Cookie、账号内容或其他可复用凭据。

## 1. 当前结论与运行状态

- 生产目录：`C:\Users\james\Dropbox\WORKS\SOFT\AI-Python\keepitrun`。
- 当前版本：`v1.24`，版本日期 `2026-09-03`。
- 调度器状态：v1.24 已隐藏启动并进入定时等待；仅主调度器进程存在，无子脚本占用。
- 最新生产回滚点：`backups/v1.23-before-v1.24-20260903_1650/`；上一个回滚点仍为 `backups/v1.22-before-v1.23-20260902_1705/`。
- 脱敏发行包：`For_Agents/keepitrun-v1.24.zip`，15 个文件，656628 bytes，SHA-256 `6F02A2D2813EA1CDC982022AE3D26F3A68DF9D04814357B1C4CD8E3851937D8C`。
- 包内没有 `.env`、日志、临时目录、用户文章、图片、账号记录、测试、缓存或凭据模式；只保留 `.env.example`。
- 后续代理不得在未确认子任务状态时重启调度器；本次用户已明确授权生产发版，v1.24 当前正在运行。

### 1.1 v1.24（2026-09-03）增量

- 根因：`run_script()` 使用 `subprocess.run(capture_output=True)`，子脚本全部结束后才回放 stdout/stderr；02 翻译超时时，总屏显无法显示最后进度点。
- 修复：改用 `Popen` 双管道读取线程，并给子 Python 进程设置无缓冲输出。stdout/stderr 逐行实时进入控制台和当天总日志；stdout 仍完整保留给清理预览等既有解析调用方。
- RSS 职责边界：01 继续还原 Google News、Techmeme 原文 URL 并清除尾部追踪参数，但不再提前去重；02 汇集 2 点、14 点、跨日积压摘要及人工输入后，按最终 URL 统一保留说明最长的一条，再翻译和分类。
- Photos：GitHub Contents API 对尚未创建的当月目录返回 404 时视为空目录并正常跳过；首次启动和 15:00 调度均只在脚本成功后记录 `photos_update` 完成。
- 验证：Python 3.14 编译通过；两批同 URL 不同追踪参数样例确认由 01 保留两条、02 留较长一条；1 秒超时探针确认进度行先写日志、随后报告超时；生产 Photos 实跑确认 2026-08 共 682 张一致、2026-09 不存在时正常跳过并以 0 退出。
- 生产实跑：02 的 239 条输入、翻译引擎、批次开始及完成均实时显示；daily、blog 无新增；Photos 成功后才写入 v1.24 完成记录。既有一次性清理预览会扫描约 20000 篇文章，本轮为恢复空闲状态结束该只读预览并写入今日启动标记，未修改清理逻辑。

## 2. 2026-09-02 公众号文章漏同步

用户早上 9:30 发布文章，但 10:10 自动 blog 任务显示 7 个固定合集均为 0 篇新文章。实时检查合集 API 后确认调度器确实按时运行，代码也没有异常；根因是发布时没有勾选文章所属的“传媒”合集。用户随后补选了合集，并明确表示无需为此修改发现逻辑。

已用用户提供的 URL 单次运行：

- 标题：从“大连没有湖南台”到甘肃卫视四省退网，落地费博弈20年浮沉
- 正文标注日期：2026-08-31
- 主站文件：`_posts/2026-08-31-cong-da-lian-mei-you-hu.md`
- 主站提交：`c6a61809f13d5d11a72a5694b227ba008706ede3`
- 合集元数据校正提交：`19b0badeec2da00d295d5fe79117b37f8c115e4a`（单次 URL 模式缺少合集上下文，已将默认 `文章／科技` 最小修正为 `传媒／传媒`）
- 图床提交：`fcac3a375fbe10680e4ffd09b31b57996870941a`
- 图片：10 张全部上传并逐项验证；7 张不透明 PNG 转为 JPG，正文与题图 URL 共回写 7 处。
- 正文发布和分类校正对应的主站 Pages 工作流均成功；线上页面 `https://lishuhang.me/posts/2026/08/31/cong-da-lian-mei-you-hu/` 返回 200，标题、JPG 图片引用和“传媒”分类均已出现。

重要行为：blog 自动发现只覆盖代码中已知的 7 个公众号合集。未勾选任何合集的文章不会出现在合集 API 中。遇到这种情况先补选正确合集，或用文章 URL 单次运行，不要擅自引入登录、Cookie、第三方监控服务或扩大抓取权限。

## 3. v1.23 本轮代码修订

### 3.1 Techmeme 原文 URL 还原

旧 `01_getrss.py` 会访问 Techmeme 聚合页，再从 HTML 找原始报道；当前部分 IP 被 Techmeme 阻断时会保留聚合页 URL。Techmeme 自己的 RSS 摘要 HTML 已直接包含原文链接，因此 v1.23 在抓 RSS 时优先从摘要提取第一个非 Techmeme 外部 URL，不再依赖打开聚合页。直接解析聚合页时也补充了 `/YYMMDD/pNN` 路径到锚点名的识别。

给定案例 `https://www.techmeme.com/260819/p26` 的期望原文为 WSJ 的 `startup-to-link-biobanks-of-patient-tissue-to-supercharge-ai-medical-research-55403925`；定向 fixture 已覆盖。实时 Techmeme feed 测试共 15 条，15 条均还原为外部原文，残留 Techmeme 链接为 0。

后续处理顺序保持不变：Google 重定向解码／Techmeme 原文提取 → 去掉 fragment、追踪参数与不定位正文的查询参数 → 按最终 URL 去重 → 相同最终 URL 保留文字说明最长的一项 → 再按标题相似度去重。v1.23 的版本任务映射只标记 `rss`。

### 3.2 图片维护工具与实际上传压缩

`91_compress-images.py` 原先在 Windows 只查系统 PATH，因此看不到发行包已经携带的 `piczip/oxipng.exe`；没有 jpegoptim/gifsicle 时 JPEG/GIF 也完全不处理。v1.23 修复为：

- 优先查找 `piczip/<tool>.exe`，其次查 PATH；
- PNG 使用随包 `oxipng.exe`；
- JPEG/GIF 缺少外部工具时使用已要求安装的 Pillow；
- 只有输出更小时才替换原文件；失败或变大时保留原文件。

生产依赖检查结果：oxipng 可用、Pillow 可用，jpegoptim/gifsicle/cwebp 未安装。定向测试覆盖 PNG、JPEG、GIF 实际压缩，均成功且结果不大于原文件。

blog/daily 的上传前压缩不依赖 `91_compress-images.py` 的批量 CLI；它们各自使用 Pillow + 内置 oxipng。今天文章的真实上传已证明这条生产链路工作：10 张均经检查，7 张 PNG 转 JPG，并在上传后逐个从 GitHub 验证。

评估了 PicLite。它适合图形桌面/Web、文件夹监控和人工择优，但当前没有供本任务无交互调用的 CLI；接入会新增 Node 22、Rust、Tauri 与桌面运行依赖。依照“无需模型、少依赖、可脚本化”的要求，本轮保留现有 Pillow + oxipng，不引入 PicLite。

### 3.3 马良残留清理

v1.19 已移除马良与 Unsplash 的自动任务、子脚本、调度入口和 `.env.example` 配置。全目录代码扫描确认当前没有活动引用或相关额外 Python 依赖。生产根目录仅剩历史运行数据 `maliang_accounts.json`，没有消费者；本轮将它可恢复地移到 `backups/v1.22-before-v1.23-20260902_1705/retired-maliang/`。发行包不包含该文件。

## 4. 生产部署与验证

部署前确认没有运行中的 `keepitrun.py`。只替换以下 4 个文件：

- `01_getrss.py`
- `91_compress-images.py`
- `keepitrun.py`
- `readme.md`

旧文件先复制到 v1.22→v1.23 回滚目录；候选与生产部署后的 SHA-256 逐文件一致。生产 `py_compile` 通过；版本检查为 `1.23 / 2026-09-02 / {'rss'}`。隔离测试还覆盖：给定 Techmeme→WSJ 原文、最终 URL 最长描述去重、内置工具探测、Pillow 回退、blog 不透明 PNG→JPG。

本轮没有修改 `.env`、`last_blog_crawl.txt`、`logs/task_completion.json`、`tmp/`、`archived/`、根目录待领取 RSS 摘要或用户内容。调度器未启动。

## 5. 当前任务链与架构

| 时间（GMT+8） | 脚本 | 作用 |
|---|---|---|
| 02:00、14:00 | `01_getrss.py` | RSS 抓取、关键词过滤、聚合链接还原、原文 URL 规范化并保留全部候选 |
| 14:05 | `02_combine-gemini.py` | 合并新 RSS 与积压摘要、按最终 URL 去重留最长说明、翻译、分类、生成唯一待领取摘要 |
| 10:05 | `03_convert-daily.py` | AIGC 早报专辑同步；远端日期差集防重复 |
| 10:10 | `04_convert-blog.py` | 7 个公众号合集或指定 URL 同步主站 |
| 15:00 | `05_photos-update.py` | 按月份扫描配置指定图床，更新 Photos JSON |
| 手动 | `90_cleanup-daily-from-blog.py` | 先 dry-run，再清理历史误入主站的 daily |
| 手动 | `91_compress-images.py` | 图库维护压缩 |
| 手动 | `92_model-process.py` | 可选模型后处理，不参与压缩判断 |

blog、daily、Photos 都在需要图片时读取目标站 `_config.yml` 的 `image_prefixes`。范围是半开区间 `[start_month, end_month)`；每月必须唯一命中，不能重叠或留空档。blog/daily 根据规则上传到 `upload.repository/branch/path_prefix`；Photos 根据同一规则扫描仓库并写公开 `prefix`。配置不完整时应停止带图发布，不能静默回退旧仓库。

当前 Photos：2026-07-31 及以前读取 `modem-56k/img@main`；2026-08-01 起读取公开的 `modem-56k/img2@main`。私有 GitHub raw URL 无法被匿名网页或 weserv 使用。

## 6. 历史版本合并时间轴

- v1.8–v1.13：修正 daily 误入主站；改善微信正文提取；建立图片相对路径和日期前缀；严格将静态非透明图片转 JPG、透明图保留 PNG、动图保留 GIF；加入 Pillow 与 oxipng 上传前压缩。历史“v2.0/v2.1”图片架构标识不是正式后续版本号。
- v1.14–v1.16：修复 RSS 翻译回退；排除“每日 AIGC 早报”进入 blog；微信 requests 受限时保留可选 page-reader 回退；清理脚本自动探测 main/master。
- v1.17：核对归档后回归可追溯正式版本线，删除可执行说明文件 `readme.py`，以 `readme.md` 为唯一说明。
- v1.18：GMT+8 调度、子任务超时与重试、RSS 首次启动恢复、单文件合并、Google/Techmeme URL 规范化、最终 URL 最长描述去重。
- v1.19：编号为 01–05/90+；移除马良和 Unsplash 活动任务；积压摘要收敛；GLM 单条拒答保留英文源内容。
- v1.20：后台 daily/blog 无交互；远端已存在时安全跳过；daily 用远端发布日期差集。
- v1.21：新增 `image_routing.py`；blog/daily/Photos 改为目标站配置驱动图床；Photos 8 月切 img2；GLM HTTP 安全拦截继续降级并最终保留英文。
- Photos 2026-08 前台热修：手机竖屏方形多列缩略图、默认关闭原图预览、移动抽屉不遮挡导航。
- v1.22：图片格式转换后统一回写正文和 front matter 题图 URL；修复 2026-08-12 与 2026-07-25 两篇历史断图。
- v1.23：Techmeme 从 RSS 摘要取得原文；修复 Windows 图片维护工具探测与 Pillow 回退；退休马良孤立账号数据。
- v1.24：子脚本输出实时进入总屏显日志；去重统一延后到 02 跨批次执行；Photos 正常跳过未创建月份目录，失败时不误记完成。

## 7. RSS、翻译与文件状态规则

- 根目录 `YYYYMMDD-HHMMSS.md`（兼容历史 `.py`）是用户尚未取走的摘要；下一次 14:05 会与新 RSS 合并、去重，原子写入新文件后才移除旧摘要。
- 翻译顺序：Gemini → GLM HTTP → Google Free Translate；所有引擎失败或安全拒答时保留英文标题、摘要和链接，不写错误文本、不丢条目。
- `last_blog_crawl.txt` 不应手动删除；删除会扩大下次合集抓取范围。
- `logs/task_completion.json` 记录同日各任务完成版本。升级后只重跑 `VERSION_TASK_CHANGES` 指定的受影响任务。
- `tmp/` 保留 1 天；日志 7 天后归档、归档日志 30 天后清除；`archived/` 用户文章与下载图片保留 30 天。

## 8. 安全、打包与操作边界

- `.env` 只能留在生产机；不得读取、复制、打印、提交或进入 ZIP。任何交接文档不得写 token、Key、Cookie 或账号内容。
- 发行包允许包含 `.env.example`、活动/维护脚本、配置 JSON、README、`piczip/oxipng.exe`；禁止包含 `.env`、日志、缓存、测试、备份、用户文章、图片和账号记录。
- 修改生产前先确认常驻脚本状态并建立最小回滚备份。没有用户明确授权时，不停止也不启动调度器。
- 站点和 GitHub 修改必须最小化；断图先对照 Markdown 引用、图床实际扩展名、日期路由与公开 URL，不能用补传同名旧格式掩盖脚本缺陷。

## 9. 旧 todo 查重结论

`todo-0708-0040.md` 与 `todo-keepitrun-0708-0040.md` 的 SHA-256 完全相同，是精确重复。其余文档属于相同项目在 v1.14、v1.17–v1.22、图床、GLM 和 Photos 阶段的增量报告，大量内容已在 2026-08-22“完整时间轴工作交接报告”重复汇总。本文件保留当前仍有效的架构、历史决策、运行规则、风险、回滚点与本轮结果，替代所有旧 `.md`。

`prompt-0724-0030.txt` 不是 Markdown，但其有效需求（排除 daily、修复 RSS 翻译、自动相册抓取、清理与归档）也已经纳入上面的历史和现行规则；是否保留该 `.txt` 由用户决定。

## 10. 下一位维护者先做什么

1. 读取本文件和生产 `readme.md`，确认生产版本仍是 v1.24。
2. 检查 `keepitrun.py` 是否仍在常驻以及是否有子脚本运行；不要在子脚本活动时替换或重启。
3. 若公众号再次漏同步，先查当日 `logs/blog_*.log` 和文章是否勾选 7 个已配置合集；有 URL 时可单次同步。
4. 若 RSS 出现 Techmeme 链接，检查日志是否出现“从 Techmeme RSS 摘要提取原始文章链接”，并以最终 URL 做去重。
5. 若图片异常，先看 blog 日志中的“压缩节省／格式转换／已回写 N 个转换后图片 URL”和上传验证；再查路由配置。
6. 改动后继续建立最小回滚点、跑受影响路径测试、更新本唯一交接文档并重新生成脱敏包。
