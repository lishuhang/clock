#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline.py（v2）—— 在 GitHub Actions runner（无过滤外网）上：
① 用真实「专利名称」+ 申请人关键词 在 Google Patents 定位到「正确公司」的真实专利，
   取回真实公开号 + 真实摘要(abstract) + 申请人 + PDF 直链；
② 带退避重试下载真实专利 PDF 到 pdf/<公开号>.pdf。

关键修正 v1→v2：
- v1 仅按标题取 top1，导致抓到同名不同公司的旧专利（如爱奇艺的标题命中荣耀旧专利）。
- v2 在候选结果中按「申请人关键词」筛选，优先选 assignee 命中者；命中不到再退化为标题+关键词检索。
- v2 PDF 下载加指数退避重试（应对 Google 503 限流），并优先用搜索结果里的 pdf 直链。
"""
import urllib.request, urllib.parse, urllib.error, re, json, os, sys, time, random

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
API = "https://patents.google.com/xhr/query"

# 申请人 -> 用于在 Google Patents 结果里做归属判定的关键词
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


def _get(url, timeout=40):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
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
    except Exception as e:
        return [], str(e)
    try:
        data = json.loads(raw)
        return data.get("results", []), None
    except Exception:
        # 正则兜底
        pubs = re.findall(r'CN\d{9}[A-Z]', raw)
        fake = {"patent_id": "google/" + (pubs[0] if pubs else ""),
                "title": "", "abstract": "", "assignee": "", "pubdate": "",
                "pdf": "", "snippet": raw[:200]}
        return [fake] if pubs else [], None


def resolve(title, kw):
    """返回 (best_dict, candidates_list, confidence)。"""
    results, err = search_raw(title)
    cands = []
    for j in results:
        p = parse_result(j)
        if p["pub"]:
            cands.append(p)
    # 1) 在候选里按申请人关键词命中
    for p in cands:
        if kw and kw in (p["assignee"] or ""):
            return p, cands, "assignee"
    # 2) 标题里含关键词（罕见，但兜底）
    for p in cands:
        if kw and kw in (p["title"] or ""):
            return p, cands, "title"
    # 3) 退化：标题+关键词 再搜一次
    if kw:
        results2, _ = search_raw(title + " " + kw)
        for j in results2:
            p = parse_result(j)
            if p["pub"] and kw in (p["assignee"] or ""):
                return p, cands, "assignee2"
    # 4) 都找不到，取 top1 但标记低置信
    if cands:
        return cands[0], cands, "low"
    return {}, cands, "none"


def download_pdf(pub, pdf_hint=""):
    urls = []
    if pdf_hint:
        urls.append(pdf_hint)
    urls.append("https://patents.google.com/patent/%s/PDF" % pub)
    urls.append("https://patentimages.storage.googleapis.com/pdfs/%s/%s.pdf" % (pub[:4], pub))
    last = None
    for attempt in range(5):
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": UA,
                                                         "Accept": "application/pdf,*/*"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                if len(data) > 1000 and data[:4] == b"%PDF":
                    os.makedirs("pdf", exist_ok=True)
                    with open(os.path.join("pdf", pub + ".pdf"), "wb") as f:
                        f.write(data)
                    return len(data)
                last = "not-a-pdf(%d bytes)" % len(data)
            except Exception as e:
                last = str(e)
                continue
        # 全部 URL 失败 -> 退避重试
        time.sleep(min(60, 5 * (2 ** attempt)) + random.uniform(0, 3))
    return "ERR " + str(last)


def main():
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
        best, cands, conf = resolve(name, kw)
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
        }
        print("   -> pub=%s conf=%s assignee=%s" % (rec["pub"], conf, rec["assignee_real"][:24]), flush=True)
        results.append(rec)
        time.sleep(random.uniform(1.5, 3))
    with open("resolved.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(results), "results": results}, f, ensure_ascii=False, indent=2)

    # 下载真实 PDF
    ok = 0
    for r in results:
        if r.get("ok") and r.get("pub"):
            sz = download_pdf(r["pub"], r.get("pdf_hint", ""))
            r["pdf_bytes"] = sz
            if isinstance(sz, int) and sz > 1000:
                ok += 1
                print("  PDF %s -> %d bytes OK" % (r["pub"], sz), flush=True)
            else:
                print("  PDF %s -> %s FAIL" % (r["pub"], sz), flush=True)
            time.sleep(random.uniform(1.5, 3.5))
    with open("resolved.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(results), "downloaded": ok, "results": results}, f, ensure_ascii=False, indent=2)
    print("完成：%d/%d PDF 下载成功" % (ok, len(results)), flush=True)


if __name__ == "__main__":
    main()
