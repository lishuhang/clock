#!/usr/bin/env python3
"""v15 stage A: 上篇修改（在v14上.docx基础上落实下篇批注引发的上篇联动修改）
1.标题6 18→17地区  2.万兴喵影导语句  3.剪辑表万兴行  4.表3六格  5.独家表(表6)小云雀/纳逗格  6.人无我有段替换
输出: /home/z/my-project/materials/下篇-1015/v15-stageA.docx
"""
import copy
import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches

SRC = '/home/z/my-project/materials/下篇-1015/v14上.docx'
OUT = '/home/z/my-project/materials/下篇-1015/v15-stageA.docx'
MEDIA = '/home/z/my-project/materials/下篇-1015/media/media'
d = docx.Document(SRC)
LOG = []

def get_rpr_tmpl(el):
    for r in el.iter(qn('w:r')):
        if r.find(qn('w:t')) is not None and (r.find(qn('w:t')).text or '').strip():
            rpr = r.find(qn('w:rPr'))
            return copy.deepcopy(rpr) if rpr is not None else None
    return None

def make_run(text, rpr_tmpl, highlight=False):
    r = OxmlElement('w:r')
    if rpr_tmpl is not None:
        r.append(copy.deepcopy(rpr_tmpl))
    if highlight:
        rpr = r.find(qn('w:rPr'))
        if rpr is None:
            rpr = OxmlElement('w:rPr'); r.insert(0, rpr)
        hl = OxmlElement('w:highlight'); hl.set(qn('w:val'), 'yellow')
        rpr.append(hl)
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text
    r.append(t)
    return r

def shade_cell(cell, fill='FFFF00'):
    tcPr = cell._tc.get_or_add_tcPr()
    for shd in tcPr.findall(qn('w:shd')):
        tcPr.remove(shd)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), fill)
    tcPr.append(shd)

def set_cell_text(cell, text, shade=False, rpr_tmpl=None):
    if rpr_tmpl is None:
        rpr_tmpl = get_rpr_tmpl(cell._tc)
    first = cell.paragraphs[0]
    for child in list(first._p):
        if child.tag != qn('w:pPr'):
            first._p.remove(child)
    first._p.append(make_run(text, rpr_tmpl))
    for p in cell.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    if shade:
        shade_cell(cell)

def cell_lines(cell, lines, shade=False):
    rpr_tmpl = get_rpr_tmpl(cell._tc)
    first = cell.paragraphs[0]
    pPr0 = first._p.find(qn('w:pPr'))
    for child in list(first._p):
        if child.tag != qn('w:pPr'):
            first._p.remove(child)
    first._p.append(make_run(lines[0], rpr_tmpl))
    prev = first._p
    for ln in lines[1:]:
        newp = OxmlElement('w:p')
        if pPr0 is not None:
            newp.append(copy.deepcopy(pPr0))
        newp.append(make_run(ln, rpr_tmpl))
        prev.addnext(newp); prev = newp
    if shade:
        shade_cell(cell)

def find_para(substr):
    for p in d.paragraphs:
        if substr in p.text:
            return p
    return None

def replace_para_runs(para, segments):
    """segments: [(text, highlight_bool)] 重建段落runs"""
    rpr_tmpl = get_rpr_tmpl(para._p)
    for child in list(para._p):
        if child.tag != qn('w:pPr'):
            para._p.remove(child)
    for txt, hl in segments:
        para._p.append(make_run(txt, rpr_tmpl, highlight=hl))

# ══════════ A1. 标题6: 18→17 ══════════
p6 = None
for p in d.paragraphs:
    if p.text.strip().startswith('6. 标题：一键出海18地区'):
        p6 = p; break
if p6 is not None:
    replace_para_runs(p6, [('6. 标题：一键出海17地区、6语种转绘，出海谁最强丨AI视频画布横评·功能篇　摘要：整部剧换国家重拍，转绘流水线卷起来', False)])
    LOG.append('A1 标题6: 18地区→17地区')

# ══════════ A2. 万兴喵影导语句 ══════════
p_wx = find_para('只能裁长短')
if p_wx is not None:
    # 原句: ...；[；有的联动自家剪辑工具，比如万兴剧厂联动喵影（只能裁长短）]{mark}；...
    # 新句按官方口径: 联动喵影（画布内只能裁长短，定稿视频与字幕可同步至万兴喵影客户端继续剪辑，后期修改双端同步）
    full = p_wx.text
    seg_fixed = '；有的联动自家剪辑工具，比如万兴剧厂联动喵影——画布内只能裁剪长短（实测），但定稿视频与字幕可以一键同步到万兴喵影客户端继续剪辑，缺素材无需本地导出，后期修改双端实时同步'
    # 找到黄色run(旧改动)整体替换
    rpr_tmpl = get_rpr_tmpl(p_wx._p)
    runs_info = [(r.text, r.font.highlight_color is not None) for r in p_wx.runs if r.text]
    # 重建: 保留非高亮部分原样, 高亮部分替换为新句(仍高亮)
    new_segs = []
    for txt, hl in runs_info:
        if hl:
            new_segs.append((seg_fixed, True))
        else:
            new_segs.append((txt, False))
    # 合并相邻同态
    merged = []
    for txt, hl in new_segs:
        if merged and merged[-1][1] == hl:
            merged[-1] = (merged[-1][0] + txt, hl)
        else:
            merged.append((txt, hl))
    replace_para_runs(p_wx, merged)
    LOG.append('A2 万兴喵影导语句: 按官方口径改写(联动/同步/双端)并高亮')

