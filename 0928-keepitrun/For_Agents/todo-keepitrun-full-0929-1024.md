# keepitrun 完整开发日志（单一真相源）

## ⚠️ Agent 守则（后续每轮维护必须首先阅读并遵守）

1. **工作日志要求**：每轮任务完成后，必须在本文件追加本轮增量日志（含用户需求脱敏转述、处理结果、验证证据、偏差与未完成项），并**将本文件重命名为 `todo-keepitrun-full-MMDD-HHMM.md`，时间戳取本轮截稿时间，时区 GMT+8**。旧文件名不留存，本文件始终是唯一活跃交接文档。
2. **单一真相源**：不得新建其他 todo 中间文件；历史文档只在 `For_Agents/merged-sources-0928/` 存档。仓库工作夹内运行时文件（logs/、tmp/ 等）不提交。
3. **凭据铁律**：本文件、readme、发行包、提交记录均不得包含 token、API Key、密码、Cookie 或任何可复用凭据；用户需求一律脱敏转述。
4. **发版纪律**：升版需同步 `keepitrun.py`（VERSION/VERSION_DATE/模块 docstring）、`readme.md`、`.env.example` 头部，打包前确认包内不含 `.env`/日志/凭据，包名 `keepitrun-vX.Y.zip`，For_Agents 与工作夹根各一份，并记录 SHA-256。
5. **调度纪律**：修改生产前确认 `keepitrun.py` 未在运行；未经用户授权不停止/启动调度器；时区一律 GMT+8。

---

生成时间：2026-09-28 17:5x 首建（GMT+8，以文件名时间戳为准，每轮更新后重命名）。本文件合并并取代 `For_Agents/todos/` 此前全部 15 份 todo、prompt 记录与时间轴报告（原件已移入 `merged-sources-0928/` 存档，其中明文凭据已脱敏）。本文件不含 token、API Key、密码、Cookie 或任何可复用凭据；用户需求一律以脱敏转述保留。

**上一轮（2026-09-28）要点速览**：版本 1.24 → **1.25**。① 核查 piczip 引用后移除 `piczip/oxipng.exe`，03/04/91 图片压缩全部改为纯 Pillow（同格式压缩为主，转换规则不变）；② 02 新增 **24 小时已提取记忆** `rss_issue_memory.json`，摘要被取走后 24 小时内重复条目不再重现；③ 打包 `keepitrun-v1.25.zip`（For_Agents + 工作文件夹根各一份）；④ 全部历史 todo 去重合并为本文件；⑤ 发现并处理旧文档中两处已泄露凭据（需轮换，见 §5.3）。

**本轮（2026-09-29）要点速览**：版本 1.25 → **1.26**。① 依据官方定价文档将 02/92 的 Gemini 升级至 `gemini-3.8-flash`（Free of charge 档）、GLM 升级至 `glm-4.7-flash`（输入/输出均免费档，GLM-5.3-Flash 为收费档故不采用）；② 移除版本变更重做机制：同日版本替换后首次运行只执行今天尚未完成的任务，首次启动逐任务门控，cleanup 纳入完成记录；③ 打包 `keepitrun-v1.26.zip` 双份；④ 本文件开头新增 Agent 守则。详见 §2A。

---

## 1. 当前状态与运行基线

- 生产目录：`C:\Users\james\Dropbox\WORKS\SOFT\AI-Python\keepitrun`（Windows 11）。
- 当前版本：**v1.26**（2026-09-29）。
- 新发行包：`For_Agents/keepitrun-v1.26.zip` 与工作文件夹根 `keepitrun-v1.26.zip`（同一文件，SHA-256 `F5D501BD7DFF8B39B78637EF825C5E54629A233A44B15ABD2CC77818E5C25554`，14 个成员，112,334 bytes）。v1.25 包（111,967 bytes）随之作废但仍可作回滚点。
- 包内无 `.env`、日志、临时文件、用户内容、凭据；仅含 `.env.example`。zip 内路径使用标准正斜杠。
- 更新方式不变：解压覆盖生产目录（保留 `.env`），替换后 `python keepitrun.py`。**v1.26 起替换当日重新打开脚本，只会补做今天尚未完成的任务，不会把当天已做过的事情重来一遍。**
- 上一回滚点：v1.25 包（For_Agents 存档）；本轮变更仅涉及仓库与发行包，生产机由用户手动替换后生效。
- 调度纪律：替换文件前确认 `keepitrun.py` 未在运行；无用户明确授权不停止/启动调度器。

