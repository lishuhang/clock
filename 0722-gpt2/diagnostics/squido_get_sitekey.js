// Get the Turnstile sitekey by intercepting the actual challenge URL
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  let sitekey = null;
  page.on('request', req => {
    const u = req.url();
    const m = u.match(/0x4AAAAAAC1lQ47ZqOstSFNo|0x4AAAAAA[A-Za-z0-9_-]+/);
    if (m && !sitekey) {
      sitekey = m[0];
      console.log(`Found sitekey in URL: ${m[0]}`);
      console.log(`  full URL: ${u.substring(0, 200)}`);
    }
  });

  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("Start for Free")');
  await page.waitForTimeout(10000); // wait longer for Turnstile widget to load

  // Now look in DOM
  const turnstileInfo = await page.evaluate(() => {
    const iframes = Array.from(document.querySelectorAll('iframe'));
    const tsDivs = Array.from(document.querySelectorAll('[id^="cf-turnstile"], .cf-turnstile, [data-sitekey]'));
    return {
      iframes: iframes.map(f => ({ src: f.src, id: f.id, name: f.name })),
      tsDivs: tsDivs.map(d => ({
        id: d.id,
        className: d.className,
        sitekey: d.getAttribute('data-sitekey'),
        html: d.outerHTML.substring(0, 400),
      })),
      turnstileGlobal: typeof window.turnstile,
      // Look at window.turnstile object
      turnstileKeys: window.turnstile ? Object.keys(window.turnstile) : null,
    };
  });
  console.log('\nTurnstile DOM info:');
  console.log(JSON.stringify(turnstileInfo, null, 2));

  if (sitekey) {
    console.log(`\n>>> SITEKEY: ${sitekey}`);
  }

  await browser.close();
})();
