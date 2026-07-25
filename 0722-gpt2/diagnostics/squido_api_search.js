// Search squido.ai JS chunks for any "API key" mention
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  // Collect all JS chunks
  const jsContents = [];
  page.on('response', async resp => {
    const u = resp.url();
    if (u.endsWith('.js') || u.includes('.js?')) {
      try {
        const text = await resp.text();
        jsContents.push({ url: u, text });
      } catch {}
    }
  });

  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  console.log(`Collected ${jsContents.length} JS chunks`);

  // Search for API key / OpenAI-compatible patterns
  const patterns = [
    'api_key', 'apiKey', 'API_KEY', 'api-key',
    'Bearer ', 'Authorization',
    'x-api-key', 'X-API-Key',
    'openai', 'OpenAI',
    'openrouter', 'OpenRouter',
    'pubkey', 'publishableKey',
    // squido API patterns
    'api.squido.ai', 'squido.ai/api',
  ];

  for (const { url, text } of jsContents) {
    for (const p of patterns) {
      if (text.includes(p)) {
        const idx = text.indexOf(p);
        const ctx = text.substring(Math.max(0, idx - 80), idx + 200).replace(/\n/g, ' ');
        console.log(`\n[${url.split('/').pop()}] pattern "${p}":`);
        console.log(`  ...${ctx}...`);
      }
    }
  }
  await browser.close();
})();
