// Cloudflare Worker - AI生图 (pm-v1.1)
// pm-v1.1: pixmind.io GPT-Image-2 通道
//   - 账号通过 mailtm-validator 注册后导入 JSON
//   - 每日签到获取 330 credits
//   - LRU 轮流使用账号
//   - 登录签到在 Worker 后端完成（避免 CORS）
//
// 配置方式: 见前端设置面板 - 导入 JSON 账号列表
// 部署: ai-image.lishuhang.workers.dev

const UPSTREAM = 'https://pixmind.io';
const VERSION = 'pm-v1.1';
const CREDITS_PER_CHECKIN = 330;
const COST_PER_IMAGE = 30;  // gpt-image-2 cost
const CHECKIN_COST = 30;    // checkin costs 30 credits, gives 330 back

// ===================== HTML 前端 =====================
const HTML_CONTENT = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI生图 (pixmind)</title>
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
.modal{background:var(--bg-card);border-radius:var(--radius);padding:var(--space-lg);max-width:640px;width:90%;max-height:80vh;overflow-y:auto}
.modal h2{margin-bottom:var(--space-md)}
.modal .form-row{margin-bottom:var(--space-md)}
.modal .form-row label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px}
.token-help{font-size:12px;color:var(--text-muted);margin-top:4px;line-height:1.6}
.token-help code{background:var(--bg-secondary);padding:1px 4px;border-radius:3px;font-family:var(--mono);font-size:11px}
.quota-badge{font-size:12px;padding:4px 10px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-xs)}
.toast{position:fixed;top:60px;right:20px;padding:10px 18px;border-radius:var(--radius);font-size:13px;font-weight:500;z-index:200;animation:slideIn .3s ease;box-shadow:0 4px 12px rgba(0,0,0,.15);max-width:400px}
.toast.success{background:#2ecc71;color:#fff}
.toast.error{background:#e74c3c;color:#fff}
.toast.info{background:var(--accent);color:#fff}
@keyframes slideIn{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:translateX(0)}}
.account-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.account-table th,.account-table td{padding:6px 8px;border:1px solid var(--border);text-align:left}
.account-table th{background:var(--bg-secondary);font-size:11px;text-transform:uppercase}
@media(max-width:768px){
  #contentArea{flex-direction:column}
  #promptPanel{width:100%;border-right:none;border-bottom:1px solid var(--border);max-height:50vh}
}
</style>
</head>
<body>
<nav id="topNav">
  <div class="nav-left">
    <span class="title">AI生图</span>
    <span class="version-badge">pm-v1.1</span>
  </div>
  <div class="nav-right">
    <span id="quotaBadge" class="quota-badge">未配置账号</span>
    <button class="btn btn-ghost btn-sm" id="checkinBtn" title="为所有账号每日签到 (+330 credits)">🎁 每日签到</button>
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
      </select>

      <div class="section-title" style="margin-top:16px">比例</div>
      <div class="size-grid" id="sizeGrid">
        <button class="size-btn active" data-ratio="1:1">1:1 正方</button>
        <button class="size-btn" data-ratio="16:9">16:9 横</button>
        <button class="size-btn" data-ratio="9:16">9:16 竖</button>
        <button class="size-btn" data-ratio="4:3">4:3 横</button>
        <button class="size-btn" data-ratio="3:4">3:4 竖</button>
        <button class="size-btn" data-ratio="3:2">3:2 横</button>
      </div>

      <div class="section-title" style="margin-top:16px">清晰度</div>
      <select id="qualitySelect" class="select-field">
        <option value="1k" selected>1K (标准)</option>
        <option value="2k">2K (高清)</option>
        <option value="4k">4K (超清)</option>
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
    <h2>⚙ 设置 — Pixmind 账号</h2>
    <div class="form-row">
      <label>账号 JSON (从 mailtm-validator 导出后粘贴)</label>
      <textarea id="accountsTextarea" class="input-field" style="min-height:200px;font-family:var(--mono);font-size:11px" placeholder="粘贴 JSON 数组，格式:
[
  {"email":"xxx@mail.tm","password":"xxx","uid":"12345","token":"..."},
  ...
]
每个账号每日可签到获取 330 credits，gpt-image-2 每张消耗约 30 credits。"></textarea>
      <div class="token-help">
        <b>获取方法:</b> 在 <a href="https://mtm.lishuhang.workers.dev" target="blank">mailtm-validator</a> 注册 pixmind 账号后，导出 JSON 粘贴到这里。<br>
        <b>签到:</b> 点击「🎁 每日签到」为所有账号签到，每次 +330 credits（需消耗 30 credits 签到费）。<br>
        <b>轮流:</b> 系统自动选择最久未用的账号生成图片。<br>
        <b>余额:</b> 右上角显示当前账号余额。切换账号时自动更新。
      </div>
    </div>
    <div style="display:flex;gap:8px;justify-content:space-between;align-items:center">
      <div style="display:flex;gap:8px">
        <button class="btn btn-sm" id="exportAccountsBtn">导出 JSON</button>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn" id="settingsCancel">取消</button>
        <button class="btn btn-primary" id="settingsSave">保存</button>
      </div>
    </div>
    <div id="accountsPreview" style="margin-top:12px"></div>
  </div>
</div>

<script>
const VERSION = 'pm-v1.1';
const AUTH_HEADER = 'X-Pm-Token';
const CREDITS_PER_CHECKIN = 330;

const state = {
  accounts: [],  // [{email,password,uid,token,credits,lastCheckinDay,lastUsed,disabled,loginFailures}]
  tasks: [],
  currentDate: '',
};

function getTodayGMT8() {
  const now = new Date();
  const gmt8 = new Date(now.getTime() + (now.getTimezoneOffset() + 480) * 60000);
  return gmt8.toISOString().slice(0, 10);
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem('pm-state-v1') || '{}');
    if (saved.accounts) state.accounts = saved.accounts;
    if (saved.currentDate !== getTodayGMT8()) {
      state.accounts.forEach(a => { /* daily reset if needed */ });
      state.currentDate = getTodayGMT8();
    }
  } catch (e) { console.warn('loadState err', e); }
}

