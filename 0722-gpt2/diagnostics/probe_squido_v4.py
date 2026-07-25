#!/usr/bin/env python3
"""Look for the actual auth URL pattern in JS chunks by searching for
context around 'sign-in', 'sign-up', 'log-in' strings."""
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

# Get all JS chunks from homepage
s, b = fetch("https://squido.ai/")
html = b.decode(errors="replace")
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
js_urls = [j if j.startswith("http") else "https://squido.ai" + j for j in js_files]
print(f"Found {len(js_urls)} JS chunks")

# Also fetch JS chunks from the image-generator page
s, b = fetch("https://squido.ai/ai-image-generator")
html2 = b.decode(errors="replace")
js_files2 = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html2)
js_urls2 = [j if j.startswith("http") else "https://squido.ai" + j for j in js_files2]
print(f"Image-gen page adds {len(set(js_urls2) - set(js_urls))} more chunks")

# Combine all chunks and search for auth URL patterns
all_js = js_urls + list(set(js_urls2) - set(js_urls))

# Patterns to search for
patterns = [
    (r'["\'`](/sign-in[^"\'`]*)["\'`]', "sign-in path"),
    (r'["\'`](/sign-up[^"\'`]*)["\'`]', "sign-up path"),
    (r'["\'`](/login[^"\'`]*)["\'`]', "login path"),
    (r'["\'`](/register[^"\'`]*)["\'`]', "register path"),
    (r'["\'`](/auth/[^"\'`]*)["\'`]', "auth path"),
    (r'["\'`](/api/[a-zA-Z0-9_\-\/]+)["\'`]', "any /api/ path"),
    (r'["\'`](https://[^"\'`]*clerk[^"\'`]*)["\'`]', "clerk URL"),
    (r'["\'`](https://[^"\'`]*auth0[^"\'`]*)["\'`]', "auth0 URL"),
    (r'["\'`](https://[^"\'`]*supabase[^"\'`]*)["\'`]', "supabase URL"),
    (r'["\'`](https://[^"\'`]*firebase[^"\'`]*)["\'`]', "firebase URL"),
    (r'["\'`](https://[^"\'`]*googleusercontent[^"\'`]*)["\'`]', "googleusercontent"),
    (r'["\'`](https://[^"\'`]*accounts.google[^"\'`]*)["\'`]', "accounts.google"),
    (r'["\'`](https://[^"\'`]*github.com/login[^"\'`]*)["\'`]', "github login"),
    (r'fetch\(["\'`]([^"\'`]+)["\'`]', "fetch() URL"),
    (r'axios\.(?:get|post|put|delete)\(["\'`]([^"\'`]+)["\'`]', "axios call"),
    (r'["\'`]https?://api\.squido\.ai[^"\'`]*["\'`]', "api.squido.ai"),
    (r'["\'`]https?://[a-z\-]+\.squido\.ai[^"\'`]*["\'`]', "any squido subdomain"),
]

results = {p[1]: set() for p in patterns}

for j in all_js:
    s, b = fetch(j)
    if s != 200 or len(b) < 100:
        continue
    text = b.decode(errors="replace")
    for pat, label in patterns:
        for m in re.findall(pat, text):
            results[label].add(m)
        # Also search for context around "sign-in" etc.
        for kw in ["sign-in", "sign_up", "signUp", "signIn", "log-in", "logIn", "log_in"]:
            idx = text.find(kw)
            while idx != -1 and idx < 50000:  # limit
                ctx = text[max(0, idx-100):idx+150]
                # Only print if it looks URL-ish (contains / or url)
                if "/" in ctx[idx-(idx-max(0,idx-100)):idx+150] or "url" in ctx.lower() or "href" in ctx.lower():
                    print(f"  {j.split('/')[-1]} [{kw}]: ...{ctx[:200]}...")
                    break
                idx = text.find(kw, idx+1)

print("\n=== RESULTS ===")
for label, items in results.items():
    if items:
        print(f"\n--- {label} ({len(items)} unique) ---")
        for it in sorted(items)[:20]:
            print(f"  {it}")

# Also: search for "sign-in" string in the chunks to find what URL it builds
print("\n=== Done ===")
