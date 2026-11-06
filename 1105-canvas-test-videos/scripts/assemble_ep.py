#!/usr/bin/env python3
"""assemble_ep.py · ep2/ep3 通用总装（v8 架构复用，常量按集分支）。
用法: EP=ep2 python3 assemble_ep.py setup|bg|seq|enc|cat|final|final_h|audio|mux|mux_h|speed|speed_h|subs|subs_h|qc

与 v8 的差异（对照 ep1）：
  - SPEED=1.0（用户指示：第二三篇配音不需要 1.1x 提速，正常速度生成）
  - 镜表/画布/帧目录/字幕/配音按 EP 分支；镜头边界全部 whisper 实测（G11 语义锚点用脚本卡文本流）
  - G13 改为字幕带抽样像素检查（3 卡点白像素在带内）
  - 无 SUBS_WHISPER 独立文件：卡即时间真值（句级全局对齐生成，_provenance 见 build_cards_ep.py）
"""
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np

EP = os.environ.get("EP", "ep2")
assert EP in ("ep2", "ep3"), "EP 必须是 ep2|ep3"

WORK = f"/home/z/my-project/{EP}-work"
REPO = "/home/z/my-project/repo/1105-canvas-test-videos"
CLIPS = f"{REPO}/clips"

if EP == "ep2":
    EP_NAME = "第二篇-功能篇"
    SHOTS = f"{REPO}/04-ep1-production/ep2_shots_real.json"
    CANVAS_DIR = f"{REPO}/04-ep1-production/canvas-ep2"
    FRAMES = f"{WORK}/frames"
    BUILD = f"{WORK}/build"
    OUT = f"{WORK}/output"
    NARR = f"{REPO}/04-ep1-production/materials/audio/1106-1239-2-功能篇.mp3"
    SUBS = f"{REPO}/04-ep1-production/ep2_subtitles.json"
    TOTAL = 566.988
    # (镜, 分句特征子串) —— 关键概念与画面的从属关系断言
    ANCHORS = [("S03", "依然是AniShort"), ("S08", "Agent对话优先型"),
               ("S12", "小云雀和纳逗Pro的支持最为全面"), ("S24", "6项基础功能"),
               ("S38", "对号入座"), ("S39", "掺水")]
    BG_EP = {
        "S01": (f"{CLIPS}/ep2_recap_ep1.mp4", 0.0, "fit"),
        "S39": (f"{CLIPS}/ep2_t2grid_9plat.mp4", 0.0, "fit"),
    }
else:
    EP_NAME = "第三篇-实测篇"
    SHOTS = f"{REPO}/04-ep1-production/ep3_shots_real.json"
    CANVAS_DIR = f"{REPO}/04-ep1-production/canvas-ep3"
    FRAMES = f"{WORK}/frames"
    BUILD = f"{WORK}/build"
    OUT = f"{WORK}/output"
    NARR = f"{REPO}/04-ep1-production/materials/audio/1106-1510-3-实测篇.mp3"
    SUBS = f"{REPO}/04-ep1-production/ep3_subtitles.json"
    TOTAL = 689.528
    ANCHORS = [("S02", "一模一样的提示词和参考图"), ("S11", "没有任何证据"),
               ("S21", "齿轮咬紧簧片，天亮前定能归位"), ("S24", "默认停留在480P"),
               ("S33", "2分48秒"), ("S41", "背景音乐")]
    BG_EP = {
        "S02": (f"{CLIPS}/ep3_t2grid_10plat.mp4", 0.0, "fit"),
        "S15": (f"{CLIPS}/ep3_t1_scene_s15.mp4", 0.0, "cover"),
        "S16": (f"{CLIPS}/ep1_t2take1_s04_3-10.mp4", 0.0, "cover", {"loop": True}),  # 7s切片循环盖8.2s镜
        "S17": (f"{CLIPS}/ep3_t3_scene_s17.mp4", 0.0, "cover"),
        "S18": (f"{CLIPS}/ep3_t4_scene_s18.mp4", 0.0, "cover"),
    }

