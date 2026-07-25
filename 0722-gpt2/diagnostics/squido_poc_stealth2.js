// Manual stealth — inject scripts to hide automation flags before any page script runs

const { chromium } = require('playwright');

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
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1366, height: 768 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  });

  // Add init script to mask automation signals BEFORE any page JS runs
  await context.addInitScript(() => {
    // 1. Override navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined,
      configurable: true,
    });

    // 2. Add missing plugins
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
      configurable: true,
    });

    // 3. Add missing languages
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
      configurable: true,
    });

    // 4. Mask chrome runtime
    window.chrome = { runtime: {} };

    // 5. Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
    );

    // 6. Mock WebGL vendor
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function (parameter) {
      if (parameter === 37445) return 'Intel Inc.';  // UNMASKED_VENDOR_WEBGL
      if (parameter === 37446) return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL
      return getParameter.call(this, parameter);
    };
  });

  const page = await context.newPage();

  // Network capture
  const apiCalls = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('squido.ai/api/') || u.includes('challenges.cloudflare') || u.includes('turnstile')) {
      apiCalls.push({ type: 'resp', status: resp.status(), url: u.substring(0, 200), t: Date.now() });
    }
  });

  console.log('Loading /ai-image-generator with stealth...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Verify stealth is working
  const stealthCheck = await page.evaluate(() => ({
    webdriver: navigator.webdriver,
    plugins: navigator.plugins.length,
    languages: navigator.languages,
    chrome: typeof window.chrome,
  }));
  console.log('Stealth check:', stealthCheck);

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
  await page.fill('[role="dialog"] input[type="email"]', tempData.email);

  // Wait up to 90s for Turnstile token (longer with stealth)
  console.log('\nWaiting up to 90s for Turnstile token...');
  let token = null;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(1000);
    const state = await page.evaluate(() => {
      const hidden = document.querySelector('input[name="cf-turnstile-response"]');
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Continue');
      return {
        tokenValue: hidden ? hidden.value : null,
        btnDisabled: btn ? btn.disabled : null,
      };
    });
    if (state.tokenValue && state.tokenValue.length > 20) {
      token = state.tokenValue;
      console.log(`\n  t+${i+1}s: TOKEN POPULATED! len=${token.length}`);
      console.log(`  token preview: ${token.substring(0, 100)}`);
      break;
    }
    if (i % 10 === 0) {
      console.log(`  t+${i+1}s: token=null, btnDisabled=${state.btnDisabled}`);
    }
  }

  if (token) {
    console.log('\n>>> SUCCESS: Stealth bypassed Turnstile <<<');
    console.log('Clicking Continue...');
    await page.click('button:has-text("Continue"):not(:has-text("Google"))').catch(e => console.log(`  click err: ${e.message}`));
    await page.waitForTimeout(8000);

    // Check OTP form
    const afterState = await page.evaluate(() => ({
      url: window.location.href,
      modalText: (document.querySelector('[role="dialog"]') || {}).innerText || '(no modal)',
      modalInputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i => ({ type: i.type, placeholder: i.placeholder, name: i.name })),
    }));
    console.log('\nAfter Continue click:');
    console.log(`  URL: ${afterState.url}`);
    console.log(`  Modal text: ${afterState.modalText.substring(0, 500)}`);
    console.log(`  Modal inputs: ${JSON.stringify(afterState.modalInputs)}`);

    await page.screenshot({ path: '/home/z/my-project/download/squido-after-stealth-continue.png', fullPage: false });

    // Save state for next step
    const fs = require('fs');
    fs.writeFileSync('/home/z/my-project/download/squido-state-after-continue.json', JSON.stringify({
      email: tempData.email,
      emailToken: tempData.token,
      modalText: afterState.modalText,
      modalInputs: afterState.modalInputs,
      timestamp: Date.now(),
    }, null, 2));
  } else {
    console.log('\n>>> FAILED: Stealth did NOT bypass Turnstile in 90s <<<');
    await page.screenshot({ path: '/home/z/my-project/download/squido-stealth-failed.png', fullPage: false });

    // Check final state
    const finalState = await page.evaluate(() => ({
      hidden: document.querySelector('input[name="cf-turnstile-response"]')?.value,
      btn: Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Continue')?.disabled,
      iframes: Array.from(document.querySelectorAll('iframe')).map(f => ({ src: f.src.substring(0, 100), w: f.width, h: f.height })),
    }));
    console.log('Final state:', finalState);
  }

  // Print recent API calls
  console.log(`\nAPI calls (${apiCalls.length}, last 20):`);
  apiCalls.slice(-20).forEach(c => console.log(`  ${c.t} [resp] ${c.status} ${c.url}`));

  await browser.close();
})();
