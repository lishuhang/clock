// Find the actual sign-up URL by exploring squido.ai
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

  console.log('Loading https://squido.ai/ai-image-generator ...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  // Click "Sign In" or "Sign up" if present
  const signInBtn = await page.$('text=Sign In');
  const signUpBtn = await page.$('text=Sign up');
  const logInBtn = await page.$('text=Log in');
  const getStartedBtn = await page.$('text=Get Started');
  const startCreatingBtn = await page.$('text=Start Creating');
  const tryNowBtn = await page.$('text=Try Now');

  console.log('Button presence:');
  console.log(`  Sign In: ${signInBtn ? 'YES' : 'no'}`);
  console.log(`  Sign up: ${signUpBtn ? 'YES' : 'no'}`);
  console.log(`  Log in: ${logInBtn ? 'YES' : 'no'}`);
  console.log(`  Get Started: ${getStartedBtn ? 'YES' : 'no'}`);
  console.log(`  Start Creating: ${startCreatingBtn ? 'YES' : 'no'}`);
  console.log(`  Try Now: ${tryNowBtn ? 'YES' : 'no'}`);

  // Click "Start Creating" or similar to trigger auth flow
  let clicked = null;
  for (const [name, btn] of [['Start Creating', startCreatingBtn], ['Try Now', tryNowBtn], ['Get Started', getStartedBtn], ['Sign up', signUpBtn], ['Sign In', signInBtn], ['Log in', logInBtn]]) {
    if (btn) {
      console.log(`\nClicking "${name}"...`);
      await btn.click().catch(e => console.log(`  click err: ${e.message}`));
      clicked = name;
      break;
    }
  }

  if (clicked) {
    await page.waitForTimeout(5000);
    console.log(`After click, URL: ${page.url()}`);
    await page.screenshot({ path: '/home/z/my-project/download/squido-after-click.png', fullPage: true });
    console.log('Screenshot saved: /home/z/my-project/download/squido-after-click.png');

    // Check current page for sign-up form
    const pageInfo = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const buttons = Array.from(document.querySelectorAll('button')).slice(0, 20);
      const iframes = Array.from(document.querySelectorAll('iframe'));
      return {
        url: window.location.href,
        title: document.title,
        inputs: inputs.map(i => ({ type: i.type, name: i.name, placeholder: i.placeholder, id: i.id })),
        buttons: buttons.map(b => b.textContent.trim().substring(0, 50)),
        iframes: iframes.map(f => f.src.substring(0, 100)),
        hasTurnstile: !!document.querySelector('[id^="cf-turnstile"], .cf-turnstile'),
        hasTurnstileScript: !!document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]'),
        hasTurnstileGlobal: typeof window.turnstile !== 'undefined',
      };
    });
    console.log('\nPage info after click:');
    console.log(JSON.stringify(pageInfo, null, 2));
  }

  // Also try direct routes
  console.log('\n\n=== Trying direct routes ===');
  for (const path of ['/sign-in', '/sign-up', '/login', '/register', '/auth/sign-in', '/auth/sign-up', '/en/sign-in', '/en/sign-up', '/en/sign-in/email', '/en/sign-up/email', '/zh/sign-in', '/zh/sign-up']) {
    const resp = await page.goto('https://squido.ai' + path, { waitUntil: 'domcontentloaded', timeout: 10000 }).catch(e => null);
    if (resp) {
      const status = resp.status();
      if (status !== 404) {
        console.log(`  ${path}: ${status}  title="${await page.title()}"  url=${page.url()}`);
      }
    }
  }

  await browser.close();
})();
