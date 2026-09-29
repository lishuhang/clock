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

**上轮（2026-09-29 上午）要点速览**：版本 1.25 → **1.26**。① 依据官方定价文档将 02/92 的 Gemini 升级至 `gemini-3.8-flash`（Free of charge 档）、GLM 升级至 `glm-4.7-flash`（输入/输出均免费档，GLM-5.3-Flash 为收费档故不采用）；② 移除版本变更重做机制：同日版本替换后首次运行只执行今天尚未完成的任务，首次启动逐任务门控，cleanup 纳入完成记录；③ 打包 `keepitrun-v1.26.zip` 双份；④ 本文件开头新增 Agent 守则。详见 §2C。

**本轮（2026-09-29 午后·第二轮）要点速览**：用户授权实施并提供 lishuhang.com 子域给 Workers 用。① 站点两仓库新增 agent 入口（blog：articles.json/llms.txt/skill.md/webmcp.js；daily：issues.json/llms.txt）；② Cloudflare Workers 免费档上线**航通社官网 MCP**（mcp.lishuhang.com/mcp，stateless 六工具，零依赖），六工具实测全通；③ 全链路整合既有资产（posts.js 同源索引管线、/img/ 图床规则、raw CDN 全文、v1.28 元数据口径），keepitrun 零改动；④ 交付 readme-site-mcp-v1-0929-1545.md（含 changelog）；Registry 收录与 webmcp.com 提交留待办（详见 §2A/README §5）。

**上轮（2026-09-29 午后）要点速览**：版本 1.26 → **1.27**。① 依据用户提供的 0928 生产日志定位冷启动拖慢约 90 分钟的根因：`90_cleanup` 对 `_posts` 逐文件调 API 拉全文，三连 1800s 超时（09:42:55–11:14:25），且 Contents API 忽略 per_page 导致 1458 个文件被重复计数成 20000；② 重建为 Git Trees 一次列全量 + raw CDN 并行拉取 + sha 增量缓存断点续扫，实测首扫 28.6 秒、日常 1.8 秒；③ 判定语义修正：裸 "aigc"/"早报" 文件名不再不经内容确认即判删（实测保护了 4 篇会被 v1.9 误删的正经文章），并修复 v1.9 多行 tags 死代码；④ 打包 `keepitrun-v1.27.zip` 双份。详见 §2B。

**上轮（2026-09-29 午后）要点速览**：keepitrun 保持 **v1.28** 零改动；新增《站点 Agent 友好化调研 v1》（`research-site-agent-friendly-v1-0929-1250.md`）。① 实测本站已有全站机器索引 posts.js（1458 篇）；② 一手验证四类案例（llms.txt v2 / elsewhere skill.md / every.to 免鉴权 MCP / mabbs WebMCP / TIME bot 版作反面参照）；③ 给出 P0–P3 零成本四层方案（Jekyll 直出索引 → skill/WebMCP → CF Worker stateless MCP + 官方 Registry → 前端搜索与 GLM flash AI 搜索）；④ agent 查询从遍历 repo 数小时变为读索引秒回，keepitrun 全程无需改动。详见 §2B。

**上轮（2026-09-29 中午）要点速览**：版本 1.27 → **1.28**。① blog 同步改纯增量：04 新增 URL 级已同步记忆 `blog_sync_memory.json`，同步过一次的文章永远不再抓取处理；调度侧合集窗口封顶 30 天，历史全量永不重跑（新电脑/长期停跑亦然）；② 发布日期以正文标注「文/书航 yyyy.mm.dd」为准（转载稿公众号时间戳晚于实际首发），正则放宽到无空格与一位数月/日；③ 04 每篇同步文章自动追加 featured 标签（首页大图滚动区域数据源）；④ 03 同日早报首同步版本为准：同日期重发（可能因审查删改）不覆盖已同步版本；⑤ 03 题图 1:1 比例校正：非 1:1（如 2:3）按原始分辨率中心裁切为 1:1，避免展示端再裁切导致整体比原图小一圈；⑥ 打包 `keepitrun-v1.28.zip` 双份。详见 §2B。

---

## 1. 当前状态与运行基线

- 生产目录：`C:\Users\james\Dropbox\WORKS\SOFT\AI-Python\keepitrun`（Windows 11）。
- 当前版本：**v1.28**（2026-09-29）。
- 本轮（0929 午后）新增 `For_Agents/research-site-agent-friendly-v1-0929-1250.md`（站点 Agent 友好化调研 v1）；keepitrun 无任何代码/版本改动。
- 站点 Agent 能力（0929 午后第二轮起上线）：blog/daily 新增 llms.txt 与 JSON 索引（push 即再生）；MCP Server `https://mcp.lishuhang.com/mcp`（Workers 免费档，源码在 clock 仓库 `site-mcp/`）；keepitrun 仍为 v1.28 且零改动。上线说明见 `readme-site-mcp-v1-0929-1545.md`。
- 新发行包：`For_Agents/keepitrun-v1.28.zip` 与工作文件夹根 `keepitrun-v1.28.zip`（同一文件，SHA-256 `B9D0DD521C71862C47E8941D121B7EED98D418BBC84F817383BA8DBD7FA6E94D`，14 个成员，124,389 bytes）。v1.27 包（119,168 bytes）随之作废但仍可作回滚点；v1.26 包已从仓库移除（git 历史仍可找回）。
- 包内无 `.env`、日志、临时文件、用户内容、凭据；仅含 `.env.example`。zip 内路径使用标准正斜杠。
- 更新方式不变：解压覆盖生产目录（保留 `.env`），替换后 `python keepitrun.py`。**v1.28 替换当日首跑，blog 会以最近 30 天为窗口做一次增量：窗口内已同步过的文章由仓库存在性确认一次性记入 `blog_sync_memory.json`（首跑多花几分钟后转秒级），此后每日增量仅处理新增文章；03/04 的首同步保护与题图校正对历史文章不回溯。**
- 上一回滚点：v1.27 包（For_Agents 存档）；本轮变更仅涉及仓库与发行包，生产机由用户手动替换后生效。
- 调度纪律：替换文件前确认 `keepitrun.py` 未在运行；无用户明确授权不停止/启动调度器。

