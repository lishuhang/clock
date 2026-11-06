#!/usr/bin/env python3
"""总装 v4（帧数精确 + 分镜分拆 + 视频背景扩容 + 字幕位1740 + 1.1x提速）：
# 通用用法: 按段执行 bg|seq|enc|cat|final|audio|mux|speed|qc；路径常量按项目改写
# 依赖 ffmpeg_master_v2.py 的 gen_ass/gen_srt/ts_ass（字幕 MarginV=180 版）


  bg    : 视频背景段（6镜：S02a/S02b/S03a/S03b/S04/S24b，各自源文件+偏移）
  seq    : 46镜 30fps 精确帧序列物化（符号链接）
  enc    : 逐镜编码（普通=帧序列直编；视频背景镜=双层合成）
  cat    : 46镜 concat → vtrack.mp4（帧数=Σn=22211 精确）
  final  : A/B 段终渲（轨道+进度条+字幕MarginV=180+水印）
  audio  : 配音+BGM闪避+loudnorm
  mux    : 混流 → v4_1x.mp4
  speed  : 1.1x 提速（setpts+atempo 不变调）→ 成片v4 + srt重定时
  qc     : 门禁（新时长 673.05s / 帧数 ~20192）
"""
import json
import os
import re
import subprocess
import sys

WORK = "/home/z/my-project/ep1-work"
REPO = "/home/z/my-project/clock-repo/1105-canvas-test-videos"
SHOTS = f"{WORK}/ep1_shots_v4.json"
CANVAS_DIR = f"{REPO}/04-ep1-production/canvas"
FRAMES = f"{WORK}/frames_v4"
BILI = f"{REPO}/04-ep1-production/materials/bili"
NEW = f"{WORK}/materials/new"
BUILD = f"{WORK}/build_v4"
OUT = f"{WORK}/output"
NARR = f"{WORK}/audio/1105-1200-第一篇.mp3"
BGM = f"{WORK}/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
CANVAS_ASSETS = f"{REPO}/04-ep1-production/assets"
WM = f"{CANVAS_ASSETS}/wm75.png"
TRACK = f"{CANVAS_ASSETS}/progress_track.png"
FONTS = f"{CANVAS_ASSETS}/fonts"
SUBS = f"{WORK}/ep1_subtitles_v4.json"
TOTAL = 740.36
FPS = 30
SPEED = 1.1
SPEED_TOTAL = TOTAL / SPEED  # 673.05

BG_V4 = {
    "S02a": (f"{BILI}/paizi_bg.mp4", 36.0),
    "S02b": (f"{BILI}/paizi_bg.mp4", 38.8),
    "S03a": (f"{BILI}/sss_bg.mp4", 100.0),
    "S03b": (f"{BILI}/sss_bg.mp4", 102.8),
    "S04": (f"{NEW}/t2第一抽.mp4", 3.2),
    "S24b": (f"{NEW}/抽卡过程延时.mp4", 85.0),
}
SEG_SPLIT = 372.0  # A/B 段切点（秒，镜头边界）

sys.path.insert(0, f"{REPO}/scripts")
from ffmpeg_master_v2 import gen_ass, gen_srt, ts_ass  # noqa: E402


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ff(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])
    return r


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


# ---------- bg ----------
def cmd_bg():
    shots, _ = load_shots()
    for sid, (src, offset) in BG_V4.items():
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
        if sid in BG_V4:
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


# ---------- final ----------
def gen_progress_cmds(total, path, step=0.5):
    lines = []
    t = 0.0
    while t <= total + 1e-6:
        w = max(1, int(1080 * t / total))
        lines.append(f"{t:.1f} drawbox w {w};")
        t += step
    open(path, "w").write("\n".join(lines) + "\n")


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
    gen_ass(evs, ass_file)
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
    n = probe_frames(f"{BUILD}/vfinal.mp4")
    print(f"[final] vfinal {n}帧")


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


# ---------- mux（1x 母版） ----------
def cmd_mux():
    os.makedirs(OUT, exist_ok=True)
    out = f"{BUILD}/v4_1x.mp4"
    ff("-i", f"{BUILD}/vfinal.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux] {out}")


