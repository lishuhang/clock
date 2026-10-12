
/* ============================================================
 * imgbd-worker — Cloudflare Worker (图床 v1.2)
 * GET  /          -> serve the single-file imagebed HTML (same origin)
 * GET  /api       -> machine-readable JSON API manifest (for AI agents)
 * GET  /llms.txt  -> plain-text API docs (for AI agents)
 * POST /upload    -> multi-channel image upload proxy
 *                    form fields: img (file) + channel (HX|JM|PP)
 * All channels are cookie-free from the caller's perspective:
 * login cookies live ONLY in Worker secrets, injected server-side.
 * Env secrets:
 *   HUXIU_COOKIE     - HX channel login cookie string
 *   JIEMIAN_COOKIE   - JM channel login cookie string
 *   THEPAPER_COOKIE  - PP channel login cookie string (incl. prod0-3)
 * ============================================================ */

const HUXIU_UPLOAD_URL = 'https://api-brief.huxiu.com/club/uploadImage';
const JIEMIAN_UPLOAD_URL = 'https://a.jiemian.com/index.php?m=writer&a=img_upload&dir=image';
const PPH_CREDS_URL = 'https://paiapi.thepaper.cn/open/html/media/upload/getCredentials?mediaType=IMAGE&source=pph';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0';

const HTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>图床</title>
<meta name="description" content="图床：上传图片，即刻获得永久 CDN 直链。支持点击/拖拽/粘贴与多张批量上传，并提供 HTTP API 供 AI Agent 直接调用（GET /api、GET /llms.txt）。">
<style>
  :root{
    --bg:#f7f7f8; --card:#ffffff; --text:#1c1e21; --muted:#8a8f98;
    --accent:#2b5fd9; --accent-soft:#eef2fd; --border:#e6e7eb;
    --ok:#0a7d43; --err:#c0392b; --radius:12px;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html{-webkit-text-size-adjust:100%}
  body{
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    background:var(--bg); color:var(--text); min-height:100vh; padding:32px 16px 64px;
  }
  .wrap{max-width:680px;margin:0 auto}
  header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:18px}
  h1{font-size:24px;font-weight:700;letter-spacing:.5px}
  h1 .ver{
    font-size:11.5px;font-weight:600;color:var(--accent);background:var(--accent-soft);
    border-radius:6px;padding:2px 8px;margin-left:8px;vertical-align:3px;letter-spacing:.3px;
  }
  .sub{color:var(--muted);font-size:13px;margin-top:6px;line-height:1.6}
  .sub b{color:var(--text);font-weight:600}
  .gear{
    border:1px solid var(--border);background:var(--card);color:var(--muted);
    width:34px;height:34px;border-radius:9px;cursor:pointer;font-size:16px;line-height:1;
    display:flex;align-items:center;justify-content:center;transition:.15s;flex:none;
  }
  .gear:hover{color:var(--accent);border-color:var(--accent)}
  .gear.on{color:var(--accent);border-color:var(--accent);background:var(--accent-soft)}

  #settings{
    display:none;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
    padding:14px 16px;margin-bottom:16px;font-size:13px;
  }
  #settings.open{display:block}
  #settings label{display:block;color:var(--muted);margin-bottom:8px}
  .setrow{display:flex;gap:8px}
  .setrow input{
    flex:1;border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:13px;
    font-family:inherit;outline:none;min-width:0;
  }
  .setrow input:focus{border-color:var(--accent)}
  .setrow button{
    border:none;background:var(--accent);color:#fff;border-radius:8px;padding:8px 14px;
    font-size:13px;cursor:pointer;font-family:inherit;flex:none;
  }
  .chlabel{font-size:12.5px;color:var(--muted);margin:0 2px 8px;line-height:1.7}
  .channels{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
  .ch{
    display:inline-flex;align-items:center;gap:7px;border:1px solid var(--border);background:var(--card);
    border-radius:10px;padding:8px 16px;cursor:pointer;font-size:13.5px;font-weight:600;
    font-family:inherit;transition:.13s;user-select:none;
  }
  .ch:hover{border-color:#c5c8cf}
  .ch input{margin:0;width:15px;height:15px;accent-color:var(--accent);flex:none}
  .ch.on{border-color:var(--accent);background:var(--accent-soft);color:var(--accent)}

  #chhint{display:none;font-size:12px;color:#9a6b00;background:#fff6e5;border-radius:8px;
    padding:8px 12px;margin-bottom:14px;line-height:1.6}
  #chhint.show{display:block}

  #drop{
    background:var(--card);border:2px dashed var(--border);border-radius:16px;
    padding:52px 20px;text-align:center;cursor:pointer;transition:.15s;user-select:none;
  }
  #drop:hover{border-color:#c9cad0}
  #drop.over{border-color:var(--accent);background:var(--accent-soft)}
  #drop .icon{font-size:34px;line-height:1;margin-bottom:14px;opacity:.9}
  #drop .t1{font-size:16px;font-weight:600}
  #drop .t1 em{font-style:normal;color:var(--accent)}
  #drop .t2{font-size:12.5px;color:var(--muted);margin-top:8px}
  kbd{
    background:#eceef1;border:1px solid #d6d9de;border-bottom-width:2px;border-radius:5px;
    padding:1px 6px;font-size:11px;font-family:inherit;
  }

  #stats{display:none;font-size:12.5px;color:var(--muted);margin:16px 2px 10px}
  #stats.show{display:block}

  .card{
    background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
    padding:14px;display:flex;gap:14px;margin-bottom:12px;align-items:flex-start;
    animation:fadein .25s ease;
  }
  @keyframes fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .thumb{
    width:76px;height:76px;border-radius:10px;background:var(--bg);flex:none;overflow:hidden;
    display:flex;align-items:center;justify-content:center;position:relative;
  }
  .thumb img{max-width:100%;max-height:100%;display:block}
  .body{flex:1;min-width:0}
  .name{
    font-size:12.5px;color:var(--muted);white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis;margin-bottom:8px;
  }
  .urlbox{display:flex;gap:8px;margin-bottom:10px}
  .urlbox input{
    flex:1;min-width:0;border:1px solid var(--border);border-radius:8px;background:var(--bg);
    padding:8px 10px;font-size:12.5px;color:var(--text);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
    outline:none;cursor:text;
  }
  .urlbox input:focus{border-color:var(--accent);background:#fff}
  .acts{display:flex;gap:8px;flex-wrap:wrap}
  .acts button{
    border:1px solid var(--border);background:#fff;color:var(--text);border-radius:8px;
    padding:5px 12px;font-size:12.5px;cursor:pointer;font-family:inherit;transition:.12s;
  }
  .acts button:hover{border-color:var(--accent);color:var(--accent)}
  .acts button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
  .acts button.primary:hover{background:#1f4cc0;color:#fff}
  .acts button.copied{background:var(--ok);border-color:var(--ok);color:#fff}
  .badge{font-size:11.5px;padding:3px 8px;border-radius:5px;font-weight:500}
  .badge.wait{background:#fff6e5;color:#9a6b00}
  .badge.fail{background:#fdecea;color:var(--err)}
  .spin{
    width:22px;height:22px;border:3px solid #ccd7f0;border-top-color:var(--accent);
    border-radius:50%;animation:rot .8s linear infinite;
  }
  @keyframes rot{to{transform:rotate(360deg)}}
  .errmsg{font-size:12.5px;color:var(--err);margin-top:4px;word-break:break-all}

  details.api{
    background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
    margin-top:26px;font-size:13px;
  }
  details.api summary{
    cursor:pointer;padding:13px 16px;font-weight:600;list-style:none;
    display:flex;align-items:center;gap:8px;user-select:none;
  }
  details.api summary::-webkit-details-marker{display:none}
  details.api summary .arr{transition:.15s;color:var(--muted);font-size:11px}
  details.api[open] summary .arr{transform:rotate(90deg)}
  details.api .api-body{padding:2px 16px 16px;color:var(--text);line-height:1.75}
  details.api h4{font-size:13px;margin:14px 0 6px}
  details.api p{color:var(--muted);font-size:12.5px}
  details.api pre{
    background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;
    font-size:11.5px;line-height:1.6;overflow-x:auto;margin:6px 0;
    font-family:ui-monospace,SFMono-Regular,Consolas,monospace;color:#2a2d33;
  }
  details.api table{border-collapse:collapse;width:100%;font-size:12px;margin:6px 0}
  details.api th,details.api td{border:1px solid var(--border);padding:6px 8px;text-align:left;vertical-align:top}
  details.api th{background:var(--bg);font-weight:600}
  details.api code{background:var(--bg);border-radius:4px;padding:1px 5px;font-size:11.5px;
    font-family:ui-monospace,SFMono-Regular,Consolas,monospace}

  footer{
    text-align:center;color:#b3b7be;font-size:11.5px;margin-top:30px;line-height:1.7;
  }
  @media (max-width:480px){
    body{padding:20px 10px 48px}
    #drop{padding:38px 14px}
    .thumb{width:60px;height:60px}
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>图床<span class="ver">v1.2</span></h1>
      <div class="sub">上传即得 <b>永久 CDN 直链</b></div>
    </div>
    <button class="gear" id="gear" title="接口端点设置">⚙</button>
  </header>

  <div id="settings">
    <label>上传代理端点（Cloudflare Worker 地址，留空使用默认）</label>
    <div class="setrow">
      <input id="apiInput" type="url" spellcheck="false">
      <button id="apiSave">保存</button>
    </div>
  </div>

  <div class="chlabel">选择上传渠道：HX（PNG/JPG）/ JM（PNG/JPG/GIF）/ PP</div>
  <div class="channels" id="channels">
    <label class="ch" data-ch="HX"><input type="radio" name="imgbd-ch" value="HX">HX</label>
    <label class="ch" data-ch="JM"><input type="radio" name="imgbd-ch" value="JM">JM</label>
    <label class="ch" data-ch="PP"><input type="radio" name="imgbd-ch" value="PP">PP</label>
  </div>
  <div id="chhint"></div>

  <div id="drop" title="点击选择图片">
    <div class="icon">🖼️</div>
    <div class="t1">点击选择 / 拖拽图片到此处 / 按 <em>Ctrl+V</em> 粘贴</div>
    <div class="t2" id="dropHint">支持 PNG · JPG（WebP/BMP 自动转 PNG），多张批量上传</div>
  </div>
  <input type="file" id="file" accept="image/*" multiple hidden>

  <div id="stats"></div>
  <div id="list"></div>

  <details class="api" id="apidoc">
    <summary><span class="arr">▶</span>API · AI Agent 调用说明</summary>
    <div class="api-body">
      <p>本站提供纯 HTTP 上传接口：AI Agent / 脚本<b>无需打开或操作本页面</b>，直接 POST 即可获取永久图片外链。无需登录、无需 Cookie、无 token。</p>
      <h4>接口定义</h4>
      <table>
        <tr><th>方法</th><td><code>POST /upload</code></td></tr>
        <tr><th>Content-Type</th><td><code>multipart/form-data</code></td></tr>
        <tr><th>字段 <code>img</code></th><td>图片文件（必需；亦接受 <code>file</code> / <code>upfile</code>）</td></tr>
        <tr><th>字段 <code>channel</code></th><td>可选渠道：<code>HX</code>（默认）/ <code>JM</code> / <code>PP</code></td></tr>
      </table>
      <h4>调用示例</h4>
      <pre>curl -F "img=@photo.png" -F "channel=PP" https://imgbd.lishuhang.com/upload

# Python
import requests
r = requests.post("https://imgbd.lishuhang.com/upload",
    files={"img": open("photo.png","rb")},
    data={"channel": "PP"})
print(r.json()["url"])   # -> 永久外链</pre>
      <h4>响应（JSON）</h4>
      <pre>{"result": 1, "msg": "文件上传成功", "url": "https://...", "channel": "PP"}
# 失败: {"result": 0, "msg": "原因..."}</pre>
      <h4>渠道差异</h4>
      <table>
        <tr><th>channel</th><th>支持格式</th><th>限制</th></tr>
        <tr><td><code>HX</code></td><td>PNG / JPG</td><td>≤10MB；网页 &lt;img&gt; 引用建议加 <code>referrerpolicy="no-referrer"</code></td></tr>
        <tr><td><code>JM</code></td><td>PNG / JPG / GIF</td><td>≤10MB；无防盗链；有频率限制（约 10 秒 1 张）</td></tr>
        <tr><td><code>PP</code></td><td>PNG / JPG / GIF / WebP / BMP</td><td>≤10MB；无防盗链</td></tr>
      </table>
      <p>机器可读接口清单：<code>GET /api</code>（JSON）· <code>GET /llms.txt</code>（纯文本）。Agent 可将其注册为图片上传 skill：输入本地图片文件，输出可公开访问的图片 URL。</p>
    </div>
  </details>

  <footer>仅供学习研究，请勿滥用</footer>
</div>

<script type="application/json" id="imgbd-api-manifest">
{
  "name": "图床",
  "version": "1.2",
  "description": "多渠道图片外链床。上传图片文件，返回可公开访问、无 token、长期有效的图片直链。支持 AI Agent / 程序通过 HTTP 直接调用，无需浏览器操作。",
  "skill_usage": "输入：本地图片文件（PNG/JPG/GIF/WebP/BMP）。输出：永久公开图片 URL。调用方式见 upload 字段。",
  "upload": {
    "method": "POST",
    "path": "/upload",
    "content_type": "multipart/form-data",
    "fields": {
      "img": "图片文件（file，必需；兼容 file / upfile 字段名）",
      "channel": "上传渠道（可选）：HX | JM | PP，默认 HX"
    }
  },
  "channels": {
    "HX": { "formats": ["png","jpg"], "max_mb": 10, "note": "网页 img 引用建议加 referrerpolicy=no-referrer" },
    "JM": { "formats": ["png","jpg","gif"], "max_mb": 10, "note": "无防盗链；有上传频率限制（约 10 秒 1 张）" },
    "PP": { "formats": ["png","jpg","gif","webp","bmp"], "max_mb": 10, "note": "无防盗链，链接无有效期" }
  },
  "response": {
    "success": { "result": 1, "msg": "文件上传成功", "url": "https://...", "channel": "PP" },
    "failure": { "result": 0, "msg": "失败原因" }
  },
  "machine_readable": ["GET /api", "GET /llms.txt"],
  "examples": {
    "curl": "curl -F img=@a.png -F channel=PP https://imgbd.lishuhang.com/upload"
  }
}
</script>

<script>
(function(){
  'use strict';

  /* ---------- 端点解析 ---------- */
  // 默认代理端点（Cloudflare Worker，已部署）：GitHub Pages / 自定义域 / 本地打开时经此代理上传。
  // 页面本身部署在 Worker 上时自动改用同域相对路径，此值不生效。
  var DEFAULT_API = '';

  function currentApi(){
    try{
      // 1) 页面本身部署在 Worker 上（workers.dev 或 Worker 自定义域）→ 同域相对路径
      if(location.protocol === 'https:' && /(\\.workers\\.dev|imgbd\\.lishuhang\\.com)$/.test(location.hostname)){
        return '';
      }
    }catch(e){}
    // 2) 用户自定义
    var saved = null;
    try{ saved = localStorage.getItem('imgbd-api'); }catch(e){}
    if(saved) return saved.replace(/\\/+$/,'');
    // 3) 内置默认（GitHub Pages / 任意静态托管 / 本地打开都走已部署的 Worker 代理）
    return (DEFAULT_API || '').replace(/\\/+$/,'');
  }

  function uploadEndpoint(){ var b = currentApi(); return (b ? b + '/upload' : '/upload'); }

  /* ---------- 渠道 ---------- */
  var CHANNELS = ['HX','JM','PP'];
  var channel = 'HX';
  try{
    var savedCh = localStorage.getItem('imgbd-channel');
    var LEGACY_CH = {huxiu:'HX', jiemian:'JM', thepaper:'PP'};  // 旧版渠道名迁移
    if(savedCh && LEGACY_CH[savedCh]) savedCh = LEGACY_CH[savedCh];
    if(CHANNELS.indexOf(savedCh) > -1) channel = savedCh;
  }catch(e){}

  var chEls = document.querySelectorAll('.ch');
  var chhint = document.getElementById('chhint');
  var dropHint = document.getElementById('dropHint');

  var CH_META = {
    HX: { hint: '', drop: '支持 PNG · JPG（WebP/BMP 自动转 PNG），多张批量上传' },
    JM: { hint: '⏳ JM 渠道有上传频率限制：批量上传将自动按 12 秒间隔排队，请耐心等待', drop: '支持 PNG · JPG · GIF（WebP/BMP 自动转 PNG），多张批量上传' },
    PP: { hint: '', drop: '支持 PNG · JPG · GIF · WebP · BMP，原样直传，多张批量上传' }
  };

  function setChannel(ch){
    channel = ch;
    try{ localStorage.setItem('imgbd-channel', ch); }catch(e){}
    for(var i = 0; i < chEls.length; i++){
      var on = chEls[i].getAttribute('data-ch') === ch;
      chEls[i].classList.toggle('on', on);
      var radio = chEls[i].querySelector('input[type=radio]');
      if(radio) radio.checked = on;
    }
    var m = CH_META[ch];
    chhint.textContent = m.hint;
    chhint.classList.toggle('show', !!m.hint);
    dropHint.textContent = m.drop;
  }
  for(var i = 0; i < chEls.length; i++){
    (function(el){
      el.addEventListener('click', function(){ setChannel(el.getAttribute('data-ch')); });
    })(chEls[i]);
  }
  setChannel(channel);

  /* ---------- DOM ---------- */
  var drop = document.getElementById('drop');
  var fileInput = document.getElementById('file');
  var list = document.getElementById('list');
  var stats = document.getElementById('stats');
  var gear = document.getElementById('gear');
  var settings = document.getElementById('settings');
  var apiInput = document.getElementById('apiInput');
  var apiSave = document.getElementById('apiSave');

  var doneCount = 0, failCount = 0;

  gear.addEventListener('click', function(){
    settings.classList.toggle('open');
    gear.classList.toggle('on');
    if(settings.classList.contains('open')){
      var saved = null;
      try{ saved = localStorage.getItem('imgbd-api'); }catch(e){}
      apiInput.value = saved || '';
    }
  });
  apiSave.addEventListener('click', function(){
    var v = apiInput.value.trim().replace(/\\/+$/,'');
    try{
      if(v){ localStorage.setItem('imgbd-api', v); }
      else{ localStorage.removeItem('imgbd-api'); }
    }catch(e){}
    apiSave.textContent = '已保存';
    setTimeout(function(){ apiSave.textContent = '保存'; }, 1200);
  });

  /* ---------- 选择 / 拖拽 / 粘贴 ---------- */
  drop.addEventListener('click', function(){ fileInput.click(); });
  fileInput.addEventListener('change', function(){
    handleFiles(fileInput.files);
    fileInput.value = '';
  });

  ['dragenter','dragover'].forEach(function(ev){
    document.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.add('over'); });
  });
  ['dragleave','drop'].forEach(function(ev){
    document.addEventListener(ev, function(e){
      e.preventDefault();
      if(ev === 'dragleave' && e.relatedTarget && e.relatedTarget !== drop) return;
      drop.classList.remove('over');
    });
  });
  document.addEventListener('drop', function(e){
    if(e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length){
      handleFiles(e.dataTransfer.files);
    }
  });

  document.addEventListener('paste', function(e){
    if(!e.clipboardData) return;
    var items = e.clipboardData.items || [];
    var files = [];
    for(var i = 0; i < items.length; i++){
      if(items[i].kind === 'file' && items[i].type.indexOf('image/') === 0){
        var f = items[i].getAsFile();
        if(f) files.push(f);
      }
    }
    if(files.length){ e.preventDefault(); handleFiles(files); }
  });

  /* ---------- 上传流程 ---------- */
  function handleFiles(files){
    for(var i = 0; i < files.length; i++){ prepareAndUpload(files[i]); }
  }

  function isImage(f){
    return f && (f.type ? f.type.indexOf('image/') === 0 : /\\.(png|jpe?g|gif|bmp|webp)$/i.test(f.name || ''));
  }

  // 各渠道支持的直传格式：
  //  HX  仅 PNG / JPEG（GIF 不支持，WebP/BMP 转 PNG）
  //  JM  PNG / JPEG / GIF（WebP/BMP 转 PNG）
  //  PP  全部直传（服务端无格式校验）
  function prepareAndUpload(file){
    if(!isImage(file)){
      addCard({name: file.name || '剪贴板图片', fail: '不是图片文件（' + (file.type || '未知类型') + '）'});
      return;
    }
    if(file.size > 10 * 1024 * 1024){
      addCard({name: file.name, fail: '图片超过 10MB，请压缩后再试'});
      return;
    }
    var t = file.type || '';
    if(channel === 'HX' && t === 'image/gif'){
      addCard({name: file.name, fail: 'HX 渠道不支持 GIF 动图，请切换到 JM / PP 渠道，或转存为 PNG / JPG'});
      return;
    }
    if(t === 'image/png' || t === 'image/jpeg' || t === 'image/gif' || /\\.(png|jpe?g|gif)$/i.test(file.name || '')){
      dispatch(file);
      return;
    }
    if(channel === 'PP' && (t === 'image/webp' || t === 'image/bmp' || /\\.(webp|bmp)$/i.test(file.name || ''))){
      dispatch(file);  // PP 渠道服务端无格式校验，原样直传
      return;
    }
    // 其余格式（webp/bmp 等）→ canvas 转 PNG
    convertToPng(file).then(dispatch, function(){
      addCard({name: file.name, fail: '该格式无法转换，请另存为 PNG / JPG 后重试'});
    });
  }

  function convertToPng(file){
    return new Promise(function(resolve, reject){
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function(){
        try{
          var c = document.createElement('canvas');
          c.width = img.naturalWidth || img.width;
          c.height = img.naturalHeight || img.height;
          c.getContext('2d').drawImage(img, 0, 0);
          var done = false;
          c.toBlob(function(blob){
            URL.revokeObjectURL(url);
            if(blob && !done){ done = true; resolve(new File([blob], (file.name || 'image').replace(/\\.[^.]+$/, '') + '.png', {type: 'image/png'})); }
            else if(!done){ done = true; reject(); }
          }, 'image/png');
        }catch(e){ URL.revokeObjectURL(url); reject(); }
      };
      img.onerror = function(){ URL.revokeObjectURL(url); reject(); };
      img.src = url;
    });
  }

  // JM 渠道：服务端限频，前端串行排队，间隔 12 秒
  var jmQueue = Promise.resolve();
  var jmLastAt = 0;
  var JM_GAP = 12000;
  function dispatch(file){
    if(channel === 'JM'){
      var run = function(){
        var wait = Math.max(0, jmLastAt + JM_GAP - Date.now());
        return sleep(wait).then(function(){ return uploadOne(file); });
      };
      jmQueue = jmQueue.then(run, run);
      jmQueue = jmQueue.then(function(){ jmLastAt = Date.now(); return null; }, function(){ jmLastAt = Date.now(); return null; });
    }else{
      uploadOne(file);
    }
  }
  function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

  function uploadOne(file){
    var previewUrl = URL.createObjectURL(file);
    var card = addCard({name: file.name || ('剪贴板_' + Date.now() + '.png'), waiting: true, preview: previewUrl, ch: channel});

    var fd = new FormData();
    fd.append('img', file, file.name || ('clipboard_' + Date.now() + '.png'));
    fd.append('channel', channel);

    fetch(uploadEndpoint(), { method: 'POST', body: fd })
      .then(function(res){
        return res.text().then(function(txt){
          var data = null;
          try{ data = JSON.parse(txt); }catch(e){}
          if(!res.ok && !data){ throw new Error('HTTP ' + res.status); }
          return data || {};
        });
      })
      .then(function(data){
        if(data && data.result === 1 && data.url){
          succeed(card, data.url, data);
        }else{
          throw new Error((data && data.msg) || '上传失败');
        }
      })
      .catch(function(err){
        fail(card, '上传失败：' + err.message + '（端点不可达或代理失效，可在 ⚙ 中检查）');
      });
  }

  /* ---------- 卡片渲染 ---------- */
  function el(tag, cls, text){
    var e = document.createElement(tag);
    if(cls) e.className = cls;
    if(text != null) e.textContent = text;
    return e;
  }

  function addCard(opt){
    var card = el('div', 'card');

    var thumb = el('div', 'thumb');
    if(opt.preview){
      var img = el('img');
      img.src = opt.preview;
      img.alt = '';
      thumb.appendChild(img);
    }else if(opt.waiting){
      thumb.appendChild(el('div', 'spin'));
    }else{
      thumb.appendChild(el('span', 'badge fail', '!'));
    }
    card.appendChild(thumb);

    var body = el('div', 'body');
    var nameTxt = opt.name + (opt.ch ? '  ·  ' + opt.ch : '');
    body.appendChild(el('div', 'name', nameTxt));

    if(opt.fail){
      body.appendChild(el('div', 'errmsg', opt.fail));
      card.appendChild(body);
      list.insertBefore(card, list.firstChild);
      failCount++; updateStats();
      return card;
    }

    if(opt.waiting){
      body.appendChild(el('div', 'badge wait', '上传中…'));
      card.appendChild(body);
      list.insertBefore(card, list.firstChild);
      return card;
    }
    card.appendChild(body);
    list.insertBefore(card, list.firstChild);
    return card;
  }

  function succeed(card, url, data){
    var body = card.querySelector('.body');
    body.innerHTML = '';

    var chName = {HX:'HX', JM:'JM', PP:'PP', huxiu:'HX', jiemian:'JM', thepaper:'PP'}[(data && data.channel) || channel] || '';
    var name = el('div', 'name', (data && data.width ? data.width + '×' + data.height + ' · ' : '') + fileNameOf(url) + (chName ? '  ·  ' + chName : ''));
    body.appendChild(name);

    var urlbox = el('div', 'urlbox');
    var input = el('input');
    input.readOnly = true;
    input.value = url;
    input.title = url;
    input.addEventListener('click', function(){ input.select(); });
    urlbox.appendChild(input);
    body.appendChild(urlbox);

    var isHx = (data && data.channel) ? String(data.channel).toLowerCase() === 'hx' : channel === 'HX';

    var acts = el('div', 'acts');

    var btnCopy = el('button', 'primary', '复制链接');
    btnCopy.addEventListener('click', function(){ copyText(url, btnCopy); });
    acts.appendChild(btnCopy);

    var btnMd = el('button', null, 'Markdown');
    btnMd.addEventListener('click', function(){ copyText('![' + fileNameOf(url) + '](' + url + ')', btnMd); });
    acts.appendChild(btnMd);

    var btnHtml = el('button', null, 'HTML');
    btnHtml.addEventListener('click', function(){
      copyText('<img src="' + url + '"' + (isHx ? ' referrerpolicy="no-referrer"' : '') + ' alt="">', btnHtml);
    });
    acts.appendChild(btnHtml);

    var btnOpen = el('button', null, '打开');
    btnOpen.addEventListener('click', function(){ window.open(url, '_blank'); });
    acts.appendChild(btnOpen);

    body.appendChild(acts);
    card.classList.add('ok');
    doneCount++; updateStats();
  }

  function fail(card, msg){
    var body = card.querySelector('.body');
    body.innerHTML = '';
    body.appendChild(el('div', 'name', '上传失败'));
    body.appendChild(el('div', 'errmsg', msg));
    var thumb = card.querySelector('.thumb');
    thumb.innerHTML = '';
    thumb.appendChild(el('span', 'badge fail', '!'));
    failCount++; updateStats();
  }

  function fileNameOf(url){
    var m = String(url).split('/').pop() || 'image';
    return decodeURIComponent(m);
  }

  function updateStats(){
    stats.classList.add('show');
    stats.textContent = '本次会话：成功 ' + doneCount + ' 张' + (failCount ? (' · 失败 ' + failCount + ' 张') : '');
  }

  /* ---------- 复制 ---------- */
  function copyText(text, btn){
    function mark(){
      var old = btn.textContent;
      btn.textContent = '已复制 ✓';
      btn.classList.add('copied');
      setTimeout(function(){ btn.textContent = old; btn.classList.remove('copied'); }, 1400);
    }
    function fallback(){
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try{ ok = document.execCommand('copy'); }catch(e){}
      ta.remove();
      if(ok){ mark(); }else{ window.prompt('请手动复制：', text); }
    }
    if(navigator.clipboard && window.isSecureContext){
      navigator.clipboard.writeText(text).then(mark, fallback);
    }else{
      fallback();
    }
  }
})();
</script>
</body>
</html>
`;

const CORS_HEADERS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, POST, OPTIONS',
  'access-control-allow-headers': '*',
  'access-control-max-age': '86400',
};

/* ============ 纯 JS MD5（澎湃 auth 需要，RFC 1321） ============ */
function md5Hex(str) {
  function rl(n, c) { return (n << c) | (n >>> (32 - c)); }
  function add(a, b) { return (((a >> 16) + (b >> 16)) + (((a & 0xffff) + (b & 0xffff)) >> 16) << 16) | ((((a & 0xffff) + (b & 0xffff)) & 0xffff)); }
  function cmn(q, a, b, x, s, t) { return add(rl(add(add(a, q), add(x, t)), s), b); }
  function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t); }
  function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t); }
  function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
  function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t); }
  var bytes = [];
  for (var i0 = 0; i0 < str.length; i0++) {
    var code = str.charCodeAt(i0);
    if (code < 0x80) bytes.push(code);
    else if (code < 0x800) { bytes.push(0xc0 | (code >> 6), 0x80 | (code & 63)); }
    else { bytes.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 63), 0x80 | (code & 63)); }
  }
  var n = bytes.length;
  var words = [];
  for (i0 = 0; i0 < n; i0++) words[i0 >> 2] = (words[i0 >> 2] || 0) | (bytes[i0] << ((i0 % 4) * 8));
  words[n >> 2] = (words[n >> 2] || 0) | (0x80 << ((n % 4) * 8));
  var total = (((n + 8) >> 6) + 1) * 16;
  for (i0 = 0; i0 < total; i0++) words[i0] = words[i0] || 0;
  words[total - 2] = n * 8;
  var a = 1732584193, b = -271733879, c = -1732584194, d = 271733878;
  for (i0 = 0; i0 < words.length; i0 += 16) {
    var oa = a, ob = b, oc = c, od = d;
    a=ff(a,b,c,d,words[i0],7,-680876936); d=ff(d,a,b,c,words[i0+1],12,-389564586); c=ff(c,d,a,b,words[i0+2],17,606105819); b=ff(b,c,d,a,words[i0+3],22,-1044525330);
    a=ff(a,b,c,d,words[i0+4],7,-176418897); d=ff(d,a,b,c,words[i0+5],12,1200080426); c=ff(c,d,a,b,words[i0+6],17,-1473231341); b=ff(b,c,d,a,words[i0+7],22,-45705983);
    a=ff(a,b,c,d,words[i0+8],7,1770035416); d=ff(d,a,b,c,words[i0+9],12,-1958414417); c=ff(c,d,a,b,words[i0+10],17,-42063); b=ff(b,c,d,a,words[i0+11],22,-1990404162);
    a=ff(a,b,c,d,words[i0+12],7,1804603682); d=ff(d,a,b,c,words[i0+13],12,-40341101); c=ff(c,d,a,b,words[i0+14],17,-1502002290); b=ff(b,c,d,a,words[i0+15],22,1236535329);
    a=gg(a,b,c,d,words[i0+1],5,-165796510); d=gg(d,a,b,c,words[i0+6],9,-1069501632); c=gg(c,d,a,b,words[i0+11],14,643717713); b=gg(b,c,d,a,words[i0],20,-373897302);
    a=gg(a,b,c,d,words[i0+5],5,-701558691); d=gg(d,a,b,c,words[i0+10],9,38016083); c=gg(c,d,a,b,words[i0+15],14,-660478335); b=gg(b,c,d,a,words[i0+4],20,-405537848);
    a=gg(a,b,c,d,words[i0+9],5,568446438); d=gg(d,a,b,c,words[i0+14],9,-1019803690); c=gg(c,d,a,b,words[i0+3],14,-187363961); b=gg(b,c,d,a,words[i0+8],20,1163531501);
    a=gg(a,b,c,d,words[i0+13],5,-1444681467); d=gg(d,a,b,c,words[i0+2],9,-51403784); c=gg(c,d,a,b,words[i0+7],14,1735328473); b=gg(b,c,d,a,words[i0+12],20,-1926607734);
    a=hh(a,b,c,d,words[i0+5],4,-378558); d=hh(d,a,b,c,words[i0+8],11,-2022574463); c=hh(c,d,a,b,words[i0+11],16,1839030562); b=hh(b,c,d,a,words[i0+14],23,-35309556);
    a=hh(a,b,c,d,words[i0+1],4,-1530992060); d=hh(d,a,b,c,words[i0+4],11,1272893353); c=hh(c,d,a,b,words[i0+7],16,-155497632); b=hh(b,c,d,a,words[i0+10],23,-1094730640);
    a=hh(a,b,c,d,words[i0+13],4,681279174); d=hh(d,a,b,c,words[i0],11,-358537222); c=hh(c,d,a,b,words[i0+3],16,-722521979); b=hh(b,c,d,a,words[i0+6],23,76029189);
    a=hh(a,b,c,d,words[i0+9],4,-640364487); d=hh(d,a,b,c,words[i0+12],11,-421815835); c=hh(c,d,a,b,words[i0+15],16,530742520); b=hh(b,c,d,a,words[i0+2],23,-995338651);
    a=ii(a,b,c,d,words[i0],6,-198630844); d=ii(d,a,b,c,words[i0+7],10,1126891415); c=ii(c,d,a,b,words[i0+14],15,-1416354905); b=ii(b,c,d,a,words[i0+5],21,-57434055);
    a=ii(a,b,c,d,words[i0+12],6,1700485571); d=ii(d,a,b,c,words[i0+3],10,-1894986606); c=ii(c,d,a,b,words[i0+10],15,-1051523); b=ii(b,c,d,a,words[i0+1],21,-2054922799);
    a=ii(a,b,c,d,words[i0+8],6,1873313359); d=ii(d,a,b,c,words[i0+15],10,-30611744); c=ii(c,d,a,b,words[i0+6],15,-1560198380); b=ii(b,c,d,a,words[i0+13],21,1309151649);
    a=ii(a,b,c,d,words[i0+4],6,-145523070); d=ii(d,a,b,c,words[i0+11],10,-1120210379); c=ii(c,d,a,b,words[i0+2],15,718787259); b=ii(b,c,d,a,words[i0+9],21,-343485551);
    a = add(a, oa); b = add(b, ob); c = add(c, oc); d = add(d, od);
  }
  function hex(x) {
    var s = '', t;
    for (var i1 = 0; i1 < 4; i1++) { t = (x >>> (i1 * 8)) & 255; s += (t < 16 ? '0' : '') + t.toString(16); }
    return s;
  }
  return hex(a) + hex(b) + hex(c) + hex(d);
}

/* ============ 纯 JS DES-ECB 解密（澎湃 prod0-3 cookie 需要，FIPS 46-3） ============ */
var PC1 = [57,49,41,33,25,17,9,1,58,50,42,34,26,18,10,2,59,51,43,35,27,19,11,3,60,52,44,36,63,55,47,39,31,23,15,7,62,54,46,38,30,22,14,6,61,53,45,37,29,21,13,5,28,20,12,4];
var PC2 = [14,17,11,24,1,5,3,28,15,6,21,10,23,19,12,4,26,8,16,7,27,20,13,2,41,52,31,37,47,55,30,40,51,45,33,48,44,49,39,56,34,53,46,42,50,36,29,32];
var SHIFTS = [1,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1];
var IP = [58,50,42,34,26,18,10,2,60,52,44,36,28,20,12,4,62,54,46,38,30,22,14,6,64,56,48,40,32,24,16,8,57,49,41,33,25,17,9,1,59,51,43,35,27,19,11,3,61,53,45,37,29,21,13,5,63,55,47,39,31,23,15,7];
var FP = [40,8,48,16,56,24,64,32,39,7,47,15,55,23,63,31,38,6,46,14,54,22,62,30,37,5,45,13,53,21,61,29,36,4,44,12,52,20,60,28,35,3,43,11,51,19,59,27,34,2,42,10,50,18,58,26,33,1,41,9,49,17,57,25];
var E = [32,1,2,3,4,5,4,5,6,7,8,9,8,9,10,11,12,13,12,13,14,15,16,17,16,17,18,19,20,21,20,21,22,23,24,25,24,25,26,27,28,29,28,29,30,31,32,1];
var PP = [16,7,20,21,29,12,28,17,1,15,23,26,5,18,31,10,2,8,24,14,32,27,3,9,19,13,30,6,22,11,4,25];
var SBOX = [
[14,4,13,1,2,15,11,8,3,10,6,12,5,9,0,7,0,15,7,4,14,2,13,1,10,6,12,11,9,5,3,8,4,1,14,8,13,6,2,11,15,12,9,7,3,10,5,0,15,12,8,2,4,9,1,7,5,11,3,14,10,0,6,13],
[15,1,8,14,6,11,3,4,9,7,2,13,12,0,5,10,3,13,4,7,15,2,8,14,12,0,1,10,6,9,11,5,0,14,7,11,10,4,13,1,5,8,12,6,9,3,2,15,13,8,10,1,3,15,4,2,11,6,7,12,0,5,14,9],
[10,0,9,14,6,3,15,5,1,13,12,7,11,4,2,8,13,7,0,9,3,4,6,10,2,8,5,14,12,11,15,1,13,6,4,9,8,15,3,0,11,1,2,12,5,10,14,7,1,10,13,0,6,9,8,7,4,15,14,3,11,5,2,12],
[7,13,14,3,0,6,9,10,1,2,8,5,11,12,4,15,13,8,11,5,6,15,0,3,4,7,2,12,1,10,14,9,10,6,9,0,12,11,7,13,15,1,3,14,5,2,8,4,3,15,0,6,10,1,13,8,9,4,5,11,12,7,2,14],
[2,12,4,1,7,10,11,6,8,5,3,15,13,0,14,9,14,11,2,12,4,7,13,1,5,0,15,10,3,9,8,6,4,2,1,11,10,13,7,8,15,9,12,5,6,3,0,14,11,8,12,7,1,14,2,13,6,15,0,9,10,4,5,3],
[12,1,10,15,9,2,6,8,0,13,3,4,14,7,5,11,10,15,4,2,7,12,9,5,6,1,13,14,0,11,3,8,9,14,15,5,2,8,12,3,7,0,4,10,1,13,11,6,4,3,2,12,9,5,15,10,11,14,1,7,6,0,8,13],
[4,11,2,14,15,0,8,13,3,12,9,7,5,10,6,1,13,0,11,7,4,9,1,10,14,3,5,12,2,15,8,6,1,4,11,13,12,3,7,14,10,15,6,8,0,5,9,2,6,11,13,8,1,4,10,7,9,5,0,15,14,2,3,12],
[13,2,8,4,6,15,11,1,10,9,3,14,5,0,12,7,1,15,13,8,10,3,7,4,12,5,6,11,0,14,9,2,7,11,4,1,9,12,14,2,0,6,10,13,15,3,5,8,2,1,14,7,4,10,8,13,15,12,9,0,3,5,6,11]
];
function getBit(bytes, pos) { return (bytes[pos >> 3] >> (7 - (pos & 7))) & 1; }
function setBit(bits, pos, val) { bits[pos >> 3] |= val << (7 - (pos & 7)); }
function desDecryptBlock(blockBytes, subKeys) {
  var i, j;
  var ipBits = [];
  for (i = 0; i < 64; i++) ipBits[i] = getBit(blockBytes, IP[i] - 1);
  var L = ipBits.slice(0, 32), R = ipBits.slice(32, 64);
  for (var round = 15; round >= 0; round--) {
    var eBits = [];
    for (i = 0; i < 48; i++) eBits[i] = R[E[i] - 1];
    var xorBits = [];
    var sk = subKeys[round];
    for (i = 0; i < 48; i++) xorBits[i] = eBits[i] ^ sk[i];
    var sOut = [];
    for (i = 0; i < 8; i++) {
      var row = (xorBits[i * 6] << 1) | xorBits[i * 6 + 5];
      var col = (xorBits[i * 6 + 1] << 3) | (xorBits[i * 6 + 2] << 2) | (xorBits[i * 6 + 3] << 1) | xorBits[i * 6 + 4];
      var v = SBOX[i][row * 16 + col];
      for (j = 0; j < 4; j++) sOut[i * 4 + j] = (v >> (3 - j)) & 1;
    }
    var f = [];
    for (i = 0; i < 32; i++) f[i] = sOut[PP[i] - 1];
    var newR = [];
    for (i = 0; i < 32; i++) newR[i] = L[i] ^ f[i];
    L = R; R = newR;
  }
  var preOut = R.concat(L);
  var out = new Array(8).fill(0);
  for (i = 0; i < 64; i++) setBit(out, i, preOut[FP[i] - 1]);
  return out;
}
function makeSubKeys(keyBytes) {
  var i, r;
  var k = [];
  for (i = 0; i < 56; i++) k[i] = getBit(keyBytes, PC1[i] - 1);
  var subKeys = [];
  var C = k.slice(0, 28), D = k.slice(28, 56);
  for (r = 0; r < 16; r++) {
    for (i = 0; i < SHIFTS[r]; i++) { C.push(C.shift()); D.push(D.shift()); }
    var cd = C.concat(D);
    var sk = [];
    for (i = 0; i < 48; i++) sk[i] = cd[PC2[i] - 1];
    subKeys.push(sk);
  }
  return subKeys;
}
function desEcbDecrypt(keyStr, data) {
  var keyBytes = [];
  for (var i = 0; i < 8; i++) keyBytes.push(keyStr.charCodeAt(i) & 255);
  var subKeys = makeSubKeys(keyBytes);
  var out = [];
  for (var off = 0; off + 8 <= data.length; off += 8) {
    var dec = desDecryptBlock(Array.prototype.slice.call(data, off, off + 8), subKeys);
    for (var j = 0; j < 8; j++) out.push(dec[j]);
  }
  var pad = out[out.length - 1];
  if (pad > 0 && pad <= 8) out = out.slice(0, out.length - pad);
  return out;
}
function utf8Of(byteArr) {
  var s = '';
  for (var i = 0; i < byteArr.length; i++) s += String.fromCharCode(byteArr[i]);
  try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
}

/* ============ 工具 ============ */
function jsonResponse(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: Object.assign({ 'content-type': 'application/json; charset=utf-8' }, CORS_HEADERS),
  });
}

function pickChannel(inFd, url) {
  // 渠道名规范化：HX / JM / PP（兼容旧名 huxiu / jiemian / thepaper / pph 等别名，大小写不敏感）
  const raw = (inFd.get('channel') || url.searchParams.get('channel') || url.searchParams.get('c') || 'HX')
    .toString().trim().toLowerCase();
  const map = {
    hx: 'HX', huxiu: 'HX',
    jm: 'JM', jiemian: 'JM',
    pp: 'PP', pph: 'PP', paper: 'PP', pengpai: 'PP', thepaper: 'PP',
  };
  return map[raw] || 'HX';
}

function getInputFile(inFd) {
  const f = inFd.get('img') || inFd.get('file') || inFd.get('upfile');
  if (f && typeof f !== 'string') return f;
  return null;
}

/* ============ 渠道 1：HX ============ */
async function uploadHuxiu(file, env) {
  const out = new FormData();
  const name = file.name || ('clipboard_' + Date.now() + '.png');
  out.append('image', file, name);
  out.append('platform', 'www');

  const cookie = (env.HUXIU_COOKIE || '').trim();
  // IMPORTANT: huxiu WAF blocks any POST carrying Origin/Referer headers.
  // Verified minimal passing header set = User-Agent + Cookie (+ Accept).
  const headers = {
    'user-agent': UA,
    'accept': 'application/json, text/javascript, */*; q=0.01',
  };
  if (cookie) headers['cookie'] = cookie;

  let resp, text;
  try {
    resp = await fetch(HUXIU_UPLOAD_URL, { method: 'POST', headers: headers, body: out });
    text = await resp.text();
  } catch (e) {
    return { result: 0, msg: '代理请求失败: ' + (e && e.message || String(e)) };
  }

  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    const blocked = /405|blocked|阻断/.test(text);
    return {
      result: 0,
      msg: (blocked ? '上游 WAF 拦截（请求过频或特征异常），请稍后重试。' : '上游返回异常: ') + text.slice(0, 140),
    };
  }

  if (data && data.success === true && data.data && data.data.image_url) {
    return {
      result: 1,
      msg: '文件上传成功',
      url: data.data.image_url,
      width: data.data.width || 0,
      height: data.data.height || 0,
    };
  }

  const msgMap = {
    '此操作需要登录': '代理登录态（HX 渠道）已过期，请重新导出对应站点 cookies 并更新 Worker Secret',
    'platform类型不正确': '上游参数异常',
    '只允许上传jpg、jpeg、png格式的文件': 'HX 渠道仅支持 PNG / JPG（JPEG），GIF、BMP、WebP 请先转存为 PNG 或切换其他渠道',
  };
  const raw = data && (data.message || data.msg);
  if (raw && msgMap[raw]) data.msg = msgMap[raw];
  else if (data && !data.msg && data.message) data.msg = data.message;
  data = data || {};
  if (data.result === undefined) data.result = 0;
  return data;
}

/* ============ 渠道 2：JM ============ */
async function uploadJiemian(file, env) {
  const out = new FormData();
  const name = file.name || ('clipboard_' + Date.now() + '.png');
  out.append('imgFile', file, name);

  const cookie = (env.JIEMIAN_COOKIE || '').trim();
  const headers = {
    'user-agent': UA,
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'x-requested-with': 'XMLHttpRequest',
    'referer': 'https://a.jiemian.com/index.php?m=writer&a=submission',
    'origin': 'https://a.jiemian.com',
  };
  if (cookie) headers['cookie'] = cookie;

  let resp, text;
  try {
    resp = await fetch(JIEMIAN_UPLOAD_URL, { method: 'POST', headers: headers, body: out });
    text = await resp.text();
  } catch (e) {
    return { result: 0, msg: '代理请求失败: ' + (e && e.message || String(e)) };
  }

  // 未登录时上游 302/直接输出登录页 HTML
  if (/^\s*</.test(text)) {
    return { result: 0, msg: '代理登录态（JM 渠道）已过期或无效，请重新导出对应站点 cookies 并更新 Worker Secret' };
  }

  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    return { result: 0, msg: '上游返回异常(HTTP ' + resp.status + '): ' + text.slice(0, 140) };
  }

  if (data && data.error === 0 && data.url) {
    return { result: 1, msg: '文件上传成功', url: data.url };
  }
  const raw = (data && (data.message || data.msg)) || ('error=' + (data && data.error));
  let msg = String(raw);
  if (/太频繁/.test(msg)) msg = 'JM 渠道上传频率受限：服务端限约 10 秒 1 张，请稍等约 1 分钟后重试';
  else if (msg === 'error=1') msg = 'JM 渠道上传失败（可能为格式或频率限制）';
  return { result: 0, msg: msg };
}

/* ============ 渠道 3：PP（STS + OSS 直传） ============ */
let pphSts = null; // { creds, bucket, region, imagePrefix, expireAt }

function cookieValue(cookieStr, name) {
  const m = new RegExp('(?:^|;\\s*)' + name + '=([^;]*)').exec(cookieStr || '');
  return m ? m[1] : null;
}

function pphUidToken(env) {
  const ck = (env.THEPAPER_COOKIE || '').trim();
  const p1 = cookieValue(ck, 'prod1');
  const p3 = cookieValue(ck, 'prod3');
  if (!p1 || !p3) return null;
  try {
    // prod1/prod3: DES-ECB(key="_whiteli") -> "random6-value" -> substr(7)
    const uid = utf8Of(desEcbDecrypt('_whiteli', b64ToBytes(decodeURIComponent(p1)))).substring(7);
    const token = utf8Of(desEcbDecrypt('_whiteli', b64ToBytes(decodeURIComponent(p3)))).substring(7);
    if (!uid || !token) return null;
    return { uid, token };
  } catch (e) {
    return null;
  }
}

function b64ToBytes(b64) {
  const bin = atob(b64);
  const out = [];
  for (let i = 0; i < bin.length; i++) out.push(bin.charCodeAt(i) & 255);
  return out;
}

async function getPphSts(env) {
  if (pphSts && Date.now() < pphSts.expireAt - 120000) return pphSts;
  const ut = pphUidToken(env);
  if (!ut) throw new Error('PP 渠道登录态缺失或已过期（cookie 需含完整加密字段），请重新导出并更新 Worker Secret');
  // 上游凭证接口偶发 520/非 JSON 响应：最多尝试 2 次
  let data = null;
  for (let attempt = 0; attempt < 2 && !data; attempt++) {
    const ts = Date.now();
    const auth = md5Hex(ut.uid + ut.token + ts).toUpperCase();
    const headers = {
      'user-agent': UA,
      'accept': 'application/json, text/plain, */*',
      'content-type': 'application/json',
      'clientname': 'THEPAPERWWW',
      'randomid': ut.uid,
      'timestamp': String(ts),
      'authorization': auth,
      'origin': 'https://pph.thepaper.cn',
      'referer': 'https://pph.thepaper.cn/',
      'cookie': (env.THEPAPER_COOKIE || '').trim(),
    };
    let text = '';
    try {
      const resp = await fetch(PPH_CREDS_URL, { method: 'POST', headers: headers, body: '{}' });
      text = await resp.text();
      data = JSON.parse(text);
    } catch (e) {
      data = null;
    }
    if (!data && attempt === 0) await new Promise(r => setTimeout(r, 800));
  }
  if (!data || data.code !== 200 || !data.data || !data.data.credentials) {
    throw new Error('PP 渠道凭证获取失败: ' + ((data && (data.desc || data.code)) || '上游暂不可用，请稍后重试'));
  }
  const d = data.data;
  pphSts = {
    creds: d.credentials,
    bucket: d.bucket,
    region: d.region,           // e.g. oss-cn-shanghai
    imagePrefix: d.imagePrefix, // e.g. newpai/image/
    expireAt: Date.parse(d.credentials.expiration),
  };
  return pphSts;
}

async function hmacSha1B64(keyStr, msg) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(keyStr), { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  let bin = '';
  const bytes = new Uint8Array(sig);
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function randomStr6() {
  const chars = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz12345678';
  let s = '';
  for (let i = 0; i < 6; i++) s += chars.charAt(Math.floor(Math.random() * chars.length));
  return s;
}

async function uploadThepaper(file, env) {
  let sts;
  try {
    sts = await getPphSts(env);
  } catch (e) {
    return { result: 0, msg: e && e.message ? e.message : String(e) };
  }

  const extFromName = (file.name || '').split('.').pop();
  const ext = (extFromName && /^[a-zA-Z0-9]{1,5}$/.test(extFromName)) ? extFromName.toLowerCase() : 'png';
  const ctype = file.type || ('image/' + (ext === 'jpg' ? 'jpeg' : ext));
  const lastMod = file.lastModified || Date.now();
  const key = sts.imagePrefix + lastMod + '_' + randomStr6() + '_' + Date.now() + '.' + ext;

  const host = sts.bucket + '.' + sts.region + '.aliyuncs.com';
  const date = new Date().toUTCString();
  const stsTok = sts.creds.securityToken;
  const stringToSign = 'PUT\n\n' + ctype + '\n' + date + '\nx-oss-security-token:' + stsTok + '\n/' + sts.bucket + '/' + key;
  let sig;
  try {
    sig = await hmacSha1B64(sts.creds.accessKeySecret, stringToSign);
  } catch (e) {
    return { result: 0, msg: 'OSS 签名失败: ' + (e && e.message || String(e)) };
  }

  let resp;
  try {
    resp = await fetch('https://' + host + '/' + key, {
      method: 'PUT',
      headers: {
        'date': date,
        'content-type': ctype,
        'x-oss-security-token': stsTok,
        'authorization': 'OSS ' + sts.creds.accessKeyId + ':' + sig,
      },
      body: file,
    });
  } catch (e) {
    return { result: 0, msg: 'OSS 上传请求失败: ' + (e && e.message || String(e)) };
  }
  if (resp.status !== 200) {
    const t = await resp.text();
    return { result: 0, msg: 'OSS 上传失败(HTTP ' + resp.status + '): ' + t.slice(0, 160) };
  }

  // 编辑器官方行为即引用该 OSS 原始直链（无 token、无防盗链、无有效期）
  return { result: 1, msg: '文件上传成功', url: 'https://' + host + '/' + key };
}

/* ============ 路由 ============ */
async function handleUpload(request, env) {
  let inFd;
  try {
    inFd = await request.formData();
  } catch (e) {
    return jsonResponse({ result: 0, msg: '请求体不是有效的 multipart 表单' }, 400);
  }

  const url = new URL(request.url);
  const channel = pickChannel(inFd, url);
  const file = getInputFile(inFd);
  if (!file) {
    return jsonResponse({ result: 0, msg: '未收到图片文件（需要 multipart 字段 img）' }, 400);
  }
  if (file.size > 10 * 1024 * 1024) {
    return jsonResponse({ result: 0, msg: '图片超过 10MB 上限' }, 400);
  }

  let out;
  if (channel === 'JM') out = await uploadJiemian(file, env);
  else if (channel === 'PP') out = await uploadThepaper(file, env);
  else out = await uploadHuxiu(file, env);

  out.channel = channel;
  if (out.result === 1) return jsonResponse(out);
  return jsonResponse(out, out.msg && /端点|代理请求失败/.test(out.msg) ? 502 : 200);
}

const API_MANIFEST = {
  name: '图床',
  version: '1.2',
  description: '多渠道图片外链床：上传图片文件，返回可公开访问、无 token、长期有效的图片直链。供 AI Agent / 程序通过 HTTP 直接调用，无需浏览器操作、无需登录、无需 Cookie。',
  skill_usage: '作为 image-upload skill 使用 —— 输入：本地图片文件（PNG/JPG/GIF/WebP/BMP，≤10MB）；输出：永久公开的图片 URL。无 token 有效期、无防盗链（JM/PP 渠道）。',
  upload: {
    method: 'POST',
    path: '/upload',
    content_type: 'multipart/form-data',
    fields: {
      img: '图片文件（file，必需；兼容字段名 file / upfile）',
      channel: '上传渠道（可选）：HX（默认）| JM | PP（大小写不敏感，兼容旧名 huxiu/jiemian/thepaper）',
    },
  },
  channels: {
    HX: { formats: ['png', 'jpg'], max_mb: 10, note: '网页 img 引用建议加 referrerpolicy=no-referrer' },
    JM: { formats: ['png', 'jpg', 'gif'], max_mb: 10, note: '无防盗链；有上传频率限制（约 10 秒 1 张）' },
    PP: { formats: ['png', 'jpg', 'gif', 'webp', 'bmp'], max_mb: 10, note: '无防盗链，链接无有效期' },
  },
  response: {
    success: { result: 1, msg: '文件上传成功', url: 'https://...', channel: 'PP' },
    failure: { result: 0, msg: '失败原因' },
  },
  examples: {
    curl: 'curl -F "img=@photo.png" -F "channel=PP" https://imgbd.lishuhang.com/upload',
    python: 'import requests\nr = requests.post("https://imgbd.lishuhang.com/upload", files={"img": open("photo.png","rb")}, data={"channel":"PP"})\nurl = r.json()["url"]',
  },
  machine_readable: ['GET /api', 'GET /llms.txt'],
};

const LLMS_TXT = `# 图床 (imgbd)

> 多渠道图片外链床：上传图片，返回永久公开直链。AI Agent 可直接通过 HTTP 调用，
> 无需打开网页、无需登录、无需 Cookie。可作为 image-upload skill 使用。

## 上传接口

- Method: POST /upload
- Content-Type: multipart/form-data
- Fields:
  - img (file, 必需): 图片文件, PNG/JPG/GIF/WebP/BMP, ≤10MB (兼容字段名 file / upfile)
  - channel (string, 可选): HX | JM | PP, 默认 HX (大小写不敏感, 兼容旧名 huxiu/jiemian/thepaper)

## 响应 (JSON)

成功: {"result":1,"msg":"文件上传成功","url":"https://...","channel":"PP"}
失败: {"result":0,"msg":"失败原因"}

## 渠道说明

| channel | 支持格式                     | 说明                                    |
|---------|------------------------------|-----------------------------------------|
| HX      | PNG / JPG                    | 网页 img 引用建议加 referrerpolicy=no-referrer |
| JM      | PNG / JPG / GIF              | 无防盗链; 有频率限制(约10秒1张)           |
| PP      | PNG / JPG / GIF / WebP / BMP | 无防盗链, 链接无有效期                    |

## 调用示例

curl -F "img=@photo.png" -F "channel=PP" https://imgbd.lishuhang.com/upload

import requests
r = requests.post(
    "https://imgbd.lishuhang.com/upload",
    files={"img": open("photo.png", "rb")},
    data={"channel": "PP"},
)
print(r.json()["url"])

## 机器可读接口清单

- GET /api  -> 本说明的 JSON 版本
- GET /llms.txt -> 本文件
`;

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }
    const url = new URL(request.url);
    if (url.pathname === '/upload') {
      if (request.method !== 'POST') {
        return jsonResponse({ result: 0, msg: '仅支持 POST' }, 405);
      }
      return handleUpload(request, env);
    }
    if (request.method === 'GET') {
      if (url.pathname === '/api') {
        return new Response(JSON.stringify(API_MANIFEST, null, 2), {
          status: 200,
          headers: Object.assign({ 'content-type': 'application/json; charset=utf-8' }, CORS_HEADERS),
        });
      }
      if (url.pathname === '/llms.txt') {
        return new Response(LLMS_TXT, {
          status: 200,
          headers: Object.assign({ 'content-type': 'text/plain; charset=utf-8' }, CORS_HEADERS),
        });
      }
      if (url.pathname === '/') {
        return new Response(HTML, {
          status: 200,
          headers: Object.assign({
            'content-type': 'text/html; charset=utf-8',
            'cache-control': 'public, max-age=300',
          }, CORS_HEADERS),
        });
      }
    }
    return jsonResponse({ result: 0, msg: 'Not Found' }, 404);
  },
};
