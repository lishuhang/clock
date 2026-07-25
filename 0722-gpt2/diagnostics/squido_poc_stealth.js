// Try with stealth mode + visible (non-headless) browser to bypass Turnstile
// Some Turnstile configs only pass when running with full browser fingerprints

const { chromium } = require('playwright');
const { stealth } = require('playwright-stealth');

(async () => {
  // Launch with more realistic args (no headless flag → use xvfb if available)
  const browser = await chromium.launch({
    headless: true,  // try headless first; if fails, switch to false + xvfb
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process',
      '--flag-switches-begin', '--flag-switches-end',
      '--disable-dev-shm-usage',
    ],
  });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1366, height: 768 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
    hasTouch: false,
    isMobile: false,
    permissions: ['geolocation'],
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  });

  // Apply stealth to context
  await stealth(context);

  const page = await context.newPage();

  // Capture network
  const apiCalls = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('squido.ai/api/') || u.includes('challenges.cloudflare') || u.includes('turnstile')) {
      apiCalls.push({ type: 'resp', status: resp.status(), url: u.substring(0, 200) });
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
  await page.fill('[role="dialog"] input[type="email"]', tempData.email);

  // Wait up to 60s for Turnstile to populate cf-turnstile-response
  console.log('\nWaiting up to 60s for Turnstile token to populate...');
  let token = null;
  let btnEnabled = false;
  for (let i = 0; i < 60; i++) {
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
      console.log(`  t+${i+1}s: TOKEN POPULATED! (${token.length} chars)`);
      break;
    }
    if (i % 10 === 0) {
      console.log(`  t+${i+1}s: token=null, btnDisabled=${state.btnDisabled}`);
    }
  }

  if (token) {
    console.log(`\nTurnstile token: ${token.substring(0, 80)}...`);

    // Try clicking Continue
    console.log('Clicking Continue...');
    await page.click('button:has-text("Continue"):not(:has-text("Google"))').catch(e => console.log(`  click err: ${e.message}`));
    await page.waitForTimeout(5000);

    // Check what happened
    const afterState = await page.evaluate(() => ({
      url: window.location.href,
      modalText: (document.querySelector('[role="dialog"]') || {}).innerText || '(no modal)',
      modalInputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i => ({ type: i.type, placeholder: i.placeholder })),
    }));
    console.log('\nAfter Continue click:');
    console.log(`  URL: ${afterState.url}`);
    console.log(`  Modal text: ${afterState.modalText.substring(0, 500)}`);
    console.log(`  Modal inputs: ${JSON.stringify(afterState.modalInputs)}`);

    await page.screenshot({ path: '/home/z/my-project/download/squido-after-continue-stealth.png', fullPage: false });
  } else {
    console.log('\n>>> Turnstile did NOT populate token in 60s — stealth mode did NOT bypass Turnstile <<<');
    await page.screenshot({ path: '/home/z/my-project/download/squido-turnstile-blocked.png', fullPage: false });
  }

  // Print recent API calls
  console.log(`\nAPI calls (${apiCalls.length}):`);
  apiCalls.slice(-20).forEach(c => console.log(`  [resp] ${c.status} ${c.url}`));

  await browser.close();

  // Save temp email for later use
  const fs = require('fs');
  fs.writeFileSync('/home/z/my-project/download/temp-email-stealth.json', JSON.stringify(tempData, null, 2));
})();
