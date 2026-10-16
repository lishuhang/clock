#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读上篇v14 docx结构（章节+表格标题），确定切分点"""
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

doc = Document('/home/z/my-project/download/漫剧智能体功能横评_功能篇_上_v14-1015-0030.docx')

def iter_block_items(parent):
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)

tbl_idx = 0
n_para = 0
for block in iter_block_items(doc):
    if isinstance(block, Paragraph):
        t = block.text.strip()
        if not t:
            continue
        n_para += 1
        style = block.style.name if block.style else ''
        if 'Heading' in style or '标题' in style:
            print(f"[{style}] {t}")
    else:
        tbl_idx += 1
        rows = len(block.rows)
        cols = len(block.columns)
        first_cells = [c.text.strip().replace('\n', ' ')[:30] for c in block.rows[0].cells]
        print(f"    >>> 表{tbl_idx} ({rows}x{cols}): {' | '.join(first_cells[:6])}")
print(f"\n共 {n_para} 段正文，{tbl_idx} 张表")
