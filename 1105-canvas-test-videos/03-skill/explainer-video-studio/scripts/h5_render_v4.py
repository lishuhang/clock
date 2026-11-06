#!/usr/bin/env python3
"""受控时钟截帧器 v3（重建版，修复 v2 丢失）：
# 通用用法: python3 h5_render_v4.py <shots.json> <canvas_dir> <frames_dir> [--only S01,S02]
# shots.json 条目需含 id/dur；canvas 页面需实现 window.renderFrame(payload) 与 yzCheck()


用法:
  python3 h5_render_v3.py <shots.json> <canvas_dir> <frames_dir> [--fps 30] [--only S01,S02]

改进（对齐 2026-11-06 三大 bug 修复）：
1. 帧时刻 = 入场窗(1.5s@30fps) ∪ 基础网格(2fps全程) ∪ 页面SHOOT_DENSE连续段 ∪ 尾帧
   —— v1 只截前1.5s导致 data-t>1.5 的元素全部丢失；
2. 每镜输出 render-manifest.json（帧文件↔镜内时刻），由 assemble 阶段做精确映射；
3. --transparent 清单：S02/S03 等透明叠层页（body 透明 + omit_background 截图），
   视频背景由 ffmpeg 单独合成；
4. 幂等续跑：每镜 .done 标记。
铁律：禁 Playwright 实时录屏（掉帧→音画错位）；每镜截帧前必须 yzCheck()==compliant。
"""
import argparse
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

FPS = 30
ENTRY = 1.5
GRID = 2  # 基础网格 fps
TRANSPARENT_SHOTS = {"S02a", "S02b", "S03a", "S03b", "S04", "S24b"}  # 视频背景叠层页(透明截帧)


def shot_times(dur, dense, entrances=None):
    """计算一镜需要渲染的时刻集合。
    v4：入场动画窗（每个 data-t 时刻 ±0.45s @15fps，平滑入场）
        + 计数器窗（data-counter 起止 ±缓冲 @12fps）
        + 基础网格 2fps（覆盖环境动效微动）+ dense 窗 + 尾帧
    """
    n = max(2, round(dur * FPS))
    ts = set()
    # 开场窗（前 0.5s @30fps）
    for k in range(0, min(int(0.5 * FPS), n) + 1):
        ts.add(round(k / FPS, 4))
    # 入场窗（v4 新增：解析 HTML 中的 data-t / counter 声明）
    if entrances:
        for ent in entrances:
            kind = ent["kind"]
            if kind == "counter":
                t0, ramp = ent["t"], ent["ramp"]
                a, b = max(0.0, t0 - 0.2), min(dur, t0 + ramp + 0.5)
                t = a
                while t <= b + 1e-6:
                    ts.add(round(t, 4))
                    t += 1 / 12
            else:
                t0, d = ent["t"], ent["d"]
                a, b = max(0.0, t0 - 0.1), min(dur, t0 + d + 0.35)
                t = a
                while t <= b + 1e-6:
                    ts.add(round(t, 4))
                    t += 1 / 15
    # 基础网格
    k = 0
    while k / GRID <= dur:
        ts.add(round(k / GRID, 4))
        k += 1
    # dense 窗
    for t0, t1, dfps in dense:
        dfps = max(2, min(FPS, int(dfps)))
        t = t0
        while t <= min(t1, dur):
            ts.add(round(t, 4))
            t += 1 / dfps
    # 尾帧
    ts.add(round((n - 1) / FPS, 4))
    # 裁剪到 [0, dur] 并排序；去重(1/60内)
    ts = sorted(t for t in ts if 0 <= t <= dur)
    out = []
    for t in ts:
        if not out or t - out[-1] > 1 / 60:
            out.append(t)
    return out


def parse_dense(html):
    m = re.search(r"window\.SHOOT_DENSE\s*=\s*(\[\[.*?\]\])\s*;", html, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(1).replace("'", '"'))
    except Exception:  # noqa: BLE001
        return []


