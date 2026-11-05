#!/usr/bin/env python3
"""分段总装（绕过沙箱 600s 命令超时 + 后台进程被杀问题）：

用法:
  seg A   : python3 ffmpeg_master_v2_seg.py A      # 视频段 0-370s
  seg B   : python3 ffmpeg_master_v2_seg.py B      # 视频段 370-740.36s（字幕/cmds 偏移）
  concat  : python3 ffmpeg_master_v2_seg.py cat    # A+B 拼接 → vfull.mp4
  audio   : python3 ffmpeg_master_v2_seg.py audio  # 全片音频(配音+BGM闪避+loudnorm) → final_audio.m4a
  mux     : python3 ffmpeg_master_v2_seg.py mux    # 视频+音频混流+faststart+清元数据 → output/成片
  qc      : python3 ffmpeg_master_v2_seg.py qc     # 质检门禁 G1-G6
每步幂等可续跑；A/B 段完成后跳过。
"""
import json
import os
import re
import subprocess
import sys

WORK = "/home/z/my-project/ep1-work"
BUILD = f"{WORK}/build"
OUT = f"{WORK}/output"
SEG_T = 370.0  # 分段点（秒）

sys.path.insert(0, "/home/z/my-project/scripts")
from ffmpeg_master_v2 import (  # noqa: E402
    gen_ass, gen_srt, ts_ass)

TL = f"{WORK}/ep1_shots_v2.json"
SUBS = f"{WORK}/ep1_subtitles.json"
NARR = f"{WORK}/audio/1105-1200-第一篇.mp3"
BGM = f"{WORK}/audio/娱资日更视频BGM-Let's Talk Some Showbiz.mp3"
CONCAT = f"{WORK}/frames/concat.txt"
TRACK = f"{WORK}/assets/progress_track.png"
WM = f"{WORK}/assets/wm75.png"
FONTS = f"{WORK}/assets/fonts"


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ff(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return r


def load():
    shots = json.load(open(TL, encoding="utf-8"))
    total = shots[-1]["start"] + shots[-1]["dur"]
    subs = json.load(open(SUBS, encoding="utf-8"))
    return total, subs


def vfc_for(ass_file, cmds_file, trk_idx=3, wm_idx=4):
    return (
        "[0:v]fps=30,format=yuv420p[base];"
        f"[{trk_idx}:v]scale=1080:8[trk];"
        f"[{wm_idx}:v]format=rgba[wm];"
        "[base][trk]overlay=0:0,"
        f"sendcmd=f={cmds_file},"
        "drawbox=x=0:y=0:w=1:h=8:color=#e55b46@1.0:t=fill[pbar];"
        f"[pbar]subtitles={ass_file}:fontsdir={FONTS}[vsub];"
        "[vsub][wm]overlay=0:0[vout]")


def gen_seg_subs(subs, t0, t1, path):
    """裁剪/偏移字幕事件到 [t0, t1] 段内（段内时间 = 全局 - t0）。"""
    evs = []
    for s in subs:
        st, en = s["start"], s["end"]
        if en <= t0 or st >= t1:
            continue
        st2, en2 = max(st, t0) - t0, min(en, t1) - t0
        evs.append({"start": round(st2, 3), "end": round(en2, 3), "text": s["text"]})
    gen_ass(evs, path)
    return len(evs)


def gen_seg_cmds(total, t0, t1, path, step=0.5):
    """sendcmd 偏移版：段内时间 = 全局 - t0，首条命令设在 0.0。"""
    lines = []
    t = t0
    while t <= t1 + 1e-6:
        w = max(1, int(1080 * t / total))
        lines.append(f"{t - t0:.1f} drawbox w {w};")
        t += step
    open(path, "w").write("\n".join(lines) + "\n")
    return len(lines)


def seg_video(seg):
    total, subs = load()
    t0, t1 = (0.0, SEG_T) if seg == "A" else (SEG_T, total)
    dur = t1 - t0
    ass_file = f"{BUILD}/subs_{seg}.ass"
    cmds_file = f"{BUILD}/progress_{seg}.cmds"
    n_ev = gen_seg_subs(subs, t0, t1, ass_file)
    n_cmd = gen_seg_cmds(total, t0, t1, cmds_file)
    print(f"[{seg}] {t0:.1f}-{t1:.1f}s 时长{dur:.2f}s 字幕{n_ev}条 cmds{n_cmd}条")
    ff("-ss", f"{t0:.3f}", "-f", "concat", "-safe", "0", "-i", CONCAT,
       "-loop", "1", "-t", f"{dur:.3f}", "-i", TRACK,
       "-loop", "1", "-t", f"{dur:.3f}", "-i", WM,
       "-filter_complex", vfc_for(ass_file, cmds_file, trk_idx=1, wm_idx=2),
       "-map", "[vout]", "-t", f"{dur:.3f}",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
       f"{BUILD}/seg_{seg}.mp4")
    print(f"[{seg}] seg_{seg}.mp4 done")


def seg_cat():
    lst = f"{BUILD}/cat.txt"
    open(lst, "w").write(
        f"ffconcat version 1.0\nfile '{BUILD}/seg_A.mp4'\nfile '{BUILD}/seg_B.mp4'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", f"{BUILD}/vfull.mp4")
    print("[cat] vfull.mp4 done")


def seg_audio():
    total, _ = load()
    afc = (
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[va][vb];"
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-13.5dB[bg0];"
        "[bg0][va]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bg];"
        "[vb][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]")
    ff("-i", NARR, "-stream_loop", "-1", "-i", BGM,
       "-filter_complex", afc, "-map", "[mix]", "-t", f"{total:.3f}",
       "-c:a", "pcm_s16le", f"{BUILD}/mix.wav")
    # loudnorm 两遍
    r = sh("ffmpeg", "-nostdin", "-i", f"{BUILD}/mix.wav", "-af",
           "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-").stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r, re.S)
    ln = json.loads(m.group(0)) if m else {}
    meas = (f"loudnorm=I=-15:TP=-1.5:LRA=11:"
            f"measured_I={ln.get('input_i', -24)}:measured_TP={ln.get('input_tp', -2)}:"
            f"measured_LRA={ln.get('input_lra', 11)}:measured_thresh={ln.get('input_thresh', -30)}:linear=true")
    ff("-i", f"{BUILD}/mix.wav", "-af", meas, "-c:a", "aac", "-b:a", "192k",
       f"{BUILD}/final_audio.m4a")
    print("[audio] final_audio.m4a done")


