#!/usr/bin/env python3
"""
Generate img5 time-line slider animation for round3.5 — v2 with JS-controlled timeline.
CSS animations were unreliable; use JS to add 'visible' class at precise times.
"""
import os, pathlib, html, subprocess, asyncio, shutil
from playwright.async_api import async_playwright

OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.5"
os.makedirs(OUT_DIR, exist_ok=True)

with open("/home/z/my-project/scripts/v2.20-svg-sprite.txt", encoding="utf-8") as f:
    sprite = f.read()
with open("/home/z/my-project/scripts/yz-logo-icon-symbol.txt", encoding="utf-8") as f:
    icon = f.read()
sprite_full = sprite.replace("  </defs>", f"  {icon}\n  </defs>")

FILMS = [
    ("2012", "我是特种兵"), ("2015", "杀破狼2"), ("2015", "战狼"), ("2017", "战狼2"),
    ("2019", "流浪地球"), ("2019", "我和我的祖国"), ("2021", "长津湖"), ("2021", "我和我的父辈"),
    ("2023", "流浪地球2"), ("2026", "镖人"),
]

DATA = {
    "专业能力": {"color": "#fc8166", "values": [[32,35],[58,60],[38,40],[42,50],[48,68],[50,62],[40,43],[52,55],[52,55],[65,70]]},
    "民族国家": {"color": "#f5a623", "values": [[8,12],[4,8],[28,45],[35,55],[35,52],[45,53],[22,30],[18,20],[22,25],[8,12]]},
    "社会文化/性别": {"color": "#7fd3f0", "values": [[10,15],[18,22],[14,18],[22,28],[18,25],[8,12],[2,4],[16,20],[12,16],[12,15]]},
}

W, H = 1000, 560
PAD_L, PAD_R, PAD_T, PAD_B = 80, 60, 60, 100
plot_w = W - PAD_L - PAD_R
plot_h = H - PAD_T - PAD_B
Y_MAX = 75

def x_pos(i):
    return PAD_L + (i / 9) * plot_w

def y_pos(v):
    return PAD_T + plot_h - (v / Y_MAX) * plot_h

