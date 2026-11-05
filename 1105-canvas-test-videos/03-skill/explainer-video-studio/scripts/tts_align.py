#!/usr/bin/env python3
"""配音对齐器（Step 3）：timeline.json → 逐句音频 + 精准时间轴。
两种模式：
  A. --tts    逐句调用 https://tts.lishuhang.com（Playwright 自动化：拦截 audio 响应）
  B. --existing <整条配音.mp3>  对齐既有配音：silencedetect 找句间静音 → 按字数权重把句子分配进说话区间
共同后处理：
  - ffmpeg silenceremove 裁首尾静音（-40dB / 0.05s，段尾保留 0.12s 呼吸）
  - 句内字幕短句按 汉字1.0 + 句末标点1.2 权重线性映射实测时长（误差<0.1s，抛弃外部SRT）
产物: audio/S##.mp3 + aligned-timeline.json
铁律：严禁整篇一次合成再切（跨句累积误差不可救）。"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

TTS_URL = "https://tts.lishuhang.com"


def sh(*cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", *cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-300:])
    return r


def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def trim_silence(src, dst):
    sh("-i", src, "-af",
       "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-40dB,"
       "areverse,silenceremove=start_periods=1:start_duration=0.05:start_threshold=-40dB,"
       "areverse,apad=pad_dur=0.12", dst)


def char_weight(text):
    n = len(re.sub(r"[^\w\u4e00-\u9fff]", "", text))
    punct = 1.2 if re.search(r"[。！？；，：,.:?!]$", text) else 0.4
    return max(1.0, n + punct)


def split_subs(text, max_len=16):
    """台词拆 ≤max_len 字的短句（字幕条用），尽量在标点处断。"""
    parts = [p for p in re.split(r"(?<=[，。！？；、,!?])", text) if p.strip()]
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) <= max_len:
            buf += p
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out or [text]


def realign(subs, total_dur):
    ws = [char_weight(s) for s in subs]
    tw = sum(ws)
    aligned, cur = [], 0.0
    for i, (s, w) in enumerate(zip(subs, ws)):
        end = round(cur + w / tw * total_dur, 3) if i < len(subs) - 1 else round(total_dur, 3)
        aligned.append({"text": s, "start": round(cur, 3), "end": end})
        cur = end
    return aligned


def detect_speech_regions(path, min_gap=0.28):
    """silencedetect 找静音段 → 反推说话区间（--existing 模式）。"""
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-af",
                        f"silencedetect=noise=-38dB:d={min_gap}", "-f", "null", "-"],
                       capture_output=True, text=True)
    durs, starts = [], []
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            starts.append(float(m.group(1)))
        m = re.search(r"silence_duration: ([\d.]+)", line)
        if m:
            durs.append(float(m.group(1)))
    total = probe_dur(path)
    regions, cur = [], 0.0
    for st in starts:
        if st - cur > 0.15:
            regions.append([cur, st])
        cur = st + (durs.pop(0) if durs else 0)
    if total - cur > 0.15:
        regions.append([cur, total])
    return regions or [[0, total]]


def tts_one(text, out_mp3, page, voice=""):
    page.goto(TTS_URL, wait_until="domcontentloaded", timeout=20000)
    page.fill("textarea", text)
    if voice:
        try:
            page.select_option("select", voice)
        except Exception:  # noqa: BLE001
            pass
    audio = []
    page.on("response", lambda r: audio.append(r.body()) if "audio" in (r.headers.get("content-type") or "") else None)
    page.click("button:has-text('生成'), button:has-text('合成'), button:has-text('转换')")
    for _ in range(40):
        if audio:
            break
        page.wait_for_timeout(500)
    if not audio:
        raise RuntimeError("TTS 无音频响应（检查服务/改手工合成上传）")
    with open(out_mp3, "wb") as f:
        f.write(audio[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("audio_dir")
    ap.add_argument("--tts", action="store_true", help="逐句调用 tts.lishuhang.com")
    ap.add_argument("--existing", default=None, help="整条既有配音 mp3（对齐模式B）")
    ap.add_argument("--voice", default="")
    args = ap.parse_args()

    tl = json.load(open(args.timeline, encoding="utf-8"))
    os.makedirs(args.audio_dir, exist_ok=True)
    shots = tl["shots"]

    if args.tts:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            for s in shots:
                out = os.path.join(args.audio_dir, f"{s['id']}.mp3")
                if os.path.exists(out):
                    continue
                raw = os.path.join(args.audio_dir, f"{s['id']}_raw.mp3")
                tts_one(s["narration"], raw, page, args.voice)
                trim_silence(raw, out)
                os.remove(raw)
                s["audio_file"] = out
                s["duration"] = round(probe_dur(out), 3)
            browser.close()
        # 重排全局时间轴
        cur = 0.0
        for s in shots:
            s["start"], s["dur"] = round(cur, 3), s["duration"]
            cur += s["duration"]
            s["subs"] = realign(split_subs(s["narration"]), s["dur"])
    elif args.existing:
        regions = detect_speech_regions(args.existing)
        total_chars = sum(char_weight(s["narration"]) for s in shots)
        total_speech = sum(e - b for b, e in regions)
        rate = total_speech / total_chars  # 秒/权重字
        # 逐镜分配：按权重在说话区间流内推进（静音按比例分摊到句间停顿）
        cur_speech, cur_region = 0.0, 0
        t = regions[0][0]
        for s in shots:
            need = char_weight(s["narration"]) * rate
            s["start"] = round(t, 3)
            while need > 0 and cur_region < len(regions):
                b, e = regions[cur_region]
                pos = b + (t - b if b <= t <= e else 0)
                room = e - pos
                if need <= room:
                    t += need
                    need = 0
                else:
                    need -= room
                    cur_region += 1
                    t = regions[cur_region][0] if cur_region < len(regions) else e
            s["dur"] = round(t - s["start"], 3)
            s["subs"] = realign(split_subs(s["narration"]), s["dur"])
        tl["narration_file"] = args.existing
    else:
        sys.exit("需要 --tts 或 --existing <mp3> 之一")

    out_json = os.path.join(args.audio_dir, "aligned-timeline.json")
    json.dump(tl, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = shots[-1]["start"] + shots[-1]["dur"]
    print(f"ALIGN OK: {len(shots)} 镜 / 总时长 {total:.1f}s -> {out_json}")


if __name__ == "__main__":
    main()
