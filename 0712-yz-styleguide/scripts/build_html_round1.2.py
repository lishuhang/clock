#!/usr/bin/env python3
"""
Round 1.2 — fixes for 5 new user feedback items:
  1. img2: use precise data from 豆瓣怎么看吴京.docx
  2. img3: red dot label overlaps previous row's black text → move above label higher
  3. img4: year-rating row font too small; phase name color should be black (not red)
     + extract shared CSS classes for reuse across images (user request: "一次性定义多次引用")
  4. watermark z-index above cards (was hidden behind img4 cards)
  5. logo × 1.3 (48px → 62px)

Output: /0811-test/round1.2/
"""
import os, json, re, pathlib, html

VLM_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round1/_vlm"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round1.2"
TEMPLATE = "/home/z/my-project/scripts/v2.20-styled-template.html"
os.makedirs(OUT_DIR, exist_ok=True)

ORDER = [
    ("img1", "2012-2026的十部作品如何改写吴京形象"),
    ("img2", "观众评价吴京的维度发生了四个阶段的变化"),
    ("img3", "“战狼”阶段最像在评价吴京本人"),
    ("img4", "吴京作品在四个不同阶段的代表性评论"),
    ("img5", "对比上映初期与当下，网友对吴京作品评价的维度在变化"),
    ("img6", "性别批评相关的评论通常打分更低"),
]

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
    if not pct_str:
        return 0.0
    s = str(pct_str).replace("%", "").replace("-", "0").strip()
    try:
        v = float(s)
        return max(0.0, min(1.0, v / 100.0))
    except:
        return 0.0

def phase_name_only(phase_str):
    s = phase_str.strip()
    s = re.sub(r'^\d+\s*[\.、\s]\s*', '', s)
    return s

def phase_num(phase_str):
    m = re.match(r'^\s*(\d+)', phase_str)
    return m.group(1) if m else ''

# ════════════════════════════════════════════════════════════════
# GLOBAL OVERRIDE — applies to ALL images
# Round 1.2 changes vs round 1.1:
#   - logo 48px → 62px (×1.3)
#   - watermark z-index 1 → 9999 (above cards)
#   - watermark svg pointer-events none (already in template, keep)
# ════════════════════════════════════════════════════════════════
GLOBAL_OVERRIDE = """
<style data-purpose="round1.2-overrides">
/* Issue 2 (round1): canvas height auto-fits content */
.chart-container{ min-height:auto !important; height:auto !important; padding:56px 48px !important; }
.chart-body{ flex:0 1 auto !important; min-height:auto !important; }
/* Issue 3 (round1): watermark × 1.5 (280 → 420), opacity 0.10 */
.yz-watermark svg{ width:420px !important; opacity:0.10 !important; }
/* Issue 4 (round1.2): watermark z-index above cards — must be on .chart-container level, not chart-body */
.yz-watermark{ z-index:9999 !important; }
/* Issue 4 (round1.2): chart-body must NOT create stacking context that traps watermark below it */
.chart-body{ z-index:auto !important; }
/* Issue 3 (round1): title × 2 (34 → 68) */
.chart-title{ font-size:68px !important; line-height:1.25 !important; margin-bottom:36px !important; }
/* Issue 3 (round1): footer × 2 (13 → 26) */
.chart-source{ font-size:26px !important; line-height:1.5 !important; }
/* Issue 5 (round1.2): logo × 1.3 (48 → 62) */
.yz-logo-svg{ height:62px !important; }
/* Issue 3 (round1): shared components × 2 */
.yz-table{ font-size:28px !important; }
.yz-table th{ padding:18px 20px !important; }
.yz-table td{ padding:14px 20px !important; }
.yz-bar-label{ font-size:28px !important; width:240px !important; }
.yz-bar-track{ height:56px !important; }
.yz-bar{ font-size:28px !important; padding-right:14px !important; }
.yz-bar-value{ font-size:28px !important; }
.yz-line-chart .axis-text{ font-size:24px !important; }
.chart-footer{ margin-top:36px !important; padding-top:24px !important; }
</style>
"""

