#!/usr/bin/env python3
"""Download all images from the article to 0812-test/images/"""
import os, subprocess, re, urllib.request, ssl

ARTICLE = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/迪士尼都去TikTok抢人了，和优爱腾一样焦虑？.md"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/images"
os.makedirs(OUT_DIR, exist_ok=True)

with open(ARTICLE, encoding="utf-8") as f:
    text = f.read()

# Extract all image URLs
urls = re.findall(r'https://mmbiz\.qpic\.cn/[^)#]+', text)
# Deduplicate preserving order
seen = set()
unique_urls = []
for u in urls:
    if u not in seen:
        seen.add(u)
        unique_urls.append(u)

print(f"Found {len(unique_urls)} unique image URLs")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for i, url in enumerate(unique_urls):
    # Determine extension
    if 'wx_fmt=png' in url:
        ext = '.png'
    elif 'wx_fmt=jpeg' in url:
        ext = '.jpg'
    else:
        ext = '.jpg'
    out_path = os.path.join(OUT_DIR, f"img{i}{ext}")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        print(f"  [{i}] exists, skip")
        continue
    print(f"  [{i}] downloading {url[:60]}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = resp.read()
        with open(out_path, 'wb') as f:
            f.write(data)
        print(f"    -> {len(data)} bytes")
    except Exception as e:
        print(f"    FAIL: {e}")

print("\n=== Downloaded files ===")
for f in sorted(os.listdir(OUT_DIR)):
    sz = os.path.getsize(os.path.join(OUT_DIR, f))
    print(f"  {f}: {sz} bytes")
