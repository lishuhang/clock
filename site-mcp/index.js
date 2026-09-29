/**
 * 航通社官网 MCP Server（stateless / Streamable HTTP / 免鉴权）
 * 域名：https://mcp.lishuhang.com/mcp （Cloudflare Workers 免费档）
 *
 * 数据源（全部为 lishuhang.me 静态索引，keepitrun 每次推文后由 GitHub Pages 自动再生）：
 *   - 文章：https://lishuhang.me/articles.json
 *   - 早报：https://lishuhang.me/daily/issues.json
 * 全文：raw.githubusercontent.com 免鉴权直链（索引 raw_md 字段）
 *
 * 设计要点：
 *   - 无第三方依赖：手写 JSON-RPC（initialize / notifications/initialized / ping /
 *     tools/list / tools/call），响应 application/json（Streamable HTTP 允许非 SSE）
 *   - 无状态：不使用 Durable Objects / KV / 会话；索引与全文经 Cache API 缓存
 *   - 免费额度：Workers Free 100k 请求/天、单次 CPU 10ms；单工具调用 ≤2 个子请求（限额 50）
 *   - 只读：所有工具均为只读，不涉及任何写操作与鉴权
 */

const VERSION = '1.0.0';
const ARTICLES_URL = 'https://lishuhang.me/articles.json';
const ISSUES_URL = 'https://lishuhang.me/daily/issues.json';
const INDEX_TTL = 3600;   // 索引缓存 1 小时（与上游 Pages 再生节奏匹配）
const RAW_TTL = 86400;    // 全文缓存 1 天
const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, POST, OPTIONS',
  'access-control-allow-headers': 'content-type, accept, mcp-session-id, mcp-protocol-version, authorization',
  'access-control-max-age': '86400',
};

/* ---------------- 数据层（Cache API） ---------------- */

async function getJSON(ctx, url, ttl) {
  const cache = caches.default;
  const hit = await cache.match(url);
  if (hit) return hit.json();
  const upstream = await fetch(url, {
    headers: { 'user-agent': 'lishuhang-site-mcp/' + VERSION, 'accept': 'application/json' },
    cf: { cacheEverything: true, cacheTtl: ttl },
  });
  if (!upstream.ok) throw new Error('上游不可用 HTTP ' + upstream.status + ': ' + url);
  const data = await upstream.json();
  const cached = new Response(JSON.stringify(data), {
    headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=' + ttl },
  });
  if (ctx) ctx.waitUntil(cache.put(url, cached.clone()));
  return data;
}

async function getText(ctx, url, ttl) {
  const cache = caches.default;
  const key = new Request('https://raw-cache.internal/?u=' + encodeURIComponent(url));
  const hit = await cache.match(key);
  if (hit) return hit.text();
  const upstream = await fetch(url, {
    headers: { 'user-agent': 'lishuhang-site-mcp/' + VERSION },
    cf: { cacheEverything: true, cacheTtl: ttl },
  });
  if (!upstream.ok) throw new Error('全文获取失败 HTTP ' + upstream.status + ': ' + url);
  const text = await upstream.text();
  const cached = new Response(text, {
    headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'public, max-age=' + ttl },
  });
  if (ctx) ctx.waitUntil(cache.put(key, cached.clone()));
  return text;
}

/* ---------------- 工具实现 ---------------- */

function normDate(s) {
  if (!s) return '';
  const m = String(s).trim().match(/^(\d{4})[.\-\/年]?(\d{1,2})[.\-\/月]?(\d{1,2})/);
  if (!m) return '';
  return m[1] + '-' + String(m[2]).padStart(2, '0') + '-' + String(m[3]).padStart(2, '0');
}

function paginate(list, args) {
  const pageSize = Math.min(Math.max(Number(args.page_size || args.pageSize || 20), 1), 100);
  const page = Math.max(Number(args.page || 1), 1);
  return {
    total: list.length,
    page: page,
    page_size: pageSize,
    pages: Math.ceil(list.length / pageSize) || 1,
    items: list.slice((page - 1) * pageSize, page * pageSize),
  };
}

function articleBrief(a) {
  return {
    title: a.title, date: a.date, url: a.url,
    categories: a.categories || [], tags: a.tags || [],
    excerpt: a.excerpt || '',
  };
}