## 2. 本轮（2026-09-29 午后·第二轮）增量日志：航通社官网 MCP v1.0.0 全上线

### 2A.1 用户需求（脱敏保留）

> 用户认可调研方案并授权实施：Cloudflare 托管的另一域名 lishuhang.com 可用（根域重定向 .me、子域有其他用途）；blog 访问网址保持 .me，Workers 内容可使用 .com URL。"直接做完"，完成后写一个单独的 README 介绍新上线的航通社官网 MCP，其中包含 changelog，整合已有资产勿重复造轮子，README 放 For_Agents 文件夹。提供 Cloudflare token 用于部署；强调切勿将敏感凭据 push 上去。

### 2A.2 实施内容（已全上线并实测通过）

- **blog 仓库**（lishuhang.github.io，commit `dd5075b` + `23f5a88`）：新增 `articles.json`（1458 篇全量索引，与首页 posts.js 同源管线，补 tags/featured/raw_md）、`llms.txt`（v2 格式接待卡）、`skill.txt`→直出 `/skill.md`（说明卡）、`assets/js/webmcp.js`（浏览器端三工具注册）；`base.html` 引入 webmcp.js、`head.html` 加 describedby 链接（均一行级）。
- **daily 仓库**（commit `abf2a21`）：新增 `issues.json`（629 期索引）与子站 `llms.txt`。
- **Cloudflare Worker**：源码入库 clock 仓库 `site-mcp/`（零 npm 依赖、stateless、无凭据）；wrangler 部署并绑定自定义域 **mcp.lishuhang.com**（首发版本 `9dfe2f30`）；数据源为两站静态索引（Cache API 索引 1h / 全文 1d），全文走 raw.githubusercontent.com。
- **实测证据**：initialize/tools/list/六工具 tools/call 全通——site_overview（blog 1458/daily 629）、list_articles(tag=featured)=14 篇、search_articles("AI短片")命中并返回 URL、get_article 返回 9KB 全文 markdown、list_daily_issues 分页、get_daily_issue("2026.9.28")日期归一化并取回全文；首页 HTML 已含 webmcp.js 引用与 describedby/llms.txt 链接。
- **交付**：`For_Agents/readme-site-mcp-v1-0929-1545.md`（上线说明 + changelog + 资产整合清单 + 待办 + 维护回滚）；keepitrun 生产机与调度**零改动**。

### 2A.3 偏差与未完成项

- skill.md 首次推送 404：Jekyll 将含 `---` 元数据块的 .md 静态文件当作页面转成 HTML；改为 `skill.txt` + `permalink: /skill.md` 后 200（机制已注释在文件与 README §7）。
- 官方 MCP Registry 暂未收录：当前 CF token 对 DNS 记录只读（创建 TXT 返回 10000 Authentication error），Registry v0.1 匿名发布端点已下线（404）；`site-mcp/server.json` 已通过 validate，三条完成路径（加 DNS 权限 / GitHub 设备流 / 手动 TXT）已写入 README §5 待办。
- webmcp.com 收录需浏览器表单提交，留待用户一次点击。
- posts.js 的题图 `i` 字段为 404 旧路径（站点既有问题），本轮未回改生产首页逻辑；新索引 cover 已按 `image_prefixes` 规则给出正确 `/img/` 路径。
- 凭据纪律：CF token 全程仅经环境变量使用；仓库树与暂存 diff 扫描无任何凭据；Registry 验证用 ed25519 私钥仅存本地 recon/（不入库）。

---

### 2B.1 用户需求（脱敏保留）

> keepitrun 整改告一段落；后续在 For_Agents 文件夹继续相关任务：官网（lishuhang.me / lishuhang.github.io）文章势必越来越多，要求调研在 robots.txt 之外增加 agent 说明，把站内内容做成 skill 或 MCP 等能力，增强本站对 agent 的吸引力。硬约束：只能依赖 GitHub 免费档（Pages/Actions）与 Cloudflare Workers 免费档，MCP/skill 的制作与运行不得产生任何费用；若需动态更新，最多由 keepitrun 在每次推送新文章时顺手完成。期望：AI 查询本站发布过哪些文章时一查即答，无需像最初脚本那样花几个小时遍历 GitHub repo；后续希望改进站内搜索并接入免费 GLM 做静态前端可用的 AI 搜索。交付：调研 v1 MD 放 For_Agents，内容含①网上已有案例整合（附用户提供的 4 份前期资料）②适合本站的 MCP/skill 方案③MCP/skill 完备之后的前端改善建议；同时针对主站 blog 与早报 daily 思考。

### 2B.2 工作过程