## 2. 本轮（2026-09-29）增量日志

### 2A.1 用户需求（脱敏保留）

> todo 已提到 For_Agents 文件夹，其他 todo 中间文件已删除，以 todo-full 为准。
> 1. 检查 combine-gemini 及其他可能用到 LLM 的地方是否使用最新模型：谷歌 Gemini 已升级到 3.8 flash 免费档，请首先查看官方 API 文档免费档位，然后在定义中选择最新模型；GLM 同样操作；其他模型用到的都根据官方完全免费的档位升级到最新版调用。不限于该脚本。
> 2. 刚才关闭 keepitrun 主脚本升级到 1.25 时，打开又重新运行了一次。本次以后的更新，在检查到版本号在今日替换时，首次运行新版只做今天还没做过的任务即可，不必所有事情都重来一遍。
> 3. 输出 1.26 打压缩包，更新 todo-full 加入本次工作日志；重命名文件为截稿时间（GMT+8）；并将每次更新工作日志的要求写入 todo-full 开头作为 agent 后续要遵循的事项。

### 2A.2 任务 1：LLM 免费档模型升级（02 / 92）

**排查范围**：全仓 10 个脚本 + 配置 JSON 扫描（generativelanguage/bigmodel/zhipu/openai/dashscope/groq/deepseek 等端点特征）。LLM 调用只存在于 `02_combine-gemini.py`（标题翻译链 Gemini → GLM HTTP → Google Free）与 `92_model-process.py`（可选后处理，Gemini → GLM SDK 回退）；keywords.json 中的 GPT/GLM 等词均为新闻分类关键词，非调用。03/04/05/90/91/01/image_routing 无任何 LLM 端点。

**官方文档核查**（2026-09-29 实测抓取）：

- Gemini：`ai.google.dev/gemini-api/docs/pricing`。`gemini-3.8-flash`（Gemini 3.8 Flash）在 Free Tier 列 "Free of charge"，Paid Tier 输入 $0.75/1M（2026-12-31 前价）；3.7/3.6/3.5/3.1/3.0/2.5 系列 Flash 均有免费档，3.8 为最新。**选定 `gemini-3.8-flash`**（与用户提示一致）。
- GLM：`docs.bigmodel.cn/cn/guide/start/pricing` 与模型概览页。GLM-5.3-Flash 输入 0.8 元/输出 2.8 元每百万 tokens，**为收费档，不符合"完全免费"**；GLM-4.7-FlashX 亦收费（0.5/3）。完全免费（输入/输出均标"免费"）的文本模型中最新为 **`glm-4.7-flash`**（200K 上下文/128K 输出，GLM-4.7 基座）；其余免费档 GLM-4.5-Flash、GLM-4-Flash-250414 均更旧。**选定 `glm-4.7-flash`**。

**代码变更**：

- `02_combine-gemini.py`：`GEMINI_MODEL` `gemini-2.5-flash` → `gemini-3.8-flash`；`GLM_MODEL` `glm-4-flash` → `glm-4.7-flash`；附官方定价出处注释。两处模型名均为参数传入引擎函数，无其他改动。
- `92_model-process.py`：`GEMINI_MODEL` → `gemini-3.8-flash`（删除过时的 "gemini-3-flash-preview" 注释）；`ZHIPU_MODEL` → `glm-4.7-flash`；回退提示文案去掉硬编码版本号。
- `.env.example`：`GEMINI_MODEL`/`GLM_MODEL` 可选覆盖项示例同步为新默认值；覆盖链路测试通过（环境变量覆盖优先级不变）。
- 兼容性：02 走官方 REST（GLM v4 chat/completions、generativelanguage SDK generateContent），模型名均为字符串参数，新模型无需接口变更；GLM-4.7-Flash 上下文 200K 远大于翻译批次需求。

