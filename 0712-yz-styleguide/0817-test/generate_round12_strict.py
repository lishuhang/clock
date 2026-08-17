from __future__ import annotations

import csv
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R1 = ROOT / 'round1.2'
R2 = ROOT / 'round2.2'
DATA = R1 / 'data'
SPRITE_FILE = R1 / 'assets' / 'yz-brand-sprite.svg'
SPRITE_TEXT = SPRITE_FILE.read_text(encoding='utf-8')
SPRITE_INNER = SPRITE_TEXT.split('<defs>', 1)[1].rsplit('</defs>', 1)[0]

ACCENT = '#fc8166'
DIMENSIONS = ['专业能力', '道德人格', '民族国家', '商业资本', '社会文化/性别', '身份符号']
F1_KEYS = ['喜剧/搞笑占比%', '演技/声台形表占比%', '共情/感染力占比%', '角色塑造/突破占比%', '剧本/节奏/整体占比%']
F1_NAMES = ['喜剧/搞笑', '演技/声台形表', '共情/感染力', '角色塑造/突破', '剧本/节奏/整体']
F1_COLORS = ['#fc8166', '#f6b65b', '#b8dba8', '#8ec6ce', '#b69aca']
DIM_COLORS = {'专业能力': '#fc8166', '民族国家': '#5b9bd5', '社会文化/性别': '#b69aca'}
COMMENTS = [
    ('D01', '豆瓣', '男性视角的意淫', '看过 · 约4星 · 2015-10-01 23:31:21 · 2665 有用', '用户提供原始截图 OCR：640(3).png'),
    ('D02', '豆瓣', '好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。', '看过 · 约3星 · 2022-07-29 11:06:17 · 7805 有用', '用户提供原始截图 OCR：640.png'),
    ('D03', '豆瓣', '各种夸张和尴尬，还用沈腾做幌子。', '看过 · 约2星 · 2021-03-19 21:55:58 · 28 有用', '用户提供原始截图 OCR：640(2).png'),
    ('D04', '豆瓣', '看到沈腾的名字立即选座无脑买的。', '看过 · 约2星 · 2021-03-19 12:10:38 · 551 有用', '用户提供原始截图 OCR：640(1).png'),
    ('D05', '豆瓣', '作为女性，对于这种中年男人的意淫完全接受不了。', '看过 · 约2星 · 2015-10-01 17:46:36 · 8823 有用', '用户提供原始截图 OCR：640(4).png'),
    ('X01', '小红书', '腾哥是我们这一辈的星爷😭', '搜索“沈腾” · 4.1万条评论 · 3天前·湖南 · 37.3万赞 · 1415条回复', '用户提供原始截图 OCR：640(1).jpg'),
    ('X02', '小红书', '内娱你欠沈腾一个实至名归的影帝。', '3天前·江苏 · 9.5万赞 · 204条回复', '用户提供原始截图 OCR：640(1).jpg'),
]


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def esc(value: object) -> str:
    return html.escape(str(value))


def brand_symbol(kind: str, cls: str) -> str:
    return f'<svg class="{cls}" viewBox="0 0 {"329.6287 100" if kind == "horizontal" else "199 231"}" aria-label="娱乐资本论图形标识"><use href="#yz-logo-{kind}"></use></svg>'


