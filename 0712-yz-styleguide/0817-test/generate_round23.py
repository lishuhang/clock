from __future__ import annotations

import csv
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R2 = ROOT / 'round2.3'
R22 = ROOT / 'round2.2'
SPRITE = (R2 / 'assets' / 'yz-brand-sprite.svg').read_text(encoding='utf-8')
SPRITE_INNER = SPRITE.split('<defs>', 1)[1].rsplit('</defs>', 1)[0]

COLORS = {'专业能力': '#17324D', '民族国家': '#D94B3D', '社会文化/性别': '#C97B8D'}
COMMENTS = [
    ('comment-part1-styled', '《夏洛特烦恼》', '男性视角的意淫', '豆瓣用户，2015-10-01，4星，2665 有用', 'xialuo.jpg', '1/7'),
    ('comment-part2-styled', '《独行月球》', '好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。', '豆瓣用户，2022-07-29，3星，7805 有用', 'duxing.jpg', '2/7'),
    ('comment-part3-styled', '《日不落酒店》', '各种夸张和尴尬，还用沈腾做幌子。', '豆瓣用户，2021-03-19，2星，28 有用', 'ribuluo.jpg', '3/7'),
    ('comment-part4-styled', '《日不落酒店》', '看到沈腾的名字立即选座无脑买的。', '豆瓣用户，2021-03-19，2星，551 有用', 'ribuluo.jpg', '4/7'),
    ('comment-part5-styled', '《夏洛特烦恼》', '作为女性，对于这种中年男人的意淫完全接受不了。', '豆瓣用户，2015-10-01，2星，8823 有用', 'xialuo.jpg', '5/7'),
    ('comment-part6-styled', '《欢迎来龙餐馆》', '腾哥是我们这一辈的星爷😭', '抖音用户，3天前·湖南，37.3万赞', 'longcanguan.jpg', '6/7'),
    ('comment-part7-styled', '《欢迎来龙餐馆》', '内娱你欠沈腾一个实至名归的影帝。', '抖音用户，3天前·江苏，9.5万赞', 'longcanguan.jpg', '7/7'),
]


def esc(v: object) -> str:
    return html.escape(str(v))


