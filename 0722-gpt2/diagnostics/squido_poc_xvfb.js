// Try NON-headless via xvfb — Turnstile more likely to pass with visible browser
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: false,  // visible via xvfb
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--start-maximized',
    ],
  });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1366, height: 768 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
    extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
  });

  // Light stealth (don't over-mask — Turnstile might detect too much masking)
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'], configurable: true });
    window.chrome = { runtime: {} };
  });

  const page = await context.newPage();

  console.log('Loading /ai-image-generator (non-headless)...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

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

  // Wait for Turnstile to populate
  console.log('\nWaiting up to 60s for Turnstile token (non-headless)...');
  let token = null;
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(1000);
    const tokenVal = await page.evaluate(() => {
      const hidden = document.querySelector('input[name="cf-turnstile-response"]');
      return hidden ? hidden.value : null;
    });
    if (tokenVal && tokenVal.length > 20) {
      token = tokenVal;
      console.log(`\n  t+${i+1}s: TOKEN! len=${token.length}`);
      break;
    }
    if (i % 5 === 0) console.log(`  t+${i+1}s: still waiting...`);
  }

  if (token) {
    console.log('\n>>> SUCCESS: Non-headless bypassed Turnstile <<<');
    console.log('Clicking Continue...');
    await page.click('button:has-text("Continue"):not(:has-text("Google"))').catch(e => console.log(`  err: ${e.message}`));
    await page.waitForTimeout(8000);

    const afterState = await page.evaluate(() => ({
      url: window.location.href,
      modalText: (document.querySelector('[role="dialog"]') || {}).innerText || '(no modal)',
      modalInputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i => ({ type: i.type, placeholder: i.placeholder })),
    }));
    console.log('\nAfter Continue:');
    console.log(`  URL: ${afterState.url}`);
    console.log(`  Modal: ${afterState.modalText.substring(0, 400)}`);
    console.log(`  Inputs: ${JSON.stringify(afterState.modalInputs)}`);

    await page.screenshot({ path: '/home/z/my-project/download/squido-xvfb-otp.png', fullPage: false });

    // Save state
    const fs = require('fs');
    fs.writeFileSync('/home/z/my-project/download/squido-xvfb-state.json', JSON.stringify({
      email: tempData.email,
      emailToken: tempData.token,
      modalText: afterState.modalText,
      modalInputs: afterState.modalInputs,
      timestamp: Date.now(),
    }, null, 2));
    console.log('State saved to /home/z/my-project/download/squido-xvfb-state.json');
  } else {
    console.log('\n>>> FAILED: Non-headless also blocked <<<');
    await page.screenshot({ path: '/home/z/my-project/download/squido-xvfb-failed.png', fullPage: false });
  }

  await browser.close();
})();
