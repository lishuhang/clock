from __future__ import annotations

"""Strict b.4 1:1 source generator for the Shen Teng infographic.

All audience-facing text has an explicit semantic size role.  The embedded
self-check blocks any PNG/video production where a body label is below 40 px,
an auxiliary label below 28 px, a source line below 27 px, or a sequence label
below 24 px.  The three data chart types read the official CSVs directly.
"""

import csv
import html
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R2 = ROOT / "round2.3"
ASSET_SOURCE = ROOT / "round2.4" / "assets"
SPRITE = (ASSET_SOURCE / "yz-brand-sprite.svg").read_text(encoding="utf-8")
SPRITE_INNER = SPRITE.split("<defs>", 1)[1].rsplit("</defs>", 1)[0]

COLORS = {"专业能力": "#17324D", "民族国家": "#D94B3D", "社会文化/性别": "#C97B8D"}
F1_NAMES = ["喜剧/搞笑", "演技/声台形表", "共情/感染力", "角色塑造/突破", "剧本/节奏/整体"]
F1_KEYS = ["喜剧/搞笑占比%", "演技/声台形表占比%", "共情/感染力占比%", "角色塑造/突破占比%", "剧本/节奏/整体占比%"]
F1_COLORS = ["#fc8166", "#f6b65b", "#b8dba8", "#8ec6ce", "#b69aca"]
COMMENTS = [
    ("comment-part1-styled", "《夏洛特烦恼》", "男性视角的意淫", "豆瓣用户，2015-10-01，4星，2665 有用", "xialuo.jpg", "1/7"),
    ("comment-part2-styled", "《独行月球》", "好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。", "豆瓣用户，2022-07-29，3星，7805 有用", "duxing.jpg", "2/7"),
    ("comment-part3-styled", "《日不落酒店》", "各种夸张和尴尬，还用沈腾做幌子。", "豆瓣用户，2021-03-19，2星，28 有用", "ribuluo.jpg", "3/7"),
    ("comment-part4-styled", "《日不落酒店》", "看到沈腾的名字立即选座无脑买的。", "豆瓣用户，2021-03-19，2星，551 有用", "ribuluo.jpg", "4/7"),
    ("comment-part5-styled", "《夏洛特烦恼》", "作为女性，对于这种中年男人的意淫完全接受不了。", "豆瓣用户，2015-10-01，2星，8823 有用", "xialuo.jpg", "5/7"),
    ("comment-part6-styled", "《欢迎来龙餐馆》", "腾哥是我们这一辈的星爷😭", "抖音用户，3天前·湖南，37.3万赞", "longcanguan.jpg", "6/7"),
    ("comment-part7-styled", "《欢迎来龙餐馆》", "内娱你欠沈腾一个实至名归的影帝。", "抖音用户，3天前·江苏，9.5万赞", "longcanguan.jpg", "7/7"),
]


def esc(value: object) -> str:
    return html.escape(str(value))


