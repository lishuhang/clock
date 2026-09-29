# 站点 AI Agent 友好化调研 v1（lishuhang.me 主站 + daily 早报站）

- 生成时间：2026-09-29 12:50（GMT+8）
- 调研方式：对用户提供的 4 份前期资料全部做了一手抓取验证，并补充抓取了规范原文、官方文档与本站实测数据（快照存 `/home/z/my-project/recon/site-audit/`、`recon/3a/`，不在仓库内提交）。
- 状态：**v1（调研稿，供用户决策）**。本文档只调研与给方案，未对任何站点仓库做改动；keepitrun 本轮零改动。
- 一句话结论：**本站已经拥有一份现成的全站机器索引（`/assets/data/posts.js`，1458 篇全文元数据），只差"翻译成 agent 惯用的入口"——按本文 P0→P3 四层方案，全部落在 GitHub Pages 免费档 + Cloudflare Workers 免费档内，总成本 0 元，且不需要 keepitrun 做任何改动。**

---

## 0. 背景与约束（本轮需求）

用户目标（脱敏整理）：

1. 官网 lishuhang.github.io / lishuhang.me 文章势必越来越多，需要为 AI agent 的访问做适配：在 robots.txt 之外增加 agent 说明，把站内内容做成 skill 或 MCP 能力，增强站点对 agent 的吸引力。
2. 硬性成本约束：只能依赖 GitHub 免费档（Pages + Actions）、Cloudflare Workers 免费档；MCP/skill 的制作与运行不得产生任何费用。
3. 若需要动态更新，最多只能由 keepitrun 在每次推送新文章时顺手完成，不能引入额外的常驻维护负担。
4. 核心体验目标：AI 查询"本站发布过哪些文章"时应能一查即答，而不是像最初脚本那样跑几个小时遍历 GitHub repo；换新电脑、新 agent 都不应要求全量重跑。
5. 后续希望改进站内搜索，最好能接入免费 GLM 等，做成静态前端可用的 AI 搜索。
6. 交付物：调研 v1（本文档），包含三部分——网上已有案例整合、适合本站的 MCP/skill 方案、MCP/skill 完备之后的前端改善建议；同时覆盖主站 blog 与早报 daily 两个站点。

## 1. 本站现状盘点（2026-09-29 实测）

### 1.1 已有资产

| 项目 | 主站 blog（lishuhang.me） | daily 早报（lishuhang.me/daily/） |
|---|---|---|
| 构建体系 | Jekyll v3.10.0（GitHub Pages 构建） | Jekyll v4.4.1（GitHub Pages 构建） |
| 内容仓库 | `lishuhang/lishuhang.github.io`（公开，main 分支，约 249MB） | `lishuhang/daily`（公开，main/_posts） |
| 内容量 | **1458 篇文章**（posts.js 实测），2006–2026；sitemap 共 1605 URL | sitemap 630 URL（含少量非文章页，实际期数以建索引时精确化） |
| 机器可读索引 | **`/assets/data/posts.js`（977KB，1458 条）**：字段 `u`（URL）、`t`（标题）、`d`（日期）、`y/m`（年/月）、`g`（分类，含 featured）、`e`（长摘要，1364 条非空）、`i`（题图 URL） | 无独立数据文件（页面为静态列表） |
| Feed | `feed.xml`（Atom，仅最新 20 条） | `feed.xml`（RSS 2.0，仅最新 20 条） |
| robots.txt | `User-agent: * / Allow: /` + Sitemap 一行（对 AI 爬虫无差别全放行） | 同主站体系 |
| sitemap.xml | 有（201KB） | 有（68KB） |
| llms.txt / skill.md / agents.md / *.json 索引 | 均无（404） | 均无 |

### 1.2 关键发现与痛点

