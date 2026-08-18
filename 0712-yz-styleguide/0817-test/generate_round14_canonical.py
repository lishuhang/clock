from __future__ import annotations

import csv
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT.parent / '0811-test' / 'round1.2' / 'img1-styled.html'
SOURCE = ROOT / 'round1.2'
OUT = ROOT / 'round1.4'
DATA = SOURCE / 'data'
SPRITE_FILE = SOURCE / 'assets' / 'yz-brand-sprite.svg'
DIMENSIONS = ['专业能力', '道德人格', '民族国家', '商业资本', '社会文化/性别', '身份符号']
F1_KEYS = ['喜剧/搞笑占比%', '演技/声台形表占比%', '共情/感染力占比%', '角色塑造/突破占比%', '剧本/节奏/整体占比%']
F1_NAMES = ['喜剧/搞笑', '演技/声台形表', '共情/感染力', '角色塑造/突破', '剧本/节奏/整体']
F1_COLORS = ['#fc8166', '#f6b65b', '#b8dba8', '#8ec6ce', '#b69aca']
DIM_COLORS = {'专业能力': '#fc8166', '民族国家': '#5b9bd5', '社会文化/性别': '#b69aca'}
COMMENTS = [
    ('《夏洛特烦恼》', '豆瓣用户', '男性视角的意淫', '2015-10-01 · 4星 · 2665 有用'),
    ('《独行月球》', '豆瓣用户', '好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。', '2022-07-29 · 3星 · 7805 有用'),
    ('《日不落酒店》', '豆瓣用户', '各种夸张和尴尬，还用沈腾做幌子。', '2021-03-19 · 2星 · 28 有用'),
    ('《日不落酒店》', '豆瓣用户', '看到沈腾的名字立即选座无脑买的。', '2021-03-19 · 2星 · 551 有用'),
    ('《夏洛特烦恼》', '豆瓣用户', '作为女性，对于这种中年男人的意淫完全接受不了。', '2015-10-01 · 2星 · 8823 有用'),
    ('《欢迎来龙餐馆》', '抖音用户', '腾哥是我们这一辈的星爷😭', '3天前 · 湖南 · 37.3万赞'),
    ('《欢迎来龙餐馆》', '抖音用户', '内娱你欠沈腾一个实至名归的影帝。', '3天前 · 江苏 · 9.5万赞'),
]


def esc(value: object) -> str:
    return html.escape(str(value))


def data_rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def brand(kind: str, cls: str) -> str:
    view = '329.6287 100' if kind == 'horizontal' else '100 153.4916'
    return f'<svg class="{cls}" viewBox="0 0 {view}" aria-label="娱乐资本论图形标识"><use href="#yz-logo-{kind}"></use></svg>'


def asset_setup() -> str:
    OUT.mkdir(exist_ok=True)
    asset = OUT / 'assets'
    if asset.exists():
        shutil.rmtree(asset)
    shutil.copytree(SOURCE / 'assets', asset)
    sprite = SPRITE_FILE.read_text(encoding='utf-8')
    return sprite.split('<defs>', 1)[1].rsplit('</defs>', 1)[0]


