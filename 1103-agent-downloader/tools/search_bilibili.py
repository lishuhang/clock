#!/usr/bin/env python3
# B站素材搜索: 游客 wbi search API, 一次跑全部素材关键词
# 产物: materials/search_raw.json (全量) + stdout 压缩摘要(每关键词1行)
import requests, json, os, sys, time, hashlib, re, urllib.parse
sys.path.insert(0, "/home/z/my-project/clock/1103-agent-downloader/tools")
from lib_media import log, wentry, now, UA_PC, WORK

RAW = os.path.join(WORK, "materials", "search_raw.json")
os.makedirs(os.path.dirname(RAW), exist_ok=True)

import sys as _sys
_args = _sys.argv[1:]
if _args:  # 重试模式: 只跑传入词, 合并入已有JSON
    KEYWORDS = _args
else:
    KEYWORDS = [
        "万智牌开卡",        # 卡包/开卡(文案1,3,6,14) ←重试词
        "小猪佩奇",          # IP矩阵(4) ←重试词
        "万智牌 魔戒",       # 抄袭争议卡(10) ←重试词(中土系列社区名)
        "万智牌 中土",       # 霍比特人联动(6) ←重试词
        "大富翁 桌游",       # 桌游死忠(8) ←重试词(Monopoly社区名)
        "万智牌 比赛",       # 线下社交/店赛(8) ←重试词
        "集装箱",            # 供应链(13) ←重试词
        "港口 吊装",         # 供应链(13) ←重试词
        "关税",              # 关税驳回(11) ←重试词
        "孩之宝 财报",       # 财报画面(2) ←补搜
    ]

MIXIN_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
             33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
             26, 4, 56, 34, 44, 51, 0, 6, 21, 30, 20, 25, 63, 11, 17, 59, 36, 52, 60, 22, 1, 57, 54]

S = requests.Session()
S.headers.update({"User-Agent": UA_PC, "Referer": "https://www.bilibili.com/",
                  "Accept": "application/json, text/plain, */*"})

def wbi_key():
    j = S.get("https://api.bilibili.com/x/web-interface/nav", timeout=15).json()
    d = j.get("data") or {}
    w = d.get("wbi_img") or {}
    if not w:
        raise RuntimeError(f"nav无wbi_img code={j.get('code')} msg={j.get('message')}")
    raw = (w.get("img_url", "").split("/")[-1].split(".")[0] + w.get("sub_url", "").split("/")[-1].split(".")[0])
    return "".join(raw[i] for i in MIXIN_TAB if i < len(raw))[:32]

def wbi_sign(params, key):
    p = dict(params)
    p["wts"] = int(time.time())
    qs = urllib.parse.urlencode(sorted(p.items()))
    return dict(p, w_rid=hashlib.md5((qs + key).encode()).hexdigest())

def search(kw, key, page=1):
    params = wbi_sign({"search_type": "video", "keyword": kw, "page": page,
                       "order": "", "single_column": 0}, key)
    r = S.get("https://api.bilibili.com/x/web-interface/wbi/search/type",
              params=params, timeout=20)
    j = r.json()
    if j.get("code") != 0:
        return None, f"code={j.get('code')} msg={j.get('message')} http={r.status_code}"
    res = j.get("data", {}).get("result") or []
    out = []
    for v in res:
        t = re.sub(r"</?em[^>]*>", "", v.get("title", ""))
        out.append({"bvid": v.get("bvid"), "title": t, "author": v.get("author"),
                    "mid": v.get("mid"), "duration": v.get("duration"),
                    "play": v.get("play"), "pubdate": v.get("pubdate"),
                    "desc": (v.get("description") or "")[:80].replace("\n", " "),
                    "url": f"https://www.bilibili.com/video/{v.get('bvid')}"})
    return out, f"n={len(out)}"

def main():
    # 预热cookie(buvid3/b_nut由Set-Cookie自动进session)
    r0 = S.get("https://www.bilibili.com/", timeout=15)
    log("material-search", "warmup", f"www.bilibili.com http={r0.status_code} cookies={list(S.cookies.keys())}")
    try:
        KEY = wbi_key()
        log("material-search", "wbi", f"key_len={len(KEY)}(前6={KEY[:6]}…)")
    except Exception as e:
        wentry("material-search", "FAIL", "search_bilibili.py", "materials/search_raw.json",
               [f"wbi_key失败: {e}"], "搜索通路死在nav", "切换: agent-browser 页内fetch(未执行)")
        print("RESULT FAIL wbi:", e)
        sys.exit(1)

    all_out, fails = {}, []
    if os.path.exists(RAW):  # 合并历史(重试模式保留首轮数据)
        try:
            all_out = json.load(open(RAW, encoding="utf-8")).get("keywords", {})
        except Exception:
            all_out = {}
    for kw in KEYWORDS:
        try:
            lst, msg = search(kw, KEY)
            if lst is None:
                fails.append(f"{kw}:{msg}"); log("material-search", "fail", f"[{kw}] {msg}")
                all_out[kw] = {"error": msg}
            else:
                all_out[kw] = {"count": len(lst), "items": lst}
                top3 = " | ".join(f"{i['title'][:18]}({i['duration']}s)" for i in lst[:3])
                print(f"[{kw}] n={len(lst)} :: {top3}")
                log("material-search", "ok", f"[{kw}] n={len(lst)} top3={top3[:150]}")
        except Exception as e:
            fails.append(f"{kw}:{str(e)[:80]}")
            all_out[kw] = {"error": str(e)[:200]}
            print(f"[{kw}] EXC {str(e)[:80]}")
        time.sleep(2.5)
    json.dump({"updated": now(), "keywords": all_out}, open(RAW, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = sum(1 for k in KEYWORDS if "error" not in all_out[k])
    stat = f"OK {ok}/{len(KEYWORDS)}; fails={' ; '.join(fails)[:200] if fails else 'none'}"
    print("RESULT:", stat)
    log("material-search", "done", f"落盘 {RAW} {stat}")

if __name__ == "__main__":
    main()
