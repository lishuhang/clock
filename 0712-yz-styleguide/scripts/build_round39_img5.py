#!/usr/bin/env python3
"""
Generate round3.9 — img5 continuous movement, all films simultaneously.

Key changes from round3.8:
  1. No years — only film names on left (no wrapping)
  2. All films start at 上映初期 position simultaneously, slide to 近一年 together
  3. Simple首尾关键帧渐变 (start frame → end frame, no staggered appearance)
  4. Precise data from SVG file
  5. Colors: F1=#17324D, F3=#D94B3D, F5=#C97B8D
  6. Legend: "评价占比（随时间移动）：⚪专业能力 ⚪民族国家 ⚪社会文化/性别"

Timeline (14s):
  0-1s: fadeIn
  1-12s: all dots slide from init to curr simultaneously (11s slow movement)
  12-13s: hold final frame with all trails
  13-14s: fadeOut
"""
import os, json, re, pathlib, html, subprocess, asyncio, shutil, glob, math
from playwright.async_api import async_playwright

OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.9"
os.makedirs(OUT_DIR, exist_ok=True)

with open("/home/z/my-project/scripts/v2.20-svg-sprite.txt", encoding="utf-8") as f:
    sprite = f.read()
with open("/home/z/my-project/scripts/yz-logo-icon-symbol.txt", encoding="utf-8") as f:
    icon = f.read()
sprite_full = sprite.replace("  </defs>", f"  {icon}\n  </defs>")

# Precise data from SVG
FILMS = [
    "我是特种兵之利刃出鞘",
    "杀破狼2",
    "战狼",
    "战狼2",
    "流浪地球",
    "我和我的祖国",
    "长津湖",
    "我和我的父辈",
    "流浪地球2",
    "镖人：风起大漠",
]

# [init, curr] for each film
DATA = {
    "专业能力": {"color": "#17324D", "values": [[29.5,30.7],[55.5,56.0],[31.9,31.0],[42.1,28.3],[64.2,44.0],[51.3,35.0],[35.5,31.0],[39.6,42.0],[41.4,46.7],[67.3,59.0]]},
    "民族国家": {"color": "#D94B3D", "values": [[6.6,9.9],[3.1,0.0],[37.1,19.0],[51.1,24.2],[43.3,25.0],[45.7,36.0],[26.8,19.0],[18.7,18.0],[22.1,23.3],[5.6,2.0]]},
    "社会文化/性别": {"color": "#C97B8D", "values": [[8.2,13.9],[14.1,3.0],[12.1,8.0],[18.5,2.0],[12.8,1.0],[8.1,5.0],[0.5,1.0],[15.9,7.0],[10.7,3.3],[9.5,6.0]]},
}

# SVG dimensions
W = 1000
H = 720
PAD_L, PAD_R, PAD_T, PAD_B = 260, 80, 50, 80
plot_w = W - PAD_L - PAD_R
plot_h = H - PAD_T - PAD_B
X_MAX = 75
ROW_H = plot_h / 10

def x_pos(pct):
    return PAD_L + (pct / X_MAX) * plot_w

def y_pos(idx):
    return PAD_T + (idx + 0.5) * ROW_H

def build_svg():
    parts = [f'<svg class="dumbbell-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" id="svg">']
    
    # Grid lines
    for tick in [0, 15, 30, 45, 60, 75]:
        x = x_pos(tick)
        parts.append(f'<line class="grid-line" x1="{x:.0f}" y1="{PAD_T}" x2="{x:.0f}" y2="{PAD_T+plot_h}"/>')
        parts.append(f'<text class="axis-text" x="{x:.0f}" y="{PAD_T-10}" text-anchor="middle">{tick}%</text>')
    
    # Y axis film labels (no year, no wrapping)
    for i, name in enumerate(FILMS):
        y = y_pos(i)
        parts.append(f'<text class="film-label" x="{PAD_L-16}" y="{y+6:.0f}" text-anchor="end">{html.escape(name)}</text>')
    
    # X axis line
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    
    # For each film × dimension: trail line + dot + label
    dim_offsets = [-14, 0, 14]
    dim_names = list(DATA.keys())
    
    for film_idx in range(10):
        for dim_idx, dim_name in enumerate(dim_names):
            info = DATA[dim_name]
            init, curr = info["values"][film_idx]
            color = info["color"]
            x_init = x_pos(init)
            x_curr = x_pos(curr)
            y = y_pos(film_idx) + dim_offsets[dim_idx]
            
            # Trail line (from init to current position, updated by JS)
            parts.append(f'<line class="trail" id="trail_{film_idx}_{dim_idx}" x1="{x_init:.1f}" y1="{y:.0f}" x2="{x_init:.1f}" y2="{y:.0f}" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.4"/>')
            
            # Solid dot
            parts.append(f'<circle class="dot" id="dot_{film_idx}_{dim_idx}" cx="{x_init:.1f}" cy="{y:.0f}" r="8" fill="{color}" opacity="0"/>')
            
            # Value label
            parts.append(f'<text class="dot-label" id="label_{film_idx}_{dim_idx}" x="{x_init:.1f}" y="{y-14:.0f}" text-anchor="middle" fill="{color}" font-size="13" font-weight="900" opacity="0">{init}%</text>')
    
    parts.append('</svg>')
    return "\n".join(parts)