# ---------- speed（1.1x 提速，不变调） ----------
def cmd_speed():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v4.mp4"
    ff("-i", f"{BUILD}/v4_1x.mp4",
       "-filter_complex",
       f"[0:v]setpts=PTS/{SPEED},fps={FPS},format=yuv420p[v];[0:a]atempo={SPEED}[a]",
       "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-crf", "17", "-preset", "slow",
       "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    n = probe_frames(out)
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", out).stdout.strip())
    print(f"[speed] 成片 {n}帧 {dur:.2f}s (目标≈{SPEED_TOTAL:.2f}s)")
    # srt 重定时
    src_srt = f"{REPO}/04-ep1-production/output/字幕v3.srt"
    dst_srt = f"{OUT}/AI视频画布横评-第一篇-价格篇-字幕v4.srt"
    retime_srt(src_srt, dst_srt)
    print(f"[speed] 字幕重定时 → {dst_srt}")


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


# ---------- qc ----------
def cmd_qc():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v4.mp4"
    gates = {}
    r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", out, "-f", "null", "-")
    gates["G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
    n = probe_frames(out)
    expect = round(SPEED_TOTAL * FPS)
    gates["G2_帧数"] = "PASS" if abs(n - expect) <= 2 else f"FAIL {n}≠{expect}±2"
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", out).stdout.strip())
    gates["G3_时长"] = "PASS" if abs(dur - SPEED_TOTAL) <= 0.5 else f"FAIL {dur:.2f}"
    w = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height", "-of", "csv=p=0", out).stdout.strip()
    gates["G4_分辨率"] = "PASS" if w.strip().rstrip(",") == "1080,1920" else f"FAIL {w}"
    r2 = sh("ffmpeg", "-nostdin", "-i", out, "-af", "loudnorm=print_format=json",
            "-f", "null", "-").stderr
    m2 = re.search(r"\"input_i\"\s*:\s*\"?(-?[\d.]+)", r2)
    gates["G5_响度"] = "PASS" if m2 and abs(float(m2.group(1)) + 15) <= 2 else f"FAIL {m2.group(1) if m2 else '?'}"
    r3 = sh("ffmpeg", "-nostdin", "-i", out, "-vf", "blackdetect=d=3:pix_th=0.05",
            "-an", "-f", "null", "-").stderr
    gates["G6_无长黑屏"] = "PASS" if "black_start" not in r3 else f"FAIL {r3[:200]}"
    meta = sh("ffprobe", "-v", "error", "-show_entries", "format_tags=comment",
              "-of", "csv=p=0", out).stdout
    gates["G7_元数据"] = "PASS" if "remotion" not in meta.lower() else "FAIL"
    ok = all(v == "PASS" for v in gates.values())
    json.dump({"gates": gates, "BUILD_SUCCESS": ok, "frames": n, "duration": dur,
               "speed": SPEED, "pre_speed_total": TOTAL},
              open(f"{OUT}/qc_report_v4.json", "w"), ensure_ascii=False, indent=1)
    for k, v in gates.items():
        print(f"  {k}: {v}")
    print("BUILD_SUCCESS" if ok else "BUILD_FAILED")
    for t in [6.0, 8.0, 12.0, 20.0, 25.0, 33.0, 60.0, 68.0, 120.0, 310.0, 330.0, 345.0, 660.0]:
        tt = round(t / SPEED, 2)  # 抽帧时刻取提速后时间轴
        ff("-ss", f"{tt}", "-i", out, "-frames:v", "1", "-update", "1", "-q:v", "3",
           f"{BUILD}/qc_{t:.0f}s.jpg")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    os.makedirs(BUILD, exist_ok=True)
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[1] == "enc" else None
    {"bg": cmd_bg, "seq": cmd_seq,
     "enc": lambda: cmd_enc(only), "cat": cmd_cat, "final": cmd_final,
     "audio": cmd_audio, "mux": cmd_mux, "speed": cmd_speed, "qc": cmd_qc}.get(
        step, lambda: sys.exit(f"用法: {sys.argv[0]} bg|seq|enc|cat|final|audio|mux|speed|qc [only]"))()
