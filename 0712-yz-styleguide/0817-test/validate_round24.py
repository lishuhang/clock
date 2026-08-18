from __future__ import annotations

"""Blocker-style verification for the Shen Teng infographic b.4 / c.4 set.

This accepts neither source-only motion nor a correctly sized but stale video.
It executes the b.4 DOM self-check in Chromium, verifies the official CSV/OCR
mappings in the HTML, and probes every c.4 MP4 for the c-skill timeline.
"""

import csv
import json
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parent
R24 = ROOT / "round2.4"
R34 = ROOT / "round3.4"
DATA = ROOT / "round1.2" / "data"
OUT = R24 / "evidence" / "final_animation_validation.json"

COMMENTS = [
    ("《夏洛特烦恼》", "男性视角的意淫", "豆瓣用户，2015-10-01，4星，2665 有用", "xialuo.jpg"),
    ("《独行月球》", "好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。", "豆瓣用户，2022-07-29，3星，7805 有用", "duxing.jpg"),
    ("《日不落酒店》", "各种夸张和尴尬，还用沈腾做幌子。", "豆瓣用户，2021-03-19，2星，28 有用", "ribuluo.jpg"),
    ("《日不落酒店》", "看到沈腾的名字立即选座无脑买的。", "豆瓣用户，2021-03-19，2星，551 有用", "ribuluo.jpg"),
    ("《夏洛特烦恼》", "作为女性，对于这种中年男人的意淫完全接受不了。", "豆瓣用户，2015-10-01，2星，8823 有用", "xialuo.jpg"),
    ("《欢迎来龙餐馆》", "腾哥是我们这一辈的星爷😭", "抖音用户，3天前·湖南，37.3万赞", "longcanguan.jpg"),
    ("《欢迎来龙餐馆》", "内娱你欠沈腾一个实至名归的影帝。", "抖音用户，3天前·江苏，9.5万赞", "longcanguan.jpg"),
]
DIMENSIONS = ["专业能力", "道德人格", "民族国家", "商业资本", "社会文化/性别", "身份符号"]
F1_KEYS = ["喜剧/搞笑占比%", "演技/声台形表占比%", "共情/感染力占比%", "角色塑造/突破占比%", "剧本/节奏/整体占比%"]
FORBIDDEN_MOTION = ["overlay_crop", "clip-path:inset", "mask:", "white-overlay", "center-mask", "#fff;position:absolute;inset:0"]


def rows(filename: str) -> list[dict[str, str]]:
    with (DATA / filename).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pct(style: str, property_name: str) -> float:
    found = re.search(rf"{re.escape(property_name)}\s*:\s*(-?\d+(?:\.\d+)?)%", style)
    if not found:
        raise ValueError(f"{property_name} percentage missing from {style!r}")
    return float(found.group(1))


def chromium_selfcheck(path: Path) -> tuple[bool, str]:
    process = subprocess.run([
        "chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=1800", "--window-size=1080,1080", "--dump-dom", path.resolve().as_uri(),
    ], text=True, capture_output=True, timeout=20)
    dom = process.stdout
    failed = re.search(r'<html[^>]*class=["\'][^"\']*yz-check-fail', dom) is not None
    return process.returncode == 0 and not failed and "function yzSelfCheck1x1" in dom, process.stderr[-600:]


def video_info(path: Path) -> dict[str, str | int]:
    doc = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames", "-show_entries", "format=duration", "-of", "json", str(path),
    ]))
    stream = doc["streams"][0]
    return {"file": path.name, "codec": stream["codec_name"], "width": stream["width"], "height": stream["height"], "fps": stream["r_frame_rate"], "frames": stream["nb_frames"], "duration": doc["format"]["duration"]}