- 派出网络调研子代理（3-a）对用户 4 份资料全部一手抓取验证，并补抓 llmstxt.org（v2）、agents.md、agentskills.io 规范、WebMCP 目录与 mabbs 实现源码、CF Workers/KV 限额官方页、MCP 官方 Registry 与收录渠道、Anthropic Agent Skills 规范（快照存本地 recon/，不入仓库）。
- 实测本站两站：主页/robots.txt/sitemap/feed/搜索实现/数据文件。**关键发现：`/assets/data/posts.js`（977KB）即全站 1458 篇文章的机器索引**（字段 u/t/d/y/m/g/e/i，2006–2026，随 Jekyll 构建 push 即更新），agent 方案的原料现成。
- 产出 `For_Agents/research-site-agent-friendly-v1-0929-1250.md`：六节两附录（背景约束、现状盘点、案例整合、推荐方案、前端建议、路线图、风险边界、实测快照与参考链接）。

### 2B.3 关键结论（方案速记）

- 四层零成本架构：**P0** Jekyll 模板直出 `llms.txt` + `articles.json` + `daily/issues.json`（push 即自动更新，**keepitrun 零改动**）→ **P1** `/skill.md` + WebMCP 浏览器端注册 → **P2** CF Workers 免费档 stateless 远程 MCP（site_overview/list_articles/search_articles/get_article/list_daily_issues/get_daily_issue）+ 官方 MCP Registry 免费注册（PulseMCP 自动同步）→ **P3** Fuse.js 全站搜索、GLM flash（glm-4.7-flash 免费档）AI 搜索（CF Worker 持 key + KV 限流）、聊天机器人。
- 效果：agent 查询从"遍历 repo 数小时"变为"读索引秒回"；索引与 MCP 全部无状态，换新电脑/新 agent 零重跑；全程 0 元。
- 明确排除：TIME 式 UA 魔改（需服务端+cloaking 争议）、mcp.so（$39 收费目录）、api.github.com 依赖（未认证 60 次/小时）。

### 2B.4 验证证据

- `every.to/mcp` initialize 200 免鉴权（三工具 feed/search/get_post，stateless Streamable HTTP）；`skills.every.to/mcp` 401（付费库，与本场景无关）——最小可复制架构确认。
- mabbs.github.io（Jekyll+Pages 同构站）经 `/assets/js/blog-console.js` 的 `document.modelContext.registerTool` 注册 5 工具并已收录 webmcp.com；目录免费提交且提供 agent 可读 JSON API。
- 官方 Registry（registry.modelcontextprotocol.io）`mcp-publisher` CLI 免费登记；raw.githubusercontent.com 公开仓库免鉴权 200（全文 md 分发通道成立）。
- 本站 posts.js 1458 条全部可解析、1364 条含摘要、题图字段齐备；blog sitemap 1605 URL、daily sitemap 630 URL、两站 feed 各仅 20 条（索引缺口确认）。

### 2B.5 偏差与未完成项

- 本轮为调研，未改任何站点仓库；P0–P3 待用户拍板后排期（预计 P0+P1 一轮即可让"查文章秒回"成立）。
- GitHub Pages 软限额（带宽/构建时长）官方当前文档页已精简，未能一手复核（调研文档 §2.8 已标注 ⚠️）。
- P2 绑自定义域 `mcp.lishuhang.me` 前需确认域名 DNS 是否托管 Cloudflare；未托管可先用 `*.workers.dev` 免费子域。
- posts.js 无独立 tags 字段（仅分类 g 含 featured）；P0 实施 articles.json 时从 front matter 补齐 tags。
- llms.txt 不会被 agent 自动发现，须与 MCP 目录注册、页脚入口组合（文档 §6 风险 1 已列）。

---

### 2C.1 用户需求（脱敏保留）

> 用户说明：后续附件将先 push 到 GitHub 供下载，不再经 IM 传输；确认 v1.27 冷启动问题排查已完成。
> 本轮需求：① blog 同步的用途是「找出已发布文章与最近新增内容的差异，同步过一次不再额外同步」，没必要遍历历史上所有文章（现在约 1 万篇，十年后可能 10 万篇，也不能要求换新电脑后重跑全史）；公众号发布时已带发布时间，查该时间前后 30 天的更新即可。② 更新 blog 时正文标注「文/书航 yyyy.mm.dd」才是正确发布日期（转载稿可能在首发后晚几天才上公众号，如公司稿件），blog 文章发布日期应以实际发布为准而非公众号转载时间戳。③ daily 部分内容可能因审查在公众号被删除，重发当天信息时可能替换/删除条目；某日早报（每日aigc早报：yyyy.mm.dd）的第一次同步版本为准确版本，后续发布同日期早报可能删改内容，无需覆盖之前的版本。④ 检查 daily 同步过来的日报题图是否 1:1：若原图 2:3 再被裁切成 1:1，整体会比原图小一圈。⑤ blog 每篇文章同步时自动加 featured 标签，用于同步更新首页大图滚动区域。输出 v1.28 及打包，更新 todo。

### 2C.2 现状核实与设计

