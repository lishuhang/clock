#!/usr/bin/env python3
"""总装 v5（安全框Y555~1365 + 字幕Y1435~1545 + 普惠体系统注册 + 横屏4:3版）：
段: setup|bg|seq|enc|cat|final|final_h|audio|mux|mux_h|speed|speed_h|qc

v5 关键变更（对齐用户 2026-11-06 v5 验收）：
  1. 4:3 安全框 = Y555~1365（1080×810 横屏比例），canvas 已全镜整改
  2. 字幕框 = Y1435~1545（高110 宽720 左右各留白180）：Alignment2 + MarginV=375 + MarginL/R=180
  3. 字幕字体修复：libass fontsdir 在本环境匹配失败 → 字体注册进 ~/.fonts（setup 段自动做）
  4. 动态字号：视觉长度 ≤10.2 字 68px / ≤12.5 字 56px / 更长 48px（WrapStyle=2 不折行）
  5. 横屏版（B站分发）：crop Y555~1365 = 1080×810，字幕烧画面底部（MarginV=36 字号56/44/38）
  6. 1.1x 提速不变（setpts/atempo）
"""
import json
import os
import re
import shutil
import subprocess
import sys

WORK = "/home/z/my-project/ep1-work"
REPO = "/home/z/my-project/clock-repo/1105-canvas-test-videos"
SHOTS = f"{WORK}/ep1_shots_v4.json"
CANVAS_DIR = f"{REPO}/04-ep1-production/canvas"
FRAMES = f"{WORK}/frames_v5"
BILI = f"{WORK}/materials/bili"  # B站完整原片（dl_bili_v2.py 下载；repo 里的 *_bg.mp4 仅14s样本不可用）
NEW = f"{WORK}/materials/new"
BUILD = f"{WORK}/build_v5"
OUT = f"{WORK}/output"
NARR = f"{WORK}/audio/1105-1200-第一篇.mp3"
BGM = f"{WORK}/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
CANVAS_ASSETS = f"{REPO}/04-ep1-production/assets"
WM = f"{CANVAS_ASSETS}/wm75.png"
TRACK = f"{CANVAS_ASSETS}/progress_track.png"
FONTS = f"{CANVAS_ASSETS}/fonts"
SUBS = f"{REPO}/04-ep1-production/ep1_subtitles.json"
TOTAL = 740.36
FPS = 30
SPEED = 1.1
SPEED_TOTAL = TOTAL / SPEED  # 673.05

BG_V5 = {
    "S02a": (f"{BILI}/paizi.mp4", 36.0),
    "S02b": (f"{BILI}/paizi.mp4", 38.8),
    "S03a": (f"{BILI}/sss.mp4", 100.0),
    "S03b": (f"{BILI}/sss.mp4", 102.8),
    "S04": (f"{NEW}/t2第一抽.mp4", 3.2),
    "S24b": (f"{NEW}/抽卡过程延时.mp4", 85.0),
}
SEG_SPLIT = 372.0
CROP_Y = 555  # 横屏 crop 起点（1080×810）


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ff(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])
    return r


# ---------- 字幕生成（v5：新位置 + 动态字号 + 普惠体） ----------
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


def gen_ass_v5(subs, path):
    """竖屏字幕：框 Y1435~1545（MarginV=375，底=1920-375=1545），宽 720（MarginL/R=180）。"""
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
    """横屏字幕：1080×810 画面内底部（MarginV=36），MarginL/R=80。"""
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


def gen_progress_cmds(total, path, step=0.5):
    lines = []
    t = 0.0
    while t <= total + 1e-6:
        w = max(1, int(1080 * t / total))
        lines.append(f"{t:.1f} drawbox w {w};")
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


