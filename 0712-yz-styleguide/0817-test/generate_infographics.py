from __future__ import annotations

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

W = 1080
COLORS = {
    "ink": "#1E2430",
    "muted": "#667085",
    "light": "#F2F4F7",
    "grid": "#E4E7EC",
    "coral": "#FF6B54",
    "blue": "#4869F5",
    "teal": "#1FA487",
    "purple": "#8668A8",
    "gold": "#F3B51B",
    "paper": "#FFFFFF",
    "tint": "#FFF4F1",
}

FONT = "'Noto Sans CJK SC','Noto Sans SC','Microsoft YaHei',sans-serif"
DIMENSIONS = [
    ("喜剧/搞笑占比%", "喜剧/搞笑", COLORS["coral"]),
    ("演技/声台形表占比%", "演技/声台形表", COLORS["blue"]),
    ("共情/感染力占比%", "共情/感染力", COLORS["teal"]),
    ("角色塑造/突破占比%", "角色塑造", COLORS["purple"]),
    ("剧本/节奏/整体占比%", "剧本/节奏/整体", COLORS["gold"]),
]


def load_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def esc(v: object) -> str:
    return html.escape(str(v))


def txt(x: float, y: float, text: str, size: int = 24, fill: str | None = None,
        weight: int = 400, anchor: str = "start", extra: str = "") -> str:
    fill = fill or COLORS["ink"]
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{esc(text)}</text>')


def rect(x: float, y: float, w: float, h: float, fill: str, r: float = 0,
         stroke: str | None = None, sw: float = 1, extra: str = "") -> str:
    stroke_s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" '
            f'fill="{fill}" rx="{r}"{stroke_s} {extra}/>' )


def line(x1: float, y1: float, x2: float, y2: float, stroke: str,
         sw: float = 1, dash: str | None = None, extra: str = "") -> str:
    dash_s = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{dash_s} {extra}/>' )


def circle(cx: float, cy: float, r: float, fill: str, stroke: str | None = None,
           sw: float = 1, extra: str = "") -> str:
    stroke_s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{stroke_s} {extra}/>'


def wrap(text: str, limit: int) -> list[str]:
    # Chinese text is naturally character-oriented; punctuation stays with its line.
    return [text[i:i + limit] for i in range(0, len(text), limit)] or [""]


def paragraph(x: float, y: float, text: str, limit: int, size: int = 22,
              line_h: int = 34, fill: str | None = None, weight: int = 400,
              anchor: str = "start") -> str:
    return "".join(txt(x, y + i * line_h, part, size, fill, weight, anchor)
                   for i, part in enumerate(wrap(text, limit)))


def page(title: str, subtitle: str, content: str, height: int, footnote: str,
         motion: bool = False, square: bool = False) -> str:
    motion_css = ""
    if motion:
        motion_css = """
        @keyframes rise { from { opacity:0; transform:translateY(24px) } to { opacity:1; transform:translateY(0) } }
        .anim { animation: rise .72s cubic-bezier(.2,.8,.2,1) both; }
        .d1 { animation-delay: .08s; } .d2 { animation-delay: .22s; }
        .d3 { animation-delay: .36s; } .d4 { animation-delay: .50s; }
        @media (prefers-reduced-motion: reduce) { .anim { animation:none; } }
        """
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{esc(title)}">
    <style>
      {motion_css}
      text {{ dominant-baseline: alphabetic; }}
    </style>
    {rect(0, 0, W, height, COLORS['paper'])}
    {rect(0, 0, W, 14, COLORS['coral'])}
    {txt(72, 86, '娱乐资本论 · 数据可视化', 20, COLORS['coral'], 700)}
    {txt(72, 150, title, 44 if square else 48, COLORS['ink'], 800)}
    {paragraph(72, 190, subtitle, 48 if square else 48, 21, 32, COLORS['muted'])}
    {content}
    {line(72, height - 104, W - 72, height - 104, COLORS['grid'], 1)}
    {paragraph(72, height - 70, footnote, 90 if not square else 76, 15, 23, COLORS['muted'])}
    {txt(W - 72, height - 34, '娱乐资本论', 18, COLORS['coral'], 800, 'end')}