- 03/04 现状核实：04 的发布日期已以「文 / 书航」标注为最高优先级（v3.x 内建），本轮验证并放宽正则；03 的后台模式（non-interactive）已有覆盖确认兜底、auto 模式按仓库日期差集天然跳过同日重发，但「同日重发不覆盖」未成为明确语义且存在交互/手动路径绕过空间，本轮改为显式短路。
- 增量架构设计：仓库本身是「已同步」的真相源；本地 `blog_sync_memory.json`（URL → 同步时间戳）是加速层，使增量运行对已同步 URL 连 HTML 都不抓。窗口封顶 30 天保证任何情况下（含新电脑冷启动、长期停跑后恢复）分页遍历都只覆盖最近 30 天，历史全量永不重跑；窗口内已同步文章在首跑时借仓库存在性检查一次性补记，之后转秒级跳过。
- 题图校正设计：同步时用 Pillow 检查宽高比，非 1:1 按原始分辨率一次性中心裁切为最大正方形（JPEG q95 单次重编码/PNG 无损），展示端不再做缩放裁切，避免 2:3 被反复裁切导致整体比原图小一圈；GIF/动图跳过，失败保留原图。

### 2C.3 代码变更

- **04_convert-blog.py（v3.4 块）**：
  - 新增 `BLOG_SYNC_MEMORY_PATH` / `load_sync_memory` / `save_sync_memory`（原子写）/ `mark_article_synced`；main 循环对记忆命中的 URL 直接跳过（不抓 HTML），`process_article` 在「仓库已有」或「本次上传成功」时把 URL 记入记忆，上传失败不记录以保留重试机会。
  - 新增 `_build_tags_with_featured`：front matter tags 自动追加 `featured`（已含去重），`process_article` 生成 front matter 时调用。
  - `extract_date` 正则放宽：`文\s*/\s*书航\s*(\d{4})[.-](\d{1,2})[.-](\d{1,2})`（允许无空格与一位数月/日，兼容 `-` 分隔）。
- **03_convert-daily.py**：
  - `process_and_upload` 在提取日期后新增首同步短路：`_posts/{date}-daily.md` 已存在于 daily 仓库 → 记录日志「首同步版本为准，跳过不覆盖」并返回 True（不下载题图、不上传 md/图片）。
  - 新增 `ensure_square_cover`：题图下载落盘后、常规压缩前检查宽高比，非 1:1 中心裁切为最大正方形并按原格式高保真保存；GIF/动图与异常路径均保留原图。
- **keepitrun.py（→ 1.28）**：新增 `BLOG_SYNC_WINDOW_DAYS = 30` 与 `resolve_blog_since_date()`；首次启动与 10:10 调度两处 blog 参数构建均接入（上次爬取位置超过 30 天即截断到窗口下界并在日志说明）；模块 docstring 增加 v1.28 变更块。
- **readme.md**：版本头/v1.28 发布重点/03、04 表格行/运行时文件表/目录树/更新日志新条目；**.env.example** 头部版本号；**.gitignore** 增补 `blog_sync_memory.json`。

### 2C.4 验证证据

- 功能测试 **49/49 通过**（`scripts/test_keepitrun_v128.py`，隔离环境 + mock，不触网）：featured 标签 4 例；同步记忆读写回路/损坏自愈/非法条目过滤 7 例；发布日期变体与优先级 6 例；窗口封顶（边界/截断/非法值）与版本断言 8 例；题图校正（2:3→1:1、1:1 不动、PNG 无损、横图、动图跳过、损坏容错、中心内容保留）9 例；同日早报短路（返回值/检查路径/不下载/不存在时原流程不受影响）5 例；py_compile 10 脚本。测试中还确认裁切结果为有效 JPEG 且原图中心内容落在裁切结果中心。
- 打包 `keepitrun-v1.28.zip`（14 成员，124,389 bytes，SHA-256 `B9D0DD521C71862C47E8941D121B7EED98D418BBC84F817383BA8DBD7FA6E94D`）双份：For_Agents + 工作夹根；包内凭据模式扫描零命中。
- 仓库状态：v1.26 zip 从工作树移除，v1.27 zip 保留为回滚点。

### 2C.5 偏差与未完成项

- **featured 仅作用于新同步文章**：按「同步时候」的增量语义，历史文章不批量改写（避免触碰近万篇历史文件）；首页大图滚动区域通常只取最新若干篇，新同步文章自动携带即可。若需一次性为存量文章补 featured，可另开维护任务（建议用 Git Trees + 批量 commit，不逐文件 API）。
- **题图裁切为居中策略**：非 1:1 题图按中心裁切，必然损失长边两端的部分画面（用户已知「比原图小一圈」的折衷）；若希望改为留白补边（保完整画面）或顶部优先裁切，属一行策略切换，待用户反馈。
- 「文/书航」标注匹配依赖该署名格式；若转载稿署名格式不同（非书航署名），仍回退公众号时间戳。如出现此类样本可再扩签名列表。
- 生产机部署（解压替换 + 重启验证）由用户手动执行；v1.28 首跑 blog 增量会先对窗口内文章做一次存在性确认并写入 `blog_sync_memory.json`，属预期一次性成本。
- 用户将改为经 GitHub push 附件（不再经 IM），后续排障日志建议继续 push 到仓库 `logs/`。

### 2D.1 用户需求（脱敏保留）

> 每天首启被拖慢约 90 分钟？必须定位所有导致拖慢速度的问题点，每天冷启动总时间应控制在半小时之内。用户提供了几份运行日志（已提交到仓库 `logs/`）辅助定位。如需修改，输出 v1.27 及其打包，并更新 todo。

### 2D.2 根因定位（依据 0928 生产日志 + 仓库实测）

**冷启动时间线拆解**（`logs/20260928.log`，v1.24 生产当日记录）：

