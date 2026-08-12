#!/usr/bin/env python3
"""
Generate round3.1 — fixes:
  1. img2 pie chart not appearing (mask + @property issue → fix animation CSS)
  2. img5: film name wrapping overlaps with chart below → shrink font slightly;
           legend moves from below bars to right of sub-title
  3. img6: bottom labels overlap with footer → increase bottom spacing
Strategy: copy round2.2 HTML, apply layout fixes via CSS injection, then add animation CSS.
"""
import os, re, pathlib, glob

ROUND22 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round2.2"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.1"
os.makedirs(OUT_DIR, exist_ok=True)

# Layout fixes for img5 and img6 (applied via CSS override)
LAYOUT_FIXES = """
<style data-purpose="round3.1-layout-fixes">
/* img5 fix: film name smaller to avoid wrapping; legend to right of sub-title */
.db5-film-name{ font-size:16px !important; line-height:1.15 !important; }
.db5-film-col{ width:180px !important; max-width:180px !important; overflow:hidden; }
/* Move legend from below to inline with sub-title (for img5) */
.db5-sub-title{ display:flex !important; align-items:center !important; gap:14px !important; flex-wrap:wrap !important; }
.db5-sub-title .inline-legend{ display:flex !important; gap:16px !important; margin-left:auto !important; font-size:18px !important; color:#6b6666 !important; }
.db5-sub-title .inline-legend .legend-item{ display:flex !important; align-items:center !important; gap:6px !important; }
.db5-sub-title .inline-legend .legend-swatch{ width:18px !important; height:18px !important; border-radius:50% !important; }
/* Hide the old bottom legend for img5 */
.db5-wrap > .chart-legend{ display:none !important; }
/* img5: reduce row gap to give more room */
.db5-rows{ gap:6px !important; }
.db5-row{ grid-template-columns:180px 1fr 90px !important; gap:12px !important; }

/* img6 fix: increase bottom spacing, label tags need more room */
.sc6-wrap{ gap:40px !important; padding-bottom:60px !important; }
.sc6-row{ gap:24px !important; }
.sc6-row .dumbbell-tag.below{ bottom:-56px !important; }
.chart-footer-1x1{ margin-top:48px !important; padding-top:20px !important; }
/* Also reduce sc6-wrap height to fit — fewer gaps if needed */
.sc6-row .dumbbell-track{ height:56px !important; }
.sc6-row .dumbbell-dot{ width:30px !important; height:30px !important; }
</style>
"""

