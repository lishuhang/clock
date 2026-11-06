#!/usr/bin/env python3
"""总装 v6（v5 复盘修复轮 · 音画同步/素材比例/进度条三修复 + 回归门禁 G8-G10）：
段: setup|bg|seq|enc|cat|final|final_h|audio|mux|mux_h|speed|speed_h|qc

v6 关键修复（对照 2026-11-06 17:56-17:58 用户审片反馈）：
  R1 音画不同步复发（竖屏+横屏）：
     根因 = v5 的 SUBS 误用仓库旧文件 ep1_subtitles.json（385卡 字数权重时间轴，
     全片漂移-23.6~+27.8s）；whisper 实测卡文件从未入库随沙盒丢失。
     修复 = 引用唯一事实源 ep1_subtitles_whisper.json（365卡，从字幕v3.srt 反向重建），
     setup 段硬断言与 字幕v3.srt 逐卡对账（G8 前置门禁）。
  R2 横屏嵌视频比例不对（拉幅/缩放错误）：
     根因 = bg 链 scale=1080:1920:force_original_aspect_ratio=increase+crop 铺满 9:16，
     16:9 原片横向只可见 32%、2.34:1 只可见 24%（放大 2.7~4.2 倍）。
     修复 = 真实影片一律原生比例呈现于 4:3 舞台框（Y555~1365）内：
       - fit 模式（影片作为主体：S02a/S02b/S03a/S03b/S24b）：scale decrease 入 1080×810，
         居中 pad #131110（16:9→1080×608、2.34:1→1080×462、16:10→1080×675）
       - cover 模式（影片作为氛围底：S04 竖版源 720×1280）：铺满 4:3 舞台框再裁，
         无拉伸（全宽可见、竖向取中段），scrim 74% 压暗
  R3 进度条中段重置（v4 引入、v5 未察觉）：
     根因 = v4/v5 重写 final 段时丢失 v2_seg 的段偏移逻辑，B 段 cmds 从 0 重画，
     全片进度条在 372s 切点归零、永远只走到 ~54%。
     修复 = gen_seg_cmds(total,t0,t1) 恢复段内偏移；G10 像素级验证进度条单调到 100%。

新增回归门禁（防同类问题再现，详见 05-retro/RETRO.md）：
  G8 字幕同步对账：canonical JSON ↔ 字幕v3.srt 逐卡 diff（±10ms/文本相等/365卡）
  G9 素材几何断言：每 bg 镜抽帧测视频窗口矩形 == ffprobe 推算期望值（±6px）
  G10 进度条连续性：切点前后 + 片尾三处抽帧测橙色条宽度，断言单调且终值≈1080
"""
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np

WORK = "/home/z/my-project/ep1-work"
REPO = "/home/z/my-project/clock/1105-canvas-test-videos"
SHOTS = f"{WORK}/ep1_shots_v4.json"
CANVAS_DIR = f"{REPO}/04-ep1-production/canvas"
FRAMES = f"{WORK}/frames_v6"
BILI = f"{WORK}/materials/bili"
NEW = f"{WORK}/materials/new"
BUILD = f"{WORK}/build_v6"
OUT = f"{WORK}/output"
NARR = f"{WORK}/audio/1105-1200-第一篇.mp3"
BGM = f"{WORK}/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
CANVAS_ASSETS = f"{REPO}/04-ep1-production/assets"
WM = f"{CANVAS_ASSETS}/wm75.png"
TRACK = f"{CANVAS_ASSETS}/progress_track.png"
FONTS = f"{CANVAS_ASSETS}/fonts"
SUBS = f"{REPO}/04-ep1-production/ep1_subtitles_whisper.json"  # 唯一事实源（R1）
SUBS_GROUND_TRUTH_SRT = f"{REPO}/04-ep1-production/output/字幕v3.srt"  # 对账基准
TOTAL = 740.36
FPS = 30
SPEED = 1.1
SPEED_TOTAL = TOTAL / SPEED  # 673.05
PAD_COLOR = "0x131110"  # 与全片底色一致（铁律17）
CROP_Y = 555

