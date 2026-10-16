#!/usr/bin/env python3
"""v15 build B: 在v15-stageA2.docx基础上追加下篇全部内容 → v15合并完整版
方法: 从下.docx克隆段落/表格XML模板(样式结构严格依从原文), 内容按批注+裁决清单重写
内容: 同类功能节 | 角色一致性表 | 主体库段 | 剧本分镜表(补3家) | ScriptBird段 | 智能预演图 |
     声音段(事实核查4段) | 团队协作表(全表重做) | 同屏/CLI段 | 出海转绘表 | 收尾 | 附:pricing12图
"""
import copy
import docx
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches
from docx.text.paragraph import Paragraph
from docx.table import Table
from datetime import datetime

BASE = '/home/z/my-project/materials/下篇-1015'
SRC_A = f'{BASE}/v15-stageA2.docx'
SRC_XIA = f'{BASE}/下.docx'
MEDIA = f'{BASE}/media/media'
TS = datetime.now().strftime('%m%d-%H%M')
OUT = f'{BASE}/漫剧智能体功能横评_功能篇_v15-{TS}.docx'

dst = Document(SRC_A)
src = Document(SRC_XIA)
LOG = []

# ───────── 通用helpers ─────────
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

# ───────── 从下.docx取模板 ─────────
def find_src_para(substr, exact=False):
    for p in src.paragraphs:
        if (exact and p.text.strip() == substr) or (not exact and substr in p.text):
            return p
    return None

tmpl_bold = find_src_para('同类功能，各家实现得怎么样', exact=True)   # 加粗节标题
tmpl_body = find_src_para('做漫剧最怕')                                # 正文段
tmpl_title = find_src_para('角色一致性及参考主体相关能力', exact=True) # 表标题
tmpl_foot = find_src_para('数据来源')                                  # 表脚注
tmpl_cap = find_src_para('在TapNow画布新建主体', exact=True)           # 图注
assert all(x is not None for x in (tmpl_bold, tmpl_body, tmpl_title, tmpl_foot, tmpl_cap)), '模板缺失'

# 表格模板定位
tbl_role = tbl_script = tbl_team = tbl_oversea = None
for t in src.tables:
    hdr = [c.text.strip() for c in t.rows[0].cells]
    all_txt = ''.join(c.text for r in t.rows for c in r.cells)
    if hdr[:2] == ['平台', '能力'] and 'ScriptBird' in all_txt:
        tbl_script = t
    elif hdr[:2] == ['平台', '能力'] and '宫格' in all_txt:
        tbl_role = t
    elif hdr[:2] == ['平台', '多人同屏']:
        tbl_team = t
    elif hdr[:2] == ['平台', '转绘模式']:
        tbl_oversea = t
assert all(x is not None for x in (tbl_role, tbl_script, tbl_team, tbl_oversea)), '表格模板缺失'
LOG.append(f'模板定位: 角色一致性{len(tbl_role.rows)}行 剧本{len(tbl_script.rows)}行 团队{len(tbl_team.rows)}行x{len(tbl_team.columns)}列 出海{len(tbl_oversea.rows)}行')

# ───────── 元素工厂 ─────────
def para_from(tmpl_p, segments, rpr=None):
    """克隆模板段落XML,保留pPr(格式),重建runs"""
    p = copy.deepcopy(tmpl_p._p)
    for child in list(p):
        if child.tag != qn('w:pPr'):
            p.remove(child)
    rr = rpr if rpr is not None else get_rpr_tmpl(tmpl_p._p)
    for txt, hl in segments:
        p.append(make_run(txt, rr, highlight=hl))
    return p

def image_para(tmpl_p, path, w_in):
    p = copy.deepcopy(tmpl_p._p)
    for child in list(p):
        if child.tag != qn('w:pPr'):
            p.remove(child)
    para = Paragraph(p, dst._body)
    run = para.add_run()
    run.add_picture(path, width=Inches(w_in))
    return p

def clone_p(src_para):
    return copy.deepcopy(src_para._p)

def clone_tbl(src_tbl):
    return copy.deepcopy(src_tbl._tbl)

# ───────── 组装元素序列 ─────────
E = []  # 待追加的XML元素
rpr_body = get_rpr_tmpl(tmpl_body._p)
rpr_cap = get_rpr_tmpl(tmpl_cap._p)
rpr_bold = get_rpr_tmpl(tmpl_bold._p)

