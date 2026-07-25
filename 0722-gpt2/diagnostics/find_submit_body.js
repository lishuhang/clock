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

  // Find 8552 chunk and look at full context around the POST
  const chunk = chunks.find(c => c.url.includes('8552-'));
  if (!chunk) { console.log('chunk not found'); await browser.close(); return; }
  
  // Find the POST request — look for the function that builds ev
  const idx = chunk.text.indexOf('api.squido.ai/v1/image"');
  if (idx === -1) { console.log('pattern not found'); await browser.close(); return; }
  
  // Print a wider context
  console.log('=== Wide context (1000 chars before) ===');
  console.log(chunk.text.substring(Math.max(0, idx - 1500), idx + 300));
  
  // Also search for "prompt" "model" "ratio" "duration" — likely body fields
  console.log('\n=== Looking for body field names ===');
  // Find "ev=" definition
  const evMatch = chunk.text.match(/ev\s*=\s*\{[^}]+\}/);
  if (evMatch) console.log('ev object:', evMatch[0]);
  
  // Find "let ev=" or "const ev="
  const evMatch2 = chunk.text.match(/(?:let|const|var)\s+ev\s*=\s*([^;]+);/);
  if (evMatch2) console.log('ev declaration:', evMatch2[0]);
  
  // Find prompt/model/ratio/duration patterns
  for (const field of ['prompt', 'model', 'ratio', 'duration', 'size', 'quality', 'resolution', 'count']) {
    const re = new RegExp(`['"\`]${field}['"\`]\\s*:`, 'g');
    let m;
    let count = 0;
    while ((m = re.exec(chunk.text)) !== null && count < 3) {
      const ctx2 = chunk.text.substring(Math.max(0, m.index - 100), m.index + 200);
      console.log(`\n  [${field}]: ${ctx2.substring(0, 300)}`);
      count++;
    }
  }
  
  await browser.close();
})();
