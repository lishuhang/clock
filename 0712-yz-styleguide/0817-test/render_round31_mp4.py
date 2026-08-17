from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "round3.1"
W = H = 1080
FPS = 24
DURATION = 4.5
FRAMES = int(FPS * DURATION)

C = {
    "paper": "#FFFFFF", "ink": "#1E2430", "muted": "#667085", "line": "#DFE4EC",
    "coral": "#FF6B54", "blue": "#4869F5", "teal": "#1FA487", "purple": "#8668A8",
    "gold": "#F3B51B", "pale_coral": "#FFF4F1", "pale_blue": "#EEF2FF", "pale_gold": "#FFF8E3",
    "track": "#EEF0F4", "trail": "#BFC9D6",
}
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {"regular": REG, "bold": BOLD, "black": BLACK}[weight]
    return ImageFont.truetype(path, size)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgba(value: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    return (*hex_rgb(value), max(0, min(255, int(round(255 * alpha)))))


def ease(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def in_at(t: float, start: float, length: float = 0.45) -> float:
    return ease((t - start) / length)


def layer(base: Image.Image) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    return overlay, ImageDraw.Draw(overlay)


def paste(base: Image.Image, overlay: Image.Image) -> None:
    base.alpha_composite(overlay)


def text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], value: str, size: int, color: str = C["ink"],
         weight: str = "regular", alpha: float = 1, anchor: str = "la", spacing: int = 4) -> None:
    draw.text(xy, value, font=font(size, weight), fill=rgba(color, alpha), anchor=anchor, spacing=spacing)


def rr(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], radius: float, fill: str, alpha: float = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=rgba(fill, alpha))


def fade_slide(draw: ImageDraw.ImageDraw, xy: tuple[float, float], value: str, size: int, t: float, start: float,
               color: str = C["ink"], weight: str = "regular", anchor: str = "la", distance: int = 26,
               spacing: int = 4) -> float:
    p = in_at(t, start)
    text(draw, (xy[0], xy[1] + (1 - p) * distance), value, size, color, weight, p, anchor, spacing)
    return p


def header(img: Image.Image, t: float, title: str, deck: str, title_size: int = 58) -> None:
    ov, d = layer(img)
    rr(d, (0, 0, W, 14), 0, C["coral"])
    fade_slide(d, (72, 68), "娱乐资本论 · 沈腾评论数据", 24, t, 0.05, C["coral"], "bold")
    fade_slide(d, (72, 126), title, title_size, t, 0.18, C["ink"], "black", spacing=2)
    # 逐帧渲染不具备浏览器的自然行宽处理；长副标题按保守行宽折行，保证视频端不裁字。
    deck_chunks = [deck[i:i + 30] for i in range(0, len(deck), 30)]
    if len(deck_chunks) > 1 and len(deck_chunks[-1]) <= 2:
        deck_chunks[-2] += deck_chunks[-1]
        deck_chunks.pop()
    deck_lines = "\n".join(deck_chunks)
    fade_slide(d, (72, 216), deck_lines, 29, t, 0.45, C["muted"], "regular", spacing=6)
    paste(img, ov)


def footer(img: Image.Image, source: str) -> None:
    d = ImageDraw.Draw(img)
    d.line((72, 984, 1008, 984), fill=hex_rgb(C["line"]), width=1)
    text(d, (72, 1011), f"数据：{source}", 18, C["muted"], "regular")
    text(d, (1008, 1011), "娱乐资本论", 24, C["coral"], "bold", anchor="ra")


