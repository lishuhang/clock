import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

const M = "/home/z/my-project/materials/下篇-1015/media/media";
const PLAN = [
  ["image9.png",  "小云雀pricing-B"],
  ["image10.png", "LibTV-pricing-A"],
  ["image11.png", "LibTV-pricing-B"],
  ["image12.png","未知平台pricing-C"],
  ["image13.png","未知平台pricing-D"],
  ["image14.png","OiiOii-pricing-A"],
  ["image15.png","OiiOii-pricing-B"],
  ["image16.png","未知平台pricing-E"],
  ["image17.png","未知平台pricing-F"],
];
const PROMPT = (label) => `这是某AI视频/漫剧画布产品的定价/会员方案页截图（预设标签：${label}，若与页面品牌不符请以页面为准）。请仔细读图并回答：
1)页面品牌名/logo是什么？
2)页面上有哪几个档位/方案名（只列名字，不要价格数字）？
3)【重点】逐条列出所有与功能相关的权益/功能点原文，特别是：团队协作、多人同屏/多光标、子账号/成员席位、团队管理、用量/积分管理看板、项目管理、企业版、CLI、MCP、API、私有化、专属服务等。每条注明属于哪个档位。
4)页面里有没有"企业版/团队版/定制"入口或"联系销售"字样？
请如实转写，看不清的条目标注[看不清]。`;

async function main() {
  const zai = await ZAI.create();
  for (const [f, label] of PLAN) {
    const b64 = fs.readFileSync(`${M}/${f}`).toString('base64');
    try {
      const r = await zai.chat.completions.createVision({
        model: 'glm-4.6v',
        messages: [{ role: 'user', content: [
          { type: 'text', text: PROMPT(label) },
          { type: 'image_url', image_url: { url: `data:image/png;base64,${b64}` } }
        ]}],
        thinking: { type: 'disabled' }
      });
      console.log(`\n########## ${f} (${label}) ##########`);
      console.log(r.choices?.[0]?.message?.content ?? 'ERR');
    } catch (e) {
      console.log(`\n########## ${f} (${label}) ##########`);
      console.log('ERR', e.message);
    }
  }
}
main().catch(e => { console.error(e); process.exit(1); });