# Build JS data
films_js = []
for i, name in enumerate(FILMS):
    film_data = {"name": name, "dims": []}
    for dim, info in DATA.items():
        init, curr = info["values"][i]
        film_data["dims"].append({
            "color": info["color"],
            "init": init, "curr": curr,
            "x_init": x_pos(init),
            "x_curr": x_pos(curr),
        })
    films_js.append(film_data)

films_json = json.dumps(films_js, ensure_ascii=False)

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>同一部作品：三种评价框架如何改变？</title>
<style>
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}}
:root{{--yz-text:#312e2e;--yz-text-muted:#9a9595;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui',sans-serif;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:var(--yz-font);background:#fff;padding:0;margin:0;}}
.chart-container-1x1{{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;transition:opacity 0.8s;}}
.chart-header-1x1{{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:12px;gap:24px;}}
.chart-title-1x1{{width:80%;font-size:38px;font-weight:900;color:var(--yz-text);line-height:1.3;opacity:0;transition:opacity 0.6s;}}
.chart-title-1x1.visible{{opacity:1;}}
.chart-logo-1x1{{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;opacity:0;transition:opacity 0.6s;}}
.chart-logo-1x1.visible{{opacity:1;}}
.chart-logo-1x1 svg{{height:76px;width:auto;}}
.chart-body-1x1{{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}}
.chart-footer-1x1{{flex-shrink:0;margin-top:10px;padding-top:10px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}}
.chart-source-1x1{{font-size:22px;color:var(--yz-text-muted);text-align:left;flex:1;opacity:0;transition:opacity 0.6s;}}
.chart-source-1x1.visible{{opacity:1;}}
.chart-part-num{{font-size:20px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:16px;opacity:0;transition:opacity 0.6s;}}
.chart-part-num.visible{{opacity:1;}}

.dumbbell-svg{{width:100%;height:auto;display:block;opacity:0;transition:opacity 0.5s;}}
.dumbbell-svg.visible{{opacity:1;}}
.grid-line{{stroke:#eee;stroke-width:1.5;}}
.axis-line{{stroke:#9a9595;stroke-width:2;}}
.axis-text{{font-family:'AliPuHui',sans-serif;font-size:16px;fill:#9a9595;}}
.film-label{{font-family:'AliPuHui',sans-serif;font-size:18px;fill:#312e2e;font-weight:700;white-space:nowrap;}}
.dot-label{{font-family:'AliPuHui',sans-serif;}}

.chart-legend{{display:flex;gap:20px;margin-top:10px;font-size:22px;color:#6b6666;justify-content:center;opacity:0;transition:opacity 0.6s;flex-wrap:wrap;}}
.chart-legend.visible{{opacity:1;}}
.chart-legend .legend-item{{display:flex;align-items:center;gap:8px;}}
.chart-legend .legend-dot{{width:18px;height:18px;border-radius:50%;flex-shrink:0;}}

#yz-selfcheck-banner{{display:none!important;}}
</style>
</head>
<body>
{sprite_full}
<div class="chart-container-1x1" id="container">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1" id="title">同一部作品：三种评价框架如何改变？</h1>
    <div class="chart-logo-1x1" id="logo"><svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg></div>
  </div>
  <div class="chart-body-1x1">
    {build_svg()}
    <div class="chart-legend" id="legend">
      <div class="legend-item"><span class="legend-dot" style="background:#17324D"></span>专业能力</div>
      <div class="legend-item"><span class="legend-dot" style="background:#D94B3D"></span>民族国家</div>
      <div class="legend-item"><span class="legend-dot" style="background:#C97B8D"></span>社会文化/性别</div>
    </div>
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1" id="source">评价占比（随时间移动）｜数据来源：豆瓣短评，娱乐资本论整理</div>
    <div class="chart-part-num" id="partnum">1/1</div>
  </div>
</div>

<script>
const FILMS = {films_json};
const SLIDE_START = 1.0;  // slide starts at 1s
const SLIDE_END = 12.0;    // slide ends at 12s
const HOLD_END = 13.0;     // hold until 13s
const FADE_OUT = 13.0;     // fadeOut starts
const ANIM_END = 14.0;     // total

window.addEventListener('load', function() {{
  // FadeIn
  setTimeout(() => document.getElementById('logo').classList.add('visible'), 100);
  setTimeout(() => document.getElementById('title').classList.add('visible'), 400);
  setTimeout(() => document.getElementById('source').classList.add('visible'), 600);
  setTimeout(() => document.getElementById('partnum').classList.add('visible'), 600);
  setTimeout(() => document.getElementById('legend').classList.add('visible'), 800);
  setTimeout(() => document.getElementById('svg').classList.add('visible'), 500);
  
  // Show all dots at init position at t=1s
  setTimeout(() => {{
    document.querySelectorAll('.dot').forEach(d => d.style.opacity = 1);
    document.querySelectorAll('.dot-label').forEach(l => l.style.opacity = 1);
  }}, 1000);
  
  const startTime = performance.now();
  
  function animate(now) {{
    const elapsed = (now - startTime) / 1000;
    
    if (elapsed > ANIM_END) {{
      document.getElementById('container').style.opacity = '0';
      return;
    }}
    
    // Calculate slide progress (0 at SLIDE_START, 1 at SLIDE_END)
    let progress;
    if (elapsed < SLIDE_START) {{
      progress = 0;
    }} else if (elapsed >= SLIDE_END) {{
      progress = 1;
    }} else {{
      progress = (elapsed - SLIDE_START) / (SLIDE_END - SLIDE_START);
    }}
    
    // Update all dots simultaneously
    for (let f = 0; f < 10; f++) {{
      const film = FILMS[f];
      for (let d = 0; d < 3; d++) {{
        const dim = film.dims[d];
        const x_init = dim.x_init;
        const x_curr = dim.x_curr;
        const x_now = x_init + (x_curr - x_init) * progress;
        
        const dot = document.getElementById('dot_' + f + '_' + d);
        if (dot) dot.setAttribute('cx', x_now.toFixed(1));
        
        const trail = document.getElementById('trail_' + f + '_' + d);
        if (trail) trail.setAttribute('x2', x_now.toFixed(1));
        
        const label = document.getElementById('label_' + f + '_' + d);
        if (label) {{
          label.setAttribute('x', x_now.toFixed(1));
          const val = dim.init + (dim.curr - dim.init) * progress;
          label.textContent = val.toFixed(1).replace('.0','') + '%';
        }}
      }}
    }}
    
    requestAnimationFrame(animate);
  }}
  
  requestAnimationFrame(animate);
}});
</script>
</body>
</html>"""

html_path = os.path.join(OUT_DIR, "img5-simultaneous-styled.html")
pathlib.Path(html_path).write_text(HTML, encoding="utf-8")
print(f"Wrote {html_path} ({len(HTML)} bytes)")

# Record
async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width":1080,"height":1080},
            record_video_dir="/tmp/r39vid",
            record_video_size={"width":1080,"height":1080}
        )
        page = await context.new_page()
        await page.goto("file://"+html_path, wait_until="load")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(100)
        await page.wait_for_timeout(15000)
        await context.close()
        await browser.close()
    
    videos = glob.glob("/tmp/r39vid/*.webm")
    if videos:
        webm = videos[0]
        dur_info = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",webm], capture_output=True, text=True).stdout.strip()
        total_dur = float(dur_info)
        print(f"webm: {total_dur}s")
        start_trim = 1.5
        target_dur = min(14.0, total_dur - start_trim)
        mp4_path = os.path.join(OUT_DIR, "img5-simultaneous.mp4")
        subprocess.run(["ffmpeg","-y","-i",webm,"-ss",str(start_trim),"-t",str(target_dur),"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",mp4_path], capture_output=True, timeout=120)
        sz = os.path.getsize(mp4_path)
        dur = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",mp4_path], capture_output=True, text=True).stdout.strip()
        print(f"MP4: {sz//1024}KB, {dur}s")
        shutil.rmtree("/tmp/r39vid", ignore_errors=True)

asyncio.run(record())
