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
  if (!chunk) { await browser.close(); return; }
  
  // Find Turnstile component usage
  for (const kw of ['Turnstile', 'onVerify', 'onSuccess', 'sitekey', 'siteKey']) {
    let pos = 0;
    while ((pos = chunk.text.indexOf(kw, pos)) !== -1) {
      const ctx = chunk.text.substring(Math.max(0, pos - 300), pos + 300);
      console.log(`\n=== [${kw} @ ${pos}] ===`);
      console.log(ctx.substring(0, 600));
      pos += kw.length;
    }
  }
  await browser.close();
})();