def probe_frames(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


# ---------- setup（字体系统注册，防沙盒重置后失效） ----------
def cmd_setup():
    os.makedirs(os.path.expanduser("~/.fonts"), exist_ok=True)
    for ttf in os.listdir(FONTS):
        shutil.copy(f"{FONTS}/{ttf}", os.path.expanduser(f"~/.fonts/{ttf}"))
    r = sh("fc-cache", "-f", os.path.expanduser("~/.fonts"))
    chk = sh("fc-match", "Alibaba PuHuiTi 3.0")
    print(f"[setup] fc-match → {chk.stdout.strip()}")
    assert "Alibaba" in chk.stdout or "PuHuiTi" in chk.stdout or "alipuhui" in chk.stdout, \
        f"普惠体系统注册失败: {chk.stdout}"


# ---------- bg ----------
def cmd_bg():
    shots, _ = load_shots()
    for sid, (src, offset) in BG_V5.items():
        s = next(x for x in shots if x["id"] == sid)
        out = f"{BUILD}/bg_{sid}.mp4"
        if os.path.exists(out) and probe_frames(out) == s["n"]:
            print(f"[skip] bg_{sid}")
            continue
        ff("-ss", f"{offset:.3f}", "-i", src,
           "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",
           "-frames:v", str(s["n"]), "-c:v", "libx264", "-crf", "18", "-preset", "fast", out)
        print(f"[ok] bg_{sid}.mp4 {s['n']}帧")


# ---------- seq ----------
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


# ---------- enc ----------
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
        if sid in BG_V5:
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


# ---------- cat ----------
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


# ---------- final（竖屏：字幕Y1435~1545） ----------
def final_pass(seg, t0, t1):
    dur = t1 - t0
    n_seg = round(dur * FPS)
    ass_file = f"{BUILD}/subs_{seg}.ass"
    cmds_file = f"{BUILD}/progress_{seg}.cmds"
    subs = json.load(open(SUBS, encoding="utf-8"))
    evs = []
    for x in subs:
        st, en = x["start"], x["end"]
        if en <= t0 or st >= t1:
            continue
        evs.append({"start": round(max(st, t0) - t0, 3), "end": round(min(en, t1) - t0, 3),
                    "text": x["text"]})
    gen_ass_v5(evs, ass_file)
    gen_progress_cmds(TOTAL, cmds_file)
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
    print(f"[final-{seg}] done")


def cmd_final():
    shots, _ = load_shots()
    split = None
    for s in shots:
        if s["start"] >= SEG_SPLIT:
            split = s["start"]
            break
    split = split or SEG_SPLIT
    split = round(round(split * FPS) / FPS, 6)
    print(f"切点: {split:.4f}s ({round(split*FPS)}帧)")
    if not (os.path.exists(f"{BUILD}/final_A.mp4") and os.path.getsize(f"{BUILD}/final_A.mp4") > 1e6):
        final_pass("A", 0.0, split)
    if not (os.path.exists(f"{BUILD}/final_B.mp4") and os.path.getsize(f"{BUILD}/final_B.mp4") > 1e6):
        final_pass("B", split, TOTAL)
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
    cmds_file = f"{BUILD}/progress_{seg}.cmds"  # 复用同一进度指令
    subs = json.load(open(SUBS, encoding="utf-8"))
    evs = []
    for x in subs:
        st, en = x["start"], x["end"]
        if en <= t0 or st >= t1:
            continue
        evs.append({"start": round(max(st, t0) - t0, 3), "end": round(min(en, t1) - t0, 3),
                    "text": x["text"]})
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
    print(f"[final_h-{seg}] done")


def cmd_final_h():
    shots, _ = load_shots()
    split = None
    for s in shots:
        if s["start"] >= SEG_SPLIT:
            split = s["start"]
            break
    split = round(round((split or SEG_SPLIT) * FPS) / FPS, 6)
    if not (os.path.exists(f"{BUILD}/final_h_A.mp4") and os.path.getsize(f"{BUILD}/final_h_A.mp4") > 1e6):
        final_h_pass("A", 0.0, split)
    if not (os.path.exists(f"{BUILD}/final_h_B.mp4") and os.path.getsize(f"{BUILD}/final_h_B.mp4") > 1e6):
        final_h_pass("B", split, TOTAL)
    lst = f"{BUILD}/fin_h.txt"
    open(lst, "w").write(
        f"ffconcat version 1.0\nfile 'final_h_A.mp4'\nfile 'final_h_B.mp4'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
       "-video_track_timescale", "30000", f"{BUILD}/vfinal_h.mp4")
    print(f"[final_h] vfinal_h {probe_frames(f'{BUILD}/vfinal_h.mp4')}帧")


# ---------- audio ----------
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


# ---------- mux ----------
def cmd_mux():
    os.makedirs(OUT, exist_ok=True)
    out = f"{BUILD}/v5_1x.mp4"
    ff("-i", f"{BUILD}/vfinal.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux] {out}")


def cmd_mux_h():
    out = f"{BUILD}/v5h_1x.mp4"
    ff("-i", f"{BUILD}/vfinal_h.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux_h] {out}")


# ---------- speed（1.1x 提速，不变调） ----------
def cmd_speed():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v5-竖屏.mp4"
    ff("-i", f"{BUILD}/v5_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-crf", "17", "-preset", "slow",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    n = probe_frames(out)
    print(f"[speed] 竖屏成片 {n}帧")


def cmd_speed_h():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v5-横屏.mp4"
    ff("-i", f"{BUILD}/v5h_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-crf", "17", "-preset", "slow",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed_h] 横屏成片 {probe_frames(out)}帧")


# ---------- srt 重定时（1.1x） ----------
def retime_srt(src, dst):
    def ts2s(ts):
        h, m, rest = ts.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    def s2ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"

    out, block = [], []
    for line in open(src, encoding="utf-8").read().split("\n") + [""]:
        if line.strip() == "":
            if block:
                m = re.match(r"(\d+)\s*\n([\d:,.]+) --> ([\d:,.]+)", "\n".join(block))
                if m:
                    st, en = ts2s(m.group(2)) / SPEED, ts2s(m.group(3)) / SPEED
                    txt = "\n".join(block[2:])
                    out += [m.group(1), f"{s2ts(st)} --> {s2ts(en)}"] + txt.split("\n") + [""]
                block = []
        else:
            block.append(line)
    open(dst, "w", encoding="utf-8").write("\n".join(out))


def gen_srt_from_json(path):
    subs = json.load(open(SUBS, encoding="utf-8"))

    def s2ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"

    out = []
    for i, s in enumerate(subs, 1):
        st, en = s["start"] / SPEED, s["end"] / SPEED
        out += [f"{i}", f"{s2ts(st)} --> {s2ts(en)}", s["text"], ""]
    open(path, "w", encoding="utf-8").write("\n".join(out))


# ---------- qc ----------
def cmd_qc():
    ok_all = True
    report = {"gates": {}, "BUILD_SUCCESS": True}
    for tag, fname, w, h in [("竖屏", "AI视频画布横评-第一篇-价格篇-成片v5-竖屏.mp4", 1080, 1920),
                              ("横屏", "AI视频画布横评-第一篇-价格篇-成片v5-横屏.mp4", 1080, 810)]:
        out = f"{OUT}/{fname}"
        gates = {}
        r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", out, "-f", "null", "-")
        gates[f"{tag}_G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
        n = probe_frames(out)
        expect = round(SPEED_TOTAL * FPS)
        # 提速重采样（setpts/1.1 + fps=30）存在 ≤0.4s 舍入漂移，与 G3 时长门禁（±0.5s）对齐
        gates[f"{tag}_G2_帧数"] = "PASS" if abs(n - expect) <= 15 else f"FAIL {n}≠{expect}±15"
        dur_raw = ""
        for _ in range(3):  # 偶发读空重试
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
        report["gates"].update(gates)
        report[f"{tag}_frames"] = n
        report[f"{tag}_duration"] = dur
        for k, v in gates.items():
            print(f"  {k}: {v}")
        ok_all = ok_all and all(v == "PASS" for v in gates.values())
    report["BUILD_SUCCESS"] = ok_all
    json.dump(report, open(f"{OUT}/qc_report_v5.json", "w"), ensure_ascii=False, indent=1)
    print("BUILD_SUCCESS" if ok_all else "BUILD_FAILED")
    # srt（竖屏/横屏通用，时间轴相同）
    gen_srt_from_json(f"{OUT}/AI视频画布横评-第一篇-价格篇-字幕v5.srt")
    print("[qc] 字幕v5.srt 已生成")
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
