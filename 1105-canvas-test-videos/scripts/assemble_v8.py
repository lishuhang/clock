#!/usr/bin/env python3
"""总装 v8（v7 防回归架构上的最小改动版 · 2026-11-07 用户三反馈）：
段: setup|bg|seq|enc|cat|final|final_h|audio|mux|mux_h|speed|speed_h|subs|subs_h|qc

v8 关键修复（对照 2026-11-07 用户反馈）：
  R8 浮水印拉伸扭曲：wm75.png 把 1231x1733（比例 0.710）非等比拉到 1080x1920
     （0.5625）——横向压 0.88x/纵向拉 1.11x。修复=wm_v8.png 等比 fit 宽 1080
     →1080x1520 垂直居中；G14 门禁断言水印内容宽高比与原版一致（±2%）。
  R9 顶部进度条移除（用户：根本看不清）：final/final_h 不再叠轨道+drawbox；
     G10 改为断言顶部 8 行无品牌橙（防止旧链回归）。
  R10 素材切片化（用户原则：首次下载即切片，之后仅引用切片）：
     BG 表全部改指 repo clips/ 切片（每片 1.5~6MB，含 MANIFEST 索引）；
     大原件（抽卡延时 323MB / B站原片 81MB+30MB）不再重下；配音/BGM 入库。
  R11 应景视频穿插（防单调）：S25 加抽卡延时另一窗背景（fit）、S34 加
     T2第三抽循环背景（cover + stream_loop）；两镜透明叠层化 + scrim 0.78。
     时间轴零改动（镜边界/Σ帧 22211 不变）→ 音画同步零风险。

门禁：G1-G9/G11-G13 沿用 v7 + G10 反转（无进度条）+ G14 水印比例
"""
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np

WORK = "/home/z/my-project/ep1-work"
REPO = "/home/z/my-project/repo/1105-canvas-test-videos"
SHOTS = f"{REPO}/04-ep1-production/ep1_shots_v7.json"   # 时间轴 v8 零改动，沿用 v7 镜表
CANVAS_DIR = f"{REPO}/04-ep1-production/canvas"
FRAMES = f"{WORK}/frames_v8"
CLIPS = f"{REPO}/clips"
BUILD = f"{WORK}/build_v8"
OUT = f"{WORK}/output"
NARR = f"{REPO}/04-ep1-production/materials/audio/1105-1200-第一篇.mp3"      # R10: 入库音频，不再重下
BGM = f"{REPO}/04-ep1-production/materials/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
CANVAS_ASSETS = f"{REPO}/04-ep1-production/assets"
WM = f"{CANVAS_ASSETS}/wm_v8.png"   # R8: 等比水印（原 wm75.png 非等比拉伸已废弃）
WM_SRC = f"{CANVAS_ASSETS}/浮水印-简版竖版黑字alpha.png"  # G14 比例基准
FONTS = f"{CANVAS_ASSETS}/fonts"
SUBS = f"{REPO}/04-ep1-production/ep1_subtitles_v7.json"  # 显示用卡（R5/R6，含 tier）
SUBS_WHISPER = f"{REPO}/04-ep1-production/ep1_subtitles_whisper.json"  # 时间真值（R1 源）
SENTS_REAL = f"{REPO}/04-ep1-production/ep1_sentences_real.json"  # 句级实测（G11）
TOTAL = 740.36
FPS = 30
SPEED = 1.1
SPEED_TOTAL = TOTAL / SPEED  # 673.05
PAD_COLOR = "0x131110"  # 与全片底色一致（铁律17）
CROP_Y = 555

