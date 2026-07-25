// Try the full flow on /ai-image-generator:
// 1. Enter email
// 2. Click "Start for Free" button
// 3. See what happens next (Turnstile? OTP? error?)

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

  // Listen for network requests to see what API calls happen
  const apiCalls = [];
  page.on('request', req => {
    if (req.url().includes('squido.ai/api/') || req.url().includes('challenges.cloudflare.com') || req.url().includes('clerk')) {
      apiCalls.push({
        method: req.method(),
        url: req.url().substring(0, 200),
        postData: req.postData() ? req.postData().substring(0, 300) : null,
      });
    }
  });
  page.on('response', resp => {
    if (resp.url().includes('squido.ai/api/') || resp.url().includes('challenges.cloudflare.com') || resp.url().includes('clerk')) {
      apiCalls.push({
        type: 'response',
        status: resp.status(),
        url: resp.url().substring(0, 200),
      });
    }
  });

  console.log('Loading /ai-image-generator ...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Create a temp email first
  console.log('\nCreating temp email via internal.temp-mail.io ...');
  const tempEmailResp = await fetch('https://api.internal.temp-mail.io/api/v3/email/new', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}'
  });
  const tempEmailData = await tempEmailResp.json();
  console.log(`Email: ${tempEmailData.email}`);
  console.log(`Token: ${tempEmailData.token}`);

  // Fill email into the input
  console.log('\nFilling email input...');
  const emailInput = await page.$('input[type="email"]');
  if (emailInput) {
    await emailInput.fill(tempEmailData.email);
    console.log(`  filled with ${tempEmailData.email}`);
  } else {
    console.log('  email input not found');
  }

  // Wait for Turnstile to render after typing
  await page.waitForTimeout(3000);

  // Take screenshot
  await page.screenshot({ path: '/home/z/my-project/download/squido-email-filled.png', fullPage: false });
  console.log('Screenshot: /home/z/my-project/download/squido-email-filled.png');

  // Check if Turnstile appeared
  const turnstileInfo = await page.evaluate(() => {
    const iframes = Array.from(document.querySelectorAll('iframe'));
    return {
      iframeCount: iframes.length,
      iframeSrcs: iframes.map(f => f.src.substring(0, 100)),
      hasTurnstileDiv: !!document.querySelector('[id^="cf-turnstile"], .cf-turnstile'),
      hasTurnstileScript: !!document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]'),
      hasTurnstileGlobal: typeof window.turnstile !== 'undefined',
      hiddenInputs: Array.from(document.querySelectorAll('input[type="hidden"]')).map(i => ({ name: i.name, value: i.value ? i.value.substring(0, 60) : '' })),
    };
  });
  console.log('\nTurnstile info after email fill:');
  console.log(JSON.stringify(turnstileInfo, null, 2));

  // Click "Start for Free" button
  console.log('\nClicking "Start for Free"...');
  const startBtn = await page.$('button:has-text("Start for Free")');
  if (startBtn) {
    await startBtn.click();
    console.log('  clicked');
  } else {
    console.log('  button not found, trying "Sign In"');
    const signInBtn = await page.$('button:has-text("Sign In")');
    if (signInBtn) await signInBtn.click();
  }

  await page.waitForTimeout(5000);

  // What happened?
  console.log(`\nAfter click, URL: ${page.url()}`);
  await page.screenshot({ path: '/home/z/my-project/download/squido-after-start.png', fullPage: false });

  // Check page state
  const afterState = await page.evaluate(() => {
    return {
      url: window.location.href,
      title: document.title,
      // Look for OTP input or any new modal
      hasOtpInput: !!document.querySelector('input[placeholder*="code" i], input[placeholder*="OTP" i], input[name*="otp" i], input[name*="code" i]'),
      bodyText: document.body.innerText.substring(0, 500),
      // Modal/dialog presence
      modals: Array.from(document.querySelectorAll('[role="dialog"], [class*="modal" i], [class*="overlay" i]')).map(m => m.innerText.substring(0, 200)),
    };
  });
  console.log('\nAfter click state:');
  console.log(`  URL: ${afterState.url}`);
  console.log(`  Title: ${afterState.title}`);
  console.log(`  hasOtpInput: ${afterState.hasOtpInput}`);
  console.log(`  Body text (first 500): ${afterState.bodyText}`);
  console.log(`  Modals: ${JSON.stringify(afterState.modals).substring(0, 500)}`);

  // Print API calls
  console.log(`\n\nAPI calls (${apiCalls.length}):`);
  apiCalls.slice(-30).forEach(c => {
    if (c.type === 'response') {
      console.log(`  [resp] ${c.status} ${c.url}`);
    } else {
      console.log(`  [req]  ${c.method} ${c.url}  body=${c.postData || '(none)'}`);
    }
  });

  await browser.close();

  // Save temp email info for later
  const fs = require('fs');
  fs.writeFileSync('/home/z/my-project/download/temp-email-1.json', JSON.stringify(tempEmailData, null, 2));
  console.log(`\nTemp email saved to /home/z/my-project/download/temp-email-1.json`);
})();
