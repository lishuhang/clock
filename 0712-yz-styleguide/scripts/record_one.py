#!/usr/bin/env python3
"""Record a single animated HTML to MP4. Triggers animation via body.play class."""
import asyncio, os, subprocess, sys, shutil
from playwright.async_api import async_playwright

async def main():
    html_path = sys.argv[1]
    mp4_path = sys.argv[2]
    name = os.path.basename(html_path).replace('.html','')
    frames_dir = f"/tmp/r3_{name}"
    FPS = 30
    DUR = 3.5
    
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1080})
        await page.goto("file://" + html_path, wait_until="domcontentloaded")
        # Wait for fonts to load (but animations are frozen until .play)
        try:
            await page.evaluate("() => document.fonts.ready")
        except:
            pass
        await page.wait_for_timeout(300)
        # Take first frame (should be pure white — no .play yet)
        await page.screenshot(path=os.path.join(frames_dir, "frame_0000.png"))
        # Now trigger animation by adding .play class
        await page.evaluate("() => document.body.classList.add('play')")
        # Capture remaining frames
        total = int(FPS * DUR)
        for i in range(1, total):
            await page.screenshot(path=os.path.join(frames_dir, f"frame_{i:04d}.png"))
            await asyncio.sleep(1.0 / FPS)
        await browser.close()
    
    # 3-step ffmpeg
    entrance_mp4 = os.path.join(frames_dir, "entrance.mp4")
    static_mp4 = os.path.join(frames_dir, "static.mp4")
    exit_mp4 = os.path.join(frames_dir, "exit.mp4")
    last = os.path.join(frames_dir, f"frame_{total-1:04d}.png")
    
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS),
                    "-i", os.path.join(frames_dir, "frame_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    entrance_mp4], capture_output=True, timeout=60)
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", last,
                    "-t", "3", "-r", str(FPS),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    static_mp4], capture_output=True, timeout=60)
    subprocess.run(["ffmpeg", "-y", "-i", entrance_mp4,
                    "-vf", "reverse",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    exit_mp4], capture_output=True, timeout=60)
    
    concat_txt = os.path.join(frames_dir, "concat.txt")
    with open(concat_txt, "w") as f:
        f.write(f"file '{entrance_mp4}'\n")
        f.write(f"file '{static_mp4}'\n")
        f.write(f"file '{exit_mp4}'\n")
    
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", concat_txt,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                        mp4_path], capture_output=True, text=True, timeout=60)
    
    if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 10000:
        print(f"OK {os.path.getsize(mp4_path)//1024}KB")
    else:
        print(f"FAIL {r.stderr[-300:]}")
    shutil.rmtree(frames_dir, ignore_errors=True)

asyncio.run(main())
