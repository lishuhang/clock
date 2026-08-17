from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
R2 = ROOT / 'round2.3'
R3 = ROOT / 'round3.3'
FPS = 30
W = H = 1080
TOTAL_SECONDS = 13.5  # Aligns with the referenced 0811 round3.9 motion timing.
FRAMES = int(TOTAL_SECONDS * FPS)


def opacity(t: float, start: float, duration: float = 0.6) -> float:
    if t <= start:
        return 0.0
    if t >= start + duration:
        return 1.0
    return (t - start) / duration


def overlay_crop(canvas: Image.Image, final: Image.Image, crop: tuple[int, int, int, int], value: float) -> None:
    if value <= 0:
        return
    piece = final.crop(crop).convert('RGBA')
    piece.putalpha(round(max(0.0, min(1.0, value)) * 255))
    canvas.alpha_composite(piece, (crop[0], crop[1]))


def frame_at(final: Image.Image, number: int) -> Image.Image:
    t = number / FPS
    base = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    # Round3.9 pattern: logo/header at 0.1/0.4s, chart body at 0.5s,
    # legend/footer at 0.6/0.8s. The complete lower graph enters as one unit.
    overlay_crop(base, final, (0, 0, W, 180), opacity(t, 0.10))
    overlay_crop(base, final, (0, 168, W, 960), opacity(t, 0.50, 0.50))
    overlay_crop(base, final, (0, 950, W, H), opacity(t, 0.60))
    if t >= 12.5:
        base.putalpha(round(max(0.0, (13.5 - t) / 1.0) * 255))
        white = Image.new('RGBA', (W, H), (255, 255, 255, 255))
        white.alpha_composite(base)
        return white.convert('RGB')
    return base.convert('RGB')


def write_motion_html(source: Path, dest: Path) -> None:
    original = source.read_text(encoding='utf-8')
    css = '''<style data-purpose="round3.3-simultaneous-motion">
.chart-logo-1x1,.chart-title-1x1,.chart-body-1x1,.chart-footer-1x1{opacity:0}.chart-logo-1x1,.chart-title-1x1{animation:yzSyncFade .6s ease-out .1s forwards}.chart-body-1x1{animation:yzSyncFade .5s ease-out .5s forwards}.chart-footer-1x1{animation:yzSyncFade .6s ease-out .6s forwards}.dumbbell-svg,.chart-legend{animation:yzSyncFade .5s ease-out .5s forwards}@keyframes yzSyncFade{to{opacity:1}}body{margin:0;padding:0;background:#fff}
</style>'''
    dest.write_text(original.replace('</head>', css + '</head>'), encoding='utf-8')


def encode(folder: Path, output: Path) -> None:
    subprocess.run([
        'ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(folder/'frame_%04d.png'),
        '-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart','-r',str(FPS),str(output)
    ], check=True)
    probe = subprocess.run([
        'ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-show_entries','format=duration','-of','json',str(output)
    ],check=True,capture_output=True,text=True)
    output.with_suffix('.mp4.json').write_text(probe.stdout,encoding='utf-8')


def main() -> None:
    R3.mkdir(exist_ok=True)
    htmls = sorted(R2.glob('*-styled.html'))
    if len(htmls) != 13:
        raise RuntimeError(f'Expected 13 round2.3 source files, found {len(htmls)}')
    with tempfile.TemporaryDirectory(prefix='round33-frames-') as tmp:
        temp = Path(tmp)
        for source in htmls:
            final_png = source.with_suffix('.png')
            final = Image.open(final_png).convert('RGB')
            stem = source.stem
            write_motion_html(source, R3 / f'{stem}-motion.html')
            folder = temp / stem
            folder.mkdir()
            for number in range(FRAMES):
                frame_at(final, number).save(folder / f'frame_{number:04d}.png', compress_level=1)
            output = R3 / f'{stem}.mp4'
            encode(folder, output)
            print(f'Rendered {output.name}')


if __name__ == '__main__':
    main()
