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
  
  // Find "Claim Reward" button, then find onClick:N definition
  // Search for N=async or function N or let N=
  const patterns = [
    /N\s*=\s*async\s*\(\)\s*=>\s*\{[^}]+\}/,
    /N\s*=\s*async\s*function[^}]+\}/,
    /let\s+N\s*=\s*[^;]+/,
    /const\s+N\s*=\s*[^;]+/,
    /var\s+N\s*=\s*[^;]+/,
  ];
  
  for (const pat of patterns) {
    const m = chunk.text.match(pat);
    if (m) {
      console.log(`=== pattern: ${pat} ===`);
      console.log(m[0].substring(0, 1500));
    }
  }
  
  // Find function N (look for N=async or "async function N")
  const idx = chunk.text.indexOf('Claim Reward');
  if (idx !== -1) {
    // search back for "N=" or "N ="
    const before = chunk.text.substring(Math.max(0, idx - 5000), idx);
    const nm = before.match(/N\s*=\s*[^,;]{1,500}/g);
    if (nm) {
      console.log('\n=== N= matches near Claim Reward (last 3) ===');
      nm.slice(-3).forEach((m, i) => {
        console.log(`\n--- match ${i} ---`);
        console.log(m.substring(0, 800));
      });
    }
  }
  
  await browser.close();
})();
