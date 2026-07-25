// Use playwright-extra + stealth plugin (real puppeteer-extra-stealth port)
const { chromium } = require('/tmp/node_modules/playwright-extra');
const stealth = require('/tmp/node_modules/puppeteer-extra-plugin-stealth')();

// Apply stealth plugin
chromium.use(stealth);

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
    ],
  });

  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1366, height: 768 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
  });

  const page = await ctx.newPage();

  console.log('Loading squido with playwright-extra + stealth...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  // Stealth check
  const stealthReport = await page.evaluate(() => ({
    webdriver: navigator.webdriver,
    languages: navigator.languages,
    plugins: navigator.plugins.length,
    chrome: typeof window.chrome,
    webglVendor: (function(){try{const c=document.createElement('canvas').getContext('webgl');return c.getParameter(c.getParameter).toString().substring(0,30)}catch(e){return 'err'}})(),
    permissions: typeof navigator.permissions,
  }));
  console.log('Stealth report:', stealthReport);

  // Click "Start for Free"
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const t = btns.find(b => b.textContent.includes('Start for Free'));
    if (t) t.click();
  });
  await page.waitForTimeout(3000);

  // Create temp email
  const r = await fetch('https://api.internal.temp-mail.io/api/v3/email/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
  });
  const d = await r.json();
  console.log('Email:', d.email);

  // Fill email
  await page.evaluate((email) => {
    const input = document.querySelector('[role="dialog"] input[type="email"]');
    if (input) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, email);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }, d.email);

  console.log('Waiting up to 90s for Turnstile token (playwright-extra stealth)...');
  let token = null;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(1000);
    const v = await page.evaluate(() => document.querySelector('input[name="cf-turnstile-response"]')?.value);
    if (v && v.length > 20) {
      token = v;
      console.log(`TOKEN at t+${i+1}s, len=${token.length}`);
      break;
    }
    if (i % 10 === 0) {
      const ts = await page.evaluate(() => ({
        iframes: document.querySelectorAll('iframe').length,
        tsDiv: document.querySelectorAll('[id^="cf-turnstile"], .cf-turnstile').length,
        tsScript: document.querySelectorAll('script[src*="turnstile"]').length,
      }));
      console.log(`  t+${i+1}s: token=null, dom=${JSON.stringify(ts)}`);
    }
  }

  if (token) {
    console.log('\n>>> SUCCESS: stealth bypassed Turnstile <<<');
    console.log('Clicking Continue...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const t = btns.find(b => b.textContent.trim() === 'Continue' && !b.textContent.includes('Google'));
      if (t) t.click();
    });
    await page.waitForTimeout(8000);

    const after = await page.evaluate(() => ({
      url: location.href,
      modal: (document.querySelector('[role="dialog"]') || {}).innerText?.substring(0, 500),
      inputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i => ({ type: i.type, placeholder: i.placeholder })),
    }));
    console.log('After Continue:', JSON.stringify(after, null, 2));

    await page.screenshot({ path: '/home/z/my-project/download/stealth-after-continue.png' });

    const cookies = await ctx.cookies();
    require('fs').writeFileSync('/home/z/my-project/download/stealth-state.json', JSON.stringify({
      email: d.email, emailToken: d.token, ...after, cookies, timestamp: Date.now(),
    }, null, 2));
    console.log(`Cookies saved: ${cookies.length}`);
  } else {
    console.log('\n>>> FAILED: stealth plugin did NOT bypass Turnstile <<<');
    await page.screenshot({ path: '/home/z/my-project/download/stealth-failed.png' });
  }

  await browser.close();
})();