def canonical_css() -> str:
    # Values are deliberately copied from 0811-test/round1.2/img1-styled.html, lines 15071-15096.
    return '''
@font-face{font-family:'AliPuHui';src:url('assets/fonts/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
@font-face{font-family:'AliPuHui';src:url('assets/fonts/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap}
@font-face{font-family:'AliPuHui';src:url('assets/fonts/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap}
:root{--yz-accent:#fc8166;--yz-accent-deep:#e55b46;--yz-ink:#312e2e;--yz-text:#312e2e;--yz-text-secondary:#6b6666;--yz-text-muted:#9a9595;--yz-bg:#fff;--yz-bg-chart:#efefef;--yz-border:#dcdcdc;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui','阿里巴巴普惠体',sans-serif}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0} html,body{background:#f0f0f0} body{font-family:var(--yz-font);color:var(--yz-text)}
.chart-container{position:relative;width:900px;min-height:auto;height:auto;margin:0 auto;background:#fff;padding:56px 48px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column}
.yz-watermark{position:absolute!important;inset:0!important;display:flex!important;align-items:center;justify-content:center;pointer-events:none;z-index:9999!important}.yz-watermark svg{width:420px!important;height:auto;opacity:.10!important}
.chart-title{position:relative;z-index:2;font-size:68px!important;font-weight:900;color:var(--yz-text);margin-bottom:36px!important;line-height:1.25!important;text-align:left}
.chart-body{position:relative;z-index:auto!important;flex:0 1 auto!important;min-height:auto!important;display:flex;flex-direction:column}
.chart-footer{position:relative;z-index:2;display:flex;justify-content:space-between;align-items:flex-end;margin-top:36px!important;padding-top:24px!important;border-top:1px solid var(--yz-border-soft);flex-shrink:0}.chart-source{font-size:26px!important;color:var(--yz-text-muted);text-align:left;line-height:1.5!important;max-width:60%}.yz-logo-svg{height:62px!important;width:auto;flex-shrink:0}
/* Canonical shared components — use these instead of per-chart lookalike classes. */
.phase-label{font-size:30px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:14px}.phase-label .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;background:#fc8166;color:#fff;border-radius:50%;font-size:26px;font-weight:900;flex-shrink:0}
.dumbbell-track{position:relative;height:64px;background:#fafafa;border-radius:32px}.dumbbell-track::before{content:'';position:absolute;top:50%;left:0;right:0;height:3px;background:#eee;transform:translateY(-50%)}.dumbbell-dot{position:absolute;top:50%;transform:translate(-50%,-50%);width:34px;height:34px;border-radius:50%;border:5px solid #fff;box-shadow:0 0 0 3px currentColor;z-index:2}.dumbbell-tag{position:absolute;font-size:22px;font-weight:700;white-space:nowrap;transform:translateX(-50%)}.dumbbell-tag.above{top:-50px}.dumbbell-tag.below{bottom:-50px}.dumbbell-line{position:absolute;top:50%;height:6px;transform:translateY(-50%);z-index:1}.axis-scale{display:flex;justify-content:space-between;font-size:18px;color:#9a9595;margin-top:14px;padding:0 4px}
.chart-legend{display:flex;flex-wrap:wrap;gap:18px 32px;margin-top:14px;font-size:22px;color:#6b6666}.chart-legend .legend-item{display:flex;align-items:center;gap:10px}.chart-legend .legend-swatch{width:24px;height:24px;border-radius:50%}.chart-legend .legend-swatch.bar{width:32px;height:8px;border-radius:4px}
.hm-table{width:100%;border-collapse:separate;border-spacing:6px;font-size:28px}.hm-table th{padding:18px 10px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:6px;font-size:24px}.hm-table th.row-head{background:transparent;text-align:left;padding-left:14px;color:#fc8166}.hm-table td{padding:22px 8px;text-align:center;border-radius:6px;font-weight:700;color:#312e2e;min-width:110px;font-size:26px}.hm-table td.row-label{text-align:left;padding-left:14px;font-weight:700;color:#fc8166;background:#fff;font-size:24px}.hm-legend{display:flex;align-items:center;gap:20px;margin-top:24px;font-size:22px;color:#6b6666}.hm-legend .grad{display:inline-block;width:240px;height:16px;background:linear-gradient(to right,rgba(252,129,102,.05),rgba(252,129,102,1));border-radius:3px}
.sb-wrap{display:flex;flex-direction:column;gap:36px}.sb-row{display:flex;flex-direction:column;gap:12px}.sb-bar{display:flex;width:100%;height:80px;border-radius:8px;overflow:hidden;background:#fafafa}.sb-seg{display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;color:#fff}.sb-label{font-size:30px;font-weight:900;color:#312e2e}
.tc-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;position:relative;z-index:auto}.tc-card{border:1px solid #f0f0f0;border-left:8px solid #fc8166;border-radius:8px;padding:28px 32px;background:rgba(255,255,255,.92);display:flex;flex-direction:column;gap:14px;position:relative}.tc-card-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}.tc-work{font-size:30px;font-weight:900;color:#312e2e}.tc-platform{font-size:24px;font-weight:900;color:#fc8166}.tc-meta{font-size:24px;color:#9a9595;margin-top:auto}.tc-quote{font-size:26px;line-height:1.65;color:#312e2e;font-weight:500}.tc-quote .qmark{color:#fc8166;font-weight:900;font-size:36px;line-height:0;vertical-align:-6px}
#yz-selfcheck-banner{position:absolute;top:8px;right:8px;padding:6px 12px;border-radius:6px;font-family:var(--yz-font);font-size:12px;font-weight:700;z-index:10000;display:none}#yz-selfcheck-banner.pass{background:#50c885;color:#fff;display:block}#yz-selfcheck-banner.fail{background:#e60012;color:#fff;display:block}
'''


