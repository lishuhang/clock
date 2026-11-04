#!/usr/bin/env python3
"""微博搜索探针3: genvisitor2访客SUB + X-Xsrf-Token -> weibo.com/s.weibo.com 域搜索接口探测
上轮未探索路径①: '补 XSRF-TOKEN 头走容器 API' 的具体化
"""
import json, re, sys, urllib.request, urllib.parse

UA_PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
kw = sys.argv[1] if len(sys.argv) > 1 else "马保国"
OUT = {"steps": []}

def log(s, ok, d):
    OUT["steps"].append({"step": s, "ok": ok, "detail": d[:300]})
    print(f"[{'OK' if ok else 'FAIL'}] {s}: {d[:300]}")

def post(url, data, headers):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8", "replace")

def get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "replace")

# Step 1: genvisitor2 + 收集全部 set-cookie
st, hd, txt = post("https://passport.weibo.com/visitor/genvisitor2", {
    "cb": "visitor_gray_callback", "tid": "01AUXHE0uWNcmbV0Qlq3L-R4dZHGS_3E7eKqUtdA9HiUgQ",
    "from": "weibo", "webdriver": "false",
}, {"User-Agent": UA_PC, "Content-Type": "application/x-www-form-urlencoded", "Referer": "https://weibo.com/"})

sub = (re.search(r'"sub":"([^"]+)"', txt) or [None, ""])[1] if re.search(r'"sub":"([^"]+)"', txt) else ""
m = re.search(r'"sub":"([^"]+)"', txt)
sub = m.group(1) if m else ""
# 解析 set-cookie 头 (可能多个)
sc = hd.get("Set-Cookie", "") or ""
xsrf = ""
for part in re.split(r"(?i),\s*(?=[A-Za-z0-9_]+=)", sc):
    if part.strip().startswith("XSRF-TOKEN="):
        xsrf = part.split("=", 1)[1].split(";")[0]
log("genvisitor2+cookies", bool(sub), f"sub_len={len(sub)} xsrf_len={len(xsrf)} setcookie_names={[p.split('=')[0] for p in re.split(r';\\s*', sc) if '=' in p][:8]}")

cookie = f"SUB={sub}"
if xsrf:
    cookie += f"; XSRF-TOKEN={xsrf}"
base_h = {"User-Agent": UA_PC, "Cookie": cookie, "Referer": "https://s.weibo.com/",
          "X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/plain, */*"}
if xsrf:
    base_h["X-Xsrf-Token"] = xsrf

q = urllib.parse.quote(kw)
candidates = [
    ("s.weibo.com_ajax_search", f"https://s.weibo.com/ajax/statuses/search?keyword={q}&page=1&has_red=1&isnew=1"),
    ("weibo.com_ajax_search_all", f"https://weibo.com/ajax/search/all?q={q}&page=1&pagesize=10"),
    ("weibo.com_ajax_statuses_searchall", f"https://weibo.com/ajax/statuses/searchall?keyword={q}&page=1"),
    ("weibo.com_ajax_side_hotssearch", f"https://weibo.com/ajax/side/hotSearch"),
]
for name, url in candidates:
    try:
        st, txt = get(url, base_h)
        is_json = txt.lstrip().startswith("{")
        ok = False
        detail = f"HTTP{st} json={is_json}"
        if is_json:
            try:
                j = json.loads(txt)
                ok = j.get("ok") == 1
                detail += f" ok={j.get('ok')} keys={list(j.keys())[:6]}"
                if "data" in j and isinstance(j["data"], dict):
                    detail += f" data_keys={list(j['data'].keys())[:8]}"
            except Exception:
                detail += " parse_err"
        else:
            detail += f" head={txt[:120]}"
        log(name, ok, detail)
        if ok and "search" in name:
            OUT[f"{name}_raw_len"] = len(txt)
            with open(f"/home/z/my-project/logs/wb_{name}.json", "w") as f:
                f.write(txt)
    except Exception as e:
        log(name, False, f"EXC {e}")

with open("/home/z/my-project/logs/wb_search_probe3.json", "w") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print("RESULT=/home/z/my-project/logs/wb_search_probe3.json")
