// Find better-auth's session endpoint and how get-user-info is called
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
  
  // Find the actual fetch call to /api/get-user-info or /api/get-credits
  for (const { url, text } of chunks) {
    let pos = 0;
    while ((pos = text.indexOf('get-user-info', pos)) !== -1) {
      const ctx2 = text.substring(Math.max(0, pos - 500), pos + 500);
      console.log(`\n=== get-user-info in ${url.split('/').pop()} @ ${pos} ===`);
      console.log(ctx2.substring(0, 1000));
      pos += 14;
    }
    pos = 0;
    while ((pos = text.indexOf('get-credits', pos)) !== -1) {
      const ctx2 = text.substring(Math.max(0, pos - 500), pos + 500);
      console.log(`\n=== get-credits in ${url.split('/').pop()} @ ${pos} ===`);
      console.log(ctx2.substring(0, 1000));
      pos += 12;
    }
  }
  await browser.close();
})();
