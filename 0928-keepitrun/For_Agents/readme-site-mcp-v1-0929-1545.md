# 航通社官网 MCP 上线说明（v1）

- 上线时间：2026-09-29 15:45（GMT+8）
- 状态：**已全线上线并实测通过**。本文档是航通社官网 AI Agent 能力的唯一说明与 changelog 载体；配套调研详见同目录 `research-site-agent-friendly-v1-0929-1250.md`。
- 设计原则：**整合已有资产、不重复造轮子**——索引由 Jekyll 构建时从同一份 `_posts` 数据再生（与首页 `posts.js` 同源同管线），全文直接复用公开仓库 raw CDN，MCP 只做无状态转发与缓存；keepitrun 与生产机**零改动**。

---

## 1. 上线了什么（全部实测 200）

| 端点 | 内容 | 实测 |
|---|---|---|
| https://lishuhang.me/llms.txt | agent 接待卡：站点简介 + 全部索引/服务入口 + 元数据口径 | 200，1.9KB |
| https://lishuhang.me/articles.json | **全站文章 JSON 索引**：1458 篇（2006–2026），字段 url/title/date/categories/tags/featured/excerpt/cover/raw_md | 200，约 1.0MB |
| https://lishuhang.me/daily/issues.json | **早报期号 JSON 索引**：629 期 | 200，约 353KB |
| https://lishuhang.me/daily/llms.txt | 早报子站的 agent 说明卡 | 200 |
| https://lishuhang.me/skill.md | agent 使用说明卡（三步用法 + 纪律 + 工具一览） | 200 |
| https://lishuhang.me/assets/js/webmcp.js | 浏览器端 WebMCP 工具注册（blog_list_posts / blog_search_posts / blog_read_post），已随全站页面引入 | 200，5.4KB |
| **https://mcp.lishuhang.com/mcp** | **航通社官网 MCP Server**（Cloudflare Workers 免费档，Streamable HTTP，免鉴权，无状态） | 200，六工具全通 |
| 官方 MCP Registry | 已收录 `io.github.lishuhang/site-mcp` v1.0.0（active，2026-09-29 15:36），remote 指向上行端点；PulseMCP 等目录宣称自动同步 | registry.modelcontextprotocol.io 实测返回 |

首页 `<head>` 已带 `<link rel="describedby" href="/llms.txt">`（llms.txt v2 建议的发现方式），页面已引入 webmcp.js。

## 2. MCP Server 详情

- 端点：`https://mcp.lishuhang.com/mcp`（域名按用户指示使用 lishuhang.com 子域；blog 本体全部链接保持 lishuhang.me）
- 传输：Streamable HTTP（POST JSON-RPC，响应 application/json；无 SSE 长连接、无会话）
- 鉴权：无（全只读、无写操作、无密钥）
- 实现依赖：零（无 npm 依赖，单文件 `site-mcp/index.js`，见 clock 仓库）
- 数据流：

```text
keepitrun 推送文章（不变）
  → GitHub Pages 自动构建（blog/daily 两仓库的 Jekyll 模板再生 articles.json / issues.json / llms.txt）
  → Worker 按需拉取索引并缓存 1 小时；全文按需拉 raw.githubusercontent.com 缓存 1 天
  → agent 一次工具调用即得答案（不再有"遍历 repo 几小时"）
```

- 工具清单（六个，全部实测）：

| 工具 | 功能 | 实测结果 |
|---|---|---|
| site_overview | 站点概览：blog 1458 篇 / daily 629 期、最新内容、全部入口 | ✓ |
| list_articles | 分页 + 按分类/标签/年份/关键词过滤文章（tag=featured 命中 14 篇） | ✓ |
| search_articles | 关键词搜索（标题加权，"AI短片"命中并返回 URL） | ✓ |
| get_article | 单篇全文 markdown（9KB 样例，含「文/书航」日期标注） | ✓ |
| list_daily_issues | 分页/按年份与日期区间列早报 | ✓ |
| get_daily_issue | 单期早报全文（`2026.9.28` 自动归一化为 2026-09-28） | ✓ |

