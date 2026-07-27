// Cloudflare Worker - AI图片/视频生成器代理 v16
// v16: 修复isGptImg正则 + 独立账号冷却 + 密码列 + 批量验证 + 额度查询过期处理
// 部署：在 CF Dashboard 创建 Worker，粘贴此代码即可

const UPSTREAM_BASE = 'https://grok.17nas.com/local-api';
const SESSION_COOKIE = 'grok_webui_local_auth';
const SESSION_HEADER = 'X-Session-Token';

// ===================== HTML 前端 =====================
const HTML_CONTENT = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI图片/视频生成器 - 免费额度代理</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0a0b;--bg2:#141416;--bg3:#1c1c20;--bg4:#242429;
  --fg:#e8e6e3;--fg2:#a09f9d;--fg3:#6b6a68;
  --accent:#6c5ce7;--accent2:#a29bfe;--accent3:#4a3fb5;
  --green:#00b894;--red:#e17055;--orange:#fdcb6e;--blue:#74b9ff;
  --radius:10px;--shadow:0 2px 12px rgba(0,0,0,.4);
  --font:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  --mono:'SF Mono',Consolas,'Liberation Mono',Menlo,monospace;
}
[data-theme="light"]{
  --bg:#f5f5f7;--bg2:#ffffff;--bg3:#e8e8ea;--bg4:#d1d1d6;
  --fg:#1d1d1f;--fg2:#6e6e73;--fg3:#86868b;
  --accent:#6c5ce7;--accent2:#4a3fb5;--accent3:#ddd6fe;
  --green:#00b894;--red:#e17055;--orange:#fdcb6e;--blue:#5a9fd4;
  --shadow:0 2px 12px rgba(0,0,0,.1);
}
html{font-size:15px}
body{font-family:var(--font);background:var(--bg);color:var(--fg);min-height:100vh;line-height:1.6;transition:background .25s,color .25s}
a{color:var(--accent2);text-decoration:none}
a:hover{text-decoration:underline}
.app{display:flex;flex-direction:column;height:100vh;overflow:hidden}
.topbar{height:48px;background:var(--bg2);border-bottom:1px solid var(--bg4);display:flex;align-items:center;padding:0 20px;gap:16px;flex-shrink:0;transition:background .25s,border-color .25s}
.topbar h1{font-size:1rem;font-weight:700;color:var(--fg);display:flex;align-items:center;gap:8px;white-space:nowrap}
.topbar h1 span.badge{font-size:.6rem;background:var(--accent);color:#fff;padding:2px 5px;border-radius:4px;font-weight:500}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:14px;font-size:.85rem;white-space:nowrap}
.topbar-credits{color:var(--accent2);font-weight:600;font-family:var(--mono)}
.topbar-settings-btn{width:36px;height:36px;border:1px solid var(--bg4);border-radius:var(--radius);background:var(--bg3);color:var(--fg2);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s}
.topbar-settings-btn:hover{background:var(--bg4);border-color:var(--fg3);color:var(--fg)}
.topbar-settings-btn svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.main-area{flex:1;display:flex;overflow:hidden}
.left-panel{width:380px;min-width:320px;display:flex;flex-direction:column;overflow-y:auto;padding:20px;border-right:1px solid var(--bg4);flex-shrink:0;transition:border-color .25s}
.right-panel{flex:1;display:flex;flex-direction:column;overflow:hidden;background:var(--bg2);min-width:0;transition:background .25s}
.right-header{padding:12px 16px;border-bottom:1px solid var(--bg4);display:flex;align-items:center;justify-content:space-between;transition:border-color .25s}
.right-header h3{font-size:.9rem;font-weight:600}
.right-body{flex:1;overflow-y:auto;padding:12px 16px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 14px;border-radius:var(--radius);border:1px solid var(--bg4);background:var(--bg3);color:var(--fg);font-size:.85rem;cursor:pointer;transition:all .15s;font-family:var(--font);white-space:nowrap}
.btn:hover{background:var(--bg4);border-color:var(--fg3)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-primary:hover{background:var(--accent2);border-color:var(--accent2)}
.btn-sm{padding:5px 10px;font-size:.8rem}
.btn-xs{padding:2px 7px;font-size:.72rem;border-radius:5px}
.btn-danger{border-color:var(--red);color:var(--red)}
.btn-danger:hover{background:var(--red);color:#fff}
.btn-ghost{border:none;background:transparent;color:var(--fg2);padding:4px 8px}
.btn-ghost:hover{color:var(--fg);background:var(--bg3)}
.gen-form{max-width:100%;margin:0 auto}
.form-group{margin-bottom:14px}
.form-group label{display:block;font-size:.8rem;color:var(--fg2);margin-bottom:5px;font-weight:500}
.form-label-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:5px}
.form-label-row label{margin-bottom:0}
.form-group textarea{width:100%;min-height:120px;padding:10px;border-radius:var(--radius);border:1px solid var(--bg4);background:var(--bg3);color:var(--fg);font-size:.88rem;font-family:var(--font);resize:vertical;transition:border-color .15s}
.form-group textarea:focus{outline:none;border-color:var(--accent)}
.form-group select,.form-group input[type="text"],.form-group input[type="password"]{width:100%;padding:8px 12px;border-radius:var(--radius);border:1px solid var(--bg4);background:var(--bg3);color:var(--fg);font-size:.85rem;font-family:var(--font);transition:border-color .15s,background .25s,color .25s}
.form-group select:focus,.form-group input:focus{outline:none;border-color:var(--accent)}
.form-row{display:flex;gap:10px;align-items:flex-end}
.form-row .form-group{flex:1}
.ratio-options{display:flex;flex-wrap:wrap;gap:5px}
.ratio-btn{padding:5px 10px;border-radius:var(--radius);border:1px solid var(--bg4);background:var(--bg3);color:var(--fg2);font-size:.78rem;cursor:pointer;transition:all .15s}
.ratio-btn:hover{border-color:var(--fg3)}
.ratio-btn.active{border-color:var(--accent);color:var(--accent2);background:var(--accent3)}
.ref-upload{border:2px dashed var(--bg4);border-radius:var(--radius);padding:14px;text-align:center;cursor:pointer;transition:border-color .15s;color:var(--fg3);font-size:.82rem}
.ref-upload:hover{border-color:var(--accent3);color:var(--fg2)}
.ref-upload.dragover{border-color:var(--accent);background:var(--accent3)}
.ref-grid{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.ref-thumb{position:relative;width:64px;height:64px;border-radius:6px;overflow:hidden;border:1px solid var(--bg4);flex-shrink:0}
.ref-thumb img{width:100%;height:100%;object-fit:cover}
.ref-thumb .ref-del{position:absolute;top:2px;right:2px;width:16px;height:16px;border-radius:50%;background:var(--red);color:#fff;font-size:10px;line-height:16px;text-align:center;cursor:pointer;opacity:.85}
.gen-actions{display:flex;gap:8px;margin-top:16px;align-items:center}
.concurrency-info{font-size:.75rem;color:var(--fg3);margin-left:auto}
.divider{height:1px;background:var(--bg4);margin:20px 0;transition:background .25s}
.bottom-actions{display:flex;flex-direction:column;gap:8px}
.bottom-btn{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:10px;border-radius:var(--radius);border:1px solid var(--bg4);background:var(--bg3);color:var(--fg);font-size:.85rem;cursor:pointer;transition:all .15s;font-family:var(--font)}
.bottom-btn:hover{background:var(--bg4);border-color:var(--fg3)}
.bottom-btn.primary{border-color:var(--accent);color:var(--accent2)}
.bottom-btn.primary:hover{background:var(--accent3);border-style:solid}
.hist-item{background:var(--bg3);border-radius:var(--radius);border:1px solid var(--bg4);margin-bottom:10px;overflow:hidden;transition:background .25s,border-color .25s}
.hist-item.running-item{border-color:var(--accent3)}
.hist-header{padding:8px 12px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;cursor:default}
.hist-status{font-size:.68rem;padding:2px 6px;border-radius:4px;font-weight:600;white-space:nowrap}
.hist-status.ok{background:var(--green);color:#fff}
.hist-status.err{background:var(--red);color:#fff}
.hist-status.timeout{background:var(--orange);color:#111}
.hist-status.running{background:var(--blue);color:#111;animation:pulse 1.5s ease-in-out infinite}
.hist-status.queued{background:var(--fg3);color:#111}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
.hist-time{font-size:.72rem;color:var(--fg3);font-family:var(--mono);margin-left:auto;white-space:nowrap}
.hist-prompt{padding:8px 12px;font-size:.82rem;color:var(--fg);white-space:pre-wrap;word-break:break-word;max-height:80px;overflow-y:auto;line-height:1.4}
.hist-prompt-actions{display:flex;gap:4px;padding:2px 12px 6px}
.hist-prompt-actions button{font-size:.7rem}
.hist-error{padding:8px 12px;font-size:.8rem;color:var(--red);background:rgba(225,112,85,.08)}
.hist-progress{padding:8px 12px}
.hist-progress .pbar{height:6px;background:var(--bg4);border-radius:3px;overflow:hidden}
.hist-progress .pfill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:3px;transition:width .5s}
.hist-progress .ptxt{font-size:.78rem;color:var(--fg2);margin-top:5px;display:flex;align-items:center;gap:6px}
.hist-progress .ptxt .elapsed{color:var(--fg3);font-family:var(--mono);font-size:.72rem;margin-left:auto}
.hist-img-link{padding:4px 12px 8px;font-size:.78rem}
.hist-img-link a{color:var(--accent2);text-decoration:none;padding:3px 8px;border-radius:4px;background:var(--bg4);transition:background .15s;display:inline-flex;align-items:center;gap:4px}
.hist-img-link a:hover{background:var(--accent3)}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:100}
.modal-backdrop.show{display:flex}
.modal{background:var(--bg2);border-radius:12px;width:90%;max-width:560px;max-height:80vh;overflow-y:auto;border:1px solid var(--bg4);box-shadow:var(--shadow);transition:background .25s,border-color .25s}
.modal-header{padding:16px 20px;border-bottom:1px solid var(--bg4);display:flex;align-items:center}
.modal-header h3{flex:1;font-size:1rem;font-weight:600}
.modal-body{padding:20px}
.accounts-table{width:100%;border-collapse:collapse;font-size:.85rem}
.accounts-table th,.accounts-table td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--bg4)}
.accounts-table th{color:var(--fg3);font-weight:500;font-size:.75rem;text-transform:uppercase}
.accounts-table tr:hover td{background:var(--bg3)}
.toast-container{position:fixed;top:16px;right:16px;z-index:200;display:flex;flex-direction:column;gap:8px}
.toast{padding:10px 16px;border-radius:var(--radius);font-size:.85rem;box-shadow:var(--shadow);animation:toastIn .3s;max-width:360px}
.toast.success{background:var(--green);color:#fff}
.toast.error{background:var(--red);color:#fff}
.toast.info{background:var(--accent);color:#fff}
@keyframes toastIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--bg4);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:900px){
  .main-area{flex-direction:column}
  .right-panel{width:100%;min-width:auto;max-height:50vh;flex:none}
  .left-panel{width:100%;min-width:auto;flex:none;border-right:none;border-bottom:1px solid var(--bg4)}
  .form-row{flex-direction:column}
}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--bg4);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--fg3)}
.help-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:90%;max-width:520px;max-height:80vh;background:var(--bg2);border:1px solid var(--bg4);border-radius:12px;box-shadow:var(--shadow);z-index:150;display:none;flex-direction:column;transition:background .25s,border-color .25s}
.help-panel.show{display:flex}
.help-panel-header{padding:14px 20px;border-bottom:1px solid var(--bg4);display:flex;align-items:center}
.help-panel-header h3{flex:1;font-size:.95rem;font-weight:600}
.help-panel-body{padding:16px 20px;overflow-y:auto;flex:1;font-size:.84rem;line-height:1.7;color:var(--fg2)}
.help-panel-body h4{color:var(--fg);font-size:.9rem;margin:14px 0 6px;font-weight:600}
.help-panel-body h4:first-child{margin-top:0}
.help-panel-body ul{padding-left:18px;margin:4px 0 10px}
.help-panel-body li{margin:3px 0}
.help-panel-body code{background:var(--bg4);padding:1px 5px;border-radius:3px;font-size:.8rem;font-family:var(--mono);color:var(--accent2)}
.help-panel-body .changelog{font-size:.78rem;color:var(--fg3);border-top:1px solid var(--bg4);padding-top:12px;margin-top:16px}
.help-panel-body .changelog dt{color:var(--fg2);font-weight:600;margin-top:8px}
.help-panel-body .changelog dd{margin:2px 0 4px 16px}
.theme-switch{display:inline-flex;border:1px solid var(--bg4);border-radius:var(--radius);overflow:hidden}
.theme-btn{padding:6px 12px;border:none;background:var(--bg3);color:var(--fg2);font-size:.78rem;cursor:pointer;transition:all .15s;font-family:var(--font);white-space:nowrap}
.theme-btn:hover{background:var(--bg4)}
.theme-btn.active{background:var(--accent);color:#fff}
.wm-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:92%;max-width:720px;max-height:88vh;background:var(--bg2);border:1px solid var(--bg4);border-radius:12px;box-shadow:var(--shadow);z-index:160;display:none;flex-direction:column;transition:background .25s,border-color .25s}
.wm-panel.show{display:flex}
.wm-titlebar{display:flex;align-items:center;justify-content:space-between;padding:0 14px;height:38px;background:var(--accent);color:#fff;border-radius:12px 12px 0 0}
.wm-titlebar-text{font-size:.88rem;font-weight:700}
.wm-titlebar-close{width:34px;height:34px;border:none;background:transparent;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1.2rem;border-radius:4px;transition:background .15s}
.wm-titlebar-close:hover{background:rgba(255,255,255,.15)}
.wm-body{padding:16px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:12px}
.wm-upload-section{border:2px dashed var(--bg4);border-radius:8px;padding:14px;text-align:center;cursor:pointer;color:var(--fg3);font-size:.82rem;transition:border-color .15s,background .25s}
.wm-upload-section:hover{border-color:var(--accent3);color:var(--fg2)}
.wm-upload-section .wm-upload-label{font-weight:600;color:var(--fg2);margin-bottom:4px}
.wm-upload-section .wm-upload-sub{font-size:.72rem;color:var(--fg3)}
.wm-canvas-wrap{position:relative;background:var(--bg);border:1px solid var(--bg4);border-radius:8px;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:180px}
.wm-canvas-wrap canvas{max-width:100%;max-height:50vh;display:block;cursor:default}
.wm-wm-preview{display:flex;align-items:center;gap:8px;margin-top:4px}
.wm-wm-preview img{max-height:40px;border-radius:4px;border:1px solid var(--bg4)}
.wm-wm-preview span{font-size:.75rem;color:var(--fg3)}
.wm-controls{display:flex;flex-wrap:wrap;gap:10px}
.wm-control-group{flex:1;min-width:140px}
.wm-control-group label{display:block;font-size:.75rem;color:var(--fg2);margin-bottom:4px;font-weight:500}
.wm-slider{display:flex;align-items:center;gap:8px}
.wm-slider input[type="range"]{flex:1;height:4px;appearance:none;-webkit-appearance:none;background:var(--bg4);border-radius:2px;outline:none}
.wm-slider input[type="range"]::-webkit-slider-thumb{appearance:none;-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:var(--accent);cursor:pointer;box-shadow:0 1px 2px rgba(0,0,0,.3);transition:transform .1s}
.wm-slider input[type="range"]::-webkit-slider-thumb:hover{transform:scale(1.2)}
.wm-slider-val{font-family:var(--mono);font-size:.75rem;color:var(--fg3);min-width:32px;text-align:right}
.wm-actions{display:flex;gap:8px;justify-content:flex-end;padding-top:8px;border-top:1px solid var(--bg4)}
.wm-preview-row{display:flex;gap:10px;align-items:center}
.wm-preview-thumb{max-height:48px;border-radius:4px;border:1px solid var(--bg4)}
.promptlib-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:90%;max-width:480px;max-height:80vh;background:var(--bg2);border:1px solid var(--bg4);border-radius:12px;box-shadow:var(--shadow);z-index:170;display:none;flex-direction:column;transition:background .25s,border-color .25s}
.promptlib-panel.show{display:flex}
.promptlib-header{padding:14px 20px;border-bottom:1px solid var(--bg4);display:flex;align-items:center}
.promptlib-header h3{flex:1;font-size:.95rem;font-weight:600}
.promptlib-body{padding:16px 20px;overflow-y:auto;flex:1}
.promptlib-item{padding:10px 12px;border:1px solid var(--bg4);border-radius:8px;margin-bottom:8px;background:var(--bg3);transition:background .15s}
.promptlib-item:hover{background:var(--bg4)}
.promptlib-item-text{font-size:.82rem;color:var(--fg);white-space:pre-wrap;word-break:break-word;max-height:60px;overflow-y:hidden;line-height:1.4;cursor:pointer}
.promptlib-item-text:hover{color:var(--accent2)}
.promptlib-item-meta{display:flex;align-items:center;gap:6px;margin-top:6px;font-size:.72rem;color:var(--fg3)}
.promptlib-item-meta button{font-size:.68rem}
.promptlib-empty{color:var(--fg3);text-align:center;padding:40px 0;font-size:.85rem}
.promptlib-actions{display:flex;gap:6px;padding:12px 20px;border-top:1px solid var(--bg4)}
</style>
</head>
<body>
<div class="app">
  <div class="topbar">
    <h1>AI图片/视频生成器 <span class="badge">代理</span></h1>
    <div class="topbar-right">
      <span id="concurrencyInfo" style="font-size:.75rem;color:var(--fg3)">并发: 0/0</span>
      <span>可用: <span id="usableCreditsTop" class="topbar-credits">0</span> / 总: <span id="totalCreditsTop" class="topbar-credits">0</span></span>
      <button class="topbar-settings-btn" onclick="showSettingsModal()" title="设置">
        <svg viewBox="0 0 24 24"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
    </div>
  </div>
  <div class="main-area">
    <div class="left-panel">
      <div class="gen-form">
        <div class="form-group">
          <div class="form-label-row">
            <label>提示词</label>
            <button class="btn btn-xs btn-ghost" onclick="pasteToPrompt()">粘贴</button>
          </div>
          <textarea id="promptInput" placeholder="描述你想生成的图片...\\n\\n例如: a cute cat sitting on a windowsill, watercolor style"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>模型</label>
            <select id="modelSelect" onchange="onModelChange()">
              <option value="gpt-image-2">[图像] gpt-image-2</option>
              <option value="gpt-image-1">[图像] gpt-image-1</option>
              <option value="grok-imagine-image">[图像] grok-imagine-image</option>
              <option value="grok-imagine-image-pro">[图像] grok-imagine-image-pro</option>
              <option value="grok-imagine-image-lite">[图像] grok-imagine-image-lite</option>
              <option value="grok-imagine-video">[视频] grok-imagine-video</option>
            </select>
          </div>
          <div class="form-group">
            <label>数量</label>
            <select id="countSelect">
              <option value="1">1 张</option>
              <option value="2">2 张</option>
              <option value="3">3 张</option>
              <option value="4">4 张</option>
              <option value="5">5 张</option>
              <option value="6">6 张</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>宽高比</label>
          <div class="ratio-options" id="ratioOptions">
            <button class="ratio-btn" data-ratio="auto">智能</button>
            <button class="ratio-btn active" data-ratio="1:1">1:1</button>
            <button class="ratio-btn" data-ratio="3:2">3:2</button>
            <button class="ratio-btn" data-ratio="2:3">2:3</button>
            <button class="ratio-btn" data-ratio="16:9">16:9</button>
            <button class="ratio-btn" data-ratio="9:16">9:16</button>
            <button class="ratio-btn" data-ratio="4:3">4:3</button>
            <button class="ratio-btn" data-ratio="3:4">3:4</button>
            <button class="ratio-btn" data-ratio="5:4">5:4</button>
            <button class="ratio-btn" data-ratio="4:5">4:5</button>
            <button class="ratio-btn" data-ratio="2:1">2:1</button>
            <button class="ratio-btn" data-ratio="1:2">1:2</button>
            <button class="ratio-btn" data-ratio="21:9">21:9</button>
            <button class="ratio-btn" data-ratio="9:21">9:21</button>
          </div>
        </div>
        <div class="form-group" id="durationGroup" style="display:none">
          <label>视频时长</label>
          <select id="durationSelect">
            <option value="6">6 秒</option>
            <option value="10">10 秒</option>
            <option value="12">12 秒</option>
            <option value="16">16 秒</option>
            <option value="20">20 秒</option>
          </select>
        </div>
        <div class="form-group">
          <label id="refLabel">参考图（可选，图生图/图生视频，可多张）</label>
          <div class="ref-upload" id="refUpload" onclick="document.getElementById('refFileInput').click()">点击或拖拽上传参考图</div>
          <input type="file" id="refFileInput" accept="image/*" multiple style="display:none" onchange="handleRefImages(this)">
          <div class="ref-grid" id="refGrid"></div>
        </div>
        <div class="gen-actions">
          <button class="btn btn-primary" id="generateBtn" onclick="startGeneration()">生成</button>
          <button class="btn btn-sm" onclick="document.getElementById('promptInput').value='';refImages=[];renderRefGrid()">清空</button>
          <span class="concurrency-info" id="concurrencyDetail"></span>
        </div>
      </div>
      <div class="divider"></div>
      <div class="bottom-actions">
        <button class="bottom-btn primary" onclick="openWatermarkModal()">为生成好的图片加水印</button>
        <button class="bottom-btn" onclick="showPromptLib()">提示词库</button>
      </div>
    </div>
    <div class="right-panel">
      <div class="right-header">
        <h3>历史记录</h3>
        <div style="display:flex;gap:6px">
          <button class="btn btn-sm" onclick="autoRegister()">+注册</button>
          <button class="btn btn-sm" onclick="addManualAccount()">+添加</button>
          <button class="btn btn-sm" onclick="exportHistory()" style="border-color:var(--accent);color:var(--accent2)">导出</button>
          <button class="btn btn-sm" onclick="importHistory()">导入</button>
          <button class="btn btn-sm btn-danger" onclick="clearHistory()">清空</button>
        </div>
      </div>
      <div class="right-body" id="historyList">
        <p id="historyEmpty" style="color:var(--fg3);text-align:center;padding:40px 0;font-size:.85rem">暂无历史记录</p>
      </div>
    </div>
  </div>
</div>

<!-- 设置弹窗 -->
<div class="modal-backdrop" id="settingsModal">
  <div class="modal">
    <div class="modal-header">
      <h3>设置 & 账号管理</h3>
      <button class="btn btn-sm" onclick="closeSettingsModal()">关闭</button>
    </div>
    <div class="modal-body">
      <div style="margin-bottom:16px">
        <label style="display:block;font-size:.8rem;color:var(--fg2);margin-bottom:6px;font-weight:500">外观主题</label>
        <div class="theme-switch">
          <button class="theme-btn" data-theme-val="system" onclick="setThemeMode('system')">跟随系统</button>
          <button class="theme-btn" data-theme-val="light" onclick="setThemeMode('light')">浅色</button>
          <button class="theme-btn" data-theme-val="dark" onclick="setThemeMode('dark')">深色</button>
        </div>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" onclick="autoRegister()">注册新账号</button>
        <button class="btn btn-sm" onclick="addManualAccount()">手动添加</button>
        <button class="btn btn-sm" onclick="checkinAll()">批量签到</button>
        <button class="btn btn-sm" onclick="refreshAllQuota()">刷新额度</button>
        <button class="btn btn-sm" onclick="batchVerifyAccounts()">批量验证</button>
        <a href="https://grok.17nas.com" target="_blank" rel="noopener" class="btn btn-sm" style="text-decoration:none">官网注册</a>
      </div>
      <div id="accountsTableContainer" style="overflow-x:auto;margin-bottom:16px"></div>
      <div id="abandonedPoolContainer" style="overflow-x:auto;margin-bottom:16px"></div>
      <div style="display:flex;gap:8px;margin-bottom:20px">
        <button class="btn btn-sm" onclick="exportAccounts()" style="border-color:var(--accent);color:var(--accent2)">导出账号</button>
        <button class="btn btn-sm" onclick="importAccounts()">导入账号</button>
      </div>
      <input type="file" id="importFileInput" accept=".json" style="display:none" onchange="handleImportFile(this)">
      <input type="file" id="importHistoryInput" accept=".json" style="display:none" onchange="handleImportHistory(this)">
      <input type="file" id="importPromptLibInput" accept=".json" style="display:none" onchange="handleImportPromptLib(this)">
      <div style="border-top:1px solid var(--bg4);padding-top:16px">
        <div class="form-group">
          <label>默认密码（自动追加yymmdd日期后缀）</label>
          <input type="text" id="defaultPassword" value="Ml@2026Proxy">
        </div>
        <div class="form-group">
          <label>轮换策略</label>
          <select id="rotationStrategy">
            <option value="most-credits">优先额度最多</option>
            <option value="round-robin">轮询</option>
            <option value="newest">优先最新</option>
          </select>
        </div>
        <div class="form-group"><label><input type="checkbox" id="autoCheckin" checked> 额度耗尽自动签到</label></div>
        <div class="form-group"><label><input type="checkbox" id="autoRegisterChk" checked> 额度耗尽自动注册</label></div>
        <button class="btn btn-primary" onclick="saveSettings()">保存设置</button>
      </div>
      <div style="border-top:1px solid var(--bg4);margin-top:16px;padding-top:12px;display:flex;gap:8px;align-items:center">
        <button class="btn btn-sm" onclick="toggleHelpPanel()" style="border-color:var(--accent);color:var(--accent2)">使用帮助 & 更新日志</button>
        <button class="btn btn-danger btn-sm" onclick="clearAllData()">清除所有数据</button>
      </div>
    </div>
  </div>
</div>
<div class="help-panel" id="helpPanel">
  <div class="help-panel-header">
    <h3>使用说明 & 更新日志</h3>
    <button class="btn btn-sm" onclick="toggleHelpPanel()">关闭</button>
  </div>
  <div class="help-panel-body">
    <h4>产品简介</h4>
    <p>AI图片/视频生成器是一个基于 Cloudflare Worker 的免费 AI 图片/视频生成代理服务，后端对接 grok.17nas.com 平台，支持多种主流图片/视频生成模型，提供免费额度管理和并发生成能力。</p>

    <h4>主要功能</h4>
    <ul>
      <li><strong>多模型支持</strong>：图像模型(gpt-image-2、gpt-image-1、grok-imagine-image/pro/lite) + 视频模型(grok-imagine-video)</li>
      <li><strong>视频生成</strong>：支持 grok-imagine-video 视频生成，可选 6/10/12/16/20 秒时长，支持参考图生视频(I2V)</li>
      <li><strong>并发生成</strong>：每个账号 3 个并发槽位，多账号叠加使用，生成按钮即时可用无需等待</li>
      <li><strong>账号池管理</strong>：自动注册、手动添加、批量签到、额度自动刷新、智能轮换策略</li>
      <li><strong>参考图生成</strong>：gpt-image 模型支持图生图，视频模型支持图生视频(I2V)</li>
      <li><strong>历史记录</strong>：生成历史自动保存到浏览器，提示词可一键复制或加入提示词库</li>
      <li><strong>提示词库</strong>：收藏常用提示词，支持导入导出，点击即可填入输入框</li>
      <li><strong>水印工具</strong>：独立水印编辑器，上传成品图和水印图，拖拽调整位置/大小/透明度，一键导出成品</li>
      <li><strong>历史导入导出</strong>：支持将历史记录导出为JSON，跨设备导入恢复</li>
      <li><strong>媒体代理</strong>：HTTP 图片/视频自动通过 Worker 代理转为 HTTPS，解决混合内容限制</li>
      <li><strong>额度耗尽自动处理</strong>：额度不足时自动签到/注册新账号，无缝续用</li>
      <li><strong>深浅色模式</strong>：支持跟随系统、浅色、深色三种主题切换</li>
    </ul>

    <h4>使用方法</h4>
    <ul>
      <li>首次使用：点击右侧面板 <code>+注册</code> 按钮自动注册账号</li>
      <li>生成图片：在左侧输入提示词，选择图像模型/比例/数量，点击 <code>生成</code></li>
      <li>生成视频：选择 [视频] grok-imagine-video 模型，选择时长和比例，点击 <code>生成</code></li>
      <li>一键粘贴：点击提示词标签旁的 <code>粘贴</code> 按钮，从剪贴板粘贴内容</li>
      <li>提示词库：点击 <code>提示词库</code> 查看收藏的提示词，点击即可使用</li>
      <li>并发生成：无需等待上一张完成，直接修改提示词再次点击生成</li>
      <li>参考图：选择支持参考图的模型后，点击或拖拽上传参考图（图生图/图生视频）</li>
      <li>添加水印：先下载生成的图片，再点击 <code>为生成好的图片加水印</code>，上传成品图和水印图</li>
      <li>管理账号：点击右上角设置图标进入设置，可签到/删除/导出/导入账号</li>
      <li>宽高比：支持 1:1、3:2、2:3、16:9、9:16、4:3、3:4、5:4、4:5、2:1、1:2、21:9、9:21 或智能</li>
    </ul>

    <h4>注意事项</h4>
    <ul>
      <li>base64 格式图片为临时数据，刷新页面后将丢失，请及时下载</li>
      <li>URL 格式图片通过代理加载，刷新后可恢复显示</li>
      <li>每个账号每日可签到获取免费额度</li>
      <li>同一 IP 每日注册数量受限，额度耗尽时可手动添加账号</li>
      <li>关闭页面前请注意保存生成的图片，如有需要可导出工具设置、历史记录和提示词库</li>
    </ul>

    <dl class="changelog">
      <dt>v16 (当前)</dt>
      <dd>修复isGptImg正则表达式在模板字面量中转义错误导致页面SyntaxError（\b被编码为退格符、\d变为字面d）</dd>
      <dd>登录冷却改为独立账号级别：单账号冷却不再阻塞其他账号登录</dd>
      <dd>账号表新增密码列（点击可复制），废弃池同步显示密码</dd>
      <dd>新增批量验证功能：使用只读额度接口检测账号有效性，不消耗生成额度</dd>
      <dd>废弃池验证增加2.5秒间隔延迟，避免触发上游频率限制</dd>
      <dd>额度查询自动清除过期token，下次操作时自动重新登录</dd>

      <dt>v15</dt>
      <dd>注册用户名改为真人风格：随机姓名/形容词名词组合，避免机器规律被检测</dd>
      <dd>默认密码末尾自动追加yymmdd日期后缀，每日MD5哈希不同</dd>
      <dd>新增废弃账号池：登录失败疑似被封号的账号自动移入，支持重新验证、一键清空、还原</dd>
      <dd>额度统计区分"可用额度"和"总额度"，仅已登录账号计入可用额度</dd>
      <dd>导出/导入账号时同时记录用户名和密码（含废弃池）</dd>
      <dd>新增登录冷却机制：连续登录失败后自动等待5分钟，避免触发上游限制</dd>

      <dt>v14</dt>
      <dd>新增视频生成模型 grok-imagine-video，支持 6/10/12/16/20 秒时长选择</dd>
      <dd>新增视频时长选择器，选择视频模型时自动显示</dd>
      <dd>新增参考图生视频(I2V)支持：视频模型可上传参考图进行图生视频</dd>
      <dd>扩展宽高比选项：从 6 种增至 14 种，新增 4:3、3:4、5:4、4:5、2:1、1:2、21:9、9:21</dd>
      <dd>宽高比"不限"更名"智能"：自动从提示词推断比例</dd>
      <dd>生成数量从 1/2/4/6/8 调整为 1-6 连续可选</dd>
      <dd>模型下拉增加分类标签 [图像]/[视频]</dd>
      <dd>生成按钮文字根据模型类型动态切换（生成图片/生成视频）</dd>
      <dd>参考图标签更新：支持图生图和图生视频</dd>
      <dd>Worker 后端新增视频文件代理支持</dd>
      <dd>更名：AI图片生成器 &rarr; AI图片/视频生成器</dd>

      <dt>v13</dt>
      <dd>历史记录图片区域简化：去掉预览，合并下载和原图为单一链接"查看和保存原图"</dd>
      <dd>历史记录提示词增加操作按钮：一键复制、加入提示词库</dd>
      <dd>提示词输入框加高（80px &rarr; 120px），标签旁新增一键粘贴按钮（如已有内容会确认是否覆盖）</dd>
      <dd>左侧面板水印区域简化为单个按钮"为生成好的图片加水印"</dd>
      <dd>新增提示词库功能：收藏提示词，支持导入/导出/删除，点击即可填入输入框，数据保存于浏览器本地存储</dd>
      <dd>关闭窗口提示优化：提醒用户保存图片、导出设置/历史记录/提示词库</dd>

      <dt>v12</dt>
      <dd>更名：马良生图 &rarr; AI图片生成器</dd>
      <dd>水印工具独立化：从历史记录移至左侧面板下方，改为上传制（先下载成品图再上传添加水印），不再尝试从base64加载</dd>
      <dd>新增深浅色模式：支持跟随系统/浅色/深色三态切换，在设置面板中配置</dd>
      <dd>右上角用户名替换为设置图标（齿轮SVG），点击打开设置面板</dd>
      <dd>设置面板增加主题切换、帮助入口，优化布局风格</dd>
      <dd>全面适配浅色模式，所有CSS变量支持深浅切换，过渡动画平滑</dd>

      <dt>v11</dt>
      <dd>新增手动加水印功能：历史记录中每张图右侧增加加水印入口，浮窗内支持上传水印图片、调整位置/大小/透明度，画布拖拽定位，一键导出成品PNG</dd>
      <dd>新增历史记录导入/导出：支持将生成历史导出为JSON文件，可跨设备导入恢复（含图片URL和base64数据）</dd>
      <dd>优化：水印浮窗遵循设计规范，Slider控件、Window标题栏风格统一</dd>

      <dt>v10</dt>
      <dd>修复 markdown 解析中 base64 数据被错误归类为 url 类型导致图片无法显示</dd>
      <dd>修复签到状态 UI 不更新（已签到仍显示错误标记）</dd>
      <dd>优化图片代理：添加 Referer 头部，改进加载失败的回退显示</dd>
      <dd>新增设置页面帮助浮窗（使用说明 & 更新日志）</dd>
      <dd>修复参考图网格添加更多按钮的模板字面量转义问题</dd>

      <dt>v9</dt>
      <dd>修复模板字面量中转义引号导致 SyntaxError（onclick 中的引号问题）</dd>
      <dd>修复 showSettingsModal / renderRefGrid 函数未定义（SyntaxError 连锁反应）</dd>
      <dd>实现图片预览嵌入历史条目内（而非独立区域）</dd>
      <dd>实现 Worker 端图片代理（服务端获取 HTTP 图片并返回 HTTPS）</dd>
      <dd>实现页面刷新恢复 URL 类型图片和历史记录</dd>
      <dd>实现并发生成（fire-and-forget 模式，即时可再次提交）</dd>
      <dd>实现刷新后中断未完成任务标记</dd>

      <dt>v8</dt>
      <dd>修复 TDZ 错误（变量声明提升至脚本顶部）</dd>
      <dd>修复 restoreLiveImages 未调用</dd>
      <dd>实现图片直链预览</dd>

      <dt>v7</dt>
      <dd>初始版本：基本生成功能、账号管理、历史记录</dd>
    </dl>
  </div>
</div>
<div class="wm-panel" id="watermarkPanel">
  <div class="wm-titlebar">
    <span class="wm-titlebar-text">水印工具</span>
    <button class="wm-titlebar-close" onclick="closeWatermarkModal()">&times;</button>
  </div>
  <div class="wm-body">
    <div class="wm-upload-section" onclick="document.getElementById('wmBaseFileInput').click()">
      <div class="wm-upload-label">点击上传成品图片</div>
      <div class="wm-upload-sub">请先下载生成的图片，再在此处上传</div>
    </div>
    <input type="file" id="wmBaseFileInput" accept="image/*" style="display:none" onchange="handleWmBaseUpload(this)">
    <div id="wmBasePreviewArea"></div>
    <div class="wm-canvas-wrap">
      <div id="wmPlaceholder" style="display:flex;align-items:center;justify-content:center;color:var(--fg3);font-size:.85rem;padding:40px">请先上传成品图片</div>
      <canvas id="wmCanvas" style="display:none"></canvas>
    </div>
    <div class="wm-upload-section" onclick="document.getElementById('wmFileInput').click()">
      <div class="wm-upload-label">点击上传水印图片</div>
      <div class="wm-upload-sub">PNG透明背景推荐</div>
    </div>
    <input type="file" id="wmFileInput" accept="image/*" style="display:none" onchange="handleWmUpload(this)">
    <div id="wmPreviewArea"></div>
    <div class="wm-controls">
      <div class="wm-control-group">
        <label>水平位置</label>
        <div class="wm-slider"><input type="range" id="wmXSlider" min="0" max="100" value="50" oninput="updateWmFromSliders()"><span class="wm-slider-val" id="wmXVal">50%</span></div>
      </div>
      <div class="wm-control-group">
        <label>垂直位置</label>
        <div class="wm-slider"><input type="range" id="wmYSlider" min="0" max="100" value="50" oninput="updateWmFromSliders()"><span class="wm-slider-val" id="wmYVal">50%</span></div>
      </div>
      <div class="wm-control-group">
        <label>大小</label>
        <div class="wm-slider"><input type="range" id="wmScaleSlider" min="3" max="100" value="20" oninput="updateWmFromSliders()"><span class="wm-slider-val" id="wmScaleVal">20%</span></div>
      </div>
      <div class="wm-control-group">
        <label>透明度</label>
        <div class="wm-slider"><input type="range" id="wmAlphaSlider" min="5" max="100" value="50" oninput="updateWmFromSliders()"><span class="wm-slider-val" id="wmAlphaVal">50%</span></div>
      </div>
    </div>
    <div style="font-size:.72rem;color:var(--fg3)">提示：可在画布上拖拽水印调整位置</div>
    <div class="wm-actions">
      <button class="btn btn-sm" onclick="closeWatermarkModal()">取消</button>
      <button class="btn btn-primary btn-sm" onclick="exportWatermarkImage()">输出成品图片</button>
    </div>
  </div>
</div>
<div class="promptlib-panel" id="promptLibPanel">
  <div class="promptlib-header">
    <h3>提示词库</h3>
    <button class="btn btn-sm" onclick="closePromptLib()">关闭</button>
  </div>
  <div class="promptlib-body" id="promptLibList">
    <p class="promptlib-empty" id="promptLibEmpty">暂无收藏的提示词</p>
  </div>
  <div class="promptlib-actions">
    <button class="btn btn-sm" onclick="exportPromptLib()" style="border-color:var(--accent);color:var(--accent2)">导出</button>
    <button class="btn btn-sm" onclick="importPromptLib()">导入</button>
    <button class="btn btn-sm btn-danger" onclick="clearPromptLib()">清空</button>
  </div>
</div>
<div class="toast-container" id="toastContainer"></div>
<script>
const STATE_KEY='maliang_state',HISTORY_KEY='maliang_history',PROMPTLIB_KEY='maliang_promptlib';
let state=loadState(),generationHistory=loadHistory(),promptLibrary=loadPromptLib();

// 运行时完整图片存储（不存localStorage，避免爆容量）
const liveImages=new Map(); // id -> [{type,value}]
// 并发相关变量
const CONCURRENT_PER_ACCOUNT=3;
let activeSlots=0;
const taskStartTimes=new Map();
let selectedRatio='1:1',refImages=[],selectedDuration=6;

// ===== 模型类型判断 =====
function isVideoModel(m){return m==='grok-imagine-video'}
function isGptImg(m){return/\\bgpt-image-\\d+\\b/.test(m)||m==='gpt-image-1'||m==='gpt-image-2'}
function supportsRefImage(m){return isGptImg(m)||isVideoModel(m)}

// ===== 模型切换处理 =====
function onModelChange(){
  var model=document.getElementById('modelSelect').value;
  var durGroup=document.getElementById('durationGroup');
  var btn=document.getElementById('generateBtn');
  var refLabel=document.getElementById('refLabel');
  durGroup.style.display=isVideoModel(model)?'block':'none';
  btn.textContent=isVideoModel(model)?'生成视频':'生成图片';
  if(isVideoModel(model)){refLabel.textContent='参考图（可选，图生视频，可多张）'}
  else if(isGptImg(model)){refLabel.textContent='参考图（可选，图生图，可多张）'}
  else{refLabel.textContent='参考图（可选，可多张）'}
}

// ===== 主题管理 =====
function getThemeMode(){return state.settings.theme||'system'}
function getEffectiveTheme(mode){if(mode==='system'){return window.matchMedia&&window.matchMedia('(prefers-color-scheme:light)').matches?'light':'dark'}return mode}
function applyTheme(){var mode=getThemeMode();var effective=getEffectiveTheme(mode);document.documentElement.setAttribute('data-theme',effective);document.querySelectorAll('.theme-btn').forEach(function(btn){btn.classList.toggle('active',btn.getAttribute('data-theme-val')===mode)})}
function setThemeMode(mode){state.settings.theme=mode;saveState();applyTheme()}
if(window.matchMedia){window.matchMedia('(prefers-color-scheme:light)').addEventListener('change',function(){if(getThemeMode()==='system')applyTheme()})}

// ===== 提示词库 =====
function loadPromptLib(){try{var r=localStorage.getItem(PROMPTLIB_KEY);if(r)return JSON.parse(r)}catch(e){}return[]}
function savePromptLib(){try{localStorage.setItem(PROMPTLIB_KEY,JSON.stringify(promptLibrary))}catch(e){}}
function addToPromptLib(text){
  if(!text||!text.trim())return;
  text=text.trim();
  if(promptLibrary.some(function(p){return p.text===text})){toast('该提示词已在词库中','info');return}
  promptLibrary.unshift({id:Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,6),text:text,addedAt:Date.now()});
  savePromptLib();
  toast('已加入提示词库','success');
}
function removeFromPromptLib(el){
  var wrapper=el.closest('[data-prompt-id]');
  if(!wrapper)return;
  var id=wrapper.getAttribute('data-prompt-id');
  promptLibrary=promptLibrary.filter(function(p){return p.id!==id});
  savePromptLib();
  renderPromptLib();
  toast('已从词库删除','success');
}
function usePromptFromLib(el){
  var wrapper=el.closest('[data-prompt-id]');
  if(!wrapper)return;
  var id=wrapper.getAttribute('data-prompt-id');
  var item=promptLibrary.find(function(p){return p.id===id});
  if(!item)return;
  var inputEl=document.getElementById('promptInput');
  if(inputEl.value&&!confirm('当前提示词已有内容，是否覆盖？')){return}
  inputEl.value=item.text;
  closePromptLib();
  toast('已填入提示词','success');
}
function showPromptLib(){renderPromptLib();document.getElementById('promptLibPanel').classList.add('show')}
function closePromptLib(){document.getElementById('promptLibPanel').classList.remove('show')}
function renderPromptLib(){
  var c=document.getElementById('promptLibList');
  var empty=document.getElementById('promptLibEmpty');
  c.querySelectorAll('.promptlib-item').forEach(function(el){el.remove()});
  if(!promptLibrary.length){if(empty)empty.style.display='';return}
  if(empty)empty.style.display='none';
  promptLibrary.forEach(function(item){
    var div=document.createElement('div');
    div.className='promptlib-item';
    var t=new Date(item.addedAt);
    var ts=String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0')+' '+String(t.getHours()).padStart(2,'0')+':'+String(t.getMinutes()).padStart(2,'0');
    div.setAttribute('data-prompt-id',item.id);
    div.innerHTML='<div class="promptlib-item-text" onclick="usePromptFromLib(this)">'+escHtml(item.text)+'</div>'
      +'<div class="promptlib-item-meta"><span>'+ts+'</span>'
      +'<button class="btn btn-xs btn-ghost" onclick="copyPromptText(this)">复制</button>'
      +'<button class="btn btn-xs btn-ghost" style="color:var(--red)" onclick="removeFromPromptLib(this)">删除</button></div>';
    c.appendChild(div);
  });
}
function copyPromptText(el){
  var wrapper=el.closest('[data-prompt-id]');
  if(!wrapper)return;
  var id=wrapper.getAttribute('data-prompt-id');
  var item=promptLibrary.find(function(p){return p.id===id});
  if(!item)return;
  navigator.clipboard.writeText(item.text).then(function(){toast('已复制','success')}).catch(function(){toast('复制失败','error')});
}
function exportPromptLib(){
  if(!promptLibrary.length){toast('提示词库为空','info');return}
  var b=new Blob([JSON.stringify(promptLibrary,null,2)],{type:'application/json'});
  var u=URL.createObjectURL(b);var a=document.createElement('a');
  a.href=u;a.download='prompt_library_'+new Date().toISOString().split('T')[0]+'.json';
  a.click();URL.revokeObjectURL(u);toast('提示词库已导出','success');
}
function importPromptLib(){document.getElementById('importPromptLibInput').click()}
function handleImportPromptLib(input){
  var file=input.files[0];if(!file)return;
  var reader=new FileReader();
  reader.onload=function(e){
    try{
      var data=JSON.parse(e.target.result);
      var arr=Array.isArray(data)?data:[data];
      var n=0;
      arr.forEach(function(item){
        if(item.text&&!promptLibrary.some(function(p){return p.text===item.text})){
          promptLibrary.push({id:item.id||Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,6),text:item.text,addedAt:item.addedAt||Date.now()});
          n++;
        }
      });
      if(n>0){savePromptLib();renderPromptLib();toast('导入'+n+'条提示词','success')}
      else{toast('无新提示词可导入','info')}
    }catch(err){toast('导入失败: '+err.message,'error')}
  };
  reader.readAsText(file);
  input.value='';
}
function clearPromptLib(){if(!confirm('确定清空提示词库？'))return;promptLibrary=[];savePromptLib();renderPromptLib();toast('提示词库已清空','success')}

