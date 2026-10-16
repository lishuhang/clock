import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

// 用法: node describe.mjs <png路径> "<提问>"
async function main(imagePath, prompt) {
  const zai = await ZAI.create();
  const b64 = fs.readFileSync(imagePath).toString('base64');
  const ext = imagePath.endsWith('.png') ? 'png' : 'jpeg';
  const messages = [
    {
      role: 'user',
      content: [
        { type: 'text', text: prompt },
        { type: 'image_url', image_url: { url: `data:image/${ext};base64,${b64}` } }
      ]
    }
  ];
  const response = await zai.chat.completions.createVision({
    model: 'glm-4.6v',
    messages,
    thinking: { type: 'disabled' }
  });
  console.log(response.choices?.[0]?.message?.content ?? JSON.stringify(response, null, 2));
}

const [img, p] = process.argv.slice(2);
if (!img) { console.error('usage: node describe.mjs <png> "<prompt>"'); process.exit(1); }
main(img, p || '详细描述这个网页界面：这是AI视频创作平台的什么页面？首屏中央是什么（对话框/画布/列表/表单）？左侧或顶部有哪些导航项？有没有聊天输入框？有没有用户登录态信息？').catch(e => { console.error('ERR', e.message); process.exit(1); });
