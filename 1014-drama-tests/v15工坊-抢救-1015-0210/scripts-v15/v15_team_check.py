#!/usr/bin/env python3
"""v15 团队协作表全平台真机核查（用户指令：cookies实跑所有10家页面）
每家: 首页/定价/团队页 → 文本关键词命中 + 截图存证
输出: /home/z/my-project/evidence/v15-team-check/
"""
import os, re, json
from playwright.sync_api import sync_playwright

COOKIES_DIR = "/home/z/my-project/cookies/打包"
OUT_DIR = "/home/z/my-project/evidence/v15-team-check"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

PATTERNS = {
    "席位/子账号/小组": r"席位|子账号|小组|团队管理|项目权限|共享资产|成员数|人数",
    "同屏/协作": r"同屏|多光标|光标|实时协作|多人.{0,6}(协作|同时|在线)|协同|跟随|聚焦",
    "限额/用量": r"限额|配额|额度|用量|管控|发放.{0,4}回收|积分.{0,6}(管|分配)",
    "看板/监控": r"看板|监控数据|数据概览|统计|报表|排行",
    "CLI/MCP/API": r"CLI|MCP|API|插件|Plugin|命令行",
    "团队版/企业版": r"团队版|企业版|团队会员|企业会员|联系销售|联系我们|定制",
}

def parse_netscape(path):
    cookies = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")):
                continue
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly_"):]
            parts = line.split("\t")
            if len(parts) != 7:
                continue
            domain, flag, path, secure, expiry, name, value = parts
            cookies.append({"name": name, "value": value, "domain": domain,
                            "path": path or "/", "secure": secure.upper() == "TRUE",
                            "httpOnly": line.startswith("#HttpOnly_"),
                            **({"expires": int(expiry)} if int(expiry) > 0 else {})})
    return cookies

RESULTS = {}

def dump(tag, page, extra_note=""):
    text = ""
    try:
        page.wait_for_timeout(2500)
        text = page.inner_text("body")[:40000]
    except Exception as e:
        text = f"[inner_text失败: {e}]"
    shot = os.path.join(OUT_DIR, f"{tag}.png")
    try: page.screenshot(path=shot, full_page=False)
    except Exception: pass
    hits = {}
    for name, pat in PATTERNS.items():
        ctx = []
        for m in re.finditer(pat, text, re.I):
            s = max(0, m.start()-60); e = min(len(text), m.end()+100)
            ctx.append(re.sub(r"\s+", " ", text[s:e]).strip())
            if len(ctx) >= 4: break
        if ctx: hits[name] = ctx
    RESULTS[tag] = {"url": page.url, "note": extra_note, "hits": hits}
    print(f"\n{'='*70}\n【{tag}】 {page.url} {extra_note}")
    if not hits: print("  (无命中)")
    for k, v in hits.items():
        print(f"  ◆{k}: {len(v)}段")
        for c in v[:3]: print(f"    · {c[:180]}")
    return text

