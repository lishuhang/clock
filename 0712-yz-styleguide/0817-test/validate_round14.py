from __future__ import annotations

"""Blocker-style acceptance for Shen Teng infographic a.4 canonical static charts.

The script intentionally re-renders first: a stale PNG cannot be accepted after HTML
changes.  It then verifies the source DOM/CSS contract, executed yzSelfCheck results,
output dimensions, and the values sourced from the three official CSV files.
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parent
R14 = ROOT / "round1.4"
DATA = ROOT / "round1.2" / "data"
RENDER = ROOT / "render_round14_canonical.py"
REPORT = R14 / "validation_report.json"

EXPECTED = {
    "img1-a-heatmap-styled.html": {
        "png": "img1-a-heatmap-styled.png",
        "title": "十部作品如何改写沈腾的形象",
        "source": "数据来源：豆瓣短评；官方表1底稿",
        "components": ["hm-table", "hm-legend"],
    },
    "img2-a-professional-styled.html": {
        "png": "img2-a-professional-styled.png",
        "title": "专业能力评价焦点如何变化",
        "source": "数据来源：豆瓣短评；官方表2底稿",
        "components": ["sb-wrap", "sb-row", "sb-bar", "sb-seg"],
    },
    "img3-a-dumbbell-styled.html": {
        "png": "img3-a-dumbbell-styled.png",
        "title": "热映期与近年回看的评价对比",
        "source": "数据来源：豆瓣短评；官方表3底稿",
        "components": ["dumbbell-track", "dumbbell-line", "dumbbell-dot", "axis-scale"],
    },
    "comments-a-styled.html": {
        "png": "comments-a-styled.png",
        "title": "豆瓣与抖音中的代表性评论",
        "source": "数据来源：用户提供评论截图 OCR 与原文段落映射",
        "components": ["tc-grid", "tc-card", "tc-work", "tc-platform", "tc-quote", "tc-meta"],
    },
}

DIMENSIONS = ["专业能力", "道德人格", "民族国家", "商业资本", "社会文化/性别", "身份符号"]
F1_KEYS = ["喜剧/搞笑占比%", "演技/声台形表占比%", "共情/感染力占比%", "角色塑造/突破占比%", "剧本/节奏/整体占比%"]
EXPECTED_COMMENTS = [
    ("《夏洛特烦恼》", "豆瓣用户", "男性视角的意淫", "2015-10-01 · 4星 · 2665 有用"),
    ("《独行月球》", "豆瓣用户", "好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。", "2022-07-29 · 3星 · 7805 有用"),
    ("《日不落酒店》", "豆瓣用户", "各种夸张和尴尬，还用沈腾做幌子。", "2021-03-19 · 2星 · 28 有用"),
    ("《日不落酒店》", "豆瓣用户", "看到沈腾的名字立即选座无脑买的。", "2021-03-19 · 2星 · 551 有用"),
    ("《夏洛特烦恼》", "豆瓣用户", "作为女性，对于这种中年男人的意淫完全接受不了。", "2015-10-01 · 2星 · 8823 有用"),
    ("《欢迎来龙餐馆》", "抖音用户", "腾哥是我们这一辈的星爷😭", "3天前 · 湖南 · 37.3万赞"),
    ("《欢迎来龙餐馆》", "抖音用户", "内娱你欠沈腾一个实至名归的影帝。", "3天前 · 江苏 · 9.5万赞"),
]


def rows(filename: str) -> list[dict[str, str]]:
    with (DATA / filename).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def style_number(style: str, key: str) -> float:
    found = re.search(rf"{re.escape(key)}\s*:\s*(-?\d+(?:\.\d+)?)%", style)
    if not found:
        raise ValueError(f"missing {key} percentage in {style!r}")
    return float(found.group(1))


def main() -> None:
    # A source edit must never be accepted using old screenshots or an old self-check log.
    rendered = subprocess.run([sys.executable, str(RENDER)], cwd=ROOT, text=True, capture_output=True)
    render_log = {"returncode": rendered.returncode, "stdout": rendered.stdout, "stderr": rendered.stderr}
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    def require(name: str, condition: bool, detail: object | None = None) -> None:
        checks[name] = bool(condition)
        if detail is not None:
            details[name] = detail

    require("fresh_canonical_render", rendered.returncode == 0, render_log)
    html_paths = sorted(R14.glob("*-styled.html"))
    require("four_expected_html_only", {p.name for p in html_paths} == set(EXPECTED), [p.name for p in html_paths])
    require("all_font_assets_present", all((R14 / "assets" / "fonts" / filename).is_file() for filename in [
        "AlibabaPuHuiTi-3-55-Regular.ttf", "AlibabaPuHuiTi-3-85-Bold.ttf", "AlibabaPuHuiTi-3-115-Black.ttf"
    ]))

    # Native execution report is not merely a string search: every HTML's yzSelfCheck ran in Chromium.
    render_report_path = R14 / "canonical_render_validation.json"
    native_report = json.loads(render_report_path.read_text(encoding="utf-8")) if render_report_path.exists() else []
    expected_report_names = set(EXPECTED)
    native_index = {item.get("file"): item for item in native_report}
    require("yzSelfCheck_executed_for_each_file", set(native_index) == expected_report_names, native_report)
    for filename in EXPECTED:
        item = native_index.get(filename, {})
        require(f"yzSelfCheck_pass::{filename}", item.get("pass") is True and item.get("errors") == [], item)
        require(f"computed_a4_tokens::{filename}", item.get("svgUse") == "#yz-logo-vertical" and item.get("fontReady") is True and item.get("rect", {}).get("width") == 900 and item.get("style", {}).get("watermark") == "420px" and item.get("style", {}).get("opacity") == "0.1" and item.get("style", {}).get("logo") == "62px", item)

    png_dimensions: dict[str, list[int]] = {}
    for filename, spec in EXPECTED.items():
        path = R14 / filename
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        soup = BeautifulSoup(text, "html.parser")
        png = R14 / spec["png"]
        if png.exists():
            with Image.open(png) as image:
                png_dimensions[png.name] = [image.width, image.height]
        require(f"png_exists::{png.name}", png.exists())
        require(f"png_container_crop::{png.name}", png_dimensions.get(png.name, [0, 0])[0] == 900 and png_dimensions.get(png.name, [0, 0])[1] > 900, png_dimensions.get(png.name))
        require(f"required_nodes::{filename}", all(soup.select_one(selector) for selector in [".chart-container", ".yz-watermark", ".chart-title", ".chart-body", ".chart-source", ".yz-logo-svg"]))
        require(f"canonical_selfcheck_embedded::{filename}", "function yzSelfCheck()" in text)
        require(f"a4_container_and_watermark_css::{filename}", all(token in text for token in ["width:900px", "z-index:9999!important", "width:420px!important", "opacity:.10!important", "height:62px!important", "z-index:auto!important"]))
        require(f"AliPuHui_only::{filename}", all(token in text for token in ["font-family:'AliPuHui'", "font-weight:400", "font-weight:700", "font-weight:900"]) and "noto" not in text.lower())
        require(f"vertical_and_horizontal_svg_symbols::{filename}", soup.select_one('.yz-watermark use[href="#yz-logo-vertical"]') is not None and soup.select_one('.yz-logo-svg use[href="#yz-logo-horizontal"]') is not None)
        require(f"no_unresolved_placeholder::{filename}", not any(token in text for token in ["【TITLE_HERE】", "【CHART_BODY_HERE】", "【SOURCE_FOOTER_HERE】"]))
        title = soup.select_one(".chart-title").get_text(" ", strip=True) if soup.select_one(".chart-title") else ""
        source = soup.select_one(".chart-source").get_text(" ", strip=True) if soup.select_one(".chart-source") else ""
        require(f"title_exact_and_no_chart_prefix::{filename}", title == spec["title"] and not re.match(r"^图\s*\d+", title), title)
        require(f"source_exact::{filename}", source == spec["source"], source)
        require(f"shared_components::{filename}", all(soup.select_one(f".{component}") for component in spec["components"]))

    # a.4 requires cards below the watermark to retain translucency, not opaque white blocks.
    comment_text = (R14 / "comments-a-styled.html").read_text(encoding="utf-8")
    require("comment_cards_translucent_under_watermark", "background:rgba(255,255,255,.92)" in comment_text)

    # Table 1: six dimensions / ten official rows, exact visible integer values.
    heat_soup = BeautifulSoup((R14 / "img1-a-heatmap-styled.html").read_text(encoding="utf-8"), "html.parser")
    heat_expected = rows("shenteng_works_heatmap.csv")
    heat_actual = heat_soup.select(".hm-table tbody tr")
    heat_ok = len(heat_actual) == len(heat_expected)
    if heat_ok:
        for actual, source in zip(heat_actual, heat_expected):
            cells = actual.select("td")
            shown = [int(re.search(r"\d+", cell.get_text()).group()) for cell in cells[1:]]
            expected = [int(source[dimension].rstrip("%")) for dimension in DIMENSIONS]
            label = cells[0].get_text(" ", strip=True)
            heat_ok = heat_ok and label == f'{source["年份"]} {source["作品"]}' and shown == expected
    require("official_csv_table1_heatmap_exact", heat_ok, {"rows": len(heat_actual), "expected_rows": len(heat_expected)})

    # Table 2: five F1 stacked segments / ten official rows, exact segment width percentages.
    f1_soup = BeautifulSoup((R14 / "img2-a-professional-styled.html").read_text(encoding="utf-8"), "html.parser")
    f1_expected = rows("f1_subdim_chart.csv")
    f1_actual = f1_soup.select(".sb-row")
    f1_ok = len(f1_actual) == len(f1_expected)
    if f1_ok:
        for actual, source in zip(f1_actual, f1_expected):
            label = actual.select_one(".sb-label").get_text(" ", strip=True)
            shown = [int(style_number(segment.get("style", ""), "width")) for segment in actual.select(".sb-seg")]
            expected = [int(source[key]) for key in F1_KEYS]
            f1_ok = f1_ok and label == f'{source["年份"]} {source["作品"]}' and shown == expected
    require("official_csv_table2_f1_segments_exact", f1_ok, {"rows": len(f1_actual), "expected_rows": len(f1_expected)})

    # Table 3: 10 works × 3 dimensions, two exact timepoint dots and delta labels per row.
    db_soup = BeautifulSoup((R14 / "img3-a-dumbbell-styled.html").read_text(encoding="utf-8"), "html.parser")
    db_source = rows("shenteng_dumbbell_chart.csv")
    # The HTML groups panels by dimension, while the source CSV is work-major.
    db_expected = [row for dimension in ["专业能力", "民族国家", "社会文化/性别"] for row in db_source if row["维度"] == dimension]
    db_actual: list[tuple[str, str, float, float, str]] = []
    for panel in db_soup.select(".db-panel"):
        dimension = panel.select_one("h2").get_text(" ", strip=True)
        for row in panel.select(".db-row"):
            dots = row.select(".dumbbell-dot")
            value = row.select_one(".db-value").get_text(" ", strip=True)
            if len(dots) == 2:
                db_actual.append((dimension, row.select_one(".db-label").get_text(" ", strip=True), style_number(dots[0].get("style", ""), "left"), style_number(dots[1].get("style", ""), "left"), value))
    db_ok = len(db_actual) == len(db_expected)
    if db_ok:
        for actual, source in zip(db_actual, db_expected):
            dimension, work, release, recent, value = actual
            expected_value = f'{float(source["上映期占比%"]):.1f}% → {float(source["近年回看占比%"]):.1f}% {source["变化Δpp"]}pp'
            db_ok = db_ok and dimension == source["维度"] and work == source["作品"] and abs(release - float(source["上映期占比%"])) < 0.001 and abs(recent - float(source["近年回看占比%"])) < 0.001 and "".join(value.split()) == "".join(expected_value.split())
    require("official_csv_table3_dumbbells_exact", db_ok, {"rows": len(db_actual), "expected_rows": len(db_expected)})

    # OCR-derived presentation data: retain the exact quote/platform/metadata while omitting internal evidence filenames.
    comment_soup = BeautifulSoup(comment_text, "html.parser")
    cards = comment_soup.select(".tc-card")
    comment_ok = len(cards) == len(EXPECTED_COMMENTS) and "640(3).png" not in comment_text and "小红书" not in comment_text
    if comment_ok:
        for card, expected in zip(cards, EXPECTED_COMMENTS):
            movie, platform, quote, meta = expected
            comment_ok = comment_ok and card.select_one(".tc-work").get_text(strip=True) == movie and card.select_one(".tc-platform").get_text(strip=True) == platform and quote in card.select_one(".tc-quote").get_text(" ", strip=True) and card.select_one(".tc-meta").get_text(" ", strip=True) == meta
    require("ocr_comments_platform_and_movie_mapping_exact", comment_ok, {"cards": len(cards), "expected": len(EXPECTED_COMMENTS)})

    result = {
        "scope": "Shen Teng infographic a.4 canonical static charts",
        "counts": {"html": len(html_paths), "png": len(list(R14.glob("*-styled.png")) )},
        "png_dimensions": png_dimensions,
        "checks": checks,
        "details": details,
        "all_pass": all(checks.values()),
    }
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_pass"]:
        raise SystemExit("a.4 validation failed; see round1.4/validation_report.json")


if __name__ == "__main__":
    main()
