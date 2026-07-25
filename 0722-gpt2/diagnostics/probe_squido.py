#!/usr/bin/env python3
"""Investigate squido.ai:
1. What's the registration flow?
2. Is there an API? What endpoints?
3. Is the 6 images/day free tier real?
4. Can it be used without registering an account?
5. What auth scheme does it use?"""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
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

print("=== 1. Homepage ===")
s, h, b = fetch("https://squido.ai")
print(f"Status: {s}, length: {len(b)}")
body = b.decode(errors="replace")
print(f"Final URL headers: Location={h.get('Location', '(none)')}")

# Find auth-related URLs
print("\n=== 2. Auth-related links in HTML ===")
auth_keywords = ["sign-in", "sign-in-up", "sign-up", "login", "register", "auth", "signin", "signup", "api"]
for kw in auth_keywords:
    matches = re.findall(r'(?:href|action|src)=["\']([^"\']*' + re.escape(kw) + r'[^"\']*)["\']', body, re.IGNORECASE)
    if matches:
        print(f"  {kw}: {matches[:3]}")

# Find any inline script that references API endpoints
print("\n=== 3. JS chunks referenced ===")
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', body)
for f in js_files[:10]:
    print(f"  {f}")

# Find any inline JSON data (Next.js __NEXT_DATA__)
print("\n=== 4. Next.js data ===")
m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([^<]+)</script>', body)
if m:
    try:
        data = json.loads(m.group(1))
        # Don't print full thing, just structure
        print(f"  Top keys: {list(data.keys())}")
        if "props" in data:
            print(f"  props keys: {list(data['props'].keys())[:10]}")
    except Exception as e:
        print(f"  parse err: {e}")
else:
    print("  (no __NEXT_DATA__ found)")

# Check for free tier mentions
print("\n=== 5. Free tier mentions ===")
for kw in ["6 credit", "6 张", "6 images", "free", "免费", "credit", "daily", "每日", "Pro", "Premium", "Basic", "$10", "$20"]:
    if kw.lower() in body.lower():
        # Find first context
        idx = body.lower().find(kw.lower())
        ctx = body[max(0, idx-100):idx+200].replace("\n", " ").strip()
        print(f"  '{kw}': ...{ctx[:200]}...")

# Check robots.txt
print("\n=== 6. /robots.txt ===")
s, h, b = fetch("https://squido.ai/robots.txt")
print(f"  Status: {s}")
print(f"  Body: {b[:500].decode(errors='replace')}")

# Try /api endpoint
print("\n=== 7. /api/ probe ===")
for path in ["/api", "/api/v1", "/api/health", "/api/models", "/v1/models", "/api/auth/session", "/api/user", "/api/me", "/api/usage"]:
    s, h, b = fetch("https://squido.ai" + path, headers={"Accept": "application/json"})
    body_str = b[:200].decode(errors="replace").replace("\n", " ")
    print(f"  {path:25s} status={s}  body={body_str[:150]}")
