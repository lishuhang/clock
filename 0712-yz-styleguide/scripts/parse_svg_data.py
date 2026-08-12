#!/usr/bin/env python3
"""Parse SVG to extract precise data values."""
import re

svg = open("/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/04b-release-vs-recent-gender-mobile.svg", encoding="utf-8").read()

# Extract film names
film_texts = re.findall(r'font-size="19"[^>]*>\s*(\d{4})\s+(.+?)</text>', svg)
print("=== Films ===")
for year, name in film_texts:
    print(f"  {year} {name}")

# Extract data rows: "X.X%→Y.Y%  +Z.Zpp" pattern
data_pattern = r'(\d+\.?\d*)%→(\d+\.?\d*)%\s+([+-]?\d+\.?\d*)pp'
matches = re.findall(data_pattern, svg)
print(f"\n=== Data ({len(matches)} matches) ===")
films = [name for _, name in film_texts]
for i, film in enumerate(films):
    if i*3+2 < len(matches):
        f1 = matches[i*3]     # 专业能力
        f3 = matches[i*3+1]   # 民族国家
        f5 = matches[i*3+2]   # 性别宽口径
        print(f"  {film}: F1={f1[0]}→{f1[1]} F3={f3[0]}→{f3[1]} F5={f5[0]}→{f5[1]}")

# Colors from SVG
print("\n=== Colors ===")
print("  F1 专业能力: #17324D (dark blue)")
print("  F3 民族国家: #D94B3D (red)")
print("  F5 性别宽口径: #C97B8D (pink)")
