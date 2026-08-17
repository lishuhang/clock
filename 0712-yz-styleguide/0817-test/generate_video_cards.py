from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "round2.1"
MOTION = ROOT / "round3.1"

COLORS = {
    "ink": "#1E2430", "muted": "#667085", "line": "#DFE4EC", "paper": "#FFFFFF",
    "coral": "#FF6B54", "blue": "#4869F5", "teal": "#1FA487", "purple": "#8668A8",
    "gold": "#F3B51B", "tint": "#FFF4F1", "pale_blue": "#EEF2FF", "pale_gold": "#FFF8E3",
}

BASE_CSS = f"""
:root {{ --ink:{COLORS['ink']}; --muted:{COLORS['muted']}; --line:{COLORS['line']}; --paper:{COLORS['paper']}; --coral:{COLORS['coral']}; --blue:{COLORS['blue']}; --teal:{COLORS['teal']}; --purple:{COLORS['purple']}; --gold:{COLORS['gold']}; }}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; width:1080px; height:1080px; overflow:hidden; background:var(--paper); }}
body {{ font-family:'Noto Sans CJK SC','Noto Sans SC','Microsoft YaHei',sans-serif; color:var(--ink); }}
.card {{ position:relative; width:1080px; height:1080px; overflow:hidden; background:#fff; padding:68px 72px 58px; }}
.card::before {{ content:''; position:absolute; left:0; top:0; width:100%; height:14px; background:var(--coral); }}
.kicker {{ color:var(--coral); font-weight:800; letter-spacing:.06em; font-size:24px; line-height:1; }}
h1 {{ position:relative; z-index:3; font-size:58px; line-height:1.18; letter-spacing:-.04em; margin:26px 0 12px; font-weight:900; }}
.deck {{ position:relative; z-index:3; max-width:900px; font-size:29px; line-height:1.45; color:var(--muted); margin:0; font-weight:500; }}
.brand {{ position:absolute; z-index:4; right:72px; bottom:48px; color:var(--coral); font-size:24px; font-weight:900; }}
.source {{ position:absolute; z-index:4; left:72px; bottom:50px; color:var(--muted); font-size:18px; font-weight:500; }}
.rule {{ position:absolute; left:72px; right:72px; bottom:96px; height:1px; background:var(--line); }}
.note {{ font-size:24px; line-height:1.45; color:var(--muted); font-weight:500; }}
.pill {{ display:inline-flex; align-items:center; border-radius:999px; padding:12px 20px; font-size:23px; font-weight:800; }}
.big-num {{ font-family:'Noto Sans',sans-serif; font-size:116px; font-weight:900; line-height:.85; letter-spacing:-.07em; }}
.big-label {{ font-size:32px; font-weight:800; line-height:1.25; }}
.static .in {{ opacity:1 !important; transform:none !important; clip-path:inset(0 0 0 0) !important; }}
.motion .in {{ opacity:0; transform:translateY(22px); }}
.motion .a1 {{ animation:rise .45s .12s cubic-bezier(.2,.8,.2,1) forwards; }}
.motion .a2 {{ animation:rise .55s .52s cubic-bezier(.2,.8,.2,1) forwards; }}
.motion .a3 {{ animation:rise .60s 1.14s cubic-bezier(.2,.8,.2,1) forwards; }}
.motion .a4 {{ animation:rise .60s 1.80s cubic-bezier(.2,.8,.2,1) forwards; }}
.motion .a5 {{ animation:rise .60s 2.40s cubic-bezier(.2,.8,.2,1) forwards; }}
.motion .draw {{ clip-path:inset(0 100% 0 0); animation:reveal .72s 1.18s cubic-bezier(.2,.8,.2,1) forwards; }}
.motion .late {{ opacity:0; animation:fade .45s 3.5s ease forwards; }}
@keyframes rise {{ to {{ opacity:1; transform:translateY(0); }} }}
@keyframes fade {{ to {{ opacity:1; }} }}
@keyframes reveal {{ to {{ clip-path:inset(0 0 0 0); }} }}
"""


def wrap_html(title: str, deck: str, content: str, source: str, motion: bool) -> str:
    klass = "motion" if motion else "static"
    return f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=1080,initial-scale=1\"><title>{title}</title><style>{BASE_CSS}</style></head>
