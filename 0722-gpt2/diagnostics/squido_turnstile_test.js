// Try alternative: load squido with --headed via xvfb-pipe and check Turnstile widget
// Actually, the issue is: in headless, Turnstile detects and refuses.
// Let's try: 1) load squido's Turnstile widget OURSELVES on a local page
//            2) extract the cf-turnstile-response
//            3) POST to squido's /api/auth/send-email-otp
// This MAY work if squido's backend doesn't check the Referer.

const { chromium } = require('playwright');

(async () => {
  // First, get the squido Turnstile sitekey from page HTML
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.click('button:has-text("Start for Free")');
  await page.waitForTimeout(3000);

  // Get sitekey
  const sitekeyInfo = await page.evaluate(() => {
    const ts = document.querySelector('.cf-turnstile, [id^="cf-turnstile"]');
    if (!ts) return { found: false };
    return {
      found: true,
      sitekey: ts.getAttribute('data-sitekey'),
      action: ts.getAttribute('data-action'),
      appearance: ts.getAttribute('data-appearance'),
      theme: ts.getAttribute('data-theme'),
      innerHTML: ts.innerHTML.substring(0, 300),
      // Also check Turnstile widget ID
      widgetId: ts.getAttribute('data-turnstile-widget-id'),
    };
  });
  console.log('Turnstile widget info:');
  console.log(JSON.stringify(sitekeyInfo, null, 2));

  // Also look for sitekey in network requests
  const scripts = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('script')).map(s => s.src || s.textContent.substring(0, 200)).filter(s => s);
  });
  const turnstileScripts = scripts.filter(s => s.includes('turnstile') || s.includes('0x4AAAA'));
  console.log('\nTurnstile scripts:', turnstileScripts);

  // Look at the actual /turnstile/ HTTP request URL we saw earlier — it has the sitekey
  // From earlier log: 0x4AAAAAAC1lQ47ZqOstSFNo
  // Let's check the HTML for this
  const html = await page.content();
  const m = html.match(/0x4AAAAAAC1lQ47ZqOstSFNo/g);
  console.log(`\nFound sitekey 0x4AAAAAAC1lQ47ZqOstSFNo in HTML: ${m ? m.length + ' times' : '0'}`);

  // Find context around sitekey
  const idx = html.indexOf('0x4AAAAAAC1lQ47ZqOstSFNo');
  if (idx !== -1) {
    console.log('Context:', html.substring(Math.max(0, idx - 200), idx + 100));
  }

  await browser.close();
})();