def rows(filename: str) -> list[dict[str, str]]:
    with (ROOT / "round1.2" / "data" / filename).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def common_css() -> str:
    return """
@font-face{font-family:AliPuHui;src:url('assets/fonts/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
@font-face{font-family:AliPuHui;src:url('assets/fonts/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap}
@font-face{font-family:AliPuHui;src:url('assets/fonts/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap}
:root{--yz-text:#312e2e;--yz-muted:#9a9595;--yz-border:#e5e5e5;--yz-accent:#fc8166;--yz-font:AliPuHui,'阿里巴巴普惠体',sans-serif}*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1080px;background:#fff}body{font-family:var(--yz-font);color:var(--yz-text)}
.chart-container-1x1{position:relative;width:1080px;height:1080px;background:#fff;padding:38px 42px 30px;display:flex;flex-direction:column;overflow:hidden;border-radius:6px}.chart-header-1x1{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;margin-bottom:16px;flex-shrink:0}.chart-title-1x1{font-size:48px;line-height:1.25;font-weight:900;letter-spacing:-.4px;max-width:800px}.chart-logo-1x1{width:106px;height:84px;display:flex;justify-content:flex-end;flex-shrink:0}.chart-logo-1x1 svg{height:78px;width:auto}.chart-body-1x1{flex:1;min-height:0;display:flex;flex-direction:column}.chart-footer-1x1{min-height:72px;flex-shrink:0;margin-top:14px;padding-top:12px;border-top:1px solid var(--yz-border);display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.chart-source{font-size:27px;line-height:1.25;color:var(--yz-muted);font-weight:400}.chart-part-num{font-size:24px;line-height:1.25;color:var(--yz-muted);font-weight:700;white-space:nowrap}
.review-card{height:100%;border:1px solid var(--yz-border);border-radius:8px;display:grid;grid-template-columns:minmax(0,1fr) 354px;overflow:hidden;background:#fff}.review-copy{padding:50px 34px 46px 44px;display:flex;flex-direction:column;justify-content:center;min-width:0}.review-quote{font-size:58px;line-height:1.3;font-weight:900;letter-spacing:-1px;word-break:break-word}.review-meta{margin-top:40px;font-size:30px;line-height:1.4;color:var(--yz-muted);font-weight:400}.review-poster{width:354px;height:100%;object-fit:cover;object-position:center}
.hm-table{width:100%;height:100%;border-collapse:separate;border-spacing:6px;table-layout:fixed}.hm-table th{height:92px;padding:6px 3px;line-height:1.16;font-size:28px;font-weight:900;background:#fafafa;border-radius:6px;text-align:center}.hm-table th.row-head{width:230px;background:transparent;color:var(--yz-accent);text-align:left;font-size:40px;white-space:normal;letter-spacing:-.8px}.hm-table td{height:102px;padding:4px;text-align:center;vertical-align:middle;border-radius:6px;font-size:40px;font-weight:900}.hm-legend{display:flex;align-items:center;gap:16px;font-size:28px;color:var(--yz-muted);margin-top:14px}.hm-grad{width:160px;height:18px;border-radius:9px;background:linear-gradient(90deg,rgba(252,129,102,.1),#fc8166)}
.prof-legend{display:flex;flex-wrap:wrap;gap:12px 24px;font-size:28px;line-height:1.25;color:var(--yz-muted);margin:4px 0 18px}.prof-legend span{display:flex;align-items:center;gap:8px}.prof-legend i{width:24px;height:24px;border-radius:50%;display:inline-block;flex-shrink:0}.prof-wrap{display:flex;flex:1;flex-direction:column;justify-content:space-around;gap:18px}.prof-row{display:flex;flex-direction:column;gap:10px}.prof-work{font-size:40px;line-height:1.15;font-weight:900}.prof-bar{height:88px;display:flex;overflow:hidden;border-radius:8px;background:#fafafa}.prof-seg{display:flex;align-items:center;justify-content:center;min-width:0;font-size:40px;line-height:1;font-weight:900;color:#fff}.prof-seg.light{color:#312e2e}
.dumbbell-svg{width:100%;height:100%;display:block}.svg-axis{stroke:#eee;stroke-width:2}.svg-base{stroke:#d8d8d8;stroke-width:3}.svg-film{font-family:AliPuHui,'阿里巴巴普惠体',sans-serif;font-size:40px;fill:#312e2e;font-weight:700}.svg-axis-text{font-family:AliPuHui,'阿里巴巴普惠体',sans-serif;font-size:28px;fill:#9a9595}.chart-legend{display:flex;justify-content:center;align-items:center;gap:18px;flex-wrap:wrap;margin:4px 0 8px;font-size:28px;line-height:1.25;color:#6b6666}.legend-item{display:flex;align-items:center;gap:7px}.legend-dot{width:20px;height:20px;border-radius:50%;display:inline-block}.legend-ring{width:20px;height:20px;border-radius:50%;border:3px solid #6b6666;display:inline-block}.dumbbell-stage{display:flex;flex:1;min-height:0;flex-direction:column}
#yz-selfcheck-banner{position:absolute;top:4px;right:4px;display:none;font-size:18px;font-weight:700;z-index:9999}.yz-check-fail #yz-selfcheck-banner{display:block;color:#e60012}
"""


