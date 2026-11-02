#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gtry.py —— 验证能否从 Google Patents 拉取真实附图与全文 PDF（runner 端）。"""
import os, re, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
nums = ["CN123020788A", "CN122933917A"]

def get(url, timeout=30):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120 Safari/537.36",
         "Accept": "text/html,application/xhtml+xml,*/*"}
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()

out = []
for num in nums:
    # 1) 直接 PDF 候选路径
    for path in (f"/pdfs/CN/{num}.pdf", f"/pdfs/{num}.pdf", f"/pdfs/CN/{num}.PDF"):
        url = "https://patentimages.storage.googleapis.com" + path
        try:
            st, data = get(url)
            head = data[:8]
            ok = head.startswith(b"%PDF")
            out.append(f"{num} PDF({path}): HTTP {st} bytes={len(data)} pdf_magic={ok}")
        except Exception as e:
            out.append(f"{num} PDF({path}): ERR {type(e).__name__}: {e}")
    # 2) 专利页 /en，提取附图 URL
    try:
        st, data = get(f"https://patents.google.com/patent/{num}/en")
        html = data.decode("utf-8", "ignore")
        imgs = re.findall(r'https://patentimages\.storage\.googleapis\.com/[^\s"\'<>]+\.(?:png|jpg|jpeg|gif)', html)
        out.append(f"{num} page /en: HTTP {st} bytes={len(html)} figure_urls={len(imgs)} sample={imgs[:3]}")
    except Exception as e:
        out.append(f"{num} page /en: ERR {type(e).__name__}: {e}")
    # 3) 尝试 Google Patents 的 xhr 取 PDF 直链
    try:
        st, data = get(f"https://patents.google.com/xhr/query?url=" + __import__("urllib.parse").quote(f"q={num}"))
        js = data.decode("utf-8", "ignore")
        pdfs = re.findall(r'https://patentimages\.storage\.googleapis\.com/[^\s"\'<>]+\.pdf', js)
        out.append(f"{num} xhr: HTTP {st} pdf_urls_in_response={len(pdfs)} sample={pdfs[:3]}")
    except Exception as e:
        out.append(f"{num} xhr: ERR {type(e).__name__}: {e}")

report = "\n".join(out)
print(report)
with open(os.path.join(ROOT, "gtry_report.txt"), "w", encoding="utf-8") as f:
    f.write(report)
