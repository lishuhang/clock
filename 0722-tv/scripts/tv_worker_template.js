// TV Monitor Wall · v1.3 — Worker wrapper
// Serves tv-app-v1.3.html as the response body for GET /
// HTML is embedded as a string literal.

const HTML_BODY = `__HTML_BODY_PLACEHOLDER__`;

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': '*',
        },
      });
    }

    if (path === '/' || path === '/index.html' || path === '') {
      return new Response(HTML_BODY, {
        status: 200,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'CDN-Cache-Control': 'no-store',
        },
      });
    }

    if (path === '/favicon.ico') {
      return new Response(null, { status: 204 });
    }

    return new Response('Not Found', { status: 404 });
  },
};
