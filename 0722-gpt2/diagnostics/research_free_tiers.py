#!/usr/bin/env python3
"""For each promising station, fetch the pricing page or homepage and
extract the EXACT free tier policy: how many images per day, refresh
schedule, model support (does it include gpt-image-2?)."""
import json
import re
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
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

def text_only(html):
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

TARGETS = [
    ("oimi.ai", "https://oimi.ai", ["/pricing", "/plans"]),
    ("yuntoken.app", "https://yuntoken.app", ["/pricing", "/plans"]),
    ("gptimage2.top", "https://gptimage2.top", ["/pricing", "/plans"]),
    ("gptimages2.ai", "https://gptimages2.ai", ["/pricing", "/plans"]),
    ("gptimager.com", "https://gptimager.com", ["/pricing", "/plans"]),
    ("glif.app", "https://glif.app", ["/pricing", "/plans"]),
    ("pixae.app", "https://pixae.app", ["/pricing", "/plans"]),
    ("ainb.plus", "https://ainb.plus", ["/pricing", "/plans"]),
    ("liuliuqiu.net", "https://liuliuqiu.net", ["/pricing", "/plans"]),
    ("playground.com", "https://playground.com", ["/pricing", "/plans"]),
    ("seaart.ai", "https://seaart.ai", ["/pricing", "/plans"]),
    ("civitai.com", "https://civitai.com", ["/pricing", "/plans"]),
    ("perchance.org", "https://perchance.org", ["/about", "/faq", "/pricing"]),
    ("squido.ai", "https://squido.ai", ["/pricing"]),  # for comparison
]

results = []

for name, base, paths in TARGETS:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    info = {"name": name, "base": base}

    # Try each path
    for path in paths:
        s, h, b = fetch(base + path)
        print(f"  GET {path}: status={s}, len={len(b) if s == 200 else 'N/A'}")
        if s == 200 and len(b) > 1000:
            text = text_only(b.decode(errors="replace"))
            info.setdefault("pricing_text", {})[path] = text[:5000]

            # Extract pricing patterns
            # Look for $X/month, X credits/day, etc.
            price_patterns = re.findall(r'(?:\$|¥|USD|CNY)\s?\d+(?:\.\d+)?(?:\s?/\s?(?:month|year|mo|yr|月|年|day))?', text)
            credit_patterns = re.findall(r'\d+\s*(?:credits?|张|images?|pics?|points?|tokens?)', text, re.IGNORECASE)
            tier_patterns = re.findall(r'(?:Basic|Pro|Premium|Free|Starter|Plus|Max|Hobby)\s*[\d$]?', text)

            info.setdefault("price_mentions", {})[path] = price_patterns[:8]
            info.setdefault("credit_mentions", {})[path] = credit_patterns[:8]
            info.setdefault("tier_mentions", {})[path] = tier_patterns[:8]

            # Look for specific keywords
            for kw in ["daily", "每日", "free", "免费", "lifetime", "永久",
                       "monthly", "每月", "annual", "yearly", "annual",
                       "trial", "试用", "credits", "额度", "image", "张",
                       "gpt-image", "GPT Image", "gpt4o", "dall-e", "sora",
                       "image-2", "image-1"]:
                idx = text.lower().find(kw.lower())
                if idx != -1:
                    ctx = text[max(0, idx-100):idx+250]
                    info.setdefault("keyword_contexts", {}).setdefault(path, []).append({
                        "kw": kw,
                        "ctx": ctx[:300]
                    })
            break
        time.sleep(0.2)

    # Also check homepage if no pricing page found
    if "pricing_text" not in info:
        s, h, b = fetch(base)
        if s == 200:
            text = text_only(b.decode(errors="replace"))[:5000]
            info["homepage_text"] = text
            for kw in ["daily", "每日", "free", "免费", "lifetime", "永久", "credits"]:
                idx = text.lower().find(kw.lower())
                if idx != -1:
                    info.setdefault("home_kw_ctx", []).append({
                        "kw": kw,
                        "ctx": text[max(0,idx-80):idx+200]
                    })

    results.append(info)
    time.sleep(0.3)

# Save
with open("/home/z/my-project/download/stations-free-tier-research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Print human-readable summary
print("\n\n=== FREE TIER EXTRACTS ===\n")
for r in results:
    print(f"\n>>> {r['name']} <<<")
    if "price_mentions" in r:
        for path, prices in r["price_mentions"].items():
            if prices:
                print(f"  Prices on {path}: {prices}")
    if "credit_mentions" in r:
        for path, credits in r["credit_mentions"].items():
            if credits:
                print(f"  Credits on {path}: {credits}")
    if "tier_mentions" in r:
        for path, tiers in r["tier_mentions"].items():
            if tiers:
                print(f"  Tiers on {path}: {tiers}")
    if "keyword_contexts" in r:
        for path, kws in r["keyword_contexts"].items():
            for k in kws[:3]:
                if k["kw"] in ["daily", "每日", "free", "免费", "lifetime", "永久"]:
                    print(f"  [{path}][{k['kw']}]: {k['ctx'][:200]}")
