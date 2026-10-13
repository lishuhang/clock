// 每日早报：RSS 多源 → GLM 汇总 → Worker /send
// 用法：node morning.mjs   （secrets 由 workflow 注入）
import { requiredEnv, fetchT, parseRss, glm, workerSend, subscriptionOn, weather, nowStr } from './lib.mjs';

requiredEnv(['CRUISE_WORKER_URL', 'CRUISE_AGENT_KEY', 'GLM_API_KEY']);

const WHO = process.env.CRUISE_WHO || 'wife';
const CITY = process.env.CITY || '上海';
const TZ = parseInt(process.env.TZ_OFFSET || '8', 10);

const FEEDS = [
  ['BBC中文', 'https://feeds.bbci.co.uk/zhongwen/simp/rss.xml'],
  ['36氪科技', 'https://36kr.com/feed'],
  ['Hacker News', 'https://hnrss.org/front_page'],
];

try {
  const on = await subscriptionOn(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, 'morning_on');
  if (!on) { console.log('早报订阅已关闭，跳过。'); process.exit(0); }

  const results = await Promise.allSettled(FEEDS.map(async ([name, url]) => {
    const r = await fetchT(url, {}, 15000);
    if (!r.ok) throw new Error(`${name} HTTP ${r.status}`);
    return { name, items: parseRss(await r.text(), 6) };
  }));
  const parts = results.filter(x => x.status === 'fulfilled').map(x => x.value);
  console.log(`抓取成功 ${parts.length}/${FEEDS.length} 源`);

  let wx = '';
  try { wx = await weather(CITY); } catch (e) { console.log('天气失败', e.message); }

  let digest;
  if (parts.length) {
    const raw = parts.map(p => `\n【${p.name}】\n` + p.items.map((it, i) => `${i + 1}. ${it.title}${it.desc ? '：' + it.desc.slice(0, 80) : ''}`).join('\n')).join('\n');
    try {
      digest = await glm(process.env,
        `以下是今天抓到的新闻标题与摘要，请整理成一份"早安早报"：\n` +
        `1) 开头按日期 ${nowStr(TZ)} 问候一句；\n2) "要闻速览"挑 6 条最重要（中英文源统一中文输出，每条 1-2 句）；\n` +
        `3) "科技/互联网"挑 3 条；\n4) 结尾给一条适合邮轮度假者的轻松提示。\n` +
        `全部纯文本（禁 Markdown），emoji 分节，总长 ≤1100 字。\n\n${raw.slice(0, 7000)}`,
        '你是可靠的新闻编辑。只基于给定素材，不编造。', { temperature: 0.4, max_tokens: 1600 });
    } catch (e) {
      console.log('GLM 失败，降级原始标题：', e.message);
      digest = raw.slice(0, 3000);
    }
  } else {
    digest = '新闻源今天集体抽风，先看看天气吧。';
  }

  const text = `🌅 早安！今日份世界观已装船。\n\n${digest}${wx ? '\n\n' + wx : ''}\n\n—— 发「帮助」看全部玩法，发「继续」追连载 📖`;
  await workerSend(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, text, WHO);
  console.log('早报已推送');
} catch (e) {
  console.error('morning 任务失败：', e);
  process.exit(1);
}