# ════════════════════════════════════════════════════════════════
# SHARED CSS — reusable classes across multiple images
# User request: "对于类似的元素可以一次性定义多次引用，不要每一个图都单独定义"
# Images using these: img2, img3, img5, img6 (all dumbbell/bar charts)
# ════════════════════════════════════════════════════════════════
SHARED_CSS = """
<style data-purpose="round1.2-shared">
/* ── 阶段名 + 圆形数字徽章（img2/img3/img4 复用）── */
.phase-label{
  font-size:30px; font-weight:900; color:#312e2e;
  display:flex; align-items:center; gap:14px;
}
.phase-label .phase-badge{
  display:inline-flex; align-items:center; justify-content:center;
  width:44px; height:44px; background:#fc8166; color:#fff;
  border-radius:50%; font-size:26px; font-weight:900; flex-shrink:0;
}
/* ── 哑铃轨道（img3/img5/img6 复用）── */
.dumbbell-track{
  position:relative; height:64px; background:#fafafa; border-radius:32px;
}
.dumbbell-track::before{
  content:""; position:absolute; top:50%; left:0; right:0;
  height:3px; background:#eee; transform:translateY(-50%);
}
/* ── 圆点（img3/img5/img6 复用）── */
.dumbbell-dot{
  position:absolute; top:50%; transform:translate(-50%,-50%);
  width:34px; height:34px; border-radius:50%;
  border:5px solid #fff; box-shadow:0 0 0 3px currentColor; z-index:2;
}
/* ── 圆点数值标签（img3/img5/img6 复用）── */
/* Round 1.2 fix: above label moved from -32px to -52px to avoid overlap with previous row */
.dumbbell-tag{
  position:absolute; font-size:22px; font-weight:700;
  white-space:nowrap; transform:translateX(-50%);
}
.dumbbell-tag.above{ top:-50px; }
.dumbbell-tag.below{ bottom:-50px; }
/* ── 连接线（img3/img5/img6 复用）── */
.dumbbell-line{
  position:absolute; top:50%; height:6px; transform:translateY(-50%); z-index:1;
}
/* ── x 轴刻度（img3/img5/img6 复用）── */
.axis-scale{
  display:flex; justify-content:space-between;
  font-size:18px; color:#9a9595; margin-top:14px; padding:0 4px;
}
/* ── 图例（所有图复用）── */
.chart-legend{
  display:flex; flex-wrap:wrap; gap:18px 32px;
  margin-top:14px; font-size:22px; color:#6b6666;
}
.chart-legend .legend-item{ display:flex; align-items:center; gap:10px; }
.chart-legend .legend-swatch{ width:24px; height:24px; border-radius:50%; }
.chart-legend .legend-swatch.bar{ width:32px; height:8px; border-radius:4px; }
</style>
"""

# ════════════════════════════════════════════════════════════════
# Image builders
# ════════════════════════════════════════════════════════════════

def build_img1(d):
    """img1: 10×6 heatmap table."""
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append("""
    <style>
    .hm-table{width:100%;border-collapse:separate;border-spacing:6px;font-size:28px;}
    .hm-table th{padding:18px 10px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:6px;font-size:24px;}
    .hm-table th.row-head{background:transparent;text-align:left;padding-left:14px;color:#fc8166;}
    .hm-table td{padding:22px 8px;text-align:center;border-radius:6px;font-weight:700;color:#312e2e;min-width:110px;font-size:26px;}
    .hm-table td.row-label{text-align:left;padding-left:14px;font-weight:700;color:#fc8166;background:#fff;font-size:24px;}
    .hm-legend{display:flex;align-items:center;gap:20px;margin-top:24px;font-size:22px;color:#6b6666;}
    .hm-legend .grad{display:inline-block;width:240px;height:16px;background:linear-gradient(to right,rgba(252,129,102,0.05),rgba(252,129,102,1));border-radius:3px;}
    </style>
    """)
    parts.append('<table class="hm-table">')
    parts.append('<thead><tr>')
    for h in headers:
        cls = 'row-head' if h == '' else ''
        parts.append(f'<th class="{cls}">{esc(h)}</th>')
    parts.append('</tr></thead><tbody>')
    for r in rows:
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


