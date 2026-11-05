#!/usr/bin/env python3
"""总装与质检（Step 7-8）：视频帧轨 + 人声 + BGM(闪避) + 音效 → 成片 → 机器质检 → BUILD_SUCCESS。
用法:
  python3 ffmpeg_master.py <aligned-timeline.json> <frames_dir> <out.mp4>
      [--narration 整条配音.mp3 | auto(用 audio/S##.mp3 拼)]
      [--bgm bgm.mp3 --bgm-gain -13.5dB] [--sfx-dir sfx/] [--loop-bgm]

质检门禁（全过才输出 BUILD_SUCCESS）:
  G1 ffmpeg -v error -f null 零坏帧   G2 时长误差 ≤2s   G3 分辨率=1080x1920
  G4 响度 -14±2 LUFS（loudnorm 两遍） G5 无 >3s 纯黑段   G6 无 Remotion 元数据残留
ffmpeg 全程 -nostdin -y（铁律③）。"""
import argparse
import json
import os
import re
import subprocess
import sys


def sh(*cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r


def ff(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("frames_dir")
    ap.add_argument("out")
    ap.add_argument("--narration", default="auto")
    ap.add_argument("--bgm", default=None)
    ap.add_argument("--bgm-gain", default="-13.5dB")
    ap.add_argument("--sfx-dir", default=None)
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    tl = json.load(open(args.timeline, encoding="utf-8"))
    shots = tl["shots"]
    total = shots[-1]["start"] + shots[-1]["dur"]
    tmp = args.out + ".tmp.mp4"

    # ---- 视频轨 ----
    concat = os.path.join(args.frames_dir, "concat.txt")
    ff("-f", "concat", "-safe", "0", "-i", concat,
       "-vf", f"fps={args.fps},format=yuv420p", "-r", str(args.fps),
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", tmp)

    # ---- 人声轨 ----
    voice = args.out + ".voice.m4a"
    if args.narration != "auto" and os.path.exists(args.narration):
        ff("-i", args.narration, "-c:a", "aac", "-b:a", "192k", voice)
    else:
        parts = []
        for s in shots:
            f = os.path.join(os.path.dirname(args.timeline), "audio", f"{s['id']}.mp3")
            if not os.path.exists(f):
                sys.exit(f"G0 FAIL: 缺 {f}")
            seg = f + ".seg.m4a"
            ff("-i", f, "-t", f"{s['dur']:.3f}", "-c:a", "aac", "-b:a", "192k", seg)
            parts.append((s["start"], seg))
        # adelay 逐段叠加
        inputs, filters = [], []
        for i, (st, seg) in enumerate(parts):
            inputs += ["-i", seg]
            filters.append(f"[{i}:a]adelay={int(st*1000)}|{int(st*1000)}[d{i}]")
        n = len(parts)
        filters.append("".join(f"[d{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,volume=1.0[aout]")
        ff(*inputs, "-filter_complex", ";".join(filters), "-map", "[aout]", "-t", f"{total:.3f}", "-c:a", "aac", "-b:a", "192k", voice)

    # ---- 混音（人声 + BGM 闪避） ----
    mix_inputs = ["-i", tmp, "-i", voice]
    fc = "[1:a]volume=1.0[v]"
    if args.bgm:
        mix_inputs += ["-stream_loop", "-1", "-i", args.bgm]
        fc += f";[2:a]volume={args.bgm_gain},sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bg];" \
              f"[v][bg]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm[fv]"
        fc = fc.replace("[v][bg]", "[va][bg]").replace("[1:a]volume=1.0", "[1:a]volume=1.0[va]")
        fc = fc.replace("[v][bg]", "[va][bg]")
        amap = "[fv]"
    else:
        amap = "[v]"
    pre = args.out + ".pre.mp4"
    ff(*mix_inputs, "-filter_complex", fc, "-map", "0:v", "-map", amap,
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total + 0.5:.3f}", pre)

    # ---- 响度两遍 + 收尾 ----
    r = sh("ffmpeg", "-nostdin", "-i", pre, "-af", "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json",
           "-f", "null", "-").stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r, re.S)
    ln = json.loads(m.group(0)) if m else {}
    meas = (f"loudnorm=I=-15:TP=-1.5:LRA=11:"
            f"measured_I={ln.get('input_i', -24)}:measured_TP={ln.get('input_tp', -2)}:"
            f"measured_LRA={ln.get('input_lra', 11)}:measured_thresh={ln.get('input_thresh', -30)}:linear=true")
    ff("-i", pre, "-af", meas, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", args.out)  # comment 置空=清 Remotion 残留(G6)

    # ---- 质检门禁 ----
    gates = {}
    r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", args.out, "-f", "null", "-")
    gates["G1_零坏帧"] = "PASS" if r.returncode == 0 and not r.stderr.strip() else f"FAIL {r.stderr[:200]}"
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", args.out).stdout.strip())
    gates["G2_时长"] = "PASS" if abs(dur - total) <= 2.0 else f"FAIL {dur:.1f}s vs {total:.1f}s"
    w = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height", "-of", "csv=p=0", args.out).stdout.strip()
    gates["G3_分辨率"] = "PASS" if w == "1080,1920" else f"FAIL {w}"
    r2 = sh("ffmpeg", "-nostdin", "-i", args.out, "-af", "loudnorm=print_format=json", "-f", "null", "-").stderr
    m2 = re.search(r"\"input_i\"\s*:\s*\"?(-?[\d.]+)", r2)
    gates["G4_响度"] = "PASS" if m2 and abs(float(m2.group(1)) + 15) <= 2 else f"FAIL {m2.group(1) if m2 else '?'} LUFS"
    r3 = sh("ffmpeg", "-nostdin", "-i", args.out, "-vf", "blackdetect=d=3:pix_th=0.05", "-an", "-f", "null", "-").stderr
    gates["G5_无长黑屏"] = "PASS" if "black_start" not in r3 else f"FAIL {r3[:200]}"
    meta = sh("ffprobe", "-v", "error", "-show_entries", "format_tags=comment", "-of", "csv=p=0", args.out).stdout
    gates["G6_元数据"] = "PASS" if "remotion" not in meta.lower() else "FAIL Remotion水印残留"

    ok = all(v == "PASS" for v in gates.values())
    report = {"gates": gates, "BUILD_SUCCESS": ok, "duration": dur,
              "output": os.path.abspath(args.out)}
    json.dump(report, open(args.out + ".qc.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in gates.items():
        print(f"  {k}: {v}")
    print("BUILD_SUCCESS" if ok else "BUILD_FAILED")
    for f in (tmp, voice, pre):
        if os.path.exists(f):
            os.remove(f)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
