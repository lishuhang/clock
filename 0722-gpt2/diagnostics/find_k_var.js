const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const chunks = [];
  page.on('response', async (resp) => {
    const ct = resp.headers()['content-type'] || '';
    if (ct.includes('javascript')) {
      try { chunks.push({ url: resp.url(), text: await resp.text() }); } catch {}
    }
  });
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  const chunk = chunks.find(c => c.url.includes('6450-'));
  if (!chunk) { console.log('not found'); await browser.close(); return; }
  
  // Find "k" variable definition that's used as the Turnstile token
  // It's the second useState argument: p] = useState("")... , [b,g]... , [v,w]... , [j,y]... , [C,N]...
  // Looking for the pattern that sets k from Turnstile callback
  
  // Print the whole function around send-email-otp
  const idx = chunk.text.indexOf('send-email-otp');
  console.log('=== Wide context (3000 chars before send-email-otp) ===');
  console.log(chunk.text.substring(Math.max(0, idx - 3000), idx + 1500));
  
  await browser.close();
})();
