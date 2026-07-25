// Find the actual submit-to-squido API call structure
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  // Collect POST requests to api.squido.ai
  const apiPosts = [];
  page.on('request', req => {
    if (req.url().includes('api.squido.ai') && req.method() === 'POST') {
      apiPosts.push({
        url: req.url(),
        method: req.method(),
        body: req.postData()?.substring(0, 1000),
        headers: Object.fromEntries(Object.entries(req.headers()).filter(([k]) => !k.startsWith('sec-') && k !== 'cookie' && k !== 'authorization')),
      });
    }
  });
  page.on('response', async resp => {
    if (resp.url().includes('api.squido.ai') && resp.request().method() === 'POST') {
      try {
        const body = await resp.text();
        apiPosts.push({
          type: 'response',
          url: resp.url(),
          status: resp.status(),
          body: body.substring(0, 500),
        });
      } catch {}
    }
  });

  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Get all JS chunks and search for the submit-to-squido API call code
  const jsChunks = [];
  page.on('response', async resp => {
    if (resp.url().endsWith('.js')) {
      try {
        const text = await resp.text();
        jsChunks.push({ url: resp.url(), text });
      } catch {}
    }
  });

  // Re-load to capture chunks
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  console.log(`Captured ${jsChunks.length} JS chunks`);
  console.log(`Captured ${apiPosts.length} api.squido.ai POST calls\n`);

  // Find code that calls api.squido.ai/v1/image
  for (const { url, text } of jsChunks) {
    // Look for fetch("https://api.squido.ai/v1/image" or similar
    const patterns = [
      /fetch\(["'`](https?:\/\/api\.squido\.ai[^"'`]+)["'`]/g,
      /fetch\(["'`](\/v1\/image[^"'`]*)["'`]/g,
    ];
    for (const pat of patterns) {
      let m;
      while ((m = pat.exec(text)) !== null) {
        const ctx = text.substring(Math.max(0, m.index - 200), m.index + 600);
        console.log(`\n=== Found fetch in ${url.split('/').pop()} ===`);
        console.log(ctx);
        console.log('---');
      }
    }
  }

  await browser.close();
})();