def main() -> None:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    def require(name: str, condition: bool, detail: object | None = None) -> None:
        checks[name] = bool(condition)
        if detail is not None:
            details[name] = detail

    html24 = sorted(R24.glob("*-styled.html"))
    html34 = sorted(R34.glob("*-motion.html"))
    mp4s = sorted(R34.glob("*.mp4"))
    expected_names = {f"comment-part{i}-styled.html" for i in range(1, 8)} | {f"img1-part{i}-styled.html" for i in range(1, 3)} | {f"img2-part{i}-styled.html" for i in range(1, 4)} | {"img3-part1-styled.html"}
    require("b4_exactly_13_expected_html", {path.name for path in html24} == expected_names, [path.name for path in html24])
    require("c4_has_13_matching_motion_html", {path.name.removesuffix("-motion.html") + ".html" for path in html34} == expected_names, [path.name for path in html34])

    # b.4 structural/self-check execution and preview specs.
    png_specs: dict[str, list[int]] = {}
    for path in html24:
        text = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(text, "html.parser")
        png = path.with_suffix(".png")
        if png.exists():
            with Image.open(png) as image:
                png_specs[png.name] = [image.width, image.height]
        selfcheck_pass, selfcheck_stderr = chromium_selfcheck(path)
        require(f"b4_selfcheck_executed::{path.name}", selfcheck_pass, selfcheck_stderr)
        require(f"b4_preview_1080::{path.name}", png_specs.get(png.name) == [1080, 1080], png_specs.get(png.name))
        require(f"b4_canvas_logo_footer::{path.name}", soup.select_one(".chart-container-1x1") is not None and soup.select_one('.chart-logo-1x1 use[href="#yz-logo-icon"]') is not None and soup.select_one(".chart-source") is not None and soup.select_one(".chart-part-num") is not None)
        require(f"b4_no_watermark::{path.name}", soup.select_one(".yz-watermark") is None and soup.select_one('use[href="#yz-logo-vertical"]') is None)
        require(f"b4_local_alipuhui::{path.name}", "font-family:AliPuHui" in text and all(item in text for item in ["font-weight:400", "font-weight:700", "font-weight:900"]) and "noto" not in text.lower())
        require(f"b4_required_size_contract::{path.name}", all(item in text for item in ["font-size:40px", "font-size:28px", "font-size:27px", "font-size:24px", "function yzSelfCheck1x1()"]))

    # The seven requested review units must be one full-height card, left quote/right correct poster.
    comment_ok = True
    comment_details = []
    for index, expected in enumerate(COMMENTS, 1):
        movie, quote, meta, poster = expected
        path = R24 / f"comment-part{index}-styled.html"
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        card = soup.select_one(".review-card")
        image = soup.select_one("img.review-poster")
        actual = {
            "title": soup.select_one(".chart-title-1x1").get_text(strip=True) if soup.select_one(".chart-title-1x1") else None,
            "quote": soup.select_one(".review-quote").get_text(strip=True) if soup.select_one(".review-quote") else None,
            "meta": soup.select_one(".review-meta").get_text(strip=True) if soup.select_one(".review-meta") else None,
            "poster": image.get("src") if image else None,
        }
        comment_details.append(actual)
        comment_ok = comment_ok and card is not None and actual["title"] == movie and quote in (actual["quote"] or "") and meta in (actual["meta"] or "") and actual["poster"] == f"assets/posters/{poster}"
    require("b4_review_quote_poster_and_ocr_mapping", comment_ok, comment_details)

    # Table 1 must remain exactly two 5-work cards and retain all official cells.
    heat_source = rows("shenteng_works_heatmap.csv")
    heat_ok = True
    heat_detail: list[dict[str, object]] = []
    for part, expected in enumerate([heat_source[:5], heat_source[5:]], 1):
        soup = BeautifulSoup((R24 / f"img1-part{part}-styled.html").read_text(encoding="utf-8"), "html.parser")
        actual_rows = soup.select(".hm-table tbody tr")
        values = []
        if len(actual_rows) == 5:
            for node, source in zip(actual_rows, expected):
                cells = node.select("td")
                shown = [int(re.search(r"\d+", cell.get_text()).group()) for cell in cells]
                values.append(shown)
                heat_ok = heat_ok and node.select_one(".row-head").get_text(" ", strip=True).replace(" ", "") == f'{source["年份"]}{source["作品"]}' and shown == [int(source[key].rstrip("%")) for key in DIMENSIONS]
        else:
            heat_ok = False
        heat_detail.append({"part": part, "rows": len(actual_rows), "values": values})
    require("b4_table1_exact_official_values_and_5plus5", heat_ok, heat_detail)

    # Table 2 has three deliberate low-density groups (4 / 3 / 3) and exact segment widths.
    f1_source = rows("f1_subdim_chart.csv")
    f1_ok = True
    f1_detail: list[int] = []
    for part, expected in enumerate([f1_source[:4], f1_source[4:7], f1_source[7:]], 1):
        soup = BeautifulSoup((R24 / f"img2-part{part}-styled.html").read_text(encoding="utf-8"), "html.parser")
        actual_rows = soup.select(".prof-row")
        f1_detail.append(len(actual_rows))
        if len(actual_rows) != len(expected):
            f1_ok = False
            continue
        for node, source in zip(actual_rows, expected):
            widths = [int(pct(segment.get("style", ""), "width")) for segment in node.select(".prof-seg")]
            f1_ok = f1_ok and node.select_one(".prof-work").get_text(" ", strip=True) == f'{source["年份"]} {source["作品"]}' and widths == [int(source[key]) for key in F1_KEYS]
    require("b4_table2_exact_official_values_and_density_split", f1_ok, f1_detail)

    # Table 3: one SVG, all ten works × three dimensions on one 0–100 scale.
    db_source = rows("shenteng_dumbbell_chart.csv")
    db_soup = BeautifulSoup((R24 / "img3-part1-styled.html").read_text(encoding="utf-8"), "html.parser")
    svg = db_soup.select_one("svg.dumbbell-svg")
    film_names = [node.get_text(strip=True) for node in db_soup.select(".svg-film")]
    actual_dots = db_soup.select(".yz-db-dot")
    expected_film_names = [row["作品"] for row in db_source if row["维度"] == "专业能力"]
    db_ok = svg is not None and film_names == expected_film_names and len(actual_dots) == 60 and all(text in (svg.get_text(" ", strip=True) if svg else "") for text in ["0%", "25%", "50%", "75%", "100%"])
    require("b4_table3_one_synchronous_svg_full_scale", db_ok, {"films": film_names, "dot_count": len(actual_dots)})

    # c.4 sources must be directly derived from b.4 plus self-element animations, never a page-level mask.
    c_source = "\n".join(path.read_text(encoding="utf-8") for path in html34)
    require("c4_no_mask_or_center_white_overlay", all(token not in c_source for token in FORBIDDEN_MOTION), [token for token in FORBIDDEN_MOTION if token in c_source])
    require("c4_required_element_motion_hooks", all(token in c_source for token in ["yz-type-char", "yz-bloom", "yzGrowX", "yz-db-line", "yz-db-dot", "reused-round34-round39-element-motion"]))
    require("c4_comment_poster_then_typewriter", "review-poster{opacity:0;animation:yzFade .7s ease-out .65s forwards}" in c_source and "animationDelay=(1.42+index*.045)" in c_source)
    require("c4_heatmap_left_to_right_bloom", "cells.forEach((cell,index)=>{ cell.classList.add('yz-bloom'); cell.style.animationDelay=(.62+index*.07)+'s'; })" in c_source)
    require("c4_sync_dumbbell_primitives", "const lines=[...svg.querySelectorAll('line')]" in c_source and "const dots=[...svg.querySelectorAll('circle')]" in c_source)

    # Video specs: 30 fps, H.264, exact 1080 1:1 and 480 frames / 16 seconds.
    video_specs = [video_info(path) for path in mp4s]
    require("c4_13_mp4s", len(mp4s) == 13, [path.name for path in mp4s])
    required_video = lambda item: item["codec"] == "h264" and item["width"] == 1080 and item["height"] == 1080 and item["fps"] == "30/1" and str(item["frames"]) == "480" and abs(float(str(item["duration"])) - 16.0) < 0.01
    require("c4_video_specs_16s_30fps_480f", bool(video_specs) and all(required_video(item) for item in video_specs), video_specs)
    manifest_path = R34 / "recording_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    spec = manifest.get("specification", {})
    manifest_ok = spec == {"fps": 30, "entrance_frames": 180, "hold_frames": 120, "exit_frames": 180, "total_frames": 480, "duration_seconds": 16.0, "capture_selector": ".chart-container-1x1"} and len(manifest.get("videos", [])) == 13 and all(item.get("capture_rect", {}).get("width") == 1080 and item.get("capture_rect", {}).get("height") == 1080 for item in manifest.get("videos", []))
    require("c4_container_capture_manifest", manifest_ok, manifest)

    result = {
        "scope": "Shen Teng infographic b.4 / c.4",
        "counts": {"round24_html": len(html24), "round24_preview_png": len(list(R24.glob("*-styled.png"))), "round34_motion_html": len(html34), "round34_mp4": len(mp4s)},
        "preview_specs": png_specs,
        "video_specs": video_specs,
        "checks": checks,
        "details": details,
        "all_pass": all(checks.values()),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_pass"]:
        raise SystemExit("b.4/c.4 validation failed; see round2.4/evidence/final_animation_validation.json")


if __name__ == "__main__":
    main()