# R10: bg 全部改用 repo 切片（offset 已折算进切片窗口，从切片内 0 起算）；
# 第 4 元 loop=True 表示源短于镜头时 stream_loop 循环（S34 37.6s ← 15.03s 切片）
BG_V8 = {
    "S02a": (f"{CLIPS}/ep1_paizi_s02_36-48.mp4", 0.0, "fit"),       # 牌子 1280x720→1080x608
    "S02b": (f"{CLIPS}/ep1_paizi_s02_36-48.mp4", 2.8, "fit"),
    "S03a": (f"{CLIPS}/ep1_sss_s03_100-113.mp4", 0.0, "fit"),       # 丧尸 1280x548→1080x462
    "S03b": (f"{CLIPS}/ep1_sss_s03_100-113.mp4", 2.8, "fit"),
    "S04": (f"{CLIPS}/ep1_t2take1_s04_3-10.mp4", 0.0, "cover"),    # 竖版 720x1280 全宽取中段
    "S24b": (f"{CLIPS}/ep1_gacha_timelapse_s24b_85-96.mp4", 0.0, "fit"),   # 1080x674 预缩切片
    # R11 v8 新增应景背景（防单调；时间轴零改动）
    "S25": (f"{CLIPS}/ep1_gacha_timelapse_s25_150-160.mp4", 0.0, "fit"),
    "S34": (f"{CLIPS}/ep1_t2take3_s34_loop.mp4", 0.0, "cover", {"loop": True}),
}
SEG_SPLIT = 372.0  # 仅用于 final A/B 分段编码（时长长，分两段防超时）；与进度条无关


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


# ---------- 字幕生成（v7：tier 句内统一制，时间 = whisper ÷1.1） ----------
VERT_SIZES = [68, 56, 48]   # tier 0/1/2 → 竖屏字号（v5 验收规格）
HORZ_SIZES = [56, 44, 38]   # tier 0/1/2 → 横屏字号


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
    """R6: tier 已句内统一写入 JSON；基础样式=档位 0，非 0 档才打 \fs 标签。"""
    t = card.get("tier", 0)
    return "" if t == 0 else f"{{\\fs{sizes[t]}}}"


