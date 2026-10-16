#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""细看stageA表7（人无我有）内容+标题摘要+图注+批注7段落落实情况"""
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

doc = Document('/home/z/my-project/materials/下篇-1015/v15-stageA.docx')

def iter_block_items(parent):
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)

blocks = list(iter_block_items(doc))
tables = [b for b in blocks if isinstance(b, Table)]
paras = [b for b in blocks if isinstance(b, Paragraph)]

print("===== stageA 表7（人无我有）完整内容 =====")
t7 = tables[6]
for row in t7.rows:
    cells = [c.text.strip().replace('\n', ' / ') for c in row.cells]
    print(' || '.join(cells))
    print("-" * 60)

print("\n===== 标题摘要10对（检查17/18地区等）=====")
for p in paras[:12]:
    t = p.text.strip()
    if t:
        print(f"· {t[:110]}")

print("\n===== 图注段落（找'3D导演台'等）=====")
for p in paras:
    t = p.text.strip()
    if len(t) < 30 and t and ('的' in t and len(t) < 25):
        print(f"· {t}")

print("\n===== 段64-67（人无我有正文尾部）=====")
for p in paras:
    t = p.text.strip()
    if '其中也有些独家功能' in t or 'OiiOii的Skill制造机' in t or '根据我们的分类' in t:
        print(f"· {t}")
        print()

# 检查表7是否有高亮（黄色标记）
from docx.oxml.ns import qn as Q
print("\n===== stageA表7黄色高亮检查 =====")
hl_count = 0
for ri, row in enumerate(t7.rows):
    for ci, cell in enumerate(row.cells):
        for p in cell.paragraphs:
            for r in p.runs:
                if r.font.highlight_color is not None:
                    hl_count += 1
                    print(f"  r{ri}c{ci}: [highlight={r.font.highlight_color}] {r.text[:40]}")
print(f"共 {hl_count} 处高亮")