def base_css(square: bool = False) -> str:
    container = '''
.chart-container-1x1{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:44px 48px 40px;border-radius:6px;overflow:hidden;display:flex;flex-direction:column;}
.chart-header-1x1{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;flex-shrink:0;margin-bottom:24px;}
.chart-title-1x1{width:80%;font-size:48px;font-weight:900;line-height:1.35;color:var(--yz-text);}
.chart-logo-1x1{width:20%;height:96px;display:flex;justify-content:flex-end;align-items:flex-start;flex-shrink:0;}.chart-logo-1x1 .yz-logo-icon{height:96px;width:auto;}
.chart-body-1x1{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;justify-content:center;}.chart-footer-1x1{margin-top:18px;padding-top:16px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;flex-shrink:0;}.chart-source-1x1{font-size:27px;color:var(--yz-text-muted);line-height:1.4;flex:1;}.chart-part-num{font-size:24px;color:var(--yz-text-muted);font-weight:700;margin-left:16px;white-space:nowrap;}
''' if square else '''
.chart-container{position:relative;width:1800px;height:var(--chart-height,2600px);margin:0 auto;background:#fff;padding:96px 100px 72px;overflow:hidden;display:flex;flex-direction:column;}.chart-header{display:flex;justify-content:space-between;align-items:flex-start;gap:40px;flex-shrink:0;margin-bottom:44px;}.chart-title{font-size:88px;font-weight:900;line-height:1.22;letter-spacing:-2px;max-width:1240px;}.chart-body{position:relative;z-index:1;flex:1 1 auto;display:flex;flex-direction:column;justify-content:flex-start;}.chart-footer{display:flex;justify-content:space-between;align-items:flex-end;margin-top:42px;padding-top:28px;border-top:1px solid var(--yz-border-soft);flex-shrink:0;}.chart-source{font-size:30px;color:var(--yz-text-muted);line-height:1.6;max-width:66%;}.yz-logo-svg{height:72px;width:auto;flex-shrink:0;}.yz-watermark{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);opacity:.11;z-index:0;pointer-events:none;}.yz-watermark .yz-logo-vertical{width:480px;height:auto;}
'''
    return f'''@font-face{{font-family:AliPuHui;src:url("assets/fonts/AlibabaPuHuiTi-3-55-Regular.ttf") format("truetype");font-weight:400;}}@font-face{{font-family:AliPuHui;src:url("assets/fonts/AlibabaPuHuiTi-3-85-Bold.ttf") format("truetype");font-weight:700;}}@font-face{{font-family:AliPuHui;src:url("assets/fonts/AlibabaPuHuiTi-3-115-Black.ttf") format("truetype");font-weight:900;}}
:root{{--yz-accent:#fc8166;--yz-accent-deep:#e55b46;--yz-ink:#312e2e;--yz-text:#312e2e;--yz-text-secondary:#6b6666;--yz-text-muted:#9a9595;--yz-bg:#fff;--yz-bg-chart:#efefef;--yz-border:#dcdcdc;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:AliPuHui,'阿里巴巴普惠体',sans-serif;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}html{{-webkit-text-size-adjust:100%;}}body{{font-family:var(--yz-font);color:var(--yz-text);background:#fff;margin:0;padding:0;}}img{{display:block;max-width:100%;}}{container}
.phase-label{{font-size:34px;font-weight:900;display:flex;align-items:center;gap:14px;}}.phase-label .phase-badge{{width:48px;height:48px;border-radius:50%;background:var(--yz-accent);color:#fff;display:inline-flex;justify-content:center;align-items:center;font-size:28px;font-weight:900;flex-shrink:0;}}
.chart-legend{{display:flex;flex-wrap:wrap;gap:18px 28px;align-items:center;}}.legend-item{{display:flex;align-items:center;gap:10px;font-size:28px;line-height:1.25;}}.legend-swatch{{width:24px;height:24px;border-radius:50%;flex-shrink:0;}}.legend-swatch.bar{{width:34px;height:12px;border-radius:6px;}}
.hm-table{{width:100%;border-collapse:separate;border-spacing:8px;font-size:34px;table-layout:fixed;}}.hm-table th{{padding:18px 8px;text-align:center;font-weight:900;background:#fafafa;border-radius:6px;line-height:1.25;}}.hm-table th.row-head{{background:transparent;text-align:left;color:var(--yz-accent);padding-left:10px;width:270px;}}.hm-table td{{height:120px;text-align:center;border-radius:6px;font-weight:900;vertical-align:middle;}}
.sb-wrap{{display:flex;flex-direction:column;gap:20px;}}.sb-row{{display:grid;grid-template-columns:260px 1fr;gap:20px;align-items:center;}}.sb-label{{font-size:34px;line-height:1.25;font-weight:900;color:var(--yz-accent);}}.sb-bar{{height:58px;border-radius:6px;overflow:hidden;background:#efefef;display:flex;}}.sb-seg{{height:100%;display:flex;align-items:center;justify-content:center;font-size:27px;font-weight:900;color:#312e2e;white-space:nowrap;overflow:hidden;}}
.db5-wrap{{display:flex;flex-direction:column;gap:34px;}}.db5-sub{{display:flex;flex-direction:column;gap:14px;}}.db5-sub-title{{font-size:38px;font-weight:900;color:var(--yz-text);}}.axis-scale{{display:flex;justify-content:space-between;font-size:27px;color:var(--yz-text-secondary);margin-left:290px;}}.db5-row{{display:grid;grid-template-columns:270px 1fr 235px;gap:20px;align-items:center;min-height:64px;}}.db5-label{{font-size:31px;font-weight:900;line-height:1.25;}}.dumbbell-track{{position:relative;height:56px;background:#fafafa;border-radius:28px;}}.dumbbell-track::before{{content:'';position:absolute;left:0;right:0;top:50%;height:3px;background:#eee;transform:translateY(-50%);}}.dumbbell-line{{position:absolute;top:50%;height:5px;transform:translateY(-50%);border-radius:3px;background:currentColor;opacity:.55;}}.dumbbell-dot{{position:absolute;top:50%;width:28px;height:28px;border-radius:50%;border:4px solid #fff;box-shadow:0 0 0 2px currentColor;transform:translate(-50%,-50%);}}.dumbbell-tag{{font-size:28px;font-weight:900;text-align:right;white-space:nowrap;}}
.tc-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px;}}.tc-card{{border:1px solid var(--yz-border-soft);border-radius:6px;padding:30px;background:#fff;display:flex;flex-direction:column;gap:18px;min-height:250px;}}.tc-platform{{font-size:28px;font-weight:900;color:var(--yz-accent);}}.tc-quote{{font-size:36px;line-height:1.42;font-weight:700;}}.tc-meta{{font-size:26px;line-height:1.45;color:var(--yz-text-secondary);margin-top:auto;}}
'''