def rows(name: str) -> list[dict[str, str]]:
    with (ROOT / 'round1.2' / 'data' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def common_css() -> str:
    return '''
@font-face{font-family:AliPuHui;src:url("assets/fonts/AlibabaPuHuiTi-3-55-Regular.ttf") format("truetype");font-weight:400}@font-face{font-family:AliPuHui;src:url("assets/fonts/AlibabaPuHuiTi-3-85-Bold.ttf") format("truetype");font-weight:700}@font-face{font-family:AliPuHui;src:url("assets/fonts/AlibabaPuHuiTi-3-115-Black.ttf") format("truetype");font-weight:900}
:root{--yz-text:#312e2e;--yz-muted:#9a9595;--yz-border:#e5e5e5;--yz-accent:#fc8166;--yz-font:AliPuHui,'阿里巴巴普惠体',sans-serif}*{box-sizing:border-box;margin:0;padding:0}body{width:1080px;height:1080px;margin:0;background:#fff;font-family:var(--yz-font);color:var(--yz-text)}.chart-container-1x1{position:relative;width:1080px;height:1080px;background:#fff;padding:38px 42px 34px;display:flex;flex-direction:column;overflow:hidden;border-radius:6px}.chart-header-1x1{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:18px;flex-shrink:0}.chart-title-1x1{font-size:48px;line-height:1.25;font-weight:900;letter-spacing:-.4px}.chart-logo-1x1{width:90px;height:80px;display:flex;justify-content:flex-end;flex-shrink:0}.chart-logo-1x1 svg{height:76px;width:auto}.chart-body-1x1{flex:1;min-height:0;display:flex;flex-direction:column}.chart-footer-1x1{flex-shrink:0;margin-top:14px;padding-top:12px;border-top:1px solid var(--yz-border);display:flex;justify-content:flex-end}.chart-part-num{font-size:24px;color:var(--yz-muted);font-weight:700}.review-card{height:100%;border:1px solid var(--yz-border);border-radius:6px;display:grid;grid-template-columns:minmax(0,1fr) 354px;overflow:hidden;background:#fff}.review-copy{padding:54px 36px 50px 46px;display:flex;flex-direction:column;justify-content:center;min-width:0}.review-quote{font-size:62px;line-height:1.34;font-weight:900;letter-spacing:-1px;word-break:break-word}.review-meta{margin-top:42px;font-size:30px;line-height:1.45;color:var(--yz-muted);font-weight:400}.review-poster{width:354px;height:100%;object-fit:cover;object-position:center}.hm-table{width:100%;border-collapse:separate;border-spacing:6px;table-layout:fixed;font-size:29px}.hm-table th{height:78px;padding:8px 4px;line-height:1.2;font-weight:900;background:#fafafa;border-radius:6px;text-align:center}.hm-table th.row-head{width:230px;background:transparent;color:var(--yz-accent);text-align:left;font-size:24px;white-space:nowrap;letter-spacing:-.6px}.hm-table td{height:106px;text-align:center;vertical-align:middle;border-radius:6px;font-weight:900}.hm-legend{display:flex;align-items:center;gap:12px;font-size:26px;color:var(--yz-muted);margin-top:20px}.hm-grad{width:140px;height:14px;border-radius:7px;background:linear-gradient(90deg,rgba(252,129,102,.1),#fc8166)}.dumbbell-svg{width:100%;height:720px;display:block}.svg-axis{stroke:#eee;stroke-width:1.5}.svg-base{stroke:#d8d8d8;stroke-width:2}.svg-film{font-family:AliPuHui,'阿里巴巴普惠体',sans-serif;font-size:18px;fill:#312e2e;font-weight:700}.svg-axis-text{font-family:AliPuHui,'阿里巴巴普惠体',sans-serif;font-size:16px;fill:#9a9595}.svg-value{font-family:AliPuHui,'阿里巴巴普惠体',sans-serif;font-size:14px;font-weight:700}.chart-legend{display:flex;justify-content:center;align-items:center;gap:20px;flex-wrap:wrap;margin-top:4px;font-size:21px;color:#6b6666}.legend-item{display:flex;align-items:center;gap:7px}.legend-dot{width:16px;height:16px;border-radius:50%;display:inline-block}.legend-ring{width:16px;height:16px;border-radius:50%;border:3px solid #6b6666;display:inline-block}
'''


def base(title: str, body: str, part: str, extra: str = '') -> str:
    sprite = f'<svg aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden"><defs>{SPRITE_INNER}</defs></svg>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1080"><title>{esc(title)}</title><style>{common_css()}{extra}</style></head><body>{sprite}<main class="chart-container-1x1"><div class="chart-header-1x1"><h1 class="chart-title-1x1">{esc(title)}</h1><div class="chart-logo-1x1"><svg viewBox="0 0 199 231" aria-label="娱乐资本论"><use href="#yz-logo-icon"></use></svg></div></div><div class="chart-body-1x1">{body}</div><div class="chart-footer-1x1"><div class="chart-part-num">{esc(part)}</div></div></main></body></html>'''


def comment_page(title: str, quote: str, meta: str, poster: str, part: str) -> str:
    body = f'<article class="review-card"><div class="review-copy"><blockquote class="review-quote">“{esc(quote)}”</blockquote><p class="review-meta">——{esc(meta)}</p></div><img class="review-poster" src="assets/posters/{esc(poster)}" alt="{esc(title)} 海报"></article>'
    return base(title, body, part)


def heatmap_body(items: list[dict[str,str]]) -> str:
    dims=['专业能力','道德人格','民族国家','商业资本','社会文化/性别','身份符号']
    head=''.join(f'<th>{esc(d)}</th>' for d in dims)
    data=[]
    for r in items:
        cells=[]
        for d in dims:
            value=int(r[d].rstrip('%')); alpha=.08+.72*value/100; fg='#fff' if value>=58 else '#312e2e'
            cells.append(f'<td style="background:rgba(252,129,102,{alpha:.3f});color:{fg}">{value}%</td>')
        data.append(f'<tr><th class="row-head">{esc(r["年份"])} {esc(r["作品"])}</th>{"".join(cells)}</tr>')
    return f'<table class="hm-table"><thead><tr><th class="row-head">作品</th>{head}</tr></thead><tbody>{"".join(data)}</tbody></table><div class="hm-legend"><i class="hm-grad"></i>低占比　高占比</div>'


def dumbbell_svg(data: list[dict[str,str]]) -> str:
    x0,x1=260,935; top=76; rows_y=[135+i*55 for i in range(10)]
    def x(v:float)->float:return x0+(x1-x0)*v/100
    pieces=['<svg class="dumbbell-svg" viewBox="0 0 1000 720" aria-label="热映期与近年回看对比">']
    for pct in [0,25,50,75,100]:
        xp=x(pct); pieces.append(f'<line class="svg-axis" x1="{xp}" y1="{top}" x2="{xp}" y2="690"/><text class="svg-axis-text" x="{xp}" y="52" text-anchor="middle">{pct}%</text>')
    grouped={dim:[r for r in data if r['维度']==dim] for dim in COLORS}
    for i, name in enumerate([r['作品'] for r in grouped['专业能力']]):
        y=rows_y[i]; pieces.append(f'<text class="svg-film" x="12" y="{y+6}">{esc(name)}</text>')
        for offset,dim in zip([-10,0,10],COLORS):
            r=grouped[dim][i]; a=float(r['上映期占比%']); b=float(r['近年回看占比%']); xa,xb=x(a),x(b); color=COLORS[dim]; yy=y+offset
            pieces.append(f'<line class="svg-base" x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" opacity=".25"/><line x1="{min(xa,xb)}" y1="{yy}" x2="{max(xa,xb)}" y2="{yy}" stroke="{color}" stroke-width="4" opacity=".7"/><circle cx="{xa}" cy="{yy}" r="6" fill="#fff" stroke="{color}" stroke-width="3"/><circle cx="{xb}" cy="{yy}" r="6" fill="{color}"/>')
    pieces.append('</svg>')
    legend=''.join(f'<span class="legend-item"><i class="legend-dot" style="background:{c}"></i>{d}</span>' for d,c in COLORS.items())
    legend += '<span class="legend-item"><i class="legend-ring"></i>热映期　●近年回看</span>'
    return ''.join(pieces)+f'<div class="chart-legend">{legend}</div>'


def copy_professional() -> None:
    for path in R22.glob('img2-part*-styled.html'):
        text=path.read_text(encoding='utf-8')
        # The existing inline brand symbols and component markup remain; relocate assets to round2.3's local folder.
        (R2/path.name).write_text(text,encoding='utf-8')


def main() -> None:
    R2.mkdir(exist_ok=True)
    for stem,title,quote,meta,poster,part in COMMENTS:
        (R2/f'{stem}.html').write_text(comment_page(title,quote,meta,poster,part),encoding='utf-8')
    heatmap=rows('shenteng_works_heatmap.csv')
    for index,(lo,hi) in enumerate([(0,5),(5,10)],1):
        (R2/f'img1-part{index}-styled.html').write_text(base('十部作品如何改写沈腾的形象',heatmap_body(heatmap[lo:hi]),f'{index}/2'),encoding='utf-8')
    db=rows('shenteng_dumbbell_chart.csv')
    (R2/'img3-part1-styled.html').write_text(base('热映期与近年回看的评价对比',dumbbell_svg(db),'1/1'),encoding='utf-8')
    copy_professional()
    print('Generated 7 comment cards, 2 heatmap cards, 3 carried professional cards, and 1 simultaneous dumbbell card.')

if __name__=='__main__':
    main()
