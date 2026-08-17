from __future__ import annotations

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
R34 = ROOT / 'round3.4'
FPS = 30
DURATION = 13.5
FRAMES = int(FPS * DURATION)
PORT = 9347
PROFILE = Path('/tmp/round34-headless-profile')
LOG = Path('/tmp/round34-headless.log')


def http_json(url: str):
    with urllib.request.urlopen(url, timeout=1) as response:
        return json.loads(response.read().decode('utf-8'))


def cdp(ws, seq: list[int], method: str, params: dict | None = None) -> dict:
    seq[0] += 1
    message = {'id': seq[0], 'method': method, 'params': params or {}}
    ws.send(json.dumps(message))
    while True:
        data = json.loads(ws.recv())
        if data.get('id') == seq[0]:
            if 'error' in data:
                raise RuntimeError(f"CDP {method}: {data['error']}")
            return data.get('result', {})


def start_browser() -> subprocess.Popen:
    if PROFILE.exists():
        shutil.rmtree(PROFILE)
    cmd = [
        'chromium','--headless=new',f'--remote-debugging-port={PORT}',f'--user-data-dir={PROFILE}',
        '--no-sandbox','--disable-gpu','--hide-scrollbars','--remote-allow-origins=*','--force-device-scale-factor=1',
        '--window-size=1080,1080','--disable-background-timer-throttling','--disable-renderer-backgrounding','about:blank'
    ]
    with LOG.open('w') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)
    for _ in range(60):
        try:
            http_json(f'http://127.0.0.1:{PORT}/json/version')
            return proc
        except Exception:
            time.sleep(.1)
    proc.terminate()
    raise RuntimeError('Headless Chromium debug endpoint did not become ready.')


def encode(frame_dir: Path, output: Path) -> None:
    subprocess.run([
        'ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(frame_dir/'frame_%04d.png'),
        '-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart','-r',str(FPS),str(output)
    ], check=True)
    probe = subprocess.run([
        'ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames',
        '-show_entries','format=duration','-of','json',str(output)
    ],check=True,capture_output=True,text=True)
    output.with_suffix('.mp4.json').write_text(probe.stdout,encoding='utf-8')


def capture_one(ws, seq: list[int], html_path: Path, frame_dir: Path) -> None:
    url = html_path.resolve().as_uri() + f'?r={time.time_ns()}'
    cdp(ws,seq,'Page.navigate',{'url':url})
    # Pause Web Animations after page load, then deterministically set every animation to the video-frame time.
    time.sleep(.45)
    cdp(ws,seq,'Runtime.evaluate',{'expression':"document.getAnimations().forEach(a=>a.pause())"})
    for index in range(FRAMES):
        milliseconds = index * 1000 / FPS
        cdp(ws,seq,'Runtime.evaluate',{'expression':f'document.getAnimations().forEach(a=>a.currentTime={milliseconds})'})
        data = cdp(ws,seq,'Page.captureScreenshot',{'format':'png','fromSurface':True})
        (frame_dir/f'frame_{index:04d}.png').write_bytes(base64.b64decode(data['data']))


def main() -> None:
    targets = sorted(R34.glob('*-motion.html'))
    requested = set(sys.argv[1:])
    if requested:
        targets = [path for path in targets if path.stem.removesuffix('-motion') in requested]
        if not targets:
            raise RuntimeError(f'No requested motion source found: {sorted(requested)}')
    elif len(targets) != 13:
        raise RuntimeError(f'Expected 13 animation HTML files, found {len(targets)}')
    proc = start_browser()
    try:
        pages = http_json(f'http://127.0.0.1:{PORT}/json')
        page = next(p for p in pages if p.get('type') == 'page')
        ws = websocket.create_connection(page['webSocketDebuggerUrl'],timeout=30)
        seq=[0]
        cdp(ws,seq,'Page.enable')
        cdp(ws,seq,'Emulation.setDeviceMetricsOverride',{'width':1080,'height':1080,'deviceScaleFactor':1,'mobile':False})
        scratch=Path('/tmp/round34-capture')
        if scratch.exists(): shutil.rmtree(scratch)
        scratch.mkdir()
        for html_path in targets:
            stem=html_path.name.removesuffix('-motion.html')
            frames=scratch/stem
            frames.mkdir()
            capture_one(ws,seq,html_path,frames)
            encode(frames,R34/f'{stem}.mp4')
            shutil.rmtree(frames)
            print(f'Recorded {stem}.mp4',flush=True)
        ws.close()
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()

if __name__=='__main__':
    main()
