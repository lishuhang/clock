#!/usr/bin/env python3
"""Probe the actual /ai-image-generator page and dig through the biggest
JS chunk for API endpoints + auth scheme."""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return 0, {}, str(e).encode()

# 1. /ai-image-generator page
print("=== 1. /ai-image-generator page ===")
s, h, b = fetch("https://squido.ai/ai-image-generator")
print(f"  status={s}, size={len(b)}")
html = b.decode(errors="replace")
# Find inline scripts
scripts = re.findall(r'<script[^>]*>([^<]+)</script>', html)
print(f"  Inline scripts: {len(scripts)}")
for i, sc in enumerate(scripts):
    if len(sc) > 100:
        print(f"  Script #{i} ({len(sc)} chars): {sc[:300]}...")

# Find login/sign-in related links/buttons
print("\n=== 2. Sign-in/up buttons in image-gen page ===")
for pattern in [
    r'href=["\']([^"\']*(?:sign-in|sign-up|login|register|signin|signup)[^"\']*)["\']',
    r'(?:Sign In|Sign Up|Log In|Register|登录|注册|登入|登錄|註冊)',
    r'data-testid=["\'](?:login|signup|signin)["\']',
]:
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        print(f"  Pattern {pattern[:50]}: {matches[:5]}")

# 3. Check the big JS chunks for fetch URLs and auth
print("\n=== 3. Big JS chunk analysis ===")
big_chunks = [
    "/_next/static/chunks/fd9d1056-cf04f469c2bd1074.js",  # 172K
    "/_next/static/chunks/2117-2a2f7cdd29e3b129.js",      # 124K
    "/_next/static/chunks/9666-9501a26a8abd63e1.js",       # 70K
]
all_apis = set()
all_auth_hints = set()
all_supabase = set()
all_firebase = set()
all_third_party = set()

for chunk in big_chunks:
    s, h, b = fetch("https://squido.ai" + chunk)
    if s != 200:
        continue
    text = b.decode(errors="replace")
    print(f"\n  {chunk}  size={len(b)}")
    # API endpoints
    apis = re.findall(r'["\'`](/api/[a-zA-Z0-9_\-\/\.\{\}]+)["\'`]', text)
    for a in apis:
        all_apis.add(a)
    # External API calls
    ext = re.findall(r'["\'`](https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[a-zA-Z0-9_\-\/\.\{\}]*)?)["\'`]', text)
    for e in ext:
        all_third_party.add(e)
    # Auth lib mentions
    for lib in ["next-auth", "NextAuth", "next_auth", "/api/auth/",
                "clerk", "Clerk",
                "supabase", "Supabase", "v1.supabase",
                "firebase", "Firebase",
                "auth0", "Auth0",
                "lucia", "Lucia",
                "better-auth", "BetterAuth",
                "signIn", "signUp", "useSession",
                "credential", "google", "github", "twitter",
                "JwtToken", "jwt_token", "accessToken"]:
        if lib in text:
            all_auth_hints.add(lib)
    # Find specific auth URLs
    auth_urls = re.findall(r'["\'`](/api/auth/[a-zA-Z0-9_\-\/]+)["\'`]', text)
    for a in auth_urls:
        all_apis.add(a)
    # Find supabase URLs
    supa = re.findall(r'(https?://[a-zA-Z0-9\-]+\.supabase[a-zA-Z0-9\-\.\/]*)', text)
    for s in supa:
        all_supabase.add(s)
    # Find firebase URLs
    fb = re.findall(r'(https?://[a-zA-Z0-9\-]+\.firebaseio[a-zA-Z0-9\-\.\/]*)', text)
    for f in fb:
        all_firebase.add(f)

print(f"\n\n=== ALL /api/ paths found across chunks ({len(all_apis)}) ===")
for a in sorted(all_apis):
    print(f"  {a}")

print(f"\n=== Auth library hints ({len(all_auth_hints)}) ===")
for a in sorted(all_auth_hints):
    print(f"  {a}")

print(f"\n=== Supabase URLs ({len(all_supabase)}) ===")
for a in sorted(all_supabase)[:5]:
    print(f"  {a}")

print(f"\n=== Firebase URLs ({len(all_firebase)}) ===")
for a in sorted(all_firebase)[:5]:
    print(f"  {a}")

print(f"\n=== Third-party URLs (top 30) ===")
# Filter to interesting ones
interesting = [t for t in all_third_party if not any(x in t for x in [
    "w3.org", "schema.org", "google.com/recaptcha", "googletagmanager",
    "google-analytics", "facebook.com", "twitter.com", "github.io",
    "tailwindcss.com", "react.dev", "nextjs.org", "vercel.com",
    "youtube.com", "youtu.be", "fonts.google", "gravatar.com",
    "avatar", "icons", "github.com/vercel", "github.com/facebook",
    "wikipedia.org", "jsdelivr", "unpkg", "cdnjs",
])]
for t in sorted(interesting)[:30]:
    print(f"  {t}")