def grab_links(page, kw):
    out = []
    try:
        for a in page.query_selector_all("a"):
            t = (a.inner_text() or "").strip()
            h = a.get_attribute("href") or ""
            if t and any(k in t for k in kw):
                out.append((t[:24], h[:120]))
    except Exception: pass
    return list(dict.fromkeys(out))[:12]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1500, "height": 950}, locale="zh-CN")
        for f in os.listdir(COOKIES_DIR):
            if f.endswith(".txt"):
                for c in parse_netscape(os.path.join(COOKIES_DIR, f)):
                    try: ctx.add_cookies([c])
                    except Exception: pass
        page = ctx.new_page()

        # ── 1. 万兴剧厂 reelmate.cn ──────────────────────────────
        try:
            page.goto("https://www.reelmate.cn/", wait_until="domcontentloaded", timeout=45000)
            t = dump("01a-reelmate-home", page, "首页:MCP&CLI/团队管理导航")
            print("  链接:", grab_links(page, ["MCP", "CLI", "团队", "会员", "价格", "订阅"]))
            for label, kw, tag in [("MCP&CLI页", ["MCP", "CLI"], "01b-reelmate-mcpcli"),
                                    ("团队管理页", ["团队管理", "团队"], "01c-reelmate-team")]:
                try:
                    for a in page.query_selector_all("a"):
                        tx = (a.inner_text() or "").strip()
                        if any(k in tx for k in kw):
                            a.click(timeout=4000); page.wait_for_timeout(2500)
                            dump(tag, page); page.go_back(wait_until="domcontentloaded"); page.wait_for_timeout(1200)
                            break
                except Exception as e: print(f"  [{label}失败] {e}")
            try:
                page.goto("https://www.reelmate.cn/price", wait_until="domcontentloaded", timeout=30000)
                dump("01d-reelmate-price", page, "定价页猜测路径")
            except Exception as e: print("  [price页失败]", e)
        except Exception as e: print("万兴失败", e)

        # ── 2. 小云雀 xyq.jianying.com ─────────────────────────
        try:
            page.goto("https://xyq.jianying.com/", wait_until="domcontentloaded", timeout=45000)
            dump("02a-xyq-home", page, "首页找团队/会员入口")
            print("  链接:", grab_links(page, ["团队", "会员", "价格", "订阅", "VIP", "企业"]))
            for u in ["https://xyq.jianying.com/vip", "https://xyq.jianying.com/price",
                      "https://xyq.jianying.com/pay", "https://xyq.jianying.com/member"]:
                try:
                    page.goto(u, wait_until="domcontentloaded", timeout=20000)
                    txt = page.inner_text("body")[:3000]
                    if "团队" in txt or "席位" in txt:
                        dump("02b-xyq-team-price", page, u); break
                except Exception: continue
        except Exception as e: print("小云雀失败", e)

        # ── 3. Seko seko.sensetime.com ─────────────────────────
        try:
            page.goto("https://seko.sensetime.com/", wait_until="domcontentloaded", timeout=45000)
            dump("03a-seko-home", page, "首页找订阅/团队入口")
            print("  链接:", grab_links(page, ["订阅", "会员", "价格", "团队", "企业", "VIP"]))
            for u in ["https://seko.sensetime.com/price", "https://seko.sensetime.com/subscription",
                      "https://seko.sensetime.com/vip", "https://seko.sensetime.com/pay"]:
                try:
                    page.goto(u, wait_until="domcontentloaded", timeout=20000)
                    txt = page.inner_text("body")[:3000]
                    if "团队" in txt or "会员" in txt:
                        dump("03b-seko-price", page, u); break
                except Exception: continue
        except Exception as e: print("Seko失败", e)

        # ── 4. LibTV www.liblib.tv ────────────────────────────
        try:
            page.goto("https://www.liblib.tv/", wait_until="domcontentloaded", timeout=45000)
            dump("04a-libtv-home", page, "首页找定价/团队")
            print("  链接:", grab_links(page, ["定价", "价格", "会员", "团队", "订阅", "VIP", "Plugin"]))
            for u in ["https://www.liblib.tv/price", "https://www.liblib.tv/pricing",
                      "https://www.liblib.tv/vip", "https://www.liblib.tv/plugin"]:
                try:
                    page.goto(u, wait_until="domcontentloaded", timeout=20000)
                    txt = page.inner_text("body")[:3000]
                    if any(k in txt for k in ["团队", "会员", "Plugin", "CLI"]):
                        dump("04b-libtv-price", page, u)
                        if "团队" in txt: break
                except Exception: continue
        except Exception as e: print("LibTV失败", e)

        # ── 5. 纳逗Pro nadoupro.iqiyi.com ─────────────────────
        try:
            page.goto("https://nadoupro.iqiyi.com/", wait_until="domcontentloaded", timeout=45000)
            dump("05a-nadou-home", page, "首页找团队入口")
            print("  链接:", grab_links(page, ["团队", "设置", "管理", "人才"]))
        except Exception as e: print("纳逗失败", e)

        # ── 6. TapNow app.tapnow.ai ──────────────────────────
        try:
            page.goto("https://app.tapnow.ai/", wait_until="domcontentloaded", timeout=45000)
            dump("06a-tapnow-home", page, "首页/应用入口")
            print("  链接:", grab_links(page, ["价格", "Pricing", "企业", "团队", "Enterprise", "订阅"]))
            for u in ["https://tapnow.ai/pricing", "https://app.tapnow.ai/pricing", "https://tapnow.ai/"]:
                try:
                    page.goto(u, wait_until="domcontentloaded", timeout=20000)
                    txt = page.inner_text("body")[:3000]
                    if any(k in txt for k in ["Enterprise", "企业", "Custom", "团队"]):
                        dump("06b-tapnow-price", page, u); break
                except Exception: continue
        except Exception as e: print("TapNow失败", e)

        # ── 7. AniShort anishort.ai ─────────────────────────
        try:
            page.goto("https://anishort.ai/", wait_until="domcontentloaded", timeout=45000)
            dump("07a-anishort-home", page, "首页:多人同屏/CLI公告")
            try:
                page.goto("https://anishort.ai/price", wait_until="domcontentloaded", timeout=30000)
                t = page.inner_text("body")[:6000]
                if "团队" in t:
                    dump("07b-anishort-price", page, "团队套餐")
            except Exception as e: print("  [price失败]", e)
        except Exception as e: print("AniShort失败", e)

        # ── 8. OiiOii www.oiioii.ai ──────────────────────────
        try:
            page.goto("https://www.oiioii.ai/price", wait_until="domcontentloaded", timeout=45000)
            dump("08a-oiioii-price", page, "定价页(含Team标签)")
            for sel in ["text=Team", "text=团队"]:
                try:
                    page.click(sel, timeout=4000)
                    dump("08b-oiioii-team", page, "Team标签内容")
                    break
                except Exception: continue
        except Exception as e: print("OiiOii失败", e)

        # ── 9. ShotLab aigc.xinpianchang.com ────────────────
        try:
            page.goto("https://aigc.xinpianchang.com/", wait_until="domcontentloaded", timeout=45000)
            dump("09a-shotlab-home", page, "首页:企业版/协作入口")
            print("  链接:", grab_links(page, ["企业", "协作", "团队", "价格", "会员"]))
        except Exception as e: print("ShotLab失败", e)

        # ── 10. 巨日禄 video.jurilu.com ──────────────────────
        try:
            page.goto("https://video.jurilu.com/", wait_until="domcontentloaded", timeout=45000)
            dump("10a-jurilu-home", page, "首页:项目管理/企业素材库")
            print("  链接:", grab_links(page, ["项目管理", "企业", "团队", "二级", "工作台"]))
        except Exception as e: print("巨日禄失败", e)

        browser.close()

    with open(os.path.join(OUT_DIR, "v15-team-digest.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=1)
    print(f"\n\nDONE: {len(RESULTS)}页已存证 → {OUT_DIR}")

if __name__ == "__main__":
    main()
