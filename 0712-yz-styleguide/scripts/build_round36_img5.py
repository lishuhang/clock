#!/usr/bin/env python3
"""
Generate round3.6 — img5 slider animation, one film at a time.

Layout (vertical, top to bottom):
  年份（2012）
  影片（《我是特种兵之利刃出鞘》）
  专业能力 +n%
  ────●─────────●────  (dumbbell slider, 32% 35%)
  民族国家 +n%
  ────●─────────●────  (8% 12%)
  社会文化/性别 +n%
  ────●─────────●────  (10% 15%)
  图例（上映初期；近一年）

Animation: each film's data shows for ~1s, then transitions to next film.
Total: 10 films × 1.2s = 12s + 1s fadeIn + 1s fadeOut = 14s
"""
import os, json, re, pathlib, html, subprocess, asyncio, shutil, glob
from playwright.async_api import async_playwright

OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.6"
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

X_MAX = 75  # max percentage for track scale

def pct_to_pos(pct):
    """Convert percentage to left position on track (2%..98%)."""
    return max(3, min(97, (pct / X_MAX) * 100))

# Build all film data as JS array
films_js = []
for i, (year, name) in enumerate(FILMS):
    film_data = {"year": year, "name": name, "dims": []}
    for dim, info in DATA.items():
        init, curr = info["values"][i]
        diff = curr - init
        film_data["dims"].append({
            "name": dim, "color": info["color"],
            "init": init, "curr": curr, "diff": diff,
            "init_pos": pct_to_pos(init), "curr_pos": pct_to_pos(curr)
        })
    films_js.append(film_data)

films_json = json.dumps(films_js, ensure_ascii=False)

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
.chart-header-1x1{{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:20px;gap:24px;}}
.chart-title-1x1{{width:80%;font-size:44px;font-weight:900;color:var(--yz-text);line-height:1.3;}}
.chart-logo-1x1{{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}}
.chart-logo-1x1 svg{{height:88px;width:auto;}}
.chart-body-1x1{{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;padding:0 20px;}}
.chart-footer-1x1{{flex-shrink:0;margin-top:16px;padding-top:12px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}}
.chart-source-1x1{{font-size:24px;color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}}
.chart-part-num{{font-size:20px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:16px;}}

