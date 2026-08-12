#!/usr/bin/env python3
"""
Generate round1 for 0812-test using v2.22a principles.
Chart types in this set:
  - img2: 双轴图（分组柱状图 + 折线图）— bar+line combo
  - img3: 双轴图（柱状图+折线图）— bar+line combo
  - img4: 堆叠柱状图 + 多折线 — stacked bar + lines
  - img6: 多系列折线图 — multi-line
  - img7: 数据表格 — data table
  - img8: 多序列折线图 — multi-line
  - img10/11/12: 数据表格 — data table

Uses v2.20 template with round1.2 style overrides (font ×2, auto-height, etc.)
"""
import os, json, re, pathlib, html, math

VLM_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/_vlm"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/round1"
TEMPLATE = "/home/z/my-project/scripts/v2.20-styled-template.html"
os.makedirs(OUT_DIR, exist_ok=True)

ORDER = [
    (2, "img2"), (3, "img3"), (4, "img4"), (6, "img6"),
    (7, "img7"), (8, "img8"), (10, "img10"), (11, "img11"), (12, "img12")
]

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
    """Parse a numeric value from string like '396', '~5.2', '7.47%', '-'."""
    if not s or s == '-': return 0
    s = str(s).replace('~','').replace('%','').replace(',','').strip()
    try: return float(s)
    except: return 0

GLOBAL_OVERRIDE = """
<style data-purpose="round1-overrides">
.chart-container{ min-height:auto !important; height:auto !important; padding:56px 48px !important; }
.chart-body{ flex:0 1 auto !important; min-height:auto !important; z-index:auto !important; }
.yz-watermark svg{ width:420px !important; opacity:0.10 !important; }
.yz-watermark{ z-index:9999 !important; }
.chart-title{ font-size:48px !important; line-height:1.25 !important; margin-bottom:32px !important; }
.chart-source{ font-size:24px !important; line-height:1.5 !important; }
.yz-logo-svg{ height:62px !important; }
.chart-footer{ margin-top:32px !important; padding-top:20px !important; }
</style>
"""

SHARED_CSS = """
<style>
.chart-legend{display:flex;flex-wrap:wrap;gap:14px 28px;margin-top:18px;font-size:20px;color:#6b6666;}
.chart-legend .legend-item{display:flex;align-items:center;gap:8px;}
.chart-legend .legend-swatch{width:20px;height:20px;border-radius:4px;}
.chart-legend .legend-swatch.line{width:28px;height:5px;border-radius:2px;}
.chart-legend .legend-swatch.dot{border-radius:50%;}
.axis-text{font-size:16px;fill:#6b6666;font-family:'AliPuHui',sans-serif;}
.axis-line{stroke:#9a9595;stroke-width:1.5;}
.grid-line{stroke:#eee;stroke-width:1;}
.data-label{font-size:14px;font-weight:700;font-family:'AliPuHui',sans-serif;}
.dual-table{width:100%;border-collapse:collapse;font-size:20px;margin-top:16px;}
.dual-table th{background:#fafafa;padding:12px 8px;text-align:center;font-weight:900;color:#312e2e;border-bottom:2px solid #dcdcdc;font-size:16px;}
.dual-table td{padding:10px 8px;text-align:center;border-bottom:1px solid #f0f0f0;color:#312e2e;font-size:18px;}
.dual-table td:first-child{text-align:left;font-weight:700;color:#fc8166;}
.dual-table tr:hover td{background:#fff8f5;}
.data-table{width:100%;border-collapse:collapse;font-size:22px;margin-top:16px;}
.data-table th{background:#fafafa;padding:14px 10px;text-align:center;font-weight:900;color:#312e2e;border-bottom:2px solid #dcdcdc;font-size:18px;}
.data-table td{padding:12px 10px;text-align:center;border-bottom:1px solid #f0f0f0;color:#312e2e;font-size:20px;}
.data-table td:first-child{text-align:left;font-weight:700;color:#fc8166;}
</style>
"""

