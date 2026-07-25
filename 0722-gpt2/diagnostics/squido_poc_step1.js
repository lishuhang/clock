// Step 1: Test if Playwright headless can pass squido.ai Turnstile
// Just load /sign-up/email and see if Turnstile widget renders + gives a token

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'en-US',
  });
  const page = await context.newPage();

  // Collect console logs and turnstile-related events
  const events = [];
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning' || msg.text().toLowerCase().includes('turnstile')) {
      events.push(`[console.${msg.type()}] ${msg.text()}`);
    }
  });
  page.on('pageerror', err => events.push(`[pageerror] ${err.message}`));

  console.log('Loading https://squido.ai/sign-up/email ...');
  try {
    const resp = await page.goto('https://squido.ai/sign-up/email', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    console.log(`HTTP status: ${resp.status()}`);
    console.log(`Final URL: ${page.url()}`);
  } catch (e) {
    console.log(`goto error: ${e.message}`);
  }

  // Wait a bit for Turnstile to render
  await page.waitForTimeout(5000);

  // Take screenshot to see what rendered
  await page.screenshot({ path: '/home/z/my-project/download/squido-signup-page.png', fullPage: true });
  console.log('Screenshot saved: /home/z/my-project/download/squido-signup-page.png');

  // Check for Turnstile widget presence
  const turnstileInfo = await page.evaluate(() => {
    const iframes = Array.from(document.querySelectorAll('iframe'));
    const turnstileIframes = iframes.filter(f => f.src && f.src.includes('challenges.cloudflare.com'));
    const turnstileDivs = document.querySelectorAll('[id^="cf-turnstile"], .cf-turnstile');
    const turnstileScripts = document.querySelectorAll('script[src*="challenges.cloudflare.com/turnstile"]');
    return {
      totalIframes: iframes.length,
      turnstileIframeCount: turnstileIframes.length,
      turnstileIframeSrcs: turnstileIframes.map(f => f.src.substring(0, 100)),
      turnstileDivCount: turnstileDivs.length,
      turnstileScriptCount: turnstileScripts.length,
      hasTurnstileGlobal: typeof window.turnstile !== 'undefined',
      turnstileResponse: window.turnstile ? '[exists]' : '[undefined]',
    };
  });
  console.log('\nTurnstile detection:');
  console.log(JSON.stringify(turnstileInfo, null, 2));

  // Try to get turnstile response token
  let turnstileToken = null;
  try {
    turnstileToken = await page.evaluate(() => {
      // Find any cf-turnstile widget
      const widgets = document.querySelectorAll('[id^="cf-turnstile"]');
      if (widgets.length > 0 && window.turnstile) {
        const widgetId = widgets[0].getAttribute('data-turnstile-widget-id') || widgets[0].id;
        try {
          return window.turnstile.getResponse(widgetId) || null;
        } catch (e) {
          return `getResponse error: ${e.message}`;
        }
      }
      // Alternative: look for hidden input with cf-turnstile-response
      const hidden = document.querySelector('input[name="cf-turnstile-response"], input[name="cf_turnstile_response"]');
      if (hidden && hidden.value) return hidden.value;
      return null;
    });
  } catch (e) {
    turnstileToken = `eval error: ${e.message}`;
  }
  console.log(`\nTurnstile token: ${turnstileToken ? turnstileToken.substring(0, 80) + '...' : 'NULL'}`);

  // Wait longer for turnstile to complete (it can take 5-15 seconds)
  console.log('\nWaiting 15s for Turnstile to complete...');
  await page.waitForTimeout(15000);

  // Re-check
  turnstileToken = await page.evaluate(() => {
    const hidden = document.querySelector('input[name="cf-turnstile-response"], input[name="cf_turnstile_response"]');
    if (hidden && hidden.value) return hidden.value;
    if (window.turnstile) {
      const widgets = document.querySelectorAll('[id^="cf-turnstile"]');
      for (const w of widgets) {
        try {
          const r = window.turnstile.getResponse(w.id);
          if (r) return r;
        } catch (e) {}
      }
    }
    return null;
  });
  console.log(`After 15s wait, turnstile token: ${turnstileToken ? turnstileToken.substring(0, 80) + '...' : 'NULL'}`);

  // Print events
  console.log(`\nConsole events (${events.length}):`);
  events.slice(-30).forEach(e => console.log(`  ${e}`));

  await browser.close();
})();
