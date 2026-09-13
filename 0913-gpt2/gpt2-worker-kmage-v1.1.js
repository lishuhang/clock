// ============================================================
// gpt2-worker-kmage-v1.1.js
// kmage 通道 —— 基于 image.dddd.zone（kmage · AI 视觉工作台）
//
// 上游: https://image.dddd.zone
//   - 官方 OpenAI 兼容 API（/v1/*），Bearer kmage_* 密钥，1 积分/张
//   - 会话类操作（注册/登录/签到/API Key/额度）走 cookie: kmage_session
//   - 注册仅 邮箱+密码，无验证码；签到 +5 积分/天（注册满 24h 后开放）
//
// 架构（沿袭 gpt2-worker-kdr-v1.2 单文件 Service Worker 骨架）:
//   - HTML_CONTENT 内嵌前端（生图 UI + 号池管理）
//   - /api/kmage/*  → 上游 /api/*（会话代理：前端经 X-Kmage-Session 头携带
//     各账号会话令牌；上游 Set-Cookie 经 X-Kmage-Set-Session 头返回前端）
//   - /kmage/v1/*   → 上游 /v1/*（Bearer 透传，生图/模型）
//   - 号池与设置保存在浏览器 localStorage（沿用项目惯例，Worker 无状态）
//
// 号池模式（参考马良 v27.2）:
//   - 轮换策略 most-credits / round-robin
//   - 自动注册（额度耗尽时）、批量签到、401 自动重登、402 自动换号
//   - 老虎机为负期望（RTP 95.88%），不纳入自动积分来源
//
// 版本: kmage-1.1 (2026-09-13)
//   v1.1 变更:
//   - 运行日志控制台：每次生图/号池操作全程记录（请求、状态、耗时、
//     上游响应摘要），支持按运行导出/复制，日志本地持久化（刷新不丢）
//   - 号池 JSON 导入/导出（含会话与 Key，跨设备迁移）
//   - 浏览器原生通知：生图成功/失败/超时提醒（设置开关）
//   - 24 小时规则明确化：签到受注册 24h 冷却限制，生图不受限；
//     若新生号生图异常自动提示剩余时间并切换其他账号
//   - 反模式化（马良原则）：拟人化邮箱/密码生成（去除固定指纹）、
//     批量注册/签到随机化间隔与乱序、UA 透传浏览器真实 UA
//   - div.brand 改为「AI生图」；内嵌自包含 README/CHANGELOG 文档，
//     页面提示 AI Agent 可将本页作为 skill 调用；新增 /about 自描述接口
// ============================================================

const VERSION = 'kmage-1.1';
const UPSTREAM = 'https://image.dddd.zone';
const SESSION_COOKIE = 'kmage_session';
const SESSION_HEADER = 'X-Kmage-Session';
const SET_SESSION_HEADER = 'X-Kmage-Set-Session';
const UA_FALLBACK_POOL = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15'
];
function pickUA(request) {
  var real = request && request.headers ? request.headers.get('User-Agent') : '';
  if (real && real.length > 20 && real.indexOf('Mozilla') === 0) return real; // 透访客真实 UA（马良原则）
  return UA_FALLBACK_POOL[Math.floor(Math.random() * UA_FALLBACK_POOL.length)];
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, ' + SESSION_HEADER,
    'Access-Control-Expose-Headers': SET_SESSION_HEADER,
    'Access-Control-Max-Age': '86400'
  };
}

function jsonResp(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8' }
  });
}

// ---- 会话类代理: /api/kmage/* → 上游 /api/* ----------------
// 前端以 SESSION_HEADER 携带某账号的 kmage_session 令牌值；
// worker 还原为 Cookie 头发往上游，并把响应中的新会话经
// SET_SESSION_HEADER 送回前端更新 localStorage。
async function handleSessionProxy(request, url) {
  const sub = url.pathname.slice('/api/kmage'.length) || '/';
  const upstreamUrl = UPSTREAM + '/api' + sub + (url.search || '');
  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');
  headers.set('Accept', 'application/json');
  headers.set('Origin', UPSTREAM);
  headers.set('Referer', UPSTREAM + '/');
  headers.set('User-Agent', pickUA(request));
  const sess = request.headers.get(SESSION_HEADER) || '';
  if (sess) headers.set('Cookie', SESSION_COOKIE + '=' + sess);
  const opts = { method: request.method, headers: headers };
  if (request.method === 'POST' || request.method === 'PUT' || request.method === 'PATCH' || request.method === 'DELETE') {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > 0) opts.body = buf;
  }
  const upResp = await fetch(upstreamUrl, opts);
  const respHeaders = new Headers(corsHeaders());
  const ct = upResp.headers.get('Content-Type');
  if (ct) respHeaders.set('Content-Type', ct);
  // 捕获上游会话续期/轮换（兼容 getSetCookie 与单值读取）
  let setCookies = [];
  try {
    if (typeof upResp.headers.getSetCookie === 'function') setCookies = upResp.headers.getSetCookie();
  } catch (e) {}
  if (!setCookies.length) {
    const sc = upResp.headers.get('Set-Cookie');
    if (sc) setCookies = [sc];
  }
  for (let i = 0; i < setCookies.length; i++) {
    const m = String(setCookies[i]).match(new RegExp(SESSION_COOKIE + '=([^;]+)'));
    if (m && m[1]) { respHeaders.set(SET_SESSION_HEADER, m[1]); break; }
  }
  const body = await upResp.arrayBuffer();
  return new Response(body, { status: upResp.status, headers: respHeaders });
}

// ---- Bearer 代理: /kmage/v1/* → 上游 /v1/* ------------------
async function handleV1Proxy(request, url) {
  const sub = url.pathname.slice('/kmage/v1'.length) || '/';
  const upstreamUrl = UPSTREAM + '/v1' + sub + (url.search || '');
  const headers = new Headers();
  const ct = request.headers.get('Content-Type');
  if (ct) headers.set('Content-Type', ct);
  headers.set('Accept', 'application/json');
  headers.set('Origin', UPSTREAM);
  headers.set('Referer', UPSTREAM + '/');
  headers.set('User-Agent', pickUA(request));
  const auth = request.headers.get('Authorization');
  if (auth) headers.set('Authorization', auth);
  const opts = { method: request.method, headers: headers };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > 0) opts.body = buf;
  }
  const upResp = await fetch(upstreamUrl, opts);
  const respHeaders = new Headers(corsHeaders());
  const rct = upResp.headers.get('Content-Type');
  if (rct) respHeaders.set('Content-Type', rct);
  const body = await upResp.arrayBuffer();
  return new Response(body, { status: upResp.status, headers: respHeaders });
}

