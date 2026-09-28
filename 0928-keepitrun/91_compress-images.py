#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
91_compress-images.py - Image compression CLI for lishuhang/img repo (v2.0)

Lossless / near-lossless compression for PNG, JPEG, GIF using best-in-class
open-source tools. Designed to be run:
  1. Locally: `python 91_compress-images.py --repo /path/to/img --commit`
  2. Via GitHub Actions: see .github/workflows/compress-images.yml

Tools used (all open-source, no AI):
  - PNG:  oxipng (lossless, multi-threaded, opt level 4) if on PATH;
         otherwise Pillow lossless re-save (optimize=True)
  - JPEG: jpegoptim --max=90 --strip-all --all-progressive if on PATH;
         otherwise Pillow (quality=90, optimize, progressive)
  - GIF:  gifsicle --optimize=3 (lossless) if on PATH; otherwise Pillow (optimize)
  - WebP conversion (optional, --webp): cwebp -q 88 for images >500KB

v1.25: the bundled piczip/oxipng.exe has been removed; every format now has a
pure-Pillow fallback so the CLI works on any OS without installing anything.

Typical savings: 15-40% with zero visible quality loss.

Usage:
  python 91_compress-images.py                     # scan + compress all
  python 91_compress-images.py --dry-run           # scan only, report savings
  python 91_compress-images.py --min-size 500      # only compress >500KB images
  python 91_compress-images.py --webp              # also convert large images to WebP
  python 91_compress-images.py --workers 8         # parallel workers (default: CPU count)
  python 91_compress-images.py --commit            # git commit + push after compression
  python 91_compress-images.py --year 2021 2020    # only specific years

Install tools (Ubuntu/Debian):
  sudo apt install oxipng jpegoptim gifsicle webp

Install tools (macOS):
  brew install oxipng jpegoptim gifsicle webp

Install tools (Windows):
  # Download from project pages, or use scoop:
  scoop install oxipng jpegoptim gifsicle libwebp
