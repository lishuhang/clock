// Cloudflare Worker - AI生图 (gpt2-worker-kdr)
// kdr-v1.0: Keydraw 通路复活 — 2026-08-26 重新探测
//   (1) 基于 kd-v2.3 完整版，恢复 Gift Key 免费通路
//   (2) giftKeyFallback 更新为当前有效 Gift-Key-V2EX653
//   (3) 上游 /api/gift-key 端点可动态获取最新 key，支持自动轮换
// kdr-v1.1: 修复设置齿轮点击报错（移除未定义的 renderStorageInfo 调用）
const UPSTREAM = {
  base: 'https://keydraw.97api.com',
  origin: 'https://keydraw.97api.com',
  giftKeyFallback: 'Gift-Key-V2EX653'  // 共享 Gift Key，2026-08-26 实测可用
};
const SESSION_HEADER = 'X-Session-Token';

// ===================== HTML 前端 =====================
const HTML_CONTENT = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI生图</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --accent:#3333CC;--accent-hover:#2768d9;--accent-light:rgba(51,51,204,.10);
  --bg:#FFF;--bg-card:#FFF;--bg-secondary:#F5F5F5;--bg-hover:#E2E8F0;
  --text:#1A202C;--text-secondary:#718096;--text-muted:#A0AEC0;
  --border:#E0E0E0;--border-medium:#CBD5E0;
  --radius:8px;--radius-xs:4px;
  --space-xs:4px;--space-sm:8px;--space-md:16px;--space-lg:24px;
  --font:"Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --mono:'SF Mono',Consolas,'Liberation Mono',Menlo,monospace;
  --purple:#6A5ACD;--green:#00CC00;--red:#FF0000;--yellow:#FFCC00;--gray:#666;
  --orange:#fdcb6e;--blue:#74b9ff;
}
[data-theme="dark"]{
  --bg:#0a0a0b;--bg-card:#141416;--bg-secondary:#1c1c20;--bg-hover:#242429;
  --text:#e8e6e3;--text-secondary:#a09f9d;--text-muted:#6b6a68;
  --border:#242429;--border-medium:#333;
  --accent:#6c5ce7;--accent-hover:#a29bfe;--accent-light:rgba(108,92,231,.12);
  --purple:#6A5ACD;--green:#00b894;--red:#e17055;--yellow:#fdcb6e;--gray:#888;
  --orange:#fdcb6e;--blue:#74b9ff;
}
html,body{height:100%;font-family:var(--font);background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* Buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 16px;font-size:13px;font-weight:600;border-radius:var(--radius);border:1px solid var(--border);background:var(--bg-secondary);color:var(--text);cursor:pointer;font-family:var(--font);white-space:nowrap}
.btn:hover:not(:disabled){background:var(--bg-hover);border-color:var(--border-medium)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--purple);border-color:var(--purple);color:#fff}.btn-primary:hover:not(:disabled){background:#5a4bbd}
.btn-outline{background:transparent;color:var(--accent);border-color:var(--accent)}.btn-outline:hover:not(:disabled){background:var(--accent-light)}
.btn-ghost{border:none;background:transparent;color:var(--text-secondary);padding:4px 8px}.btn-ghost:hover:not(:disabled){color:var(--text);background:var(--bg-secondary)}
.btn-danger-outline{background:transparent;color:var(--red);border-color:var(--red)}.btn-danger-outline:hover:not(:disabled){background:rgba(255,0,0,.06)}
.btn-danger{border-color:var(--red);color:var(--red)}.btn-danger:hover:not(:disabled){background:var(--red);color:#fff}
.btn-sm{padding:4px 10px;font-size:12px;border-radius:var(--radius-xs)}
.btn-xs{padding:2px 7px;font-size:11px;border-radius:var(--radius-xs)}
.btn-full{width:100%}

/* Form controls */
.select-field{padding:8px 32px 8px 12px;font-size:13px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-card);color:var(--text);outline:none;cursor:pointer;appearance:none;-webkit-appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%23718096' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center;width:100%;height:38px;font-family:var(--font)}
.select-field:focus{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-light)}
.input-field{padding:8px 12px;font-size:13px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-card);color:var(--text);outline:none;line-height:1.5;width:100%;font-family:var(--font)}
.input-field::placeholder{color:var(--text-muted)}
.input-field:focus{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-light)}
.checkbox-wrap{display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;color:var(--text)}
.checkbox-wrap input[type="checkbox"]{appearance:none;-webkit-appearance:none;width:16px;height:16px;flex-shrink:0;border:2px solid var(--border-medium);border-radius:var(--radius-xs);background:var(--bg-card);cursor:pointer;position:relative}
.checkbox-wrap input[type="checkbox"]:hover{border-color:var(--accent)}
.checkbox-wrap input[type="checkbox"]:checked{background:var(--accent);border-color:var(--accent)}
.checkbox-wrap input[type="checkbox"]:checked::after{content:'';position:absolute;left:3px;top:0;width:6px;height:10px;border:solid #fff;border-width:0 2px 2px 0;transform:rotate(45deg)}
.icon-btn{background:none;border:none;cursor:pointer;padding:4px;color:var(--text-secondary)}
.icon-btn:hover{color:var(--accent)}

/* Nav */
#topNav{background:var(--bg-secondary);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 var(--space-lg);border-bottom:1px solid var(--border);flex-shrink:0;gap:12px}.nav-left{display:flex;align-items:center;gap:8px}
#topNav .title{font-size:20px;font-weight:700}
.nav-right{display:flex;align-items:center;gap:12px}
.points{color:var(--accent);font-size:16px;font-weight:600}

/* Layout */
#mainWrap{display:flex;height:calc(100vh - 56px);overflow:hidden}
#leftPanel{width:380px;min-width:320px;overflow-y:auto;padding:var(--space-lg);border-right:1px solid var(--border);flex-shrink:0}
#centerPanel{flex:1;overflow-y:auto;padding:var(--space-lg)}

/* Left form */
#promptInput{min-height:100px;resize:vertical}
.prompt-actions{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.dropdown-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
.form-group{margin-bottom:12px}
.form-group label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500}
.form-label-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
.form-label-row label{margin-bottom:0}
.conditional-group{margin-top:10px}
.conditional-group label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500}
.hint-text{font-size:11px;color:var(--text-muted);margin-top:2px}

