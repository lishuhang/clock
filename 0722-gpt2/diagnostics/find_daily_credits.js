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
  
  for (const { url, text } of chunks) {
    for (const kw of ['daily_free_credits', 'dailyFreeCredits', 'claim', 'reward', 'free_credits', 'freeCredits', 'addCredits']) {
      let pos = 0;
      let count = 0;
      while ((pos = text.indexOf(kw, pos)) !== -1 && count < 3) {
        const ctx = text.substring(Math.max(0, pos - 200), pos + 300);
        if (!ctx.includes('data:') && !ctx.includes('label:')) {
          console.log(`\n=== [${kw}] in ${url.split('/').pop()} @ ${pos} ===`);
          console.log(ctx.substring(0, 500));
          count++;
        }
        pos += kw.length;
      }
    }
  }
  await browser.close();
})();