</svg>'''
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>html,body{{margin:0;background:#EEF1F5}}body{{display:flex;justify-content:center}}svg{{display:block;width:1080px;height:auto;background:#fff}}@media(max-width:1080px){{svg{{width:100%;height:auto}}}}</style></head>
<body>{svg}</body></html>'''


def legend(x: float, y: float, dims: list[tuple[str, str, str]], font: int = 17) -> str:
    out = []
    cursor = x
    for _, label, color in dims:
        out.append(rect(cursor, y - 15, 14, 14, color, 3))
        out.append(txt(cursor + 21, y - 2, label, font, COLORS['muted'], 600))
        cursor += 21 + len(label) * font + 23
    return "".join(out)


def stage_label(y: float, title: str, year_range: str, color: str = COLORS["coral"]) -> str:
    return (rect(72, y - 28, 10, 50, color, 5) + txt(100, y, title, 23, COLORS["ink"], 800) +
            txt(100, y + 28, year_range, 17, COLORS["muted"], 500))


def professional_long(f1: list[dict[str, str]]) -> str:
    height = 1920
    x0, bar_w = 292, 650
    y0, row_h = 440, 112
    parts = [legend(72, 260, DIMENSIONS)]
    for tick in [0, 25, 50, 75, 100]:
        x = x0 + bar_w * tick / 100
        parts += [line(x, 360, x, 1565, COLORS['grid'], 1, "4 7"), txt(x, 345, f"{tick}%", 16, COLORS['muted'], 500, "middle")]
    stage_rows = {0: ("喜剧演员定型期", "2015–2018"), 3: ("形象扩容与争议期", "2019–2023"), 6: ("转型被看见", "2023–2026")}
    for i, row in enumerate(f1):
        # 每个阶段前保留独立标题留白，防止跨阶段标题压住上一行数据。
        stage_offset = 0 if i < 3 else (58 if i < 6 else 116)
        y = y0 + i * row_h + stage_offset
        if i in stage_rows:
            label, years = stage_rows[i]
            parts.append(stage_label(y - 34, label, years, COLORS["coral"] if i == 0 else (COLORS["blue"] if i == 3 else COLORS["teal"])))
        bar_y = y + 32
        if i > 0:
            parts.append(line(72, y - 9, W - 72, y - 9, COLORS['grid'], 1))
        parts += [txt(72, y + 32, row['作品'], 24, COLORS['ink'], 700), txt(72, y + 57, row['年份'], 17, COLORS['muted'], 500)]
        cursor = x0
        for key, label, color in DIMENSIONS:
            pct = float(row[key])
            # 轴严格以 0–100% 绘制；逐项取整后合计 99%–102% 的边缘差异如实保留。
            w = bar_w * pct / 100
            parts.append(rect(cursor, bar_y, w, 40, color, 4 if cursor == x0 else 0))
            if pct >= 8:
                parts.append(txt(cursor + w / 2, bar_y + 27, f"{pct:.0f}", 16,
                                 COLORS['paper'] if color != COLORS['gold'] else COLORS['ink'], 800, 'middle'))
            cursor += w
        parts += [txt(W - 72, bar_y + 29, f"非喜剧 {row['非喜剧(S2+S3+S4)占比%']}%", 18, COLORS['blue'], 700, 'end')]
        if row['作品'] == '抓娃娃':
            parts += [rect(x0 + 365, y + 77, 284, 34, '#FFF2EC', 17), txt(x0 + 507, y + 100, '喜剧关注回升，不是线性转型', 15, COLORS['coral'], 700, 'middle')]
        if row['作品'] == '欢迎来龙餐馆':
            parts += [rect(x0, y + 77, 650, 34, '#EEF2FF', 17), txt(x0 + 325, y + 100, '4% 喜剧 · 25% 演技 · 57% 剧本/节奏/整体', 15, COLORS['blue'], 700, 'middle')]
    parts += [rect(72, 1650, 936, 120, COLORS['tint'], 14), txt(100, 1690, '从“好笑”到“好笑以外”：变化从来不是直线。', 25, COLORS['ink'], 800),
              paragraph(100, 1725, '《抓娃娃》让喜剧讨论回升；《欢迎来龙餐馆》则把注意力推向表演与作品整体。', 58, 19, 30, COLORS['muted'])]
    foot = '数据：用户提供 f1_subdim_chart.csv（每部作品专业能力评论的子维度占比）。各项为整数百分比，逐项取整后合计可能存在微小偏差。'
    return page('沈腾，观众并没有忘记他好笑', '十部作品的“专业能力”评价焦点。喜剧始终在场，但被讨论的能力越来越复杂。', ''.join(parts), height, foot)


