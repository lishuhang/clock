// Cloudflare Worker - AI生图 (sq-v1.0)
// sq-v1.0: 全新架构, 仅兼容 squido.ai
//   - 去除 keydraw/97api/马良历史元素
//   - 用户在 squido.ai 浏览器手工注册账号, 把 __session cookie 配置到 Worker
//   - Worker 代理 api.squido.ai, 用配置的 session token 调用生图 API
//   - 支持多 session token 轮换 (号池系统)
//   - 每日 6 credits/account = 2 张 gpt-image-2/日/account
//
// 配置方式:
//   前端设置面板 textarea 中粘贴 session token (每行一个)
//   session token 获取: 浏览器登录 squido.ai → DevTools → Application → Cookies → __session
//
// 部署: 见 0722-gpt2/.deploy/wrangler.toml

const UPSTREAM = {
  base: 'https://api.squido.ai',
  site: 'https://squido.ai',
  models: ['gpt-image-2', 'gpt-image-1-5', 'nano-banana-2', 'nano-banana-pro',
           'qwen-image', 'seedream-4-5', 'flux-schnell']
};

const VERSION = 'sq-v1.0';
const SESSION_HEADER = 'X-Squido-Session';

// ===================== HTML 前端 =====================
const HTML_CONTENT = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI生图 (squido)</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --accent:#6c5ce7;--accent-hover:#a29bfe;--accent-light:rgba(108,92,231,.10);
  --bg:#FFF;--bg-card:#FFF;--bg-secondary:#F5F5F5;--bg-hover:#E2E8F0;
  --text:#1A202C;--text-secondary:#718096;--text-muted:#A0AEC0;
  --border:#E0E0E0;--border-medium:#CBD5E0;
  --radius:8px;--radius-xs:4px;
  --space-xs:4px;--space-sm:8px;--space-md:16px;--space-lg:24px;
  --font:"Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --mono:'SF Mono',Consolas,'Liberation Mono',Menlo,monospace;
  --green:#00b894;--red:#e17055;--yellow:#fdcb6e;--gray:#666;
}
[data-theme="dark"]{
  --bg:#0a0a0b;--bg-card:#141416;--bg-secondary:#1c1c20;--bg-hover:#242429;
  --text:#e8e6e3;--text-secondary:#a09f9d;--text-muted:#6b6a68;
  --border:#242429;--border-medium:#333;
  --accent:#6c5ce7;--accent-hover:#a29bfe;--accent-light:rgba(108,92,231,.12);
  --green:#00b894;--red:#e17055;--yellow:#fdcb6e;--gray:#888;
}
html,body{height:100%;font-family:var(--font);background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 16px;font-size:13px;font-weight:600;border-radius:var(--radius);border:1px solid var(--border);background:var(--bg-secondary);color:var(--text);cursor:pointer;font-family:var(--font);white-space:nowrap}
.btn:hover:not(:disabled){background:var(--bg-hover);border-color:var(--border-medium)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--accent-hover)}
.btn-ghost{border:none;background:transparent;color:var(--text-secondary);padding:4px 8px}
.btn-ghost:hover:not(:disabled){color:var(--text);background:var(--bg-secondary)}
.btn-sm{padding:4px 10px;font-size:12px;border-radius:var(--radius-xs)}
.btn-full{width:100%}
.select-field{padding:8px 32px 8px 12px;font-size:13px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-card);color:var(--text);outline:none;cursor:pointer;appearance:none;-webkit-appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%23718096' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center;width:100%;height:38px;font-family:var(--font)}
.input-field{padding:8px 12px;font-size:13px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-card);color:var(--text);outline:none;line-height:1.5;width:100%;font-family:var(--font)}
.input-field:focus{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-light)}
textarea.input-field{min-height:80px;resize:vertical;font-family:var(--mono);font-size:12px}

#topNav{background:var(--bg-secondary);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 var(--space-lg);border-bottom:1px solid var(--border)}
.nav-left{display:flex;align-items:center;gap:8px}
.nav-right{display:flex;align-items:center;gap:12px}
#topNav .title{font-size:20px;font-weight:700}
.version-badge{font-size:11px;color:var(--text-muted);font-family:var(--mono)}

