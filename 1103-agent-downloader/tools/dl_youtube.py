#!/usr/bin/env python3
# YouTube: ytsearch 自发现 → yt-dlp(player_client=ios,web_safari) 下载 ≤1080p ≤90MB
# --planb: player_client=web,android_vr,tv_downgraded (唯一一次换法重试)
# 再失败不再尝试: bgutil POT provider(node server) / burner cookies 记录为未探索路径
import subprocess, json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "youtube"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/youtube_001.txt"
ARGS = (["--extractor-args", "youtube:player_client=web,android_vr,tv_downgraded"] if PLANB
        else ["--extractor-args", "youtube:player_client=ios,web_safari"])

def search_pick():
    r = subprocess.run([YTDLP, "--flat-playlist", "--no-warnings", "--print",
                        "%(id)s|%(duration)s|%(title)s", "ytsearch10:AI agent"],
                       capture_output=True, text=True, timeout=180)
    cands = []
    for line in r.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            try:
                d = int(float(parts[1])) if parts[1] not in ("NA", "None", "") else -1
            except ValueError:
                d = -1
            if 45 <= d <= 600:
                cands.append((abs(d - 150), parts[0], d, parts[2]))
    if not cands:
        log(PLAT, "discover", f"ytsearch10:AI agent 无45-600s结果 rc={r.returncode} err={(r.stderr or '')[:200]}")
        return None
    cands.sort()
    _, vid, dur, title = cands[0]
    log(PLAT, "discover", f"ytsearch10:AI agent 命中 {vid} dur={dur}s title={title[:60]}")
    return vid, dur, title

picked = search_pick()
if not picked:
    wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_youtube.py", RAWLOG,
           ["ytsearch10:AI agent 无 45-600s 候选"], "自发现失败", "改用已知视频ID重试")
    finish(PLAT, False, "ytsearch无合适候选")
    sys.exit(1)
vid, dur, title = picked
url = f"https://www.youtube.com/watch?v={vid}"
print(f"STEP 目标: {url} | {title[:40]} | {dur}s")

try:
    info = ytdlp_json(url, ARGS)
except Exception as e:
    log(PLAT, "fail", str(e))
    wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_youtube.py{' --planb' if PLANB else ''}", RAWLOG,
           [f"target={url}", f"extractor_args={ARGS[1]}", str(e)[:250]],
           "yt-dlp 提取失败(疑似bot-check)" if "bot" in str(e).lower() or "sign in" in str(e).lower() else "yt-dlp 提取失败",
           "重试: --planb; 未探索: bgutil POT provider(node) / burner cookies")
    finish(PLAT, False, f"提取失败: {str(e)[-140:]} (重试: --planb)")
    sys.exit(1)

fmt, height = pick_ytdlp_format(info, 1080, 90)
log(PLAT, "extract", f"formats={len(info.get('formats', []))} 选定={fmt} 高度={height} 时长={info.get('duration')}")
print(f"STEP yt-dlp: formats={len(info.get('formats', []))} fmt={fmt} h={height}")

r = subprocess.run([YTDLP, *ARGS, "-f", fmt, "--merge-output-format", "mp4", "-o",
                    f"{OUT}/youtube_{vid}.%(ext)s", url], capture_output=True, text=True, timeout=1200)
out = find_out_file(OUT, f"youtube_{vid}")
if r.returncode != 0 or not out:
    tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
    log(PLAT, "fail", f"下载: {tail[:250]}")
    wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_youtube.py{' --planb' if PLANB else ''}", RAWLOG,
           [f"target={url}", f"extract ok fmt={fmt}", f"download: {tail[:250]}"],
           "提取成功但下载失败", "重试: --planb; 未探索: bgutil POT / cookies / aria2c -x8")
    finish(PLAT, False, f"下载失败: {tail[:120]} (重试: --planb)")
    sys.exit(1)

p = probe(out)
ud = info.get("upload_date") or ""
meta = {
    "platform": PLAT, "status": "ok",
    "source_url": info.get("webpage_url") or url,
    "author": f"{info.get('uploader')} (channel={info.get('channel')})",
    "title": info.get("title"),
    "summary": (info.get("description") or "")[:500],
    "publish_time": f"{ud[:4]}-{ud[4:6]}-{ud[6:]}" if len(ud) == 8 else ud,
    "duration_sec": info.get("duration"),
    "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height}p",
    "size_bytes": p["size"], "file": os.path.basename(out),
    "view_count": info.get("view_count"), "like_count": info.get("like_count"),
    "method": f"yt-dlp {ARGS[1]} fmt={fmt}",
    "discover": "yt-dlp ytsearch10:AI agent",
}
save_meta(PLAT, meta)
upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                    "resolution": meta["resolution"], "method": meta["method"]})
wentry(f"{PLAT}-download", "OK", f"python3 tools/dl_youtube.py{' --planb' if PLANB else ''}", RAWLOG,
       [f"target={meta['source_url']}", f"author={meta['author']}",
        f"file={meta['file']} size={p['size']} res={meta['resolution']}",
        f"method={meta['method']}"],
       "YouTube下载成功", "下一平台: x")
finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} {meta['author']}")