- **关键发现（方案基石）**：首页已在用 `/assets/data/posts.js` 驱动前端列表/翻页/标签筛选，等于全站文章的结构化索引**每天随 Jekyll 构建自动再生**、随 push 自动更新。它只差被"翻译"成 agent 世界的标准入口（llms.txt、JSON、MCP），无需从零建设任何索引。
- **agent 视角的三大痛点**：
  1. 问"你发过哪些文章"——唯一完整答案在 GitHub 仓库里，遍历一次数小时且未认证 GitHub API 限流 60 次/小时，实际不可用；RSS 只有 20 条，sitemap 只有 URL 没有标题摘要。
  2. 问某篇文章内容——只能抓 255KB 的 HTML 页面自行抽取正文，信噪比低、浪费 token。
  3. 站内搜索（`/?search=`）只在首页已加载的列表里过滤，没有独立索引页，agent 无从利用。
- **已就绪的隐性优势**：v1.28 起文章元数据质量很高——发布日期以「文/书航 yyyy.mm.dd」正文标注为准、每日早报首同步版本受保护不被审查删改覆盖、题图强制 1:1、新文章自动带 featured 标签。**agent 读到的将是"干净、准确、一致"的数据源**，这是很多大站都做不到的。

## 2. 网上已有案例整合（一手验证）

用户提供的 4 份资料 + 补充调研的规范原文与官方文档，按"模式"归为四类，外加一个特例。

### 2.1 四种模式总览

| 模式 | 代表案例 | 本质 | 成本 | 对本站适用度 |
|---|---|---|---|---|
| A. 静态说明文件（llms.txt / skill.md） | elsewhere.news、every.to | 一份教 agent"怎么用本站"的 Markdown | 0 | ★★★★★（P0/P1） |
| B. 站点自建远程 MCP | every.to（skills.every.to/mcp） | 网站暴露 search/list/get 三件套工具 | 托管费（有免费档则 0） | ★★★★★（P2） |
| C. 浏览器端 WebMCP | mabbs.github.io | 页面 JS 向浏览器内 agent 注册工具 | 0 | ★★★☆（P3 可选） |
| D. 为 AI 单独渲染的站点版本 | TIME（bot 专版 13KB） | 按 UA 返回精简 markdown + AI 专属广告 | 需服务端 | ★（不建议，见 2.6） |

### 2.2 llms.txt 规范（llmstxt.org，现 v2）

- 格式：可选 BOM → 一个 H1（项目名，唯一必需）→ blockquote 摘要 → 若干 H2 分节的链接列表（`[名称](URL): 注记`）→ `## Optional` 区放次要链接。文件保持小，细节放到各页的 `.md` 版本。
- 两点对本站直接有利：其一，规范原文点名 **GitHub Pages 项目站无法写 `/.well-known/`（RFC 8615）**，而 llms.txt 放站点根路径即可覆盖这个场景——本站正是 Pages 站，无障碍；其二，v2 自述已有数千站点采用、Chrome Lighthouse 会检测，说明"有总比没有好，且不会带来惩罚"。
- 局限（须清醒）：llms.txt **不会被 agent 自动发现和阅读**，它更像"agent 到站后的接待卡"。发现要靠：搜索引擎收录、MCP 目录注册、页脚入口链接，以及 MCP 工具本身。因此本方案把它与 B/C 配套使用而不是单点依赖。

### 2.3 elsewhere.news 的 skill.md（用户资料①，已一手验证）

- `https://elsewhere.news/skill.md` 是一份完整可安装的 Agent Skill（front matter：`name/version/user-invocable/compatibility/metadata` 等），正文定义了 Preflight 状态机（UNCHECKED/READY/BLOCKED）、固定 SHA-256 的客户端脚本、双模式：**匿名模式只允许 GET 公开页/llms.txt/feed.xml 取标题与短摘录**；Connected 模式绑定 `els_live_` 密钥后调用只读检索 API。
- 其 robots.txt 对 GPTBot/ClaudeBot/PerplexityBot 等 20+ AI UA 逐一 Allow，只禁 `/api/|/admin/|/studio/`；站点另有标准 llms.txt（注明语料 6568 篇文章 + 218 播客）。
- 可借鉴点：**把"允许 agent 做什么、不鼓励做什么"写成显式规则**（本站对应：允许查索引、取 raw.md 全文、引用 canonical URL；不鼓励遍历 GitHub 仓库与整站爬 HTML），并给 agent 一个可执行的最短路径。个人站无需它的密钥/签名脚本层，取其结构即可。