// ===== 一键粘贴 =====
async function pasteToPrompt(){
  try{
    var text=await navigator.clipboard.readText();
    if(!text||!text.trim()){toast('剪贴板为空','info');return}
    var el=document.getElementById('promptInput');
    if(el.value&&!confirm('当前提示词已有内容，是否覆盖？'))return;
    el.value=text;
    toast('已粘贴','success');
  }catch(e){toast('无法读取剪贴板，请手动粘贴','error')}
}

// ===== 历史记录提示词操作 =====
function copyHistPrompt(el){
  var histId=el.closest('[data-hist-id]');
  if(!histId)return;
  var id=histId.getAttribute('data-hist-id');
  var h=generationHistory.find(function(x){return x.id===id});
  if(!h)return;
  navigator.clipboard.writeText(h.prompt).then(function(){toast('已复制提示词','success')}).catch(function(){toast('复制失败','error')});
}
function addHistPromptToLib(el){
  var histId=el.closest('[data-hist-id]');
  if(!histId)return;
  var id=histId.getAttribute('data-hist-id');
  var h=generationHistory.find(function(x){return x.id===id});
  if(!h)return;
  addToPromptLib(h.prompt);
}

// 从localStorage恢复url类型图片到liveImages
function restoreLiveImages(){
  generationHistory.forEach(h=>{
    if(h.images&&h.images.length){
      const restored=h.images.filter(img=>img.type==='url'&&img.value).map(img=>({type:img.type,value:img.value}));
      if(restored.length) liveImages.set(h.id,restored);
    }
    if(h.startedAt&&h.startedAt>0){taskStartTimes.set(h.id,h.startedAt)}
    else if(h.timestamp){taskStartTimes.set(h.id,h.timestamp)}
  });
}

