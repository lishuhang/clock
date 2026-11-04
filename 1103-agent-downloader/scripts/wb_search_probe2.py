#!/usr/bin/env python3
"""微博搜索探针2: m.weibo.cn 游客cookie(直接GET首页种下) -> 容器搜索API
上轮 ok=-100 真因: requests 没带任何 cookie; m.weibo.cn 首页 GET 即种游客 SUB
"""
import json, re, sys, urllib.request, urllib.parse, http.cookiejar

UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
OUT = {"steps": []}

def log(step, ok, detail):
    OUT["steps"].append({"step": step, "ok": ok, "detail": detail[:400]})
    print(f"[{'OK' if ok else 'FAIL'}] {step}: {detail[:400]}")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [("User-Agent", UA_MOBILE)]

# Step 1: GET m.weibo.cn 首页种游客 cookie
try:
    with opener.open("https://m.weibo.cn/", timeout=20) as r:
        cookies = {c.name: c.value for c in cj}
    need = {"SUB", "SUBP"}
    log("mweibo_home_cookies", bool(need & set(cookies)), f"got={list(cookies.keys())}")
except Exception as e:
    cookies = {}
    log("mweibo_home_cookies", False, f"EXC {e}")

# Step 2: 容器搜索 API
kw = sys.argv[1] if len(sys.argv) > 1 else "马保国"
try:
    q = urllib.parse.quote(kw)
    url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{q}&page_type=searchall"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA_MOBILE,
        "Referer": f"https://m.weibo.cn/search?containerid=100103type%3D1%26q%3D{q}",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
    })
    with opener.open(req, timeout=20) as r:
        txt = r.read().decode("utf-8", "replace")
    try:
        j = json.loads(txt)
        ok = j.get("ok") == 1
        cards = j.get("data", {}).get("cards", [])
        log("mweibo_container_search", ok, f"ok={j.get('ok')} cards={len(cards)} msg={j.get('msg','')}")
        if ok:
            hits = []
            for c in cards:
                for mb in ([c.get("mblog")] if c.get("mblog") else [g.get("mblog") for g in c.get("card_group", []) if g]):
                    if not mb:
                        continue
                    mi = mb.get("page_info", {}).get("media_info", {})
                    has_video = bool(mi.get("stream_url") or mi.get("playback_list") or mb.get("page_info", {}).get("type") == "video")
                    hits.append({"mid": mb.get("id") or mb.get("mid"), "user": mb.get("user", {}).get("screen_name"),
                                 "video": has_video, "text": re.sub("<[^>]+>", "", mb.get("text", ""))[:60]})
            OUT["hits"] = hits
            print(json.dumps(hits[:12], ensure_ascii=False, indent=1))
    except Exception:
        log("mweibo_container_search", False, f"non-json head={txt[:200]}")
except Exception as e:
    log("mweibo_container_search", False, f"EXC {e}")

# Step 3(备用): 备选容器ID 视频tab (100103type=1&q=xxx&tb=video? 官方视频搜索容器)
try:
    q = urllib.parse.quote(kw)
    cid = urllib.parse.quote(f"100103type%3D1%26q%3D{q}%26t%3D0%26playtype%3D1")
    url = f"https://m.weibo.cn/api/container/getIndex?containerid={cid}&page_type=searchall"
    req = urllib.request.Request(url, headers={"User-Agent": UA_MOBILE,
        "Referer": f"https://m.weibo.cn/search?containerid={cid}", "X-Requested-With": "XMLHttpRequest"})
    with opener.open(req, timeout=20) as r:
        txt = r.read().decode("utf-8", "replace")
    j = json.loads(txt)
    cards = j.get("data", {}).get("cards", [])
    n_video = 0
    vid_hits = []
    for c in cards:
        for mb in ([c.get("mblog")] if c.get("mblog") else [g.get("mblog") for g in c.get("card_group", []) if g]):
            if mb and mb.get("page_info", {}).get("type") == "video":
                n_video += 1
                vid_hits.append({"mid": mb.get("id") or mb.get("mid"), "user": mb.get("user", {}).get("screen_name"),
                                 "text": re.sub("<[^>]+>", "", mb.get("text", ""))[:60]})
    log("mweibo_video_tab_search", j.get("ok") == 1, f"ok={j.get('ok')} cards={len(cards)} video_cards={n_video}")
    if vid_hits:
        OUT["video_hits"] = vid_hits
        print(json.dumps(vid_hits[:12], ensure_ascii=False, indent=1))
except Exception as e:
    log("mweibo_video_tab_search", False, f"EXC {e}")

with open("/home/z/my-project/logs/wb_search_probe2.json", "w") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("\nRESULT=/home/z/my-project/logs/wb_search_probe2.json")