BGM = f"{REPO}/04-ep1-production/materials/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
CANVAS_ASSETS = f"{REPO}/04-ep1-production/assets"
WM = f"{CANVAS_ASSETS}/wm_v8.png"
WM_SRC = f"{CANVAS_ASSETS}/浮水印-简版竖版黑字alpha.png"
FONTS = f"{CANVAS_ASSETS}/fonts"
FPS = 30
SPEED = 1.0                      # 用户指示：第二三篇正常速度
SPEED_TOTAL = TOTAL / SPEED
PAD_COLOR = "0x131110"
CROP_Y = 555
SEG_SPLIT = TOTAL * 0.62         # final A/B 分段编码防超时（比例取整到镜边界）


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


VERT_SIZES = [68, 56, 48]
HORZ_SIZES = [56, 44, 38]


def ts_ass(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


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


def _tier_tag(card, sizes):
    t = card.get("tier", 0)
    return "" if t == 0 else f"{{\\fs{sizes[t]}}}"


def gen_ass_v(subs, path):
    head = _ass_header(1920, 180, 180, 375, VERT_SIZES[0])
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{_tier_tag(s, VERT_SIZES)}{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


def gen_ass_h(subs, path):
    head = _ass_header(810, 80, 80, 36, HORZ_SIZES[0])
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{_tier_tag(s, HORZ_SIZES)}{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


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


def cmd_setup():
    os.makedirs(os.path.expanduser("~/.fonts"), exist_ok=True)
    for ttf in os.listdir(FONTS):
        shutil.copy(f"{FONTS}/{ttf}", os.path.expanduser(f"~/.fonts/{ttf}"))
    sh("fc-cache", "-f", os.path.expanduser("~/.fonts"))
    chk = sh("fc-match", "Alibaba PuHuiTi 3.0")
    print(f"[setup] fc-match → {chk.stdout.strip()}")
    assert "Alibaba" in chk.stdout or "PuHuiTi" in chk.stdout or "alipuhui" in chk.stdout
    # G8 前置：卡自检（无退化卡/同句同档/时间单调/全覆盖）
    cards = load_subs()
    punct = "，。：；！？、…—,.:;!?~“”\"'（）()《》<>【】"
    degen = [c["text"] for c in cards if len(re.sub(f"[{re.escape(punct)}]", "", c["text"])) <= 2]
    assert not degen, f"G8: 残留退化卡 {degen[:5]}"
    for x, y in zip(cards, cards[1:]):
        assert y["start"] >= x["start"] - 0.01, f"G8: 卡时间非单调 @{x['end']}"
        if x.get("sent") == y.get("sent"):
            assert x.get("tier") == y.get("tier"), f"G8: 同句跳档「{x['text']}」"
    n_cards = len(cards)
    print(f"[setup] G8 前置对账 PASS：{n_cards} 卡，无退化/同句同档/时间单调")


# ---------- bg ----------
def bg_vf(mode):
    if mode == "fit":
        return (f"scale=1080:810:force_original_aspect_ratio=decrease,"
                f"pad=1080:810:(ow-iw)/2:(oh-ih)/2:color={PAD_COLOR},"
                f"pad=1080:1920:0:{CROP_Y}:color={PAD_COLOR},fps=30,format=yuv420p")
    return (f"scale=1080:810:force_original_aspect_ratio=increase,crop=1080:810,"
            f"pad=1080:1920:0:{CROP_Y}:color={PAD_COLOR},fps=30,format=yuv420p")


def cmd_bg():
    shots, _ = load_shots()
    for sid, entry in BG_EP.items():
        src, offset, mode = entry[0], entry[1], entry[2]
        opt = entry[3] if len(entry) > 3 else {}
        s = next(x for x in shots if x["id"] == sid)
        out = f"{BUILD}/bg_{sid}.mp4"
        if os.path.exists(out) and probe_frames(out) == s["n"]:
            print(f"[skip] bg_{sid}")
            continue
        pre = ["-stream_loop", "-1"] if opt.get("loop") else []
        ff(*pre, "-ss", f"{offset:.3f}", "-i", src,
           "-vf", bg_vf(mode),
           "-frames:v", str(s["n"]), "-c:v", "libx264", "-crf", "18", "-preset", "fast", out)
        print(f"[ok] bg_{sid}.mp4 {s['n']}帧 ({mode})")


# ---------- seq / enc / cat ----------
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
        if sid in BG_EP:
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


# ---------- final（只叠等比水印，无进度条） ----------
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
    vfc = (
        "[0:v]format=yuv420p[base];"
        "[1:v]format=rgba[wm];"
        "[base][wm]overlay=0:0[vout]")
    if seg == "A":
        ff("-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_{seg}.mp4")
    else:
        ff("-ss", f"{t0:.6f}", "-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_{seg}.mp4")
    print(f"[final-{seg}] 等比水印✓（无进度条/无字幕）")


def cmd_final():
    split = find_split()
    for seg, (a, b) in {"A": (0.0, split), "B": (split, TOTAL)}.items():
        p = f"{BUILD}/final_{seg}.mp4"
        if not (os.path.exists(p) and probe_frames(p) == round((b - a) * FPS)):
            final_pass(seg, a, b)
    lst = f"{BUILD}/fin.txt"
    open(lst, "w").write(
        f"ffconcat version 1.0\nfile 'final_A.mp4'\nfile 'final_B.mp4'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
       "-video_track_timescale", "30000", f"{BUILD}/vfinal.mp4")
    print(f"[final] vfinal {probe_frames(f'{BUILD}/vfinal.mp4')}帧")


def final_h_pass(seg, t0, t1):
    dur = t1 - t0
    n_seg = round(dur * FPS)
    vfc = (
        "[0:v]format=yuv420p[base];"
        "[1:v]format=rgba[wm];"
        "[base][wm]overlay=0:0[wmd],"
        f"[wmd]crop=1080:810:0:{CROP_Y}[vout]")
    if seg == "A":
        ff("-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_h_{seg}.mp4")
    else:
        ff("-ss", f"{t0:.6f}", "-i", f"{BUILD}/vtrack.mp4",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
           "-filter_complex", vfc, "-map", "[vout]", "-frames:v", str(n_seg),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           f"{BUILD}/final_h_{seg}.mp4")
    print(f"[final_h-{seg}] 等比水印+裁切（无进度条/无字幕）")


def cmd_final_h():
    split = find_split()
    for seg, (a, b) in {"A": (0.0, split), "B": (split, TOTAL)}.items():
        p = f"{BUILD}/final_h_{seg}.mp4"
        if not (os.path.exists(p) and probe_frames(p) == round((b - a) * FPS)):
            final_h_pass(seg, a, b)
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


def cmd_mux():
    os.makedirs(OUT, exist_ok=True)
    out = f"{BUILD}/v_1x.mp4"
    ff("-i", f"{BUILD}/vfinal.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux] {out}")


def cmd_mux_h():
    out = f"{BUILD}/vh_1x.mp4"
    ff("-i", f"{BUILD}/vfinal_h.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux_h] {out}")


# ---------- speed（SPEED=1.0：仍走统一链路保证帧数精确钳制） ----------
def cmd_speed():
    out = f"{BUILD}/speed_v.mp4"
    n_exact = round(SPEED_TOTAL * FPS)
    ff("-i", f"{BUILD}/v_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]", "-frames:v", str(n_exact),
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed] 干净竖屏 {probe_frames(out)}帧（1.0x 正常速度）")


def cmd_speed_h():
    out = f"{BUILD}/speed_h.mp4"
    n_exact = round(SPEED_TOTAL * FPS)
    ff("-i", f"{BUILD}/vh_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]", "-frames:v", str(n_exact),
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed_h] 干净横屏 {probe_frames(out)}帧")


# ---------- subs（最后一步烧字幕；SPEED=1.0 → 时间原样） ----------
def burn_subs(clean, ass_file, out, gen_ass):
    subs = [{**c, "start": c["start"] / SPEED, "end": c["end"] / SPEED}
            for c in load_subs()]
    gen_ass(subs, ass_file)
    ff("-i", clean,
       "-vf", f"subtitles={ass_file}:fontsdir={FONTS}",
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[subs] {out.split('/')[-1]} 烧录 {len(subs)} 卡")


def cmd_subs():
    os.makedirs(OUT, exist_ok=True)
    burn_subs(f"{BUILD}/speed_v.mp4", f"{BUILD}/subs_v.ass",
              f"{OUT}/AI视频画布横评-{EP_NAME}-成片v1-竖屏.mp4", gen_ass_v)


def cmd_subs_h():
    burn_subs(f"{BUILD}/speed_h.mp4", f"{BUILD}/subs_h.ass",
              f"{OUT}/AI视频画布横评-{EP_NAME}-成片v1-横屏.mp4", gen_ass_h)


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


# ---------- QC ----------
def grab_frame(path, t, w, h):
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-ss", f"{t:.3f}", "-i", path,
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    return a.reshape(h, w, 3)


def measure_pbar_width(frame):
    top = frame[0:8, :, :].astype(int)
    dr = np.abs(top[:, :, 0] - 229) < 45
    dg = np.abs(top[:, :, 1] - 91) < 45
    db = np.abs(top[:, :, 2] - 70) < 45
    mask = dr & dg & db
    cols = np.where(mask.any(axis=0))[0]
    return (int(cols.max()) + 1) if len(cols) else 0


def measure_video_window(frame, bg_rgb=(0x13, 0x11, 0x10)):
    band = frame[CROP_Y:CROP_Y + 810, :, :].astype(int)
    d = np.abs(band - np.array(bg_rgb)).sum(axis=2)
    rows = np.where((d > 30).sum(axis=1) > 20)[0]
    if not len(rows):
        return None
    r0, r1 = int(rows.min()), int(rows.max())
    sub = band[r0:r1 + 1, :, :]
    d2 = np.abs(sub - np.array(bg_rgb)).sum(axis=2)
    cols = np.where((d2 > 30).sum(axis=0) > 5)[0]
    c0, c1 = int(cols.min()), int(cols.max())
    return (c0, CROP_Y + r0, c1 - c0 + 1, r1 - r0 + 1)


def expected_fit_rect(src_w, src_h):
    scale = min(1080 / src_w, 810 / src_h)
    w = int(round(src_w * scale)) // 2 * 2
    h = int(round(src_h * scale)) // 2 * 2
    x = (1080 - w) // 2
    y = CROP_Y + (810 - h) // 2
    return (x, y, w, h)


def cmd_qc():
    ok_all = True
    report = {"gates": {}, "BUILD_SUCCESS": True}
    files = [("竖屏", f"AI视频画布横评-{EP_NAME}-成片v1-竖屏.mp4", 1080, 1920),
             ("横屏", f"AI视频画布横评-{EP_NAME}-成片v1-横屏.mp4", 1080, 810)]
    for tag, fname, w, h in files:
        out = f"{OUT}/{fname}"
        gates = {}
        r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", out, "-f", "null", "-")
        gates[f"{tag}_G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
        n = probe_frames(out)
        expect = round(SPEED_TOTAL * FPS)
        gates[f"{tag}_G2_帧数"] = "PASS" if abs(n - expect) <= 2 else f"FAIL {n}≠{expect}"
        dur_raw = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", out).stdout.strip()
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
        src = f"{BUILD}/{'vfinal.mp4' if tag == '竖屏' else 'vfinal_h.mp4'}"
        if os.path.exists(src):
            fw, fh = (1080, 1920) if tag == "竖屏" else (1080, 810)
            wmid = measure_pbar_width(grab_frame(src, TOTAL * 0.5, fw, fh))
            wend = measure_pbar_width(grab_frame(src, TOTAL - 0.2, fw, fh))
            no_bar = wmid < 50 and wend < 50
            gates[f"{tag}_G10_无进度条"] = "PASS" if no_bar else f"FAIL wmid={wmid} wend={wend}"
        report["gates"].update(gates)
        report[f"{tag}_frames"] = n
        report[f"{tag}_duration"] = dur
        for k, v in gates.items():
            print(f"  {k}: {v}")
        ok_all = ok_all and all(v == "PASS" for v in gates.values())

    # G8 字幕对账：ASS 卡数 == JSON 卡数
    n_cards = len(load_subs())
    n_ass_v = open(f"{BUILD}/subs_v.ass", encoding="utf-8").read().count("Dialogue:")
    n_ass_h = open(f"{BUILD}/subs_h.ass", encoding="utf-8").read().count("Dialogue:")
    g8 = (n_ass_v == n_cards and n_ass_h == n_cards)
    report["gates"]["G8_字幕对账"] = "PASS" if g8 else f"FAIL cards={n_cards} v={n_ass_v} h={n_ass_h}"
    print(f"  G8_字幕对账: {report['gates']['G8_字幕对账']}")
    ok_all = ok_all and g8

    # G11 语义锚点：分句特征卡区间 ⊆ 对应镜区间（卡文本流定位）
    cards = load_subs()
    shots, _ = load_shots()
    shot_by = {s["id"]: s for s in shots}
    _stream = "".join(c["text"] for c in cards)
    _bounds = [0]
    for c in cards:
        _bounds.append(_bounds[-1] + len(c["text"]))

    def card_span(key):
        p = _stream.find(key)
        assert p >= 0, f"分句特征「{key}」不在卡片文本流中"
        q = p + len(key) - 1
        import bisect as _bi
        i = _bi.bisect_right(_bounds, p) - 1
        j = _bi.bisect_right(_bounds, q) - 1
        return cards[i]["start"], cards[j]["end"]

    g11_detail, g11_ok = [], True
    for sid, key in ANCHORS:
        span = card_span(key)
        s = shot_by[sid]
        inside = span[0] >= s["start"] - 0.05 and span[1] <= s["start"] + s["dur"] + 0.05
        g11_detail.append(f"{sid}「{key[:12]}」卡区间 {span[0]:.2f}~{span[1]:.2f} ⊆ 镜 "
                          f"{s['start']:.2f}~{s['start']+s['dur']:.2f} {'✓' if inside else '✗'}")
        g11_ok = g11_ok and inside
    report["gates"]["G11_语义锚点"] = "PASS" if g11_ok else "FAIL"
    report["G11_detail"] = g11_detail
    for d in g11_detail:
        print(f"  G11: {d}")
    ok_all = ok_all and g11_ok

    # G12 字幕显示质量
    def _vlen(t):
        return sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in t)
    punct = "，。：；！？、…—,.:;!?~“”\"'（）()《》<>【】"
    short = [c["text"] for c in cards if len(re.sub(f"[{re.escape(punct)}]", "", c["text"])) <= 2]
    jump = sum(1 for x, y in zip(cards, cards[1:])
               if x.get("sent") == y.get("sent") and x.get("tier") != y.get("tier"))
    widths = {("v", 0): 720 / VERT_SIZES[0], ("v", 1): 720 / VERT_SIZES[1], ("v", 2): 720 / VERT_SIZES[2],
              ("h", 0): 920 / HORZ_SIZES[0], ("h", 1): 920 / HORZ_SIZES[1], ("h", 2): 920 / HORZ_SIZES[2]}
    over_v = [c["text"] for c in cards if _vlen(c["text"]) > widths[("v", c.get("tier", 0))]]
    over_h = [c["text"] for c in cards if _vlen(c["text"]) > widths[("h", c.get("tier", 0))]]
    g12 = (not short) and jump == 0 and not over_v and not over_h
    report["gates"]["G12_字幕质量"] = ("PASS" if g12 else
                                     f"FAIL short={short[:3]} jump={jump} over_v={over_v[:2]}")
    print(f"  G12_字幕质量: {report['gates']['G12_字幕质量']}")
    ok_all = ok_all and g12

    # G13 字幕带抽样像素：3 个卡中点，Y1435~1545 带内白像素 > 800（字幕在场）
    vfinal = f"{OUT}/AI视频画布横评-{EP_NAME}-成片v1-竖屏.mp4"
    g13_detail, g13_ok = [], True
    for c in [cards[len(cards)//4], cards[len(cards)//2], cards[3*len(cards)//4]]:
        t = (c["start"] + c["end"]) / 2
        f = grab_frame(vfinal, t, 1080, 1920)
        band = f[1435:1545, :, :].astype(int)
        white = int(((band.min(axis=2)) > 200).sum())
        ok = white > 800
        g13_detail.append(f"@{t:.1f}s「{c['text'][:10]}」带内白像素={white} {'✓' if ok else '✗'}")
        g13_ok = g13_ok and ok
    report["gates"]["G13_字幕带抽样"] = "PASS" if g13_ok else "FAIL"
    report["G13_detail"] = g13_detail
    for d in g13_detail:
        print(f"  G13: {d}")
    ok_all = ok_all and g13_ok

    # G14 水印等比
    from PIL import Image as _PILImage

    def _wm_aspect(p):
        a = np.array(_PILImage.open(p).convert("RGBA"))
        ys, xs = np.where(a[:, :, 3] > 5)
        if not len(ys):
            return None
        return (xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1)

    a_src, a_v8 = _wm_aspect(WM_SRC), _wm_aspect(WM)
    g14_ok = a_v8 is not None and a_src is not None and abs(a_v8 - a_src) / a_src < 0.02
    report["gates"]["G14_水印等比"] = "PASS" if g14_ok else f"FAIL src={a_src} v8={a_v8}"
    print(f"  G14_水印等比: {report['gates']['G14_水印等比']}")
    ok_all = ok_all and g14_ok

    # G9 素材几何
    g9_detail = []
    g9_ok = True
    for sid, entry in BG_EP.items():
        src, offset, mode = entry[0], entry[1], entry[2]
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
            # 暗/亮场内容敏感 → 采 3 个时刻取最大行数（几何错误时任何时刻都不满格）
            best_rows = 0
            for tt in (min(1.0, s["dur"] * 0.3), s["dur"] / 2, s["dur"] * 0.8):
                fr = grab_frame(bgf, tt, 1080, 1920)
                band = fr[CROP_Y:CROP_Y + 810, :, :].astype(int)
                d = np.abs(band - np.array([0x13, 0x11, 0x10])).sum(axis=2)
                best_rows = max(best_rows, int(((d > 30).sum(axis=1) > 100).sum()))
            ok = best_rows > 810 * 0.85
            g9_detail.append(f"{sid}:cover 视频行max{best_rows}/810 {'✓' if ok else '✗'}")
            g9_ok = g9_ok and ok
    report["gates"]["G9_素材几何"] = "PASS" if g9_ok else "FAIL"
    report["G9_detail"] = g9_detail
    for d in g9_detail:
        print(f"  G9: {d}")
    ok_all = ok_all and g9_ok

    report["BUILD_SUCCESS"] = ok_all
    json.dump(report, open(f"{OUT}/qc_report_{EP}_v1.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("BUILD_SUCCESS" if ok_all else "BUILD_FAILED")
    gen_srt(f"{OUT}/AI视频画布横评-{EP_NAME}-字幕v1.srt")
    print(f"[qc] 字幕v1.srt 已生成")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[1] == "enc" else None
    {"setup": cmd_setup, "bg": cmd_bg, "seq": cmd_seq,
     "enc": lambda: cmd_enc(only), "cat": cmd_cat, "final": cmd_final,
     "final_h": cmd_final_h, "audio": cmd_audio, "mux": cmd_mux, "mux_h": cmd_mux_h,
     "speed": cmd_speed, "speed_h": cmd_speed_h, "subs": cmd_subs, "subs_h": cmd_subs_h,
     "qc": cmd_qc}.get(
        step, lambda: sys.exit(f"用法: EP=ep2|ep3 python3 {sys.argv[0]} setup|bg|...|qc"))()
