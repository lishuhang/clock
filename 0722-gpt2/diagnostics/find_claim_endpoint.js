// Search ALL chunks for daily claim / reward API
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
  
  // Search ALL chunks for fetch POST /api/* patterns
  console.log('=== All /api/ paths across ALL chunks ===');
  const allApis = new Set();
  for (const { url, text } of chunks) {
    const matches = text.matchAll(/["'`](\/api\/[a-zA-Z0-9_\-\/]+)["'`]/g);
    for (const m of matches) {
      allApis.add(m[1]);
    }
  }
  [...allApis].sort().forEach(p => console.log(`  ${p}`));
  
  // Also search for "claim" in API path context
  console.log('\n=== API paths containing claim/reward/daily/free ===');
  for (const p of allApis) {
    if (/claim|reward|daily|free|credit|bonus|sign/i.test(p)) {
      console.log(`  ${p}`);
    }
  }
  
  await browser.close();
})();
