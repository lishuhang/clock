#!/usr/bin/env python3
"""
Generate round3.8 — img5 continuous movement dumbbell.

Concept:
  - 10 films on Y axis (2012→2026)
  - X axis = percentage (0-75%)
  - Each film has 3 solid colored dots (no hollow points)
  - ALL dots move CONTINUOUSLY from 上映初期 to 近一年 position
  - Film 0 (2012) appears at t=0, moves slowly over full 12s
  - Film 9 (2026) appears at t=10s, moves fast over 2s
  - Trail line grows behind each dot as it moves
  - At t=12s: all dots at 近一年 position, all trails complete

Timeline (13s):
  0-12s: continuous movement (films appear staggered, all reach curr at t=12)
  12-13s: fadeOut
"""
import os, json, re, pathlib, html, subprocess, asyncio, shutil, glob, math
from playwright.async_api import async_playwright

OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.8"
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
ROW_H = plot_h / 10

def x_pos(pct):
    return PAD_L + (pct / X_MAX) * plot_w

def y_pos(idx):
    return PAD_T + (idx + 0.5) * ROW_H

# Build SVG skeleton — dots and trails will be updated by JS
def build_svg():
    parts = [f'<svg class="dumbbell-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" id="svg">']
    
    # Grid lines
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
    
    # For each film × dimension: trail line + dot + labels
    dim_offsets = [-12, 0, 12]
    dim_names = list(DATA.keys())
    
    for film_idx in range(10):
        for dim_idx, dim_name in enumerate(dim_names):
            info = DATA[dim_name]
            init, curr = info["values"][film_idx]
            color = info["color"]
            x_init = x_pos(init)
            x_curr = x_pos(curr)
            y = y_pos(film_idx) + dim_offsets[dim_idx]
            
            # Trail line (from init to current dot position, updated by JS)
            parts.append(f'<line class="trail" id="trail_{film_idx}_{dim_idx}" x1="{x_init:.0f}" y1="{y:.0f}" x2="{x_init:.0f}" y2="{y:.0f}" stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.4"/>')
            
            # Solid dot (position updated by JS)
            parts.append(f'<circle class="dot" id="dot_{film_idx}_{dim_idx}" cx="{x_init:.0f}" cy="{y:.0f}" r="9" fill="{color}" opacity="0"/>')
            
            # Value label (follows dot, updated by JS)
            parts.append(f'<text class="dot-label" id="label_{film_idx}_{dim_idx}" x="{x_init:.0f}" y="{y-16:.0f}" text-anchor="middle" fill="{color}" font-size="14" font-weight="900" opacity="0">{init}%</text>')
    
    parts.append('</svg>')
    return "\n".join(parts)

# Build JS data
films_js = []
for i, (year, name) in enumerate(FILMS):
    film_data = {"year": year, "name": name, "dims": []}
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

# Film appear times: staggered, all reach curr at t=12s
# Film 0 at t=0, film 9 at t=10s, evenly spaced
appear_times = [i * (10.0 / 9) for i in range(10)]  # 0, 1.11, 2.22, ... 10.0
appear_js = json.dumps(appear_times)

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
.chart-title-1x1{{width:80%;font-size:40px;font-weight:900;color:var(--yz-text);line-height:1.3;opacity:0;transition:opacity 0.6s;}}
.chart-title-1x1.visible{{opacity:1;}}
.chart-logo-1x1{{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;opacity:0;transition:opacity 0.6s;}}
.chart-logo-1x1.visible{{opacity:1;}}
.chart-logo-1x1 svg{{height:80px;width:auto;}}
.chart-body-1x1{{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}}
.chart-footer-1x1{{flex-shrink:0;margin-top:12px;padding-top:10px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}}
.chart-source-1x1{{font-size:24px;color:var(--yz-text-muted);text-align:left;flex:1;opacity:0;transition:opacity 0.6s;}}
.chart-source-1x1.visible{{opacity:1;}}
.chart-part-num{{font-size:20px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:16px;opacity:0;transition:opacity 0.6s;}}
.chart-part-num.visible{{opacity:1;}}