# R2: bg 素材模式表 —— fit=原生比例入4:3舞台(主体展示) / cover=铺满4:3舞台(氛围底,无拉伸)
BG_V6 = {
    "S02a": (f"{BILI}/paizi.mp4", 36.0, "fit"),     # 牌子 1280×720 → 1080×608
    "S02b": (f"{BILI}/paizi.mp4", 38.8, "fit"),
    "S03a": (f"{BILI}/sss.mp4", 100.0, "fit"),      # 丧尸清道夫 1280×548 → 1080×462
    "S03b": (f"{BILI}/sss.mp4", 102.8, "fit"),
    "S04": (f"{NEW}/t2第一抽.mp4", 3.2, "cover"),   # 竖版 720×1280 → 全宽取中段810
    "S24b": (f"{NEW}/抽卡过程延时.mp4", 85.0, "fit"),  # 录屏 2880×1800 → 1080×675
}
SEG_SPLIT = 372.0


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ff(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])
    return r


def probe_frames(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def probe_wh(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height", "-of", "csv=p=0", path)
    w, h = r.stdout.strip().rstrip(",").split(",")[:2]
    return int(w), int(h)


def load_subs():
    doc = json.load(open(SUBS, encoding="utf-8"))
    return doc["cards"] if isinstance(doc, dict) else doc


# ---------- 字幕生成（v6：位置/字号沿用 v5 验收样式，时间轴换 whisper 权威源） ----------
def ts_ass(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def vlen(s):
    return sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in s)


def _ass_header(pres_y, mvl, mvr, mv, base_size):
    return (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: %d\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Sub,Alibaba PuHuiTi 3.0,%d,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
        "1,0,0,0,100,100,0,0,1,7,0,2,%d,%d,%d,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        % (pres_y, base_size, mvl, mvr, mv))


def gen_ass_v(subs, path):
    """竖屏字幕：框 Y1435~1545（MarginV=375），宽 720（MarginL/R=180），动态字号 68/56/48。"""
    head = _ass_header(1920, 180, 180, 375, 68)
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        n = vlen(text)
        if n > 12.5:
            text = "{\\fs48}" + text
        elif n > 10.2:
            text = "{\\fs56}" + text
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


def gen_ass_h(subs, path):
    """横屏字幕：1080×810 画面内底部（MarginV=36），动态字号 56/44/38。"""
    head = _ass_header(810, 80, 80, 36, 56)
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        n = vlen(text)
        if n > 12.5:
            text = "{\\fs38}" + text
        elif n > 10.2:
            text = "{\\fs44}" + text
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


# R3: 进度条 cmds —— 恢复 v2_seg 的段内偏移（段内时间 = 全局 - t0）
def gen_seg_cmds(total, t0, t1, path, step=0.5):
    lines = []
    t = t0
    while t <= t1 + 1e-6:
        w = max(1, int(1080 * t / total))
        lines.append(f"{t - t0:.1f} drawbox w {w};")
        t += step
    open(path, "w").write("\n".join(lines) + "\n")


def load_shots():
    shots = json.load(open(SHOTS, encoding="utf-8"))
    ns = [max(2, round(s["dur"] * FPS)) for s in shots]
    total_n = round(TOTAL * FPS)
    diff = total_n - sum(ns)
    ns[-1] += diff
    for s, n in zip(shots, ns):
        s["n"] = n
    assert sum(ns) == total_n, f"帧数校准失败 {sum(ns)} != {total_n}"
    return shots, total_n


# ---------- setup（字体注册 + R1 血缘对账断言） ----------
def cmd_setup():
    os.makedirs(os.path.expanduser("~/.fonts"), exist_ok=True)
    for ttf in os.listdir(FONTS):
        shutil.copy(f"{FONTS}/{ttf}", os.path.expanduser(f"~/.fonts/{ttf}"))
    r = sh("fc-cache", "-f", os.path.expanduser("~/.fonts"))
    chk = sh("fc-match", "Alibaba PuHuiTi 3.0")
    print(f"[setup] fc-match → {chk.stdout.strip()}")
    assert "Alibaba" in chk.stdout or "PuHuiTi" in chk.stdout or "alipuhui" in chk.stdout, \
        f"普惠体系统注册失败: {chk.stdout}"
    # G8 前置：canonical JSON ↔ 字幕v3.srt 逐卡对账
    cards = load_subs()
    gt = parse_srt_cards(SUBS_GROUND_TRUTH_SRT)
    assert len(cards) == len(gt) == 365, f"卡数对账失败 json={len(cards)} srt={len(gt)}"
    for i, (a, b) in enumerate(zip(cards, gt)):
        assert a["text"] == b["text"], f"第{i}卡文本不符: {a['text']!r} vs {b['text']!r}"
        assert abs(a["start"] - b["start"]) <= 0.011 and abs(a["end"] - b["end"]) <= 0.011, \
            f"第{i}卡时间不符: {a['start']}/{a['end']} vs {b['start']}/{b['end']}"
    print(f"[setup] G8 前置对账 PASS：365 卡与 字幕v3.srt 逐卡一致（±10ms）")


def parse_srt_cards(path):
    def ts2s(t):
        h, m, rest = t.split(":")
        s, ms = rest.split(",")
        return round(int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000, 3)
    cards = []
    for block in open(path, encoding="utf-8").read().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        m = re.match(r"([\d:,.]+) --> ([\d:,.]+)", lines[1])
        if not m:
            continue
        cards.append({"start": ts2s(m.group(1)), "end": ts2s(m.group(2)),
                      "text": "\n".join(lines[2:]).strip()})
    return cards


# ---------- bg（R2：fit/cover 双模式，原生比例） ----------
def bg_vf(mode):
    if mode == "fit":
        return (f"scale=1080:810:force_original_aspect_ratio=decrease,"
                f"pad=1080:810:(ow-iw)/2:(oh-ih)/2:color={PAD_COLOR},"
                f"pad=1080:1920:0:{CROP_Y}:color={PAD_COLOR},fps=30,format=yuv420p")
    return (f"scale=1080:810:force_original_aspect_ratio=increase,crop=1080:810,"
            f"pad=1080:1920:0:{CROP_Y}:color={PAD_COLOR},fps=30,format=yuv420p")


def cmd_bg():
    shots, _ = load_shots()
    for sid, (src, offset, mode) in BG_V6.items():
        s = next(x for x in shots if x["id"] == sid)
        out = f"{BUILD}/bg_{sid}.mp4"
        if os.path.exists(out) and probe_frames(out) == s["n"]:
            print(f"[skip] bg_{sid}")
            continue
        ff("-ss", f"{offset:.3f}", "-i", src,
           "-vf", bg_vf(mode),
           "-frames:v", str(s["n"]), "-c:v", "libx264", "-crf", "18", "-preset", "fast", out)
        print(f"[ok] bg_{sid}.mp4 {s['n']}帧 ({mode})")


# ---------- seq / enc / cat（与 v5 相同，帧数精确架构） ----------
def cmd_seq():
    shots, _ = load_shots()
    import bisect
    for s in shots:
        sid = s["id"]
        mpath = f"{FRAMES}/{sid}/render-manifest.json"
        if not os.path.exists(mpath):
            print(f"[miss] {sid} 无manifest")
            continue
        manifest = json.load(open(mpath))
        ts = [x["t"] for x in manifest]
        seq_dir = f"{FRAMES}/{sid}/seq"
        os.makedirs(seq_dir, exist_ok=True)
        marker = f"{seq_dir}/.done_{s['n']}"
        if os.path.exists(marker):
            continue
        for f in os.listdir(seq_dir):
            if f.startswith("k_"):
                os.remove(os.path.join(seq_dir, f))
        for k in range(s["n"]):
            t = k / FPS
            i = bisect.bisect_right(ts, t + 1e-6) - 1
            if i < 0:
                i = 0
            src = f"../{manifest[i]['f']}"
            os.symlink(src, f"{seq_dir}/k_{k:06d}.png")
        open(marker, "w").close()
        print(f"[ok] {sid} seq {s['n']}帧")


def cmd_enc(only=None):
    shots, _ = load_shots()
    os.makedirs(f"{BUILD}/seg", exist_ok=True)
    for s in shots:
        sid = s["id"]
        if only and sid not in only:
            continue
        out = f"{BUILD}/seg/{sid}.mp4"
        if os.path.exists(out) and probe_frames(out) == s["n"]:
            continue
        seq_dir = f"{FRAMES}/{sid}/seq"
        if not os.path.exists(f"{seq_dir}/k_{s['n']-1:06d}.png"):
            print(f"[miss] {sid} 序列不完整")
            continue
        if sid in BG_V6:
            ff("-i", f"{BUILD}/bg_{sid}.mp4",
               "-framerate", "30", "-start_number", "0", "-i", f"{seq_dir}/k_%06d.png",
               "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p[v]",
               "-map", "[v]", "-frames:v", str(s["n"]),
               "-c:v", "libx264", "-crf", "18", "-preset", "fast", out)
        else:
            ff("-framerate", "30", "-start_number", "0", "-i", f"{seq_dir}/k_%06d.png",
               "-frames:v", str(s["n"]), "-pix_fmt", "yuv420p",
               "-c:v", "libx264", "-crf", "18", "-preset", "fast", out)
        print(f"[ok] {sid} {s['n']}帧")


def cmd_cat():
    shots, total_n = load_shots()
    lst = f"{BUILD}/shots.txt"
    with open(lst, "w") as f:
        f.write("ffconcat version 1.0\n")
        for s in shots:
            f.write(f"file 'seg/{s['id']}.mp4'\n")
    out = f"{BUILD}/vtrack.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
       "-video_track_timescale", "30000", out)
    n = probe_frames(out)
    print(f"[cat] vtrack {n}帧 (目标{total_n})")
    assert n == total_n, "帧数不精确!"


# ---------- final（竖屏：字幕Y1435~1545 + R3 修复后的进度条） ----------
def seg_subs_evs(subs, t0, t1):
    evs = []
    for x in subs:
        st, en = x["start"], x["end"]
        if en <= t0 or st >= t1:
            continue
        evs.append({"start": round(max(st, t0) - t0, 3), "end": round(min(en, t1) - t0, 3),
                    "text": x["text"]})
    return evs


def find_split():
    shots, _ = load_shots()
    split = None
    for s in shots:
        if s["start"] >= SEG_SPLIT:
            split = s["start"]
            break
    split = round(round((split or SEG_SPLIT) * FPS) / FPS, 6)
    print(f"切点: {split:.4f}s ({round(split*FPS)}帧)")
    return split


def final_pass(seg, t0, t1):
    dur = t1 - t0
    n_seg = round(dur * FPS)
    ass_file = f"{BUILD}/subs_{seg}.ass"
    cmds_file = f"{BUILD}/progress_{seg}.cmds"
    evs = seg_subs_evs(load_subs(), t0, t1)
    gen_ass_v(evs, ass_file)
    gen_seg_cmds(TOTAL, t0, t1, cmds_file)  # R3: 段偏移
    vfc = (
        "[0:v]format=yuv420p[base];"
        "[1:v]scale=1080:8[trk];"
        "[2:v]format=rgba[wm];"
        "[base][trk]overlay=0:0,"
        f"sendcmd=f={cmds_file},"
        "drawbox=x=0:y=0:w=1:h=8:color=#e55b46@1.0:t=fill[pbar];"
        f"[pbar]subtitles={ass_file}:fontsdir={FONTS}[vsub];"
        "[vsub][wm]overlay=0:0[vout]")
    if seg == "A":
        ff("-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", TRACK,
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_{seg}.mp4")
    else:
        ff("-ss", f"{t0:.6f}", "-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", TRACK,
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_{seg}.mp4")
    print(f"[final-{seg}] 字幕{len(evs)}卡 cmds段内偏移✓")


def cmd_final():
    split = find_split()
    for seg, (a, b) in {"A": (0.0, split), "B": (split, TOTAL)}.items():
        p = f"{BUILD}/final_{seg}.mp4"
        if not (os.path.exists(p) and os.path.getsize(p) > 1e6):
            final_pass(seg, a, b)
    lst = f"{BUILD}/fin.txt"
    open(lst, "w").write(
        f"ffconcat version 1.0\nfile 'final_A.mp4'\nfile 'final_B.mp4'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
       "-video_track_timescale", "30000", f"{BUILD}/vfinal.mp4")
    print(f"[final] vfinal {probe_frames(f'{BUILD}/vfinal.mp4')}帧")


# ---------- final_h（横屏 4:3 = 1080×810，crop Y555~1365） ----------
def final_h_pass(seg, t0, t1):
    dur = t1 - t0
    n_seg = round(dur * FPS)
    ass_file = f"{BUILD}/subs_h_{seg}.ass"
    cmds_file = f"{BUILD}/progress_{seg}.cmds"  # R3: 与竖屏共用偏移版 cmds
    evs = seg_subs_evs(load_subs(), t0, t1)
    gen_ass_h(evs, ass_file)
    vfc = (
        "[0:v]format=yuv420p[base];"
        "[1:v]format=rgba[wm];"
        "[2:v]scale=1080:8[trk];"
        "[base][wm]overlay=0:0[wmd],"
        f"[wmd]crop=1080:810:0:{CROP_Y}[crop];"
        "[crop][trk]overlay=0:0,"
        f"sendcmd=f={cmds_file},"
        "drawbox=x=0:y=0:w=1:h=8:color=#e55b46@1.0:t=fill[pbar];"
        f"[pbar]subtitles={ass_file}:fontsdir={FONTS}[vout]")
    if seg == "A":
        ff("-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-loop", "1", "-t", f"{dur:.3f}", "-i", TRACK,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_h_{seg}.mp4")
    else:
        ff("-ss", f"{t0:.6f}", "-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-loop", "1", "-t", f"{dur:.3f}", "-i", TRACK,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_h_{seg}.mp4")
    print(f"[final_h-{seg}] 字幕{len(evs)}卡")


def cmd_final_h():
    split = find_split()
    for seg, (a, b) in {"A": (0.0, split), "B": (split, TOTAL)}.items():
        p = f"{BUILD}/final_h_{seg}.mp4"
        if not (os.path.exists(p) and os.path.getsize(p) > 1e6):
            final_h_pass(seg, a, b)
    lst = f"{BUILD}/fin_h.txt"
    open(lst, "w").write(
        f"ffconcat version 1.0\nfile 'final_h_A.mp4'\nfile 'final_h_B.mp4'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
       "-video_track_timescale", "30000", f"{BUILD}/vfinal_h.mp4")
    print(f"[final_h] vfinal_h {probe_frames(f'{BUILD}/vfinal_h.mp4')}帧")


# ---------- audio（与 v5 相同：人声+BGM闪避+loudnorm 两遍） ----------
def cmd_audio():
    if os.path.exists(f"{BUILD}/final_audio.m4a"):
        print("[skip] audio")
        return
    afc = (
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[va][vb];"
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-13.5dB[bg0];"
        "[bg0][va]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bg];"
        "[vb][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]")
    ff("-i", NARR, "-stream_loop", "-1", "-i", BGM,
       "-filter_complex", afc, "-map", "[mix]", "-t", f"{TOTAL:.3f}",
       "-c:a", "pcm_s16le", f"{BUILD}/mix.wav")
    r = sh("ffmpeg", "-nostdin", "-i", f"{BUILD}/mix.wav", "-af",
           "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-").stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r, re.S)
    ln = json.loads(m.group(0)) if m else {}
    meas = (f"loudnorm=I=-15:TP=-1.5:LRA=11:"
            f"measured_I={ln.get('input_i', -24)}:measured_TP={ln.get('input_tp', -2)}:"
            f"measured_LRA={ln.get('input_lra', 11)}:measured_thresh={ln.get('input_thresh', -30)}:linear=true")
    ff("-i", f"{BUILD}/mix.wav", "-af", meas, "-c:a", "aac", "-b:a", "192k",
       f"{BUILD}/final_audio.m4a")
    print("[audio] done")


# ---------- mux / speed ----------
def cmd_mux():
    os.makedirs(OUT, exist_ok=True)
    out = f"{BUILD}/v6_1x.mp4"
    ff("-i", f"{BUILD}/vfinal.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux] {out}")


def cmd_mux_h():
    out = f"{BUILD}/v6h_1x.mp4"
    ff("-i", f"{BUILD}/vfinal_h.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux_h] {out}")


def cmd_speed():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v6-竖屏.mp4"
    ff("-i", f"{BUILD}/v6_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed] 竖屏成片 {probe_frames(out)}帧")


def cmd_speed_h():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v6-横屏.mp4"
    ff("-i", f"{BUILD}/v6h_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed_h] 横屏成片 {probe_frames(out)}帧")


# ---------- srt（权威源 ÷1.1 重定时） ----------
def gen_srt(path):
    subs = load_subs()

    def s2ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"

    out = []
    for i, s in enumerate(subs, 1):
        st, en = s["start"] / SPEED, s["end"] / SPEED
        out += [f"{i}", f"{s2ts(st)} --> {s2ts(en)}", s["text"], ""]
    open(path, "w", encoding="utf-8").write("\n".join(out))


# ---------- QC（G1-G7 + 回归门禁 G8/G9/G10） ----------
def grab_frame(path, t, w, h):
    """抽一帧 → numpy 数组（h,w,3 rgb）。"""
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-ss", f"{t:.3f}", "-i", path,
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    return a.reshape(h, w, 3)


def measure_pbar_width(frame):
    """进度条宽度：顶部8行中接近品牌橙 #e55b46 的像素列数。"""
    top = frame[0:8, :, :].astype(int)
    dr = np.abs(top[:, :, 0] - 229) < 45
    dg = np.abs(top[:, :, 1] - 91) < 45
    db = np.abs(top[:, :, 2] - 70) < 45
    mask = dr & dg & db
    cols = np.where(mask.any(axis=0))[0]
    return (int(cols.max()) + 1) if len(cols) else 0


def measure_video_window(frame, bg_rgb=(0x13, 0x11, 0x10)):
    """fit 模式视频窗口矩形：与 pad 底色不同的行/列范围（在 4:3 舞台带内测）。"""
    band = frame[CROP_Y:CROP_Y + 810, :, :].astype(int)
    d = np.abs(band - np.array(bg_rgb)).sum(axis=2)
    rows = np.where((d > 30).sum(axis=1) > 20)[0]   # 行内差异像素>20 视为视频行
    if not len(rows):
        return None
    r0, r1 = int(rows.min()), int(rows.max())
    sub = band[r0:r1 + 1, :, :]
    d2 = np.abs(sub - np.array(bg_rgb)).sum(axis=2)
    cols = np.where((d2 > 30).sum(axis=0) > 5)[0]
    c0, c1 = int(cols.min()), int(cols.max())
    return (c0, CROP_Y + r0, c1 - c0 + 1, r1 - r0 + 1)  # x,y,w,h


def expected_fit_rect(src_w, src_h):
    """ffmpeg scale decrease 到 1080×810 的期望窗口（与滤镜同样的取整）。"""
    scale = min(1080 / src_w, 810 / src_h)
    w = int(round(src_w * scale)) // 2 * 2  # ffmpeg 对奇数会取偶
    h = int(round(src_h * scale)) // 2 * 2
    x = (1080 - w) // 2
    y = CROP_Y + (810 - h) // 2
    return (x, y, w, h)


def cmd_qc():
    ok_all = True
    report = {"gates": {}, "BUILD_SUCCESS": True}
    files = [("竖屏", "AI视频画布横评-第一篇-价格篇-成片v6-竖屏.mp4", 1080, 1920),
             ("横屏", "AI视频画布横评-第一篇-价格篇-成片v6-横屏.mp4", 1080, 810)]
    split = find_split()
    for tag, fname, w, h in files:
        out = f"{OUT}/{fname}"
        gates = {}
        r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", out, "-f", "null", "-")
        gates[f"{tag}_G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
        n = probe_frames(out)
        expect = round(SPEED_TOTAL * FPS)
        gates[f"{tag}_G2_帧数"] = "PASS" if abs(n - expect) <= 15 else f"FAIL {n}≠{expect}±15"
        dur_raw = ""
        for _ in range(3):
            dur_raw = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", out).stdout.strip()
            if dur_raw:
                break
        dur = float(dur_raw)
        gates[f"{tag}_G3_时长"] = "PASS" if abs(dur - SPEED_TOTAL) <= 0.5 else f"FAIL {dur:.2f}"
        wh = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "stream=width,height", "-of", "csv=p=0", out).stdout.strip()
        gates[f"{tag}_G4_分辨率"] = "PASS" if wh.strip().rstrip(",") == f"{w},{h}" else f"FAIL {wh}"
        r3 = sh("ffmpeg", "-nostdin", "-i", out, "-vf", "blackdetect=d=3:pix_th=0.05",
                "-an", "-f", "null", "-").stderr
        gates[f"{tag}_G6_无长黑屏"] = "PASS" if "black_start" not in r3 else f"FAIL {r3[:200]}"
        meta = sh("ffprobe", "-v", "error", "-show_entries", "format_tags=comment",
                  "-of", "csv=p=0", out).stdout
        gates[f"{tag}_G7_元数据"] = "PASS" if "remotion" not in meta.lower() else "FAIL"
        # G10 进度条连续性（在 1x 的 vfinal 上测，横竖屏共用 cmds，只测竖屏 vfinal + 横屏 vfinal_h 各一次）
        src = f"{BUILD}/{'vfinal.mp4' if tag == '竖屏' else 'vfinal_h.mp4'}"
        if os.path.exists(src):
            fw, fh = (1080, 1920) if tag == "竖屏" else (1080, 810)
            w1 = measure_pbar_width(grab_frame(src, split - 2.0, fw, fh))
            w2 = measure_pbar_width(grab_frame(src, split + 2.0, fw, fh))
            wend = measure_pbar_width(grab_frame(src, TOTAL - 0.2, fw, fh))
            e1, e2 = 1080 * (split - 2) / TOTAL, 1080 * (split + 2) / TOTAL
            mono = w2 >= w1 and w1 > 0.35 * 1080 and w2 > 0.35 * 1080
            end_ok = wend > 0.92 * 1080
            gates[f"{tag}_G10_进度条"] = ("PASS" if (mono and end_ok) else
                                      f"FAIL w1={w1} w2={w2} wend={wend} (期望~{e1:.0f}/{e2:.0f}/1080)")
        report["gates"].update(gates)
        report[f"{tag}_frames"] = n
        report[f"{tag}_duration"] = dur
        for k, v in gates.items():
            print(f"  {k}: {v}")
        ok_all = ok_all and all(v == "PASS" for v in gates.values())

    # G8 字幕对账（成片复验：烧录 ASS 卡数与权威源一致）
    n_cards = len(load_subs())
    n_ass_v = sum(open(f"{BUILD}/subs_{s}.ass", encoding="utf-8").read().count("Dialogue:")
                  for s in ("A", "B"))
    n_ass_h = sum(open(f"{BUILD}/subs_h_{s}.ass", encoding="utf-8").read().count("Dialogue:")
                  for s in ("A", "B"))
    # 段边界字幕会被 A/B 各算一次（跨切点卡在两段都有），允许 A+B ∈ [N, N+2]
    g8 = (n_cards == 365 and n_ass_v - n_cards in (0, 1, 2) and n_ass_h - n_cards in (0, 1, 2))
    report["gates"]["G8_字幕对账"] = "PASS" if g8 else \
        f"FAIL cards={n_cards} ass_v={n_ass_v} ass_h={n_ass_h}"
    print(f"  G8_字幕对账: {report['gates']['G8_字幕对账']} (canonical={n_cards}, 竖{n_ass_v}, 横{n_ass_h})")
    ok_all = ok_all and g8

    # G9 素材几何（fit 模式窗口矩形 == 期望；cover 模式舞台带充满）
    shots, _ = load_shots()
    g9_detail = []
    g9_ok = True
    for sid, (src, offset, mode) in BG_V6.items():
        bgf = f"{BUILD}/bg_{sid}.mp4"
        if not os.path.exists(bgf):
            g9_ok = False; g9_detail.append(f"{sid}:无bg"); continue
        s = next(x for x in shots if x["id"] == sid)
        frame = grab_frame(bgf, s["dur"] / 2, 1080, 1920)
        if mode == "fit":
            sw, sh_ = probe_wh(src)
            exp = expected_fit_rect(sw, sh_)
            got = measure_video_window(frame)
            if got is None:
                g9_ok = False; g9_detail.append(f"{sid}:未检出窗口"); continue
            dx, dy = abs(got[0] - exp[0]), abs(got[1] - exp[1])
            dw, dh = abs(got[2] - exp[2]), abs(got[3] - exp[3])
            ok = dx <= 6 and dy <= 6 and dw <= 8 and dh <= 8
            g9_detail.append(f"{sid}:fit exp={exp} got={got} {'✓' if ok else '✗'}")
            g9_ok = g9_ok and ok
        else:
            band = frame[CROP_Y:CROP_Y + 810, :, :].astype(int)
            d = np.abs(band - np.array([0x13, 0x11, 0x10])).sum(axis=2)
            video_rows = int(((d > 30).sum(axis=1) > 100).sum())
            ok = video_rows > 810 * 0.85
            g9_detail.append(f"{sid}:cover 视频行{video_rows}/810 {'✓' if ok else '✗'}")
            g9_ok = g9_ok and ok
    report["gates"]["G9_素材几何"] = "PASS" if g9_ok else "FAIL"
    report["G9_detail"] = g9_detail
    for d in g9_detail:
        print(f"  G9: {d}")
    ok_all = ok_all and g9_ok

    report["BUILD_SUCCESS"] = ok_all
    json.dump(report, open(f"{OUT}/qc_report_v6.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("BUILD_SUCCESS" if ok_all else "BUILD_FAILED")
    gen_srt(f"{OUT}/AI视频画布横评-第一篇-价格篇-字幕v6.srt")
    print("[qc] 字幕v6.srt 已生成（whisper 权威源 ÷1.1）")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[1] == "enc" else None
    {"setup": cmd_setup, "bg": cmd_bg, "seq": cmd_seq,
     "enc": lambda: cmd_enc(only), "cat": cmd_cat, "final": cmd_final,
     "final_h": cmd_final_h, "audio": cmd_audio, "mux": cmd_mux, "mux_h": cmd_mux_h,
     "speed": cmd_speed, "speed_h": cmd_speed_h, "qc": cmd_qc}.get(
        step, lambda: sys.exit(f"用法: {sys.argv[0]} setup|bg|seq|enc|cat|final|final_h|audio|mux|mux_h|speed|speed_h|qc [only]"))()
