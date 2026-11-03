#!/usr/bin/env python3
# 抖音: 分享短链→aweme_id → iesdouyin 分享页SSR(iOS UA) → bit_rate最高档 → playwm→play + ratio=default → 下载
# 用法: dl_douyin.py [URL] [--planb]
# --planb: yt-dlp Douyin extractor(findings B13: 已知失效, 只按预算试一次)
# 未探索(不再尝试): TikTokDownloader(扫码登录) / playwright真浏览器
import requests, json, os, sys, re, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_media import *

PLAT = "douyin"
OUT = f"{WORK}/downloads/{PLAT}"
os.makedirs(OUT, exist_ok=True)
PLANB = "--planb" in sys.argv
RAWLOG = "logs/douyin_001.txt"
DEFAULT = "https://v.douyin.com/kcvMpuN/"   # 探测存活的示例短链 → aweme 6915675899241450760
target = next((a for a in sys.argv[1:] if not a.startswith("--")), DEFAULT)

S = requests.Session()
S.headers.update({"User-Agent": UA_IOS, "Accept-Language": "zh-CN,zh;q=0.9"})

def resolve_aweme(u):
    r = S.get(u, timeout=20, allow_redirects=True)
    m = re.search(r"/(?:video|note)/(\d{15,21})", r.url)
    log(PLAT, "resolve", f"{u} -> {r.url[:110]}")
    if m:
        return m.group(1)
    m2 = re.search(r'"(?:aweme_id|itemId)":\s*"?(\d{15,21})', r.text)
    return m2.group(1) if m2 else None

def fetch_item(aid):
    r = S.get(f"https://www.iesdouyin.com/share/video/{aid}/", timeout=20)
    m = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", r.text, re.S)
    if not m:
        raise RuntimeError(f"分享页无_ROUTER_DATA http={r.status_code} bytes={len(r.text)}")
    data = json.loads(m.group(1))
    items = []

    def walk(o):
        if isinstance(o, dict):
            if "aweme_id" in o and isinstance(o.get("video"), dict):
                items.append(o)
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    if not items:
        raise RuntimeError(f"_ROUTER_DATA无item(删除/风控?) loaderData keys={list(data.get('loaderData', {}).keys())[:5]}")
    return max(items, key=lambda i: len(json.dumps(i.get("video", {}).get("bit_rate") or [])))

def finish_ok(aid, out, p, meta):
    save_meta(PLAT, meta)
    upsert_state(PLAT, {"ok": True, "file": meta["file"], "size_mb": round(p["size"] / 1e6, 1),
                        "resolution": meta["resolution"], "method": meta["method"]})
    wentry(f"{PLAT}-download", "OK", f"python3 tools/dl_douyin.py {target}" + (" --planb" if PLANB else ""), RAWLOG,
           [f"aweme_id={aid}", f"author={meta['author']}",
            f"file={meta['file']} size={p['size']} res={meta['resolution']}",
            f"method={meta['method']}"],
           "抖音视频下载成功", "下一平台: threads")
    finish(PLAT, True, f"{meta['file']} {p['size']/1e6:.1f}MB {meta['resolution']} @{meta['author']}")

def fail(msg, nxt):
    wentry(f"{PLAT}-download", "FAIL", f"python3 tools/dl_douyin.py {target}" + (" --planb" if PLANB else ""), RAWLOG,
           [f"target={target}", str(msg)[:250]], "失败", nxt)
    finish(PLAT, False, f"{str(msg)[:140]} | next: {nxt}")
    sys.exit(1)

if PLANB:
    m = re.search(r"/video/(\d{15,21})", target) or re.search(r"status/(\d{15,21})", target)
    url = f"https://www.douyin.com/video/{m.group(1)}/" if m else target
    try:
        info = ytdlp_json(url)
        fmt, height = pick_ytdlp_format(info, 1080, 95)
    except Exception as e:
        log(PLAT, "fail", str(e))
        fail(str(e), "未探索: TikTokDownloader(扫码) / playwright真浏览器")
    r = subprocess.run([YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                        f"{OUT}/%(id)s.%(ext)s", url], capture_output=True, text=True, timeout=900)
    out = find_out_file(OUT, m.group(1) if m else "douyin")
    if r.returncode != 0 or not out:
        tail = ((r.stderr or "").strip().splitlines()[-1:] or ["(empty)"])[0]
        fail(tail, "未探索: TikTokDownloader / playwright")
    p = probe(out)
    meta = {"platform": PLAT, "status": "ok", "source_url": url,
            "author": info.get("uploader"), "title": info.get("title"),
            "summary": (info.get("description") or "")[:500], "duration_sec": info.get("duration"),
            "resolution": f"{p.get('width')}x{p.get('height')}", "size_bytes": p["size"],
            "file": os.path.basename(out), "method": f"planB: yt-dlp fmt={fmt}",
            "discover": "示例短链(工具文档)"}
    finish_ok(m.group(1) if m else "?", out, p, meta)
    sys.exit(0)

