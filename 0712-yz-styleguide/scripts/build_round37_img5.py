#!/usr/bin/env python3
"""
Generate round3.7 — img5 animated dumbbell with trails.

Concept:
  - 10 films on Y axis (top to bottom: 2012→2026)
  - X axis = percentage (0-75%)
  - Each film has 3 colored dots (专业能力/民族国家/社会文化性别)
  - Animation: films appear one by one (top to bottom)
  - For each film, 3 dots animate from "上映初期" X position to "近一年" X position
  - A trail line is left behind showing the path
  - No arrows, just dots + trail lines
  - Final frame: all 10 films with 3 trails + 3 end dots each

Timeline:
  0-1s: fadeIn (title, axes)
  1-2s: film 1 (2012) dots appear at init position, then slide to curr position
  2-3s: film 2 (2015) ...
  ...
  10-11s: film 10 (2026)
  11-12s: hold
  12-13s: fadeOut
  Total: ~13s
"""
import os, json, re, pathlib, html, subprocess, asyncio, shutil, glob, math
from playwright.async_api import async_playwright

OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.7"
os.makedirs(OUT_DIR, exist_ok=True)

with open("/home/z/my-project/scripts/v2.20-svg-sprite.txt", encoding="utf-8") as f:
    sprite = f.read()
with open("/home/z/my-project/scripts/yz-logo-icon-symbol.txt", encoding="utf-8") as f:
    icon = f.read()
sprite_full = sprite.replace("  </defs>", f"  {icon}\n  </defs>")

FILMS = [
    ("2012", "我是特种兵之利刃出鞘"),
    ("2015", "杀破狼2"),
    ("2015", "战狼"),
    ("2017", "战狼2"),
    ("2019", "流浪地球"),
    ("2019", "我和我的祖国"),
    ("2021", "长津湖"),
    ("2021", "我和我的父辈"),
    ("2023", "流浪地球2"),
    ("2026", "镖人：风起大漠"),
]

DATA = {
    "专业能力": {"color": "#fc8166", "values": [[32,35],[58,60],[38,40],[42,50],[48,68],[50,62],[40,43],[52,55],[52,55],[65,70]]},
    "民族国家": {"color": "#f5a623", "values": [[8,12],[4,8],[28,45],[35,55],[35,52],[45,53],[22,30],[18,20],[22,25],[8,12]]},
    "社会文化/性别": {"color": "#7fd3f0", "values": [[10,15],[18,22],[14,18],[22,28],[18,25],[8,12],[2,4],[16,20],[12,16],[12,15]]},
}

# SVG dimensions
W = 1000
H = 700
PAD_L, PAD_R, PAD_T, PAD_B = 100, 80, 60, 100
plot_w = W - PAD_L - PAD_R
plot_h = H - PAD_T - PAD_B
X_MAX = 75
ROW_H = plot_h / 10  # 10 films

def x_pos(pct):
    return PAD_L + (pct / X_MAX) * plot_w

def y_pos(idx):
    return PAD_T + (idx + 0.5) * ROW_H

# Build SVG
def build_svg():
    parts = [f'<svg class="dumbbell-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">']
    
    # Grid lines (vertical, at 0/15/30/45/60/75%)
    for tick in [0, 15, 30, 45, 60, 75]:
        x = x_pos(tick)
        parts.append(f'<line class="grid-line" x1="{x:.0f}" y1="{PAD_T}" x2="{x:.0f}" y2="{PAD_T+plot_h}"/>')
        parts.append(f'<text class="axis-text" x="{x:.0f}" y="{PAD_T+plot_h+28}" text-anchor="middle">{tick}%</text>')
    
    # Y axis film labels
    for i, (year, name) in enumerate(FILMS):
        y = y_pos(i)
        short = name if len(name) <= 7 else name[:6] + '…'
        parts.append(f'<text class="film-label" x="{PAD_L-12}" y="{y+5:.0f}" text-anchor="end">{year} {html.escape(short)}</text>')
    
    # X axis line
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    
    # For each film, 3 dimensions
    # Each dimension offset slightly in Y to avoid overlap (like original)
    dim_offsets = [-12, 0, 12]  # 专业能力 up, 民族国家 middle, 社会文化 down
    dim_names = list(DATA.keys())
    
    for film_idx in range(10):
        for dim_idx, dim_name in enumerate(dim_names):
            info = DATA[dim_name]
            init, curr = info["values"][film_idx]
            color = info["color"]
            x_init = x_pos(init)
            x_curr = x_pos(curr)
            y = y_pos(film_idx) + dim_offsets[dim_idx]
            
            # Trail line (hidden initially, revealed during animation)
            # We use stroke-dasharray to "draw" the line
            line_len = abs(x_curr - x_init)
            parts.append(f'<line class="trail film-{film_idx} dim-{dim_idx}" x1="{x_init:.0f}" y1="{y:.0f}" x2="{x_curr:.0f}" y2="{y:.0f}" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.5" stroke-dasharray="{line_len:.0f}" stroke-dashoffset="{line_len:.0f}"/>')
            
            # Init dot (hollow, smaller — start point, fades after animation)
            parts.append(f'<circle class="dot-init film-{film_idx} dim-{dim_idx}" cx="{x_init:.0f}" cy="{y:.0f}" r="5" fill="#fff" stroke="{color}" stroke-width="2.5" opacity="0"/>')
            
            # Moving dot (the animated one)
            parts.append(f'<circle class="dot-move film-{film_idx} dim-{dim_idx}" cx="{x_init:.0f}" cy="{y:.0f}" r="9" fill="{color}" opacity="0"/>')
            
            # Curr dot (solid, final position)
            parts.append(f'<circle class="dot-curr film-{film_idx} dim-{dim_idx}" cx="{x_curr:.0f}" cy="{y:.0f}" r="8" fill="{color}" opacity="0"/>')
            
            # Value labels (shown after animation)
            parts.append(f'<text class="label-init film-{film_idx} dim-{dim_idx}" x="{x_init-8:.0f}" y="{y+4:.0f}" text-anchor="end" fill="{color}" font-size="13" font-weight="700" opacity="0">{init}%</text>')
            parts.append(f'<text class="label-curr film-{film_idx} dim-{dim_idx}" x="{x_curr+8:.0f}" y="{y+4:.0f}" text-anchor="start" fill="{color}" font-size="14" font-weight="900" opacity="0">{curr}%</text>')
    
    parts.append('</svg>')
    return "\n".join(parts)

