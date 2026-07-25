// Find the logic that enables/disables the Continue button
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

  // Search for "Continue" button disabled logic
  for (const { url, text } of chunks) {
    // Look for "turnstile" near "disabled"
    let pos = 0;
    let found = 0;
    while ((pos = text.indexOf('turnstile', pos)) !== -1 && found < 5) {
      // Get surrounding context that includes "disabled" or "Continue"
      const ctx2 = text.substring(Math.max(0, pos - 500), pos + 500);
      if (ctx2.includes('disabled') || ctx2.includes('Continue')) {
        console.log(`\n=== ${url.split('/').pop()} [turnstile @ ${pos}] ===`);
        console.log(ctx2.substring(0, 1000));
        found++;
      }
      pos += 9;
    }
  }
  await browser.close();
})();
