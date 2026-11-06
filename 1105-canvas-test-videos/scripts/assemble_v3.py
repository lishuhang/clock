#!/usr/bin/env python3
"""总装 v3（帧数精确架构，修复 concat 图像时长量化漂移）：

  bg    : S02/S03 视频背景段（1080x1920@30fps 精确帧数）
  seq    : 全部镜头 30fps 精确帧序列物化（符号链接）
  enc    : 逐镜编码（普通=帧序列直编；S02/S03=背景+透明叠层双层合成）
  cat    : 全部镜头段 concat → vtrack.mp4（帧数=Σn 必须精确）
  final  : A/B 段终渲（轨道+进度条+字幕+水印）→ 拼接 → vfinal.mp4
  audio  : 配音+BGM闪避+loudnorm → final_audio.m4a
  mux    : 混流+faststart+清元数据 → output/成片
  qc     : G1-G6 + 帧数/时长精确校验

关键不变量：n_i = round(dur_i×30)，Σn_i = round(总长×30) = 22211；
vtrack 帧数精确 → 画面切换与音频句子边界对齐（句首误差≤0.3s 实测对齐）。
"""
import json
import os
import re
import subprocess
import sys

WORK = "/home/z/my-project/ep1-work"
SHOTS = f"{WORK}/ep1_shots_v3.json"
FRAMES = f"{WORK}/frames_v3"
CANVAS_ASSETS = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/assets"
BILI = f"{WORK}/materials/bili"
BUILD = f"{WORK}/build_v3"
OUT = f"{WORK}/output"
NARR = f"{WORK}/audio/1105-1200-第一篇.mp3"
BGM = f"{WORK}/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
WM = f"{CANVAS_ASSETS}/wm75.png"
TRACK = f"{CANVAS_ASSETS}/progress_track.png"
FONTS = f"{CANVAS_ASSETS}/fonts"
SUBS = f"{WORK}/ep1_subtitles_real.json"
TOTAL = 740.36
FPS = 30
BG_SHOTS = {"S02": f"{BILI}/paizi_bg.mp4", "S03": f"{BILI}/sss_bg.mp4"}
SEG_SPLIT = 370.0  # A/B 段切点（秒）

sys.path.insert(0, "/home/z/my-project/github-work/1105-canvas-test-videos/scripts")
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
    # n_i 与总量校准（尾镜吸收误差）
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
    for sid, src in BG_SHOTS.items():
        s = next(x for x in shots if x["id"] == sid)
        out = f"{BUILD}/bg_{sid}.mp4"
        if os.path.exists(out) and probe_frames(out) == s["n"]:
            print(f"[skip] bg_{sid}")
            continue
        ff("-i", src,
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
        # 已物化则跳过
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
        if sid in BG_SHOTS:
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
    """A/B 段终渲（帧数精确：A 用 -frames:v，B 用 -ss n_A/30 + -frames:v）。"""
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
    # A/B 切点取镜头边界（近似370s）
    shots, _ = load_shots()
    split = None
    for s in shots:
        if s["start"] >= SEG_SPLIT:
            split = s["start"]
            break
    split = split or SEG_SPLIT
    split = round(round(split * FPS) / FPS, 6)  # 帧边界对齐
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


# ---------- mux ----------
def cmd_mux():
    os.makedirs(OUT, exist_ok=True)
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v3.mp4"
    ff("-i", f"{BUILD}/vfinal.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux] {out}")


# ---------- qc ----------
def cmd_qc():
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片v3.mp4"
    gates = {}
    r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", out, "-f", "null", "-")
    gates["G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
    n = probe_frames(out)
    gates["G2_帧数精确"] = "PASS" if n == round(TOTAL * FPS) else f"FAIL {n}"
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", out).stdout.strip())
    gates["G3_时长"] = "PASS" if abs(dur - TOTAL) <= 0.5 else f"FAIL {dur:.2f}"
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
    json.dump({"gates": gates, "BUILD_SUCCESS": ok, "frames": n, "duration": dur},
              open(f"{OUT}/qc_report_v3.json", "w"), ensure_ascii=False, indent=1)
    for k, v in gates.items():
        print(f"  {k}: {v}")
    print("BUILD_SUCCESS" if ok else "BUILD_FAILED")
    # 同步点抽帧
    for t in [29.4, 36.0, 100.0, 369.5, 370.5, 600.0, 739.0]:
        ff("-ss", f"{t}", "-i", out, "-frames:v", "1", "-update", "1", "-q:v", "3",
           f"{BUILD}/qc_{t:.0f}s.jpg")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    os.makedirs(BUILD, exist_ok=True)
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[1] == "enc" else None
    {"bg": cmd_bg, "seq": cmd_seq,
     "enc": lambda: cmd_enc(only), "cat": cmd_cat, "final": cmd_final,
     "audio": cmd_audio, "mux": cmd_mux, "qc": cmd_qc}.get(
        step, lambda: sys.exit(f"用法: {sys.argv[0]} bg|seq|enc|cat|final|audio|mux|qc [only]"))()
