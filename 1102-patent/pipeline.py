#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline.py（v3，双模式，runner 端执行）
用法:
  python3 pipeline.py resolve    # 仅解析：用真实专利名称+申请人关键词在 Google Patents 定位真实专利，
                                 #          写出 resolved.json（含真实公开号/摘要/申请人），不下载 PDF
  python3 pipeline.py download   # 仅下载：读 resolved.json，带退避+浏览器态(cookie/Referer)下载真实 PDF 到 pdf/

设计要点:
- resolve 阶段快且不会卡死，先把高价值的「真实摘要」落库，再单独重试易限流的 PDF 下载。
- download 用 http.cookiejar 维持会话、带 Referer，规避 Google Patents /PDF 端 503 限流。
"""
import urllib.request, urllib.parse, urllib.error, re, json, os, sys, time, random
from http.cookiejar import CookieJar

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
API = "https://patents.google.com/xhr/query"
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

# 申请人 -> 用于在结果里做归属判定的关键词
KW = {
    "上海爱奇艺新媒体科技有限公司": "爱奇艺",
    "湖南快乐阳光互动娱乐传媒有限公司": "快乐阳光",
    "上海哔哩哔哩科技有限公司": "哔哩哔哩",
    "北京优酷科技有限公司": "优酷",
    "网易（杭州）网络有限公司": "网易",
    "腾讯科技（深圳）有限公司": "腾讯",
    "上海鹰角网络科技有限公司": "鹰角",
    "咪咕互动娱乐有限公司": "咪咕",
    "优酷文化科技（北京）有限公司": "优酷",
    "百度在线网络技术(北京)有限公司": "百度",
    "北京字跳网络技术有限公司": "字跳",
    "金山办公": "金山",
    "腾讯": "腾讯",
    "青岛海尔多媒体有限公司": "海尔",
    "荣耀终端股份有限公司": "荣耀",
    "美团科技有限公司": "美团",
}


def _get(url, timeout=40, referer=None):
    headers = {"User-Agent": UA,
               "Accept": "application/json, text/plain, */*",
               "Accept-Language": "zh-CN,zh;q=0.9"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with OPENER.open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def parse_result(j):
    out = {}
    pid = j.get("patent_id", "")
    out["pub"] = pid.split("/")[-1] if pid else ""
    out["title"] = j.get("title", "")
    ab = j.get("abstract", "")
    if isinstance(ab, dict):
        ab = ab.get("text", "")
    out["abstract"] = ab or ""
    asg = j.get("assignee") or []
    if isinstance(asg, str):
        asg = [asg]
    out["assignee"] = " / ".join(asg)
    out["pubdate"] = j.get("pubdate", "")
    out["pdf"] = j.get("pdf") or j.get("pdfUrl") or ""
    out["snippet"] = j.get("snippet", "")
    return out


def search_raw(title, num=20):
    inner = urllib.parse.urlencode({"q": title})
    url = API + "?" + urllib.parse.urlencode({"url": inner, "num": str(num)})
    try:
        raw = _get(url)
        data = json.loads(raw)
    except Exception:
        data = None
    if isinstance(data, dict):
        results = data.get("results", [])
    elif isinstance(data, list):
        results = data
    else:
        results = []
    out = [j for j in results if isinstance(j, dict) and j.get("patent_id")]
    if out:
        return out
    pubs = re.findall(r'CN\d{9}[A-Z]', raw if 'raw' in dir() else "")
    fake = {"patent_id": "google/" + (pubs[0] if pubs else ""),
            "title": "", "abstract": "", "assignee": "", "pubdate": "", "pdf": "", "snippet": ""}
    return [fake] if pubs else []


def resolve_one(title, kw):
    results = search_raw(title)
    cands = []
    for j in results:
        p = parse_result(j)
        if p["pub"]:
            cands.append(p)
    for p in cands:
        if kw and kw in (p["assignee"] or ""):
            return p, cands, "assignee"
    for p in cands:
        if kw and kw in (p["title"] or ""):
            return p, cands, "title"
    if kw:
        results2 = search_raw(title + " " + kw)
        for j in results2:
            p = parse_result(j)
            if p["pub"] and kw in (p["assignee"] or ""):
                return p, cands, "assignee2"
    if cands:
        return cands[0], cands, "low"
    return {}, cands, "none"


def download_pdf(pub, pdf_hint=""):
    # 预热：先访问专利 HTML 页，让 cookie 落地，规避 /PDF 端 503
    try:
        OPENER.open(urllib.request.Request(
            "https://patents.google.com/patent/%s/" % pub,
            headers={"User-Agent": UA, "Accept": "text/html,*/*"}), timeout=20)
    except Exception:
        pass
    urls = []
    if pdf_hint:
        urls.append(pdf_hint)
    urls.append("https://patents.google.com/patent/%s/PDF" % pub)
    last = None
    for attempt in range(3):
        for u in urls:
            ref = "https://patents.google.com/patent/%s/" % pub if "patents.google.com" in u else "https://patents.google.com/"
            try:
                req = urllib.request.Request(u, headers={
                    "User-Agent": UA, "Accept": "application/pdf,*/*",
                    "Referer": ref})
                with OPENER.open(req, timeout=45) as r:
                    data = r.read()
                if len(data) > 1000 and data[:4] == b"%PDF":
                    os.makedirs("pdf", exist_ok=True)
                    with open(os.path.join("pdf", pub + ".pdf"), "wb") as f:
                        f.write(data)
                    return len(data)
                last = "not-pdf(%d)" % len(data)
            except Exception as e:
                last = str(e)
                continue
        time.sleep(min(40, 8 * (2 ** attempt)) + random.uniform(0, 4))
    return "ERR " + str(last)


def do_resolve():
    with open("patents.json", encoding="utf-8") as f:
        db = json.load(f)
    patents = db.get("patents", [])
    print("载入专利 %d 条" % len(patents), flush=True)
    results = []
    for i, p in enumerate(patents, 1):
        name = p.get("patent_name", "")
        applicant = p.get("applicant", "")
        kw = KW.get(applicant, "")
        print("[%d/%d] %s | kw=%s" % (i, len(patents), name[:24], kw), flush=True)
        best, cands, conf = resolve_one(name, kw)
        rec = {
            "applicant_docx": applicant,
            "docx_title": p.get("title", ""),
            "category": p.get("category", ""),
            "progress": p.get("progress", ""),
            "summary_docx": p.get("summary", ""),
            "pub": best.get("pub", ""),
            "title_real": best.get("title", ""),
            "assignee_real": best.get("assignee", ""),
            "abstract_real": best.get("abstract", ""),
            "pubdate": best.get("pubdate", ""),
            "pdf_hint": best.get("pdf", ""),
            "confidence": conf,
            "candidates": [{"pub": c["pub"], "assignee": c["assignee"], "title": c["title"]}
                           for c in cands[:5]],
            "ok": bool(best.get("pub")),
            "pdf_bytes": None,
        }
        print("   -> pub=%s conf=%s assignee=%s" % (rec["pub"], conf, rec["assignee_real"][:24]), flush=True)
        results.append(rec)
        time.sleep(random.uniform(1.5, 3))
    with open("resolved.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(results), "results": results}, f, ensure_ascii=False, indent=2)
    print("resolved.json 写出完成（%d 条）" % len(results), flush=True)


def do_download():
    with open("resolved.json", encoding="utf-8") as f:
        db = json.load(f)
    results = db.get("results", [])
    ok = 0
    for i, r in enumerate(results, 1):
        if not r.get("ok") or not r.get("pub"):
            continue
        pub = r["pub"]
        print("[%d/%d] 下载 %s" % (i, len(results), pub), flush=True)
        sz = download_pdf(pub, r.get("pdf_hint", ""))
        r["pdf_bytes"] = sz
        if isinstance(sz, int) and sz > 1000:
            ok += 1
            print("   -> %d bytes OK" % sz, flush=True)
        else:
            print("   -> %s FAIL" % sz, flush=True)
        time.sleep(random.uniform(3, 6))
    db["downloaded"] = ok
    with open("resolved.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("完成：%d/%d PDF 下载成功" % (ok, len(results)), flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "resolve"
    if mode == "resolve":
        do_resolve()
    elif mode == "download":
        do_download()
    else:
        print("未知模式:", mode)
