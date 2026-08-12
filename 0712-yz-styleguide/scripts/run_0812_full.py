#!/usr/bin/env python3
"""
Full pipeline for 0812-test:
  1. Screenshot round1 (static posters)
  2. Screenshot round2 (1:1 static)
  3. Generate round3 (animated HTML + MP4)
"""
import os, asyncio, subprocess, shutil, glob, re, pathlib
from playwright.async_api import async_playwright

BASE = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test"
ROUND1 = os.path.join(BASE, "round1")
ROUND2 = os.path.join(BASE, "round2")
ROUND3 = os.path.join(BASE, "round3")
os.makedirs(ROUND3, exist_ok=True)

ANIMATION_CSS = """
<style data-purpose="round3-animations">
@property --pie-reveal { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
.chart-logo-1x1, .chart-title-1x1, .chart-source-1x1, .chart-part-num,
.chart-body-1x1 .chart-legend,
.chart-body-1x1 .data-table-1x1,
.chart-body-1x1 svg { opacity:0; }
.chart-body-1x1 .data-table-1x1 tbody tr { opacity:0; }
.chart-logo-1x1{ animation: fadeIn 1.2s ease-out 0s forwards; }
.chart-title-1x1{ animation: fadeIn 1.2s ease-out 1.5s forwards; }
.chart-source-1x1{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-part-num{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-body-1x1 .chart-legend{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-body-1x1 svg{ animation: fadeIn 1.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1{ animation: fadeIn 1.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1 thead{ animation: fadeIn 0.6s ease-out 4.5s forwards; opacity:0; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(1){ animation: rowFade 0.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(2){ animation: rowFade 0.5s ease-out 4.8s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(3){ animation: rowFade 0.5s ease-out 5.1s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(4){ animation: rowFade 0.5s ease-out 5.4s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(5){ animation: rowFade 0.5s ease-out 5.7s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(6){ animation: rowFade 0.5s ease-out 6.0s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(7){ animation: rowFade 0.5s ease-out 6.3s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(8){ animation: rowFade 0.5s ease-out 6.6s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(9){ animation: rowFade 0.5s ease-out 6.9s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(10){ animation: rowFade 0.5s ease-out 7.2s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(11){ animation: rowFade 0.5s ease-out 7.5s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(12){ animation: rowFade 0.5s ease-out 7.8s forwards; }
@keyframes fadeIn{ to{ opacity:1; } }
@keyframes rowFade{ to{ opacity:1; } }
#yz-selfcheck-banner{ display:none !important; }
body{ background:#fff !important; padding:0 !important; margin:0 !important; }
</style>
"""

async def screenshot_round(htmls_dir, selector, out_ext, viewport_size=1200):
    """Screenshot all styled HTML in a directory."""
    htmls = sorted(glob.glob(os.path.join(htmls_dir, "*-styled.html")))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for html_path in htmls:
            name = os.path.basename(html_path).replace(".html", out_ext)
            page = await browser.new_page(viewport={"width": viewport_size, "height": viewport_size}, device_scale_factor=1)
            await page.goto("file://" + html_path, wait_until="networkidle", timeout=60000)
            try: await page.evaluate("() => document.fonts.ready")
            except: pass
            await page.wait_for_timeout(600)
            await page.evaluate("() => { const b = document.getElementById('yz-selfcheck-banner'); if (b) b.style.display = 'none'; }")
            cc = await page.query_selector(selector)
            if cc:
                await cc.screenshot(path=os.path.join(htmls_dir, name))
            else:
                await page.screenshot(path=os.path.join(htmls_dir, name), full_page=True)
            await page.close()
            print(f"  {name}")
        await browser.close()

def inject_animation(html_path, out_path):
    """Inject animation CSS into HTML for round3."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("</head>", ANIMATION_CSS + "\n</head>", 1)
    pathlib.Path(out_path).write_text(html, encoding="utf-8")

async def record_mp4(html_path, mp4_path):
    """Record animated HTML to MP4. 6s entrance + 4s static + 6s exit = 16s."""
    frames_dir = f"/tmp/r3_0812_{os.path.basename(html_path).replace('.html','')}"
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    
    FPS = 30
    ENTRANCE_DUR = 6.0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1100, "height": 1100})
        await page.goto("file://" + html_path, wait_until="domcontentloaded")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(50)
        container = await page.query_selector(".chart-container-1x1")
        if not container:
            await browser.close()
            return False
        total = int(FPS * ENTRANCE_DUR)
        for i in range(total):
            await container.screenshot(path=os.path.join(frames_dir, f"frame_{i:04d}.png"))
            await asyncio.sleep(1.0 / FPS)
        await browser.close()
    
    # 3-step ffmpeg
    entrance = os.path.join(frames_dir, "entrance.mp4")
    static = os.path.join(frames_dir, "static.mp4")
    exit_v = os.path.join(frames_dir, "exit.mp4")
    last = os.path.join(frames_dir, f"frame_{total-1:04d}.png")
    
    subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(frames_dir,"frame_%04d.png"),
                    "-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",entrance], capture_output=True, timeout=120)
    subprocess.run(["ffmpeg","-y","-loop","1","-i",last,"-t","4","-r",str(FPS),
                    "-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",static], capture_output=True, timeout=120)
    subprocess.run(["ffmpeg","-y","-i",entrance,"-vf","reverse",
                    "-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",exit_v], capture_output=True, timeout=120)
    concat_txt = os.path.join(frames_dir, "concat.txt")
    with open(concat_txt, "w") as f:
        f.write(f"file '{entrance}'\n")
        f.write(f"file '{static}'\n")
        f.write(f"file '{exit_v}'\n")
    r = subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_txt,
                        "-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",mp4_path], capture_output=True, timeout=120)
    ok = os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 50000
    shutil.rmtree(frames_dir, ignore_errors=True)
    return ok

async def main():
    # Step 1: Screenshot round1
    print("=== Step 1: Screenshot round1 (static posters) ===")
    await screenshot_round(ROUND1, ".chart-container", ".png", 1200)
    
    # Step 2: Screenshot round2 (1:1)
    print("\n=== Step 2: Screenshot round2 (1:1) ===")
    await screenshot_round(ROUND2, ".chart-container-1x1", ".png", 1100)
    
    # Step 3: Generate round3 animated HTML + MP4
    print("\n=== Step 3: Generate round3 (animated HTML + MP4) ===")
    round2_htmls = sorted(glob.glob(os.path.join(ROUND2, "*-styled.html")))
    for html_path in round2_htmls:
        name = os.path.basename(html_path)
        # Inject animation
        r3_html = os.path.join(ROUND3, name)
        inject_animation(html_path, r3_html)
        # Record MP4
        mp4_name = name.replace(".html", ".mp4")
        mp4_path = os.path.join(ROUND3, mp4_name)
        if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 50000:
            print(f"  {mp4_name} exists, skip")
            continue
        print(f"  recording {mp4_name}...")
        ok = await record_mp4(r3_html, mp4_path)
        if ok:
            print(f"    OK {os.path.getsize(mp4_path)//1024}KB")
        else:
            print(f"    FAIL")
    
    print(f"\n=== Done ===")
    print(f"round1: {len(glob.glob(os.path.join(ROUND1,'*-styled.png')))} PNGs")
    print(f"round2: {len(glob.glob(os.path.join(ROUND2,'*-styled.png')))} PNGs")
    print(f"round3: {len(glob.glob(os.path.join(ROUND3,'*.mp4')))} MP4s")

asyncio.run(main())
