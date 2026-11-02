#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe.py —— 在 runner 上探测各专利数据源的可达性（仅 GET，不下载大文件）。
写出 probe_report.txt 供人工通过 API 读取。"""
import os, urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
CK = os.path.join(ROOT, ".cookies", "tyc.txt")
cookies = {}
try:
    for line in open(CK, encoding="utf-8", errors="ignore").read().splitlines():
        p = line.split("\t")
        if len(p) >= 7:
            cookies[p[5]] = p[6]
except Exception:
    pass
cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
TOKEN = cookies.get("auth_token", "")
CSRF = cookies.get("csrfToken", "")


def test(name, url, headers=None, timeout=25):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120 Safari/537.36", "Accept": "*/*"}
    if headers:
        h.update(headers)
    if cookie_header:
        h.setdefault("Cookie", cookie_header)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return f"{name}: HTTP {r.status}  bytes={len(data)}  head={data[:160].decode('utf-8','ignore')!r}"
    except urllib.error.HTTPError as e:
        try:
            b = e.read()[:240].decode("utf-8", "ignore")
        except Exception:
            b = ""
        return f"{name}: HTTP {e.code}  body={b!r}"
    except Exception as e:
        return f"{name}: ERROR {type(e).__name__}: {e}"


lines = []
lines.append("=== 天眼查各 host 探测（cookie 已注入）===")
lines.append(test("api-gateway-web",
                  "https://api-gateway-web.tianyancha.com/services/v3/search/patent?word=CN123020788A&pageNum=1",
                  {"tyc-auth-token": TOKEN, "csrfToken": CSRF, "Referer": "https://zhuanli.tianyancha.com/"}))
lines.append(test("api.tianyancha",
                  "https://api.tianyancha.com/services/v3/search/patent?word=CN123020788A&pageNum=1",
                  {"tyc-auth-token": TOKEN, "csrfToken": CSRF}))
lines.append(test("napi-huawei",
                  "https://napi-huawei.tianyancha.com/services/v3/search/patent?word=CN123020788A&pageNum=1",
                  {"tyc-auth-token": TOKEN, "csrfToken": CSRF}))
lines.append(test("zhuanli-root", "https://zhuanli.tianyancha.com/"))
lines.append(test("www-root", "https://www.tianyancha.com/"))
lines.append("")
lines.append("=== 备选专利数据源（runner 可达性）===")
lines.append(test("google-patents-page", "https://patents.google.com/patent/CN123020788A/"))
lines.append(test("google-patentimages", "https://patentimages.storage.googleapis.com/"))
lines.append(test("espacenet", "https://worldwide.espacenet.com/"))
lines.append(test("cnipa", "https://pss-system.cponline.cnipa.gov.cn/"))
lines.append(test("qcc-web", "https://www.qcc.com/"))
lines.append(test("soopat", "https://www.soopat.com/"))
lines.append("")

# ---- 关键校验：文章里的专利号是否真实存在？用 Google Patents 搜索 API 验证 ----
import re as _re
def gquery(num):
    # Google Patents xhr query 返回 JSON（含 results），可判断专利号是否真实存在
    url = "https://patents.google.com/xhr/query?url=" + urllib.parse.quote("q=" + num)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read().decode("utf-8", "ignore")
        found = ('"num_results"' in data) or ('"results"' in data and 'total' in data)
        has = "FOUND" if found else "NOT-FOUND"
        return f"{num}: HTTP {r.status} -> {has} (len={len(data)})"
    except urllib.error.HTTPError as e:
        return f"{num}: HTTP {e.code}"
    except Exception as e:
        return f"{num}: ERROR {e}"

lines.append("=== 专利号真实性校验（Google Patents 搜索 API）===")
mdfiles = ["2026年10月互联网专利盘点.md", "2026年10月互联网专利盘点_备选专利池.md"]
nums = []
for mf in mdfiles:
    try:
        txt = open(os.path.join(ROOT, mf), encoding="utf-8").read()
        for m in _re.finditer(r"CN\d{9}A", txt):
            if m.group(0) not in nums:
                nums.append(m.group(0))
    except FileNotFoundError:
        lines.append(f"(找不到 {mf})")
lines.append(f"从稿件提取到 {len(nums)} 个唯一专利号，取前 10 个校验：")
for n in nums[:10]:
    lines.append("  " + gquery(n))
lines.append("对照（端点可用性 + 已知真实专利，应 FOUND）：")
lines.append("  " + gquery("tensorflow"))     # 文本检索，端点可用时应 FOUND
lines.append("  " + gquery("US4656098A"))      # 已知真实美国专利，应 FOUND

out = "\n".join(lines)
print(out)
with open(os.path.join(ROOT, "probe_report.txt"), "w", encoding="utf-8") as f:
    f.write(out)
