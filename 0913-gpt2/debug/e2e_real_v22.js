#!/usr/bin/env node
// v2.2 真实上游 E2E：vm 加载 worker，fetch 用 Node 真网络——完整走
// /api/zimage/generate → task 轮询 → /zimage/img 代理，验证真实上游契约。
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'gpt2-worker-kmage-v2.2.js'), 'utf8');

class H {
  constructor(init) { this.m = new Map(); if (init) { if (init instanceof H) init.m.forEach((v, k) => this.m.set(k, v)); else for (const [k, v] of Object.entries(init)) this.m.set(k.toLowerCase(), v); } }
  get(k) { return this.m.get(String(k).toLowerCase()) || null; }
  set(k, v) { this.m.set(String(k).toLowerCase(), String(v)); }
  append(k, v) { const o = this.m.get(String(k).toLowerCase()); this.m.set(String(k).toLowerCase(), o ? o + ', ' + v : String(v)); }
  has(k) { return this.m.has(String(k).toLowerCase()); }
}
class Rsp {
  constructor(body, init) { this.status = (init && init.status) || 200; this.headers = new H(init && init.headers); this._body = body || ''; }
  get ok() { return this.status >= 200 && this.status < 300; }
  async text() { return typeof this._body === 'string' ? this._body : new TextDecoder().decode(this._body); }
  async json() { return JSON.parse(await this.text()); }
  async arrayBuffer() { return typeof this._body === 'string' ? new TextEncoder().encode(this._body).buffer : this._body; }
}
class Req {
  constructor(url, init) { this.url = url; this.method = (init && init.method) || 'GET'; this.headers = new H(init && init.headers); this._body = (init && init.body) || ''; }
  async json() { return JSON.parse(this._body); }
  async arrayBuffer() { return new TextEncoder().encode(this._body).buffer; }
}

let fetchListener = null;
const ctx = {
  addEventListener: (t, fn) => { if (t === 'fetch') fetchListener = fn; },
  fetch: (url, init) => fetch(url, init), // Node 18+ 真网络 fetch
  Request: Req, Response: Rsp, Headers: H, URL, TextEncoder, TextDecoder, console,
  crypto: global.crypto, setTimeout, clearTimeout, setInterval, clearInterval,
  atob: (s) => Buffer.from(s, 'base64').toString('binary'), btoa: (s) => Buffer.from(s, 'binary').toString('base64'),
};
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'worker-v2.2.js' });

async function fire(p, opts) {
  const req = new Req('https://ai-image.test' + p, opts);
  let pr = null;
  const ev = { request: req, respondWith: (x) => { pr = x; } };
  fetchListener(ev);
  return await pr;
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  console.log('[1] 提交 /api/zimage/generate（turbo 512x512）…');
  let r = await fire('/api/zimage/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: 'a corgi running on a sunny beach, golden hour, photorealistic', width: 512, height: 512, modelType: 'turbo', batchSize: 1 }) });
  let j = await r.json();
  console.log('    HTTP', r.status, 'success:', j.success, 'uuid:', j.data && j.data.uuid, 'seed:', j.data && j.data.task && j.data.task.seed);
  if (r.status !== 200 || !j.success) { console.log('    提交失败:', JSON.stringify(j).slice(0, 200)); process.exit(1); }
  const uuid = j.data.uuid;

  let resultUrl = '';
  for (let i = 0; i < 50; i++) {
    await sleep(3000);
    r = await fire('/api/zimage/task/' + uuid);
    j = await r.json();
    const tk = j.data && j.data.task;
    const st = tk && tk.taskStatus;
    process.stdout.write('    poll#' + i + ' ' + (st || r.status) + (tk && tk.progress ? ' ' + tk.progress + '%' : '') + '\r');
    if (st === 'completed') { resultUrl = tk.resultUrl; break; }
    if (st === 'failed') { console.log('\n    上游失败:', tk.errorMessage); process.exit(1); }
  }
  console.log('\n[2] 轮询 completed，resultUrl:', resultUrl);
  if (!resultUrl) { console.log('    超时未完成'); process.exit(1); }

  console.log('[3] /zimage/img 代理拉取结果图…');
  r = await fire('/zimage/img?url=' + encodeURIComponent(resultUrl));
  const buf = await r.arrayBuffer();
  const head = Buffer.from(buf.slice(0, 16));
  console.log('    HTTP', r.status, 'bytes:', buf.byteLength, 'ct:', r.headers.get('Content-Type'), 'magic:', head.toString('hex').slice(0, 8), '(webp=52494646)');
  const ok = r.status === 200 && buf.byteLength > 5000;
  console.log(ok ? '\nE2E 真实上游全链通过 ✅' : '\nE2E 失败 ❌');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('E2E CRASH:', e); process.exit(1); });
