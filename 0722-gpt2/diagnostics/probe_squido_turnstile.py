#!/usr/bin/env python3
"""Find what 'token' is required by /api/auth/send-email-otp.
Most likely Cloudflare Turnstile — let's confirm by searching JS chunks."""
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, timeout=20):
    h = {"User-Agent": UA}
    r = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

# Get all JS chunks
s, b = fetch("https://squido.ai/")
html = b.decode(errors="replace")
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
js_urls = [j if j.startswith("http") else "https://squido.ai" + j for j in js_files]

# Search each chunk for context around "send-email-otp" and "turnstile"
print("=== Searching for send-email-otp + turnstile context ===")
for j in js_urls:
    s, b = fetch(j)
    if s != 200 or len(b) < 100:
        continue
    text = b.decode(errors="replace")
    # Search for send-email-otp
    for kw in ["send-email-otp", "turnstile", "Turnstile", "cf-turnstile",
               "cf_turnstile", "challenges.cloudflare", "captcha",
               "recaptcha", "hcaptcha"]:
        idx = text.find(kw)
        while idx != -1:
            ctx = text[max(0, idx-200):idx+400]
            print(f"\n--- {j.split('/')[-1]} [{kw}] at idx {idx} ---")
            print(f"  {ctx[:600]}")
            idx = text.find(kw, idx + len(kw))
            if idx > 200000:  # safety limit
                break