# ══════════ A3. 剪辑表(表5) 万兴行 ══════════
tbian = d.tables[5]
for r in tbian.rows:
    if r.cells[0].text.strip() == '万兴剧厂':
        set_cell_text(r.cells[1], '画布内剪辑只能裁长短（实测）+定稿同步至万兴喵影', shade=True)
        LOG.append('A3 剪辑表万兴行: →画布内只能裁长短+定稿同步至万兴喵影(黄)')
        break

# ══════════ A4. 表3(电商bingo) 六格更新 ══════════
t3 = d.tables[3]
UPD = {
  '小云雀': {2: '√ 重制转绘17地区（规模最大）', 4: '√ 团队版（团队席位10/20，画布实时协作、积分发放与回收、项目运营看板与排行榜）'},
  'Seko':   {4: '√ 团队会员（4/8/15席位）+企业会员（1对1VIP客服与课程培训）'},
  '万兴剧厂': {4: '√ 团队版三档（多账号创建角色、权限分级、灵活增购席位、积分按成员/分组管控、全链路监控，官方称多光标同屏）',
               5: '√ CLI公测版（Agent工具，导航含MCP & CLI）'},
  'OiiOii': {5: '√ OIIOII CLI（会员权益）'},
  'AniShort': {5: '√ CLI（官网公告正式上线）+3D导演台MCP'},
}
for r in t3.rows[1:]:
    plat = r.cells[0].text.strip()
    if plat in UPD:
        for ci, txt in UPD[plat].items():
            old = r.cells[ci].text
            set_cell_text(r.cells[ci], txt, shade=True)
            LOG.append(f'A4 表3 {plat}列{ci}: {old[:18]}…→ {txt[:34]}…(黄)')

# ══════════ A5. 独家表(表6) 更新 ══════════
t6 = d.tables[6]
for r in t6.rows[1:]:
    plat = r.cells[0].text.strip()
    if plat == '小云雀':
        cell_lines(r.cells[1], ['• 智能预演（多镜头统一规划分镜图降抽卡）', '• 自研剧本模型'], shade=True)
        set_cell_text(r.cells[2], '• 素模/图转白模、动作库、机位运镜库、帧级时间轴、轨迹/WASD走位等', shade=True)
        set_cell_text(r.cells[3], '重制转绘（17地区/单集5分钟/总100分钟/镜头1:1复刻）', shade=True)
        LOG.append('A5 独家表小云雀行: 漫剧+自研剧本模型/专业影视3D能力串/17地区(黄)')
    if plat == '纳逗Pro':
        # 专业影视列(第3列)含积分分成
        cell_lines(r.cells[2], ['• 6000+IP库+数字资产库（364角色图/168模型图/309视频/14个3D模型）',
                                 '• Skills定价上架、积分分成全部给到发布者'], shade=False)
        LOG.append('A5 独家表纳逗行: 积分分成→全部给到发布者(手册原词,不黄-用户草稿只差两字)')
# 18地区残余清理(表6若有)
for r in t6.rows:
    for c in r.cells:
        if '18地区' in c.text:
            set_cell_text(c, c.text.replace('18地区', '17地区'), shade=False)
            LOG.append('A5 独家表残余18地区→17')

# ══════════ A6. 人无我有段替换 + image1 ══════════
p_old = find_para('其中也有些独家功能本质上有共同点')
if p_old is not None:
    new_para_text = ('其中也有些独家功能本质上有共同点。小云雀智能预演是为了解决多镜头一致性的问题。它先让智能体替整组镜头'
                     '排好走位再生成，有助于减少抽卡次数。它家和万兴、AniShort等的3D白模、ShotLab、LibTV和OiiOii的逐帧拆解等'
                     '也是为了同样的减少抽卡的目的服务。小娱最近采访一位专业影视向超创，对方表示，3D白模是他使用画布最重要的功能之一。')
    rpr_tmpl = get_rpr_tmpl(p_old._p)
    pPr = p_old._p.find(qn('w:pPr'))
    for child in list(p_old._p):
        if child.tag != qn('w:pPr'):
            p_old._p.remove(child)
    p_old._p.append(make_run(new_para_text, rpr_tmpl))
    LOG.append('A6 人无我有段: 按批注整段替换(它家…/超创采访句)')

    # image1: 小云雀3D导演台 → 插在该段后、"OiiOii的Skill制造机"段前
    p_next = find_para('OiiOii的Skill制造机、纳逗Pro的Skill商店')
    anchor = p_next if p_next is not None else p_old
    # 图注段(插在图后)
    cap = OxmlElement('w:p')
    if pPr is not None: cap.append(copy.deepcopy(pPr))
    cap.append(make_run('小云雀的3D导演台', rpr_tmpl))
    # 图段
    img_p = OxmlElement('w:p')
    if pPr is not None: img_p.append(copy.deepcopy(pPr))
    anchor._p.addprevious(cap)
    anchor._p.addprevious(img_p)
    # 用python-docx API插不了到空XML段,改为: 在anchor前insert段落对象
    # 简便法: 新建段落再移动XML
    from docx.text.paragraph import Paragraph
    img_para = Paragraph(img_p, p_old._parent)
    run = img_para.add_run()
    run.add_picture(f'{MEDIA}/image1.png', width=Inches(5.73))
    LOG.append('A6 image1(小云雀3D导演台)已插入人无我有段后、Skill制造机段前,图注已加')

d.save(OUT)
print('\n'.join(LOG))
print('STAGE A OK ->', OUT)
