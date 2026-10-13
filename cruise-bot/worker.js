/**
 * cruise-bot — 邮轮五日文字内容 Bot（Cloudflare Worker）
 * =====================================================
 * 场景：用户夫人在邮轮上 5 天，不购互联网套餐时仅 WhatsApp / iMessage 可收发文字。
 * 本 Worker 是整个 bot 的中枢：
 *   1. WhatsApp Cloud API 官方 webhook（接收 + 回复，service 对话 24h 窗口内免费）
 *   2. iMessage 备通道：家里 Mac 跑 BlueBubbles + Cloudflare Tunnel（支持主动推送）
 *   3. 内容服务：早报/晚报/搜索/小红书特化/链接全文/维基/天气/热榜/公版书/连载/猜谜/翻译/聊天
 *   4. 智能发送路由 deliver()：WhatsApp 24h 窗口判定 → iMessage 兜底 → KV 待发队列
 *   5. /send + /state 内部 API：供 GitHub Actions 定时任务与人工调用（AGENT_KEY 保护）
 *
 * 凭据全部走环境变量/secret，本文件不含任何敏感值。
 *
 * 便利性定位（与 kmage-kdr 一致的原则）：
 *   工具为用户终端使用便利尽可能自动化完成全流程；用户打开并使用本工具即视为
 *   对后续自动化操作的合法授权（收到什么发什么、抓取哪些公开源、调用免费模型）。
 */

const VERSION = 'cruise-bot-1.0';

/* ============================ 通用小工具 ============================ */

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8' };
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

function jresp(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), { status, headers: JSON_HEADERS });
}
function tresp(text, status = 200) {
  return new Response(text, { status, headers: { 'content-type': 'text/plain; charset=utf-8' } });
}
function nowSec() { return Math.floor(Date.now() / 1000); }
function clampStr(s, n) { s = String(s == null ? '' : s); return s.length <= n ? s : s.slice(0, n - 1) + '…'; }
function digits(s) { return String(s || '').replace(/\D/g, ''); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchT(url, opts = {}, timeoutMs = 20000) {
  return fetch(url, {
    ...opts,
    headers: { 'user-agent': UA, ...(opts.headers || {}) },
    signal: AbortSignal.timeout(timeoutMs),
  });
}

async function hmacSha256Hex(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(message));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, '0')).join('');
}

/* ---------------------------- KV 封装 ---------------------------- */

async function kvGet(env, key, fallback = null) {
  try { const v = await env.CKV.get(key); return v === null ? fallback : v; } catch { return fallback; }
}
async function kvGetJson(env, key, fallback = null) {
  const v = await kvGet(env, key);
  if (v === null) return fallback;
  try { return JSON.parse(v); } catch { return fallback; }
}
async function kvPut(env, key, value, ttlSec = null) {
  try { await env.CKV.put(key, String(value), ttlSec ? { expirationTtl: Math.max(60, ttlSec) } : {}); } catch {}
}
async function kvPutJson(env, key, obj, ttlSec = null) { return kvPut(env, key, JSON.stringify(obj), ttlSec); }
async function kvDel(env, key) { try { await env.CKV.delete(key); } catch {} }

/* ============================ 配置与身份 ============================ */

function whoAmI(env, address) {
  // 返回 'owner' | 'wife' | null（其他号码一律不服务，防滥用防费 token）
  const d = digits(address);
  if (!d) return null;
  if (env.OWNER_WA && digits(env.OWNER_WA).endsWith(d.slice(-9))) return 'owner';
  if (env.WIFE_WA && digits(env.WIFE_WA).endsWith(d.slice(-9))) return 'wife';
  return null;
}

async function cfgGet(env) {
  return await kvGetJson(env, 'cfg', {
    mirror_on: true,         // 老婆收到的 bot 消息是否抄送老公（测试期建议 true）
    morning_on: true,        // 订阅：早报
    evening_on: true,        // 订阅：晚安包
    flash_on: false,         // 订阅：突发新闻
    channel_pref: 'auto',    // auto | wa | im
    tz_offset: 8,            // 邮轮时区 UTC 偏移
  });
}
async function cfgSet(env, patch) {
  const cfg = { ...(await cfgGet(env)), ...patch };
  await kvPutJson(env, 'cfg', cfg);
  return cfg;
}

// 24h service 窗口管理：她每发一条消息刷新 last_seen
const WINDOW_SECS = 23 * 3600; // 留 1h 安全余量
async function markSeen(env, who) { await kvPut(env, `seen:${who}`, String(nowSec())); }
async function windowAlive(env, who) {
  const t = parseInt(await kvGet(env, `seen:${who}`, '0'), 10);
  return nowSec() - t < WINDOW_SECS;
}

/* ============================ GLM（免费不限量） ============================ */

async function glmChat(env, messages, opts = {}) {
  const base = (env.GLM_BASE || 'https://open.bigmodel.cn').replace(/\/$/, '');
  const model = env.GLM_MODEL || 'glm-4-flash';
  const body = {
    model,
    messages,
    temperature: opts.temperature ?? 0.7,
    max_tokens: opts.max_tokens ?? 1500,
  };
  const r = await fetchT(`${base}/api/paas/v4/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${env.GLM_API_KEY}` },
    body: JSON.stringify(body),
  }, 60000);
  if (!r.ok) throw new Error(`GLM HTTP ${r.status}: ${clampStr(await r.text(), 200)}`);
  const j = await r.json();
  const out = j?.choices?.[0]?.message?.content;
  if (!out) throw new Error('GLM 空响应');
  return out.trim();
}

const GLM_PERSONA = '你是"小巡"，一位贴心的中文内容管家，服务对象正在邮轮上度假、手机只能收发纯文本消息。' +
  '规则：① 输出纯文本，禁用 Markdown 语法（不要 **加粗**、# 标题、[]()链接），可用 emoji 与空行分节；' +
  '② 简洁但信息密度高；③ 数字与事实准确，不确定就说不确定。';