.dumbbell-svg{{width:100%;height:auto;display:block;opacity:0;transition:opacity 0.5s;}}
.dumbbell-svg.visible{{opacity:1;}}
.grid-line{{stroke:#eee;stroke-width:1.5;}}
.axis-line{{stroke:#9a9595;stroke-width:2;}}
.axis-text{{font-family:'AliPuHui',sans-serif;font-size:16px;fill:#9a9595;}}
.film-label{{font-family:'AliPuHui',sans-serif;font-size:18px;fill:#312e2e;font-weight:700;}}
.dot-label{{font-family:'AliPuHui',sans-serif;}}

.chart-legend{{display:flex;gap:24px;margin-top:12px;font-size:22px;color:#6b6666;justify-content:center;opacity:0;transition:opacity 0.6s;}}
.chart-legend.visible{{opacity:1;}}
.chart-legend .legend-item{{display:flex;align-items:center;gap:8px;}}
.chart-legend .legend-swatch{{width:24px;height:8px;border-radius:4px;}}
.chart-legend .legend-dot-solid{{width:18px;height:18px;border-radius:50%;background:#999;}}

#yz-selfcheck-banner{{display:none!important;}}
</style>
</head>
<body>
{sprite_full}
<div class="chart-container-1x1" id="container">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1" id="title">对比上映初期与当下，网友对吴京作品评价的维度在变化</h1>
    <div class="chart-logo-1x1" id="logo"><svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg></div>
  </div>
  <div class="chart-body-1x1">
    {build_svg()}
    <div class="chart-legend" id="legend">
      <div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>专业能力</div>
      <div class="legend-item"><span class="legend-swatch" style="background:#f5a623"></span>民族国家</div>
      <div class="legend-item"><span class="legend-swatch" style="background:#7fd3f0"></span>社会文化/性别</div>
      <div class="legend-item"><span class="legend-dot-solid"></span>评价占比（随时间移动）</div>
    </div>
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1" id="source">数据来源：豆瓣短评，娱乐资本论整理</div>
    <div class="chart-part-num" id="partnum">1/1</div>
  </div>
</div>

<script>
const FILMS = {films_json};
const APPEAR_TIMES = {appear_js}; // [0, 1.11, 2.22, ... 10.0]
const TOTAL_DUR = 12.0; // seconds — all films reach curr at t=12
const FADE_OUT_TIME = 12.5; // start fadeOut at 12.5s
const ANIM_END = 13.5; // total animation duration

window.addEventListener('load', function() {{
  // FadeIn elements
  setTimeout(() => document.getElementById('logo').classList.add('visible'), 100);
  setTimeout(() => document.getElementById('title').classList.add('visible'), 400);
  setTimeout(() => document.getElementById('source').classList.add('visible'), 600);
  setTimeout(() => document.getElementById('partnum').classList.add('visible'), 600);
  setTimeout(() => document.getElementById('legend').classList.add('visible'), 800);
  setTimeout(() => document.getElementById('svg').classList.add('visible'), 500);
  
  const startTime = performance.now();
  
  function animate(now) {{
    const elapsed = (now - startTime) / 1000; // seconds
    
    if (elapsed > ANIM_END) {{
      // Animation done — trigger fadeOut
      document.getElementById('container').style.opacity = '0';
      return;
    }}
    
    // Update each film's dots
    for (let f = 0; f < 10; f++) {{
      const appearTime = APPEAR_TIMES[f];
      const film = FILMS[f];
      
      // Progress: 0 at appearTime, 1 at TOTAL_DUR
      let progress;
      if (elapsed < appearTime) {{
        progress = 0; // not yet appeared
      }} else if (elapsed >= TOTAL_DUR) {{
        progress = 1; // reached final
      }} else {{
        progress = (elapsed - appearTime) / (TOTAL_DUR - appearTime);
      }}
      
      // Ease function (linear for smooth continuous movement)
      // progress is already linear
      
      const dotOpacity = (elapsed >= appearTime) ? 1 : 0;
      
      for (let d = 0; d < 3; d++) {{
        const dim = film.dims[d];
        const x_init = dim.x_init;
        const x_curr = dim.x_curr;
        const x_now = x_init + (x_curr - x_init) * progress;
        
        // Update dot position
        const dot = document.getElementById('dot_' + f + '_' + d);
        if (dot) {{
          dot.setAttribute('cx', x_now.toFixed(1));
          dot.style.opacity = dotOpacity;
        }}
        
        // Update trail (from x_init to x_now)
        const trail = document.getElementById('trail_' + f + '_' + d);
        if (trail) {{
          trail.setAttribute('x2', x_now.toFixed(1));
          trail.style.opacity = dotOpacity ? 0.4 : 0;
        }}
        
        // Update label position and value
        const label = document.getElementById('label_' + f + '_' + d);
        if (label) {{
          label.setAttribute('x', x_now.toFixed(1));
          const val = dim.init + (dim.curr - dim.init) * progress;
          label.textContent = Math.round(val) + '%';
          label.style.opacity = dotOpacity;
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

html_path = os.path.join(OUT_DIR, "img5-continuous-styled.html")
pathlib.Path(html_path).write_text(HTML, encoding="utf-8")
print(f"Wrote {html_path} ({len(HTML)} bytes)")

# Record using Playwright video recording
async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width":1080,"height":1080},
            record_video_dir="/tmp/r38vid",
            record_video_size={"width":1080,"height":1080}
        )
        page = await context.new_page()
        await page.goto("file://"+html_path, wait_until="load")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(100)
        # Animation: 0-12s movement + 0.5-1.5s fadeOut = ~14s total
        await page.wait_for_timeout(15000)
        await context.close()
        await browser.close()
    
    videos = glob.glob("/tmp/r38vid/*.webm")
    if videos:
        webm = videos[0]
        dur_info = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",webm], capture_output=True, text=True).stdout.strip()
        total_dur = float(dur_info)
        print(f"webm duration: {total_dur}s")
        # Trim: skip ~1.5s page load, take 14s
        start_trim = 1.5
        target_dur = min(14.0, total_dur - start_trim)
        mp4_path = os.path.join(OUT_DIR, "img5-continuous.mp4")
        subprocess.run(["ffmpeg","-y","-i",webm,"-ss",str(start_trim),"-t",str(target_dur),"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",mp4_path], capture_output=True, timeout=120)
        sz = os.path.getsize(mp4_path)
        dur = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",mp4_path], capture_output=True, text=True).stdout.strip()
        print(f"MP4: {mp4_path} ({sz//1024}KB, {dur}s)")
        shutil.rmtree("/tmp/r38vid", ignore_errors=True)

asyncio.run(record())
