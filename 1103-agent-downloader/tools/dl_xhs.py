#!/usr/bin/env python3
# 小红书: 用户给定 xsec_token 分享链 → yt-dlp XiaoHongShu extractor(匿名档)
# --planb: 直接解析页面 __INITIAL_STATE__ 提取视频流(递归找 masterUrl)
import requests, json, os, sys, re, subprocess, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "xiaohongshu"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/xiaohongshu_001.txt"
NOTE_URL = ("https://www.xiaohongshu.com/discovery/item/6ae70cc2000000000602374d"
            "?source=webshare&xhsshare=pc_web&xsec_token=ABkoBqM9GMVdo1NVmw_Y6JKBLjknYMEg4LoEXLOXOsQJ0=&xsec_source=pc_share")
NOTE_ID = "6ae70cc2000000000602374d"

def planb_fetch():
    S = requests.Session()
    S.headers.update({"User-Agent": UA_PC,
                      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                      "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    r = S.get(NOTE_URL, timeout=20, allow_redirects=True)
    log(PLAT, "planB-fetch", f"http={r.status_code} final={r.url[:90]} bytes={len(r.text)}")
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", r.text, re.S)
    if not m:
        raise RuntimeError(f"无__INITIAL_STATE__ http={r.status_code} bytes={len(r.text)} 前200字={r.text[:200]}")
    raw = re.sub(r":\s*undefined", ":null", m.group(1))
    try:
        data = json.loads(raw)
    except Exception:
        data = json.loads(urllib.parse.unescape(raw))
    streams, notes = [], []

    def walk(o):
        if isinstance(o, dict):
            if "masterUrl" in o or "master_url" in o:
                streams.append(o)
            if o.get("noteId") and ("desc" in o or "title" in o):
                notes.append(o)
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    if not streams:
        raise RuntimeError(f"INITIAL_STATE无视频流 streams=0 notes={len(notes)} (可能是图文笔记)")
    def su(s):
        return (s.get("masterUrl") or s.get("master_url")
                or ((s.get("backupUrls") or s.get("backup_urls") or [None])[0]))
    stream = max(streams, key=lambda s: s.get("width") or 0)
    note = next((n for n in notes if str(n.get("noteId")) == NOTE_ID), None) or (notes[0] if notes else {})
    log(PLAT, "planB-extract", f"streams={len(streams)} 选中width={stream.get('width')} codec={stream.get('videoCodec') or stream.get('codec') or stream.get('streamType')}")
    return stream, su(stream), note

if PLANB:
    try:
        stream, vurl, note = planb_fetch()
    except Exception as e:
        log(PLAT, "fail", str(e))
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_xhs.py --planb", RAWLOG,
               [f"target={NOTE_URL}", str(e)[:250]], "planB解析失败", "记录未探索路径(XHS-Downloader等), 结束本平台")
        finish(PLAT, False, f"planB失败: {str(e)[:130]}")
        sys.exit(1)
    out = f"{OUT}/xhs_{NOTE_ID}.mp4"
    try:
        size = download(vurl, out, {"User-Agent": UA_PC, "Referer": "https://www.xiaohongshu.com/",
                                    "Origin": "https://www.xiaohongshu.com"}, PLAT, 110)
    except Exception as e:
        log(PLAT, "fail", f"planB下载: {e}")
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_xhs.py --planb", RAWLOG,
               [f"vurl={str(vurl)[:150]}", f"error={str(e)[:250]}"], "planB下载失败", "结束本平台, 记录未探索路径")
        finish(PLAT, False, f"planB下载失败: {str(e)[:120]}")
        sys.exit(1)
    p = probe(out)
    user = note.get("user") or {}
    desc = note.get("desc") or ""
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": NOTE_URL,
        "source_url_canonical": f"https://www.xiaohongshu.com/explore/{NOTE_ID}",
        "author": f"{user.get('nickname')} (userId={user.get('userId') or user.get('userid')})",
        "title": note.get("title") or desc[:60],
        "summary": desc[:500],
        "publish_time": note.get("time") or note.get("lastUpdateTime"),
        "duration_sec": (stream.get("duration") or (stream.get("avgBitrate") and None)),
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"{stream.get('width')}x{stream.get('height')}",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "stats": {"like": ((note.get("interactInfo") or {}).get("likedCount"))},
        "method": f"planB: __INITIAL_STATE__ 解析 (width={stream.get('width')}, {stream.get('videoCodec') or stream.get('codec')})",
        "discover": "用户提供分享链接(带xsec_token)",
    }
else:
    # ---- 方案A: yt-dlp XiaoHongShu extractor ----
    try:
        info = ytdlp_json(NOTE_URL)
        fmt, height = pick_ytdlp_format(info, 2160, 95)
        log(PLAT, "extract", f"yt-dlp formats={len(info.get('formats', []))} 选定={fmt} 高度={height}")
        print(f"STEP yt-dlp: formats={len(info.get('formats', []))} fmt={fmt} h={height}")
    except Exception as e:
        log(PLAT, "fail", str(e))
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_xhs.py", RAWLOG,
               [f"target={NOTE_URL}", str(e)[:250]], "yt-dlp XiaoHongShu extractor 失败",
               "重试: --planb (__INITIAL_STATE__解析)")
        finish(PLAT, False, f"yt-dlp失败: {str(e)[-140:]} (重试: --planb)")
        sys.exit(1)
    r = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                        f"{OUT}/xhs_{NOTE_ID}.%(ext)s", NOTE_URL],
                       capture_output=True, text=True, timeout=900)
    out = find_out_file(OUT, f"xhs_{NOTE_ID}")
    if r.returncode != 0 or not out:
        tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
        log(PLAT, "fail", f"下载: {tail[:250]}")
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_xhs.py", RAWLOG,
               [f"extract ok fmt={fmt}", f"download: {tail[:250]}"], "yt-dlp下载失败", "重试: --planb")
        finish(PLAT, False, f"下载失败: {tail[:120]} (重试: --planb)")
        sys.exit(1)
    p = probe(out)
    meta = {
        "platform": PLAT, "status": "ok",
        "source_url": NOTE_URL,
        "source_url_canonical": f"https://www.xiaohongshu.com/explore/{NOTE_ID}",
        "author": info.get("uploader") or info.get("channel"),
        "title": info.get("title"),
        "summary": (info.get("description") or "")[:500],
        "publish_time": None,
        "duration_sec": info.get("duration"),
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height}p",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "method": f"yt-dlp XiaoHongShu extractor(匿名) fmt={fmt}",
        "discover": "用户提供分享链接(带xsec_token)",
    }

save_meta(PLAT, meta)
upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                    "resolution": meta["resolution"], "method": meta["method"]})
wentry(f"{PLAT}-download", "OK", "python3 tools/dl_xhs.py" + (" --planb" if PLANB else ""), RAWLOG,
       [f"target={meta['source_url_canonical']}", f"author={meta['author']}",
        f"file={meta['file']} size={p['size']} res={meta['resolution']}",
        f"method={meta['method']}"],
       "小红书视频下载成功", "下一平台: douyin")
finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} {meta['author']}")
