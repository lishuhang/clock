#!/usr/bin/env python3
"""Build markdown doc for 0812-test images (step 1 deliverable)."""
import os, json, glob, pathlib

VLM_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/_vlm"
OUT = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/0812-images-as-tables.md"

ORDER = [2, 3, 4, 6, 7, 8, 10, 11, 12]

def load_vlm(idx):
    path = os.path.join(VLM_DIR, f"img{idx}.json")
    with open(path, encoding="utf-8") as f:
        outer = json.load(f)
    content = outer["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n",1)[1].rsplit("```",1)[0]
    return json.loads(content)

def md_table(headers, rows):
    if not headers: return "(无表格数据)"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"]*len(headers)) + "|")
    for r in rows:
        r2 = list(r) + [""]*(len(headers)-len(r))
        out.append("| " + " | ".join(str(c) for c in r2[:len(headers)]) + " |")
    return "\n".join(out)

lines = ["# 0812-test 配图数据还原与可视化说明\n",
         "> 数据来源：娱资原文 + VLM(GLM-5V) 对配图的逆向识别。\n"]

for i, idx in enumerate(ORDER, 1):
    d = load_vlm(idx)
    lines.append(f"\n---\n\n## 图 {i}（原图 img{idx}）：{d.get('title_text','')[:60]}\n")
    lines.append(f"**图表类型**：{d.get('chart_type','')}\n")
    lines.append(f"**核心摘要**：{d.get('image_summary','')}\n")
    if d.get('footer_text'):
        lines.append(f"**脚注**：{d['footer_text']}\n")
    if d.get('data_source_text'):
        lines.append(f"**数据来源**：{d['data_source_text']}\n")
    
    # Table
    td = d.get('table_data',{})
    if td.get('headers'):
        lines.append("\n### 数据表格\n")
        lines.append(md_table(td['headers'], td.get('rows',[])))
        lines.append("")
    
    # Series
    series = d.get('series',[])
    if series:
        lines.append("\n### 序列数据\n")
        for j, s in enumerate(series,1):
            lines.append(f"\n**序列 {j}：{s.get('name','')}**  颜色：{s.get('color','')}  含义：{s.get('meaning','')}")
            pts = s.get('data_points',[])
            if pts:
                lines.append("\n| 类目 | 数值 |\n|---|---|")
                for p in pts:
                    if isinstance(p, list) and len(p)>=2:
                        lines.append(f"| {p[0]} | {p[1]} |")
    
    # Color encoding
    ce = d.get('color_encoding',[])
    if ce:
        lines.append("\n### 颜色编码\n")
        lines.append("| 颜色 | 含义 |\n|---|---|")
        for c in ce:
            lines.append(f"| {c.get('color','')} | {c.get('meaning','')} |")
    
    # Viz spec
    lines.append("\n### 可视化还原说明\n")
    lines.append(d.get('visualization_spec','') + "\n")
    
    # Highlights
    hl = d.get('key_data_highlights',[])
    if hl:
        lines.append("\n### 关键数据点\n")
        for h in hl:
            lines.append(f"- {h}")
        lines.append("")

pathlib.Path(OUT).write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT} ({os.path.getsize(OUT)} bytes)")