### 2.4 every.to 的 MCP（用户资料②，已一手验证）

- `every.to/llms.txt`（22KB）明列 MCP Endpoint；实测 `every.to/mcp` initialize 直接 200、**免鉴权、stateless（Streamable HTTP，无 session）**，`tools/list` 返回三个工具：`public_feed_tool`（最新免费文章）、`public_search_tool`（全文搜索）、`public_get_post_tool`（返回单篇 markdown 正文，镜像自 `every.to/:publication/:slug.md`——即**每篇文章都有直出的 .md 版本**）。
- 另一个端点 `skills.every.to/mcp` 则 401 需 OAuth（那是它的付费 Skill 库，与本场景无关）。
- **这是与本站最同构、可直接照抄的最小架构**：llms.txt + 每篇 .md 直出 + stateless MCP 三件套（feed/search/get_post），全部零鉴权零费用。本方案 §3.4 的工具集即按此扩写（增加 daily 早报与分页）。

### 2.5 WebMCP 与 mabbs.github.io（用户资料③，已一手验证）

- WebMCP 是 W3C 提案（webmachinelearning/webmcp）：网页用 JS 把函数/表单注册为带描述与参数 schema 的"工具"，供浏览器内置 agent 与扩展调用。webmcp.com 是收录目录（1301 站 / 7411 工具），收录免费：站点上线工具后经"Add your site"提交，扫描器验证即列录；目录还提供 agent 可读的 `/api/v1/sites/<host>` JSON。
- mabbs.github.io 是与本站完全同构的 Jekyll + GitHub Pages 博客，被收录 5 个工具：`blog_list_posts`（分页列全站：序号/标题/日期/链接/分类/标签/摘要，**不返回正文**）、`blog_get_post`、`blog_search_posts`、`blog_grep_posts`、`blog_read_post`。实现方式：`/assets/js/blog-console.js` 在页面里调用 `document.modelContext.registerTool(...)` 动态注册——首页 HTML 无任何 mcp 字样，纯前端、零后端、零费用。
- 可借鉴点：本站已有 `posts.js` + 标签筛选逻辑，包一层 `registerTool` 即可复制该站全部能力，并免费进目录；WebMCP 与远程 MCP 面向不同客户端（浏览器内 agent vs. Claude 等 MCP host），互补不冲突。

### 2.6 TIME 的 AI 专版（用户资料④，已一手验证）——一个"反面参照"

- 同一 URL 按 UA 返回不同内容：人类浏览器 303KB HTML；ClaudeBot/PerplexityBot/OAI-SearchBot 得到 **13KB text/markdown**（约 1/23）；GPTBot/ChatGPT-User 被 406 拒绝。AI 版由广告技术商 Mobian 注入广告：`x-mobian-impression` 头 + `cache-control: no-store`（每次抓取计一次曝光）、`x-mobian-tokens: 3323`（按 token 计量），赞助内容只出现在 AI 版。
- 争议点：AI 专属广告、按 token 计费、bot 版人类不可见、区别性封锁特定 bot。
- 对本站的启示是**反着做**：个人站没有广告销售链路，不必做 UA 魔改；正确的差异化是给 agent 一个"全网最干净、带准确发布日期、免鉴权"的版本——靠 Jekyll 直出静态文件天然达成，无需任何服务器逻辑。2.7 节回应用户"占据 agent 入口"的判断时再展开变现问题。

### 2.7 关于"占据 agent 入口位置"与流量变现（回应用户策略思考）

用户在资料①旁注的判断（媒体做 skill/MCP 是为了占据 agent 入口；若官网成为统一终点，流量成本与广告变现要另算）方向正确，落到本站可以这样处理：

