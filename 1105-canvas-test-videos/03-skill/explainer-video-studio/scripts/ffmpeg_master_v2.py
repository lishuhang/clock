#!/usr/bin/env python3
"""总装与质检 v2（1105 价格篇投产版）：

管线：concat帧轨 → PNG轨道 + sendcmd/drawbox动画进度条 → ASS字幕(白字黑边普惠体)
      → 全屏wm75水印 → 人声+BGM闪避混音 → loudnorm两遍 → 质检门禁 → BUILD_SUCCESS。

v2 与 skill 版 v1 的差异（2026-11-05 用户修订规格）：
  1. 字幕烧录：剪映风白字黑边、透明底、单行不折行（ASS WrapStyle=2 + Outline=7）
  2. 顶部全宽细进度条：静态轨道PNG + drawbox 填充（sendcmd 每 0.5s 推进）
  3. 全屏浮水印 wm75.png 叠最顶层（防盗，alpha 已在 PNG 内置 75%）
  4. BGM 闪避修正：sidechaincompress 正确双输入接法（v1 单输入链写法不可用）
铁律：ffmpeg 全程 -nostdin -y；drawtext 禁用（字幕走 libass/ASS）。
"""
import argparse
import json
import os
import re
import subprocess
import sys

DUR = None  # 由 timeline 填充


def sh(*cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ff(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])
    return r


