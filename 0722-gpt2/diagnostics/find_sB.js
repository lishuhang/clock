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
  
  // Find s.B definition (likely an enum)
  for (const { url, text } of chunks) {
    // Look for "Image:" or "Video:" in enum-like definitions
    const m = text.match(/\{[^{}]*Image[^{}]*Video[^{}]*\}/g);
    if (m) {
      for (const match of m) {
        if (match.length < 500) {
          console.log(`\n=== enum in ${url.split('/').pop()} ===`);
          console.log(match.substring(0, 400));
        }
      }
    }
  }
  
  // Also look for "Image=\"Image\"" or similar
  for (const { url, text } of chunks) {
    let pos = 0;
    let count = 0;
    while ((pos = text.indexOf('Image="', pos)) !== -1 && count < 3) {
      const ctx = text.substring(pos, pos + 100);
      console.log(`\n=== Image=" in ${url.split('/').pop()} @ ${pos} ===`);
      console.log(ctx);
      pos += 7;
      count++;
    }
  }
  
  await browser.close();
})();
