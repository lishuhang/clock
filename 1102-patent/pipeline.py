#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline.py —— 在 GitHub Actions runner（无过滤外网）上执行：
① 用 docx 解析出的真实「专利名称」在 Google Patents 搜索，
   取回真实公开号 + 真实摘要 + 申请人 + PDF 直链；
② 下载真实专利 PDF 到 pdf/<公开号>.pdf。
全程仅用标准库，无需 pip 安装。结果写 resolved.json 并提交。
"""
import urllib.request, urllib.parse, urllib.error, re, json, os, sys, time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
API = "https://patents.google.com/xhr/query"


def _get(url, timeout=40):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def parse_result(j):
    """从 Google Patents xhr JSON 中抽取关键字段。"""
    out = {}
    pid = j.get("patent_id", "")
    pub = pid.split("/")[-1] if pid else ""
    out["pub"] = pub
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
    # 申请人可能是中文/英文，额外抓 snippet
    out["snippet"] = j.get("snippet", "")
    return out


def search(title):
    inner = urllib.parse.urlencode({"q": title})
    url = API + "?" + urllib.parse.urlencode({"url": inner, "num": "20"})
    try:
        raw = _get(url)
    except Exception as e:
        return {"ok": False, "err": str(e)}
    # 先尝试 JSON
    try:
        data = json.loads(raw)
        results = data.get("results", [])
        if results:
            top = parse_result(results[0])
            top["ok"] = True
            top["total"] = data.get("total", len(results))
            top["source"] = "json"
            return top
    except Exception:
        pass
    # 正则兜底
    pubs = re.findall(r'CN\d{9}[A-Z]', raw)
    pub = pubs[0] if pubs else ""
    abs_m = re.search(r'"abstract"\s*:\s*\{?\s*"text"\s*:\s*"([^"]{10,2000})"', raw)
    abstract = abs_m.group(1) if abs_m else ""
    asg_m = re.findall(r'"assignee"\s*:\s*\[?\s*"([^"]{2,80})"', raw)
    return {
        "ok": bool(pub), "pub": pub, "title": "", "abstract": abstract,
        "assignee": " / ".join(asg_m[:3]), "pubdate": "",
        "pdf": "", "snippet": "", "source": "regex",
        "total": len(pubs),
    }


def download_pdf(pub):
    dest = os.path.join("pdf", pub + ".pdf")
    os.makedirs("pdf", exist_ok=True)
    url = "https://patents.google.com/patent/%s/PDF" % pub
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        with open(dest, "wb") as f:
            f.write(data)
        return len(data)
    except Exception as e:
        # 重试一次（换存储桶直链）
        try:
            url2 = "https://patentimages.storage.googleapis.com/pdfs/%s/%s.pdf" % (pub[:4], pub)
            req = urllib.request.Request(url2, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            with open(dest, "wb") as f:
                f.write(data)
            return len(data)
        except Exception as e2:
            return "ERR %s | %s" % (e, e2)


def main():
    with open("patents.json", encoding="utf-8") as f:
        db = json.load(f)
    patents = db.get("patents", [])
    print("载入专利 %d 条" % len(patents), flush=True)
    results = []
    for i, p in enumerate(patents, 1):
        name = p.get("patent_name", "")
        applicant = p.get("applicant", "")
        print("[%d/%d] 解析: %s" % (i, len(patents), name), flush=True)
        r = search(name)
        r.update({"applicant_docx": applicant,
                  "docx_title": p.get("title", ""),
                  "category": p.get("category", ""),
                  "progress": p.get("progress", ""),
                  "summary_docx": p.get("summary", "")})
        print("   -> pub=%s ok=%s assignee=%s" % (r.get("pub"), r.get("ok"), r.get("assignee")), flush=True)
        results.append(r)
        time.sleep(1.5)  # 礼貌限速，避免触发反爬
    with open("resolved.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(results), "results": results}, f,
                  ensure_ascii=False, indent=2)
    print("已写出 resolved.json", flush=True)

    # 下载真实 PDF
    ok = 0
    for r in results:
        if r.get("ok") and r.get("pub"):
            sz = download_pdf(r["pub"])
            r["pdf_bytes"] = sz
            if isinstance(sz, int) and sz > 1000:
                ok += 1
                print("  PDF %s -> %d bytes OK" % (r["pub"], sz), flush=True)
            else:
                print("  PDF %s -> %s FAIL" % (r["pub"], sz), flush=True)
            time.sleep(1.5)
    with open("resolved.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(results), "downloaded": ok, "results": results}, f,
                  ensure_ascii=False, indent=2)
    print("完成：%d/%d PDF 下载成功" % (ok, len(results)), flush=True)


if __name__ == "__main__":
    main()
