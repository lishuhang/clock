// Better capture - register response listener BEFORE goto
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  const chunks = [];
  page.on('response', async (resp) => {
    const ct = resp.headers()['content-type'] || '';
    if (ct.includes('javascript') || resp.url().endsWith('.js')) {
      try {
        const text = await resp.text();
        chunks.push({ url: resp.url(), text });
      } catch (e) {}
    }
  });

  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  console.log(`Captured ${chunks.length} chunks`);
  // Find chunk with v1/image submit
  for (const { url, text } of chunks) {
    if (text.includes('v1/image')) {
      // Print all instances
      let idx = 0;
      while ((idx = text.indexOf('v1/image', idx)) !== -1) {
        const ctx = text.substring(Math.max(0, idx - 300), idx + 500);
        console.log(`\n=== ${url.split('/').pop()} [v1/image @ ${idx}] ===`);
        console.log(ctx.replace(/\\n/g, '\n').substring(0, 800));
        idx += 8;
      }
    }
    // Also look for fetch POST to api.squido.ai
    if (text.includes('api.squido.ai')) {
      let idx = 0;
      while ((idx = text.indexOf('api.squido.ai', idx)) !== -1) {
        const ctx = text.substring(Math.max(0, idx - 200), idx + 500);
        console.log(`\n=== ${url.split('/').pop()} [api.squido.ai @ ${idx}] ===`);
        console.log(ctx.substring(0, 700));
        idx += 14;
      }
    }
  }

  await browser.close();
})();
