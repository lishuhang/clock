// Try Firefox — Turnstile detection differs from Chrome
const { firefox } = require('playwright');

(async () => {
  const browser = await firefox.launch({
    headless: true,
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
    viewport: { width: 1366, height: 768 },
    locale: 'en-US',
  });
  const page = await ctx.newPage();

  console.log('Loading squido with Firefox headless...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

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

  // Check webdriver
  const isHeadless = await page.evaluate(() => navigator.webdriver);
  console.log('navigator.webdriver:', isHeadless);

  // Wait for Turnstile
  console.log('Waiting up to 60s for Turnstile token (Firefox)...');
  let token = null;
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(1000);
    const v = await page.evaluate(() => document.querySelector('input[name="cf-turnstile-response"]')?.value);
    if (v && v.length > 20) {
      token = v;
      console.log(`TOKEN at t+${i+1}s, len=${token.length}`);
      break;
    }
    if (i % 10 === 0) console.log(`  t+${i+1}s: waiting...`);
  }

  if (token) {
    console.log('\n>>> Firefox bypassed Turnstile! <<<');
  } else {
    console.log('\n>>> Firefox also blocked <<<');
  }

  await browser.close();
})();