### 2A.3 任务 2：同日版本替换不重做已完成任务（keepitrun.py 1.26）

**问题还原**（依据仓库内存档的生产日志 `logs/20260928.log` 与 `logs/task_completion.json`）：0928 全天任务由 v1.24 完成并记录；用户当日关闭脚本替换 v1.25 后，`should_task_redo` 判定 done_version(1.24) ≠ VERSION(1.25) 且任务在 `VERSION_TASK_CHANGES["1.25"]` 影响集内 → 触发 `version_changed` 重做；首次启动流程 `run_first_boot_tasks` 也无条件执行全部任务、不看当日完成记录。两条路径都会把当天已做过的事情重来一遍。

**处置**（v1.26 语义：今天已完成 = 已完成，无论由哪个版本完成）：

- 移除 `VERSION_TASK_CHANGES` 映射、`should_task_redo`、`get_tasks_changed_between`；`task_completion.json` 仍记录完成任务时的版本号，仅作审计与跳过提示。
- `should_run`：内存去重后仅查 `get_done_version_today`——今天已完成（任意版本）即跳过；版本不同时日志明确提示"版本替换日不重做"。
- `run_first_boot_tasks` 逐任务门控：combine/daily/blog/photos_update 均先查当日完成记录再执行；**cleanup（首次启动维护）也纳入完成记录**（`record_task_done("cleanup")`），成功才记，避免版本替换日重复 3×1800 秒的预览重试。
- 失败任务仍不记完成、次日或下次调度照常重试；昨日完成记录不影响今日运行（按日滚动语义不变）。
- 同步：模块 docstring v1.26 变更、启动横幅改为"同日任务去重: 已启用"、readme §同日任务完成追踪 + v1.26 更新日志、`.env.example` 头部版本。

### 2A.4 验证证据

- `py_compile` 全部 10 个脚本通过（04 的 docstring `\s` SyntaxWarning 为历史遗留，未改动）。
- 功能测试 **36/36 通过**（隔离副本 + monkeypatch，测试脚本 `scripts/test_keepitrun_v126.py`）：v1.26 模块断言 5 项；should_run 同日去重语义 7 项（未完成运行/完成跳过/旧版本今日完成跳过/昨日完成今日运行/会话内去重）；首次启动门控 15 项（全部已完成→零调用、全部未完成→全部执行并记录 v1.26、仅 combine 完成→其余执行）；02/92 模型默认值 4 项；02 `.env` 覆盖链路 2 项。
- 发行包：14 成员、正斜杠路径、无 `.env`/敏感条目；内容级凭据扫描仅命中 03/04/90 的 `ghp_xxxxx` 类**占位示例串**（帮助文本，非实值）。

### 2A.5 偏差与未完成项

- GLM 免费档停留在 glm-4.7-flash：GLM-5.3-Flash（2026-08-26 发布）与 FlashX 均为收费档，不满足用户"完全免费"限定；后续若智谱将 5.3-Flash 转免费可再升级。
- 生产日志发现 90_cleanup 预览在 2 万篇文章上 3 次×1800 秒全部超时（20260928.log 11:14 结束后才进入定时调度），本轮未处理——首轮启动已因此拖慢约 90 分钟；建议下轮评估（分批列出/缓存文件清单/提高时限/降频）。本轮 v1.26 的 cleanup 同日门控可避免版本替换日的重复浪费。
- 生产机部署（解压替换 + 重启验证）由用户手动执行；替换当日首次运行只会补做未完成任务，无需用户做任何额外操作。

## 2B. 上一轮（2026-09-28）增量日志

### 2B.1 任务 1：piczip 核查结论与处置

**核查证据**（静态 + 动态）：