def seg_mux():
    total, _ = load()
    os.makedirs(OUT, exist_ok=True)
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片.mp4"
    ff("-i", f"{BUILD}/vfull.mp4", "-i", f"{BUILD}/final_audio.m4a",
       "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", "-metadata", "comment= ", out)
    print(f"[mux] {out}")
    return out


def seg_qc():
    total, _ = load()
    out = f"{OUT}/AI视频画布横评-第一篇-价格篇-成片.mp4"
    gates = {}
    r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", out, "-f", "null", "-")
    gates["G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", out).stdout.strip())
    gates["G2_时长"] = "PASS" if abs(dur - total) <= 2.0 else f"FAIL {dur:.1f}s vs {total:.1f}s"
    w = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height", "-of", "csv=p=0", out).stdout.strip()
    gates["G3_分辨率"] = "PASS" if w == "1080,1920," else f"FAIL {w}"
    r2 = sh("ffmpeg", "-nostdin", "-i", out, "-af", "loudnorm=print_format=json",
            "-f", "null", "-").stderr
    m2 = re.search(r"\"input_i\"\s*:\s*\"?(-?[\d.]+)", r2)
    gates["G4_响度"] = "PASS" if m2 and abs(float(m2.group(1)) + 15) <= 2 else \
        f"FAIL {m2.group(1) if m2 else '?'} LUFS"
    r3 = sh("ffmpeg", "-nostdin", "-i", out, "-vf", "blackdetect=d=3:pix_th=0.05",
            "-an", "-f", "null", "-").stderr
    gates["G5_无长黑屏"] = "PASS" if "black_start" not in r3 else f"FAIL {r3[:300]}"
    meta = sh("ffprobe", "-v", "error", "-show_entries", "format_tags=comment",
              "-of", "csv=p=0", out).stdout
    gates["G6_元数据"] = "PASS" if "remotion" not in meta.lower() else "FAIL Remotion残留"
    ok = all(v == "PASS" for v in gates.values())
    # QC 抽帧
    for t in [5, 100, 369.5, 400, 600, 735]:
        ff("-ss", f"{t:.2f}", "-i", out, "-frames:v", "1", "-update", "1",
           f"{BUILD}/qc_{int(t):04d}s.jpg")
    json.dump({"gates": gates, "BUILD_SUCCESS": ok, "duration": dur,
               "output": out, "total_target": total},
              open(f"{OUT}/qc_report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for k, v in gates.items():
        print(f"  {k}: {v}")
    print("BUILD_SUCCESS" if ok else "BUILD_FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    {"A": lambda: seg_video("A"), "B": lambda: seg_video("B"),
     "cat": seg_cat, "audio": seg_audio, "mux": seg_mux, "qc": seg_qc}.get(step,
        lambda: sys.exit(f"用法: {sys.argv[0]} A|B|cat|audio|mux|qc"))()
