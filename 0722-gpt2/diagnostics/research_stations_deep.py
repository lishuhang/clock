#!/usr/bin/env python3
"""Deep-dive on promising stations: oimi.ai, yuntoken.app, gptimage2.top,
gptimages2.ai, gptimager.com, gpt-image-prompt.com, perchance.org, glif.app,
atlascloud.ai, pixae.app, ainb.plus, liuliuqiu.net, leonardo.ai, ideogram.ai,
playground.com.

For each: find sign-up page, look at actual auth JS, find free tier details,
determine if email-only signup works (no Google/phone required)."""
import json
import re
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
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

def text_only(html):
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# Focus on stations likely to support email-only signup
TARGETS = [
    ("oimi.ai", "https://oimi.ai"),
    ("yuntoken.app", "https://yuntoken.app"),
    ("gptimage2.top", "https://gptimage2.top"),
    ("gptimages2.ai", "https://gptimages2.ai"),
    ("gptimager.com", "https://gptimager.com"),
    ("gpt-image-prompt.com", "https://gpt-image-prompt.com"),
    ("perchance.org", "https://perchance.org"),
    ("glif.app", "https://glif.app"),
    ("atlascloud.ai", "https://atlascloud.ai"),
    ("pixae.app", "https://pixae.app"),
    ("ainb.plus", "https://ainb.plus"),
    ("liuliuqiu.net", "https://liuliuqiu.net"),
    ("leonardo.ai", "https://leonardo.ai"),
    ("ideogram.ai", "https://ideogram.ai"),
    ("playground.com", "https://playground.com"),
    ("seaart.ai", "https://seaart.ai"),
    ("tensor.art", "https://tensor.art"),
    ("civitai.com", "https://civitai.com"),
]

def find_auth_in_page(html):
    """Find all auth-related hints in HTML/JS text."""
    sigs = set()

    # OAuth providers
    if re.search(r'accounts\.google\.com/o/oauth2|signInWithGoogle|"google"|clerk.*google', html, re.IGNORECASE):
        sigs.add("Google OAuth")
    if re.search(r'github\.com/login/oauth|signInWithGithub|"github"', html, re.IGNORECASE):
        sigs.add("GitHub OAuth")
    if re.search(r'api\.twitter\.com/oauth|signInWithTwitter', html, re.IGNORECASE):
        sigs.add("Twitter OAuth")
    if re.search(r'facebook\.com/v\d+\.\d+/oauth|signInWithFacebook', html, re.IGNORECASE):
        sigs.add("Facebook OAuth")
    if re.search(r'appleid\.apple\.com/auth|signInWithApple', html, re.IGNORECASE):
        sigs.add("Apple OAuth")
    if re.search(r'microsoftonline\.com|signInWithMicrosoft', html, re.IGNORECASE):
        sigs.add("Microsoft OAuth")

    # Email/phone/password patterns
    if re.search(r'type=["\']password["\']', html):
        sigs.add("Password field")
    if re.search(r'输入手机|手机号|sms|短信|phone.*verification|phoneNumber', html, re.IGNORECASE):
        sigs.add("Phone OTP/SMS")
    if re.search(r'email.*otp|email.*verification|send.*code|sendCode|send-otp', html, re.IGNORECASE):
        sigs.add("Email OTP")
    if re.search(r'magic.*link|magiclink|sendMagicLink', html, re.IGNORECASE):
        sigs.add("Magic link")

    # Auth libraries
    if re.search(r'clerk\.com|@clerk|__clerk', html, re.IGNORECASE):
        sigs.add("Clerk")
    if re.search(r'next-auth|nextauth|/api/auth/providers', html, re.IGNORECASE):
        sigs.add("NextAuth")
    if re.search(r'supabase', html, re.IGNORECASE):
        sigs.add("Supabase")
    if re.search(r'firebase|firebaseauth', html, re.IGNORECASE):
        sigs.add("Firebase")
    if re.search(r'auth0', html, re.IGNORECASE):
        sigs.add("Auth0")
    if re.search(r'lucia-auth|lucia/lib', html, re.IGNORECASE):
        sigs.add("Lucia")
    if re.search(r'better-auth', html, re.IGNORECASE):
        sigs.add("BetterAuth")

    # CAPTCHA
    if re.search(r'cf-turnstile|challenges\.cloudflare\.com/turnstile', html, re.IGNORECASE):
        sigs.add("Turnstile")
    if re.search(r'g-recaptcha|google\.com/recaptcha', html, re.IGNORECASE):
        sigs.add("reCAPTCHA")
    if re.search(r'hcaptcha|h-captcha', html, re.IGNORECASE):
        sigs.add("hCaptcha")

    # CF Challenge
    if re.search(r'cloudflare.*challenge|cf-mitigated|cf-chl-bypass', html, re.IGNORECASE):
        sigs.add("CF-Challenge")

    return sigs

