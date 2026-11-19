#!/usr/bin/env node
// v2.2 worker VM 冒烟测试：Node vm 沙箱加载 worker，模拟 zimage 上游，
// 端到端验证代理三端点 + 白名单预检 + 页面/自描述/健康检查。
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'gpt2-worker-kmage-v2.2.js'), 'utf8');

let pass = 0, fail = 0;
const check = (name, ok, extra) => {
  console.log((ok ? 'PASS' : 'FAIL') + '  ' + name + (extra ? '  :: ' + extra : ''));
  ok ? pass++ : fail++;
};

// ---- 最小 Request/Response/Headers 模拟 ----
class H {
  constructor(init) { this.m = new Map(); if (init) { if (init instanceof H) { init.m.forEach((v, k) => this.m.set(k, v)); } else { for (const [k, v] of Object.entries(init)) this.m.set(k.toLowerCase(), v); } } }
  get(k) { return this.m.get(String(k).toLowerCase()) || null; }
  set(k, v) { this.m.set(String(k).toLowerCase(), String(v)); }
  append(k, v) { const old = this.m.get(String(k).toLowerCase()); this.m.set(String(k).toLowerCase(), old ? old + ', ' + v : String(v)); }
  has(k) { return this.m.has(String(k).toLowerCase()); }
}
class Rsp {
  constructor(body, init) {
    this.status = (init && init.status) || 200;
    this.headers = new H(init && init.headers);
    this._body = body || '';
  }
  get ok() { return this.status >= 200 && this.status < 300; }
  async text() { return typeof this._body === 'string' ? this._body : new TextDecoder().decode(this._body); }
  async json() { return JSON.parse(await this.text()); }
  async arrayBuffer() { return typeof this._body === 'string' ? new TextEncoder().encode(this._body).buffer : this._body; }
}
class Req {
  constructor(url, init) {
    this.url = url; this.method = (init && init.method) || 'GET';
    this.headers = new H(init && init.headers);
    this._body = (init && init.body) || '';
  }
  async json() { return JSON.parse(this._body); }
  async arrayBuffer() { return new TextEncoder().encode(this._body).buffer; }
}