function saveState() {
  state.currentDate = getTodayGMT8();
  localStorage.setItem('pm-state-v1', JSON.stringify({
    accounts: state.accounts,
    currentDate: state.currentDate,
  }));
}

function getAvailableAccounts() {
  return state.accounts.filter(a => !a.disabled && a.credits > 0 && a.token);
}

// LRU: pick account with smallest lastUsed
function selectAccount() {
  const avail = getAvailableAccounts();
  if (!avail.length) return null;
  avail.sort((a, b) => (a.lastUsed || 0) - (b.lastUsed || 0));
  return avail[0];
}

function markAccountExhausted(email) {
  const a = state.accounts.find(x => x.email === email);
  if (a) {
    a.credits = 0;
    saveState();
    renderQuotaBadge();
  }
}

function renderQuotaBadge() {
  const total = state.accounts.length;
  const avail = getAvailableAccounts().length;
  const current = selectAccount();
  const el = document.getElementById('quotaBadge');
  if (total === 0) {
    el.textContent = '未配置账号';
    el.style.color = 'var(--red)';
    return;
  }
  const creditsText = current ? current.credits + ' credits' : '无可用';
  el.textContent = avail + '/' + total + ' 账号 | ' + creditsText;
  el.style.color = avail > 0 ? 'var(--green)' : 'var(--red)';
}

// ===================== Toast =====================
function toast(msg, type) {
  type = type || 'info';
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(function() { el.remove(); }, 3000);
}

