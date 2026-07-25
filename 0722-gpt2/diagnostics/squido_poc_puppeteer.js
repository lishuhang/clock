// Use puppeteer-core with our installed chromium
process.env.DISPLAY = ':99';
const puppeteer = require('/tmp/node_modules/puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/home/z/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
    headless: false,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--disable-blink-features=AutomationControlled',
      '--window-size=1366,768',
    ],
    env: { ...process.env, DISPLAY: ':99' },
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1366, height: 768 });
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');

  // Stealth: remove webdriver flag
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    window.chrome = { runtime: {} };
  });

  console.log('Loading /ai-image-generator ...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));

  console.log('Clicking "Start for Free"...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const t = btns.find(b => b.textContent.includes('Start for Free'));
    if (t) t.click();
  });
  await new Promise(r => setTimeout(r, 3000));

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
      // React-controlled input — need to use native setter
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, email);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }, d.email);

  await new Promise(r => setTimeout(r, 2000));

  console.log('Waiting up to 60s for Turnstile token (non-headless via Xvfb)...');
  let token = null;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const v = await page.evaluate(() => document.querySelector('input[name="cf-turnstile-response"]')?.value);
    if (v && v.length > 20) {
      token = v;
      console.log(`TOKEN at t+${i+1}s, len=${token.length}`);
      break;
    }
    if (i % 5 === 0) console.log(`  t+${i+1}s: waiting...`);
  }

  if (token) {
    console.log('\n>>> SUCCESS: Non-headless bypassed Turnstile <<<');
    console.log('Clicking Continue...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const t = btns.find(b => b.textContent.trim() === 'Continue' && !b.textContent.includes('Google'));
      if (t) t.click();
    });
    await new Promise(r => setTimeout(r, 8000));

    const afterState = await page.evaluate(() => ({
      url: location.href,
      modal: (document.querySelector('[role="dialog"]') || {}).innerText?.substring(0, 500),
      inputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i => ({ type: i.type, placeholder: i.placeholder, name: i.name })),
    }));
    console.log('After Continue:');
    console.log('  URL:', afterState.url);
    console.log('  Modal:', afterState.modal);
    console.log('  Inputs:', JSON.stringify(afterState.inputs));

    await page.screenshot({ path: '/home/z/my-project/download/puppet-xvfb-after-continue.png' });

    // Save state
    const cookies = await page.cookies();
    require('fs').writeFileSync('/home/z/my-project/download/puppet-xvfb-state.json', JSON.stringify({
      email: d.email,
      emailToken: d.token,
      modalText: afterState.modal,
      modalInputs: afterState.inputs,
      cookies: cookies,
      timestamp: Date.now(),
    }, null, 2));
    console.log(`Cookies saved: ${cookies.length}`);
  } else {
    console.log('\n>>> FAILED: Even non-headless could not bypass Turnstile <<<');
    await page.screenshot({ path: '/home/z/my-project/download/puppet-xvfb-failed.png' });
  }

  await browser.close();
})();