1. 引用面共 3 处：`03_convert-daily.py`（嵌套 `_get_tool`）、`04_convert-blog.py`（模块级 `_get_tool`）、`91_compress-images.py`（`find_tool`）。三处逻辑一致：win32 下查 `piczip/<name>.exe`，否则查系统 PATH。
2. `piczip/` 内只有 `oxipng.exe`（1,127,424 bytes，Windows PE）。发行包 v1.24.zip **确实包含**该 exe（`piczip\oxipng.exe`），打包无遗漏。
3. 功能性缺陷（判定"未可靠起作用"的依据）：
   - 03/04 调用 oxipng 时 `subprocess.run(capture_output=True)` **不检查返回码**：被杀毒软件/SmartScreen 拦截、exe 损坏等情况全部静默失败，PNG 保持原样，无任何日志；
   - 该 exe 为 Windows 专用，非 Windows 环境完全失效（91 在 Linux/macOS 找不到 `piczip/oxipng`，只能依赖 PATH）；
   - 91 的 PNG 分类在 oxipng 缺失时直接跳过（无 Pillow 兜底）；
   - 05_photos-update.py 只生成 JSON 索引、不上传图片本体，压缩覆盖面实际就是 03/04/91。
4. 结论：引用路径本身正确（win32 可命中），但整条链路存在"静默失效、单平台、无法验证"三重风险，且 1.1MB 二进制长期随仓库/发行包携带。

**处置**（按"如果没有起作用，删除它"授权执行）：

- `git rm piczip/oxipng.exe`，目录删除；
- 03/04：删除 `_get_tool`/`_piczip_dir`，透明 PNG 压缩改用新增的 Pillow 无损优化（`Image.save('PNG', optimize=True)`，**仅在结果更小时替换**，失败保留原文件）；
- 91：`find_tool` 改为仅查 PATH（oxipng/jpegoptim/gifsicle 仍可用即优先），并为 PNG/JPEG/GIF **全部格式提供 Pillow 兜底**——任何平台零外部依赖即可运行；
- **后缀名规则不变**：不透明 PNG→JPG、静态 GIF→PNG、透明 PNG/动图 GIF 保留原格式、WebP/AVIF 按透明度转换；v1.22 的"转换后 URL 回写正文与题图"逻辑原样保留。Pillow 已在既有依赖清单（`pip install ... Pillow`），无新增依赖。

**调研备选**（为何选择 Pillow）：v1.23 已评估过 PicLite（桌面/Web 工作流，无 CLI，依赖 Node/Rust/Tauri）被否决；jpegoptim/gifsicle/oxipng 均为非 pip 系统工具，正是"Windows 上装不了"的痛点本身；pngquant 有损、需系统安装。Pillow 是唯一"已在依赖内、跨平台、纯 pip、可脚本调用"的选项，其中 PNG `optimize=True` 为无损压缩（等效 oxipng 低档收益，透明 PNG 场景本就收益有限）。

### 2B.2 任务 2：getrss/02 的 24 小时已提取记忆

- 架构说明：按 v1.24 设计，跨批次去重职责在 `02_combine-gemini.py`（01 只抓取与规范化），因此本需求实现在 02。
- 新增根目录运行时文件 `rss_issue_memory.json`：02 每次成功写出摘要后，将本次全部条目记入（键与去重规则一致：优先最终规范化 URL，无链接项按标题文本；值为提取时间戳）。
- 合并流程在去重之后、翻译之前执行新过滤：过去 **24 小时**内已提取的条目直接跳过，并打印 `Past-24h already-issued duplicates removed: N`；全部条目都被过滤时不生成空摘要、正常退出。
- 记忆每次运行自动修剪（>24h 丢弃），原子写入（tmp + os.replace），写入失败仅警告不阻断主流程；文件损坏/缺失视为空记忆。
- 效果：摘要文件被用户取走后，早晨已发过的条目不会在下午摘要中重现；超过 24 小时的旧闻不受限。README 的"RSS 增量摘要规则""目录结构""文件清理策略"均已同步该文件（不应手动删除）。

### 2B.3 验证证据