def issue_long(f4f3: list[dict[str, str]]) -> str:
    height = 1650
    x0, plot_w = 310, 600
    max_v = 12.0
    panels = [("民族国家（F3）", 'hot_F3_pct', 'latest_F3_pct', COLORS['purple']),
              ("商业资本（F4）", 'hot_F4_pct', 'latest_F4_pct', COLORS['gold'])]
    parts = []
    ybase = 300
    for panel_i, (label, hot_key, latest_key, panel_color) in enumerate(panels):
        top = ybase + panel_i * 565
        parts += [rect(72, top, 12, 48, panel_color, 6), txt(102, top + 25, label, 29, COLORS['ink'], 800),
                  txt(102, top + 53, '热映期（橙）→ 近期回看（蓝）｜同一作品、同一 0–12% 横轴', 18, COLORS['muted'])]
        for tick in [0, 3, 6, 9, 12]:
            x = x0 + plot_w * tick / max_v
            parts += [line(x, top + 88, x, top + 440, COLORS['grid'], 1, '4 6'), txt(x, top + 79, f'{tick}%', 15, COLORS['muted'], 500, 'middle')]
        for i, row in enumerate(f4f3):
            y = top + 123 + i * 32
            hot, latest = float(row[hot_key]), float(row[latest_key])
            xh, xl = x0 + plot_w * hot / max_v, x0 + plot_w * latest / max_v
            parts += [txt(72, y + 5, row['电影'], 17, COLORS['ink'], 600),
                      line(min(xh, xl), y, max(xh, xl), y, '#B9C2D0', 5),
                      circle(xh, y, 8, COLORS['coral']), circle(xl, y, 8, COLORS['blue']),
                      txt(936, y + 5, f'{hot:.1f}→{latest:.1f}%', 16, COLORS['muted'], 600, 'end')]
        if label.startswith('民族'):
            parts += [rect(72, top + 468, 936, 66, '#F7F5FC', 12),
                      txt(96, top + 510, '最大回落：〈独行月球〉10.5% → 1.2%（−9.3pp）', 20, COLORS['purple'], 800)]
        else:
            parts += [rect(72, top + 468, 936, 66, '#FFF9E8', 12),
                      txt(96, top + 510, '最大回落：〈超能一家人〉11.3% → 4.8%（−6.5pp）', 20, '#9C7000', 800)]
    parts += [rect(72, 1422, 936, 94, COLORS['light'], 14),
              paragraph(98, 1458, '低频维度不等于没有变化；本图用相同尺度呈现，避免把个位数比例放大成主叙事。', 65, 18, 28, COLORS['muted'])]
    foot = '数据：用户提供 chart_04_f4_f3.csv。每部作品热映期/近期的有效样本数分别见源表（热映期 151–160；近期 76–97）。'
    return page('热映期退潮后，题材性议题如何回落', '官方补充数据：民族国家（F3）与商业资本（F4）。变化更多指向作品题材与上映语境，而非沈腾的稳定个人标签。', ''.join(parts), height, foot)


