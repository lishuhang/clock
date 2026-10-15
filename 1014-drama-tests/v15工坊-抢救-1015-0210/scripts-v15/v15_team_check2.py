#!/usr/bin/env python3
"""v15 第二轮: 深挖各家定价/团队页真实URL与内容
万兴(会员订阅+MCP&CLI页) / 小云雀(团队套餐) / Seko(订阅页) / LibTV(团队会员)
/ TapNow(企业版) / AniShort(会员充值-团队) / 纳逗(团队页)
"""
import os, re, json
from playwright.sync_api import sync_playwright

COOKIES_DIR = "/home/z/my-project/cookies/打包"
OUT_DIR = "/home/z/my-project/evidence/v15-team-check"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

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
            if len(parts) != 7: continue
            domain, flag, path, secure, expiry, name, value = parts
            cookies.append({"name": name, "value": value, "domain": domain,
                            "path": path or "/", "secure": secure.upper() == "TRUE",
                            "httpOnly": line.startswith("#HttpOnly_"),
                            **({"expires": int(expiry)} if int(expiry) > 0 else {})})
    return cookies

KEY = r"席位|子账号|小组|团队|同屏|光标|实时协作|多人|协同|限额|配额|额度|用量|管控|看板|监控|CLI|MCP|API|插件|Plugin|命令行|企业|定制|联系销售|SSO|角色|权限"

def dump(tag, page, note=""):
    try:
        page.wait_for_timeout(2800)
        text = page.inner_text("body")[:45000]
    except Exception as e:
        text = f"[失败: {e}]"
    try: page.screenshot(path=os.path.join(OUT_DIR, f"{tag}.png"), full_page=False)
    except Exception: pass
    print(f"\n{'='*70}\n【{tag}】 {page.url} {note}")
    n = 0
    for m in re.finditer(KEY, text, re.I):
        s = max(0, m.start()-55); e = min(len(text), m.end()+95)
        seg = re.sub(r"\s+", " ", text[s:e]).strip()
        print(f"  · {seg[:175]}"); n += 1
        if n >= 22: break
    if n == 0: print("  (无命中)")
    return text

def all_links(page):
    out = []
    try:
        for a in page.query_selector_all("a[href]"):
            t = (a.inner_text() or "").strip()[:20]; h = a.get_attribute("href") or ""
            if h and h not in ("#", "javascript:;"): out.append(f"{t}→{h[:100]}")
    except Exception: pass
    return list(dict.fromkeys(out))[:40]

def try_click(page, texts, tag, note=""):
    for t in texts:
        for sel in [f"text={t}", f"a:has-text('{t}')", f"button:has-text('{t}')", f"div:has-text('{t}')"]:
            try:
                el = page.locator(sel).first
                if el.count() == 0: continue
                el.click(timeout=3500)
                page.wait_for_timeout(2800)
                dump(tag, page, note + f"(点击:{t})")
                return True
            except Exception: continue
    return False

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

        # 万兴: 抓全部链接 → 会员订阅页 + MCP&CLI页
        try:
            page.goto("https://www.reelmate.cn/", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
            links = all_links(page)
            print("【万兴全部链接】", json.dumps(links, ensure_ascii=False)[:1200])
            for kw, tag in [("MCP", "r2-reelmate-mcpcli"), ("订阅", "r2-reelmate-subscribe")]:
                for l in links:
                    if kw.lower() in l.lower() and "http" in l:
                        u = l.split("→")[-1]
                        try:
                            page.goto(u if u.startswith("http") else f"https://www.reelmate.cn{u}",
                                      wait_until="domcontentloaded", timeout=25000)
                            dump(tag, page, u)
                        except Exception as e: print(f"  [{tag}失败]", e)
                        break
            # 直接试常见路径
            for u in ["/mcp", "/cli", "/mcp-cli", "/subscription", "/member"]:
                try:
                    r = page.goto(f"https://www.reelmate.cn{u}", wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1500)
                    t = page.inner_text("body")[:500]
                    if r.status == 200 and ("MCP" in t or "CLI" in t or "团队" in t or "会员" in t):
                        dump(f"r2-reelmate-path{u.replace('/','-')}", page, u)
                except Exception: continue
        except Exception as e: print("万兴失败", e)

        # 小云雀: 试app内常见会员/团队路径
        for u in ["https://xyq.jianying.com/lark/membership", "https://xyq.jianying.com/membership",
                  "https://xyq.jianying.com/paycenter", "https://xyq.jianying.com/team",
                  "https://xyq.jianying.com/home?tab_name=team"]:
            try:
                r = page.goto(u, wait_until="domcontentloaded", timeout=18000)
                page.wait_for_timeout(1800)
                t = page.inner_text("body")[:600]
                if "团队" in t or "席位" in t:
                    dump("r2-xyq-team", page, u); break
            except Exception: continue

        # Seko: 首页找按钮点进订阅
        try:
            page.goto("https://seko.sensetime.com/", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            print("【Seko链接】", json.dumps(all_links(page), ensure_ascii=False)[:800])
            if not try_click(page, ["订阅", "会员", "充值", "立即订阅", "升级"], "r2-seko-sub", "订阅页"):
                for u in ["/price", "/subscribe", "/pricing", "/membership", "/#/price"]:
                    try:
                        r = page.goto(f"https://seko.sensetime.com{u}", wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(1500)
                        t = page.inner_text("body")[:400]
                        if "会员" in t or "团队" in t: dump(f"r2-seko{u.replace('/','-')}", page, u); break
                    except Exception: continue
        except Exception as e: print("Seko失败", e)

        # LibTV: 找团队会员页(用户图10/11: 高级/超级团队会员)
        try:
            page.goto("https://www.liblib.tv/", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2200)
            print("【LibTV链接】", json.dumps(all_links(page), ensure_ascii=False)[:1000])
            if not try_click(page, ["会员", "团队会员", "订阅", "充值", "升级会员"], "r2-libtv-vip", "会员页"):
                for u in ["/vip", "/membership", "/subscribe", "/pricing"]:
                    try:
                        page.goto(f"https://www.liblib.tv{u}", wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(1500)
                        t = page.inner_text("body")[:400]
                        if "会员" in t or "团队" in t: dump(f"r2-libtv{u.replace('/','-')}", page, u); break
                    except Exception: continue
        except Exception as e: print("LibTV失败", e)

        # TapNow: tapnow.ai/pricing → 企业版tab
        try:
            page.goto("https://tapnow.ai/pricing", wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(2500)
            dump("r2-tapnow-pricing", page, "定价页")
            try_click(page, ["Enterprise", "企业版", "Custom"], "r2-tapnow-enterprise", "企业档")
        except Exception as e: print("TapNow失败", e)

        # AniShort: 会员充值 → 团队套餐
        try:
            page.goto("https://anishort.ai/", wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(2200)
            try_click(page, ["会员充值", "充值", "会员"], "r2-anishort-recharge", "充值页找团队套餐")
        except Exception as e: print("AniShort失败", e)

        # 纳逗: app内团队路由(手册: 团队空间/团队看板)
        for u in ["https://nadoupro.iqiyi.com/team", "https://nadoupro.iqiyi.com/settings/team",
                  "https://nadoupro.iqiyi.com/space/team", "https://nadoupro.iqiyi.com/user/team"]:
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1800)
                t = page.inner_text("body")[:500]
                if "团队" in t: dump("r2-nadou-team", page, u); break
            except Exception: continue

        browser.close()
    print("\nROUND2 DONE")

if __name__ == "__main__":
    main()