def parse_entrances(html, dur):
    """从 HTML 的 BG+STAGE 编辑区解析入场声明（逐开标签解析，counter 独立窗口）。"""
    blocks = re.findall(r"YZ_EDIT_(?:BG|STAGE)_BEGIN.*?YZ_EDIT_(?:BG|STAGE)_END", html, re.S)
    body = "\n".join(blocks)
    ents = []
    for tag in re.findall(r"<[^>]+>", body):
        if "data-t=" not in tag:
            continue
        m_t = re.search(r'data-t="(end-[\d.]+|[\d.]+)"', tag)
        if not m_t:
            continue
        t0s = m_t.group(1)
        t0 = dur - float(t0s[4:]) if t0s.startswith("end-") else float(t0s)
        m_d = re.search(r'data-d="([\d.]+)"', tag)
        d = float(m_d.group(1)) if m_d else 0.5
        if not (0 <= t0 <= dur):
            continue
        m_c = re.search(r'data-counter="([^"]+)"', tag)
        if m_c:
            parts = m_c.group(1).split(",")
            ramp = float(parts[2]) if len(parts) >= 3 and parts[2] else 1.0
            ents.append({"kind": "counter", "t": t0, "ramp": ramp})
        else:
            ents.append({"kind": "anim", "t": t0, "d": d})
    # 去重
    seen, uniq = set(), []
    for e in ents:
        key = (e["kind"], round(e["t"], 2))
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


def render_shot(page, sid, html_path, dur, dense, out_dir, transparent, entrances=None):
    os.makedirs(out_dir, exist_ok=True)
    page.goto(f"file://{os.path.abspath(html_path)}")
    try:
        page.wait_for_function(
            "() => document.fonts.ready.then(r => r.status).catch(() => 'loaded')",
            timeout=5000)
    except Exception:  # noqa: BLE001
        pass
    try:
        page.wait_for_function(
            "() => Array.from(document.images).every(i => i.src === '' || (i.complete && i.naturalWidth > 0))",
            timeout=8000)
    except Exception:  # noqa: BLE001
        print(f"  [{sid}] 图片加载等待超时（继续）")
    chk = page.evaluate("window.yzCheck ? yzCheck() : {status:'compliant'}")
    if chk.get("status") != "compliant":
        return None, chk
    times = shot_times(dur, dense, entrances)
    manifest = []
    for i, t in enumerate(times):
        page.evaluate("p => renderFrame(p)",
                      {"chapter": "", "subtitle": "", "progress_pct": 0,
                       "watermark": "", "t": t, "shot_dur": dur, "hud": False})
        fname = f"f_{i:04d}.png"
        page.screenshot(path=os.path.join(out_dir, fname), omit_background=transparent)
        manifest.append({"f": fname, "t": t})
    return manifest, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots")
    ap.add_argument("canvas_dir")
    ap.add_argument("frames_dir")
    ap.add_argument("--only", default=None, help="逗号分隔的镜头ID")
    args = ap.parse_args()

    shots = json.load(open(args.shots, encoding="utf-8"))
    if args.only:
        keep = set(args.only.split(","))
        shots = [s for s in shots if s["id"] in keep]
    os.makedirs(args.frames_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        for s in shots:
            sid = s["id"]
            out_dir = os.path.join(args.frames_dir, sid)
            marker = os.path.join(out_dir, ".done")
            if os.path.exists(marker):
                print(f"[skip] {sid}")
                continue
            html_path = os.path.join(args.canvas_dir, f"{sid}.html")
            if not os.path.exists(html_path):
                print(f"[miss] {sid}.html 不存在")
                continue
            html_src = open(html_path, encoding="utf-8").read()
            dense = parse_dense(html_src)
            transparent = sid in TRANSPARENT_SHOTS
            entrances = parse_entrances(html_src, s["dur"])
            manifest, bad = render_shot(page, sid, html_path, s["dur"], dense,
                                        out_dir, transparent, entrances)
            if bad is not None:
                print(f"[BAD] {sid}: {bad}")
                continue
            json.dump(manifest, open(os.path.join(out_dir, "render-manifest.json"), "w"))
            open(marker, "w").close()
            print(f"[ok] {sid}: {len(manifest)} 帧 / {s['dur']:.2f}s")
        browser.close()
    print("RENDER DONE")


if __name__ == "__main__":
    main()
