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
  
  // The "claim" button in layout-d3671fb789ffb2bd.js — find its onClick
  const chunk = chunks.find(c => c.url.includes('layout-d3671fb789ffb2bd'));
  if (!chunk) { console.log('layout chunk not found'); await browser.close(); return; }
  
  // Find "Claim your daily" context
  let pos = chunk.text.indexOf('Claim your daily');
  if (pos === -1) { console.log('not found'); await browser.close(); return; }
  
  console.log('=== Claim button context (3000 chars around) ===');
  console.log(chunk.text.substring(Math.max(0, pos - 2500), pos + 1500));
  
  await browser.close();
})();