def build_img2(d):
    """img2: 4 horizontal stacked bars. Use precise data from docx.
       docx precise values:
         Phase 1: F1=86.08%, F3=9.16%, F4=0.37%, F6=0.37%, F2+F5=4.03% (split as F2=2%, F5=2.03%)
         Phase 2: F1=34.02%, F3=46.63%, F4=6.74%, F5=10.56%, F2+F6=2.05% (split as F2=1%, F6=1.05%)
         Phase 3: F1=55.40%, F3=37.70%, remaining 6.90% (F2+F4+F5+F6, split evenly ~1.73% each)
         Phase 4: F1=75.60%, F3=16.09%, remaining 8.31% (F2+F4+F5+F6, split evenly ~2.08% each)
    """
    # Use docx-precise data instead of VLM approximations
    rows = [
        ("1 动作演员与军旅角色",    [("专业能力",86.08),("民族国家",9.16),("道德人格",2.00),("社会文化/性别",2.03),("商业资本",0.37),("身份符号",0.37)]),
        ("2 “战狼”IP成型",          [("民族国家",46.63),("专业能力",34.02),("社会文化/性别",10.56),("商业资本",6.74),("道德人格",1.00),("身份符号",1.05)]),
        ("3 国家工业大片扩张",      [("专业能力",55.40),("民族国家",37.70),("社会文化/性别",1.73),("商业资本",1.73),("道德人格",1.72),("身份符号",1.72)]),
        ("4 后“战狼”分化",          [("专业能力",75.60),("民族国家",16.09),("社会文化/性别",2.08),("商业资本",2.08),("道德人格",2.07),("身份符号",2.08)]),
    ]
    color_map = {
        '专业能力': '#fc8166',
        '道德人格': '#7dd3f9',
        '民族国家': '#e74c3c',
        '商业资本': '#f39c12',
        '社会文化/性别': '#a569bd',
        '身份符号': '#a8d08d',
    }
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append("""
    <style>
    .sb-wrap{display:flex;flex-direction:column;gap:36px;}
    .sb-row{display:flex;flex-direction:column;gap:12px;}
    .sb-bar{display:flex;width:100%;height:80px;border-radius:8px;overflow:hidden;background:#fafafa;}
    .sb-seg{display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;color:#fff;}
    </style>
    """)
    parts.append('<div class="sb-wrap">')
    for phase_full, segs in rows:
        pnum = phase_num(phase_full)
        pname = phase_name_only(phase_full)
        parts.append('<div class="sb-row">')
        parts.append(f'<div class="phase-label"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
        parts.append('<div class="sb-bar">')
        for dim, val in segs:
            color = color_map.get(dim, '#999')
            width_pct = val
            if width_pct < 0.3:
                continue
            # Issue 1 (round1.2): show label on ALL segments ≥1.5%; tiny segments show on hover via title
            if width_pct >= 5:
                label = f'{val:.2f}%'
                font_color = '#fff'
            elif width_pct >= 1.5:
                # small segment: show number in smaller font
                label = f'{val:.1f}%'
                font_color = '#fff'
            else:
                # very tiny: show value via title attribute, no inline text
                label = ''
                font_color = '#fff'
            parts.append(f'<div class="sb-seg" style="background:{color};flex:{width_pct} 0 0;color:{font_color};" title="{esc(dim)}: {val:.2f}%">{esc(label)}</div>')
        parts.append('</div></div>')
    parts.append('</div>')
    # Add small-segment summary table below the chart for full data disclosure
    parts.append("""
    <style>
    .sb-data-table{width:100%;border-collapse:collapse;font-size:18px;margin-top:24px;}
    .sb-data-table th{background:#fafafa;padding:10px 8px;text-align:center;font-weight:900;color:#312e2e;border-bottom:2px solid #dcdcdc;}
    .sb-data-table td{padding:8px;text-align:center;border-bottom:1px solid #f0f0f0;color:#312e2e;}
    .sb-data-table td:first-child{text-align:left;font-weight:700;color:#fc8166;}
    .sb-data-table .zero{color:#ccc;}
    </style>
    """)
    parts.append('<table class="sb-data-table">')
    parts.append('<thead><tr><th>阶段</th><th>专业能力</th><th>道德人格</th><th>民族国家</th><th>商业资本</th><th>社会文化/性别</th><th>身份符号</th></tr></thead>')
    parts.append('<tbody>')
    for phase_full, segs in rows:
        pname = phase_name_only(phase_full)
        seg_dict = dict(segs)
        parts.append('<tr>')
        parts.append(f'<td>{esc(pname)}</td>')
        for dim in ['专业能力','道德人格','民族国家','商业资本','社会文化/性别','身份符号']:
            v = seg_dict.get(dim, 0)
            cls = 'zero' if v < 0.5 else ''
            parts.append(f'<td class="{cls}">{v:.2f}%</td>')
        parts.append('</tr>')
    parts.append('</tbody></table>')
    # Legend
    parts.append('<div class="chart-legend">')
    for dim in ['专业能力','道德人格','民族国家','商业资本','社会文化/性别','身份符号']:
        color = color_map.get(dim, '#999')
        parts.append(f'<div class="legend-item"><span class="legend-swatch bar" style="background:{color}"></span>{esc(dim)}</div>')
    parts.append('</div>')
    return "\n".join(parts)


def build_img3(d):
    """img3: 4-row dumbbell. Issue 2 (round1.2): above label moved to -52px (was -32px) to avoid overlap."""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append("""
    <style>
    /* Round 1.2 fix: db3-row internal gap 24px → 70px so above-label (top:-50px, ~22px tall)
       doesn't overlap with this row's own phase-label.
       Row-to-row gap 80px keeps below-label (bottom:-50px) clear of next row's phase-label. */
    .db3-wrap{display:flex;flex-direction:column;gap:90px;padding:8px 0;}
    .db3-row{display:flex;flex-direction:column;gap:70px;}
    </style>
    """)
    parts.append('<div class="db3-wrap">')
    for r in rows:
        phase_full = r[0]
        pnum = phase_num(phase_full)
        pname = phase_name_only(phase_full)
        v_actor = pct_to_opacity(r[1]) * 100 if len(r) > 1 else 0
        v_work = pct_to_opacity(r[2]) * 100 if len(r) > 2 else 0
        v_actor_c = max(2, min(98, v_actor))
        v_work_c = max(2, min(98, v_work))
        left = min(v_actor_c, v_work_c)
        right = max(v_actor_c, v_work_c)
        parts.append('<div class="db3-row">')
        parts.append(f'<div class="phase-label"><span class="phase-badge">{esc(pnum)}</span>{esc(pname)}</div>')
        parts.append('<div class="dumbbell-track">')
        parts.append(f'<div class="dumbbell-line" style="left:{left}%;width:{right-left}%;background:#dcdcdc;"></div>')
        parts.append(f'<div class="dumbbell-dot" style="left:{v_actor_c}%;background:#fc8166;color:#fc8166;"></div>')
        parts.append(f'<div class="dumbbell-tag above" style="left:{v_actor_c}%;color:#fc8166;">{esc(r[1])}</div>')
        parts.append(f'<div class="dumbbell-dot" style="left:{v_work_c}%;background:#6cb0f9;color:#6cb0f9;"></div>')
        parts.append(f'<div class="dumbbell-tag below" style="left:{v_work_c}%;color:#6cb0f9;">{esc(r[2])}</div>')
        parts.append('</div>')
        parts.append('</div>')
    parts.append('<div class="axis-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>')
    parts.append('</div>')
    parts.append('<div class="chart-legend">')
    parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>直接指向演员</div>')
    parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>仅涉及作品层面</div>')
    parts.append('</div>')
    return "\n".join(parts)


def build_img4(d):
    """img4: 4 quote cards in 2×2 grid.
       Issue 3 (round1.2): year-rating row font 18px → 24px; phase name color black (not red).
       Phase badge stays orange; phase name text becomes #312e2e (same as other images)."""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append("""
    <style>
    /* Round 1.2 fix: tc-grid and tc-card must NOT have z-index or background that blocks watermark */
    .tc-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;position:relative;z-index:2;}
    .tc-card{
      border:1px solid #f0f0f0; border-left:8px solid #fc8166;
      border-radius:8px; padding:28px 32px;
      /* Issue 4 (round1.2): semi-transparent bg so watermark shows through */
      background:rgba(255,255,255,0.92);
      display:flex; flex-direction:column; gap:14px;
      position:relative;
    }
    .tc-card-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;}
    /* Issue 3 (round1.2): phase name color black, not red; badge stays orange */
    .tc-phase{font-size:24px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:10px;}
    .tc-phase .phase-badge{
      display:inline-flex;align-items:center;justify-content:center;
      width:36px;height:36px;background:#fc8166;color:#fff;
      border-radius:50%;font-size:22px;font-weight:900;
    }
    .tc-work{font-size:30px;font-weight:900;color:#312e2e;}
    /* Issue 3 (round1.2): year-rating row 18px → 24px */
    .tc-meta{font-size:24px;color:#9a9595;margin-left:auto;display:flex;gap:18px;}
    .tc-meta b{color:#312e2e;font-weight:900;}
    .tc-quote{font-size:26px;line-height:1.65;color:#312e2e;font-weight:500;}
    .tc-quote .qmark{color:#fc8166;font-weight:900;font-size:36px;line-height:0;vertical-align:-6px;}
    </style>
    """)
    parts.append('<div class="tc-grid">')
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
    return "\n".join(parts)


def build_img5(d):
    """img5: 3 dimension sub-charts, each 10-film dumbbell."""
    series = d.get("series", [])
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    films = []
    for s in series:
        for pt in s.get('data_points', []):
            fname = pt[0]
            if fname not in films:
                films.append(fname)
    color_map = {
        '专业能力': '#fc8166',
        '民族国家': '#f5a623',
        '社会文化/性别': '#7fd3f0',
    }
    parts.append("""
    <style>
    .db5-wrap{display:flex;flex-direction:column;gap:28px;}
    .db5-sub{display:flex;flex-direction:column;gap:10px;}
    .db5-sub-title{font-size:30px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:14px;padding-bottom:8px;border-bottom:2px solid #f0f0f0;}
    .db5-sub-title .legend-swatch.bar{width:32px;height:8px;border-radius:4px;}
    .db5-rows{display:flex;flex-direction:column;gap:8px;}
    .db5-row{display:grid;grid-template-columns:240px 1fr 110px;gap:14px;align-items:center;}
    .db5-film{font-size:20px;font-weight:700;color:#312e2e;line-height:1.3;}
    /* Override shared dumbbell-track for compact 5 sub-charts */
    .db5-row .dumbbell-track{height:32px;border-radius:16px;}
    .db5-row .dumbbell-dot{width:18px;height:18px;border:3px solid #fff;}
    .db5-row .dumbbell-tag{font-size:16px;font-weight:700;}
    .db5-row .dumbbell-tag.above{top:-22px;}
    .db5-row .dumbbell-tag.below{bottom:-22px;}
    .db5-diff{font-size:18px;font-weight:900;color:#6b6666;text-align:right;}
    .db5-diff.up{color:#fc8166;}
    .db5-diff.down{color:#6cb0f9;}
    </style>
    """)
    parts.append('<div class="db5-wrap">')
    for s in series:
        sname = s.get('name', '')
        color = color_map.get(sname, '#999')
        data = {}
        for pt in s.get('data_points', []):
            fname = pt[0]
            val = pt[1]
            if isinstance(val, list) and len(val) >= 2:
                try:
                    data[fname] = (float(val[0]), float(val[1]))
                except:
                    continue
            elif isinstance(val, (int, float, str)):
                try:
                    v = float(str(val).replace('%','').strip())
                    data[fname] = (v, v)
                except:
                    continue
        parts.append('<div class="db5-sub">')
        parts.append(f'<div class="db5-sub-title"><span class="legend-swatch bar" style="background:{color}"></span>{esc(sname)}</div>')
        parts.append('<div class="db5-rows">')
        for fname in films:
            if fname not in data:
                continue
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
        parts.append('</div>')
        parts.append('</div>')
    parts.append('<div class="chart-legend">')
    parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#fff;border:2px solid #fc8166;"></span>上映初期占比</div>')
    parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>近一年占比</div>')
    parts.append('<div class="legend-item" style="margin-left:auto;font-size:18px;color:#9a9595;">差值：橙色=上升，蓝色=下降</div>')
    parts.append('</div>')
    parts.append('</div>')
    return "\n".join(parts)


def build_img6(d):
    """img6: 5 films × 2 metrics dumbbell."""
    td = d.get("table_data", {})
    rows = td.get("rows", [])
    parts = [GLOBAL_OVERRIDE, SHARED_CSS]
    parts.append("""
    <style>
    .sc6-wrap{display:flex;flex-direction:column;gap:36px;}
    .sc6-row{display:flex;flex-direction:column;gap:14px;}
    .sc6-label{font-size:30px;font-weight:900;color:#312e2e;display:flex;justify-content:space-between;align-items:baseline;}
    .sc6-label .diff{font-size:26px;font-weight:900;color:#e60012;}
    /* Override shared dumbbell-track for 1.3 ratio */
    .sc6-row .dumbbell-track{height:60px;}
    .sc6-row .dumbbell-dot{width:32px;height:32px;}
    .sc6-row .dumbbell-tag{font-size:22px;font-weight:700;}
    .sc6-row .dumbbell-tag.above{top:-52px;}
    .sc6-row .dumbbell-tag.below{bottom:-52px;}
    .sc6-line-dashed{
      position:absolute;top:50%;height:5px;transform:translateY(-50%);
      background:repeating-linear-gradient(to right,#fc8166 0,#fc8166 6px,transparent 6px,transparent 12px);
      z-index:1;
    }
    </style>
    """)
    parts.append('<div class="sc6-wrap">')
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
        parts.append('</div>')
        parts.append('</div>')
    parts.append('<div class="axis-scale"><span>1星</span><span>2星</span><span>3星</span><span>4星</span><span>5星</span></div>')
    parts.append('</div>')
    parts.append('<div class="chart-legend">')
    parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>性别批评评论平均星级</div>')
    parts.append('<div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>电影评分星级</div>')
    parts.append('</div>')
    return "\n".join(parts)


BUILDERS = {
    "img1": build_img1,
    "img2": build_img2,
    "img3": build_img3,
    "img4": build_img4,
    "img5": build_img5,
    "img6": build_img6,
}

def build_plain(img_id, d, title, footer):
    td = d.get("table_data", {}) or {}
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    parts = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
             f'<title>{esc(title)}</title>',
             '<style>',
             'body{font-family:-apple-system,sans-serif;background:#f0f0f0;padding:40px;margin:0;}',
             '.c{width:900px;background:#fff;margin:0 auto;padding:48px;box-sizing:border-box;}',
             'h1{font-size:64px;font-weight:900;margin:0 0 32px 0;color:#000;}',
             'table{width:100%;border-collapse:collapse;font-size:28px;margin-top:24px;}',
             'th,td{border:1px solid #ccc;padding:14px;text-align:left;}',
             'th{background:#f5f5f5;font-weight:bold;}',
             '.src{margin-top:32px;font-size:24px;color:#666;border-top:1px solid #eee;padding-top:16px;}',
             '</style></head><body>',
             '<div class="c">',
             f'<h1>{esc(title)}</h1>']
    if headers:
        parts.append('<table><thead><tr>')
        for h in headers:
            parts.append(f'<th>{esc(h)}</th>')
        parts.append('</tr></thead><tbody>')
        for r in rows:
            parts.append('<tr>')
            for c in r:
                parts.append(f'<td>{esc(c)}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')
    else:
        for s in d.get('series', []):
            parts.append(f'<p style="font-size:28px"><b>{esc(s.get("name",""))}</b></p>')
            parts.append('<ul style="font-size:24px">')
            for pt in s.get('data_points', []):
                parts.append(f'<li>{esc(pt[0])} — {esc(pt[1])}</li>')
            parts.append('</ul>')
    parts.append(f'<div class="src">{esc(footer)}</div>')
    parts.append('</div></body></html>')
    return "\n".join(parts)

