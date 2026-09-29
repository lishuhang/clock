# lishuhang-site-mcp（航通社官网 MCP Server）

Cloudflare Workers 免费档上的 stateless MCP Server（Streamable HTTP、免鉴权、零 npm 依赖）。

- 线上端点：`https://mcp.lishuhang.com/mcp`（GET 返回 405 属预期；POST JSON-RPC）
- 工具：site_overview / list_articles / search_articles / get_article / list_daily_issues / get_daily_issue
- 数据源：`https://lishuhang.me/articles.json` 与 `https://lishuhang.me/daily/issues.json`（Jekyll 构建时再生，keepitrun 推文即更新）；全文走 raw.githubusercontent.com
- 缓存：索引 1 小时（Cache API）、全文 1 天
- 完整说明与 changelog：`../0928-keepitrun/For_Agents/readme-site-mcp-v1-0929-1545.md`

## 部署 / 更新

```bash
cd site-mcp
CLOUDFLARE_API_TOKEN=<token> npx wrangler deploy
```

token 只放环境变量；仓库内不含任何凭据。

## 官方 Registry 发布（已完成）

- `server.json`（name: `io.github.lishuhang/site-mcp`）已于 2026-09-29 发布至官方 Registry 并处于 active 状态（发布记录见主 README §4 changelog v1.0.1）。
- 更新版本流程：改 `server.json` 的 `version` → `mcp-publisher login github`（浏览器设备流授权）→ `mcp-publisher publish`。
- 备用通道（域名式名称 `com.lishuhang/site-mcp`）：DNS 鉴权 TXT 已在 apex 就位、HTTP 鉴权 proof Worker 已部署，启用条件见主 README §5.1。
