#!/usr/bin/env python3
"""受控时钟截帧器（Step 6）：timeline.json + 逐镜 canvas HTML → 关键帧序列 + concat 清单。
用法: python3 h5_render.py <timeline.json> <canvas_dir> <frames_dir> [--fps 30] [--template master.html]

约定：
- canvas_dir/S##.html 存在 → 用它（须实现 window.renderFrame(payload) 与 window.yzCheck()）；
  不存在 → 用 --template 母版，payload.stage_html 取 timeline.shots[].visual（纯文字舞台兜底）。
- 只在动效窗口（每镜前 1.5s + 字幕切换点）按 fps 截帧，其余区间单帧复用（concat -d 段）。
- 产物: frames/S##/f_*.png + frames/concat.txt（ffmpeg concat demuxer 格式）+ render-report.json
铁律：禁 Playwright 实时录屏（掉帧→音画错位）；每镜截帧前必须 yzCheck()==compliant。
"""
import argparse
import json
import os
import subprocess
import sys

from playwright.sync_api import sync_playwright


def build_concat(frames_dir, shots, fps):
    """concat demuxer：静态段复用单帧（duration 延展），动效段逐帧 1/fps。"""
    lines = ["ffconcat version 1.0"]
    for s in shots:
        d = os.path.join(frames_dir, s["id"])
        if not os.path.isdir(d):
            continue
        pngs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        if not pngs:
            continue
        anim_window = min(1.5, s["dur"])
        still_dur = max(0.0, s["dur"] - anim_window)
        if still_dur > 0.05:
            lines.append(f"file '{s['id']}/{pngs[0]}'")
            lines.append(f"duration {still_dur:.3f}")
        for i, f in enumerate(pngs):
            t = i / fps
            if t >= anim_window and i != len(pngs) - 1:
                continue  # 动效窗口外的中间帧不复用
            dur = min(1 / fps, anim_window - t) if i < len(pngs) - 1 else max(0.001, anim_window - (len(pngs) - 1) / fps)
            lines.append(f"file '{s['id']}/{f}'")
            lines.append(f"duration {dur:.3f}")
        # concat demuxer 尾帧需重复一次 file 行以固定时长
        lines.append(f"file '{s['id']}/{pngs[-1]}'")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("canvas_dir")
    ap.add_argument("frames_dir")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--template", default=None, help="未提供逐镜HTML时的母版")
    ap.add_argument("--watermark", default="", help="浮水印图片路径（file:// 或 https）")
    args = ap.parse_args()

    tl = json.load(open(args.timeline, encoding="utf-8"))
    shots = tl["shots"]
    os.makedirs(args.frames_dir, exist_ok=True)
    template_html = open(args.template, encoding="utf-8").read() if args.template else None

    report = {"shots": [], "noncompliant": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        for s in shots:
            out_dir = os.path.join(args.frames_dir, s["id"])
            marker = os.path.join(out_dir, ".done")
            if os.path.exists(marker):  # 幂等续跑
                report["shots"].append({"id": s["id"], "status": "skip"})
                continue
            os.makedirs(out_dir, exist_ok=True)
            html_path = os.path.join(args.canvas_dir, f"{s['id']}.html")
            if os.path.exists(html_path):
                page.goto(f"file://{os.path.abspath(html_path)}")
            elif template_html:
                tmp = os.path.join(out_dir, "_page.html")
                open(tmp, "w", encoding="utf-8").write(
                    template_html.replace(
                        "<!-- ======== YZ_EDIT_STAGE_BEGIN（每镜内容只改这里） ======== -->"
                        "<div style=\"display:flex;height:100%;align-items:center;justify-content:center;\">"
                        "<div data-anim=\"pop\" data-t=\"0.3\" style=\"font-size:120px;font-weight:900;color:var(--ink);\">示例：大数字砸屏</div>"
                        "</div><!-- ======== YZ_EDIT_STAGE_END ======== -->",
                        s.get("visual", "")))
                page.goto(f"file://{os.path.abspath(tmp)}")
            else:
                report["noncompliant"].append({"id": s["id"], "reason": "无HTML且未提供母版"})
                continue
            page.wait_for_function("() => document.fonts && document.fonts.ready ? document.fonts.ready.status === 'loaded' : true", timeout=8000)
            chk = page.evaluate("window.yzCheck ? yzCheck() : {status:'compliant'}")
            if chk.get("status") != "compliant":
                report["noncompliant"].append({"id": s["id"], "problems": chk.get("problems")})
                continue
            dur = s["dur"]
            anim_window = min(1.5, dur)
            n_frames = max(2, int(anim_window * args.fps) + 1)
            for i in range(n_frames):
                t = round(i / args.fps, 3)
                page.evaluate(
                    "p => renderFrame(p)",
                    {"chapter": s.get("chapter", ""), "subtitle": s.get("subtitle", s.get("narration", "")),
                     "progress_pct": 0, "watermark": args.watermark, "t": t, "shot_dur": dur})
                page.screenshot(path=os.path.join(out_dir, f"f_{i:04d}.png"))
            open(marker, "w").close()
            report["shots"].append({"id": s["id"], "frames": n_frames, "dur": dur})
        browser.close()

    concat = build_concat(args.frames_dir, shots, args.fps)
    open(os.path.join(args.frames_dir, "concat.txt"), "w", encoding="utf-8").write(concat)
    json.dump(report, open(os.path.join(args.frames_dir, "render-report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_bad = len(report["noncompliant"])
    print(f"RENDER {'OK' if n_bad == 0 else 'NONCOMPLIANT'}: {len(report['shots'])} 镜 / {n_bad} 不合规 -> {args.frames_dir}/concat.txt")
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()
