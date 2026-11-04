#!/usr/bin/env python3
# B站: 热门API自发现 → [1) guest html5 playurl 探针(可能720p mp4) → 2) yt-dlp 免登录480p] → meta
# --planb <URL>: yt-dlp + Referer头 重试
# 未探索(不再尝试): agent-browser __playinfo__ 管线(findings/03 B6, 含极验验证码, 工作量大)
import requests, json, os, sys, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "bilibili"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/bilibili_001.txt"

S = requests.Session()
S.headers.update({"User-Agent": UA_PC, "Referer": "https://www.bilibili.com/",
                  "Accept": "application/json, text/plain, */*"})

def discover():
    r = S.get("https://api.bilibili.com/x/web-interface/popular", params={"ps": 30, "pn": 1}, timeout=15)
    j = r.json()
    if j.get("code") != 0:
        log(PLAT, "discover", f"popular code={j.get('code')} msg={j.get('message')} http={r.status_code}")
        return None
    lst = j["data"]["list"]
    cands = [v for v in lst if 60 <= v.get("duration", 0) <= 420]
    v = cands[0] if cands else min(lst, key=lambda x: abs(x.get("duration", 0) - 300))
    log(PLAT, "discover", f"热门API命中 bvid={v['bvid']} cid={v.get('cid')} 时长={v['duration']}s 标题={v['title'][:50]} UP={v['owner']['name']}")
    return v

def playurl_html5(bvid, cid):
    """游客 html5 playurl: 历史上可给 720p mp4 单文件"""
    try:
        r = S.get("https://api.bilibili.com/x/player/playurl",
                  params={"bvid": bvid, "cid": cid, "qn": 80, "platform": "html5", "high_quality": 1},
                  timeout=15)
        j = r.json()
        log(PLAT, "playurl-html5", f"code={j.get('code')} msg={j.get('message')} quality={j.get('data',{}).get('quality')}")
        if j.get("code") == 0 and j["data"].get("durl"):
            d0 = j["data"]["durl"][0]
            return {"url": d0["url"], "quality": j["data"].get("quality"), "size": d0.get("size")}
    except Exception as e:
        log(PLAT, "playurl-html5", f"异常: {e}")
    return None

if PLANB:
    url = sys.argv[sys.argv.index("--planb") + 1]
    bvid = re.search(r"(BV[\w]+)", url).group(1) if re.search(r"(BV[\w]+)", url) else "planb"
    print(f"STEP planB 目标: {url}")
    try:
        info = ytdlp_json(url, ["--add-headers", "Referer:https://www.bilibili.com/"])
        fmt, height = pick_ytdlp_format(info, 1080, 90)
    except Exception as e:
        log(PLAT, "fail", str(e))
        wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_bilibili.py --planb {url}", RAWLOG,
               [f"error={str(e)[:250]}"], "planB也失败", "记录agent-browser管线为未探索路径, 结束本平台")
        finish(PLAT, False, f"planB失败: {str(e)[-130:]}")
        sys.exit(1)
    subprocess.run([YTDLP, "--add-headers", "Referer:https://www.bilibili.com/", "-f", fmt,
                    "--merge-output-format", "mp4", "-o", f"{OUT}/%(id)s.%(ext)s", url],
                   capture_output=True, text=True, timeout=900)
    out = find_out_file(OUT, bvid) or find_out_file(OUT, "BV")
    if not out:
        finish(PLAT, False, "planB下载无产物")
        sys.exit(1)
    p = probe(out)
    meta = {"platform": PLAT, "status": "ok", "source_url": url, "author": info.get("uploader"),
            "title": info.get("title"), "summary": (info.get("description") or "")[:500],
            "resolution": f"{p.get('width')}x{p.get('height')}", "size_bytes": p["size"],
            "file": os.path.basename(out), "method": f"planB: yt-dlp+Referer fmt={fmt}",
            "discover": "用户/搜索提供URL"}
