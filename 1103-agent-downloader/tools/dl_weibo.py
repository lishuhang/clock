#!/usr/bin/env python3
# 微博: m.weibo.cn 容器API自发现(央视新闻/人民日报时间线) → yt-dlp Weibo extractor(游客, 自动cookie)
# 失败重试(1次): --planb = m.weibo.cn API 直接下载 stream_url_hd
import requests, json, os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "weibo"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/weibo_001.txt"

S = requests.Session()
S.headers.update({"User-Agent": UA_MOBILE, "Referer": "https://m.weibo.cn/",
                  "X-Requested-With": "XMLHttpRequest", "MWeibo-Pwa": "1"})

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").replace("\n", " ").strip()

def discover():
    S.get("https://m.weibo.cn/", timeout=15)  # 预热取cookie
    for uid, name in (("2656274875", "央视新闻"), ("2803301701", "人民日报")):
        for page in (1, 2):
            r = S.get("https://m.weibo.cn/api/container/getIndex",
                      params={"type": "uid", "value": uid, "containerid": f"107603{uid}", "page": page},
                      timeout=15)
            try:
                j = r.json()
            except Exception:
                j = {}
            if j.get("ok") != 1:
                log(PLAT, "discover", f"uid={uid}({name}) page={page} ok={j.get('ok')} msg={j.get('msg')} http={r.status_code}")
                continue
            for card in j.get("data", {}).get("cards", []):
                mb = card.get("mblog") or {}
                pi = mb.get("page_info") or {}
                mi = pi.get("media_info") or {}
                if pi.get("type") == "video" and (mi.get("stream_url_hd") or mi.get("stream_url")):
                    log(PLAT, "discover", f"uid={uid}({name}) 命中 bid={mb.get('bid')} 文案={strip_html(mb.get('text',''))[:50]}")
                    return mb
            log(PLAT, "discover", f"uid={uid}({name}) page={page} 无视频卡片")
    return None

def build_meta(mb, out, p, method, height=None, info=None):
    bid = mb["bid"]
    text = strip_html(mb.get("text", ""))
    user = mb.get("user", {})
    mi = (mb.get("page_info") or {}).get("media_info") or {}
    return {
        "platform": PLAT, "status": "ok",
        "source_url": f"https://m.weibo.cn/status/{bid}",
        "source_url_canonical": f"https://weibo.com/{user.get('id','')}/{bid}",
        "author": f"{user.get('screen_name')} (uid={user.get('id')})",
        "title": text[:60] or "(无文案)",
        "summary": text[:500],
        "publish_time": mb.get("created_at"),
        "duration_sec": (info or {}).get("duration") or mi.get("duration"),
        "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height or '?'}p",
        "size_bytes": p["size"], "file": os.path.basename(out),
        "stats": {"like": mb.get("attitudes_count"), "comment": mb.get("comments_count"),
                  "repost": mb.get("reposts_count")},
        "method": method,
        "discover": "m.weibo.cn/api/container/getIndex (央视新闻/人民日报时间线, 免登录)",
    }

mb = None if PLANB else discover()
if not PLANB and not mb:
    wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_weibo.py", RAWLOG,
           ["容器API getIndex 两账号×两页 均未命中视频微博(ok=-100, 需JS级cookie)"],
           "自发现失败", "重试: --planb (yt-dlp WeiboUser extractor)")
    finish(PLAT, False, "自发现失败(容器API无视频微博)")
    sys.exit(1)

if not PLANB:
    bid = mb["bid"]
    status_url = f"https://m.weibo.cn/status/{bid}"
    print(f"STEP 目标: {status_url} @{mb.get('user',{}).get('screen_name')} | {strip_html(mb.get('text',''))[:40]}")

