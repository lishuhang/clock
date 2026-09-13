// ============================================================
// gpt2-worker-kmage-v1.0.js
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
// 版本: kmage-v1.0 (2026-09-13)
// ============================================================

const VERSION = 'kmage-v1.0';
const UPSTREAM = 'https://image.dddd.zone';
const SESSION_COOKIE = 'kmage_session';
const SESSION_HEADER = 'X-Kmage-Session';
const SET_SESSION_HEADER = 'X-Kmage-Set-Session';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

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
  headers.set('User-Agent', UA);
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
  headers.set('User-Agent', UA);
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
<title>kmage 生图 · AI 视觉工作台</title>
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
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <h1>kmage 生图</h1>
      <span class="ver">kmage-v1.0</span>
    </div>
    <div class="top-right">
      <span class="badge" id="creditBadge" title="号池可用总积分">积分 -</span>
      <button class="btn sm" id="poolBtn" type="button">号池</button>
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
    <p>· 站内老虎机为娱乐玩法，理论返还率 95.88%（负期望），本工具不对其进行自动化，避免把积分赌没。</p>
    <h4>号池怎么用</h4>
    <p>· 点"注册新账号"或批量注册，工具会自动完成注册、创建 API Key、记录会话；全部数据只保存在你浏览器的 localStorage 中。</p>
    <p>· 每天打开页面时（或手动点"批量签到"），工具会自动为满足条件的账号签到。"待激活"状态的账号要等注册满 24 小时才会开放签到。</p>
    <p>· 生成时按轮换策略选号：积分优先（most-credits）或轮询均衡（round-robin）。遇 402（积分不足）自动换下一个号；遇 401（会话失效）自动用保存的邮箱密码重登并重建 Key。</p>
    <h4>边界说明</h4>
    <p>· 会话与密钥为本工具对注册账号的自身凭据管理，不涉及破解或绕过任何验证；请遵守上游站点服务条款，控制用量，避免滥用免费产能。</p>
    <p>· 邀请奖励需被邀请人首次充值后才到账，不属于免费路径，工具不做链式邀请。</p>
  </div>
</dialog>

<div class="toast-wrap" id="toastWrap"></div>
<script>
// ================= kmage 前端 =================
var VERSION='kmage-v1.0';
var STATE_KEY='kmage_state_v1';
var DEFAULT_SETTINGS={rotationStrategy:'most-credits',autoRegister:true,autoCheckin:true,emailDomain:'gmail.com'};
var state={accounts:[],abandoned:[],settings:{},rotationIndex:0};
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
function genEmail(){
  var dom=(state.settings.emailDomain||'gmail.com').replace(/^@/,'');
  return 'kmg'+randStr(4)+'x'+randStr(8)+Math.floor(Date.now()/1000)%100000+'@'+dom;
}
function genPassword(){
  var up='ABCDEFGHJKLMNPQRSTUVWXYZ',low='abcdefghijkmnpqrstuvwxyz',dg='23456789',sy='#!@%+';
  var p=randStr(3,up)+randStr(4,low)+randStr(3,dg)+sy.charAt(Math.floor(Math.random()*sy.length));
  var arr=p.split('');for(var i=arr.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=arr[i];arr[i]=arr[j];arr[j]=t}
  return arr.join('')+'Zq9';
}
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
  var resp=await fetch('/api/kmage'+path,{method:opts.method||'GET',headers:headers,body:opts.body||undefined,credentials:'omit'});
  captureSession(resp,account);
  var data=null;
  try{data=await resp.json()}catch(e){data={}}
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
  var resp=await fetch('/kmage/v1'+path,fo);
  var data=null;
  try{data=await resp.json()}catch(e){data={}}
  return {ok:resp.ok,status:resp.status,data:data};
}
function upstreamErrMsg(r,fallback){
  if(r&&r.data){
    if(typeof r.data.error==='string')return r.data.error;
    if(r.data.error&&r.data.error.message)return r.data.error.message;
    if(r.data.message)return r.data.message;
  }
  return fallback||('上游错误 HTTP '+(r?r.status:''));
}

