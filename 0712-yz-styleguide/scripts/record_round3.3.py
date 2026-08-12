#!/usr/bin/env python3
"""
Record round3.3 — 2s entrance + 4s static + 2s exit = 8s total.
Capture .chart-container-1x1 element (no gray border).
Entrance: 2s × 30fps = 60 frames
Static: 4s × 30fps = 120 frames (last frame duplicated)
Exit: 2s = reverse of entrance (60 frames)
"""
import asyncio, os, subprocess, sys, shutil, glob
from playwright.async_api import async_playwright

ROUND33 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.3"
TEMP_BASE = "/tmp/r3.3_frames"
FPS = 30
ENTRANCE_DUR = 2.0   # 2s entrance
STATIC_DUR = 4.0     # 4s static

async def capture_frames(html_path, frames_dir):
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1100, "height": 1100})
        await page.goto("file://" + html_path, wait_until="domcontentloaded")
        try:
            await page.evaluate("() => document.fonts.ready")
        except:
            pass
        await page.wait_for_timeout(300)
        container = await page.query_selector(".chart-container-1x1")
        if not container:
            await browser.close()
            return 0
        # First frame (no .play)
        await container.screenshot(path=os.path.join(frames_dir, "frame_0000.png"))
        # Trigger animation
        await page.evaluate("() => document.body.classList.add('play')")
        total = int(FPS * ENTRANCE_DUR)
        for i in range(1, total):
            await container.screenshot(path=os.path.join(frames_dir, f"frame_{i:04d}.png"))
            await asyncio.sleep(1.0 / FPS)
        await browser.close()
    return total

def build_video(frames_dir, output_mp4, total):
    entrance = os.path.join(frames_dir, "entrance.mp4")
    static = os.path.join(frames_dir, "static.mp4")
    exit_v = os.path.join(frames_dir, "exit.mp4")
    last = os.path.join(frames_dir, f"frame_{total-1:04d}.png")
    
    # Entrance: 2s
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS),
                    "-i", os.path.join(frames_dir, "frame_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    entrance], capture_output=True, timeout=60)
    # Static: 4s (last frame looped)
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", last,
                    "-t", str(STATIC_DUR), "-r", str(FPS),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    static], capture_output=True, timeout=60)
    # Exit: reverse entrance (2s)
    subprocess.run(["ffmpeg", "-y", "-i", entrance, "-vf", "reverse",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                    exit_v], capture_output=True, timeout=60)
    # Concat: 2s + 4s + 2s = 8s
    concat_txt = os.path.join(frames_dir, "concat.txt")
    with open(concat_txt, "w") as f:
        f.write(f"file '{entrance}'\n")
        f.write(f"file '{static}'\n")
        f.write(f"file '{exit_v}'\n")
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", concat_txt,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                        output_mp4], capture_output=True, timeout=60)
    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 50000

async def main():
    htmls = sorted(glob.glob(os.path.join(ROUND33, "*-styled.html")))
    print(f"Found {len(htmls)} HTML files", flush=True)
    for idx, html_path in enumerate(htmls, 1):
        name = os.path.basename(html_path).replace("-styled.html", "")
        mp4 = os.path.join(ROUND33, f"{name}.mp4")
        frames = os.path.join(TEMP_BASE, name)
        print(f"[{idx}/{len(htmls)}] {name}...", flush=True)
        n = await capture_frames(html_path, frames)
        if n < 60:
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