def selfcheck_js() -> str:
    return """
<script>
function yzSelfCheck1x1(){const e=[];const c=document.querySelector('.chart-container-1x1');if(!c||c.offsetWidth!==1080||c.offsetHeight!==1080)e.push('画布必须为1080×1080');if(document.querySelector('.yz-watermark'))e.push('b.4禁止大型水印');if(!document.querySelector('.chart-logo-1x1 use[href="#yz-logo-icon"]'))e.push('缺少右上图形SVG logo');const checks=[['[data-role="body"]',40,'正文'],['[data-role="aux"]',28,'辅助文字'],['.chart-source',27,'脚注'],['.chart-part-num',24,'序号']];checks.forEach(([s,min,n])=>document.querySelectorAll(s).forEach(x=>{const z=parseFloat(getComputedStyle(x).fontSize);if(z<min-.01)e.push(n+'字号不足：'+z)}));if(!document.fonts.check('900 48px AliPuHui'))e.push('AliPuHui未加载');window.yzSelfCheck1x1Errors=e;document.documentElement.classList.toggle('yz-check-fail',!!e.length);document.getElementById('yz-selfcheck-banner').textContent=e.join('；');return !e.length}document.fonts.ready.then(()=>setTimeout(yzSelfCheck1x1,100));
</script>
"""


def base(title: str, body: str, source: str, part: str) -> str:
    sprite = f'<svg aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden"><defs>{SPRITE_INNER}</defs></svg>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1080"><title>{esc(title)}</title><style>{common_css()}</style></head><body>{sprite}<div id="yz-selfcheck-banner"></div><main class="chart-container-1x1"><div class="chart-header-1x1"><h1 class="chart-title-1x1" data-role="body">{esc(title)}</h1><div class="chart-logo-1x1"><svg viewBox="0 0 199 231" aria-label="娱乐资本论图形标识"><use href="#yz-logo-icon"></use></svg></div></div><div class="chart-body-1x1">{body}</div><div class="chart-footer-1x1"><div class="chart-source">{esc(source)}</div><div class="chart-part-num">{esc(part)}</div></div></main>{selfcheck_js()}</body></html>'''


def comment_page(title: str, quote: str, meta: str, poster: str, part: str) -> str:
    body = f'<article class="review-card"><div class="review-copy"><blockquote class="review-quote" data-role="body">“{esc(quote)}”</blockquote><p class="review-meta" data-role="aux">——{esc(meta)}</p></div><img class="review-poster" src="assets/posters/{esc(poster)}" alt="{esc(title)} 海报"></article>'
    return base(title, body, "来源：用户提供评论截图 OCR 与原文段落映射", part)


def heatmap_body(items: list[dict[str, str]]) -> str:
    dims = ["专业能力", "道德人格", "民族国家", "商业资本", "社会文化/性别", "身份符号"]
    head = "".join(f'<th data-role="aux">{esc(d)}</th>' for d in dims)
    data = []
    for row in items:
        cells = []
        for dimension in dims:
            value = int(row[dimension].rstrip("%")); alpha = 0.08 + 0.72 * value / 100; fg = "#fff" if value >= 58 else "#312e2e"
            cells.append(f'<td data-role="body" style="background:rgba(252,129,102,{alpha:.3f});color:{fg}">{value}%</td>')
        data.append(f'<tr><th class="row-head" data-role="body">{esc(row["年份"])}<br>{esc(row["作品"])}</th>{"".join(cells)}</tr>')
    return f'<table class="hm-table"><thead><tr><th class="row-head" data-role="body">作品</th>{head}</tr></thead><tbody>{"".join(data)}</tbody></table><div class="hm-legend" data-role="aux"><i class="hm-grad"></i>低占比　高占比</div>'


def professional_body(items: list[dict[str, str]]) -> str:
    legend = "".join(f'<span data-role="aux"><i style="background:{color}"></i>{esc(name)}</span>' for name, color in zip(F1_NAMES, F1_COLORS))
    rows_html = []
    for item in items:
        segments = []
        for key, color in zip(F1_KEYS, F1_COLORS):
            value = int(item[key]); label = f"{value}%" if value >= 18 else ""; light = " light" if color in {"#f6b65b", "#b8dba8", "#8ec6ce"} else ""
            segments.append(f'<span class="prof-seg{light}" data-role="body" style="width:{value}%;background:{color}">{label}</span>')
        rows_html.append(f'<section class="prof-row"><h2 class="prof-work" data-role="body">{esc(item["年份"])} {esc(item["作品"])}</h2><div class="prof-bar">{"".join(segments)}</div></section>')
    return f'<div class="prof-legend">{legend}</div><div class="prof-wrap">{"".join(rows_html)}</div>'


