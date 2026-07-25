#!/usr/bin/env python3
"""Research 2: Comprehensive audit of all known gpt-image-2 relay stations.

For each station, determine:
- Sign-up methods (email OTP / email+password / Google OAuth / GitHub OAuth / phone / none)
- Free tier model (daily refresh / one-time gift / monthly subscription / paid only)
- Free tier generosity (how many gpt-image-2 images per day or per account lifetime)
- API availability (can be called server-side? or only via UI?)
- Anti-bot defenses (Turnstile / reCAPTCHA / Cloudflare Challenge / IP rate limit)

Build on the 2026-07-22 CSV + new sites discovered since.
"""
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

# All known gpt-image-2 relay stations (from CSV + new finds)
STATIONS = [
    # (name, homepage, signup_url_candidates, notes)
    ("keydraw.97api.com", "https://keydraw.97api.com", ["/sign-up", "/sign-up/email", "/api/auth"], "Free Gift Key, no signup needed (DEAD)"),
    ("www.97api.com", "https://www.97api.com", ["/en/register", "/register", "/v1/models", "/pricing"], "Paid gateway, requires API key"),
    ("oimi.ai", "https://oimi.ai", ["/sign-in", "/sign-up", "/login", "/en/sign-in", "/en/sign-up", "/auth/sign-in"], "NextAuth site"),
    ("yuntoken.app", "https://yuntoken.app", ["/sign-in", "/sign-up", "/login", "/register", "/auth/login", "/auth/register"], "$10 free with promo"),
    ("squido.ai", "https://squido.ai", ["/sign-in/email", "/sign-in/email-otp", "/sign-up/email"], "Clerk + Turnstile, 6 credits/day"),
    ("gptimage2.top", "https://gptimage2.top", ["/sign-in", "/sign-up", "/login", "/register"], "Chinese site, ¥0.30/1K"),
    ("grok.17nas.com (maliang)", "https://grok.17nas.com", ["/login", "/register", "/sign-up"], "Maliang, ¥0.2/image, CF Challenge"),
    ("atlascloud.ai", "https://atlascloud.ai", ["/sign-in", "/sign-up", "/login", "/auth/login", "/auth/sign-up"], "$0.009/image, no public free tier mentioned"),
    ("pixae.app", "https://pixae.app", ["/sign-in", "/sign-up", "/login"], "Pixae AI"),
    ("ainb.plus", "https://ainb.plus", ["/sign-in", "/sign-up", "/login"], "NEXUS AI"),
    ("liuliuqiu.net", "https://liuliuqiu.net", ["/sign-in", "/sign-up", "/login"], "溜溜球"),
    ("gptimage2.im", "https://gptimage2.im", ["/sign-in", "/sign-up", "/login"], "$10/month"),
    ("gptimages2.ai", "https://gptimages2.ai", ["/sign-in", "/sign-up", "/login"], "$10/month"),
    ("gptimager.com", "https://gptimager.com", ["/sign-in", "/sign-up", "/login"], "$19.9/month"),
    ("gpt-image-prompt.com", "https://gpt-image-prompt.com", ["/sign-in", "/sign-up", "/login"], "HTTP 451"),
    ("freegpt.im", "https://freegpt.im", ["/sign-in", "/sign-up", "/login"], "CF blocked"),
    ("image.aitool.cfd", "https://image.aitool.cfd", ["/"], "DNS dead"),
    # Additional ones to check (new finds)
    ("aistudio.google.com", "https://aistudio.google.com", ["/"], "Google AI Studio, requires Google login"),
    ("polymath.ai", "https://polymath.ai", ["/sign-in", "/sign-up", "/login"], "Possible candidate"),
    ("fluxlabs.ai", "https://fluxlabs.ai", ["/sign-in", "/sign-up", "/login"], "Possible candidate"),
    ("fal.ai", "https://fal.ai", ["/dashboard", "/login", "/sign-up"], "Known image API"),
    ("replicate.com", "https://replicate.com", ["/sign-in", "/sign-up"], "Known model host"),
    ("huggingface.co", "https://huggingface.co", ["/join", "/login", "/signup"], "Has inference API"),
    ("openrouter.ai", "https://openrouter.ai", ["/sign-in", "/signup", "/auth/login"], "Multi-model router"),
    ("glif.app", "https://glif.app", ["/login", "/signup", "/sign-in", "/auth/login"], "Image generator host"),
    ("seaart.ai", "https://seaart.ai", ["/login", "/signup", "/sign-in"], "AI art site"),
    ("tensor.art", "https://tensor.art", ["/login", "/signup", "/sign-in"], "AI art site"),
    ("civitai.com", "https://civitai.com", ["/login", "/signup", "/sign-in"], "AI art community"),
    ("leonardo.ai", "https://leonardo.ai", ["/login", "/signup", "/sign-in"], "Known image gen"),
    ("ideogram.ai", "https://ideogram.ai", ["/sign-in", "/sign-up", "/login"], "Known image gen"),
    ("playground.com", "https://playground.com", ["/login", "/signup", "/sign-in"], "Known image gen"),
    ("perchance.org", "https://perchance.org", ["/"], "Free AI image, no signup mentioned"),
    ("gemini.google.com", "https://gemini.google.com", ["/"], "Google Gemini (requires Google account)"),
]