def frame_01(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), rgba(C["paper"]))
    header(img, t, "好笑，是沈腾最稳定的能力入口", "2015–2018：早期三部作品中，专业能力评价首先指向喜剧。")
    ov, d = layer(img)
    fade_slide(d, (72, 343), "喜剧/搞笑，占专业能力评价的", 35, t, 0.80, C["coral"], "bold")
    rows = [("夏洛特烦恼", "2015", 78), ("羞羞的铁拳", "2017", 76), ("西虹市首富", "2018", 76)]
    for i, (work, year, val) in enumerate(rows):
        p = in_at(t, 1.05 + i * .32, .85)
        y = 420 + i * 118
        text(d, (72, y), work, 37, C["ink"], "bold", p)
        text(d, (72, y + 47), year, 24, C["muted"], "bold", p)
        rr(d, (385, y - 1, 1008, y + 65), 14, C["track"], p)
        width = 623 * val / 100 * p
        rr(d, (385, y - 1, 385 + width, y + 65), 14, C["coral"], p)
        if p > .18:
            shown = round(val * p)
            text(d, (407, y + 12), f"{shown}%", 34, C["paper"], "bold", p)
    p = in_at(t, 3.05)
    rr(d, (72, 806 + (1 - p) * 18, 1008, 955 + (1 - p) * 18), 20, C["pale_coral"], p)
    text(d, (108, 842 + (1 - p) * 18), "三部早期代表作均在 76% 以上。", 31, C["ink"], "bold", p)
    text(d, (108, 887 + (1 - p) * 18), "“好笑”是最稳定的能力入口。", 31, C["ink"], "bold", p)
    paste(img, ov)
    footer(img, "f1_subdim_chart.csv")
    return img.convert("RGB")


def metric(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], value: int, label: str, color: str, pale: str,
           t: float, start: float) -> None:
    p = in_at(t, start, .6)
    x1, y1, x2, y2 = box
    rr(d, (x1, y1 + (1 - p) * 30, x2, y2 + (1 - p) * 30), 22, pale, p)
    text(d, (x1 + 24, y1 + 32 + (1 - p) * 30), f"{round(value * p)}%", 82, color, "black", p)
    text(d, (x1 + 24, y1 + 143 + (1 - p) * 30), label, 30, C["ink"], "bold", p)


def frame_02(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), rgba(C["paper"]))
    header(img, t, "2019，观众开始谈论“好笑”以外", "一部《飞驰人生》，把喜剧、共情和作品整体同时推入评论中心。", 55)
    ov, d = layer(img)
    metric(d, (72, 388, 365, 630), 31, "喜剧/搞笑", C["coral"], C["pale_coral"], t, 1.0)
    metric(d, (393, 388, 686, 630), 25, "共情/感染力", C["blue"], C["pale_blue"], t, 1.28)
    metric(d, (714, 388, 1008, 630), 35, "剧本/节奏/整体", "#9C7000", C["pale_gold"], t, 1.56)
    p = in_at(t, 2.45)
    rr(d, (72, 710 + (1-p)*20, 1008, 866 + (1-p)*20), 20, "#F7F8FA", p)
    text(d, (106, 750 + (1-p)*20), "《飞驰人生》是一个转折：", 31, C["blue"], "bold", p)
    text(d, (106, 798 + (1-p)*20), "评论不再只谈“好不好笑”，", 31, C["ink"], "bold", p)
    text(d, (106, 842 + (1-p)*20), "开始谈热血、感动和作品整体。", 31, C["ink"], "bold", p)
    paste(img, ov)
    footer(img, "f1_subdim_chart.csv")
    return img.convert("RGB")


def panel(d: ImageDraw.ImageDraw, box: tuple[int,int,int,int], year: str, work: str, value: int, desc: str,
          color: str, pale: str, t: float, start: float) -> None:
    p = in_at(t, start, .72)
    x1,y1,x2,y2 = box
    rr(d, (x1, y1+(1-p)*35, x2, y2+(1-p)*35), 24, pale, p)
    text(d,(x1+32,y1+32+(1-p)*35),year,31,C["muted"],"bold",p)
    text(d,(x1+32,y1+76+(1-p)*35),work,35,C["ink"],"black",p)
    text(d,(x1+32,y1+166+(1-p)*35),f"{round(value*p)}%",90,color,"black",p)
    text(d,(x1+32,y1+274+(1-p)*35),desc,27,C["ink"],"bold",p)