- `py_compile` 全部 10 个脚本通过（沙箱 Python 3.12；04 的 docstring `\s` SyntaxWarning 为历史遗留，未改动其逻辑）。
- 功能测试 31 项全部通过（隔离副本执行，测试脚本 `scripts/test_keepitrun_v125.py`）：
  - 02 记忆链路 14 项：正常合并并建记忆（3 个唯一键，重复 URL 合并保留最长标题）→ 模拟用户取走摘要后重跑（跳过 3 条、不生成新摘要）→ 新旧混合输入（旧 URL 被跳过、新 URL 保留，记忆增至 4）→ 时间戳回拨 25 小时（条目重新出现，记忆修剪+回填）；
  - 03/04/91 压缩链路 17 项：透明 PNG 保持 `.png`、不透明 PNG→`.jpg`（既有规则）、JPEG 保持 `.jpg` 且 17,732→6,942 字节、动图 GIF 保持 `.gif` 且 2 帧保留、静态 GIF→PNG/JPG（既有规则）、WebP→JPG/PNG、无文件变大、无 `.tmp` 残留、91 报告中各格式均出现 `ok-pillow` 状态。
- 沙箱为 Linux，无法执行 Windows exe 语义测试；但移除 exe 后代码路径与平台无关，上述测试即为生产行为的直接验证。

### 2B.4 偏差与未完成项

- 05_photos-update.py 本身不上传图片，故未纳入压缩改造（原任务描述"上传到图床"经核实仅发生在 03/04）。
- zip 内路径分隔符由反斜杠改为正斜杠：Windows 资源管理器/7-Zip 解压均正常，属标准化修正而非行为变更。
- `.env.example` 头部版本号 v1.19→v1.25（历史遗漏的陈旧标注）。
- 生产机部署（解压替换 + 调度器重启验证）由用户手动执行，本轮未触碰生产。

## 3. 完整开发时间轴（v1.0 → v1.25）

> 来源合并：`todo-keepitrun-all-prompts.md`（31 条需求索引）、`todo-keepitrun-0902-1630.md`（截至 v1.24 的单一真相源）、`keepitrun 与关联站点完整时间轴工作交接报告.md`（2026-08-22，v1.17–v1.22）及各阶段 todo 的独有踩坑记录。重复内容只保留一份。

### 阶段一：v1.0–v1.13（2026-07-08 前后，来源 todo-0708-0040.md 十个阶段）

| # | 用户需求（脱敏转述） | 处理结果 |
|---|---|---|
| 1 | 马良生图参考图频繁 dimension_mismatch，浪费额度；要求修复尺寸传参、额度探测与连续注册 | 定位为编辑接口返回原图尺寸而脚本强制 size；参考图任务不再固定 size，部署 Worker v28 |
| 2 | 每日自动注册马良账号；AIGC 早报不得进入主站 blog，应只在 daily 发布 | 发现"贴图"album_id 实为早报专辑，从 blog 合集移除并新增清理脚本（90 前身） |
| 3 | 已手删 35 篇误发早报；另有文章正文仅剩 14 行 | 清理脚本写死 master 导致 404→自动探测分支；正文提取补 section 回退 |
| 4 | img 仓库超 GitHub Pages 体积限制、图片 URL 硬编码 | 备份后建立 image_prefixes 相对路径架构 + Jekyll 解析插件；新增图片压缩 CLI（91 前身）与上传前压缩 |
| 5 | 首次无损压缩收益不够 | 更激进压缩与格式转换，同步更新两站引用；指出历史 blob 仍占 Git 体积 |
| 6 | daily 图片仍用 raw URL 与主站规则不一致 | 统一日期相对路径、处理 WebP、未引用图片归档 |
| 7 | Cortana 等文章大量图片消失（误归档） | 对照历史提交恢复 137 个 slug 的 167 张曾被引用图片 |
| 8 | 部分"贴图"文章引用不存在的 PNG | 逐篇校正 PNG→JPG 引用；确认从未存在的删除死链，不补造旧格式掩盖问题 |
| 9 | v1.12：图片只允许 JPG/透明 PNG/动图 GIF，兼容 IE6 | 统一压缩转换函数，引入 Pillow 做透明/动图判断 |
| 10 | v1.13：Windows 装不了 oxipng 等，要求开箱可用 | 发行包内置 oxipng.exe（即 piczip 模块起源），JPEG/GIF 用 Pillow |
| — | 版本号纪律：1.9 之后应为 1.10，"2.0"不是正式版本 | 后续统一连续 1.x 编号 |