results = []

for name, homepage, signup_candidates, notes in STATIONS:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    info = {"name": name, "homepage": homepage, "notes": notes}

    # 1. Fetch homepage
    s, h, b = fetch(homepage)
    info["homepage_status"] = s
    info["homepage_final_url"] = h.get("Location", homepage)
    info["homepage_size"] = len(b)
    homepage_html = b.decode(errors="replace") if s == 200 else ""

    if s == 0 or s >= 500:
        info["reachable"] = False
        info["signup_methods"] = "unreachable"
        info["free_tier"] = "unknown"
        info["antibot"] = "unknown"
        results.append(info)
        continue

    info["reachable"] = True

    # 2. Look for auth-related keywords in homepage HTML
    auth_signals = {
        "google_oauth": bool(re.search(r'accounts\.google\.com/o/oauth2|google.*oauth|signInWithGoogle|clerk.*google', homepage_html, re.IGNORECASE)),
        "github_oauth": bool(re.search(r'github\.com/login/oauth|signInWithGithub', homepage_html, re.IGNORECASE)),
        "phone_otp": bool(re.search(r'phone|sms|手机|短信|验证码|手机号', homepage_html, re.IGNORECASE) and "phone" in homepage_html.lower()),
        "email_password": bool(re.search(r'type=["\']password["\']', homepage_html)),
        "turnstile": "turnstile" in homepage_html.lower() or "cf-turnstile" in homepage_html.lower(),
        "recaptcha": "recaptcha" in homepage_html.lower() or "g-recaptcha" in homepage_html.lower(),
        "hcaptcha": "hcaptcha" in homepage_html.lower() or "h-captcha" in homepage_html.lower(),
        "cloudflare_challenge": "cloudflare" in homepage_html.lower() and ("challenge" in homepage_html.lower() or "cf-mitigated" in homepage_html.lower()),
        "clerk": "clerk" in homepage_html.lower(),
        "nextauth": "next-auth" in homepage_html.lower() or "nextauth" in homepage_html.lower(),
        "supabase": "supabase" in homepage_html.lower(),
        "firebase": "firebase" in homepage_html.lower(),
        "auth0": "auth0" in homepage_html.lower(),
    }
    info["auth_signals_homepage"] = auth_signals

    # 3. Try signup URL candidates
    found_signup = []
    for path in signup_candidates:
        s2, h2, b2 = fetch(homepage + path)
        if s2 == 200 and len(b2) > 1000:
            # Page exists; check what auth methods are mentioned
            sp_html = b2.decode(errors="replace")
            sp_auth = {
                "google_oauth": bool(re.search(r'accounts\.google\.com/o/oauth2|signInWithGoogle', sp_html, re.IGNORECASE)),
                "github_oauth": bool(re.search(r'github\.com/login/oauth|signInWithGithub', sp_html, re.IGNORECASE)),
                "phone_otp": bool(re.search(r'phone|sms|手机|短信|验证码|手机号', sp_html, re.IGNORECASE)),
                "email_password": bool(re.search(r'type=["\']password["\']', sp_html)),
                "email_otp": "otp" in sp_html.lower() or "code" in sp_html.lower() and "email" in sp_html.lower(),
                "turnstile": "turnstile" in sp_html.lower(),
                "recaptcha": "recaptcha" in sp_html.lower(),
                "hcaptcha": "hcaptcha" in sp_html.lower(),
            }
            found_signup.append({"path": path, "status": s2, "auth": sp_auth})
            break  # first match is enough
        elif s2 in (301, 302, 303, 307, 308):
            found_signup.append({"path": path, "status": s2, "redirect": h2.get("Location", "")})

    info["signup_pages"] = found_signup

    # 4. Look for pricing/free tier mentions
    if homepage_html:
        text = text_only(homepage_html)
        free_keywords = ["free", "免费", "freemium", "free tier", "daily", "每日", "credits",
                        "lifetime", "永久", "lifetime access", "one-time"]
        free_mentions = []
        for kw in free_keywords:
            if kw.lower() in text.lower():
                idx = text.lower().find(kw.lower())
                free_mentions.append({"keyword": kw, "context": text[max(0,idx-60):idx+150]})
        info["free_mentions"] = free_mentions[:5]

    # Try /pricing page
    s3, h3, b3 = fetch(homepage + "/pricing")
    if s3 == 200:
        pricing_text = text_only(b3.decode(errors="replace"))
        info["pricing_text_excerpt"] = pricing_text[:1500]
        # Find daily/credit mentions
        for kw in ["daily", "free", "credit", "$", "¥", "month", "year"]:
            idx = pricing_text.lower().find(kw.lower())
            if idx != -1:
                info.setdefault("pricing_highlights", []).append({
                    "keyword": kw,
                    "context": pricing_text[max(0,idx-80):idx+200]
                })
                break

    results.append(info)
    time.sleep(0.3)