- **入口≠终点**：agent 场景下的"入口"是目录与索引（MCP Registry、webmcp.com、llms.txt），"终点"是文章 canonical URL。MCP/skill 的设计应当**始终把 canonical URL 与作者署名放进返回结果**——引用者、读者、其他 agent 仍会回到 lishuhang.me，不存在"流量被截走在别处变现"的问题；反而头条号/企鹅号等平台账号继续作为"发现面"，官网作为"权威版"（发布日期以正文标注为准），分层分工。
- **变现顺序**：先零成本铺 agent 入口（本方案），站内广告位是独立的后置话题（若未来要上，可参考 TIME 的"AI 版可见广告"思路，但那需要服务端，届时再议）。
- **平台引导**：与 agent 友好化正交，属 SEO/分发范畴：保持各平台账号与官网同名同标题，让"全网搜站名→同名同题文章→官网为 canonical"成立即可，不需要为本站额外付费。

### 2.8 基础设施事实（免费额度核算的依据）

| 事实 | 数值/结论 | 来源与置信度 |
|---|---|---|
| CF Workers 免费档 | 100,000 请求/天；CPU 10ms/次；**支持 stateless MCP（`createMcpHandler()`，Streamable HTTP，无需 Durable Objects、无需付费计划）**；超限返回 1027；子请求 ≤50/次 | Cloudflare 官方文档，一手抓取 ✅ |
| CF Workers KV 免费档 | 读 100,000/天、写/删/list 各 1,000/天、1GB 存储 | 官方定价页 ✅ |
| GitHub Pages | 公开仓库免费；官方当前文档页只明确"每账号一用户站/每仓一项目站"；社区/历史文档软限额（≈100GB/月带宽、1GB 站点、10 次构建/小时）**本轮未能一手复核，引用需谨慎**，但本站流量级远低于阈值 | 官方页抓取成功但信息精简 ⚠️ |
| raw.githubusercontent.com | 公开仓库文件免鉴权直出（实测 200），可当免费内容 CDN；本站文章 markdown 源即公开仓库 `_posts/` | 实测 ✅ |
| api.github.com 未认证 | 60 次/小时/IP（实测曾 403）。**agent 方案绝不依赖它** | 实测 ✅ |
| MCP 官方注册表 | registry.modelcontextprotocol.io，`mcp-publisher` CLI + GitHub 鉴权，只登记元数据，**免费**；PulseMCP 明确"发官方 Registry 后自动同步收录"；mcp.so 收 $39（排除）；Smithery 未确认收费 | 一手抓取 ✅ |
| Anthropic Agent Skills（SKILL.md） | YAML front matter：`name`（必填，≤64，小写连字符）、`description`（必填，≤1024，写"做什么+何时用"）、`license/compatibility/metadata/allowed-tools`（可选）；目录结构 `SKILL.md + scripts/ + references/ + assets/`；网站可直接发布可下载 skill 包（elsewhere 即实例） | agentskills.io 规范 ✅（docs.claude.com 本环境区域屏蔽） |
| AGENTS.md | 给"进仓库干活的编码 agent"的说明（6 万+项目采用），与 llms.txt（给"读网站的 agent"）定位不同；本站仓库可顺手放一份，非本轮重点 | agents.md ✅ |
| 免费模型（v1.26 已核实） | GLM 完全免费档最新为 `glm-4.7-flash`（200K 上下文）；Gemini 免费档 `gemini-3.8-flash`；GLM-5.3-Flash 为收费档不采用 | docs.bigmodel.cn / ai.google.dev（v1.26 轮已一手核实）✅ |

## 3. 适合本站的 MCP/skill 方案（推荐架构 v1）

### 3.0 设计原则

1. **静态优先**：凡是能由 Jekyll 在构建时生成的东西，绝不引入运行时组件——push 即更新，天然满足"keepitrun 顺手更新"（其实 keepitrun 连改都不用改：它已经把文章推上去了，Pages 构建会自动再生索引）。
2. **仓库=真相源**：索引全部从 `_posts` front matter 生成，与 v1.28 确立的"仓库即真相、首同步为准、文/书航日期为准"完全一致；换新电脑、新 agent，一切都在 git 与 Pages 上，**没有任何状态需要重跑**。
3. **零鉴权、只读**：学习 every.to——公开内容全放行；不做写操作，自然也没有安全面。
4. **分页防爆炸**：所有列表类返回都分页/截断，摘要默认截 160 字，全文单独取。

