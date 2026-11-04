#!/usr/bin/env python3
"""小红书 搜索→下载 全链路固化脚本 (零LLM token) — 需要 web_session cookie
实测结论(2026-11-04): 游客态搜索三条路全灭(RedCrack 471 IP风控 / 页面300012 IP风险或登录墙 / API签名有效但-101无登录信息)
=> 搜索必须登录态。本脚本注入用户提供的一次性 web_session cookie 后全自动。
用法: python3 xhs_search_download.py <关键词> [保存目录]
cookie: /home/z/my-project/.secrets/cookies/xiaohongshu_web_session.txt
获取方法: 浏览器登录 xiaohongshu.com → F12 → Application → Cookies → 复制 web_session 值
"""
import json, os, re, subprocess, sys, urllib.parse

COOKIE_FILE = "/home/z/my-project/.secrets/cookies/xiaohongshu_web_session.txt"
KW = sys.argv[1] if len(sys.argv) > 1 else "万智牌"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else f"/home/z/my-project/download/1103-agent-downloader/downloads/xiaohongshu/search_{KW}"
os.makedirs(OUTDIR, exist_ok=True)

if not os.path.exists(COOKIE_FILE) or not open(COOKIE_FILE).read().strip():
    print("缺少 web_session cookie。获取方法:\n"
          "  1. 浏览器登录 https://www.xiaohongshu.com\n"
          "  2. F12 → Application → Cookies → https://www.xiaohongshu.com\n"
          "  3. 找到 web_session, 复制其值\n"
          f"  4. 写入 {COOKIE_FILE}")
    sys.exit(2)
WEB_SESSION = open(COOKIE_FILE).read().strip().splitlines()[0]

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

print(f"[1/6] 种 cookie 到 xiaohongshu.com 域 (web_session={'<'+str(len(WEB_SESSION))+'chars>'})")
# 打开搜索URL: 游客态会被 300012 拦到 website-login/error 页, 但域名保持 xiaohongshu.com —— 正好在该域种 cookie
qkw = urllib.parse.quote(KW)
ab("open", f"https://www.xiaohongshu.com/search_result?keyword={qkw}")
ab("wait", "3000")
cur = ab("get", "url")
print(f"    当前页: {cur[:80]}")
r = ab_eval(f"document.cookie = 'web_session={WEB_SESSION}; domain=.xiaohongshu.com; path=/; max-age=31536000'; 'SET_DONE'")
print(f"    cookie set: {r}")

print(f"[2/6] 重新打开搜索页: {KW}")
ab("open", f"https://www.xiaohongshu.com/search_result?keyword={qkw}")
ab("wait", "5000")
cur = ab("get", "url")
state = ab_eval("JSON.stringify({err: location.href.includes('website-login/error'), loginWall: document.body.innerText.includes('Log in to view') || document.body.innerText.includes('登录'), len: document.body.innerText.length})")
print(f"    url={cur[:70]} state={state}")

print("[3/6] 抽取笔记链接(note_id+xsec_token)")
links = ab_eval("""(async () => {
  await new Promise(r => setTimeout(r, 2500));
  const hs = [...new Set([...document.querySelectorAll('a[href*="/explore/"], a[href*="/discovery/item/"], a[href*="/search_result/"]')]
    .map(a => a.getAttribute('href')).filter(h => h && (h.includes('xsec_token') || /\\/(explore|discovery\\/item)\\/[0-9a-f]{16,}/.test(h))))];
  return JSON.stringify(hs.slice(0, 20));
})()""", timeout=60)
if not isinstance(links, list) or not links:
    print(f"未抽到链接(links={links}) — cookie 可能失效或仍被风控")
    sys.exit(1)
print(f"    命中 {len(links)} 条")

print("[4/6] 筛视频笔记(yt-dlp 逐条探测元数据)")
target, meta_info = None, None
for link in links[:8]:
    url = link if link.startswith("http") else f"https://www.xiaohongshu.com{link}"
    p = subprocess.run(["/home/z/.venv/bin/yt-dlp", "--dump-json", "--no-warnings", url],
                       capture_output=True, text=True, timeout=90)
    if p.returncode == 0 and p.stdout.strip():
        j = json.loads(p.stdout.splitlines()[0])
        if j.get("ext") == "mp4" or any(f.get("vcodec") != "none" for f in j.get("formats", [])):
            target, meta_info = url, j
            print(f"    视频笔记: {j.get('title','')[:50]}")
            break
if not target:
    print("前8条无视频笔记")
    sys.exit(1)

print("[5/6] 下载")
fname = os.path.join(OUTDIR, f"xhs_{meta_info['id']}.mp4")
p = subprocess.run(["/home/z/.venv/bin/yt-dlp", "-f", "best", "-o", fname, "--no-warnings", target],
                   capture_output=True, text=True, timeout=600)
size_mb = os.path.getsize(fname) / 1048576 if os.path.exists(fname) else 0
if size_mb < 0.05:
    print(f"下载失败: {(p.stderr or '')[-200:]}")
    sys.exit(1)
print(f"    {fname} {size_mb:.1f}MB")

print("[6/6] meta.json")
fp = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", fname], capture_output=True, text=True)
stream = next((s for s in json.loads(fp.stdout or "{}").get("streams", []) if s.get("codec_type") == "video"), {})
meta = {
    "platform": "xiaohongshu", "method": "agent-browser + web_session cookie 注入 + yt-dlp XiaoHongShu extractor",
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