else:
    v = discover()
    if not v:
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_bilibili.py", RAWLOG,
               ["热门API x/web-interface/popular 失败(code!=0)"], "自发现失败", "重试需提供BV URL --planb")
        finish(PLAT, False, "热门API失败(重试: --planb <URL>)")
        sys.exit(1)
    import re as _re
    bvid, cid = v["bvid"], v.get("cid")
    if not cid:
        jv = S.get("https://api.bilibili.com/x/web-interface/view", params={"bvid": bvid}, timeout=15).json()
        cid = (jv.get("data") or {}).get("cid")
        log(PLAT, "discover", f"view API cid={cid} code={jv.get('code')}")
    title, owner, desc = v["title"], v["owner"], (v.get("desc") or "")
    url = f"https://www.bilibili.com/video/{bvid}"
    print(f"STEP 目标: {url} | {title[:40]} | UP:{owner['name']} | {v['duration']}s")

    out, method, height, info = None, None, None, None
    # 通路1: html5 playurl 探针(≥720p才采用)
    if cid:
        h = playurl_html5(bvid, cid)
        if h and (h["quality"] or 0) >= 64:
            try:
                download(h["url"], f"{OUT}/bilibili_{bvid}.mp4",
                         {"Referer": "https://www.bilibili.com/", "User-Agent": UA_PC}, PLAT, 110)
                out = f"{OUT}/bilibili_{bvid}.mp4"
                method = f"guest playurl(platform=html5,high_quality=1, qn={h['quality']})"
                height = {80: 1080, 74: 720, 64: 720, 48: 480, 32: 480, 16: 360}.get(h["quality"], h["quality"])
                print(f"STEP html5通路: qn={h['quality']}")
            except Exception as e:
                log(PLAT, "fail", f"html5直下异常: {e}")
                out = None
    # 通路2: yt-dlp 免登录
    if not out:
        try:
            info = ytdlp_json(url)
            fmt, height = pick_ytdlp_format(info, 1080, 90)
            log(PLAT, "extract", f"yt-dlp formats={len(info.get('formats', []))} 选定={fmt} 高度={height}")
            print(f"STEP yt-dlp通路: fmt={fmt} h={height}")
        except Exception as e:
            log(PLAT, "fail", str(e))
            wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_bilibili.py", RAWLOG,
                   [f"target={url}", str(e)[:250]],
                   "html5探针+yt-dlp 均失败", "重试: --planb <URL>; 未探索: agent-browser __playinfo__ 管线")
            finish(PLAT, False, f"yt-dlp失败: {str(e)[-130:]} (重试: --planb)")
            sys.exit(1)
        r = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                            f"{OUT}/bilibili_{bvid}.%(ext)s", url],
                           capture_output=True, text=True, timeout=900)
        out = find_out_file(OUT, f"bilibili_{bvid}")
        if r.returncode != 0 or not out:
            tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
            log(PLAT, "fail", f"yt-dlp下载: {tail[:250]}")
            wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_bilibili.py", RAWLOG,
                   [f"target={url}", f"download: {tail[:250]}"], "yt-dlp下载失败",
                   "重试: --planb <URL>; 未探索: agent-browser __playinfo__ 管线")
            finish(PLAT, False, f"下载失败: {tail[:120]} (重试: --planb)")
            sys.exit(1)
        method = f"yt-dlp guest(免登录) fmt={fmt}"
    p = probe(out)
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": url,
        "author": f"{owner['name']} (mid={owner['mid']})" if owner else (info or {}).get("uploader"),
        "title": title or (info or {}).get("title"),
        "summary": desc[:500],
        "publish_time": time.strftime("%Y-%m-%d", time.localtime(v.get("pubdate", 0))) if v.get("pubdate") else None,
        "duration_sec": v.get("duration"),
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height}p",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "view": v.get("stat", {}).get("view"), "like": v.get("stat", {}).get("like"),
        "method": method,
        "discover": "api.bilibili.com/x/web-interface/popular 热门榜(免登录)",
        "note": "免登录最高480p(B11); 720p+需SESSDATA cookie(用户未提供, 记录为未探索路径)",
    }

save_meta(PLAT, meta)
upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                    "resolution": meta["resolution"], "method": meta["method"]})
wentry(f"{PLAT}-download", "OK", "python3 tools/dl_bilibili.py" + (" --planb" if PLANB else ""), RAWLOG,
       [f"target={meta['source_url']}", f"author={meta['author']}",
        f"file={meta['file']} size={p['size']} res={meta['resolution']}",
        f"method={meta['method']}"],
       "B站视频下载成功", "下一平台: youtube")
finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} @{meta['author']}")