<body class=\"{klass}\"><main class=\"card\"><div class=\"kicker in a1\">娱乐资本论 · 沈腾评论数据</div><h1 class=\"in a1\">{title}</h1><p class=\"deck in a2\">{deck}</p>{content}<div class=\"rule\"></div><div class=\"source\">数据：{source}</div><div class=\"brand\">娱乐资本论</div></main></body></html>"""


def card_01(motion: bool) -> str:
    rows = [("夏洛特烦恼", "2015", 78), ("羞羞的铁拳", "2017", 76), ("西虹市首富", "2018", 76)]
    row_html = []
    for i, (work, year, value) in enumerate(rows):
        delay = f"a{3 + min(i,2)}"
        row_html.append(f"""<div class=\"row in {delay}\"><div class=\"row-name\"><strong>{work}</strong><span>{year}</span></div><div class=\"bar\"><div class=\"fill draw\" style=\"width:{value}%\"></div><b>{value}%</b></div></div>""")
    content = f"""
<style>
.hero-tag {{ position:absolute; top:330px; left:72px; color:var(--coral); font-size:35px; font-weight:900; }}
.rows {{ position:absolute; top:410px; left:72px; right:72px; display:grid; gap:35px; }}
.row {{ display:grid; grid-template-columns:285px 1fr; align-items:center; gap:28px; }}
.row-name strong {{ display:block; font-size:37px; line-height:1.1; }} .row-name span {{ display:block; margin-top:8px; color:var(--muted); font-size:24px; font-weight:700; }}
.bar {{ position:relative; height:66px; border-radius:14px; background:#F1F3F6; overflow:visible; }} .fill {{ position:absolute; left:0; top:0; height:100%; border-radius:14px; background:var(--coral); }} .bar b {{ position:absolute; top:13px; font-size:34px; color:#fff; padding-left:22px; z-index:2; }}
.bottom {{ position:absolute; top:805px; left:72px; right:72px; padding:30px 34px; border-radius:20px; background:#FFF4F1; font-size:31px; line-height:1.45; font-weight:800; }}
</style><div class=\"hero-tag in a2\">喜剧/搞笑，占专业能力评价的</div><div class=\"rows\">{''.join(row_html)}</div><div class=\"bottom late\">三部早期代表作均在 76% 以上。<br>“好笑”是最稳定的能力入口。</div>"""
    return wrap_html("好笑，是沈腾最稳定的能力入口", "2015–2018：早期三部作品中，专业能力评价首先指向喜剧。", content, "f1_subdim_chart.csv", motion)


def card_02(motion: bool) -> str:
    content = """
<style>
.metrics { position:absolute; top:370px; left:72px; right:72px; display:flex; gap:20px; } .metric { flex:1; min-height:238px; padding:28px 24px; border-radius:22px; background:#F7F8FA; } .metric:nth-child(1){background:#FFF4F1}.metric:nth-child(2){background:#EEF2FF}.metric:nth-child(3){background:#FFF8E3}.metric .big-num{color:var(--coral)}.metric:nth-child(2) .big-num{color:var(--blue)}.metric:nth-child(3) .big-num{color:#A77B00}.metric .big-label{margin-top:18px;}.work {position:absolute; left:72px; right:72px; top:700px; padding:29px 34px; border-radius:20px; background:#F7F8FA; font-size:31px;line-height:1.44; font-weight:800;} .work strong{color:var(--blue)}
</style><section class="metrics"><div class="metric in a3"><div class="big-num">31%</div><div class="big-label">喜剧/搞笑</div></div><div class="metric in a4"><div class="big-num">25%</div><div class="big-label">共情/感染力</div></div><div class="metric in a5"><div class="big-num">35%</div><div class="big-label">剧本/节奏/整体</div></div></section><div class="work late"><strong>《飞驰人生》</strong>是一个转折：<br>评论不再只谈“好不好笑”，开始谈热血、感动和作品整体。</div>"""
    return wrap_html("2019，观众开始谈论“好笑”以外", "一部《飞驰人生》，把喜剧、共情和作品整体同时推入评论中心。", content, "f1_subdim_chart.csv", motion)


