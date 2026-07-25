// Look for "apiKeys" panel mentioned in 8010 chunk — does squido offer user API keys?
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  let foundChunks = [];
  page.on('response', async resp => {
    const u = resp.url();
    if (u.includes('8010-') || u.includes('8052-') || u.includes('8552-') || u.includes('1899-')) {
      foundChunks.push({ url: u, text: await resp.text() });
    }
  });

  await page.goto('https://squido.ai/ai-image-generator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  for (const { url, text } of foundChunks) {
    console.log(`\n=== ${url.split('/').pop()} (size ${text.length}) ===`);
    // Look for "apiKeys" context
    let pos = 0;
    while ((pos = text.indexOf('apiKeys', pos)) !== -1) {
      console.log(`  [apiKeys @${pos}]: ...${text.substring(Math.max(0,pos-100), pos+200).replace(/\s+/g, ' ')}...`);
      pos += 7;
    }
    // Look for "apiKey" context
    pos = 0;
    while ((pos = text.indexOf('apiKey', pos)) !== -1) {
      console.log(`  [apiKey @${pos}]: ...${text.substring(Math.max(0,pos-80), pos+150).replace(/\s+/g, ' ')}...`);
      pos += 6;
    }
    // Look for "v1/image" context
    pos = 0;
    while ((pos = text.indexOf('v1/image', pos)) !== -1) {
      console.log(`  [v1/image @${pos}]: ...${text.substring(Math.max(0,pos-100), pos+300).replace(/\s+/g, ' ')}...`);
      pos += 8;
    }
  }

  await browser.close();
})();