# Save
with open("/home/z/my-project/download/gpt-image-2-stations-audit.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n\n=== HIGH-LEVEL SUMMARY ===")
print(f"{'Station':30s} {'Reachable':10s} {'Auth methods detected':40s} {'Anti-bot':30s}")
print("-" * 120)
for r in results:
    if not r.get("reachable"):
        print(f"{r['name']:30s} NO         -                                         -")
        continue
    auth = []
    sigs = r.get("auth_signals_homepage", {})
    if sigs.get("google_oauth"): auth.append("Google")
    if sigs.get("github_oauth"): auth.append("GitHub")
    if sigs.get("phone_otp"): auth.append("Phone")
    if sigs.get("email_password"): auth.append("Email+PW")
    if sigs.get("email_otp"): auth.append("EmailOTP")
    # Check signup pages too
    for sp in r.get("signup_pages", []):
        if isinstance(sp.get("auth"), dict):
            if sp["auth"].get("google_oauth"): auth.append("Google(sp)")
            if sp["auth"].get("github_oauth"): auth.append("GitHub(sp)")
            if sp["auth"].get("phone_otp"): auth.append("Phone(sp)")
            if sp["auth"].get("email_password"): auth.append("Email+Pw(sp)")
            if sp["auth"].get("email_otp"): auth.append("EmailOTP(sp)")
    auth_str = ",".join(sorted(set(auth))) or "?"

    antibot = []
    if sigs.get("turnstile"): antibot.append("Turnstile")
    if sigs.get("recaptcha"): antibot.append("reCAPTCHA")
    if sigs.get("hcaptcha"): antibot.append("hCaptcha")
    if sigs.get("cloudflare_challenge"): antibot.append("CF-Challenge")
    for sp in r.get("signup_pages", []):
        if isinstance(sp.get("auth"), dict):
            if sp["auth"].get("turnstile"): antibot.append("Turnstile(sp)")
            if sp["auth"].get("recaptcha"): antibot.append("reCAPTCHA(sp)")
            if sp["auth"].get("hcaptcha"): antibot.append("hCaptcha(sp)")
    antibot_str = ",".join(sorted(set(antibot))) or "none"

    print(f"{r['name']:30s} YES        {auth_str:40s} {antibot_str:30s}")
