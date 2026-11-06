#!/usr/bin/env python3
"""实测字幕重建：句实测时间 + whisper 词锚定的卡内时间。
产物: ep1-work/ep1_subtitles_real.json
"""
import json
import re
import jieba

from difflib import SequenceMatcher

WORK = "/home/z/my-project/ep1-work"
SENT_IN = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/ep1_sentences.json"


def norm(s):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)


def split_subs(text, max_len=14):
    parts = [p for p in re.split(r"(?<=[，。！？；、,!?：:])", text) if p.strip()]
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) <= max_len:
            buf += p
        else:
            if buf:
                out.append(buf)
            # 超长片段按词边界硬切（jieba 词不跨卡）
            while len(p) > max_len:
                words = list(jieba.cut(p))
                cut, acc = max_len, 0
                for wi, wd in enumerate(words):
                    if acc + len(wd) > max_len:
                        cut = acc if acc > 0 else max_len
                        break
                    acc += len(wd)
                else:
                    cut = max_len
                out.append(p[:cut])
                p = p[cut:]
            buf = p
    if buf:
        out.append(buf)
    return [o.strip().rstrip("。") or o for o in out] or [text]


def main():
    sents = json.load(open(SENT_IN, encoding="utf-8"))
    real = json.load(open(f"{WORK}/ep1_sentences_real.json", encoding="utf-8"))
    wsegs = json.load(open(f"{WORK}/whisper_segs.json", encoding="utf-8"))

    # whisper 字符时间线
    W = ""
    wchars = []
    for seg in wsegs:
        for w in seg["words"]:
            t = norm(w["w"])
            if t:
                W += t
                wchars.append((w["s"], w["e"], len(t)))
    S = "".join(norm(s["text"]) for s in sents)
    m = SequenceMatcher(None, S, W, autojunk=False)
    blocks = [b for b in m.get_matching_blocks() if b.size > 0]

    def wtime(wpos, want_end=False):
        acc = 0
        for ws, we, ln in wchars:
            if acc <= wpos < acc + ln:
                frac = (wpos - acc) / ln
                return we if want_end else ws + frac * (we - ws)
            acc += ln
        return wchars[-1][1] if wchars else 0.0

    def stime(spos, want_end=False):
        for b in blocks:
            if b.a <= spos < b.a + b.size:
                wpos = min(b.b + (spos - b.a), len(W) - 1)
                return wtime(wpos, want_end)
        prev = 0
        for b in blocks:
            if spos < b.a:
                return (wtime(max(0, prev - 1), True) + wtime(b.b, False)) / 2
            prev = b.b + b.size
        return wtime(len(W) - 1, True)

    out = []
    cur = 0
    for s, r in zip(sents, real):
        pieces = split_subs(s["text"])
        c = cur
        for j, p in enumerate(pieces):
            n = len(norm(p))
            st = stime(c, False)
            en = stime(c + n - 1, True)
            # 夹在句实测区间内
            st = max(st, r["start"]) if j == 0 else max(st, r["start"])
            en = min(en, r["end"]) if j == len(pieces) - 1 else min(en, r["end"])
            if en <= st:
                en = st + 0.3
            out.append({"start": round(st, 2), "end": round(en, 2), "text": p})
            c += n
        cur += len(norm(s["text"]))

    # 单调修正
    for k in range(1, len(out)):
        if out[k]["start"] < out[k - 1]["end"]:
            out[k]["start"] = out[k - 1]["end"]
        if out[k]["end"] < out[k]["start"] + 0.25:
            out[k]["end"] = out[k]["start"] + 0.25
    json.dump(out, open(f"{WORK}/ep1_subtitles_real.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    lens = [len(o["text"]) for o in out]
    print(f"字幕 {len(out)} 条, 最长 {max(lens)} 字, 覆盖 {out[0]['start']:.1f}s → {out[-1]['end']:.1f}s")
    for o in out[:8]:
        print(f"  {o['start']:7.2f}-{o['end']:7.2f} {o['text']}")


if __name__ == "__main__":
    main()