- 冒烟测试命令（无需任何鉴权）：

```bash
curl -sS -X POST https://mcp.lishuhang.com/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"site_overview","arguments":{}}}'
```

- 在 Claude 等客户端挂载：远程 MCP，URL 填 `https://mcp.lishuhang.com/mcp`，选 Streamable HTTP，无需认证。
- 官方 Registry 收录页：`https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.lishuhang/site-mcp`（名称为 GitHub 命名空间，见 §4/§5 的取舍说明）。

## 3. 与已有资产的整合（本轮零重复建设）

| 已有资产 | 如何复用 |
|---|---|
| 首页索引 `assets/data/posts.js` 及其模板 | articles.json 复用同一 Jekyll 遍历与字段口径（excerpt 管线 `strip_html → normalize_whitespace → truncatewords:30`，另加 `truncate:280` 限长），并补 tags/featured/raw_md 三字段 |
| `_config.yml` 的 `image_prefixes` | articles.json/issues.json 的 cover 按现行规则改写为 `https://lishuhang.me/img` + `post.image`（**顺带修复了 posts.js 题图为 404 旧路径的问题**，新旧索引并存、互不影响） |
| 公开仓库 `_posts/` markdown 源 | 全文 = raw.githubusercontent.com 免鉴权直链，Worker 只做缓存转发，不在 Workers 侧存任何内容 |
| keepitrun v1.28 规则 | 「文/书航」发布日期、早报首同步保护、1:1 题图、featured 标签全部自然带入索引与 MCP 返回（索引由仓库文件生成，仓库即真相源） |
| clock 仓库 | Worker 源码与 server.json 入库 `site-mcp/`，部署命令见该目录 README |
| 调研 v1 | 本 README 是其 P0+P1+P2 的落地版 |

## 4. Changelog

### 2026-09-29 v1.0.1（官方 Registry 收录）

- **官方 MCP Registry 收录完成**：`io.github.lishuhang/site-mcp` v1.0.0，status=active（publishedAt 2026-09-29T07:36:57Z 即 GMT+8 15:36），remote=streamable-http `https://mcp.lishuhang.com/mcp`。收录后 PulseMCP 等目录按其同步机制自动跟进，无需逐家提交。
- `server.json` name 从 `com.lishuhang/site-mcp` 改为 `io.github.lishuhang/site-mcp`：域名式名称要求 DNS/HTTP 域名鉴权，两者当时均不可用（见 §5.1），GitHub 设备流要求 `io.github.<用户名>/` 前缀。
- 新增备用资产（零成本保留）：lishuhang.com apex TXT 所有权记录（ed25519 公钥）；`lishuhang-mcp-registry-proof` Worker + 精确路径路由 `lishuhang.com/.well-known/mcp-registry-auth`（现被根域跳转规则遮蔽，跳转规则一旦排除该路径即恢复 HTTP 鉴权通道可用）。
- 经验记录：Registry DNS 鉴权查的是 **apex 裸域 TXT**（`_mcp-registry-auth.` 前缀是源码里点名的常见错放）；Registry 自有解析器（34.118.224.10）当日对 lishuhang.com 返回 NXDOMAIN，属其基础设施侧问题。

### 2026-09-29 v1.0.0（首发上线）

- **blog 仓库**（lishuhang.github.io，commit `dd5075b` + `23f5a88`）
  - 新增 `articles.json`（Jekyll 模板，1458 篇全量索引，含 featured 标记与 raw_md 直链）
  - 新增 `llms.txt`（agent 接待卡，v2 规范格式）
  - 新增 `skill.txt` → 直出 `/skill.md`（Jekyll 对含 front matter 的 .md 会转 HTML，故用 txt 模板 + `permalink: /skill.md`，文件内含原因注释）
  - 新增 `assets/js/webmcp.js`（浏览器端三工具注册，数据惰性读取 posts.js）
  - `_layouts/base.html` 引入 webmcp.js（main.js 下一行）；`_includes/head.html` 加 describedby 链接