function markInterruptedTasks(){
  let changed=false;
  generationHistory.forEach(h=>{if(h.status==='running'||h.status==='queued'){h.status='error';h.error='页面刷新，任务已中断';h.progressText='已中断';changed=true}});
  if(changed){saveHistory()}
}

function defaultState(){return{accounts:[],abandonedAccounts:[],settings:{defaultPassword:'Ml@2026Proxy',rotationStrategy:'most-credits',autoCheckin:true,autoRegister:true,theme:'system'},activeAccountIndex:-1,rotationIndex:0,lastAutoDay:''}}
function loadState(){try{const r=localStorage.getItem(STATE_KEY);if(r){const s=JSON.parse(r);return{...defaultState(),...s,settings:{...defaultState().settings,...(s.settings||{})}}}}catch(e){}return defaultState()}
function saveState(){localStorage.setItem(STATE_KEY,JSON.stringify(state))}
function loadHistory(){try{const r=localStorage.getItem(HISTORY_KEY);if(r)return JSON.parse(r)}catch(e){}return[]}
function saveHistory(){try{localStorage.setItem(HISTORY_KEY,JSON.stringify(generationHistory))}catch(e){}}

function addHistory(entry){
  if(entry.images&&entry.images.length){
    liveImages.set(entry.id,entry.images.map(img=>({type:img.type,value:img.value})));
    entry.images=entry.images.map(img=>{if(img.type==='url')return{type:'url',value:img.value};return{type:'live',value:'in_liveImages'}});
  }
  generationHistory.unshift(entry);
  if(generationHistory.length>300){const removed=generationHistory.splice(300);removed.forEach(h=>liveImages.delete(h.id))}
  saveHistory();
  try{renderHistoryItem(entry)}catch(e){console.warn('renderHistoryItem failed:',e)}
}