### 3.1 总架构（四层，自下而上实施）

```text
[P0 静态层]  Jekyll 模板（layout:null）随每次 push 自动生成：
             /llms.txt          —— agent 接待卡（站点简介+索引入口+MCP 地址）
             /articles.json     —— 全站文章索引（blog，1458 篇起）
             /daily/issues.json —— 早报期号索引（daily）
                  │ 托管于 GitHub Pages（免费）
                  ▼
[P1 说明层]  /skill.md（教 agent 三步用法）+ /assets/js/webmcp.js（浏览器端注册工具）
                  ▼
[P2 服务层]  Cloudflare Worker（免费档）stateless 远程 MCP：
             site_overview / list_articles / search_articles / get_article
             / list_daily_issues / get_daily_issue
             数据源= articles.json（Cache API 缓存）+ raw.githubusercontent（全文 md）
                  ▼
[P3 发现层]  官方 MCP Registry 注册（免费）→ PulseMCP 自动收录
             webmcp.com 提交；页脚"AI/Agent"入口链接
```

### 3.2 P0 静态层（收益最大、改动最小，建议最先做）

**做法**：在 blog 仓库与 daily 仓库各加 2 个 `layout: null` 的 Jekyll 模板页。Jekyll 构建本来就遍历全站文章（posts.js 就是这么来的），模板循环 `site.posts` 输出 JSON/llms.txt 即可；**每次 keepitrun push 新文章 → Pages 自动构建 → 索引自动更新**，满足"顺手更新"且 keepitrun 零改动。

`/articles.json` 字段设计（与 posts.js 同源，另补 agent 需要的 3 个字段）：

```json
{
  "site": "lishuhang.me",
  "title": "书航的博客",
  "updated": "2026-09-29T01:30:34+00:00",
  "count": 1458,
  "articles": [
    {
      "url": "https://lishuhang.me/posts/2026/09/18/ai-duan-pian-da-sai-xian/",
      "title": "AI短片大赛现场，掌声到底给"故事"还是"炫技"？",
      "date": "2026-09-18",
      "date_note": "以正文「文/书航 yyyy.mm.dd」标注为准（v1.28 规则）",
      "categories": ["AI", "featured"],
      "tags": [],
      "excerpt": "……（截断 160 字）",
      "cover": "https://lishuhang.me/2026/09/18/ai-duan-pian-da-sai-xian/01.jpg",
      "raw_md": "https://raw.githubusercontent.com/lishuhang/lishuhang.github.io/main/_posts/2026-09-18-ai-duan-pian-da-sai-xian.md"
    }
  ]
}
```

规模核算：1458 篇 × 约 450B ≈ **0.7MB**；万篇 ≈ 5MB；十万篇需按年分片（`articles-2026.json` 等 + 一个分片清单）。llms.txt 本体约 200KB 以内（万篇级），保持"索引的索引"定位。10 万篇时 Jekyll 构建时长是主要风险（Pages 构建上限），届时把索引生成挪到 GitHub Actions（公开仓库免费）——设计里已预留这条退路，P0-P3 阶段用不到。

`/llms.txt` 草稿：

