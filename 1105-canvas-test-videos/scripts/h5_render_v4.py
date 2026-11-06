#!/usr/bin/env python3
"""受控时钟截帧器 v4（重建版 · 2026-11-07）：

v3→v4 关键修复：
  透明页不再靠硬编码清单（v3 的 TRANSPARENT_SHOTS={"S02","S03"} 在 v4 分镜改名
  S02a/S02b/S03a/S03b 后从未匹配，v6/v7 用的 v4 渲染器又未入库丢失）——
  改为**自动检测**：页面加载后读 body 计算样式，backgroundColor 为全透明即按
  omit_background 截图。页面侧只管把 body/#bg-layer 改透明，渲染器自动跟随。

用法:
  python3 h5_render_v4.py <shots.json> <canvas_dir> <frames_dir> [--only S01,S02]
铁律：禁 Playwright 实时录屏（掉帧→音画错位）；每镜截帧前必须 yzCheck()==compliant；
  幂等续跑：每镜 .done 标记（重跑前删对应目录）。
"""
import argparse
import json
import os
import re

from playwright.sync_api import sync_playwright

FPS = 30
ENTRY = 1.5
GRID = 2  # 基础网格 fps


def shot_times(dur, dense):
    """帧时刻 = 入场窗(1.5s@30fps) ∪ 基础网格(2fps全程) ∪ SHOOT_DENSE 连续段 ∪ 尾帧。"""
    n = max(2, round(dur * FPS))
    ts = set()
    for k in range(0, min(int(ENTRY * FPS), n) + 1):
        ts.add(round(k / FPS, 4))
    k = 0
    while k / GRID <= dur:
        ts.add(round(k / GRID, 4))
        k += 1
    for t0, t1, dfps in dense:
        dfps = max(2, min(FPS, int(dfps)))
        t = t0
        while t <= min(t1, dur):
            ts.add(round(t, 4))
            t += 1 / dfps
    ts.add(round((n - 1) / FPS, 4))
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


def render_shot(page, sid, html_path, dur, dense, out_dir):
    """返回 (manifest, transparent, yzCheck问题)；manifest=None 表示自检不过。"""
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
        return None, False, chk
    # v4：透明页自动检测（body 背景计算样式为全透明 → omit_background 截图）
    transparent = page.evaluate(
        "() => { const c = getComputedStyle(document.body).backgroundColor;"
        " return c === 'rgba(0, 0, 0, 0)' || c === 'transparent'; }")
    times = shot_times(dur, dense)
    manifest = []
    for i, t in enumerate(times):
        page.evaluate("p => renderFrame(p)",
                      {"chapter": "", "subtitle": "", "progress_pct": 0,
                       "watermark": "", "t": t, "shot_dur": dur, "hud": False})
        fname = f"f_{i:04d}.png"
        page.screenshot(path=os.path.join(out_dir, fname), omit_background=transparent)
        manifest.append({"f": fname, "t": t})
    return manifest, transparent, None


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
            dense = parse_dense(open(html_path, encoding="utf-8").read())
            manifest, transparent, bad = render_shot(page, sid, html_path, s["dur"], dense, out_dir)
            if bad is not None:
                print(f"[BAD] {sid}: {bad}")
                continue
            json.dump(manifest, open(os.path.join(out_dir, "render-manifest.json"), "w"))
            open(marker, "w").close()
            print(f"[ok] {sid}: {len(manifest)} 帧 / {s['dur']:.2f}s{' [透明叠层]' if transparent else ''}")
        browser.close()
    print("RENDER DONE")


if __name__ == "__main__":
    main()
