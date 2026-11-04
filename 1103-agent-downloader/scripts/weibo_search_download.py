#!/usr/bin/env python3
"""微博 搜索→下载 全链路固化脚本 (零LLM token)
原理: agent-browser 真浏览器走访客护照JS(m.weibo.cn游客态) -> 页面内fetch容器搜索API
      -> statuses/show 拿视频直链(playback_list) -> curl下载
用法: python3 weibo_search_download.py <关键词> [保存目录]
依赖: agent-browser CLI (环境预装)
产出: <目录>/weibo_<mid>.mp4 + meta.json
"""
import json, os, re, subprocess, sys, urllib.parse

KW = sys.argv[1] if len(sys.argv) > 1 else "马保国"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else f"/home/z/my-project/download/1103-agent-downloader/downloads/weibo/search_{KW}"
os.makedirs(OUTDIR, exist_ok=True)

def ab(*args, timeout=60):
    """调 agent-browser CLI"""
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return out.strip()

def ab_eval(js, timeout=60):
    """eval 并解析 JSON 字符串结果 (agent-browser 返回带引号的 JSON 字符串, 需两层解析)"""
    out = ab("eval", js, timeout=timeout)
    val = out
    for _ in range(2):  # 两层: 外层引号包裹 + 内层JSON文本
        if isinstance(val, str) and val.startswith('"') and val.endswith('"'):
            try:
                val = json.loads(val)
            except Exception:
                break
        elif isinstance(val, str) and val.startswith(("[", "{")):
            try:
                val = json.loads(val)
            except Exception:
                break
        else:
            break
    return val

print(f"[1/5] 打开 m.weibo.cn 走游客护照: {KW}")
ab("open", "https://m.weibo.cn/")
ab("wait", "--load", "networkidle", timeout=60)

print("[2/5] 页面内调容器搜索API")
qkw = urllib.parse.quote(KW)
search_js = f"""(async () => {{
  const r = await fetch('/api/container/getIndex?containerid=100103type%3D1%26q%3D' + encodeURIComponent('{KW}') + '&page_type=searchall', {{headers: {{'X-Requested-With':'XMLHttpRequest'}}}});
  const j = await r.json();
  if (j.ok !== 1) return 'SEARCH_FAIL ok=' + j.ok;
  const hits = [];
  for (const c of (j.data.cards || [])) {{
    const mbs = c.mblog ? [c.mblog] : (c.card_group || []).map(g => g.mblog).filter(Boolean);
    for (const mb of mbs) {{
      const pi = mb.page_info || {{}};
      if (pi.type === 'video' || (pi.media_info && (pi.media_info.stream_url || pi.media_info.playback_list))) {{
        hits.push({{id: mb.id, u: (mb.user||{{}}).screen_name, t: (mb.text||'').replace(/<[^>]+>/g,'').slice(0,80)}});
      }}
    }}
  }}
  return JSON.stringify(hits.slice(0, 20));
}})()"""
res = ab_eval(search_js, timeout=60)
if not isinstance(res, list):
    print(f"搜索失败: {res}")
    sys.exit(1)
print(f"    视频命中 {len(res)} 条, 取第1条: {res[0]['u']} | {res[0]['t'][:40]}")
mid, author, text = res[0]["id"], res[0]["u"], res[0]["t"]

print(f"[3/5] statuses/show 拿视频直链 (mid={mid})")
show_js = f"""(async () => {{
  const r = await fetch('https://m.weibo.cn/statuses/show?id={mid}', {{headers: {{'X-Requested-With':'XMLHttpRequest'}}}});
  const j = await r.json();
  if (j.ok !== 1) return 'SHOW_FAIL ' + JSON.stringify(j).slice(0,100);
  const d = j.data; const pi = (d.page_info||{{}}); const mi = (pi.media_info||{{}});
  const vids = [];
  if (mi.playback_list) for (const p of mi.playback_list) vids.push({{q: p.meta_quality, url: (p.play_url||{{}}).url||''}});
  if (!vids.length && mi.stream_url) vids.push({{q: 'stream', url: mi.stream_url}});
  return JSON.stringify({{ok:1, mid: d.id, bid: d.bid, uid: (d.user||{{}}).id, author: (d.user||{{}}).screen_name, text: (d.text_raw||d.text||'').replace(/\\s+/g,' ').slice(0,200), created: d.created_at, vids: vids}});
}})()"""
info = ab_eval(show_js, timeout=60)
if not isinstance(info, dict) or not info.get("ok"):
    print(f"详情失败: {info}")
    sys.exit(1)
vids = [v for v in info.get("vids", []) if v["url"]]
if not vids:
    print("无视频直链")
    sys.exit(1)
print(f"    清晰度档位: {[v['q'] for v in vids]}")

print("[4/5] 下载最高清晰度")
best = vids[-1] if len(vids) > 1 else vids[0]
url = best["url"].replace("\\u002F", "/").replace("&amp;", "&")
fname = os.path.join(OUTDIR, f"weibo_{mid}.mp4")
dl = subprocess.run(["curl", "-sL", "--retry", "2", "-H", "Referer: https://m.weibo.cn/",
                     "-H", "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
                     "-o", fname, url], capture_output=True, text=True, timeout=300)
size_mb = os.path.getsize(fname) / 1048576 if os.path.exists(fname) else 0
print(f"    {fname} {size_mb:.1f}MB ({best['q']})")
if size_mb < 0.05:
    print("下载过小, 失败")
    sys.exit(1)

print("[5/5] ffprobe 体检 + meta.json")
fp = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", fname],
                    capture_output=True, text=True)
probe = json.loads(fp.stdout) if fp.stdout.strip() else {}
stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
meta = {
    "platform": "weibo", "method": "agent-browser游客护照 + 页面内容器搜索API + statuses/show直链",
    "search_keyword": KW, "mid": mid, "bid": info.get("bid"),
    "source_url": f"https://m.weibo.cn/status/{mid}",
    "web_url": f"https://weibo.com/{info.get('uid')}/{info.get('bid')}",
    "author": info.get("author"), "title": info.get("text", "")[:120],
    "created_at": info.get("created"), "quality": best["q"],
    "video": {"resolution": f"{stream.get('width','?')}x{stream.get('height','?')}",
              "codec": stream.get("codec_name"), "duration_s": float(probe.get("format", {}).get("duration", 0))},
    "file": os.path.basename(fname), "size_mb": round(size_mb, 2),
    "search_hits_preview": res[:5],
}
with open(os.path.join(OUTDIR, "meta.json"), "w") as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
print(f"DONE {stream.get('width','?')}x{stream.get('height','?')} {size_mb:.1f}MB -> {OUTDIR}")
