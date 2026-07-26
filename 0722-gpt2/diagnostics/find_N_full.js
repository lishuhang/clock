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
  
  // Find N=async()=>{ ... } and print full body
  const idx = chunk.text.indexOf('N=async()=>{');
  if (idx === -1) { console.log('not found'); await browser.close(); return; }
  
  // Find matching closing brace
  let depth = 0;
  let end = idx;
  for (let i = idx + 12; i < chunk.text.length; i++) {
    if (chunk.text[i] === '{') depth++;
    else if (chunk.text[i] === '}') {
      if (depth === 0) { end = i + 1; break; }
      depth--;
    }
  }
  console.log('=== N function full body ===');
  console.log(chunk.text.substring(idx, Math.min(end + 200, idx + 3000)));
  
  await browser.close();
})();