def P(segments, tmpl=tmpl_body, rpr=None):
    E.append(para_from(tmpl, segments, rpr))

def PCLONE(src_para):
    E.append(clone_p(src_para))

def IMG(name, w_in):
    E.append(image_para(tmpl_body, f'{MEDIA}/{name}', w_in))

def CAP(text):
    E.append(para_from(tmpl_cap, [(text, False)], rpr_cap))

# ═══ 1. 节标题 + 引入 ═══
E.append(clone_p(tmpl_bold))
PCLONE(tmpl_body)  # 做漫剧最怕…

# ═══ 2. 角色一致性表 ═══
PCLONE(tmpl_title)
E.append(clone_tbl(tbl_role))
PCLONE(tmpl_foot)
IMG('image2.png', 5.758)
CAP('在TapNow画布新建主体')

# ═══ 3. 主体库段(改写,回答【其他家就没有吗？】) ═══
P([
 ('小云雀的角色资料库支持改动后、该角色出场的剧集画面和声音一键同步更新，AniShort替换设定图后主体库也会更新生效（注意名字必须一字不差才能准确联动），这是主体库能力中比较重要的一点。', False),
 ('其他家手册未见角色层面的类似联动表述——LibTV脚本节点的"同步更新"只联动提示词，万兴剧厂的资产库重在批量生成，都不等于改动角色后全剧集自动更新。', True),
 ('也有平台用模型能力或者智能体能力来做主体库，代表是ShotLab的人像锁定算法。', False),
])
IMG('image3.png', 5.760)
CAP('小云雀重制转绘的资产库')

# ═══ 4. 剧本与分镜表 ═══
PCLONE(find_src_para('几乎每家都在喊'))
PCLONE(tmpl_title)  # 占位: 稍后替换为"剧本与分镜能力"标题
E[-1] = para_from(tmpl_title, [('剧本与分镜能力', False)], get_rpr_tmpl(tmpl_title._p))
E.append(clone_tbl(tbl_script))
PCLONE(tmpl_foot)
IMG('image4.png', 5.761)
CAP('小云雀剧本助手')
PCLONE(find_src_para('小云雀将底层联手资深编剧打磨'))
PCLONE(find_src_para('在拆分镜时，纳逗Pro和万兴剧厂'))
IMG('image5.png', 5.765)
CAP('小云雀智能预演（图源：官方教程《智能预演体验指南》：xyq.jianying.com/tutorials/short-drama-agent-smart-preview）')

# ═══ 5. 声音段(事实核查改写,4段) ═══
P([
 ('如果你更习惯最后自己剪辑、配音、配乐，那就需要生成时音画分离，特别是最好能人声和背景音分离。比如用小云雀S2.5生成时想只要画面不要声音，', False),
 ('只能靠负向提示词控制（它家没有静音开关）', True),
 ('，问题是日后还得单独配角色对白。', False),
])
P([
 ('根据手册说明，巨日禄的星光模型', False),
 ('基于Seedance特调', True),
 ('，只支持音画同出，仅支持角色绑定音频文件后的独立音频生成。其他家', False),
 ('大多', True),
 ('可以用模型能力、提示词或者手动开关控制声音', False),
 ('（OiiOii手册未提及）', True),
 ('。TapNow的Wan3.0/FLUX3生成可关声音，MiniMax H3原生音频不可关。Seko的视频/音频分两步生成。', False),
])
P([
 ('在单独生成音频方面，各家基本都支持音乐、音效和对白的单独或组合生成，其中', False),
 ('纳逗Pro内置150个音色资产、LibTV内置300+专业音色', True),
 ('；', False),
 ('Seko还接入Mureka V9作曲模型生成BGM', True),
 ('。', False),
])
P([
 ('LibTV、纳逗Pro、AniShort明确支持成片的人声和背景音分离，ShotLab支持', False),
 ('多轨混音', True),
 ('，小云雀可实现', False),
 ('角色资料库改动后、该角色出场剧集画面和声音的一键同步更新', True),
 ('。甚至，纳逗Pro还在说明书中', False),
 ('提及了口型与配音的配合问题，建议在全片粗剪之后单独处理', True),
 ('。', False),
])

# ═══ 6. 团队协作表 ═══
E.append(para_from(tmpl_title, [('团队协作能力', False)], get_rpr_tmpl(tmpl_title._p)))
E.append(clone_tbl(tbl_team))
PCLONE(tmpl_foot)