def ts_ass(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ts_srt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def gen_ass(subs, path):
    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Sub,Alibaba PuHuiTi 3.0,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
        "1,0,0,0,100,100,0,0,1,7,0,2,60,60,180,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [head]
    for s in subs:
        text = s["text"].replace("{", "｛").replace("}", "｝").replace("\\", "＼")
        lines.append(f"Dialogue: 0,{ts_ass(s['start'])},{ts_ass(s['end'])},Sub,,0,0,0,,{text}\n")
    open(path, "w", encoding="utf-8").write("".join(lines))


def gen_srt(subs, path):
    out = []
    for i, s in enumerate(subs, 1):
        out.append(f"{i}\n{ts_srt(s['start'])} --> {ts_srt(s['end'])}\n{s['text']}\n\n")
    open(path, "w", encoding="utf-8").write("".join(out))


def gen_progress_cmds(total, path, step=0.5):
    """sendcmd 指令：每 step 秒把 drawbox 宽度推到 1080*t/total。"""
    lines = []
    t = 0.0
    while t <= total:
        w = max(1, int(1080 * t / total))
        lines.append(f"{t:.1f} drawbox w {w};")
        t += step
    open(path, "w").write("\n".join(lines) + "\n")
    return len(lines)


def video_filter_complex(ass_file, cmds_file, fonts_dir, trk_idx=1, wm_idx=2):
    # trk_idx/wm_idx：轨道PNG与水印PNG在输入列表中的序号（预览模式 1,2；全渲染 3,4）
    return (
        "[0:v]fps=30,format=yuv420p[base];"
        f"[{trk_idx}:v]scale=1080:8[trk];"
        f"[{wm_idx}:v]format=rgba[wm];"
        "[base][trk]overlay=0:0,"
        f"sendcmd=f={cmds_file},"
        "drawbox=x=0:y=0:w=1:h=8:color=#e55b46@1.0:t=fill[pbar];"
        f"[pbar]subtitles={ass_file}:fontsdir={fonts_dir}[vsub];"
        "[vsub][wm]overlay=0:0[vout]")


def audio_filter_complex():
    # 统一 48kHz 立体声（配音源为 44.1k 单声道，BGM 为 48k 立体声，sidechaincompress 要求一致）
    return (
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[va][vb];"
        "[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-13.5dB[bg0];"
        "[bg0][va]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bg];"
        "[vb][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("frames_dir")
    ap.add_argument("subs_json")
    ap.add_argument("narration")
    ap.add_argument("bgm")
    ap.add_argument("out")
    ap.add_argument("--wm", default=None, help="全屏水印PNG(默认 assets/wm75.png)")
    ap.add_argument("--track", default=None, help="进度条轨道PNG")
    ap.add_argument("--preview-ts", default="", help="只渲染预览帧: 逗号分隔秒数")
    args = ap.parse_args()

    shots = json.load(open(args.timeline, encoding="utf-8"))
    total = shots[-1]["start"] + shots[-1]["dur"]
    subs = json.load(open(args.subs_json, encoding="utf-8"))
    work = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(work, exist_ok=True)

    ass_file = os.path.join(work, "subs.ass")
    srt_file = os.path.join(work, "字幕.srt")
    cmds_file = os.path.join(work, "progress.cmds")
    gen_ass(subs, ass_file)
    gen_srt(subs, srt_file)
    n_cmds = gen_progress_cmds(total, cmds_file)
    print(f"[gen] ASS {len(subs)}条 / SRT / sendcmd {n_cmds}条 / 总时长 {total:.2f}s")

    base_dir = os.path.dirname(os.path.abspath(args.timeline))
    wm = args.wm or os.path.abspath(os.path.join(base_dir, "assets", "wm75.png"))
    track = args.track or os.path.abspath(os.path.join(base_dir, "assets", "progress_track.png"))
    fonts_dir = os.path.abspath(os.path.join(base_dir, "assets", "fonts"))
    concat = os.path.join(args.frames_dir, "concat.txt")

    vfc = video_filter_complex(os.path.abspath(ass_file), os.path.abspath(cmds_file), fonts_dir,
                               trk_idx=3, wm_idx=4)
    afc = audio_filter_complex()

    if args.preview_ts:
        # 预览模式：只出静帧检查字幕/进度条/水印
        for t in [float(x) for x in args.preview_ts.split(",")]:
            out_png = os.path.join(work, f"preview_{int(t):04d}s.jpg")
            ff("-ss", f"{t:.2f}", "-copyts", "-f", "concat", "-safe", "0", "-i", concat,
               "-loop", "1", "-t", "1", "-i", track,
               "-loop", "1", "-t", "1", "-i", wm,
               "-filter_complex", vfc, "-map", "[vout]",
               "-frames:v", "1", "-update", "1", out_png)
            print(f"[preview] {out_png}")
        return

    # ---- Pass 1: 视频全叠加 + 混音 ----
    pre = args.out + ".pre.mp4"
    ff("-f", "concat", "-safe", "0", "-i", concat,
       "-i", args.narration,
       "-stream_loop", "-1", "-i", args.bgm,
       "-loop", "1", "-t", f"{total:.3f}", "-i", track,
       "-loop", "1", "-t", f"{total:.3f}", "-i", wm,
       "-filter_complex", vfc + ";" + afc,
       "-map", "[vout]", "-map", "[mix]",
       "-c:v", "libx264", "-preset", "medium", "-crf", "18",
       "-c:a", "aac", "-b:a", "192k",
       "-t", f"{total:.3f}", pre)
    print("[pass1] pre.mp4 done")

    # ---- Pass 2: loudnorm 两遍 ----
    r = sh("ffmpeg", "-nostdin", "-i", pre, "-af",
           "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-").stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r, re.S)
    ln = json.loads(m.group(0)) if m else {}
    meas = (f"loudnorm=I=-15:TP=-1.5:LRA=11:"
            f"measured_I={ln.get('input_i', -24)}:measured_TP={ln.get('input_tp', -2)}:"
            f"measured_LRA={ln.get('input_lra', 11)}:measured_thresh={ln.get('input_thresh', -30)}:linear=true")
    ff("-i", pre, "-af", meas, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", "-metadata", "comment= ", args.out)
    print("[pass2] loudnorm done")

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
    r2 = sh("ffmpeg", "-nostdin", "-i", args.out, "-af", "loudnorm=print_format=json",
            "-f", "null", "-").stderr
    m2 = re.search(r"\"input_i\"\s*:\s*\"?(-?[\d.]+)", r2)
    gates["G4_响度"] = "PASS" if m2 and abs(float(m2.group(1)) + 15) <= 2 else \
        f"FAIL {m2.group(1) if m2 else '?'} LUFS"
    r3 = sh("ffmpeg", "-nostdin", "-i", args.out, "-vf", "blackdetect=d=3:pix_th=0.05",
            "-an", "-f", "null", "-").stderr
    gates["G5_无长黑屏"] = "PASS" if "black_start" not in r3 else f"FAIL {r3[:200]}"
    meta = sh("ffprobe", "-v", "error", "-show_entries", "format_tags=comment",
              "-of", "csv=p=0", args.out).stdout
    gates["G6_元数据"] = "PASS" if "remotion" not in meta.lower() else "FAIL Remotion残留"
    # G7: 字幕/进度条/水印目检帧
    probe_ts = [10, total / 2, total - 10]
    probe_pngs = []
    for t in probe_ts:
        p = os.path.join(work, f"qc_{int(t):04d}s.jpg")
        ff("-ss", f"{t:.2f}", "-i", args.out, "-frames:v", "1", "-update", "1", p)
        probe_pngs.append(p)
    gates["G7_抽帧"] = f"{' '.join(probe_pngs)} (待目检)"

    ok = all(v == "PASS" for k, v in gates.items() if k != "G7_抽帧")
    report = {"gates": gates, "BUILD_SUCCESS": ok, "duration": dur,
              "output": os.path.abspath(args.out), "total_target": total}
    json.dump(report, open(args.out + ".qc.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for k, v in gates.items():
        print(f"  {k}: {v}")
    print("BUILD_SUCCESS" if ok else "BUILD_FAILED")
    if os.path.exists(pre):
        os.remove(pre)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
