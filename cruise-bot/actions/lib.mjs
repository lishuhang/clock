// cruise-bot actions 共享库：RSS 抓取、GLM 调用、Worker /send
// 全部免费：RSS 公开源 + GLM-4-Flash（免费额度）+ Worker 内部 API

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

export function requiredEnv(names) {
  const missing = names.filter(n => !process.env[n]);
  if (missing.length) {
    console.error(`缺少 secrets：${missing.join(', ')}。请在仓库 Settings → Secrets and variables → Actions 配置。`);
    process.exit(1);
  }
}

export async function fetchT(url, opts = {}, timeoutMs = 20000) {
  return fetch(url, { ...opts, headers: { 'user-agent': UA, ...(opts.headers || {}) }, signal: AbortSignal.timeout(timeoutMs) });
}

// ---- RSS/XML 解析（无依赖，正则版） ----
export function parseRss(xml, limit = 8) {
  const items = [];
  const blocks = xml.match(/<(item|entry)[\s\S]*?<\/(item|entry)>/g) || [];
  for (const b of blocks.slice(0, limit)) {
    const title = (b.match(/<title[^>]*>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/) || [])[1] || '';
    const link = (b.match(/<link[^>]*href="([^"]+)"/) || b.match(/<link[^>]*>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/link>/) || [])[1] || '';
    const desc = (b.match(/<description[^>]*>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/description>/)
      || b.match(/<summary[^>]*>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/summary>/) || [])[1] || '';
    items.push({ title: title.trim(), link: (link || '').trim(), desc: desc.replace(/<[^>]+>/g, ' ').trim() });
  }
  return items;
}

// ---- GLM-4-Flash（免费） ----
export async function glm(env, prompt, system = null, opts = {}) {
  const base = (env.GLM_BASE || 'https://open.bigmodel.cn').replace(/\/$/, '');
  const model = env.GLM_MODEL || 'glm-4-flash';
  const messages = [];
  if (system) messages.push({ role: 'system', content: system });
  messages.push({ role: 'user', content: prompt });
  const r = await fetchT(`${base}/api/paas/v4/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${env.GLM_API_KEY}` },
    body: JSON.stringify({ model, messages, temperature: opts.temperature ?? 0.5, max_tokens: opts.max_tokens ?? 1600 }),
  }, 90000);
  if (!r.ok) throw new Error(`GLM HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  const out = j?.choices?.[0]?.message?.content;
  if (!out) throw new Error('GLM 空响应');
  return out.trim();
}

// ---- Worker 内部 API ----
export async function workerSend(workerUrl, agentKey, text, who = 'wife', channel = 'auto') {
  const r = await fetch(`${workerUrl.replace(/\/$/, '')}/send`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-agent-key': agentKey },
    body: JSON.stringify({ text, who, channel }),
  });
  const body = await r.text();
  console.log(`/send → HTTP ${r.status}: ${body.slice(0, 500)}`);
  if (!r.ok) throw new Error(`/send 失败 HTTP ${r.status}`);
  return JSON.parse(body);
}

export async function workerStateGet(workerUrl, agentKey, key) {
  const r = await fetch(`${workerUrl.replace(/\/$/, '')}/state?key=${encodeURIComponent(key)}`, {
    headers: { 'x-agent-key': agentKey },
  });
  if (!r.ok) return null;
  const j = await r.json();
  return j.value;
}

export async function workerStatePut(workerUrl, agentKey, key, value, ttl = null) {
  const r = await fetch(`${workerUrl.replace(/\/$/, '')}/state`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-agent-key': agentKey },
    body: JSON.stringify({ key, value, ttl }),
  });
  return r.ok;
}

// 订阅开关读取（cfg JSON 存在 KV 'cfg'）
export async function subscriptionOn(workerUrl, agentKey, field) {
  try {
    const raw = await workerStateGet(workerUrl, agentKey, 'cfg');
    if (!raw) return true;
    const cfg = JSON.parse(raw);
    return cfg[field] !== false;
  } catch { return true; }
}

// ---- 天气（open-meteo 免 key） ----
export async function weather(city) {
  const g = await (await fetchT(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=zh`)).json();
  const loc = g?.results?.[0];
  if (!loc) return '';
  const w = await (await fetchT(`https://api.open-meteo.com/v1/forecast?latitude=${loc.latitude}&longitude=${loc.longitude}` +
    '&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days=3&timezone=auto')).json();
  const W = { 0: '晴', 1: '多云', 2: '局部多云', 3: '阴', 45: '雾', 51: '毛毛雨', 61: '小雨', 63: '中雨', 65: '大雨', 71: '小雪', 73: '中雪', 80: '阵雨', 95: '雷雨' };
  const wc = c => W[c] || '·';
  const d = w.daily, cur = w.current;
  let s = `🌍 ${loc.name}（${loc.country || ''}）天气\n\n当前 ${cur.temperature_2m}°C 体感 ${cur.apparent_temperature}°C，${wc(cur.weather_code)}\n\n`;
  for (let i = 0; i < d.time.length; i++) {
    s += `${d.time[i].slice(5)}：${wc(d.weather_code[i])}，${d.temperature_2m_min[i]}~${d.temperature_2m_max[i]}°C，降水概率 ${d.precipitation_probability_max[i] ?? '-'}%\n`;
  }
  return s;
}

export function nowStr(offsetHours = 8) {
  const d = new Date(Date.now() + offsetHours * 3600 * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
}
