// Use env passed via process.env
process.env.DISPLAY = ':99';
const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({
    headless: false,
    executablePath: '/home/z/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
  });
  const ctx = await b.newContext({
    viewport: { width: 1366, height: 768 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    locale: 'en-US',
  });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    window.chrome = { runtime: {} };
  });
  const p = await ctx.newPage();
  console.log('Loading squido...');
  await p.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(3000);
  await p.click('button:has-text("Start for Free")');
  await p.waitForTimeout(3000);

  const r = await fetch('https://api.internal.temp-mail.io/api/v3/email/new', {method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}'});
  const d = await r.json();
  console.log('Email:', d.email);
  await p.fill('[role="dialog"] input[type="email"]', d.email);

  console.log('Waiting up to 60s for Turnstile token...');
  let token = null;
  for (let i = 0; i < 60; i++) {
    await p.waitForTimeout(1000);
    const v = await p.evaluate(() => document.querySelector('input[name="cf-turnstile-response"]')?.value);
    if (v && v.length > 20) { token = v; console.log(`TOKEN at t+${i+1}s, len=${token.length}`); break; }
    if (i % 5 === 0) console.log(`  t+${i+1}s: waiting...`);
  }
  if (token) {
    console.log('CLICK Continue');
    await p.click('button:has-text("Continue"):not(:has-text("Google"))').catch(e => console.log('err', e.message));
    await p.waitForTimeout(8000);
    const s = await p.evaluate(() => ({
      url: location.href,
      modal: (document.querySelector('[role="dialog"]')||{}).innerText?.substring(0, 500),
      inputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i=>({type:i.type, placeholder:i.placeholder, name:i.name}))
    }));
    console.log('After:', JSON.stringify(s));
    require('fs').writeFileSync('/home/z/my-project/download/xvfb-state.json', JSON.stringify({email: d.email, emailToken: d.token, ...s}, null, 2));
    await p.screenshot({path: '/home/z/my-project/download/xvfb-after-continue.png'});
    // Save the page's session cookies for later API calls
    const cookies = await ctx.cookies();
    require('fs').writeFileSync('/home/z/my-project/download/xvfb-cookies.json', JSON.stringify(cookies, null, 2));
    console.log('Cookies saved:', cookies.length);
  } else {
    console.log('FAILED - no token');
    await p.screenshot({path: '/home/z/my-project/download/xvfb-failed.png'});
  }
  await b.close();
})();