def selfcheck_js() -> str:
    return '''
<script>
function yzSelfCheck(){
 const errors=[];for(const [selector,label] of [['.chart-container','画布容器'],['.yz-watermark','水印'],['.chart-title','标题'],['.chart-body','主体'],['.chart-source','脚注'],['.yz-logo-svg','横版SVG logo']])if(!document.querySelector(selector))errors.push('缺失：'+label);
 if(document.fonts&&document.fonts.check&&!document.fonts.check('900 34px AliPuHui'))errors.push('字体 AliPuHui 未加载');
 const html=document.body.innerHTML;for(const token of ['【'+'TITLE_HERE'+'】','【'+'CHART_BODY_HERE'+'】','【'+'SOURCE_FOOTER_HERE'+'】'])if(html.includes(token))errors.push('未替换占位符：'+token);
 const wm=document.querySelector('.yz-watermark svg use');if(!wm||wm.getAttribute('href')!=='#yz-logo-vertical')errors.push('水印必须引用 #yz-logo-vertical');
 const cc=document.querySelector('.chart-container'),style=cc&&getComputedStyle(cc),wmStyle=document.querySelector('.yz-watermark svg')&&getComputedStyle(document.querySelector('.yz-watermark svg')),logoStyle=document.querySelector('.yz-logo-svg')&&getComputedStyle(document.querySelector('.yz-logo-svg'));
 if(!cc||cc.offsetWidth!==900)errors.push('a.4 画布必须为 900px 宽');
 if(!wmStyle||wmStyle.width!=='420px'||wmStyle.opacity!=='0.1')errors.push('水印必须为 420px / opacity 0.10');
 if(!logoStyle||logoStyle.height!=='62px')errors.push('footer logo 必须为 62px');
 if(!style||style.zIndex!=='auto')errors.push('chart-body 不得建立水印遮挡层');
 if(/^图\\s*\\d+/.test(document.querySelector('.chart-title').textContent.trim()))errors.push('标题不得含图N前缀');
 window.yzSelfCheckErrors=errors.slice();const banner=document.getElementById('yz-selfcheck-banner');if(errors.length){if(banner){banner.className='fail';banner.textContent='自检失败：'+errors.length+'项'};console.error(errors);return false}if(banner){banner.className='pass';banner.textContent='a.4 自检通过'};return true;
}
document.fonts.ready.then(()=>setTimeout(yzSelfCheck,100));
</script>'''


def document(title: str, body: str, source: str, sprite: str) -> str:
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=900"><title>{esc(title)}</title><style>{canonical_css()}</style></head><body><svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>{sprite}</defs></svg><div id="yz-selfcheck-banner"></div><main class="chart-container"><div class="yz-watermark">{brand('vertical','')}</div><h1 class="chart-title">{esc(title)}</h1><div class="chart-body">{body}</div><div class="chart-footer"><div class="chart-source">{esc(source)}</div>{brand('horizontal','yz-logo-svg')}</div></main>{selfcheck_js()}</body></html>'''


def heatmap(items: list[dict[str,str]]) -> str:
    head=''.join(f'<th>{esc(dim)}</th>' for dim in DIMENSIONS)
    rows=[]
    for item in items:
        cells=[]
        for dim in DIMENSIONS:
            value=int(item[dim].rstrip('%')); alpha=.03+.72*value/100; color='#fff' if value>=58 else '#312e2e'
            cells.append(f'<td style="background:rgba(252,129,102,{alpha:.3f});color:{color}">{value}%</td>')
        rows.append(f'<tr><td class="row-label">{esc(item["年份"])} {esc(item["作品"])}</td>{"".join(cells)}</tr>')
    return f'<table class="hm-table"><thead><tr><th class="row-head">作品</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table><div class="hm-legend"><span>低占比</span><span class="grad"></span><span>高占比</span></div>'


