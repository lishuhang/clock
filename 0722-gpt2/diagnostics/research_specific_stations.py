#!/usr/bin/env python3
"""Verify Playground.com free tier — does it really give GPT Image 2 free?
Also test oimi.ai — does it have ANY free tier or only paid?
Also test gptimage2.top free trial — does it work without credit card?"""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "text/html,application/json"}
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        else:
            data = body.encode()
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return 0, {}, str(e).encode()

# ============ Playground.com — look at API endpoints ============
print("="*60)
print("playground.com")
print("="*60)

# Find all routes in playground
s, h, b = fetch("https://playground.com/")
html = b.decode(errors="replace")
print(f"  homepage size: {len(b)}")
# Look for any login/signup hints
for kw in ["login", "signup", "sign-in", "sign-up", "register", "auth"]:
    matches = re.findall(rf'href=["\']([^"\']*{kw}[^"\']*)["\']', html, re.IGNORECASE)
    if matches:
        print(f"  {kw} links: {matches[:5]}")

# Find JS chunks
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
print(f"  JS chunks: {len(js_files)}")

# ============ oimi.ai — login flow ============
print("\n" + "="*60)
print("oimi.ai")
print("="*60)

s, h, b = fetch("https://oimi.ai/")
html = b.decode(errors="replace")
print(f"  homepage size: {len(b)}")

# Search for login/signup URLs
login_links = re.findall(r'href=["\']([^"\']*(?:login|signin|sign-in|register|signup|sign-up)[^"\']*)["\']', html, re.IGNORECASE)
print(f"  login links: {login_links[:5]}")

# Look at pricing for free tier
# Already know: 体验会员 ¥9.9 — but is there a free tier? Check "登录" page text
s, h, b = fetch("https://oimi.ai/login")
print(f"\n  /login status: {s}, size: {len(b) if s == 200 else 'N/A'}")
if s == 200:
    text = re.sub(r"<script[^>]*>.*?</script>", "", b.decode(errors="replace"), flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Find login-related keywords
    for kw in ["免费", "free", "试用", "trial", "Google", "github", "phone", "手机", "邮箱", "email", "OTP", "验证码", "wechat", "微信"]:
        idx = text.lower().find(kw.lower())
        if idx != -1:
            ctx = text[max(0,idx-80):idx+200]
            print(f"  [{kw}]: {ctx[:250]}")

# ============ gptimage2.top — "free trial" reality ============
print("\n" + "="*60)
print("gptimage2.top")
print("="*60)

s, h, b = fetch("https://gptimage2.top/")
html = b.decode(errors="replace")
print(f"  homepage size: {len(b)}")

# Look for "free trial" / "免费体验" buttons
for kw in ["free trial", "free experience", "免费体验", "免费试用", "free generate", "立即生成", "免费"]:
    idx = html.lower().find(kw.lower())
    if idx != -1:
        ctx = html[max(0,idx-150):idx+300]
        print(f"  [{kw}] at idx {idx}: {ctx[:400]}")
        print()

# Find login URL
login_links = re.findall(r'href=["\']([^"\']*(?:login|signin|sign-in|register|signup|sign-up|auth)[^"\']*)["\']', html, re.IGNORECASE)
print(f"  login links: {login_links[:5]}")

# ============ Test mail.tm account creation rate ============
print("\n" + "="*60)
print("mail.tm rate limit test")
print("="*60)

import time
# Try to create 5 accounts quickly
created = 0
for i in range(5):
    username = f"ratetest{i}{int(time.time())%10000}"
    s, h, b = fetch("https://api.mail.tm/domains?page=1",
                   headers={"Accept": "application/ld+json"})
    if s != 200:
        print(f"  iter {i}: /domains status={s}")
        time.sleep(1)
        continue
    try:
        domains = json.loads(b)
        if "hydra:member" in domains:
            domain = domains["hydra:member"][0]["domain"]
        elif isinstance(domains, list):
            domain = domains[0]["domain"]
        else:
            continue
    except Exception as e:
        print(f"  iter {i}: parse err {e}")
        continue

    email = f"{username}@{domain}"
    s2, h2, b2 = fetch("https://api.mail.tm/accounts", method="POST",
                      body={"address": email, "password": "Test12345!"},
                      headers={"Accept": "application/ld+json"})
    print(f"  iter {i}: {email} → status={s2}")
    if s2 in (200, 201):
        created += 1
    elif s2 == 429:
        print(f"    rate limited! body: {b2[:200].decode(errors='replace')}")
        break
    time.sleep(0.5)

print(f"\n  Created {created}/5 accounts — rate limit OK if 5/5")

# ============ internal.temp-mail.io rate test ============
print("\n" + "="*60)
print("internal.temp-mail.io rate limit test")
print("="*60)
created2 = 0
for i in range(5):
    s, h, b = fetch("https://api.internal.temp-mail.io/api/v3/email/new", method="POST", body={})
    print(f"  iter {i}: status={s}, body={b[:150].decode(errors='replace')}")
    if s == 200:
        created2 += 1
    elif s == 429:
        print(f"    rate limited")
        break
    time.sleep(0.5)
print(f"\n  Created {created2}/5 accounts")