# ---- 方案A: iesdouyin 分享页 SSR 五步法 ----
aid = resolve_aweme(target)
if not aid:
    fail("短链解析不出aweme_id", "换目标URL重跑方案A")
print(f"STEP aweme_id={aid}")

try:
    item = fetch_item(aid)
except Exception as e:
    log(PLAT, "fail", str(e))
    fail(e, "重试: --planb (yt-dlp)")
    sys.exit(1)

desc = item.get("desc", "")
author = item.get("author") or {}
stats = item.get("statistics") or {}
brs = (item.get("video") or {}).get("bit_rate") or []
if not brs:
    fail("item无bit_rate(可能是图集)", "换视频类目标")
br = max(brs, key=lambda b: b.get("bitrate") or 0)
pa = br.get("play_addr") or {}
uri = pa.get("uri", "")
vurl = (pa.get("url_list") or [None])[0]
log(PLAT, "extract", f"gear={br.get('gear_name')} bitrate={br.get('bitrate')} uri={uri[:60]}")
print(f"STEP gear={br.get('gear_name')} bitrate={br.get('bitrate')}")
if vurl:
    vurl = vurl.replace("/playwm/", "/play/")                     # B14: playwm 忽略ratio且带水印
    if "ratio=" in vurl:
        vurl = re.sub(r"ratio=[^&]+", "ratio=default", vurl)      # ratio=default = 原始master
    else:
        vurl += ("&" if "?" in vurl else "?") + "ratio=default"
    log(PLAT, "rewrite", f"改写后URL={vurl[:130]}")

out = f"{OUT}/douyin_{aid}.mp4"
try:
    size = download(vurl, out, {"User-Agent": UA_IOS, "Referer": "https://www.douyin.com/"}, PLAT, 110)
    log(PLAT, "download", f"主URL直下 size={size}")
except Exception as e:
    alt = f"https://www.iesdouyin.com/aweme/v1/play/?video_id={uri}&ratio=default&line=0"
    log(PLAT, "fallback-url", f"主URL失败({e}); 改构造端点: {alt[:100]}")
    try:
        size = download(alt, out, {"User-Agent": UA_IOS}, PLAT, 110)
    except Exception as e2:
        fail(f"主URL={e} / 构造端点={e2}", "重试: --planb")

p = probe(out)
ct = item.get("create_time")
meta = {
    "platform": PLAT, "status": "ok",
    "source_url": f"https://www.douyin.com/video/{aid}",
    "source_url_share": target,
    "author": f"{author.get('nickname')} (uid={author.get('uid')}, sec_uid={str(author.get('sec_uid') or '')[:30]}...)",
    "title": desc[:80] or "(无文案)",
    "summary": desc[:500],
    "publish_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(ct)) if ct else None,
    "duration_sec": (item.get("video") or {}).get("duration") or (((item.get("video") or {}).get("bit_rate") or [{}])[0].get("duration")),
    "resolution": f"{p.get('width')}x{p.get('height')}" if p.get("width") else (f"{(item.get('video') or {}).get('width')}x{(item.get('video') or {}).get('height')}" if (item.get('video') or {}).get('width') else "未知"),
    "size_bytes": p["size"], "file": os.path.basename(out),
    "stats": {"digg": stats.get("digg_count"), "comment": stats.get("comment_count"), "share": stats.get("share_count")},
    "method": f"iesdouyin分享页SSR(iOS UA) gear={br.get('gear_name')} playwm→play ratio=default",
    "discover": "示例短链v.douyin.com/kcvMpuN (douyin-downloader文档示例, 探测存活)",
}
finish_ok(aid, out, p, meta)
