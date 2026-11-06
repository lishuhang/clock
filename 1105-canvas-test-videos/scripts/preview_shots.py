#!/usr/bin/env python3
"""换肤抽检：渲染指定页在指定时间的预览帧。"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

CANVAS = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/canvas"
OUT = "/home/z/my-project/ep1-work/preview"
SHOT_DUR = {"S01": 5.53, "S07": 17.4, "S11": 21.9, "S17": 12.9, "S06": 4.59, "S12": 22.3}


def main(pages, ts):
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        for f in pages:
            path = f"{CANVAS}/{f}.html"
            page.goto(f"file://{path}")
            try:
                page.wait_for_function(
                    "() => document.fonts.ready.then(r => r.status).catch(() => 'loaded')",
                    timeout=5000)
            except Exception:  # noqa: BLE001
                pass  # 字体等待超时容忍（截图时已加载大概率）
            # 等图片加载（忽略空src占位）
            page.wait_for_function(
                "() => Array.from(document.images).every(i => i.src === '' || (i.complete && i.naturalWidth > 0))",
                timeout=8000)
            for t in ts:
                page.evaluate("p => renderFrame(p)",
                              {"chapter": "价格篇", "subtitle": "", "progress_pct": 30,
                               "watermark": "", "t": t, "shot_dur": SHOT_DUR.get(f, 12),
                               "hud": False})
                page.screenshot(path=f"{OUT}/{f}_t{t:.1f}.png")
                print(f"[ok] {f} t={t}")
        browser.close()


if __name__ == "__main__":
    pages = sys.argv[1].split(",") if len(sys.argv) > 1 else ["S01", "S07", "S11", "S17", "S06"]
    ts = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [2.0, 4.0]
    main(pages, ts)
