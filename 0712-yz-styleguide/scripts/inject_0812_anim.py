#!/usr/bin/env python3
"""Inject animation CSS into all round2 HTML → round3 HTML."""
import os, glob, pathlib, shutil

ROUND2 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/round2"
ROUND3 = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/round3"
os.makedirs(ROUND3, exist_ok=True)

ANIMATION_CSS = """
<style data-purpose="round3-animations">
@property --pie-reveal { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
.chart-logo-1x1, .chart-title-1x1, .chart-source-1x1, .chart-part-num,
.chart-body-1x1 .chart-legend,
.chart-body-1x1 .data-table-1x1,
.chart-body-1x1 svg { opacity:0; }
.chart-body-1x1 .data-table-1x1 tbody tr { opacity:0; }
.chart-logo-1x1{ animation: fadeIn 1.2s ease-out 0s forwards; }
.chart-title-1x1{ animation: fadeIn 1.2s ease-out 1.5s forwards; }
.chart-source-1x1{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-part-num{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-body-1x1 .chart-legend{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-body-1x1 svg{ animation: fadeIn 1.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1{ animation: fadeIn 1.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1 thead{ animation: fadeIn 0.6s ease-out 4.5s forwards; opacity:0; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(1){ animation: rowFade 0.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(2){ animation: rowFade 0.5s ease-out 4.8s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(3){ animation: rowFade 0.5s ease-out 5.1s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(4){ animation: rowFade 0.5s ease-out 5.4s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(5){ animation: rowFade 0.5s ease-out 5.7s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(6){ animation: rowFade 0.5s ease-out 6.0s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(7){ animation: rowFade 0.5s ease-out 6.3s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(8){ animation: rowFade 0.5s ease-out 6.6s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(9){ animation: rowFade 0.5s ease-out 6.9s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(10){ animation: rowFade 0.5s ease-out 7.2s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(11){ animation: rowFade 0.5s ease-out 7.5s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(12){ animation: rowFade 0.5s ease-out 7.8s forwards; }
@keyframes fadeIn{ to{ opacity:1; } }
@keyframes rowFade{ to{ opacity:1; } }
#yz-selfcheck-banner{ display:none !important; }
body{ background:#fff !important; padding:0 !important; margin:0 !important; }
</style>
"""

htmls = sorted(glob.glob(os.path.join(ROUND2, "*-styled.html")))
for html_path in htmls:
    name = os.path.basename(html_path)
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("</head>", ANIMATION_CSS + "\n</head>", 1)
    out_path = os.path.join(ROUND3, name)
    pathlib.Path(out_path).write_text(html, encoding="utf-8")
    print(f"  {name}")
print(f"\nTotal: {len(htmls)} animated HTML files in round3")
