// Deep dive on the Squido auth modal:
// 1. Open the modal
// 2. See what auth options are presented
// 3. Try email + Continue — does it trigger Turnstile or send OTP directly?

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

  // Capture network
  const apiCalls = [];
  page.on('request', req => {
    if (req.url().includes('squido.ai/api/') || req.url().includes('challenges.cloudflare') || req.url().includes('clerk')) {
      apiCalls.push({ type: 'req', method: req.method(), url: req.url().substring(0, 200), postData: req.postData() ? req.postData().substring(0, 500) : null });
    }
  });
  page.on('response', resp => {
    if (resp.url().includes('squido.ai/api/') || resp.url().includes('challenges.cloudflare') || resp.url().includes('clerk')) {
      apiCalls.push({ type: 'resp', status: resp.status(), url: resp.url().substring(0, 200) });
    }
  });

  console.log('Loading /ai-image-generator ...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Click "Start for Free" to open modal
  console.log('Clicking "Start for Free"...');
  await page.click('button:has-text("Start for Free")');
  await page.waitForTimeout(3000);

  // Screenshot the modal
  await page.screenshot({ path: '/home/z/my-project/download/squido-modal-1.png', fullPage: false });
  console.log('Screenshot 1 saved');

  // Examine modal structure
  const modalInfo = await page.evaluate(() => {
    const modal = document.querySelector('[role="dialog"]') || document.querySelector('.cl-modal, [class*="modal" i]');
    if (!modal) return { found: false };
    return {
      found: true,
      text: modal.innerText,
      html: modal.innerHTML.substring(0, 3000),
      inputs: Array.from(modal.querySelectorAll('input')).map(i => ({ type: i.type, name: i.name, placeholder: i.placeholder, id: i.id })),
      buttons: Array.from(modal.querySelectorAll('button')).map(b => b.textContent.trim()),
      iframes: Array.from(modal.querySelectorAll('iframe')).map(f => f.src.substring(0, 150)),
      // Check for Clerk-specific elements
      hasClerkClass: !!modal.querySelector('[class*="clerk" i], [class*="cl-" i]'),
      // Check for Turnstile
      hasTurnstile: !!modal.querySelector('[id^="cf-turnstile"], .cf-turnstile, iframe[src*="challenges.cloudflare.com"]'),
    };
  });
  console.log('\nModal info:');
  console.log(JSON.stringify(modalInfo, null, 2).substring(0, 5000));

  // Create temp email
  console.log('\nCreating temp email...');
  const tempResp = await fetch('https://api.internal.temp-mail.io/api/v3/email/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
  });
  const tempData = await tempResp.json();
  console.log(`Email: ${tempData.email}`);

  // Find email input in modal
  console.log('\nLooking for email input in modal...');
  const emailInput = await page.$('[role="dialog"] input[type="email"], .cl-modal input[type="email"], [class*="modal" i] input[type="email"]');
  if (emailInput) {
    await emailInput.fill(tempData.email);
    console.log(`  filled`);
  } else {
    console.log('  not found, dumping all inputs:');
    const allInputs = await page.$$eval('input', els => els.map(e => ({ type: e.type, name: e.name, placeholder: e.placeholder, id: e.id, className: e.className.substring(0, 80) })));
    console.log(JSON.stringify(allInputs, null, 2));
  }

  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/home/z/my-project/download/squido-modal-2-email.png', fullPage: false });

  // Click "Continue" button (not "Continue with Google")
  console.log('\nLooking for "Continue" button (not Google)...');
  const continueBtns = await page.$$('button:has-text("Continue")');
  console.log(`  Found ${continueBtns.length} Continue buttons`);
  for (let i = 0; i < continueBtns.length; i++) {
    const text = await continueBtns[i].textContent();
    console.log(`  Button ${i}: "${text.trim()}"`);
  }

  // Click the last "Continue" (the email one, not Google)
  if (continueBtns.length > 0) {
    const target = continueBtns[continueBtns.length - 1];
    console.log('Clicking last Continue button...');
    await target.click();
    await page.waitForTimeout(5000);
  }

  await page.screenshot({ path: '/home/z/my-project/download/squido-modal-3-after-continue.png', fullPage: false });

  // Check what happened
  const afterState = await page.evaluate(() => {
    const modal = document.querySelector('[role="dialog"]') || document.querySelector('.cl-modal, [class*="modal" i]');
    return {
      url: window.location.href,
      modalText: modal ? modal.innerText : '(no modal)',
      modalInputs: modal ? Array.from(modal.querySelectorAll('input')).map(i => ({ type: i.type, placeholder: i.placeholder, name: i.name })) : [],
      hasTurnstile: !!document.querySelector('iframe[src*="challenges.cloudflare.com"]'),
      turnstileIframeSrc: (document.querySelector('iframe[src*="challenges.cloudflare.com"]') || {}).src,
    };
  });
  console.log('\nAfter Continue click:');
  console.log(JSON.stringify(afterState, null, 2));

  // Print API calls
  console.log(`\n\nAPI calls (${apiCalls.length}):`);
  apiCalls.forEach(c => {
    if (c.type === 'resp') console.log(`  [resp] ${c.status} ${c.url}`);
    else console.log(`  [req]  ${c.method} ${c.url}  body=${c.postData || '(none)'}`);
  });

  // Save temp email info
  const fs = require('fs');
  fs.writeFileSync('/home/z/my-project/download/temp-email-2.json', JSON.stringify(tempData, null, 2));

  // Don't close browser yet — wait a bit more for any async flows
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/home/z/my-project/download/squido-modal-4-final.png', fullPage: false });

  await browser.close();
})();
