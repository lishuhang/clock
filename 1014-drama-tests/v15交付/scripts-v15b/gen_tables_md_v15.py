#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从v15成品docx提取11张表 → 功能篇表格定稿-v15 md（raw文字表格,与docx/信息图三方一致）"""
import glob
import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn as _qn

path = sorted(glob.glob('/home/z/my-project/materials/下篇-1015/漫剧智能体功能横评_功能篇_v15-*.docx'))[-1]
d = docx.Document(path)

def iter_blocks(doc):
    for c in doc.element.body.iterchildren():
        if c.tag == qn('w:p'): yield Paragraph(c, doc)
        elif c.tag == qn('w:tbl'): yield Table(c, doc)
tables = [b for b in iter_blocks(d) if isinstance(b, Table)]

def cell_md(cell):
    lines = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
    out = '<br>'.join(lines) if lines else '-'
    return out.replace('|', '\\|')

def is_shaded(cell):
    tcPr = cell._tc.find(qn('w:tcPr'))
    if tcPr is None: return False
    shd = tcPr.find(qn('w:shd'))
    return shd is not None and shd.get(qn('w:fill')) == 'FFFF00'

TITLES = [
    '表S 按用户画像分的各平台功能适配情况（总表）',
    '表1 漫剧连载类需求点',
    '表2 专业影视类需求点',
    '表3 电商出海类需求点',
    '表4 AI视频画布的"标配"',
    '表5 抽完后的剪辑动作',
    '表6 "人无我有"和独家功能',
    '表7 角色一致性及参考主体相关能力',
    '表8 剧本与分镜能力',
    '表9 团队协作能力',
    '表10 短剧出海转绘能力',
]
LEGENDS = {1: '√有 △有一部分/间接实现 ×没有', 2: '√有 △有一部分/间接实现 ×没有', 3: '√有 △有一部分/间接实现 ×没有',
           6: '注：有的功能可能面向多种人群，会被归类到它可能帮助最大的一群。'}
FOOT = '数据来源：娱乐资本论根据官方手册和实测整理，信息截至2026年10月5日，如与实际有差异，以实际呈现为准。'

md = []
md.append('# 功能篇表格定稿 v15（合并完整版）\n')
md.append('> 底稿：上篇v14-1015-0030 + 下篇线上版1014-0100批注34条全部落实')
md.append('> 事实口径：10-14/15实测与pricing页 > 实习生10-09实测 > 官方手册 > 网络资料；文中数据截至统一写死2026年10月5日（用户口径）')
md.append('> 排序：三类分表按√数降序→△数降序（并列字母序）；其余表按字母序：AniShort、巨日禄、LibTV、纳逗Pro、OiiOii、Seko、ShotLab、TapNow、万兴剧厂、小云雀')
md.append('> 名称规范：ShotLab（不写"新片场ShotLab"）、Seko（不写"商汤Seko"）、万兴剧厂（全称）')
md.append('> 🟡=docx中黄底/黄高亮（本轮修正处）；信息图不标黄\n')

yellow_total = 0
for i, (t, title) in enumerate(zip(tables, TITLES)):
    md.append(f'\n## {title}\n')
    if i in LEGENDS:
        md.append(LEGENDS[i] + '\n')
    hdr = [c.text.strip() for c in t.rows[0].cells]
    md.append('| ' + ' | '.join(hdr) + ' |')
    md.append('|' + '---|' * len(hdr))
    for r in t.rows[1:]:
        cells = []
        for c in r.cells:
            txt = cell_md(c)
            if is_shaded(c):
                txt = f'🟡{txt}'
                yellow_total += 1
            cells.append(txt)
        md.append('| ' + ' | '.join(cells) + ' |')
    md.append(f'\n{FOOT}')

md.append(f'\n\n黄底格合计：{yellow_total}（上篇StageA/FixA约20处+v15下篇新增处）\n')

out = '/home/z/my-project/download/v15交付/功能篇表格定稿-v15-1015-0303.md'
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(md))
print('表格定稿md ->', out, f'（11表,黄底{yellow_total}格）')
