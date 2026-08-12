#!/usr/bin/env python3
"""
Generate round2 (1:1) and round3 (animated MP4) for 0812-test.
Reuses v2.22b 1:1 template + round3.4 animation CSS.
Split plan based on content density:
  img2 (3 rows × 6 cols bar+line) → no split (1 image)
  img3 (4 rows × 5 cols bar+line) → no split (1 image)
  img4 (6 rows × 6 cols stacked+line) → 3-3 split (2 images)
  img6 (5 rows × 5 cols multi-line) → no split (1 image)
  img7 (11 rows table) → 4-4-3 split (3 images)
  img8 (5 rows × 5 cols multi-line) → no split (1 image)
  img10 (12 rows table) → 4-4-4 split (3 images)
  img11 (7 rows table) → 4-3 split (2 images)
  img12 (9 rows table) → 3-3-3 split (3 images)
  Total: 17 1:1 images
"""
import os, json, re, pathlib, html, math, glob

VLM_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/_vlm"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/round2"
os.makedirs(OUT_DIR, exist_ok=True)

def load_vlm(idx):
    path = os.path.join(VLM_DIR, f"img{idx}.json")
    with open(path, encoding="utf-8") as f:
        outer = json.load(f)
    content = outer["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n",1)[1].rsplit("```",1)[0]
    return json.loads(content)

def esc(s):
    return html.escape(str(s) if s is not None else "")

def num(s):
    if not s or s == '-': return 0
    s = str(s).replace('~','').replace('%','').replace(',','').strip()
    try: return float(s)
    except: return 0

# SVG sprite
with open("/home/z/my-project/scripts/v2.20-svg-sprite.txt", encoding="utf-8") as f:
    sprite = f.read()
with open("/home/z/my-project/scripts/yz-logo-icon-symbol.txt", encoding="utf-8") as f:
    icon = f.read()
sprite_full = sprite.replace("  </defs>", f"  {icon}\n  </defs>")

