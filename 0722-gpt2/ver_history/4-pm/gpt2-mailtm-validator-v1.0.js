// Cloudflare Worker - Mail.tm 邮箱管理 (mailtm-validator-v1.0)
// 辅助用户快速注册 pixmind.io 账号
//   - 管理 mail.tm 一次性邮箱
//   - 代收邮件验证码（标题中含6位数字）
//   - 后台登录 pixmind 获取 UID
//   - 导出已注册账号 JSON 供 pm Worker 导入
//
// 部署: mtm.lishuhang.workers.dev

const VERSION = 'mailtm-validator-v1.0';
const MAILTM_API = 'https://api.mail.tm';
const PIXMIND_API = 'https://pixmind.io';

// ===================== HTML 前端 =====================
const HTML_CONTENT = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pixmind 注册助手 - Mail.tm 邮箱管理</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --accent:#4361ee;--accent-hover:#3a56d4;--accent-light:rgba(67,97,238,.10);
  --bg:#f8f9fa;--bg-card:#fff;--bg-secondary:#f1f3f5;--bg-hover:#e9ecef;
  --text:#212529;--text-secondary:#6c757d;--text-muted:#adb5bd;
  --border:#dee2e6;--border-medium:#ced4da;
  --radius:8px;--radius-xs:4px;
  --space-xs:4px;--space-sm:8px;--space-md:12px;--space-lg:20px;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans SC",sans-serif;
  --mono:'SF Mono',Consolas,Monaco,monospace;
  --green:#2ecc71;--red:#e74c3c;--yellow:#f39c12;--blue:#3498db;
}
html,body{height:100%;font-family:var(--font);background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:7px 14px;font-size:13px;font-weight:600;border-radius:var(--radius);border:1px solid var(--border);background:var(--bg-card);color:var(--text);cursor:pointer;font-family:var(--font);white-space:nowrap;transition:all .15s}
.btn:hover:not(:disabled){background:var(--bg-hover);border-color:var(--border-medium)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--accent-hover)}
.btn-success{background:var(--green);border-color:var(--green);color:#fff}
.btn-sm{padding:4px 10px;font-size:12px;border-radius:var(--radius-xs)}
.btn-danger{background:var(--red);border-color:var(--red);color:#fff}

#topNav{background:var(--bg-card);height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 var(--space-lg);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50}
.nav-left{display:flex;align-items:center;gap:10px}
.nav-left .title{font-size:18px;font-weight:700}
.version-badge{font-size:11px;color:var(--text-muted);font-family:var(--mono);background:var(--bg-secondary);padding:2px 8px;border-radius:10px}
.nav-right{display:flex;align-items:center;gap:8px}

.container{max-width:1100px;margin:0 auto;padding:var(--space-lg)}

.stats-bar{display:flex;gap:16px;margin-bottom:var(--space-md);padding:var(--space-sm) var(--space-md);background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius)}
.stat-item{font-size:13px;color:var(--text-secondary)}
.stat-item span{font-weight:700;color:var(--text);margin-left:4px}
.stat-item .green{color:var(--green)}
.stat-item .red{color:var(--red)}

.action-bar{display:flex;gap:8px;margin-bottom:var(--space-md);flex-wrap:wrap}

.table-wrap{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:13px}
thead{background:var(--bg-secondary)}
th{padding:10px 12px;text-align:left;font-weight:600;color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover{background:var(--bg-secondary)}

.email-cell{font-family:var(--mono);font-size:12px;cursor:pointer;color:var(--accent);max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.email-cell:hover{text-decoration:underline}
.pwd-cell{font-family:var(--mono);font-size:12px;color:var(--text-muted);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.subject-cell{cursor:pointer;color:var(--blue);max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.subject-cell:hover{text-decoration:underline}
.subject-cell.empty{color:var(--text-muted);cursor:default}
.subject-cell.empty:hover{text-decoration:none}
.uid-cell{font-family:var(--mono);font-size:12px;color:var(--green);font-weight:600}
.uid-cell.pending{color:var(--text-muted)}
.status-badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600}
.status-badge.registered{background:rgba(46,204,113,.12);color:var(--green)}
.status-badge.unregistered{background:rgba(231,76,60,.12);color:var(--red)}

.toast{position:fixed;top:60px;right:20px;padding:10px 18px;border-radius:var(--radius);font-size:13px;font-weight:500;z-index:200;animation:slideIn .3s ease;box-shadow:0 4px 12px rgba(0,0,0,.15);max-width:400px}
.toast.success{background:#2ecc71;color:#fff}
.toast.error{background:#e74c3c;color:#fff}
.toast.info{background:var(--blue);color:#fff}
@keyframes slideIn{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:translateX(0)}}

.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:100}
.modal-backdrop.show{display:flex}
.modal{background:var(--bg-card);border-radius:var(--radius);padding:var(--space-lg);max-width:700px;width:90%;max-height:80vh;overflow-y:auto}
.modal h2{margin-bottom:var(--space-md);font-size:18px}
.modal h3{margin:var(--space-md) 0 var(--space-sm);font-size:15px}
.modal pre{background:#1e1e2e;color:#cdd6f4;padding:var(--space-md);border-radius:var(--radius);font-family:var(--mono);font-size:11px;overflow-x:auto;max-height:400px;overflow-y:auto;line-height:1.5}
.modal .form-row{margin-bottom:var(--space-md)}
.modal .form-row label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:600}
.modal textarea{width:100%;min-height:120px;padding:8px;border:1px solid var(--border);border-radius:var(--radius);font-family:var(--mono);font-size:12px;resize:vertical}
.modal textarea:focus{outline:none;border-color:var(--accent)}
.modal-footer{display:flex;gap:8px;justify-content:flex-end;margin-top:var(--space-md)}

.auto-refresh-bar{display:flex;align-items:center;gap:8px;padding:6px 12px;background:rgba(67,97,238,.06);border:1px solid rgba(67,97,238,.15);border-radius:var(--radius);margin-bottom:var(--space-md);font-size:12px;color:var(--text-secondary)}
.auto-refresh-bar label{cursor:pointer}

.empty-state{text-align:center;padding:60px 20px;color:var(--text-muted)}
.empty-state p{margin-bottom:12px}

@media(max-width:768px){
  .container{padding:var(--space-sm)}
  table{font-size:11px}
  th,td{padding:6px 8px}
  .action-bar{flex-direction:column}
  .btn{width:100%}
}
</style>
</head>
<body>
<nav id="topNav">
  <div class="nav-left">
    <span class="title">Pixmind 注册助手</span>
    <span class="version-badge">` + VERSION + `</span>
  </div>
  <div class="nav-right">
    <button class="btn btn-sm" id="settingsBtn" title="导出/导入设置">⚙ 设置</button>
  </div>
</nav>

<div class="container">
  <div class="stats-bar" id="statsBar">
    <div class="stat-item">邮箱: <span id="statTotal">0</span></div>
    <div class="stat-item">已注册: <span id="statRegistered" class="green">0</span></div>
    <div class="stat-item">待注册: <span id="statUnregistered" class="red">0</span></div>
  </div>

  <div class="auto-refresh-bar">
    <label><input type="checkbox" id="autoRefreshCheck" checked> 自动刷新收件箱（每10秒）</label>
    <span id="refreshStatus"></span>
  </div>

  <div class="action-bar">
    <button class="btn btn-primary" id="createEmailBtn">+ 申请新邮箱</button>
    <button class="btn" id="refreshAllBtn">刷新全部收件箱</button>
    <button class="btn" id="exportJsonBtn">导出已注册 JSON</button>
    <button class="btn btn-danger btn-sm" id="clearAllBtn">清空全部</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>邮箱地址 (点击复制)</th>
          <th>邮箱密码</th>
          <th>最近邮件标题 (点击查看)</th>
          <th>注册状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody id="emailTableBody">
      </tbody>
    </table>
    <div id="emptyState" class="empty-state">
      <p>暂无邮箱，点击「申请新邮箱」开始</p>
    </div>
  </div>
</div>

<!-- Settings Modal -->
<div id="settingsModal" class="modal-backdrop">
  <div class="modal">
    <h2>设置</h2>
    <div class="form-row">
      <label>导入已注册账号 JSON</label>
      <textarea id="importTextarea" placeholder='粘贴从其他地方导出的 JSON...'></textarea>
    </div>
    <div class="form-row">
      <label>导出已注册账号 JSON (含 email, password, uid, token)</label>
      <pre id="exportPreview" style="min-height:80px">点击下方按钮生成</pre>
    </div>
    <div class="modal-footer">
      <button class="btn" id="importBtn">导入</button>
      <button class="btn btn-primary" id="genExportBtn">生成导出 JSON</button>
      <button class="btn" id="copyExportBtn">复制 JSON</button>
      <button class="btn" id="closeSettingsBtn">关闭</button>
    </div>
  </div>
</div>

<script>
const VERSION = '` + VERSION + `';
const STORAGE_KEY = 'mailtm-pm-accounts-v1';

// state.emails = [{email, password, mailtmToken, registered, uid, token, lastSubject, lastSubjectCode, registeredAt, createdAt}]
const state = {
  emails: [],
  autoRefresh: true,
  refreshTimer: null,
};

// ===================== State =====================
function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    if (Array.isArray(saved)) state.emails = saved;
  } catch(e) { console.warn('loadState err', e); }
  const ar = localStorage.getItem('mailtm-auto-refresh');
  if (ar !== null) state.autoRefresh = ar === 'true';
  document.getElementById('autoRefreshCheck').checked = state.autoRefresh;
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.emails));
  localStorage.setItem('mailtm-auto-refresh', String(state.autoRefresh));
}

// ===================== Toast =====================
function toast(msg, type='info') {
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ===================== Render =====================
function render() {
  const tbody = document.getElementById('emailTableBody');
  const empty = document.getElementById('emptyState');

  if (!state.emails.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
  } else {
    empty.style.display = 'none';
    tbody.innerHTML = state.emails.map((e, i) => {
      const statusHtml = e.registered
        ? '<span class="status-badge registered">UID: ' + (e.uid || '?') + '</span>'
        : '<button class="btn btn-sm" onclick="markRegistered(' + i + ')" title="点击后台登录 pixmind 获取 UID">已注册</button>';
      const subjectHtml = e.lastSubject
        ? '<span class="subject-cell" onclick="openInbox(' + i + ')" title="点击在新窗口查看收件箱">' + escHtml(e.lastSubject) + (e.lastSubjectCode ? ' [' + e.lastSubjectCode + ']' : '') + '</span>'
        : '<span class="subject-cell empty" title="暂无邮件">等待收件...</span>';
      const actionsHtml = e.registered
        ? '<button class="btn btn-sm" onclick="copyPassword(' + i + ')">复制密码</button>'
        : '<button class="btn btn-sm" onclick="copyPassword(' + i + ')">复制密码</button> <button class="btn btn-sm btn-danger" onclick="removeEmail(' + i + ')">删除</button>';
      return '<tr>'
        + '<td>' + (i+1) + '</td>'
        + '<td class="email-cell" onclick="copyEmail(' + i + ')" title="点击复制邮箱地址">' + escHtml(e.email) + '</td>'
        + '<td class="pwd-cell" title="' + escHtml(e.password) + '">' + escHtml(e.password.slice(0,4)) + '****</td>'
        + '<td>' + subjectHtml + '</td>'
        + '<td class="uid-cell ' + (e.registered ? '' : 'pending') + '">' + statusHtml + '</td>'
        + '<td>' + actionsHtml + '</td>'
        + '</tr>';
    }).join('');
  }

  // Stats
  const total = state.emails.length;
  const registered = state.emails.filter(e => e.registered).length;
  document.getElementById('statTotal').textContent = total;
  document.getElementById('statRegistered').textContent = registered;
  document.getElementById('statUnregistered').textContent = total - registered;
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ===================== Mail.tm API (proxied through worker) =====================
async function mailtmApi(path, method='GET', body=null, token=null) {
  const hdrs = { 'Accept': 'application/json' };
  if (token) hdrs['Authorization'] = 'Bearer ' + token;
  if (body) {
    hdrs['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  const r = await fetch('/api/mailtm' + path, { method, headers: hdrs, body });
  if (!r.ok) {
    const errText = await r.text().catch(() => '');
    throw new Error('Mail.tm API ' + r.status + ': ' + errText.slice(0,200));
  }
  return r.json();
}

// ===================== Create Email =====================
async function createEmail() {
  const btn = document.getElementById('createEmailBtn');
  btn.disabled = true;
  btn.textContent = '申请中...';
  try {
    const data = await mailtmApi('/create', 'POST');
    const entry = {
      email: data.email,
      password: data.password,
      mailtmToken: data.token,
      registered: false,
      uid: null,
      token: null,
      lastSubject: null,
      lastSubjectCode: null,
      registeredAt: null,
      createdAt: Date.now(),
    };
    state.emails.push(entry);
    saveState();
    render();
    toast('邮箱已创建: ' + data.email, 'success');
    // Auto-copy email
    try { navigator.clipboard.writeText(data.email); toast('邮箱地址已复制到剪贴板', 'info'); } catch(e) {}
  } catch(e) {
    toast('创建失败: ' + e.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = '+ 申请新邮箱';
}

// ===================== Refresh Inbox =====================
async function refreshInbox(index) {
  const e = state.emails[index];
  if (!e || !e.mailtmToken) return null;
  try {
    const data = await mailtmApi('/inbox', 'POST', { token: e.mailtmToken });
    if (data.messages && data.messages.length > 0) {
      const latest = data.messages[0];
      e.lastSubject = latest.subject || latest.intro || '(无标题)';
      // Extract 6-digit code from subject
      const codeMatch = e.lastSubject.match(/\b(\d{6})\b/);
      e.lastSubjectCode = codeMatch ? codeMatch[1] : null;
      saveState();
      render();
      return { subject: e.lastSubject, code: e.lastSubjectCode };
    }
  } catch(err) {
    console.warn('refreshInbox err', index, err.message);
  }
  return null;
}

async function refreshAllInboxes() {
  const btn = document.getElementById('refreshAllBtn');
  btn.disabled = true;
  btn.textContent = '刷新中...';
  document.getElementById('refreshStatus').textContent = '正在刷新...';
  let newMails = 0;
  for (let i = 0; i < state.emails.length; i++) {
    const result = await refreshInbox(i);
    if (result && result.code) newMails++;
  }
  btn.disabled = false;
  btn.textContent = '刷新全部收件箱';
  document.getElementById('refreshStatus').textContent = newMails > 0 ? '发现 ' + newMails + ' 封含验证码的邮件' : '无新邮件';
  setTimeout(() => { document.getElementById('refreshStatus').textContent = ''; }, 5000);
}

// ===================== Mark Registered =====================
async function markRegistered(index) {
  const e = state.emails[index];
  if (!e || e.registered) return;
  // Try to login to pixmind to get UID and token
  toast('正在登录 pixmind 获取 UID: ' + e.email, 'info');
  try {
    const r = await fetch('/api/pixmind/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: e.email, password: e.password }),
    });
    const data = await r.json();
    if (data.ok && data.uid) {
      e.registered = true;
      e.uid = String(data.uid);
      e.token = data.token || null;
      e.registeredAt = Date.now();
      saveState();
      render();
      toast('登录成功! UID: ' + data.uid + ', Credits: ' + (data.credits || '?'), 'success');
    } else {
      toast('登录失败: ' + (data.error || '未知错误') + '。请在浏览器中手动完成注册后重试。', 'error');
    }
  } catch(err) {
    toast('登录请求失败: ' + err.message, 'error');
  }
}

// ===================== Actions =====================
function copyEmail(i) {
  const e = state.emails[i];
  if (!e) return;
  navigator.clipboard.writeText(e.email).then(() => toast('已复制: ' + e.email, 'info')).catch(() => toast('复制失败', 'error'));
}

function copyPassword(i) {
  const e = state.emails[i];
  if (!e) return;
  navigator.clipboard.writeText(e.password).then(() => toast('密码已复制', 'info')).catch(() => toast('复制失败', 'error'));
}

function openInbox(i) {
  const e = state.emails[i];
  if (!e) return;
  // Open mail.tm web interface - user logs in with email/password to read mail
  window.open('https://mail.tm/', '_blank');
  toast('在 mail.tm 登录: ' + e.email + ' / ' + e.password, 'info');
}

function removeEmail(i) {
  if (!confirm('确定删除 ' + state.emails[i].email + '?')) return;
  state.emails.splice(i, 1);
  saveState();
  render();
  toast('已删除', 'info');
}

function clearAll() {
  if (!confirm('确定清空所有邮箱记录?')) return;
  state.emails = [];
  saveState();
  render();
  toast('已清空', 'info');
}

// ===================== Settings / Export / Import =====================
function showSettings() {
  document.getElementById('settingsModal').classList.add('show');
  updateExportPreview();
}

function hideSettings() {
  document.getElementById('settingsModal').classList.remove('show');
}

function getExportJson() {
  return state.emails
    .filter(e => e.registered)
    .map(e => ({
      email: e.email,
      password: e.password,
      uid: e.uid,
      token: e.token,
      registeredAt: e.registeredAt,
    }));
}

function updateExportPreview() {
  const json = getExportJson();
  document.getElementById('exportPreview').textContent = json.length
    ? JSON.stringify(json, null, 2)
    : '(暂无已注册账号)';
}

function copyExportJson() {
  const json = getExportJson();
  if (!json.length) { toast('暂无已注册账号', 'error'); return; }
  navigator.clipboard.writeText(JSON.stringify(json, null, 2))
    .then(() => toast('JSON 已复制到剪贴板 (' + json.length + ' 个账号)', 'success'))
    .catch(() => toast('复制失败', 'error'));
}

function importAccounts() {
  const text = document.getElementById('importTextarea').value.trim();
  if (!text) { toast('请粘贴 JSON', 'error'); return; }
  try {
    const arr = JSON.parse(text);
    if (!Array.isArray(arr)) throw new Error('必须是数组');
    let imported = 0;
    for (const item of arr) {
      if (!item.email || !item.password) continue;
      // Check duplicate
      if (state.emails.some(e => e.email === item.email)) continue;
      state.emails.push({
        email: item.email,
        password: item.password,
        mailtmToken: null,
        registered: !!item.uid,
        uid: item.uid || null,
        token: item.token || null,
        lastSubject: null,
        lastSubjectCode: null,
        registeredAt: item.registeredAt || null,
        createdAt: Date.now(),
      });
      imported++;
    }
    saveState();
    render();
    updateExportPreview();
    document.getElementById('importTextarea').value = '';
    toast('导入 ' + imported + ' 个账号', 'success');
  } catch(e) {
    toast('JSON 解析失败: ' + e.message, 'error');
  }
}

// ===================== Auto Refresh =====================
function startAutoRefresh() {
  stopAutoRefresh();
  if (!state.autoRefresh) return;
  state.refreshTimer = setInterval(async () => {
    // Only refresh unregistered emails
    const unregistered = state.emails
      .map((e, i) => ({ e, i }))
      .filter(x => !x.e.registered);
    for (const { e, i } of unregistered) {
      const result = await refreshInbox(i);
      if (result && result.code) {
        toast('收到验证码: ' + e.email + ' -> ' + result.code, 'success');
      }
    }
  }, 10000);
}

function stopAutoRefresh() {
  if (state.refreshTimer) { clearInterval(state.refreshTimer); state.refreshTimer = null; }
}

// ===================== Init =====================
function init() {
  loadState();
  render();

  document.getElementById('createEmailBtn').addEventListener('click', createEmail);
  document.getElementById('refreshAllBtn').addEventListener('click', refreshAllInboxes);
  document.getElementById('exportJsonBtn').addEventListener('click', () => { showSettings(); updateExportPreview(); });
  document.getElementById('clearAllBtn').addEventListener('click', clearAll);
  document.getElementById('settingsBtn').addEventListener('click', showSettings);
  document.getElementById('closeSettingsBtn').addEventListener('click', hideSettings);
  document.getElementById('genExportBtn').addEventListener('click', updateExportPreview);
  document.getElementById('copyExportBtn').addEventListener('click', copyExportJson);
  document.getElementById('importBtn').addEventListener('click', importAccounts);
  document.getElementById('autoRefreshCheck').addEventListener('change', (ev) => {
    state.autoRefresh = ev.target.checked;
    localStorage.setItem('mailtm-auto-refresh', String(state.autoRefresh));
    if (state.autoRefresh) startAutoRefresh(); else stopAutoRefresh();
  });

  // Close modal on backdrop click
  document.getElementById('settingsModal').addEventListener('click', (ev) => {
    if (ev.target === ev.currentTarget) hideSettings();
  });

  startAutoRefresh();
}

init();
</script>
</body>
</html>`;

// ===================== Worker 后端 =====================

async function handleMailtmCreate(request) {
  // 1. Get available domain
  const domainRes = await fetch(MAILTM_API + '/domains', { headers: { 'Accept': 'application/ld+json' } });
  const domainData = await domainRes.json();
  const members = domainData['hydra:member'] || [];
  const domain = members.length > 0 ? members[0].domain : 'web-library.net';

  // 2. Generate random email
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let user = '';
  for (let i = 0; i < 10; i++) user += chars[Math.floor(Math.random() * chars.length)];
  const password = 'Px' + Array.from(crypto.getRandomValues(new Uint8Array(10)), b => chars[b % chars.length]).join('') + '!';
  const email = user + '@' + domain;

  // 3. Create account
  const createRes = await fetch(MAILTM_API + '/accounts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/ld+json' },
    body: JSON.stringify({ address: email, password: password }),
  });

  if (createRes.status === 422) {
    // Email taken, retry with different user
    return handleMailtmCreate(request); // recursion with new random
  }

  if (!createRes.ok) {
    const errText = await createRes.text();
    return new Response(JSON.stringify({ error: 'mail.tm create failed: ' + createRes.status, detail: errText.slice(0, 300) }), {
      status: 502, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }

  // 4. Get token
  const tokenRes = await fetch(MAILTM_API + '/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/ld+json' },
    body: JSON.stringify({ address: email, password: password }),
  });
  const tokenData = await tokenRes.json();

  return new Response(JSON.stringify({
    email: email,
    password: password,
    token: tokenData.token || tokenData.jwt || null,
    domain: domain,
  }), { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } });
}

async function handleMailtmInbox(request) {
  const body = await request.json();
  const token = body.token;
  if (!token) return new Response(JSON.stringify({ error: 'missing token' }), { status: 400, headers: { 'Content-Type': 'application/json' } });

  const res = await fetch(MAILTM_API + '/messages', {
    headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' }
  });
  const data = await res.json();
  const messages = (data['hydra:member'] || data.messages || []).map(m => ({
    id: m.id,
    subject: m.subject || '',
    from: (m.from && m.from.address) || '',
    intro: m.intro || '',
    createdAt: m.createdAt || '',
  }));

  return new Response(JSON.stringify({ messages }), { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } });
}

async function handlePixmindLogin(request) {
  const body = await request.json();
  const { email, password } = body;
  if (!email || !password) return new Response(JSON.stringify({ error: 'missing email or password' }), { status: 400, headers: { 'Content-Type': 'application/json' } });

  try {
    // Login to pixmind
    const loginRes = await fetch(PIXMIND_API + '/api/user/login/emailPassword', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': 'https://pixmind.io',
        'Referer': 'https://pixmind.io/',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!loginRes.ok) {
      const errText = await loginRes.text();
      return new Response(JSON.stringify({
        ok: false,
        error: 'pixmind login ' + loginRes.status + ': ' + errText.slice(0, 200),
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    const loginData = await loginRes.json();
    const token = loginData.data?.token || loginData.token || loginData.data?.accessToken || null;

    if (!token) {
      return new Response(JSON.stringify({ ok: false, error: '登录成功但未获取到 token，响应: ' + JSON.stringify(loginData).slice(0, 200) }), {
        status: 200, headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get user info
    let uid = null, credits = null;
    try {
      const infoRes = await fetch(PIXMIND_API + '/api/user/info', {
        headers: {
          'Authorization': 'Bearer ' + token,
          'Accept': 'application/json',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
      });
      if (infoRes.ok) {
        const info = await infoRes.json();
        uid = info.data?.id || info.data?.uid || info.id || info.uid || null;
        credits = info.data?.credits || info.data?.balance || info.credits || null;
      }
    } catch(e) { console.warn('get user info err', e); }

    return new Response(JSON.stringify({
      ok: true,
      uid: uid,
      token: token,
      credits: credits,
      email: email,
    }), { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } });

  } catch(e) {
    return new Response(JSON.stringify({ ok: false, error: e.message }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }
}

// ===================== Router =====================
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }
      });
    }

    // Serve frontend
    if (path === '/' || path === '/index.html') {
      return new Response(HTML_CONTENT, {
        headers: { 'Content-Type': 'text/html;charset=UTF-8' }
      });
    }

    // API: Mail.tm create email
    if (path === '/api/mailtm/create' && request.method === 'POST') {
      return handleMailtmCreate(request);
    }

    // API: Mail.tm inbox
    if (path === '/api/mailtm/inbox' && request.method === 'POST') {
      return handleMailtmInbox(request);
    }

    // API: Pixmind login
    if (path === '/api/pixmind/login' && request.method === 'POST') {
      return handlePixmindLogin(request);
    }

    return new Response('Not Found', { status: 404 });
  }
};
