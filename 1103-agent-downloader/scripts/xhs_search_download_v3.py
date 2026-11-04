#!/usr/bin/env python3
"""小红书 搜索→下载 全链路 v3 定稿 (零LLM token)
链路: Netscape全量cookie → Playwright state注入(agent-browser) → 搜索页 →
      点「筛选→视频」(纯UI, 不碰签名) → 抽xsec_token链接 → yt-dlp --cookies下载
用法: python3 xhs_search_download_v3.py <关键词> [保存目录]
cookie: /home/z/my-project/.secrets/cookies/xiaohongshu_cookies.txt (Netscape格式, 需web_session+a1)
实测: 2026-11-04 "万智牌" 筛选后20条全视频笔记
"""
import json, os, subprocess, sys, urllib.parse, time

COOKIE_FILE = "/home/z/my-project/.secrets/cookies/xiaohongshu_cookies.txt"
STATE_FILE = "/home/z/my-project/.secrets/cookies/xhs_state.json"
KW = sys.argv[1] if len(sys.argv) > 1 else "万智牌"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else f"/home/z/my-project/download/1103-agent-downloader/downloads/xiaohongshu/search_{KW}"
os.makedirs(OUTDIR, exist_ok=True)

def ab(*args, timeout=60):
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    return ((r.stdout or "") + (r.stderr or "")).strip()

def ab_eval(js, timeout=60):
    val = ab("eval", js, timeout=timeout)
    for _ in range(2):
        if isinstance(val, str) and (val.startswith('"') and val.endswith('"') or val.startswith(("[", "{"))):
            try:
                val = json.loads(val)
            except Exception:
                break
        else:
            break
    return val

def netscape_to_state(path):
    cookies = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        domain, _, path_, secure, expires, name, value = parts
        c = {"name": name, "value": value,
             "domain": domain if domain.startswith(".") else "." + domain,
             "path": path_, "secure": secure.upper() == "TRUE",
             "httpOnly": name in ("web_session", "id_token", "x-rednote-datactry", "x-rednote-holderctry")}
        try:
            exp = int(expires)
            c["expires"] = exp if exp > 0 else -1
        except ValueError:
            c["expires"] = -1
        cookies.append(c)
    return {"cookies": cookies, "origins": []}

# ---- Step 1-2: cookie注入 ----
state = netscape_to_state(COOKIE_FILE)
with open(STATE_FILE, "w") as f:
    json.dump(state, f)
ab("close")
ab("state", "load", STATE_FILE, timeout=60)
print(f"[1/7] cookie注入: {len(state['cookies'])}枚 (含a1+web_session)")

# ---- Step 3: 搜索页 ----
qkw = urllib.parse.quote(KW)
ab("open", f"https://www.xiaohongshu.com/search_result?keyword={qkw}", timeout=90)
time.sleep(6)
st = ab_eval("JSON.stringify({err: location.href.includes('website-login/error'), wall: /Log in to view|扫码登录/.test(document.body.innerText), title: document.title})")
print(f"[2/7] 搜索页: {st}")
if not isinstance(st, dict) or st.get("err") or st.get("wall"):
    print("被风控/登录墙拦截 — cookie 可能失效")
    sys.exit(1)

# ---- Step 4: 点 筛选→视频 ----
r1 = ab_eval("JSON.stringify((function(){const els=[...document.querySelectorAll('div,span')].filter(e=>e.childElementCount===0&&e.innerText==='筛选'); if(!els.length) return 'NO_BTN'; els[els.length-1].click(); return 'OK';})())")
time.sleep(1.5)
r2 = ab_eval("JSON.stringify((function(){const els=[...document.querySelectorAll('span,div')].filter(e=>e.childElementCount===0&&e.innerText==='视频'); if(!els.length) return 'NO_OPT'; els[els.length-1].click(); return 'OK';})())")
time.sleep(4)
print(f"[3/7] 视频筛选: 筛选btn={r1} 视频opt={r2}")

# ---- Step 5: 抽链接 ----
links = ab_eval("""(async () => {
  await new Promise(r => setTimeout(r, 2000));
  const hs = [...new Set([...document.querySelectorAll('a[href*="/search_result/"], a[href*="/explore/"], a[href*="/discovery/item/"]')]
    .map(a => a.getAttribute('href')).filter(h => h && h.includes('xsec_token')))];
  return JSON.stringify(hs.slice(0, 25));
})()""", timeout=60)
if not isinstance(links, list) or not links:
    print(f"[4/7] 无链接: {links}")
    sys.exit(1)
print(f"[4/7] 抽到 {len(links)} 条视频笔记链接")

# ---- Step 6: yt-dlp 下载第一条视频 ----
target, meta_info = None, None
for link in links[:5]:
    url = link if link.startswith("http") else f"https://www.xiaohongshu.com{link}"
    p = subprocess.run(["/home/z/.venv/bin/yt-dlp", "--dump-json", "--no-warnings",
                        "--cookies", COOKIE_FILE, url], capture_output=True, text=True, timeout=120)
    if p.returncode == 0 and p.stdout.strip():
        j = json.loads(p.stdout.splitlines()[0])
        if j.get("ext") == "mp4" or any((f.get("vcodec") or "none") != "none" for f in j.get("formats", [])):
            target, meta_info = url, j
            break
if not target:
    print("[5/7] 前5条无视频")
    sys.exit(1)
print(f"[5/7] 选定: {meta_info.get('title','')[:50]}")

fname = os.path.join(OUTDIR, f"xhs_{meta_info['id'][:24]}.mp4")
p = subprocess.run(["/home/z/.venv/bin/yt-dlp", "-f", "best", "-o", fname, "--no-warnings",
                    "--cookies", COOKIE_FILE, target], capture_output=True, text=True, timeout=900)
size_mb = os.path.getsize(fname) / 1048576 if os.path.exists(fname) else 0
if size_mb < 0.05:
    print(f"[6/7] 下载失败: {(p.stderr or '')[-300:]}")
    sys.exit(1)
print(f"[6/7] 下载: {size_mb:.1f}MB")

# ---- Step 7: 体检+meta ----
fp = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", fname], capture_output=True, text=True)
stream = next((s for s in json.loads(fp.stdout or "{}").get("streams", []) if s.get("codec_type") == "video"), {})
meta = {
    "platform": "xiaohongshu",
    "method": "agent-browser + 全量cookie(Playwright state load) + UI视频筛选(筛选→视频) + yt-dlp --cookies",
    "search_keyword": KW, "note_id": meta_info["id"][:24], "source_url": target,
    "author": meta_info.get("uploader") or meta_info.get("channel"),
    "title": (meta_info.get("title") or "").replace(" - 小红书", ""),
    "video": {"resolution": f"{stream.get('width','?')}x{stream.get('height','?')}",
              "codec": stream.get("codec_name"), "duration_s": float(meta_info.get("duration", 0))},
    "file": os.path.basename(fname), "size_mb": round(size_mb, 2),
    "search_hits_preview": links[:5],
}
with open(os.path.join(OUTDIR, "meta.json"), "w") as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
print(f"DONE {stream.get('width','?')}x{stream.get('height','?')} {size_mb:.1f}MB -> {OUTDIR}")