def page(title: str, body: str, source: str, square: bool = False, part: str = '', height: int = 2600) -> str:
    if square:
        header = f'<div class="chart-header-1x1"><h1 class="chart-title-1x1">{esc(title)}</h1><div class="chart-logo-1x1">{brand_symbol("icon", "yz-logo-icon")}</div></div>'
        footer = f'<div class="chart-footer-1x1"><div class="chart-source-1x1">{esc(source)}</div><div class="chart-part-num">{esc(part)}</div></div>'
        container = f'<main class="chart-container-1x1">{header}<div class="chart-body-1x1">{body}</div>{footer}</main>'
    else:
        header = f'<div class="chart-header"><h1 class="chart-title">{esc(title)}</h1></div>'
        watermark = f'<div class="yz-watermark">{brand_symbol("vertical", "yz-logo-vertical")}</div>'
        footer = f'<div class="chart-footer"><div class="chart-source">{esc(source)}</div>{brand_symbol("horizontal", "yz-logo-svg")}</div>'
        container = f'<main class="chart-container" style="--chart-height:{height}px">{watermark}{header}<div class="chart-body">{body}</div>{footer}</main>'
    sprite = f'<svg aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden"><defs>{SPRITE_INNER}</defs></svg>'
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{base_css(square)}</style></head><body>{sprite}{container}</body></html>'


def heatmap_body(items: list[dict[str, str]]) -> str:
    head = ''.join(f'<th>{esc(d)}</th>' for d in DIMENSIONS)
    trs = []
    for r in items:
        cells = []
        for d in DIMENSIONS:
            val = int(r[d].rstrip('%'))
            alpha = 0.08 + 0.72 * val / 100
            fg = '#fff' if val >= 58 else '#312e2e'
            cells.append(f'<td style="background:rgba(252,129,102,{alpha:.3f});color:{fg}">{val}%</td>')
        trs.append(f'<tr><th class="row-head">{esc(r["年份"])} {esc(r["作品"])}</th>{"".join(cells)}</tr>')
    return f'<table class="hm-table"><thead><tr><th class="row-head">作品</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table><div class="chart-legend" style="margin-top:30px"><span class="legend-item"><span class="legend-swatch bar" style="background:linear-gradient(90deg,rgba(252,129,102,.1),#fc8166)"></span>低占比　高占比</span></div>'


def professional_body(items: list[dict[str, str]]) -> str:
    legend = ''.join(f'<span class="legend-item"><i class="legend-swatch" style="background:{c}"></i>{esc(n)}</span>' for n,c in zip(F1_NAMES,F1_COLORS))
    bars = []
    for r in items:
        segs = []
        for key,color in zip(F1_KEYS,F1_COLORS):
            value = int(r[key])
            label = f'{value}%' if value >= 11 else ''
            segs.append(f'<span class="sb-seg" style="width:{value}%;background:{color}">{label}</span>')
        bars.append(f'<div class="sb-row"><div class="sb-label">{esc(r["年份"])} {esc(r["作品"])}</div><div class="sb-bar">{"".join(segs)}</div></div>')
    return f'<div class="chart-legend" style="margin-bottom:30px">{legend}</div><div class="sb-wrap">{"".join(bars)}</div>'