// ===================== Settings Modal =====================
function showSettings() {
  const ta = document.getElementById('accountsTextarea');
  const exportable = state.accounts.map(function(a) {
    return { email: a.email, password: a.password, uid: a.uid, token: a.token };
  });
  ta.value = exportable.length ? JSON.stringify(exportable, null, 2) : '';
  document.getElementById('settingsModal').classList.add('show');
  renderAccountsPreview();
}
function hideSettings() {
  document.getElementById('settingsModal').classList.remove('show');
}
function saveSettings() {
  const ta = document.getElementById('accountsTextarea');
  const text = ta.value.trim();
  if (!text) {
    state.accounts = [];
    saveState(); renderQuotaBadge(); hideSettings();
    toast('已清空所有账号', 'info');
    return;
  }
  try {
    const arr = JSON.parse(text);
    if (!Array.isArray(arr)) throw new Error('必须是数组');
    const existing = new Map(state.accounts.map(function(a) { return [a.email, a]; }));
    state.accounts = arr.map(function(item) {
      const old = existing.get(item.email);
      return {
        email: item.email,
        password: item.password || '',
        uid: item.uid || '',
        token: item.token || '',
        credits: (old && old.credits) || 0,
        lastCheckinDay: (old && old.lastCheckinDay) || '',
        lastUsed: (old && old.lastUsed) || 0,
        disabled: (old && old.disabled) || false,
        loginFailures: (old && old.loginFailures) || 0,
      };
    });
    saveState(); renderQuotaBadge(); hideSettings();
    toast('已导入 ' + state.accounts.length + ' 个账号', 'success');
    // Auto-refresh all accounts quota
    refreshAllQuota();
  } catch(e) {
    toast('JSON 解析失败: ' + e.message, 'error');
  }
}

function exportAccounts() {
  const exportable = state.accounts.map(function(a) {
    return { email: a.email, password: a.password, uid: a.uid, token: a.token, credits: a.credits };
  });
  const json = JSON.stringify(exportable, null, 2);
  navigator.clipboard.writeText(json).then(function() {
    toast('JSON 已复制到剪贴板 (' + exportable.length + ' 个账号)', 'success');
  }).catch(function() { toast('复制失败', 'error'); });
}

function renderAccountsPreview() {
  const container = document.getElementById('accountsPreview');
  if (!state.accounts.length) { container.innerHTML = ''; return; }
  let html = '<table class="account-table"><tr><th>邮箱</th><th>UID</th><th>余额</th><th>今日签到</th><th>状态</th></tr>';
  state.accounts.forEach(function(a) {
    const today = getTodayGMT8();
    const checked = a.lastCheckinDay === today;
    html += '<tr>'
      + '<td style="font-family:var(--mono);font-size:11px">' + (a.email || '?') + '</td>'
      + '<td>' + (a.uid || '-') + '</td>'
      + '<td>' + (a.credits || 0) + '</td>'
      + '<td>' + (checked ? '✅' : '❌') + '</td>'
      + '<td>' + (a.disabled ? '❌ 禁用' : (a.token ? '✅ 正常' : '⚠ 无token')) + '</td>'
      + '</tr>';
  });
  html += '</table>';
  container.innerHTML = html;
}

// ===================== Account Operations (via Worker backend) =====================
async function loginAccount(i) {
  const a = state.accounts[i];
  if (!a || !a.email) return false;
  try {
    const r = await fetch('/api/account/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: a.email, password: a.password }),
    });
    const d = await r.json();
    if (d.ok && d.token) {
      a.token = d.token;
      a.uid = d.uid || a.uid;
      a.credits = d.credits || 0;
      a.loginFailures = 0;
      saveState();
      renderQuotaBadge();
      return true;
    } else {
      a.loginFailures = (a.loginFailures || 0) + 1;
      if (a.loginFailures >= 3) a.disabled = true;
      saveState();
      console.warn('login failed', a.email, d.error);
      return false;
    }
  } catch(e) {
    console.error('login err', a.email, e);
    return false;
  }
}

async function checkinAccount(i) {
  const a = state.accounts[i];
  if (!a || !a.token) return false;
  try {
    const r = await fetch('/api/account/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: a.token }),
    });
    const d = await r.json();
    if (d.ok) {
      a.credits = d.credits || a.credits;
      a.lastCheckinDay = getTodayGMT8();
      saveState();
      return true;
    } else {
      // Token may be expired, try re-login
      if (d.error && (d.error.includes('401') || d.error.includes('expired') || d.error.includes('unauthorized'))) {
        const logged = await loginAccount(i);
        if (logged) return checkinAccount(i); // retry
      }
      console.warn('checkin failed', a.email, d.error);
      return false;
    }
  } catch(e) {
    console.error('checkin err', a.email, e);
    return false;
  }
}

async function refreshQuota(i) {
  const a = state.accounts[i];
  if (!a || !a.token) return;
  try {
    const r = await fetch('/api/account/info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: a.token }),
    });
    const d = await r.json();
    if (d.ok) {
      a.credits = d.credits || 0;
      a.uid = d.uid || a.uid;
      a.token = d.token || a.token; // refresh token if updated
      a.disabled = false;
      saveState();
    } else if (d.error && (d.error.includes('401') || d.error.includes('expired'))) {
        // Try re-login
        const logged = await loginAccount(i);
      }
  } catch(e) { console.warn('refreshQuota err', e); }
}