# Fixed animation CSS — pie uses mask sweep, opacity stays 1
ANIMATION_CSS = """
<style data-purpose="round3.1-animations">
@property --pie-reveal {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

/* Initial state: everything invisible (before .play) */
.chart-logo-1x1,
.chart-title-1x1,
.chart-source-1x1,
.chart-part-num,
.chart-body-1x1 .phase-label,
.chart-body-1x1 .axis-scale,
.chart-body-1x1 .chart-legend,
.chart-body-1x1 .hm-legend,
.chart-body-1x1 .pie-legend-h,
.chart-body-1x1 .pie-phase-label,
.chart-body-1x1 .sb-data-table,
.chart-body-1x1 .tc-meta-block,
.chart-body-1x1 .tc-quote-center,
.chart-body-1x1 .db5-sub-title,
.chart-body-1x1 .sc6-label,
.chart-body-1x1 .hm-table,
.chart-body-1x1 .hm-table tbody tr,
.chart-body-1x1 .hm-table thead,
.chart-body-1x1 .sb-bar,
.chart-body-1x1 .dumbbell-dot,
.chart-body-1x1 .dumbbell-tag,
.chart-body-1x1 .tc-bg,
.chart-body-1x1 .sc6-row,
.chart-body-1x1 .db5-row{ opacity:0; }
/* pie-svg: mask controls visibility (sweep), opacity stays 1 */
.chart-body-1x1 .pie-svg{
  opacity:1;
  -webkit-mask: conic-gradient(from -90deg, white 0deg, white 0deg, transparent 0deg);
  mask: conic-gradient(from -90deg, white 0deg, white 0deg, transparent 0deg);
}
.chart-body-1x1 .sb-bar{ transform: scaleY(0); transform-origin: bottom; }
.chart-body-1x1 .dumbbell-line,
.chart-body-1x1 .sc6-line-dashed{ transform: scaleX(0); transform-origin: left; opacity:1; }
.chart-body-1x1 .tc-bg{ transform: translateY(20px); }

/* body.play triggers animations */
body.play .chart-logo-1x1{ animation: fadeIn 0.6s ease-out 0s forwards !important; }
body.play .chart-title-1x1{ animation: fadeIn 0.6s ease-out 0.4s forwards !important; }
body.play .chart-source-1x1{ animation: fadeIn 0.6s ease-out 0.8s forwards !important; }
body.play .chart-part-num{ animation: fadeIn 0.6s ease-out 0.8s forwards !important; }
body.play .chart-body-1x1 .phase-label,
body.play .chart-body-1x1 .axis-scale,
body.play .chart-body-1x1 .chart-legend,
body.play .chart-body-1x1 .hm-legend,
body.play .chart-body-1x1 .pie-legend-h,
body.play .chart-body-1x1 .pie-phase-label,
body.play .chart-body-1x1 .sb-data-table,
body.play .chart-body-1x1 .tc-meta-block,
body.play .chart-body-1x1 .tc-quote-center,
body.play .chart-body-1x1 .db5-sub-title,
body.play .chart-body-1x1 .sc6-label{ animation: fadeIn 0.6s ease-out 0.8s forwards !important; }
body.play .chart-body-1x1 .hm-table{ animation: fadeIn 0.8s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(1){ animation: rowFade 0.4s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(2){ animation: rowFade 0.4s ease-out 1.4s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(3){ animation: rowFade 0.4s ease-out 1.6s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(4){ animation: rowFade 0.4s ease-out 1.8s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(5){ animation: rowFade 0.4s ease-out 2.0s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(6){ animation: rowFade 0.4s ease-out 2.2s forwards !important; }
body.play .chart-body-1x1 .hm-table tbody tr:nth-child(7){ animation: rowFade 0.4s ease-out 2.4s forwards !important; }
body.play .chart-body-1x1 .hm-table thead{ animation: fadeIn 0.4s ease-out 1.2s forwards !important; }
/* Pie: animate --pie-reveal from 0 to 360deg, mask follows */
body.play .chart-body-1x1 .pie-svg{
  animation: pieSweep 1.2s ease-out 1.2s forwards !important;
  -webkit-mask: conic-gradient(from -90deg, white 0deg, white var(--pie-reveal, 0deg), transparent var(--pie-reveal, 0deg));
  mask: conic-gradient(from -90deg, white 0deg, white var(--pie-reveal, 0deg), transparent var(--pie-reveal, 0deg));
}
body.play .chart-body-1x1 .sb-bar{ animation: growUp 0.8s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .dumbbell-line{ animation: growRight 0.6s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .dumbbell-dot{ animation: fadeIn 0.4s ease-out 1.8s forwards !important; }
body.play .chart-body-1x1 .dumbbell-tag{ animation: fadeIn 0.4s ease-out 2.0s forwards !important; }
body.play .chart-body-1x1 .tc-bg{ animation: riseFade 0.8s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .sc6-row{ animation: fadeIn 0.5s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .sc6-row:nth-child(2){ animation-delay: 1.4s !important; }
body.play .chart-body-1x1 .sc6-row:nth-child(3){ animation-delay: 1.6s !important; }
body.play .chart-body-1x1 .sc6-row:nth-child(4){ animation-delay: 1.8s !important; }
body.play .chart-body-1x1 .sc6-row:nth-child(5){ animation-delay: 2.0s !important; }
body.play .chart-body-1x1 .sc6-line-dashed{ animation: growRight 0.6s ease-out 2.2s forwards !important; }
body.play .chart-body-1x1 .sc6-row .dumbbell-dot{ animation-delay: 2.4s !important; }
body.play .chart-body-1x1 .sc6-row .dumbbell-tag{ animation-delay: 2.6s !important; }
body.play .chart-body-1x1 .db5-row{ animation: fadeIn 0.4s ease-out 1.2s forwards !important; }
body.play .chart-body-1x1 .db5-row:nth-child(2){ animation-delay: 1.3s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(3){ animation-delay: 1.4s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(4){ animation-delay: 1.5s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(5){ animation-delay: 1.6s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(6){ animation-delay: 1.7s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(7){ animation-delay: 1.8s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(8){ animation-delay: 1.9s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(9){ animation-delay: 2.0s !important; }
body.play .chart-body-1x1 .db5-row:nth-child(10){ animation-delay: 2.1s !important; }
body.play .chart-body-1x1 .db5-row .dumbbell-line{ animation-delay: 2.3s !important; }
body.play .chart-body-1x1 .db5-row .dumbbell-dot{ animation-delay: 2.5s !important; }
body.play .chart-body-1x1 .db5-row .dumbbell-tag{ animation-delay: 2.7s !important; }

@keyframes fadeIn{ to{ opacity:1; } }
@keyframes rowFade{ to{ opacity:1; } }
@keyframes pieSweep{ to{ --pie-reveal: 360deg; } }
@keyframes growUp{ to{ transform: scaleY(1); opacity:1; } }
@keyframes growRight{ to{ transform: scaleX(1); opacity:1; } }
@keyframes riseFade{ to{ opacity:1; transform: translateY(0); } }
#yz-selfcheck-banner{ display:none !important; }
</style>
"""

def add_inline_legend_to_img5(html):
    """For img5 HTML, move legend from below to inline with sub-title."""
    # The sub-title is: <div class="db5-sub-title"><span ...>...</span>专业能力</div>
    # Insert inline legend before the closing </div> of sub-title
    inline_legend = '<div class="inline-legend"><div class="legend-item"><span class="legend-swatch" style="background:#fff;border:2px solid #fc8166;"></span>上映初期</div><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>近一年</div></div>'
    
    # Match: <div class="db5-sub-title">...some content...</div>
    # The sub-title contains a span + text like "专业能力"
    html = re.sub(
        r'(<div class="db5-sub-title">)(.*?)(</div>)',
        r'\1\2' + inline_legend + r'\3',
        html,
        flags=re.DOTALL
    )
    
    return html

def process_html(html_path):
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    
    name = os.path.basename(html_path).replace('-styled.html', '')
    
    # Apply img5-specific fix: inline legend
    if name.startswith('img5'):
        html = add_inline_legend_to_img5(html)
    
    # Inject layout fixes (applies to img5 and img6, harmless to others)
    html = html.replace("</head>", LAYOUT_FIXES + "\n</head>", 1)
    
    # Inject animation CSS
    html = html.replace("</head>", ANIMATION_CSS + "\n</head>", 1)
    
    return html

def main():
    htmls = sorted(glob.glob(os.path.join(ROUND22, "*-styled.html")))
    total = 0
    for html_path in htmls:
        name = os.path.basename(html_path)
        processed = process_html(html_path)
        out_path = os.path.join(OUT_DIR, name)
        pathlib.Path(out_path).write_text(processed, encoding="utf-8")
        total += 1
    print(f"Generated {total} HTML files to {OUT_DIR}")

if __name__ == "__main__":
    main()