- **daily 仓库**（commit `abf2a21`）
  - 新增 `issues.json`（629 期全量索引）
  - 新增 `llms.txt`（子站版）
- **Cloudflare Workers**（lishuhang-site-mcp，版本 `9dfe2f30`）
  - 新增 Worker：stateless MCP Server，六工具，零依赖，绑定自定义域 `mcp.lishuhang.com`
  - 源码入库 clock 仓库 `site-mcp/`（index.js / wrangler.toml / server.json / README），仓库内无任何凭据
- **clock 仓库**：本 README + todo 更新

## 5. 待办（需要用户动作或额外权限，均为免费）

1. ~~官方 MCP Registry 收录~~ **已完成（2026-09-29 v1.0.1，见 §4）**。三条通道的实测结论存档：
   - DNS 鉴权：TXT 须建在 **apex 裸域**（服务端源码 dns.go `LookupTXT(ctx, domain)`，`_mcp-registry-auth.` 前缀是常见错放）；TXT 资产已在 apex 就位且全球可见，但 Registry 自有解析器当日对 lishuhang.com 返回 NXDOMAIN（其基础设施问题），通道暂不可用——日后可在 `mcp-publisher login dns --domain lishuhang.com --private-key <hex>` 上重试，恢复后可再发布域名式名称 `com.lishuhang/site-mcp`。
   - HTTP 鉴权：要求 `https://lishuhang.com/.well-known/mcp-registry-auth` 200 直出且不跟随重定向；proof Worker 已部署在该精确路径，但被根域跳转规则先于 Worker 拦截（301）。**若在 CF 里把该路径从跳转规则中排除（需 Rulesets 编辑权限，当前 token 没有），通道即自动恢复。**
   - GitHub 设备流：`mcp-publisher login github` → 浏览器打开 github.com/login/device 输码授权 → `publish`（本轮即经此通道完成）。
2. **webmcp.com 收录**：浏览器打开 webmcp.com → "Add your site" 提交 `lishuhang.me`（免费，扫描器验证工具在线即收录）。
3. **CF token 权限现状备忘**：可部署 Workers（含自定义域）、DNS/Zone 可读写（v1.0.1 轮已验证 TXT 创建与删除）；仍无 Rulesets 写权限；`/user/tokens/verify` 对该类 token 返回 Invalid 属正常现象（账户级 token 不支持 user 端点）。
4. **P3 前端路线**（见调研 v1 §4/§5，未实施）：Fuse.js 全站搜索 → CF Worker + glm-4.7-flash 免费档 AI 搜索 → 聊天机器人。

## 6. 维护与回滚

- **日常更新 = 零操作**：keepitrun 推文后 Pages 自动再生索引（约 1–2 分钟），Worker 缓存 1 小时后自然跟进。
- 改 MCP 代码：编辑 `clock/site-mcp/index.js` → `cd site-mcp && CLOUDFLARE_API_TOKEN=<token> npx wrangler deploy`（token 只放环境变量）。
- 回滚 MCP：`npx wrangler delete`（或 CF 控制台删除 Worker），站点其余能力不受影响。
- 回滚站点入口：revert 两仓库对应 commit 即可（Jekyll 模板均为新增文件 + 两处一行级编辑）。
- 免费额度：Workers 100k 请求/天（当前用量 <0.1%）；Pages/Jekyll 无新增成本；无 KV/R2/DO 依赖。

## 7. 已知偏差与注意事项

- articles.json 覆盖**全部** 1458 篇（含首页 posts.js 因 `tags contains 'AIGC'` 排除的文章）——对 agent 更完整；如需与首页口径一致可加过滤。
- cover 字段为改写后的 `/img/` 正确路径；posts.js 的 `i` 字段旧路径问题未回改（避免动生产首页逻辑），新索引已给出正确值。
- 换新电脑/新 agent 均无状态需要重建：索引在 git+Pages，MCP 无状态。
- 早报「首同步为准」、发布日期以正文「文/书航」为准两条口径已写入 llms.txt/skill.md/MCP 返回，agent 侧可感知。
