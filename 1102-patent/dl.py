#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dl.py —— 在 GitHub Actions(ubuntu-latest)  runner 上运行：
解析同目录两份 md 中的相对路径链接，逐件向天眼查查询说明书附图与全文 PDF，
落入 img/<分类>[/备选]/<公开号>.png 与 pdf/<分类>[/备选]/<公开号>.pdf。

依赖：仅 Python 标准库（urllib）。无第三方依赖。
说明：天眼查 API 返回结构未知，本脚本做“尽力而为”提取，并把前 3 件的
search/detail 原始 JSON 写入 api_probe.json 供人工核对字段名（已脱敏）。
"""
import os, re, json, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
CK = os.path.join(ROOT, ".cookies", "tyc.txt")
API = "https://api-gateway-web.tianyancha.com"
REF = "https://zhuanli.tianyancha.com/"

# ---- 读取 cookie ----
cookies = {}
try:
    for line in open(CK, encoding="utf-8", errors="ignore").read().splitlines():
        p = line.split("\t")
        if len(p) >= 7:
            cookies[p[5]] = p[6]
except FileNotFoundError:
    print("[fatal] 缺少 .cookies/tyc.txt，请确认 secret TYCCOOKIE 已写入")
    raise SystemExit(1)

cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
TOKEN = cookies.get("auth_token", "")
CSRF = cookies.get("csrfToken", "")


def hdr():
    return {
        "Cookie": cookie_header,
        "tyc-auth-token": TOKEN,
        "csrfToken": CSRF,
        "Referer": REF,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }


def get(url):
    req = urllib.request.Request(url, headers=hdr())
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def get_bytes(url):
    req = urllib.request.Request(url, headers={"Referer": REF, "Cookie": cookie_header,
                                               "User-Agent": hdr()["User-Agent"]})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def deep_find(obj, keys, exts=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str):
                if exts is None or any(v.lower().endswith(e) for e in exts):
                    return v
            r = deep_find(v, keys, exts)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_find(v, keys, exts)
            if r:
                return r
    return None


def find_id(obj):
    for k in ("id", "patentId", "pid", "paId", "patent_id", "pdId", "patentId_"):
        v = deep_find(obj, [k])
        if v and str(v).isdigit():
            return str(v)
    return None


def redact(obj):
    """递归删除可能含凭据的字段，避免写入日志。"""
    if isinstance(obj, dict):
        return {k: ("***" if any(s in k.lower() for s in ("token", "auth", "cookie", "csrf", "session", "password", "secret")) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


# ---- 解析两份 md，得到 (公开号, img相对路径, pdf相对路径) ----
MDFILES = [
    os.path.join(ROOT, "2026年10月互联网专利盘点.md"),
    os.path.join(ROOT, "2026年10月互联网专利盘点_备选专利池.md"),
]
jobs = []
for md in MDFILES:
    if not os.path.exists(md):
        print("[warn] 找不到", md)
        continue
    cur = None
    for line in open(md, encoding="utf-8"):
        m = re.search(r'!\[专利原图\]\(img/(.+?/(CN[0-9]+A)\.png)\)', line)
        if m:
            cur = (m.group(2), "img/" + m.group(1))
            continue
        m = re.search(r'\*\*专利PDF\*\*：\[pdf/(.+?)\]\(pdf/(.+?)\)', line)
        if m and cur:
            pub, _ = cur
            jobs.append((pub, "img/" + m.group(1), "pdf/" + m.group(2)))
            cur = None

print(f"[info] 解析到 {len(jobs)} 件专利目标")
probe = []
ok_img = ok_pdf = 0

for i, (pub, imgrel, pdfrel) in enumerate(jobs):
    try:
        s = get(f"{API}/services/v3/search/patent?word={pub}&pageNum=1")
        sj = json.loads(s)
        if i < 3:
            probe.append({"stage": "search", "pub": pub, "json": redact(sj)})
        pid = find_id(sj)
        if not pid:
            print(f"[skip] {pub} 无专利 id"); continue
        d = None
        for dpath in (f"/services/v3/patent/{pid}",
                      f"/services/v3/patent/detail?id={pid}",
                      f"/services/v3/patent/detail?pid={pid}",
                      f"/services/v3/search/patent/detail/{pid}"):
            try:
                d = get(f"{API}{dpath}"); break
            except Exception:
                d = None
        if not d:
            print(f"[skip] {pub} 详情获取失败"); continue
        dj = json.loads(d)
        if i < 3:
            probe.append({"stage": "detail", "pub": pub, "json": redact(dj)})

        fig = deep_find(dj, ("figureUrl", "figure", "imgUrl", "drawings", "imageUrl", "picUrl", "pdfImage"), (".png", ".jpg", ".jpeg", ".gif"))
        pdf = deep_find(dj, ("pdfUrl", "pdf", "fullTextUrl", "pdfPath", "downloadUrl", "fileUrl"), (".pdf",))
        if not fig:
            fig = deep_find(sj, ("figureUrl", "imgUrl", "imageUrl", "picUrl"), (".png", ".jpg", ".jpeg"))
        if not pdf:
            pdf = deep_find(sj, ("pdfUrl", "downloadUrl", "fullTextUrl"), (".pdf",))

        if fig:
            try:
                data = get_bytes(fig)
                if data[:4] not in (b"%PDF", b"\x89PNG", b"\xff\xd8\xff"):
                    print(f"[fig?] {pub} 返回非图片({len(data)}B)，跳过")
                else:
                    os.makedirs(os.path.dirname(os.path.join(ROOT, imgrel)), exist_ok=True)
                    with open(os.path.join(ROOT, imgrel), "wb") as f:
                        f.write(data)
                    ok_img += 1
                    print(f"[图OK] {pub} -> {imgrel} ({len(data)}B)")
            except Exception as e:
                print(f"[图失败] {pub}: {e}")
        else:
            print(f"[无图] {pub} 详情未找到附图URL")

        if pdf:
            try:
                data = get_bytes(pdf)
                if not data.startswith(b"%PDF"):
                    print(f"[pdf?] {pub} 返回非PDF({len(data)}B)，跳过")
                else:
                    os.makedirs(os.path.dirname(os.path.join(ROOT, pdfrel)), exist_ok=True)
                    with open(os.path.join(ROOT, pdfrel), "wb") as f:
                        f.write(data)
                    ok_pdf += 1
                    print(f"[PDF OK] {pub} -> {pdfrel} ({len(data)}B)")
            except Exception as e:
                print(f"[PDF失败] {pub}: {e}")
        else:
            print(f"[无PDF] {pub} 详情未找到PDF URL")

        time.sleep(1.0)  # 礼貌限速
    except Exception as e:
        print(f"[err] {pub}: {e}")

if probe:
    with open(os.path.join(ROOT, "api_probe.json"), "w", encoding="utf-8") as f:
        json.dump(probe, f, ensure_ascii=False, indent=2)
    print("[info] 已写出 api_probe.json（前3件原始结构，已脱敏）")

print(f"[done] 图={ok_img}/{len(jobs)}  PDF={ok_pdf}/{len(jobs)}")