function glmSys(extra) { return extra ? `${GLM_PERSONA}\n${extra}` : GLM_PERSONA; }

async function glmAsk(env, prompt, sysExtra = null, opts = {}) {
  return glmChat(env, [{ role: 'system', content: glmSys(sysExtra) }, { role: 'user', content: prompt }], opts);
}

async function glmSummarize(env, title, text, maxChars = 900) {
  return glmAsk(env,
    `把下面内容整理成适合手机短信阅读的中文要点（≤${maxChars} 字），保留关键数字与结论，末尾加一行"📌 一句话总结"：\n\n标题：${title}\n\n${clampStr(text, 9000)}`,
    '做摘要时严格基于原文，不要编造原文没有的事实。', { temperature: 0.3, max_tokens: 1200 });
}

/* ============================ 发送层 ============================ */

// WhatsApp/iMessage 文本切分（4096 上限，按段落边界）
function splitText(text, limit = 3800) {
  const out = [];
  let buf = '';
  for (const para of String(text).split(/\n\n/)) {
    if ((buf + '\n\n' + para).length > limit) {
      if (buf) out.push(buf);
      if (para.length > limit) {
        let s = para;
        while (s.length > limit) { out.push(s.slice(0, limit)); s = s.slice(limit); }
        buf = s;
      } else buf = para;
    } else buf = buf ? buf + '\n\n' + para : para;
  }
  if (buf) out.push(buf);
  return out;
}

async function sendWhatsApp(env, to, text) {
  const url = `https://graph.facebook.com/v23.0/${env.META_PHONE_NUMBER_ID}/messages`;
  const parts = splitText(text);
  const results = [];
  for (const p of parts) {
    const r = await fetchT(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${env.META_TOKEN}` },
      body: JSON.stringify({ messaging_product: 'whatsapp', to, type: 'text', text: { preview_url: false, body: p } }),
    }, 30000);
    if (!r.ok) results.push({ ok: false, status: r.status, body: clampStr(await r.text(), 300) });
    else results.push({ ok: true });
    if (parts.length > 1) await sleep(1200); // 分条节流，避免卫星链路乱序
  }
  return { ok: results.every(x => x.ok), parts: parts.length, results };
}

// iMessage 发送（BlueBubbles over Cloudflare Tunnel）；带 🤖 前缀用于 webhook 自环过滤
async function sendIMessage(env, text) {
  if (!env.BB_BASE || !env.BB_PASSWORD || !env.WIFE_IGUID) return { ok: false, skipped: true, reason: 'imessage 未配置' };
  const base = env.BB_BASE.replace(/\/$/, '');
  const parts = splitText(text, 7000);
  const results = [];
  for (const p of parts) {
    const r = await fetchT(`${base}/api/v1/message/text?password=${encodeURIComponent(env.BB_PASSWORD)}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chatGuid: env.WIFE_IGUID, message: '🤖 ' + p, method: 'private-api' }),
    }, 30000);
    if (!r.ok) results.push({ ok: false, status: r.status, body: clampStr(await r.text(), 300) });
    else results.push({ ok: true });
    if (parts.length > 1) await sleep(1200);
  }
  return { ok: results.every(x => x.ok), parts: parts.length, results };
}

/**
 * 智能路由发送（核心）：
 *   1. channel 显式指定 → 直接走
 *   2. auto：WhatsApp 24h 窗口内 → WA；否则 iMessage；再不行 → KV 待发队列
 *   3. mirror_on 时抄送老公（测试期能同看消息）
 *   4. 补发：她下次发消息时把队列内容一次性补上
 */
async function deliver(env, text, opts = {}) {
  const cfg = await cfgGet(env);
  const who = opts.who || 'wife';
  const to = who === 'owner' ? env.OWNER_WA : env.WIFE_WA;
  const pref = opts.channel || cfg.channel_pref;
  const log = { t: nowSec(), who, pref, attempts: [] };

  const tryWA = async () => {
    if (!env.META_TOKEN || !env.META_PHONE_NUMBER_ID || !to) { log.attempts.push({ ch: 'wa', skip: '未配置' }); return false; }
    const r = await sendWhatsApp(env, to, text);
    log.attempts.push({ ch: 'wa', ok: r.ok, parts: r.parts });
    return r.ok;
  };
  const tryIM = async () => {
    const r = await sendIMessage(env, text);
    log.attempts.push({ ch: 'im', ok: r.ok, skipped: !!r.skipped });
    return r.ok;
  };

  let sent = false;
  if (pref === 'wa') sent = await tryWA();
  else if (pref === 'im') sent = await tryIM();
  else {
    if (await windowAlive(env, who)) sent = await tryWA();
    if (!sent) sent = await tryIM();
    if (!sent) sent = await tryWA(); // 最后再试一次 WA（窗口可能刚被她刷新）
  }

  log.sent = sent;
  if (!sent) await enqueuePending(env, who, text);
  await kvPutJson(env, `sendlog:${nowSec()}`, log, 7 * 86400);

  if (cfg.mirror_on && who === 'wife' && !opts.noMirror) {
    try { if (env.META_TOKEN && env.OWNER_WA && await windowAlive(env, 'owner')) await sendWhatsApp(env, env.OWNER_WA, '【抄送】' + clampStr(text, 3200)); } catch {}
  }
  return { sent, log };
}

