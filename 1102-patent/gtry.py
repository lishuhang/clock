#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gtry.py v2 —— 打印 Google Patents xhr 查询的原始响应，判断专利号是否真实存在。"""
import os, re, urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))

def xhr(num):
    url = "https://patents.google.com/xhr/query?url=" + urllib.parse.quote("q=" + num)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64) Chrome/120"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

out = []
for num in ["CN123020788A", "CN122933917A", "US4656098A", "tensorflow"]:
    st, data = xhr(num)
    m = re.search(r'"total"\s*:\s*(\d+)', data) if isinstance(data, str) else None
    total = m.group(1) if m else "n/a"
    out.append(f"=== {num}  status={st} len={len(data) if isinstance(data,str) else 0} total={total} ===")
    out.append((data if isinstance(data, str) else str(data))[:500])
    out.append("")

report = "\n".join(out)
print(report)
with open(os.path.join(ROOT, "gtry_report.txt"), "w", encoding="utf-8") as f:
    f.write(report)