async function toolSiteOverview(ctx) {
  const [art, iss] = await Promise.all([
    getJSON(ctx, ARTICLES_URL, INDEX_TTL),
    getJSON(ctx, ISSUES_URL, INDEX_TTL),
  ]);
  return {
    site: '航通社（lishuhang.me）',
    author: '书航',
    description: art.description,
    blog: {
      count: art.count, updated: art.updated,
      latest: art.articles.slice(0, 5).map(articleBrief),
    },
    daily: {
      count: iss.count, updated: iss.updated,
      latest: iss.issues.slice(0, 3).map(articleBrief),
    },
    endpoints: {
      llms_txt: 'https://lishuhang.me/llms.txt',
      articles_json: ARTICLES_URL,
      daily_issues_json: ISSUES_URL,
      skill_md: 'https://lishuhang.me/skill.md',
      mcp: 'https://mcp.lishuhang.com/mcp',
    },
    metadata_note: '发布日期以正文「文 / 书航 yyyy.mm.dd」为准；早报同日重发不覆盖，以每日首次同步版本为准。',
  };
}

async function toolListArticles(ctx, args) {
  const art = await getJSON(ctx, ARTICLES_URL, INDEX_TTL);
  let list = art.articles;
  if (args.category) { const c = String(args.category); list = list.filter(a => (a.categories || []).includes(c)); }
  if (args.tag) { const t = String(args.tag); list = list.filter(a => (a.tags || []).includes(t)); }
  if (args.year) { const y = String(args.year); list = list.filter(a => a.date.slice(0, 4) === y); }
  if (args.q) {
    const q = String(args.q).toLowerCase();
    list = list.filter(a => (a.title || '').toLowerCase().includes(q) || (a.excerpt || '').toLowerCase().includes(q));
  }
  const p = paginate(list, args);
  return { total: p.total, page: p.page, page_size: p.page_size, pages: p.pages, articles: p.items.map(articleBrief) };
}

async function toolSearchArticles(ctx, args) {
  const art = await getJSON(ctx, ARTICLES_URL, INDEX_TTL);
  const q = String(args.query || '').trim();
  const limit = Math.min(Math.max(Number(args.limit || 10), 1), 30);
  if (!q) return { query: q, hits: 0, results: [] };
  const tokens = q.split(/\s+/).filter(Boolean);
  const scored = [];
  for (let i = 0; i < art.articles.length; i++) {
    const a = art.articles[i];
    let score = 0;
    for (const tk of tokens) {
      if ((a.title || '').includes(tk)) score += 5;
      if ((a.tags || []).some(t => t.includes(tk)) || (a.categories || []).some(c => c.includes(tk))) score += 3;
      if ((a.excerpt || '').includes(tk)) score += 1;
    }
    if (score > 0) scored.push({ score, a });
  }
  scored.sort((x, y) => y.score - x.score);
  return {
    query: q, hits: scored.length,
    results: scored.slice(0, limit).map(s => ({ ...articleBrief(s.a), score: s.score })),
  };
}