# ═══ 7. 同屏段/CLI段 ═══
P([
 ('对于团队合作而言，最直观的做法是多人的光标可以在同一块画布上实时共同移动，TapNow', False),
 ('、纳逗Pro和ShotLab', True),
 ('都做到了这一点。其中纳逗Pro支持100人同画布、', False),
 ('按成员/项目/工程三维度的团队看板', True),
 ('、积分配额、跨团队克隆等。', False),
])
P([
 ('对于有开发能力的团队，能用CLI命令行工具、Skill化或者MCP化是', False),
 ('纳逗Pro、LibTV、OiiOii、AniShort和万兴剧厂', True),
 ('的特殊能力，它们让画布有机会接上Claude Code等AI智能体来做更多有趣的事情。TapNow', False),
 ('虽然不走CLI路线，但', True),
 ('称自己的画布是"操作系统"，名为Creative OS，向上接飞书/Slack/Notion，向下通过MCP被Claude、ChatGPT调用，官方插件已经上架豆包工作、千问办公和WorkBuddy。', False),
])
IMG('image18.png', 5.753)
CAP('巨日禄的表单式工作台')
PCLONE(find_src_para('AniShort的团队管理看板'))

# ═══ 8. 出海转绘表 ═══
PCLONE(find_src_para('最后，下面几个平台针对电商素材'))
E.append(para_from(tmpl_title, [('短剧出海转绘能力', False)], get_rpr_tmpl(tmpl_title._p)))
E.append(clone_tbl(tbl_oversea))
PCLONE(tmpl_foot)
IMG('image19.png', 5.753)
CAP('万兴剧厂的AI广告剧生成向导')
PCLONE(find_src_para('小云雀重制转绘是很'))
PCLONE(find_src_para('综合来看，如果你使用画布的类型不同'))
P([
 ('在下一篇，小娱将带大家看一下各个平台使用同样的', False),
 ('Seedance', True),
 (' 2.5模型，做同样提示词、同样参数的视频，结果会不会有不一样。请继续关注娱乐资本论后续相关报道。', False),
])

# ═══ 9. 附录: pricing 12图 ═══
E.append(para_from(tmpl_bold, [('附：各家定价页截图（供参考，非正文内容）', False)], rpr_bold))
APPENDIX = [
    ('image6.png', 5.765, 'Seko订阅页（团队标准/高级/至尊会员+企业会员）'),
    ('image7.png', 5.758, '万兴剧厂定价页（团队版三档）'),
    ('image8.png', 5.765, '小云雀团队版定价页（一）'),
    ('image9.png', 5.751, '小云雀团队版定价页（二）'),
    ('image10.png', 5.765, 'LibTV团队会员定价页（一）'),
    ('image11.png', 5.765, 'LibTV团队会员定价页（二）'),
    ('image12.png', 5.765, 'LibTV个人版定价页（一）'),
    ('image13.png', 5.765, 'LibTV个人版定价页（二）'),
    ('image14.png', 5.765, 'AniShort充值页（团队版档位）'),
    ('image15.png', 5.765, 'TapNow企业版页'),
    ('image16.png', 5.765, 'OiiOii团队版定价页（TEAM LITE/PLUS/PRO/MAX）'),
    ('image17.png', 5.766, 'OiiOii订阅权益页'),
]
for name, w, cap in APPENDIX:
    IMG(name, w)
    CAP(cap)

# ───────── 追加到stageA2末尾 ═══
anchor = None
for p in dst.paragraphs:
    if p.text.startswith('根据我们的分类'):
        anchor = p
        break
assert anchor is not None, '未找到上篇结尾锚点段'
cur = anchor._p
for el in E:
    cur.addnext(el)
    cur = el
LOG.append(f'已追加{len(E)}个元素(段落/表格/图片)')

d2 = dst  # 便于阅读
NEW_TABLE_START = 7  # 0-6为原上篇表, 7=角色一致性 8=剧本 9=团队 10=出海