#mainLayout{display:flex;flex-direction:column;height:calc(100vh - 56px)}
#contentArea{flex:1;display:flex;overflow:hidden}
#promptPanel{width:380px;border-right:1px solid var(--border);padding:var(--space-md);overflow-y:auto;background:var(--bg)}
#resultPanel{flex:1;padding:var(--space-md);overflow-y:auto;display:flex;flex-direction:column;gap:var(--space-md)}

.section-title{font-size:13px;font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-sm);text-transform:uppercase;letter-spacing:.5px}
.prompt-textarea{min-height:120px;resize:vertical}
.size-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.size-btn{padding:8px;border:1px solid var(--border);background:var(--bg-card);color:var(--text);border-radius:var(--radius-xs);cursor:pointer;font-size:12px;font-family:var(--font)}
.size-btn:hover{border-color:var(--accent)}
.size-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.gen-btn{width:100%;padding:14px;background:var(--accent);color:#fff;border:none;border-radius:var(--radius);font-size:15px;font-weight:700;cursor:pointer;margin-top:var(--space-md)}
.gen-btn:hover:not(:disabled){background:var(--accent-hover)}
.gen-btn:disabled{opacity:.5;cursor:not-allowed}

.task-card{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:var(--space-md);display:flex;flex-direction:column;gap:var(--space-sm)}
.task-card.error{border-color:var(--red)}
.task-card .task-prompt{font-size:13px;color:var(--text-secondary);max-height:60px;overflow:hidden}
.task-card .task-status{display:inline-block;padding:2px 8px;border-radius:var(--radius-xs);font-size:11px;font-weight:600}
.task-card .task-status.queued{background:var(--bg-secondary);color:var(--text-secondary)}
.task-card .task-status.running{background:var(--accent-light);color:var(--accent)}
.task-card .task-status.success{background:rgba(0,184,148,.1);color:var(--green)}
.task-card .task-status.error{background:rgba(225,112,85,.1);color:var(--red)}
.task-card .progress-bar{height:4px;background:var(--bg-secondary);border-radius:2px;overflow:hidden}
.task-card .progress-bar .progress-fill{height:100%;background:var(--accent);transition:width .3s}
.task-card .task-image{max-width:100%;border-radius:var(--radius-xs);margin-top:var(--space-sm)}

.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:100}
.modal-backdrop.show{display:flex}
.modal{background:var(--bg-card);border-radius:var(--radius);padding:var(--space-lg);max-width:600px;width:90%;max-height:80vh;overflow-y:auto}
.modal h2{margin-bottom:var(--space-md)}
.modal .form-row{margin-bottom:var(--space-md)}
.modal .form-row label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px}
.token-help{font-size:12px;color:var(--text-muted);margin-top:4px;line-height:1.5}
.token-help code{background:var(--bg-secondary);padding:1px 4px;border-radius:3px;font-family:var(--mono);font-size:11px}

.quota-badge{font-size:12px;padding:4px 10px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-xs)}
</style>
</head>
<body>
<nav id="topNav">
  <div class="nav-left">
    <span class="title">AI生图</span>
    <span class="version-badge">sq-v1.0</span>
  </div>
  <div class="nav-right">
    <span id="quotaBadge" class="quota-badge">未配置 token</span>
    <button class="btn btn-ghost btn-sm" id="settingsBtn">⚙ 设置</button>
  </div>
</nav>