function findArticle(art, args) {
  const list = art.articles;
  if (args.url) {
    const u = String(args.url);
    const tail = u.replace(/https?:\/\/[^/]+\//, '').replace(/\/?$/, '/');
    const a = list.find(x => x.url === u || x.url.replace(/\/?$/, '/') === tail || x.url.endsWith(tail));
    if (a) return a;
  }
  if (args.slug) {
    const s = String(args.slug).replace(/\.md$/, '').replace(/\/?$/, '/');
    const a = list.find(x => x.url.endsWith('/' + s) || x.raw_md.endsWith('/' + s + '.md'));
    if (a) return a;
  }
  return null;
}

async function toolGetArticle(ctx, args) {
  const art = await getJSON(ctx, ARTICLES_URL, INDEX_TTL);
  const a = findArticle(art, args);
  if (!a) return { error: '未找到文章：请先 list_articles / search_articles 取得 url 再试（也支持 _posts 文件名作为 slug，如 2026-09-18-ai-duan-pian-da-sai-xian.md）' };
  const markdown = await getText(ctx, a.raw_md, RAW_TTL);
  return { title: a.title, date: a.date, url: a.url, categories: a.categories || [], tags: a.tags || [], cover: a.cover, source: 'markdown 源文件（发布日期以正文「文 / 书航」标注为准）', markdown };
}

async function toolListDailyIssues(ctx, args) {
  const iss = await getJSON(ctx, ISSUES_URL, INDEX_TTL);
  let list = iss.issues;
  if (args.year) { const y = String(args.year); list = list.filter(x => x.date.slice(0, 4) === y); }
  if (args.date_from) { const f = normDate(args.date_from); if (f) list = list.filter(x => x.date >= f); }
  if (args.date_to) { const t = normDate(args.date_to); if (t) list = list.filter(x => x.date <= t); }
  const p = paginate(list, args);
  return { total: p.total, page: p.page, page_size: p.page_size, pages: p.pages, issues: p.items.map(articleBrief) };
}

async function toolGetDailyIssue(ctx, args) {
  const iss = await getJSON(ctx, ISSUES_URL, INDEX_TTL);
  const d = normDate(args.date);
  if (!d) return { error: 'date 参数缺失或无法解析（支持 2026-09-28 / 2026.9.28 等写法）' };
  const a = iss.issues.find(x => x.date === d);
  if (!a) return { error: '该日期无早报（索引范围 ' + iss.issues[iss.issues.length - 1].date + ' ~ ' + iss.issues[0].date + '）' };
  const markdown = await getText(ctx, a.raw_md, RAW_TTL);
  return { title: a.title, date: a.date, url: a.url, cover: a.cover, source: 'markdown 源文件（同日重发不覆盖，以每日首次同步版本为准）', markdown };
}

/* ---------------- 工具清单 ---------------- */

const TOOLS = [
  {
    name: 'site_overview',
    description: '航通社（lishuhang.me，书航的博客）站点概览：文章与早报总数、最新内容、全部 agent 入口。首次接触本站时调用。',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'list_articles',
    description: '分页浏览航通社全站文章（按发布时间倒序）。支持按分类、标签、年份、关键词过滤。不返回正文。',
    inputSchema: {
      type: 'object',
      properties: {
        page: { type: 'number', description: '页码，默认 1' },
        page_size: { type: 'number', description: '每页条数，默认 20，最大 100' },
        category: { type: 'string', description: '按分类过滤，如 AI、科技、传媒' },
        tag: { type: 'string', description: '按标签过滤，如 featured' },
        year: { type: 'string', description: '按年份过滤，如 2026' },
        q: { type: 'string', description: '标题/摘要包含的关键词（粗过滤）' },
      },
    },
  },
  {
    name: 'search_articles',
    description: '关键词搜索航通社全站文章（标题加权、标签/分类次之、摘要兜底），返回命中列表与评分。',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: '关键词，可空格分隔多词' },
        limit: { type: 'number', description: '返回条数上限，默认 10，最大 30' },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_article',
    description: '取航通社单篇文章全文 markdown（含 front matter、正文与发布日期标注）。',
    inputSchema: {
      type: 'object',
      properties: {
        url: { type: 'string', description: '文章页 URL（list_articles/search_articles 结果中的 url）' },
        slug: { type: 'string', description: '或直接给 _posts 文件名（如 2026-09-18-ai-duan-pian-da-sai-xian.md）' },
      },
    },
  },
  {
    name: 'list_daily_issues',
    description: '分页浏览「每日 AIGC 早报」期号（按日期倒序）。支持按年份与日期区间过滤。',
    inputSchema: {
      type: 'object',
      properties: {
        page: { type: 'number', description: '页码，默认 1' },
        page_size: { type: 'number', description: '每页条数，默认 20，最大 100' },
        year: { type: 'string', description: '按年份过滤，如 2026' },
        date_from: { type: 'string', description: '起始日期 2026-09-01' },
        date_to: { type: 'string', description: '截止日期 2026-09-28' },
      },
    },
  },
  {
    name: 'get_daily_issue',
    description: '取「每日 AIGC 早报」单期全文 markdown（同日重发不覆盖，以每日首次同步版本为准）。',
    inputSchema: {
      type: 'object',
      properties: {
        date: { type: 'string', description: '日期，支持 2026-09-28 / 2026.9.28 等写法' },
      },
      required: ['date'],
    },
  },
];

const TOOL_IMPL = {
  site_overview: (ctx, args) => toolSiteOverview(ctx),
  list_articles: toolListArticles,
  search_articles: toolSearchArticles,
  get_article: toolGetArticle,
  list_daily_issues: toolListDailyIssues,
  get_daily_issue: toolGetDailyIssue,
};

