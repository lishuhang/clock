#!/usr/bin/env python3
"""43 页 canvas 全量黑底换肤（S02/S03/S14/S23 跳过——将整体重写）。
规则见 make_shots_v3 时代的 v3 规格：底#131110/面板#1e1b19/正文#f2efec/次级#b5aea9/线#3a3634，品牌橙保留。
"""
import glob
import os
import re

CANVAS = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/canvas"
ASSETS = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/assets"
SKIP = {"S02", "S03", "S14", "S23"}  # 将重写


def make_white_assets():
    # SVG 白色副本
    for src, dst, fills in [
        ("logo-icon.svg", "logo-icon-white.svg", ("#221815", "#000000")),
        ("logo-text.svg", "logo-text-white.svg", ("#221815", "#000000")),
    ]:
        s = open(f"{ASSETS}/{src}", encoding="utf-8").read()
        for f in fills:
            s = s.replace(f'fill="{f}"', 'fill="#f2efec"')
        open(f"{ASSETS}/{dst}", "w", encoding="utf-8").write(s)
    # 小云雀 logo 反色副本
    from PIL import Image
    im = Image.open(f"{ASSETS}/logos/xiaoyunque.png").convert("RGBA")
    r, g, b, a = im.split()
    from PIL import ImageOps
    rgb = ImageOps.invert(Image.merge("RGB", (r, g, b)))
    ro, go, bo = rgb.split()
    Image.merge("RGBA", (ro, go, bo, a)).save(f"{ASSETS}/logos/xiaoyunque_w.png")
    print("[assets] 白色副本: logo-icon-white.svg / logo-text-white.svg / xiaoyunque_w.png")


def chip_inversion(html):
    """background:var(--ink) 的深底白字块 → 浅色芯片(浅底深字)。"""
    def fix_block(m):
        blk = m.group(0)
        blk = blk.replace("background:var(--ink)", "background:__CHIP__")
        blk = re.sub(r"(color\s*:\s*)(#fff\b|#ffffff|#f2efec)", r"\1#131110", blk)
        return blk
    # CSS 规则块
    html = re.sub(r"\{[^{}]*background:var\(--ink\)[^{}]*\}", fix_block, html)
    # 行内 style
    html = re.sub(r'style="[^"]*background:var\(--ink\)[^"]*"', fix_block, html)
    return html


REPLACEMENTS = [
    # 渐变（先于通用色替换）
    (r"linear-gradient\(180deg,#ffffff,#f2efec\)", "linear-gradient(180deg,#242020,#1a1716)"),
    (r"linear-gradient\(180deg,#ffffff,\s*#f2efec\)", "linear-gradient(180deg,#242020,#1a1716)"),
    (r"linear-gradient\(160deg,#fff 0%,#fdf1ec 100%\)", "linear-gradient(160deg,#242020 0%,rgba(252,129,102,.10) 100%)"),
    (r"linear-gradient\(90deg,#e7e3e1,#d8d2ce\)", "linear-gradient(90deg,#3a3634,#4a4441)"),
    (r"linear-gradient\(180deg,#eef4f7,#dfe9ef\)", "linear-gradient(180deg,#1d2226,#171b1e)"),
    (r"linear-gradient\(180deg,#ffffff,#f6f0eb\)", "linear-gradient(180deg,#242020,#1a1715)"),
    (r"linear-gradient\(180deg,#f3e2bb,#e6cf9d\)", "linear-gradient(180deg,#332a1a,#28200f)"),
    # 背景
    (r"#f6f4f2", "#131110"),
    (r"(background(?:-color)?\s*:\s*)#fff(?:fff)?\b", r"\1#1e1b19"),
    (r"(background(?:-color)?\s*:\s*)#f2efec\b", r"\1#1e1b19"),
    (r"(background(?:-color)?\s*:\s*)#e7e3e1\b", r"\1#2a2624"),
    (r"(background(?:-color)?\s*:\s*)#eee9e5\b", r"\1#171412"),
    (r"(background(?:-color)?\s*:\s*)#f8f6f4\b", r"\1#171412"),
    # 文字色
    (r"(color\s*:\s*)#312e2e\b", r"\1#f2efec"),
    (r"(color\s*:\s*)#6b6666\b", r"\1#b5aea9"),
    (r"(color\s*:\s*)#9a9595\b", r"\1#8f8984"),
    # 线/分隔/浅装饰通用
    (r"#e7e3e1\b", "#3a3634"),
    (r"#d8d2ce\b", "#4a4441"),
    (r"#c9c4c2\b", "#9c948f"),
    (r"#fdf1ec\b", "rgba(252,129,102,.12)"),
    (r"#fff4f0\b", "rgba(252,129,102,.10)"),
    # 语义色提亮
    (r"#2e8b57\b", "#4caf7d"),
    (r"#8a6d3b\b", "#e0b571"),
    (r"#b98a3e\b", "#d9a952"),
    # 阴影/轨道
    (r"rgba\(49,46,46,", "rgba(0,0,0,"),
    (r"rgba\(255,255,255,\.96\)", "rgba(19,17,16,.96)"),
    # CSS 变量上下文替换
    (r"color\s*:\s*var\(--ink\)", "color:#f2efec"),
    (r"color\s*:\s*var\(--ink-2\)", "color:#b5aea9"),
    (r"var\(--line\)", "#3a3634"),
    # logo 白色副本
    (r"logo-icon\.svg", "logo-icon-white.svg"),
    (r"logo-text\.svg", "logo-text-white.svg"),
    (r"logos/xiaoyunque\.png", "logos/xiaoyunque_w.png"),
]


def convert():
    make_white_assets()
    report = []
    for f in sorted(glob.glob(f"{CANVAS}/S*.html")):
        sid = os.path.basename(f)[:3]
        if sid in SKIP:
            report.append((sid, "skip(重写)"))
            continue
        html = open(f, encoding="utf-8").read()
        html = chip_inversion(html)
        n = 0
        for pat, rep in REPLACEMENTS:
            html, k = re.subn(pat, rep, html)
            n += k
        html = html.replace("__CHIP__", "#f2efec")
        open(f, "w", encoding="utf-8").write(html)
        report.append((sid, f"{n} 处"))
    for sid, r in report:
        print(f"  {sid}: {r}")


if __name__ == "__main__":
    convert()