if PLANB:
    # ---- 方案B: yt-dlp Weibo extractor + (给定URL 或 WeiboUser自发现) ----
    arg_url = next((a for a in sys.argv[1:] if a.startswith("http") and "weibo" in a), None)
    if arg_url:
        log(PLAT, "planB", f"使用给定URL: {arg_url}")
        entries = [(arg_url.rstrip("/").split("/")[-1], arg_url, "")]
    else:
        log(PLAT, "planB", "改用 yt-dlp WeiboUser extractor 自发现(央视新闻 u/2656274875)")
        rr = subprocess.run([YTDLP, "--flat-playlist", "--no-warnings", "--print",
                             "%(id)s|%(url)s|%(title).60B", "--playlist-items", "1:20",
                             "https://m.weibo.cn/u/2656274875"], capture_output=True, text=True, timeout=300)
        entries = []
        for l in rr.stdout.splitlines():
            parts = l.split("|", 2)
            if len(parts) == 3 and parts[0].strip():
                entries.append(parts)
        log(PLAT, "planB-discover",
            f"entries={len(entries)} ids={[e[0] for e in entries[:5]]} err={(rr.stderr or '')[-180:]}")
        print(f"STEP planB自发现: {len(entries)}条")
    ok_meta = None
    for eid, eurl, etitle in entries[:5]:
        eid = eid.strip()
        eurl = eurl.strip()
        if eurl in ("NA", "None", ""):
            eurl = f"https://m.weibo.cn/status/{eid}"
        try:
            info = ytdlp_json(eurl)
        except Exception as e:
            log(PLAT, "planB", f"条目 {eid} 非视频/失败: {str(e)[-120:]}")
            continue
        fmt, height = pick_ytdlp_format(info, 1080, 90)
        d = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                            f"{OUT}/weibo_{eid}.%(ext)s", eurl], capture_output=True, text=True, timeout=900)
        out = find_out_file(OUT, f"weibo_{eid}")
        if d.returncode == 0 and out:
            p = probe(out)
            ok_meta = {
                "platform": PLAT, "status": "ok",
                "source_url": info.get("webpage_url") or eurl,
                "author": info.get("uploader") or "央视新闻",
                "title": (info.get("title") or etitle or "")[:60],
                "summary": (info.get("description") or etitle or "")[:500],
                "publish_time": None,
                "duration_sec": info.get("duration"),
                "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else f"~{height}p",
                "size_bytes": p["size"], "file": os.path.basename(out),
                "view_count": info.get("view_count"), "like_count": info.get("like_count"),
                "method": f"planB: yt-dlp WeiboUser自发现 + Weibo extractor(游客) fmt={fmt}",
                "discover": "yt-dlp WeiboUser extractor (m.weibo.cn/u/2656274875, 免登录)",
            }
            bid = eid
            break
        log(PLAT, "planB", f"条目 {eid} 下载失败: {((d.stderr or '').strip().splitlines()[-1:] or ['?'])[0][:150]}")
    if not ok_meta:
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_weibo.py --planb", RAWLOG,
               [f"entries={len(entries)} 前5条均非视频或下载失败"],
               "WeiboUser 通路失败", "未探索: 修XSRF cookie走容器API / gallery-dl weibo / 用户给URL")
        finish(PLAT, False, "planB(WeiboUser)失败")
        sys.exit(1)
    meta = ok_meta
    mb = {"user": {"screen_name": meta["author"]}}
else:
    # ---- 方案A: yt-dlp ----
    try:
        info = ytdlp_json(status_url)
        fmt, height = pick_ytdlp_format(info, 1080, 90)
        log(PLAT, "extract", f"yt-dlp formats={len(info.get('formats', []))} 选定={fmt} 高度={height} 时长={info.get('duration')}")
        print(f"STEP yt-dlp: formats={len(info.get('formats', []))} fmt={fmt} h={height}")
    except Exception as e:
        log(PLAT, "fail", str(e))
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_weibo.py", RAWLOG,
               [f"target={status_url}", str(e)[:250]],
               "yt-dlp Weibo extractor 提取失败", "重试: --planb (API直下)")
        finish(PLAT, False, f"yt-dlp提取失败: {str(e)[-140:]} (重试: --planb)")
        sys.exit(1)
    r = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                        f"{OUT}/weibo_{bid}.%(ext)s", status_url],
                       capture_output=True, text=True, timeout=900)
    out = find_out_file(OUT, f"weibo_{bid}")
    if r.returncode != 0 or not out:
        tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
        log(PLAT, "fail", f"yt-dlp下载: {tail[:250]}")
        wentry(f"{PLAT}-download", "FAIL", "python3 tools/dl_weibo.py", RAWLOG,
               [f"target={status_url}", f"extract ok fmt={fmt}", f"download: {tail[:250]}"],
               "yt-dlp 提取成功但下载失败", "重试: --planb (API直下)")
        finish(PLAT, False, f"下载失败: {tail[:120]} (重试: --planb)")
        sys.exit(1)
    p = probe(out)
    meta = build_meta(mb, out, p, f"yt-dlp Weibo extractor(游客) fmt={fmt}", height, info)

save_meta(PLAT, meta)
upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                    "resolution": meta["resolution"], "method": meta["method"]})
wentry(f"{PLAT}-download", "OK", "python3 tools/dl_weibo.py" + (" --planb" if PLANB else ""), RAWLOG,
       [f"target={meta['source_url']}", f"author={meta['author']}",
        f"file={meta['file']} size={p['size']} res={meta['resolution']} dur={meta['duration_sec']}",
        f"method={meta['method']}"],
       "微博视频下载成功", "下一平台: bilibili")
finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} @{mb.get('user',{}).get('screen_name')}")
