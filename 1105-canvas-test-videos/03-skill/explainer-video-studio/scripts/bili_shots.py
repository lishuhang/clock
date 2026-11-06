#!/usr/bin/env python3
"""移动版B站页面截图 + 新闻证据截图。
产物 → /home/z/my-project/ep1-work/materials/bili/shots/
"""
import os
import time

from playwright.sync_api import sync_playwright

OUT = "/home/z/my-project/ep1-work/materials/bili/shots"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

VIDEOS = {
    "paizi": "BV11mFLziEyP",
    "sss": "BV1FFRQB2Eqw",
}


def crop_el(page, sel, path, desc):
    try:
        el = page.query_selector(sel)
        if el:
            el.screenshot(path=path)
            print(f"[ok] {desc} -> {os.path.basename(path)}")
            return True
        print(f"[miss] {desc}: 选择器无命中 {sel}")
    except Exception as e:  # noqa: BLE001
        print(f"[skip] {desc}: {e}")
    return False


def shoot_bili(page, name, bvid):
    page.goto(f"https://m.bilibili.com/video/{bvid}/",
              wait_until="domcontentloaded", timeout=30000)
    time.sleep(6)
    # 整页首屏（海报+播放量+标题+UP）
    page.screenshot(path=f"{OUT}/{name}_page_full.png")
    # 元素级裁切
    crop_el(page, ".main-cover", f"{OUT}/{name}_cover_play.png", "海报+播放量")
    crop_el(page, ".main-cover .left", f"{OUT}/{name}_playcount.png", "播放量条")
    crop_el(page, ".gsl-poster-tips-view", f"{OUT}/{name}_view_only.png", "播放数")
    crop_el(page, ".video-title, .title, h1", f"{OUT}/{name}_title.png", "标题")
    crop_el(page, ".up-name, .author, [class*=up-name]", f"{OUT}/{name}_up.png", "UP主")


def shoot_news(page):
    """腾讯新闻·差评文章：郭帆转发点赞段落。"""
    try:
        page.goto("https://view.inews.qq.com/a/20260213A021B900",
                  wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        page.screenshot(path=f"{OUT}/news_paizi_full.png")
        # 找含郭帆的段落
        paras = page.query_selector_all("p, .content-article p, section p")
        for i, el in enumerate(paras):
            try:
                t = el.inner_text()
                if "郭帆" in t and ("点赞" in t or "转发" in t):
                    el.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    el.screenshot(path=f"{OUT}/news_guofan_para.png")
                    print(f"[ok] 郭帆段落({len(t)}字): {t[:80]}")
                    break
            except Exception:  # noqa: BLE001
                continue
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 新闻页: {e}")


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                  user_agent=UA, device_scale_factor=3,
                                  is_mobile=True, locale="zh-CN")
        page = ctx.new_page()
        for name, bvid in VIDEOS.items():
            try:
                shoot_bili(page, name, bvid)
            except Exception as e:  # noqa: BLE001
                print(f"[FAIL] {name}: {e}")
        try:
            shoot_news(page)
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] news: {e}")
        browser.close()


if __name__ == "__main__":
    main()