/* ---------------- JSON-RPC / HTTP 层 ---------------- */

function rpc(id, result) { return { jsonrpc: '2.0', id, result }; }
function rpcErr(id, code, message, data) {
  return { jsonrpc: '2.0', id, error: { code, message, ...(data ? { data } : {}) } };
}

async function handleRpc(ctx, msg) {
  const { id, method, params } = msg || {};
  const isNotification = id === undefined || id === null;
  try {
    switch (method) {
      case 'initialize':
        return rpc(id, {
          protocolVersion: (params && SUPPORTED.includes(params.protocolVersion)) ? params.protocolVersion : '2025-06-18',
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: 'lishuhang-site-mcp', title: '航通社官网 MCP', version: VERSION },
          instructions: '航通社（书航博客 lishuhang.me + 每日 AIGC 早报）只读检索服务。先 site_overview 概览，list/search 找文章，get_article / get_daily_issue 取全文。',
        });
      case 'notifications/initialized':
        return null; // 通知无需响应
      case 'ping':
        return rpc(id, {});
      case 'tools/list':
        return rpc(id, { tools: TOOLS });
      case 'tools/call': {
        const name = params && params.name;
        const impl = TOOL_IMPL[name];
        if (!impl) return rpcErr(id, -32602, '未知工具: ' + name);
        const result = await impl(ctx, (params && params.arguments) || {});
        const isError = result && result.error !== undefined;
        return rpc(id, {
          content: [{ type: 'text', text: isError ? JSON.stringify(result) : toText(name, result) }],
          ...(isError ? { isError: true } : {}),
        });
      }
      default:
        if (isNotification) return null;
        return rpcErr(id, -32601, '方法不存在: ' + method);
    }
  } catch (e) {
    if (isNotification) return null;
    return rpcErr(id, -32603, '内部错误: ' + (e && e.message));
  }
}

function toText(tool, result) {
  if (tool === 'get_article' || tool === 'get_daily_issue') {
    return '# ' + result.title + '\n\n> 来源: ' + result.url + ' | 发布: ' + result.date + '\n> ' + result.source + '\n\n' + result.markdown;
  }
  return JSON.stringify(result, null, 1);
}

function jsonResponse(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'content-type': 'application/json; charset=utf-8', ...CORS },
  });
}

function infoPage() {
  return jsonResponse({
    server: 'lishuhang-site-mcp', version: VERSION,
    transport: 'Streamable HTTP (stateless, POST JSON-RPC)',
    endpoint: '/mcp',
    tools: TOOLS.map(t => t.name),
    upstream: { articles: ARTICLES_URL, daily_issues: ISSUES_URL },
    docs: 'https://lishuhang.me/llms.txt',
  });
}

const SUPPORTED = ['2025-06-18', '2025-03-26', '2024-11-05'];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
    if (url.pathname === '/health') return new Response('ok', { headers: { 'content-type': 'text/plain', ...CORS } });
    if (url.pathname === '/' && request.method === 'GET') return infoPage();
    if (url.pathname === '/mcp' || url.pathname === '/mcp/') {
      if (request.method === 'GET') {
        return jsonResponse({ jsonrpc: '2.0', id: null, error: { code: -32000, message: '本服务为无状态 Streamable HTTP：请用 POST 发送 JSON-RPC；不支持 SSE 长连接' } }, 405);
      }
      if (request.method !== 'POST') {
        return jsonResponse({ jsonrpc: '2.0', id: null, error: { code: -32000, message: 'Method Not Allowed' } }, 405);
      }
      let body;
      try { body = await request.json(); } catch (e) {
        return jsonResponse(rpcErr(null, -32700, 'JSON 解析失败'), 400);
      }
      const batch = Array.isArray(body) ? body : [body];
      const out = [];
      for (const msg of batch) {
        const r = await handleRpc(ctx, msg);
        if (r !== null) out.push(r);
      }
      if (out.length === 0) return new Response(null, { status: 202, headers: CORS });
      return jsonResponse(Array.isArray(body) ? out : out[0]);
    }
    return jsonResponse({ error: 'not found', hint: 'MCP endpoint: POST /mcp' }, 404);
  },
};