<div id="mainLayout">
  <div id="contentArea">
    <div id="promptPanel">
      <div class="section-title">提示词</div>
      <textarea id="promptInput" class="input-field prompt-textarea" placeholder="描述你想生成的图片..."></textarea>

      <div class="section-title" style="margin-top:16px">模型</div>
      <select id="modelSelect" class="select-field">
        <option value="gpt-image-2" selected>GPT Image 2</option>
        <option value="gpt-image-1-5">GPT Image 1.5</option>
        <option value="nano-banana-2">Nano Banana 2</option>
        <option value="nano-banana-pro">Nano Banana Pro</option>
        <option value="qwen-image">Qwen Image</option>
        <option value="seedream-4-5">Seedream 4.5</option>
        <option value="flux-schnell">Flux Schnell</option>
      </select>

      <div class="section-title" style="margin-top:16px">比例</div>
      <div class="size-grid" id="sizeGrid">
        <button class="size-btn" data-size="1024x1024" data-ratio="1:1">1:1 正方</button>
        <button class="size-btn active" data-size="1792x1024" data-ratio="16:9">16:9 横</button>
        <button class="size-btn" data-size="1024x1792" data-ratio="9:16">9:16 竖</button>
        <button class="size-btn" data-size="1536x1024" data-ratio="3:2">3:2 横</button>
        <button class="size-btn" data-size="1024x1536" data-ratio="2:3">2:3 竖</button>
        <button class="size-btn" data-size="1280x768" data-ratio="5:3">5:3 横</button>
      </div>

      <div class="section-title" style="margin-top:16px">清晰度</div>
      <select id="qualitySelect" class="select-field">
        <option value="1K" selected>1K (标准)</option>
        <option value="2K">2K (高清)</option>
        <option value="4K">4K (超清)</option>
      </select>

      <button id="generateBtn" class="gen-btn">生成图片</button>
    </div>

    <div id="resultPanel">
      <div class="section-title">任务列表</div>
      <div id="taskList"></div>
    </div>
  </div>
</div>

<!-- Settings Modal -->
<div id="settingsModal" class="modal-backdrop">
  <div class="modal">
    <h2>⚙ 设置</h2>
    <div class="form-row">
      <label>Squido Session Tokens (每行一个)</label>
      <textarea id="tokensTextarea" class="input-field" style="min-height:140px;font-family:var(--mono);font-size:11px" placeholder="eyJ...&#10;eyJ...&#10;eyJ..."></textarea>
      <div class="token-help">
        获取方法: 浏览器登录 <a href="https://squido.ai/ai-image-generator" target="_blank">squido.ai</a> → F12 DevTools → Application → Cookies → <code>https://squido.ai</code> → 复制 <code>__session</code> 的值。<br>
        每个账号每日 6 credits = 2 张 gpt-image-2。多个 token 自动轮换。
      </div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button class="btn" id="settingsCancel">取消</button>
      <button class="btn btn-primary" id="settingsSave">保存</button>
    </div>
  </div>
</div>

<script>
const VERSION = 'sq-v1.0';
const state = {
  tokens: [],  // array of {token, exhaustedToday, lastUsed, label}
  tasks: [],   // array of task objects
  currentDate: '',
};

// ===================== State Management =====================
function getTodayGMT8() {
  const now = new Date();
  // GMT+8
  const gmt8 = new Date(now.getTime() + (now.getTimezoneOffset() + 480) * 60000);
  return gmt8.toISOString().slice(0, 10);
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem('sq-state') || '{}');
    if (saved.tokens) state.tokens = saved.tokens;
    if (saved.currentDate !== getTodayGMT8()) {
      // Daily reset
      state.tokens.forEach(t => t.exhaustedToday = false);
      state.currentDate = getTodayGMT8();
    }
  } catch (e) { console.warn('loadState err', e); }
}

function saveState() {
  state.currentDate = getTodayGMT8();
  localStorage.setItem('sq-state', JSON.stringify({
    tokens: state.tokens,
    currentDate: state.currentDate,
  }));
}

function getAvailableTokens() {
  return state.tokens.filter(t => !t.exhaustedToday);
}

function pickToken() {
  const avail = getAvailableTokens();
  if (!avail.length) return null;
  // Pick least recently used
  avail.sort((a, b) => (a.lastUsed || 0) - (b.lastUsed || 0));
  return avail[0];
}

