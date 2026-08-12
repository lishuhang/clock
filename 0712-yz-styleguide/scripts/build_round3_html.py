#!/usr/bin/env python3
"""
Generate animated HTML for round3 — adds CSS entrance animations to round2.2 HTML.
Uses body.play class to trigger animations (ensures first screenshot is pure white).
"""
import os, pathlib, glob

ROUND22 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round2.2"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3"
os.makedirs(OUT_DIR, exist_ok=True)

ANIMATION_CSS = """
<style data-purpose="round3-animations">
@property --pie-reveal {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

/* Initial state: everything invisible (before .play) — NO !important so animation can override */
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
.chart-body-1x1 .pie-svg,
.chart-body-1x1 .sb-bar,
.chart-body-1x1 .dumbbell-line,
.chart-body-1x1 .dumbbell-dot,
.chart-body-1x1 .dumbbell-tag,
.chart-body-1x1 .tc-bg,
.chart-body-1x1 .sc6-row,
.chart-body-1x1 .sc6-line-dashed,
.chart-body-1x1 .db5-row{ opacity:0; }
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
body.play .chart-body-1x1 .pie-svg{
  animation: pieSweep 1.2s ease-out 1.2s forwards !important;
  -webkit-mask: conic-gradient(from -90deg, white 0deg, white var(--pie-reveal), transparent var(--pie-reveal), transparent 360deg);
  mask: conic-gradient(from -90deg, white 0deg, white var(--pie-reveal), transparent var(--pie-reveal), transparent 360deg);
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

def add_animations_to_html(html_content):
    return html_content.replace("</head>", ANIMATION_CSS + "\n</head>", 1)

def main():
    htmls = sorted(glob.glob(os.path.join(ROUND22, "*-styled.html")))
    total = 0
    for html_path in htmls:
        name = os.path.basename(html_path)
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        animated = add_animations_to_html(html)
        out_path = os.path.join(OUT_DIR, name)
        pathlib.Path(out_path).write_text(animated, encoding="utf-8")
        total += 1
    print(f"Generated {total} animated HTML files to {OUT_DIR}")

if __name__ == "__main__":
    main()