```markdown
# 书航（lishuhang.me）
> 中国科技/传媒领域写作者。主站 1458 篇文章（2006–2026），每日 AIGC 早报 630+ 期。
> 查询本站内容请用下方索引，不要遍历 GitHub 仓库或整站抓取 HTML。

## 文章索引
- [全站文章 JSON 索引](https://lishuhang.me/articles.json): 标题/日期/分类/摘要/题图/全文 raw.md 地址
- [每日 AIGC 早报索引](https://lishuhang.me/daily/issues.json): 全部期号（早报以每日首同步版本为准）
## 内容获取
- [Markdown 全文](https://raw.githubusercontent.com/lishuhang/lishuhang.github.io/main/_posts/): 命名 YYYY-MM-DD-slug.md
- [RSS 订阅](https://lishuhang.me/feed.xml): 最新 20 条
## Agent 服务
- [MCP Server](https://mcp.lishuhang.me/mcp): 搜索/列表/全文（Streamable HTTP，免鉴权）
- [skill.md](https://lishuhang.me/skill.md): 教 agent 使用本站的说明卡
## Optional
- [关于](https://lishuhang.me/about/): 作者简介与联系方式
- [图片库](https://lishuhang.me/photos/)
```

### 3.3 P1 说明层：skill.md + WebMCP

- `/skill.md`（elsewhere 模式精简版）：YAML front matter（name: lishuhang-me；description 写明"查询书航发布过的文章与每日 AIGC 早报时使用"）+ 正文三步法：① 读 `/llms.txt`；② 检索/翻阅 `/articles.json`（或直接调 MCP）；③ 取全文用 `raw_md`。附两条纪律：不要遍历 GitHub 仓库（未认证 API 限流 60 次/小时，必然失败）、引用时保留 canonical URL 与作者署名。
- `/assets/js/webmcp.js`（mabbs 模式）：页面加载后 `document.modelContext.registerTool` 注册 3 个工具——`blog_list_posts(page)`、`blog_search_posts(query)`、`blog_read_post(url)`，数据全部来自已有 `posts.js`（浏览器内已缓存），写约 100 行 JS；随后到 webmcp.com 免费提交收录。

### 3.4 P2 服务层：Cloudflare Workers 免费档 stateless MCP

- 实现：Worker + 官方 `createMcpHandler()`（Streamable HTTP、stateless、免鉴权，官方指南明确支持免费档）。Worker 首次请求拉取 `/articles.json` 与 `/daily/issues.json` 并用 Cache API 缓存（TTL 1 小时），`get_article` 按 URL 回源 raw.githubusercontent 并缓存——**单次工具调用 ≤2 个子请求，远低于免费档 50 上限**。
- 工具集（每篇返回都带 canonical URL）：

| 工具 | 输入 | 返回 | 说明 |
|---|---|---|---|
| `site_overview` | 无 | 站点简介、文章总数、早报期数、最新 5 篇 | agent 的"开场白" |
| `list_articles` | page, page_size≤50, category?, year?, tag? | 标题+日期+URL+摘要 | 分页，不回正文 |
| `search_articles` | query, limit≤20 | 命中列表（标题/日期/URL/摘要） | 索引内存匹配，1458 篇 <5ms |
| `get_article` | url 或 slug | 标题+发布日期+分类+**全文 markdown**+canonical | raw CDN + 缓存 |
| `list_daily_issues` | page, date range | 期号+日期+题图 | 早报索引 |
| `get_daily_issue` | date（如 2026-09-28） | 单期早报全文 markdown | 首 日同步版本为准 |

- 免费额度核算：每查询 1–2 个 Worker 请求，100,000/天对应数万次 agent 会话，个人站余量四个数量级；KV 可完全不用（省掉写入额度焦虑）；10ms CPU 对"JSON 内存匹配"绰绰有余。域名：若 lishuhang.me DNS 已托管 Cloudflare（本站图床体系本就用 CF 生态，需实施时确认），绑 `mcp.lishuhang.me` 自定义域免费；否则先用 `*.workers.dev` 免费子域起步。
- 注册发现：`mcp-publisher` CLI 登记官方 Registry（免费，GitHub 鉴权）→ PulseMCP 自动同步；webmcp.com 与 llms.txt 里的 MCP 入口互链。

### 3.5 效果对照（回应用户核心痛点）

