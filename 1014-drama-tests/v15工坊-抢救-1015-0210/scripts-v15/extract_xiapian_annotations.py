#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取下篇docx全文结构 + 【】批注（带上下文）"""
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

doc = Document('/home/z/my-project/materials/下篇-1014-0100/下篇.docx')

def iter_block_items(parent):
    from docx.oxml.ns import qn
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)

out = []
annos = []
tbl_idx = 0
for block in iter_block_items(doc):
    if isinstance(block, Paragraph):
        t = block.text.strip()
        if not t:
            continue
        style = block.style.name if block.style else ''
        # 检查是否含批注
        if '【' in t:
            # 找出所有批注段
            for m in re.finditer(r'【[^】]*】', t):
                annos.append(m.group(0))
        out.append(('P', style, t))
    else:
        tbl_idx += 1
        rows = len(block.rows)
        cols = len(block.columns)
        # 表格标题用第一行拼接
        first_cells = [c.text.strip().replace('\n', ' ') for c in block.rows[0].cells]
        # 表内批注
        tbl_annos = []
        for ri, row in enumerate(block.rows):
            for ci, cell in enumerate(row.cells):
                ct = cell.text
                for m in re.finditer(r'【[^】]*】', ct):
                    tbl_annos.append((ri, ci, m.group(0)))
        header = ' | '.join(first_cells[:8])
        out.append(('T', f'表{tbl_idx}({rows}x{cols})', header))
        if tbl_annos:
            for (ri, ci, a) in tbl_annos:
                annos.append(f'[表{tbl_idx} r{ri}c{ci}] {a}')

print("=" * 80)
print("文档结构概览：")
for kind, style, text in out:
    if kind == 'T':
        print(f"  [表格] {style}: {text[:100]}")
    else:
        if 'Heading' in style or 'heading' in style or '标题' in style:
            print(f"  [{style}] {text[:80]}")
        else:
            print(f"  [P] {text[:60]}")

print()
print("=" * 80)
print(f"共发现 {len(annos)} 处【】批注：")
print("=" * 80)
for i, a in enumerate(annos, 1):
    print(f"{i}. {a}")