def stage_card(f1: list[dict[str, str]], title: str, subtitle: str, indices: list[int], note: str, color: str) -> str:
    height = 1080
    x0, bar_w, y0 = 90, 900, 325
    parts = [legend(90, 260, DIMENSIONS, 15)]
    for i, index in enumerate(indices):
        row = f1[index]
        y = y0 + i * 145
        parts += [txt(90, y, f"{row['年份']}  {row['作品']}", 26, COLORS['ink'], 800),
                  txt(990, y, f"非喜剧 {row['非喜剧(S2+S3+S4)占比%']}%", 18, COLORS['blue'], 700, 'end'),
                  rect(x0, y + 28, bar_w, 50, COLORS['light'], 8)]
        cursor = x0
        for key, _, c in DIMENSIONS:
            pct = float(row[key])
            # 轴严格以 0–100% 绘制；逐项取整后合计 99%–102% 的边缘差异如实保留。
            w = bar_w * pct / 100
            parts.append(rect(cursor, y + 28, w, 50, c, 0))
            if pct >= 8:
                parts.append(txt(cursor + w/2, y + 60, f'{pct:.0f}', 17,
                                 COLORS['paper'] if c != COLORS['gold'] else COLORS['ink'], 800, 'middle'))
            cursor += w
    note_y = y0 + len(indices) * 145 + 8
    parts += [rect(90, note_y, 900, 118, '#FFF5F2' if color == COLORS['coral'] else '#EEF8F6', 16),
              txt(118, note_y + 40, note, 23, COLORS['ink'], 800),
              paragraph(118, note_y + 74, '百分比为官方原始整数值；色块长度使用统一刻度，不对每行重新归一化。', 58, 17, 25, COLORS['muted'])]
    foot = '数据：f1_subdim_chart.csv｜专业能力评论的 5 个子维度。色块含义见上方图例。'
    return page(title, subtitle, ''.join(parts), height, foot, square=True)


def trend_card(f1: list[dict[str, str]]) -> str:
    height = 1080
    # Four key rows make the non-linear story easy to scan in a square format.
    keys = [f1[i] for i in [3, 6, 7, 9]]
    x0, y0, plot_w, plot_h = 130, 365, 815, 350
    series = [
        ('喜剧/搞笑占比%', '喜剧/搞笑', COLORS['coral']),
        ('演技/声台形表占比%', '演技/声台形表', COLORS['blue']),
        ('剧本/节奏/整体占比%', '剧本/节奏/整体', COLORS['gold']),
    ]
    parts = [rect(90, 275, 900, 50, COLORS['tint'], 12), txt(540, 308, '不是直线“去喜剧化”，而是更多能力被看见', 21, COLORS['ink'], 800, 'middle')]
    for tick in [0, 25, 50, 75, 100]:
        y = y0 + plot_h - tick / 100 * plot_h
        parts += [line(x0, y, x0 + plot_w, y, COLORS['grid'], 1, '4 6'), txt(x0 - 18, y + 5, f'{tick}%', 15, COLORS['muted'], 500, 'end')]
    for i, row in enumerate(keys):
        x = x0 + i * plot_w / (len(keys) - 1)
        parts += [line(x, y0, x, y0 + plot_h, COLORS['grid'], 1), txt(x, y0 + plot_h + 38, f"{row['年份']}\n", 16, COLORS['muted'], 600, 'middle'), txt(x, y0 + plot_h + 61, row['作品'], 18, COLORS['ink'], 700, 'middle')]
    for key, label, color in series:
        points = []
        for i, row in enumerate(keys):
            x = x0 + i * plot_w / (len(keys) - 1)
            y = y0 + plot_h - float(row[key]) / 100 * plot_h
            points.append((x, y, row[key]))
        d = ' '.join(f'{x:.1f},{y:.1f}' for x,y,_ in points)
        parts.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
        for x, y, value in points:
            parts += [circle(x, y, 9, COLORS['paper'], color, 5), txt(x, y - 18, value, 16, color, 800, 'middle')]
    parts += [legend(225, 805, [(a,b,c) for a,b,c in series], 18),
              paragraph(90, 875, '2024 年〈抓娃娃〉的喜剧回升提醒我们：沈腾并非放弃喜剧；2026 年〈欢迎来龙餐馆〉则让演技与作品整体进入评论中心。', 42, 20, 31, COLORS['muted'])]
    foot = '数据：f1_subdim_chart.csv。抽取四部关键作品展示趋势；完整十片细目见 round1 主图。'
    return page('“好笑”之外，被讨论的能力越来越多', '从〈飞驰人生〉到〈欢迎来龙餐馆〉：三条线保留作品之间的回弹，而不是把它讲成一条直线。', ''.join(parts), height, foot, square=True)