def build_bar_line_combo(d):
    """Dual-axis: grouped bars + line chart. For img2, img3."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if not rows:
        return "<p>(无数据)</p>"
    
    # Determine columns: first col = category, middle cols = bar values, last col(s) = line (growth rate)
    # For img2: 6 cols → col0=业务, col1-4=bar(FY2022-2025), col5=FY2026九个月, col6=增速(line)
    # For img3: 5 cols → col0=财年, col1=Netflix收入(bar), col2=迪士尼收入(bar), col3-4=增速(line)
    
    # Generic: col0=category, numeric cols = bars, percentage cols = lines
    bar_cols = []
    line_cols = []
    for i, h in enumerate(headers[1:], 1):
        # Check if any row has % in this column
        is_pct = any('%' in str(r[i]) if i < len(r) else False for r in rows)
        if is_pct:
            line_cols.append(i)
        else:
            bar_cols.append(i)
    
    if not bar_cols:
        bar_cols = [1]
    
    # Build SVG
    W = 1000
    H = 480
    PAD_L, PAD_R, PAD_T, PAD_B = 70, 70, 40, 80
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    
    # Bar values
    all_bar_vals = []
    for r in rows:
        for i in bar_cols:
            if i < len(r):
                all_bar_vals.append(num(r[i]))
    max_bar = max(all_bar_vals) if all_bar_vals else 100
    max_bar_ceil = math.ceil(max_bar / 50) * 50  # round to nearest 50
    
    n_categories = len(rows)
    n_bars = len(bar_cols)
    group_width = plot_w / n_categories
    bar_width = min(group_width * 0.6 / n_bars, 50)
    
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append(f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">')
    
    # Grid lines + Y axis labels (left = bar values)
    for tick in range(0, max_bar_ceil+1, max_bar_ceil//5 if max_bar_ceil > 0 else 1):
        y = PAD_T + plot_h - (tick / max_bar_ceil) * plot_h if max_bar_ceil else PAD_T + plot_h
        parts.append(f'<line class="grid-line" x1="{PAD_L}" y1="{y:.0f}" x2="{W-PAD_R}" y2="{y:.0f}"/>')
        parts.append(f'<text class="axis-text" x="{PAD_L-8}" y="{y+5:.0f}" text-anchor="end">{tick}</text>')
    
    # X axis
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    # Y axis
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+plot_h}"/>')
    
    # Colors for bars
    bar_colors = ['#fc8166', '#7cc4f5', '#a8d08d', '#f5a623', '#a569bd']
    
    # Bars
    for ci, r in enumerate(rows):
        group_x = PAD_L + ci * group_width + group_width / 2
        # X label
        parts.append(f'<text class="axis-text" x="{group_x:.0f}" y="{PAD_T+plot_h+22}" text-anchor="middle">{esc(r[0])}</text>')
        for bi, col_idx in enumerate(bar_cols):
            if col_idx >= len(r): continue
            val = num(r[col_idx])
            bar_h = (val / max_bar_ceil) * plot_h if max_bar_ceil else 0
            bx = group_x - (n_bars * bar_width) / 2 + bi * bar_width
            by = PAD_T + plot_h - bar_h
            color = bar_colors[bi % len(bar_colors)]
            parts.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{bar_width:.0f}" height="{bar_h:.0f}" fill="{color}" rx="3"/>')
            # Value label on top
            if val > 0:
                parts.append(f'<text class="data-label" x="{bx+bar_width/2:.0f}" y="{by-4:.0f}" text-anchor="middle" fill="{color}">{val:g}</text>')
    
    # Lines (growth rate %)
    if line_cols:
        line_colors = ['#e74c3c', '#3498db']
        # Right Y axis for percentages
        all_line_vals = []
        for r in rows:
            for i in line_cols:
                if i < len(r):
                    all_line_vals.append(num(r[i]))
        if all_line_vals:
            max_line = max(all_line_vals) if all_line_vals else 20
            min_line = min(all_line_vals) if all_line_vals else 0
            range_line = max(max_line - min_line, 10)
            # Draw line
            for li, col_idx in enumerate(line_cols):
                color = line_colors[li % len(line_colors)]
                pts = []
                for ci, r in enumerate(rows):
                    if col_idx >= len(r): continue
                    val = num(r[col_idx])
                    x = PAD_L + ci * group_width + group_width / 2
                    y = PAD_T + plot_h - ((val - min_line) / range_line) * plot_h
                    pts.append((x, y, val))
                # Polyline
                pts_str = " ".join(f"{x:.0f},{y:.0f}" for x,y,_ in pts)
                parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round"/>')
                # Dots + labels
                for x, y, val in pts:
                    parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="#fff" stroke="{color}" stroke-width="2.5"/>')
                    parts.append(f'<text class="data-label" x="{x:.0f}" y="{y-10:.0f}" text-anchor="middle" fill="{color}">{val:g}%</text>')
    
    parts.append('</svg>')
    
    # Legend
    parts.append('<div class="chart-legend">')
    for bi, col_idx in enumerate(bar_cols):
        color = bar_colors[bi % len(bar_colors)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    for li, col_idx in enumerate(line_cols):
        color = line_colors[li % len(line_colors)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch line" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    parts.append('</div>')
    
    # Data table below
    parts.append('<table class="dual-table">')
    parts.append('<thead><tr>')
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


def build_multi_line(d):
    """Multi-series line chart. For img6, img8."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if not rows:
        return "<p>(无数据)</p>"
    
    # col0 = year/category, col1+ = line series
    line_cols = list(range(1, len(headers)))
    
    W = 1000
    H = 480
    PAD_L, PAD_R, PAD_T, PAD_B = 70, 40, 40, 80
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    
    all_vals = []
    for r in rows:
        for i in line_cols:
            if i < len(r):
                all_vals.append(num(r[i]))
    max_val = max(all_vals) if all_vals else 100
    min_val = min(0, min(all_vals)) if all_vals else 0
    val_range = max(max_val - min_val, 10)
    max_ceil = math.ceil(max_val / 10) * 10
    
    colors = ['#fc8166', '#7cc4f5', '#a8d08d', '#f5a623', '#a569bd', '#e74c3c']
    
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append(f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">')
    
    # Grid + Y axis
    n_ticks = 5
    for t in range(n_ticks+1):
        tick = min_val + (max_val - min_val) * t / n_ticks
        y = PAD_T + plot_h - (t / n_ticks) * plot_h
        parts.append(f'<line class="grid-line" x1="{PAD_L}" y1="{y:.0f}" x2="{W-PAD_R}" y2="{y:.0f}"/>')
        parts.append(f'<text class="axis-text" x="{PAD_L-8}" y="{y+5:.0f}" text-anchor="end">{tick:g}</text>')
    
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+plot_h}"/>')
    
    # X labels
    n_cats = len(rows)
    for ci, r in enumerate(rows):
        x = PAD_L + (ci / max(n_cats-1, 1)) * plot_w
        parts.append(f'<text class="axis-text" x="{x:.0f}" y="{PAD_T+plot_h+22}" text-anchor="middle">{esc(r[0])}</text>')
    
    # Lines
    for li, col_idx in enumerate(line_cols):
        color = colors[li % len(colors)]
        pts = []
        for ci, r in enumerate(rows):
            if col_idx >= len(r): continue
            val = num(r[col_idx])
            x = PAD_L + (ci / max(n_cats-1, 1)) * plot_w
            y = PAD_T + plot_h - ((val - min_val) / val_range) * plot_h
            pts.append((x, y, val))
        pts_str = " ".join(f"{x:.0f},{y:.0f}" for x,y,_ in pts)
        parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
        for x, y, val in pts:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="#fff" stroke="{color}" stroke-width="3"/>')
            parts.append(f'<text class="data-label" x="{x:.0f}" y="{y-12:.0f}" text-anchor="middle" fill="{color}">{val:g}</text>')
    
    parts.append('</svg>')
    
    # Legend
    parts.append('<div class="chart-legend">')
    for li, col_idx in enumerate(line_cols):
        color = colors[li % len(colors)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch line" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    parts.append('</div>')
    
    # Data table
    parts.append('<table class="dual-table">')
    parts.append('<thead><tr>')
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


def build_stacked_bar_lines(d):
    """Stacked bar + multi-line. For img4."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if not rows:
        return "<p>(无数据)</p>"
    
    # For img4: col0=财年, col1-2=订阅数(bar stacked), col3-5=ARPU(lines)
    # Detect: cols with "订阅" = bar, cols with "ARPU" = line
    bar_cols = []
    line_cols = []
    for i, h in enumerate(headers[1:], 1):
        if '订阅' in h or '数' in h:
            bar_cols.append(i)
        elif 'ARPU' in h or 'arpu' in h:
            line_cols.append(i)
    if not bar_cols: bar_cols = [1, 2]
    if not line_cols: line_cols = [3, 4, 5] if len(headers) > 5 else []
    
    W = 1000
    H = 480
    PAD_L, PAD_R, PAD_T, PAD_B = 70, 70, 40, 80
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    
    # Bar totals
    bar_totals = []
    for r in rows:
        total = sum(num(r[i]) if i < len(r) else 0 for i in bar_cols)
        bar_totals.append(total)
    max_bar = max(bar_totals) if bar_totals else 100
    max_ceil = math.ceil(max_bar / 20) * 20
    
    # Line values
    line_vals = []
    for r in rows:
        for i in line_cols:
            if i < len(r):
                line_vals.append(num(r[i]))
    max_line = max(line_vals) if line_vals else 10
    min_line = min(line_vals) if line_vals else 0
    line_range = max(max_line - min_line, 1)
    
    colors_bar = ['#fc8166', '#7cc4f5']
    colors_line = ['#e74c3c', '#3498db', '#a8d08d']
    
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append(f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;">')
    
    # Grid
    for t in range(6):
        tick = max_ceil * t / 5
        y = PAD_T + plot_h - (t / 5) * plot_h
        parts.append(f'<line class="grid-line" x1="{PAD_L}" y1="{y:.0f}" x2="{W-PAD_R}" y2="{y:.0f}"/>')
        parts.append(f'<text class="axis-text" x="{PAD_L-8}" y="{y+5:.0f}" text-anchor="end">{tick:g}</text>')
    
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T+plot_h}" x2="{W-PAD_R}" y2="{PAD_T+plot_h}"/>')
    parts.append(f'<line class="axis-line" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T+plot_h}"/>')
    
    n_cats = len(rows)
    group_width = plot_w / n_cats
    bar_width = min(group_width * 0.5, 60)
    
    # Stacked bars
    for ci, r in enumerate(rows):
        cx = PAD_L + ci * group_width + group_width / 2
        parts.append(f'<text class="axis-text" x="{cx:.0f}" y="{PAD_T+plot_h+22}" text-anchor="middle">{esc(r[0])}</text>')
        cum_h = 0
        for bi, col_idx in enumerate(bar_cols):
            if col_idx >= len(r): continue
            val = num(r[col_idx])
            bar_h = (val / max_ceil) * plot_h if max_ceil else 0
            bx = cx - bar_width / 2
            by = PAD_T + plot_h - cum_h - bar_h
            color = colors_bar[bi % len(colors_bar)]
            parts.append(f'<rect x="{bx:.0f}" y="{by:.0f}" width="{bar_width:.0f}" height="{bar_h:.0f}" fill="{color}" rx="2"/>')
            if val > 0:
                parts.append(f'<text class="data-label" x="{cx:.0f}" y="{by+bar_h/2+5:.0f}" text-anchor="middle" fill="#fff">{val:g}</text>')
            cum_h += bar_h
        # Total label
        total = bar_totals[ci]
        parts.append(f'<text class="data-label" x="{cx:.0f}" y="{PAD_T+plot_h-cum_h-6:.0f}" text-anchor="middle" fill="#312e2e" font-size="16">{total:g}</text>')
    
    # Lines
    for li, col_idx in enumerate(line_cols):
        color = colors_line[li % len(colors_line)]
        pts = []
        for ci, r in enumerate(rows):
            if col_idx >= len(r): continue
            val = num(r[col_idx])
            x = PAD_L + ci * group_width + group_width / 2
            y = PAD_T + plot_h - ((val - min_line) / line_range) * plot_h
            pts.append((x, y, val))
        pts_str = " ".join(f"{x:.0f},{y:.0f}" for x,y,_ in pts)
        parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="6,3"/>')
        for x, y, val in pts:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{color}"/>')
    
    parts.append('</svg>')
    
    # Legend
    parts.append('<div class="chart-legend">')
    for bi, col_idx in enumerate(bar_cols):
        color = colors_bar[bi % len(colors_bar)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    for li, col_idx in enumerate(line_cols):
        color = colors_line[li % len(colors_line)]
        parts.append(f'<div class="legend-item"><span class="legend-swatch line" style="background:{color}"></span>{esc(headers[col_idx])}</div>')
    parts.append('</div>')
    
    # Table
    parts.append('<table class="dual-table">')
    parts.append('<thead><tr>')
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


def build_data_table(d):
    """Pure data table. For img7, img10, img11, img12."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    if not headers:
        return "<p>(无数据)</p>"
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append('<table class="data-table">')
    parts.append('<thead><tr>')
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


BUILDERS = {
    "bar_line": build_bar_line_combo,
    "multi_line": build_multi_line,
    "stacked_bar_lines": build_stacked_bar_lines,
    "table": build_data_table,
}

# Map each image to builder
IMG_MAP = {
    2: "bar_line",
    3: "bar_line",
    4: "stacked_bar_lines",
    6: "multi_line",
    7: "table",
    8: "multi_line",
    10: "table",
    11: "table",
    12: "table",
}

def build_plain(title, body, footer):
    parts = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
             f'<title>{esc(title)}</title>',
             '<style>body{font-family:-apple-system,sans-serif;background:#f0f0f0;padding:40px;margin:0;}',
             '.c{width:900px;background:#fff;margin:0 auto;padding:48px;box-sizing:border-box;}',
             'h1{font-size:48px;font-weight:900;margin:0 0 32px 0;color:#000;}',
             '.src{margin-top:32px;font-size:24px;color:#666;border-top:1px solid #eee;padding-top:16px;}',
             '</style></head><body><div class="c">',
             f'<h1>{esc(title)}</h1>', body, f'<div class="src">{esc(footer)}</div>',
             '</div></body></html>']
    return "\n".join(parts)