# Generate CSS for animations
# Each film animates at time 1 + film_idx * 1.0s
# Within each film: dot-move slides from init to curr (0.5s), trail draws simultaneously
# After slide: dot-curr appears, label-curr appears

def build_animations():
    css = ""
    for film_idx in range(10):
        start_t = 1.0 + film_idx * 1.0  # 1s, 2s, 3s, ... 10s
        slide_dur = 0.5
        slide_end = start_t + slide_dur
        
        for dim_idx in range(3):
            info = list(DATA.values())[dim_idx]
            init, curr = info["values"][film_idx]
            x_init = x_pos(init)
            x_curr = x_pos(curr)
            line_len = abs(x_curr - x_init)
            
            # Trail: stroke-dashoffset from line_len to 0
            css += f".trail.film-{film_idx}.dim-{dim_idx}{{ animation: drawTrail_{film_idx}_{dim_idx} {slide_dur}s ease-in-out {start_t}s forwards; }}\n"
            css += f"@keyframes drawTrail_{film_idx}_{dim_idx}{{ to {{ stroke-dashoffset: 0; }} }}\n"
            
            # dot-move: cx from x_init to x_curr, opacity 0→1 at start, 1→0 at end
            css += f".dot-move.film-{film_idx}.dim-{dim_idx}{{ animation: moveDot_{film_idx}_{dim_idx} {slide_dur}s ease-in-out {start_t}s forwards; }}\n"
            css += f"@keyframes moveDot_{film_idx}_{dim_idx}{{ 0%{{ opacity:0; }} 10%{{ opacity:1; }} 90%{{ opacity:1; }} 100%{{ opacity:0; cx:{x_curr:.0f}px; }} }}\n"
            
            # dot-init: appears at start_t, stays
            css += f".dot-init.film-{film_idx}.dim-{dim_idx}{{ animation: fadeIn 0.2s ease-out {start_t}s forwards; }}\n"
            
            # dot-curr: appears at slide_end
            css += f".dot-curr.film-{film_idx}.dim-{dim_idx}{{ animation: fadeIn 0.3s ease-out {slide_end}s forwards; }}\n"
            
            # labels
            css += f".label-init.film-{film_idx}.dim-{dim_idx}{{ animation: fadeIn 0.2s ease-out {start_t}s forwards; }}\n"
            css += f".label-curr.film-{film_idx}.dim-{dim_idx}{{ animation: fadeIn 0.3s ease-out {slide_end}s forwards; }}\n"
    
    return css

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>对比上映初期与当下，网友对吴京作品评价的维度在变化</title>
<style>
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}}
:root{{--yz-text:#312e2e;--yz-text-muted:#9a9595;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui',sans-serif;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:var(--yz-font);background:#fff;padding:0;margin:0;}}
.chart-container-1x1{{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;transition:opacity 0.8s;}}
.chart-header-1x1{{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:16px;gap:24px;}}
.chart-title-1x1{{width:80%;font-size:40px;font-weight:900;color:var(--yz-text);line-height:1.3;opacity:0;animation:fadeIn 0.6s ease-out 0.1s forwards;}}
.chart-logo-1x1{{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;opacity:0;animation:fadeIn 0.6s ease-out 0s forwards;}}
.chart-logo-1x1 svg{{height:80px;width:auto;}}
.chart-body-1x1{{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}}
.chart-footer-1x1{{flex-shrink:0;margin-top:12px;padding-top:10px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}}
.chart-source-1x1{{font-size:24px;color:var(--yz-text-muted);text-align:left;flex:1;opacity:0;animation:fadeIn 0.6s ease-out 0.3s forwards;}}
.chart-part-num{{font-size:20px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:16px;opacity:0;animation:fadeIn 0.6s ease-out 0.3s forwards;}}

.dumbbell-svg{{width:100%;height:auto;display:block;opacity:0;animation:fadeIn 0.5s ease-out 0.5s forwards;}}
.grid-line{{stroke:#eee;stroke-width:1.5;}}
.axis-line{{stroke:#9a9595;stroke-width:2;}}
.axis-text{{font-family:'AliPuHui',sans-serif;font-size:16px;fill:#9a9595;}}
.film-label{{font-family:'AliPuHui',sans-serif;font-size:18px;fill:#312e2e;font-weight:700;}}

/* Chart legend */
.chart-legend{{display:flex;gap:24px;margin-top:12px;font-size:22px;color:#6b6666;justify-content:center;opacity:0;animation:fadeIn 0.6s ease-out 0.4s forwards;}}
.chart-legend .legend-item{{display:flex;align-items:center;gap:8px;}}
.chart-legend .legend-swatch{{width:24px;height:8px;border-radius:4px;}}
.chart-legend .legend-dot-hollow{{width:18px;height:18px;border-radius:50%;background:#fff;border:3px solid #999;}}
.chart-legend .legend-dot-solid{{width:18px;height:18px;border-radius:50%;background:#999;}}

/* Initial state */
.trail, .dot-init, .dot-move, .dot-curr, .label-init, .label-curr {{ opacity:0; }}

@keyframes fadeIn{{ to{{ opacity:1; }} }}

/* Per-film animations */
{build_animations()}

/* FadeOut entire container at 11.5s */
.chart-container-1x1{{ animation: fadeOut 1s ease-out 11.5s forwards; }}
@keyframes fadeOut{{ to{{ opacity:0; }} }}

#yz-selfcheck-banner{{display:none!important;}}
</style>
</head>
<body>
{sprite_full}
<div class="chart-container-1x1" id="container">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1">对比上映初期与当下，网友对吴京作品评价的维度在变化</h1>
    <div class="chart-logo-1x1"><svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg></div>
  </div>
  <div class="chart-body-1x1">
    {build_svg()}
    <div class="chart-legend">
      <div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>专业能力</div>
      <div class="legend-item"><span class="legend-swatch" style="background:#f5a623"></span>民族国家</div>
      <div class="legend-item"><span class="legend-swatch" style="background:#7fd3f0"></span>社会文化/性别</div>
      <div class="legend-item"><span class="legend-dot-hollow"></span>上映初期</div>
      <div class="legend-item"><span class="legend-dot-solid"></span>近一年</div>
    </div>
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1">数据来源：豆瓣短评，娱乐资本论整理</div>
    <div class="chart-part-num">1/1</div>
  </div>
</div>
</body>
</html>"""

html_path = os.path.join(OUT_DIR, "img5-dumbbell-trail-styled.html")
pathlib.Path(html_path).write_text(HTML, encoding="utf-8")
print(f"Wrote {html_path} ({len(HTML)} bytes)")

# Record using Playwright video recording
async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width":1080,"height":1080},
            record_video_dir="/tmp/r37vid",
            record_video_size={"width":1080,"height":1080}
        )
        page = await context.new_page()
        await page.goto("file://"+html_path, wait_until="load")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(200)
        # Animation: 0-1s fadeIn, 1-11s films, 11.5-12.5s fadeOut = ~13s
        await page.wait_for_timeout(14000)
        await context.close()
        await browser.close()
    
    videos = glob.glob("/tmp/r37vid/*.webm")
    if videos:
        webm = videos[0]
        dur_info = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",webm], capture_output=True, text=True).stdout.strip()
        total_dur = float(dur_info)
        print(f"webm duration: {total_dur}s")
        target_dur = min(13.0, total_dur)
        start_trim = max(0, total_dur - target_dur - 0.3)
        mp4_path = os.path.join(OUT_DIR, "img5-dumbbell-trail.mp4")
        subprocess.run(["ffmpeg","-y","-i",webm,"-ss",str(start_trim),"-t",str(target_dur),"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",mp4_path], capture_output=True, timeout=120)
        sz = os.path.getsize(mp4_path)
        dur = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",mp4_path], capture_output=True, text=True).stdout.strip()
        print(f"MP4: {mp4_path} ({sz//1024}KB, {dur}s)")
        shutil.rmtree("/tmp/r37vid", ignore_errors=True)

asyncio.run(record())