| 时段 | 任务 | 耗时 | 结论 |
|---|---|---|---|
| 09:39:53–09:42:55 | getrss 补抓（33s）→ combine 翻译（99s）→ daily（7s）→ blog（14s）→ photos（26s） | 约 3 分钟 | 全部正常 |
| 09:42:55–10:12:55 | `90_cleanup` 预览第 1 次 | **1800s 超时** | 卡在「[2/3] 检查每个文件」 |
| 10:13:25–10:43:25 | 第 2 次（重试延迟 30s） | **1800s 超时** | 同上 |
| 10:44:25–11:14:25 | 第 3 次（重试延迟 60s） | **1800s 超时** | 同上，最终「预览失败，停止实际删除」 |

三连超时合计约 91.5 分钟——与用户感知的「拖慢约 90 分钟」精确吻合；其余任务合计仅 3 分钟。另据 `task_completion.json`：**cleanup 自 v1.9 上线 67 天从未出现在完成记录中**，即每天烧 90 分钟却从未完成过一次扫描。

**两个叠加的代码级根因**（`90_cleanup-daily-from-blog.py` v1.9）：

1. **逐文件 API 拉全文**：`_posts/` 每个文件单独调 Contents API 取内容（每文件 1 次请求、约 0.5 秒），实际需要 100 分钟以上，且必然触发限流，在 1800 秒时限内永远无法完成；超时后重试机制原样再来三遍。
2. **列表虚假膨胀**：脚本以 `per_page=100` 分页列目录，但 GitHub Contents API 对目录列表忽略该参数（每页实际最多返回 1000 条），1458 个 `.md` 被重复计数成日志中的「20000 个」，且字典序第 1000 名之后的文件从未被检查过（本次已用 Git Trees API 实测确认真实文件数）。

**顺带发现的误删隐患**：v1.9 对文件名含 `aigc` 的文件不经内容确认即判待删除，而真实 `_posts` 里存在 `2024-03-22-aigc-shi-dai-de-di-yi.md` 等 4 篇正经 AIGC 主题文章——v1.9 若曾完成过一次扫描就会将它们误删。另据 03 的生成逻辑，真实泄漏文件的命名是 `YYYY-MM-DD-daily.md`（非拼音），v1.9 的拼音文件名模式本就匹配不到目标，内容匹配才是唯一可靠判据。

### 2D.3 修复内容（90_cleanup v2.0 + keepitrun.py 1.27）

- **扫描引擎重建**（`90_cleanup-daily-from-blog.py` → v2.0）：
  - Git Trees API 一次调用拿真实全量清单与 blob sha（失败回退旧分页列表并在输出中注明）；
  - 文件内容改经 `raw.githubusercontent.com` CDN 并行拉取（默认 16 线程，`--workers` 可调，不占 GitHub API 限速配额，429 指数退避重试）；
  - 新增增量缓存 `cleanup_scan_memory.json`（path → sha → 判定，原子写、自动修剪已删文件条目、损坏/版本不符自动重建）：内容未变不重拉，疑似早报命名（`YYYY-MM-DD-daily.md`）优先检查；
  - 内部时间预算 `--time-budget`（默认 900 秒，低于外层 1800 秒时限）：超限保存断点、以退出码 2 结束，由调度器重试与次日运行从缓存续扫，不再从头重扫；
  - 判定语义修正：判定 = front matter 内容匹配（categories/tags/title 模式与 v1.9 完全相同）或无歧义拼音组合文件名（`mei-ri-aigc*`/`aigc-zao-bao*`）；裸 `aigc`/`早报` 文件名仅作为候选透明化输出，不构成删除依据；
  - 修复 v1.9 遗留死代码：多行 tags 检查的 `^-` 模式要求行首，对标准 YAML 缩进列表（`  - 贴图`）永不命中，现改为 `^\s*-\s+`。
- **keepitrun.py → 1.27**：版本号、模块 docstring v1.27 变更块、cleanup 调用日志文案更新；同日任务去重（v1.26 语义）与超时上限不变。
- **readme.md**：版本头、v1.27 发布重点、90 表格行、更新日志新条目；**.env.example** 头部版本号同步；**.gitignore** 增补两个运行时状态缓存文件（`cleanup_scan_memory.json`、`rss_issue_memory.json`）。

### 2D.4 验证证据

- 功能测试 **46/46 通过**（`scripts/test_keepitrun_v127.py`，隔离环境 + mock，不触网）：判定语义 11 例（含 4 篇真实误删反例）、sha 增量缓存 8 例（命中不重拉/变更重拉/error 重试/断点落盘重载）、预算耗尽 6 例、Trees 解析与截断回退 3 例、优先级 1 例、缓存容错 2 例、py_compile 10 脚本。
- **真实仓库冒烟测试**（dry-run 只读，测试缓存事后清理）：1458 个文件首扫 **28.6 秒**完成、0 失败、退出码 0；二次运行缓存命中 1458/1458，**1.8 秒**完成。作为对照：v1.9 同一任务三连 1800 秒超时共 91.5 分钟且从未完成。
- 误删保护实测：`2023-11-24-aigc-gai-nian-gu-fa-san.md` 等 4 篇正经 AIGC 文章在 v2.0 下正确不判删并被透明化列出（v1.9 会全部误删）。
- 打包 `keepitrun-v1.27.zip`（14 成员，119,168 bytes，SHA-256 `EF61B3BCEE3A4A9BB905015749041A15B67E3A3BF0A09071CEDC2AE8B1E0B589`）双份：For_Agents + 工作夹根；包内凭据模式扫描零命中。

