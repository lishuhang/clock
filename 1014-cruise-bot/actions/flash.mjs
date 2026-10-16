// 突发新闻检查：对比头条 hash，有变化才推送（每 4h 跑一次也几乎不打扰）
// flash_on 订阅默认关，需要时她发「订阅 突发 开」
import { requiredEnv, fetchT, parseRss, glm, workerSend, workerStateGet, workerStatePut, subscriptionOn } from './lib.mjs';
import { createHash } from 'node:crypto';

requiredEnv(['CRUISE_WORKER_URL', 'CRUISE_AGENT_KEY', 'GLM_API_KEY']);

const FEED = 'https://feeds.bbci.co.uk/zhongwen/simp/rss.xml';

try {
  const on = await subscriptionOn(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, 'flash_on');
  if (!on) { console.log('突发新闻订阅关闭，跳过。'); process.exit(0); }

  const r = await fetchT(FEED, {}, 15000);
  if (!r.ok) throw new Error(`RSS HTTP ${r.status}`);
  const items = parseRss(await r.text(), 6);
  if (!items.length) { console.log('RSS 空结果'); process.exit(0); }

  const hash = createHash('sha256').update(items.map(x => x.title).join('|')).digest('hex').slice(0, 16);
  const prev = await workerStateGet(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, 'flash_hash');
  console.log(`hash=${hash} prev=${prev}`);
  if (hash === prev) { console.log('头条无变化，跳过。'); process.exit(0); }

  const digest = await glm(process.env,
    `以下是最新头条，写一条 3 条要点以内的"突发速览"（每条 1-2 句，纯文本 ≤350 字，开头加 ⚡）：\n\n` +
    items.map(x => `- ${x.title}`).join('\n'),
    '只基于给定素材，不编造。', { temperature: 0.3, max_tokens: 700 });

  await workerSend(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, `⚡ 突发速览\n\n${digest}\n\n—— 想展开某条就发「搜 关键词」`);
  await workerStatePut(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, 'flash_hash', hash, 14 * 86400);
  console.log('突发速览已推送');
} catch (e) {
  console.error('flash 任务失败：', e);
  process.exit(1);
}
