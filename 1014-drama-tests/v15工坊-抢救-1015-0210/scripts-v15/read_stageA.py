#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读v15-stageA.docx结构，看上次会话做到哪了"""
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

tbl_idx = 0
paras = []
for block in iter_block_items(doc):
    if isinstance(block, Paragraph):
        t = block.text.strip()
        if t:
            paras.append(t)
    else:
        tbl_idx += 1
        rows = len(block.rows)
        cols = len(block.columns)
        first_cells = [c.text.strip().replace('\n', ' ')[:22] for c in block.rows[0].cells]
        print(f">>> 表{tbl_idx} ({rows}x{cols}): {' | '.join(first_cells[:6])}")

print(f"\n共 {len(paras)} 段正文段落。前25段：")
for i, p in enumerate(paras[:25]):
    print(f"{i}: {p[:70]}")
print("\n后20段：")
for i, p in enumerate(paras[-20:]):
    print(f"{len(paras)-20+i}: {p[:70]}")

# 检查是否有【】批注残留
import re
annos = []
for i, p in enumerate(paras):
    for m in re.finditer(r'【[^】]*】', p):
        annos.append((i, m.group(0)[:50]))
print(f"\n【】残留 {len(annos)} 处：")
for i, a in annos[:40]:
    print(f"  段{i}: {a}")
