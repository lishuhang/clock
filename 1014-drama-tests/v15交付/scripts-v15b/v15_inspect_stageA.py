#!/usr/bin/env python3
"""检查v15-stageA.docx现状：表S电商列/表3/标题6/独家表/喵影句/剪辑表万兴行/人无我有段"""
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

doc = docx.Document('/home/z/my-project/materials/下篇-1015/v15-stageA.docx')

def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, doc)
        elif child.tag == qn('w:tbl'):
            yield Table(child, doc)

blocks = list(iter_blocks(doc))
tables = [b for b in blocks if isinstance(b, Table)]
paras = [b for b in blocks if isinstance(b, Paragraph)]

print(f"表格数={len(tables)} 段落数={len(paras)}")
for i, t in enumerate(tables):
    print(f"\n===== 表{i+1} ({len(t.rows)}行×{len(t.columns)}列) =====")
    # 打印表头行
    hdr = [c.text.replace('\n', '/')[:14] for c in t.rows[0].cells]
    print("表头:", " | ".join(hdr))
    if i == 0:  # 表S 全部打印
        for r in t.rows:
            print("  ", " | ".join(c.text.strip() for c in r.cells))
    elif len(tables) > 3 and t is tables[3]:  # 表4(电商出海类需求点) 假设
        for r in t.rows:
            print("  ", " | ".join(c.text.replace('\n', '/')[:38] for c in r.cells))

print("\n===== 关键段落检索 =====")
for i, p in enumerate(paras):
    t = p.text
    if ('17地区' in t or '18地区' in t or '18种' in t or '17种' in t):
        print(f"[地区] 段{i}: {t[:80]}")
    if '喵影' in t:
        print(f"[喵影] 段{i}: {t[:100]}")
    if '3D白模' in t and '共同点' in t:
        print(f"[人无我有段] 段{i}: {t[:80]}...{t[-60:]}")
    if '只能裁长短' in t:
        print(f"[剪辑万兴] 段{i}: {t[:60]}")
    if t.strip().startswith('6. 标题'):
        print(f"[标题6] 段{i}: {t[:60]}")

# 表3(电商需求点)与表S判断：打印所有表的第一列前两行来定位
print("\n===== 表定位 =====")
for i, t in enumerate(tables):
    c00 = t.rows[0].cells[0].text.strip()[:10]
    c10 = t.rows[1].cells[0].text.strip()[:10] if len(t.rows) > 1 else ''
    c11 = t.rows[1].cells[1].text.strip()[:22] if len(t.rows) > 1 and len(t.columns) > 1 else ''
    print(f"表{i+1}: [{c00}] 行1=[{c10}|{c11}]")
