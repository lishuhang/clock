// Find the EXACT URL squido frontend calls for image generation
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  
  // Capture actual API calls when clicking Create button
  const apiCalls = [];
  page.on('request', req => {
    const u = req.url();
    if (u.includes('/api/') && !u.includes('_next')) {
      apiCalls.push({ method: req.method(), url: u, body: req.postData()?.substring(0, 500) });
    }
  });
  
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // Don't click anything yet - first see what calls happen on load
  console.log("=== API calls on page load ===");
  apiCalls.forEach(c => console.log(`  ${c.method} ${c.url}  body=${c.body || '(none)'}`));
  
  // Get all JS chunks and search for "generate" patterns
  console.log("\n=== Searching JS chunks for generate URL patterns ===");
  const chunks = [];
  page.on('response', async (resp) => {
    const ct = resp.headers()['content-type'] || '';
    if (ct.includes('javascript')) {
      try { chunks.push({ url: resp.url(), text: await resp.text() }); } catch {}
    }
  });
  // Reload to capture chunks
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  
  for (const { url, text } of chunks) {
    // Find /api/generate* URLs
    const matches = text.match(/["'`](\/api\/generate[^"'`]*)["'`]/g);
    if (matches) {
      const unique = [...new Set(matches)];
      for (const m of unique) {
        console.log(`  in ${url.split('/').pop()}: ${m}`);
      }
    }
  }
  
  await browser.close();
})();