def dumbbell_body(items: list[dict[str, str]], dimensions: list[str]) -> str:
    panels=[]
    for dim in dimensions:
        data = [r for r in items if r['维度']==dim]
        lines=[]
        for r in data:
            a=float(r['上映期占比%']); b=float(r['近年回看占比%']); d=r['变化Δpp']
            left=min(a,b); width=abs(a-b); color=DIM_COLORS[dim]
            lines.append(f'''<div class="db5-row"><div class="db5-label">{esc(r['作品'])}</div><div class="dumbbell-track" style="color:{color}"><i class="dumbbell-line" style="left:{left}%;width:{width}%"></i><i class="dumbbell-dot" style="left:{a}%;background:{color}"></i><i class="dumbbell-dot" style="left:{b}%;background:#fff"></i></div><div class="dumbbell-tag">{a:.1f}% → {b:.1f}%<br><span style="color:{color}">{esc(d)}pp</span></div></div>''')
        panels.append(f'<section class="db5-sub"><div class="db5-sub-title">{esc(dim)}</div><div class="axis-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>{"".join(lines)}</section>')
    legend='<div class="chart-legend" style="margin-bottom:22px"><span class="legend-item"><i class="legend-swatch" style="background:#fc8166"></i>热映期</span><span class="legend-item"><i class="legend-swatch" style="background:#fff;border:2px solid #312e2e"></i>近年回看</span><span class="legend-item">线段为两期变化</span></div>'
    return legend + f'<div class="db5-wrap">{"".join(panels)}</div>'


def comments_body(comments: list[tuple[str,str,str,str,str]], square: bool=False) -> str:
    cards=[]
    for code,platform,quote,meta,source in comments:
        qsize='48px' if square else '36px'
        cards.append(f'<article class="tc-card"><div class="tc-platform">{esc(platform)}</div><blockquote class="tc-quote" style="font-size:{qsize}">“{esc(quote)}”</blockquote><div class="tc-meta">{esc(meta)}<br>{esc(source)}</div></article>')
    return f'<div class="tc-grid">{"".join(cards)}</div>'


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def main() -> None:
    R1.mkdir(exist_ok=True); R2.mkdir(exist_ok=True)
    heatmap = rows('shenteng_works_heatmap.csv')
    f1 = rows('f1_subdim_chart.csv')
    db = rows('shenteng_dumbbell_chart.csv')
    write(R1/'img1-a-heatmap-styled.html', page('十部作品如何改写沈腾的形象', heatmap_body(heatmap), '数据来源：豆瓣短评；官方表1底稿', height=2400))
    write(R1/'img2-a-professional-styled.html', page('专业能力评价焦点如何变化', professional_body(f1), '数据来源：豆瓣短评；官方表2底稿', height=2400))
    write(R1/'img3-a-dumbbell-styled.html', page('热映期与近年回看的评价对比', dumbbell_body(db, ['专业能力','民族国家','社会文化/性别']), '数据来源：豆瓣短评；官方表3底稿', height=3000))
    write(R1/'comments-a-styled.html', page('豆瓣与小红书中的代表性评论', comments_body(COMMENTS), '数据来源：用户提供原始评论截图 OCR', height=2400))
    # 4-3-3 heatmap and professional split series.
    for group, (lo,hi) in enumerate([(0,4),(4,7),(7,10)], 1):
        write(R2/f'img1-part{group}-styled.html', page('十部作品如何改写沈腾的形象', heatmap_body(heatmap[lo:hi]), '数据：官方表1底稿', True, f'{group}/3'))
        write(R2/f'img2-part{group}-styled.html', page('专业能力评价焦点如何变化', professional_body(f1[lo:hi]), '数据：官方表2底稿', True, f'{group}/3'))
    for idx, dim in enumerate(['专业能力','民族国家','社会文化/性别'],1):
        write(R2/f'img3-part{idx}-styled.html', page('热映期与近年回看的评价对比', dumbbell_body(db,[dim]), '数据：官方表3底稿；变化值以源表为准', True, f'{idx}/3'))
    for idx, comment in enumerate(COMMENTS,1):
        write(R2/f'comment-part{idx}-styled.html', page('豆瓣与小红书中的代表性评论', comments_body([comment], True), '数据：用户提供原始评论截图 OCR', True, f'{idx}/7'))
    print('Generated 4 round1.2 pages and 16 round2.2 pages.')


if __name__ == '__main__':
    main()