/* Film info block */
.film-info{{text-align:center;margin-bottom:24px;}}
.film-year{{font-size:48px;font-weight:900;color:#fc8166;line-height:1.2;}}
.film-name{{font-size:32px;font-weight:700;color:var(--yz-text);margin-top:4px;}}

/* Dimension slider rows */
.dim-rows{{display:flex;flex-direction:column;gap:32px;}}
.dim-row{{display:flex;flex-direction:column;gap:8px;}}
.dim-label{{display:flex;justify-content:space-between;align-items:baseline;font-size:28px;}}
.dim-name{{font-weight:900;color:var(--yz-text);}}
.dim-diff{{font-weight:900;font-size:28px;}}
.dim-diff.up{{color:#fc8166;}}
.dim-diff.down{{color:#6cb0f9;}}
.dim-diff.zero{{color:#9a9595;}}

/* Dumbbell slider */
.dumbbell-track{{position:relative;height:48px;background:#fafafa;border-radius:24px;}}
.dumbbell-track::before{{content:"";position:absolute;top:50%;left:0;right:0;height:3px;background:#eee;transform:translateY(-50%);}}
.dumbbell-line{{position:absolute;top:50%;height:5px;transform:translateY(-50%);z-index:1;transition:all 0.5s ease-in-out;border-radius:3px;}}
.dumbbell-dot{{position:absolute;top:50%;transform:translate(-50%,-50%);width:28px;height:28px;border-radius:50%;border:5px solid #fff;box-shadow:0 0 0 3px currentColor;z-index:2;transition:all 0.5s ease-in-out;}}
.dumbbell-tag{{position:absolute;font-size:24px;font-weight:900;white-space:nowrap;transform:translateX(-50%);transition:all 0.5s ease-in-out;}}
.dumbbell-tag.above{{top:-34px;}}
.dumbbell-tag.below{{bottom:-34px;}}

/* Legend */
.chart-legend{{display:flex;gap:32px;margin-top:24px;font-size:24px;color:#6b6666;justify-content:center;}}
.chart-legend .legend-item{{display:flex;align-items:center;gap:10px;}}
.chart-legend .legend-dot-hollow{{width:22px;height:22px;border-radius:50%;background:#fff;border:3px solid #fc8166;}}
.chart-legend .legend-dot-solid{{width:22px;height:22px;border-radius:50%;background:#fc8166;}}

/* Fade elements */
.fade-element{{opacity:0;transition:opacity 0.5s ease-out;}}
.fade-element.visible{{opacity:1;}}

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
    <div class="film-info fade-element" id="filmInfo">
      <div class="film-year" id="filmYear">2012</div>
      <div class="film-name" id="filmName">我是特种兵之利刃出鞘</div>
    </div>
    <div class="dim-rows" id="dimRows">
      <!-- 3 dimension rows generated by JS -->
    </div>
    <div class="chart-legend fade-element" id="legend">
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
const FILMS = {films_json};

function buildDimRows() {{
  const container = document.getElementById('dimRows');
  container.innerHTML = '';
  FILMS[0].dims.forEach((dim, idx) => {{
    const row = document.createElement('div');
    row.className = 'dim-row fade-element';
    row.id = 'dimRow' + idx;
    const diffSign = dim.diff > 0 ? '+' : '';
    const diffClass = dim.diff > 0 ? 'up' : (dim.diff < 0 ? 'down' : 'zero');
    row.innerHTML = `
      <div class="dim-label">
        <span class="dim-name">${{dim.name}}</span>
        <span class="dim-diff ${{diffClass}}" id="diff${{idx}}">${{diffSign}}${{dim.diff}}%</span>
      </div>
      <div class="dumbbell-track">
        <div class="dumbbell-line" id="line${{idx}}" style="left:${{dim.init_pos}}%;width:${{dim.curr_pos - dim.init_pos}}%;background:${{dim.color}};opacity:0.5;"></div>
        <div class="dumbbell-dot" id="dotInit${{idx}}" style="left:${{dim.init_pos}}%;background:#fff;color:${{dim.color}};"></div>
        <div class="dumbbell-tag above" id="tagInit${{idx}}" style="left:${{dim.init_pos}}%;color:${{dim.color}};">${{dim.init}}%</div>
        <div class="dumbbell-dot" id="dotCurr${{idx}}" style="left:${{dim.curr_pos}}%;background:${{dim.color}};color:${{dim.color}};"></div>
        <div class="dumbbell-tag below" id="tagCurr${{idx}}" style="left:${{dim.curr_pos}}%;color:${{dim.color}};">${{dim.curr}}%</div>
      </div>
    `;
    container.appendChild(row);
  }});
}}

function updateFilm(idx) {{
  const film = FILMS[idx];
  document.getElementById('filmYear').textContent = film.year;
  document.getElementById('filmName').textContent = film.name;
  film.dims.forEach((dim, i) => {{
    const diffSign = dim.diff > 0 ? '+' : '';
    const diffClass = dim.diff > 0 ? 'up' : (dim.diff < 0 ? 'down' : 'zero');
    document.getElementById('diff' + i).textContent = diffSign + dim.diff + '%';
    document.getElementById('diff' + i).className = 'dim-diff ' + diffClass;
    document.getElementById('line' + i).style.left = dim.init_pos + '%';
    document.getElementById('line' + i).style.width = (dim.curr_pos - dim.init_pos) + '%';
    document.getElementById('line' + i).style.background = dim.color;
    document.getElementById('dotInit' + i).style.left = dim.init_pos + '%';
    document.getElementById('dotInit' + i).style.color = dim.color;
    document.getElementById('tagInit' + i).style.left = dim.init_pos + '%';
    document.getElementById('tagInit' + i).textContent = dim.init + '%';
    document.getElementById('tagInit' + i).style.color = dim.color;
    document.getElementById('dotCurr' + i).style.left = dim.curr_pos + '%';
    document.getElementById('dotCurr' + i).style.background = dim.color;
    document.getElementById('dotCurr' + i).style.color = dim.color;
    document.getElementById('tagCurr' + i).style.left = dim.curr_pos + '%';
    document.getElementById('tagCurr' + i).textContent = dim.curr + '%';
    document.getElementById('tagCurr' + i).style.color = dim.color;
  }});
}}

window.addEventListener('load', function() {{
  buildDimRows();
  
  // 0-1s: fadeIn
  setTimeout(() => document.getElementById('logo').classList.add('visible'), 100);
  setTimeout(() => document.getElementById('title').classList.add('visible'), 400);
  setTimeout(() => document.getElementById('source').classList.add('visible'), 600);
  setTimeout(() => document.getElementById('partnum').classList.add('visible'), 600);
  setTimeout(() => document.getElementById('filmInfo').classList.add('visible'), 700);
  setTimeout(() => {{
    document.querySelectorAll('.dim-row').forEach(r => r.classList.add('visible'));
  }}, 900);
  setTimeout(() => document.getElementById('legend').classList.add('visible'), 1000);
  
  // 1.5s: film 0 already shown (buildDimRows used film 0)
  // Then cycle through films 1-9, each at 1.2s interval
  for (let i = 1; i < 10; i++) {{
    setTimeout(() => updateFilm(i), 1500 + (i - 1) * 1200);
  }}
  
  // Last film at 1500 + 9*1200 = 12300ms = 12.3s
  // Hold 1s, then fadeOut at 13.3s
  setTimeout(() => {{
    document.getElementById('container').style.opacity = '0';
  }}, 13300);
}});
</script>
</body>
</html>"""

html_path = os.path.join(OUT_DIR, "img5-slider-styled.html")
pathlib.Path(html_path).write_text(HTML, encoding="utf-8")
print(f"Wrote {html_path} ({len(HTML)} bytes)")

# Record using Playwright video recording (stable)
async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width":1080,"height":1080},
            record_video_dir="/tmp/r36vid",
            record_video_size={"width":1080,"height":1080}
        )
        page = await context.new_page()
        await page.goto("file://"+html_path, wait_until="load")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(200)
        # Total animation ~14.1s (0-1s fadeIn + 1.5-12.3s films + 13.3s fadeOut + 0.8s transition)
        await page.wait_for_timeout(15000)
        await context.close()
        await browser.close()
    
    videos = glob.glob("/tmp/r36vid/*.webm")
    if videos:
        webm = videos[0]
        dur_info = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",webm], capture_output=True, text=True).stdout.strip()
        total_dur = float(dur_info)
        print(f"webm duration: {total_dur}s")
        # Trim to 14.5s (animation duration)
        target_dur = min(14.5, total_dur)
        start_trim = max(0, total_dur - target_dur - 0.3)
        mp4_path = os.path.join(OUT_DIR, "img5-slider.mp4")
        subprocess.run(["ffmpeg","-y","-i",webm,"-ss",str(start_trim),"-t",str(target_dur),"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",mp4_path], capture_output=True, timeout=120)
        sz = os.path.getsize(mp4_path)
        dur = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",mp4_path], capture_output=True, text=True).stdout.strip()
        print(f"MP4: {mp4_path} ({sz//1024}KB, {dur}s)")
        shutil.rmtree("/tmp/r36vid", ignore_errors=True)

asyncio.run(record())
