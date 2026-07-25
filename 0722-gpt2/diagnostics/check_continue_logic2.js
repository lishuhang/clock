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
    // Search for send-email-otp references
    let pos = 0;
    while ((pos = text.indexOf('send-email-otp', pos)) !== -1) {
      const ctx = text.substring(Math.max(0, pos - 600), pos + 600);
      console.log(`\n=== ${url.split('/').pop()} [send-email-otp @ ${pos}] ===`);
      console.log(ctx.substring(0, 1200));
      pos += 15;
    }
    // Also look for cf-turnstile-response usage
    pos = 0;
    while ((pos = text.indexOf('cf-turnstile-response', pos)) !== -1) {
      const ctx = text.substring(Math.max(0, pos - 400), pos + 600);
      console.log(`\n=== ${url.split('/').pop()} [cf-turnstile-response @ ${pos}] ===`);
      console.log(ctx.substring(0, 1000));
      pos += 21;
    }
  }
  await browser.close();
})();