def main():
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    for idx, img_id in ORDER:
        d = load_vlm(idx)
        builder = BUILDERS[IMG_MAP[idx]]
        body = builder(d)
        title = d.get("title_text", f"图{idx}")
        title = re.sub(r'^图\s*\d+\s*[：:]\s*', '', title)
        footer = d.get("data_source_text") or d.get("footer_text") or "数据来源：公司公告，娱乐资本论整理"
        
        html_out = tpl.replace("【TITLE_HERE】", esc(title))
        html_out = html_out.replace("【CHART_BODY_HERE】", body)
        html_out = html_out.replace("【SOURCE_FOOTER_HERE：数据来源 + 测试概述（基于x个平台x段录屏的x个片段，时间段xxx）】", esc(footer))
        html_out = html_out.replace("【SOURCE_FOOTER_HERE】", esc(footer))
        
        out_path = os.path.join(OUT_DIR, f"{img_id}-styled.html")
        pathlib.Path(out_path).write_text(html_out, encoding="utf-8")
        plain = build_plain(title, body, footer)
        pathlib.Path(os.path.join(OUT_DIR, f"{img_id}.html")).write_text(plain, encoding="utf-8")
        print(f"  wrote {img_id}-styled.html ({len(html_out)} bytes)")

if __name__ == "__main__":
    main()
