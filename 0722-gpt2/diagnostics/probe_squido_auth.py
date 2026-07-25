#!/usr/bin/env python3
"""Test whether squido.ai's OTP flow can be triggered with a temp email,
and whether Clerk blocks disposable email domains.

DOES NOT actually create an account yet — just tests the /api/auth/send-email-otp
endpoint with various email formats to see what response we get."""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "application/json"}
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

# 1. Check mail.tm (temp email API service) is reachable
print("=== 1. mail.tm availability ===")
s, h, b = fetch("https://api.mail.tm/")
print(f"  status={s} body={b[:200].decode(errors='replace')}")
s, h, b = fetch("https://api.mail.tm/domains?page=1")
print(f"  /domains status={s} body={b[:300].decode(errors='replace')}")

# 2. Test squido OTP send with various email formats
print("\n=== 2. Squido /api/auth/send-email-otp with various emails ===")
test_emails = [
    # Real-looking but fake (will likely succeed at OTP send, fail at verify)
    ("gmail-realistic", "test.user.87234@gmail.com"),
    ("outlook-realistic", "john.smith.39872@outlook.com"),
    # Disposable email domains
    ("mail.tm",         "test87234@triots.com"),  # mail.tm domain
    ("tempmail",        "test87234@1secmail.com"),
    ("mailinator",      "test87234@mailinator.com"),
    ("guerillamail",    "test87234@guerrillamail.com"),
    ("yopmail",         "test87234@yopmail.com"),
    ("temp-mail.org",   "test87234@temp-mail.org"),
    # Invalid email
    ("invalid",         "not-an-email"),
]

for label, email in test_emails:
    body = {"email": email}
    s, h, b = fetch("https://squido.ai/api/auth/send-email-otp", method="POST", body=body)
    body_str = b[:300].decode(errors="replace").replace("\n", " ")
    print(f"  {label:20s}  status={s}  body={body_str[:250]}")

# 3. Check what the sign-up endpoint expects
print("\n=== 3. /sign-up/email page (look for form fields) ===")
s, h, b = fetch("https://squido.ai/sign-up/email")
if s == 200:
    html = b.decode(errors="replace")
    # Look for form fields
    forms = re.findall(r'<input[^>]+>', html)
    print(f"  status={s}, found {len(forms)} inputs")
    for f in forms[:10]:
        print(f"    {f[:200]}")
    # Also find any inline JS that calls /api/auth
    js_calls = re.findall(r'(/api/auth/[a-zA-Z0-9_\-/]+)', html)
    print(f"  /api/auth calls in HTML: {set(js_calls)}")
else:
    print(f"  status={s}")

# 4. Check Clerk configuration (frontend publishable key)
print("\n=== 4. Clerk publishable key (from JS chunks) ===")
s, b = fetch("https://squido.ai/")
html = b.decode(errors="replace")
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
clerk_keys = set()
for j in js_files[:15]:
    s2, b2 = fetch("https://squido.ai" + j if j.startswith("/") else j)
    if s2 != 200:
        continue
    text = b2.decode(errors="replace")
    # Clerk publishable keys start with "pk_"
    keys = re.findall(r'["\'`](pk_[a-zA-Z0-9_]+)["\'`]', text)
    for k in keys:
        clerk_keys.add(k)
    # Also look for clerk instance URL
    clerk_urls = re.findall(r'["\'`](https://[a-zA-Z0-9\-]+\.clerk\.accounts\.com[^"\'`]*)["\'`]', text)
    for u in clerk_urls:
        print(f"  Clerk URL: {u}")
    # Or "clerk." subdomain references
    clerk_subdomains = re.findall(r'["\'`](https://[a-zA-Z0-9\-]+\.clerk\.[a-zA-Z]+[^"\'`]*)["\'`]', text)
    for u in clerk_subdomains:
        print(f"  Clerk subdomain: {u}")

print(f"\n  Clerk publishable keys found: {clerk_keys}")

# 5. Check if /api/get-user-info or /api/get-credits-by-sign-in respond without auth
print("\n=== 5. Test endpoints without auth ===")
for path in ["/api/get-user-info", "/api/get-credits-by-sign-in", "/api/auth"]:
    s, h, b = fetch("https://squido.ai" + path)
    body_str = b[:200].decode(errors="replace").replace("\n", " ")
    print(f"  GET  {path:35s} status={s}  body={body_str[:150]}")
    s, h, b = fetch("https://squido.ai" + path, method="POST", body={})
    body_str = b[:200].decode(errors="replace").replace("\n", " ")
    print(f"  POST {path:35s} status={s}  body={body_str[:150]}")