// ---------- 账号生命周期 ----------
// 注册：{email,password} → 201 + Set-Cookie 会话；随后建 API Key
async function registerAccount(silent){
  var email=genEmail(),password=genPassword();
  var a={id:'acc_'+randStr(10),email:email,password:password,session:'',apiKey:'',apiKeyId:'',apiKeyHint:'',
    credits:1,lastCheckinDay:'',eligibleAt:0,createdAt:Date.now(),disabled:false,lastError:''};
  var r=await kmageApi('/auth/register',{method:'POST',body:JSON.stringify({email:email,password:password})},a);
  if(!r.ok){
    throw new Error('注册失败: '+upstreamErrMsg(r,'HTTP '+r.status));
  }
  a.credits=(r.data&&r.data.user&&typeof r.data.user.credits==='number')?r.data.user.credits:1;
  if(!a.session){ // 极少数情况上游未返回 Set-Cookie，主动登录补会话
    try{await loginAccount(a)}catch(e){a.lastError='会话获取失败:'+e.message}
  }
  // 注册成功后立刻创建 API Key（密钥只显示一次，必须当场保存）
  try{await createKeyFor(a)}catch(e){a.lastError='建Key失败:'+e.message}
  state.accounts.push(a);saveState();renderAll();
  if(!silent)toast('注册成功: '+maskEmail(email)+'（'+a.credits+' 分'+(a.apiKey?', Key已建':'')+'）','success');
  return a;
}
// 登录（会话失效时自动调用）
async function loginAccount(a){
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
  var r=await withSession(a,function(){return kmageApi('/api-keys',{method:'POST',body:JSON.stringify({name:'pool-'+randStr(4)})},a)});
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
  if(d.eligible===false){return {wait:true,eligibleAt:d.eligible_at||0}}
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
  for(var i=0;i<n;i++){
    try{await registerAccount(true);done++}
    catch(e){fail++;toast(e.message,'error');break}
    await sleep(600+Math.floor(Math.random()*900));
  }
  if(!silent)toast('批量注册完成: 成功 '+done+' 个'+(fail?('，失败 '+fail+' 个'):''),fail?'info':'success');
  renderAll();
}
function sleep(ms){return new Promise(function(res){setTimeout(res,ms)})}
async function checkinAll(silent){
  var done=0,already=0,wait=0,failed=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];if(a.disabled||!a.session)continue;
    try{
      var r=await checkinAccount(a);
      if(r.done){done++;if(r.credits!=null)a.credits=r.credits}
      else if(r.already)already++;
      else if(r.wait)wait++;
      else failed++;
    }catch(e){failed++}
    renderAll();
    await sleep(400+Math.floor(Math.random()*500));
  }
  saveState();renderAll();
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
  setStatus('genStatus','正在选取号池账号…','info');
  var histEntry={ts:Date.now(),prompt:(prompt||'（参考图创作）').slice(0,80),model:$('model').value,size:$('ratio').value,quality:$('quality').value,account:'',status:'running',error:''};
  histItems.unshift(histEntry);histItems=histItems.slice(0,30);renderHist();
  try{
    var acc=await findReadyAccount();
    histEntry.account=maskEmail(acc.email);
    setStatus('genStatus','使用 '+maskEmail(acc.email)+'（'+acc.credits+' 分）· 正在上游生成，约 20~60 秒…','info');
    var body={prompt:prompt||'基于参考图创作',model:$('model').value,size:$('ratio').value,quality:$('quality').value,response_format:'b64_json',n:1};
    if(refCount())body.reference_images=refImages.slice(0,10);
    var ctrl=new AbortController();var timer=setTimeout(function(){ctrl.abort()},180000);
    var r=await kmageV1('/images/generations',{method:'POST',body:JSON.stringify(body),signal:ctrl.signal},acc.apiKey);
    clearTimeout(timer);
    if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
      lastResultB64=r.data.data[0].b64_json;
      showResult(r.data);
      if(typeof acc.credits==='number')acc.credits=Math.max(0,acc.credits-1);
      histEntry.status='ok';
      setStatus('genStatus','生成完成（耗时 '+((r.data.generation_time_ms||0)/1000).toFixed(1)+'s）· '+maskEmail(acc.email)+' 剩余 '+acc.credits+' 分','ok');
    }else{
      var msg=upstreamErrMsg(r,'生成失败');
      // 401: Key 失效 → 重登 + 重建 Key 重试一次；402: 积分不足 → 标记后换号重试一次；429: 稍候重试一次
      if(r.status===401){
        setStatus('genStatus','API Key 失效，正在重新登录并重建 Key…','info');
        await loginAccount(acc);await createKeyFor(acc);saveState();
        r=await kmageV1('/images/generations',{method:'POST',body:JSON.stringify(body)},acc.apiKey);
        if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
          lastResultB64=r.data.data[0].b64_json;showResult(r.data);
          if(typeof acc.credits==='number')acc.credits=Math.max(0,acc.credits-1);
          histEntry.status='ok';
          setStatus('genStatus','生成完成（Key 已重建）','ok');
        }else{throw new Error(upstreamErrMsg(r,'重试后仍失败'))}
      }else if(r.status===402){
        acc.credits=0;saveState();renderAll();
        setStatus('genStatus',maskEmail(acc.email)+' 积分不足，切换其他账号…','info');
        var acc2=await findReadyAccount();
        if(acc2===acc)throw new Error('积分不足: '+msg);
        histEntry.account=maskEmail(acc2.email);
        setStatus('genStatus','使用 '+maskEmail(acc2.email)+'（'+acc2.credits+' 分）· 重新生成…','info');
        r=await kmageV1('/images/generations',{method:'POST',body:JSON.stringify(body)},acc2.apiKey);
        if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
          lastResultB64=r.data.data[0].b64_json;showResult(r.data);
          if(typeof acc2.credits==='number')acc2.credits=Math.max(0,acc2.credits-1);
          histEntry.status='ok';
          setStatus('genStatus','生成完成 · '+maskEmail(acc2.email)+' 剩余 '+acc2.credits+' 分','ok');
        }else{throw new Error(upstreamErrMsg(r,'切换账号后仍失败'))}
      }else if(r.status===429){
        setStatus('genStatus','上游限流，5 秒后重试…','info');
        await sleep(5000);
        r=await kmageV1('/images/generations',{method:'POST',body:JSON.stringify(body)},acc.apiKey);
        if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
          lastResultB64=r.data.data[0].b64_json;showResult(r.data);
          if(typeof acc.credits==='number')acc.credits=Math.max(0,acc.credits-1);
          histEntry.status='ok';
          setStatus('genStatus','生成完成（限流重试成功）','ok');
        }else{throw new Error(upstreamErrMsg(r,'限流重试失败'))}
      }else{
        throw new Error(msg);
      }
    }
  }catch(e){
    var m=(e&&e.name==='AbortError')?'生成超时（180s），已终止。积分未扣除则已由上游返还。':(e.message||String(e));
    histEntry.status='error';histEntry.error=m.slice(0,120);
    setStatus('genStatus',m,'err');
  }finally{
    saveState();generating=false;btn.disabled=false;btn.textContent='开始生成（消耗 1 积分）';
    renderAll();renderHist();
  }
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
    var h=Math.ceil((a.eligibleAt-now)/3600000);
    return '<span class="pill warn">待激活 '+h+'h</span>';
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
}
function saveSettingsFromUI(){
  state.settings.rotationStrategy=$('rotationStrategy').value;
  state.settings.emailDomain=($('emailDomain').value.trim()||'gmail.com');
  state.settings.autoRegister=$('autoRegisterChk').checked;
  state.settings.autoCheckin=$('autoCheckinChk').checked;
  saveState();toast('设置已保存','success');
}

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
        else if(r.wait)toast('账号未满 24 小时，暂不能签到','info');
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
  $('helpBtn').addEventListener('click',function(){$('helpDialog').showModal()});
  $('helpClose').addEventListener('click',function(){$('helpDialog').close()});
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
      await sleep(600+Math.floor(Math.random()*900));
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
  loadState();renderSettings();renderBadge();renderHist();renderRefs();bindAll();bindPoolActions();
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
