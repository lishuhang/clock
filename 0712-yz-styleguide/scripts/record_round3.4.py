#!/usr/bin/env python3
"""
Record round3.4 — 6s entrance + 4s static + 6s exit = 16s total.
Animation auto-plays on page load (no body.play trigger needed).
Capture .chart-container-1x1 element (no gray border).
"""
import asyncio, os, subprocess, shutil, glob
from playwright.async_api import async_playwright

ROUND34 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.4"
TEMP_BASE = "/tmp/r3.4_frames"
FPS = 30
ENTRANCE_DUR = 6.0   # 6s entrance (3x of 2s)
STATIC_DUR = 4.0     # 4s static

async def capture_frames(html_path, frames_dir):
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1100, "height": 1100})
        # Navigate — animation auto-plays on load
        await page.goto("file://" + html_path, wait_until="domcontentloaded")
        try:
            await page.evaluate("() => document.fonts.ready")
        except:
            pass
        # Small delay to ensure page is ready but animation hasn't progressed much
        await page.wait_for_timeout(50)
        container = await page.query_selector(".chart-container-1x1")
        if not container:
            await browser.close()
            return 0
        # Capture frames immediately — animation auto-plays
        total = int(FPS * ENTRANCE_DUR)
        for i in range(total):
            await container.screenshot(path=os.path.join(frames_dir, f"frame_{i:04d}.png"))
            await asyncio.sleep(1.0 / FPS)
        await browser.close()
    return total

def build_video(frames_dir, output_mp4, total):
    entrance = os.path.join(frames_dir, "entrance.mp4")
    static = os.path.join(frames_dir, "static.mp4")
    exit_v = os.path.join(frames_dir, "exit.mp4")
    last = os.path.join(frames_dir, f"frame_{total-1:04d}.png")
    
    # Entrance: 6s
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS),
                    "-i", os.path.join(frames_dir, "frame_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    entrance], capture_output=True, timeout=120)
    # Static: 4s
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", last,
                    "-t", str(STATIC_DUR), "-r", str(FPS),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    static], capture_output=True, timeout=120)
    # Exit: reverse entrance (6s)
    subprocess.run(["ffmpeg", "-y", "-i", entrance, "-vf", "reverse",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    exit_v], capture_output=True, timeout=120)
    # Concat: 6s + 4s + 6s = 16s
    concat_txt = os.path.join(frames_dir, "concat.txt")
    with open(concat_txt, "w") as f:
        f.write(f"file '{entrance}'\n")
        f.write(f"file '{static}'\n")
        f.write(f"file '{exit_v}'\n")
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", concat_txt,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                        output_mp4], capture_output=True, timeout=120)
    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 50000

async def main():
    htmls = sorted(glob.glob(os.path.join(ROUND34, "*-styled.html")))
    print(f"Found {len(htmls)} HTML files", flush=True)
    for idx, html_path in enumerate(htmls, 1):
        name = os.path.basename(html_path).replace("-styled.html", "")
        mp4 = os.path.join(ROUND34, f"{name}.mp4")
        frames = os.path.join(TEMP_BASE, name)
        print(f"[{idx}/{len(htmls)}] {name}...", flush=True)
        n = await capture_frames(html_path, frames)
        if n < 180:
            print(f"  FAIL: only {n} frames")
            continue
        ok = build_video(frames, mp4, n)
        if ok:
            dur = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",mp4], capture_output=True, text=True).stdout.strip()
            print(f"  OK {os.path.getsize(mp4)//1024}KB {dur}s")
        else:
            print(f"  FAIL")
        shutil.rmtree(frames, ignore_errors=True)

asyncio.run(main())