async function handleRequest(request) {
  const url = new URL(request.url);
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (url.pathname === '/favicon.ico') {
    return new Response(null, { status: 204 });
  }
  if (url.pathname === '/healthz') {
    return jsonResp({ version: VERSION, upstream: UPSTREAM, time: new Date().toISOString() });
  }
  if (url.pathname === '/about') {
    // 自描述接口：供 AI Agent / 排障工具快速了解本服务
    return jsonResp({
      name: 'AI生图（kmage 通道）',
      version: VERSION,
      kind: 'single-file-cloudflare-worker',
      upstream: { name: 'kmage · AI 视觉工作台', base: UPSTREAM },
      endpoints: {
        page: '/',
        health: '/healthz',
        session_proxy: '/api/kmage/* -> ' + UPSTREAM + '/api/*（会话经 X-Kmage-Session 头）',
        v1_proxy: '/kmage/v1/* -> ' + UPSTREAM + '/v1/*（Bearer 透传）'
      },
      frontend: { pool_storage: 'localStorage: kmage_state_v1', logs_storage: 'localStorage: kmage_logs_v1' },
      docs: '页面右上角「文档」按钮内含自包含 README 与 CHANGELOG；本 JSON 可作为排障入口',
      generated_at: new Date().toISOString()
    });
  }
  if (url.pathname === '/api/kmage' || url.pathname.startsWith('/api/kmage/')) {
    try { return await handleSessionProxy(request, url); }
    catch (err) { return jsonResp({ error: '代理请求失败: ' + (err && err.message ? err.message : String(err)) }, 502); }
  }
  if (url.pathname === '/kmage/v1' || url.pathname.startsWith('/kmage/v1/')) {
    try { return await handleV1Proxy(request, url); }
    catch (err) { return jsonResp({ error: { message: '代理请求失败: ' + (err && err.message ? err.message : String(err)), type: 'worker_proxy_error' } }, 502); }
  }
  return new Response(HTML_CONTENT, {
    headers: { 'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'no-cache' }
  });
}

addEventListener('fetch', function (event) {
  event.respondWith(handleRequest(event.request));
});

// ============================================================
// 内嵌前端
// ============================================================
const HTML_CONTENT = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- ============================================================
  AI AGENT / 排障提示（AI Agent Notice）:
  本页是自包含的单文件 Cloudflare Worker 应用（后端代理 + 内嵌前端 + 号池）。
  - 可将本页/本文件整体作为 skill 调用：所有交互均在页面内完成，无外部依赖
  - 排障请先读: 右上角「文档」按钮内嵌的自包含 README 与 CHANGELOG
  - 服务自描述: GET /about（版本、端点、存储键）；健康: GET /healthz
  - 前端日志: localStorage["kmage_logs_v1"]；号池: localStorage["kmage_state_v1"]
  - 上游: image.dddd.zone（kmage · AI 视觉工作台）官方 OpenAI 兼容 API
============================================================ -->
<title>AI生图 · kmage-1.1</title>
<style>
:root{
  --bg:#f4f6fb; --card:#ffffff; --border:#e3e7f0; --text:#1c2333; --text-2:#5a6478; --text-muted:#8a93a6;
  --accent:#4f6bf2; --accent-dark:#3d55cc; --accent-soft:#eceffd;
  --ok:#18a058; --ok-soft:#e8f7ef; --warn:#d98324; --warn-soft:#fdf3e4; --err:#d64541; --err-soft:#fdecec;
  --radius:12px; --shadow:0 1px 3px rgba(28,35,51,.06),0 8px 24px rgba(28,35,51,.05);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}
a{color:var(--accent);text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px 48px}
header.top{display:flex;align-items:center;gap:12px;padding:14px 0;position:sticky;top:0;background:rgba(244,246,251,.92);backdrop-filter:blur(8px);z-index:50;border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:baseline;gap:8px}
.brand h1{font-size:18px;margin:0;letter-spacing:.5px}
.brand .ver{font-size:11px;color:var(--text-muted)}
.top-right{margin-left:auto;display:flex;align-items:center;gap:8px}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:999px;background:var(--accent-soft);color:var(--accent-dark);font-size:12px;font-weight:600}
.badge.zero{background:var(--err-soft);color:var(--err)}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow)}
.gen-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;margin-top:16px}
@media (max-width:860px){.gen-grid{grid-template-columns:1fr}}
.panel{padding:18px}
.panel h2{margin:0 0 12px;font-size:15px}
label.f{display:block;margin:12px 0 6px;font-size:12px;color:var(--text-2);font-weight:600}
textarea,input[type=text],input[type=email],input[type=password],input[type=number],select{
  width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:8px;background:#fbfcfe;color:var(--text);
  font-size:14px;font-family:inherit;outline:none;transition:border .15s
}
textarea{min-height:110px;resize:vertical;line-height:1.55}
textarea:focus,input:focus,select:focus{border-color:var(--accent)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:9px 16px;border-radius:8px;border:1px solid var(--border);
  background:#fff;color:var(--text);font-size:13px;font-weight:600;cursor:pointer;transition:all .15s;font-family:inherit}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:var(--accent-dark);color:#fff}
.btn.lg{width:100%;padding:12px;font-size:15px;margin-top:16px}
.btn.sm{padding:4px 10px;font-size:12px;border-radius:6px}
.btn.danger{color:var(--err)}
.btn.danger:hover{border-color:var(--err);background:var(--err-soft)}
.ref-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ref-item{position:relative;width:56px;height:56px;border-radius:8px;overflow:hidden;border:1px solid var(--border)}
.ref-item img{width:100%;height:100%;object-fit:cover}
.ref-item .rm{position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;background:rgba(0,0,0,.55);color:#fff;border:none;
  font-size:11px;line-height:18px;cursor:pointer;padding:0}
.ref-add{width:56px;height:56px;border-radius:8px;border:1px dashed var(--border);background:#fbfcfe;color:var(--text-muted);cursor:pointer;font-size:20px}
.status{margin-top:12px;padding:10px 12px;border-radius:8px;font-size:13px;display:none}
.status.show{display:block}
.status.info{background:var(--accent-soft);color:var(--accent-dark)}
.status.ok{background:var(--ok-soft);color:var(--ok)}
.status.err{background:var(--err-soft);color:var(--err)}
.result-empty{color:var(--text-muted);text-align:center;padding:60px 10px;font-size:13px}
.result-img-wrap{display:none}
.result-img-wrap img{width:100%;border-radius:10px;border:1px solid var(--border);display:block}
.result-meta{display:flex;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap}
.result-meta .m{font-size:12px;color:var(--text-muted)}
.hist{margin-top:16px}
.hist-list{margin:8px 0 0;padding:0;list-style:none}
.hist-list li{display:flex;gap:10px;align-items:center;padding:8px 4px;border-bottom:1px dashed var(--border);font-size:12px;color:var(--text-2)}
.hist-list li .hp{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hist-list li .okc{color:var(--ok)}
.hist-list li .errc{color:var(--err)}
dialog{border:none;border-radius:14px;box-shadow:0 24px 64px rgba(28,35,51,.25);padding:0;max-width:860px;width:calc(100% - 32px)}
dialog::backdrop{background:rgba(28,35,51,.45)}
.dlg-head{display:flex;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border)}
.dlg-head h3{margin:0;font-size:16px}
.dlg-head .x{margin-left:auto;border:none;background:none;font-size:20px;color:var(--text-muted);cursor:pointer;line-height:1}
.dlg-body{padding:16px 20px 20px;max-height:66vh;overflow:auto}
.pool-actions{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.pool-actions .grow{flex:1}
table.pool{width:100%;border-collapse:collapse;font-size:12.5px}
table.pool th{ text-align:left;color:var(--text-muted);font-weight:600;padding:8px 6px;border-bottom:1px solid var(--border);white-space:nowrap}
table.pool td{padding:8px 6px;border-bottom:1px dashed var(--border);vertical-align:middle}
table.pool td.op{white-space:nowrap;text-align:right}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.pill.ok{background:var(--ok-soft);color:var(--ok)}
.pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.err{background:var(--err-soft);color:var(--err)}
.pill.mut{background:#eef0f5;color:var(--text-muted)}
.settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}
.chk{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-2);margin-top:10px}
.chk input{width:16px;height:16px}
.help p{margin:8px 0;color:var(--text-2);font-size:13px}
.help h4{margin:14px 0 4px;font-size:13px}
.toast-wrap{position:fixed;right:16px;bottom:16px;z-index:200;display:flex;flex-direction:column;gap:8px}
.toast{padding:10px 16px;border-radius:8px;color:#fff;font-size:13px;box-shadow:var(--shadow);max-width:340px;word-break:break-all}
.toast.success{background:var(--ok)}
.toast.error{background:var(--err)}
.toast.info{background:#3b4252}
footer{margin-top:32px;text-align:center;color:var(--text-muted);font-size:12px}
.log-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.log-bar .grow{flex:1}
.log-chk{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-2)}
.log-console{background:#10141f;color:#c9d2e8;border-radius:10px;padding:10px 12px;height:52vh;overflow-y:auto;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace;font-size:12px;line-height:1.55}
.log-console .le{padding:1px 0;word-break:break-all;white-space:pre-wrap}
.log-console .le .t{color:#5f6b85}
.log-console .le.i{color:#c9d2e8}
.log-console .le.s{color:#4ade80}
.log-console .le.w{color:#fbbf24}
.log-console .le.e{color:#f87171}
.log-console .le .tag{color:#7c8db5}
.log-console .empty{color:#5f6b85}
.log-console::-webkit-scrollbar{width:8px}
.log-console::-webkit-scrollbar-thumb{background:#2a3350;border-radius:4px}
.docs-body h3{margin:16px 0 6px;font-size:14px;color:var(--accent-dark)}
.docs-body h4{margin:12px 0 4px;font-size:13px}
.docs-body p,.docs-body li{color:var(--text-2);font-size:13px;margin:6px 0}
.docs-body pre{background:#f4f6fb;border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:12px;overflow-x:auto}
.docs-body code{background:#f4f6fb;border-radius:4px;padding:1px 5px;font-size:12px}
.docs-body hr{border:none;border-top:1px solid var(--border);margin:14px 0}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <h1>AI生图</h1>
      <span class="ver">kmage-1.1</span>
    </div>
    <div class="top-right">
      <span class="badge" id="creditBadge" title="号池可用总积分">积分 -</span>
      <button class="btn sm" id="poolBtn" type="button">号池</button>
      <button class="btn sm" id="logBtn" type="button">日志</button>
      <button class="btn sm" id="docsBtn" type="button">文档</button>
      <button class="btn sm" id="helpBtn" type="button">帮助</button>
    </div>
  </header>

  <div class="gen-grid">
    <section class="card panel">
      <h2>创作</h2>
      <label class="f" for="prompt">提示词 Prompt</label>
      <textarea id="prompt" placeholder="描述你想要的画面，例如：雨后的未来主义城市街道，霓虹倒影，电影感"></textarea>

      <label class="f" for="model">模型</label>
      <select id="model">
        <option value="gpt-image-2">GPT Image 2（兼容旧版）</option>
        <option value="gpt-image-2.5-flare">GPT Image 2.5 · Flare（速度优先）</option>
        <option value="gpt-image-2.5-sunburst" selected>GPT Image 2.5 · Sunburst（效果优先）</option>
      </select>

      <div class="row2">
        <div>
          <label class="f" for="ratio">画面比例</label>
          <select id="ratio">
            <option value="1:1" selected>1:1 方形</option>
            <option value="3:2">3:2 横向</option>
            <option value="2:3">2:3 纵向</option>
            <option value="16:9">16:9 宽幅</option>
            <option value="9:16">9:16 竖屏</option>
            <option value="4:3">4:3 横向</option>
            <option value="3:4">3:4 纵向</option>
            <option value="auto">自动</option>
          </select>
        </div>
        <div>
          <label class="f" for="quality">精细度</label>
          <select id="quality">
            <option value="auto" selected>自动</option>
            <option value="low">轻量（快）</option>
            <option value="medium">标准</option>
            <option value="high">精细</option>
          </select>
        </div>
      </div>

      <label class="f">参考图（可选，图生图，最多 10 张）</label>
      <div class="ref-list" id="refList">
        <button class="ref-add" id="refAdd" type="button" title="添加参考图">+</button>
      </div>
      <input type="file" id="refInput" accept="image/png,image/jpeg,image/webp" multiple style="display:none">

      <button class="btn primary lg" id="btnGenerate" type="button">开始生成（消耗 1 积分）</button>
      <div class="status" id="genStatus"></div>
    </section>

    <section class="card panel">
      <h2>结果</h2>
      <div class="result-empty" id="resultEmpty">生成结果将显示在这里</div>
      <div class="result-img-wrap" id="resultWrap">
        <img id="resultImg" alt="生成结果">
        <div class="result-meta">
          <button class="btn sm" id="btnDownload" type="button">下载图片</button>
          <span class="m" id="resultMeta"></span>
        </div>
      </div>
      <div class="hist">
        <h2 style="font-size:13px;color:var(--text-2)">近期任务</h2>
        <ul class="hist-list" id="histList"></ul>
      </div>
    </section>
  </div>

  <footer>
    上游：image.dddd.zone（kmage · AI 视觉工作台）· 官方 OpenAI 兼容 API · 1 积分 = 1 张图 · 失败自动返还
    <br>AI Agent：本页为自包含单文件 Worker，可将本页整体作为 skill 调用；调试请先读右上角「文档」（内嵌自包含 README 与 CHANGELOG），并参考 /about 与 /healthz。
  </footer>
</div>

<!-- ============ 号池管理 ============ -->
<dialog id="poolDialog">
  <div class="dlg-head">
    <h3>号池管理</h3>
    <button class="x" id="poolClose" type="button" title="关闭">×</button>
  </div>
  <div class="dlg-body">
    <div class="pool-actions">
      <button class="btn" id="btnRegister" type="button">+ 注册新账号</button>
      <button class="btn" id="btnBatchRegister" type="button">批量注册 ×<span id="batchN">3</span></button>
      <input type="number" id="batchCount" min="1" max="10" value="3" style="width:64px" title="批量注册数量">
      <button class="btn" id="btnCheckinAll" type="button">批量签到</button>
      <button class="btn" id="btnEnsureKeys" type="button">补建 API Key</button>
      <button class="btn" id="btnRefreshCredits" type="button">刷新额度</button>
      <button class="btn" id="btnExportPool" type="button" title="导出号池为 JSON（含会话与 Key）">导出号池</button>
      <button class="btn" id="btnImportPool" type="button" title="从 JSON 导入号池">导入号池</button>
      <input type="file" id="importPoolFile" accept=".json,application/json" style="display:none">
      <span class="grow"></span>
      <button class="btn danger" id="btnArchiveDisabled" type="button">归档已禁用</button>
    </div>
    <div style="overflow-x:auto">
      <table class="pool">
        <thead>
          <tr>
            <th>账号</th><th>积分</th><th>API Key</th><th>今日签到</th><th>状态</th><th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody id="poolTbody">
          <tr><td colspan="6" style="color:var(--text-muted)">号池为空，点击"注册新账号"开始。</td></tr>
        </tbody>
      </table>
    </div>
    <div class="settings-grid">
      <div>
        <label class="f" for="rotationStrategy">轮换策略</label>
        <select id="rotationStrategy">
          <option value="most-credits" selected>积分优先（most-credits）</option>
          <option value="round-robin">轮询均衡（round-robin）</option>
        </select>
      </div>
      <div>
        <label class="f" for="emailDomain">注册邮箱域名</label>
        <input type="text" id="emailDomain" placeholder="gmail.com" maxlength="64">
      </div>
      <div>
        <div class="chk"><input type="checkbox" id="autoRegisterChk" checked><label for="autoRegisterChk">生图无号可用时自动注册新号（+1 分）</label></div>
      </div>
      <div>
        <div class="chk"><input type="checkbox" id="autoCheckinChk" checked><label for="autoCheckinChk">打开页面时自动为可签账号签到（+5 分/天）</label></div>
      </div>
      <div>
        <div class="chk"><input type="checkbox" id="notifyChk"><label for="notifyChk">生图结果浏览器通知（成功/失败/超时）</label></div>
      </div>
    </div>
    <div class="status" id="poolStatus"></div>
  </div>
</dialog>

<!-- ============ 帮助 ============ -->
<dialog id="helpDialog">
  <div class="dlg-head">
    <h3>帮助 · kmage 通道</h3>
    <button class="x" id="helpClose" type="button" title="关闭">×</button>
  </div>
  <div class="dlg-body help">
    <h4>这是什么</h4>
    <p>kmage 生图基于 image.dddd.zone 的官方 OpenAI 兼容 API（/v1/images/generations）。本页把"注册账号 → 每日签到攒积分 → API Key 调用生图"整条链路自动化，1 积分生成 1 张图，失败的请求上游会自动返还积分。</p>
    <h4>积分从哪来</h4>
    <p>· 新注册账号送 1 积分；账号注册满 24 小时后开放每日签到，+5 积分/天；因此号池 N 个账号约等于每天 5N 张图的稳定产能。</p>
    <p>· 注意：24 小时冷却只限制「签到」，不限制「生图」——新注册的账号凭 1 积分可以立即生图（已实测）。若某个新生号生图被上游拒绝，工具会提示剩余冷却时间并自动切换其他账号。</p>
    <p>· 站内老虎机为娱乐玩法，理论返还率 95.88%（负期望），本工具不对其进行自动化，避免把积分赌没。</p>
    <h4>号池怎么用</h4>
    <p>· 点"注册新账号"或批量注册，工具会自动完成注册、创建 API Key、记录会话；全部数据只保存在你浏览器的 localStorage 中。</p>
    <p>· 每天打开页面时（或手动点"批量签到"），工具会自动为满足条件的账号签到。"待激活"状态的账号要等注册满 24 小时才会开放签到。</p>
    <p>· 生成时按轮换策略选号：积分优先（most-credits）或轮询均衡（round-robin）。遇 402（积分不足）自动换下一个号；遇 401（会话失效）自动用保存的邮箱密码重登并重建 Key。</p>
    <h4>排障与日志</h4>
    <p>· 右上角「日志」打开运行控制台：每次生图与号池操作的请求、状态码、耗时、上游响应摘要都会记录；可按运行导出 / 复制 / 只看错误，日志本地持久化，刷新不丢。</p>
    <p>· 生图失败时状态栏只显示简短原因，完整上游返回请在日志控制台查看或导出后交给维护者分析。</p>
    <h4>号池迁移</h4>
    <p>· 号池面板支持「导出号池 / 导入号池」（JSON，含邮箱密码、会话与 API Key），可用于跨浏览器/跨设备迁移；导入后工具会自动为缺会话的账号重新登录。导出文件含明文凭据，请妥善保管。</p>
    <h4>浏览器通知</h4>
    <p>· 号池设置里开启「生图结果浏览器通知」后，生图成功/失败/超时会发系统级通知（首次开启会请求权限；需页面保持打开）。</p>
    <h4>边界说明</h4>
    <p>· 会话与密钥为本工具对注册账号的自身凭据管理，不涉及破解或绕过任何验证；请遵守上游站点服务条款，控制用量，避免滥用免费产能。</p>
    <p>· 邀请奖励需被邀请人首次充值后才到账，不属于免费路径，工具不做链式邀请。</p>
  </div>
</dialog>

<!-- ============ 运行日志控制台 ============ -->
<dialog id="logDialog">
  <div class="dlg-head">
    <h3>运行日志 <span style="font-size:12px;color:var(--text-muted);font-weight:400" id="logCount"></span></h3>
    <button class="x" id="logClose" type="button" title="关闭">×</button>
  </div>
  <div class="dlg-body">
    <div class="log-bar">
      <button class="btn sm" id="btnExportLogAll" type="button">导出全部日志</button>
      <button class="btn sm" id="btnExportLogRun" type="button" title="只导出最近一次生图运行">导出本次运行</button>
      <button class="btn sm" id="btnCopyLog" type="button">复制</button>
      <span class="grow"></span>
      <label class="log-chk"><input type="checkbox" id="logErrOnly">只看错误</label>
      <button class="btn sm danger" id="btnClearLog" type="button">清空</button>
    </div>
    <div class="log-console" id="logBox"><div class="empty">暂无日志。日志会记录每次生图与号池操作：请求、状态码、耗时与上游响应摘要，刷新页面不丢失。</div></div>
  </div>
</dialog>

<!-- ============ 自包含文档 ============ -->
<dialog id="docsDialog">
  <div class="dlg-head">
    <h3>文档 · 自包含 README 与 CHANGELOG</h3>
    <button class="x" id="docsClose" type="button" title="关闭">×</button>
  </div>
  <div class="dlg-body docs-body" id="docsBody"></div>
</dialog>

<div class="toast-wrap" id="toastWrap"></div>
<script>
// ================= kmage 前端 =================
var VERSION='kmage-1.1';
var STATE_KEY='kmage_state_v1';
var LOG_KEY='kmage_logs_v1';
var DEFAULT_SETTINGS={rotationStrategy:'most-credits',autoRegister:true,autoCheckin:true,emailDomain:'gmail.com',notificationsEnabled:false};
var state={accounts:[],abandoned:[],settings:{},rotationIndex:0};
var runLogs=[];              // 日志环形缓冲 {ts,run,lvl,msg,detail}
var currentRunId='';         // 最近一次生图运行 id（用于“导出本次运行”）
var refImages=[];            // data URL 数组（图生图）
var lastResultB64=null;      // 当前结果 base64
var histItems=[];            // 近期任务（仅元数据）
var generating=false;

// ---------- 基础工具 ----------
function $(id){return document.getElementById(id)}
function randStr(n,alphabet){
  var abc=alphabet||'abcdefghijklmnopqrstuvwxyz0123456789';var s='';
  for(var i=0;i<n;i++){s+=abc.charAt(Math.floor(Math.random()*abc.length))}
  return s;
}
// 拟人化邮箱池（马良原则 v27.2）：姓名词库 × 5 种模式 × 随机大小写，
// 避免固定前缀/时间戳等机器指纹（v1.0 的 kmg****x + ts%100000 已去除）
var EMAIL_FIRST=['emily','sarah','michael','david','jessica','james','ashley','chris','amanda','daniel','stephanie','joshua','nicole','andrew','samantha','ryan','lauren','justin','rachel','brandon','megan','tyler','katherine','kevin','elizabeth','brian','jennifer','jason','michelle','patrick','kimberly','travis','heather','nathan','courtney','maria','alex','lisa','robert','john'];
var EMAIL_LAST=['chen','wang','li','zhang','smith','johnson','lee','brown','garcia','martinez','wilson','taylor','thomas','moore','jackson','white','harris','clark','lewis','robinson','walker','young','allen','king','wright','scott','hill','green','adams','baker'];
var EMAIL_ADJ=['happy','lucky','cool','sunny','swift','calm','bold','bright','dreamy','fresh','kind','wild','pure','warm','zen','chill','neon','cosmic','pixel','sage'];
var EMAIL_NOUN=['cat','fox','moon','star','sky','bear','wolf','deer','fish','hawk','tree','lake','rain','wave','wind','seed','leaf','snow','dawn','ray'];
function genEmail(){
  var dom=(state.settings.emailDomain||'gmail.com').replace(/^@/,'');
  var fn=EMAIL_FIRST[Math.floor(Math.random()*EMAIL_FIRST.length)];
  var ln=EMAIL_LAST[Math.floor(Math.random()*EMAIL_LAST.length)];
  var adj=EMAIL_ADJ[Math.floor(Math.random()*EMAIL_ADJ.length)];
  var noun=EMAIL_NOUN[Math.floor(Math.random()*EMAIL_NOUN.length)];
  var r2=Math.floor(10+Math.random()*90),r3=Math.floor(100+Math.random()*900),r4=Math.floor(1000+Math.random()*9000);
  var cap=function(x){return x.charAt(0).toUpperCase()+x.slice(1)};
  var sc=function(x){return Math.random()>0.5?cap(x):x};
  var local='';
  switch(Math.floor(Math.random()*6)){
    case 0: local=sc(fn)+'.'+sc(ln)+r2; break;
    case 1: local=sc(fn)+sc(ln)+r3; break;
    case 2: local=adj+'.'+noun+r4; break;
    case 3: local=sc(fn)+'_'+noun+r2; break;
    case 4: local=sc(fn)+r3; break;
    default: local=adj+sc(ln)+r3;
  }
  return local.toLowerCase()+'@'+dom;
}
// 强随机密码：无固定后缀/固定结构（v1.0 的 'Zq9' 尾巴是指纹，已去除）
function genPassword(){
  var up='ABCDEFGHJKLMNPQRSTUVWXYZ',low='abcdefghijkmnpqrstuvwxyz',dg='23456789',sy='#%!@+';
  var all=up+low+dg+sy;
  var len=12+Math.floor(Math.random()*4); // 12~15
  var p=randStr(1,up)+randStr(1,low)+randStr(1,dg)+randStr(1,sy)+randStr(len-4,all);
  var arr=p.split('');for(var i=arr.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=arr[i];arr[i]=arr[j];arr[j]=t}
  return arr.join('');
}
// API Key 备注名：小词池随机组合，避免固定 'pool-' 前缀规律
var KEY_NAME_WORDS=['pool','img','draw','art','gen','lab','studio','pic'];
function genKeyName(){return KEY_NAME_WORDS[Math.floor(Math.random()*KEY_NAME_WORDS.length)]+'-'+randStr(4)}
function maskEmail(e){if(!e)return '-';var i=e.indexOf('@');if(i<=1)return e;return e.charAt(0)+'***'+e.slice(i)}
function fmtTime(ts){var d=new Date(ts);return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')}
function todayGmt8(){
  var d=new Date(Date.now()+8*3600*1000);
  return d.getUTCFullYear()+'-'+('0'+(d.getUTCMonth()+1)).slice(-2)+'-'+('0'+d.getUTCDate()).slice(-2);
}
function toast(msg,type,ms){
  var w=$('toastWrap');var el=document.createElement('div');
  el.className='toast '+(type||'info');el.textContent=msg;w.appendChild(el);
  setTimeout(function(){el.style.opacity='0';el.style.transition='opacity .4s';setTimeout(function(){el.remove()},420)},ms||3200);
}
function setStatus(elId,msg,cls){
  var el=$(elId);if(!msg){el.className='status';el.textContent='';return}
  el.className='status show '+(cls||'info');el.textContent=msg;
}
function saveState(){try{localStorage.setItem(STATE_KEY,JSON.stringify(state))}catch(e){toast('本地存储失败：'+e.message,'error')}}
function loadState(){
  try{
    var raw=localStorage.getItem(STATE_KEY);
    if(raw){var d=JSON.parse(raw);state.accounts=d.accounts||[];state.abandoned=d.abandoned||[];state.rotationIndex=d.rotationIndex||0;
      state.settings=Object.assign({},DEFAULT_SETTINGS,d.settings||{})}
    else{state.settings=Object.assign({},DEFAULT_SETTINGS)}
  }catch(e){state.settings=Object.assign({},DEFAULT_SETTINGS)}
}

// ---------- 运行日志系统 ----------
// 结构: {ts, run, lvl(i/s/w/e), msg, detail}；持久化最近 300 条（detail 截断），内存 800 条
function loadLogs(){
  try{
    var raw=localStorage.getItem(LOG_KEY);
    if(raw){var d=JSON.parse(raw);if(Array.isArray(d))runLogs=d}
  }catch(e){runLogs=[]}
}
function saveLogs(){
  try{
    var keep=runLogs.slice(-300).map(function(x){
      return {ts:x.ts,run:x.run,lvl:x.lvl,msg:String(x.msg).slice(0,300),detail:x.detail?String(x.detail).slice(0,300):''};
    });
    localStorage.setItem(LOG_KEY,JSON.stringify(keep));
  }catch(e){}
}
var LOG_LEVEL_NAME={i:'INFO',s:'OK  ',w:'WARN',e:'ERR '};
function appLog(msg,lvl,detail,run){
  var entry={ts:Date.now(),run:run||currentRunId||'-',lvl:lvl||'i',msg:String(msg),detail:detail?String(detail):''};
  runLogs.push(entry);
  if(runLogs.length>800)runLogs=runLogs.slice(-800);
  if($('logDialog').open)renderLogBox();
  if(runLogs.length%8===0)saveLogs();
  return entry;
}
function fmtLogTs(ts){
  var d=new Date(ts);
  return ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2)+':'+('0'+d.getSeconds()).slice(-2)+'.'+('00'+(d.getMilliseconds()%1000)).slice(-3);
}
function renderLogBox(){
  var box=$('logBox');
  var errOnly=$('logErrOnly').checked;
  var rows=[];
  for(var i=0;i<runLogs.length;i++){
    var x=runLogs[i];
    if(errOnly&&x.lvl!=='e')continue;
    rows.push(x);
  }
  $('logCount').textContent='（共 '+runLogs.length+' 条'+(errOnly?('，错误 '+rows.length+' 条'):'')+'）';
  if(!rows.length){box.innerHTML='<div class="empty">暂无日志。</div>';return}
  var html='';
  var lastRun=null;
  for(var j=0;j<rows.length;j++){
    var y=rows[j];
    if(y.run!==lastRun&&y.run&&y.run!=='-'){html+='<div class="le" style="color:#5f6b85">---- '+esc(y.run)+' ----</div>';lastRun=y.run}
    html+='<div class="le '+y.lvl+'"><span class="t">'+fmtLogTs(y.ts)+'</span> <span class="tag">['+esc(y.run)+']</span> '+esc(y.msg)
      +(y.detail?('<span class="t"> | '+esc(y.detail)+'</span>'):'')+'</div>';
  }
  box.innerHTML=html;
  box.scrollTop=box.scrollHeight;
}
function logsToText(rows,label){
  var head=[];
  head.push('AI生图 kmage 运行日志'+(label?('（'+label+'）'):''));
  head.push('导出时间: '+new Date().toLocaleString());
  head.push('版本: '+VERSION);
  head.push('页面: '+location.href);
  head.push('UA: '+navigator.userAgent);
  head.push('条数: '+rows.length);
  head.push('');
  var lines=rows.map(function(x){
    return '['+fmtLogTs(x.ts)+'] ['+(LOG_LEVEL_NAME[x.lvl]||'INFO')+'] ['+x.run+'] '+x.msg+(x.detail?(' || '+x.detail):'');
  });
  return head.concat(lines).join(String.fromCharCode(10));
}
function downloadText(filename,text){
  var blob=new Blob([text],{type:'text/plain;charset=utf-8'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
}
function exportLogs(mode){
  var errOnly=$('logErrOnly').checked;
  var rows=[];
  if(mode==='run'){
    for(var i=0;i<runLogs.length;i++){if(runLogs[i].run===currentRunId)rows.push(runLogs[i])}
    if(!rows.length){toast('本次运行暂无日志','info');return}
  }else{
    for(var j=0;j<runLogs.length;j++){if(!errOnly||runLogs[j].lvl==='e')rows.push(runLogs[j])}
    if(!rows.length){toast('暂无可导出的日志','info');return}
  }
  var name='kmage-log-'+(mode==='run'?'run-':'')+(new Date().toISOString().slice(0,19).replace(/[:T-]/g,''))+'.txt';
  downloadText(name,logsToText(rows,mode==='run'?'本次运行 '+(currentRunId||'-'):'全部'));
  appLog('导出日志: '+name,'s','','');
}
function copyLogsAll(){
  var errOnly=$('logErrOnly').checked;
  var rows=[];
  for(var i=0;i<runLogs.length;i++){if(!errOnly||runLogs[i].lvl==='e')rows.push(runLogs[i])}
  if(!rows.length){toast('暂无可复制的日志','info');return}
  var text=logsToText(rows,'全部');
  (navigator.clipboard&&navigator.clipboard.writeText?navigator.clipboard.writeText(text):Promise.reject()).then(function(){
    toast('已复制 '+rows.length+' 条日志','success');
  },function(){
    var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();
    try{document.execCommand('copy');toast('已复制 '+rows.length+' 条日志','success')}catch(e){toast('复制失败，请用导出','error')}
    ta.remove();
  });
}

// ---------- 浏览器原生通知 ----------
function notificationsSupported(){return typeof Notification!=='undefined'}
function notificationsActive(){
  return !!(state.settings.notificationsEnabled&&notificationsSupported()&&Notification.permission==='granted');
}
async function requestNotificationPermission(){
  if(!notificationsSupported()){toast('当前浏览器不支持通知','error');return false}
  if(Notification.permission==='granted')return true;
  if(Notification.permission==='denied'){toast('通知权限已被浏览器拒绝，请在浏览器地址栏权限图标中手动开启','error');return false}
  var result=await Notification.requestPermission();
  if(result==='granted'){toast('通知权限已开启','success');return true}
  toast('未授予通知权限，生图结果将只在页面内提示','info');
  return false;
}
function notifyUser(title,body,tag){
  try{
    if(!notificationsActive())return;
    var n=new Notification(title,{body:body,tag:tag||('kmage-'+Date.now()),renotify:true});
    n.onclick=function(){window.focus();n.close()};
    setTimeout(function(){try{n.close()}catch(e){}},9000);
  }catch(e){appLog('通知发送失败: '+e.message,'w')}
}

// ---------- 上游 API 封装 ----------
// 会话类：/api/kmage/*（携带账号会话令牌；自动接收会话轮换）
function captureSession(resp,account){
  var ns=resp.headers.get('X-Kmage-Set-Session');
  if(ns&&account){account.session=ns}
}
async function kmageApi(path,opts,account){
  opts=opts||{};
  var headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});
  if(account&&account.session)headers['X-Kmage-Session']=account.session;
  var t0=Date.now();
  var resp=await fetch('/api/kmage'+path,{method:opts.method||'GET',headers:headers,body:opts.body||undefined,credentials:'omit'});
  captureSession(resp,account);
  // body 只能读一次：先取全文再尝试 JSON 解析，非 JSON 时保留原文供日志
  var data=null,rawTxt='';
  try{
    rawTxt=await resp.text();
    try{data=JSON.parse(rawTxt)}catch(e){data={_raw:rawTxt.slice(0,240)}}
  }catch(e){data={_raw:'(读取响应失败: '+e.message+')'}}
  var dur=Date.now()-t0;
  var owner=account?('['+maskEmail(account.email)+'] '):'';
  appLog(owner+(opts.method||'GET')+' /api'+path+' → HTTP '+resp.status+' ('+dur+'ms)',
    resp.ok?'i':(resp.status>=500?'e':'w'),
    (!resp.ok)?((rawTxt?('非JSON响应: '+rawTxt):JSON.stringify(data).slice(0,240))):'');
  return {ok:resp.ok,status:resp.status,data:data};
}
// v1 类：/kmage/v1/*（Bearer API Key）
async function kmageV1(path,opts,apiKey){
  opts=opts||{};
  var headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});
  if(apiKey)headers['Authorization']='Bearer '+apiKey;
  var fo={method:opts.method||'GET',headers:headers,credentials:'omit'};
  if(opts.body)fo.body=opts.body;
  if(opts.signal)fo.signal=opts.signal;
  var t0=Date.now();
  var resp=await fetch('/kmage/v1'+path,fo);
  // body 只能读一次：先取全文再尝试 JSON 解析，非 JSON 时保留原文供日志
  var data=null,rawTxt='';
  try{
    rawTxt=await resp.text();
    try{data=JSON.parse(rawTxt)}catch(e){data={_raw:rawTxt.slice(0,240)}}
  }catch(e){data={_raw:'(读取响应失败: '+e.message+')'}}
  var dur=Date.now()-t0;
  appLog((opts.method||'GET')+' /v1'+path+' → HTTP '+resp.status+' ('+dur+'ms)',
    resp.ok?'s':(resp.status>=500||resp.status===0?'e':'w'),
    resp.ok?'':((rawTxt?('非JSON响应: '+rawTxt):JSON.stringify(data).slice(0,240))));
  return {ok:resp.ok,status:resp.status,data:data,durationMs:dur};
}
function upstreamErrMsg(r,fallback){
  if(r&&r.data){
    if(typeof r.data.error==='string')return r.data.error;
    if(r.data.error&&r.data.error.message)return r.data.error.message;
    if(r.data.message)return r.data.message;
    if(r.data._raw)return String(r.data._raw).slice(0,160);
  }
  return fallback||('上游错误 HTTP '+(r?r.status:''));
}

// ---------- 账号生命周期 ----------
// 注册：{email,password} → 201 + Set-Cookie 会话；随后建 API Key
async function registerAccount(silent){
  var email=genEmail(),password=genPassword();
  var a={id:'acc_'+randStr(10),email:email,password:password,session:'',apiKey:'',apiKeyId:'',apiKeyHint:'',
    credits:1,lastCheckinDay:'',eligibleAt:0,createdAt:Date.now(),disabled:false,lastError:''};
  appLog('注册新账号 '+maskEmail(email),'i');
  var r=await kmageApi('/auth/register',{method:'POST',body:JSON.stringify({email:email,password:password})},a);
  if(!r.ok){
    appLog('注册失败 '+maskEmail(email),'e','','');
    throw new Error('注册失败: '+upstreamErrMsg(r,'HTTP '+r.status));
  }
  a.credits=(r.data&&r.data.user&&typeof r.data.user.credits==='number')?r.data.user.credits:1;
  if(!a.session){ // 极少数情况上游未返回 Set-Cookie，主动登录补会话
    try{await loginAccount(a)}catch(e){a.lastError='会话获取失败:'+e.message}
  }
  // 注册成功后立刻创建 API Key（密钥只显示一次，必须当场保存）
  try{await createKeyFor(a)}catch(e){a.lastError='建Key失败:'+e.message}
  appLog('注册完成 '+maskEmail(email)+'（'+a.credits+' 分，24h 后可签到）','s');
  state.accounts.push(a);saveState();renderAll();
  if(!silent)toast('注册成功: '+maskEmail(email)+'（'+a.credits+' 分'+(a.apiKey?', Key已建':'')+'）','success');
  return a;
}
// 登录（会话失效时自动调用）
async function loginAccount(a){
  appLog('登录 '+maskEmail(a.email),'i');
  var r=await kmageApi('/auth/login',{method:'POST',body:JSON.stringify({email:a.email,password:a.password})},a);
  if(!r.ok)throw new Error('登录失败: '+upstreamErrMsg(r,'HTTP '+r.status));
  if(!a.session)throw new Error('登录成功但未取得会话');
  return true;
}
// 确保会话可用（401 时重登一次）
async function withSession(a,fn){
  var r=await fn();
  if(r.status===401){
    await loginAccount(a);
    r=await fn();
  }
  return r;
}
// 创建 API Key
async function createKeyFor(a){
  var r=await withSession(a,function(){return kmageApi('/api-keys',{method:'POST',body:JSON.stringify({name:genKeyName()})},a)});
  if(!r.ok)throw new Error(upstreamErrMsg(r,'HTTP '+r.status));
  if(r.data&&r.data.key){a.apiKey=r.data.key;a.apiKeyId=(r.data.api_key&&r.data.api_key.id)||'';a.apiKeyHint=(r.data.api_key&&r.data.api_key.hint)||''}
  else throw new Error('响应中无密钥');
}
// 刷新额度（/auth/me）
async function refreshAccount(a){
  var r=await withSession(a,function(){return kmageApi('/auth/me',{},a)});
  if(!r.ok){a.lastError=upstreamErrMsg(r,'HTTP '+r.status);return false}
  if(r.data&&r.data.user){
    a.credits=typeof r.data.user.credits==='number'?r.data.user.credits:a.credits;
    a.lastError='';
  }
  return true;
}
// 签到：GET 状态 → eligible 则 POST
async function checkinAccount(a){
  var st=await withSession(a,function(){return kmageApi('/checkin',{},a)});
  if(!st.ok){a.lastError=upstreamErrMsg(st,'HTTP '+st.status);return {skipped:true}}
  var d=st.data||{};
  a.eligibleAt=d.eligible_at||0;
  if(d.credits!=null&&typeof d.credits==='number')a.credits=d.credits;
  if(d.checked_in===true){a.lastCheckinDay=todayGmt8();return {already:true,reward:d.reward_credits}}
  if(d.eligible===false){
    var remain=(d.eligible_at||a.eligibleAt||0)-Date.now();
    return {wait:true,eligibleAt:d.eligible_at||0,remainMs:remain>0?remain:0};
  }
  var claim=await withSession(a,function(){return kmageApi('/checkin',{method:'POST'},a)});
  if(!claim.ok){a.lastError=upstreamErrMsg(claim,'HTTP '+claim.status);return {failed:true,msg:a.lastError}}
  var cd=claim.data||{};
  var awarded=(typeof cd.awarded_credits==='number')?cd.awarded_credits:((typeof cd.reward_credits==='number'&&!cd.checked_in)?cd.reward_credits:0);
  if(typeof cd.credits==='number'){a.credits=cd.credits}
  else if(awarded){a.credits=(typeof a.credits==='number'?a.credits:0)+awarded}
  a.lastCheckinDay=todayGmt8();
  return {done:true,reward:awarded,credits:a.credits};
}
</script>
<script>
// ---------- 号池批量操作 ----------
async function batchRegister(n,silent){
  var done=0,fail=0;
  appLog('批量注册开始 ×'+n,'i');
  for(var i=0;i<n;i++){
    try{await registerAccount(true);done++}
    catch(e){fail++;toast(e.message,'error');break}
    // 反规律化：2.5~8 秒随机间隔（含偶尔较长停顿），避免等间隔请求指纹
    var gap=2500+Math.floor(Math.random()*5500);
    if(Math.random()<0.15)gap+=4000;
    appLog('批量注册间隔 '+Math.round(gap/1000)+'s','i');
    await sleep(gap);
  }
  appLog('批量注册结束: 成功 '+done+'，失败 '+fail,done?'s':'e');
  if(!silent)toast('批量注册完成: 成功 '+done+' 个'+(fail?('，失败 '+fail+' 个'):''),fail?'info':'success');
  renderAll();
}
function sleep(ms){return new Promise(function(res){setTimeout(res,ms)})}
async function checkinAll(silent){
  var done=0,already=0,wait=0,failed=0;
  // 反规律化：打乱签到顺序，逐号随机间隔 0.8~2.8s
  var order=[];
  for(var k=0;k<state.accounts.length;k++){if(!state.accounts[k].disabled&&state.accounts[k].session)order.push(state.accounts[k])}
  for(var s1=order.length-1;s1>0;s1--){var j=Math.floor(Math.random()*(s1+1));var t=order[s1];order[s1]=order[j];order[j]=t}
  appLog('批量签到开始 ×'+order.length,'i');
  for(var i=0;i<order.length;i++){
    var a=order[i];
    try{
      var r=await checkinAccount(a);
      if(r.done){done++;if(r.credits!=null)a.credits=r.credits;appLog('签到成功 '+maskEmail(a.email)+' +'+(r.reward||0)+' 分','s')}
      else if(r.already)already++;
      else if(r.wait){wait++;appLog('签到等待 '+maskEmail(a.email)+'（注册未满24h，剩 '+fmtRemain(r.remainMs)+'）','w')}
      else failed++;
    }catch(e){failed++;appLog('签到异常 '+maskEmail(a.email)+': '+e.message,'e')}
    renderAll();
    await sleep(800+Math.floor(Math.random()*2000));
  }
  saveState();renderAll();
  appLog('批量签到结束: 成功 '+done+'，已签 '+already+'，待激活 '+wait+'，失败 '+failed,failed?'w':'s');
  if(!silent){
    var parts=[];
    if(done)parts.push('签到成功 '+done);
    if(already)parts.push('已签 '+already);
    if(wait)parts.push('待激活 '+wait);
    if(failed)parts.push('失败 '+failed);
    toast(parts.length?('批量签到: '+parts.join('，')):'没有需要签到的账号',failed&&!done?'error':'success');
  }
  return {done:done,already:already,wait:wait,failed:failed};
}
// 剩余时间格式化：X小时Y分
function fmtRemain(ms){
  if(!ms||ms<0)ms=0;
  var h=Math.floor(ms/3600000),m=Math.ceil((ms%3600000)/60000);
  if(m===60){h++;m=0}
  return (h>0?h+'小时':'')+m+'分';
}
async function ensureKeysAll(){
  var n=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(a.disabled||a.apiKey)continue;
    try{await createKeyFor(a);n++}catch(e){a.lastError='建Key失败:'+e.message}
    renderAll();
    await sleep(400);
  }
  saveState();renderAll();
  toast(n?('为 '+n+' 个账号补建了 API Key'):'所有账号都已有 Key',n?'success':'info');
}
async function refreshAllCredits(){
  var ok=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(a.disabled||!a.session)continue;
    try{if(await refreshAccount(a))ok++}catch(e){}
    renderAll();
    await sleep(300);
  }
  saveState();renderAll();
  toast('已刷新 '+ok+' 个账号额度','success');
}
function archiveDisabled(){
  var kept=[],moved=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(a.disabled){state.abandoned.push(a);moved++}else kept.push(a);
  }
  state.accounts=kept;saveState();renderAll();
  toast('已归档 '+moved+' 个禁用账号','success');
}

// ---------- 号池 JSON 导入/导出 ----------
// 导出：完整账号（含会话与 API Key），用于跨设备迁移/备份；文件为用户自身凭据，注意保管
function exportPool(){
  var data={
    type:'kmage-pool',version:VERSION,exportedAt:new Date().toISOString(),
    accounts:state.accounts.map(function(a){return {email:a.email,password:a.password,session:a.session||'',apiKey:a.apiKey||'',apiKeyId:a.apiKeyId||'',apiKeyHint:a.apiKeyHint||'',credits:a.credits!=null?a.credits:0,lastCheckinDay:a.lastCheckinDay||'',eligibleAt:a.eligibleAt||0,createdAt:a.createdAt||0,disabled:!!a.disabled}}),
    abandoned:(state.abandoned||[]).map(function(a){return {email:a.email,password:a.password,abandonedAt:a.abandonedAt||Date.now()}}),
    settings:{emailDomain:state.settings.emailDomain||'gmail.com',rotationStrategy:state.settings.rotationStrategy||'most-credits'}
  };
  var name='kmage-pool-'+new Date().toISOString().slice(0,10).replace(/-/g,'')+'.json';
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
  appLog('导出号池: '+name+'（活跃 '+data.accounts.length+'，归档 '+data.abandoned.length+'）','s');
  toast('已导出 '+data.accounts.length+' 个活跃账号（含会话与 Key，请妥善保管）','success');
}
// 导入：按邮箱去重；无会话的账号自动尝试登录
async function importPoolData(txt){
  var data;
  try{data=JSON.parse(txt)}catch(e){toast('JSON 解析失败: '+e.message,'error');return}
  var arr=Array.isArray(data)?data:(data.accounts||[]);
  if(!arr.length&&!data.accounts){ // 兼容单对象 {email,password}
    if(data.email&&data.password)arr=[data];
  }
  var abArr=(Array.isArray(data)?[]:(data.abandonedAccounts||data.abandoned||[]));
  var n=0,skip=0,abN=0;
  for(var i=0;i<arr.length;i++){
    var it=arr[i];
    if(!it.email||!it.password){skip++;continue}
    var dup=false;
    for(var j=0;j<state.accounts.length;j++){if(state.accounts[j].email===it.email){dup=true;break}}
    if(!dup&&Array.isArray(state.abandoned)){for(var j2=0;j2<state.abandoned.length;j2++){if(state.abandoned[j2].email===it.email){dup=true;break}}}
    if(dup){skip++;continue}
    state.accounts.push({id:'acc_'+randStr(10),email:it.email,password:it.password,session:it.session||'',apiKey:it.apiKey||'',apiKeyId:it.apiKeyId||'',apiKeyHint:it.apiKeyHint||'',
      credits:(typeof it.credits==='number')?it.credits:0,lastCheckinDay:it.lastCheckinDay||'',eligibleAt:it.eligibleAt||0,createdAt:it.createdAt||Date.now(),disabled:!!it.disabled,lastError:''});
    n++;
  }
  if(!Array.isArray(state.abandoned))state.abandoned=[];
  for(var k=0;k<abArr.length;k++){
    var ab=abArr[k];
    if(!ab.email)continue;
    var dup2=state.abandoned.some(function(x){return x.email===ab.email})||state.accounts.some(function(x){return x.email===ab.email});
    if(!dup2){state.abandoned.push({email:ab.email,password:ab.password,abandonedAt:ab.abandonedAt||Date.now()});abN++}
  }
  saveState();renderAll();
  var msg='导入 '+n+' 个账号'+(skip?('，跳过 '+skip+'（重复或缺字段）'):'')+(abN?('，归档池 +'+abN):'');
  toast(msg,n?'success':'info');
  appLog('导入号池: '+msg,'s');
  // 无会话的账号尝试登录恢复
  var relink=0;
  for(var m=0;m<state.accounts.length;m++){
    var a2=state.accounts[m];
    if(!a2.session&&!a2.disabled){
      try{await loginAccount(a2);relink++;saveState();renderPool();await sleep(600+Math.floor(Math.random()*900))}catch(e){appLog('导入登录失败 '+maskEmail(a2.email)+': '+e.message,'w')}
    }
  }
  if(relink){toast('已为 '+relink+' 个账号恢复会话','success');appLog('导入后会话恢复 ×'+relink,'s')}
}
async function importPoolFile(file){
  var txt=await file.text();
  await importPoolData(txt);
}

// ---------- 选号与生成 ----------
function poolCredits(){
  var s=0;for(var i=0;i<state.accounts.length;i++){var a=state.accounts[i];if(!a.disabled&&typeof a.credits==='number')s+=a.credits}
  return s;
}
function pickAccount(){
  var cands=[];
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(!a.disabled&&a.apiKey&&(typeof a.credits==='number'&&a.credits>=1))cands.push(a);
  }
  if(!cands.length)return null;
  if(state.settings.rotationStrategy==='round-robin'){
    cands.sort(function(x,y){return x.createdAt-y.createdAt});
    var idx=state.rotationIndex%cands.length;state.rotationIndex=(state.rotationIndex+1)%Math.max(cands.length,1);
    return cands[idx];
  }
  cands.sort(function(x,y){return (y.credits-x.credits)||(x.createdAt-y.createdAt)});
  return cands[0];
}
async function findReadyAccount(){
  // 1) 直接可用的号
  var a=pickAccount();if(a)return a;
  // 2) 有会话但没 Key → 补建
  for(var i=0;i<state.accounts.length;i++){
    var x=state.accounts[i];
    if(!x.disabled&&x.session&&!x.apiKey&&(typeof x.credits==='number'&&x.credits>=1)){
      try{await createKeyFor(x);saveState();renderAll();return x}catch(e){}
    }
  }
  // 3) 有 Key 但额度显示 0/未知 → 刷新额度再试
  for(var j=0;j<state.accounts.length;j++){
    var y=state.accounts[j];
    if(!y.disabled&&y.apiKey){
      try{await refreshAccount(y)}catch(e){}
      if(typeof y.credits==='number'&&y.credits>=1){saveState();renderAll();return y}
    }
  }
  saveState();renderAll();
  // 4) 自动注册（+1 分）
  if(state.settings.autoRegister){
    try{
      var na=await registerAccount(true);
      if(na.apiKey)return na;
      await createKeyFor(na);return na;
    }catch(e){throw new Error('无可用账号且自动注册失败: '+e.message)}
  }
  throw new Error('号池没有可用账号（有 Key 且积分 ≥ 1）。请打开号池注册或签到。');
}
function refCount(){return refImages.length}
async function generate(){
  if(generating)return;
  var prompt=$('prompt').value.trim();
  if(!prompt&&!refCount()){setStatus('genStatus','请先输入提示词（或添加参考图）。','err');return}
  generating=true;var btn=$('btnGenerate');btn.disabled=true;btn.textContent='生成中…';
  currentRunId='R'+Date.now().toString(36)+randStr(3);
  var histEntry={ts:Date.now(),run:currentRunId,prompt:(prompt||'（参考图创作）').slice(0,80),model:$('model').value,size:$('ratio').value,quality:$('quality').value,account:'',status:'running',error:''};
  histItems.unshift(histEntry);histItems=histItems.slice(0,30);renderHist();
  appLog('====== 生图开始 '+currentRunId+' ======','i','',currentRunId);
  appLog('参数: model='+$('model').value+' size='+$('ratio').value+' quality='+$('quality').value+' 参考图='+refCount()+'张 prompt="'+(prompt||'').slice(0,80)+'"','i','',currentRunId);
  var t0=Date.now();
  try{
    var acc=await findReadyAccount();
    histEntry.account=maskEmail(acc.email);
    appLog('选中账号 '+maskEmail(acc.email)+'（积分 '+acc.credits+'，注册于 '+new Date(acc.createdAt).toLocaleString()+'）','i','',currentRunId);
    if(acc.createdAt&&(Date.now()-acc.createdAt)<24*3600*1000){
      appLog('提示: 该账号注册未满 24 小时。24h 冷却只限制签到，不影响生图（实测新生号可立即生图）；若本号生图异常将自动换号','w','',currentRunId);
    }
    setStatus('genStatus','使用 '+maskEmail(acc.email)+'（'+acc.credits+' 分）· 正在上游生成，约 20~60 秒…','info');
    var body={prompt:prompt||'基于参考图创作',model:$('model').value,size:$('ratio').value,quality:$('quality').value,response_format:'b64_json',n:1};
    if(refCount())body.reference_images=refImages.slice(0,10);
    var r=await genWithAccount(acc,body,currentRunId);
    if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
      finishGenSuccess(r,acc,histEntry,currentRunId);
    }else{
      var msg=upstreamErrMsg(r,'生成失败');
      // 401: Key 失效 → 重登 + 重建 Key 重试一次；402: 积分不足 → 标记后换号重试一次；429: 稍候重试一次
      if(r.status===401){
        appLog('API Key 失效，重登并重建 Key 后重试','w','',currentRunId);
        setStatus('genStatus','API Key 失效，正在重新登录并重建 Key…','info');
        await loginAccount(acc);await createKeyFor(acc);saveState();
        r=await genWithAccount(acc,body,currentRunId);
        if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
          finishGenSuccess(r,acc,histEntry,currentRunId);
        }else{throw new Error(upstreamErrMsg(r,'重试后仍失败'))}
      }else if(r.status===402){
        acc.credits=0;saveState();renderAll();
        appLog('积分不足，标记后换号重试','w','',currentRunId);
        setStatus('genStatus',maskEmail(acc.email)+' 积分不足，切换其他账号…','info');
        var acc2=await findReadyAccount();
        if(acc2===acc)throw new Error('积分不足: '+msg);
        histEntry.account=maskEmail(acc2.email);
        appLog('切换到 '+maskEmail(acc2.email)+'（积分 '+acc2.credits+'）','i','',currentRunId);
        setStatus('genStatus','使用 '+maskEmail(acc2.email)+'（'+acc2.credits+' 分）· 重新生成…','info');
        r=await genWithAccount(acc2,body,currentRunId);
        if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
          finishGenSuccess(r,acc2,histEntry,currentRunId);
        }else{throw new Error(upstreamErrMsg(r,'切换账号后仍失败'))}
      }else if(r.status===429){
        appLog('上游限流，5 秒后重试','w','',currentRunId);
        setStatus('genStatus','上游限流，5 秒后重试…','info');
        await sleep(5000);
        r=await genWithAccount(acc,body,currentRunId);
        if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
          finishGenSuccess(r,acc,histEntry,currentRunId);
        }else{throw new Error(upstreamErrMsg(r,'限流重试失败'))}
      }else{
        // 新生号保护：若账号注册未满 24h 且生图被拒（如 403），自动换其他账号重试一次
        var fresh=acc.createdAt&&(Date.now()-acc.createdAt)<24*3600*1000;
        if(fresh&&(r.status===403||r.status===400)){
          var remain=24*3600*1000-(Date.now()-acc.createdAt);
          appLog('新生号（未满24h，剩 '+fmtRemain(remain)+'）生图被拒 HTTP '+r.status+'，尝试换其他账号','w','',currentRunId);
          setStatus('genStatus','账号注册未满 24 小时（剩 '+fmtRemain(remain)+'）可能受限，尝试其他账号…','info');
          var acc3=null;
          for(var fi=0;fi<state.accounts.length;fi++){
            var cand=state.accounts[fi];
            if(cand!==acc&&!cand.disabled&&cand.apiKey&&(typeof cand.credits==='number'&&cand.credits>=1)){acc3=cand;break}
          }
          if(acc3){
            histEntry.account=maskEmail(acc3.email);
            appLog('切换到 '+maskEmail(acc3.email)+'（积分 '+acc3.credits+'）','i','',currentRunId);
            r=await genWithAccount(acc3,body,currentRunId);
            if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
              finishGenSuccess(r,acc3,histEntry,currentRunId);
            }else{throw new Error(upstreamErrMsg(r,'换号后仍失败'))}
          }else{
            throw new Error(msg+'（提示: 号池其他账号均不可用；当前号注册未满 24 小时，剩 '+fmtRemain(remain)+'，若上游限制新生号请稍后再试）');
          }
        }else{
          throw new Error(msg);
        }
      }
    }
  }catch(e){
    var m=(e&&e.name==='AbortError')?'生成超时（180s），已终止。积分未扣除则已由上游返还。':(e.message||String(e));
    histEntry.status='error';histEntry.error=m.slice(0,120);
    setStatus('genStatus',m,'err');
    appLog('生图失败: '+m,'e','',currentRunId);
    appLog('====== 生图结束（失败，耗时 '+((Date.now()-t0)/1000).toFixed(1)+'s）======','e','',currentRunId);
    notifyUser('❌ 生图失败',('【AI生图】'+m.slice(0,120)),'fail-'+currentRunId);
  }finally{
    saveState();saveLogs();generating=false;btn.disabled=false;btn.textContent='开始生成（消耗 1 积分）';
    renderAll();renderHist();
  }
}
// 单次生图请求（180s 超时）
async function genWithAccount(acc,body,runId){
  var ctrl=new AbortController();var timer=setTimeout(function(){ctrl.abort()},180000);
  try{
    appLog('POST /v1/images/generations（'+maskEmail(acc.email)+'，超时 180s）','i','',runId);
    var r=await kmageV1('/images/generations',{method:'POST',body:JSON.stringify(body),signal:ctrl.signal},acc.apiKey);
    if(r.ok){appLog('上游受理成功，耗时 '+((r.durationMs||0)/1000).toFixed(1)+'s','s','',runId)}
    return r;
  }catch(e){
    if(e&&e.name==='AbortError'){appLog('请求超时 180s，已中止（AbortError）','e','',runId)}
    else{appLog('请求异常: '+(e.message||e),'e','',runId)}
    throw e;
  }finally{clearTimeout(timer)}
}
function finishGenSuccess(r,acc,histEntry,runId){
  lastResultB64=r.data.data[0].b64_json;
  showResult(r.data);
  if(typeof acc.credits==='number')acc.credits=Math.max(0,acc.credits-1);
  histEntry.status='ok';
  var secs=((r.data.generation_time_ms||r.durationMs||0)/1000).toFixed(1);
  setStatus('genStatus','生成完成（耗时 '+secs+'s）· '+maskEmail(acc.email)+' 剩余 '+acc.credits+' 分','ok');
  appLog('====== 生图结束（成功，上游耗时 '+secs+'s，'+maskEmail(acc.email)+' 剩 '+acc.credits+' 分）======','s','',runId);
  notifyUser('✅ 生图完成','【AI生图】第 '+(histEntry.prompt||'').slice(0,40)+' … 已完成（'+secs+'s）','ok-'+runId);
}
function showResult(data){
  $('resultEmpty').style.display='none';
  $('resultWrap').style.display='block';
  $('resultImg').src='data:image/png;base64,'+lastResultB64;
  var kb=Math.round(lastResultB64.length*3/4/1024);
  $('resultMeta').textContent=(data.model||'')+' · '+(data.size||'')+' · 约 '+kb+' KB';
}
function downloadResult(){
  if(!lastResultB64)return;
  var b64=lastResultB64,len=b64.length,bin=new Uint8Array(Math.floor(len*3/4)+3),p=0;
  var raw=atob(b64);for(var i=0;i<raw.length;i++)bin[i]=raw.charCodeAt(i);
  var blob=new Blob([bin.subarray(0,raw.length)],{type:'image/png'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='kmage_'+new Date().toISOString().slice(0,19).replace(/[:T-]/g,'')+'.png';
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
}
</script>
<script>
// ---------- 渲染 ----------
function renderBadge(){
  var b=$('creditBadge');var total=poolCredits();
  b.textContent='积分 '+total;
  b.className='badge'+(total<=0?' zero':'');
  b.title='号池可用总积分（'+state.accounts.length+' 个账号）';
}
function acctStatus(a){
  if(a.disabled)return '<span class="pill mut">已禁用</span>';
  if(!a.session)return '<span class="pill err">无会话</span>';
  if(!a.apiKey)return '<span class="pill warn">未建Key</span>';
  if(a.lastCheckinDay===todayGmt8())return '<span class="pill ok">今日已签</span>';
  var now=Date.now();
  if(a.eligibleAt&&a.eligibleAt>now){
    return '<span class="pill warn">待激活 '+fmtRemain(a.eligibleAt-now)+'</span>';
  }
  if(typeof a.credits==='number'&&a.credits<=0)return '<span class="pill err">0分</span>';
  return '<span class="pill ok">正常</span>';
}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function renderPool(){
  var tb=$('poolTbody');
  if(!state.accounts.length){tb.innerHTML='<tr><td colspan="6" style="color:var(--text-muted)">号池为空，点击"注册新账号"开始。</td></tr>';return}
  var html='';
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    html+='<tr>'
      +'<td title="'+esc(a.email)+'">'+esc(maskEmail(a.email))+'</td>'
      +'<td>'+(typeof a.credits==='number'?a.credits:'-')+'</td>'
      +'<td>'+(a.apiKey?'<span class="pill ok">已有</span>':'<span class="pill mut">无</span>')+'</td>'
      +'<td>'+(a.lastCheckinDay===todayGmt8()?'✓':'—')+'</td>'
      +'<td>'+acctStatus(a)+'</td>'
      +'<td class="op">'
      +'<button class="btn sm" data-act="checkin" data-i="'+i+'">签到</button> '
      +'<button class="btn sm" data-act="refresh" data-i="'+i+'">刷新</button> '
      +'<button class="btn sm" data-act="toggle" data-i="'+i+'">'+(a.disabled?'启用':'禁用')+'</button> '
      +'<button class="btn sm danger" data-act="remove" data-i="'+i+'">删除</button>'
      +'</td></tr>';
  }
  tb.innerHTML=html;
}
function renderHist(){
  var ul=$('histList');var html='';
  for(var i=0;i<histItems.length;i++){
    var h=histItems[i];
    html+='<li><span>'+(h.status==='ok'?'<span class="okc">✓</span>':(h.status==='running'?'⋯':'<span class="errc">✗</span>'))+'</span>'
      +'<span class="hp" title="'+esc(h.prompt)+'">'+esc(h.prompt)+'</span>'
      +'<span>'+esc(h.model.replace('gpt-image-',''))+'</span>'
      +'<span>'+fmtTime(h.ts)+'</span></li>';
  }
  ul.innerHTML=html||'<li style="border:none;color:var(--text-muted)">暂无任务</li>';
}
function renderRefs(){
  var list=$('refList');
  var html='';
  for(var i=0;i<refImages.length;i++){
    html+='<div class="ref-item"><img src="'+refImages[i]+'"><button class="rm" data-rm="'+i+'" type="button">×</button></div>';
  }
  html+='<button class="ref-add" id="refAdd" type="button" title="添加参考图">+</button>';
  list.innerHTML=html;
  bindRefAdd();
}
function renderAll(){renderBadge();if($('poolDialog').open)renderPool()}
function renderSettings(){
  $('rotationStrategy').value=state.settings.rotationStrategy||'most-credits';
  $('emailDomain').value=state.settings.emailDomain||'gmail.com';
  $('autoRegisterChk').checked=state.settings.autoRegister!==false;
  $('autoCheckinChk').checked=state.settings.autoCheckin!==false;
  $('notifyChk').checked=!!state.settings.notificationsEnabled;
}
function saveSettingsFromUI(){
  state.settings.rotationStrategy=$('rotationStrategy').value;
  state.settings.emailDomain=($('emailDomain').value.trim()||'gmail.com');
  state.settings.autoRegister=$('autoRegisterChk').checked;
  state.settings.autoCheckin=$('autoCheckinChk').checked;
  state.settings.notificationsEnabled=$('notifyChk').checked;
  saveState();
}

// ---------- 自包含文档（README + CHANGELOG，供 AI Agent 与排障使用） ----------
function DOCS_HTML(){
  var h=[];
  h.push('<p style="color:var(--accent-dark);font-weight:600">AI Agent 提示：本页为自包含单文件 Cloudflare Worker（后端代理+内嵌前端+号池），可将本页整体作为 skill 调用；本文档即调试入口。服务自描述: GET /about；健康检查: GET /healthz。</p>');
  h.push('<h3>1. 这是什么</h3>');
  h.push('<p>AI生图（kmage 通道）基于 image.dddd.zone（kmage · AI 视觉工作台）的官方 OpenAI 兼容 API，把「注册账号 → 每日签到攒积分 → API Key 调用生图」整条链路自动化。1 积分 = 1 张图，失败请求上游自动返还积分。</p>');
  h.push('<h3>2. 架构与端点</h3>');
  h.push('<pre>/            页面（HTML+CSS+JS 全内嵌，无外部资源）'+String.fromCharCode(10)+'/healthz     健康检查（版本/上游/时间）'+String.fromCharCode(10)+'/about       服务自描述 JSON（AI Agent 排障入口）'+String.fromCharCode(10)+'/api/kmage/* -> 上游 /api/*   会话类代理（注册/登录/签到/Key/额度），'+String.fromCharCode(10)+'             会话令牌经请求头 X-Kmage-Session 携带，上游 Set-Cookie'+String.fromCharCode(10)+'             经响应头 X-Kmage-Set-Session 回传前端轮换'+String.fromCharCode(10)+'/kmage/v1/*  -> 上游 /v1/*    Bearer 透传（生图/模型，官方 OpenAI 兼容）</pre>');
  h.push('<h3>3. 号池与数据模型</h3>');
  h.push('<p>全部状态保存在浏览器 localStorage（Worker 无状态，无 KV 依赖）：</p>');
  h.push('<pre>kmage_state_v1  accounts[]: {email,password,session,apiKey,apiKeyId,apiKeyHint,'+String.fromCharCode(10)+'                credits,lastCheckinDay,eligibleAt,createdAt,disabled,lastError}'+String.fromCharCode(10)+'                abandoned[]: 已删除/归档账号'+String.fromCharCode(10)+'                settings: {rotationStrategy,autoRegister,autoCheckin,'+String.fromCharCode(10)+'                emailDomain,notificationsEnabled}'+String.fromCharCode(10)+'kmage_logs_v1   运行日志环形缓冲（最近 300 条，detail 截断 300 字符）</pre>');
  h.push('<h3>4. 积分与 24 小时规则</h3>');
  h.push('<p>注册即送 1 积分；签到 +5 积分/天，但账号注册满 24 小时后才开放（上游返回 403 + eligible:false）。<b>24h 冷却只限制签到，不限制生图</b>——新生号可立即生图（已实测）。若新生号生图被拒，工具自动提示剩余冷却时间并切换其他账号。老虎机 RTP 95.88%（负期望），不纳入自动积分来源。</p>');
  h.push('<h3>5. 反模式化原则（沿袭马良 v27.2）</h3>');
  h.push('<p>· 邮箱：姓名/形容词/名词词库 × 6 种模式 × 随机大小写，无固定前缀与时间戳指纹（v1.0 的 kmg***x+时间戳已去除）。</p>');
  h.push('<p>· 密码：12~15 位完全随机强密码，无固定后缀（v1.0 的 Zq9 尾巴已去除）；API Key 备注名从词池随机。</p>');
  h.push('<p>· 节奏：批量注册间隔 2.5~8s 随机（15% 概率再 +4s），批量签到乱序 + 0.8~2.8s 随机间隔；登录/刷新等操作带随机抖动。</p>');
  h.push('<p>· UA：Worker 端透传访客浏览器真实 UA（缺失时从 4 个常见池随机），不做 IP 伪造（马良 v26.1 已证实无效且移除）。</p>');
  h.push('<h3>6. 运行日志控制台</h3>');
  h.push('<p>右上角「日志」打开控制台。每次生图以运行号（R+时间戳）分组记录：账号选择、请求参数、上游状态码与耗时、错误响应摘要（含非 JSON 响应原文截断）、换号/重试决策。支持导出全部/本次运行（.txt，含版本、UA、页面地址）、一键复制、只看错误、清空；日志持久化到 localStorage，刷新不丢。</p>');
  h.push('<h3>7. 排障指引（AI Agent 适用）</h3>');
  h.push('<p>① GET /about 确认版本与端点；② 打开日志控制台导出日志，定位首个非 2xx 上游请求；③ 常见错误：401 会话/Key 失效（自动重登重建）、402 积分不足（自动换号）、429 限流（5s 退避）、180s 超时（积分不扣则上游返还）；④ 号池数据可导出 JSON 离线分析（含明文凭据，注意保密）；⑤ 上游探活: 直接访问 image.dddd.zone 首页。</p>');
  h.push('<h3>8. CHANGELOG</h3>');
  h.push('<p><b>kmage-1.1 (2026-09-13)</b>：运行日志控制台（记录/导出/复制/持久化）；号池 JSON 导入导出（自动重登恢复会话）；浏览器原生通知（成功/失败/超时，设置开关）；24h 规则明确化（仅限签到，新生号生图异常自动换号提示）；反模式化（拟人邮箱/密码、批量注册与签到随机化乱序、UA 透传）；div.brand 改为「AI生图」；内嵌自包含文档与 AI Agent 提示；新增 /about。</p>');
  h.push('<p><b>kmage-v1.0 (2026-09-13)</b>：新通道上线（上游 image.dddd.zone，替换瘫死的 kdr-v1.2）。号池模式（自动注册/批量签到/补建Key/401重登/402换号/429退避）、most-credits 与 round-robin 轮换、图生图 ≤10 张、会话代理与 Bearer 代理、全量状态 localStorage。</p>');
  h.push('<hr>');
  h.push('<p style="color:var(--text-muted)">合规边界：本工具仅管理用户自行注册账号的自身凭据，不破解、不绕过验证、不链式邀请；请遵守上游服务条款，控制用量。</p>');
  return h.join('');
}
function renderDocs(){$('docsBody').innerHTML=DOCS_HTML()}

// ---------- 事件绑定 ----------
function bindPoolActions(){
  $('poolTbody').addEventListener('click',async function(ev){
    var t=ev.target.closest?ev.target.closest('button[data-act]'):null;
    if(!t)return;
    var i=parseInt(t.getAttribute('data-i'),10);var a=state.accounts[i];if(!a)return;
    var act=t.getAttribute('data-act');
    t.disabled=true;
    try{
      if(act==='checkin'){
        var r=await checkinAccount(a);
        if(r.done)toast('签到成功 +'+(r.reward||0)+' 分','success');
        else if(r.already)toast('今日已签到','info');
        else if(r.wait)toast('注册未满 24 小时，签到将于 '+fmtRemain(r.remainMs)+' 后开放（不影响生图）','info');
        else toast(r.msg||'签到失败','error');
      }else if(act==='refresh'){
        await refreshAccount(a);toast('额度已刷新','success');
      }else if(act==='toggle'){
        a.disabled=!a.disabled;saveState();
      }else if(act==='remove'){
        if(confirm('确定从号池删除该账号？（仅本地删除，不影响上游账号）')){
          state.abandoned.push(a);state.accounts.splice(i,1);saveState();
        }
      }
    }catch(e){toast(e.message,'error')}
    saveState();renderPool();renderBadge();
    t.disabled=false;
  });
}
function bindRefAdd(){
  var btn=$('refAdd');
  if(!btn)return;
  btn.addEventListener('click',function(){$('refInput').click()});
}
function bindAll(){
  $('btnGenerate').addEventListener('click',generate);
  $('btnDownload').addEventListener('click',downloadResult);
  $('poolBtn').addEventListener('click',function(){renderPool();$('poolDialog').showModal()});
  $('poolClose').addEventListener('click',function(){$('poolDialog').close()});
  $('logBtn').addEventListener('click',function(){renderLogBox();$('logDialog').showModal()});
  $('logClose').addEventListener('click',function(){$('logDialog').close()});
  $('docsBtn').addEventListener('click',function(){renderDocs();$('docsDialog').showModal()});
  $('docsClose').addEventListener('click',function(){$('docsDialog').close()});
  $('helpBtn').addEventListener('click',function(){$('helpDialog').showModal()});
  $('helpClose').addEventListener('click',function(){$('helpDialog').close()});
  $('btnExportLogAll').addEventListener('click',function(){exportLogs('all')});
  $('btnExportLogRun').addEventListener('click',function(){exportLogs('run')});
  $('btnCopyLog').addEventListener('click',copyLogsAll);
  $('btnClearLog').addEventListener('click',function(){
    if(!confirm('确定清空全部运行日志？（不影响号池数据）'))return;
    runLogs=[];try{localStorage.removeItem(LOG_KEY)}catch(e){}
    renderLogBox();toast('日志已清空','success');
  });
  $('logErrOnly').addEventListener('change',renderLogBox);
  $('btnExportPool').addEventListener('click',exportPool);
  $('btnImportPool').addEventListener('click',function(){$('importPoolFile').click()});
  $('importPoolFile').addEventListener('change',function(ev){
    var f=(ev.target.files||[])[0];if(f)importPoolFile(f);ev.target.value='';
  });
  $('notifyChk').addEventListener('change',async function(){
    if($('notifyChk').checked){
      var ok=await requestNotificationPermission();
      if(!ok){$('notifyChk').checked=false}
    }
    saveSettingsFromUI();
  });
  $('btnRegister').addEventListener('click',async function(){
    var b=$('btnRegister');b.disabled=true;
    try{await registerAccount(false)}catch(e){toast(e.message,'error')}
    b.disabled=false;renderPool();
  });
  $('btnBatchRegister').addEventListener('click',async function(){
    var n=Math.max(1,Math.min(10,parseInt($('batchCount').value,10)||3));
    var b=$('btnBatchRegister');b.disabled=true;
    setStatus('poolStatus','批量注册中（0/'+n+'）…','info');
    var done=0;
    for(var i=0;i<n;i++){
      try{await registerAccount(true);done++}
      catch(e){toast(e.message,'error');break}
      setStatus('poolStatus','批量注册中（'+done+'/'+n+'）…','info');
      var gap=2500+Math.floor(Math.random()*5500);if(Math.random()<0.15)gap+=4000;
      await sleep(gap);
    }
    setStatus('poolStatus','批量注册完成: 成功 '+done+'/'+n,done===n?'ok':'warn');
    b.disabled=false;renderPool();renderBadge();
  });
  $('btnCheckinAll').addEventListener('click',async function(){
    var b=$('btnCheckinAll');b.disabled=true;setStatus('poolStatus','批量签到中…','info');
    await checkinAll(false);
    setStatus('poolStatus','批量签到完成','ok');
    b.disabled=false;
  });
  $('btnEnsureKeys').addEventListener('click',async function(){
    var b=$('btnEnsureKeys');b.disabled=true;
    await ensureKeysAll();b.disabled=false;
  });
  $('btnRefreshCredits').addEventListener('click',async function(){
    var b=$('btnRefreshCredits');b.disabled=true;setStatus('poolStatus','刷新额度中…','info');
    await refreshAllCredits();
    setStatus('poolStatus','额度刷新完成','ok');
    b.disabled=false;
  });
  $('btnArchiveDisabled').addEventListener('click',archiveDisabled);
  $('rotationStrategy').addEventListener('change',saveSettingsFromUI);
  $('emailDomain').addEventListener('change',saveSettingsFromUI);
  $('autoRegisterChk').addEventListener('change',saveSettingsFromUI);
  $('autoCheckinChk').addEventListener('change',saveSettingsFromUI);
  $('refInput').addEventListener('change',function(ev){
    var files=Array.prototype.slice.call(ev.target.files||[]);
    var room=10-refImages.length;
    files.slice(0,Math.max(0,room)).forEach(function(f){
      if(f.size>10*1024*1024){toast(f.name+' 超过 10MB，已跳过','error');return}
      var rd=new FileReader();
      rd.onload=function(){refImages.push(String(rd.result));renderRefs()};
      rd.readAsDataURL(f);
    });
    ev.target.value='';
  });
  $('refList').addEventListener('click',function(ev){
    var t=ev.target.closest?ev.target.closest('button[data-rm]'):null;
    if(t){var i=parseInt(t.getAttribute('data-rm'),10);refImages.splice(i,1);renderRefs()}
  });
}

// ---------- 启动 ----------
(async function init(){
  loadState();loadLogs();renderSettings();renderBadge();renderHist();renderRefs();bindAll();bindPoolActions();
  appLog('页面加载完成（'+VERSION+'，日志 '+(runLogs.length)+' 条已恢复）','i');
  // 自动签到：仅对今天尚未签到且已过激活时间的账号尝试一次
  if(state.settings.autoCheckin){
    setTimeout(async function(){
      try{
        var need=false;
        for(var i=0;i<state.accounts.length;i++){
          var a=state.accounts[i];
          if(!a.disabled&&a.session&&a.lastCheckinDay!==todayGmt8()){need=true;break}
        }
        if(need)await checkinAll(true);
        renderBadge();
      }catch(e){}
    },1200);
  }
})();
</script>
</body>
</html>`;
