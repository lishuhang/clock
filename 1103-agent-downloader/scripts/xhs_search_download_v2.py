#!/usr/bin/env python3
"""小红书 搜索→下载 全链路 v2 (零LLM token) — 全量cookie经Playwright state注入
改进 vs v1: web_session是httpOnly, document.cookie种不进 → 转Netscape为storage state,
agent-browser state load 一次性注入全部cookie(含a1设备指纹, 签名绑定它)
用法: python3 xhs_search_download_v2.py <关键词> [保存目录]
cookie: /home/z/my-project/.secrets/cookies/xiaohongshu_cookies.txt (Netscape格式)
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

# ---- Step 1: Netscape → Playwright storage state ----
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
        c = {
            "name": name, "value": value,
            "domain": domain if domain.startswith(".") else "." + domain,
            "path": path_,
            "secure": secure.upper() == "TRUE",
            "httpOnly": False,  # Netscape 第6列是httpOnly
        }
        # httpOnly 列 (第7列前的第6列FALSE/TRUE) — Netscape顺序: domain, flag, path, secure, expiry, name, value
        # 注: 用户文件里第4列secure=FALSE但web_session那行第6域TRUE是httpOnly标记(非标准位置), 按XHS实际: web_session/id_token/x-rednote-* 为 httpOnly
        c["httpOnly"] = name in ("web_session", "id_token", "x-rednote-datactry", "x-rednote-holderctry")
        try:
            exp = int(expires)
            c["expires"] = exp if exp > 0 else -1
        except ValueError:
            c["expires"] = -1
        cookies.append(c)
    return {"cookies": cookies, "origins": []}

if not os.path.exists(COOKIE_FILE):
    print(f"缺少 {COOKIE_FILE} (Netscape格式全量cookie)")
    sys.exit(2)
state = netscape_to_state(COOKIE_FILE)
with open(STATE_FILE, "w") as f:
    json.dump(state, f)
print(f"[1/6] cookie 转换: {len(state['cookies'])} 枚 -> {STATE_FILE}")

# ---- Step 2: 关浏览器, state load 注入 ----
ab("close")
r = ab("state", "load", STATE_FILE, timeout=60)
print(f"[2/6] state load: {r[:80]}")

# ---- Step 3: 打开搜索页 ----
qkw = urllib.parse.quote(KW)
ab("open", f"https://www.xiaohongshu.com/search_result?keyword={qkw}", timeout=90)
time.sleep(6)
cur = ab("get", "url")
title = ab("get", "title")
print(f"[3/6] 页面: {title} | {cur[:90]}")
state_js = "JSON.stringify({err: location.href.includes('website-login/error'), loginWall: /Log in to view|扫码登录/.test(document.body.innerText), len: document.body.innerText.length, hasKW: document.body.innerText.includes('" + KW + "')})"
st = ab_eval(state_js)
print(f"    状态: {st}")

# ---- Step 4: 抽取笔记链接 ----
links = ab_eval("""(async () => {
  await new Promise(r => setTimeout(r, 3000));
  const hs = [...new Set([...document.querySelectorAll('a[href*="/explore/"], a[href*="/discovery/item/"], a[href*="/search_result/"]')]
    .map(a => a.getAttribute('href')).filter(h => h && h.includes('xsec_token')))];
  return JSON.stringify(hs.slice(0, 25));
})()""", timeout=60)
if not isinstance(links, list) or not links:
    print(f"[4/6] 未抽到链接: {links}")
    sys.exit(1)
print(f"[4/6] 抽到 {len(links)} 条含xsec_token链接")

# ---- Step 5: 筛视频笔记 (页面内取title类型) + yt-dlp 探测 ----
target, meta_info = None, None
for link in links[:10]:
    url = link if link.startswith("http") else f"https://www.xiaohongshu.com{link}"
    p = subprocess.run(["/home/z/.venv/bin/yt-dlp", "--dump-json", "--no-warnings",
                        "--cookies", COOKIE_FILE, url], capture_output=True, text=True, timeout=120)
    if p.returncode == 0 and p.stdout.strip():
        j = json.loads(p.stdout.splitlines()[0])
        if j.get("ext") == "mp4" or any((f.get("vcodec") or "none") != "none" for f in j.get("formats", [])):
            target, meta_info = url, j
            print(f"[5/6] 视频笔记: {j.get('title','')[:60]}")
            break
if not target:
    print("[5/6] 前10条无视频笔记(可能全是图文)")
    sys.exit(1)

# ---- Step 6: 下载 + meta ----
fname = os.path.join(OUTDIR, f"xhs_{meta_info['id']}.mp4")
p = subprocess.run(["/home/z/.venv/bin/yt-dlp", "-f", "best", "-o", fname, "--no-warnings",
                    "--cookies", COOKIE_FILE, target], capture_output=True, text=True, timeout=900)
size_mb = os.path.getsize(fname) / 1048576 if os.path.exists(fname) else 0
if size_mb < 0.05:
    print(f"[6/6] 下载失败: {(p.stderr or '')[-300:]}")
    sys.exit(1)
fp = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", fname], capture_output=True, text=True)
stream = next((s for s in json.loads(fp.stdout or "{}").get("streams", []) if s.get("codec_type") == "video"), {})
meta = {
    "platform": "xiaohongshu", "method": "agent-browser + 全量cookie(Playwright state) + yt-dlp --cookies",
    "search_keyword": KW, "note_id": meta_info["id"], "source_url": target,
    "author": meta_info.get("uploader") or meta_info.get("channel"), "title": meta_info.get("title"),
    "video": {"resolution": f"{stream.get('width','?')}x{stream.get('height','?')}", "codec": stream.get("codec_name"),
              "duration_s": float(meta_info.get("duration", 0))},
    "file": os.path.basename(fname), "size_mb": round(size_mb, 2),
    "search_hits_preview": links[:5],
}
with open(os.path.join(OUTDIR, "meta.json"), "w") as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
print(f"DONE {stream.get('width','?')}x{stream.get('height','?')} {size_mb:.1f}MB -> {OUTDIR}")
