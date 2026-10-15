#!/usr/bin/env python3
"""v15 postcheck: 补丁4格措辞对齐草稿 + 合并版全面验收
验收项: 11表内容/23图/无批注残留/无SeeDance/无17地区/无旧名称/段落顺序/脚注×4/黄底分布
"""
import sys, glob
import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

path = sorted(glob.glob('/home/z/my-project/materials/下篇-1015/漫剧智能体功能横评_功能篇_v15-*.docx'))[-1]
d = docx.Document(path)
FAIL = []

# ═══ 补丁: 团队协作表4格措辞对齐草稿(非事实修正,不黄) ═══
t_team = d.tables[9]
PATCH = {  # (行平台, 列index): 新文本
    ('纳逗Pro', 1): '√ 最高100人同时在线',
    ('纳逗Pro', 3): '√ 成员积分配额+单期额度',
    ('纳逗Pro', 4): '√ 团队看板按成员/项目/工程三维度',
    ('ShotLab', 1): '√ 单画布最高5人同时在线制作',
}
def get_rpr(el):
    for r in el.iter(qn('w:r')):
        if r.find(qn('w:t')) is not None and (r.find(qn('w:t')).text or '').strip():
            rpr = r.find(qn('w:rPr'))
            import copy as _c
            return _c.deepcopy(rpr) if rpr is not None else None
    return None
from docx.oxml import OxmlElement
import copy
def set_cell(cell, text):
    rpr = get_rpr(cell._tc)
    first = cell.paragraphs[0]
    for child in list(first._p):
        if child.tag != qn('w:pPr'):
            first._p.remove(child)
    r = OxmlElement('w:r')
    if rpr is not None: r.append(copy.deepcopy(rpr))
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text
    r.append(t)
    first._p.append(r)
    for p in cell.paragraphs[1:]:
        p._p.getparent().remove(p._p)

patched = []
for row in t_team.rows[1:]:
    plat = row.cells[0].text.strip()
    for (pp, ci), txt in PATCH.items():
        if plat == pp and row.cells[ci].text.strip() != txt:
            set_cell(row.cells[ci], txt)
            patched.append(f'{pp}列{ci}→{txt[:18]}')
if patched:
    d.save(path)
    print('补丁:', '; '.join(patched))

# ═══ 验收 ═══
def iter_blocks(doc):
    for c in doc.element.body.iterchildren():
        if c.tag == qn('w:p'): yield Paragraph(c, doc)
        elif c.tag == qn('w:tbl'): yield Table(c, doc)

blocks = list(iter_blocks(d))
tables = [b for b in blocks if isinstance(b, Table)]
paras = [b for b in blocks if isinstance(b, Paragraph)]
full_text = '\n'.join(p.text for p in paras)
tbl_text = '\n'.join(c.text for t in tables for r in t.rows for c in r.cells)

# 1. 结构
print(f'表={len(tables)} 段={len(paras)} 图={len(d.inline_shapes)}')
if len(tables) != 11: FAIL.append(f'表数{len(tables)}≠11')
if len(d.inline_shapes) != 23: FAIL.append(f'图数{len(d.inline_shapes)}≠23')

# 2. 批注/旧错残留
for bad in ['【', '】', 'SeeDance', '17地区', '17种目标', '新片场ShotLab', '商汤Seko', '三制', '双限额取低', '每天/每月/固定', '10种宫格', '整体跟换', '项目管理界面']:
    if bad in full_text or bad in tbl_text:
        # 定位
        loc = [p.text[:60] for p in paras if bad in p.text][:2] or [f'{t.rows[0].cells[0].text}表' for t in tables for r in t.rows for c in r.cells if bad in c.text][:2]
        FAIL.append(f'残留[{bad}]: {loc}')

# 3. 18地区/Seedance正字
if '18地区' not in tbl_text: FAIL.append('表内无18地区')
if '18种目标地区' not in tbl_text: FAIL.append('表内无18种目标地区')

# 4. 关键新内容抽查
checks = [
    ('正文', '同类功能，各家实现得怎么样'),
    ('正文', '其他家手册未见角色层面的类似联动表述'),
    ('正文', '只能靠负向提示词控制'),
    ('正文', '基于Seedance特调'),
    ('正文', '纳逗Pro内置150个音色资产、LibTV内置300+专业音色'),
    ('正文', 'Seko还接入Mureka V9作曲模型生成BGM'),
    ('正文', '多轨混音'),
    ('正文', '、纳逗Pro和ShotLab'),
    ('正文', '纳逗Pro、LibTV、OiiOii、AniShort和万兴剧厂'),
    ('正文', '附：各家定价页截图'),
    ('正文', '图源：官方教程《智能预演体验指南》'),
    ('正文', 'Seedance 2.5模型'),
    ('表格', '十余种宫格设定图'),
    ('表格', '须名称完全一致，主体库更新后生效'),
    ('表格', '人像参考图需先过合规检测'),
    ('表格', '分镜脚本节点：输入剧情文本'),
    ('表格', 'Brainstorm创意开发'),
    ('表格', '团队版4档5/10/20/50席位'),
    ('表格', '画布实时协作（团队版权益）'),
    ('表格', '多光标同屏（官方宣传）'),
    ('表格', '高级/超级团队会员'),
    ('表格', 'MCP&CLI（CLI公测版）'),
    ('表格', 'TEAM LITE/PLUS/PRO/MAX'),
    ('表格', '年度积分包（72000/120000/192000积分）'),
]
for where, key in checks:
    hay = full_text if where == '正文' else tbl_text
    if key not in hay:
        FAIL.append(f'缺[{where}]: {key}')

# 5. 表9团队协作表逐行首列+多人同屏列
t9 = tables[9]
print('表9平台序:', ' '.join(r.cells[0].text.strip() for r in t9.rows[1:]))
expect_order = ['AniShort', '巨日禄', 'LibTV', '纳逗Pro', 'OiiOii', 'Seko', 'ShotLab', 'TapNow', '万兴剧厂', '小云雀']
got_order = [r.cells[0].text.strip() for r in t9.rows[1:]]
if got_order != expect_order: FAIL.append(f'表9顺序错: {got_order}')

# 6. 表11出海转绘顺序
t11 = tables[10]
got = [r.cells[0].text.strip() for r in t11.rows[1:]]
print('表11平台序:', ' '.join(got))
if got != ['AniShort', '巨日禄', 'OiiOii', 'Seko', '万兴剧厂', '小云雀']: FAIL.append(f'表11顺序错: {got}')

# 7. 脚注计数(全表11张+上篇原有)
foot_cnt = sum(1 for p in paras if p.text.startswith('数据来源'))
print(f'脚注数={foot_cnt}')
if foot_cnt < 11: FAIL.append(f'脚注数{foot_cnt}<11')

# 8. 附录12图注
caps = [p.text for p in paras if any(k in p.text for k in ['定价页', '订阅页', '充值页', '企业版页'])]
print(f'附录图注数={len(caps)}')
if len(caps) < 12: FAIL.append(f'附录图注不足: {len(caps)}')

print('\n===== 结果 =====')
if FAIL:
    print(f'✗ {len(FAIL)}项未过:')
    for f in FAIL: print(' -', f)
    sys.exit(1)
print('✓ 全部通过 ->', path)
