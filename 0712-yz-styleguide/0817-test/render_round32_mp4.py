from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
R2 = ROOT / 'round2.2'
R3 = ROOT / 'round3.2'
FPS = 30
W = H = 1080
ENTRANCE_FRAMES = 180  # 6 s
STATIC_FRAMES = 120    # 4 s
TOTAL_FRAMES = ENTRANCE_FRAMES * 2 + STATIC_FRAMES  # 16 s


def alpha(frame: int, start_s: float, duration_s: float = 1.2) -> float:
    start = int(start_s * FPS)
    duration = int(duration_s * FPS)
    return max(0.0, min(1.0, (frame - start) / max(1, duration)))


def blend_crop(base: Image.Image, source: Image.Image, box: tuple[int, int, int, int], opacity: float) -> None:
    if opacity <= 0:
        return
    crop = source.crop(box).convert('RGBA')
    crop.putalpha(int(255 * opacity))
    base.alpha_composite(crop, (box[0], box[1]))


def entrance_frame(final: Image.Image, n: int) -> Image.Image:
    # v2.22c 4-stage progression:
    # 0.0–1.2s logo, 1.5–2.7s title, 3.0–4.2s footer/meta, 4.5–6.0s chart body.
    frame = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    blend_crop(frame, final, (850, 35, 1040, 165), alpha(n, 0.0))
    blend_crop(frame, final, (0, 0, 860, 230), alpha(n, 1.5))
    blend_crop(frame, final, (0, 880, W, H), alpha(n, 3.0))
    body_alpha = alpha(n, 4.5, 1.5)
    if body_alpha > 0:
        body = final.convert('RGBA')
        body.putalpha(int(255 * body_alpha))
        frame.alpha_composite(body)
    return frame.convert('RGB')


def encode_frames(frames: Path, output: Path) -> None:
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(frames / 'frame_%04d.png'),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-r', str(FPS), str(output),
    ], check=True)
    probe = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height,r_frame_rate,nb_frames',
        '-show_entries', 'format=duration', '-of', 'json', str(output)
    ], check=True, capture_output=True, text=True)
    output.with_suffix('.mp4.json').write_text(probe.stdout, encoding='utf-8')


def write_motion_html(source: Path, dest: Path) -> None:
    original = source.read_text(encoding='utf-8')
    css = '''<style data-purpose="round3-animations">
.chart-logo-1x1,.chart-title-1x1,.chart-source-1x1,.chart-part-num,.chart-body-1x1{opacity:0}
.chart-logo-1x1{animation:yzFade 1.2s ease-out 0s forwards}.chart-title-1x1{animation:yzFade 1.2s ease-out 1.5s forwards}.chart-source-1x1,.chart-part-num{animation:yzFade 1.2s ease-out 3s forwards}.chart-body-1x1{animation:yzFade 1.5s ease-out 4.5s forwards}@keyframes yzFade{to{opacity:1}}body{background:#fff;margin:0;padding:0}
</style>'''
    dest.write_text(original.replace('</head>', css + '</head>'), encoding='utf-8')


def main() -> None:
    R3.mkdir(exist_ok=True)
    htmls = sorted(R2.glob('*-styled.html'))
    if len(htmls) != 16:
        raise RuntimeError(f'Expected 16 round2.2 HTML files, found {len(htmls)}')
    with tempfile.TemporaryDirectory(prefix='round32-frames-') as tmp:
        temp = Path(tmp)
        for source in htmls:
            stem = source.stem
            motion_html = R3 / f'{stem}-motion.html'
            write_motion_html(source, motion_html)
            final_png = source.with_suffix('.png')
            final = Image.open(final_png).convert('RGB')
            folder = temp / stem
            folder.mkdir()
            entrance = [entrance_frame(final, n) for n in range(ENTRANCE_FRAMES)]
            all_frames = entrance + [final] * STATIC_FRAMES + list(reversed(entrance))
            for i, frame in enumerate(all_frames):
                frame.save(folder / f'frame_{i:04d}.png', compress_level=1)
            output = R3 / f'{stem}.mp4'
            encode_frames(folder, output)
            print(f'Rendered {output.name}')


if __name__ == '__main__':
    main()
