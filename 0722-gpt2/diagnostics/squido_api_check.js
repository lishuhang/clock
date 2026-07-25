// Probe squido API endpoints to find any that DON'T require Turnstile
const endpoints = [
  ['GET', '/api/auth/get-session'],
  ['GET', '/api/get-user-info'],
  ['POST', '/api/get-user-info', {}],
  ['POST', '/api/get-credits-by-sign-in', {}],
  ['GET', '/api/auth'],
  ['POST', '/api/auth/send-email-otp', {email: 'test@web-library.net'}],
  // Clerk endpoints
  ['GET', '/v1/client?_is_native=1'],
  ['POST', '/v1/client/sign_ups?_is_native=1', {}],
  ['GET', '/v1/environment'],
];

for (const [method, path, body] of endpoints) {
  const opts = {
    method,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
      'Accept': 'application/json',
      'Origin': 'https://squido.ai',
      'Referer': 'https://squido.ai/ai-image-generator',
    }
  };
  if (body) {
    opts.body = JSON.stringify(body);
    opts.headers['Content-Type'] = 'application/json';
  }
  try {
    const r = await fetch('https://squido.ai' + path, opts);
    const txt = await r.text();
    console.log(`${method} ${path}`);
    console.log(`  status=${r.status}  body=${txt.substring(0, 300).replace(/\n/g, ' ')}`);
  } catch (e) {
    console.log(`${method} ${path} ERR: ${e.message}`);
  }
}