def issue_card(f4f3: list[dict[str, str]]) -> str:
    height = 1080
    selections = [
        (next(r for r in f4f3 if r['电影'] == '独行月球'), 'hot_F3_pct', 'latest_F3_pct', '民族国家（F3）', COLORS['purple']),
        (next(r for r in f4f3 if r['电影'] == '超能一家人'), 'hot_F4_pct', 'latest_F4_pct', '商业资本（F4）', COLORS['gold']),
        (next(r for r in f4f3 if r['电影'] == '欢迎来龙餐馆'), 'hot_F3_pct', 'latest_F3_pct', '民族国家（F3）', COLORS['purple']),
    ]
    parts = [rect(90, 280, 900, 70, '#F7F8FA', 16), txt(540, 323, '橙＝热映期　蓝＝近期回看　同一 0–12% 比例尺', 20, COLORS['muted'], 700, 'middle')]
    x0, plot_w = 260, 610
    for tick in [0, 3, 6, 9, 12]:
        x = x0 + plot_w * tick / 12
        parts += [line(x, 385, x, 845, COLORS['grid'], 1, '4 6'), txt(x, 374, f'{tick}%', 15, COLORS['muted'], 500, 'middle')]
    for i, (row, hkey, lkey, label, color) in enumerate(selections):
        y = 470 + i * 150
        hot, late = float(row[hkey]), float(row[lkey])
        xh, xl = x0 + plot_w * hot / 12, x0 + plot_w * late / 12
        delta = late - hot
        parts += [txt(90, y - 25, row['电影'], 26, COLORS['ink'], 800), txt(90, y + 5, label, 17, color, 700),
                  line(min(xh,xl), y, max(xh,xl), y, '#B9C2D0', 8), circle(xh, y, 14, COLORS['coral']), circle(xl, y, 14, COLORS['blue']),
                  txt(924, y + 7, f'{hot:.1f}→{late:.1f}%\n', 21, COLORS['ink'], 800, 'end'),
                  txt(924, y + 33, f'{delta:+.1f}pp', 18, COLORS['muted'], 600, 'end')]
    parts += [rect(90, 895, 900, 70, '#F7F8FA', 16), paragraph(118, 928, '议题会随上映热度退潮；对作品的讨论不应直接等同于对演员本人的稳定标签。', 64, 19, 29, COLORS['muted'])]
    foot = '数据：chart_04_f4_f3.csv。仅展示已收到的 F3/F4 官方数据；完整表 3 仍需补齐另两维度的两期比例。'
    return page('热映期的议题，不一定会留成演员标签', '三部作品的代表性变化：回看时，题材性讨论普遍更弱，评论重新回到作品与表演。', ''.join(parts), height, foot, square=True)


def write(path: Path, contents: str) -> None:
    path.write_text(contents, encoding='utf-8')


def motion_html(static_html: str) -> str:
    # SVG elements use CSS classes for staggered entry; the static end state remains fully readable.
    return static_html.replace('<svg ', '<svg class="anim d1" ').replace('</style></head>',
        '.anim{animation:rise .75s ease-out both}@keyframes rise{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}@media(prefers-reduced-motion:reduce){.anim{animation:none}}</style></head>')


def main() -> None:
    f1 = load_csv('f1_subdim_chart.csv')
    f4f3 = load_csv('chart_04_f4_f3.csv')
    # Round 1: editorial long-form main graphics.
    round1 = ROOT / 'round1'
    write(round1 / '01-professional-focus.html', professional_long(f1))
    write(round1 / '02-issue-fade.html', issue_long(f4f3))
    # Round 2: social square splits.
    round2 = ROOT / 'round2'
    card1 = stage_card(f1, '好笑，是沈腾最稳定的能力入口', '2015–2018：三部作品中，喜剧/搞笑都稳定在 76% 以上。', [0, 1, 2], '喜剧演员定型期：优势清晰，评价维度也更集中。', COLORS['coral'])
    card2 = trend_card(f1)
    card3 = issue_card(f4f3)
    write(round2 / '01-comedy-anchor.html', card1)
    write(round2 / '02-beyond-comedy.html', card2)
    write(round2 / '03-issue-fade.html', card3)
    # Round 3: animation-ready variants of the three social cards.
    round3 = ROOT / 'round3'
    write(round3 / '01-comedy-anchor-motion.html', motion_html(card1))
    write(round3 / '02-beyond-comedy-motion.html', motion_html(card2))
    write(round3 / '03-issue-fade-motion.html', motion_html(card3))
    print('Generated 8 HTML infographics.')


if __name__ == '__main__':
    main()