function markTokenExhausted(token) {
  const t = state.tokens.find(x => x.token === token);
  if (t) {
    t.exhaustedToday = true;
    saveState();
    renderQuotaBadge();
  }
}

function renderQuotaBadge() {
  const total = state.tokens.length;
  const avail = getAvailableTokens().length;
  const el = document.getElementById('quotaBadge');
  if (total === 0) {
    el.textContent = '未配置 token';
    el.style.color = 'var(--red)';
  } else {
    el.textContent = avail + '/' + total + ' tokens 可用';
    el.style.color = avail > 0 ? 'var(--green)' : 'var(--red)';
  }
}

// ===================== Settings Modal =====================
function showSettings() {
  const ta = document.getElementById('tokensTextarea');
  ta.value = state.tokens.map(t => t.token).join('\\n');
  document.getElementById('settingsModal').classList.add('show');
}
function hideSettings() {
  document.getElementById('settingsModal').classList.remove('show');
}
function saveSettings() {
  const ta = document.getElementById('tokensTextarea');
  const lines = ta.value.split(String.fromCharCode(10)).map(s => s.trim()).filter(Boolean);
  // Preserve existing token metadata, add new ones
  const existing = new Map(state.tokens.map(t => [t.token, t]));
  state.tokens = lines.map((line, i) => existing.get(line) || {
    token: line,
    exhaustedToday: false,
    lastUsed: 0,
    label: 'Token ' + (i + 1),
  });
  saveState();
  renderQuotaBadge();
  hideSettings();
}

// ===================== Tasks =====================
function genClientTaskId() {
  return 'sq-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
}

function addTask(task) {
  state.tasks.unshift(task);
  if (state.tasks.length > 50) state.tasks.pop();
  renderTasks();
}

function updateTask(id, updates) {
  const t = state.tasks.find(x => x.id === id);
  if (t) Object.assign(t, updates);
  renderTasks();
}

function renderTasks() {
  const list = document.getElementById('taskList');
  if (!state.tasks.length) {
    list.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px">还没有任务。输入提示词后点击"生成图片"。</div>';
    return;
  }
  list.innerHTML = state.tasks.map(t => {
    const statusClass = t.status || 'queued';
    const statusText = {queued:'排队中', running:t.progressText || '生成中', success:'完成', error:'失败'}[t.status] || t.status;
    const imageHtml = t.imageUrl
      ? '<a href="' + t.imageUrl + '" target="_blank"><img src="' + t.imageUrl + '" class="task-image" /></a>'
      : '';
    const errorHtml = t.error ? '<div style="color:var(--red);font-size:12px">' + t.error + '</div>' : '';
    return '<div class="task-card ' + (t.status === 'error' ? 'error' : '') + '">'
      + '<div style="display:flex;justify-content:space-between;align-items:center">'
      + '<span class="task-status ' + statusClass + '">' + statusText + '</span>'
      + '<span style="font-size:11px;color:var(--text-muted)">' + (t.tokenLabel || '') + '</span>'
      + '</div>'
      + '<div class="task-prompt">' + (t.prompt || '') + '</div>'
      + (t.status === 'running' ? '<div class="progress-bar"><div class="progress-fill" style="width:' + (t.progress || 0) + '%"></div></div>' : '')
      + imageHtml + errorHtml
      + '</div>';
  }).join('');
}

// ===================== API calls (via Worker proxy) =====================
async function apiFetch(path, options) {
  const opts = options || {};
  const headers = opts.headers || {};
  if (opts._sessionToken) {
    headers[SESSION_HEADER] = opts._sessionToken;
  }
  headers['Content-Type'] = 'application/json';
  const r = await fetch(path, {
    method: opts.method || 'GET',
    headers,
    body: opts.body,
  });
  return r;
}

