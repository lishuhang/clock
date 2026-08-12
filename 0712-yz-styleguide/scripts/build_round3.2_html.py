#!/usr/bin/env python3
"""
Generate round3.2 — fixes:
  1. img6: above tags → below (both red and blue dots' labels below the track)
  2. img6: more bottom spacing to avoid overlap with footer
  3. All images: remove gray border (left/top) by screenshotting .chart-container-1x1 element, not viewport
"""
import os, re, pathlib, glob

ROUND22 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round2.2"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.2"
os.makedirs(OUT_DIR, exist_ok=True)

# Layout fixes
LAYOUT_FIXES = """
<style data-purpose="round3.2-layout-fixes">
/* img5 fix: film name smaller; legend inline with sub-title */
.db5-film-name{ font-size:16px !important; line-height:1.15 !important; }
.db5-film-col{ width:180px !important; max-width:180px !important; overflow:hidden; }
.db5-sub-title{ display:flex !important; align-items:center !important; gap:14px !important; flex-wrap:wrap !important; }
.db5-sub-title .inline-legend{ display:flex !important; gap:16px !important; margin-left:auto !important; font-size:18px !important; color:#6b6666 !important; }
.db5-sub-title .inline-legend .legend-item{ display:flex !important; align-items:center !important; gap:6px !important; }
.db5-sub-title .inline-legend .legend-swatch{ width:18px !important; height:18px !important; border-radius:50% !important; }
.db5-wrap > .chart-legend{ display:none !important; }
.db5-rows{ gap:6px !important; }
.db5-row{ grid-template-columns:180px 1fr 90px !important; gap:12px !important; }

/* img6 fix: BOTH labels below the track, staggered to avoid overlap */
.sc6-wrap{ gap:36px !important; padding-bottom:100px !important; }
.sc6-row{ gap:8px !important; }
/* Red dot label (was above) → move to below at -56px */
.sc6-row .dumbbell-tag.above{ top:auto !important; bottom:-56px !important; }
/* Blue dot label (was below at -50px) → move to -100px to stagger below red */
.sc6-row .dumbbell-tag.below{ bottom:-100px !important; }
.chart-footer-1x1{ margin-top:80px !important; padding-top:20px !important; }
.sc6-row .dumbbell-track{ height:52px !important; }
.sc6-row .dumbbell-dot{ width:28px !important; height:28px !important; }

/* Remove body padding/background gray edge */
body{ background:#fff !important; padding:0 !important; margin:0 !important; }
.chart-container-1x1{ margin:0 !important; }
</style>
"""

# Animation CSS (same as round3.1, pie mask fix included)
ANIMATION_CSS = """
<style data-purpose="round3.2-animations">
@property --pie-reveal {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

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
.chart-body-1x1 .pie-svg{
  opacity:1;
  -webkit-mask: conic-gradient(from -90deg, white 0deg, white 0deg, transparent 0deg);
  mask: conic-gradient(from -90deg, white 0deg, white 0deg, transparent 0deg);
}
.chart-body-1x1 .sb-bar{ transform: scaleY(0); transform-origin: bottom; }
.chart-body-1x1 .dumbbell-line,
.chart-body-1x1 .sc6-line-dashed{ transform: scaleX(0); transform-origin: left; opacity:1; }
.chart-body-1x1 .tc-bg{ transform: translateY(20px); }

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
    inline_legend = '<div class="inline-legend"><div class="legend-item"><span class="legend-swatch" style="background:#fff;border:2px solid #fc8166;"></span>上映初期</div><div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>近一年</div></div>'
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
    if name.startswith('img5'):
        html = add_inline_legend_to_img5(html)
    html = html.replace("</head>", LAYOUT_FIXES + "\n</head>", 1)
    html = html.replace("</head>", ANIMATION_CSS + "\n</head>", 1)
    return html

def main():
    htmls = sorted(glob.glob(os.path.join(ROUND22, "*-styled.html")))
    for html_path in htmls:
        name = os.path.basename(html_path)
        processed = process_html(html_path)
        out_path = os.path.join(OUT_DIR, name)
        pathlib.Path(out_path).write_text(processed, encoding="utf-8")
    print(f"Generated {len(htmls)} HTML files to {OUT_DIR}")

if __name__ == "__main__":
    main()
