// Look at what Turnstile actually POSTs to challenges.cloudflare.com
// The token comes from a POST response, not a frontend calc.
// If we can replicate the POST with the right fingerprint, we may get a token.

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  // Capture ALL turnstile-related requests in detail
  const requests = [];
  page.on('request', req => {
    const u = req.url();
    if (u.includes('challenges.cloudflare.com') || u.includes('turnstile')) {
      requests.push({
        type: 'request',
        method: req.method(),
        url: u,
        headers: req.headers(),
        postData: req.postData()?.substring(0, 1000),
      });
    }
  });
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('challenges.cloudflare.com') || u.includes('turnstile')) {
      requests.push({
        type: 'response',
        status: resp.status(),
        url: u,
      });
    }
  });

  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("Start for Free")');
  await page.waitForTimeout(15000);

  console.log(`Captured ${requests.length} turnstile requests:\n`);
  requests.forEach((r, i) => {
    console.log(`--- ${i+1} ---`);
    if (r.type === 'request') {
      console.log(`[REQ] ${r.method} ${r.url.substring(0, 200)}`);
      if (r.postData) console.log(`  body: ${r.postData.substring(0, 300)}`);
    } else {
      console.log(`[RESP] ${r.status} ${r.url.substring(0, 200)}`);
    }
  });

  await browser.close();
})();