TEMPLATE_1x1 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>__TITLE__</title>
<style>
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}
:root{--yz-accent:#fc8166;--yz-text:#312e2e;--yz-text-muted:#9a9595;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui',sans-serif;--yz-fs-body:40px;--yz-fs-title:48px;--yz-fs-footer:27px;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:var(--yz-font);background:#fff;padding:0;margin:0;}
.chart-container-1x1{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;}
.chart-header-1x1{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:24px;gap:24px;}
.chart-title-1x1{width:80%;font-size:var(--yz-fs-title);font-weight:900;color:var(--yz-text);line-height:1.35;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.chart-logo-1x1{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}
.chart-logo-1x1 svg{height:96px;width:auto;}
.chart-body-1x1{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}
.chart-footer-1x1{flex-shrink:0;margin-top:20px;padding-top:14px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}
.chart-source-1x1{font-size:var(--yz-fs-footer);color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}
.chart-part-num{font-size:24px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:20px;}
.chart-legend{display:flex;flex-wrap:wrap;gap:14px 28px;margin-top:18px;font-size:28px;color:#6b6666;}
.chart-legend .legend-item{display:flex;align-items:center;gap:10px;}
.chart-legend .legend-swatch{width:24px;height:24px;border-radius:4px;}
.chart-legend .legend-swatch.line{width:32px;height:8px;border-radius:2px;}
.axis-text{font-size:24px;fill:#6b6666;font-family:'AliPuHui',sans-serif;}
.axis-line{stroke:#9a9595;stroke-width:2;}
.grid-line{stroke:#eee;stroke-width:1.5;}
.data-label{font-size:22px;font-weight:700;font-family:'AliPuHui',sans-serif;}
.data-table-1x1{width:100%;border-collapse:collapse;font-size:32px;margin-top:20px;}
.data-table-1x1 th{background:#fafafa;padding:16px 10px;text-align:center;font-weight:900;color:#312e2e;border-bottom:2px solid #dcdcdc;font-size:26px;}
.data-table-1x1 td{padding:14px 10px;text-align:center;border-bottom:1px solid #f0f0f0;color:#312e2e;font-size:28px;}
.data-table-1x1 td:first-child{text-align:left;font-weight:700;color:#fc8166;}
#yz-selfcheck-banner{position:absolute;top:8px;right:8px;padding:8px 16px;border-radius:6px;font-size:14px;font-weight:700;z-index:99999;display:none;}
#yz-selfcheck-banner.pass{background:#50c885;color:#fff;display:block;}
#yz-selfcheck-banner.fail{background:#e60012;color:#fff;display:block;}
</style>
</head>
<body>
__SPRITE__
<div id="yz-selfcheck-banner"></div>
<div class="chart-container-1x1">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1">__TITLE__</h1>
    <div class="chart-logo-1x1"><svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg></div>
  </div>
  <div class="chart-body-1x1">
__BODY__
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1">__FOOTER__</div>
    <div class="chart-part-num">__PART__</div>
  </div>
</div>
<script>
function yzSelfCheck1x1(){var errors=[];var cc=document.querySelector('.chart-container-1x1');if(cc){var w=cc.offsetWidth,h=cc.offsetHeight;if(Math.abs(w-1080)>5||Math.abs(h-1080)>5)errors.push('画布尺寸：'+w+'x'+h);}var banner=document.getElementById('yz-selfcheck-banner');if(errors.length===0){if(banner){banner.className='pass';banner.textContent='✅ 通过';}return true;}else{if(banner){banner.className='fail';banner.textContent='❌ '+errors.length+'项';}return false;}}
if(document.fonts){document.fonts.ready.then(function(){setTimeout(yzSelfCheck1x1,200);});}
</script>
</body>
</html>"""

def make_html(title, body, footer, part):
    h = TEMPLATE_1x1
    h = h.replace("__SPRITE__", sprite_full)
    h = h.replace("__TITLE__", esc(title))
    h = h.replace("__BODY__", body)
    h = h.replace("__FOOTER__", esc(footer))
    h = h.replace("__PART__", esc(part))
    return h

def build_bar_line_body(d, row_subset=None):
    """1:1 version of bar+line combo. Larger fonts."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if row_subset:
        rows = row_subset
    
    bar_cols = []
    line_cols = []
    for i, h in enumerate(headers[1:], 1):
        is_pct = any('%' in str(r[i]) if i < len(r) else False for r in rows)
        if is_pct: line_cols.append(i)
        else: bar_cols.append(i)
    if not bar_cols: bar_cols = [1]
    
    W, H = 900, 500
    PAD_L, PAD_R, PAD_T, PAD_B = 80, 80, 50, 90
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    
    all_bar_vals = [num(r[i]) for r in rows for i in bar_cols if i < len(r)]
    max_bar = max(all_bar_vals) if all_bar_vals else 100
    max_ceil = math.ceil(max_bar / 50) * 50 or 50
    
    n_cats = len(rows)
    n_bars = len(bar_cols)
    group_width = plot_w / n_cats
    bar_width = min(group_width * 0.6 / n_bars, 60)
    
    bar_colors = ['#fc8166', '#7cc4f5', '#a8d08d', '#f5a623']
    line_colors = ['#e74c3c', '#3498db']
    
    parts = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">']
    for t in range(6):
        tick = max_ceil * t / 5
        y = PAD_T + plot_h - (t/5) * plot_h
        parts.append(f'<line class="grid-line" x1="{PAD_L}" y1="{y:.0f}" x2="{W-PAD_R}" y2="{y:.0f}"/>')
        parts.append(f'<text class="axis-text" x="{PAD_L-10}" y="{y+8:.0f}" text-anchor="end">{tick:g}</text>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+plot_h}"/>')
    
    for ci, r in enumerate(rows):
        cx = PAD_L + ci * group_width + group_width/2
        parts.append(f'<text class="axis-text" x="{cx:.0f}" y="{PAD_T+plot_h+28}" text-anchor="middle">{esc(r[0])}</text>')
        for bi, col_idx in enumerate(bar_cols):
            if col_idx >= len(r): continue
            val = num(r[col_idx])
            bar_h = (val/max_ceil) * plot_h if max_ceil else 0
            bx = cx - (n_bars*bar_width)/2 + bi*bar_width
            by = PAD_T + plot_h - bar_h
            color = bar_colors[bi % len(bar_colors)]
            parts.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{bar_width:.0f}" height="{bar_h:.0f}" fill="{color}" rx="4"/>')
            if val > 0:
                parts.append(f'<text class="data-label" x="{bx+bar_width/2:.0f}" y="{by-6:.0f}" text-anchor="middle" fill="{color}">{val:g}</text>')
    
    if line_cols:
        all_line_vals = [num(r[i]) for r in rows for i in line_cols if i < len(r)]
        if all_line_vals:
            max_line = max(all_line_vals)
            min_line = min(all_line_vals)
            range_line = max(max_line - min_line, 10)
            for li, col_idx in enumerate(line_cols):
                color = line_colors[li % len(line_colors)]
                pts = []
                for ci, r in enumerate(rows):
                    if col_idx >= len(r): continue
                    val = num(r[col_idx])
                    x = PAD_L + ci * group_width + group_width/2
                    y = PAD_T + plot_h - ((val-min_line)/range_line) * plot_h
                    pts.append((x,y,val))
                pts_str = " ".join(f"{x:.0f},{y:.0f}" for x,y,_ in pts)
                parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round"/>')
                for x,y,val in pts:
                    parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="#fff" stroke="{color}" stroke-width="3"/>')
                    parts.append(f'<text class="data-label" x="{x:.0f}" y="{y-14:.0f}" text-anchor="middle" fill="{color}">{val:g}%</text>')
    parts.append('</svg>')
    
    parts.append('<div class="chart-legend">')
    for bi, col_idx in enumerate(bar_cols):
        color = bar_colors[bi % len(bar_colors)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    for li, col_idx in enumerate(line_cols):
        color = line_colors[li % len(line_colors)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch line" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    parts.append('</div>')
    return "\n".join(parts)

def build_multi_line_body(d, row_subset=None):
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if row_subset: rows = row_subset
    line_cols = list(range(1, len(headers)))
    
    W, H = 900, 500
    PAD_L, PAD_R, PAD_T, PAD_B = 80, 50, 50, 90
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    
    all_vals = [num(r[i]) for r in rows for i in line_cols if i < len(r)]
    max_val = max(all_vals) if all_vals else 100
    min_val = min(0, min(all_vals)) if all_vals else 0
    val_range = max(max_val - min_val, 10)
    
    colors = ['#fc8166', '#7cc4f5', '#a8d08d', '#f5a623', '#a569bd']
    
    parts = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">']
    for t in range(6):
        tick = min_val + (max_val-min_val)*t/5
        y = PAD_T + plot_h - (t/5)*plot_h
        parts.append(f'<line class="grid-line" x1="{PAD_L}" y1="{y:.0f}" x2="{W-PAD_R}" y2="{y:.0f}"/>')
        parts.append(f'<text class="axis-text" x="{PAD_L-10}" y="{y+8:.0f}" text-anchor="end">{tick:g}</text>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+plot_h}"/>')
    
    n_cats = len(rows)
    for ci, r in enumerate(rows):
        x = PAD_L + (ci/max(n_cats-1,1)) * plot_w
        parts.append(f'<text class="axis-text" x="{x:.0f}" y="{PAD_T+plot_h+28}" text-anchor="middle">{esc(r[0])}</text>')
    
    for li, col_idx in enumerate(line_cols):
        color = colors[li % len(colors)]
        pts = []
        for ci, r in enumerate(rows):
            if col_idx >= len(r): continue
            val = num(r[col_idx])
            x = PAD_L + (ci/max(n_cats-1,1)) * plot_w
            y = PAD_T + plot_h - ((val-min_val)/val_range) * plot_h
            pts.append((x,y,val))
        pts_str = " ".join(f"{x:.0f},{y:.0f}" for x,y,_ in pts)
        parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')
        for x,y,val in pts:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="#fff" stroke="{color}" stroke-width="3"/>')
            parts.append(f'<text class="data-label" x="{x:.0f}" y="{y-14:.0f}" text-anchor="middle" fill="{color}">{val:g}</text>')
    parts.append('</svg>')
    
    parts.append('<div class="chart-legend">')
    for li, col_idx in enumerate(line_cols):
        color = colors[li % len(colors)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch line" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    parts.append('</div>')
    return "\n".join(parts)

def build_table_body(d, row_subset=None):
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if row_subset: rows = row_subset
    parts = ['<table class="data-table-1x1"><thead><tr>']
    for h in headers:
        parts.append(f'<th>{esc(h)}</th>')
    parts.append('</tr></thead><tbody>')
    for r in rows:
        parts.append('<tr>')
        for c in r:
            parts.append(f'<td>{esc(c)}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table>')
    return "\n".join(parts)

# Split plans
SPLIT_PLANS = {
    2: [(None, "1/1")],           # no split
    3: [(None, "1/1")],           # no split
    4: [(0, "1/2"), (3, "2/2")], # 3-3 split
    6: [(None, "1/1")],           # no split
    7: [(0, "1/3"), (4, "2/3"), (8, "3/3")],  # 4-4-3
    8: [(None, "1/1")],           # no split
    10: [(0, "1/3"), (4, "2/3"), (8, "3/3")], # 4-4-4
    11: [(0, "1/2"), (4, "2/2")], # 4-3
    12: [(0, "1/3"), (3, "2/3"), (6, "3/3")], # 3-3-3
}

IMG_BUILDERS = {
    2: build_bar_line_body,
    3: build_bar_line_body,
    4: build_bar_line_body,  # treat as bar+line (simplified for 1:1)
    6: build_multi_line_body,
    7: build_table_body,
    8: build_multi_line_body,
    10: build_table_body,
    11: build_table_body,
    12: build_table_body,
}

def main():
    total = 0
    for idx, splits in SPLIT_PLANS.items():
        d = load_vlm(idx)
        td = d.get("table_data", {})
        all_rows = td.get("rows", [])
        title = d.get("title_text", f"图{idx}")
        footer = d.get("data_source_text") or d.get("footer_text") or "数据来源：公司公告，娱乐资本论整理"
        builder = IMG_BUILDERS[idx]
        
        for start, part_num in splits:
            if start is None:
                row_subset = None
            else:
                # Determine end based on plan
                plan_sizes = {2:[6], 4:[3,3], 7:[4,4,3], 10:[4,4,4], 11:[4,3], 12:[3,3,3]}[idx]
                part_idx = int(part_num.split('/')[0]) - 1
                size = plan_sizes[part_idx]
                row_subset = all_rows[start:start+size]
            
            body = builder(d, row_subset)
            html_out = make_html(title, body, footer, part_num)
            out_name = f"img{idx}-part{part_num.split('/')[0]}-styled.html"
            pathlib.Path(os.path.join(OUT_DIR, out_name)).write_text(html_out, encoding="utf-8")
            total += 1
            print(f"  wrote {out_name}")
    print(f"\nTotal: {total} 1:1 HTML files")

if __name__ == "__main__":
    main()
