#!/usr/bin/env python3
"""v15 第三轮: 万兴团队管理页(登录态) + Seko订阅弹窗 + 小云雀会员/团队页"""
import os, re
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
            if line.startswith("#HttpOnly_"): line = line[len("#HttpOnly_"):]
            parts = line.split("\t")
            if len(parts) != 7: continue
            domain, flag, path, secure, expiry, name, value = parts
            cookies.append({"name": name, "value": value, "domain": domain,
                            "path": path or "/", "secure": secure.upper() == "TRUE",
                            "httpOnly": line.startswith("#HttpOnly_"),
                            **({"expires": int(expiry)} if int(expiry) > 0 else {})})
    return cookies

KEY = r"席位|子账号|小组|团队|同屏|光标|实时协作|多人|协同|限额|配额|额度|用量|管控|看板|监控|CLI|MCP|API|插件|命令行|企业|定制|联系|SSO|权限|角色|会员|订阅"

def dump(tag, page, note=""):
    try:
        page.wait_for_timeout(2800)
        text = page.inner_text("body")[:40000]
    except Exception as e: text = f"[失败:{e}]"
    try: page.screenshot(path=os.path.join(OUT_DIR, f"{tag}.png"))
    except Exception: pass
    print(f"\n{'='*70}\n【{tag}】 {page.url} {note}")
    n = 0
    for m in re.finditer(KEY, text, re.I):
        s = max(0, m.start()-55); e = min(len(text), m.end()+95)
        print(f"  · {re.sub(r' ', ' ', text[s:e]).strip()[:175]}"); n += 1
        if n >= 20: break
    if n == 0: print("  (无命中)")

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

        # 万兴: 登录态访问团队管理页
        for u in ["https://www.reelmate.cn/team", "https://www.reelmate.cn/teamManagement",
                  "https://www.reelmate.cn/team-manage", "https://www.reelmate.cn/workspace/team"]:
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=18000)
                page.wait_for_timeout(2500)
                t = page.inner_text("body")[:800]
                if "团队" in t or "成员" in t or "席位" in t:
                    dump("r3-reelmate-team", page, u); break
                print(f"  [try {u}] 未命中团队字样")
            except Exception as e: print(f"  [try {u}]", str(e)[:80])
        # 万兴: 点击导航"团队管理"按钮(JS按钮)
        try:
            page.goto("https://www.reelmate.cn/", wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(2500)
            for sel in ["text=团队管理", "text=团队"]:
                try:
                    els = page.locator(sel)
                    for i in range(min(els.count(), 3)):
                        els.nth(i).click(timeout=3000)
                        page.wait_for_timeout(2500)
                        t = page.inner_text("body")[:600]
                        if "成员" in t or "席位" in t or page.url != "https://www.reelmate.cn/":
                            dump("r3-reelmate-team-click", page, "点击导航"); break
                except Exception: continue
        except Exception as e: print("万兴nav失败", str(e)[:100])

        # Seko: 登录态点头像/积分/会员入口
        try:
            page.goto("https://seko.sensetime.com/", wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3000)
            for sel in ["text=订阅", "text=会员", "text=升级", "text=充值", "text=积分",
                        "[class*=avatar]", "[class*=user]", "[class*=Avatar]"]:
                try:
                    el = page.locator(sel).first
                    if el.count() == 0: continue
                    el.click(timeout=3000)
                    page.wait_for_timeout(2500)
                    t = page.inner_text("body")[:2000]
                    if "会员" in t or "团队" in t or "订阅" in t:
                        dump("r3-seko-sub", page, f"点击:{sel}"); break
                except Exception: continue
        except Exception as e: print("Seko失败", str(e)[:100])

        # 小云雀: 登录态 app 内找会员/团队
        for u in ["https://xyq.jianying.com/home", "https://xyq.jianying.com/membership",
                  "https://xyq.jianying.com/price", "https://xyq.jianying.com/vip-center",
                  "https://xyq.jianying.com/pay/vip"]:
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
                t = page.inner_text("body")[:800]
                if any(k in t for k in ["会员", "团队", "充值", "订阅"]):
                    dump("r3-xyq-member", page, u); break
            except Exception: continue
        # 小云雀: 首页点会员/充值按钮
        try:
            page.goto("https://xyq.jianying.com/home", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            for sel in ["text=会员", "text=充值", "text=订阅", "text=升级", "[class*=vip]", "[class*=Vip]"]:
                try:
                    el = page.locator(sel).first
                    if el.count() == 0: continue
                    el.click(timeout=3000); page.wait_for_timeout(2500)
                    t = page.inner_text("body")[:2000]
                    if "会员" in t or "团队" in t:
                        dump("r3-xyq-member-click", page, f"点击:{sel}"); break
                except Exception: continue
        except Exception as e: print("小云雀失败", str(e)[:100])

        browser.close()
    print("\nROUND3 DONE")

if __name__ == "__main__":
    main()