def card_03(motion: bool) -> str:
    content = """
<style>
.split {position:absolute; top:355px; left:72px; right:72px; display:grid; grid-template-columns:1fr 1fr; gap:26px;} .side{min-height:350px; padding:36px 34px; border-radius:24px;} .left{background:#FFF4F1}.right{background:#EEF2FF}.year{font-size:31px;font-weight:900;color:var(--muted)}.work{font-size:35px;font-weight:900;margin-top:8px}.big-num{margin-top:54px}.left .big-num{color:var(--coral)}.right .big-num{color:var(--blue)}.stat{font-size:29px;font-weight:800;margin-top:16px}.divider{position:absolute;top:770px;left:72px;right:72px;padding:26px 32px;background:#F7F8FA;border-radius:20px;font-size:29px;line-height:1.45;font-weight:800}.divider strong{color:var(--coral)}
</style><section class="split"><div class="side left in a3"><div class="year">2024</div><div class="work">《抓娃娃》</div><div class="big-num">73%</div><div class="stat">喜剧/搞笑</div></div><div class="side right in a4"><div class="year">2026</div><div class="work">《欢迎来龙餐馆》</div><div class="big-num">4%</div><div class="stat">喜剧/搞笑</div><div class="stat" style="color:var(--blue)">演技 25% · 剧本/整体 57%</div></div></section><div class="divider late">不是直线“去喜剧化”。<strong>喜剧会回弹</strong>，但在《欢迎来龙餐馆》，更多能力被看见。</div>"""
    return wrap_html("喜剧会回弹，但不再是唯一焦点", "2024 与 2026 的对照：沈腾没有放弃喜剧，评论的注意力却变得更复杂。", content, "f1_subdim_chart.csv", motion)


def card_04(motion: bool) -> str:
    content = """
<style>
.item{position:absolute;left:72px;right:72px;display:grid;grid-template-columns:310px 1fr 180px;gap:24px;align-items:center}.one{top:390px}.two{top:630px}.name{font-size:35px;line-height:1.23;font-weight:900}.name span{display:block;color:var(--purple);font-size:25px;margin-top:10px}.two .name span{color:#A77B00}.track{height:22px;background:#CAD2DE;border-radius:20px;position:relative}.track .run{height:22px;position:absolute;left:0;top:0;border-radius:20px;background:linear-gradient(90deg,var(--coral),var(--blue));}.dot{position:absolute;top:50%;width:38px;height:38px;border-radius:50%;transform:translate(-50%,-50%)}.hot{background:var(--coral)}.recent{background:var(--blue)}.value{font-size:31px;text-align:right;font-weight:900}.value span{display:block;font-size:24px;color:var(--muted);margin-top:7px}.caption{position:absolute;left:72px;right:72px;top:840px;padding:26px 32px;border-radius:20px;background:#F7F8FA;font-size:28px;line-height:1.45;font-weight:800}.caption b{color:var(--blue)}
</style><div class="item one in a3"><div class="name">《独行月球》<span>民族国家（F3）</span></div><div class="track draw"><div class="run" style="width:87.5%"></div><i class="dot hot" style="left:87.5%"></i><i class="dot recent" style="left:10%"></i></div><div class="value">10.5% → 1.2%<span>−9.3pp</span></div></div><div class="item two in a4"><div class="name">《超能一家人》<span>商业资本（F4）</span></div><div class="track draw"><div class="run" style="width:94%"></div><i class="dot hot" style="left:94%"></i><i class="dot recent" style="left:40%"></i></div><div class="value">11.3% → 4.8%<span>−6.5pp</span></div></div><div class="caption late">热映期的题材性议题会退潮。<b>对作品的讨论，不等于演员的稳定标签。</b></div>"""
    return wrap_html("热映期的议题，不一定会留成演员标签", "已收到的官方补充数据：热映期与近期回看中，民族国家与商业资本讨论均显著回落。", content, "chart_04_f4_f3.csv", motion)


def main() -> None:
    STATIC.mkdir(exist_ok=True)
    MOTION.mkdir(exist_ok=True)
    cards = [card_01, card_02, card_03, card_04]
    names = ["01-comedy-anchor", "02-beyond-comedy", "03-comedy-not-only-focus", "04-issue-fade"]
    for name, build in zip(names, cards, strict=True):
        (STATIC / f"{name}.html").write_text(build(False), encoding="utf-8")
        (MOTION / f"{name}-motion.html").write_text(build(True), encoding="utf-8")
    print("Generated 4 large-type static cards and 4 animation HTML cards.")


if __name__ == "__main__":
    main()