def frame_03(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), rgba(C["paper"]))
    header(img, t, "喜剧会回弹，但不再是唯一焦点", "2024 与 2026 的对照：沈腾没有放弃喜剧，评论的注意力却变得更复杂。", 54)
    ov, d = layer(img)
    panel(d,(72,385,521,735),"2024","《抓娃娃》",73,"喜剧/搞笑",C["coral"],C["pale_coral"],t,1.0)
    panel(d,(559,385,1008,735),"2026","《欢迎来龙餐馆》",4,"喜剧/搞笑",C["blue"],C["pale_blue"],t,1.32)
    p = in_at(t, 2.25)
    text(d,(591,678+(1-p)*20),"演技 25% · 剧本/整体 57%",23,C["blue"],"bold",p)
    p = in_at(t,2.75)
    rr(d,(72,792+(1-p)*20,1008,920+(1-p)*20),20,"#F7F8FA",p)
    text(d,(106,828+(1-p)*20),"不是直线“去喜剧化”。喜剧会回弹，",29,C["ink"],"bold",p)
    text(d,(106,873+(1-p)*20),"但在《欢迎来龙餐馆》，更多能力被看见。",29,C["coral"],"bold",p)
    paste(img, ov)
    footer(img, "f1_subdim_chart.csv")
    return img.convert("RGB")


def issue_row(d: ImageDraw.ImageDraw, y: int, work: str, dimension: str, hot: float, current: float,
              delta: float, color: str, t: float, start: float) -> None:
    p = in_at(t, start, .55)
    text(d, (72, y), work, 35, C["ink"], "black", p)
    text(d, (72, y + 48), dimension, 25, color, "bold", p)
    x1, x2 = 412, 808
    hot_x = x1 + (x2 - x1) * hot / 12
    current_x = x1 + (x2 - x1) * current / 12
    rr(d,(x1,y+20,x2,y+42),12,C["trail"],p)
    move = in_at(t, start + .58, 1.25)
    traveling_x = hot_x + (current_x-hot_x)*move
    left, right = sorted((hot_x, traveling_x))
    rr(d,(left,y+20,right,y+42),12,C["blue"],p*.75)
    d.ellipse((hot_x-18,y+13,hot_x+18,y+49),fill=rgba(C["coral"],p))
    d.ellipse((traveling_x-18,y+13,traveling_x+18,y+49),fill=rgba(C["blue"],p))
    p_text = in_at(t, start + 1.85, .42)
    text(d,(1008,y-6),f"{hot:.1f}% → {current:.1f}%",31,C["ink"],"black",p_text,anchor="ra")
    text(d,(1008,y+46),f"{delta:+.1f}pp",24,C["muted"],"bold",p_text,anchor="ra")


def frame_04(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), rgba(C["paper"]))
    header(img, t, "热映期的议题，不一定会留成演员标签", "已收到的官方补充数据：热映期与近期回看中，民族国家与商业资本讨论均显著回落。", 51)
    ov, d = layer(img)
    issue_row(d, 430, "《独行月球》", "民族国家（F3）", 10.5, 1.2, -9.3, C["purple"], t, .96)
    issue_row(d, 652, "《超能一家人》", "商业资本（F4）", 11.3, 4.8, -6.5, "#A77B00", t, 1.45)
    p = in_at(t, 3.10)
    rr(d,(72,830+(1-p)*18,1008,936+(1-p)*18),20,"#F7F8FA",p)
    text(d,(106,865+(1-p)*18),"热映期的题材性议题会退潮。",27,C["ink"],"bold",p)
    text(d,(106,907+(1-p)*18),"对作品的讨论，不等于演员的稳定标签。",27,C["blue"],"bold",p)
    paste(img, ov)
    footer(img, "chart_04_f4_f3.csv")
    return img.convert("RGB")


CARDS = [
    ("01-comedy-anchor-motion", frame_01),
    ("02-beyond-comedy-motion", frame_02),
    ("03-comedy-not-only-focus-motion", frame_03),
    ("04-issue-fade-motion", frame_04),
]


def encode(frames: Path, output: Path) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "frame_%04d.png"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-r", str(FPS), str(output)]
    subprocess.run(cmd, check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height,r_frame_rate",
                            "-of", "json", str(output)], check=True, capture_output=True, text=True)
    output.with_suffix(".mp4.json").write_text(probe.stdout, encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="round31-pil-frames-") as temp:
        temp_dir = Path(temp)
        for name, renderer in CARDS:
            frame_dir = temp_dir / name
            frame_dir.mkdir()
            for i in range(FRAMES):
                t = i / FPS
                renderer(t).save(frame_dir / f"frame_{i:04d}.png", compress_level=1)
            encode(frame_dir, OUT / f"{name}.mp4")
            print(f"Rendered {name}.mp4")


if __name__ == "__main__":
    main()