### 阶段二：v1.14–v1.16（2026-07-23/24，RSS 翻译与误发布修复）

- **v1.14**：RSS 英文内容一周未翻译→旧 Gemini key 失效且有硬编码；改从 `.env` 读取、增加 GLM 与 auto 回退、清理实值密钥、补 `.env.example`。
- **v1.15**：v1.14 回退旧脚本导致 daily 混入 blog、图片路径错误；对比各版本拼回正确链路，删除误发文章与冗余图片，自动发现世界杯文章并加 featured，脚本实测后发版。
- **v1.16**：世界杯文章 18 图缺失（微信反爬）；从公开镜像恢复图片、blog 增加可选 page-reader 回退、新增 Google Free Translate 形成三级翻译回退。
- **踩坑**：微信"环境异常"反爬；img 仓库 Pages 构建曾 errored；Google Free 有限速；Ruby `json` 模块作用域问题。

### 阶段三：v1.17–v1.22（2026-08-18/21，版本回归与可靠性）

- **v1.17**：核对归档认定生产出现的"2.0"不是可追溯正式版本；以 v1.16 为基线做版本与文档校正，删除 `readme.py`。
- **v1.18**：combine 超 300 秒被终止→协调主子脚本超时并重试；GMT+8 调度；单文件合并始终可用；Techmeme/Google News 聚合 URL 不能作为去重身份，先还原原文再按最终 URL 保留最长描述。
  - 踩坑：主/子脚本时限必须保持"子不高于主"；无中间文件时不得放弃当天产物。
- **v1.19**：移除马良与 Unsplash；脚本按执行顺序编号 01–05/90+；积压摘要收敛为唯一最新文件（原子替换）；GLM 单条拒答回显英文。
- **v1.20**：daily"无限重复"实为远程已存在时等待覆盖输入被超时重试；自动任务一律无交互（`--non-interactive`、空 stdin），daily 用远程完整发布日期差集。
  - 踩坑：别把"重试同一阻塞子进程"误判为"远程无限提交"；空 stdin 是兜底，不替代子脚本显式无交互语义。
- **v1.21**：新增 `image_routing.py`（受限 YAML 解析器），blog/daily/Photos 改为目标站 `_config.yml` 的 `image_prefixes` 驱动；img2 改公开（用户授权）以让匿名 raw/weserv 可读。
  - 踩坑：日期范围 `[null,"2026-07") + ["2026-08",null)` 漏掉整个 2026-07（半开区间语义）；私有 raw URL 无法被公开页面读取；05 只写 photos JSON 不传图。
- **v1.22**：最新两篇主站文章断图→PNG 已转 JPG 但引用未回写；新增转换 URL 回写正文与 front matter 题图，最小修正 2026-08-12 与 2026-07-25 两篇历史文章。
- **Photos 前台热修（不升版）**：手机竖屏方形多列缩略图、默认 weserv 480×480、导航遮挡修复。

### 阶段四：2026-09-02（v1.23 + Photos 前端小修 + 首次文档合并）

- 公众号文章漏同步：根因是发布时未勾选"传媒"合集（自动发现只覆盖 7 个已配置合集）；用户补选后单次 URL 补发，10 图上传、7 张不透明 PNG 转 JPG 并回写引用，分类最小校正为"传媒/传媒"。
- **v1.23**：Techmeme 改从 RSS 摘要 HTML 直接还原原文（部分 IP 被聚合页阻断时仍可用，15/15 fixture 验证）；91 修复 Windows 探测并支持随包 oxipng + Pillow 回退（piczip 模块"修复"的由来）；评估 PicLite 后不引入；马良孤立账号数据退休至备份目录。
- **Photos 小修**：点击缩略图新窗口仍打开 480×480 → `<a href>` 改为仅带 `url=` 的 weserv 原图地址（默认关闭原图预览时），验证 4096×3072 原尺寸后推送（提交 `1f2aa2d`）。
- **首次合并**：0902-1630 文档自称单一真相源；其中"todo-0708 两文件 SHA-256 完全相同"的结论**有误**（本轮实测两文件 SHA-256 不同：`fcb6ba03…` vs `ee0a9ee7…`，分别泄露了不同凭据，详见 §5.3）。