# ═══ 填充: 角色一致性表(tables[7]) ═══
t_role = d2.tables[NEW_TABLE_START]
ROLE = [
    ('AniShort', '智能连线：@主体名与设定图名匹配自动连线；设定图替换须名称完全一致，主体库更新后生效', True),
    ('巨日禄', '在教程中提供成手向融图经验，如纯白底+多视图+先融图再图生视频', True),
    ('LibTV', '主体库+AutoLink：多图或单段视频建主体；上传5-30秒音频，自动生成人物音色', False),
    ('纳逗Pro', '用十余种宫格设定图（全身/脸部三视图、表情九宫格、场景氛围四宫格等）构建主体模块，且拥有6000+IP库、150音色', True),
    ('OiiOii', '角色设计师Agent；剧本→角色主图→资产库；另有演员库', False),
    ('Seko', '视频生成前智能推荐角色/场景/道具参考图', False),
    ('ShotLab', '模型层特征库：人像锁定算法，从视频提取人物特征（人像参考图需先过合规检测）', True),
    ('TapNow', '主体库：一组图/视频/音频打包复用', False),
    ('万兴剧厂', '广告剧流程内批量生成资产', False),
    ('小云雀', '角色节点：一处更新，全链路自动生效', False),
]
rpr_role = get_rpr_tmpl(t_role.rows[1].cells[1]._tc)
for i, (plat, txt, hl) in enumerate(ROLE):
    row = t_role.rows[i + 1]
    set_cell_text(row.cells[0], plat, shade=('ShotLab' in plat or plat == 'Seko'))  # 名称规范黄
    set_cell_text(row.cells[1], txt, shade=hl, rpr_tmpl=rpr_role)
LOG.append('角色一致性表: 10行重写(纳逗十余种/AniShort联动句/ShotLab合规前置/巨日禄typo/名称规范 黄)')

# ═══ 填充: 剧本分镜表(tables[8]) ═══
t_scr = d2.tables[NEW_TABLE_START + 1]
SCRIPT = [
    ('AniShort', '剧本框架创作教程（学院实战精讲：剧本创意人物设定/剧本框架/从框架到完整剧本）+优化情节、智能分段', True),
    ('巨日禄', '剧本优化师Agent+"本入剧出"直接扔小说', False),
    ('LibTV', '脚本节点，拆解向非创作向；25宫格连贯分镜+宫格切分', False),
    ('纳逗Pro', '剧本空间：评估4品类+IP速读+人物情感关系图+故事银行，"先诊断、再创作"；分镜卡片标注丰富信息、时间轴预览分镜序列', False),
    ('OiiOii', '超5000字长剧本自动激活智能分集；多宫格视图+手搓提示词双模式分镜', False),
    ('Seko', '多剧集续作两种方式+编剧类Skill；分镜表投画布节点+两种修改方式', True),
    ('ShotLab', '分镜脚本节点：输入剧情文本一键生成标准化分镜脚本+批量生成分镜图像与视频素材；场鸽智能体把引用视频按镜头拆解成结构化分镜表', True),
    ('TapNow', 'Brainstorm创意开发：对话发展剧本/角色/世界观/广告方案，成果整理成剧本、分镜、HTML页面或Pitch Deck；应用市场"分镜预演"把剧本拆成可预演的镜头/动作/节奏/转场', True),
    ('万兴剧厂', '分镜参数透明', False),
    ('小云雀', '自研模型ScriptBird、三阶段剧本定稿、专业热点库等；分镜时可智能预演', False),
]
rpr_scr = get_rpr_tmpl(t_scr.rows[0].cells[1]._tc) or get_rpr_tmpl(t_scr.rows[6].cells[1]._tc)
for i, (plat, txt, hl) in enumerate(SCRIPT):
    row = t_scr.rows[i + 1]
    set_cell_text(row.cells[0], plat, shade=False)
    set_cell_text(row.cells[1], txt, shade=hl, rpr_tmpl=rpr_scr)
LOG.append('剧本分镜表: 10行重写(补ShotLab/TapNow/AniShort三行+Seko两种 黄)')

