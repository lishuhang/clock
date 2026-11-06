#!/usr/bin/env python3
"""playwright 真浏览器 B站素材采集：
1. 预热 bilibili.com 拿全量 cookie
2. 加载视频页 → 截图（标题/播放量/点赞/UP 区）+ 提取 __playinfo__ 下载视频
3. 评论区找郭帆评论并截图
产物 → /home/z/my-project/ep1-work/materials/bili/
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

OUT = "/home/z/my-project/ep1-work/materials/bili"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

VIDEOS = {
    "paizi": "BV11mFLziEyP",
    "sss": "BV1FFRQB2Eqw",
}


def extract_playinfo_and_download(page, ctx, name, bvid):
    """从视频页提取 __playinfo__ 并用页面 cookie 下载。"""
    info = page.evaluate("() => window.__playinfo__ || null")
    meta = page.evaluate("""() => {
        const g = s => { const el = document.querySelector(s); return el ? el.innerText.trim() : ''; };
        return {
            title: g('h1.video-title, .video-info-title h1, h1'),
            view: g('.view-text, .play-text'),
            danmaku: g('.dm-text, .danmaku-text'),
            like: g('.like-text, video-like .like-text'),
            coin: g('.coin-text'),
            fav: g('.collect-text, .fav-text'),
            share: g('.share-text'),
            up: g('.up-name, .up-detail-top a'),
        };
    }""")
    json.dump(meta, open(f"{OUT}/{name}_page_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[meta] {name}: {json.dumps(meta, ensure_ascii=False)[:220]}")
    if not info:
        print(f"[WARN] {name} 无 __playinfo__")
        return
    json.dump(info, open(f"{OUT}/{name}_playinfo.json", "w"))
    data = info.get("data", {})
    durl = data.get("durl")
    final = f"{OUT}/{name}.mp4"
    if durl and not (os.path.exists(final) and os.path.getsize(final) > 1e6):
        url = durl[0]["url"]
        q = data.get("quality")
        print(f"[dl] {name} durl quality={q} size={durl[0].get('size', 0)/1e6:.1f}MB")
        r = ctx.request.get(url, headers={"Referer": "https://www.bilibili.com/",
                                          "User-Agent": UA}, timeout=300000)
        if r.ok():
            open(final + ".part", "wb").write(r.body())
            if os.path.getsize(final + ".part") > 1e6:
                os.replace(final + ".part", final)
                print(f"[ok] {final} {os.path.getsize(final)/1e6:.1f}MB")
        else:
            print(f"[FAIL] {name} 下载: HTTP {r.status}")
    else:
        # dash 流（分开的音视频）
        dash = (data.get("dash") or {})
        vstreams = dash.get("video") or []
        if vstreams:
            best = max(vstreams, key=lambda v: v.get("id", 0))
            print(f"[dash] {name} 最高视频流 id={best.get('id')} "
                  f"({best.get('width')}x{best.get('height')})")
            vurl = best["baseUrl"]
            astreams = dash.get("audio") or []
            aurl = max(astreams, key=lambda a: a.get("id", 0))["baseUrl"] if astreams else None
            for tag, u in [("v", vurl)] + ([("a", aurl)] if aurl else []):
                dst = f"{OUT}/{name}_{tag}.mp4"
                if os.path.exists(dst) and os.path.getsize(dst) > 1e5:
                    continue
                rr = ctx.request.get(u, headers={"Referer": "https://www.bilibili.com/",
                                                 "User-Agent": UA}, timeout=300000)
                if rr.ok():
                    open(dst + ".part", "wb").write(rr.body())
                    os.replace(dst + ".part", dst)
                    print(f"[ok] {dst} {os.path.getsize(dst)/1e6:.1f}MB")
                else:
                    print(f"[FAIL] {tag} 流: HTTP {rr.status}")


def shoot_page(page, name):
    os.makedirs(f"{OUT}/shots", exist_ok=True)
    # 顶部信息区截图（标题+播放量+点赞栏）
    page.screenshot(path=f"{OUT}/shots/{name}_page.png")
    # 定位裁切：标题栏、播放心（view+dm）、点赞栏、UP主栏
    crops = {
        "title": "h1.video-title, .video-info-title h1, h1",
        "view": ".view-info, .video-info-detail",
        "like": ".video-like, .video-toolbar-left, .toolbar-left",
        "up": ".up-detail-top, .up-info",
    }
    for tag, sel in crops.items():
        try:
            el = page.query_selector(sel)
            if el:
                el.screenshot(path=f"{OUT}/shots/{name}_{tag}.png")
                print(f"[ok] shots/{name}_{tag}.png")
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {name}_{tag}: {e}")


def find_guofan(page, name):
    """滚到评论区找郭帆评论并截图该元素。"""
    if name != "paizi":
        return
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.55)")
        page.wait_for_selector(".reply-item, .reply-list", timeout=15000)
        time.sleep(4)  # 评论异步加载
        for _ in range(6):
            hit = page.query_selector(".reply-item:has-text('郭帆')")
            if hit:
                hit.scroll_into_view_if_needed()
                time.sleep(1)
                hit.screenshot(path=f"{OUT}/shots/guofan_comment.png")
                txt = hit.inner_text()[:200]
                print(f"[ok] guofan_comment.png: {txt[:100]}")
                return
            # 翻一页热评
            nxt = page.query_selector(".pagination-btn:last-child, .next")
            if nxt:
                nxt.click()
                time.sleep(3)
            else:
                break
        print("[miss] 评论区前几页未见郭帆评论")
    except Exception as e:  # noqa: BLE001
        print(f"[skip] 郭帆评论: {e}")


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  user_agent=UA, device_scale_factor=2,
                                  locale="zh-CN")
        page = ctx.new_page()
        # 预热主站
        try:
            page.goto("https://www.bilibili.com/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            print(f"[warm] 主站 OK cookies={len(ctx.cookies())}")
        except Exception as e:  # noqa: BLE001
            print(f"[warm] 主站异常: {e}")
        for name, bvid in VIDEOS.items():
            try:
                page.goto(f"https://www.bilibili.com/video/{bvid}/",
                          wait_until="domcontentloaded", timeout=30000)
                page.wait_for_selector(".view-text, video, .bpx-player", timeout=20000)
                time.sleep(4)
                shoot_page(page, name)
                extract_playinfo_and_download(page, ctx, name, bvid)
                find_guofan(page, name)
            except Exception as e:  # noqa: BLE001
                print(f"[FAIL] {name}: {e}")
        browser.close()


if __name__ == "__main__":
    main()
