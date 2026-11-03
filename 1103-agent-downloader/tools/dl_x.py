#!/usr/bin/env python3
# X/Twitter: yt-dlp twitter extractor(公开推文, 游客) → ≤1080p
# 目标: SpaceX 官方 2024-06 筷子臂测试推文
# --planb: fxtwitter API(元数据) + video.twimg.com 直链(文件)  [Lemmy帖子留档的1080p直链]
import requests, json, os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "x"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/x_001.txt"
URL = "https://x.com/SpaceX/status/1806444569107865825"
M = re.search(r"(?:x|twitter)\.com/([^/]+)/status/(\d+)", URL)
USER, TID = M.group(1), M.group(2)
DIRECT_MP4 = "https://video.twimg.com/ext_tw_video/1806444172456742912/pu/vid/avc1/1920x1080/Mh-weZFtRiQec8V0.mp4"

if PLANB:
    # ---- 方案B: fxtwitter API + 直链 ----
    j = requests.get(f"https://api.fxtwitter.com/{USER}/status/{TID}", timeout=20,
                     headers={"User-Agent": UA_PC}).json()
    tw = j.get("tweet") or {}
    vids = ((tw.get("media") or {}).get("all") or [])
    vurl = None
    for mv in vids:
        if mv.get("type") == "video":
            vurl = mv.get("url")
            break
    if not vurl:
        vurl = DIRECT_MP4
        log(PLAT, "planB", "fxtwitter未给视频URL, 使用留档直链 video.twimg.com 1920x1080")
    else:
        log(PLAT, "planB", f"fxtwitter video url={str(vurl)[:120]}")
    text = tw.get("text") or ""
    au = tw.get("author") or {}
    out = f"{OUT}/x_{TID}.mp4"
    try:
        size = download(vurl, out, {"User-Agent": UA_PC, "Referer": "https://x.com/"}, PLAT, 110)
    except Exception as e:
        log(PLAT, "fail", f"fxtwitter URL失败({e}), 改留档直链")
        size = download(DIRECT_MP4, out, {"User-Agent": UA_PC}, PLAT, 110)
    p = probe(out)
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": tw.get("url") or URL,
        "author": f"{au.get('name')} (@{au.get('screen_name')})",
        "title": text[:100] or "(推文无文字)",
        "summary": text[:500],
        "publish_time": tw.get("created_at"),
        "duration_sec": ((vids[0].get("duration")) if vids else None),
        "resolution": f"{p.get('width')}x{p.get('height')}",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "stats": {"likes": tw.get("likes"), "replies": tw.get("replies"), "retweets": tw.get("retweets")},
        "method": "planB: api.fxtwitter.com 元数据 + video.twimg.com 直链",
        "discover": "WebSearch Lemmy 帖留档(MarioNawfal/SpaceX 推文及1080p直链)",
    }
else:
    # ---- 方案A: yt-dlp ----
    try:
        info = ytdlp_json(URL)
        fmt, height = pick_ytdlp_format(info, 1080, 95)
        log(PLAT, "extract", f"yt-dlp formats={len(info.get('formats', []))} 选定={fmt} 高度={height}")
        print(f"STEP yt-dlp: formats={len(info.get('formats', []))} fmt={fmt} h={height}")
    except Exception as e:
        log(PLAT, "fail", str(e))
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_x.py", RAWLOG,
               [f"target={URL}", str(e)[:250]], "yt-dlp twitter extractor 失败",
               "重试: --planb (fxtwitter API+直链)")
        finish(PLAT, False, f"yt-dlp失败: {str(e)[-140:]} (重试: --planb)")
        sys.exit(1)
    r = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                        f"{OUT}/x_{TID}.%(ext)s", URL], capture_output=True, text=True, timeout=900)
    out = find_out_file(OUT, f"x_{TID}")
    if r.returncode != 0 or not out:
        tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
        log(PLAT, "fail", f"下载: {tail[:250]}")
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_x.py", RAWLOG,
               [f"extract ok fmt={fmt}", f"download: {tail[:250]}"], "yt-dlp下载失败", "重试: --planb")
        finish(PLAT, False, f"下载失败: {tail[:120]} (重试: --planb)")
        sys.exit(1)
    p = probe(out)
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": info.get("webpage_url") or URL,
        "author": f"{info.get('uploader')} (@{USER})",
        "title": (info.get("title") or "")[:100],
        "summary": (info.get("description") or "")[:500],
        "publish_time": info.get("upload_date"),
        "duration_sec": info.get("duration"),
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height}p",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "view_count": info.get("view_count"), "like_count": info.get("like_count"),
        "method": f"yt-dlp twitter extractor(游客) fmt={fmt}",
        "discover": "WebSearch(Lemmy帖留档: SpaceX 官方筷子臂测试推文)",
    }

save_meta(PLAT, meta)
upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                    "resolution": meta["resolution"], "method": meta["method"]})
wentry(f"{PLAT}-download", "OK", "python3 tools/dl_x.py" + (" --planb" if PLANB else ""), RAWLOG,
       [f"target={meta['source_url']}", f"author={meta['author']}",
        f"file={meta['file']} size={p['size']} res={meta['resolution']}",
        f"method={meta['method']}"],
       "X视频下载成功", "下一平台: threads")
finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} {meta['author']}")
