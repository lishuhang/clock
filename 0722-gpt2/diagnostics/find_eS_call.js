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
  if (!chunk) { console.log('8552 not found'); await browser.close(); return; }
  
  // Look for "/api/generate/" + pattern (string concatenation)
  const matches = chunk.text.match(/["'`](\/api\/[^"'`]+)["'`]/g);
  const unique = matches ? [...new Set(matches)] : [];
  console.log(`=== All /api/ strings in 8552 ===`);
  unique.forEach(m => console.log(`  ${m}`));
  
  // Also look for fetch( patterns
  console.log(`\n=== fetch() calls in 8552 ===`);
  const fetches = chunk.text.match(/fetch\([^)]{1,150}\)/g);
  if (fetches) {
    fetches.slice(0, 20).forEach(f => console.log(`  ${f.substring(0, 200)}`));
  }
  
  await browser.close();
})();