async function startGeneration() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) { alert('请输入提示词'); return; }
  const model = document.getElementById('modelSelect').value;
  const sizeBtn = document.querySelector('.size-btn.active');
  const size = sizeBtn ? sizeBtn.dataset.size : '1792x1024';
  const quality = document.getElementById('qualitySelect').value;

  const tokenEntry = pickToken();
  if (!tokenEntry) {
    alert('没有可用的 token。请点击"⚙ 设置"配置 Squido session token。');
    showSettings();
    return;
  }

  const taskId = genClientTaskId();
  const task = {
    id: taskId,
    prompt,
    model,
    size,
    quality,
    status: 'queued',
    progress: 0,
    progressText: '排队中',
    tokenLabel: tokenEntry.label,
    createdAt: Date.now(),
  };
  addTask(task);

  // Mark token as used (rotate)
  tokenEntry.lastUsed = Date.now();
  saveState();

  try {
    // Step 1: Submit generation task
    // Squido API: POST /api/generate/{type}  where type = 'Image' or 'Video'
    // Body fields: {prompt, fileUrls, model, resolution, ratio, generationMode, ...}
    updateTask(taskId, {status: 'running', progress: 30, progressText: '提交中'});
    const submitBody = JSON.stringify({
      prompt: prompt,
      fileUrls: [],
      model: model,
      resolution: quality,  // "1K" / "2K" / "4K"
      ratio: sizeBtn.dataset.ratio,  // "16:9" / "1:1" 等
      remove_watermark: false,
      generationMode: 'text-to-image',
      web_search: true,
      files: [],
    });
    const r = await apiFetch('/api/generate/Image', {
      method: 'POST',
      body: submitBody,
      _sessionToken: tokenEntry.token,
    });
    const d = await r.json();
    if (!r.ok) {
      const errMsg = d.error || d.message || '提交失败';
      if (errMsg.includes('quota') || errMsg.includes('limit') || errMsg.includes('credit') || errMsg.includes('额度') || errMsg.includes('上限')) {
        markTokenExhausted(tokenEntry.token);
      }
      throw new Error(errMsg);
    }
    const upstreamTaskId = d.taskId || d.id || d.data?.id;
    if (!upstreamTaskId) throw new Error('未返回 taskId: ' + JSON.stringify(d));

    // Step 2: Poll for completion
    updateTask(taskId, {status: 'running', progress: 50, progressText: '生成中', upstreamTaskId});
    let pollCount = 0;
    while (pollCount < 60) {
      await new Promise(r => setTimeout(r, 3000));
      pollCount++;
      const pr = await apiFetch('/api/generate/' + encodeURIComponent(upstreamTaskId), {
        _sessionToken: tokenEntry.token,
      });
      const pd = await pr.json();
      if (!pr.ok) {
        throw new Error(pd.error || pd.message || '轮询失败');
      }
      const status = pd.status;
      if (status === 'COMPLETED' || status === 'success') {
        const imageUrl = pd.result?.url || pd.url || pd.data?.url;
        if (!imageUrl) throw new Error('成功但无图片: ' + JSON.stringify(pd));
        updateTask(taskId, {status: 'success', progress: 100, progressText: '完成', imageUrl: resolveUrl(imageUrl)});
        return;
      }
      if (status === 'FAILED' || status === 'error') {
        const errMsg = pd.error || pd.message || '上游生成失败';
        throw new Error(errMsg);
      }
      // PENDING / PROCESSING — continue
      updateTask(taskId, {progress: 50 + pollCount, progressText: pd.status || '生成中'});
    }
    throw new Error('超时 (180s)');
  } catch (e) {
    console.error('Generation err:', e);
    updateTask(taskId, {status: 'error', error: e.message, progressText: '失败'});
  }
}

function resolveUrl(url) {
  if (!url) return url;
  if (url.startsWith('http')) return url;
  return UPSTREAM_BASE + (url.startsWith('/') ? url : '/' + url);
}
const UPSTREAM_BASE = 'https://api.squido.ai';

// ===================== Event handlers =====================
document.getElementById('generateBtn').addEventListener('click', startGeneration);
document.getElementById('settingsBtn').addEventListener('click', showSettings);
document.getElementById('settingsCancel').addEventListener('click', hideSettings);
document.getElementById('settingsSave').addEventListener('click', saveSettings);