def gen_ass_v(subs, path):
    """竖屏字幕：框 Y1435~1545（MarginV=375），宽 720（MarginL/R=180），字号 68/56/48 句内统一。"""
    head = _ass_header(1920, 180, 180, 375, VERT_SIZES[0])
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{_tier_tag(s, VERT_SIZES)}{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


def gen_ass_h(subs, path):
    """横屏字幕：1080×810 画面内底部（MarginV=36），字号 56/44/38 句内统一。"""
    head = _ass_header(810, 80, 80, 36, HORZ_SIZES[0])
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{_tier_tag(s, HORZ_SIZES)}{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


# R9: gen_seg_cmds 已删（进度条移除）；find_split 仅用于 final A/B 分段编码防超时


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


# ---------- setup（字体注册 + G8 血缘对账：v7 显示卡 ← whisper 时间真值） ----------
def cmd_setup():
    os.makedirs(os.path.expanduser("~/.fonts"), exist_ok=True)
    for ttf in os.listdir(FONTS):
        shutil.copy(f"{FONTS}/{ttf}", os.path.expanduser(f"~/.fonts/{ttf}"))
    r = sh("fc-cache", "-f", os.path.expanduser("~/.fonts"))
    chk = sh("fc-match", "Alibaba PuHuiTi 3.0")
    print(f"[setup] fc-match → {chk.stdout.strip()}")
    assert "Alibaba" in chk.stdout or "PuHuiTi" in chk.stdout or "alipuhui" in chk.stdout, \
        f"普惠体系统注册失败: {chk.stdout}"
    # G8 前置：显示卡（v7）↔ whisper 真值对账（时间零漂移 + 文本流守恒 + 分卡质量）
    cards = load_subs()
    wh = json.load(open(SUBS_WHISPER, encoding="utf-8"))["cards"]
    a = "".join(c["text"] for c in cards).replace(" ", "")
    b = "".join(c["text"] for c in wh).replace(" ", "")
    assert a == b, "G8: 显示卡与 whisper 文本流不守恒"
    starts = {c["start"] for c in wh}
    ends = {c["end"] for c in wh}
    for c in cards:
        if c.get("split"):
            continue  # 再平衡拆分卡的内插点豁免（首尾仍为 whisper 锚点，见 resplit_subs.py）
        assert c["start"] in starts and c["end"] in ends, \
            f"G8: 卡 @{c['start']:.2f} 时间锚点非 whisper 实测"
    import re as _re
    punct = "，。：；！？、…—,.:;!?~“”\"'（）()《》<>【】"
    degen = [c for c in cards if len(_re.sub(f"[{_re.escape(punct)}]", "", c["text"])) <= 2]
    assert not degen, f"G8: 残留退化卡 {[c['text'] for c in degen[:5]]}"
    for x, y in zip(cards, cards[1:]):
        if x.get("sent") == y.get("sent"):
            assert x.get("tier") == y.get("tier"), \
                f"G8: 同句跳档 @{x['end']:.2f}「{x['text']}」→「{y['text']}」"
    # 镜头帧数守恒（v7 三镜边界改动后 Σ帧 仍 = 22211）
    shots, total_n = load_shots()
    assert total_n == round(TOTAL * FPS), f"G8: 总帧数 {total_n} ≠ {round(TOTAL*FPS)}"
    print(f"[setup] G8 前置对账 PASS：{len(cards)} 显示卡 ← {len(wh)} whisper 锚点，"
          f"文本流守恒/零漂移/无退化卡/同句同档")


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
    for sid, entry in BG_V8.items():
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
        print(f"[ok] bg_{sid}.mp4 {s['n']}帧 ({mode}{' 循环' if opt.get('loop') else ''})")


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
        if sid in BG_V8:
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


# ---------- final（竖屏：R7 只叠水印+进度条，字幕移到提速后烧） ----------
def seg_subs_evs(subs, t0, t1):
    evs = []
    for x in subs:
        st, en = x["start"], x["end"]
        if en <= t0 or st >= t1:
            continue
        evs.append({"start": round(max(st, t0) - t0, 3), "end": round(min(en, t1) - t0, 3),
                    "text": x["text"], "tier": x.get("tier", 0), "sent": x.get("sent")})
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
    vfc = (
        "[0:v]format=yuv420p[base];"
        "[1:v]format=rgba[wm];"
        "[base][wm]overlay=0:0[vout]")  # R9: 只叠等比水印（进度条已按用户要求移除）
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
    vfc = (
        "[0:v]format=yuv420p[base];"
        "[1:v]format=rgba[wm];"
        "[base][wm]overlay=0:0[wmd],"
        f"[wmd]crop=1080:810:0:{CROP_Y}[vout]")  # R9: 水印→裁切（无进度条/无字幕）
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


# ---------- mux ----------
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


# ---------- speed（R7：出干净提速成片，字幕随后烧） ----------
def cmd_speed():
    out = f"{BUILD}/v7_speed_v.mp4"
    # 帧数精确钳制（v4 工艺回归）：fps 重采样会漂 ±15 帧（v7 丢此参数致 G3 边缘 FAIL）
    n_exact = round(SPEED_TOTAL * FPS)
    ff("-i", f"{BUILD}/v6_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]", "-frames:v", str(n_exact),
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed] 干净竖屏（无字幕）{probe_frames(out)}帧")


def cmd_speed_h():
    out = f"{BUILD}/v7_speed_h.mp4"
    n_exact = round(SPEED_TOTAL * FPS)
    ff("-i", f"{BUILD}/v6h_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]", "-frames:v", str(n_exact),
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[speed_h] 干净横屏（无字幕）{probe_frames(out)}帧")


# ---------- subs（R7：最后一步，在提速成片上烧字幕，时间 = whisper ÷1.1） ----------
def burn_subs(clean, ass_file, out, gen_ass):
    """字幕烧录独立成段：字幕相关改动只需重跑本段（单次重编码，不碰画面管线）。"""
    subs = [{**c, "start": c["start"] / SPEED, "end": c["end"] / SPEED}
            for c in load_subs()]  # 成片时间 = canvas 时间 ÷1.1
    gen_ass(subs, ass_file)
    ff("-i", clean,
       "-vf", f"subtitles={ass_file}:fontsdir={FONTS}",
       "-c:v", "libx264", "-crf", "17", "-preset", "fast",
       "-c:a", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[subs] {out.split('/')[-1]} 烧录 {len(subs)} 卡（÷{SPEED} 重定时）")


def cmd_subs():
    os.makedirs(OUT, exist_ok=True)
    burn_subs(f"{BUILD}/v7_speed_v.mp4", f"{BUILD}/subs_v.ass",
              f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v8-竖屏.mp4", gen_ass_v)


def cmd_subs_h():
    burn_subs(f"{BUILD}/v7_speed_h.mp4", f"{BUILD}/subs_h.ass",
              f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v8-横屏.mp4", gen_ass_h)


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
    files = [("竖屏", "AI视频画布横评-第一篇-价格篇-成片v8-竖屏.mp4", 1080, 1920),
             ("横屏", "AI视频画布横评-第一篇-价格篇-成片v8-横屏.mp4", 1080, 810)]
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
        # G10（R9 反转）：顶部 8 行不得再有品牌橙进度条（防旧链回归）
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

    # G8 字幕对账（R7 新架构：单次烧录，ASS 卡数 == JSON 卡数，无跨段重复计数）
    n_cards = len(load_subs())
    n_ass_v = open(f"{BUILD}/subs_v.ass", encoding="utf-8").read().count("Dialogue:")
    n_ass_h = open(f"{BUILD}/subs_h.ass", encoding="utf-8").read().count("Dialogue:")
    g8 = (n_ass_v == n_cards and n_ass_h == n_cards)
    report["gates"]["G8_字幕对账"] = "PASS" if g8 else \
        f"FAIL cards={n_cards} ass_v={n_ass_v} ass_h={n_ass_h}"
    print(f"  G8_字幕对账: {report['gates']['G8_字幕对账']} (json={n_cards}, 竖{n_ass_v}, 横{n_ass_h})")
    ok_all = ok_all and g8

    # G11 语义锚点（R4）：关键概念分句的 whisper 卡区间必须完整落在对应镜内
    #   注：句级 sents_real 里 S09+S10 台词同属一个长句，画面 mid-sentence 切换是正常
    #   剪辑（分句级换镜）；要拦的是 v4 那类"概念句落在错误场景"（如「沉没成本」
    #   说在盖章镜），所以锚点按 whisper 卡片级分句断言。
    sents = json.load(open(SENTS_REAL, encoding="utf-8"))
    wh_cards = json.load(open(SUBS_WHISPER, encoding="utf-8"))["cards"]
    shots, _ = load_shots()
    shot_by = {s["id"]: s for s in shots}
    ANCHORS = [  # (镜, 分句特征子串) —— 关键概念与画面的从属关系
        ("S08", "沉淀在最初起步的平台上"),
        ("S08", "变成沉没成本"),
        ("S09", "同质化严重"),
        ("S10", "价格战"),
        ("S10", "很难一眼算清"),
    ]

    # 预建全文字符流 → 卡片映射（key 定位到覆盖它的最小卡片区间）
    _stream = "".join(c["text"] for c in wh_cards)
    _bounds = [0]
    for c in wh_cards:
        _bounds.append(_bounds[-1] + len(c["text"]))

    def card_span(key):
        """key 在全文的位置 → 覆盖它的最小卡片区间 [start, end]（whisper 锚点）。"""
        p = _stream.find(key)
        assert p >= 0, f"分句特征「{key}」不在卡片文本流中"
        q = p + len(key) - 1
        import bisect as _bi
        i = _bi.bisect_right(_bounds, p) - 1      # 首覆盖卡
        j = _bi.bisect_right(_bounds, q) - 1      # 末覆盖卡
        return wh_cards[i]["start"], wh_cards[j]["end"]

    g11_detail, g11_ok = [], True
    for sid, key in ANCHORS:
        span = card_span(key)
        assert span, f"G11: 分句特征「{key}」在卡片流中未找到"
        s = shot_by[sid]
        inside = span[0] >= s["start"] - 0.01 and span[1] <= s["end"] + 0.01
        g11_detail.append(f"{sid}「{key}」卡区间 {span[0]:.2f}~{span[1]:.2f} ⊆ 镜 {s['start']:.2f}~{s['end']:.2f} {'✓' if inside else '✗'}")
        g11_ok = g11_ok and inside
    # 边界跨骑审计（信息级）：单卡严格跨过边界（start<t 且 end>t）才告警；贴齐边界（end==t）不算
    for b_t, pair in ((87.80, "S08→S09"), (93.66, "S09→S10")):
        ride = [c for c in wh_cards if c["start"] < b_t - 0.01 and c["end"] > b_t + 0.01]
        tagx = "✓ 无跨骑" if not ride else "ℹ 跨骑卡:" + str([r["text"][:10] for r in ride])
        g11_detail.append(f"边界 {pair}@{b_t} {tagx}")
    report["gates"]["G11_语义锚点"] = "PASS" if g11_ok else "FAIL"
    report["G11_detail"] = g11_detail
    for d in g11_detail:
        print(f"  G11: {d}")
    ok_all = ok_all and g11_ok

    # G12 字幕显示质量（R5/R6）：无短卡 / 同句同档 / 单行宽度适配
    def _vlen(t):
        return sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in t)
    cards = load_subs()
    punct = "，。：；！？、…—,.:;!?~“”\"'（）()《》<>【】"
    short = [c["text"] for c in cards if len(re.sub(f"[{re.escape(punct)}]", "", c["text"])) <= 2]
    jump = sum(1 for x, y in zip(cards, cards[1:])
               if x.get("sent") == y.get("sent") and x.get("tier") != y.get("tier"))
    widths = {  # 每档单行容量（可用宽 720 / 字号）
        ("v", 0): 720 / VERT_SIZES[0], ("v", 1): 720 / VERT_SIZES[1], ("v", 2): 720 / VERT_SIZES[2],
        ("h", 0): 920 / HORZ_SIZES[0], ("h", 1): 920 / HORZ_SIZES[1], ("h", 2): 920 / HORZ_SIZES[2],
    }
    over_v = [c["text"] for c in cards if _vlen(c["text"]) > widths[("v", c.get("tier", 0))]]
    over_h = [c["text"] for c in cards if _vlen(c["text"]) > widths[("h", c.get("tier", 0))]]
    g12 = (not short) and jump == 0 and not over_v and not over_h
    report["gates"]["G12_字幕质量"] = ("PASS" if g12 else
                                     f"FAIL short={short[:3]} jump={jump} over_v={over_v[:2]} over_h={over_h[:2]}")
    print(f"  G12_字幕质量: {report['gates']['G12_字幕质量']}")
    ok_all = ok_all and g12

    # G13 端到端像素锚点（R4 验收点）：成片指定时刻的语义画面必须在场
    #   推箱子沉没成本大字：canvas 87.0s（=69.79+17.2，章已落下）→ 成片 87.0/1.1=79.09s
    #   盖章场景同质化章：canvas 92.0s（=87.80+4.2，章已落下）→ 成片 92.0/1.1=83.64s
    g13_detail, g13_ok = [], True
    vfinal = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v8-竖屏.mp4"
    for tag_name, t_final, lo, hi in (("S08沉没成本大字", 79.09, 3000, 60000),
                                      ("S09同质化盖章", 83.64, 3000, 60000)):
        f = grab_frame(vfinal, t_final, 1080, 1920)
        band = f[CROP_Y:CROP_Y + 810, :, :].astype(int)
        red = int(((np.abs(band - np.array([229, 91, 70])).sum(axis=2)) < 120).sum())
        ok = lo < red < hi
        g13_detail.append(f"{tag_name} @{t_final}s 红像素={red} {'✓' if ok else '✗'}")
        g13_ok = g13_ok and ok
    report["gates"]["G13_像素锚点"] = "PASS" if g13_ok else "FAIL"
    report["G13_detail"] = g13_detail
    for d in g13_detail:
        print(f"  G13: {d}")
    ok_all = ok_all and g13_ok

    # G14 水印等比（R8）：wm_v8 内容宽高比必须与原版水印一致（±2%）
    from PIL import Image as _PILImage

    def _wm_aspect(p):
        a = np.array(_PILImage.open(p).convert("RGBA"))
        ys, xs = np.where(a[:, :, 3] > 5)
        if not len(ys):
            return None
        return (xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1)

    a_src, a_v8 = _wm_aspect(WM_SRC), _wm_aspect(WM)
    g14_ok = a_v8 is not None and a_src is not None and abs(a_v8 - a_src) / a_src < 0.02
    report["gates"]["G14_水印等比"] = ("PASS" if g14_ok else
                                   f"FAIL src={a_src:.4f} v8={a_v8:.4f}")
    print(f"  G14_水印等比: {report['gates']['G14_水印等比']} (原版 {a_src:.4f} → v8 {a_v8:.4f})")
    ok_all = ok_all and g14_ok

    # G9 素材几何（fit 模式窗口矩形 == 期望；cover 模式舞台带充满）
    shots, _ = load_shots()
    g9_detail = []
    g9_ok = True
    for sid, entry in BG_V8.items():
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
    json.dump(report, open(f"{OUT}/qc_report_v8.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("BUILD_SUCCESS" if ok_all else "BUILD_FAILED")
    gen_srt(f"{OUT}/AI视频画布横评-第一篇-价格篇-字幕v8.srt")
    print("[qc] 字幕v8.srt 已生成（whisper 权威源 ÷1.1）")
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
        step, lambda: sys.exit(f"用法: {sys.argv[0]} setup|bg|seq|enc|cat|final|final_h|audio|mux|mux_h|speed|speed_h|subs|subs_h|qc [only]"))()
