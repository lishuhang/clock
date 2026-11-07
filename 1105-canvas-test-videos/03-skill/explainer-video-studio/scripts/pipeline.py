#!/usr/bin/env python3
"""pipeline.py · 解耦统一运行器（1105-canvas-test-videos，2026-11-07 用户解耦指令落地）

职责分层（谁干什么）：
  AI / 外部模型（可换 Kimi 等） : 创意决策、分镜、H5 页面制作（按 ../H5-SPEC.md 契约）
  本脚本（零 token）           : check 齐全性检测 / render 受控截帧 / assemble 总装15段 / deliver 归档
  既有 assemble_v8 / assemble_ep : 已验收的防回归总装（G1-G14 门禁），本脚本只编排不改内容

用法：
  python3 pipeline.py --list                                # 三集步骤×状态总览
  python3 pipeline.py --ep 1                                # ep1 全流程 check→render→assemble→deliver
  python3 pipeline.py --ep all                              # 三集全流程
  python3 pipeline.py --ep 2 --from render                  # 从某步开始
  python3 pipeline.py --ep 3 --to assemble                  # 跑到某步为止
  python3 pipeline.py --ep all --steps check,render         # 只跑指定步
  python3 pipeline.py --ep 1 --skip render                  # 跳过某步（帧已在，只重组装）
  python3 pipeline.py --ep 1 --segments subs,subs_h,qc      # 只跑总装某几段（如改字幕后只重烧字幕）
  python3 pipeline.py --ep 2 --only-shots S07,S25           # render 只重截指定镜（换 H5 后用）

设计原则：
  1. 任何机械步骤可独立运行/跳过/指定停留 —— 改一样东西只重跑受影响的最小段
  2. 幂等续跑：所有决策基于实际文件状态（.done 标记/帧数断言），沙盒崩溃后重跑自动接续
  3. 零 token：check/render/assemble/deliver 全部本地脚本执行
  4. H5 可替换：换成任何符合 H5-SPEC.md 的页面 → render --only-shots <镜> → assemble 即可
  5. 不改 assemble_v8/assemble_ep 内部逻辑（防回归），路径常量从其 import（单一事实源）
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(SCRIPTS)                      # .../1105-canvas-test-videos
SANDBOX = "/home/z/my-project"
REPO_LINK = f"{SANDBOX}/repo"                        # assemble 脚本硬编码期望的路径
REPO = f"{REPO_LINK}/1105-canvas-test-videos"
CLONE_CANDIDATES = [f"{SANDBOX}/work-clock", f"{SANDBOX}/clock", f"{SANDBOX}/github-work"]
STATE_DIR = os.path.join(PROJ, ".pipeline")

STEPS = ["check", "render", "assemble", "deliver"]   # bootstrap 隐式先行
ASSEMBLE_SEGMENTS = ["setup", "bg", "seq", "enc", "cat", "final", "final_h",
                     "audio", "mux", "mux_h", "speed", "speed_h", "subs", "subs_h", "qc"]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- EP 配置（单一事实源=assemble 脚本常量）
def ep_config(ep):
    """从 assemble 脚本 import 路径/素材表常量，避免两处维护。"""
    if ep == 1:
        m = load_module("assemble_v8_ref", os.path.join(SCRIPTS, "assemble_v8.py"))
        return {
            "ep": 1, "label": "ep1", "name": "第一篇-价格篇", "ver": "v8",
            "shots": m.SHOTS, "canvas": m.CANVAS_DIR, "frames": m.FRAMES,
            "build": m.BUILD, "out": m.OUT, "narr": m.NARR, "bgm": m.BGM,
            "subs": m.SUBS, "bg": m.BG_V8, "total": m.TOTAL, "speed": m.SPEED,
            "assembler": os.path.join(SCRIPTS, "assemble_v8.py"), "env": {},
            "extras": {"SUBS_WHISPER": m.SUBS_WHISPER, "SENTS_REAL": m.SENTS_REAL},
        }
    os.environ["EP"] = f"ep{ep}"
    m = load_module(f"assemble_ep_ref_ep{ep}", os.path.join(SCRIPTS, "assemble_ep.py"))
    return {
        "ep": ep, "label": f"ep{ep}", "name": m.EP_NAME, "ver": "v1",
        "shots": m.SHOTS, "canvas": m.CANVAS_DIR, "frames": m.FRAMES,
        "build": m.BUILD, "out": m.OUT, "narr": m.NARR, "bgm": m.BGM,
        "subs": m.SUBS, "bg": m.BG_EP, "total": m.TOTAL, "speed": m.SPEED,
        "assembler": os.path.join(SCRIPTS, "assemble_ep.py"),
        "env": {"EP": f"ep{ep}"}, "extras": {},
    }


# ---------------------------------------------------------------- bootstrap（隐式）
def bootstrap():
    """确保 assemble 脚本期望的 /home/z/my-project/repo 路径可用 + 工作目录存在。幂等。"""
    ok = os.path.isdir(f"{REPO_LINK}/1105-canvas-test-videos")
    if not ok:
        src = next((c for c in CLONE_CANDIDATES
                    if os.path.isdir(os.path.join(c, "1105-canvas-test-videos"))), None)
        assert src, (
            "未找到工程仓。请先克隆：\n"
            "  git clone --depth 1 https://x-access-token:${GH_TOKEN}@github.com/lishuhang/clock.git "
            f"{'或 '.join(CLONE_CANDIDATES)}\n（详见 RESUME.md 崩溃恢复协议）")
        if os.path.islink(REPO_LINK) or os.path.exists(REPO_LINK):
            os.remove(REPO_LINK)
        os.symlink(src, REPO_LINK)
        ok = True
    for d in ("ep1-work", "ep2-work", "ep3-work"):
        os.makedirs(f"{SANDBOX}/{d}", exist_ok=True)
    return ok


# ---------------------------------------------------------------- check（齐全性检测）
def sh_out(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def check_ep(cfg, verbose=True):
    problems, infos = [], []

    # 1. 镜表
    try:
        shots = json.load(open(cfg["shots"], encoding="utf-8"))
        total = sum(s["dur"] for s in shots)
        if abs(total - cfg["total"]) > 1.0:
            problems.append(f"镜表Σdur {total:.2f}s ≠ 预期 {cfg['total']}s")
    except Exception as e:  # noqa: BLE001
        problems.append(f"镜表不可读: {cfg['shots']} ({e})")
        shots = []
    infos.append(f"镜表 {len(shots)} 镜 / Σ {total:.2f}s（预期 {cfg['total']}s）" if shots
                 else "镜表缺失")

    # 2. canvas 页面（每镜一页）
    missing_html = [s["id"] for s in shots
                    if not os.path.exists(os.path.join(cfg["canvas"], f"{s['id']}.html"))]
    if missing_html:
        problems.append(f"缺 canvas 页: {missing_html}")
    infos.append(f"canvas {len(shots)-len(missing_html)}/{len(shots)} 页齐全"
                 f"（{os.path.relpath(cfg['canvas'], PROJ)}）")

    # 3. bg 切片
    for sid, entry in cfg["bg"].items():
        p = entry[0]
        if not (os.path.exists(p) and os.path.getsize(p) > 10000):
            problems.append(f"bg 切片缺失/过小: {sid} ← {p}")
    infos.append(f"bg 切片 {len(cfg['bg'])} 路全部在库（clips/ + MANIFEST）")

    # 4. 音频 / 字幕 / 水印 / 字体
    for key, path in (("配音", cfg["narr"]), ("BGM", cfg["bgm"]), ("字幕JSON", cfg["subs"]),
                      ("等比水印", f"{PROJ}/04-ep1-production/assets/wm_v8.png"),
                      ("水印原版", f"{PROJ}/04-ep1-production/assets/浮水印-简版竖版黑字alpha.png")):
        if not os.path.exists(path):
            problems.append(f"{key}缺失: {path}")
        else:
            infos.append(f"{key} ✓ {os.path.relpath(path, PROJ)}")
    for k, path in cfg["extras"].items():
        (problems.append(f"{k} 缺失: {path}") if not os.path.exists(path)
         else infos.append(f"{k} ✓ {os.path.relpath(path, PROJ)}"))
    fonts = f"{PROJ}/04-ep1-production/assets/fonts"
    n_fonts = len(os.listdir(fonts)) if os.path.isdir(fonts) else 0
    if n_fonts < 3:
        problems.append(f"字体不全: {fonts} 仅 {n_fonts} 个")
    else:
        infos.append(f"字体 ✓ {n_fonts} 个 ttf")

    # 5. 环境
    env_bad = []
    if not shutil.which("ffmpeg"):
        env_bad.append("ffmpeg")
    if not shutil.which("ffprobe"):
        env_bad.append("ffprobe")
    try:
        import playwright  # noqa: F401
        import numpy  # noqa: F401
    except Exception:  # noqa: BLE001
        env_bad.append("playwright/numpy")
    pw_dir = os.path.expanduser("~/.cache/ms-playwright")
    if not (os.path.isdir(pw_dir) and any(x.startswith("chromium") for x in os.listdir(pw_dir))):
        env_bad.append("chromium")
    if env_bad:
        problems.append(f"环境缺: {env_bad}")
    else:
        infos.append("环境 ✓ ffmpeg/ffprobe/playwright/chromium/numpy")

    # 6. 既有进度（信息性，不作失败判据）
    done = sum(1 for s in shots
               if os.path.exists(os.path.join(cfg["frames"], s["id"], ".done")))
    infos.append(f"截帧进度 {done}/{len(shots)} 镜（.done 标记，重跑自动接续）")
    outputs = [f for f in os.listdir(cfg["out"]) if f.startswith("AI视频") and f.endswith(".mp4")] \
        if os.path.isdir(cfg["out"]) else []
    if outputs:
        infos.append(f"既有成片 {len(outputs)} 个（work output/）")

    if verbose:
        print(f"\n===== check {cfg['label']}（{cfg['name']}）=====")
        for i in infos:
            print(f"  · {i}")
        for p in problems:
            print(f"  ✗ {p}")
        print(f"  → {'PASS 文件齐全，可投产' if not problems else 'FAIL 见上'}")
    return problems


# ---------------------------------------------------------------- render
def render_ep(cfg, only_shots=None):
    cmd = [sys.executable, os.path.join(SCRIPTS, "h5_render_v4.py"),
           cfg["shots"], cfg["canvas"], cfg["frames"]]
    if only_shots:
        cmd += ["--only", ",".join(only_shots)]
        for sid in only_shots:  # 指定重截 → 清该镜幂等标记
            marker = os.path.join(cfg["frames"], sid, ".done")
            if os.path.exists(marker):
                os.remove(marker)
    print(f"[render:{cfg['label']}] {' '.join(os.path.basename(c) for c in cmd[:2])} ...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"render {cfg['label']} 失败 rc={r.returncode}")
    shots = json.load(open(cfg["shots"], encoding="utf-8"))
    done = sum(1 for s in shots
               if os.path.exists(os.path.join(cfg["frames"], s["id"], ".done")))
    print(f"[render:{cfg['label']}] 完成 {done}/{len(shots)} 镜")
    if done < len(shots):
        raise RuntimeError(f"render {cfg['label']} 仍有 {len(shots)-done} 镜未完成")


# ---------------------------------------------------------------- assemble
def assemble_ep(cfg, segments):
    env = {**os.environ, **cfg["env"]}
    for seg in segments:
        if seg not in ASSEMBLE_SEGMENTS:
            raise ValueError(f"未知总装段: {seg}（可选 {ASSEMBLE_SEGMENTS}）")
    for i, seg in enumerate(segments, 1):
        t0 = time.time()
        print(f"[assemble:{cfg['label']}] ({i}/{len(segments)}) {seg} ...", flush=True)
        r = subprocess.run([sys.executable, cfg["assembler"], seg], env=env)
        dt = time.time() - t0
        if r.returncode != 0:
            raise RuntimeError(
                f"assemble {cfg['label']} 段 {seg} 失败 rc={r.returncode}（{dt:.0f}s）— "
                f"修复后用 --from assemble --segments {','.join(segments[i-1:])} 续跑")
        print(f"[assemble:{cfg['label']}] {seg} ✓ ({dt:.0f}s)", flush=True)
        state(cfg, f"assemble.{seg}")


# ---------------------------------------------------------------- deliver
def bname(fname):
    """v8→v8b / v1→v1b（小版本后缀 b = 同内容、仅验证解耦流程）"""
    return re.sub(r"(v\d+(?:\.\d+)?)", r"\1b", fname, count=1)


def deliver_ep(cfg):
    out, repo_out = cfg["out"], os.path.join(PROJ, "04-ep1-production/output")
    os.makedirs(repo_out, exist_ok=True)
    produced = []
    for f in sorted(os.listdir(out)):
        if not re.match(r"(AI视频画布横评-.*(成片|字幕)v[\d.]+|qc_report_.*v[\d.]+)", f):
            continue
        src, dst = os.path.join(out, f), os.path.join(repo_out, bname(f))
        shutil.copy2(src, dst)
        produced.append((f, bname(f), os.path.getsize(dst) // 1024 // 1024))
    if not produced:
        raise RuntimeError(f"deliver {cfg['label']}: work output/ 无可交付产物")
    print(f"\n===== deliver {cfg['label']} → 仓库 output/ =====")
    for a, b, mb in produced:
        print(f"  {a}  →  {b}  ({mb} MB)")
    return produced


# ---------------------------------------------------------------- state（信息性日志；真实状态=文件系统）
def state(cfg, step):
    os.makedirs(STATE_DIR, exist_ok=True)
    p = os.path.join(STATE_DIR, f"state-{cfg['label']}.json")
    doc = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    doc[step] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(doc, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- list
def list_status():
    bootstrap()
    print("=" * 72)
    print("pipeline.py 解耦管线状态总览（STEPS: check → render → assemble → deliver）")
    print("=" * 72)
    all_ok = True
    for ep in (1, 2, 3):
        cfg = ep_config(ep)
        problems = check_ep(cfg, verbose=False)
        all_ok &= not problems
        st = json.load(open(os.path.join(STATE_DIR, f"state-{cfg['label']}.json"),
                            encoding="utf-8")) if os.path.exists(
            os.path.join(STATE_DIR, f"state-{cfg['label']}.json")) else {}
        last = max(st.values()) if st else "-"
        shots = json.load(open(cfg["shots"], encoding="utf-8"))
        done = sum(1 for s in shots
                   if os.path.exists(os.path.join(cfg["frames"], s["id"], ".done")))
        vfinal = os.path.join(cfg["out"], f"AI视频画布横评-{cfg['name']}-成片{cfg['ver']}-竖屏.mp4")
        print(f"\n[{cfg['label']}] {cfg['name']}  帧率进度 {done}/{len(shots)}镜  "
              f"成片 {'✓' if os.path.exists(vfinal) else '✗'}  最近段 {last}")
        for i in (x for x in [
                f"check {'PASS' if not problems else 'FAIL: ' + '; '.join(problems[:3])}",
                f"render {done}/{len(shots)}",
                f"assemble {'15段完成' if os.path.exists(vfinal) else '未完成/未跑'}",
                f"deliver {'b版本在库' if os.path.exists(os.path.join(
                    PROJ, '04-ep1-production/output',
                    bname(os.path.basename(vfinal)))) else '—'}"]):
            print(f"    {i}")
    print("\n说明：状态判定全部基于实际文件（.done 标记/成片存在性），崩溃后重跑自动接续。")
    return 0 if all_ok else 1


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="1105 三集解耦管线运行器")
    ap.add_argument("--ep", default="1", help="1|2|3|all")
    ap.add_argument("--from", dest="from_step", choices=STEPS)
    ap.add_argument("--to", dest="to_step", choices=STEPS)
    ap.add_argument("--steps", help="逗号分隔，如 check,render（优先于 from/to）")
    ap.add_argument("--skip", help="逗号分隔要跳过的步骤")
    ap.add_argument("--segments", help="assemble 段覆盖，如 subs,subs_h,qc（默认全15段）")
    ap.add_argument("--only-shots", dest="only_shots", help="render 只重截指定镜，如 S08,S09")
    ap.add_argument("--list", action="store_true", help="只看状态")
    args = ap.parse_args()

    if args.list:
        sys.exit(list_status())

    eps = [1, 2, 3] if args.ep == "all" else [int(args.ep)]
    steps = (args.steps.split(",") if args.steps else STEPS)
    if args.from_step:
        steps = STEPS[STEPS.index(args.from_step):]
    if args.to_step:
        steps = steps[:steps.index(args.to_step) + 1]
    if args.skip:
        drop = set(args.skip.split(","))
        steps = [s for s in steps if s not in drop]
    bad = [s for s in steps if s not in STEPS]
    assert not bad, f"未知步骤 {bad}，可选 {STEPS}"

    bootstrap()
    for ep in eps:
        cfg = ep_config(ep)
        print(f"\n########## {cfg['label']} · {cfg['name']} · steps={steps} ##########", flush=True)
        for step in steps:
            if step == "check":
                if check_ep(cfg):
                    raise SystemExit(f"[{cfg['label']}] check FAIL — 先补齐文件（见上）")
                state(cfg, "check")
            elif step == "render":
                render_ep(cfg, args.only_shots.split(",") if args.only_shots else None)
                state(cfg, "render")
            elif step == "assemble":
                segs = args.segments.split(",") if args.segments else ASSEMBLE_SEGMENTS
                assemble_ep(cfg, segs)
                state(cfg, "assemble")
            elif step == "deliver":
                deliver_ep(cfg)
                state(cfg, "deliver")
        print(f"[{cfg['label']}] 全部步骤完成 ✓", flush=True)


if __name__ == "__main__":
    main()