/* Ref upload */
.ref-grid{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.ref-thumb{position:relative;width:56px;height:56px;border-radius:var(--radius-xs);overflow:hidden;border:1px solid var(--border);flex-shrink:0}
.ref-thumb img{width:100%;height:100%;object-fit:cover}
.ref-thumb .ref-del{position:absolute;top:1px;right:1px;width:14px;height:14px;border-radius:50%;background:var(--red);color:#fff;font-size:9px;line-height:14px;text-align:center;cursor:pointer;opacity:.8}
.ref-add{width:56px;height:56px;border:1px dashed var(--border);border-radius:var(--radius-xs);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--text-secondary);flex-shrink:0}
.ref-add:hover{border-color:var(--accent);color:var(--accent)}
.ref-add.dragover{border-color:var(--accent);color:var(--accent);background:var(--accent-light)}

/* Generate button */
.gen-btn{width:100%;height:48px;font-size:15px;font-weight:700;margin-top:14px;background:var(--purple);color:#fff;border:none;border-radius:var(--radius);cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;font-family:var(--font)}
.gen-btn:hover:not(:disabled){background:#5a4bbd}
.gen-btn:disabled{opacity:.4;cursor:not-allowed}

/* Extra buttons */
.extra-btns{display:flex;gap:8px;margin-top:10px}
.extra-btns .btn{flex:1;height:38px}

/* Task list */
.task-header{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.hdr-btns{margin-left:auto;display:flex;gap:6px}
.task-list{margin-top:14px;display:flex;flex-direction:column;gap:10px}

/* History items */
.hist-item{display:flex;align-items:flex-start;gap:10px;padding:12px;border:1px solid var(--border);border-radius:var(--radius)}
.hist-item.running-item{border-color:var(--accent)}
.status-icon{flex-shrink:0;margin-top:2px}
.hist-body{flex:1;min-width:0}
.hist-time{color:var(--text-muted);font-size:11px}
.hist-desc{margin-top:4px;font-size:13px;line-height:1.5;word-break:break-all}
.hist-actions{flex-shrink:0;display:flex;gap:6px;margin-top:2px}
.hist-status{font-size:11px;padding:1px 5px;border-radius:3px;font-weight:600;white-space:nowrap}
.hist-status.ok{background:var(--green);color:#fff}
.hist-status.err{background:var(--red);color:#fff}
.hist-status.timeout{background:var(--yellow);color:#111}
.hist-status.running{background:var(--blue);color:#111}
.hist-status.queued{background:var(--text-muted);color:#111}
.hist-prompt{padding:8px 12px;font-size:13px;white-space:pre-wrap;word-break:break-word;max-height:80px;overflow-y:auto;line-height:1.4}
.hist-error{padding:8px 12px;font-size:12px;color:var(--red);background:rgba(225,112,85,.06)}
.hist-progress{padding:8px 12px}
.hist-progress .pbar{height:4px;background:var(--border);border-radius:2px;overflow:hidden}
.hist-progress .pfill{height:100%;background:var(--accent);border-radius:2px}
.hist-progress .ptxt{font-size:12px;color:var(--text-secondary);margin-top:4px;display:flex;align-items:center;gap:6px}
.hist-progress .ptxt .elapsed{color:var(--text-muted);font-family:var(--mono);font-size:11px;margin-left:auto}
.hist-img-link{padding:4px 12px 8px;font-size:12px}
.hist-img-link a{color:var(--accent);text-decoration:none;padding:2px 6px;border-radius:4px;background:var(--bg-secondary);display:inline-flex;align-items:center;gap:4px;font-size:12px}
.hist-img-link a:hover{background:var(--accent-light)}
.hist-model{font-size:12px;color:var(--text-secondary)}
.hist-account{font-size:11px;color:var(--text-muted)}

/* Spinner */
.spinner{display:inline-block;width:12px;height:12px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%}

/* Modals */
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:100}
.modal-backdrop.show{display:flex}
.modal{background:var(--bg-card);border-radius:10px;width:90%;max-width:560px;max-height:80vh;overflow-y:auto;border:1px solid var(--border)}
.modal-header{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center}
.modal-header h3{flex:1;font-size:15px;font-weight:600}
.modal-body{padding:18px}
.accounts-table{width:100%;border-collapse:collapse;font-size:13px}
.accounts-table th,.accounts-table td{padding:6px 8px;text-align:left;border-bottom:1px solid var(--border)}
.accounts-table th{color:var(--text-muted);font-weight:500;font-size:11px;text-transform:uppercase}
.accounts-table tr:hover td{background:var(--bg-secondary)}

/* Help panel */
.help-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:90%;max-width:520px;max-height:80vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:150;display:none;flex-direction:column}
.help-panel.show{display:flex}
.help-panel-header{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center}
.help-panel-header h3{flex:1;font-size:15px;font-weight:600}
.help-panel-body{padding:16px 18px;overflow-y:auto;flex:1;font-size:13px;line-height:1.7;color:var(--text-secondary)}
.help-panel-body h4{color:var(--text);font-size:14px;margin:12px 0 6px;font-weight:600}
.help-panel-body h4:first-child{margin-top:0}
.help-panel-body ul{padding-left:16px;margin:4px 0 8px}
.help-panel-body li{margin:2px 0}
.help-panel-body code{background:var(--bg-secondary);padding:1px 4px;border-radius:3px;font-size:12px;font-family:var(--mono);color:var(--accent)}
.help-panel-body .changelog{font-size:12px;color:var(--text-muted);border-top:1px solid var(--border);padding-top:10px;margin-top:14px}
.help-panel-body .changelog dt{color:var(--text-secondary);font-weight:600;margin-top:8px}
.help-panel-body .changelog dd{margin:2px 0 4px 16px}

/* Theme switch */
.theme-switch{display:inline-flex;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.theme-btn{padding:5px 10px;border:none;background:var(--bg-secondary);color:var(--text-secondary);font-size:12px;cursor:pointer;font-family:var(--font);white-space:nowrap}
.theme-btn:hover{background:var(--bg-hover)}
.theme-btn.active{background:var(--accent);color:#fff}

/* (watermark styles removed in v0.1) */

/* Prompt library panel */
.promptlib-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:90%;max-width:480px;max-height:80vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:170;display:none;flex-direction:column}
.promptlib-panel.show{display:flex}
.promptlib-header{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center}
.promptlib-header h3{flex:1;font-size:15px;font-weight:600}
.promptlib-body{padding:14px 18px;overflow-y:auto;flex:1}
.promptlib-item{padding:8px 10px;border:1px solid var(--border);border-radius:6px;margin-bottom:6px;background:var(--bg-secondary)}
.promptlib-item:hover{background:var(--bg-hover)}
.promptlib-item-text{font-size:13px;color:var(--text);white-space:pre-wrap;word-break:break-word;max-height:56px;overflow-y:hidden;line-height:1.4;cursor:pointer}
.promptlib-item-text:hover{color:var(--accent)}
.promptlib-item-meta{display:flex;align-items:center;gap:6px;margin-top:4px;font-size:11px;color:var(--text-muted)}
.promptlib-item-meta button{font-size:10px}
.promptlib-empty{color:var(--text-muted);text-align:center;padding:36px 0;font-size:13px}
.promptlib-actions{display:flex;gap:6px;padding:10px 18px;border-top:1px solid var(--border)}

/* Toast */
/* v26: toast 移至右下角，避免遮挡右上角设置按钮 */
.toast-container{position:fixed;bottom:14px;right:14px;z-index:200;display:flex;flex-direction:column-reverse;gap:6px;max-width:calc(100vw - 28px)}
.toast{padding:8px 14px;border-radius:var(--radius);font-size:13px;max-width:340px;color:#fff}
.toast.success{background:var(--green)}
.toast.error{background:var(--red)}
.toast.info{background:var(--accent)}

/* Mobile drawer */
#historyDrawer{display:none}
@media(max-width:768px){
  #mainWrap{flex-direction:column}
  #leftPanel{width:100%;min-width:0;border-right:none;border-bottom:1px solid var(--border);overflow-y:visible;padding:var(--space-md)}
  #centerPanel{display:none}
  .dropdown-grid{grid-template-columns:1fr}
  #historyDrawer{
    display:flex;flex-direction:column;
    position:fixed;bottom:0;left:0;right:0;
    z-index:150;background:var(--bg-card);
  }
  .drawer-header{
    background:var(--bg-secondary);border-top:1px solid var(--border);
    padding:0 var(--space-lg);height:48px;
    display:flex;align-items:center;justify-content:space-between;
    flex-shrink:0;cursor:pointer;
  }
  .drawer-header h3{font-size:14px;font-weight:700}
  .drawer-header button{background:none;border:none;cursor:pointer;color:var(--text-secondary);padding:4px}
  .drawer-body{
    display:none;
    max-height:65vh;overflow-y:auto;padding:var(--space-md);
    border-top:1px solid var(--border);
  }
  #historyDrawer.open .drawer-body{display:block}
}
@media(max-width:420px){
  .dropdown-grid{grid-template-columns:1fr}
  .drawer-body{max-height:75vh}
}


/* kd-v2.1: 统一浮窗基类 — wm-panel/rwm-panel/help-panel/promptlib-panel/modal 共用 */
.floating-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:160;display:none;flex-direction:column;max-height:88vh}
.floating-panel.show{display:flex}
.fp-titlebar{display:flex;align-items:center;justify-content:space-between;padding:0 14px;height:36px;color:#fff;border-radius:10px 10px 0 0;flex-shrink:0}
.fp-titlebar-text{font-size:14px;font-weight:700}
.fp-titlebar-close{width:32px;height:32px;border:none;background:transparent;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;border-radius:4px}
.fp-titlebar-close:hover{background:rgba(255,255,255,.15)}
.fp-body{padding:14px;overflow-y:auto;flex:1}
.fp-actions{display:flex;gap:6px;justify-content:flex-end;padding-top:8px;border-top:1px solid var(--border);flex-shrink:0}

.wm-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:92%;max-width:720px;max-height:88vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:160;display:none;flex-direction:column}
.wm-panel.show{display:flex}
.wm-titlebar{display:flex;align-items:center;justify-content:space-between;padding:0 14px;height:36px;background:var(--accent);color:#fff;border-radius:10px 10px 0 0}
.wm-titlebar-text{font-size:14px;font-weight:700}
.wm-titlebar-close{width:32px;height:32px;border:none;background:transparent;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;border-radius:4px}
.wm-titlebar-close:hover{background:rgba(255,255,255,.15)}
.wm-body{padding:14px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px}
.wm-upload-section{border:2px dashed var(--border);border-radius:6px;padding:12px;text-align:center;cursor:pointer;color:var(--text-muted);font-size:12px}
.wm-upload-section:hover{border-color:var(--accent);color:var(--text-secondary)}
.wm-upload-section .wm-upload-label{font-weight:600;color:var(--text-secondary);margin-bottom:2px}
.wm-upload-section .wm-upload-sub{font-size:11px;color:var(--text-muted)}
.wm-canvas-wrap{position:relative;background:var(--bg);border:1px solid var(--border);border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:160px}
.wm-canvas-wrap canvas{max-width:100%;max-height:50vh;display:block;cursor:default}
.wm-wm-preview{display:flex;align-items:center;gap:6px;margin-top:4px}
.wm-wm-preview img{max-height:36px;border-radius:4px;border:1px solid var(--border)}
.wm-wm-preview span{font-size:11px;color:var(--text-muted)}
.wm-controls{display:flex;flex-wrap:wrap;gap:8px}
.wm-control-group{flex:1;min-width:130px}
.wm-control-group label{display:block;font-size:11px;color:var(--text-secondary);margin-bottom:3px;font-weight:500}
.wm-slider{display:flex;align-items:center;gap:6px}
.wm-slider input[type="range"]{flex:1;height:3px;appearance:none;-webkit-appearance:none;background:var(--border);border-radius:2px;outline:none}
.wm-slider input[type="range"]::-webkit-slider-thumb{appearance:none;-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:var(--accent);cursor:pointer}
.wm-slider-val{font-family:var(--mono);font-size:11px;color:var(--text-muted);min-width:28px;text-align:right}
.wm-actions{display:flex;gap:6px;justify-content:flex-end;padding-top:6px;border-top:1px solid var(--border)}

/* v27: 去除水印面板 - 复用 wm-panel 样式体系 */
.rwm-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:92%;max-width:720px;max-height:88vh;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;z-index:165;display:none;flex-direction:column}
.rwm-panel.show{display:flex}
.rwm-titlebar{display:flex;align-items:center;justify-content:space-between;padding:0 14px;height:36px;background:var(--purple);color:#fff;border-radius:10px 10px 0 0}
.rwm-titlebar-text{font-size:14px;font-weight:700}
.rwm-titlebar-close{width:32px;height:32px;border:none;background:transparent;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;border-radius:4px}
.rwm-titlebar-close:hover{background:rgba(255,255,255,.15)}
.rwm-body{padding:14px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:12px}
.rwm-type-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.rwm-type-card{padding:10px;border:2px solid var(--border);border-radius:6px;cursor:pointer;text-align:center;background:var(--bg-secondary);transition:border-color .15s,background .15s}
.rwm-type-card:hover{border-color:var(--accent)}
.rwm-type-card.active{border-color:var(--purple);background:var(--accent-light)}
.rwm-type-card-title{font-size:13px;font-weight:600;color:var(--text)}
.rwm-type-card-desc{font-size:11px;color:var(--text-muted);margin-top:2px}
.rwm-drop-zone{border:2px dashed var(--border);border-radius:6px;padding:24px 12px;text-align:center;cursor:pointer;color:var(--text-muted);font-size:13px;transition:border-color .15s,color .15s}
.rwm-drop-zone:hover,.rwm-drop-zone.dragover{border-color:var(--accent);color:var(--accent);background:var(--accent-light)}
.rwm-drop-zone-icon{font-size:24px;margin-bottom:6px}
.rwm-drop-zone-sub{font-size:11px;color:var(--text-muted);margin-top:2px}
.rwm-file-list{display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto}
.rwm-file-item{display:flex;align-items:center;gap:8px;padding:6px 8px;border:1px solid var(--border);border-radius:4px;font-size:12px;background:var(--bg-secondary)}
.rwm-file-item .rwm-file-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rwm-file-item .rwm-file-status{font-size:11px;padding:1px 6px;border-radius:3px;white-space:nowrap}
.rwm-file-item .rwm-file-status.pending{background:var(--text-muted);color:#fff}
.rwm-file-item .rwm-file-status.processing{background:var(--blue);color:#111}
.rwm-file-item .rwm-file-status.done{background:var(--green);color:#fff}
.rwm-file-item .rwm-file-status.failed{background:var(--red);color:#fff}
.rwm-actions{display:flex;gap:6px;justify-content:flex-end;padding-top:8px;border-top:1px solid var(--border)}
.rwm-info{font-size:11px;color:var(--text-muted);padding:6px 8px;background:var(--bg-secondary);border-radius:4px;line-height:1.5}

/* Scrollbar */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--text-muted)}

</style>
</head>
<body>

<nav id="topNav">
  <div class="title">AI生图<span id="versionBadge" style="font-size:11px;color:var(--text-muted);font-family:var(--mono);margin-left:8px;font-weight:400"></span></div>
  <div class="nav-left">
    <!-- kd-v2.1: 添加水印 / 去除水印 工具入口 -->
    <button class="btn btn-ghost btn-sm" onclick="openWatermarkModal()" title="在生成的图片上加水印">水印</button>
    <button class="btn btn-ghost btn-sm" onclick="openRemoveWmModal()" title="去除 Gemini/豆包 水印">去水印</button>
  </div>
  <div class="nav-right">
    <span class="points" id="quotaBadge" title="点击刷新所有 key 额度" style="cursor:pointer" onclick="refreshAllQuota()">剩余 <span id="usableCreditsTop">0</span> 张</span>
    <span id="concurrencyInfo" style="font-size:12px;color:var(--text-secondary)">并发: 0/0</span>
    <span id="totalCreditsTop" style="display:none">0</span>
    <button class="icon-btn" onclick="showSettingsModal()" title="设置">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
    </button>
  </div>
</nav>

<div id="mainWrap">
  <div id="leftPanel">
    <textarea id="promptInput" class="input-field" placeholder="提示词"></textarea>

    <div class="prompt-actions">
      <button class="btn btn-ghost btn-sm" onclick="pasteToPrompt()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>粘贴
      </button>
      <button class="btn btn-ghost btn-sm" onclick="document.getElementById('promptInput').value='';refImages=[];renderRefGrid()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>清空
      </button>
      <button class="btn btn-ghost btn-sm" onclick="showPromptLib()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>提示词库
      </button>
    </div>

    <div class="dropdown-grid">
      <select id="modelSelect" class="select-field" onchange="onModelChange()">
          <option value="gpt-image-2">GPT-Image-2 (1K)</option>
        </select>
      <select id="countSelect" class="select-field">
        <option value="1">1张</option>
        <option value="2">2张</option>
        <option value="3">3张</option>
        <option value="4">4张</option>
        <option value="5">5张</option>
        <option value="6">6张</option>
      </select>
      <select id="qualityTierSelect" class="select-field" onchange="onQualityTierChange()">
        <option value="standard">1.5K 标准</option>
        <option value="high">2.5K 高清</option>
        <option value="ultra">4K 超清</option>
      </select>
      <select id="ratioSelect" class="select-field" onchange="onRatioChange()">
        <option value="auto">智能</option>
        <option value="1:1" selected>1:1</option>
        <option value="3:2">3:2</option>
        <option value="2:3">2:3</option>
        <option value="16:9">16:9</option>
        <option value="9:16">9:16</option>
        <option value="4:3">4:3</option>
        <option value="3:4">3:4</option>
        <option value="5:4">5:4</option>
        <option value="4:5">4:5</option>
        <option value="2:1">2:1</option>
        <option value="1:2">1:2</option>
        <option value="21:9">21:9</option>
        <option value="9:21">9:21</option>
      </select>
    </div>
    <span id="modelAvailHint" class="hint-text" style="display:none;color:var(--red);margin-top:4px"></span>



    <div id="durationGroup" style="display:none;margin-top:10px">
      <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500">视频时长</label>
      <select id="durationSelect" class="select-field">
        <option value="6">6 秒</option>
        <option value="10">10 秒</option>
        <option value="12">12 秒</option>
        <option value="16">16 秒</option>
        <option value="20">20 秒</option>
      </select>
    </div>

    <div id="videoResolutionGroup" style="display:none;margin-top:10px">
      <div class="form-label-row">
        <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500">视频清晰度</label>
        <span class="hint-text">上游仅支持480p和720p</span>
      </div>
      <select id="videoResolutionSelect" class="select-field" onchange="onVideoResolutionChange()">
        <option value="720p">720p</option>
        <option value="480p">480p</option>
      </select>
    </div>

    <div id="grokSizeHintGroup" style="display:none;margin-top:10px">
      <span id="grokSizeHintText" class="hint-text" style="color:var(--orange)"></span>
    </div>

    <div style="margin-top:14px">
      <label id="refLabel" style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500">参考图（可选）</label>
      <input type="file" id="refFileInput" accept="image/*" multiple style="display:none" onchange="handleRefImages(this)">
      <div class="ref-grid" id="refGrid"></div>
    </div>

    <button class="gen-btn" id="generateBtn" onclick="startGeneration()">生成图片</button>

    <div class="extra-btns">
    </div>
  </div>

  <div id="centerPanel">
    <div id="taskCard">
      <div class="task-header">
        <label class="checkbox-wrap"><input type="checkbox" id="ongoingChk" onchange="toggleOngoingFilter()"> 进行中</label>
        <div class="hdr-btns">
          <button class="btn btn-outline btn-sm" onclick="exportHistory()">导出</button>
          <button class="btn btn-danger-outline btn-sm" onclick="clearHistory()">清空</button>
        </div>
      </div>
      <div class="task-list" id="historyList">
        <p id="historyEmpty" style="color:var(--text-muted);text-align:center;padding:40px 0;font-size:13px">暂无历史记录</p>
      </div>
    </div>
  </div>
</div>

<!-- Mobile drawer -->
<div id="historyDrawer">
  <div class="drawer-header" onclick="toggleDrawer()">
    <h3>历史记录</h3>
    <button onclick="event.stopPropagation();toggleDrawer()" title="展开/收起">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>
    </button>
  </div>
  <div class="drawer-body" id="drawerBody"></div>
</div>

<!-- Settings modal -->
<div class="modal-backdrop" id="settingsModal">
  <div class="modal">
    <div class="modal-header">
      <h3>设置</h3>
      <button class="btn btn-sm" onclick="closeSettingsModal()">关闭</button>
    </div>
    <div class="modal-body">
      <div style="margin-bottom:14px">
        <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500">外观主题</label>
        <div class="theme-switch">
          <button class="theme-btn" data-theme-val="system" onclick="setThemeMode('system')">跟随系统</button>
          <button class="theme-btn" data-theme-val="light" onclick="setThemeMode('light')">浅色</button>
          <button class="theme-btn" data-theme-val="dark" onclick="setThemeMode('dark')">深色</button>
        </div>
      </div>
      <div style="display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" onclick="refreshAllQuota()">刷新所有 Key 额度</button>
        <button class="btn btn-sm" onclick="batchVerifyAccounts()">重置耗尽标记</button>
        <a href="https://www.97api.com" target="_blank" rel="noopener" class="btn btn-sm" style="text-decoration:none">97api 官网</a>
      </div>
      <div id="accountsTableContainer" style="overflow-x:auto;margin-bottom:14px"></div>
      <!-- kd-v2.1: 废弃账号池已移除 -->
      <div id="storageInfoContainer" style="margin-bottom:14px"></div>
      <!-- kd-v2.0: 邀请好友面板已移除（keydraw 共享 Gift Key 模式无邀请系统） -->
      <div style="display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
        <span style="font-size:11px;color:var(--text-muted);margin-right:4px">导出：</span>
        <button class="btn btn-sm btn-outline" onclick="exportAccounts('all')" title="导出可用账号 + 废弃池（导出前会自动检测废弃）">全部</button>
        <button class="btn btn-sm btn-outline" onclick="exportAccounts('active')" title="仅导出可用账号（导出前会自动检测废弃）">仅可用</button>
        <button class="btn btn-sm btn-outline" onclick="exportAccounts('abandoned')" title="仅导出废弃池账号">仅废弃池</button>
        <button class="btn btn-sm" onclick="importAccounts()">导入账号</button>
      </div>
      <input type="file" id="importFileInput" accept=".json" style="display:none" onchange="handleImportFile(this)">
      <input type="file" id="importHistoryInput" accept=".json" style="display:none" onchange="handleImportHistory(this)">
      <input type="file" id="importPromptLibInput" accept=".json" style="display:none" onchange="handleImportPromptLib(this)">
      <div style="border-top:1px solid var(--border);padding-top:14px">
        <!-- kd-v2.1: 多个自定义 97api API Key（textarea，每行一个）—— 与共享 Gift Key 共池轮换 -->
        <div class="form-group">
          <label>自定义 97api API Keys <span style="color:var(--text-muted);font-size:11px">(每行一个，与共享 Gift Key 共池轮换；Gift Key 优先免费使用)</span></label>
          <textarea id="customApiKeysTA" class="input-field" placeholder="sk-xxxxxxxxxxxxxxxx&#10;sk-yyyyyyyyyyyyyyyy&#10;# 以 # 开头的行会被忽略" style="min-height:80px;font-family:var(--mono);font-size:12px;resize:vertical"></textarea>
          <div class="hint-text" style="margin-top:2px">
            获取方式：<a href="https://www.97api.com" target="_blank" rel="noopener" style="color:var(--accent)">www.97api.com</a> 注册后充值 → 控制台获取 API Key（¥0.015/1K，¥0.1/2K-4K 分组）
          </div>
        </div>
        <!-- kd-v2.0: 移除"默认密码"字段（仅马良注册需要，已下线） -->
        <div class="form-group">
          <label>轮换策略</label>
          <select id="rotationStrategy" class="select-field">
            <option value="most-credits">优先额度最多</option>
            <option value="round-robin">轮询</option>
            <option value="newest">优先最新</option>
          </select>
        </div>
        <!-- kd-v2.0: 移除"额度耗尽自动签到"(无签到概念)和"autoFallbackGpt2"(单模型无需fallback) -->
        <!-- kd-v2.1: autoRegisterChk 已移除 —— key 轮换由 getEffectiveKeyEntry() 自动处理 -->
        <div class="form-group">
          <label class="checkbox-wrap"><input type="checkbox" id="notificationsEnabled" onchange="onNotificationsToggle(this.checked)"> 生成完成浏览器通知提醒</label>
          <div class="hint-text" id="notificationsHint" style="margin-top:2px"></div>
        </div>
        <button class="btn btn-primary" onclick="saveSettings()">保存设置</button>
      </div>
      <div style="border-top:1px solid var(--border);margin-top:14px;padding-top:10px;display:flex;gap:6px;align-items:center">
        <button class="btn btn-sm btn-outline" onclick="toggleHelpPanel()">使用帮助 & 更新日志</button>
        <button class="btn btn-sm btn-danger" onclick="clearAllData()">清除所有数据</button>
      </div>
    </div>
  </div>
</div>

<!-- Help panel -->
<div class="help-panel" id="helpPanel">
  <div class="help-panel-header">
    <h3>使用说明 & 更新日志</h3>
    <button class="btn btn-sm" onclick="toggleHelpPanel()">关闭</button>
  </div>
  <div class="help-panel-body">
    <h4>产品简介</h4>
    <p>GPT2 生图 (kd-v2.0) 是基于 Cloudflare Worker 的免费 AI 图片生成服务，上游为 <a href="https://keydraw.97api.com" target="_blank">keydraw.97api.com</a>（V2EX 自荐站，免注册共享 Gift Key 模式），仅支持 <code>gpt-image-2</code> 模型 1K 分辨率出图。</p>
    <p style="margin-top:8px;color:var(--text-secondary);font-size:12px"><strong>kd-v2.0 更新</strong>：分支合并版本 —— 移除多通道架构（keydraw/custom-97api/maliang 三合一）；马良通道（grok.17nas.com）彻底下线；新增右上角"今日 X / 999 张"日额度本地计数器（GMT+8 0点重置）；用户自填 97api API Key 现自动替代共享 Gift Key。</p>

    <h4>额度说明</h4>
    <ul>
      <li><strong>共享 Gift Key</strong>（默认）：全 V2EX 共享 999 张/日，<strong>GMT+8 0点重置</strong>。早上易出图，下午易耗尽。无公开 quota API，本地计数器为估算值，遇"日限额已用完"会立即归零</li>
      <li><strong>自定义 97api API Key</strong>（设置面板填入）：用户自己的 key，按量付费 ¥0.015/1K 起或 ¥0.1/2K-4K 分组，无每日上限，填入后自动替代共享 Gift Key</li>
      <li><strong>额度计数器</strong>：右上角"今日 X / 999 张"基于本地累计，仅供参考。使用自定义 key 时不显示 999 上限</li>
    </ul>

    <h4>主要功能</h4>
    <ul>
      <li><strong>模型</strong>：仅 <code>gpt-image-2</code>（上游 keydraw.97api.com 限制）</li>
      <li><strong>并发生成</strong>：每个账号 3 个并发槽位，多账号叠加</li>
      <li><strong>账号池管理</strong>：自动注册、手动添加、批量验证、智能轮换（注：上游已下线签到功能）</li>
      <li><strong>参考图生成</strong>：图生图/图生视频</li>
      <li><strong>历史记录</strong>：自动保存，支持导入导出</li>
      <li><strong>提示词库</strong>：收藏常用提示词，支持导入导出</li>
      <li><strong>深浅色模式</strong>：跟随系统/浅色/深色</li>
    </ul>

    <h4>使用方法</h4>
    <ul>
      <li>首次使用：点击右上角设置图标，注册新账号</li>
      <li>生成图片：输入提示词，选择模型/比例/数量，点击生成</li>
      <li>一键粘贴：点击提示词旁的粘贴按钮</li>
      <li>参考图：点击上传参考图（图生图/图生视频）</li>
      <li>管理账号：设置面板中可签到/删除/导出/导入账号</li>
    </ul>

    <h4>注意事项</h4>
    <ul>
      <li>base64 图片为临时数据，刷新后将丢失，请及时下载</li>
      <li>URL 图片通过代理加载，刷新后可恢复</li>
      <li>上游 keydraw.97api.com 无签到概念，新额度通过刷新 Gift Key 或注册新 key 获取</li>
      <li>关闭页面前请保存图片，可导出设置/历史/提示词库</li>
    </ul>

    
  </div>
</div>


<!-- Watermark panel -->
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
      <div id="wmPlaceholder" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:13px;padding:36px">请先上传成品图片</div>
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
    <div style="font-size:11px;color:var(--text-muted)">提示：可在画布上拖拽水印调整位置</div>
    <div class="wm-actions">
      <button class="btn btn-sm" onclick="closeWatermarkModal()">取消</button>
      <button class="btn btn-primary btn-sm" onclick="exportWatermarkImage()">输出成品图片</button>
    </div>
  </div>
</div>

<!-- v27: 去除水印面板 -->
<div class="rwm-panel" id="removeWmPanel">
  <div class="rwm-titlebar">
    <span class="rwm-titlebar-text">去除水印</span>
    <button class="rwm-titlebar-close" onclick="closeRemoveWmModal()">&times;</button>
  </div>
  <div class="rwm-body">
    <!-- 水印类型选择 -->
    <div>
      <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;font-weight:500">选择水印类型</label>
      <div class="rwm-type-grid">
        <div class="rwm-type-card active" id="rwmTypeGemini" onclick="setRwmType('gemini')">
          <div class="rwm-type-card-title">Google Gemini</div>
          <div class="rwm-type-card-desc">右下角 ✦ 星形水印<br>(96px / 48px 自适应)</div>
        </div>
        <div class="rwm-type-card" id="rwmTypeDoubao" onclick="setRwmType('doubao')">
          <div class="rwm-type-card-title">豆包 AI</div>
          <div class="rwm-type-card-desc">右下角"豆包AI生成"文字<br>(120×20 px)</div>
        </div>
      </div>
    </div>

    <!-- 上传区域 -->
    <div>
      <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;font-weight:500">上传图片（可多选，上限 20 张）</label>
      <input type="file" id="rwmFileInput" accept="image/*" multiple style="display:none" onchange="handleRwmFiles(this.files)">
      <div class="rwm-drop-zone" id="rwmDropZone" onclick="document.getElementById('rwmFileInput').click()">
        <div class="rwm-drop-zone-icon">📁</div>
        <div>点击上传或拖拽图片到此</div>
        <div class="rwm-drop-zone-sub">支持 PNG / JPEG / WebP，可多选，单次上限 20 张</div>
      </div>
    </div>

    <!-- 文件列表 -->
    <div id="rwmFileListContainer" style="display:none">
      <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;font-weight:500">处理进度</label>
      <div class="rwm-file-list" id="rwmFileList"></div>
    </div>

    <!-- v27.2: 增益控制 -->
    <div>
      <div class="form-label-row">
        <label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:4px;font-weight:500">Alpha 增益</label>
        <span class="hint-text" id="rwmGainHint">自动检测（推荐）</span>
      </div>
      <div class="wm-slider" style="margin-bottom:4px">
        <input type="range" id="rwmGainSlider" min="0" max="30" value="0" step="1" oninput="onRwmGainSlider()">
        <span class="wm-slider-val" id="rwmGainVal">0.0</span>
      </div>
      <div style="font-size:11px;color:var(--text-muted)">滑块=0 时自动检测水印强度（推荐）；滑块>0 时使用手动增益（1.0-3.0），适用于自动检测不准的情况</div>
    </div>

    <!-- 说明 -->
    <div class="rwm-info" id="rwmInfo">
      <strong>原理：</strong>基于反向 alpha 混合算法（lossless），从水印区域反向计算原始像素值。<br>
      <strong>v27.2 新增：</strong>自动检测 alpha 增益，适配不同版本的 Gemini 水印（部分版本 alpha 强度更高）。<br>
      <strong>注意：</strong>仅去除右下角可见水印，不影响隐式 SynthID 等水印。处理完成后图片会自动下载，文件名加 <code>_nowm_yyyymmdd_hhmmss</code> 后缀。
    </div>

    <!-- 操作按钮 -->
    <div class="rwm-actions">
      <button class="btn btn-sm" onclick="closeRemoveWmModal()">关闭</button>
      <button class="btn btn-primary btn-sm" id="rwmProcessBtn" onclick="processAllRwmFiles()" disabled>开始去除水印</button>
    </div>
  </div>
</div>

<!-- Prompt library panel -->
<div class="promptlib-panel" id="promptLibPanel">
  <div class="promptlib-header">
    <h3>提示词库</h3>
    <button class="btn btn-sm" onclick="closePromptLib()">关闭</button>
  </div>
  <div class="promptlib-body" id="promptLibList">
    <p class="promptlib-empty" id="promptLibEmpty">暂无收藏的提示词</p>
  </div>
  <div class="promptlib-actions">
    <button class="btn btn-sm btn-outline" onclick="exportPromptLib()">导出</button>
    <button class="btn btn-sm" onclick="importPromptLib()">导入</button>
    <button class="btn btn-sm btn-danger" onclick="clearPromptLib()">清空</button>
  </div>
</div>

<div class="toast-container" id="toastContainer"></div>

<script>
const VERSION='kdr-v1.1';
const STATE_KEY='maliang_state',HISTORY_KEY='maliang_history',PROMPTLIB_KEY='maliang_promptlib';
// kd-v2.0: 单一上游配置（前端副本） —— 顶层 worker 常量在前端不可见，需在 script 内重复定义
const UPSTREAM={base:'https://keydraw.97api.com',origin:'https://keydraw.97api.com',giftKeyFallback:'Gift-Key-V2EX653'};
const SESSION_HEADER='X-Session-Token';
// kd-v2.0: 日额度上限（共享 Gift Key 全 V2EX 共享 999 张/日）
const DAILY_QUOTA=999;
let state=loadState(),generationHistory=loadHistory(),promptLibrary=loadPromptLib();

// 运行时完整图片存储（不存localStorage，避免爆容量）
const liveImages=new Map(); // id -> [{type,value}]
// 并发相关变量
const CONCURRENT_PER_ACCOUNT=3;
let activeSlots=0;
const taskStartTimes=new Map();
let selectedRatio='1:1',refImages=[],selectedDuration=6,selectedQualityTier='standard',selectedVideoResolution='720p';
// 存储配额缓存: accountId -> {mediaUsageBytes, mediaQuotaMb, usagePercent}
const storageCache=new Map();
// 邀请码缓存: accountId -> {inviteCode, inviteLink}
const inviteCache=new Map();

// ===== 模型可用性预检 =====

async function refreshModelAvailability() { return; }

function updateModelAvailabilityUI() { return; }

// ===== 模型类型判断 =====
function isVideoModel(m){return false}  // v1.1: video removed
function isGptImg(m){return m==='gpt-image-2'||m==='grok-imagine-image-edit'}
function supportsRefImage(m){return isGptImg(m)||isVideoModel(m)}

// ===== 模型切换处理 =====
function onModelChange(){
  var model=document.getElementById('modelSelect').value;
  var durGroup=document.getElementById('durationGroup');
  var btn=document.getElementById('generateBtn');
  var refLabel=document.getElementById('refLabel');
  var qtGroup=document.getElementById('qualityTierGroup');
  var vrGroup=document.getElementById('videoResolutionGroup');
  if(durGroup)durGroup.style.display=isVideoModel(model)?'block':'none';
  if(vrGroup)vrGroup.style.display=isVideoModel(model)?'block':'none';
  if(qtGroup)qtGroup.style.display=(model==='gpt-image-2')?'block':'none';
  var qtSelect=document.getElementById('qualityTierSelect');if(qtSelect){qtSelect.disabled=(model!=='gpt-image-2');qtSelect.style.opacity=(model==='gpt-image-2')?'1':'0.4'}
  if(btn)btn.textContent=isVideoModel(model)?'生成视频':'生成图片';
  if(refLabel){
  if(isVideoModel(model)){refLabel.textContent='参考图（可选，图生视频，可多张）'}
  else if(isGptImg(model)){refLabel.textContent='参考图（可选，图生图，可多张）'}
  else{refLabel.textContent='参考图（可选，可多张）'}
  }
  if(model==='gpt-image-2'){updateQualityTierHint()}
  updateGrokSizeHint();
  updateModelAvailabilityUI();
  renderQuotaBadge();
  updateConcurrencyUI();
  if(document.getElementById('settingsModal').classList.contains('show')){
    renderAccountsTable();
  }
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
  renderPromptLib();
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

function defaultState(){return{
  // kd-v2.1: 多 key 池 —— gift key（免费，优先）+ 多个自定义 97api key
  // 每 key 独立跟踪日额度；任 key 当日耗尽则跳过，GMT+8 0点重置
  // key 结构: {key, label, type:'gift'|'custom', dailyCount, dailyDate, exhaustedToday, totalCredits, usedCredits}
  apiKeys:[],
  activeKeyIndex:0,
  // kd-v2.1: 移除 abandonedAccounts（马良遗留，keydraw 共享 Gift Key 模式无废弃概念）
  // kd-v2.1: dailyUsage 现为全局聚合（所有 key 当日总提交数）
  dailyUsage:{date:'',totalCount:0},
  settings:{rotationStrategy:'round-robin',theme:'system',notificationsEnabled:false,customApiKeys:[]},
  activeAccountIndex:-1,rotationIndex:0,lastAutoDay:''
}}
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
    var fetchOpts={};
    // 传递当前账号的session token，以便媒体代理能通过上游认证
    var acc=getEffectiveKeyEntry();
    if(acc&&acc.sessionToken){fetchOpts.headers={'X-Session-Token':acc.sessionToken}}
    var resp=await fetch(proxyUrl,fetchOpts);
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

// ===== API & Key 轮换 =====
// kd-v2.1: 多 key 池 —— gift key（免费，优先）+ 多个自定义 97api key
// 选 key 策略：gift key 优先（免费），若当日耗尽则轮换到下一个可用 custom key
function getGiftKeyEntry(){
  return state.apiKeys.find(k=>k.type==='gift');
}
function getAvailableKeys(){
  checkAndResetDailyUsage();
  return state.apiKeys.filter(k=>!k.exhaustedToday);
}
// 返回当前生效 key（gift 优先，若耗尽则用第一个可用 custom key）
function getEffectiveKeyEntry(){
  var avail=getAvailableKeys();
  if(!avail.length)return null;
  // gift 优先
  var gift=avail.find(k=>k.type==='gift');
  if(gift)return gift;
  // 否则按 rotationStrategy 选 custom key
  if(state.settings.rotationStrategy==='round-robin'){
    return avail[state.activeKeyIndex%avail.length];
  }
  return avail[0]; // most-credits / newest 都返回第一个
}
function getEffectiveKey(){
  var e=getEffectiveKeyEntry();
  return e?e.key:UPSTREAM.giftKeyFallback;
}
function isUsingCustomKey(){
  var e=getEffectiveKeyEntry();
  return e&&e.type==='custom';
}
async function apiFetch(path,options={}){
  const url='/api'+path;
  const st=options._sessionToken||getEffectiveKey();
  const headers={'Content-Type':'application/json',...(options.headers||{})};
  if(st)headers['Authorization']='Bearer '+st;
  return fetch(url,{...options,headers,credentials:'omit'});
}
async function apiFetchMultipart(path,formData,sessionToken){
  const url='/api'+path;
  const st=sessionToken||getEffectiveKey();
  const headers={};
  if(st)headers['Authorization']='Bearer '+st;
  return fetch(url,{method:'POST',headers,body:formData,credentials:'omit'});
}

// kd-v2.1: 旧 state 迁移
function migrateOldStateIfNeeded(){
  // v1.x accountsByKeydraw → 弃用（keydraw 共享 Gift Key 不需要账号池）
  if(state.accountsByKeydraw!==undefined){
    delete state.accountsByKeydraw;delete state.abandonedAccountsByKeydraw;
    delete state.accountsByMaliang;delete state.abandonedAccountsByMaliang;
    delete state.accountsByCustom97api;delete state.abandonedAccountsByCustom97api;
    delete state.activeChannel;delete state.lastChannel;
    delete state.accounts;delete state.abandonedAccounts;
  }
  // kd-v2.0 → v2.1: customApiKey95 (单字符串) → customApiKeys (数组)
  if(state.settings&&state.settings.customApiKey95&&!state.settings.customApiKeys){
    state.settings.customApiKeys=state.settings.customApiKey95?[state.settings.customApiKey95]:[];
    delete state.settings.customApiKey95;
  }
  if(state.settings){
    delete state.settings.defaultPassword;
    delete state.settings.autoCheckin;
    delete state.settings.autoFallbackGpt2;
    delete state.settings.autoRegister;
    if(!state.settings.customApiKeys)state.settings.customApiKeys=[];
  }
  if(!state.dailyUsage||typeof state.dailyUsage!=='object'){
    state.dailyUsage={date:'',totalCount:0};
  }
  if(!Array.isArray(state.apiKeys))state.apiKeys=[];
}

// kd-v2.1: 初始化 key 池 —— gift key 始终在第一位，custom keys 从 settings 加载
function initKeyPool(){
  migrateOldStateIfNeeded();
  checkAndResetDailyUsage();
  var pool=[];
  // gift key 永远第一位
  pool.push({key:UPSTREAM.giftKeyFallback,label:'共享 Gift Key',type:'gift',
    dailyCount:0,dailyDate:getTodayGMT8(),exhaustedToday:false,
    totalCredits:DAILY_QUOTA,usedCredits:0});
  // custom keys
  (state.settings.customApiKeys||[]).forEach(function(k,i){
    if(!k||!k.trim())return;
    pool.push({key:k.trim(),label:'自定义#'+(i+1),type:'custom',
      dailyCount:0,dailyDate:getTodayGMT8(),exhaustedToday:false,
      totalCredits:0,usedCredits:0});  // custom key 无 quota API，totalCredits=0 表示未知
  });
  // 保留旧 key 的 dailyCount/exhaustedToday（如果 key 相同）
  state.apiKeys.forEach(function(old){
    var n=pool.find(p=>p.key===old.key);
    if(n&&old.dailyDate===getTodayGMT8()){
      n.dailyCount=old.dailyCount||0;
      n.exhaustedToday=!!old.exhaustedToday;
      n.usedCredits=old.usedCredits||0;
    }
  });
  state.apiKeys=pool;
  if(state.activeKeyIndex>=pool.length)state.activeKeyIndex=0;
  saveState();
}

// kd-v2.1: 启动时确保 key 池就绪
async function ensureChannelReady(){
  initKeyPool();
  renderQuotaBadge();
  // 异步刷新真实 gift-key（可能上游已轮换）
  (async()=>{try{await refreshGiftKey()}catch(e){console.warn('gift-key 刷新失败:',e.message)}})();
}

// kd-v2.1: 从上游刷新 gift key（若与当前不同则更新池）
async function refreshGiftKey(){
  try{
    const r=await apiFetch('/gift-key',{});
    const d=await r.json();
    const key=d.key||'';
    if(!key)return;
    var gift=getGiftKeyEntry();
    if(gift&&gift.key!==key){
      gift.key=key;
      saveState();renderQuotaBadge();
    }
  }catch(e){/* fallback key 已在池中，无需处理 */}
}

// kd-v2.1: 日额度本地计数器 —— GMT+8 0点重置
function getTodayGMT8(){
  var now=new Date();
  var gmt8Ms=now.getTime()+(now.getTimezoneOffset()*60000)+(8*3600000);
  var gmt8=new Date(gmt8Ms);
  return gmt8.getUTCFullYear()+'-'+String(gmt8.getUTCMonth()+1).padStart(2,'0')+'-'+String(gmt8.getUTCDate()).padStart(2,'0');
}
function checkAndResetDailyUsage(){
  var today=getTodayGMT8();
  if(!state.dailyUsage||state.dailyUsage.date!==today){
    state.dailyUsage={date:today,totalCount:0};
    // 重置所有 key 的当日计数
    (state.apiKeys||[]).forEach(function(k){
      k.dailyDate=today;k.dailyCount=0;k.exhaustedToday=false;k.usedCredits=0;
    });
    saveState();
  }
}
// 任务成功提交后：当前 key 的 dailyCount+1，全局 totalCount+1
function incrementDailyUsage(){
  checkAndResetDailyUsage();
  var e=getEffectiveKeyEntry();
  if(e){e.dailyCount++;e.usedCredits+=getCreditsPerImage(getCurrentModel(),getCurrentTier())}
  state.dailyUsage.totalCount++;
  state.activeKeyIndex++;  // round-robin 推进
  saveState();renderQuotaBadge();
}
// 收到"日限额已用完"错误：标记当前 key 当日耗尽
function markCurrentKeyExhausted(){
  checkAndResetDailyUsage();
  var e=getEffectiveKeyEntry();
  if(e){
    e.exhaustedToday=true;
    toast((e.label||e.key.substring(0,16))+' 当日已耗尽，自动切换到下一个 key','info');
  }
  saveState();renderQuotaBadge();
}

// kd-v2.1: 渲染右上角额度徽章（合并到 usableCreditsTop）
// gift key: 显示 "剩余 X / 999 张"（X = 999 - 全V2EX今日已用，本地估算）
// custom key: 显示 "今日 X 张"（本地累计）
// 多 key: 显示 "X keys · 今日 N 张"
function renderQuotaBadge(){
  var el=document.getElementById('usableCreditsTop');
  var badge=document.getElementById('quotaBadge');
  if(!el||!badge)return;
  checkAndResetDailyUsage();
  var pool=state.apiKeys||[];
  var avail=getAvailableKeys();
  var gift=getGiftKeyEntry();
  var customAvail=avail.filter(k=>k.type==='custom');
  if(!avail.length){
    el.textContent='0';
    badge.title='所有 key 当日已耗尽。GMT+8 0点自动重置，或在设置中添加新的 97api API Key';
    badge.style.color='var(--red)';
  }else if(gift&&!gift.exhaustedToday&&customAvail.length===0){
    // 仅 gift key 可用
    var remaining=DAILY_QUOTA-gift.dailyCount;
    el.textContent=remaining;
    badge.title='共享 Gift Key：今日本地已用 '+gift.dailyCount+' / '+DAILY_QUOTA+' 张（全 V2EX 共享，实际剩余可能更少）。GMT+8 0点重置';
    badge.style.color='var(--text-secondary)';
  }else if(customAvail.length>0){
    // 有 custom key 可用
    el.textContent=state.dailyUsage.totalCount;
    var keyCount=avail.length;
    badge.title=keyCount+' 个 key 可用（gift '+(gift&&!gift.exhaustedToday?'可用':'耗尽')+' + '+customAvail.length+' 自定义）。今日共提交 '+state.dailyUsage.totalCount+' 张';
    badge.style.color='var(--accent)';
  }
}

// kd-v2.1: 注册 = 刷新 gift key（keydraw 共享 Gift Key 模式无需注册）
async function registerAccount(){
  await refreshGiftKey();
  return state.apiKeys[0];
}
// kd-v2.1: 登录 = no-op（Bearer key 鉴权，无需登录）
async function loginAccount(i){
  return {user:{imageCredits:9999}};
}
// kd-v2.1: 刷新所有 key 额度 —— 重新获取 gift key + 重置本地计数显示
// 注：keydraw 无公开 quota API，custom key 的 97api 也无 /v1/dashboard/billing 端点
// "刷新"的实际效果：1) 重新获取 gift key（可能已轮换）2) 重置本地 exhaustedToday 标记
// 这让用户可以在误判耗尽后手动恢复
async function refreshQuota(i){
  // kd-v2.1: 单 key 刷新 = 重置该 key 的 exhaustedToday 标记
  if(i>=0&&i<state.apiKeys.length){
    state.apiKeys[i].exhaustedToday=false;
    saveState();renderQuotaBadge();
  }
}
async function refreshAllQuota(){
  toast('正在刷新所有 key...','info');
  // 1. 重新获取 gift key
  try{await refreshGiftKey()}catch(e){}
  // 2. 重置所有 key 的 exhaustedToday 标记（让用户手动恢复）
  checkAndResetDailyUsage();
  state.apiKeys.forEach(function(k){k.exhaustedToday=false});
  saveState();renderQuotaBadge();
  toast('已刷新 '+state.apiKeys.length+' 个 key（耗尽标记已重置）','success');
}
async function autoRegister(){await registerAccount()}
async function batchVerifyAccounts(){
  if(!state.apiKeys.length){toast('暂无 key','info');return}
  toast('开始批量验证...','info');
  var okN=0;
  for(var i=0;i<state.apiKeys.length;i++){
    // kd-v2.1: 验证方式 = 重置 exhaustedToday 标记（无 quota API 可真实查询）
    state.apiKeys[i].exhaustedToday=false;
    okN++;
  }
  saveState();renderQuotaBadge();
  toast('验证完成: '+okN+' 个 key 已重置','success');
}

// kd-v2.1: autoAbandonAccount 已移除（无废弃账号池概念）
function autoAbandonAccount(){}

// ===== 会话过期检测 (v24) =====
// 上游在 session token 失效时会返回 "请先登录" 等错误，此时需要清除旧 token 重新登录
function isAuthError(msg){
  if(!msg)return false;
  msg=String(msg);
  return msg.includes('请先登录')||msg.includes('未登录')||msg.includes('会话已过期')||msg.includes('无效会话')||msg.includes('token expired')||msg.includes('session expired')||msg.includes('unauthorized')||msg.includes('请重新登录');
}

// ===== 浏览器通知 (v24) =====
function notificationsSupported(){
  return typeof Notification!=='undefined';
}
function notificationsEnabled(){
  return !!(state.settings.notificationsEnabled&&notificationsSupported()&&Notification.permission==='granted');
}
async function requestNotificationPermission(){
  if(!notificationsSupported()){
    toast('当前浏览器不支持通知','error');
    return false;
  }
  if(Notification.permission==='granted')return true;
  if(Notification.permission==='denied'){
    toast('通知权限已被浏览器拒绝，请在浏览器设置中手动开启','error');
    return false;
  }
  var result=await Notification.requestPermission();
  if(result==='granted'){
    toast('通知权限已开启','success');
    return true;
  }
  toast('未授予通知权限','info');
  return false;
}
function notifyGenerationComplete(entry){
  if(!notificationsEnabled()||!entry)return;
  try{
    var title='';
    var body='';
    if(entry.status==='success'){
      title='图片生成完成';
      body='第'+entry.index+'张已生成完成 ('+(entry.model||'')+')';
      if(entry.images&&entry.images.length){
        body+='，共'+entry.images.length+'张';
      }
    }else if(entry.status==='error'){
      title='图片生成失败';
      body='第'+entry.index+'张失败: '+(entry.error||'未知错误');
    }else if(entry.status==='timeout'){
      title='图片生成超时';
      body='第'+entry.index+'张已超时，请检查上游服务';
    }else{
      return;
    }
    var n=new Notification(title,{
      body:body,
      icon:'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="%236A5ACD"/><text x="32" y="42" font-size="36" text-anchor="middle" fill="white" font-family="sans-serif">AI</text></svg>',
      tag:'gen-'+entry.id,
      renotify:true
    });
    // 点击通知聚焦窗口
    n.onclick=function(){window.focus();n.close()};
    // 5 秒后自动关闭（部分浏览器会自动管理）
    setTimeout(function(){try{n.close()}catch(e){}},8000);
  }catch(e){
    console.warn('通知发送失败:',e.message);
  }
}

// kd-v2.1: 设置面板保存/加载 + 通知开关
function updateNotificationsHint(){
  var el=document.getElementById('notificationsHint');
  if(!el)return;
  if(!notificationsSupported()){el.textContent='当前浏览器不支持通知';el.style.color='var(--text-muted)';return}
  if(Notification.permission==='granted'){el.textContent='已开启';el.style.color='var(--green)'}
  else if(Notification.permission==='denied'){el.textContent='已被浏览器拒绝';el.style.color='var(--red)'}
  else{el.textContent='开启后将请求浏览器通知权限';el.style.color='var(--text-muted)'}
}
async function onNotificationsToggle(checked){
  if(checked){
    var granted=await requestNotificationPermission();
    if(!granted){document.getElementById('notificationsEnabled').checked=false}
  }
  updateNotificationsHint();
}
function saveSettings(){
  state.settings.rotationStrategy=document.getElementById('rotationStrategy').value;
  state.settings.notificationsEnabled=document.getElementById('notificationsEnabled').checked;
  // kd-v2.1: 保存多个自定义 97api key（textarea，每行一个）
  var ta=document.getElementById('customApiKeysTA');
  if(ta){
    var keys=ta.value.split(String.fromCharCode(10)).map(k=>k.trim()).filter(k=>k&&!k.startsWith('#'));
    var oldKeys=JSON.stringify(state.settings.customApiKeys||[]);
    state.settings.customApiKeys=keys;
    if(JSON.stringify(keys)!==oldKeys){
      toast('已更新 '+keys.length+' 个自定义 key，正在重新初始化...','info');
      setTimeout(function(){initKeyPool();renderQuotaBadge();renderAccountsTable()},100);
    }
  }
  saveState();updateNotificationsHint();renderQuotaBadge();toast('设置已保存','success');
}
function loadSettingsUI(){
  document.getElementById('rotationStrategy').value=state.settings.rotationStrategy||'round-robin';
  document.getElementById('notificationsEnabled').checked=state.settings.notificationsEnabled===true;
  var ta=document.getElementById('customApiKeysTA');
  if(ta){ta.value=(state.settings.customApiKeys||[]).join(String.fromCharCode(10))}
  applyTheme();updateNotificationsHint();
}
// kd-v2.1: 测试自定义 97api key —— 测试 textarea 中第一个 key
async function testCustomApiKey(){
  var ta=document.getElementById('customApiKeysTA');
  if(!ta){toast('未找到 key 输入框','error');return}
  var keys=ta.value.split(String.fromCharCode(10)).map(k=>k.trim()).filter(k=>k&&!k.startsWith('#'));
  if(!keys.length){toast('请先填入至少一个 API Key','error');return}
  var key=keys[0];
  toast('正在测试第一个 Key ('+key.substring(0,12)+'...)...','info');
  try{
    var r=await fetch('/api/image-tasks/generations',{
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},
      body:JSON.stringify({client_task_id:Date.now()+'-keytest',prompt:'a tiny red dot',model:'gpt-image-2',size:'1024x1024',quality:'auto'})
    });
    var d=await r.json();
    if(!r.ok){toast('Key 测试失败: '+(d.error||d.message||'HTTP '+r.status),'error');return}
    var tid=d.id;
    if(!tid){toast('Key 提交成功但未返回任务ID','info');return}
    var pr=await fetch('/api/image-tasks/'+encodeURIComponent(tid)+'/resume-poll',{
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},
      body:JSON.stringify({extra_timeout_secs:30})
    });
    var pd=await pr.json();
    if(pd.status==='success'){toast('Key 有效，生成成功！','success')}
    else if(pd.status==='error'){toast('Key 有效但生成出错: '+(pd.error||'未知'),'error')}
    else{toast('Key 有效，任务状态: '+pd.status,'info')}
  }catch(e){toast('Key 测试异常: '+e.message,'error')}
}


// ===== 账号/Key 选择 =====
// kd-v2.1: 选 key 由 getEffectiveKeyEntry() 处理，无需 selectAccount/ensureAccount
function getCurrentModel(){return document.getElementById('modelSelect')?document.getElementById('modelSelect').value:'gpt-image-2'}
function getCurrentTier(){return selectedQualityTier||'standard'}
// kd-v2.1: 兼容 stub —— selectAccount 返回当前生效 key entry
function selectAccount(){return getEffectiveKeyEntry()}
async function ensureAccount(){await ensureChannelReady();return getEffectiveKeyEntry()}
function selectAccountWithExclude(excludeSet){return getEffectiveKeyEntry()}
async function ensureAccountWithExclude(excludeSet){await ensureChannelReady();return getEffectiveKeyEntry()}

// ===== 并发生成 =====
// kd-v2.1: 并发数 = 可用 key 数 × 3（每 key 3 并发槽位）
function maxConcurrency(){return getAvailableKeys().length*CONCURRENT_PER_ACCOUNT}
function availableSlots(){return Math.max(0,maxConcurrency()-activeSlots)}
function isGptImgInner(m){return m==='gpt-image-2'||m==='grok-imagine-image-edit'}
function isVideoModelInner(m){return false}  // v1.1: video removed
function isGrokImgModel(m){return m==='grok-imagine-image'||m==='grok-imagine-image-pro'||m==='grok-imagine-image-lite'||m==='grok-imagine-image-edit'}
function supportsRefImageInner(m){return isGptImgInner(m)||isVideoModelInner(m)}

// ===== 画质档位 & 视频清晰度 =====
var TIER_LONGEST={standard:1536,high:2560,ultra:3840};
var TIER_SQUARE={standard:1024,high:2048,ultra:2816};
var PIXEL_BUDGET=8294400;
var ALIGN=64;
var TIER_LABEL={standard:'1.5K',high:'2.5K',ultra:'4K'};
var TIER_PRICE={standard:'¥0.2',high:'¥0.3',ultra:'¥2.0'};

// ===== v25: 计费模型 (credits-based, 1 credit = ¥0.1) =====
// 上游仍在用 imageCredits 字段记账，但签到下线后老账号余额无法补充，一次性即抛
// 各模型/档位单张所需 credits（来自上游 system 配置）
var GPT2_TIER_CREDITS={standard:3,high:8,ultra:30};
var MODEL_CREDITS={
  'grok-imagine-image-lite':0.2,
  'grok-imagine-image':0.4,
  'grok-imagine-image-edit':0.4,
  'grok-imagine-image-pro':1
};
// 视频模型：每秒 credits
var VIDEO_CREDITS_PER_SEC={'grok-imagine-video':1};

// 获取指定模型/档位下单张图片所需 credits
function getCreditsPerImage(model,tier){
  if(model==='gpt-image-2'){
    return GPT2_TIER_CREDITS[tier||'standard']||3;
  }
  if(MODEL_CREDITS[model]){
    return MODEL_CREDITS[model];
  }
  return 3; // 默认按 gpt-image-2 standard
}

// 将 credits 转换为可生成图片数（向下取整）
function creditsToImageCount(credits,model,tier){
  if(!credits||credits<=0)return 0;
  var cost=getCreditsPerImage(model,tier);
  if(cost<=0)return 0;
  return Math.floor(credits/cost);
}

// 判断账号余额是否足以生成至少 1 张图（按当前模型/档位）
function canGenerateAtLeastOne(credits,model,tier){
  return credits>=getCreditsPerImage(model,tier);
}

function calcGptImage2Size(ratio,tier){
  if(ratio==='auto'||ratio==='1:1'){
    return TIER_SQUARE[tier]+'x'+TIER_SQUARE[tier];
  }
  var parts=ratio.split(':');
  var rLong=parseInt(parts[0]),rShort=parseInt(parts[1]);
  var isWide=rLong>=rShort;
  var longE=TIER_LONGEST[tier];
  var shortE=Math.round(longE*(isWide?rShort:rLong)/(isWide?rLong:rShort)/ALIGN)*ALIGN;
  if(shortE<512)shortE=512;
  if(longE*shortE>PIXEL_BUDGET){
    var scale=Math.sqrt(PIXEL_BUDGET/(longE*shortE));
    longE=Math.round(longE*scale/ALIGN)*ALIGN;
    shortE=Math.round(shortE*scale/ALIGN)*ALIGN;
    if(shortE<512)shortE=512;
  }
  return (isWide?longE:shortE)+'x'+(isWide?shortE:longE);
}

function getGrokSize(r){
  if(r==='auto')r='1:1';
  var grokMap={
    '1:1':'1024x1024',
    '16:9':'1280x720','2:1':'1280x720','21:9':'1280x720',
    '9:16':'720x1280','1:2':'720x1280','9:21':'720x1280',
    '3:2':'1792x1024','4:3':'1792x1024','5:4':'1792x1024',
    '2:3':'1024x1792','3:4':'1024x1792','4:5':'1024x1792'
  };
  return grokMap[r]||'1024x1024';
}

function getEffectiveSize(model,ratio,tier){
  if(model==='grok-imagine-image-lite')return '784x1168';
  if(isGrokImgModel(model))return getGrokSize(ratio);
  if(isVideoModelInner(model))return getGrokSize(ratio);
  if(model==='gpt-image-2')return calcGptImage2Size(ratio,tier||'standard');
  return getGptSizeLegacy(ratio);
}

function getGptSizeLegacy(r){
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

function onRatioChange(){
  var sel=document.getElementById('ratioSelect');
  if(sel)selectedRatio=sel.value;
  var model=document.getElementById('modelSelect').value;
  if(model==='gpt-image-2'){updateQualityTierHint()}
  updateGrokSizeHint();
}

function toggleOngoingFilter(){
  var chk=document.getElementById('ongoingChk');
  var showOngoing=chk&&chk.checked;
  document.querySelectorAll('.hist-item').forEach(function(el){
    if(!showOngoing){el.style.display='';return}
    var isRunning=el.classList.contains('running-item');
    el.style.display=isRunning?'':'none';
  });
}

// kd-v2.1: onQualityTierChange2 已移除（重复下拉已删除）
function onQualityTierChange(){
  selectedQualityTier=document.getElementById('qualityTierSelect').value;
  updateQualityTierHint();
  renderQuotaBadge();
  updateConcurrencyUI();
  if(document.getElementById('settingsModal').classList.contains('show')){
    renderAccountsTable();
  }
}
function updateQualityTierHint(){
  var model=document.getElementById('modelSelect').value;
  var tier=selectedQualityTier;
  var sizeStr=calcGptImage2Size(selectedRatio,tier);
  var qh=document.getElementById('qualityTierHint');if(qh)qh.textContent=TIER_LABEL[tier]+'\\u00B7'+sizeStr+'\\u00B7'+TIER_PRICE[tier]+'/张';
}
function onVideoResolutionChange(){
  selectedVideoResolution=document.getElementById('videoResolutionSelect').value;
}
function updateGrokSizeHint(){
  var model=document.getElementById('modelSelect').value;
  var hintGroup=document.getElementById('grokSizeHintGroup');
  var hintEl=document.getElementById('grokSizeHintText');
  if(!hintGroup||!hintEl)return;
  if(model==='grok-imagine-image-lite'){
    hintGroup.style.display='block';
    hintEl.textContent='lite 模型上游仅支持 2:3 \\u00B7 784\\u00D71168';
  }else if(isGrokImgModel(model)||isVideoModelInner(model)){
    hintGroup.style.display='block';
    var sz=getGrokSize(selectedRatio);
    hintEl.textContent='Grok 上游尺寸: '+sz;
  }else{
    hintGroup.style.display='none';
  }
}

// v0.4: keydraw requires client_task_id in format: timestamp-randomhex
//       (e.g. 1783440890123-3d70ac176c97). Other formats are silently
//       rejected with misleading error '生成数量只能是 1、2、3、4'.
function genClientTaskId(){return Date.now()+'-'+Math.random().toString(16).slice(2)}
async function startGeneration(){
  const prompt=document.getElementById('promptInput').value.trim();
  if(!prompt){toast('请输入提示词','error');return}
  const model=document.getElementById('modelSelect').value;
  // Model availability pre-check
  if(model==='grok-imagine-video'&&modelAvailability.videoAvailable===false){toast(modelAvailability.videoError||'视频模型已临时下架，暂不可用','error');return}
  const count=parseInt(document.getElementById('countSelect').value)||1;
  const size=getEffectiveSize(model,selectedRatio,selectedQualityTier);
  const hasRef=refImages.length>0&&supportsRefImageInner(model);
  const currentRefImages=[...refImages];
  const isVideo=isVideoModelInner(model);
  const duration=isVideo?parseInt(document.getElementById('durationSelect').value)||6:null;
  const currentQualityTier=(model==='gpt-image-2')?selectedQualityTier:null;
  const currentResolution=isVideo?selectedVideoResolution:null;
  const btn=document.getElementById('generateBtn');btn.disabled=true;btn.textContent='提交中...';setTimeout(()=>{btn.disabled=false;btn.textContent='生成图片'},500);
  const entries=[];
  for(let i=0;i<count;i++){const entry={id:Date.now().toString(36)+'_'+i,prompt,model,ratio:selectedRatio,count,index:i+1,timestamp:Date.now(),status:'queued',images:[],error:'',account:'',progress:0,progressText:'排队中',startedAt:0,isVideo:isVideo,duration:duration};entries.push(entry);taskStartTimes.set(entry.id,Date.now());addHistory(entry)}
  toast(count+'个任务已加入队列','info');
  (async()=>{let submitted=0;while(submitted<entries.length){while(availableSlots()<=0){await sleep(500)}const entry=entries[submitted];submitted++;activeSlots++;updateConcurrencyUI();executeTask(entry,model,prompt,size,hasRef,currentRefImages,isVideo,duration,currentQualityTier,currentResolution).finally(()=>{activeSlots--;updateConcurrencyUI()});await sleep(300)}})();
}

// 额度不足时自动换号：记录已试过的账号，避免重复
let exhaustedAccounts=new Set();

async function executeTaskOnChannel(entry,model,prompt,size,hasRef,currentRefImages,isVideo,duration,qualityTier,resolutionName){
  let retryCount=0;const maxRetries=3;
  while(retryCount<=maxRetries){
    try{
      // kd-v2.1: 选 key —— gift 优先，耗尽则轮换到 custom key
      var keyEntry=getEffectiveKeyEntry();
      if(!keyEntry){
        entry.status='error';entry.error='所有 key 当日已耗尽，请等待 GMT+8 0点重置或在设置中添加新 key';
        entry.progressText='失败';updateHistory(entry.id,{status:entry.status,error:entry.error,progressText:entry.progressText});
        toast(entry.error,'error');notifyGenerationComplete(entry);return;
      }
      entry.account=keyEntry.label;entry.status='running';entry.progressText='提交任务中... [使用'+keyEntry.label+']';entry.progress=5;entry.startedAt=Date.now();taskStartTimes.set(entry.id,entry.startedAt);
      updateHistory(entry.id,{status:entry.status,account:entry.account,progressText:entry.progressText,progress:entry.progress,startedAt:entry.startedAt});
      const clientTaskId=entry.clientTaskId||(entry.clientTaskId=genClientTaskId());
      let r;
      if(hasRef && currentRefImages && currentRefImages.length){
        const fd=new FormData();
        currentRefImages.forEach((img,idx)=>{
          const arr=img.dataUrl.split(',');
          const mime=arr[0].match(/:(.*?);/)[1];
          const bstr=atob(arr[1]);
          const u8=new Uint8Array(bstr.length);
          for(let i=0;i<bstr.length;i++)u8[i]=bstr.charCodeAt(i);
          fd.append('image', new Blob([u8],{type:mime}), img.name||('ref_'+idx+'.png'));
        });
        fd.append('client_task_id', clientTaskId);
        fd.append('prompt', prompt);
        fd.append('model', model);
        if(size) fd.append('size', size);
        fd.append('quality', 'auto');
        fd.append('n', '1');
        r=await apiFetchMultipart('/image-tasks/edits', fd, keyEntry.key);
      } else {
        const body={client_task_id:clientTaskId, prompt, model, quality:'auto'};
        if(size) body.size=size;
        r=await apiFetch('/image-tasks/generations',{method:'POST',body:JSON.stringify(body),_sessionToken:keyEntry.key});
      }
      const d=await r.json();if(!r.ok){const errMsg=d.error||d.message||d.detail?.error?.message||d.detail||'创建任务失败';
        // kd-v2.1: 日限额/额度耗尽 → 标记当前 key 当日耗尽，自动换 key 重试
        if(errMsg.includes('日限额')||errMsg.includes('insufficient_quota')||errMsg.includes('额度不足')||errMsg.includes('余额不足')||errMsg.includes('quota')){
          markCurrentKeyExhausted();
          retryCount++;entry.progressText=keyEntry.label+' 耗尽，换 key 重试 ('+retryCount+'/'+maxRetries+')';entry.progress=0;
          updateHistory(entry.id,{status:'queued',progressText:entry.progressText,progress:entry.progress});
          await sleep(500);continue;
        }
        throw new Error(errMsg)}
      const tid=d.id;if(!tid)throw new Error('未返回任务ID');
      entry.progressText='任务已提交，等待生成...';entry.progress=10;updateHistory(entry.id,{progressText:entry.progressText,progress:entry.progress});
      const res=await pollTask(tid,keyEntry.key,entry);
      if(res){entry.status='success';entry.images=res.images;entry.progress=100;entry.progressText='生成完成';updateHistory(entry.id,{status:entry.status,images:entry.images,progress:entry.progress,progressText:entry.progressText});notifyGenerationComplete(entry);return}
    }catch(e){const errMsg=extractErrorMessage(e.message);
      // kd-v2.1: 日限额错误 → 已在 pollTask 内标记，这里只重试
      if(errMsg.includes('日限额')||errMsg.includes('额度')||errMsg.includes('quota')){
        if(retryCount<maxRetries){retryCount++;entry.status='running';entry.progressText='换 key 重试 ('+retryCount+'/'+maxRetries+')';entry.progress=0;updateHistory(entry.id,{status:entry.status,progressText:entry.progressText,progress:entry.progress});await sleep(500);continue}
      }
      if(retryCount<maxRetries){retryCount++;entry.status='running';entry.progressText='失败，准备重试 ('+retryCount+'/'+maxRetries+')';entry.progress=0;updateHistory(entry.id,{status:entry.status,progressText:entry.progressText,progress:entry.progress});await sleep(1500);continue}
      entry.status=errMsg.includes('超时')?'timeout':'error';entry.error=errMsg;entry.progressText='失败';updateHistory(entry.id,{status:entry.status,error:entry.error,progressText:entry.progressText});toast('第'+entry.index+'张失败: '+errMsg,'error');notifyGenerationComplete(entry);
      return}
  }
}

// kd-v2.1: executeTask 包装层 —— 确保通道就绪，委托给 executeTaskOnChannel
// 任务成功后调用 incrementDailyUsage()；日限额错误由 executeTaskOnChannel 内部处理换 key
async function executeTask(entry,model,prompt,size,hasRef,currentRefImages,isVideo,duration,qualityTier,resolutionName){
  await ensureChannelReady();
  var result=await executeTaskOnChannel(entry,model,prompt,size,hasRef,currentRefImages,isVideo,duration,qualityTier,resolutionName);
  // 任务成功 → 日计数器 +1
  incrementDailyUsage();
  return result;
}

// v1.2: 错误消息处理 —— 优先透传上游原始错误（带"日限额"/"Invalid API key"/"quota"等关键字）
//       方便用户在前端任务列表看到真实原因，而非笼统的"生成失败"
function extractErrorMessage(raw){var msg=raw||'未知错误';
  // v1.2: 上游错误原样透传（不替换为模糊描述）
  if(msg.includes('日限额')||msg.includes('api key')||msg.includes('API key')||msg.includes('Invalid API')||msg.includes('quota')||msg.includes('额度'))return msg;
  if(msg.includes('上游图片接口返回失败')||msg.includes('上游')&&msg.includes('失败'))return msg;
  if(msg.includes('临时下架')||msg.includes('暂不开放'))return'视频模型已临时下架，暂不可用';
  if(msg.includes('not an image model'))return'视频模型API端点错误，请更新版本';
  if(msg.includes('content_policy')||msg.includes('policy')||msg.includes('safety'))return'内容违反政策(OpenAI安全策略限制)';
  if(msg.includes('rate_limit'))return'请求频率超限，请稍后再试';
  if(msg.includes('insufficient_quota')||msg.includes('额度不足')||msg.includes('余额不足'))return'账户余额不足，请注册新账号或充值';
  if(msg.includes('超时')||msg.includes('timeout'))return msg;
  if(msg.includes('已注册'))return'当前IP今日已注册过账号';
  if(msg.includes('无效')||msg.includes('invalid'))return'请求参数无效: '+msg;
  if(msg.includes('failed'))return'生成失败: '+msg;
  return msg}

function mapProgressInfo(task,isVideo){const p=task.progress||0;const status=task.status||'';const detail=task.detail||task.statusText||'';if(status==='pending'||status==='queued')return{text:'排队等待中...',pct:5};if(status==='processing'||status==='running'){if(p<20)return{text:'正在分析提示词...',pct:15};if(p<40)return{text:isVideo?'正在生成视频初稿...':'正在生成图片初稿...',pct:30};if(p<60)return{text:isVideo?'正在细化视频细节...':'正在细化图片细节...',pct:50};if(p<80)return{text:isVideo?'正在渲染最终视频...':'正在渲染最终图片...',pct:70};if(p<95)return{text:'即将完成...',pct:88};return{text:'最后处理中...',pct:95}}if(detail)return{text:detail,pct:Math.max(10,Math.min(90,p))};return{text:'生成中... '+p+'%',pct:Math.max(10,Math.min(90,p))}}
function formatElapsed(ms){const s=Math.floor(ms/1000);if(s<60)return s+'秒';const m=Math.floor(s/60);return m+'分'+(s%60)+'秒'}

async function pollTask(tid,st,entry){
  // v0.1: keydraw.97api.com 长轮询
  // POST /api/image-tasks/{id}/resume-poll {extra_timeout_secs:120}
  // 响应格式: {id, mode, status:"queued"|"running"|"success"|"failed"|"error", progress:"...", data:[{url, revised_prompt}], duration_ms, error?}
  // v1.2: status:"error" 也视为终止状态（上游 97api 在 API key 限额耗尽等场景会返回此状态）
  //       v1.1 只识别 "success"/"failed"，导致对 "error" 持续轮询 300s 然后误报"超时"
  const max=300*1000,start=Date.now();let errs=0;
  function resolveUrl(v){if(!v)return v;if(v.startsWith('data:')||v.startsWith('http://')||v.startsWith('https://'))return v;if(v.startsWith('/'))return 'https://keydraw.97api.com'+v;return v}
  while(Date.now()-start<max){
    try{
      const r=await apiFetch('/image-tasks/'+encodeURIComponent(tid)+'/resume-poll',{method:'POST',body:JSON.stringify({extra_timeout_secs:120}),_sessionToken:st});
      const d=await r.json();
      if(!r.ok){
        const pollErr=d.error||d.message||'轮询失败';
        if(isAuthError(pollErr)&&!authRetried){
          // gift-key 模式下不太可能过期，但保留逻辑
        }
        throw new Error(pollErr);
      }
      // v0.1: keydraw 直接在顶层返回任务字段（无 d.task / d.video 包装）
      const status=d.status||'';
      const progress=d.progress||'';
      // 更新进度
      var pct=50,ptext='生成中';
      if(status==='queued'){pct=5;ptext='排队中'}
      else if(status==='running'){pct=70;ptext=progress||'生成中'}
      else if(status==='success'){pct=100;ptext='完成'}
      else if(status==='failed'){pct=0;ptext='失败'}
      else if(status==='error'){pct=0;ptext='上游错误'}  // v1.2: 新增
      entry.progress=pct;entry.progressText=ptext;
      // v1.2: 保存上游原始错误，供前端 debug
      if(d.error){entry.upstreamError=d.error;entry.upstreamProgress=progress}
      updateHistory(entry.id,{progress:entry.progress,progressText:entry.progressText,upstreamError:entry.upstreamError});
      if(status==='success'){
        // 提取图片
        let images=[];
        if(Array.isArray(d.data)){
          d.data.forEach(item=>{
            if(item.url)images.push({type:'url',value:resolveUrl(item.url)});
            else if(item.b64_json)images.push({type:'b64',value:'data:image/png;base64,'+item.b64_json});
          });
        }
        if(!images.length)throw new Error('任务成功但无图片数据');
        return{images,model:d.model||entry.model,taskId:tid};
      }
      // v1.2: status === 'error' 也是终止状态，直接抛出上游原始错误
      //       上游典型错误："api key 日限额已用完"、"Invalid API key"、"content_policy_violation"
      if(status==='error'){
        var errDetail=d.error||d.detail||d.message||'上游返回 error 状态（无具体错误信息）';
        // 附加 progress 阶段信息（如 "starting_generation"），方便定位
        if(progress&&progress!==errDetail){errDetail=errDetail+' [阶段: '+progress+']'}
        throw new Error(errDetail);
      }
      if(status==='failed'){
        throw new Error(d.error||d.detail||'生成失败');
      }
      // queued / running → 继续轮询（resume-poll 会阻塞 120s，所以直接 continue）
      errs=0;
    }catch(e){
      errs++;
      if(errs>=8)throw e;
      if(e.name==='AbortError')throw e;
      await sleep(2000*errs);
    }
  }
  // v1.2: 真超时才走这里 —— 此时上游确实没在 max 秒内返回终态
  //       附带 entry.upstreamError（如有）让用户看到最后已知状态
  var upstreamDetail=entry.upstreamError||'';
  var upstreamProgress=entry.upstreamProgress||'';
  var suffix='';
  if(upstreamDetail){suffix='，上游最后状态: '+upstreamDetail}
  else if(upstreamProgress){suffix='，最后阶段: '+upstreamProgress}
  throw new Error('图片生成超时('+Math.floor(max/1000)+'秒)'+suffix);
}

// ===== 渲染 =====
function renderAll(){renderQuotaBadge();updateConcurrencyUI()}
// kd-v2.1: renderTopbar 合并到 renderQuotaBadge（右上角额度徽章）
function updateConcurrencyUI(){const mx=maxConcurrency(),cur=activeSlots;var el1=document.getElementById('concurrencyInfo');if(el1)el1.textContent='并发: '+cur+'/'+mx}

// ===== 构建图片HTML =====
function buildImageHtml(h,imgs){
  var html='';
  var isVideo=h.isVideo||false;
  var hasB64=imgs.some(function(img){return img.type==='b64'});
  if(hasB64){html+='<div style="padding:4px 12px;font-size:.72rem;color:var(--orange);background:rgba(253,203,110,.08)">\\u26A0 部分数据为临时内容，刷新后将丢失，请及时保存</div>'}
  // 获取当前session token用于媒体代理认证
  var currentToken='';
  var acc=getEffectiveKeyEntry();
  if(acc)currentToken=acc.sessionToken;
  html+='<div class="hist-img-link">';
  imgs.forEach(function(img,imgIdx){
    var rawSrc;
    if(img.type==='b64'||img.value.startsWith('data:')){rawSrc=img.value}
    else if(img.value.startsWith('http')){rawSrc=img.value}
    else{rawSrc='https://grok.17nas.com'+(img.value.startsWith('/')?'':'/')+img.value}
    var isVideoFile=img.type==='video'||rawSrc.match(/\\.(mp4|webm)(\\?|$)/i);
    if(isVideoFile){
      var videoSrc=proxyImageUrl(rawSrc);
      if(currentToken&&!videoSrc.startsWith('data:')){videoSrc+=(videoSrc.includes('?')?'&':'?')+'token='+encodeURIComponent(currentToken)}
      var dlHref=rawSrc;
      if(!dlHref.startsWith('data:')&&currentToken){dlHref=videoSrc}
      html+='<a href="'+dlHref+'" target="_blank" download="video_'+h.id+'_'+imgIdx+'.mp4">\\u2197 查看和保存视频</a>';
      html+='<video src="'+videoSrc+'" controls style="max-width:100%;max-height:300px;margin:4px 12px 8px;border-radius:6px;display:block"></video>';
    }else{
      var dlHref=rawSrc;
      // 下载链接也走代理，确保浏览器能下载
      if(!dlHref.startsWith('data:')&&currentToken){
        var proxySrc=proxyImageUrl(rawSrc);
        if(proxySrc!==rawSrc){dlHref=proxySrc+(proxySrc.includes('?')?'&':'?')+'token='+encodeURIComponent(currentToken)}
      }
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
  if(h.status==='success'){const imgs=liveImages.get(h.id);if(imgs&&imgs.length&&!el.querySelector('.hist-img-link')){const imagesHtml=buildImageHtml(h,imgs);const errorEl2=el.querySelector('.hist-error');const promptEl=el.querySelector('.hist-prompt');if(errorEl2){errorEl2.insertAdjacentHTML('afterend',imagesHtml)}else if(promptEl){promptEl.insertAdjacentHTML('afterend',imagesHtml)}}}
}

function buildHistoryElement(h){
  const t=new Date(h.timestamp);
  const timeStr=String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0')+' '+String(t.getHours()).padStart(2,'0')+':'+String(t.getMinutes()).padStart(2,'0')+':'+String(t.getSeconds()).padStart(2,'0');
  const statusMap={success:{cls:'ok',label:'\\u2713成功'},error:{cls:'err',label:'\\u2717失败'},timeout:{cls:'timeout',label:'\\u23F1超时'},running:{cls:'running',label:'\\u25CF生成中'},queued:{cls:'queued',label:'\\u25CB排队中'}};
  const st=statusMap[h.status]||statusMap.error;
  const div=document.createElement('div');
  div.className='hist-item'+((h.status==='running'||h.status==='queued')?' running-item':'');
  div.setAttribute('data-hist-id',h.id);
  const statusIconMap={success:'<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="#00CC00"/><path d="M4.5 8L7 10.5L11.5 5.5" stroke="#FFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',error:'<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="#FF0000"/><path d="M5.5 5.5L10.5 10.5M10.5 5.5L5.5 10.5" stroke="#FFF" stroke-width="1.8" stroke-linecap="round"/></svg>',timeout:'<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="#FFCC00"/><path d="M8 4.5V8.5L10.5 10" stroke="#FFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',running:'<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="#74b9ff"/><circle cx="8" cy="8" r="2" fill="#FFF"/></svg>',queued:'<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="#A0AEC0"/><circle cx="8" cy="8" r="2" fill="#FFF"/></svg>'};
  const icon=statusIconMap[h.status]||statusIconMap.error;
  let inner='<span class="status-icon">'+icon+'</span><div class="hist-body">';
  inner+='<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"><span class="hist-time">'+timeStr+'</span><span class="hist-model">'+escHtml(h.model||'')+'</span>';
  if(h.account)inner+='<span class="hist-account">@'+escHtml(h.account)+'</span>';
  inner+='<span style="flex:1"></span>';
  inner+='<span class="hist-actions">';
  inner+='<button class="icon-btn" onclick="copyHistPrompt(this)" title="复制提示词"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>';
  if(h.status==='success'){
    inner+='<button class="icon-btn" onclick="downloadHistImage(this)" title="下载图片"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg></button>';
  }
  inner+='</span></div>';
  inner+='<div class="hist-prompt">'+escHtml(h.prompt)+'</div>';
  if(h.error)inner+='<div class="hist-error">'+escHtml(h.error)+'</div>';
  if(h.status==='running'||h.status==='queued'){const startTs=taskStartTimes.get(h.id)||h.timestamp;const elapsed=formatElapsed(Date.now()-startTs);inner+='<div class="hist-progress"><div class="pbar"><div class="pfill" style="width:'+Math.max(5,h.progress||0)+'%"></div></div><div class="ptxt">'+escHtml(h.progressText||'等待中')+'<span class="elapsed">'+elapsed+'</span></div></div>'}
  const imgs=liveImages.get(h.id);
  if(imgs&&imgs.length){inner+=buildImageHtml(h,imgs)}
  inner+='</div>'; // close hist-body
  div.innerHTML=inner;
  return div;
}

function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function proxyImageUrl(src){if(!src)return src;if(src.startsWith('data:'))return src;if(src.startsWith('http://'))return '/api/media-proxy?url='+encodeURIComponent(src);if(src.startsWith('https://grok.17nas.com/'))return '/api/media-proxy?url='+encodeURIComponent(src);if(src.startsWith('https://'))return src;if(src.startsWith('/local-api/'))return '/api/media-proxy?url='+encodeURIComponent('https://grok.17nas.com'+src);return src}

function downloadHistImage(el){
  var histEl=el.closest('[data-hist-id]');
  if(!histEl)return;
  var id=histEl.getAttribute('data-hist-id');
  var imgs=liveImages.get(id);
  if(!imgs||!imgs.length){toast('暂无可下载图片','info');return}
  var link=histEl.querySelector('.hist-img-link a[download]');
  if(link){link.click();return}
  var img=imgs[0];
  if(img.type==='b64'||img.value.startsWith('data:')){
    var a=document.createElement('a');a.href=img.value;a.download='image_'+id+'.png';a.click();
  }else{
    var proxySrc=proxyImageUrl(img.value);
    var acc=getEffectiveKeyEntry();
    if(acc&&!proxySrc.startsWith('data:'))proxySrc+=(proxySrc.includes('?')?'&':'?')+'token='+encodeURIComponent(acc.sessionToken);
    var a=document.createElement('a');a.href=proxySrc;a.target='_blank';a.download='image_'+id+'.png';a.click();
  }
}

setInterval(()=>{document.querySelectorAll('.hist-item.running-item').forEach(el=>{const id=el.getAttribute('data-hist-id');const startTs=taskStartTimes.get(id);if(!startTs)return;const elapsedEl=el.querySelector('.elapsed');if(elapsedEl)elapsedEl.textContent=formatElapsed(Date.now()-startTs)})},1000);

// ===== 参考图 =====
function handleRefImages(input){const files=Array.from(input.files).filter(f=>f.type.startsWith('image/'));if(!files.length)return;let pending=files.length;files.forEach(f=>{const r=new FileReader();r.onload=e=>{refImages.push({name:f.name,type:f.type,dataUrl:e.target.result});pending--;if(pending===0)renderRefGrid()};r.readAsDataURL(f)});input.value=''}
function addMoreRefImages(){document.getElementById('refFileInput').click()}
function renderRefGrid(){const g=document.getElementById('refGrid');if(!refImages.length){g.innerHTML='<div class="ref-add" onclick="addMoreRefImages()" id="refAddBtn" title="添加参考图"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></div>';setupRefDragDrop();return}g.innerHTML=refImages.map((img,i)=>'<div class="ref-thumb"><img src="'+img.dataUrl+'" alt="ref'+(i+1)+'"><span class="ref-del" onclick="removeRefImage('+i+')">&times;</span></div>').join('')+'<div class="ref-add" onclick="addMoreRefImages()" id="refAddBtn" title="添加参考图"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></div>';setupRefDragDrop()}
function removeRefImage(i){refImages.splice(i,1);renderRefGrid()}
function setupRefDragDrop(){
  var el=document.getElementById('refAddBtn');
  if(!el)return;
  el.addEventListener('dragover',function(e){e.preventDefault();el.classList.add('dragover')});
  el.addEventListener('dragleave',function(){el.classList.remove('dragover')});
  el.addEventListener('drop',function(e){e.preventDefault();el.classList.remove('dragover');var files=Array.from(e.dataTransfer.files).filter(f=>f.type.startsWith('image/'));if(!files.length)return;var pending=files.length;files.forEach(f=>{var r=new FileReader();r.onload=ev=>{refImages.push({name:f.name,type:f.type,dataUrl:ev.target.result});pending--;if(pending===0)renderRefGrid()};r.readAsDataURL(f)})});
}
// Ratio select init
(function(){var sel=document.getElementById('ratioSelect');if(sel){sel.value=selectedRatio}})();

// Mobile drawer
function relocate(){var tc=document.getElementById('taskCard'),cp=document.getElementById('centerPanel'),db=document.getElementById('drawerBody');if(!tc||!cp||!db)return;if(innerWidth<=768){if(tc.parentElement!==db)db.appendChild(tc)}else{if(tc.parentElement!==cp)cp.appendChild(tc);document.getElementById('historyDrawer').classList.remove('open')}}
function toggleDrawer(){var d=document.getElementById('historyDrawer'),svg=d.querySelector('.drawer-header button svg');d.classList.toggle('open');if(svg)svg.setAttribute('points',d.classList.contains('open')?'6 9 12 15 18 9':'18 15 12 9 6 15')}
relocate();addEventListener('resize',relocate);

// ===== 设置弹窗 =====
function showSettingsModal(){renderAccountsTable();loadSettingsUI();document.getElementById('settingsModal').classList.add('show')}
function closeSettingsModal(){document.getElementById('settingsModal').classList.remove('show')}
// kd-v2.1: key 列表渲染（替代 v25 账号表）
function renderAccountsTable(){
  var c=document.getElementById('accountsTableContainer');
  if(!c)return;
  var pool=state.apiKeys||[];
  if(!pool.length){c.innerHTML='<p style="color:var(--text-muted);font-size:13px;padding:10px">暂无 key</p>';return}
  var html='<table class="accounts-table"><thead><tr><th>Key</th><th>类型</th><th>今日</th><th>状态</th><th>操作</th></tr></thead><tbody>';
  pool.forEach(function(k,i){
    var status=k.exhaustedToday?'<span style="color:var(--red)">已耗尽</span>':'<span style="color:var(--green)">可用</span>';
    var typeLabel=k.type==='gift'?'共享 Gift':'自定义';
    var keyDisplay=k.type==='gift'?'(内置)':escHtml(k.key.substring(0,12))+'...';
    html+='<tr><td title="'+escHtml(k.key)+'">'+escHtml(k.label)+'<br><span style="font-size:10px;color:var(--text-muted);font-family:var(--mono)">'+keyDisplay+'</span></td>';
    html+='<td>'+typeLabel+'</td>';
    html+='<td>'+k.dailyCount+(k.type==='gift'?' / '+DAILY_QUOTA:'')+'</td>';
    html+='<td>'+status+'</td>';
    html+='<td><button class="btn btn-xs" onclick="refreshQuota('+i+')" title="重置该 key 的耗尽标记">恢复</button></td>';
    html+='</tr>';
  });
  html+='</tbody></table>';
  c.innerHTML=html;
}

// ===== 历史记录导入导出 =====
function exportHistory(){if(!generationHistory.length){toast('暂无历史记录可导出','info');return}var exportData=generationHistory.map(function(h){var entry={id:h.id,prompt:h.prompt,model:h.model,ratio:h.ratio,timestamp:h.timestamp,status:h.status,error:h.error||'',account:h.account||'',startedAt:h.startedAt||0};if(h.images&&h.images.length){var imgs=liveImages.get(h.id);entry.images=h.images.map(function(img,idx){if(img.type==='url')return{type:'url',value:img.value};if(imgs&&imgs[idx]&&(imgs[idx].type==='b64'||imgs[idx].value.startsWith('data:'))){return{type:'b64',value:imgs[idx].value}}return{type:img.type,value:img.value}})}return entry});var b=new Blob([JSON.stringify(exportData,null,2)],{type:'application/json'});var u=URL.createObjectURL(b);var a=document.createElement('a');a.href=u;a.download='ai_image_generator_history_'+new Date().toISOString().split('T')[0]+'.json';a.click();URL.revokeObjectURL(u);toast('历史记录已导出','success')}
function importHistory(){document.getElementById('importHistoryInput').click()}
function handleImportHistory(input){var file=input.files[0];if(!file)return;var reader=new FileReader();reader.onload=function(e){try{var data=JSON.parse(e.target.result);var arr=Array.isArray(data)?data:[data];var n=0;arr.forEach(function(item){if(!item.id||!item.prompt)return;if(generationHistory.some(function(h){return h.id===item.id}))return;generationHistory.push(item);if(item.images&&item.images.length){var restored=item.images.filter(function(img){return img.type==='url'&&img.value}).map(function(img){return{type:img.type,value:img.value}});if(restored.length)liveImages.set(item.id,restored);var b64restored=item.images.filter(function(img){return img.type==='b64'&&img.value&&img.value.startsWith('data:')}).map(function(img){return{type:img.type,value:img.value}});if(b64restored.length){if(!liveImages.has(item.id))liveImages.set(item.id,[]);var existing=liveImages.get(item.id);b64restored.forEach(function(br){if(!existing.some(function(e){return e.value===br.value}))existing.push(br)})}}if(item.startedAt&&item.startedAt>0)taskStartTimes.set(item.id,item.startedAt);else if(item.timestamp)taskStartTimes.set(item.id,item.timestamp);n++});if(n>0){saveHistory();renderFullHistory();toast('导入'+n+'条历史记录','success')}else{toast('无新历史记录可导入','info')}}catch(err){toast('导入失败: '+err.message,'error')}};reader.readAsText(file);input.value=''}


// ===== 水印/去水印模块（从 v27.2 恢复）=====
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

// ===== v27: 去除水印功能 =====
// 基于"反向 alpha 混合"算法（lossless），从水印区域反向计算原始像素值
// 算法：C_original = (C_watermarked - alpha * 255) / (1 - alpha)
// alpha 来自参考 PNG（在纯黑背景上捕获的水印图像，像素亮度 = alpha 值）

// 内嵌的 alpha map PNG（base64 data URL），避免外部资源依赖
const RWM_ALPHA_MAPS = {
  gemini_48: 'data:image/png;base64,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',
  gemini_96: 'data:image/png;base64,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',
  doubao: 'data:image/png;base64,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'
};

// 去除水印状态
let rwmState = {
  type: 'gemini',  // 'gemini' or 'doubao'
  files: [],       // [{file, status, name, blob, error}]
  alphaMaps: {     // 缓存解码后的 alpha map（Float32Array）
    gemini_48: null,
    gemini_96: null,
    doubao: null
  },
  alphaMapDims: {  // alpha map 的宽高
    gemini_48: {w: 48, h: 48},
    gemini_96: {w: 96, h: 96},
    doubao: {w: 120, h: 20}
  },
  manualGain: 0  // v27.2: 手动增益（0 = 自动检测，>0 = 使用指定值）
};

const RWM_MAX_FILES = 20;
const RWM_ALPHA_THRESHOLD = 0.002;
const RWM_MAX_ALPHA = 0.99;
const RWM_LOGO_VALUE = 255;  // 水印颜色为白色

// 打开/关闭面板
function openRemoveWmModal() {
  document.getElementById('removeWmPanel').classList.add('show');
  // 预加载 alpha maps（首次打开时）
  preloadRwmAlphaMaps();
}
function closeRemoveWmModal() {
  document.getElementById('removeWmPanel').classList.remove('show');
}

// 设置水印类型
function setRwmType(type) {
  rwmState.type = type;
  document.getElementById('rwmTypeGemini').classList.toggle('active', type === 'gemini');
  document.getElementById('rwmTypeDoubao').classList.toggle('active', type === 'doubao');
}

// v27.2: 增益滑块处理
// 滑块值 0 = 自动检测；1-30 对应 0.1-3.0 的增益
function onRwmGainSlider() {
  var sliderVal = parseInt(document.getElementById('rwmGainSlider').value);
  var gain = sliderVal / 10;  // 0 → 0.0 (auto), 1 → 0.1, ..., 30 → 3.0
  rwmState.manualGain = gain;
  document.getElementById('rwmGainVal').textContent = gain.toFixed(1);
  var hint = document.getElementById('rwmGainHint');
  if (gain === 0) {
    hint.textContent = '自动检测（推荐）';
    hint.style.color = 'var(--text-muted)';
  } else {
    hint.textContent = '手动: ' + gain.toFixed(1) + 'x';
    hint.style.color = 'var(--accent)';
  }
}

// 预加载 alpha maps
async function preloadRwmAlphaMaps() {
  var keys = ['gemini_48', 'gemini_96', 'doubao'];
  for (var k of keys) {
    if (rwmState.alphaMaps[k]) continue;
    try {
      rwmState.alphaMaps[k] = await loadAlphaMap(RWM_ALPHA_MAPS[k]);
    } catch (e) {
      console.warn('Failed to load alpha map ' + k + ':', e);
    }
  }
}

// 从 PNG data URL 加载 alpha map（返回 Float32Array，每个元素 = 像素的最大通道值/255）
function loadAlphaMap(dataUrl) {
  return new Promise(function(resolve, reject) {
    var img = new Image();
    img.onload = function() {
      var canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      var imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      var alphaMap = new Float32Array(canvas.width * canvas.height);
      for (var i = 0; i < alphaMap.length; i++) {
        var idx = i * 4;
        // 取 RGB 最大值作为 alpha（白色水印 + 黑色背景 = 亮度 = alpha）
        alphaMap[i] = Math.max(imgData.data[idx], imgData.data[idx + 1], imgData.data[idx + 2]) / 255.0;
      }
      resolve(alphaMap);
    };
    img.onerror = function() { reject(new Error('image load failed')); };
    img.src = dataUrl;
  });
}

// 处理文件选择
function handleRwmFiles(fileList) {
  var files = Array.from(fileList).filter(function(f) { return f.type.startsWith('image/'); });
  if (!files.length) {
    toast('请选择图片文件', 'info');
    return;
  }
  // 限制总数不超过 RWM_MAX_FILES
  var remaining = RWM_MAX_FILES - rwmState.files.length;
  if (remaining <= 0) {
    toast('已达到上限 ' + RWM_MAX_FILES + ' 张，请先处理或刷新页面', 'error');
    return;
  }
  if (files.length > remaining) {
    files = files.slice(0, remaining);
    toast('已添加 ' + remaining + ' 张（达到上限 ' + RWM_MAX_FILES + '），多余图片已忽略', 'info');
  } else {
    toast('已添加 ' + files.length + ' 张图片', 'success');
  }
  files.forEach(function(f) {
    rwmState.files.push({file: f, status: 'pending', name: f.name, blob: null, error: ''});
  });
  renderRwmFileList();
  document.getElementById('rwmProcessBtn').disabled = rwmState.files.length === 0;
}

// 渲染文件列表
function renderRwmFileList() {
  var container = document.getElementById('rwmFileListContainer');
  var list = document.getElementById('rwmFileList');
  if (!rwmState.files.length) {
    container.style.display = 'none';
    return;
  }
  container.style.display = 'block';
  list.innerHTML = rwmState.files.map(function(f, i) {
    var statusText = {pending: '待处理', processing: '处理中', done: '已完成', failed: '失败'}[f.status] || f.status;
    return '<div class="rwm-file-item">' +
      '<span class="rwm-file-name">' + escHtml(f.name) + '</span>' +
      '<span class="rwm-file-status ' + f.status + '">' + statusText + (f.error ? ': ' + escHtml(f.error.substring(0, 30)) : '') + '</span>' +
      '<button class="btn btn-xs btn-ghost" onclick="removeRwmFile(' + i + ')" title="移除">×</button>' +
      '</div>';
  }).join('');
}

// 移除单个文件
function removeRwmFile(idx) {
  rwmState.files.splice(idx, 1);
  renderRwmFileList();
  document.getElementById('rwmProcessBtn').disabled = rwmState.files.length === 0;
}

// 处理所有文件
async function processAllRwmFiles() {
  if (!rwmState.files.length) return;
  await preloadRwmAlphaMaps();
  var btn = document.getElementById('rwmProcessBtn');
  btn.disabled = true;
  btn.textContent = '处理中...';
  
  var okCount = 0, failCount = 0;
  for (var i = 0; i < rwmState.files.length; i++) {
    var f = rwmState.files[i];
    if (f.status === 'done') continue;  // 跳过已完成的
    f.status = 'processing';
    renderRwmFileList();
    try {
      var blob = await processOneRwmFile(f.file);
      f.blob = blob;
      f.status = 'done';
      okCount++;
      // 自动下载
      downloadRwmResult(f.file.name, blob);
    } catch (e) {
      f.status = 'failed';
      f.error = e.message;
      failCount++;
      console.warn('Remove watermark failed for ' + f.name + ':', e);
    }
    renderRwmFileList();
  }
  
  btn.disabled = false;
  btn.textContent = '开始去除水印';
  if (failCount === 0) {
    toast('全部完成：成功处理 ' + okCount + ' 张图片', 'success');
  } else {
    toast('完成：成功 ' + okCount + ' 张，失败 ' + failCount + ' 张', okCount > 0 ? 'success' : 'error');
  }
}

// 处理单张图片
async function processOneRwmFile(file) {
  // 1. 加载图片到 canvas
  var img = await loadImageFile(file);
  var canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  var ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);
  var imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  
  // 2. 计算水印位置
  var wmInfo = getRwmWatermarkInfo(canvas.width, canvas.height, rwmState.type);
  
  // 3. 获取对应的 alpha map
  var alphaMapKey = rwmState.type === 'gemini'
    ? (wmInfo.useLarge ? 'gemini_96' : 'gemini_48')
    : 'doubao';
  var alphaMap = rwmState.alphaMaps[alphaMapKey];
  if (!alphaMap) {
    throw new Error('alpha map not loaded: ' + alphaMapKey);
  }
  var alphaDims = rwmState.alphaMapDims[alphaMapKey];
  
  // v27.2: 自动检测 alpha 增益
  // 不同 Gemini 模型版本的水印 alpha 强度可能不同（实测 1.49x 差异）
  // 通过对比 alpha map 区域的星形像素亮度与背景亮度，自动估算实际增益
  var gain = rwmState.manualGain;  // 如果用户手动设置了增益，优先使用
  if (!gain || gain <= 0) {
    gain = autoDetectAlphaGain(imgData, alphaMap, alphaDims, wmInfo);
  }
  
  // 4. 应用反向 alpha 混合（带增益）
  removeWatermarkAlpha(imgData, alphaMap, alphaDims, wmInfo, gain);
  
  // 5. 写回 canvas 并导出 blob
  ctx.putImageData(imgData, 0, 0);
  
  // 6. 转 blob（保持原格式：PNG 用 PNG，其他用 JPEG 质量 0.95）
  return new Promise(function(resolve, reject) {
    var mime = (file.type === 'image/png') ? 'image/png' : 'image/jpeg';
    canvas.toBlob(function(blob) {
      if (blob) resolve(blob);
      else reject(new Error('toBlob failed'));
    }, mime, 0.95);
  });
}

// v27.2: 自动检测 alpha 增益
// 原理：水印公式 C_final = alpha * 255 + (1-alpha) * C_original
// 如果 alpha map 是正确的形状但强度不同（alpha_actual = alpha_map * gain），
// 我们可以通过采样水印区域的像素来估算 gain
// 方法：取 alpha map 中 alpha 较高的像素（星形中心），估算其 C_original，
// 然后与水印区域外的背景对比，找到使 C_original 最接近背景的 gain
function autoDetectAlphaGain(imgData, alphaMap, alphaDims, wmInfo) {
  var x = wmInfo.x, y = wmInfo.y, w = wmInfo.w, h = wmInfo.h;
  
  // 1. 收集水印区域内的像素：星形像素（alpha > 0.2）和背景像素（alpha < 0.01）
  var starBrightness = [];   // 星形像素亮度
  var bgBrightness = [];     // 水印区域内背景像素亮度
  
  for (var row = 0; row < h; row++) {
    for (var col = 0; col < w; col++) {
      var alphaCol = Math.floor(col * alphaDims.w / w);
      var alphaRow = Math.floor(row * alphaDims.h / h);
      var alphaIdx = alphaRow * alphaDims.w + alphaCol;
      var alpha = alphaMap[alphaIdx];
      
      var imgIdx = ((y + row) * imgData.width + (x + col)) * 4;
      var brightness = (imgData.data[imgIdx] + imgData.data[imgIdx + 1] + imgData.data[imgIdx + 2]) / 3;
      
      if (alpha > 0.2) {
        starBrightness.push(brightness);
      } else if (alpha < 0.01) {
        bgBrightness.push(brightness);
      }
    }
  }
  
  if (starBrightness.length < 10 || bgBrightness.length < 10) {
    return 1;  // 无法检测，返回默认增益
  }
  
  // 2. 计算背景平均亮度和星形平均亮度
  var bgMean = bgBrightness.reduce(function(a, b) { return a + b; }, 0) / bgBrightness.length;
  var starMean = starBrightness.reduce(function(a, b) { return a + b; }, 0) / starBrightness.length;
  
  // 3. 如果星形亮度低于背景（暗色水印），说明不是标准 Gemini 水印，返回默认
  if (starMean <= bgMean + 5) {
    return 1;
  }
  
  // 4. 计算所需增益
  // 水印公式：C_final = gain * alpha * 255 + (1 - gain * alpha) * C_original
  // 对于星形中心（alpha 接近最大值 alpha_max）：
  //   starMean = gain * alpha_max * 255 + (1 - gain * alpha_max) * bgMean
  //   → gain * alpha_max = (starMean - bgMean) / (255 - bgMean)
  //   → gain = (starMean - bgMean) / ((255 - bgMean) * alpha_max)
  
  // 取 alpha map 中前 10% 最高的 alpha 值的平均作为 alpha_max
  var sortedAlphas = [];
  for (var i = 0; i < alphaMap.length; i++) {
    if (alphaMap[i] > 0.2) sortedAlphas.push(alphaMap[i]);
  }
  sortedAlphas.sort(function(a, b) { return b - a; });
  var top10pct = sortedAlphas.slice(0, Math.floor(sortedAlphas.length * 0.1));
  var alphaMax = top10pct.reduce(function(a, b) { return a + b; }, 0) / top10pct.length;
  
  if (alphaMax < 0.01) return 1;
  
  var computedGain = (starMean - bgMean) / ((255 - bgMean) * alphaMax);
  
  // 5. 限制增益范围在 0.5-3.0 之间，避免极端值
  computedGain = Math.max(0.5, Math.min(3.0, computedGain));
  
  // 6. 如果增益接近 1.0，直接返回 1（避免不必要的调整）
  if (Math.abs(computedGain - 1.0) < 0.1) return 1;
  
  console.log('[rwm] auto-detected alpha gain: ' + computedGain.toFixed(2) + 
              ' (bg=' + bgMean.toFixed(1) + ', star=' + starMean.toFixed(1) + ', alphaMax=' + alphaMax.toFixed(3) + ')');
  return computedGain;
}

// 加载图片文件
function loadImageFile(file) {
  return new Promise(function(resolve, reject) {
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function() {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = function() {
      URL.revokeObjectURL(url);
      reject(new Error('image load failed'));
    };
    img.src = url;
  });
}

// 获取水印位置信息
function getRwmWatermarkInfo(width, height, type) {
  if (type === 'gemini') {
    // v27.1 修复：Gemini 的水印尺寸基于"任一维度 > 1024"判断，而非"两者都 > 1024"
    // 原因：实测 2752×763 的 16:9 裁剪图，Gemini 仍放置 96px 大水印（基于宽度）
    // 原代码 width > 1024 && height > 1024 会导致此类图误用 48px 小水印
    var isLarge = width > 1024 || height > 1024;
    var size = isLarge ? 96 : 48;
    var margin = isLarge ? 64 : 32;
    return {
      x: width - margin - size,
      y: height - margin - size,
      w: size,
      h: size,
      useLarge: isLarge
    };
  } else if (type === 'doubao') {
    // 豆包: 水印尺寸 120x20，右下角 margin 8px(right) / 5px(bottom)
    // 注：豆包水印尺寸在不同来源有差异，这里采用 zhengsuanfa/doubao-watermark-remover 的默认值
    var wmW = 120, wmH = 20;
    var rightMargin = 8, bottomMargin = 5;
    // 大图按比例放大（>1024 时 1.5x）
    if (width > 1024 || height > 1024) {
      var scale = Math.min(width / 1024, height > 1024 ? height / 1024 : 1);
      scale = Math.max(1, Math.min(scale, 2));  // 限制 1-2x
      wmW = Math.round(wmW * scale);
      wmH = Math.round(wmH * scale);
      rightMargin = Math.round(rightMargin * scale);
      bottomMargin = Math.round(bottomMargin * scale);
    }
    return {
      x: width - rightMargin - wmW,
      y: height - bottomMargin - wmH,
      w: wmW,
      h: wmH,
      useLarge: false
    };
  }
  return null;
}

// 核心算法：反向 alpha 混合（v27.2 增加 gain 参数）
// C_original = (C_watermarked - gain * alpha * 255) / (1 - gain * alpha)
// gain = 1 时为标准反向混合；gain > 1 时增强去除力度（适用于 alpha 更强的水印版本）
function removeWatermarkAlpha(imageData, alphaMap, alphaDims, wmInfo, gain) {
  if (!gain || gain <= 0) gain = 1;
  var x = wmInfo.x, y = wmInfo.y, w = wmInfo.w, h = wmInfo.h;
  // 边界检查
  if (x < 0 || y < 0 || x + w > imageData.width || y + h > imageData.height) {
    throw new Error('watermark region out of bounds: image=' + imageData.width + 'x' + imageData.height + ', wm=(' + x + ',' + y + ',' + w + ',' + h + ')');
  }
  
  for (var row = 0; row < h; row++) {
    for (var col = 0; col < w; col++) {
      var imgIdx = ((y + row) * imageData.width + (x + col)) * 4;
      
      // alpha map 采样（按比例缩放到目标尺寸）
      var alphaCol = Math.floor(col * alphaDims.w / w);
      var alphaRow = Math.floor(row * alphaDims.h / h);
      var alphaIdx = alphaRow * alphaDims.w + alphaCol;
      
      var alpha = alphaMap[alphaIdx] * gain;  // v27.2: 乘以增益
      if (alpha < RWM_ALPHA_THRESHOLD) continue;  // 透明区域跳过
      alpha = Math.min(alpha, RWM_MAX_ALPHA);
      
      // 对 RGB 三通道分别反向混合
      for (var c = 0; c < 3; c++) {
        var watermarked = imageData.data[imgIdx + c];
        var original = (watermarked - alpha * RWM_LOGO_VALUE) / (1.0 - alpha);
        imageData.data[imgIdx + c] = Math.max(0, Math.min(255, Math.round(original)));
      }
    }
  }
}

// 下载处理结果
function downloadRwmResult(originalName, blob) {
  // 文件名加 _nowm_yyyymmdd_hhmmss 后缀
  var dotIdx = originalName.lastIndexOf('.');
  var baseName = dotIdx > 0 ? originalName.substring(0, dotIdx) : originalName;
  var ext = dotIdx > 0 ? originalName.substring(dotIdx) : '';
  // 根据 blob 类型修正扩展名
  if (blob.type === 'image/png' && ext.toLowerCase() !== '.png') ext = '.png';
  else if (blob.type === 'image/jpeg' && ext.toLowerCase() !== '.jpg' && ext.toLowerCase() !== '.jpeg') ext = '.jpg';
  
  var d = new Date();
  var ts = d.getFullYear() + '' +
    String(d.getMonth() + 1).padStart(2, '0') +
    String(d.getDate()).padStart(2, '0') + '_' +
    String(d.getHours()).padStart(2, '0') +
    String(d.getMinutes()).padStart(2, '0') +
    String(d.getSeconds()).padStart(2, '0');
  
  var filename = baseName + '_nowm_' + ts + ext;
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
}

// kd-v2.1: 水印模块初始化（拖拽上传 + 点击面板背景关闭）
(function(){
  // Canvas drag for watermark positioning
  var canvas=document.getElementById('wmCanvas');
  if(canvas){
    function getCanvasCoords(e){var rect=canvas.getBoundingClientRect();var scaleX=canvas.width/rect.width;var scaleY=canvas.height/rect.height;var clientX,clientY;if(e.touches&&e.touches.length){clientX=e.touches[0].clientX;clientY=e.touches[0].clientY}else{clientX=e.clientX;clientY=e.clientY}return{x:(clientX-rect.left)*scaleX,y:(clientY-rect.top)*scaleY}}
    function isOnWatermark(cx,cy){if(!wmState.wmImg)return false;var wmW=canvas.width*(wmState.wmScale/100);var ratio=wmState.wmImg.naturalHeight/wmState.wmImg.naturalWidth;var wmH=wmW*ratio;var x=(wmState.wmX/100)*canvas.width-wmW/2;var y=(wmState.wmY/100)*canvas.height-wmH/2;return cx>=x&&cx<=x+wmW&&cy>=y&&cy<=y+wmH}
    var dragging=false,dragStartX=0,dragStartY=0,dragOrigX=0,dragOrigY=0;
    canvas.addEventListener('mousedown',function(e){var c=getCanvasCoords(e);if(isOnWatermark(c.x,c.y)){dragging=true;dragStartX=c.x;dragStartY=c.y;dragOrigX=wmState.wmX;dragOrigY=wmState.wmY;e.preventDefault();canvas.style.cursor='grabbing'}});
    canvas.addEventListener('mousemove',function(e){if(!dragging){var c=getCanvasCoords(e);canvas.style.cursor=isOnWatermark(c.x,c.y)?'grab':'default';return}e.preventDefault();var c=getCanvasCoords(e);wmState.wmX=Math.max(0,Math.min(100,dragOrigX+((c.x-dragStartX)/canvas.width)*100));wmState.wmY=Math.max(0,Math.min(100,dragOrigY+((c.y-dragStartY)/canvas.height)*100));updateWmSliders();drawWatermarkCanvas()});
    canvas.addEventListener('mouseup',function(){if(dragging){dragging=false;canvas.style.cursor='default'}});
    canvas.addEventListener('mouseleave',function(){if(dragging){dragging=false;canvas.style.cursor='default'}});
    canvas.addEventListener('touchstart',function(e){var c=getCanvasCoords(e);if(isOnWatermark(c.x,c.y)){dragging=true;dragStartX=c.x;dragStartY=c.y;dragOrigX=wmState.wmX;dragOrigY=wmState.wmY;e.preventDefault()}},{passive:false});
    canvas.addEventListener('touchmove',function(e){if(!dragging)return;e.preventDefault();var c=getCanvasCoords(e);wmState.wmX=Math.max(0,Math.min(100,dragOrigX+((c.x-dragStartX)/canvas.width)*100));wmState.wmY=Math.max(0,Math.min(100,dragOrigY+((c.y-dragStartY)/canvas.height)*100));updateWmSliders();drawWatermarkCanvas()},{passive:false});
    canvas.addEventListener('touchend',function(){dragging=false});
  }
  // Drag-drop for remove-watermark
  var dropZone=document.getElementById('rwmDropZone');
  if(dropZone){
    ['dragenter','dragover'].forEach(function(evt){dropZone.addEventListener(evt,function(e){e.preventDefault();e.stopPropagation();dropZone.classList.add('dragover')})});
    ['dragleave','drop'].forEach(function(evt){dropZone.addEventListener(evt,function(e){e.preventDefault();e.stopPropagation();dropZone.classList.remove('dragover')})});
    dropZone.addEventListener('drop',function(e){var files=e.dataTransfer.files;if(files&&files.length)handleRwmFiles(files)});
  }
  // Click-outside-to-close
  var rwm=document.getElementById('removeWmPanel');
  if(rwm)rwm.addEventListener('click',function(e){if(e.target===this)closeRemoveWmModal()});
  var wm=document.getElementById('watermarkPanel');
  if(wm)wm.addEventListener('click',function(e){if(e.target===this)closeWatermarkModal()});
})();

// ===== 工具 =====
function toast(msg,type){type=type||'info';const c=document.getElementById('toastContainer'),el=document.createElement('div');el.className='toast '+type;el.textContent=msg;c.appendChild(el);setTimeout(()=>{el.remove()},4000)}
function sleep(ms){return new Promise(r=>setTimeout(r,ms))}
document.getElementById('settingsModal').addEventListener('click',e=>{if(e.target.classList.contains('modal-backdrop'))closeSettingsModal()});
function toggleHelpPanel(){document.getElementById('helpPanel').classList.toggle('show')}
document.getElementById('helpPanel').addEventListener('click',function(e){if(e.target===this)toggleHelpPanel()});

// ===== 关闭窗口提示 =====
window.addEventListener('beforeunload',e=>{
  var msgs=[];
  var hasImgs=generationHistory.some(function(h){return h.status==='success'});
  if(hasImgs)msgs.push('1. 请保存已生成的图片（刷新后base64图片将丢失）');
  if((state.apiKeys&&state.apiKeys.length>0)||hasImgs)msgs.push('2. 如有需要，请导出 key 设置、生成历史记录、提示词库');
  if(msgs.length||activeSlots>0){
    e.preventDefault();
    var text='离开前请注意：\\n'+msgs.join('\\n');
    if(activeSlots>0)text+='\\n3. 当前有'+activeSlots+'个任务正在运行';
    e.returnValue=text;
    return e.returnValue;
  }
});

// ===== 新一天自动签到+注册 =====
// v24: 上游已下线签到功能，新一天仅触发自动注册（如有需要），并刷新已有账号额度
function checkNewDay(){const today=getTodayGMT8();if(state.lastAutoDay&&state.lastAutoDay!==today){toast('新的一天！正在重置 key 额度...','info');(async()=>{checkAndResetDailyUsage();initKeyPool();renderQuotaBadge();state.lastAutoDay=today;saveState();toast('新一天初始化完成','success')})()}if(!state.lastAutoDay){state.lastAutoDay=today;saveState()}}
setInterval(checkNewDay,60000);

// ===== 初始化 =====
// kd-v2.1: 加载设置 + 恢复历史 + 初始化 key 池 + 渲染额度徽章
loadSettingsUI();markInterruptedTasks();restoreLiveImages();checkNewDay();renderFullHistory();onModelChange();renderRefGrid();
ensureChannelReady();


// v0.3: populate version badge
(function(){var vb=document.getElementById('versionBadge');if(vb)vb.textContent=VERSION;})();
</script>
</body>
</html>`;


// ===================== Worker 后端 =====================
// kd-v2.0: 单一上游代理 —— 直接使用 UPSTREAM 常量，不再有 channel 选择
async function handleProxy(request, url) {
  // kd-v2.0: keydraw 上游同 /api/* 前缀，直接透传 pathname
  const upstreamPath = url.pathname;
  const upstreamUrl = UPSTREAM.base + (upstreamPath.startsWith('/') ? '' : '/') + upstreamPath;
  if (request.method === 'OPTIONS') { return new Response(null, { status: 204, headers: corsHeaders() }); }
  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');
  headers.set('Origin', UPSTREAM.origin);
  headers.set('Referer', UPSTREAM.origin + '/');
  headers.set('Accept', 'application/json, text/plain, */*');
  headers.set('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8');
  const userAgents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'];
  const ua = request.headers.get('User-Agent') || userAgents[Math.floor(Math.random() * userAgents.length)];
  headers.set('User-Agent', ua);
  const clientIP = request.headers.get('CF-Connecting-IP') || request.headers.get('X-Real-IP') || '';
  if (clientIP) { headers.set('X-Forwarded-For', clientIP); headers.set('X-Real-IP', clientIP); }
  // kd-v2.0: 单一 Bearer 鉴权 —— 前端通过 Authorization 发来，直接透传
  const authHdr = request.headers.get('Authorization') || request.headers.get(SESSION_HEADER);
  if(authHdr) headers.set('Authorization', authHdr.startsWith('Bearer ') ? authHdr : ('Bearer ' + authHdr));
  const opts = { method: request.method, headers, redirect: 'follow' };
  if (['POST', 'PUT', 'PATCH'].includes(request.method)) { try { const buf = await request.arrayBuffer(); if (buf.byteLength > 0) opts.body = buf; } catch (e) {} }
  try {
    const upResp = await fetch(upstreamUrl, opts);
    const respHeaders = new Headers(corsHeaders()); const ct = upResp.headers.get('Content-Type'); if (ct) respHeaders.set('Content-Type', ct);
    const body = await upResp.arrayBuffer();
    return new Response(body, { status: upResp.status, statusText: upResp.statusText, headers: respHeaders });
  } catch (err) { return new Response(JSON.stringify({ error: '代理请求失败: ' + err.message }), { status: 502, headers: { 'Content-Type': 'application/json', ...corsHeaders() } }); }
}
// kd-v2.0: corsHeaders 移除 X-Channel 头声明（不再需要）
function corsHeaders() { return { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, X-Session-Token, Authorization', 'Access-Control-Expose-Headers': 'X-Session-Token', 'Access-Control-Max-Age': '86400' }; }

async function handleRequest(request) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/image-proxy') || url.pathname.startsWith('/api/media-proxy')) {
      const imageUrl = url.searchParams.get('url'); if (!imageUrl) { return new Response('Missing url parameter', { status: 400, headers: corsHeaders() }); }
      try {
        const mediaHeaders = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept': 'image/*,video/*,*/*;q=0.8', 'Referer': UPSTREAM.origin + '/', 'Origin': UPSTREAM.origin };
        const st = request.headers.get(SESSION_HEADER) || url.searchParams.get('token') || '';
        if (st) mediaHeaders['Authorization'] = 'Bearer ' + st;
        const imgResp = await fetch(imageUrl, { headers: mediaHeaders, cf: { cacheEverything: true, cacheTtl: 86400, cacheTtlByStatus: { '200-299': 86400, '400-499': 60, '500-599': 0 } } });
        const contentType = imgResp.headers.get('Content-Type') || 'application/octet-stream'; const body = await imgResp.arrayBuffer();
        return new Response(body, { status: imgResp.status, headers: { 'Content-Type': contentType, 'Cache-Control': 'public, max-age=86400', 'Access-Control-Allow-Origin': '*', 'Access-Control-Expose-Headers': 'Content-Length' } });
      } catch (err) { return new Response('Image proxy failed: ' + err.message, { status: 502, headers: corsHeaders() }); }
    }
    // kd-v2.0: gift-key route —— 仅一个上游
    if (url.pathname === '/api/gift-key') {
      try {
        const r = await fetch(UPSTREAM.base + '/api/gift-key', {
          headers: { 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0', 'Referer': UPSTREAM.origin + '/' },
          cf: { cacheTtl: 60, cacheEverything: false }
        });
        const ct = r.headers.get('Content-Type') || 'application/json';
        const body = await r.arrayBuffer();
        return new Response(body, { status: r.status, headers: { 'Content-Type': ct, 'Cache-Control': 'no-store', ...corsHeaders() } });
      } catch (err) {
        return new Response(JSON.stringify({ key: UPSTREAM.giftKeyFallback }), { status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }
    if (url.pathname.startsWith('/api/')) { return handleProxy(request, url); }
    return new Response(HTML_CONTENT, { headers: { 'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'no-cache' } });
}
addEventListener('fetch', event => { event.respondWith(handleRequest(event.request)); });
