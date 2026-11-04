#!/usr/bin/env python3
"""微博搜索探针: genvisitor2 访客 cookie -> m.weibo.cn 容器搜索 API
依据: 2025-08 ThinkPHP 教程 (blog.csdn.net/m0_55735473/article/details/155749531)
      passport.weibo.com/visitor/genvisitor2 纯HTTP POST 拿访客 SUB, 免登录
输出: 精简 JSON 摘要 (防 token 狂烧)
"""
import json, re, sys, urllib.request, urllib.parse

UA_PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
OUT = {"steps": []}

def log(step, ok, detail):
    OUT["steps"].append({"step": step, "ok": ok, "detail": detail})
    print(f"[{'OK' if ok else 'FAIL'}] {step}: {detail[:300]}")

def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8", "replace")

# ---- Step 1: genvisitor2 拿访客 SUB (教程原参数) ----
try:
    body = urllib.parse.urlencode({
        "cb": "visitor_gray_callback",
        "tid": "01AUXHE0uWNcmbV0Qlq3L-R4dZHGS_3E7eKqUtdA9HiUgQ",
        "from": "weibo",
        "webdriver": "false",
    }).encode()
    st, hd, txt = http("https://passport.weibo.com/visitor/genvisitor2", data=body,
        headers={"User-Agent": UA_PC, "Content-Type": "application/x-www-form-urlencoded",
                 "Referer": "https://weibo.com/"})
    m = re.search(r'"sub":"([^"]+)"', txt) or re.search(r'"SUB":"([^"]+)"', txt)
    sub = m.group(1) if m else ""
    log("genvisitor2", bool(sub), f"HTTP{st} sub={'<'+str(len(sub))+'chars>' if sub else 'MISS'} raw_head={txt[:200]}")
except Exception as e:
    sub = ""
    log("genvisitor2", False, f"EXC {e}")

if not sub:
    # 退路: 老 genvisitor (fp 指纹法, dataabc/weibo-search 同款)
    try:
        fp = json.dumps({"os":"1","browser":"Chrome137","fonts":"undefined","screenInfo":"1920*1080*30","plugins":""})
        body = urllib.parse.urlencode({"cb": "gen_callback", "fp": fp}).encode()
        st, hd, txt = http("https://passport.weibo.com/visitor/genvisitor", data=body,
            headers={"User-Agent": UA_PC, "Content-Type": "application/x-www-form-urlencoded"})
        m = re.search(r'"tid":"([^"]+)"', txt)
        tid = m.group(1) if m else ""
        log("genvisitor(old)_tid", bool(tid), f"HTTP{st} tid={tid[:20]}...")
        if tid:
            st, hd, txt = http(f"https://passport.weibo.com/visitor/visitor?a=incarnate&t={urllib.parse.quote(tid)}&w=2&c=100&gc=&cb=cross_domain&from=weibo&_rand={__import__('random').random()}",
                headers={"User-Agent": UA_PC, "Referer": "https://weibo.com/"})
            m = re.search(r'"sub":"([^"]+)"', txt)
            sub = m.group(1) if m else ""
            log("incarnate_sub", bool(sub), f"HTTP{st} sub={'<'+str(len(sub))+'chars>' if sub else 'MISS'}")
    except Exception as e:
        log("genvisitor(old)", False, f"EXC {e}")

# ---- Step 2: 访客 SUB 验证 + m.weibo.cn 容器搜索 ----
if sub:
    kw = sys.argv[1] if len(sys.argv) > 1 else "马保国"
    cookie = f"SUB={sub}; SUBP=0033WrSXqPxfM72-Ws9jqgSFh70L9BLhLEdSfWFCfS0Gceh4awbGVFq.I"
    # 2a: weibo.com/ajax/feed/hottimeline (教程同款验证)
    try:
        st, hd, txt = http("https://weibo.com/ajax/feed/hottimeline?refresh=2&group_id=102803&containerid=102803&extparam=discover%7Cnew_feed&max_id=1&count=10",
            headers={"User-Agent": UA_PC, "Cookie": cookie, "Referer": "https://weibo.com/",
                     "X-Requested-With": "XMLHttpRequest"})
        ok = '"statuses"' in txt
        log("hottimeline_verify", ok, f"HTTP{st} has_statuses={ok} head={txt[:150]}")
    except Exception as e:
        log("hottimeline_verify", False, f"EXC {e}")
    # 2b: m.weibo.cn 容器搜索 (把 SUB 带过去试试, .weibo.cn 域可能不认)
    try:
        q = urllib.parse.quote(kw)
        url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{q}&page_type=searchall"
        st, hd, txt = http(url, headers={"User-Agent": UA_MOBILE, "Cookie": cookie,
                         "Referer": f"https://m.weibo.cn/search?containerid=100103type%3D1%26q%3D{q}"})
        try:
            j = json.loads(txt)
            ok = j.get("ok") == 1
            n = len(j.get("data", {}).get("cards", []))
            log("mweibo_search", ok, f"HTTP{st} ok={j.get('ok')} cards={n}")
            if ok and n:
                hits = []
                for c in j["data"]["cards"]:
                    mb = c.get("mblog") or (c.get("card_group", [{}])[0].get("mblog") if c.get("card_group") else None)
                    if mb:
                        pi = mb.get("page_info", {})
                        has_video = bool(pi.get("media_info", {}).get("stream_url") or pi.get("media_info", {}).get("playback_list"))
                        hits.append({"mid": mb.get("id"), "user": mb.get("user", {}).get("screen_name"),
                                     "video": has_video, "text": re.sub("<[^>]+>", "", mb.get("text", ""))[:50]})
                OUT["search_hits"] = hits[:10]
                print(json.dumps(hits[:10], ensure_ascii=False, indent=1))
        except Exception:
            log("mweibo_search", False, f"HTTP{st} non-json head={txt[:150]}")
    except Exception as e:
        log("mweibo_search", False, f"EXC {e}")

with open("/home/z/my-project/logs/wb_search_probe.json", "w") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("\nRESULT_JSON_PATH=/home/z/my-project/logs/wb_search_probe.json")