# ═══ 填充: 团队协作表(tables[9]) ═══
t_team = d2.tables[NEW_TABLE_START + 2]
TEAM = [  # (多人同屏, 席位, 积分, 看板, CLI) — None=不变内容沿用克隆值
    ('AniShort', ['√ 多人同屏梳理脚本、分镜与资产（官方首页）', '√ 团队版4档5/10/20/50席位', '√ 团队积分管控功能全量开放', None, '√ AniShort CLI（正式上线）+3D导演台MCP']),
    ('巨日禄',   [None, '√ 二级账户（拆子团队/项目独立核算）', '△ 子团队/项目独立核算', None, None]),
    ('LibTV',    ['√ 多人画布协作+多人故事板协作（团队会员权益）', '√ 团队席位管理（高级/超级团队会员；20人以上企业采购咨询）', '√ 积分灵活分配+充值折扣', None, '√ Plugin/CLI（接Claude Code等Agent）']),
    ('纳逗Pro',  [None, '△ 团队/个人双空间（个人付费后可创建团队，未见专门团队版付费）', None, None, '√ CLI命令行工具（批量自动化）']),
    ('OiiOii',   [None, '√ 20子账号+小组制（团队版TEAM LITE/PLUS/PRO/MAX，最多5/10/20/不限个小组）', '√ 子账号月积分限额+小组项目积分限额', None, '√ OIIOII CLI（会员权益）']),
    ('Seko',     [None, '√ 团队标准/高级/至尊会员4/8/15席位+企业会员定制席位', '√ 年度积分包（72000/120000/192000积分）+热门模型时长额度', '△ 团队与权限管理（订阅页权益项）', None]),
    ('ShotLab',  [None, '△ 手机号添加协作者（可编辑/仅查看/管理者）', None, None, None]),
    ('TapNow',   [None, '√ 3角色+SSO；企业版Custom定制套餐', '√ 无限额度/订阅/散充', '△ 成员使用量；企业版按天/周/月精细化管控', '×（MCP被Claude/ChatGPT调用）']),
    ('万兴剧厂', ['√ 多光标同屏（官方宣传）', '√ 团队版三档（入门/专业/企业）：多账号创建角色+灵活增购席位+权限分级', '√ 积分用量按成员/分组精细化管控', '√ 全链路监控数据+团队管理', '√ MCP&CLI（CLI公测版）']),
    ('小云雀',   ['√ 画布实时协作（团队版权益）', '√ 团队版4档：10-20席位（体验/基础/进阶/豪华）', '√ 积分发放与回收', '√ 项目运营看板与排行榜', None]),
]
rpr_team = get_rpr_tmpl(t_team.rows[1].cells[1]._tc)
for i, (plat, cells) in enumerate(TEAM):
    row = t_team.rows[i + 1]
    set_cell_text(row.cells[0], plat, shade=False)
    for ci, val in enumerate(cells):
        if val is None:
            # None=克隆原表中该格内容已是正确值(ShotLab多人同屏/纳逗多人同屏等),仅确认非空
            if not row.cells[ci + 1].text.strip():
                set_cell_text(row.cells[ci + 1], '×', shade=False, rpr_tmpl=rpr_team)
        else:
            set_cell_text(row.cells[ci + 1], val, shade=True, rpr_tmpl=rpr_team)
LOG.append('团队协作表: 10行×5列重做(变化格黄底,不变格沿用克隆原文)')

# ═══ 填充: 出海转绘表(tables[10]) ═══
t_ov = d2.tables[NEW_TABLE_START + 3]
OVERSEA = [
    ('AniShort', ['短剧出海专用转绘', '语言/人种/风格一键切换', '比例跟原片相同', '非人类角色可选保留+台词翻译+重配音']),
    ('巨日禄', ['"一键转绘"', '-', '-', '详情需要向商务咨询']),
    ('OiiOii', ['一键出海（转角色/转语言/转画风）', '多语种批量', '时长<5分钟/文件<500M', '改编4档（不改编/弱/中/强）+男频/女频+文化元素映射']),
    ('Seko', ['剧本级出海Skill', '多国口语台词', '剧本<20M', '剧情场景保留中文方便制作']),
    ('万兴剧厂', ['视频转绘beta', '中英日印尼西葡6语种', '≤300MB/5秒-3分钟', '语种导向']),
    ('小云雀', ['重制转绘（白模/普通）', '18种目标地区', '单段5-300秒/≤500MB/最多20段/总时长100分钟', '资产本土化+定妆核对+镜头语言1:1复刻']),
]
rpr_ov = get_rpr_tmpl(t_ov.rows[1].cells[1]._tc)
for i, (plat, cells) in enumerate(OVERSEA):
    row = t_ov.rows[i + 1]
    set_cell_text(row.cells[0], plat, shade=False)
    for ci, val in enumerate(cells):
        set_cell_text(row.cells[ci + 1], val, shade=False, rpr_tmpl=rpr_ov)
LOG.append('出海转绘表: 6行重排字母序(内容核查无改动,不黄)')

dst.save(OUT)
print('\n'.join(LOG))
print('STAGE B OK ->', OUT)
