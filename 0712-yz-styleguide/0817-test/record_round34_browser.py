from __future__ import annotations

"""Deterministic c.4 recorder for 1:1 element-motion HTML.

The c skill defines a fixed timeline: 6 s entrance (180 frames at 30 fps),
4 s hold (120 copies of the final entrance frame), and 6 s exit made by
reversing those 180 entrance frames.  Screenshots are clipped to the actual
.chart-container-1x1 rectangle, never to the viewport.
"""

import base64
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websocket

ROOT = Path(__file__).resolve().parent
R34 = ROOT / "round3.4"
FPS = 30
ENTRANCE_FRAMES = 180
HOLD_FRAMES = 120
EXIT_FRAMES = 180
TOTAL_FRAMES = ENTRANCE_FRAMES + HOLD_FRAMES + EXIT_FRAMES
DURATION_SECONDS = TOTAL_FRAMES / FPS
PORT = 9347
PROFILE = Path("/tmp/round34-headless-profile")
LOG = Path("/tmp/round34-headless.log")


def http_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=1) as response:
        return json.loads(response.read().decode("utf-8"))


def cdp(ws: websocket.WebSocket, seq: list[int], method: str, params: dict | None = None) -> dict:
    seq[0] += 1
    message = {"id": seq[0], "method": method, "params": params or {}}
    ws.send(json.dumps(message))
    while True:
        data = json.loads(ws.recv())
        if data.get("id") == seq[0]:
            if "error" in data:
                raise RuntimeError(f"CDP {method}: {data['error']}")
            return data.get("result", {})


def start_browser() -> subprocess.Popen:
    if PROFILE.exists():
        shutil.rmtree(PROFILE)
    cmd = [
        "chromium", "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
        "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--remote-allow-origins=*", "--force-device-scale-factor=1",
        "--window-size=1080,1080", "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "about:blank",
    ]
    with LOG.open("w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)
    for _ in range(60):
        try:
            http_json(f"http://127.0.0.1:{PORT}/json/version")
            return proc
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("Headless Chromium debug endpoint did not become ready.")


def encode(frame_dir: Path, output: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frame_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", str(FPS), str(output),
    ], check=True)
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration", "-of", "json", str(output),
    ], check=True, capture_output=True, text=True)
    output.with_suffix(".mp4.json").write_text(probe.stdout, encoding="utf-8")


def capture_entrance(ws: websocket.WebSocket, seq: list[int], html_path: Path, frame_dir: Path) -> dict[str, float]:
    url = html_path.resolve().as_uri() + f"?r={time.time_ns()}"
    cdp(ws, seq, "Page.navigate", {"url": url})
    time.sleep(0.45)
    geometry = cdp(ws, seq, "Runtime.evaluate", {"expression": """(async()=>{await document.fonts.ready;const e=document.querySelector('.chart-container-1x1');if(!e)throw new Error('missing .chart-container-1x1');const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};})()""", "awaitPromise": True, "returnByValue": True})
    rect = geometry["result"]["value"]
    if rect["width"] != 1080 or rect["height"] != 1080:
        raise RuntimeError(f"c.4 recorder requires exact 1080×1080 container, got {rect}")
    cdp(ws, seq, "Runtime.evaluate", {"expression": "document.getAnimations().forEach(a=>a.pause())"})
    clip = {"x": rect["x"], "y": rect["y"], "width": rect["width"], "height": rect["height"], "scale": 1}
    for index in range(ENTRANCE_FRAMES):
        milliseconds = index * 1000 / FPS
        cdp(ws, seq, "Runtime.evaluate", {"expression": f"document.getAnimations().forEach(a=>a.currentTime={milliseconds})"})
        screenshot = cdp(ws, seq, "Page.captureScreenshot", {"format": "png", "clip": clip, "fromSurface": True, "captureBeyondViewport": True})
        (frame_dir / f"entrance_{index:04d}.png").write_bytes(base64.b64decode(screenshot["data"]))
    return {key: float(value) for key, value in rect.items()}


def make_timeline(entrance_dir: Path, timeline_dir: Path) -> None:
    timeline_dir.mkdir()
    # A 480-frame timeline is deliberately materialized rather than delegated to a video filter;
    # this makes exact frame count, pause duration and reversed exit inspectable before encoding.
    mapping = list(range(ENTRANCE_FRAMES)) + [ENTRANCE_FRAMES - 1] * HOLD_FRAMES + list(range(ENTRANCE_FRAMES - 1, -1, -1))
    if len(mapping) != TOTAL_FRAMES:
        raise AssertionError(f"expected {TOTAL_FRAMES} timeline frames, got {len(mapping)}")
    for index, entrance_index in enumerate(mapping):
        shutil.copyfile(entrance_dir / f"entrance_{entrance_index:04d}.png", timeline_dir / f"frame_{index:04d}.png")


def main() -> None:
    targets = sorted(R34.glob("*-motion.html"))
    requested = set(sys.argv[1:])
    if requested:
        targets = [path for path in targets if path.stem.removesuffix("-motion") in requested]
        if not targets:
            raise RuntimeError(f"No requested motion source found: {sorted(requested)}")
    elif len(targets) != 13:
        raise RuntimeError(f"Expected 13 animation HTML files, found {len(targets)}")

    proc = start_browser()
    manifest = {
        "specification": {"fps": FPS, "entrance_frames": ENTRANCE_FRAMES, "hold_frames": HOLD_FRAMES, "exit_frames": EXIT_FRAMES, "total_frames": TOTAL_FRAMES, "duration_seconds": DURATION_SECONDS, "capture_selector": ".chart-container-1x1"},
        "videos": [],
    }
    try:
        pages = http_json(f"http://127.0.0.1:{PORT}/json")
        page = next(p for p in pages if p.get("type") == "page")
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30)
        seq = [0]
        cdp(ws, seq, "Page.enable")
        cdp(ws, seq, "Emulation.setDeviceMetricsOverride", {"width": 1080, "height": 1080, "deviceScaleFactor": 1, "mobile": False})
        scratch = Path("/tmp/round34-capture")
        if scratch.exists():
            shutil.rmtree(scratch)
        scratch.mkdir()
        for html_path in targets:
            stem = html_path.name.removesuffix("-motion.html")
            entrance = scratch / f"{stem}-entrance"
            timeline = scratch / f"{stem}-timeline"
            entrance.mkdir()
            rect = capture_entrance(ws, seq, html_path, entrance)
            make_timeline(entrance, timeline)
            output = R34 / f"{stem}.mp4"
            encode(timeline, output)
            manifest["videos"].append({"html": html_path.name, "mp4": output.name, "capture_rect": rect, "timeline_frames": TOTAL_FRAMES})
            shutil.rmtree(entrance)
            shutil.rmtree(timeline)
            print(f"Recorded {output.name} ({TOTAL_FRAMES} frames / {DURATION_SECONDS:.1f}s)", flush=True)
        ws.close()
    finally:
        R34.joinpath("recording_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
