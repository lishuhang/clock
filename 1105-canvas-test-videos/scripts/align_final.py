#!/usr/bin/env python3
"""最终时间轴对齐器：whisper 词级时间戳 + 脚本文本模糊对齐 + 静音边界吸附。
产物: ep1-work/ep1_sentences_real.json（与 ep1_sentences.json 同构，时间实测）
"""
import json
import re

from difflib import SequenceMatcher

WORK = "/home/z/my-project/ep1-work"
SENT_IN = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/ep1_sentences.json"


def norm(s):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)


def main():
    sents = json.load(open(SENT_IN, encoding="utf-8"))
    wsegs = json.load(open(f"{WORK}/whisper_segs.json", encoding="utf-8"))
    regions = json.load(open(f"{WORK}/speech_regions.json"))["regions"]
    region_starts = [r[0] for r in regions]
    region_ends = [r[1] for r in regions]

    # 1) whisper 字符时间线
    W, wt_s, wt_e = "", [], []  # 每字符的 (start, end)
    for seg in wsegs:
        for w in seg["words"]:
            t = norm(w["w"])
            for _ in t:
                W += "0"
                wt_s.append(w["s"])
                wt_e.append(w["e"])
    # W 用占位构建，实际字符流单独存
    # 重建字符流
    W = ""
    wchars = []
    for seg in wsegs:
        for w in seg["words"]:
            t = norm(w["w"])
            if t:
                W += t
                wchars.append((w["s"], w["e"], len(t)))
    S = "".join(norm(s["text"]) for s in sents)
    print(f"脚本字符 {len(S)} / whisper字符 {len(W)} (比值 {len(S)/max(1,len(W)):.3f})")

    # 2) 全局对齐：脚本字符 → whisper字符
    m = SequenceMatcher(None, S, W, autojunk=False)
    blocks = [b for b in m.get_matching_blocks() if b.size > 0]

    def whisper_char_time(wpos, want_end=False):
        """whisper 字符位置 → 时间（线性插值词内）。"""
        # 找到 wpos 所在词
        acc = 0
        for ws, we, ln in wchars:
            if acc <= wpos < acc + ln:
                frac = (wpos - acc) / ln
                return we if want_end else ws + frac * (we - ws)
            acc += ln
        return wchars[-1][1] if wchars else 0.0

    def script_pos_time(spos, want_end=False):
        """脚本字符位置 → 时间：经匹配块映射到 whisper 字符，再转时间。"""
        for b in blocks:
            if b.a <= spos < b.a + b.size:
                wpos = b.b + (spos - b.a)
                if wpos >= b.size + b.b:
                    wpos = b.b + b.size - 1
                return whisper_char_time(min(wpos, len(W) - 1), want_end)
        # 落在 gap：取左右最近块边界的中点
        prev_end = 0
        for b in blocks:
            if spos < b.a:
                t_gap_s = whisper_char_time(max(0, prev_end - 1), True)
                t_gap_e = whisper_char_time(b.b, False)
                mid = (t_gap_s + t_gap_e) / 2
                return mid
            prev_end = b.b + b.size
        return whisper_char_time(len(W) - 1, True)

    # 3) 句子边界
    out = []
    cur = 0
    for s in sents:
        n = len(norm(s["text"]))
        st = script_pos_time(cur, False)
        en = script_pos_time(cur + n - 1, True)
        # 吸附：句首接近某区间起点(<=0.35s)则吸附
        for rs in region_starts:
            if 0 <= st - rs <= 0.35:
                st = rs
                break
            if 0 <= rs - st <= 0.15:
                st = rs
                break
        for re_ in region_ends:
            if 0 <= re_ - en <= 0.35:
                en = re_
                break
        out.append({"i": s["i"], "text": s["text"],
                    "start": round(st, 2), "end": round(en, 2)})
        cur += n

    # 4) 单调性修正
    for k in range(1, len(out)):
        if out[k]["start"] < out[k - 1]["end"]:
            out[k]["start"] = out[k - 1]["end"]
        if out[k]["end"] < out[k]["start"] + 0.3:
            out[k]["end"] = out[k]["start"] + 0.3
    json.dump(out, open(f"{WORK}/ep1_sentences_real.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 5) 报告
    print("\n前12句 实测 vs 原估算：")
    for k in range(min(12, len(out))):
        d = out[k]["start"] - sents[k]["start"]
        print(f"  句{k}: 实测 {out[k]['start']:7.2f}-{out[k]['end']:7.2f} | 原估 {sents[k]['start']:7.2f}-{sents[k]['end']:7.2f} | 偏差 {d:+.2f}s")
    dev = [out[k]["start"] - sents[k]["start"] for k in range(len(out))]
    print(f"\n句首偏差: max {max(dev):+.2f}s / min {min(dev):+.2f}s")
    print(f"句尾 {out[-1]['end']:.2f}s (音轨 740.36s)")
    # 与silencedetect区间起点的一致性抽检
    print("\n抽查：句首 vs 最近的区间起点差")
    diffs = []
    for k in range(0, len(out), 8):
        st = out[k]["start"]
        near = min(region_starts, key=lambda r: abs(r - st))
        diffs.append(abs(st - near))
        print(f"  句{k}: {st:.2f} vs 区间 {near:.2f} (Δ{st-near:+.2f}s)")


if __name__ == "__main__":
    main()
