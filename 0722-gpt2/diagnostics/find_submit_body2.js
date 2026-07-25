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

  const chunk = chunks.find(c => c.url.includes('8552-'));
  if (!chunk) { console.log('chunk not found'); await browser.close(); return; }
  
  // Find ANY "v1/image" reference
  let pos = 0;
  while ((pos = chunk.text.indexOf('v1/image', pos)) !== -1) {
    console.log(`\n=== v1/image @ ${pos} ===`);
    console.log(chunk.text.substring(Math.max(0, pos - 1200), pos + 500));
    pos += 8;
  }
  await browser.close();
})();