### 2D.5 偏差与未完成项

- **冷启动预算现状**：修复后每日首次启动 ≈ 正常任务 3 分钟 + cleanup 首扫约 0.5–1 分钟（缓存生成后每日秒级），远低于用户要求的 30 分钟上限；即使 raw CDN 全部失败，时间预算 + 退出码 2 + 外层 1800 秒兜底，最坏情况也不再叠加到 90 分钟。
- **其余任务的观察项**（均在 30 分钟预算内，本轮未动，记录备查）：02 标题翻译批次内重试较频繁（16 个标题耗约 76 秒）；01 的 39 个 RSS 源为串行抓取（33 秒）；05 photos 全月扫描（24 秒）。若未来冷启动需进一步压缩，可考虑 01 并行化与 02 翻译批内去重。
- cleanup 实际删除仍由 keepitrun「预览通过 → 实际执行」两段式完成；本轮只做 dry-run 验证，未对博客仓库做任何写操作。
- 用户需手动解压替换生产目录（保留 `.env`）；替换当日首跑 cleanup 全量扫描一次（约 1 分钟）后进入秒级常态。

### 2E.1 用户需求（脱敏保留）

> todo 已提到 For_Agents 文件夹，其他 todo 中间文件已删除，以 todo-full 为准。
> 1. 检查 combine-gemini 及其他可能用到 LLM 的地方是否使用最新模型：谷歌 Gemini 已升级到 3.8 flash 免费档，请首先查看官方 API 文档免费档位，然后在定义中选择最新模型；GLM 同样操作；其他模型用到的都根据官方完全免费的档位升级到最新版调用。不限于该脚本。
> 2. 刚才关闭 keepitrun 主脚本升级到 1.25 时，打开又重新运行了一次。本次以后的更新，在检查到版本号在今日替换时，首次运行新版只做今天还没做过的任务即可，不必所有事情都重来一遍。
> 3. 输出 1.26 打压缩包，更新 todo-full 加入本次工作日志；重命名文件为截稿时间（GMT+8）；并将每次更新工作日志的要求写入 todo-full 开头作为 agent 后续要遵循的事项。

### 2E.2 任务 1：LLM 免费档模型升级（02 / 92）

**排查范围**：全仓 10 个脚本 + 配置 JSON 扫描（generativelanguage/bigmodel/zhipu/openai/dashscope/groq/deepseek 等端点特征）。LLM 调用只存在于 `02_combine-gemini.py`（标题翻译链 Gemini → GLM HTTP → Google Free）与 `92_model-process.py`（可选后处理，Gemini → GLM SDK 回退）；keywords.json 中的 GPT/GLM 等词均为新闻分类关键词，非调用。03/04/05/90/91/01/image_routing 无任何 LLM 端点。

**官方文档核查**（2026-09-29 实测抓取）：

- Gemini：`ai.google.dev/gemini-api/docs/pricing`。`gemini-3.8-flash`（Gemini 3.8 Flash）在 Free Tier 列 "Free of charge"，Paid Tier 输入 $0.75/1M（2026-12-31 前价）；3.7/3.6/3.5/3.1/3.0/2.5 系列 Flash 均有免费档，3.8 为最新。**选定 `gemini-3.8-flash`**（与用户提示一致）。
- GLM：`docs.bigmodel.cn/cn/guide/start/pricing` 与模型概览页。GLM-5.3-Flash 输入 0.8 元/输出 2.8 元每百万 tokens，**为收费档，不符合"完全免费"**；GLM-4.7-FlashX 亦收费（0.5/3）。完全免费（输入/输出均标"免费"）的文本模型中最新为 **`glm-4.7-flash`**（200K 上下文/128K 输出，GLM-4.7 基座）；其余免费档 GLM-4.5-Flash、GLM-4-Flash-250414 均更旧。**选定 `glm-4.7-flash`**。

**代码变更**：

- `02_combine-gemini.py`：`GEMINI_MODEL` `gemini-2.5-flash` → `gemini-3.8-flash`；`GLM_MODEL` `glm-4-flash` → `glm-4.7-flash`；附官方定价出处注释。两处模型名均为参数传入引擎函数，无其他改动。
- `92_model-process.py`：`GEMINI_MODEL` → `gemini-3.8-flash`（删除过时的 "gemini-3-flash-preview" 注释）；`ZHIPU_MODEL` → `glm-4.7-flash`；回退提示文案去掉硬编码版本号。
- `.env.example`：`GEMINI_MODEL`/`GLM_MODEL` 可选覆盖项示例同步为新默认值；覆盖链路测试通过（环境变量覆盖优先级不变）。
- 兼容性：02 走官方 REST（GLM v4 chat/completions、generativelanguage SDK generateContent），模型名均为字符串参数，新模型无需接口变更；GLM-4.7-Flash 上下文 200K 远大于翻译批次需求。

### 2E.3 任务 2：同日版本替换不重做已完成任务（keepitrun.py 1.26）

**问题还原**（依据仓库内存档的生产日志 `logs/20260928.log` 与 `logs/task_completion.json`）：0928 全天任务由 v1.24 完成并记录；用户当日关闭脚本替换 v1.25 后，`should_task_redo` 判定 done_version(1.24) ≠ VERSION(1.25) 且任务在 `VERSION_TASK_CHANGES["1.25"]` 影响集内 → 触发 `version_changed` 重做；首次启动流程 `run_first_boot_tasks` 也无条件执行全部任务、不看当日完成记录。两条路径都会把当天已做过的事情重来一遍。

