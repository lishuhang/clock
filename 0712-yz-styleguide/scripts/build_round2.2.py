#!/usr/bin/env python3
"""
Round 2.2 — fixes for 6 user feedback items + abstract principles to skill:
  1. img1: legend font < min font → enforce min font 24px (skill rule)
  2. img2: pie chart bigger, less whitespace, legend horizontal 2 rows below,
           phase name NOT in center (move to top). Abstract: main content fills
           canvas, overflow content goes outside main chart area.
  3. img3: axis scale font too small → min font 24px
  4. img4 (one-off, NOT in skill): download 4 film stills, semi-transparent bg;
           metadata top-left aligned, quote centered.
           Fact-check: 我是特种兵之利刃出鞘 = 2012 (not 2017)
  5. img5: split by dimension (3 images, one per dimension, 10 films each)
  6. img6: x-axis font too small, legend lost gap with divider

Skill principles abstracted:
  - Min font: all visible text ≥24px (60% of 40px body)
  - Main content fills chart-body, whitespace <10%
  - Overflow: wrap or expand outside main area, never shrink font
  - Metadata layout: top-left aligned, body content centered
"""
import os, json, re, pathlib, html, math, base64

VLM_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round1/_vlm"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round2.2"
ASSETS_DIR = os.path.join(OUT_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

def load_vlm(name):
    path = os.path.join(VLM_DIR, name + ".json")
    with open(path, encoding="utf-8") as f:
        outer = json.load(f)
    content = outer["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
    return json.loads(content)

def esc(s):
    return html.escape(str(s) if s is not None else "")

def pct_to_opacity(pct_str):
    if not pct_str: return 0.0
    s = str(pct_str).replace("%", "").replace("-", "0").strip()
    try: return max(0.0, min(1.0, float(s) / 100.0))
    except: return 0.0

def phase_name_only(s):
    return re.sub(r'^\d+\s*[\.、\s]\s*', '', s.strip())

def phase_num(s):
    m = re.match(r'^\s*(\d+)', s.strip())
    return m.group(1) if m else ''

def img_to_base64(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    mime = 'jpeg' if ext in ('jpg','jpeg') else ext
    return f"data:image/{mime};base64,{data}"

# Load film stills as base64
FILM_STILLS = {}
for name in ["我是特种兵之利刃出鞘", "战狼2", "流浪地球", "镖人风起大漠"]:
    path = os.path.join(ASSETS_DIR, f"{name}.jpg")
    if os.path.exists(path):
        FILM_STILLS[name] = img_to_base64(path)
        print(f"  loaded still: {name} ({os.path.getsize(path)} bytes)")

# ════════════════════════════════════════════════════════════════
# 1:1 HTML template — 1080×1080, min font 24px
# ════════════════════════════════════════════════════════════════
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
:root{--yz-accent:#fc8166;--yz-text:#312e2e;--yz-text-muted:#9a9595;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui',sans-serif;--yz-fs-body:40px;--yz-fs-title:48px;--yz-fs-footer:27px;--yz-fs-min:24px;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:var(--yz-font);background:#f0f0f0;padding:20px;}
.chart-container-1x1{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;}
.chart-header-1x1{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:24px;gap:24px;}
.chart-title-1x1{width:80%;font-size:var(--yz-fs-title);font-weight:900;color:var(--yz-text);line-height:1.35;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.chart-logo-1x1{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}
.chart-logo-1x1 svg{height:96px;width:auto;}
.chart-body-1x1{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}
.chart-footer-1x1{flex-shrink:0;margin-top:20px;padding-top:14px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}
.chart-source-1x1{font-size:var(--yz-fs-footer);color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}
.chart-part-num{font-size:24px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:20px;}
/* Shared classes — 1080 canvas, min font 24px */
.phase-label{font-size:36px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:16px;}
.phase-label .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;background:#fc8166;color:#fff;border-radius:50%;font-size:32px;font-weight:900;flex-shrink:0;}
.dumbbell-track{position:relative;height:72px;background:#fafafa;border-radius:36px;}
.dumbbell-track::before{content:"";position:absolute;top:50%;left:0;right:0;height:4px;background:#eee;transform:translateY(-50%);}
.dumbbell-dot{position:absolute;top:50%;transform:translate(-50%,-50%);width:36px;height:36px;border-radius:50%;border:6px solid #fff;box-shadow:0 0 0 3px currentColor;z-index:2;}
.dumbbell-tag{position:absolute;font-size:24px;font-weight:700;white-space:nowrap;transform:translateX(-50%);}
.dumbbell-tag.above{top:-56px;}
.dumbbell-tag.below{bottom:-56px;}
.dumbbell-line{position:absolute;top:50%;height:6px;transform:translateY(-50%);z-index:1;}
.axis-scale{display:flex;justify-content:space-between;font-size:28px;color:#9a9595;margin-top:12px;padding:0 4px;}
.chart-legend{display:flex;flex-wrap:wrap;gap:16px 32px;margin-top:16px;font-size:28px;color:#6b6666;}
.chart-legend .legend-item{display:flex;align-items:center;gap:12px;}
.chart-legend .legend-swatch{width:28px;height:28px;border-radius:50%;}
.chart-legend .legend-swatch.bar{width:36px;height:10px;border-radius:3px;}
/* Heatmap table — 1080, min font 24px */
.hm-table{width:100%;border-collapse:separate;border-spacing:6px;font-size:36px;}
.hm-table th{padding:16px 8px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:6px;font-size:28px;}
.hm-table th.row-head{background:transparent;text-align:left;padding-left:14px;color:#fc8166;}
.hm-table td{padding:20px 8px;text-align:center;border-radius:6px;font-weight:700;color:#312e2e;min-width:100px;font-size:32px;}
.hm-table td.row-label{text-align:left;padding-left:14px;font-weight:700;color:#fc8166;background:#fff;font-size:28px;line-height:1.25;}
.hm-legend{display:flex;align-items:center;gap:20px;margin-top:20px;font-size:28px;color:#6b6666;}
.hm-legend .grad{display:inline-block;width:240px;height:16px;background:linear-gradient(to right,rgba(252,129,102,0.05),rgba(252,129,102,1));border-radius:3px;}
/* Pie chart — bigger, legend horizontal below */
.pie-wrap{display:flex;flex-direction:column;align-items:center;gap:24px;height:100%;justify-content:center;}
.pie-phase-label{font-size:36px;font-weight:900;color:#312e2e;text-align:center;display:flex;align-items:center;gap:16px;}
.pie-phase-label .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;background:#fc8166;color:#fff;border-radius:50%;font-size:32px;font-weight:900;}
.pie-svg{width:560px;height:560px;flex-shrink:0;}
.pie-legend-h{display:flex;flex-wrap:wrap;gap:12px 28px;justify-content:center;font-size:28px;color:#312e2e;max-width:900px;}
.pie-legend-h .pie-item{display:flex;align-items:center;gap:10px;}
.pie-legend-h .pie-swatch{width:24px;height:24px;border-radius:4px;flex-shrink:0;}
.pie-legend-h .pie-pct{font-weight:900;margin-left:4px;}
.pie-slice-label{font-family:var(--yz-font);font-size:28px;font-weight:900;fill:#fff;text-anchor:middle;dominant-baseline:middle;}
/* Text card with film still bg — 1080 */
.tc-bg{position:relative;border-radius:10px;overflow:hidden;flex:1;min-height:0;display:flex;flex-direction:column;border:1px solid #f0f0f0;}
.tc-bg-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0.25;z-index:0;}
.tc-bg-overlay{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(255,255,255,0.7) 0%,rgba(255,255,255,0.85) 100%);z-index:1;}
.tc-bg-content{position:relative;z-index:2;padding:48px 56px;display:flex;flex-direction:column;gap:32px;height:100%;}
.tc-meta-block{display:flex;flex-direction:column;gap:8px;align-items:flex-start;}
.tc-meta-phase{font-size:32px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:14px;}
.tc-meta-phase .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;background:#fc8166;color:#fff;border-radius:50%;font-size:28px;font-weight:900;}
.tc-meta-work{font-size:40px;font-weight:900;color:#312e2e;}
.tc-meta-info{font-size:28px;color:#6b6666;display:flex;gap:24px;}
.tc-meta-info b{color:#312e2e;font-weight:900;}
.tc-quote-center{flex:1;display:flex;align-items:center;justify-content:center;}
.tc-quote-text{font-size:48px;line-height:1.65;color:#312e2e;font-weight:500;text-align:center;max-width:900px;}
.tc-quote-text .qmark{color:#fc8166;font-weight:900;font-size:56px;line-height:0;vertical-align:-8px;}
/* Multi-series dumbbell — 1080 (for img5 single dimension) */
.db5-wrap{display:flex;flex-direction:column;gap:20px;height:100%;}
.db5-sub{display:flex;flex-direction:column;gap:10px;flex:1;}
.db5-sub-title{font-size:36px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:14px;padding-bottom:8px;border-bottom:2px solid #f0f0f0;}
.db5-rows{display:flex;flex-direction:column;gap:10px;flex:1;justify-content:space-around;}
.db5-row{display:grid;grid-template-columns:200px 1fr 100px;gap:16px;align-items:center;}
.db5-film-col{display:flex;flex-direction:column;gap:2px;line-height:1.2;}
.db5-year{font-size:28px;font-weight:900;color:#fc8166;}
.db5-film-name{font-size:24px;font-weight:700;color:#312e2e;}
.db5-row .dumbbell-track{height:36px;border-radius:18px;}
.db5-row .dumbbell-dot{width:22px;height:22px;border:4px solid #fff;}
.db5-row .dumbbell-tag{font-size:24px;}
.db5-row .dumbbell-tag.above{top:-32px;}
.db5-row .dumbbell-tag.below{bottom:-32px;}
.db5-diff{font-size:28px;font-weight:900;color:#6b6666;text-align:right;}
.db5-diff.up{color:#fc8166;}
.db5-diff.down{color:#6cb0f9;}
/* Scatter — 1080 */
.sc6-wrap{display:flex;flex-direction:column;gap:32px;}
.sc6-row{display:flex;flex-direction:column;gap:16px;}
.sc6-label{font-size:32px;font-weight:900;color:#312e2e;display:flex;justify-content:space-between;align-items:baseline;}
.sc6-label .diff{font-size:28px;font-weight:900;color:#e60012;}
.sc6-row .dumbbell-track{height:64px;}
.sc6-row .dumbbell-dot{width:34px;height:34px;}
.sc6-row .dumbbell-tag{font-size:24px;}
.sc6-line-dashed{position:absolute;top:50%;height:6px;transform:translateY(-50%);background:repeating-linear-gradient(to right,#fc8166 0,#fc8166 8px,transparent 8px,transparent 16px);z-index:1;}
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
function yzSelfCheck1x1(){var errors=[];var checks=[['.chart-container-1x1','画布'],['.chart-title-1x1','标题'],['.chart-logo-1x1','Logo'],['.chart-body-1x1','主体'],['.chart-source-1x1','脚注']];checks.forEach(function(c){if(!document.querySelector(c[0]))errors.push('缺失：'+c[1]);});var cc=document.querySelector('.chart-container-1x1');if(cc){var w=cc.offsetWidth,h=cc.offsetHeight;if(Math.abs(w-1080)>5||Math.abs(h-1080)>5)errors.push('画布尺寸：'+w+'x'+h);}var banner=document.getElementById('yz-selfcheck-banner');if(errors.length===0){console.log('✅ PASSED');if(banner){banner.className='pass';banner.textContent='✅ 通过';}return true;}else{console.log('❌ FAILED',errors);if(banner){banner.className='fail';banner.textContent='❌ '+errors.length+'项';}return false;}}
if(document.fonts){document.fonts.ready.then(function(){setTimeout(yzSelfCheck1x1,200);});}
</script>
</body>
</html>"""

# Load SVG sprite
with open("/home/z/my-project/scripts/v2.20-svg-sprite.txt", encoding="utf-8") as f:
    sprite = f.read()
with open("/home/z/my-project/scripts/yz-logo-icon-symbol.txt", encoding="utf-8") as f:
    icon = f.read()
sprite_full = sprite.replace("  </defs>", f"  {icon}\n  </defs>")

def make_html(title, body, footer, part_num_str):
    html_out = TEMPLATE_1x1
    html_out = html_out.replace("__SPRITE__", sprite_full)
    html_out = html_out.replace("__TITLE__", esc(title))
    html_out = html_out.replace("__BODY__", body)
    html_out = html_out.replace("__FOOTER__", esc(footer))
    html_out = html_out.replace("__PART__", esc(part_num_str))
    return html_out

# ════════════════════════════════════════════════════════════════
# Image builders
# ════════════════════════════════════════════════════════════════

def build_img1_parts(d):
    """img1: 10×6 heatmap → 4-3-3. Fix: legend font 22→24px (min font)."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    title = "2012-2026的十部作品如何改写吴京的形象"
    footer = "数据来源：豆瓣短评，娱乐资本论整理。颜色越深，占比越高。"

    def build_heatmap_table(row_subset):
        parts = ['<table class="hm-table"><thead><tr>']
        for h in headers:
            cls = 'row-head' if h == '' else ''
            parts.append(f'<th class="{cls}">{esc(h)}</th>')
        parts.append('</tr></thead><tbody>')
        for r in row_subset:
            parts.append('<tr>')
            for i, c in enumerate(r):
                if i == 0:
                    name = str(c)
                    name_wrapped = re.sub(r'^(\d{4})\s*', r'\1<br>', name)
                    parts.append(f'<td class="row-label">{name_wrapped}</td>')
                else:
                    op = pct_to_opacity(c)
                    txt_color = '#fff' if op > 0.55 else '#312e2e'
                    bg = f'background:rgba(252,129,102,{op*0.95+0.03});color:{txt_color};'
                    parts.append(f'<td style="{bg}">{esc(c)}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')
        # Fix: legend font 22px → 24px (min font rule)
        parts.append('<div class="hm-legend"><span>低占比</span><span class="grad"></span><span>高占比</span></div>')
        return "\n".join(parts)

    splits = [(rows[0:4], "1/3"), (rows[4:7], "2/3"), (rows[7:10], "3/3")]
    return [(title, footer, pn, build_heatmap_table(sub)) for sub, pn in splits]


def build_img2_parts(d):
    """img2: 4-stage → 1 stage per image (4 pie charts).
       Fix: pie bigger (480→560), legend horizontal 2 rows below,
       phase name NOT in center (move to top above pie)."""
    title = "观众评价吴京的维度发生了四个阶段的变化"
    footer = "数据来源：豆瓣短评 2,968 条，娱乐资本论整理。"

    rows_data = [
        ("1 动作演员与军旅角色", [("专业能力",86.08),("民族国家",9.16),("道德人格",2.00),("社会文化/性别",2.03),("商业资本",0.37),("身份符号",0.37)]),
        ("2 “战狼”IP成型", [("民族国家",46.63),("专业能力",34.02),("社会文化/性别",10.56),("商业资本",6.74),("道德人格",1.00),("身份符号",1.05)]),
        ("3 国家工业大片扩张", [("专业能力",55.40),("民族国家",37.70),("社会文化/性别",1.73),("商业资本",1.73),("道德人格",1.72),("身份符号",1.72)]),
        ("4 后“战狼”分化", [("专业能力",75.60),("民族国家",16.09),("社会文化/性别",2.08),("商业资本",2.08),("道德人格",2.07),("身份符号",2.08)]),
    ]
    color_map = {'专业能力':'#fc8166','道德人格':'#7dd3f9','民族国家':'#e74c3c','商业资本':'#f39c12','社会文化/性别':'#a569bd','身份符号':'#a8d08d'}

    def build_pie_chart(phase_full, segs):
        pnum = phase_num(phase_full)
        pname = phase_name_only(phase_full)
        # SVG pie — bigger (560×560, r=240)
        cx, cy, r = 280, 280, 240
        total = sum(v for _, v in segs)
        parts = ['<div class="pie-wrap">']
        # Phase label on TOP (not in center)
        parts.append(f'<div class="pie-phase-label"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
        parts.append(f'<svg class="pie-svg" viewBox="0 0 560 560">')
        start_angle = -90
        for dim, val in segs:
            if val < 0.1: continue
            angle = (val / total) * 360
            end_angle = start_angle + angle
            sa = math.radians(start_angle)
            ea = math.radians(end_angle)
            x1 = cx + r * math.cos(sa)
            y1 = cy + r * math.sin(sa)
            x2 = cx + r * math.cos(ea)
            y2 = cy + r * math.sin(ea)
            large_arc = 1 if angle > 180 else 0
            color = color_map.get(dim, '#999')
            path = f'M {cx},{cy} L {x1:.1f},{y1:.1f} A {r},{r} 0 {large_arc} 1 {x2:.1f},{y2:.1f} Z'
            parts.append(f'<path d="{path}" fill="{color}" stroke="#fff" stroke-width="3"/>')
            mid_angle = math.radians(start_angle + angle/2)
            label_r = r * 0.65
            lx = cx + label_r * math.cos(mid_angle)
            ly = cy + label_r * math.sin(mid_angle)
            if val >= 5:
                parts.append(f'<text class="pie-slice-label" x="{lx:.1f}" y="{ly:.1f}">{val:.1f}%</text>')
            start_angle = end_angle
        # No center label (moved to top)
        parts.append('</svg>')
        # Legend horizontal below, 2 rows
        parts.append('<div class="pie-legend-h">')
        for dim, val in segs:
            color = color_map.get(dim, '#999')
            parts.append(f'<div class="pie-item"><span class="pie-swatch" style="background:{color}"></span>{esc(dim)}<span class="pie-pct">{val:.2f}%</span></div>')
        parts.append('</div>')
        parts.append('</div>')
        return "\n".join(parts)

    results = []
    for idx, (phase_full, segs) in enumerate(rows_data, 1):
        body = build_pie_chart(phase_full, segs)
        results.append((title, footer, f"{idx}/4", body))
    return results


def build_img3_parts(d):
    """img3: 4-stage dumbbell → 2-2. Fix: axis scale font 18→24px."""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    title = "“战狼”阶段最像在评价吴京本人"
    footer = "互文关系采用互斥优先级。来源：2,968条豆瓣短评"

    def build_dumbbell(row_subset):
        parts = ['<div style="display:flex;flex-direction:column;gap:100px;padding:8px 0;">']
        for r in row_subset:
            phase_full = r[0]
            pnum = phase_num(phase_full)
            pname = phase_name_only(phase_full)
            v_actor = pct_to_opacity(r[1]) * 100 if len(r) > 1 else 0
            v_work = pct_to_opacity(r[2]) * 100 if len(r) > 2 else 0
            v_actor_c = max(2, min(98, v_actor))
            v_work_c = max(2, min(98, v_work))
            left = min(v_actor_c, v_work_c)
            right = max(v_actor_c, v_work_c)
            parts.append('<div style="display:flex;flex-direction:column;gap:80px;">')
            parts.append(f'<div class="phase-label"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
            parts.append('<div class="dumbbell-track">')
            parts.append(f'<div class="dumbbell-line" style="left:{left}%;width:{right-left}%;background:#dcdcdc;"></div>')
            parts.append(f'<div class="dumbbell-dot" style="left:{v_actor_c}%;background:#fc8166;color:#fc8166;"></div>')
            parts.append(f'<div class="dumbbell-tag above" style="left:{v_actor_c}%;color:#fc8166;">{esc(r[1])}</div>')
            parts.append(f'<div class="dumbbell-dot" style="left:{v_work_c}%;background:#6cb0f9;color:#6cb0f9;"></div>')
            parts.append(f'<div class="dumbbell-tag below" style="left:{v_work_c}%;color:#6cb0f9;">{esc(r[2])}</div>')
            parts.append('</div></div>')
        # Fix: axis scale font now 24px (via .axis-scale class)
        parts.append('<div class="axis-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>')
        parts.append('</div>')
        parts.append('<div class="chart-legend"><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>直接指向演员</div><div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>仅涉及作品层面</div></div>')
        return "\n".join(parts)

    return [(title, footer, pn, build_dumbbell(sub)) for sub, pn in [(rows[0:2], "1/2"), (rows[2:4], "2/2")]]


def build_img4_parts(d):
    """img4: 4 quote cards → 1 card per image (4 images).
       One-off (NOT in skill): film still semi-transparent bg, metadata top-left, quote centered.
       Fact-check: 我是特种兵之利刃出鞘 = 2012 (not 2017)."""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    title = "吴京作品在四个不同阶段的代表性评论"
    footer = "数据来源：豆瓣短评，娱乐资本论整理"

    # Fact-checked data: 我是特种兵之利刃出鞘 is 2012
    fact_check_years = {
        "《我是特种兵之利刃出鞘》": "2012",
        "《战狼2》": "2017",
        "《流浪地球》": "2019",
        "《镖人：风起大漠》": "2026",
    }
    # Map film name to still image key
    film_still_map = {
        "《我是特种兵之利刃出鞘》": "我是特种兵之利刃出鞘",
        "《战狼2》": "战狼2",
        "《流浪地球》": "流浪地球",
        "《镖人：风起大漠》": "镖人风起大漠",
    }

    results = []
    for idx, r in enumerate(rows, 1):
        phase_full = r[0] if len(r) > 0 else ''
        work = r[1] if len(r) > 1 else ''
        year_orig = r[2] if len(r) > 2 else ''
        rating = r[3] if len(r) > 3 else ''
        likes = r[4] if len(r) > 4 else ''
        quote = r[5] if len(r) > 5 else ''
        # Fact-check year
        year = fact_check_years.get(work, year_orig)
        pnum = phase_num(phase_full)
        pname = phase_name_only(phase_full)
        # Get film still base64
        still_key = film_still_map.get(work, '')
        still_b64 = FILM_STILLS.get(still_key, '')

        parts = [f'<div class="tc-bg">']
        if still_b64:
            parts.append(f'<img class="tc-bg-img" src="{still_b64}" alt="{esc(work)}剧照">')
            parts.append('<div class="tc-bg-overlay"></div>')
        parts.append('<div class="tc-bg-content">')
        # Metadata top-left aligned
        parts.append('<div class="tc-meta-block">')
        parts.append(f'<div class="tc-meta-phase"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
        parts.append(f'<div class="tc-meta-work">{esc(work)}</div>')
        parts.append(f'<div class="tc-meta-info"><span>年份 <b>{esc(year)}</b></span><span>评分 <b>{esc(rating)}</b></span><span>互动 <b>{esc(likes)}</b></span></div>')
        parts.append('</div>')
        # Quote centered
        parts.append('<div class="tc-quote-center">')
        parts.append(f'<div class="tc-quote-text"><span class="qmark">\u201c</span>{esc(quote)}<span class="qmark">\u201d</span></div>')
        parts.append('</div>')
        parts.append('</div></div>')
        results.append((title, footer, f"{idx}/4", "\n".join(parts)))
    return results


def build_img5_parts(d):
    """img5: split by dimension (3 images, one per dimension, 10 films each).
       User: '专业能力 和 民族国家 等应该拆分，每个section内10部电影不拆分'"""
    series = d.get("series", [])
    title = "对比上映初期与当下，网友对吴京作品评价的维度在变化"
    footer = "数据来源：豆瓣短评，娱乐资本论整理"

    films = []
    for s in series:
        for pt in s.get('data_points', []):
            fname = pt[0]
            if fname not in films:
                films.append(fname)
    color_map = {'专业能力':'#fc8166','民族国家':'#f5a623','社会文化/性别':'#7fd3f0'}

    results = []
    for idx, s in enumerate(series, 1):
        sname = s.get('name', '')
        color = color_map.get(sname, '#999')
        data = {}
        for pt in s.get('data_points', []):
            fname = pt[0]
            val = pt[1]
            if isinstance(val, list) and len(val) >= 2:
                try: data[fname] = (float(val[0]), float(val[1]))
                except: continue
            elif isinstance(val, (int, float, str)):
                try:
                    v = float(str(val).replace('%','').strip())
                    data[fname] = (v, v)
                except: continue
        parts = ['<div class="db5-wrap">']
        parts.append(f'<div class="db5-sub">')
        parts.append(f'<div class="db5-sub-title"><span class="chart-legend legend-swatch bar" style="background:{color};width:36px;height:10px;border-radius:3px;display:inline-block;"></span>{esc(sname)}</div>')
        parts.append('<div class="db5-rows">')
        for fname in films:
            if fname not in data: continue
            v_init, v_curr = data[fname]
            x_max = 75
            x_init = max(2, min(98, (v_init / x_max) * 100))
            x_curr = max(2, min(98, (v_curr / x_max) * 100))
            left = min(x_init, x_curr)
            right = max(x_init, x_curr)
            diff = v_curr - v_init
            diff_cls = 'up' if diff > 0 else ('down' if diff < 0 else '')
            diff_sign = '+' if diff > 0 else ''
            m = re.match(r'^(\d{4})', fname)
            year = m.group(1) if m else ''
            film_name = re.sub(r'^\d{4}\s*', '', fname)
            parts.append('<div class="db5-row">')
            parts.append(f'<div class="db5-film-col"><div class="db5-year">{esc(year)}</div><div class="db5-film-name">{esc(film_name)}</div></div>')
            parts.append('<div class="dumbbell-track">')
            parts.append(f'<div class="dumbbell-line" style="left:{left}%;width:{right-left}%;background:{color};opacity:.5;"></div>')
            parts.append(f'<div class="dumbbell-dot" style="left:{x_init}%;background:#fff;color:{color};"></div>')
            parts.append(f'<div class="dumbbell-tag above" style="left:{x_init}%;color:{color};">{v_init:.0f}%</div>')
            parts.append(f'<div class="dumbbell-dot" style="left:{x_curr}%;background:{color};color:{color};"></div>')
            parts.append(f'<div class="dumbbell-tag below" style="left:{x_curr}%;color:{color};">{v_curr:.0f}%</div>')
            parts.append('</div>')
            parts.append(f'<div class="db5-diff {diff_cls}">{diff_sign}{diff:.0f}%</div>')
            parts.append('</div>')
        parts.append('<div class="axis-scale"><span>0%</span><span>15%</span><span>30%</span><span>45%</span><span>60%</span><span>75%</span></div>')
        parts.append('</div></div></div>')
        parts.append('<div class="chart-legend"><div class="legend-item"><span class="legend-swatch" style="background:#fff;border:2px solid #fc8166;"></span>上映初期</div><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>近一年</div></div>')

        results.append((title, footer, f"{idx}/3", "\n".join(parts)))
    return results


def build_img6_parts(d):
    """img6: no split (1 image). Fix: x-axis font 18→24px, legend gap with divider."""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    title = "性别批评相关的评论通常打分更低"
    footer = "数据来源：豆瓣"

    parts = ['<div class="sc6-wrap">']
    for r in rows:
        film = r[0]
        v1 = r[1]
        v2 = r[2]
        diff = r[3] if len(r) > 3 else ''
        try:
            x1 = (float(str(v1).replace('星','').strip()) / 5.0) * 100
            x2 = (float(str(v2).replace('星','').strip()) / 5.0) * 100
        except:
            x1, x2 = 0, 0
        x1_c = max(3, min(97, x1))
        x2_c = max(3, min(97, x2))
        left = min(x1_c, x2_c)
        right = max(x1_c, x2_c)
        parts.append('<div class="sc6-row">')
        parts.append(f'<div class="sc6-label"><span>{esc(film)}</span><span class="diff">{esc(diff)}</span></div>')
        parts.append('<div class="dumbbell-track">')
        parts.append(f'<div class="sc6-line-dashed" style="left:{left}%;width:{right-left}%;"></div>')
        parts.append(f'<div class="dumbbell-dot" style="left:{x1_c}%;background:#fc8166;color:#fc8166;"></div>')
        parts.append(f'<div class="dumbbell-tag above" style="left:{x1_c}%;color:#fc8166;">{esc(v1)}星</div>')
        parts.append(f'<div class="dumbbell-dot" style="left:{x2_c}%;background:#6cb0f9;color:#6cb0f9;"></div>')
        parts.append(f'<div class="dumbbell-tag below" style="left:{x2_c}%;color:#6cb0f9;">{esc(v2)}星</div>')
        parts.append('</div></div>')
    # Fix: axis scale font now 24px
    parts.append('<div class="axis-scale"><span>1星</span><span>2星</span><span>3星</span><span>4星</span><span>5星</span></div>')
    parts.append('</div>')
    # Fix: legend margin-top 16px → 32px for gap with divider
    parts.append('<div class="chart-legend" style="margin-top:32px;"><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>性别批评评论平均星级</div><div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>电影评分星级</div></div>')
    return [(title, footer, "1/1", "\n".join(parts))]


def main():
    builders = [
        ("img1", "2012-2026的十部作品如何改写吴京形象", build_img1_parts),
        ("img2", "观众评价吴京的维度发生了四个阶段的变化", build_img2_parts),
        ("img3", "“战狼”阶段最像在评价吴京本人", build_img3_parts),
        ("img4", "吴京作品在四个不同阶段的代表性评论", build_img4_parts),
        ("img5", "对比上映初期与当下，网友对吴京作品评价的维度在变化", build_img5_parts),
        ("img6", "性别批评相关的评论通常打分更低", build_img6_parts),
    ]
    total = 0
    for img_id, vlm_name, builder_fn in builders:
        d = load_vlm(vlm_name)
        parts = builder_fn(d)
        for idx, (title, footer, pn, body) in enumerate(parts, 1):
            html_out = make_html(title, body, footer, pn)
            out_path = os.path.join(OUT_DIR, f"{img_id}-part{idx}-styled.html")
            pathlib.Path(out_path).write_text(html_out, encoding="utf-8")
            total += 1
            print(f"  wrote {img_id}-part{idx}-styled.html ({len(html_out)} bytes)")
    print(f"\nTotal: {total} 1:1 HTML files written to {OUT_DIR}")

if __name__ == "__main__":
    main()