async function enqueuePending(env, who, text) {
  const key = `pending:${who}`;
  const list = await kvGetJson(env, key, []);
  list.push({ t: nowSec(), text: clampStr(text, 3500) });
  while (list.length > 20) list.shift();
  await kvPutJson(env, key, list, 10 * 86400);
}
async function flushPending(env, who) {
  const key = `pending:${who}`;
  const list = await kvGetJson(env, key, []);
  if (!list.length) return '';
  await kvDel(env, key);
  const lines = list.map(x => `⏳${new Date(x.t * 1000).toISOString().slice(5, 16).replace('T', ' ')} ${clampStr(x.text, 1200)}`);
  return `📮 离线期间没能送达的 ${list.length} 条内容：\n\n` + lines.join('\n\n');
}

/* ============================ 内容服务（全部免费源） ============================ */

// ---- RSS / XML 解析（Worker 环境无 DOMParser，用正则） ----
function parseRss(xml, limit = 8) {
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

// ---- 多源搜索：Bing RSS（免 key 较稳）→ DuckDuckGo Lite 兜底 ----
async function searchWeb(query, limit = 8) {
  const out = [];
  try {
    const r = await fetchT(`https://www.bing.com/search?q=${encodeURIComponent(query)}&format=rss&count=${limit}`, {}, 15000);
    if (r.ok) out.push(...parseRss(await r.text(), limit).map(x => ({ ...x, src: 'bing' })));
  } catch {}
  if (out.length < 3) {
    try {
      const r = await fetchT(`https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`, { headers: { accept: 'text/html' } }, 15000);
      if (r.ok) {
        const html = await r.text();
        const re = /<a[^>]+class="result-link"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g;
        let m;
        while ((m = re.exec(html)) && out.length < limit) {
          let url = m[1];
          const ud = url.match(/uddg=([^&]+)/); if (ud) url = decodeURIComponent(ud[1]);
          out.push({ title: m[2].replace(/<[^>]+>/g, '').trim(), link: url, desc: '', src: 'ddg' });
        }
      }
    } catch {}
  }
  return out;
}

// ---- Jina Reader 免费抓正文 ----
async function readArticle(url, maxChars = 9000) {
  const r = await fetchT(`https://r.jina.ai/${url}`, { headers: { accept: 'text/plain', 'x-return-format': 'text' } }, 30000);
  if (!r.ok) throw new Error(`Reader HTTP ${r.status}`);
  const t = (await r.text()).replace(/\n{3,}/g, '\n\n').trim();
  return clampStr(t, maxChars) || '';
}

// ---- 维基百科摘要 ----
async function wikiSummary(term) {
  const r = await fetchT(`https://zh.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(term)}`, { headers: { accept: 'application/json' } }, 15000);
  if (!r.ok) throw new Error(`wiki HTTP ${r.status}`);
  const j = await r.json();
  if (String(j.type || '').includes('not_found')) throw new Error('词条不存在');
  return { title: j.title, extract: j.extract || '', url: j?.content_urls?.desktop?.page || '' };
}

// ---- 天气（open-meteo，免 key） ----
async function weather(city) {
  const g = await (await fetchT(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=zh`, {}, 15000)).json();
  const loc = g?.results?.[0];
  if (!loc) throw new Error(`找不到城市：${city}`);
  const w = await (await fetchT(`https://api.open-meteo.com/v1/forecast?latitude=${loc.latitude}&longitude=${loc.longitude}` +
    '&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days=3&timezone=auto', {}, 15000)).json();
  const W = { 0: '晴', 1: '多云', 2: '局部多云', 3: '阴', 45: '雾', 51: '毛毛雨', 61: '小雨', 63: '中雨', 65: '大雨', 71: '小雪', 73: '中雪', 80: '阵雨', 95: '雷雨' };
  const wc = c => W[c] || '·';
  const d = w.daily, cur = w.current;
  let s = `🌍 ${loc.name}（${loc.country || ''}）天气\n\n`;
  s += `当前 ${cur.temperature_2m}°C 体感 ${cur.apparent_temperature}°C，${wc(cur.weather_code)}，风速 ${cur.wind_speed_10m} km/h\n\n`;
  for (let i = 0; i < d.time.length; i++) {
    s += `${d.time[i].slice(5)}：${wc(d.weather_code[i])}，${d.temperature_2m_min[i]}~${d.temperature_2m_max[i]}°C，降水概率 ${d.precipitation_probability_max[i] ?? '-'}%\n`;
  }
  return s;
}

// ---- 热榜（多源 fallback，尽力而为） ----
async function hotList(board) {
  const tries = [];
  if (board === 'weibo') tries.push(['https://api.vvhan.com/api/hotlist/wbHot', j => (j.data || []).slice(0, 15).map(x => x.title)]);
  tries.push(['https://api.vvhan.com/api/hotlist/zhihuHot', j => (j.data || []).slice(0, 15).map(x => x.title)]);
  tries.push(['https://api.zhihu.com/topstory/hot-list?limit=10', j => (j.data || []).map(x => x.target?.title?.replace(/<[^>]+>/g, ''))]);
  for (const [url, pick] of tries) {
    try {
      const r = await fetchT(url, {}, 12000);
      if (!r.ok) continue;
      const j = await r.json();
      const titles = (pick(j) || []).filter(Boolean);
      if (titles.length) return titles;
    } catch {}
  }
  throw new Error('热榜源全部不可用');
}

// ---- 古腾堡公版书 ----
async function bookSearch(q) {
  const r = await fetchT(`https://gutendex.com/books?search=${encodeURIComponent(q)}`, {}, 15000);
  const j = await r.json();
  return (j.results || []).slice(0, 5).map(b => ({
    id: b.id, title: b.title, author: b.authors?.[0]?.name || '佚名',
    zh: b.languages?.includes('zh'), downloads: b.download_count,
    txt: (b.formats || {})['text/plain; charset=utf-8'] || (b.formats || {})['text/plain'],
  }));
}
async function bookChunk(url, idx, chunkLen = 3400) {
  const r = await fetchT(url, {}, 30000);
  if (!r.ok) throw new Error(`Gutenberg HTTP ${r.status}`);
  const text = (await r.text()).replace(/\r\n/g, '\n');
  const nChunks = Math.ceil(text.length / chunkLen);
  if (idx < 1 || idx > nChunks) throw new Error(`章节号 1~${nChunks}`);
  return { chunk: text.slice((idx - 1) * chunkLen, idx * chunkLen), total: nChunks };
}

/* ============================ 早报 / 晚报组装 ============================ */

async function buildMorning(env) {
  const city = env.DEFAULT_CITY || '上海';
  const feeds = [
    ['BBC中文', 'https://feeds.bbci.co.uk/zhongwen/simp/rss.xml'],
    ['36氪科技', 'https://36kr.com/feed'],
    ['Hacker News', 'https://hnrss.org/front_page'],
  ];
  const results = await Promise.allSettled(feeds.map(async ([name, url]) => {
    const r = await fetchT(url, {}, 15000);
    if (!r.ok) throw new Error(`${name} HTTP ${r.status}`);
    return { name, items: parseRss(await r.text(), 6) };
  }));
  let wx = '';
  try { wx = await weather(city); } catch {}

  const parts = results.filter(x => x.status === 'fulfilled').map(x => x.value);
  if (!parts.length && !wx) return '🌅 早报源暂时全部不可达，请稍后再发一次「早」试试。';

  let raw = '';
  for (const p of parts) {
    raw += `\n【${p.name}】\n` + p.items.map((it, i) => `${i + 1}. ${it.title}${it.desc ? '：' + clampStr(it.desc, 80) : ''}`).join('\n');
  }
  let digest = '';
  try {
    digest = await glmAsk(env,
      `以下是今天抓到的新闻标题与摘要，请整理成一份"早安早报"：\n` +
      `1) 开头一句今日日期问候；\n2) "要闻速览"挑 6 条最重要（中英文源统一中文输出，每条 1-2 句）；\n` +
      `3) "科技/互联网"挑 3 条；\n4) 结尾给一条适合邮轮度假者的轻松提示。\n全部纯文本，emoji 分节，总长 ≤1100 字。\n\n${clampStr(raw, 7000)}`,
      '你是可靠的新闻编辑。只基于给定素材，不编造。', { temperature: 0.4, max_tokens: 1600 });
  } catch (e) {
    digest = raw.slice(0, 3000); // GLM 挂了就发原始标题
  }
  return `🌅 早安！今日份世界观已装船。\n\n${digest}${wx ? '\n\n' + wx : ''}\n\n—— 发「帮助」看全部玩法，发「继续」追连载 📖`;
}

async function buildEvening(env) {
  const fact = await glmAsk(env,
    '随机讲一个有趣的冷知识（80 字内），再出一个适合睡前玩的谜语（不给答案，让对方猜，回复「猜 xxx」验证）。' +
    '格式：\n🌙 晚间冷知识\n…\n\n🧩 今日谜题\n…',
    null, { temperature: 1.0, max_tokens: 500 });
  return `🌆 晚安包来啦。\n\n${fact}\n\n—— 发「继续」追你的连载小说，发「游戏」来玩猜谜 🎲`;
}

/* ============================ 指令路由 ============================ */

function menuText(isOwner) {
  return [
    '🛳️ 小巡 · 邮轮文字管家（帮助）',
    '',
    '📰 内容订阅（每天自动送达）',
    '· 「早」 早报：要闻+科技+天气',
    '· 「晚」 晚安包：冷知识+谜题',
    '',
    '🔍 随点随看（发文字给我）',
    '· 「搜 关键词」 联网搜索+归纳',
    '· 「小红书 关键词」 小红书尽力找',
    '· 直接发链接 → 我读全文讲给你',
    '· 「全文 链接」 长文分节原汁原味',
    '· 「wiki 词条」「天气 城市」',
    '· 「热榜」 知乎/微博在吵什么',
    '· 「翻译 内容」 中英日韩随便',
    '',
    '📚 打发时间',
    '· 「读 书名」 公版书分章看',
    '· 「新故事 玄幻」 我给你写连载',
    '· 「继续」 连载下一章',
    '· 「游戏」 猜谜，「猜 答案」验证',
    '· 「聊 开心点」 纯聊天',
    '',
    '⚙️ 设置',
    '· 「时区 UTC+2」 邮轮当地时间',
    '· 「订阅 早报 关」 停推早报',
    isOwner ? '· 「广播 内容」 直达她\n· 「帮我 早」 代她执行并推送\n· 「回微信 @人 内容」 经云电脑发微信' : '· 「回老公 内容」 消息直达岸上',
    '',
    '⚠️ 船上网络只放行文字消息，长文我会切成多条发。',
  ].join('\n');
}

async function handleCommand(env, who, raw) {
  const text = String(raw || '').trim();
  const cfg = await cfgGet(env);

  // ---- 高频/设置类 ----
  if (/^(帮助|菜单|指令|help)$/i.test(text)) return menuText(who === 'owner');

  if (/^时区/i.test(text)) {
    const m = text.match(/UTC\s*([+-]?\d{1,2})/i) || text.match(/([+-]?\d{1,2})/);
    if (m) {
      const off = Math.max(-12, Math.min(14, parseInt(m[1], 10)));
      await cfgSet(env, { tz_offset: off });
      return `✅ 邮轮时区已记为 UTC${off >= 0 ? '+' : ''}${off}。定时推送的时点如需精确对齐当地早 8 点，改 GitHub Actions cron 即可（README 有说明）。`;
    }
    return `当前时区 UTC${cfg.tz_offset >= 0 ? '+' : ''}${cfg.tz_offset}。发送示例：「时区 UTC+2」`;
  }

  if (/^(订阅|开关)/.test(text)) {
    const on = /开|on|true/i.test(text) && !/关|off/i.test(text.split(/订阅|开关/)[1] || '');
    if (/早/.test(text)) { await cfgSet(env, { morning_on: on }); return `✅ 早报已${on ? '开启' : '关闭'}`; }
    if (/晚/.test(text)) { await cfgSet(env, { evening_on: on }); return `✅ 晚安包已${on ? '开启' : '关闭'}`; }
    if (/突发|新闻/.test(text)) { await cfgSet(env, { flash_on: on }); return `✅ 突发新闻已${on ? '开启' : '关闭'}`; }
    const j = await cfgGet(env);
    return `当前订阅：早报=${j.morning_on ? '开' : '闭'} 晚安包=${j.evening_on ? '开' : '闭'} 突发=${j.flash_on ? '开' : '闭'}\n示例：「订阅 早报 关」`;
  }

  // ---- 通道/角色专属 ----
  if (who === 'owner') {
    if (/^广播/.test(text)) {
      const content = text.replace(/^广播\s*/, '');
      if (!content) return '用法：「广播 晚上七点船长晚宴，记得穿正装」——内容会原文发给她。';
      const r = await deliver(env, `📣 来自岸上的话：\n\n${content}`, { who: 'wife' });
      return r.sent ? '✅ 已送达她的收件箱。' : '⚠️ 暂时没送出去，已进待发队列（她下次发消息时补送）。';
    }
    if (/^帮我\s*/.test(text)) {
      const cmd = text.replace(/^帮我\s*/, '');
      if (!cmd) return '用法：「帮我 早」→ 我执行后把结果直接推送给她。';
      const reply = await handleCommand(env, 'wife', cmd);
      const r = await deliver(env, `🤝 老公代点：${cmd}\n\n${reply}`, { who: 'wife' });
      return r.sent ? `✅ 已执行并推送给她（内容开头）：\n\n${clampStr(reply, 600)}` : '⚠️ 已执行但推送失败，进了待发队列。';
    }
    if (/^回微信/.test(text)) {
      // 语法：「回微信 @联系人 内容」或「回微信 内容」（默认发文件传输助手）
      // 由 Windows 365 云电脑上的 wxbridge.py 轮询 KV wx_outbox 执行真实发送
      const rest = text.replace(/^回微信\s*/, '');
      let to = env.WX_DEFAULT_TO || '文件传输助手';
      let content = rest;
      const m = rest.match(/^@(\S+)\s*([\s\S]*)/);
      if (m && m[2].trim()) { to = m[1]; content = m[2].trim(); }
      if (!content.trim()) return '用法：「回微信 @联系人 内容」，省略 @ 则发给文件传输助手。';
      const box = await kvGetJson(env, 'wx_outbox', []);
      box.push({ t: nowSec(), to, text: clampStr(content, 1500) });
      await kvPutJson(env, 'wx_outbox', box.slice(-20), 86400);
      return `✅ 已交微信桥投递：→「${to}」：${clampStr(content, 80)}（云电脑在线时 30 秒内发出）`;
    }
  }
  if (who === 'wife') {
    const m = text.match(/^(?:回老公|告诉老公|reply)\s*([\s\S]*)/i);
    if (m) {
      if (!m[1].trim()) return '用法：「回老公 我很好，今天到了米克诺斯」';
      const r = await deliver(env, `💕 她从船上发来：\n\n${m[1].trim()}`, { who: 'owner' });
      return r.sent ? '✅ 已转达岸上。' : '⚠️ 岸上暂时没收到，进了待发队列。';
    }
  }

  // ---- 内容指令 ----
  if (text === '早' || /^(早安|早报|早上好)$/.test(text)) return await buildMorning(env);
  if (text === '晚' || /^(晚安|晚上好)$/.test(text)) return await buildEvening(env);

  if (/^(热榜|知乎热榜|微博热搜|微博热榜)/.test(text)) {
    const board = /微博/.test(text) ? 'weibo' : 'zhihu';
    try {
      const titles = await hotList(board);
      return `🔥 ${board === 'weibo' ? '微博' : '知乎'}热榜 Top ${titles.length}\n\n` +
        titles.map((t, i) => `${i + 1}. ${clampStr(t, 60)}`).join('\n') +
        `\n\n想看哪条？回复「搜 标题关键词」我展开讲。`;
    } catch (e) { return `😅 热榜源抽风了（${e.message}）。可以试试「搜 今天的新闻」。`; }
  }

  const sh = text.match(/^(?:小红书|红书|xhs)\s*([\s\S]+)/);
  if (sh) return await svcXhs(env, sh[1].trim());

  const se = text.match(/^(?:搜|search|查一下)\s*([\s\S]+)/i);
  if (se) return await svcSearch(env, se[1].trim());

  const full = text.match(/^(?:全文|原文)\s+(\S+)/);
  if (full) return await svcRead(env, full[1], true, who);

  const tr = text.match(/^(?:翻译|translate)\s*([\s\S]+)/i);
  if (tr) {
    const t = tr[1].trim();
    return glmAsk(env, `把以下内容在中文与其他语言间智能互译（按内容自动判断方向），只给译文：\n\n${clampStr(t, 3000)}`,
      null, { temperature: 0.2, max_tokens: 1400 });
  }

  const wk = text.match(/^(?:wiki|维基)\s*([\s\S]+)/i);
  if (wk) {
    try {
      const w = await wikiSummary(wk[1].trim());
      return `📖 ${w.title}\n\n${w.extract || '（无摘要）'}${w.url ? `\n\n🔗 ${w.url}（回港可看图）` : ''}`;
    } catch (e) { return `没找到词条「${wk[1]}」：${e.message}\n试试「搜 ${wk[1]}」`; }
  }

  const we = text.match(/^(?:天气|weather)\s*(.*)/i);
  if (we) {
    try { return await weather(we[1].trim() || env.DEFAULT_CITY || '上海'); }
    catch (e) { return `天气查询失败：${e.message}`; }
  }

  const bk = text.match(/^(?:读|book)\s*([\s\S]+)/i);
  if (bk) return await svcBook(env, who, bk[1].trim());
  const pick = text.match(/^(?:看|选|read)\s+(\d{1,4})$/i);
  if (pick) return await svcBookRead(env, who, parseInt(pick[1], 10));

  const ns = text.match(/^(?:新故事|连载)\s*([\s\S]*)/);
  if (ns) return await svcStoryNew(env, who, ns[1].trim() || '温馨治愈');
  if (/^继续/.test(text)) return await svcStoryNext(env, who);

  if (/^(游戏|猜谜|谜语|来一局)/.test(text)) return await svcRiddleNew(env, who);
  const guess = text.match(/^(?:猜)\s*([\s\S]+)/);
  if (guess) return await svcRiddleCheck(env, who, guess[1].trim());
  if (/^放弃/.test(text)) return await svcRiddleCheck(env, who, '放弃');

  // ---- URL 直接阅读 ----
  if (/^https?:\/\//i.test(text)) return await svcRead(env, text.trim(), false, who);

  // ---- 兜底：自由聊天 ----
  return glmAsk(env, clampStr(text, 3000), '对方可能在船上随手跟你闲聊。自然回应，篇幅适中（100~300 字），可以顺势提议玩法（如「想听连载可以说 新故事 悬疑」）。');
}

/* ---------------------- 内容服务实现 ---------------------- */

async function svcSearch(env, q) {
  const items = await searchWeb(q, 8);
  if (!items.length) {
    try {
      return `🔍「${q}」搜索引擎不可达，以下基于模型知识（可能不是最新）：\n\n` +
        await glmAsk(env, `介绍「${q}」相关要点（300 字内，纯文本）。`, null, { temperature: 0.5 });
    } catch { return '🔍 搜索和模型都暂时不可达，请过几分钟再试。'; }
  }
  const listing = items.map((x, i) => `${i + 1}. ${x.title}${x.desc ? '\n   ' + clampStr(x.desc, 90) : ''}`).join('\n');
  let digest = '';
  try {
    digest = await glmAsk(env, `搜索「${q}」的结果如下，请归纳成 300 字内的情报卡：核心事实/各方说法/一句话点评。\n\n${items.map(x => `${x.title}：${x.desc}`).join('\n')}`,
      null, { temperature: 0.4 });
  } catch {}
  return `🔍「${q}」\n\n${digest ? '💡 ' + digest + '\n\n' : ''}🗂️ 来源：\n${listing}\n\n想读全文？把对应链接发给我。`;
}

async function svcXhs(env, q) {
  // 小红书无官方 API 且反爬强：Bing RSS 站内搜索 + Jina 尽力抓取，失败诚实降级
  const items = await searchWeb(`site:xiaohongshu.com ${q}`, 6);
  const xhs = items.filter(x => /xiaohongshu\.com/.test(x.link));
  if (!xhs.length) {
    const alt = await searchWeb(`${q} 小红书 笔记`, 5);
    if (!alt.length) return `📕 小红书内容抓不动（反爬+未登录态）。给你普通搜索兜底：\n\n` + await svcSearch(env, q);
    return `📕 小红书直采失败，搜索引擎找到这些相关内容：\n\n` +
      alt.map((x, i) => `${i + 1}. ${x.title}${x.link ? '\n   ' + x.link : ''}`).join('\n') +
      `\n\n把链接发给我即可读全文。`;
  }
  let body = '';
  try { body = await readArticle(xhs[0].link, 6000); } catch {}
  if (body) {
    try {
      const digest = await glmSummarize(env, `小红书「${q}」笔记`, body, 700);
      return `📕 小红书「${q}」· 篇1摘要\n\n${digest}\n\n🗂️ 其他结果：\n` +
        xhs.slice(1).map((x, i) => `${i + 2}. ${x.title}`).join('\n') +
        `\n\n把对应链接粘给我可继续读。`;
    } catch {}
  }
  return `📕 小红书「${q}」找到 ${xhs.length} 条（正文有登录墙，只能给标题和链接）：\n\n` +
    xhs.map((x, i) => `${i + 1}. ${x.title}\n   ${x.link}`).join('\n') +
    `\n\n把链接发给我可试读全文；或「搜 ${q}」换普通搜索。`;
}

async function svcRead(env, url, fullMode, who = 'wife') {
  try {
    const body = await readArticle(url, fullMode ? 26000 : 9000);
    if (!body) throw new Error('正文为空');
    if (fullMode) {
      const parts = splitText(body, 3400);
      for (let i = 0; i < Math.min(parts.length, 8); i++) {
        await deliver(env, `${i + 1}/${parts.length}\n${parts[i]}`, { who });
        await sleep(800);
      }
      return parts.length > 8
        ? `前 8 条已发出（全文共 ${parts.length} 条，受单轮篇幅限制先到这里）。需要剩余部分再发一次「全文 ${url}」。`
        : '✅ 全文发送完毕。';
    }
    const digest = await glmSummarize(env, url, body, 1000);
    return `📰 ${url}\n\n${digest}\n\n想要原汁原味全文？发「全文 ${url}」。`;
  } catch (e) {
    return `📄 这篇读不动（${e.message}）。可以发「搜 ${clampStr(url, 60)}」换搜索引擎。`;
  }
}

async function svcBook(env, who, q) {
  const books = await bookSearch(q);
  if (!books.length) return `📚 古腾堡没找到「${q}」。试试英文名，或换「新故事 ${q}」让我现写。`;
  await kvPutJson(env, `book:${who}`, books, 86400);
  return `📚 公版书搜索「${q}」：\n\n` + books.map((b, i) =>
    `${i + 1}.《${b.title}》\n   ${b.author} · 下载${b.downloads}${b.zh ? ' · 中文' : ' · 外文'}\n   回复「看 ${i + 1}」开始分章读`
  ).join('\n\n') + `\n\n（约每 3400 字一段，我会切成多条发）`;
}

async function svcBookRead(env, who, idx) {
  const books = await kvGetJson(env, `book:${who}`, []);
  const b = books[idx - 1];
  if (!b || !b.txt) return '书单过期了，重新发「读 书名」。';
  try {
    const { chunk, total } = await bookChunk(b.txt, 1);
    await kvPutJson(env, `bookpos:${who}`, { url: b.txt, idx: 1, total }, 86400);
    const parts = splitText(chunk, 3400);
    for (const p of parts) { await deliver(env, p, { who }); await sleep(800); }
    return `📖《${b.title}》第 1/${total} 段已发出。回复「看 2」读下一段…（回复书名可重新搜书）`;
  } catch (e) { return `书籍下载失败：${e.message}`; }
}

async function svcStoryNew(env, who, topic) {
  const seed = await glmAsk(env,
    `开始写一篇连载小说的第一章，题材：「${topic}」。要求：800 字左右，结尾留钩子，主角设定留白给后续展开。` +
    `开头给小说一个标题，格式：\n📖《书名》· 第一章 章节名\n\n正文…`,
    null, { temperature: 0.9, max_tokens: 1800 });
  await kvPutJson(env, `story:${who}`, { topic, tail: seed.slice(-600), chapter: 1 }, 10 * 86400);
  return seed;
}

async function svcStoryNext(env, who) {
  const st = await kvGetJson(env, `story:${who}`);
  if (!st) return '还没有连载。发「新故事 题材」开一本（例：新故事 悬疑）';
  const next = await glmAsk(env,
    `这是连载小说最近的情节结尾：\n…${st.tail}\n\n请续写第 ${st.chapter + 1} 章，800 字左右，题材基调「${st.topic}」，结尾继续留钩子。` +
    `格式开头：\n📖 第 ${st.chapter + 1} 章\n`,
    '保持人物与情节连贯，若上文信息不足可自然推进。', { temperature: 0.9, max_tokens: 1800 });
  st.chapter += 1; st.tail = next.slice(-600);
  await kvPutJson(env, `story:${who}`, st, 10 * 86400);
  return next;
}

async function svcRiddleNew(env, who) {
  const r = await glmAsk(env,
    '出一道中等难度的中文谜语（或脑筋急转弯），严格输出 JSON：{"q":"谜面","a":"谜底"}，不要其他文字。',
    null, { temperature: 1.0, max_tokens: 300 });
  let obj = null;
  try { obj = JSON.parse(r.match(/\{[\s\S]*\}/)[0]); } catch {}
  if (!obj || !obj.q || !obj.a) return '出题失败了，再发一次「游戏」试试。';
  await kvPutJson(env, `riddle:${who}`, { q: obj.q, a: String(obj.a) }, 86400);
  return `🧩 谜题来了：\n\n${obj.q}\n\n回复「猜 你的答案」验证；回复「放弃」看答案。`;
}

async function svcRiddleCheck(env, who, guess) {
  const r = await kvGetJson(env, `riddle:${who}`);
  if (!r) return '先发「游戏」领取谜题。';
  if (/放弃/.test(guess)) { await kvDel(env, `riddle:${who}`); return `😤 谜底是：「${r.a}」。再来一局？发「游戏」`; }
  const verdict = await glmAsk(env, `谜面：${r.q}\n谜底：${r.a}\n用户答案：${guess}\n判断用户答案是否算对（意思对即可）。输出 JSON：{"correct":true/false,"say":"一句俏皮回应"}`,
    null, { temperature: 0.3, max_tokens: 200 });
  let v = null;
  try { v = JSON.parse(verdict.match(/\{[\s\S]*\}/)[0]); } catch {}
  if (v?.correct) { await kvDel(env, `riddle:${who}`); return `🎉 答对了！${v.say || ''}\n（谜底：${r.a}）\n再来一局？发「游戏」`; }
  return `${v?.say || '再想想～'}\n（提示：可用「放弃」看答案）`;
}

/* ============================ WhatsApp Webhook ============================ */

function envTokenOk(env, token) { return !!(env.META_VERIFY_TOKEN && token === env.META_VERIFY_TOKEN); }

async function handleWhatsAppVerify(env, url) {
  const mode = url.searchParams.get('hub.mode');
  const token = url.searchParams.get('hub.verify_token');
  const challenge = url.searchParams.get('hub.challenge');
  if (mode === 'subscribe' && token && envTokenOk(env, token)) return tresp(challenge || '');
  return tresp('forbidden', 403);
}

async function handleWhatsAppPost(env, req) {
  const raw = await req.text();
  // 签名校验（Meta 用 app secret 对原始 body 做 HMAC-SHA256）
  const sig = req.headers.get('x-hub-signature-256') || '';
  if (env.META_APP_SECRET) {
    const expect = 'sha256=' + await hmacSha256Hex(env.META_APP_SECRET, raw);
    if (sig !== expect) return jresp({ error: 'bad signature' }, 403);
  }
  let payload;
  try { payload = JSON.parse(raw); } catch { return jresp({ ok: true }); }

  const values = payload?.entry?.[0]?.changes?.[0]?.value || {};
  if (values.statuses?.length) {
    const st = values.statuses[0];
    await kvPutJson(env, `wastat:${nowSec()}`, { id: st.id, status: st.status, t: nowSec() }, 86400);
    return jresp({ ok: true });
  }
  const msgs = values.messages || [];
  for (const m of msgs) {
    try {
      const who = whoAmI(env, m.from);
      if (!who) {
        if (env.META_TOKEN) await sendWhatsApp(env, m.from, '🤖 本助手仅服务指定用户。');
        continue;
      }
      const text = m?.text?.body || m?.interactive?.button_reply?.title || m?.button?.text || '';
      await markSeen(env, who);
      if (!text || !text.trim()) {
        await deliver(env, '收到～船上只通文字，图片语音我读不了。想看什么发文字给我就行！', { who });
        continue;
      }
      const pending = await flushPending(env, who);
      let reply;
      try { reply = await handleCommand(env, who, text); }
      catch (e) { reply = `😵 这条指令翻车了：${e.message}\n发「帮助」看可用指令。`; }
      if (pending) reply = pending + '\n\n———\n\n' + reply;
      await deliver(env, reply, { who });
    } catch (e) { /* 单条失败不阻塞其他消息 */ }
  }
  return jresp({ ok: true });
}

/* ============================ iMessage Webhook（BlueBubbles） ============================ */

async function handleIMessage(env, req, url) {
  const pw = url.searchParams.get('p') || req.headers.get('x-bb-password') || '';
  if (!env.BB_PASSWORD || pw !== env.BB_PASSWORD) return jresp({ error: 'bad password' }, 403);
  let payload;
  try { payload = await req.json(); } catch { return jresp({ ok: true }); }

  const type = payload?.type || '';
  if (type !== 'new-message' && type !== 'sent-message') return jresp({ ok: true });
  const d = payload.data || {};
  const text = String(d.text || '').trim();

  // bot 自己发的消息带 🤖 前缀 → 忽略（同 Apple ID 下 fromMe 无法区分人与 bot，靠前缀）
  if (d.isFromMe && text.startsWith('🤖')) return jresp({ ok: true });
  if (!text) return jresp({ ok: true });

  // 判定身份：聊天对象 handle 匹配 wife / owner
  const handles = [d.handle?.address, ...(d.chats?.[0]?.participants || []).map(p => p.address)]
    .filter(Boolean).map(x => String(x).toLowerCase());
  let who = null;
  for (const h of handles) {
    if (env.OWNER_WA && digits(env.OWNER_WA).endsWith(digits(h).slice(-9))) who = 'owner';
    if (env.WIFE_WA && digits(env.WIFE_WA).endsWith(digits(h).slice(-9))) who = 'wife';
  }
  // 同 ID 自发消息（老婆在 iPhone 手动输入，同步到 Mac）：fromMe=true → 视为 wife
  if (!who && d.isFromMe) who = 'wife';
  if (!who) return jresp({ ok: true });

  await markSeen(env, who);
  const pending = await flushPending(env, who);
  let reply;
  try { reply = await handleCommand(env, who, text); }
  catch (e) { reply = `😵 这条指令翻车了：${e.message}`; }
  if (pending) reply = pending + '\n\n———\n\n' + reply;
  await deliver(env, reply, { who });
  return jresp({ ok: true });
}

/* ============================ 内部 API（Actions / 人工） ============================ */

function agentOk(env, req) { return !!(env.AGENT_KEY && req.headers.get('x-agent-key') === env.AGENT_KEY); }

async function handleSend(env, req) {
  const body = await req.json();
  const text = String(body.text || '').trim();
  if (!text) return jresp({ error: 'text required' }, 400);
  const r = await deliver(env, text, { who: body.who || 'wife', channel: body.channel });
  return jresp({ ok: r.sent, detail: r.log });
}

async function handleState(env, req, url) {
  if (req.method === 'GET') {
    const key = url.searchParams.get('key');
    if (!key) return jresp({ error: 'key required' }, 400);
    return jresp({ key, value: await kvGet(env, key) });
  }
  const body = await req.json();
  if (!body.key) return jresp({ error: 'key required' }, 400);
  await kvPut(env, body.key, body.value ?? '', body.ttl || null);
  return jresp({ ok: true });
}

/* ============================ 入口路由 ============================ */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (path === '/' && request.method === 'GET') {
        return tresp(`cruise-bot worker ✓ ${VERSION}\nhealthy & awaiting sailor messages.`);
      }

      if (path === '/health' && request.method === 'GET') {
        return jresp({
          version: VERSION,
          whatsapp: !!(env.META_TOKEN && env.META_PHONE_NUMBER_ID),
          imessage: !!(env.BB_BASE && env.BB_PASSWORD && env.WIFE_IGUID),
          glm: !!env.GLM_API_KEY,
          owner: !!env.OWNER_WA, wife: !!env.WIFE_WA,
          actions_key: !!env.AGENT_KEY,
        });
      }

      // ---- WhatsApp ----
      if (path === '/webhook/whatsapp') {
        if (request.method === 'GET') return handleWhatsAppVerify(env, url);
        if (request.method === 'POST') return handleWhatsAppPost(env, request);
        return tresp('method not allowed', 405);
      }

      // ---- iMessage（BlueBubbles） ----
      if (path === '/webhook/imessage' && request.method === 'POST') {
        return handleIMessage(env, request, url);
      }

      // ---- 内部 API ----
      if (path === '/send' && request.method === 'POST') {
        if (!agentOk(env, request)) return jresp({ error: 'unauthorized' }, 401);
        return handleSend(env, request);
      }
      if (path === '/state' && (request.method === 'GET' || request.method === 'POST')) {
        if (!agentOk(env, request)) return jresp({ error: 'unauthorized' }, 401);
        return handleState(env, request, url);
      }
      if (path === '/cfg' && request.method === 'GET') {
        if (!agentOk(env, request)) return jresp({ error: 'unauthorized' }, 401);
        return jresp(await cfgGet(env));
      }

      return tresp('not found', 404);
    } catch (e) {
      return jresp({ error: e.message, version: VERSION }, 500);
    }
  },
};