**处置**（v1.26 语义：今天已完成 = 已完成，无论由哪个版本完成）：

- 移除 `VERSION_TASK_CHANGES` 映射、`should_task_redo`、`get_tasks_changed_between`；`task_completion.json` 仍记录完成任务时的版本号，仅作审计与跳过提示。
- `should_run`：内存去重后仅查 `get_done_version_today`——今天已完成（任意版本）即跳过；版本不同时日志明确提示"版本替换日不重做"。
- `run_first_boot_tasks` 逐任务门控：combine/daily/blog/photos_update 均先查当日完成记录再执行；**cleanup（首次启动维护）也纳入完成记录**（`record_task_done("cleanup")`），成功才记，避免版本替换日重复 3×1800 秒的预览重试。
- 失败任务仍不记完成、次日或下次调度照常重试；昨日完成记录不影响今日运行（按日滚动语义不变）。
- 同步：模块 docstring v1.26 变更、启动横幅改为"同日任务去重: 已启用"、readme §同日任务完成追踪 + v1.26 更新日志、`.env.example` 头部版本。

### 2E.4 验证证据

- `py_compile` 全部 10 个脚本通过（04 的 docstring `\s` SyntaxWarning 为历史遗留，未改动）。
- 功能测试 **36/36 通过**（隔离副本 + monkeypatch，测试脚本 `scripts/test_keepitrun_v126.py`）：v1.26 模块断言 5 项；should_run 同日去重语义 7 项（未完成运行/完成跳过/旧版本今日完成跳过/昨日完成今日运行/会话内去重）；首次启动门控 15 项（全部已完成→零调用、全部未完成→全部执行并记录 v1.26、仅 combine 完成→其余执行）；02/92 模型默认值 4 项；02 `.env` 覆盖链路 2 项。
- 发行包：14 成员、正斜杠路径、无 `.env`/敏感条目；内容级凭据扫描仅命中 03/04/90 的 `ghp_xxxxx` 类**占位示例串**（帮助文本，非实值）。

### 2E.5 偏差与未完成项

- GLM 免费档停留在 glm-4.7-flash：GLM-5.3-Flash（2026-08-26 发布）与 FlashX 均为收费档，不满足用户"完全免费"限定；后续若智谱将 5.3-Flash 转免费可再升级。
- 生产日志发现 90_cleanup 预览在 2 万篇文章上 3 次×1800 秒全部超时（20260928.log 11:14 结束后才进入定时调度），本轮未处理——首轮启动已因此拖慢约 90 分钟；建议下轮评估（分批列出/缓存文件清单/提高时限/降频）。本轮 v1.26 的 cleanup 同日门控可避免版本替换日的重复浪费。
- 生产机部署（解压替换 + 重启验证）由用户手动执行；替换当日首次运行只会补做未完成任务，无需用户做任何额外操作。

## 2F. 前轮（2026-09-28）增量日志

### 2F.1 任务 1：piczip 核查结论与处置

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

### 2F.2 任务 2：getrss/02 的 24 小时已提取记忆

- 架构说明：按 v1.24 设计，跨批次去重职责在 `02_combine-gemini.py`（01 只抓取与规范化），因此本需求实现在 02。
- 新增根目录运行时文件 `rss_issue_memory.json`：02 每次成功写出摘要后，将本次全部条目记入（键与去重规则一致：优先最终规范化 URL，无链接项按标题文本；值为提取时间戳）。
- 合并流程在去重之后、翻译之前执行新过滤：过去 **24 小时**内已提取的条目直接跳过，并打印 `Past-24h already-issued duplicates removed: N`；全部条目都被过滤时不生成空摘要、正常退出。
- 记忆每次运行自动修剪（>24h 丢弃），原子写入（tmp + os.replace），写入失败仅警告不阻断主流程；文件损坏/缺失视为空记忆。
- 效果：摘要文件被用户取走后，早晨已发过的条目不会在下午摘要中重现；超过 24 小时的旧闻不受限。README 的"RSS 增量摘要规则""目录结构""文件清理策略"均已同步该文件（不应手动删除）。

### 2F.3 验证证据

- `py_compile` 全部 10 个脚本通过（沙箱 Python 3.12；04 的 docstring `\s` SyntaxWarning 为历史遗留，未改动其逻辑）。
- 功能测试 31 项全部通过（隔离副本执行，测试脚本 `scripts/test_keepitrun_v125.py`）：
  - 02 记忆链路 14 项：正常合并并建记忆（3 个唯一键，重复 URL 合并保留最长标题）→ 模拟用户取走摘要后重跑（跳过 3 条、不生成新摘要）→ 新旧混合输入（旧 URL 被跳过、新 URL 保留，记忆增至 4）→ 时间戳回拨 25 小时（条目重新出现，记忆修剪+回填）；
  - 03/04/91 压缩链路 17 项：透明 PNG 保持 `.png`、不透明 PNG→`.jpg`（既有规则）、JPEG 保持 `.jpg` 且 17,732→6,942 字节、动图 GIF 保持 `.gif` 且 2 帧保留、静态 GIF→PNG/JPG（既有规则）、WebP→JPG/PNG、无文件变大、无 `.tmp` 残留、91 报告中各格式均出现 `ok-pillow` 状态。
- 沙箱为 Linux，无法执行 Windows exe 语义测试；但移除 exe 后代码路径与平台无关，上述测试即为生产行为的直接验证。

