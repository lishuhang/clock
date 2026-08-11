#!/usr/bin/env python3
"""
Generate round2 — split round1.2's 6 large images into 1:1 images using v2.21b template.

Split plan:
  img1 (10×6 heatmap)       → 4-3-3 → 3 parts
  img2 (4-stage stacked bar) → 2-2  → 2 parts
  img3 (4-stage dumbbell)    → 2-2  → 2 parts
  img4 (4 quote cards 2×2)   → no split → 1 part
  img5 (3-sub dumbbell)      → 1-1-1 → 3 parts
  img6 (5-film scatter)      → 3-2  → 2 parts
  Total: 13 1:1 images
"""
import os, json, re, pathlib, html

VLM_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round1/_vlm"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round2"
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
    try:
        return max(0.0, min(1.0, float(s) / 100.0))
    except: return 0.0

def phase_name_only(s):
    return re.sub(r'^\d+\s*[\.、\s]\s*', '', s.strip())

def phase_num(s):
    m = re.sub(r'^\s*(\d+)', r'\1', s.strip())
    return m if m and m[0].isdigit() else ''

# ════════════════════════════════════════════════════════════════
# 1:1 HTML template (inline, based on v2.21b's template)
# ════════════════════════════════════════════════════════════════
TEMPLATE_1x1 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=900">
<title>__TITLE__</title>
<style>
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}
:root{--yz-accent:#fc8166;--yz-text:#312e2e;--yz-text-muted:#9a9595;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui',sans-serif;--yz-fs-1x1-title:34px;--yz-fs-1x1-footer:18px;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:var(--yz-font);background:#f0f0f0;padding:20px;}
.chart-container-1x1{position:relative;width:900px;height:900px;margin:0 auto;background:#fff;padding:36px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;}
.chart-header-1x1{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:20px;gap:20px;}
.chart-title-1x1{width:80%;font-size:var(--yz-fs-1x1-title);font-weight:900;color:var(--yz-text);line-height:1.35;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.chart-logo-1x1{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}
.chart-logo-1x1 svg{height:80px;width:auto;}
.chart-body-1x1{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}
.chart-footer-1x1{flex-shrink:0;margin-top:16px;padding-top:12px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}
.chart-source-1x1{font-size:var(--yz-fs-1x1-footer);color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}
.chart-part-num{font-size:14px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:16px;}
.phase-label{font-size:28px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:12px;}
.phase-label .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;background:#fc8166;color:#fff;border-radius:50%;font-size:24px;font-weight:900;flex-shrink:0;}
.dumbbell-track{position:relative;height:56px;background:#fafafa;border-radius:28px;}
.dumbbell-track::before{content:"";position:absolute;top:50%;left:0;right:0;height:3px;background:#eee;transform:translateY(-50%);}
.dumbbell-dot{position:absolute;top:50%;transform:translate(-50%,-50%);width:28px;height:28px;border-radius:50%;border:4px solid #fff;box-shadow:0 0 0 2px currentColor;z-index:2;}
.dumbbell-tag{position:absolute;font-size:18px;font-weight:700;white-space:nowrap;transform:translateX(-50%);}
.dumbbell-tag.above{top:-42px;}
.dumbbell-tag.below{bottom:-42px;}
.dumbbell-line{position:absolute;top:50%;height:5px;transform:translateY(-50%);z-index:1;}
.axis-scale{display:flex;justify-content:space-between;font-size:14px;color:#9a9595;margin-top:10px;padding:0 4px;}
.chart-legend{display:flex;flex-wrap:wrap;gap:12px 24px;margin-top:12px;font-size:18px;color:#6b6666;}
.chart-legend .legend-item{display:flex;align-items:center;gap:8px;}
.chart-legend .legend-swatch{width:20px;height:20px;border-radius:50%;}
.chart-legend .legend-swatch.bar{width:28px;height:6px;border-radius:3px;}
.hm-table{width:100%;border-collapse:separate;border-spacing:4px;font-size:22px;}
.hm-table th{padding:12px 6px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:4px;font-size:18px;}
.hm-table th.row-head{background:transparent;text-align:left;padding-left:10px;color:#fc8166;}
.hm-table td{padding:14px 6px;text-align:center;border-radius:4px;font-weight:700;color:#312e2e;min-width:80px;font-size:20px;}
.hm-table td.row-label{text-align:left;padding-left:10px;font-weight:700;color:#fc8166;background:#fff;font-size:18px;}
.hm-legend{display:flex;align-items:center;gap:16px;margin-top:16px;font-size:16px;color:#6b6666;}
.hm-legend .grad{display:inline-block;width:180px;height:12px;background:linear-gradient(to right,rgba(252,129,102,0.05),rgba(252,129,102,1));border-radius:2px;}
.sb-wrap{display:flex;flex-direction:column;gap:24px;}
.sb-row{display:flex;flex-direction:column;gap:8px;}
.sb-bar{display:flex;width:100%;height:60px;border-radius:6px;overflow:hidden;background:#fafafa;}
.sb-seg{display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#fff;}
.sb-data-table{width:100%;border-collapse:collapse;font-size:14px;margin-top:16px;}
.sb-data-table th{background:#fafafa;padding:8px 6px;text-align:center;font-weight:900;color:#312e2e;border-bottom:2px solid #dcdcdc;font-size:13px;}
.sb-data-table td{padding:6px;text-align:center;border-bottom:1px solid #f0f0f0;color:#312e2e;font-size:13px;}
.sb-data-table td:first-child{text-align:left;font-weight:700;color:#fc8166;}
.tc-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;position:relative;z-index:2;}
.tc-card{border:1px solid #f0f0f0;border-left:6px solid #fc8166;border-radius:6px;padding:18px 22px;background:rgba(255,255,255,0.92);display:flex;flex-direction:column;gap:10px;position:relative;}
.tc-card-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;}
.tc-phase{font-size:18px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:8px;}
.tc-phase .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:#fc8166;color:#fff;border-radius:50%;font-size:16px;font-weight:900;}
.tc-work{font-size:22px;font-weight:900;color:#312e2e;}
.tc-meta{font-size:14px;color:#9a9595;margin-left:auto;display:flex;gap:10px;}
.tc-meta b{color:#312e2e;font-weight:900;}
.tc-quote{font-size:18px;line-height:1.55;color:#312e2e;font-weight:500;}
.tc-quote .qmark{color:#fc8166;font-weight:900;font-size:24px;line-height:0;vertical-align:-4px;}
.db5-sub{display:flex;flex-direction:column;gap:6px;}
.db5-sub-title{font-size:22px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:10px;padding-bottom:6px;border-bottom:2px solid #f0f0f0;}
.db5-rows{display:flex;flex-direction:column;gap:8px;}
.db5-row{display:grid;grid-template-columns:180px 1fr 80px;gap:10px;align-items:center;}
.db5-film{font-size:14px;font-weight:700;color:#312e2e;line-height:1.3;}
.db5-row .dumbbell-track{height:24px;border-radius:12px;}
.db5-row .dumbbell-dot{width:14px;height:14px;border:2px solid #fff;}
.db5-row .dumbbell-tag{font-size:12px;}
.db5-row .dumbbell-tag.above{top:-16px;}
.db5-row .dumbbell-tag.below{bottom:-16px;}
.db5-diff{font-size:14px;font-weight:900;color:#6b6666;text-align:right;}
.db5-diff.up{color:#fc8166;}
.db5-diff.down{color:#6cb0f9;}
.sc6-wrap{display:flex;flex-direction:column;gap:24px;}
.sc6-row{display:flex;flex-direction:column;gap:10px;}
.sc6-label{font-size:24px;font-weight:900;color:#312e2e;display:flex;justify-content:space-between;align-items:baseline;}
.sc6-label .diff{font-size:20px;font-weight:900;color:#e60012;}
.sc6-row .dumbbell-track{height:48px;}
.sc6-row .dumbbell-dot{width:26px;height:26px;}
.sc6-row .dumbbell-tag{font-size:18px;}
.sc6-line-dashed{position:absolute;top:50%;height:4px;transform:translateY(-50%);background:repeating-linear-gradient(to right,#fc8166 0,#fc8166 5px,transparent 5px,transparent 10px);z-index:1;}
#yz-selfcheck-banner{position:absolute;top:8px;right:8px;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:700;z-index:99999;display:none;}
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
function yzSelfCheck1x1(){var errors=[];var checks=[['.chart-container-1x1','画布'],['.chart-title-1x1','标题'],['.chart-logo-1x1','Logo'],['.chart-body-1x1','主体'],['.chart-source-1x1','脚注']];checks.forEach(function(c){if(!document.querySelector(c[0]))errors.push('缺失：'+c[1]);});var cc=document.querySelector('.chart-container-1x1');if(cc){var w=cc.offsetWidth,h=cc.offsetHeight;if(Math.abs(w-900)>5||Math.abs(h-900)>5)errors.push('画布尺寸：'+w+'x'+h);}var banner=document.getElementById('yz-selfcheck-banner');if(errors.length===0){console.log('✅ PASSED');if(banner){banner.className='pass';banner.textContent='✅ 通过';}return true;}else{console.log('❌ FAILED',errors);if(banner){banner.className='fail';banner.textContent='❌ '+errors.length+'项';}return false;}}
if(document.fonts){document.fonts.ready.then(function(){setTimeout(yzSelfCheck1x1,200);});}
</script>
</body>
</html>"""

# Load SVG sprite (with icon)
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
# Image builders — each returns list of (part_num, body_html) tuples
# ════════════════════════════════════════════════════════════════

def build_img1_parts(d):
    """img1: 10×6 heatmap → 4-3-3 split → 3 parts"""
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
                    parts.append(f'<td class="row-label">{esc(c)}</td>')
                else:
                    op = pct_to_opacity(c)
                    txt_color = '#fff' if op > 0.55 else '#312e2e'
                    bg = f'background:rgba(252,129,102,{op*0.95+0.03});color:{txt_color};'
                    parts.append(f'<td style="{bg}">{esc(c)}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')
        parts.append('<div class="hm-legend"><span>低占比</span><span class="grad"></span><span>高占比</span></div>')
        return "\n".join(parts)
    
    # 4-3-3 split
    splits = [(rows[0:4], "1/3"), (rows[4:7], "2/3"), (rows[7:10], "3/3")]
    return [(title, footer, pn, build_heatmap_table(sub)) for sub, pn in splits]


def build_img2_parts(d):
    """img2: 4-stage stacked bar → 2-2 split → 2 parts"""
    title = "观众评价吴京的维度发生了四个阶段的变化"
    footer = "数据来源：豆瓣短评 2,968 条，娱乐资本论整理。"
    
    rows_data = [
        ("1 动作演员与军旅角色", [("专业能力",86.08),("民族国家",9.16),("道德人格",2.00),("社会文化/性别",2.03),("商业资本",0.37),("身份符号",0.37)]),
        ("2 “战狼”IP成型", [("民族国家",46.63),("专业能力",34.02),("社会文化/性别",10.56),("商业资本",6.74),("道德人格",1.00),("身份符号",1.05)]),
        ("3 国家工业大片扩张", [("专业能力",55.40),("民族国家",37.70),("社会文化/性别",1.73),("商业资本",1.73),("道德人格",1.72),("身份符号",1.72)]),
        ("4 后“战狼”分化", [("专业能力",75.60),("民族国家",16.09),("社会文化/性别",2.08),("商业资本",2.08),("道德人格",2.07),("身份符号",2.08)]),
    ]
    color_map = {'专业能力':'#fc8166','道德人格':'#7dd3f9','民族国家':'#e74c3c','商业资本':'#f39c12','社会文化/性别':'#a569bd','身份符号':'#a8d08d'}
    
    def build_stacked_bar(row_subset):
        parts = ['<div class="sb-wrap">']
        for phase_full, segs in row_subset:
            pnum = phase_num(phase_full)
            pname = phase_name_only(phase_full)
            parts.append('<div class="sb-row">')
            parts.append(f'<div class="phase-label"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
            parts.append('<div class="sb-bar">')
            for dim, val in segs:
                color = color_map.get(dim, '#999')
                if val < 0.3: continue
                if val >= 5:
                    label = f'{val:.2f}%'
                elif val >= 1.5:
                    label = f'{val:.1f}%'
                else:
                    label = ''
                parts.append(f'<div class="sb-seg" style="background:{color};flex:{val} 0 0;" title="{esc(dim)}: {val:.2f}%">{esc(label)}</div>')
            parts.append('</div></div>')
        parts.append('</div>')
        # legend
        parts.append('<div class="chart-legend">')
        for dim in ['专业能力','道德人格','民族国家','商业资本','社会文化/性别','身份符号']:
            color = color_map.get(dim, '#999')
            parts.append(f'<div class="legend-item"><span class="legend-swatch bar" style="background:{color}"></span>{esc(dim)}</div>')
        parts.append('</div>')
        return "\n".join(parts)
    
    # 2-2 split
    return [(title, footer, pn, build_stacked_bar(sub)) for sub, pn in [(rows_data[0:2], "1/2"), (rows_data[2:4], "2/2")]]


def build_img3_parts(d):
    """img3: 4-stage dumbbell → 2-2 split → 2 parts"""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    title = "“战狼”阶段最像在评价吴京本人"
    footer = "互文关系采用互斥优先级。来源：2,968条豆瓣短评"
    
    def build_dumbbell(row_subset):
        parts = ['<div style="display:flex;flex-direction:column;gap:80px;padding:8px 0;">']
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
            parts.append('<div style="display:flex;flex-direction:column;gap:60px;">')
            parts.append(f'<div class="phase-label"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
            parts.append('<div class="dumbbell-track">')
            parts.append(f'<div class="dumbbell-line" style="left:{left}%;width:{right-left}%;background:#dcdcdc;"></div>')
            parts.append(f'<div class="dumbbell-dot" style="left:{v_actor_c}%;background:#fc8166;color:#fc8166;"></div>')
            parts.append(f'<div class="dumbbell-tag above" style="left:{v_actor_c}%;color:#fc8166;">{esc(r[1])}</div>')
            parts.append(f'<div class="dumbbell-dot" style="left:{v_work_c}%;background:#6cb0f9;color:#6cb0f9;"></div>')
            parts.append(f'<div class="dumbbell-tag below" style="left:{v_work_c}%;color:#6cb0f9;">{esc(r[2])}</div>')
            parts.append('</div></div>')
        parts.append('<div class="axis-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>')
        parts.append('</div>')
        parts.append('<div class="chart-legend">')
        parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>直接指向演员</div>')
        parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>仅涉及作品层面</div>')
        parts.append('</div>')
        return "\n".join(parts)
    
    # 2-2 split
    return [(title, footer, pn, build_dumbbell(sub)) for sub, pn in [(rows[0:2], "1/2"), (rows[2:4], "2/2")]]


def build_img4_parts(d):
    """img4: 4 quote cards 2×2 → no split → 1 part"""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    title = "吴京作品在四个不同阶段的代表性评论"
    footer = "数据来源：豆瓣短评，娱乐资本论整理"
    
    parts = ['<div class="tc-grid">']
    for r in rows:
        phase_full = r[0] if len(r) > 0 else ''
        work = r[1] if len(r) > 1 else ''
        year = r[2] if len(r) > 2 else ''
        rating = r[3] if len(r) > 3 else ''
        likes = r[4] if len(r) > 4 else ''
        quote = r[5] if len(r) > 5 else ''
        pnum = phase_num(phase_full)
        pname = phase_name_only(phase_full)
        parts.append('<div class="tc-card">')
        parts.append('<div class="tc-card-head">')
        parts.append(f'<span class="tc-phase"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</span>')
        parts.append(f'<span class="tc-work">{esc(work)}</span>')
        parts.append(f'<span class="tc-meta"><span>年份 <b>{esc(year)}</b></span><span>评分 <b>{esc(rating)}</b></span><span>互动 <b>{esc(likes)}</b></span></span>')
        parts.append('</div>')
        parts.append(f'<div class="tc-quote"><span class="qmark">\u201c</span>{esc(quote)}<span class="qmark">\u201d</span></div>')
        parts.append('</div>')
    parts.append('</div>')
    return [(title, footer, "1/1", "\n".join(parts))]


def build_img5_parts(d):
    """img5: 3-sub dumbbell → 1-1-1 split → 3 parts"""
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
    for idx, s in enumerate(series):
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
        
        parts = [f'<div class="db5-sub"><div class="db5-sub-title"><span class="chart-legend legend-swatch bar" style="background:{color};width:28px;height:6px;border-radius:3px;display:inline-block;"></span>{esc(sname)}</div><div class="db5-rows">']
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
            parts.append('<div class="db5-row">')
            parts.append(f'<div class="db5-film">{esc(fname)}</div>')
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
        parts.append('</div></div>')
        parts.append('<div class="chart-legend"><div class="legend-item"><span class="legend-swatch" style="background:#fff;border:2px solid #fc8166;"></span>上映初期</div><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>近一年</div></div>')
        
        pn = f"{idx+1}/3"
        results.append((title, footer, pn, "\n".join(parts)))
    return results


def build_img6_parts(d):
    """img6: 5-film scatter → 3-2 split → 2 parts"""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    title = "性别批评相关的评论通常打分更低"
    footer = "数据来源：豆瓣"
    
    def build_scatter(row_subset):
        parts = ['<div class="sc6-wrap">']
        for r in row_subset:
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
        parts.append('<div class="axis-scale"><span>1星</span><span>2星</span><span>3星</span><span>4星</span><span>5星</span></div>')
        parts.append('</div>')
        parts.append('<div class="chart-legend"><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>性别批评评论平均星级</div><div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>电影评分星级</div></div>')
        return "\n".join(parts)
    
    # 3-2 split
    return [(title, footer, pn, build_scatter(sub)) for sub, pn in [(rows[0:3], "1/2"), (rows[3:5], "2/2")]]


BUILDERS = {
    "img1": ("2012-2026的十部作品如何改写吴京形象", build_img1_parts),
    "img2": ("观众评价吴京的维度发生了四个阶段的变化", build_img2_parts),
    "img3": ("“战狼”阶段最像在评价吴京本人", build_img3_parts),
    "img4": ("吴京作品在四个不同阶段的代表性评论", build_img4_parts),
    "img5": ("对比上映初期与当下，网友对吴京作品评价的维度在变化", build_img5_parts),
    "img6": ("性别批评相关的评论通常打分更低", build_img6_parts),
}

def main():
    total = 0
    for img_id, vlm_name, builder_fn in [
        ("img1", "2012-2026的十部作品如何改写吴京形象", build_img1_parts),
        ("img2", "观众评价吴京的维度发生了四个阶段的变化", build_img2_parts),
        ("img3", "“战狼”阶段最像在评价吴京本人", build_img3_parts),
        ("img4", "吴京作品在四个不同阶段的代表性评论", build_img4_parts),
        ("img5", "对比上映初期与当下，网友对吴京作品评价的维度在变化", build_img5_parts),
        ("img6", "性别批评相关的评论通常打分更低", build_img6_parts),
    ]:
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