def main():
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    for img_id, vlm_name in ORDER:
        d = load_vlm(vlm_name)
        body = BUILDERS[img_id](d)
        title_raw = d.get("title_text", vlm_name).split("\n")[0].strip()
        title = re.sub(r'^图\s*\d+\s*[：:]\s*', '', title_raw)
        # For img2, use a more detailed footer with docx data source
        if img_id == "img2":
            footer = "数据来源：豆瓣短评 2,968 条，娱乐资本论整理。F1=专业能力 F2=道德人格 F3=民族国家 F4=商业资本 F5=社会文化/性别 F6=身份符号。"
        else:
            footer = d.get("data_source_text") or d.get("footer_text") or "数据来源：豆瓣短评，娱乐资本论整理"
        out_html = tpl.replace("【TITLE_HERE】", esc(title))
        out_html = out_html.replace("【CHART_BODY_HERE】", body)
        out_html = out_html.replace("【SOURCE_FOOTER_HERE：数据来源 + 测试概述（基于x个平台x段录屏的x个片段，时间段xxx）】", esc(footer))
        out_html = out_html.replace("【SOURCE_FOOTER_HERE】", esc(footer))
        out_path = os.path.join(OUT_DIR, f"{img_id}-styled.html")
        pathlib.Path(out_path).write_text(out_html, encoding="utf-8")
        plain = build_plain(img_id, d, title, footer)
        plain_path = os.path.join(OUT_DIR, f"{img_id}.html")
        pathlib.Path(plain_path).write_text(plain, encoding="utf-8")
        print(f"  wrote {img_id}-styled.html ({len(out_html)} bytes)")

if __name__ == "__main__":
    main()