def professional(items: list[dict[str,str]]) -> str:
    legend=''.join(f'<span class="legend-item"><i class="legend-swatch" style="background:{color}"></i>{esc(name)}</span>' for name,color in zip(F1_NAMES,F1_COLORS))
    bars=[]
    for item in items:
        parts=[]
        for key,color in zip(F1_KEYS,F1_COLORS):
            value=int(item[key]); label=f'{value}%' if value>=11 else ''
            parts.append(f'<span class="sb-seg" style="width:{value}%;background:{color}">{label}</span>')
        bars.append(f'<div class="sb-row"><div class="sb-label">{esc(item["年份"])} {esc(item["作品"])}</div><div class="sb-bar">{"".join(parts)}</div></div>')
    return f'<div class="chart-legend" style="margin-bottom:28px">{legend}</div><div class="sb-wrap">{"".join(bars)}</div>'


def dumbbell(items: list[dict[str,str]]) -> str:
    panels=[]
    for dim in ['专业能力','民族国家','社会文化/性别']:
        rows=[]; color=DIM_COLORS[dim]
        for item in [x for x in items if x['维度']==dim]:
            release=float(item['上映期占比%']); recent=float(item['近年回看占比%']); left=min(release,recent); width=abs(release-recent)
            rows.append(f'<div class="db-row"><div class="db-label">{esc(item["作品"])}</div><div class="dumbbell-track" style="color:{color}"><i class="dumbbell-line" style="left:{left}%;width:{width}%;background:{color}"></i><i class="dumbbell-dot" style="left:{release}%;background:{color}"></i><i class="dumbbell-dot" style="left:{recent}%;background:#fff"></i></div><div class="db-value">{release:.1f}% → {recent:.1f}%<br><b style="color:{color}">{esc(item["变化Δpp"])}pp</b></div></div>')
        panels.append(f'<section class="db-panel"><h2>{esc(dim)}</h2><div class="axis-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>{"".join(rows)}</section>')
    return '<style>.db-panel{margin-bottom:34px}.db-panel h2{font-size:34px;margin-bottom:12px}.db-row{display:grid;grid-template-columns:220px 1fr 170px;gap:18px;align-items:center;min-height:74px}.db-label{font-size:28px;font-weight:900;line-height:1.25}.db-value{font-size:22px;font-weight:900;text-align:right;white-space:nowrap}</style><div class="chart-legend"><span class="legend-item"><i class="legend-swatch" style="background:#fc8166"></i>热映期</span><span class="legend-item"><i class="legend-swatch" style="background:#fff;border:2px solid #312e2e"></i>近年回看</span><span class="legend-item">线段为两期变化</span></div>'+''.join(panels)


def comment_cards() -> str:
    cards=[]
    for movie,platform,quote,meta in COMMENTS:
        cards.append(f'<article class="tc-card"><div class="tc-card-head"><div class="tc-work">{esc(movie)}</div><div class="tc-platform">{esc(platform)}</div></div><blockquote class="tc-quote"><span class="qmark">“</span>{esc(quote)}<span class="qmark">”</span></blockquote><div class="tc-meta">{esc(meta)}</div></article>')
    return '<div class="tc-grid">'+''.join(cards)+'</div>'


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text,encoding='utf-8')


def main() -> None:
    sprite=asset_setup(); heat=data_rows('shenteng_works_heatmap.csv'); f1=data_rows('f1_subdim_chart.csv'); db=data_rows('shenteng_dumbbell_chart.csv')
    write('img1-a-heatmap-styled.html',document('十部作品如何改写沈腾的形象',heatmap(heat),'数据来源：豆瓣短评；官方表1底稿',sprite))
    write('img2-a-professional-styled.html',document('专业能力评价焦点如何变化',professional(f1),'数据来源：豆瓣短评；官方表2底稿',sprite))
    write('img3-a-dumbbell-styled.html',document('热映期与近年回看的评价对比',dumbbell(db),'数据来源：豆瓣短评；官方表3底稿',sprite))
    write('comments-a-styled.html',document('豆瓣与抖音中的代表性评论',comment_cards(),'数据来源：用户提供评论截图 OCR 与原文段落映射',sprite))
    print('Generated 4 canonical a.4 static HTML files.')

if __name__=='__main__':
    main()