async function refreshAllQuota() {
  toast('正在刷新所有账号余额...', 'info');
  for (let i = 0; i < state.accounts.length; i++) {
    if (state.accounts[i].token) {
      await refreshQuota(i);
    } else {
      await loginAccount(i);
    }
  }
  renderQuotaBadge();
  toast('余额刷新完成', 'success');
}

// ===================== Daily Checkin All =====================
async function dailyCheckinAll() {
  if (!state.accounts.length) {
    alert('请先配置账号'); showSettings(); return;
  }
  const btn = document.getElementById('checkinBtn');
  btn.disabled = true;
  btn.textContent = '🎁 签到中...';
  let ok = 0, fail = 0;
  for (let i = 0; i < state.accounts.length; i++) {
    const a = state.accounts[i];
    // Ensure logged in
    if (!a.token) {
      const logged = await loginAccount(i);
      if (!logged) { fail++; continue; }
    }
    // Skip if already checked in today
    if (a.lastCheckinDay === getTodayGMT8()) { ok++; continue; }
    const result = await checkinAccount(i);
    if (result) ok++; else fail++;
  }
  btn.disabled = false;
  btn.textContent = '🎁 每日签到';
  renderQuotaBadge();
  toast('签到完成: ' + ok + ' 成功, ' + fail + ' 失败', ok > 0 ? 'success' : 'error');
}

// ===================== Auto check new day (v14 style) =====================
function checkNewDay() {
  const today = getTodayGMT8();
  if (state.lastAutoDay === today) return;
  state.lastAutoDay = today;
  // Auto checkin all accounts
  dailyCheckinAll();
}

// ===================== Ensure Account Before Generate =====================
async function ensureAccount() {
  let a = selectAccount();
  if (a) return a;
  // No available account - try to refresh all and re-login
  await refreshAllQuota();
  a = selectAccount();
  if (a) return a;
  // Still nothing
  toast('所有账号余额不足或未登录，请点击签到或检查设置', 'error');
  return null;
}

// ===================== Tasks =====================
function genClientTaskId() {
  return 'pm-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
}

function addTask(task) {
  state.tasks.unshift(task);
  if (state.tasks.length > 50) state.tasks.pop();
  renderTasks();
}

function updateTask(id, updates) {
  const t = state.tasks.find(function(x) { return x.id === id; });
  if (t) Object.assign(t, updates);
  renderTasks();
}

function renderTasks() {
  const list = document.getElementById('taskList');
  if (!state.tasks.length) {
    list.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px">还没有任务。输入提示词后点击"生成图片"。<br>首次使用请先点右上角 ⚙ 设置导入账号 JSON，然后点「🎁 每日签到」。</div>';
    return;
  }
  list.innerHTML = state.tasks.map(function(t) {
    const statusClass = t.status || 'queued';
    const statusText = {queued:'排队中', running:(t.progressText || '生成中'), success:'完成', error:'失败'}[t.status] || t.status;
    const imageHtml = t.imageUrl
      ? '<a href="' + t.imageUrl + '" target="_blank"><img src="' + t.imageUrl + '" class="task-image" /></a>'
      : '';
    const errorHtml = t.error ? '<div style="color:var(--red);font-size:12px">' + t.error + '</div>' : '';
    return '<div class="task-card ' + (t.status === 'error' ? 'error' : '') + '">'
      + '<div style="display:flex;justify-content:space-between;align-items:center">'
      + '<span class="task-status ' + statusClass + '">' + statusText + '</span>'
      + '<span style="font-size:11px;color:var(--text-muted)">' + (t.accountLabel || '') + '</span>'
      + '</div>'
      + '<div class="task-prompt">' + (t.prompt || '') + '</div>'
      + (t.status === 'running' ? '<div class="progress-bar"><div class="progress-fill" style="width:' + (t.progress || 0) + '%"></div></div>' : '')
      + imageHtml + errorHtml
      + '</div>';
  }).join('');
}