results = []

for name, base in TARGETS:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    info = {"name": name, "base": base}

    # Get homepage
    s, h, b = fetch(base)
    info["homepage_status"] = s
    if s != 200:
        info["reachable"] = False
        results.append(info)
        continue
    info["reachable"] = True
    homepage_html = b.decode(errors="replace")

    # Find JS chunks
    js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', homepage_html)
    js_urls = [j if j.startswith("http") else (base + j if j.startswith("/") else base + "/" + j) for j in js_files]

    # Combine homepage + first few JS chunks for auth detection
    combined = homepage_html
    js_text_collected = ""
    for j in js_urls[:6]:  # first 6 chunks (the main app ones)
        s2, _h2, b2 = fetch(j)
        if s2 == 200 and len(b2) > 500:
            js_text_collected += b2.decode(errors="replace")[:50000]  # cap each at 50K
    combined += "\n\n" + js_text_collected

    # Find auth signals
    sigs = find_auth_in_page(combined)
    info["auth_signals"] = sorted(sigs)
    print(f"Auth signals: {sorted(sigs)}")

    # Find internal links (for signup/login)
    links = re.findall(r'href=["\']([^"\']+)["\']', homepage_html)
    auth_links = sorted(set(l for l in links if re.search(r'login|sign|auth|register|account', l, re.IGNORECASE)))[:10]
    info["auth_links"] = auth_links
    print(f"Auth-related links: {auth_links[:5]}")

    # Try fetching each auth link to confirm
    for link in auth_links[:5]:
        full = link if link.startswith("http") else (base + link if link.startswith("/") else base + "/" + link)
        s3, _h3, b3 = fetch(full)
        if s3 == 200:
            sp_html = b3.decode(errors="replace")
            sp_sigs = find_auth_in_page(sp_html)
            if sp_sigs:
                print(f"  {link}: {sorted(sp_sigs)}")
                info.setdefault("signup_page_signals", {})[link] = sorted(sp_sigs)
            # Also look for explicit form fields
            inputs = re.findall(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*>', sp_html)
            if inputs:
                print(f"    form inputs: {inputs[:10]}")
                info.setdefault("signup_form_inputs", {})[link] = inputs[:10]
        time.sleep(0.2)

    # Find pricing/free tier info
    s4, _h4, b4 = fetch(base + "/pricing")
    if s4 == 200:
        pricing_text = text_only(b4.decode(errors="replace"))
        # Find free tier mentions
        free_keywords = ["free", "免费", "freemium", "free tier", "daily", "每日",
                        "lifetime", "永久", "credits", "trial", "试用"]
        free_found = []
        for kw in free_keywords:
            idx = pricing_text.lower().find(kw.lower())
            if idx != -1:
                free_found.append({"kw": kw, "ctx": pricing_text[max(0,idx-80):idx+200]})
        if free_found:
            info["free_tier_pricing_page"] = free_found[:3]
            print(f"Pricing free mentions: {[f['kw'] for f in free_found[:5]]}")

    # Look for free tier in homepage
    home_text = text_only(homepage_html)
    for kw in ["free", "免费", "daily", "credits", "trial"]:
        idx = home_text.lower().find(kw.lower())
        if idx != -1:
            info.setdefault("free_tier_homepage", []).append({
                "kw": kw,
                "ctx": home_text[max(0,idx-80):idx+200]
            })
            break

    results.append(info)
    time.sleep(0.3)

# Save
with open("/home/z/my-project/download/stations-deep-audit.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n\n=== DETAILED SUMMARY ===")
print(f"{'Station':25s} {'Auth methods':50s} {'Anti-bot':30s}")
print("-" * 110)
for r in results:
    if not r.get("reachable"):
        print(f"{r['name']:25s} UNREACHABLE")
        continue
    auth = [s for s in r.get("auth_signals", []) if s not in ["Turnstile", "reCAPTCHA", "hCaptcha", "CF-Challenge"]]
    antibot = [s for s in r.get("auth_signals", []) if s in ["Turnstile", "reCAPTCHA", "hCaptcha", "CF-Challenge"]]
    print(f"{r['name']:25s} {','.join(auth):50s} {','.join(antibot) or 'none':30s}")