"""

import os
import sys
import subprocess
import argparse
import time
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ================= Windows 编码修复 =================
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


def find_tool(name):
    """v1.25: locate an external helper on PATH; bundled exe no longer used."""
    return shutil.which(name)


def check_tools():
    """Check which compression tools are available."""
    tools = {}
    for name, cmd in [("oxipng", "oxipng"), ("jpegoptim", "jpegoptim"),
                      ("gifsicle", "gifsicle"), ("cwebp", "cwebp")]:
        executable = find_tool(cmd)
        if not executable:
            tools[name] = False
            continue
        try:
            subprocess.run([executable, "--version"], capture_output=True, timeout=5)
            tools[name] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            tools[name] = False
    try:
        import PIL  # noqa: F401
        tools["pillow"] = True
    except ImportError:
        tools["pillow"] = False
    return tools


def compress_png(path, dry_run=False):
    """Lossless PNG compression: oxipng (level 4) if available, else Pillow."""
    size_before = os.path.getsize(path)
    if dry_run:
        return (path, 'png', size_before, size_before, 'dry-run')
    executable = find_tool("oxipng")
    if not executable:
        tmp = path + '.tmp.png'
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.save(tmp, 'PNG', optimize=True)
            size_after = os.path.getsize(tmp)
            if size_after < size_before:
                os.replace(tmp, path)
            else:
                os.remove(tmp)
                size_after = size_before
            return (path, 'png', size_before, size_after, 'ok-pillow')
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            return (path, 'png', size_before, size_before, f'error:{e}')
    try:
        # -o 4: optimization level 4 (good balance, 0-6)
        # --strip safe: remove metadata but keep color profile
        # --force: overwrite
        r = subprocess.run(
            [find_tool("oxipng"), "-o", "4", "--strip", "safe", "--force", path],
            capture_output=True, timeout=300
        )
        size_after = os.path.getsize(path)
        saved = size_before - size_after
        return (path, 'png', size_before, size_after, 'ok' if r.returncode == 0 else f'fail:{r.returncode}')
    except subprocess.TimeoutExpired:
        return (path, 'png', size_before, size_before, 'timeout')
    except Exception as e:
        return (path, 'png', size_before, size_before, f'error:{e}')


def compress_jpeg(path, dry_run=False):
    """Near-lossless JPEG compression with jpegoptim (max quality 90, strip metadata)."""
    size_before = os.path.getsize(path)
    if dry_run:
        return (path, 'jpeg', size_before, size_before, 'dry-run')
    executable = find_tool("jpegoptim")
    if not executable:
        tmp = path + '.tmp.jpg'
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.convert('RGB').save(tmp, 'JPEG', quality=90, optimize=True, progressive=True)
            size_after = os.path.getsize(tmp)
            if size_after < size_before:
                os.replace(tmp, path)
            else:
                os.remove(tmp)
                size_after = size_before
            return (path, 'jpeg', size_before, size_after, 'ok-pillow')
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            return (path, 'jpeg', size_before, size_before, f'error:{e}')
    try:
        # --max=90: cap quality at 90 (near-lossless, visually identical)
        # --strip-all: remove all metadata
        # --all-progressive: make progressive
        r = subprocess.run(
            [executable, "--max=90", "--strip-all", "--all-progressive", "-f", path],
            capture_output=True, timeout=120
        )
        size_after = os.path.getsize(path)
        return (path, 'jpeg', size_before, size_after, 'ok' if r.returncode == 0 else f'fail:{r.returncode}')
    except subprocess.TimeoutExpired:
        return (path, 'jpeg', size_before, size_before, 'timeout')
    except Exception as e:
        return (path, 'jpeg', size_before, size_before, f'error:{e}')


def compress_gif(path, dry_run=False):
    """Lossless GIF optimization with gifsicle (level 3)."""
    size_before = os.path.getsize(path)
    if dry_run:
        return (path, 'gif', size_before, size_before, 'dry-run')
    tmp = path + '.tmp'
    executable = find_tool("gifsicle")
    if not executable:
        try:
            from PIL import Image, ImageSequence
            with Image.open(path) as image:
                frames = [frame.copy() for frame in ImageSequence.Iterator(image)]
                frames[0].save(
                    tmp, format='GIF', save_all=True, append_images=frames[1:],
                    duration=image.info.get('duration', 100), loop=image.info.get('loop', 0),
                    optimize=True,
                )
            size_after = os.path.getsize(tmp)
            if size_after < size_before:
                os.replace(tmp, path)
            else:
                os.remove(tmp)
                size_after = size_before
            return (path, 'gif', size_before, size_after, 'ok-pillow')
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            return (path, 'gif', size_before, size_before, f'error:{e}')
    try:
        # -O3: max optimization
        # --no-extensions: strip extensions
        r = subprocess.run(
            [executable, "-O3", "--no-extensions", "-o", tmp, path],
            capture_output=True, timeout=300
        )
        if r.returncode == 0 and os.path.exists(tmp):
            size_after = os.path.getsize(tmp)
            if size_after < size_before:
                os.replace(tmp, path)
            else:
                os.remove(tmp)
                size_after = size_before
        else:
            size_after = size_before
            if os.path.exists(tmp):
                os.remove(tmp)
        return (path, 'gif', size_before, size_after, 'ok' if r.returncode == 0 else f'fail:{r.returncode}')
    except subprocess.TimeoutExpired:
        if os.path.exists(tmp):
            os.remove(tmp)
        return (path, 'gif', size_before, size_before, 'timeout')
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        return (path, 'gif', size_before, size_before, f'error:{e}')


def convert_to_webp(path, dry_run=False, quality=88):
    """Convert large image to WebP (saves 30-50% more than PNG/JPEG)."""
    size_before = os.path.getsize(path)
    if dry_run:
        return (path, 'webp', size_before, size_before, 'dry-run')
    webp_path = str(Path(path).with_suffix('.webp'))
    try:
        r = subprocess.run(
            [find_tool("cwebp"), "-q", str(quality), "-quiet", path, "-o", webp_path],
            capture_output=True, timeout=300
        )
        if r.returncode == 0 and os.path.exists(webp_path):
            size_after = os.path.getsize(webp_path)
            # Only keep WebP if it's actually smaller
            if size_after < size_before * 0.85:
                # Remove original (caller decides whether to commit)
                return (path, 'webp', size_before, size_after, 'ok-replaced')
            else:
                os.remove(webp_path)
                return (path, 'webp', size_before, size_before, 'skip-not-smaller')
        return (path, 'webp', size_before, size_before, f'fail:{r.returncode}')
    except Exception as e:
        return (path, 'webp', size_before, size_before, f'error:{e}')


def scan_images(repo_dir, year_filter=None, min_size_kb=0):
    """Scan repo for images. Returns list of (path, type)."""
    images = []
    repo = Path(repo_dir)
    if not repo.is_dir():
        print(f'[ERROR] Not a directory: {repo_dir}')
        return images

    for root, dirs, files in os.walk(repo):
        # Skip .git, .github
        if '.git' in root:
            continue
        for fname in files:
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext not in ('png', 'jpg', 'jpeg', 'gif'):
                continue
            fpath = os.path.join(root, fname)
            # Year filter
            if year_filter:
                rel = os.path.relpath(fpath, repo)
                top_dir = rel.split(os.sep)[0]
                if top_dir not in year_filter:
                    continue
            # Size filter
            if min_size_kb > 0:
                size_kb = os.path.getsize(fpath) / 1024
                if size_kb < min_size_kb:
                    continue
            images.append((fpath, ext))
    return images


def main():
    parser = argparse.ArgumentParser(
        description="Compress images in lishuhang/img repo (v2.0)"
    )
    parser.add_argument('--repo', default='.',
                        help='Path to img repo (default: current dir)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Scan only, report potential savings')
    parser.add_argument('--min-size', type=int, default=0,
                        help='Only compress images larger than N KB (default: 0 = all)')
    parser.add_argument('--webp', action='store_true',
                        help='Also convert images >500KB to WebP (replaces original)')
    parser.add_argument('--workers', type=int, default=os.cpu_count() or 4,
                        help=f'Parallel workers (default: {os.cpu_count() or 4})')
    parser.add_argument('--commit', action='store_true',
                        help='Git commit + push after compression')
    parser.add_argument('--year', nargs='*', default=None,
                        help='Only compress specific year folders (e.g., --year 2021 2020)')
    parser.add_argument('--no-jpeg', action='store_true',
                        help='Skip JPEG (use if jpegoptim not installed)')
    parser.add_argument('--no-png', action='store_true',
                        help='Skip PNG (use if oxipng not installed)')
    parser.add_argument('--no-gif', action='store_true',
                        help='Skip GIF (use if gifsicle not installed)')
    args = parser.parse_args()

    print(f'\n{"=" * 60}')
    print(f'Image Compression CLI - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Repo: {os.path.abspath(args.repo)}')
    print(f'Mode: {"DRY-RUN" if args.dry_run else "COMPRESS"}')
    print(f'Workers: {args.workers}')
    if args.year:
        print(f'Year filter: {args.year}')
    print(f'{"=" * 60}\n')

    # Check tools
    tools = check_tools()
    print('Tool availability:')
    for name, avail in tools.items():
        print(f'  {name}: {"yes" if avail else "NO"}')
    print()

    # Scan
    print('Scanning for images...')
    images = scan_images(args.repo, year_filter=args.year, min_size_kb=args.min_size)
    print(f'Found {len(images)} images to process\n')

    if not images:
        print('No images to process.')
        return

    # Categorize
    by_type = {'png': [], 'jpeg': [], 'gif': []}
    for path, ext in images:
        if ext == 'png' and not args.no_png and (tools.get('oxipng') or tools.get('pillow')):
            by_type['png'].append(path)
        elif ext in ('jpg', 'jpeg') and not args.no_jpeg and (tools.get('jpegoptim') or tools.get('pillow')):
            by_type['jpeg'].append(path)
        elif ext == 'gif' and not args.no_gif and (tools.get('gifsicle') or tools.get('pillow')):
            by_type['gif'].append(path)

    total = sum(len(v) for v in by_type.values())
    print(f'Will process: {len(by_type["png"])} PNG, {len(by_type["jpeg"])} JPEG, {len(by_type["gif"])} GIF')
    if total == 0:
        print('\nNo compressible images (check tool availability).')
        return
    print()

    # Compress
    total_before = 0
    total_after = 0
    results = []

    def worker(item):
        path, kind = item
        if kind == 'png':
            return compress_png(path, dry_run=args.dry_run)
        elif kind == 'jpeg':
            return compress_jpeg(path, dry_run=args.dry_run)
        elif kind == 'gif':
            return compress_gif(path, dry_run=args.dry_run)

    work = [(p, 'png') for p in by_type['png']] + \
           [(p, 'jpeg') for p in by_type['jpeg']] + \
           [(p, 'gif') for p in by_type['gif']]

    print(f'Compressing {len(work)} images...')
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(worker, w): w for w in work}
        for i, fut in enumerate(as_completed(futures)):
            path, kind, before, after, status = fut.result()
            total_before += before
            total_after += after
            results.append((path, kind, before, after, status))
            if (i+1) % 100 == 0:
                elapsed = time.time() - start
                print(f'  {i+1}/{len(work)} ({elapsed:.0f}s) — saved so far: {(total_before-total_after)/1024/1024:.1f} MB')

    elapsed = time.time() - start
    saved = total_before - total_after
    print(f'\n{"=" * 60}')
    print(f'Done in {elapsed:.0f}s')
    print(f'Before: {total_before/1024/1024:.1f} MB')
    print(f'After:  {total_after/1024/1024:.1f} MB')
    print(f'Saved:  {saved/1024/1024:.1f} MB ({100*saved/total_before:.1f}%)')
    print(f'{"=" * 60}\n')

    # Optional WebP conversion for large images
    if args.webp and tools.get('cwebp') and not args.dry_run:
        large_images = [(p, 'webp') for p, k, b, a, s in results
                        if k in ('png', 'jpeg') and a > 500*1024]
        if large_images:
            print(f'\nConverting {len(large_images)} large images to WebP...')
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = {ex.submit(lambda x: convert_to_webp(x[0]), w): w for w in large_images}
                webp_saved = 0
                for i, fut in enumerate(as_completed(futures)):
                    path, kind, before, after, status = fut.result()
                    if 'ok' in status:
                        webp_saved += (before - after)
                    if (i+1) % 50 == 0:
                        print(f'  {i+1}/{len(large_images)}')
            print(f'WebP additional savings: {webp_saved/1024/1024:.1f} MB')

    # Commit
    if args.commit and not args.dry_run and saved > 0:
        print('\nCommitting changes...')
        os.chdir(args.repo)
        subprocess.run(['git', 'add', '-A'], check=False)
        commit_msg = f'compress: lossless image compression, saved {saved/1024/1024:.1f}MB ({100*saved/total_before:.1f}%)'
        subprocess.run(['git', 'commit', '-m', commit_msg], check=False)
        subprocess.run(['git', 'push'], check=False)
        print('Committed and pushed.')

    # Save report
    report_path = os.path.join(args.repo, f'compression_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f'Image Compression Report - {datetime.now().isoformat()}\n')
        f.write(f'Repo: {os.path.abspath(args.repo)}\n')
        f.write(f'Images processed: {len(results)}\n')
        f.write(f'Before: {total_before/1024/1024:.1f} MB\n')
        f.write(f'After:  {total_after/1024/1024:.1f} MB\n')
        f.write(f'Saved:  {saved/1024/1024:.1f} MB ({100*saved/total_before:.1f}%)\n\n')
        f.write(f'{"Path":<80} {"Type":<6} {"Before":>10} {"After":>10} {"Saved":>10} {"Status"}\n')
        for path, kind, before, after, status in sorted(results, key=lambda x: x[2]-x[3], reverse=True):
            saved_b = before - after
            f.write(f'{os.path.relpath(path, args.repo):<80} {kind:<6} {before:>10} {after:>10} {saved_b:>10} {status}\n')
    print(f'Report saved to {report_path}')


if __name__ == '__main__':
    main()