// ===================== Generate =====================
async function generate() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) { toast('请输入提示词', 'error'); return; }
  const model = document.getElementById('modelSelect').value;
  const ratioBtn = document.querySelector('.size-btn.active');
  const ratio = ratioBtn ? ratioBtn.dataset.ratio : '1:1';
  const quality = document.getElementById('qualitySelect').value;

  const account = await ensureAccount();
  if (!account) return;

  // Mark as used (LRU)
  account.lastUsed = Date.now();
  saveState();

  const taskId = genClientTaskId();
  addTask({
    id: taskId, prompt: prompt, status: 'queued', accountLabel: account.email.split('@')[0],
    progress: 0, progressText: '排队中',
  });

  try {
    updateTask(taskId, { status: 'running', progress: 10, progressText: '提交生成任务...' });
    const genRes = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        model: model,
        aspectRatio: ratio,
        quality: quality,
        token: account.token,
        email: account.email,
      }),
    });
    const genData = await genRes.json();
    if (!genData.ok) {
      updateTask(taskId, { status: 'error', error: genData.error || '生成失败' });
      if (genData.exhausted) markAccountExhausted(account.email);
      return;
    }

    const upstreamTaskId = genData.taskId;
    updateTask(taskId, { status: 'running', progress: 30, progressText: '生成中...' });

    // Poll for result
    for (let poll = 0; poll < 60; poll++) {
      await new Promise(function(r) { setTimeout(r, 3000); });
      const statusRes = await fetch('/api/task-status?taskId=' + upstreamTaskId + '&token=' + encodeURIComponent(account.token));
      const statusData = await statusRes.json();
      if (!statusData.ok) {
        updateTask(taskId, { status: 'error', error: statusData.error || '查询失败' });
        return;
      }
      const st = statusData.status;
      if (st === 'success' || st === 'completed' || st === 'succeeded') {
        const imageUrl = statusData.imageUrl || statusData.data?.imageUrl || '';
        // Deduct credits estimate
        account.credits = Math.max(0, (account.credits || 0) - 30);
        account.lastUsed = Date.now();
        saveState();
        renderQuotaBadge();
        updateTask(taskId, {
          status: 'success', progress: 100, progressText: '完成',
          imageUrl: imageUrl, accountLabel: account.email.split('@')[0] + ' (剩余 ' + account.credits + ')',
        });
        return;
      } else if (st === 'error' || st === 'failed') {
        updateTask(taskId, { status: 'error', error: statusData.error || '生成失败' });
        return;
      }
      // Still running
      const pct = Math.min(30 + poll * 2, 90);
      updateTask(taskId, { progress: pct, progressText: '生成中... (' + (poll + 1) + 's)' });
    }
    updateTask(taskId, { status: 'error', error: '超时 (3分钟)' });
  } catch(e) {
    updateTask(taskId, { status: 'error', error: e.message });
  }
}

// ===================== Init =====================
function init() {
  loadState();
  renderQuotaBadge();
  renderTasks();

  // Size buttons
  document.querySelectorAll('.size-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.size-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
    });
  });

  document.getElementById('generateBtn').addEventListener('click', generate);
  document.getElementById('checkinBtn').addEventListener('click', dailyCheckinAll);
  document.getElementById('settingsBtn').addEventListener('click', showSettings);
  document.getElementById('settingsCancel').addEventListener('click', hideSettings);
  document.getElementById('settingsSave').addEventListener('click', saveSettings);
  document.getElementById('exportAccountsBtn').addEventListener('click', exportAccounts);
  document.getElementById('settingsModal').addEventListener('click', function(ev) {
    if (ev.target === ev.currentTarget) hideSettings();
  });

  // Auto check new day every 60s
  setTimeout(function() { checkNewDay(); }, 5000);
  setInterval(checkNewDay, 60000);

  // If has accounts, auto refresh quota
  if (state.accounts.length > 0) {
    setTimeout(refreshAllQuota, 2000);
  }
}