function updateHistory(id,updates){
  const idx=generationHistory.findIndex(h=>h.id===id);
  if(idx<0)return;
  const h=generationHistory[idx];
  if(updates.images&&updates.images.length){
    const first=updates.images[0];
    if(first&&first.type!=='live'){
      liveImages.set(id,updates.images.map(img=>({type:img.type,value:img.value})));
      updates.images=updates.images.map(img=>{if(img.type==='url')return{type:'url',value:img.value};return{type:'live',value:'in_liveImages'}});
    }
  }
  Object.assign(h,updates);
  saveHistory();
  try{patchHistoryItem(h)}catch(e){console.warn('patchHistoryItem failed:',e)}
}

function clearHistory(){if(!confirm('确定清空历史？'))return;generationHistory=[];liveImages.clear();saveHistory();renderFullHistory();toast('历史已清空','success')}

// ===== 图片错误处理 =====
function handleImgError(img){
  if(img._err)return;
  img._err=1;
  var rawSrc=img.dataset.raw||'';
  if(rawSrc.startsWith('http')){img._err=0;tryConvertUrlToB64(img,rawSrc);return}
  img.style.display='none';
  var p=img.parentElement;
  var a=document.createElement('a');
  a.href=img.dataset.raw;a.target='_blank';a.textContent='查看和保存原图';a.className='hist-img-link';
  p.appendChild(a);
}

async function tryConvertUrlToB64(imgEl,rawUrl){
  try{
    var proxyUrl='/api/media-proxy?url='+encodeURIComponent(rawUrl);
    var resp=await fetch(proxyUrl);
    if(!resp.ok)throw new Error('proxy failed: '+resp.status);
    var blob=await resp.blob();
    var reader=new FileReader();
    reader.onload=function(){
      var b64Url=reader.result;
      imgEl.src=b64Url;imgEl.style.display='';
      var histId=imgEl.closest('[data-hist-id]');
      if(histId){
        var id=histId.getAttribute('data-hist-id');
        var imgs=liveImages.get(id);
        if(imgs){imgs.forEach(function(im){if(im.value===rawUrl||im.type==='url'&&im.value===rawUrl){im.type='b64';im.value=b64Url}});var hist=generationHistory.find(function(h){return h.id===id});if(hist)saveHistory()}
      }
    };
    reader.readAsDataURL(blob);
  }catch(e){
    console.warn('图片代理转换失败:',e.message);
    imgEl._err=1;imgEl.style.display='none';
    var p=imgEl.parentElement;var a=document.createElement('a');
    a.href=rawUrl;a.target='_blank';a.textContent='查看和保存原图';a.className='hist-img-link';p.appendChild(a);
  }
}

// ===== API =====
async function apiFetch(path,options={}){
  const url='/api'+path;const st=options._sessionToken||null;
  const headers={'Content-Type':'application/json',...(options.headers||{})};
  if(st)headers['X-Session-Token']=st;
  return fetch(url,{...options,headers,credentials:'omit'});
}

function generateUsername(){
  var firstNames=['emily','sarah','michael','david','jessica','james','ashley','chris','amanda','daniel','stephanie','joshua','nicole','andrew','samantha','ryan','lauren','justin','rachel','brandon','megan','tyler','katherine','kevin','elizabeth','brian','jennifer','jason','michelle','patrick','kimberly','travis','heather','nathan','courtney','maria','alex','lisa','robert','john'];
  var lastNames=['chen','wang','li','zhang','smith','johnson','lee','brown','garcia','martinez','wilson','taylor','thomas','moore','jackson','white','harris','clark','lewis','robinson','walker','young','allen','king','wright','scott','hill','green','adams','baker'];
  var adjectives=['happy','lucky','cool','sunny','swift','calm','bold','bright','dreamy','fresh','kind','wild','pure','warm','zen','chill','neon','cosmic','pixel','sage'];
  var nouns=['cat','fox','moon','star','sky','bear','wolf','deer','fish','hawk','tree','lake','rain','wave','wind','seed','leaf','snow','dawn','ray'];
  var fn=firstNames[Math.floor(Math.random()*firstNames.length)];
  var ln=lastNames[Math.floor(Math.random()*lastNames.length)];
  var adj=adjectives[Math.floor(Math.random()*adjectives.length)];
  var noun=nouns[Math.floor(Math.random()*nouns.length)];
  var pattern=Math.floor(Math.random()*5);
  var r2=Math.floor(10+Math.random()*90);
  var r3=Math.floor(100+Math.random()*900);
  var capitalize=function(s){return s.charAt(0).toUpperCase()+s.slice(1)};
  var sometimesCap=function(s){return Math.random()>0.5?capitalize(s):s};
  switch(pattern){
    case 0:return sometimesCap(fn)+'_'+sometimesCap(ln);
    case 1:return sometimesCap(fn)+sometimesCap(ln)+r2;
    case 2:return sometimesCap(fn)+r3;
    case 3:return adj+'_'+noun+r2;
    case 4:return sometimesCap(fn)+'.'+sometimesCap(ln)+r2;
    default:return fn+'_'+ln;
  }
}
function generatePassword(){var base=state.settings.defaultPassword||'Ml@2026Proxy';var d=new Date();var yy=String(d.getFullYear()).slice(-2);var mm=String(d.getMonth()+1).padStart(2,'0');var dd=String(d.getDate()).padStart(2,'0');return base+yy+mm+dd}

