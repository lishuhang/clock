#!/usr/bin/env python3
"""抽检 canvas 渲染：每镜截 2 帧（入场中段+停留段），快速网格拼图供目检。"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

WORK = "/home/z/my-project/ep1-work"
OUT = "/home/z/my-project/ep1-work/spotcheck"
os.makedirs(OUT, exist_ok=True)

shots = json.load(open(f"{WORK}/ep1_shots_v2.json", encoding="utf-8"))
want = sys.argv[1].split(",") if len(sys.argv) > 1 else ["S01", "S05", "S10", "S20", "S30", "S43"]
sel = [s for s in shots if s["id"] in want]

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--force-device-scale-factor=1"])
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    for s in sel:
        html = f"{WORK}/canvas/{s['id']}.html"
        page.goto(f"file://{html}")
        try:
            page.wait_for_function(
                "() => (document.fonts ? document.fonts.status : 'loaded') === 'loaded'", timeout=8000)
        except Exception:
            pass
        for frac, tag in [(0.5, "in"), (min(1.0, (1.5 + s["dur"] * 0.5) / s["dur"]), "mid")]:
            t = round(s["dur"] * frac, 3)
            page.evaluate("p => renderFrame(p)",
                          {"t": t, "shot_dur": s["dur"], "hud": True, "watermark": "../assets/wm75.png",
                           "progress_pct": round(s["start"] / 740.36 * 100, 2), "chapter": s.get("chapter", "")})
            page.screenshot(path=f"{OUT}/{s['id']}_{tag}.jpg", type="jpeg", quality=80)
            print(f"{s['id']}_{tag} t={t:.2f}s")
    browser.close()
print("done")
