#!/usr/bin/env python3
# Threads: tribixbite/yt-dlp-threads 插件(Googlebot UA SSR, 绕登录墙)
# 用法: dl_threads.py <post URL> [--planb]
# --planb: 手工 curl Googlebot UA + 正则 video_versions + og:meta
import requests, json, os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "threads"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/threads_001.txt"
URL = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
UA_GB = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
if not URL:
    finish(PLAT, False, "需要 post URL 参数")
    sys.exit(1)

pid_m = re.search(r"/post/([A-Za-z0-9_-]+)", URL)
PID = pid_m.group(1) if pid_m else "threads"
handle_m = re.search(r"@([A-Za-z0-9_.]+)", URL)
HANDLE = handle_m.group(1) if handle_m else ""

if PLANB:
    # ---- 方案B: 手工 Googlebot SSR 解析 ----
    r = requests.get(URL, headers={"User-Agent": UA_GB, "Accept-Language": "en"}, timeout=20)
    log(PLAT, "planB-fetch", f"http={r.status_code} bytes={len(r.text)}")
    m = re.search(r'"video_versions":(\[.*?\])', r.text)
    if not m:
        wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_threads.py {URL} --planb", RAWLOG,
               [f"http={r.status_code} bytes={len(r.text)}", "无 video_versions"],
               "Googlebot SSR 无视频数据", "未探索: /share/短链 / threads官方API / 用户给URL")
        finish(PLAT, False, f"planB无video_versions http={r.status_code}")
        sys.exit(1)
    try:
        vs = json.loads(m.group(1))
    except Exception:
        vs = json.loads(m.group(1).replace("\\/", "/"))
    v = max(vs, key=lambda x: x.get("width") or 0)
    vurl = v["url"]
    og = {}
    for k in ("og:title", "og:description"):
        mm = re.search(rf'<meta property="{k}" content="([^"]*)"', r.text)
        og[k] = mm.group(1) if mm else ""
    log(PLAT, "planB-extract", f"video_versions={len(vs)} 选中 width={v.get('width')} url={vurl[:100]}")
    out = f"{OUT}/threads_{PID}.mp4"
    size = download(vurl, out, {"User-Agent": UA_GB}, PLAT, 110)
    p = probe(out)
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": URL,
        "author": f"@{HANDLE}",
        "title": og.get("og:title", "")[:100] or "(无标题)",
        "summary": og.get("og:description", "")[:500],
        "publish_time": None,
        "duration_sec": None,
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"{v.get('width')}x{v.get('height')}",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "method": f"planB: Googlebot UA SSR + video_versions (width={v.get('width')})",
        "discover": "搜索提供URL",
    }
else:
    # ---- 方案A: yt-dlp-threads 插件 ----
    try:
        info = ytdlp_json(URL)
        fmt, height = pick_ytdlp_format(info, 1440, 95)
        log(PLAT, "extract", f"插件 formats={len(info.get('formats', []))} 选定={fmt} 高度={height} 时长={info.get('duration')}")
        print(f"STEP 插件: formats={len(info.get('formats', []))} fmt={fmt} h={height}")
    except Exception as e:
        log(PLAT, "fail", str(e))
        wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_threads.py {URL}", RAWLOG,
               [f"target={URL}", str(e)[:250]], "yt-dlp-threads 插件失败",
               "重试: --planb (Googlebot手工解析)")
        finish(PLAT, False, f"插件失败: {str(e)[-140:]} (重试: --planb)")
        sys.exit(1)
    r = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                        f"{OUT}/threads_{PID}.%(ext)s", URL], capture_output=True, text=True, timeout=900)
    out = find_out_file(OUT, f"threads_{PID}")
    if r.returncode != 0 or not out:
        tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
        log(PLAT, "fail", f"下载: {tail[:250]}")
        wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_threads.py {URL}", RAWLOG,
               [f"extract ok fmt={fmt}", f"download: {tail[:250]}"], "插件下载失败", "重试: --planb")
        finish(PLAT, False, f"下载失败: {tail[:120]} (重试: --planb)")
        sys.exit(1)
    p = probe(out)
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": info.get("webpage_url") or URL,
        "author": info.get("uploader") or f"@{HANDLE}",
        "title": (info.get("title") or "")[:100],
        "summary": (info.get("description") or "")[:500],
        "publish_time": None,
        "duration_sec": info.get("duration"),
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height}p",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "view_count": info.get("view_count"), "like_count": info.get("like_count"),
        "method": f"yt-dlp-threads 插件(Googlebot SSR) fmt={fmt}",
        "discover": "搜索提供URL",
    }

save_meta(PLAT, meta)
upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                    "resolution": meta["resolution"], "method": meta["method"]})
wentry(f"{PLAT}-download", "OK", f"python3 tools/dl_threads.py {URL}" + (" --planb" if PLANB else ""), RAWLOG,
       [f"target={meta['source_url']}", f"author={meta['author']}",
        f"file={meta['file']} size={p['size']} res={meta['resolution']}",
        f"method={meta['method']}"],
       "Threads视频下载成功", "收尾: REPORT.md")
finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} @{meta['author']}")