def build_svg():
    parts = [f'<svg class="timeline-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">']
    # Grid
    for t in [0, 15, 30, 45, 60, 75]:
        y = y_pos(t)
        parts.append(f'<line class="grid-line" x1="{PAD_L}" y1="{y:.0f}" x2="{W-PAD_R}" y2="{y:.0f}"/>')
        parts.append(f'<text class="axis-text" x="{PAD_L-12}" y="{y+7:.0f}" text-anchor="end">{t}%</text>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+plot_h}"/>')
    for i, (year, name) in enumerate(FILMS):
        x = x_pos(i)
        parts.append(f'<text class="axis-text-year" x="{x:.0f}" y="{PAD_T+plot_h+26}" text-anchor="middle">{year}</text>')
        parts.append(f'<text class="axis-text-film" x="{x:.0f}" y="{PAD_T+plot_h+50}" text-anchor="middle">{html.escape(name)}</text>')
    
    dim_idx = 0
    for dim_name, info in DATA.items():
        color = info["color"]
        vals = info["values"]
        init_pts = [(x_pos(i), y_pos(v[0])) for i, v in enumerate(vals)]
        curr_pts = [(x_pos(i), y_pos(v[1])) for i, v in enumerate(vals)]
        init_str = " ".join(f"{x:.0f},{y:.0f}" for x, y in init_pts)
        curr_str = " ".join(f"{x:.0f},{y:.0f}" for x, y in curr_pts)
        parts.append(f'<polyline class="line-init dim-{dim_idx}" points="{init_str}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.35"/>')
        parts.append(f'<polyline class="line-curr dim-{dim_idx}" points="{curr_str}" fill="none" stroke="{color}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')
        for i, (init, curr) in enumerate(vals):
            x = x_pos(i)
            y_i = y_pos(init)
            y_c = y_pos(curr)
            parts.append(f'<line class="dumbbell-seg dim-{dim_idx} film-{i}" x1="{x:.0f}" y1="{y_i:.0f}" x2="{x:.0f}" y2="{y_c:.0f}" stroke="{color}" stroke-width="2" opacity="0.5"/>')
            parts.append(f'<circle class="dot-init dim-{dim_idx} film-{i}" cx="{x:.0f}" cy="{y_i:.0f}" r="6" fill="#fff" stroke="{color}" stroke-width="2.5"/>')
            parts.append(f'<circle class="dot-curr dim-{dim_idx} film-{i}" cx="{x:.0f}" cy="{y_c:.0f}" r="7" fill="{color}"/>')
            parts.append(f'<text class="label-curr dim-{dim_idx} film-{i}" x="{x:.0f}" y="{y_c-12:.0f}" text-anchor="middle" fill="{color}" font-size="16" font-weight="900">{curr}%</text>')
            parts.append(f'<text class="label-init dim-{dim_idx} film-{i}" x="{x:.0f}" y="{y_i+18:.0f}" text-anchor="middle" fill="{color}" font-size="14" font-weight="700" opacity="0.7">{init}%</text>')
        dim_idx += 1
    
    # Slider cursor
    parts.append(f'<g class="slider-group">')
    parts.append(f'<line class="slider-cursor" x1="0" y1="{PAD_T-10}" x2="0" y2="{PAD_T+plot_h+10}" stroke="#312e2e" stroke-width="3" stroke-dasharray="8,4"/>')
    parts.append(f'<text class="slider-label" x="0" y="{PAD_T-20}" text-anchor="middle" font-size="20" font-weight="900" fill="#312e2e">2012</text>')
    parts.append(f'</g>')
    parts.append('</svg>')
    return "\n".join(parts)

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
.chart-container-1x1{{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;transition:opacity 0.5s;}}
.chart-header-1x1{{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:24px;gap:24px;}}
.chart-title-1x1{{width:80%;font-size:48px;font-weight:900;color:var(--yz-text);line-height:1.35;}}
.chart-logo-1x1{{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}}
.chart-logo-1x1 svg{{height:96px;width:auto;}}
.chart-body-1x1{{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}}
.chart-footer-1x1{{flex-shrink:0;margin-top:20px;padding-top:14px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}}
.chart-source-1x1{{font-size:27px;color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}}
.chart-part-num{{font-size:24px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:20px;}}
.timeline-svg{{width:100%;height:auto;display:block;}}
.grid-line{{stroke:#eee;stroke-width:1.5;}}
.axis-line{{stroke:#9a9595;stroke-width:2;}}
.axis-text{{font-family:'AliPuHui',sans-serif;font-size:18px;fill:#9a9595;}}
.axis-text-year{{font-family:'AliPuHui',sans-serif;font-size:20px;fill:#312e2e;font-weight:900;}}
.axis-text-film{{font-family:'AliPuHui',sans-serif;font-size:14px;fill:#6b6666;font-weight:700;}}
.chart-legend{{display:flex;flex-wrap:wrap;gap:18px 36px;margin-top:20px;font-size:24px;color:#6b6666;justify-content:center;}}
.chart-legend .legend-item{{display:flex;align-items:center;gap:12px;}}
.chart-legend .legend-swatch{{width:28px;height:8px;border-radius:4px;}}
.chart-legend .legend-dot-hollow{{width:20px;height:20px;border-radius:50%;background:#fff;border:3px solid #fc8166;}}
.chart-legend .legend-dot-solid{{width:20px;height:20px;border-radius:50%;background:#fc8166;}}

/* Initial state: everything hidden */
.fade-element{{opacity:0; transition:opacity 0.4s ease-out;}}
.fade-element.visible{{opacity:1;}}
.dumbbell-seg, .dot-init, .dot-curr, .label-curr, .label-init{{opacity:0; transition:opacity 0.3s ease-out;}}
.dumbbell-seg.visible, .dot-init.visible, .dot-curr.visible, .label-curr.visible, .label-init.visible{{opacity:0.8;}}
.dot-curr.visible{{opacity:1;}}
.label-curr.visible{{opacity:1;}}
.slider-group{{opacity:0; transition:opacity 0.3s; transform:translateX({PAD_L}px);}}
.slider-group.visible{{opacity:1;}}
.slider-group{{transition:transform 0.8s ease-in-out, opacity 0.3s;}}
#yz-selfcheck-banner{{display:none!important;}}
</style>
</head>
<body>
{sprite_full}
<div class="chart-container-1x1" id="container">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1 fade-element" id="title">对比上映初期与当下，网友对吴京作品评价的维度在变化</h1>
    <div class="chart-logo-1x1 fade-element" id="logo"><svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg></div>
  </div>
  <div class="chart-body-1x1">
    <div class="fade-element" id="svg-wrap" style="display:flex;justify-content:center;">
      {build_svg()}
    </div>
    <div class="chart-legend fade-element" id="legend">
      <div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>专业能力</div>
      <div class="legend-item"><span class="legend-swatch" style="background:#f5a623"></span>民族国家</div>
      <div class="legend-item"><span class="legend-swatch" style="background:#7fd3f0"></span>社会文化/性别</div>
      <div class="legend-item"><span class="legend-dot-hollow"></span>上映初期</div>
      <div class="legend-item"><span class="legend-dot-solid"></span>近一年</div>
    </div>
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1 fade-element" id="source">数据来源：豆瓣短评，娱乐资本论整理</div>
    <div class="chart-part-num fade-element" id="partnum">1/1</div>
  </div>
</div>

<script>
// JS-controlled timeline
// 0-1s: fadeIn logo, title, legend, source, svg
// 1-2s: hold 2012 (show film 0 data + slider at film 0)
// 2-10s: slide through films 1-9 (0.8s per film, slider moves)
// 10-11s: hold 2026
// 11-12s: fadeOut entire container

const FILMS_X = [{','.join(f"{x_pos(i):.0f}" for i in range(10))}];
const FILMS_YEAR = [{','.join(f'"{y}"' for y, n in FILMS)}];

function show(id) {{
  const el = document.getElementById(id);
  if (el) el.classList.add('visible');
}}

function showFilm(idx) {{
  document.querySelectorAll('.film-' + idx).forEach(el => el.classList.add('visible'));
}}

function moveSlider(idx) {{
  const sg = document.querySelector('.slider-group');
  if (sg) {{
    sg.style.transform = 'translateX(' + FILMS_X[idx] + 'px)';
    const label = sg.querySelector('.slider-label');
    if (label) label.textContent = FILMS_YEAR[idx];
  }}
}}

// Timeline
window.addEventListener('load', function() {{
  // 0s: start fadeIn
  setTimeout(() => show('logo'), 100);
  setTimeout(() => show('title'), 400);
  setTimeout(() => show('legend'), 700);
  setTimeout(() => show('source'), 700);
  setTimeout(() => show('partnum'), 700);
  setTimeout(() => show('svg-wrap'), 900);
  
  // 1.0s: show slider at film 0
  setTimeout(() => {{
    document.querySelector('.slider-group').classList.add('visible');
    moveSlider(0);
  }}, 1000);
  // 1.1s: show film 0 data
  setTimeout(() => showFilm(0), 1100);
  
  // 2.0s: film 1
  setTimeout(() => {{ showFilm(1); moveSlider(1); }}, 2000);
  // 2.8s: film 2
  setTimeout(() => {{ showFilm(2); moveSlider(2); }}, 2800);
  // 3.6s: film 3
  setTimeout(() => {{ showFilm(3); moveSlider(3); }}, 3600);
  // 4.4s: film 4
  setTimeout(() => {{ showFilm(4); moveSlider(4); }}, 4400);
  // 5.2s: film 5
  setTimeout(() => {{ showFilm(5); moveSlider(5); }}, 5200);
  // 6.0s: film 6
  setTimeout(() => {{ showFilm(6); moveSlider(6); }}, 6000);
  // 6.8s: film 7
  setTimeout(() => {{ showFilm(7); moveSlider(7); }}, 6800);
  // 7.6s: film 8
  setTimeout(() => {{ showFilm(8); moveSlider(8); }}, 7600);
  // 8.4s: film 9 (2026 镖人)
  setTimeout(() => {{ showFilm(9); moveSlider(9); }}, 8400);
  
  // 10.5s: start fadeOut
  setTimeout(() => {{
    document.getElementById('container').style.opacity = '0';
  }}, 10500);
}});
</script>
</body>
</html>"""

html_path = os.path.join(OUT_DIR, "img5-timeline-styled.html")
pathlib.Path(html_path).write_text(HTML, encoding="utf-8")
print(f"Wrote {html_path} ({len(HTML)} bytes)")

# Record MP4
async def record():
    frames_dir = "/tmp/r35v2_img5"
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir): os.remove(os.path.join(frames_dir, f))
    FPS = 30
    DUR = 12.0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width":1100,"height":1100})
        await page.goto("file://"+html_path, wait_until="networkidle")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(50)
        container = await page.query_selector(".chart-container-1x1")
        total = int(FPS * DUR)
        for i in range(total):
            await container.screenshot(path=os.path.join(frames_dir, f"frame_{i:04d}.png"))
            await asyncio.sleep(1.0/FPS)
        await browser.close()
    mp4_path = os.path.join(OUT_DIR, "img5-timeline.mp4")
    subprocess.run(["ffmpeg","-y","-framerate",str(FPS),
                    "-i",os.path.join(frames_dir,"frame_%04d.png"),
                    "-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",
                    mp4_path], capture_output=True, timeout=120)
    shutil.rmtree(frames_dir, ignore_errors=True)
    sz = os.path.getsize(mp4_path)
    dur = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",mp4_path], capture_output=True, text=True).stdout.strip()
    print(f"MP4: {mp4_path} ({sz//1024}KB, {dur}s)")

asyncio.run(record())
