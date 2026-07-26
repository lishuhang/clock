"""Find squido's signIn.emailOtp implementation to verify it doesn't need Turnstile."""
import urllib.request
import re

UA = "Mozilla/5.0 Chrome"
r = urllib.request.Request("https://squido.ai/ai-image-generator", headers={"User-Agent": UA})
html = urllib.request.urlopen(r, timeout=15).read().decode(errors='replace')
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
js_urls = [j if j.startswith("http") else "https://squido.ai" + j for j in js_files]

for j in js_urls:
    try:
        r2 = urllib.request.Request(j, headers={"User-Agent": UA})
        text = urllib.request.urlopen(r2, timeout=15).read().decode(errors='replace')
        if "emailOtp" in text:
            print(f"=== Found emailOtp in {j.split('/')[-1]} ===")
            for m in re.finditer(r'emailOtp', text):
                idx = m.start()
                ctx = text[max(0, idx-300):idx+800]
                if 'function' in ctx[200:400] or 'async' in ctx[200:400] or 'post' in ctx.lower() or 'fetch' in ctx.lower():
                    print(f"\n--- @ {idx} ---")
                    print(ctx[:1100])
                    print('---')
                    break
    except Exception as e:
        pass