### 2F.4 偏差与未完成项

- 05_photos-update.py 本身不上传图片，故未纳入压缩改造（原任务描述"上传到图床"经核实仅发生在 03/04）。
- zip 内路径分隔符由反斜杠改为正斜杠：Windows 资源管理器/7-Zip 解压均正常，属标准化修正而非行为变更。
- `.env.example` 头部版本号 v1.19→v1.25（历史遗漏的陈旧标注）。
- 生产机部署（解压替换 + 调度器重启验证）由用户手动执行，本轮未触碰生产。

## 3. 完整开发时间轴（v1.0 → v1.28）

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

见 §2D。

### 阶段七：v1.26（2026-09-29，上午轮）

见 §2C。

### 阶段八：v1.27（2026-09-29，午后轮）

见 §2B。

### 阶段九：v1.28（2026-09-29 中午）

见 §2B。

### 阶段十：站点 Agent 友好化调研 v1（2026-09-29 午后，非发版轮）

见 §2B。

### 阶段十一：航通社官网 MCP v1.0.0 上线（2026-09-29 午后第二轮，非发版轮）

见 §2A。

## 4. 运行规则与文件策略（现行有效）

- 调度（GMT+8）：02:00/14:00 getrss → 10:05 daily → 10:10 blog → 14:05 combine → 15:00 photos；90/91/92 手动。
- 根目录 `YYYYMMDD-HHMMSS.md` = 用户尚未取走的摘要；02 会把它与新 RSS 合并去重，原子写入新文件后才删旧摘要。
- `rss_issue_memory.json`（v1.25 新增）= 24 小时已提取记忆；不应手动删除，删除会短暂失去跨批去重能力；02 每次运行自动修剪。
- 翻译顺序 Gemini → GLM HTTP → Google Free（v1.26 默认模型：`gemini-3.8-flash`、`glm-4.7-flash`，均为官方免费档）；全部失败或安全拒答时保留英文源内容，不写错误文本、不丢条目。
- 清理：tmp/ 1 天、logs/ 7 天转归档、归档日志与 archived/ 30 天；`last_blog_crawl.txt`、`rss_issue_memory.json`、`blog_sync_memory.json`、`logs/task_completion.json` 不应手动删除。
- 版本感知任务追踪：v1.26 起改为**同日任务去重**——今天已完成（无论哪个版本）即不再执行，版本替换日首跑只补做未完成任务；`task_completion.json` 仅记完成版本供审计。
- blog 增量同步（v1.28）：04 以 `blog_sync_memory.json` 记录已同步 URL，命中即跳过；调度侧合集窗口封顶 30 天（`BLOG_SYNC_WINDOW_DAYS`），`last_blog_crawl.txt` 过旧时自动截断到窗口下界；发布日期以正文「文/书航」标注为准；新同步文章自动携带 featured 标签。
- daily 首同步保护（v1.28）：同日期早报已存在于 daily 仓库时直接跳过，不覆盖 md 与题图（首同步版本为准）；题图非 1:1 时按原始分辨率中心裁切为 1:1。
- 图床路由：blog/daily/Photos 均读目标站 `_config.yml` 的 `image_prefixes`（半开区间，不得重叠/留空档）；Photos 2026-07-31 前 `modem-56k/img@main`、2026-08-01 起 `modem-56k/img2@main`（公开仓库）。

## 5. 安全、打包与操作边界

### 5.1 铁律（继承并持续有效）

- `.env` 只留在生产机；不得读取、复制、打印、提交或进入 ZIP；任何交接文档不得写 token、Key、Cookie、密码或账号内容。
- 发行包仅含 `.env.example`、活动/维护脚本、配置 JSON、README；禁止 `.env`、日志、缓存、测试、备份、用户内容。v1.25 起不再包含 `piczip/oxipng.exe`。
- 修改生产前确认常驻进程状态并建立最小回滚备份；未经授权不停止/启动调度器。
- 每轮完成后在本文件追加增量日志并重命名文件名时间戳（详见文件开头 Agent 守则；不再新建单独 todo 文件）。

### 5.3 打包清单（v1.28）

`.env.example`、01–05、90–92、image_routing.py、keepitrun.py、keywords.json、readme.md、rss_feeds.json，共 14 项；SHA-256 见 §1。运行时状态文件不入包：`cleanup_scan_memory.json`、`rss_issue_memory.json`、`blog_sync_memory.json`（v1.28 新增）。

## 6. 下一位维护者先做什么

1. 读本文件与 `readme.md`，确认生产版本号与期望一致；检查调度器与子脚本进程状态。
2. RSS 出现重复条目时：先确认 `rss_issue_memory.json` 存在且时间戳新鲜；确认重复对是否超过 24 小时窗口（超窗重复属预期）。
3. 图片未压缩/体积异常时：确认 Pillow 已安装；03/04/91 已无外部 exe 依赖，失败会在日志/报告中有 `ok-pillow` 或原始状态，不再静默。
4. 凭据问题：先完成 §5.2 的轮换，再谈其他。
5. 改动后保持惯例：最小回滚点、受影响路径测试、更新本文件、重新生成脱敏包。

## 7. 归档说明

原 15 份文档移入 `For_Agents/todos/merged-sources-0928/`（git mv 保留历史），其中明文凭据已就地脱敏。本文件为唯一活跃交接文档；后续轮次按用户指示继续在本文件上追加增量并更新文件名时间戳。
