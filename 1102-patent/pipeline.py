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
import urllib.request, urllib.parse, urllib.error, re, json, os, sys, time, random, html
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


def parse_result(p):
    """p 为 Google xhr 结果里嵌套的 patent 对象。"""
    out = {}
    out["pub"] = p.get("publication_number", "")
    out["title"] = (p.get("title") or "").strip()
    ab = p.get("abstract") or p.get("snippet") or ""
    out["abstract"] = html.unescape(ab)
    out["assignee"] = p.get("assignee", "")
    out["pubdate"] = p.get("publication_date", "")
    rel = p.get("pdf", "")
    out["pdf"] = ("https://patentimages.storage.googleapis.com/pdfs/" + rel) if rel else ""
    out["snippet"] = html.unescape(p.get("snippet", ""))
    return out


def search_raw(query, num=20):
    inner = urllib.parse.urlencode({"q": query})
    url = API + "?" + urllib.parse.urlencode({"url": inner, "num": str(num)})
    last_err = None
    for attempt in range(3):  # 应对 Google 偶发空响应/限流
        try:
            raw = _get(url)
            data = json.loads(raw)
        except Exception as e:
            last_err = str(e)
            time.sleep(3 + attempt * 2)
            continue
        results = data.get("results", {})
        items = []
        if isinstance(results, dict):  # 新结构: results.cluster[].result[].patent
            for cl in results.get("cluster", []):
                for r in cl.get("result", []):
                    if isinstance(r, dict) and isinstance(r.get("patent"), dict):
                        items.append(r["patent"])
        elif isinstance(results, list):  # 兼容旧结构
            for j in results:
                if isinstance(j, dict) and j.get("patent_id"):
                    items.append(j)
        if items:
            return items
        time.sleep(4 + attempt * 3)  # 空结果，退避后重试
    return []


def _title_hit(name, t):
    return bool(name[:6] in t or t[:6] in name)


def resolve_one(name, kw):
    # 主搜索：标题 + 公司关键词（自由文本，一次请求）
    primary = search_raw((name + " " + kw) if kw else name, num=20)
    time.sleep(random.uniform(4, 7))  # 礼貌限速，避免触发 Google 限流
    for p in primary:
        if kw and kw in (p.get("assignee") or ""):
            return parse_result(p), [parse_result(x) for x in primary], "assignee"
    for p in primary:
        if _title_hit(name, p.get("title", "")):
            return parse_result(p), [parse_result(x) for x in primary], "title_sub"
    # 兜底：仅公司名，按申请人/标题命中挑选
    if kw:
        comp = search_raw(kw, num=40)
        time.sleep(random.uniform(6, 10))
        for p in comp:
            if kw and kw in (p.get("assignee") or ""):
                return parse_result(p), [parse_result(x) for x in comp], "assignee"
        for p in comp:
            if _title_hit(name, p.get("title", "")):
                return parse_result(p), [parse_result(x) for x in comp], "company_title"
        if comp:
            return parse_result(comp[0]), [parse_result(x) for x in comp], "company"
    if primary:
        return parse_result(primary[0]), [parse_result(x) for x in primary], "top"
    return {}, [], "none"


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


def _placeholder(p):
    return {
        "applicant_docx": p.get("applicant", ""),
        "docx_title": p.get("title", ""),
        "category": p.get("category", ""),
        "progress": p.get("progress", ""),
        "summary_docx": p.get("summary", ""),
        "pub": "", "title_real": "", "assignee_real": "", "abstract_real": "",
        "pubdate": "", "pdf_hint": "", "confidence": "pending",
        "candidates": [], "ok": False, "pdf_bytes": None,
    }


def do_resolve():
    with open("patents.json", encoding="utf-8") as f:
        db = json.load(f)
    patents = db.get("patents", [])
    # 分批解析：env PAT_RANGE="a:b" 只处理索引 [a,b) 的子集，规避 Google 限流；
    # 不在区间内的条目保留 resolved.json 中已有的结果（增量合并），避免覆盖已解出的专利。
    rng = os.environ.get("PAT_RANGE", "")
    if rng and ":" in rng:
        a, b = rng.split(":")
        slice_idx = set(range(int(a), int(b)))
    else:
        slice_idx = set(range(len(patents)))
    print("载入专利 %d 条，本次处理索引 %s" % (len(patents), sorted(slice_idx)), flush=True)
    old_list = []
    try:
        with open("resolved.json", encoding="utf-8") as f:
            old_list = json.load(f).get("results", [])
    except FileNotFoundError:
        old_list = []
    results = []
    for i, p in enumerate(patents):
        name = p.get("patent_name", "")
        applicant = p.get("applicant", "")
        kw = KW.get(applicant, "")
        if i not in slice_idx:
            results.append(old_list[i] if i < len(old_list) else _placeholder(p))
            continue
        print("[%d] %s | kw=%s" % (i, name[:24], kw), flush=True)
        best, cands, conf = resolve_one(name, kw)
        # 防御：若本次解析失败(none)但旧结果已 ok，则保留旧的好结果，绝不降级
        if conf == "none" and i < len(old_list) and old_list[i].get("ok"):
            results.append(old_list[i])
            print("   -> 本次 none，保留旧 ok 结果(%s)" % old_list[i].get("pub"), flush=True)
            time.sleep(random.uniform(1.5, 3))
            continue
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