def dumbbell_body(data: list[dict[str, str]]) -> str:
    x0, x1, top, height = 260, 960, 88, 692
    row_y = [144 + index * 62 for index in range(10)]
    def x(value: float) -> float:
        return x0 + (x1 - x0) * value / 100
    pieces = [f'<svg class="dumbbell-svg" viewBox="0 0 1040 780" aria-label="热映期与近年回看同步哑铃图">']
    for pct in [0, 25, 50, 75, 100]:
        xp = x(pct); pieces.append(f'<line class="svg-axis" x1="{xp}" y1="{top}" x2="{xp}" y2="{height}"/><text class="svg-axis-text" data-role="aux" x="{xp}" y="46" text-anchor="middle">{pct}%</text>')
    grouped = {dimension: [row for row in data if row["维度"] == dimension] for dimension in COLORS}
    for index, name in enumerate(row["作品"] for row in grouped["专业能力"]):
        y = row_y[index]; pieces.append(f'<text class="svg-film" data-role="body" x="8" y="{y + 12}">{esc(name)}</text>')
        for offset, dimension in zip([-12, 0, 12], COLORS):
            row = grouped[dimension][index]; release = float(row["上映期占比%"]); recent = float(row["近年回看占比%"]); xa, xb = x(release), x(recent); color = COLORS[dimension]; yy = y + offset
            pieces.append(f'<line class="svg-base" x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" opacity=".25"/><line class="yz-db-line" x1="{min(xa, xb)}" y1="{yy}" x2="{max(xa, xb)}" y2="{yy}" stroke="{color}" stroke-width="5" opacity=".8"/><circle class="yz-db-dot" cx="{xa}" cy="{yy}" r="8" fill="#fff" stroke="{color}" stroke-width="4"/><circle class="yz-db-dot" cx="{xb}" cy="{yy}" r="8" fill="{color}"/>')
    pieces.append("</svg>")
    legend = "".join(f'<span class="legend-item" data-role="aux"><i class="legend-dot" style="background:{color}"></i>{dimension}</span>' for dimension, color in COLORS.items())
    legend += '<span class="legend-item" data-role="aux"><i class="legend-ring"></i>空心：热映期　实心：近年回看</span>'
    return f'<div class="dumbbell-stage">{"".join(pieces)}<div class="chart-legend">{legend}</div></div>'


def write(name: str, content: str) -> None:
    (R2 / name).write_text(content, encoding="utf-8")


def main() -> None:
    R2.mkdir(exist_ok=True)
    assets = R2 / "assets"
    if assets.exists() or assets.is_symlink():
        if assets.is_dir() and not assets.is_symlink():
            shutil.rmtree(assets)
        else:
            assets.unlink()
    shutil.copytree(ASSET_SOURCE, assets)
    for stem, title, quote, meta, poster, part in COMMENTS:
        write(f"{stem}.html", comment_page(title, quote, meta, poster, part))
    heat = rows("shenteng_works_heatmap.csv")
    for index, (lo, hi) in enumerate([(0, 5), (5, 10)], 1):
        write(f"img1-part{index}-styled.html", base("十部作品如何改写沈腾的形象", heatmap_body(heat[lo:hi]), "来源：豆瓣短评；官方表1底稿", f"{index}/2"))
    f1 = rows("f1_subdim_chart.csv")
    for index, (lo, hi) in enumerate([(0, 4), (4, 7), (7, 10)], 1):
        write(f"img2-part{index}-styled.html", base("专业能力评价焦点如何变化", professional_body(f1[lo:hi]), "来源：豆瓣短评；官方表2底稿", f"{index}/3"))
    db = rows("shenteng_dumbbell_chart.csv")
    write("img3-part1-styled.html", base("热映期与近年回看的评价对比", dumbbell_body(db), "来源：豆瓣短评；官方表3底稿", "1/1"))
    print("Generated 13 strict b.4 source HTML files (7 review / 2 heatmap / 3 professional / 1 dumbbell).")


if __name__ == "__main__":
    main()