| 场景 | 现状 | P0-P3 完成后 |
|---|---|---|
| agent 问"发过哪些文章" | 遍历 GitHub repo 数小时且被 API 限流打死 | 读 `/llms.txt` → `/articles.json`，或 `list_articles` 分页，**秒级** |
| agent 问某篇文章内容 | 抓 255KB HTML 自行抽取 | `get_article` 一次返回干净 markdown |
| agent 问某天早报 | 无从下手 | `get_daily_issue(date)` 一次返回 |
| 换新电脑 / 新 agent | — | 无任何状态需重建（索引在 git+Pages，MCP stateless） |
| keepitrun | — | **零改动**（push 即自动再生索引） |

## 4. MCP/skill 完备之后：前端访问改善建议

### 4.1 站内搜索升级（纯静态，两步走）

- 现状问题：`/?search=` 只过滤首页已加载的那一页数据，全站 1458 篇搜不全、无高亮、无摘要定位；"Google/Bing"档实际是跳站外 `site:` 搜索。
- 第一步（推荐先做）：**Fuse.js + articles.json**——前端直接复用 P0 的 `/articles.json`（0.7MB，gzip 后更小），全站标题/摘要模糊检索，零构建零服务端，与现有标签筛选 UI 无缝融合。
- 第二步（可选进阶）：**Pagefind**——构建期生成倒排索引，支持全文级命中与高亮；需要把索引生成挂到构建流程（本地构建提交或 GH Actions），复杂度略高，收益是长文全文检索。

### 4.2 AI 搜索（免费 GLM，静态前端可用）

- 架构：静态前端 → `CF Worker /api/ai-search` → ① Worker 内用 articles.json 做关键词召回（top 20，纯内存，10ms 内）→ ② 调 `glm-4.7-flash`（**完全免费档**，v1.26 已核实；备选 `gemini-3.8-flash` 免费档）生成 3–5 句带引用的回答 → ③ 返回 JSON（answer + 引用条目数组，含 canonical URL）。
- 防滥用（免费手段全够用）：API key 只存 Worker 环境变量（**绝不进 git、绝不进前端**）；KV 按 IP 限流（如 20 次/小时）；同问句答案缓存（命中率高的站点几乎不花 LLM 调用）；Origin 校验；LLM 失败/超时降级为纯检索结果列表。
- 前端形态：首页搜索框加"AI"档（与现有"站内/Google/Bing"并列），结果卡片带文章链接——**这就是"静态前端可展示可用的 AI 搜索"**，成本仍为 0。

### 4.3 站内聊天机器人（更后置，可选）

与 4.2 共用同一 Worker，加 `/api/chat`（SSE 流式）：系统提示词定位"书航站点的导读员"，检索逻辑复用 4.2 召回；建议等 AI 搜索稳定运行一段时间（观察滥用与调用量）后再上。Web 端挂一个小窗组件即可，仍全部免费档。

### 4.4 daily 早报站专属建议

- `issues.json`（P0 已含）+ 侧栏"最新一期"直链；早报数据天然适合 agent 每日定时拉取（feed 只有 20 条的问题被索引解决）。
- 题图 1:1（v1.28 已保证）在索引 `cover` 字段直接可用，首页大图滚动区与 agent 摘要卡可共用同一素材，无需再裁切。
- 「每日首同步版本为准」原则在索引层自动成立：索引从仓库生成，仓库里的就是首同步版本。

### 4.5 其他小项（顺手级）

- 首页 HTML 255KB 偏重（内联数据+样式），可做关键 CSS 拆分与 `posts.js` 摘要截断（`e` 字段目前过长，977KB 里大头是它；P0 出 JSON 版时截 160 字即可，网页版可另出精简文件）。
- robots.txt 保持极简即可（全站对 AI 开放是本站策略）；不建议加非标指令，避免误导。

## 5. 实施路线图

