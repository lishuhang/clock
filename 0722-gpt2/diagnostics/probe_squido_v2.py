#!/usr/bin/env python3
"""Better squido probe: fetch pricing page text, find the actual sign-in URL
from the page navigation, and probe larger JS chunks."""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, timeout=20):
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

# 1. Get homepage and find all internal links
print("=== 1. Internal links from homepage ===")
s, h, b = fetch("https://squido.ai/")
html = b.decode(errors="replace")
links = re.findall(r'href=["\']([^"\']+)["\']', html)
internal = sorted(set(l for l in links if l.startswith("/") or l.startswith("https://squido.ai")))
print(f"Found {len(internal)} unique internal links:")
for l in internal[:30]:
    print(f"  {l}")

# 2. Pricing page — find tier details
print("\n=== 2. Pricing page text ===")
s, h, b = fetch("https://squido.ai/pricing")
html = b.decode(errors="replace")
# Strip HTML to get text
text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
text = re.sub(r"<[^>]+>", " ", text)
text = re.sub(r"\s+", " ", text).strip()
# Find pricing-related sections
for kw in ["credit", "free", "Free", "Basic", "Pro", "Premium", "Starter",
           "monthly", "annual", "yearly", "$", "month", "day", "daily",
           "image", "video", "Sora", "GPT", "generate"]:
    indices = [m.start() for m in re.finditer(re.escape(kw), text)]
    for idx in indices[:1]:  # first occurrence only
        ctx = text[max(0, idx-60):idx+200]
        print(f"  [{kw}] ...{ctx[:240]}...")
        print()

# 3. Find which pages exist beyond /pricing
print("\n=== 3. Other likely pages ===")
candidates = ["/en", "/zh", "/cn", "/about", "/faq", "/help", "/contact",
              "/blog", "/tools", "/sora", "/sora-2", "/video", "/image-generation",
              "/text-to-image", "/ai-image", "/generator", "/try",
              "/api/v1/auth", "/api/v1/user", "/api/v1/me", "/api/v1/billing",
              "/api/v1/usage", "/api/v1/quota", "/api/v1/generate",
              "/trpc", "/trpc/user.me", "/trpc/auth.session"]
for p in candidates:
    s, h, b = fetch("https://squido.ai" + p)
    if s != 404:
        body_str = b[:150].decode(errors="replace").replace("\n", " ")
        print(f"  {p:35s} status={s}  body={body_str[:100]}")

# 4. Look at the bigger JS chunks
print("\n=== 4. Bigger JS chunks ===")
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
print(f"Found {len(js_files)} JS files")
for j in js_files[:5]:
    s, h, b = fetch("https://squido.ai" + j if j.startswith("/") else j)
    print(f"  {j[:80]:80s}  size={len(b)}")
    if len(b) > 1000:
        text = b.decode(errors="replace")
        # Find API endpoints
        apis = sorted(set(re.findall(r'["\'`](/api/[a-zA-Z0-9_\-\/\.]+)["\'`]', text)))
        auth_libs_found = []
        for lib in ["next-auth", "NextAuth", "clerk", "Clerk", "supabase", "Supabase",
                    "firebase", "Firebase", "auth0", "Auth0", "lucia", "Lucia",
                    "better-auth", "BetterAuth", "createClient", "signIn", "signUp"]:
            if lib in text:
                auth_libs_found.append(lib)
        if apis:
            print(f"    /api/ paths: {apis[:10]}")
        if auth_libs_found:
            print(f"    auth libs: {auth_libs_found}")
        # Find postgREST / supabase URLs
        supa_urls = sorted(set(re.findall(r'(https?://[a-zA-Z0-9\-]+\.supabase[a-zA-Z0-9\-\.\/]*)', text)))
        if supa_urls:
            print(f"    supabase URLs: {supa_urls[:3]}")