init();
</script>
</body>
</html>`;

// ===================== Worker Backend =====================
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

async function pixmindFetch(path, method, body, token) {
  const hdrs = {
    'User-Agent': UA,
    'Accept': 'application/json',
    'Origin': 'https://pixmind.io',
    'Referer': 'https://pixmind.io/',
  };
  if (token) hdrs['Authorization'] = 'Bearer ' + token;
  if (body) {
    hdrs['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  const res = await fetch(UPSTREAM + path, {
    method: method || 'GET',
    headers: hdrs,
    body: body || undefined,
  });
  let data;
  try { data = await res.json(); } catch(e) { data = { raw: await res.text().catch(() => '') }; }
  return { status: res.status, data: data, headers: res.headers };
}

function jsonResponse(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}

function findToken(d, depth) {
  depth = depth || 0;
  if (depth > 5 || !d) return null;
  if (typeof d === 'string' && d.length > 50) return d;
  if (typeof d === 'object') {
    for (var k of ['token', 'access_token', 'accessToken']) {
      if (d[k] && typeof d[k] === 'string' && d[k].length > 20) return d[k];
    }
    for (var v of Object.values(d)) {
      var t = findToken(v, depth + 1);
      if (t) return t;
    }
  }
  return null;
}

function findVal(d, key, depth) {
  depth = depth || 0;
  if (depth > 5 || !d) return null;
  if (typeof d === 'object' && !Array.isArray(d) && d[key] !== undefined) return d[key];
  if (Array.isArray(d)) { for (var item of d) { var r = findVal(item, key, depth+1); if (r !== undefined && r !== null) return r; } }
  if (typeof d === 'object') { for (var v of Object.values(d)) { var r = findVal(v, key, depth+1); if (r !== undefined && r !== null) return r; } }
  return null;
}

// Handle /api/account/login
async function handleLogin(request) {
  try {
    const { email, password } = await request.json();
    if (!email || !password) return jsonResponse({ ok: false, error: 'missing email or password' }, 400);

    const r = await pixmindFetch('/api/user/login/emailPassword', 'POST', { email: email, password: password });
    if (r.status !== 200) {
      return jsonResponse({ ok: false, error: 'pixmind login ' + r.status + ': ' + JSON.stringify(r.data).slice(0, 300) });
    }

    const token = findToken(r.data);
    if (!token) {
      return jsonResponse({ ok: false, error: '登录响应中未找到 token: ' + JSON.stringify(r.data).slice(0, 300) });
    }

    // Get user info
    const info = await pixmindFetch('/api/user/info', 'GET', null, token);
    const uid = findVal(info.data, 'id') || findVal(info.data, 'uid');
    const credits = findVal(info.data, 'credits') || findVal(info.data, 'balance') || 0;

    return jsonResponse({ ok: true, token: token, uid: uid, credits: credits, email: email });
  } catch(e) {
    return jsonResponse({ ok: false, error: e.message });
  }
}

// Handle /api/account/checkin
async function handleCheckin(request) {
  try {
    const { token } = await request.json();
    if (!token) return jsonResponse({ ok: false, error: 'missing token' }, 400);

    const r = await pixmindFetch('/api/user/checkin', 'POST', {}, token);
    if (r.status !== 200) {
      // Check for various error patterns
      const bodyStr = JSON.stringify(r.data).toLowerCase();
      if (bodyStr.includes('already') || bodyStr.includes('signed') || bodyStr.includes('已签')) {
        // Already checked in, get current credits
        const info = await pixmindFetch('/api/user/info', 'GET', null, token);
        const credits = findVal(info.data, 'credits') || findVal(info.data, 'balance') || 0;
        return jsonResponse({ ok: true, credits: credits, note: 'already checked in' });
      }
      return jsonResponse({ ok: false, error: 'checkin ' + r.status + ': ' + JSON.stringify(r.data).slice(0, 300) });
    }

    // Get updated credits
    const info = await pixmindFetch('/api/user/info', 'GET', null, token);
    const credits = findVal(info.data, 'credits') || findVal(info.data, 'balance') || 0;
    return jsonResponse({ ok: true, credits: credits });
  } catch(e) {
    return jsonResponse({ ok: false, error: e.message });
  }
}

// Handle /api/account/info
async function handleInfo(request) {
  try {
    const { token } = await request.json();
    if (!token) return jsonResponse({ ok: false, error: 'missing token' }, 400);

    const r = await pixmindFetch('/api/user/info', 'GET', null, token);
    if (r.status !== 200) {
      return jsonResponse({ ok: false, error: 'info ' + r.status + ': ' + JSON.stringify(r.data).slice(0, 300) });
    }

    const uid = findVal(r.data, 'id') || findVal(r.data, 'uid');
    const credits = findVal(r.data, 'credits') || findVal(r.data, 'balance') || 0;
    return jsonResponse({ ok: true, uid: uid, credits: credits });
  } catch(e) {
    return jsonResponse({ ok: false, error: e.message });
  }
}

// Handle /api/generate
async function handleGenerate(request) {
  try {
    const { prompt, model, aspectRatio, quality, token, email } = await request.json();
    if (!prompt || !token) return jsonResponse({ ok: false, error: 'missing prompt or token' }, 400);

    const r = await pixmindFetch('/api/ai/text-to-image', 'POST', {
      prompt: prompt,
      model: model || 'gpt-image-2',
      aspectRatio: aspectRatio || '1:1',
      quality: quality || '1k',
    }, token);

    if (r.status !== 200) {
      const errStr = JSON.stringify(r.data);
      const exhausted = errStr.includes('insufficient') || errStr.includes('余额') || errStr.includes('credits');
      return jsonResponse({ ok: false, error: 'generate ' + r.status + ': ' + errStr.slice(0, 300), exhausted: exhausted });
    }

    const taskId = findVal(r.data, 'taskId') || findVal(r.data, 'task_id');
    if (!taskId) {
      return jsonResponse({ ok: false, error: 'no taskId in response: ' + JSON.stringify(r.data).slice(0, 300) });
    }

    return jsonResponse({ ok: true, taskId: taskId });
  } catch(e) {
    return jsonResponse({ ok: false, error: e.message });
  }
}

// Handle /api/task-status
async function handleTaskStatus(request) {
  const url = new URL(request.url);
  const taskId = url.searchParams.get('taskId');
  const token = url.searchParams.get('token');
  if (!taskId || !token) return jsonResponse({ ok: false, error: 'missing taskId or token' }, 400);

  try {
    const r = await pixmindFetch('/api/ai/image-generate/task-status?taskId=' + encodeURIComponent(taskId), 'GET', null, token);
    if (r.status !== 200) {
      return jsonResponse({ ok: false, error: 'status ' + r.status + ': ' + JSON.stringify(r.data).slice(0, 300) });
    }

    const status = findVal(r.data, 'status') || findVal(r.data, 'state');
    let imageUrl = findVal(r.data, 'imageUrl') || findVal(r.data, 'image_url') || '';
    // Proxy image through our worker if needed
    if (imageUrl && imageUrl.startsWith('http')) {
      imageUrl = '/api/image-proxy?url=' + encodeURIComponent(imageUrl);
    }

    return jsonResponse({
      ok: true,
      status: status,
      imageUrl: imageUrl,
      raw: r.data,
    });
  } catch(e) {
    return jsonResponse({ ok: false, error: e.message });
  }
}

// Handle /api/image-proxy
async function handleImageProxy(request) {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get('url');
  if (!targetUrl) return new Response('missing url', { status: 400 });

  try {
    const res = await fetch(targetUrl, {
      headers: { 'User-Agent': UA, 'Referer': 'https://pixmind.io/' }
    });
    const ct = res.headers.get('content-type') || 'image/png';
    return new Response(res.body, {
      headers: {
        'Content-Type': ct,
        'Cache-Control': 'public, max-age=86400',
        'Access-Control-Allow-Origin': '*',
      }
    });
  } catch(e) {
    return new Response('proxy error: ' + e.message, { status: 502 });
  }
}

// ===================== Router =====================
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Pm-Token',
        }
      });
    }

    if (path === '/' || path === '/index.html') {
      return new Response(HTML_CONTENT, { headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
    }

    if (path === '/api/account/login' && request.method === 'POST') return handleLogin(request);
    if (path === '/api/account/checkin' && request.method === 'POST') return handleCheckin(request);
    if (path === '/api/account/info' && request.method === 'POST') return handleInfo(request);
    if (path === '/api/generate' && request.method === 'POST') return handleGenerate(request);
    if (path === '/api/task-status' && request.method === 'GET') return handleTaskStatus(request);
    if (path === '/api/image-proxy' && request.method === 'GET') return handleImageProxy(request);

    return new Response('Not Found', { status: 404 });
  }
};
