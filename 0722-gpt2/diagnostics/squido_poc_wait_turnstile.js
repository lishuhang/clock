// Refine: wait for Turnstile to load invisibly, then for the Continue button to enable

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'en-US',
  });
  const page = await context.newPage();

  // Network capture
  const apiCalls = [];
  page.on('request', req => {
    const u = req.url();
    if (u.includes('squido.ai/api/') || u.includes('challenges.cloudflare') || u.includes('clerk') || u.includes('turnstile')) {
      apiCalls.push({ type: 'req', method: req.method(), url: u.substring(0, 250), postData: req.postData() ? req.postData().substring(0, 500) : null, t: Date.now() });
    }
  });
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('squido.ai/api/') || u.includes('challenges.cloudflare') || u.includes('clerk') || u.includes('turnstile')) {
      apiCalls.push({ type: 'resp', status: resp.status(), url: u.substring(0, 250), t: Date.now() });
    }
  });

  console.log('Loading /ai-image-generator ...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  console.log('Clicking "Start for Free"...');
  await page.click('button:has-text("Start for Free")');
  await page.waitForTimeout(3000);

  // Create temp email
  const tempResp = await fetch('https://api.internal.temp-mail.io/api/v3/email/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
  });
  const tempData = await tempResp.json();
  console.log(`Email: ${tempData.email}`);

  // Fill email
  console.log('Filling email input in modal...');
  await page.fill('[role="dialog"] input[type="email"]', tempData.email);

  // Now wait for Turnstile to load (it may be invisible mode)
  console.log('\nWaiting for Turnstile/Cloudflare to load (up to 30s)...');
  let turnstileLoaded = false;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000);
    const ts = await page.evaluate(() => {
      const iframes = Array.from(document.querySelectorAll('iframe'));
      const cfIframe = iframes.find(f => f.src && f.src.includes('challenges.cloudflare.com'));
      const tsScript = document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]');
      const tsGlobal = typeof window.turnstile !== 'undefined';
      const tsDiv = document.querySelector('[id^="cf-turnstile"], .cf-turnstile');
      return {
        cfIframe: cfIframe ? cfIframe.src.substring(0, 150) : null,
        tsScript: !!tsScript,
        tsGlobal: tsGlobal,
        tsDiv: !!tsDiv,
        iframeCount: iframes.length,
      };
    });
    if (i % 5 === 0 || ts.cfIframe || ts.tsScript) {
      console.log(`  t+${i+1}s: ${JSON.stringify(ts)}`);
    }
    if (ts.cfIframe || ts.tsScript) {
      turnstileLoaded = true;
      console.log(`  >>> Turnstile detected at t+${i+1}s`);
      // Don't break — keep waiting for it to complete
    }
  }

  // Final state check
  console.log('\nFinal page state:');
  const finalState = await page.evaluate(() => {
    const iframes = Array.from(document.querySelectorAll('iframe'));
    const continueBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Continue');
    return {
      iframes: iframes.map(f => ({ src: f.src.substring(0, 150), w: f.width, h: f.height, visible: f.offsetParent !== null })),
      continueBtn: continueBtn ? {
        disabled: continueBtn.disabled,
        visible: continueBtn.offsetParent !== null,
        classList: continueBtn.className.substring(0, 200),
      } : null,
      // Check for any cf-turnstile-response hidden inputs
      hiddenInputs: Array.from(document.querySelectorAll('input[type="hidden"]')).map(i => ({ name: i.name, value: i.value.substring(0, 80), id: i.id })),
      // Look for any visible Turnstile widgets
      turnstileWidgets: Array.from(document.querySelectorAll('[id^="cf-turnstile"], .cf-turnstile')).map(w => ({ id: w.id, html: w.innerHTML.substring(0, 200) })),
    };
  });
  console.log(JSON.stringify(finalState, null, 2));

  await page.screenshot({ path: '/home/z/my-project/download/squido-after-wait.png', fullPage: false });

  // Print API calls
  console.log(`\n\nAPI calls (${apiCalls.length}):`);
  apiCalls.forEach(c => {
    if (c.type === 'resp') console.log(`  ${c.t} [resp] ${c.status} ${c.url}`);
    else console.log(`  ${c.t} [req]  ${c.method} ${c.url}  body=${c.postData || '(none)'}`);
  });

  // Save email info
  const fs = require('fs');
  fs.writeFileSync('/home/z/my-project/download/temp-email-3.json', JSON.stringify(tempData, null, 2));

  await browser.close();
})();
