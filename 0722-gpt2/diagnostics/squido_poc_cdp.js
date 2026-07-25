// Launch Chrome manually with DISPLAY, then connect via CDP
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');

async function main() {
  const CHROME_PATH = '/home/z/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome';
  const USER_DATA = '/tmp/chrome-squido-profile';
  const CDP_PORT = 9333;

  fs.mkdirSync(USER_DATA, { recursive: true });
  try { fs.unlinkSync(`${USER_DATA}/SingletonLock`); } catch {}

  console.log('Spawning Chrome with DISPLAY=:99...');
  const chromeProc = spawn(CHROME_PATH, [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    `--user-data-dir=${USER_DATA}`,
    `--remote-debugging-port=${CDP_PORT}`,
    '--window-size=1366,768',
    'about:blank',
  ], {
    env: { ...process.env, DISPLAY: ':99' },
    stdio: 'pipe',
  });

  chromeProc.stderr.on('data', d => {
    const s = d.toString();
    if (s.includes('DevTools') || s.includes('listening')) {
      console.log('[chrome stderr]', s.trim());
    }
  });
  chromeProc.on('exit', code => console.log(`Chrome exited with ${code}`));

  console.log('Waiting for CDP...');
  let connected = false;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const r = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`);
      if (r.ok) {
        const data = await r.json();
        console.log('CDP ready:', data.Browser);
        connected = true;
        break;
      }
    } catch {}
  }
  if (!connected) {
    console.log('CDP never came up');
    chromeProc.kill();
    process.exit(1);
  }

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${CDP_PORT}`);
  const ctx = await browser.newContext({
    viewport: { width: 1366, height: 768 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    locale: 'en-US',
  });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    window.chrome = { runtime: {} };
  });

  const page = await ctx.newPage();
  console.log('Loading squido...');
  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  console.log('Clicking "Start for Free"...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const t = btns.find(b => b.textContent.includes('Start for Free'));
    if (t) t.click();
  });
  await page.waitForTimeout(3000);

  const r = await fetch('https://api.internal.temp-mail.io/api/v3/email/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
  });
  const d = await r.json();
  console.log('Email:', d.email);

  await page.evaluate((email) => {
    const input = document.querySelector('[role="dialog"] input[type="email"]');
    if (input) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, email);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }, d.email);

  console.log('Waiting up to 60s for Turnstile token...');
  let token = null;
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(1000);
    const v = await page.evaluate(() => document.querySelector('input[name="cf-turnstile-response"]')?.value);
    if (v && v.length > 20) {
      token = v;
      console.log(`TOKEN at t+${i+1}s, len=${token.length}`);
      break;
    }
    if (i % 5 === 0) console.log(`  t+${i+1}s: waiting...`);
  }

  if (token) {
    console.log('\n>>> SUCCESS: Turnstile bypassed via CDP + Xvfb <<<');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const t = btns.find(b => b.textContent.trim() === 'Continue' && !b.textContent.includes('Google'));
      if (t) t.click();
    });
    await page.waitForTimeout(8000);

    const afterState = await page.evaluate(() => ({
      url: location.href,
      modal: (document.querySelector('[role="dialog"]') || {}).innerText?.substring(0, 500),
      inputs: Array.from(document.querySelectorAll('[role="dialog"] input')).map(i => ({ type: i.type, placeholder: i.placeholder, name: i.name })),
    }));
    console.log('After Continue:');
    console.log('  URL:', afterState.url);
    console.log('  Modal:', afterState.modal);
    console.log('  Inputs:', JSON.stringify(afterState.inputs));

    await page.screenshot({ path: '/home/z/my-project/download/cdp-xvfb-after-continue.png' });

    const cookies = await ctx.cookies();
    fs.writeFileSync('/home/z/my-project/download/cdp-xvfb-state.json', JSON.stringify({
      email: d.email, emailToken: d.token, ...afterState, cookies, timestamp: Date.now(),
    }, null, 2));
    console.log(`Cookies saved: ${cookies.length}`);
  } else {
    console.log('\n>>> FAILED <<<');
    await page.screenshot({ path: '/home/z/my-project/download/cdp-xvfb-failed.png' });
  }

  await browser.close();
  chromeProc.kill();
}

main().catch(e => { console.error(e); process.exit(1); });