// ---- 上游模拟 ----
const upstreamCalls = [];
function mockFetch(url, init) {
  const u = new URL(url);
  upstreamCalls.push({ url, method: (init && init.method) || 'GET', headers: (init && init.headers) || {}, body: (init && init.body) || null });
  if (u.host === 'zimage.run') {
    if (u.pathname === '/api/z-image/generate') {
      return Promise.resolve(new Rsp(JSON.stringify({ success: true, data: { uuid: 'zk-smoke-001', task: { taskStatus: 'pending', seed: '777' } } }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    if (u.pathname === '/api/z-image/task/zk-smoke-001') {
      return Promise.resolve(new Rsp(JSON.stringify({ success: true, data: { task: { taskStatus: 'completed', resultUrl: 'https://files.zimage.run/images/z-image/generated/2026-11-19/zk/result-0-x.webp', seed: '777' } } }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    return Promise.resolve(new Rsp(JSON.stringify({ success: false, error: 'not found' }), { status: 404 }));
  }
  if (u.host === 'files.zimage.run') {
    return Promise.resolve(new Rsp('WEBPDATA-FAKE', { status: 200, headers: { 'Content-Type': 'image/webp' } }));
  }
  return Promise.resolve(new Rsp('{"error":"no route"}', { status: 404 }));
}

// ---- vm 加载 ----
let fetchListener = null;
const ctx = {
  addEventListener: (t, fn) => { if (t === 'fetch') fetchListener = fn; },
  fetch: mockFetch, Request: Req, Response: Rsp, Headers: H,
  URL, TextEncoder, TextDecoder, console,
  crypto: { getRandomValues: (a) => { for (let i = 0; i < a.length; i++) a[i] = Math.floor(Math.random() * 256); return a; }, randomUUID: () => 'x' },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'), btoa: (s) => Buffer.from(s, 'binary').toString('base64'),
  setTimeout, clearTimeout, setInterval, clearInterval, Date, JSON, Math, Object, Array, String, Number, Boolean, Promise, Error, Map, Set, RegExp, parseInt, parseFloat, isNaN, encodeURIComponent, decodeURIComponent, Uint8Array, ArrayBuffer, Blob: class { constructor(parts) { this._p = parts; } },
};
vm.createContext(ctx);
try {
  vm.runInContext(src, ctx, { filename: 'worker-v2.2.js' });
  check('vm 加载 worker 无异常', true);
} catch (e) {
  check('vm 加载 worker 无异常', false, e.message);
  process.exit(1);
}

async function fire(path, opts) {
  const req = new Req('https://ai-image.test' + path, opts);
  let respPromise = null;
  const ev = { request: req, respondWith: (p) => { respPromise = p; } };
  fetchListener(ev);
  return await respPromise;
}

(async () => {
  // 1) 首页
  let r = await fire('/');
  const html = await r.text();
  check('GET / 200 含 zimage 通道选项', r.status === 200 && html.includes('<option value="zimage">zimage</option>'));
  check('页面含 zimageHint 限额提示元素', html.includes('id="zimageHint"'));
  check('页面版本徽章 2.2', html.includes('kmage-kdr-rapi-zimage-2.2'));
  check('页面通知文案四通道', html.includes('四通道生效'));
  check('页面含 KMODELS_ZIMAGE（8 模型）', (html.match(/KMODELS_ZIMAGE/g) || []).length > 0 && html.includes('dark-beast') && html.includes('qwen-image-2-1'));
  check('页面含 zimageSizeFor 映射', html.includes('function zimageSizeFor'));
  check('页面含 RATIO_OPTIONS_ZIMAGE 裁剪', html.includes('RATIO_OPTIONS_ZIMAGE'));
  check('页面含 generateZimage 流程', html.includes('async function generateZimage'));
  check('页面 loadChannel 含 zimage（bug 修复）', /loadChannel[\s\S]{0,200}zimage/.test(html));
  check('页面下载前缀 zimage_', html.includes("'zimage_'"));

  // 2) /healthz
  r = await fire('/healthz');
  const hz = await r.json();
  check('/healthz channels 含 zimage', Array.isArray(hz.channels) && hz.channels.indexOf('zimage') >= 0);
  check('/healthz zimage_upstream', hz.zimage_upstream === 'https://zimage.run');

  // 3) /about
  r = await fire('/about');
  const ab = await r.json();
  check('/about channels.zimage 存在', !!(ab.channels && ab.channels.zimage));
  check('/about notes_v2_2 存在', !!ab.notes_v2_2);
  check('/about 名称四通道', /四通道/.test(ab.name));

  // 4) generate 合法请求透传上游
  upstreamCalls.length = 0;
  r = await fire('/api/zimage/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: 'a corgi', width: 512, height: 512, modelType: 'turbo', batchSize: 1 }) });
  let j = await r.json();
  check('generate 200 透传 uuid', r.status === 200 && j.data && j.data.uuid === 'zk-smoke-001');
  const g = upstreamCalls[0] || {};
  check('上游收到 POST /api/z-image/generate', g.url === 'https://zimage.run/api/z-image/generate' && g.method === 'POST');
  const gHeaders = g.headers instanceof H ? g.headers : new H(g.headers);
  check('上游请求 Origin 伪装 zimage.run', gHeaders.get('Origin') === 'https://zimage.run');
  check('上游请求 Referer /zh', gHeaders.get('Referer') === 'https://zimage.run/zh');
  const gBody = JSON.parse(g.body);
  check('上游 body batchSize 恒 1 + model 透传', gBody.batchSize === 1 && gBody.modelType === 'turbo');

  // 5) 非白名单模型 → 回退 turbo；batchSize>1 请求被强制 1（不透传原始值）
  upstreamCalls.length = 0;
  await fire('/api/zimage/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: 'x', width: 512, height: 512, modelType: 'EVIL-MODEL', batchSize: 99 }) });
  const gb2 = JSON.parse((upstreamCalls[0] || {}).body);
  check('非白名单模型回退 turbo', gb2.modelType === 'turbo');
  check('外部 batchSize=99 被强制为 1', gb2.batchSize === 1);

  // 6) 非白名单尺寸 → 400 预检（不打上游）
  upstreamCalls.length = 0;
  r = await fire('/api/zimage/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: 'x', width: 1280, height: 720, modelType: 'turbo', batchSize: 1 }) });
  j = await r.json();
  check('1280x720 预检 400', r.status === 400 && /512x512/.test(j.error));
  check('尺寸预检未打上游', upstreamCalls.length === 0);

  // 7) 空 prompt → 400
  r = await fire('/api/zimage/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: '   ', width: 512, height: 512, modelType: 'turbo' }) });
  check('空 prompt 400', r.status === 400);

  // 8) task 轮询透传 + uuid 白名单
  upstreamCalls.length = 0;
  r = await fire('/api/zimage/task/zk-smoke-001');
  j = await r.json();
  check('task 200 透传 completed', r.status === 200 && j.data.task.taskStatus === 'completed');
  check('task 请求打到上游', (upstreamCalls[0] || {}).url === 'https://zimage.run/api/z-image/task/zk-smoke-001');
  r = await fire('/api/zimage/task/..%2fevil');
  check('恶意 uuid 400 拒绝', r.status === 400);
  upstreamCalls.length = 0;
  r = await fire('/api/zimage/task/ok_uuid-123');
  check('合法 uuid（下划线连字符）透传上游', upstreamCalls.some(c => c.url === 'https://zimage.run/api/z-image/task/ok_uuid-123') && r.status === 404);

  // 9) 未知端点 → 404
  r = await fire('/api/zimage/other');
  check('未知 zimage 端点 404', r.status === 404);

  // 10) 结果图代理: 前缀放行 / 外域拒绝
  r = await fire('/zimage/img?url=' + encodeURIComponent('https://files.zimage.run/images/z-image/generated/2026-11-19/zk/result-0-x.webp'));
  const img = await r.text();
  check('/zimage/img 放行 files.zimage.run 并回传字节', r.status === 200 && img === 'WEBPDATA-FAKE' && /image\/webp/.test(r.headers.get('Content-Type')));
  r = await fire('/zimage/img?url=' + encodeURIComponent('https://evil.example.com/x.png'));
  check('/zimage/img 拒绝非 files 前缀', r.status === 400);

  // 11) seed 透传（可选参数）
  upstreamCalls.length = 0;
  await fire('/api/zimage/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: 'x', width: 768, height: 512, modelType: 'dark-beast', batchSize: 1, seed: '12345' }) });
  const gb3 = JSON.parse(upstreamCalls[0].body);
  check('seed 可选透传 + 768x512 放行 + dark-beast 白名单', gb3.seed === '12345' && gb3.width === 768 && gb3.modelType === 'dark-beast');

  console.log(fail ? `\n${fail} 项未通过（${pass} 项通过）` : `\n冒烟全部通过（${pass} 项）`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('SMOKE CRASH:', e); process.exit(1); });
