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
  if (!chunk) { await browser.close(); return; }
  
  // Find ev definition: useMemo
  const m = chunk.text.match(/ev\s*=\s*[^;]*useMemo[^;]+;?\s*[^;]+;/);
  if (m) {
    console.log('=== ev definition ===');
    console.log(m[0].substring(0, 800));
  }
  
  // Find the useMemo that builds ev (generateParams)
  const m2 = chunk.text.match(/(generateParams\s*[:=]\s*\{[^}]+\})/);
  if (m2) {
    console.log('\n=== generateParams object ===');
    console.log(m2[0]);
  }
  
  // Find ev = useMemo
  const m3 = chunk.text.match(/ev\s*=\s*\(0,c\.useMemo\)\(\(\)=>[^;]+/);
  if (m3) {
    console.log('\n=== ev = useMemo ===');
    console.log(m3[0].substring(0, 1000));
  }
  
  // Just search for "ev=" with surrounding context
  let idx = 0;
  while ((idx = chunk.text.indexOf('ev=', idx)) !== -1) {
    // Check if it's the useMemo one
    const ctx2 = chunk.text.substring(Math.max(0, idx - 50), idx + 500);
    if (ctx2.includes('useMemo') || ctx2.includes('prompt') || ctx2.includes('model')) {
      console.log(`\n=== ev= @ ${idx} ===`);
      console.log(ctx2.substring(0, 600));
    }
    idx += 3;
  }
  await browser.close();
})();
