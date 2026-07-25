#!/usr/bin/env python3
"""Fetch full pricing text for the most promising stations and save raw
text so we can extract precise free tier rules."""
import json
import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, timeout=15):
    h = {"User-Agent": UA, "Accept": "text/html"}
    r = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

def text_only(html):
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

TARGETS = [
    ("playground.com", "https://playground.com/pricing"),
    ("civitai.com", "https://civitai.com/pricing"),
    ("gptimage2.top", "https://gptimage2.top/pricing"),
    ("oimi.ai", "https://oimi.ai/pricing"),
    ("gptimages2.ai", "https://gptimages2.ai/pricing"),
    ("gptimager.com", "https://gptimager.com/pricing"),
    ("squido.ai", "https://squido.ai/pricing"),
    ("glif.app", "https://glif.app/pricing"),
    ("pixae.app", "https://pixae.app/pricing"),
]

results = {}

for name, url in TARGETS:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    s, b = fetch(url)
    if s != 200:
        print(f"  status={s}")
        continue
    text = text_only(b.decode(errors="replace"))
    print(f"  text length: {len(text)}")
    results[name] = text

    # Extract first 3000 chars
    print(f"  First 2500 chars:")
    print(f"  {text[:2500]}")
    print()

# Save full text
with open("/home/z/my-project/download/pricing-full-text.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
