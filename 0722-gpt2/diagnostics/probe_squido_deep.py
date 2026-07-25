#!/usr/bin/env python3
"""Deep-dive squido.ai: find sign-in/sign-up, image generation page,
API endpoints hidden in JS bundles."""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    data = body.encode() if isinstance(body, str) else body
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return 0, {}, str(e).encode()

# Probe common auth/product routes
print("=== 1. Common routes ===")
routes = ["/sign-in", "/signin", "/login", "/sign-up", "/signup", "/register",
          "/auth/signin", "/auth/signup", "/auth/login",
          "/generate", "/image", "/images", "/tools/image-generator",
          "/playground", "/app", "/dashboard", "/studio",
          "/pricing", "/plans", "/subscribe",
          "/api/auth/providers", "/api/auth/csrf"]
for r in routes:
    s, h, b = fetch("https://squido.ai" + r)
    final = h.get("Location", "")
    body_str = b[:200].decode(errors="replace").replace("\n", " ")
    # Look for <title> in body
    title_m = re.search(r"<title[^>]*>([^<]+)</title>", b.decode(errors="replace"))
    title = title_m.group(1)[:50] if title_m else "(no title)"
    print(f"  {r:30s} status={s}  redirect={final[:50]:50s}  title={title}")

# Fetch main JS chunk and search for API endpoints
print("\n=== 2. Search main JS chunk for API endpoints ===")
s, h, b = fetch("https://squido.ai/_next/static/chunks/main-app-e79cc41388b9a524.js")
print(f"  main-app.js: status={s}, size={len(b)}")

# Search for /api/ patterns in JS
js_text = b.decode(errors="replace")
api_patterns = re.findall(r'["\'`](/api/[a-zA-Z0-9_\-\/\.]+)["\'`]', js_text)
unique_apis = sorted(set(api_patterns))
print(f"  Unique /api/ paths found: {len(unique_apis)}")
for p in unique_apis[:30]:
    print(f"    {p}")

# Look for fetch / axios calls
fetch_calls = re.findall(r'fetch\(["\'`]([^"\'`]+)["\'`]', js_text)
print(f"\n  fetch() calls: {len(set(fetch_calls))}")
for f in sorted(set(fetch_calls))[:20]:
    print(f"    {f}")

# Look for NextAuth or similar auth libraries
print("\n=== 3. Auth library detection ===")
auth_libs = ["next-auth", "NextAuth", "clerk", "Clerk", "supabase", "Supabase",
             "firebase", "Firebase", "auth0", "Auth0", "lucia", "Lucia",
             "better-auth", "BetterAuth"]
for lib in auth_libs:
    if lib in js_text:
        # Get context
        idx = js_text.find(lib)
        ctx = js_text[max(0, idx-50):idx+150].replace("\n", " ")
        print(f"  {lib}: ...{ctx[:180]}...")

# Also check the homepage HTML for these
s, h, b = fetch("https://squido.ai/")
html = b.decode(errors="replace")
print("\n=== 4. Auth libs in homepage HTML ===")
for lib in auth_libs:
    if lib.lower() in html.lower():
        print(f"  {lib} mentioned in HTML")

# Look for sign-in/sign-up page links specifically
print("\n=== 5. Sign-in/up URLs in HTML ===")
signin_patterns = re.findall(r'href=["\']([^"\']*(?:sign-in|sign-up|login|register|auth)[^"\']*)["\']', html, re.IGNORECASE)
for m in set(signin_patterns)[:10]:
    print(f"  {m}")

# Also look for /pricing or /plans to find tier info
print("\n=== 6. Pricing ===")
s, h, b = fetch("https://squido.ai/pricing")
if s == 200:
    phtml = b.decode(errors="replace")
    # Find pricing tables
    price_matches = re.findall(r'(?:\$|¥|USD|CNY)\s?\d+(?:\.\d+)?(?:\s?/\s?(?:month|year|mo|yr|月|年))?', phtml)
    print(f"  Price mentions: {price_matches[:10]}")
    # Find credit counts
    credit_matches = re.findall(r'\d+\s*(?:credits?|张|images?|pics?)', phtml, re.IGNORECASE)
    print(f"  Credit mentions: {credit_matches[:10]}")
    # Find tier names
    tier_matches = re.findall(r'(?:Basic|Pro|Premium|Free|Starter|Plus|Max)\s*[\d$]?', phtml)
    print(f"  Tier names: {tier_matches[:10]}")
else:
    print(f"  /pricing status={s}")