| 阶段 | 内容 | 预计工作量 | 依赖 | 验证方式 |
|---|---|---|---|---|
| P0 | blog/daily 各加模板：`llms.txt`、`articles.json`、`issues.json`；页脚加"AI/Agent"入口 | 2–4 小时 | 无（纯 Jekyll 模板） | curl 三件 200 + 字段抽查；push 一篇测试文看自动更新 |
| P1 | `/skill.md` + `webmcp.js` + webmcp.com 提交 | 2–3 小时 | P0 | 浏览器 agent 实测注册；webmcp 扫描收录 |
| P2 | CF Worker 远程 MCP + `mcp.lishuhang.me` + 官方 Registry 注册 | 3–5 小时 | P0；确认域名 DNS 在 CF（否则先用 workers.dev） | MCP Inspector 实测 6 工具；Registry 页面可查 |
| P3a | Fuse.js 全站搜索 | 1–2 小时 | P0 | 首页搜索全站命中 |
| P3b | Worker AI 搜索（GLM flash + 限流 + 缓存） | 3–4 小时 | P0；GLM key（仅存 Worker 环境变量） | 前端问答抽测；限流验证 |
| P3c | 聊天机器人 widget | 2–4 小时 | P3b 稳定后 | 同上 |

建议节奏：P0+P1 一轮做完即可让"查文章秒回"成立；P2 使 Claude 等主流 MCP host 可直接挂载；P3 按体验优先级排期。所有阶段合计成本 0 元。

## 6. 风险与边界

1. **llms.txt 不是强制标准**，agent 不会自动来读——因此方案是"索引文件 + MCP 注册 + 目录收录 + 页脚入口"组合拳，单一环节失效不影响整体。
2. **CF Workers 10ms CPU**：只做内存匹配与转发，不做分词/向量重计算；十万篇规模时搜索改为"年份/分类过滤 + 年内匹配"或引入 KV/Vectorize（免费额度届时再核）。
3. **GitHub Pages 构建时长**：十万篇时 Liquid 全量循环有超时风险，退路是 GH Actions 生成索引（公开仓库 Actions 免费），P0-P3 不需要。
4. **api.github.com 限流 60 次/小时**：所有 agent 入口明确指示"用索引、别用 GitHub API"，skill.md 与 llms.txt 双处写明。
5. **域名前提**：P2 绑自定义域需 lishuhang.me DNS 托管在 Cloudflare；未托管不影响 P0/P1，且 workers.dev 子域可先行。
6. **不建议 TIME 式 UA 魔改**：需要服务端、有 cloaking 争议，静态站无收益；"最干净的 AI 版"用静态直出达成。
7. **额度重置口径**：CF 免费额度按 UTC 日重置；官方 MCP Registry API 处于 v0.1 冻结期，登记格式以实施日文档为准。

## 附录 A：实测快照索引

- 站点抓取：`recon/site-audit/`（home.html、robots.txt、sitemap.xml、feed.xml、daily*.xml、posts.js、main.js 等 14 个文件）
- 案例一手快照：`recon/3a/`（子代理抓取存档）
- 关键实测数：posts.js 977,298B/1458 条；blog sitemap 1605 URL；daily sitemap 630 URL；feed 各 20 条；`every.to/mcp` initialize 200 免鉴权；`skills.every.to/mcp` 401；`registry.modelcontextprotocol.io` 200；`raw.githubusercontent.com` 免鉴权 200；`api.github.com` 未认证 60/h（曾 403）。

## 附录 B：参考链接

- 规范：llmstxt.org（v2）｜agents.md｜agentskills.io/specification｜W3C webmachinelearning/webmcp
- 案例：elsewhere.news/skill.md｜every.to/mcp + every.to/llms.txt｜mabbs.github.io（/assets/js/blog-console.js）｜webmcp.com/sites/mabbs.github.io｜vincentschmalbach.com/time-serves-ai-bots-a-different-website/
- 基础设施：developers.cloudflare.com/agents/guides/remote-mcp-server/（+ workers limits/pricing、KV pricing）｜docs.github.com/pages｜registry.modelcontextprotocol.io｜pulsemcp.com/submit｜mcp.so/submit
- 本站既有体系：`/assets/data/posts.js`｜`feed.xml`｜`/daily/`｜clock 仓库 keepitrun v1.28（发布日期/首同步/题图/featured 规则的来源）
