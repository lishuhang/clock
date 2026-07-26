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
  
  const chunk = chunks.find(c => c.url.includes('layout-d3671fb789ffb2bd'));
  
  // Find "let s=" or "const s=" or "s=async"
  // Look near N=async
  const idx = chunk.text.indexOf('N=async()=>{');
  const before = chunk.text.substring(Math.max(0, idx - 5000), idx);
  
  // Find s= async function or arrow
  const matches = before.match(/s\s*=\s*async[^,;]{1,1000}/g);
  if (matches) {
    console.log(`=== s= matches (last 3) ===`);
    matches.slice(-3).forEach((m, i) => {
      console.log(`\n--- match ${i} ---`);
      console.log(m.substring(0, 1200));
    });
  }
  
  // Also look for fetch("/api/... patterns near here
  console.log('\n=== All /api/ paths in layout chunk ===');
  const apiPaths = chunk.text.match(/["'`](\/api\/[^"'`]+)["'`]/g);
  if (apiPaths) {
    [...new Set(apiPaths)].forEach(p => console.log(`  ${p}`));
  }
  
  await browser.close();
})();
