#!/usr/bin/env python3
"""Record a single 0812 round3 HTML to MP4. Usage: record_one_0812.py <name>"""
import asyncio, os, subprocess, sys, shutil
from playwright.async_api import async_playwright

NAME = sys.argv[1]
ROUND3 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/round3"
HTML = f"{ROUND3}/{NAME}-styled.html"
MP4 = f"{ROUND3}/{NAME}.mp4"

if os.path.exists(MP4) and os.path.getsize(MP4) > 50000:
    print(f"skip {NAME}")
    sys.exit(0)

FRAMES = f"/tmp/r3d_{NAME}"
os.makedirs(FRAMES, exist_ok=True)
for f in os.listdir(FRAMES): os.remove(os.path.join(FRAMES, f))

async def go():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width":1100,"height":1100})
        await page.goto("file://"+HTML, wait_until="domcontentloaded")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(50)
        c = await page.query_selector(".chart-container-1x1")
        if not c: await b.close(); return False
        for i in range(180):
            await c.screenshot(path=f"{FRAMES}/frame_{i:04d}.png")
            await asyncio.sleep(1/30)
        await b.close()
    return True

ok = asyncio.run(go())
if not ok:
    print(f"FAIL {NAME}: no container")
    sys.exit(1)

subprocess.run(["ffmpeg","-y","-framerate","30","-i",f"{FRAMES}/frame_%04d.png","-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",f"{FRAMES}/entrance.mp4"],capture_output=True,timeout=120)
subprocess.run(["ffmpeg","-y","-loop","1","-i",f"{FRAMES}/frame_0179.png","-t","4","-r","30","-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",f"{FRAMES}/static.mp4"],capture_output=True,timeout=120)
subprocess.run(["ffmpeg","-y","-i",f"{FRAMES}/entrance.mp4","-vf","reverse","-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",f"{FRAMES}/exit.mp4"],capture_output=True,timeout=120)
with open(f"{FRAMES}/concat.txt","w") as f:
    f.write(f"file '{FRAMES}/entrance.mp4'\n")
    f.write(f"file '{FRAMES}/static.mp4'\n")
    f.write(f"file '{FRAMES}/exit.mp4'\n")
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",f"{FRAMES}/concat.txt","-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",MP4],capture_output=True,timeout=120)

sz = os.path.getsize(MP4) if os.path.exists(MP4) else 0
print(f"{'OK' if sz > 50000 else 'FAIL'} {NAME} {sz//1024}KB")
shutil.rmtree(FRAMES, ignore_errors=True)
