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
  // Find what values currentGenType can take
  // Search for "Image", "Video", etc.
  const types = ['Image', 'Video', 'image', 'video'];
  for (const t of types) {
    let pos = 0;
    let count = 0;
    while ((pos = chunk.text.indexOf(`"${t}"`, pos)) !== -1 && count < 5) {
      const ctx = chunk.text.substring(Math.max(0, pos - 150), pos + 200);
      if (ctx.includes('Gen') || ctx.includes('gen') || ctx.includes('current') || ctx.includes('type')) {
        console.log(`\n=== "${t}" @ ${pos} ===`);
        console.log(ctx.substring(0, 350));
        count++;
      }
      pos += t.length + 2;
    }
  }
  
  // Also look for the literal v= call
  const idx = chunk.text.indexOf('"/api/generate/"+v');
  if (idx !== -1) {
    // Look back for v= definition
    console.log('\n=== v = ... (search back from generate call) ===');
    const before = chunk.text.substring(Math.max(0, idx - 3000), idx);
    // Find "v=" assignments
    const vMatches = before.match(/v\s*=\s*[^,;]{1,80}/g);
    if (vMatches) {
      vMatches.slice(-5).forEach(m => console.log(`  ${m.substring(0, 100)}`));
    }
  }
  
  await browser.close();
})();