document.querySelectorAll('.size-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

document.getElementById('settingsModal').addEventListener('click', (e) => {
  if (e.target.id === 'settingsModal') hideSettings();
});

// ===================== Init =====================
loadState();
renderQuotaBadge();
renderTasks();
console.log('sq-v1.0 init. Tokens:', state.tokens.length);
</script>
`;

// ===================== Worker Backend =====================
// Re-use UPSTREAM defined at top of file (base + site)
// SESSION_HEADER defined at top of file

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,' + SESSION_HEADER,
    'Access-Control-Expose-Headers': 'Content-Length, Content-Type',
  };
}

async function handleProxy(request, url) {
  // Forward to https://api.squido.ai/v1/...
  // Path mapping:
  //   POST /api/generate           → POST https://api.squido.ai/v1/image
  //   GET  /api/generate/{taskId}  → GET  https://api.squido.ai/v1/image/{taskId}
  //   POST /api/upload             → POST https://api.squido.ai/upload

  const path = url.pathname;
  const sessionToken = request.headers.get(SESSION_HEADER) || url.searchParams.get('token') || '';

  let upstreamUrl;
  let upstreamInit = {
    method: request.method,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
      'Accept': 'application/json',
      'Origin': UPSTREAM.site,
      'Referer': UPSTREAM.site + '/ai-image-generator',
    },
  };

  // Session token goes into Cookie header (Clerk session)
  if (sessionToken) {
    upstreamInit.headers['Cookie'] = '__session=' + sessionToken + '; __client_uat=1';
  }

  if (path === '/api/generate/Image' && request.method === 'POST') {
    // Squido's own proxy: POST /api/generate/Image with ev body
    upstreamUrl = UPSTREAM.site + '/api/generate/Image';
    const body = await request.text();
    upstreamInit.body = body;
    upstreamInit.headers['Content-Type'] = 'application/json';
  } else if (path.startsWith('/api/generate/') && request.method === 'GET') {
    // Squido's poll endpoint: GET /api/generate/{taskId} (proxy to api.squido.ai/v1/image/{taskId})
    const taskId = path.replace('/api/generate/', '');
    upstreamUrl = UPSTREAM.base + '/v1/image/' + encodeURIComponent(taskId);
  } else if (path === '/api/upload' && request.method === 'POST') {
    upstreamUrl = UPSTREAM.base + '/upload';
    // Forward body (multipart)
    const body = await request.arrayBuffer();
    upstreamInit.body = body;
    upstreamInit.headers['Content-Type'] = request.headers.get('Content-Type') || 'multipart/form-data';
  } else if (path === '/api/check-session' && request.method === 'GET') {
    // Verify the session token works
    upstreamUrl = UPSTREAM.site + '/api/get-user-info';
    upstreamInit.method = 'POST';
    upstreamInit.body = JSON.stringify({});
    upstreamInit.headers['Content-Type'] = 'application/json';
  } else {
    return new Response(JSON.stringify({error: 'Not found: ' + path}), {
      status: 404, headers: {'Content-Type': 'application/json', ...corsHeaders()},
    });
  }

  try {
    const r = await fetch(upstreamUrl, upstreamInit);
    const ct = r.headers.get('Content-Type') || 'application/json';
    const body = await r.arrayBuffer();
    return new Response(body, {
      status: r.status,
      headers: {'Content-Type': ct, ...corsHeaders()},
    });
  } catch (e) {
    return new Response(JSON.stringify({error: 'Upstream fetch failed: ' + e.message}), {
      status: 502, headers: {'Content-Type': 'application/json', ...corsHeaders()},
    });
  }
}

addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method === 'OPTIONS') {
    event.respondWith(new Response(null, {status: 204, headers: corsHeaders()}));
    return;
  }

  if (url.pathname === '/' || url.pathname === '') {
    event.respondWith(new Response(HTML_CONTENT, {
      headers: {'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'no-cache'},
    }));
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleProxy(request, url));
    return;
  }

  event.respondWith(new Response('Not found', {status: 404}));
});