// ===== 注册 =====
async function registerAccount(){
  const u=generateUsername(),pw=generatePassword();
  try{
    const r=await fetch('https://grok.17nas.com/local-api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:pw}),credentials:'omit'});
    if(r.ok){const d=await r.json();const a={username:u,password:pw,sessionToken:'',credits:d.user?.imageCredits||3,lastCheckinDay:'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:d.user?.id||'',loginFailCount:0,lastLoginFailTs:0};state.accounts.push(a);if(state.activeAccountIndex<0)state.activeAccountIndex=0;saveState();renderAll();toast('直接注册成功: '+u,'success');try{await loginAccount(state.accounts.length-1)}catch(e){}return state.accounts[state.accounts.length-1]}
  }catch(e){if(e.name==='TypeError')toast('直接注册被CORS阻止，使用代理...','info')}
  const maxRetries=6;let lastErr='';
  for(let attempt=0;attempt<maxRetries;attempt++){
    try{
      if(attempt>0){const delay=500+Math.floor(Math.random()*1500);toast('第'+(attempt+1)+'次重试(换IP)...','info');await sleep(delay)}
      const r=await apiFetch('/auth/register',{method:'POST',body:JSON.stringify({username:u,password:pw})});
      const d=await r.json();if(!r.ok)throw new Error(d.error||'注册失败: HTTP '+r.status);
      const st=r.headers.get('X-Session-Token')||'';
      const a={username:u,password:pw,sessionToken:st,credits:d.user?.imageCredits||3,lastCheckinDay:'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:d.user?.id||'',loginFailCount:0,lastLoginFailTs:0};
      state.accounts.push(a);if(state.activeAccountIndex<0)state.activeAccountIndex=0;
      saveState();renderAll();toast('注册成功: '+u+' ('+a.credits+'额度)','success');return a;
    }catch(e){lastErr=e.message;if(e.message.includes('已注册')&&attempt<maxRetries-1)continue;if(!e.message.includes('已注册'))break}
  }
  toast('自动注册失败: '+lastErr,'error');
  if(lastErr.includes('已注册')){toast('IP限制：当前网络今日已注册过账号，请手动添加账号或明天再试','error');window.open('https://grok.17nas.com','_blank')}
  throw new Error(lastErr);
}

// ===== 登录/签到/额度 =====
async function loginAccount(i){const a=state.accounts[i];if(!a)return;if(Date.now()<(a.cooldownUntil||0)){toast(a.username+' 登录冷却中，请等待'+Math.ceil(((a.cooldownUntil||0)-Date.now())/60000)+'分钟','info');throw new Error('登录冷却中')}try{const r=await apiFetch('/auth/login',{method:'POST',body:JSON.stringify({username:a.username,password:a.password})});const d=await r.json();if(!r.ok){const errMsg=d.error||'登录失败';if(errMsg.includes('用户名或密码错误')||errMsg.includes('Invalid credentials')){a.loginFailCount=(a.loginFailCount||0)+1;a.lastLoginFailTs=Date.now();a.cooldownUntil=Date.now()+300000;if(a.loginFailCount>=2){var abandoned={username:a.username,password:a.password,abandonedAt:Date.now(),loginFailCount:a.loginFailCount,lastLoginFailTs:a.lastLoginFailTs};state.abandonedAccounts.push(abandoned);state.accounts.splice(i,1);if(state.activeAccountIndex>=state.accounts.length)state.activeAccountIndex=Math.max(0,state.accounts.length-1);saveState();renderAll();renderAccountsTable();toast('用户名 '+abandoned.username+' 疑似被废弃，已移至废弃池','error');throw new Error(errMsg)}}saveState();throw new Error(errMsg)}a.sessionToken=r.headers.get('X-Session-Token')||'';a.credits=d.user?.imageCredits||a.credits;a.lastCheckinDay=d.user?.lastCheckInDay||a.lastCheckinDay;a.userId=d.user?.id||a.userId;a.loginFailCount=0;a.lastLoginFailTs=0;a.cooldownUntil=0;saveState();renderAll();return d}catch(e){console.warn('登录'+a.username+'失败:',e.message);throw e}}
async function checkinAccount(i){const a=state.accounts[i];if(!a||!a.sessionToken)await loginAccount(i);const acc=state.accounts[i];try{const r=await apiFetch('/account/checkin',{method:'POST',body:JSON.stringify({}),_sessionToken:acc.sessionToken});const d=await r.json();if(!r.ok)throw new Error(d.error||'签到失败');acc.credits=d.user?.imageCredits||acc.credits;acc.lastCheckinDay=d.checkIn?.today||'';acc.lastCheckinTs=Date.now();saveState();renderAll();toast(acc.username+' 签到+'+(d.grantedImages||3),'success');return d}catch(e){if(e.message.includes('已经签到')){acc.lastCheckinDay=new Date().toISOString().split('T')[0];acc.lastCheckinTs=Date.now();saveState();renderAll();renderAccountsTable();toast(acc.username+' 今日已签到','info');return}toast(acc.username+' 签到失败: '+e.message,'error');throw e}}
async function refreshQuota(i){const a=state.accounts[i];if(!a)return;if(!a.sessionToken)try{await loginAccount(i)}catch(e){return}const acc=state.accounts[i];try{const r=await apiFetch('/account/quota',{_sessionToken:acc.sessionToken});const d=await r.json();if(!r.ok){if(d.error&&(d.error.includes('token')||d.error.includes('session')||d.error.includes('登录')||d.error.includes('expired'))){acc.sessionToken='';saveState();renderAll()}throw new Error(d.error||'查询额度失败')}acc.credits=d.user?.imageCredits??acc.credits;acc.lastCheckinDay=d.checkIn?.today||acc.lastCheckinDay;saveState();renderAll();return d}catch(e){toast('查询'+acc.username+'额度失败','error')}}

async function autoRegister(){await registerAccount()}
async function addManualAccount(){const u=prompt('请输入用户名:');if(!u||!u.trim())return;const pw=prompt('请输入密码:');if(!pw||!pw.trim())return;const username=u.trim(),password=pw.trim();if(state.accounts.some(a=>a.username===username)){toast('该用户名已存在','error');return}state.accounts.push({username,password,sessionToken:'',credits:0,lastCheckinDay:'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:'',loginFailCount:0,lastLoginFailTs:0});if(state.activeAccountIndex<0)state.activeAccountIndex=0;saveState();renderAll();toast('账号已添加，正在登录...','success');try{await loginAccount(state.accounts.length-1);await refreshQuota(state.accounts.length-1)}catch(e){toast('登录失败，请检查账号密码','error')}}
async function checkinAll(){const today=new Date().toISOString().split('T')[0];const need=state.accounts.filter(a=>!a.disabled&&a.lastCheckinDay!==today);if(!need.length){toast('所有账号今日已签到','info');return}toast('开始签到'+need.length+'个账号...','info');for(const a of need){try{await checkinAccount(state.accounts.indexOf(a));await sleep(800)}catch(e){}}toast('批量签到完成','success')}
async function refreshAllQuota(){if(!state.accounts.length){toast('暂无账号','info');return}toast('正在刷新额度...','info');for(let i=0;i<state.accounts.length;i++){if(!state.accounts[i].disabled){await refreshQuota(i);await sleep(400)}}toast('额度刷新完成','success')}
async function batchVerifyAccounts(){if(!state.accounts.length){toast('暂无账号','info');return}toast('开始批量验证(只读额度查询)...','info');var okN=0,deadN=0,coolN=0;for(var i=0;i<state.accounts.length;i++){var a=state.accounts[i];if(a.disabled)continue;if(Date.now()<(a.cooldownUntil||0)){coolN++;continue}if(!a.sessionToken){try{await loginAccount(i);okN++}catch(e){deadN++}await sleep(300);continue}try{var r=await apiFetch('/account/quota',{_sessionToken:a.sessionToken});if(r.ok){okN++;var d=await r.json();a.credits=d.user?.imageCredits??a.credits;saveState();renderAll()}else{a.sessionToken='';saveState();try{await loginAccount(i);okN++}catch(e){deadN++}}}catch(e){a.sessionToken='';saveState();try{await loginAccount(i);okN++}catch(e2){deadN++}}await sleep(500)}renderAccountsTable();toast('验证完成: '+okN+'个可用'+(deadN?'，'+deadN+'个失效':'')+(coolN?'，'+coolN+'个冷却中':''),okN>0?'success':'error')}

// ===== 账号选择 =====
function selectAccount(){const avail=state.accounts.map((a,i)=>({...a,_i:i})).filter(a=>!a.disabled&&a.credits>0&&a.sessionToken);if(!avail.length)return null;switch(state.settings.rotationStrategy){case'most-credits':avail.sort((a,b)=>b.credits-a.credits);return avail[0];case'round-robin':state.rotationIndex=state.rotationIndex%avail.length;const p=avail[state.rotationIndex];state.rotationIndex++;saveState();return p;case'newest':avail.sort((a,b)=>b.createdAt-a.createdAt);return avail[0];default:return avail[0]}}
async function ensureAccount(){let a=selectAccount();if(a)return a;for(let i=0;i<state.accounts.length;i++){if(!state.accounts[i].disabled&&!state.accounts[i].sessionToken)try{await loginAccount(i)}catch(e){}}a=selectAccount();if(a)return a;if(state.settings.autoCheckin){const today=new Date().toISOString().split('T')[0];for(const acc of state.accounts.filter(a=>!a.disabled&&a.lastCheckinDay!==today)){try{await checkinAccount(state.accounts.indexOf(acc))}catch(e){}}a=selectAccount();if(a)return a}const totalCredits=state.accounts.filter(a=>!a.disabled).reduce((s,a)=>s+(a.credits||0),0);if(totalCredits<=0){toast('所有账号额度为0，正在自动注册新账号...','info')}if(state.settings.autoRegister){try{await registerAccount()}catch(e){return null}a=selectAccount();if(a)return a}return null}

// ===== 并发生成 =====
function maxConcurrency(){return state.accounts.filter(a=>!a.disabled&&a.credits>0&&a.sessionToken).length*CONCURRENT_PER_ACCOUNT}
function availableSlots(){return Math.max(0,maxConcurrency()-activeSlots)}
function getGptSize(r){
  if(r==='auto')return null;
  r=r||'1:1';
  var sizeMap={
    '1:1':'1024x1024',
    '3:2':'1536x1024','2:3':'1024x1536',
    '16:9':'1792x1024','9:16':'1024x1792',
    '4:3':'1536x1152','3:4':'1152x1536',
    '5:4':'1280x1024','4:5':'1024x1280',
    '2:1':'1792x896','1:2':'896x1792',
    '21:9':'1792x768','9:21':'768x1792'
  };
  return sizeMap[r]||'1024x1024';
}
function isGptImgInner(m){return/\\bgpt-image-\\d+\\b/.test(m)||m==='gpt-image-1'||m==='gpt-image-2'}
function isVideoModelInner(m){return m==='grok-imagine-video'}
function supportsRefImageInner(m){return isGptImgInner(m)||isVideoModelInner(m)}

async function startGeneration(){
  const prompt=document.getElementById('promptInput').value.trim();
  if(!prompt){toast('请输入提示词','error');return}
  const model=document.getElementById('modelSelect').value;
  const count=parseInt(document.getElementById('countSelect').value)||1;
  const size=getGptSize(selectedRatio);
  const hasRef=refImages.length>0&&supportsRefImageInner(model);
  const currentRefImages=[...refImages];
  const isVideo=isVideoModelInner(model);
  const duration=isVideo?parseInt(document.getElementById('durationSelect').value)||6:null;
  const btn=document.getElementById('generateBtn');btn.disabled=true;btn.textContent='提交中...';setTimeout(()=>{btn.disabled=false;btn.textContent=isVideo?'生成视频':'生成图片'},500);
  const entries=[];
  for(let i=0;i<count;i++){const entry={id:Date.now().toString(36)+'_'+i,prompt,model,ratio:selectedRatio,count,index:i+1,timestamp:Date.now(),status:'queued',images:[],error:'',account:'',progress:0,progressText:'排队中',startedAt:0,isVideo:isVideo,duration:duration};entries.push(entry);taskStartTimes.set(entry.id,Date.now());addHistory(entry)}
  toast(count+'个任务已加入队列','info');
  (async()=>{let submitted=0;while(submitted<entries.length){while(availableSlots()<=0){await sleep(500)}const entry=entries[submitted];submitted++;activeSlots++;updateConcurrencyUI();executeTask(entry,model,prompt,size,hasRef,currentRefImages,isVideo,duration).finally(()=>{activeSlots--;updateConcurrencyUI()});await sleep(300)}})();
}

async function executeTask(entry,model,prompt,size,hasRef,currentRefImages,isVideo,duration){
  let retryCount=0;const maxRetries=1;
  while(retryCount<=maxRetries){
    try{
      const acc=await ensureAccount();
      if(!acc){entry.status='error';entry.error='无可用账号';entry.progressText='失败';updateHistory(entry.id,{status:entry.status,error:entry.error,progressText:entry.progressText});toast(entry.error,'error');return}
      entry.account=acc.username;entry.status='running';entry.progressText='提交任务中...';entry.progress=5;entry.startedAt=Date.now();taskStartTimes.set(entry.id,entry.startedAt);
      updateHistory(entry.id,{status:entry.status,account:entry.account,progressText:entry.progressText,progress:entry.progress,startedAt:entry.startedAt});
      const body={model,prompt,n:1,response_format:'b64_json',endpointKind:hasRef?'edits':'generations',attachments:[]};
      if(isVideo&&duration){body.duration=duration}
      if(size&&!isVideo)body.size=size;
      if(selectedRatio!=='auto')body.requestAspectRatio=selectedRatio;
      if(hasRef&&currentRefImages){currentRefImages.forEach((img,idx)=>{body.attachments.push({name:img.name||('ref_'+idx+'.png'),type:img.type||'image/png',dataUrl:img.dataUrl})})}
      const r=await apiFetch('/proxy/image-tasks',{method:'POST',body:JSON.stringify(body),_sessionToken:acc.sessionToken});
      const d=await r.json();if(!r.ok){const errMsg=d.error||d.message||'创建任务失败';throw new Error(errMsg)}
      const ai=state.accounts.findIndex(a=>a.username===acc.username);if(ai>=0&&d.user){state.accounts[ai].credits=d.user.imageCredits??state.accounts[ai].credits;saveState();renderAll()}
      const tid=d.task?.id;if(!tid)throw new Error('未返回任务ID');
      entry.progressText='任务已提交，等待生成...';entry.progress=10;updateHistory(entry.id,{progressText:entry.progressText,progress:entry.progress});
      const res=await pollTask(tid,acc.sessionToken,entry);
      if(res){entry.status='success';entry.images=res.images;entry.progress=100;entry.progressText='生成完成';updateHistory(entry.id,{status:entry.status,images:entry.images,progress:entry.progress,progressText:entry.progressText});return}
    }catch(e){const errMsg=extractErrorMessage(e.message);if(retryCount<maxRetries){retryCount++;entry.status='running';entry.progressText='失败，准备重试 ('+retryCount+'/'+maxRetries+')';entry.progress=0;updateHistory(entry.id,{status:entry.status,progressText:entry.progressText,progress:entry.progress});await sleep(1500);continue}entry.status=errMsg.includes('超时')?'timeout':'error';entry.error=errMsg;entry.progressText='失败';updateHistory(entry.id,{status:entry.status,error:entry.error,progressText:entry.progressText});toast('第'+entry.index+'张失败: '+errMsg,'error');return}
  }
}

function extractErrorMessage(raw){const msg=raw||'未知错误';if(msg.includes('content_policy')||msg.includes('policy')||msg.includes('safety'))return'内容违反政策(OpenAI安全策略限制)';if(msg.includes('rate_limit'))return'请求频率超限，请稍后再试';if(msg.includes('insufficient_quota')||msg.includes('额度不足'))return'平台额度不足，请先签到或充值';if(msg.includes('超时')||msg.includes('timeout'))return'生成超时(300秒)，可能服务器繁忙';if(msg.includes('已注册'))return'当前IP今日已注册过账号';if(msg.includes('无效')||msg.includes('invalid'))return'请求参数无效: '+msg;if(msg.includes('failed'))return'生成失败: '+msg;return msg}

function mapProgressInfo(task,isVideo){const p=task.progress||0;const status=task.status||'';const detail=task.detail||task.statusText||'';if(status==='pending'||status==='queued')return{text:'排队等待中...',pct:5};if(status==='processing'||status==='running'){if(p<20)return{text:'正在分析提示词...',pct:15};if(p<40)return{text:isVideo?'正在生成视频初稿...':'正在生成图片初稿...',pct:30};if(p<60)return{text:isVideo?'正在细化视频细节...':'正在细化图片细节...',pct:50};if(p<80)return{text:isVideo?'正在渲染最终视频...':'正在渲染最终图片...',pct:70};if(p<95)return{text:'即将完成...',pct:88};return{text:'最后处理中...',pct:95}}if(detail)return{text:detail,pct:Math.max(10,Math.min(90,p))};return{text:'生成中... '+p+'%',pct:Math.max(10,Math.min(90,p))}}
function formatElapsed(ms){const s=Math.floor(ms/1000);if(s<60)return s+'秒';const m=Math.floor(s/60);return m+'分'+(s%60)+'秒'}

async function pollTask(tid,st,entry){
  const max=300*1000,start=Date.now();let errs=0;
  while(Date.now()-start<max){await sleep(2000);try{const r=await apiFetch('/proxy/image-tasks/'+encodeURIComponent(tid),{_sessionToken:st});const d=await r.json();if(!r.ok)throw new Error(d.error||'轮询失败');const t=d.task;if(!t)throw new Error('任务状态缺失');const pInfo=mapProgressInfo(t,entry.isVideo);entry.progress=pInfo.pct;entry.progressText=pInfo.text;updateHistory(entry.id,{progress:entry.progress,progressText:entry.progressText});if(t.status==='succeeded'){const p=t.payload;if(!p)throw new Error('任务成功但无图片数据');let images=[];if(p.data&&Array.isArray(p.data)){p.data.forEach(item=>{if(item.url)images.push({type:'url',value:item.url});else if(item.b64_json)images.push({type:'b64',value:'data:image/png;base64,'+item.b64_json})})}if(p.markdown){const m=p.markdown.match(/!\\[.*?\\]\\((.*?)\\)/g);if(m)m.forEach(x=>{const u=x.match(/\\((.*?)\\)/);if(u&&u[1]){const urlVal=u[1];if(urlVal.startsWith('data:')){images.push({type:'b64',value:urlVal})}else if(!images.some(im=>im.type==='b64')){images.push({type:'url',value:urlVal})}}})}if(!images.length&&p.markdown){const links=p.markdown.match(/https?:\\/\\/[^\\s\\)]+\\.png/g);if(links)links.forEach(link=>{if(link.startsWith('data:')){images.push({type:'b64',value:link})}else{images.push({type:link.match(/\\.(mp4|webm)$/)?'video':'url',value:link})}})}if(d.user){const ai=state.accounts.findIndex(a=>a.sessionToken===st);if(ai>=0){state.accounts[ai].credits=d.user.imageCredits??state.accounts[ai].credits;saveState();renderAll()}}return{images,model:t.model,taskId:tid}}if(t.status==='failed'){throw new Error(t.error||t.failReason||t.detail||'生成失败')}errs=0}catch(e){errs++;if(errs>=8)throw e;if(e.name==='AbortError')throw e;await sleep(2000*errs)}}
  throw new Error(entry.isVideo?'视频生成超时(300秒)':'图片生成超时(300秒)');
}

// ===== 渲染 =====
function renderAll(){renderTopbar();updateConcurrencyUI()}
function renderTopbar(){const usable=state.accounts.filter(a=>!a.disabled&&a.sessionToken).reduce((s,a)=>s+(a.credits||0),0);const total=state.accounts.filter(a=>!a.disabled).reduce((s,a)=>s+(a.credits||0),0);document.getElementById('usableCreditsTop').textContent=usable;document.getElementById('totalCreditsTop').textContent=total}
function updateConcurrencyUI(){const mx=maxConcurrency(),cur=activeSlots;document.getElementById('concurrencyInfo').textContent='并发: '+cur+'/'+mx;document.getElementById('concurrencyDetail').textContent='可用账号'+state.accounts.filter(a=>!a.disabled&&a.credits>0&&a.sessionToken).length+'个 x '+CONCURRENT_PER_ACCOUNT+' = '+mx+'并发槽位'}

// ===== 构建图片HTML =====
function buildImageHtml(h,imgs){
  var html='';
  var isVideo=h.isVideo||false;
  var hasB64=imgs.some(function(img){return img.type==='b64'});
  if(hasB64){html+='<div style="padding:4px 12px;font-size:.72rem;color:var(--orange);background:rgba(253,203,110,.08)">\\u26A0 部分数据为临时内容，刷新后将丢失，请及时保存</div>'}
  html+='<div class="hist-img-link">';
  imgs.forEach(function(img,imgIdx){
    var rawSrc;
    if(img.type==='b64'||img.value.startsWith('data:')){rawSrc=img.value}
    else if(img.value.startsWith('http')){rawSrc=img.value}
    else{rawSrc='https://grok.17nas.com'+(img.value.startsWith('/')?'':'/')+img.value}
    var dlHref=rawSrc.startsWith('data:')?rawSrc:rawSrc;
    var isVideoFile=img.type==='video'||rawSrc.match(/\\.(mp4|webm)(\\?|$)/i);
    if(isVideoFile){
      var videoSrc=proxyImageUrl(rawSrc);
      html+='<a href="'+dlHref+'" target="_blank" download="video_'+h.id+'_'+imgIdx+'.mp4">\\u2197 查看和保存视频</a>';
      html+='<video src="'+videoSrc+'" controls style="max-width:100%;max-height:300px;margin:4px 12px 8px;border-radius:6px;display:block"></video>';
    }else{
      html+='<a href="'+dlHref+'" target="_blank" download="image_'+h.id+'_'+imgIdx+'.png">\\u2197 查看和保存原图</a>';
    }
  });
  html+='</div>';
  return html;
}

// ===== 历史渲染 =====
function ensureEmptyEl(){let el=document.getElementById('historyEmpty');if(!el){const c=document.getElementById('historyList');el=document.createElement('p');el.id='historyEmpty';el.style.cssText='color:var(--fg3);text-align:center;padding:40px 0;font-size:.85rem';el.textContent='暂无历史记录';c.prepend(el)}return el}
function renderFullHistory(){const c=document.getElementById('historyList');c.querySelectorAll('.hist-item').forEach(el=>el.remove());const empty=ensureEmptyEl();if(!generationHistory.length){empty.style.display='';return}empty.style.display='none';for(let i=generationHistory.length-1;i>=0;i--){const el=buildHistoryElement(generationHistory[i]);if(empty.nextSibling){c.insertBefore(el,empty.nextSibling)}else{c.appendChild(el)}}}
function renderHistoryItem(h){const c=document.getElementById('historyList');const empty=ensureEmptyEl();empty.style.display='none';const el=buildHistoryElement(h);if(empty.nextSibling){c.insertBefore(el,empty.nextSibling)}else{c.appendChild(el)}}

function patchHistoryItem(h){
  const el=document.querySelector('[data-hist-id="'+h.id+'"]');if(!el){renderHistoryItem(h);return}
  const statusEl=el.querySelector('.hist-status');
  if(statusEl){const statusMap={success:{cls:'ok',label:'\\u2713成功'},error:{cls:'err',label:'\\u2717失败'},timeout:{cls:'timeout',label:'\\u23F1超时'},running:{cls:'running',label:'\\u25CF生成中'},queued:{cls:'queued',label:'\\u25CB排队中'}};const st=statusMap[h.status]||statusMap.error;statusEl.className='hist-status '+st.cls;statusEl.textContent=st.label}
  if(h.status==='running'||h.status==='queued'){el.classList.add('running-item')}else{el.classList.remove('running-item')}
  const progressContainer=el.querySelector('.hist-progress');
  if(h.status==='running'||h.status==='queued'){const startTs=taskStartTimes.get(h.id)||h.timestamp;const elapsed=Date.now()-startTs;const elapsedStr=formatElapsed(elapsed);if(progressContainer){progressContainer.querySelector('.pfill').style.width=Math.max(5,h.progress||0)+'%';progressContainer.querySelector('.ptxt').innerHTML=escHtml(h.progressText||'等待中')+'<span class="elapsed">'+elapsedStr+'</span>'}else{const promptEl=el.querySelector('.hist-prompt');const div=document.createElement('div');div.className='hist-progress';div.innerHTML='<div class="pbar"><div class="pfill" style="width:'+Math.max(5,h.progress||0)+'%"></div></div><div class="ptxt">'+escHtml(h.progressText||'等待中')+'<span class="elapsed">'+elapsedStr+'</span></div>';promptEl.after(div)}}else if(progressContainer){progressContainer.remove()}
  let errorEl=el.querySelector('.hist-error');if(h.error){if(errorEl){errorEl.textContent=h.error}else{const div=document.createElement('div');div.className='hist-error';div.textContent=h.error;const promptEl=el.querySelector('.hist-prompt');promptEl.after(div)}}
  if(h.status==='success'){const imgs=liveImages.get(h.id);if(imgs&&imgs.length&&!el.querySelector('.hist-img-link')){const imagesHtml=buildImageHtml(h,imgs);const errorEl2=el.querySelector('.hist-error');const promptActions=el.querySelector('.hist-prompt-actions');if(errorEl2){errorEl2.insertAdjacentHTML('afterend',imagesHtml)}else if(promptActions){promptActions.insertAdjacentHTML('afterend',imagesHtml)}else{const promptEl=el.querySelector('.hist-prompt');promptEl.insertAdjacentHTML('afterend',imagesHtml)}}}
}

function buildHistoryElement(h){
  const t=new Date(h.timestamp);
  const timeStr=String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0')+' '+String(t.getHours()).padStart(2,'0')+':'+String(t.getMinutes()).padStart(2,'0')+':'+String(t.getSeconds()).padStart(2,'0');
  const statusMap={success:{cls:'ok',label:'\\u2713成功'},error:{cls:'err',label:'\\u2717失败'},timeout:{cls:'timeout',label:'\\u23F1超时'},running:{cls:'running',label:'\\u25CF生成中'},queued:{cls:'queued',label:'\\u25CB排队中'}};
  const st=statusMap[h.status]||statusMap.error;
  const div=document.createElement('div');
  div.className='hist-item'+((h.status==='running'||h.status==='queued')?' running-item':'');
  div.setAttribute('data-hist-id',h.id);
  let inner='<div class="hist-header"><span class="hist-status '+st.cls+'">'+st.label+'</span><span style="font-size:.78rem;color:var(--fg2)">'+escHtml(h.model||'')+'</span>';
  if(h.account)inner+='<span style="font-size:.72rem;color:var(--fg3)">@'+escHtml(h.account)+'</span>';
  inner+='<span class="hist-time">'+timeStr+'</span></div>';
  inner+='<div class="hist-prompt">'+escHtml(h.prompt)+'</div>';
  inner+='<div class="hist-prompt-actions"><button class="btn btn-xs btn-ghost" onclick="copyHistPrompt(this)">复制</button><button class="btn btn-xs btn-ghost" onclick="addHistPromptToLib(this)">加入提示词库</button></div>';
  if(h.error)inner+='<div class="hist-error">'+escHtml(h.error)+'</div>';
  if(h.status==='running'||h.status==='queued'){const startTs=taskStartTimes.get(h.id)||h.timestamp;const elapsed=formatElapsed(Date.now()-startTs);inner+='<div class="hist-progress"><div class="pbar"><div class="pfill" style="width:'+Math.max(5,h.progress||0)+'%"></div></div><div class="ptxt">'+escHtml(h.progressText||'等待中')+'<span class="elapsed">'+elapsed+'</span></div></div>'}
  const imgs=liveImages.get(h.id);
  if(imgs&&imgs.length){inner+=buildImageHtml(h,imgs)}
  div.innerHTML=inner;
  return div;
}

function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function proxyImageUrl(src){if(!src)return src;if(src.startsWith('data:'))return src;if(src.startsWith('https://'))return src;if(src.startsWith('http://'))return '/api/media-proxy?url='+encodeURIComponent(src);return src}

setInterval(()=>{document.querySelectorAll('.hist-item.running-item').forEach(el=>{const id=el.getAttribute('data-hist-id');const startTs=taskStartTimes.get(id);if(!startTs)return;const elapsedEl=el.querySelector('.elapsed');if(elapsedEl)elapsedEl.textContent=formatElapsed(Date.now()-startTs)})},1000);

// ===== 参考图 =====
function handleRefImages(input){const files=Array.from(input.files).filter(f=>f.type.startsWith('image/'));if(!files.length)return;let pending=files.length;files.forEach(f=>{const r=new FileReader();r.onload=e=>{refImages.push({name:f.name,type:f.type,dataUrl:e.target.result});pending--;if(pending===0)renderRefGrid()};r.readAsDataURL(f)});input.value=''}
function addMoreRefImages(){document.getElementById('refFileInput').click()}
function renderRefGrid(){const g=document.getElementById('refGrid');if(!refImages.length){g.innerHTML='';return}g.innerHTML=refImages.map((img,i)=>'<div class="ref-thumb"><img src="'+img.dataUrl+'" alt="ref'+(i+1)+'"><span class="ref-del" onclick="removeRefImage('+i+')">&times;</span></div>').join('')+'<div class="ref-thumb" style="display:flex;align-items:center;justify-content:center;cursor:pointer;border-style:dashed;color:var(--fg3);font-size:1.2rem" onclick="addMoreRefImages()">+</div>'}
function removeRefImage(i){refImages.splice(i,1);renderRefGrid()}
const refEl=document.getElementById('refUpload');
refEl.addEventListener('dragover',e=>{e.preventDefault();refEl.classList.add('dragover')});
refEl.addEventListener('dragleave',()=>refEl.classList.remove('dragover'));
refEl.addEventListener('drop',e=>{e.preventDefault();refEl.classList.remove('dragover');const files=Array.from(e.dataTransfer.files).filter(f=>f.type.startsWith('image/'));if(!files.length)return;let pending=files.length;files.forEach(f=>{const r=new FileReader();r.onload=ev=>{refImages.push({name:f.name,type:f.type,dataUrl:ev.target.result});pending--;if(pending===0)renderRefGrid()};r.readAsDataURL(f)})});
document.querySelectorAll('.ratio-btn').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.ratio-btn').forEach(x=>x.classList.remove('active'));b.classList.add('active');selectedRatio=b.dataset.ratio}));

// ===== 设置弹窗 =====
function showSettingsModal(){renderAccountsTable();loadSettingsUI();document.getElementById('settingsModal').classList.add('show')}
function closeSettingsModal(){document.getElementById('settingsModal').classList.remove('show')}
function renderAccountsTable(){const today=new Date().toISOString().split('T')[0],c=document.getElementById('accountsTableContainer');if(!state.accounts.length){c.innerHTML='<p style="color:var(--fg3);text-align:center;padding:20px">暂无账号</p>'}else{c.innerHTML='<table class="accounts-table"><thead><tr><th>用户名</th><th>密码</th><th>额度</th><th>签到</th><th>操作</th></tr></thead><tbody>'+state.accounts.map((a,i)=>'<tr><td style="font-family:var(--mono);font-size:.8rem;'+(a.disabled?'opacity:.5;text-decoration:line-through':'')+'">'+escHtml(a.username)+'</td><td style="font-family:var(--mono);font-size:.75rem;cursor:pointer" onclick="navigator.clipboard.writeText(this.textContent).then(function(){toast(\\'已复制密码\\',\\'success\\')}).catch(function(){})" title="点击复制密码">'+escHtml(a.password||'')+'</td><td>'+a.credits+'</td><td>'+(a.lastCheckinDay===today?'<span style="color:var(--green)">\\u2713</span>':'<span style="color:var(--orange)">\\u2717</span>')+'</td><td><button class="btn btn-sm" onclick="loginAndRefresh('+i+')">登录</button> <button class="btn btn-sm" onclick="checkinAccount('+i+')" '+(a.lastCheckinDay===today?'disabled':'')+'>签到</button> <button class="btn btn-sm btn-danger" onclick="removeAccount('+i+')">删除</button></td></tr>').join('')+'</tbody></table>'}renderAbandonedPool()}
async function loginAndRefresh(i){try{await loginAccount(i);await refreshQuota(i);renderAccountsTable()}catch(e){}}
function removeAccount(i){if(!confirm('确定删除'+state.accounts[i].username+'？'))return;state.accounts.splice(i,1);if(state.activeAccountIndex>=state.accounts.length)state.activeAccountIndex=state.accounts.length-1;saveState();renderAll();renderAccountsTable();toast('已删除','success')}
function renderAbandonedPool(){var c=document.getElementById('abandonedPoolContainer');if(!c)return;var ab=state.abandonedAccounts||[];if(!ab.length){c.innerHTML='';return}var rows=ab.map(function(a,i){var d=new Date(a.abandonedAt||Date.now());var ts=String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');return '<tr><td style="font-family:var(--mono);font-size:.8rem;color:var(--fg3)">'+escHtml(a.username)+'</td><td style="font-family:var(--mono);font-size:.75rem;cursor:pointer;color:var(--fg3)" onclick="navigator.clipboard.writeText(this.textContent).then(function(){toast(\\'已复制密码\\',\\'success\\')}).catch(function(){})" title="点击复制密码">'+escHtml(a.password||'')+'</td><td style="font-size:.78rem;color:var(--fg3)">'+ts+'</td><td><button class="btn btn-xs" onclick="reverifyAbandoned('+i+')">重新验证</button> <button class="btn btn-xs" onclick="restoreAbandoned('+i+')">还原</button> <button class="btn btn-xs btn-danger" onclick="deleteAbandoned('+i+')">删除</button></td></tr>'}).join('');c.innerHTML='<div style="border-top:1px solid var(--bg4);padding-top:12px;margin-top:4px"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><span style="font-size:.85rem;color:var(--orange);font-weight:600">\\u26A0 废弃账号池 ('+ab.length+')</span><div style="display:flex;gap:6px"><button class="btn btn-xs" onclick="reverifyAllAbandoned()">一键验证全部</button><button class="btn btn-xs btn-danger" onclick="clearAbandoned()">一键清空</button></div></div><table class="accounts-table"><thead><tr><th>用户名</th><th>密码</th><th>废弃时间</th><th>操作</th></tr></thead><tbody>'+rows+'</tbody></table></div>'}
async function reverifyAbandoned(i){var ab=state.abandonedAccounts||[];if(!ab[i])return;var a=ab[i];toast('正在验证 '+a.username+'...','info');try{var r=await apiFetch('/auth/login',{method:'POST',body:JSON.stringify({username:a.username,password:a.password})});var d=await r.json();if(r.ok){var st=r.headers.get('X-Session-Token')||'';state.accounts.push({username:a.username,password:a.password,sessionToken:st,credits:d.user?.imageCredits||0,lastCheckinDay:d.user?.lastCheckInDay||'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:d.user?.id||'',loginFailCount:0,lastLoginFailTs:0});ab.splice(i,1);state.abandonedAccounts=ab;saveState();renderAll();renderAccountsTable();toast(a.username+' 验证成功，已还原到活跃池','success')}else{toast(a.username+' 验证失败: '+(d.error||'登录失败'),'error');await sleep(2500)}}catch(e){toast(a.username+' 验证失败: '+e.message,'error');await sleep(2500)}}
async function reverifyAllAbandoned(){var ab=state.abandonedAccounts||[];if(!ab.length){toast('废弃池为空','info');return}toast('开始验证 '+ab.length+' 个废弃账号...','info');var okN=0,failN=0;for(var i=ab.length-1;i>=0;i--){try{var a=ab[i];var r=await apiFetch('/auth/login',{method:'POST',body:JSON.stringify({username:a.username,password:a.password})});var d=await r.json();if(r.ok){var st=r.headers.get('X-Session-Token')||'';state.accounts.push({username:a.username,password:a.password,sessionToken:st,credits:d.user?.imageCredits||0,lastCheckinDay:d.user?.lastCheckInDay||'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:d.user?.id||'',loginFailCount:0,lastLoginFailTs:0});ab.splice(i,1);okN++}else{failN++}await sleep(2500)}catch(e){failN++;await sleep(2500)}}state.abandonedAccounts=ab;saveState();renderAll();renderAccountsTable();toast('验证完成: '+okN+'个还原成功'+(failN?'，'+failN+'个仍失败':''),okN>0?'success':'error')}
function clearAbandoned(){if(!confirm('确定清空所有废弃账号？此操作不可恢复！'))return;state.abandonedAccounts=[];saveState();renderAccountsTable();toast('废弃池已清空','success')}
function deleteAbandoned(i){var ab=state.abandonedAccounts||[];if(!ab[i])return;if(!confirm('确定删除废弃账号 '+ab[i].username+'？'))return;ab.splice(i,1);state.abandonedAccounts=ab;saveState();renderAccountsTable();toast('已删除','success')}
function restoreAbandoned(i){var ab=state.abandonedAccounts||[];if(!ab[i])return;var a=ab[i];state.accounts.push({username:a.username,password:a.password,sessionToken:'',credits:0,lastCheckinDay:'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:'',loginFailCount:0,lastLoginFailTs:0});ab.splice(i,1);state.abandonedAccounts=ab;if(state.activeAccountIndex<0)state.activeAccountIndex=0;saveState();renderAll();renderAccountsTable();toast(a.username+' 已还原到活跃池（需手动登录验证）','success')}
function saveSettings(){state.settings.defaultPassword=document.getElementById('defaultPassword').value.trim()||'Ml@2026Proxy';state.settings.rotationStrategy=document.getElementById('rotationStrategy').value;state.settings.autoCheckin=document.getElementById('autoCheckin').checked;state.settings.autoRegister=document.getElementById('autoRegisterChk').checked;saveState();toast('设置已保存','success')}
function loadSettingsUI(){document.getElementById('defaultPassword').value=state.settings.defaultPassword||'Ml@2026Proxy';document.getElementById('rotationStrategy').value=state.settings.rotationStrategy||'most-credits';document.getElementById('autoCheckin').checked=state.settings.autoCheckin!==false;document.getElementById('autoRegisterChk').checked=state.settings.autoRegister!==false;applyTheme()}
function exportAccounts(){const d={accounts:state.accounts.map(a=>({username:a.username,password:a.password})),abandonedAccounts:(state.abandonedAccounts||[]).map(a=>({username:a.username,password:a.password,abandonedAt:a.abandonedAt}))};const b=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='ai_image_generator_accounts_'+new Date().toISOString().split('T')[0]+'.json';a.click();URL.revokeObjectURL(u);toast('已导出（含废弃池）','success')}
function importAccounts(){document.getElementById('importFileInput').click()}
async function handleImportFile(input){const file=input.files[0];if(!file)return;try{const txt=await file.text();const data=JSON.parse(txt);var arr=Array.isArray(data)?data:(data.accounts||[data]);let n=0;arr.forEach(item=>{if(item.username&&item.password&&!state.accounts.some(a=>a.username===item.username)){state.accounts.push({username:item.username,password:item.password,sessionToken:'',credits:0,lastCheckinDay:'',lastCheckinTs:0,createdAt:Date.now(),disabled:false,userId:'',loginFailCount:0,lastLoginFailTs:0});n++}});var abArr=data.abandonedAccounts||[];let abN=0;abArr.forEach(item=>{if(item.username&&item.password&&!(state.abandonedAccounts||[]).some(a=>a.username===item.username)&&!state.accounts.some(a=>a.username===item.username)){if(!state.abandonedAccounts)state.abandonedAccounts=[];state.abandonedAccounts.push({username:item.username,password:item.password,abandonedAt:item.abandonedAt||Date.now()});abN++}});if(n>0||abN>0){if(state.activeAccountIndex<0)state.activeAccountIndex=0;saveState();renderAll();var msg='';if(n>0)msg+='导入'+n+'个账号';if(abN>0)msg+=(msg?'，':'')+'导入'+abN+'个废弃账号';toast(msg+'，正在登录...','success');for(let i=0;i<state.accounts.length;i++){if(!state.accounts[i].sessionToken&&!state.accounts[i].disabled){try{await loginAccount(i);await sleep(300)}catch(e){}}}}else{toast('无新账号可导入','info')}}catch(e){toast('导入失败: '+e.message,'error')}input.value=''}
function clearAllData(){if(!confirm('确定清除所有数据？'))return;state=defaultState();saveState();generationHistory=[];liveImages.clear();saveHistory();promptLibrary=[];savePromptLib();renderFullHistory();renderAll();loadSettingsUI();toast('已清除','success')}

// ===== 历史记录导入导出 =====
function exportHistory(){if(!generationHistory.length){toast('暂无历史记录可导出','info');return}var exportData=generationHistory.map(function(h){var entry={id:h.id,prompt:h.prompt,model:h.model,ratio:h.ratio,timestamp:h.timestamp,status:h.status,error:h.error||'',account:h.account||'',startedAt:h.startedAt||0};if(h.images&&h.images.length){var imgs=liveImages.get(h.id);entry.images=h.images.map(function(img,idx){if(img.type==='url')return{type:'url',value:img.value};if(imgs&&imgs[idx]&&(imgs[idx].type==='b64'||imgs[idx].value.startsWith('data:'))){return{type:'b64',value:imgs[idx].value}}return{type:img.type,value:img.value}})}return entry});var b=new Blob([JSON.stringify(exportData,null,2)],{type:'application/json'});var u=URL.createObjectURL(b);var a=document.createElement('a');a.href=u;a.download='ai_image_generator_history_'+new Date().toISOString().split('T')[0]+'.json';a.click();URL.revokeObjectURL(u);toast('历史记录已导出','success')}
function importHistory(){document.getElementById('importHistoryInput').click()}
function handleImportHistory(input){var file=input.files[0];if(!file)return;var reader=new FileReader();reader.onload=function(e){try{var data=JSON.parse(e.target.result);var arr=Array.isArray(data)?data:[data];var n=0;arr.forEach(function(item){if(!item.id||!item.prompt)return;if(generationHistory.some(function(h){return h.id===item.id}))return;generationHistory.push(item);if(item.images&&item.images.length){var restored=item.images.filter(function(img){return img.type==='url'&&img.value}).map(function(img){return{type:img.type,value:img.value}});if(restored.length)liveImages.set(item.id,restored);var b64restored=item.images.filter(function(img){return img.type==='b64'&&img.value&&img.value.startsWith('data:')}).map(function(img){return{type:img.type,value:img.value}});if(b64restored.length){if(!liveImages.has(item.id))liveImages.set(item.id,[]);var existing=liveImages.get(item.id);b64restored.forEach(function(br){if(!existing.some(function(e){return e.value===br.value}))existing.push(br)})}}if(item.startedAt&&item.startedAt>0)taskStartTimes.set(item.id,item.startedAt);else if(item.timestamp)taskStartTimes.set(item.id,item.timestamp);n++});if(n>0){saveHistory();renderFullHistory();toast('导入'+n+'条历史记录','success')}else{toast('无新历史记录可导入','info')}}catch(err){toast('导入失败: '+err.message,'error')}};reader.readAsText(file);input.value=''}

// ===== 水印功能 =====
var wmState={baseImg:null,wmImg:null,wmX:50,wmY:50,wmScale:20,wmAlpha:50,dragging:false,dragStartX:0,dragStartY:0,dragOrigX:0,dragOrigY:0};
function openWatermarkModal(){document.getElementById('watermarkPanel').classList.add('show');wmState.baseImg=null;wmState.wmImg=null;wmState.wmScale=20;wmState.wmAlpha=50;wmState.wmX=50;wmState.wmY=50;wmState.dragging=false;document.getElementById('wmBaseFileInput').value='';document.getElementById('wmFileInput').value='';document.getElementById('wmBasePreviewArea').innerHTML='';document.getElementById('wmPreviewArea').innerHTML='';document.getElementById('wmPlaceholder').style.display='flex';document.getElementById('wmPlaceholder').textContent='请先上传成品图片';document.getElementById('wmCanvas').style.display='none';updateWmSliders()}
function closeWatermarkModal(){document.getElementById('watermarkPanel').classList.remove('show');wmState.baseImg=null;wmState.wmImg=null}
function handleWmBaseUpload(input){var file=input.files[0];if(!file)return;var reader=new FileReader();reader.onload=function(e){var image=new Image();image.onload=function(){wmState.baseImg=image;wmState.wmImg=null;wmState.wmX=50;wmState.wmY=50;var canvas=document.getElementById('wmCanvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;document.getElementById('wmPlaceholder').style.display='none';canvas.style.display='block';updateWmSliders();drawWatermarkCanvas();var area=document.getElementById('wmBasePreviewArea');area.innerHTML='<div class="wm-preview-row"><img class="wm-preview-thumb" src="'+e.target.result+'"><span style="font-size:.75rem;color:var(--fg3)">'+file.name+' ('+image.naturalWidth+'x'+image.naturalHeight+')</span></div>';toast('成品图已加载，请上传水印图片','success')};image.onerror=function(){toast('无法加载成品图片','error')};image.src=e.target.result};reader.readAsDataURL(file);input.value=''}
function handleWmUpload(input){var file=input.files[0];if(!file)return;if(!wmState.baseImg){toast('请先上传成品图片','error');input.value='';return}var reader=new FileReader();reader.onload=function(e){var image=new Image();image.onload=function(){wmState.wmImg=image;wmState.wmX=50;wmState.wmY=50;updateWmSliders();drawWatermarkCanvas();var area=document.getElementById('wmPreviewArea');area.innerHTML='<div class="wm-wm-preview"><img src="'+e.target.result+'"><span>'+file.name+' ('+image.naturalWidth+'x'+image.naturalHeight+')</span></div>';toast('水印已加载，可拖拽调整位置','success')};image.src=e.target.result};reader.readAsDataURL(file);input.value=''}
function updateWmSliders(){document.getElementById('wmXSlider').value=wmState.wmX;document.getElementById('wmYSlider').value=wmState.wmY;document.getElementById('wmScaleSlider').value=wmState.wmScale;document.getElementById('wmAlphaSlider').value=wmState.wmAlpha;document.getElementById('wmXVal').textContent=Math.round(wmState.wmX)+'%';document.getElementById('wmYVal').textContent=Math.round(wmState.wmY)+'%';document.getElementById('wmScaleVal').textContent=wmState.wmScale+'%';document.getElementById('wmAlphaVal').textContent=wmState.wmAlpha+'%'}
function updateWmFromSliders(){wmState.wmX=parseInt(document.getElementById('wmXSlider').value);wmState.wmY=parseInt(document.getElementById('wmYSlider').value);wmState.wmScale=parseInt(document.getElementById('wmScaleSlider').value);wmState.wmAlpha=parseInt(document.getElementById('wmAlphaSlider').value);document.getElementById('wmXVal').textContent=wmState.wmX+'%';document.getElementById('wmYVal').textContent=wmState.wmY+'%';document.getElementById('wmScaleVal').textContent=wmState.wmScale+'%';document.getElementById('wmAlphaVal').textContent=wmState.wmAlpha+'%';drawWatermarkCanvas()}
function drawWatermarkCanvas(){var canvas=document.getElementById('wmCanvas');var ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);if(wmState.baseImg){ctx.drawImage(wmState.baseImg,0,0)}if(wmState.wmImg){var wmW=canvas.width*(wmState.wmScale/100);var ratio=wmState.wmImg.naturalHeight/wmState.wmImg.naturalWidth;var wmH=wmW*ratio;var x=(wmState.wmX/100)*canvas.width-wmW/2;var y=(wmState.wmY/100)*canvas.height-wmH/2;ctx.save();ctx.globalAlpha=wmState.wmAlpha/100;ctx.drawImage(wmState.wmImg,x,y,wmH>0?wmW:0,wmH>0?wmH:0);ctx.restore()}}
function exportWatermarkImage(){if(!wmState.baseImg){toast('请先上传成品图片','error');return}var canvas=document.getElementById('wmCanvas');canvas.toBlob(function(blob){var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download='watermarked_'+Date.now()+'.png';a.click();URL.revokeObjectURL(url);toast('成品图片已导出','success')},'image/png')}

// Canvas drag for watermark positioning
(function(){var canvas=document.getElementById('wmCanvas');function getCanvasCoords(e){var rect=canvas.getBoundingClientRect();var scaleX=canvas.width/rect.width;var scaleY=canvas.height/rect.height;var clientX,clientY;if(e.touches&&e.touches.length){clientX=e.touches[0].clientX;clientY=e.touches[0].clientY}else{clientX=e.clientX;clientY=e.clientY}return{x:(clientX-rect.left)*scaleX,y:(clientY-rect.top)*scaleY}}function isOnWatermark(cx,cy){if(!wmState.wmImg)return false;var wmW=canvas.width*(wmState.wmScale/100);var ratio=wmState.wmImg.naturalHeight/wmState.wmImg.naturalWidth;var wmH=wmW*ratio;var x=(wmState.wmX/100)*canvas.width-wmW/2;var y=(wmState.wmY/100)*canvas.height-wmH/2;return cx>=x&&cx<=x+wmW&&cy>=y&&cy<=y+wmH}function onDown(e){var coords=getCanvasCoords(e);if(isOnWatermark(coords.x,coords.y)){wmState.dragging=true;wmState.dragStartX=coords.x;wmState.dragStartY=coords.y;wmState.dragOrigX=wmState.wmX;wmState.dragOrigY=wmState.wmY;e.preventDefault();canvas.style.cursor='grabbing'}}function onMove(e){if(!wmState.dragging){var coords=getCanvasCoords(e);canvas.style.cursor=isOnWatermark(coords.x,coords.y)?'grab':'default';return}e.preventDefault();var coords=getCanvasCoords(e);var dx=coords.x-wmState.dragStartX;var dy=coords.y-wmState.dragStartY;wmState.wmX=Math.max(0,Math.min(100,wmState.dragOrigX+(dx/canvas.width)*100));wmState.wmY=Math.max(0,Math.min(100,wmState.dragOrigY+(dy/canvas.height)*100));updateWmSliders();drawWatermarkCanvas()}function onUp(){if(wmState.dragging){wmState.dragging=false;canvas.style.cursor='default'}}canvas.addEventListener('mousedown',onDown);canvas.addEventListener('mousemove',onMove);canvas.addEventListener('mouseup',onUp);canvas.addEventListener('mouseleave',onUp);canvas.addEventListener('touchstart',onDown,{passive:false});canvas.addEventListener('touchmove',onMove,{passive:false});canvas.addEventListener('touchend',onUp)})();

document.getElementById('watermarkPanel').addEventListener('click',function(e){if(e.target===this)closeWatermarkModal()});
document.getElementById('promptLibPanel').addEventListener('click',function(e){if(e.target===this)closePromptLib()});

// ===== 工具 =====
function toast(msg,type){type=type||'info';const c=document.getElementById('toastContainer'),el=document.createElement('div');el.className='toast '+type;el.textContent=msg;c.appendChild(el);setTimeout(()=>{el.style.opacity='0';el.style.transition='opacity .3s';setTimeout(()=>el.remove(),300)},4000)}
function sleep(ms){return new Promise(r=>setTimeout(r,ms))}
document.getElementById('settingsModal').addEventListener('click',e=>{if(e.target.classList.contains('modal-backdrop'))closeSettingsModal()});
function toggleHelpPanel(){document.getElementById('helpPanel').classList.toggle('show')}
document.getElementById('helpPanel').addEventListener('click',function(e){if(e.target===this)toggleHelpPanel()});

// ===== 关闭窗口提示 =====
window.addEventListener('beforeunload',e=>{
  var msgs=[];
  var hasImgs=generationHistory.some(function(h){return h.status==='success'});
  if(hasImgs)msgs.push('1. 请保存已生成的图片（刷新后base64图片将丢失）');
  if(state.accounts.length>0||hasImgs)msgs.push('2. 如有需要，请导出工具设置、生成历史记录、提示词库');
  if(msgs.length||activeSlots>0){
    e.preventDefault();
    var text='离开前请注意：\\n'+msgs.join('\\n');
    if(activeSlots>0)text+='\\n3. 当前有'+activeSlots+'个任务正在运行';
    e.returnValue=text;
    return e.returnValue;
  }
});

// ===== 新一天自动签到+注册 =====
function checkNewDay(){const today=new Date().toISOString().split('T')[0];if(state.lastAutoDay&&state.lastAutoDay!==today){toast('新的一天！自动签到+注册中...','info');(async()=>{const need=state.accounts.filter(a=>!a.disabled&&a.lastCheckinDay!==today);for(const a of need){try{await checkinAccount(state.accounts.indexOf(a));await sleep(600)}catch(e){}}try{await registerAccount()}catch(e){}state.lastAutoDay=today;saveState();toast('新一天初始化完成','success')})()}if(!state.lastAutoDay){state.lastAutoDay=today;saveState()}}
setInterval(checkNewDay,60000);

// ===== 初始化 =====
loadSettingsUI();markInterruptedTasks();restoreLiveImages();renderAll();checkNewDay();renderFullHistory();
if(state.accounts.length>0){toast('正在恢复'+state.accounts.length+'个账号...','info');(async()=>{let okCount=0,failCount=0;for(let i=0;i<state.accounts.length;i++){if(!state.accounts[i].disabled){try{await loginAccount(i);okCount++;await sleep(300)}catch(e){failCount++}}}if(okCount>0)toast('已恢复'+okCount+'个账号'+(failCount?'，'+failCount+'个失败':''),okCount>0?'success':'error');else if(failCount>0)toast(failCount+'个账号恢复失败','error')})()}
</script>
</body>
</html>`;

// ===================== Worker 后端 =====================
async function handleProxy(request, url) {
  const apiPath = url.pathname.replace(/^\/api\/?/, '') || '/';
  const upstreamUrl = UPSTREAM_BASE + (apiPath.startsWith('/') ? '' : '/') + apiPath;
  if (request.method === 'OPTIONS') { return new Response(null, { status: 204, headers: corsHeaders() }); }
  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');
  headers.set('Origin', 'https://grok.17nas.com');
  headers.set('Referer', 'https://grok.17nas.com/');
  headers.set('Accept', 'application/json, text/plain, */*');
  headers.set('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8');
  const userAgents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.37 Edg/131.0.0.0'];
  const ua = request.headers.get('User-Agent') || userAgents[Math.floor(Math.random() * userAgents.length)];
  headers.set('User-Agent', ua);
  const clientIP = request.headers.get('CF-Connecting-IP') || request.headers.get('X-Real-IP') || '';
  const isRegister = apiPath.includes('/auth/register');
  if (isRegister) { const rIP = generateRandomIP(); headers.set('X-Forwarded-For', rIP); headers.set('X-Real-IP', rIP); } else if (clientIP) { headers.set('X-Forwarded-For', clientIP); headers.set('X-Real-IP', clientIP); }
  const st = request.headers.get(SESSION_HEADER);
  if (st) headers.set('Cookie', SESSION_COOKIE + '=' + st);
  const opts = { method: request.method, headers, redirect: 'follow' };
  if (['POST', 'PUT', 'PATCH'].includes(request.method)) { try { const buf = await request.arrayBuffer(); if (buf.byteLength > 0) opts.body = buf; } catch (e) {} }
  try {
    const upResp = await fetch(upstreamUrl, opts);
    let token = ''; try { const rawCookie = upResp.headers.get('set-cookie') || ''; const m = rawCookie.match(new RegExp(SESSION_COOKIE + '=([^;\\s]+)')); if (m) token = m[1]; } catch (e) {}
    const respHeaders = new Headers(corsHeaders()); const ct = upResp.headers.get('Content-Type'); if (ct) respHeaders.set('Content-Type', ct); if (token) respHeaders.set(SESSION_HEADER, token);
    const body = await upResp.arrayBuffer();
    return new Response(body, { status: upResp.status, statusText: upResp.statusText, headers: respHeaders });
  } catch (err) { return new Response(JSON.stringify({ error: '代理请求失败: ' + err.message }), { status: 502, headers: { 'Content-Type': 'application/json', ...corsHeaders() } }); }
}
function generateRandomIP() { const a = 1 + Math.floor(Math.random() * 223); const b = Math.floor(Math.random() * 256); const c = Math.floor(Math.random() * 256); const d = 1 + Math.floor(Math.random() * 254); return a + '.' + b + '.' + c + '.' + d; }
function corsHeaders() { return { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, X-Session-Token', 'Access-Control-Expose-Headers': 'X-Session-Token', 'Access-Control-Max-Age': '86400' }; }

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/image-proxy') || url.pathname.startsWith('/api/media-proxy')) {
      const imageUrl = url.searchParams.get('url'); if (!imageUrl) { return new Response('Missing url parameter', { status: 400, headers: corsHeaders() }); }
      try {
        const imgResp = await fetch(imageUrl, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept': 'image/*,video/*,*/*;q=0.8', 'Referer': 'https://grok.17nas.com/', 'Origin': 'https://grok.17nas.com' }, cf: { cacheEverything: true, cacheTtl: 86400, cacheTtlByStatus: { '200-299': 86400, '400-499': 60, '500-599': 0 } } });
        const contentType = imgResp.headers.get('Content-Type') || 'application/octet-stream'; const body = await imgResp.arrayBuffer();
        return new Response(body, { status: imgResp.status, headers: { 'Content-Type': contentType, 'Cache-Control': 'public, max-age=86400', 'Access-Control-Allow-Origin': '*' } });
      } catch (err) { return new Response('Image proxy failed: ' + err.message, { status: 502, headers: corsHeaders() }); }
    }
    if (url.pathname.startsWith('/api/')) { return handleProxy(request, url); }
    return new Response(HTML_CONTENT, { headers: { 'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'no-cache' } });
  },
};
