#!/usr/bin/env node
/* Validate the current 345 page's data-only decoding scheme without eval(). */
const fs = require('fs');

function b64decode(s) {
  if (!s) return s;
  const keyStr = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
  let i = 0, ac = 0;
  const out = [];
  do {
    const h1 = keyStr.indexOf(s.charAt(i++));
    const h2 = keyStr.indexOf(s.charAt(i++));
    const h3 = keyStr.indexOf(s.charAt(i++));
    const h4 = keyStr.indexOf(s.charAt(i++));
    const bits = (h1 << 18) | (h2 << 12) | (h3 << 6) | h4;
    const o1 = (bits >> 16) & 0xff;
    const o2 = (bits >> 8) & 0xff;
    const o3 = bits & 0xff;
    if (h3 === 64) out[ac++] = String.fromCharCode(o1);
    else if (h4 === 64) out[ac++] = String.fromCharCode(o1, o2);
    else out[ac++] = String.fromCharCode(o1, o2, o3);
  } while (i < s.length);
  return out.join('');
}

function xorStr(s, key) {
  return Array.from(s, (ch, index) => String.fromCharCode(ch.charCodeAt(0) ^ key.charCodeAt(index % key.length))).join('');
}

function evalConcat(expr) {
  const re = /"([^"]*)"(\.split\(""\)\.reverse\(\)\.join\(""\))?/g;
  let result = '';
  let match;
  while ((match = re.exec(expr)) !== null) {
    result += match[2] ? match[1].split('').reverse().join('') : match[1];
  }
  return result;
}

function parseCurrentParams(html) {
  const vars = {};
  for (const match of html.matchAll(/var\s+(\w+)\s*=\s*([\s\S]*?)\s*;/g)) {
    if (match[2].trim().startsWith('"')) vars[match[1]] = evalConcat(match[2]);
  }
  for (const match of html.matchAll(/(\w+)\s*=\s*"([^"]+)"\s*;/g)) {
    if (vars[match[1]] === undefined) vars[match[1]] = match[2];
  }
  for (let turn = 0; turn < 10; turn += 1) {
    let changed = false;
    for (const match of html.matchAll(/(\w+)\s*=\s*(\w+)\s*;/g)) {
      const [_, target, source] = match;
      if (target !== source && vars[source] && !vars[target]) { vars[target] = vars[source]; changed = true; }
    }
    if (!changed) break;
  }
  const functionMatch = html.match(/function\s+\w+\s*\((\w+)\)\s*\{\s*\1\s*=\s*\1\.split\(""\)\.reverse\(\)\.join\(""\);\s*\1\s*=\s*\w+\(\s*\1\s*,\s*(\w+)\s*\);\s*\1\s*=\s*\1\.replace\(\s*"token="\s*\+\s*(\w+)\s*,\s*"token="\s*\+\s*(\w+)\s*\);\s*\1\s*=\s*\1\.replace\(\s*(\w+)\s*,\s*""\s*\);\s*return\s+\1;\s*\}/);
  const suffixMatch = html.match(/key\s*=\s*key\s*\+\s*"([0-9a-f]{16})"\s*;/);
  if (!functionMatch || !suffixMatch) throw new Error('current decoder shape not found');
  const key = vars[functionMatch[2]];
  const staticToken = vars[functionMatch[3]];
  const dynamicToken = vars[functionMatch[4]];
  if (!key || !staticToken || !dynamicToken) throw new Error('required variables were not resolved');
  return { key, staticToken, dynamicToken, suffix: suffixMatch[1] };
}

function resolveOptionUrl(html, params) {
  const match = html.match(/<option value="([^"]+)">/);
  if (!match) throw new Error('no line option found');
  const reversed = match[1].split('').reverse().join('');
  let decoded = b64decode(xorStr(b64decode(reversed), params.key + params.suffix));
  decoded = decoded.replace(`token=${params.staticToken}`, `token=${params.dynamicToken}`);
  decoded = decoded.replace(params.key, '');
  if (!decoded.startsWith('https://')) throw new Error('decoded URL is not HTTPS');
  return decoded;
}

async function main() {
  const htmlPath = process.argv[2];
  if (!htmlPath) throw new Error('Usage: test_345_current_decoder.js <play-page.html>');
  const html = fs.readFileSync(htmlPath, 'utf8');
  const params = parseCurrentParams(html);
  const url = resolveOptionUrl(html, params);
  const response = await fetch(url, { redirect: 'manual', headers: { Referer: 'https://m.345iptv.com/', 'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)' } });
  console.log(JSON.stringify({ decoded_https: true, dynamic_token_length: params.dynamicToken.length, upstream_status: response.status, has_location: Boolean(response.headers.get('location')) }));
}

main().catch((error) => { console.error(error.message); process.exit(1); });