### 阶段五：v1.24（2026-09-03）

- 子脚本 stdout/stderr 逐行实时进入总日志（Popen 双管道 + 无缓冲），02 翻译超时可定位最后进度；
- 01 只负责抓取/还原/规范化，跨批次去重统一延后到 02（按最终 URL 保留最长说明）；
- Photos 将未创建的月份目录视为空目录正常跳过；失败不再误记完成。

### 阶段六：v1.25（2026-09-28，上一轮）

见 §2B。

### 阶段七：v1.26（2026-09-29，本轮）

见 §2A。

## 4. 运行规则与文件策略（现行有效）

- 调度（GMT+8）：02:00/14:00 getrss → 10:05 daily → 10:10 blog → 14:05 combine → 15:00 photos；90/91/92 手动。
- 根目录 `YYYYMMDD-HHMMSS.md` = 用户尚未取走的摘要；02 会把它与新 RSS 合并去重，原子写入新文件后才删旧摘要。
- `rss_issue_memory.json`（v1.25 新增）= 24 小时已提取记忆；不应手动删除，删除会短暂失去跨批去重能力；02 每次运行自动修剪。
- 翻译顺序 Gemini → GLM HTTP → Google Free（v1.26 默认模型：`gemini-3.8-flash`、`glm-4.7-flash`，均为官方免费档）；全部失败或安全拒答时保留英文源内容，不写错误文本、不丢条目。
- 清理：tmp/ 1 天、logs/ 7 天转归档、归档日志与 archived/ 30 天；`last_blog_crawl.txt`、`rss_issue_memory.json`、`logs/task_completion.json` 不应手动删除。
- 版本感知任务追踪：v1.26 起改为**同日任务去重**——今天已完成（无论哪个版本）即不再执行，版本替换日首跑只补做未完成任务；`task_completion.json` 仅记完成版本供审计。
- 图床路由：blog/daily/Photos 均读目标站 `_config.yml` 的 `image_prefixes`（半开区间，不得重叠/留空档）；Photos 2026-07-31 前 `modem-56k/img@main`、2026-08-01 起 `modem-56k/img2@main`（公开仓库）。

## 5. 安全、打包与操作边界

### 5.1 铁律（继承并持续有效）

- `.env` 只留在生产机；不得读取、复制、打印、提交或进入 ZIP；任何交接文档不得写 token、Key、Cookie、密码或账号内容。
- 发行包仅含 `.env.example`、活动/维护脚本、配置 JSON、README；禁止 `.env`、日志、缓存、测试、备份、用户内容。v1.25 起不再包含 `piczip/oxipng.exe`。
- 修改生产前确认常驻进程状态并建立最小回滚备份；未经授权不停止/启动调度器。
- 每轮完成后在本文件追加增量日志并重命名文件名时间戳（详见文件开头 Agent 守则；不再新建单独 todo 文件）。

### 5.3 打包清单（v1.26）

`.env.example`、01–05、90–92、image_routing.py、keepitrun.py、keywords.json、readme.md、rss_feeds.json，共 14 项；SHA-256 见 §1。

## 6. 下一位维护者先做什么

1. 读本文件与 `readme.md`，确认生产版本号与期望一致；检查调度器与子脚本进程状态。
2. RSS 出现重复条目时：先确认 `rss_issue_memory.json` 存在且时间戳新鲜；确认重复对是否超过 24 小时窗口（超窗重复属预期）。
3. 图片未压缩/体积异常时：确认 Pillow 已安装；03/04/91 已无外部 exe 依赖，失败会在日志/报告中有 `ok-pillow` 或原始状态，不再静默。
4. 凭据问题：先完成 §5.2 的轮换，再谈其他。
5. 改动后保持惯例：最小回滚点、受影响路径测试、更新本文件、重新生成脱敏包。

## 7. 归档说明

原 15 份文档移入 `For_Agents/todos/merged-sources-0928/`（git mv 保留历史），其中明文凭据已就地脱敏。本文件为唯一活跃交接文档；后续轮次按用户指示继续在本文件上追加增量并更新文件名时间戳。
