// 晚安包：冷知识 + 谜题提示 + 连载提醒
import { requiredEnv, glm, workerSend, subscriptionOn } from './lib.mjs';

requiredEnv(['CRUISE_WORKER_URL', 'CRUISE_AGENT_KEY', 'GLM_API_KEY']);

try {
  const on = await subscriptionOn(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, 'evening_on');
  if (!on) { console.log('晚安包订阅已关闭，跳过。'); process.exit(0); }

  const fact = await glm(process.env,
    '随机讲一个有趣的冷知识（80 字内），再出一个适合睡前玩的中文谜语（不给答案，让对方猜，回复「猜 xxx」验证）。' +
    '格式：\n🌙 晚间冷知识\n…\n\n🧩 今日谜题\n…',
    null, { temperature: 1.0, max_tokens: 500 });

  const text = `🌆 晚安包来啦。\n\n${fact}\n\n—— 发「继续」追你的连载小说，发「游戏」来玩猜谜 🎲`;
  await workerSend(process.env.CRUISE_WORKER_URL, process.env.CRUISE_AGENT_KEY, text, 'wife');
  console.log('晚安包已推送');
} catch (e) {
  console.error('evening 任务失败：', e);
  process.exit(1);
}
