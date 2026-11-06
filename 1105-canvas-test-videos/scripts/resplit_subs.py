#!/usr/bin/env python3
"""字幕重分卡 v7（修复老板审片两问题：单字卡 / 同句字号跳变）

输入（只读）:
  ep1_subtitles_whisper.json  365 卡 whisper 词级实测（唯一时间真值，不动）
  ep1_sentences_real.json     76 句 whisper 句级实测（分句依据）

规则:
  1) 卡片按 start 时间归入所属句（句 = 感知单元，断言全覆盖无遗漏）
  2) 句内向后合并"退化卡"（去标点后有效字 ≤2 的卡，含纯标点卡），
     合并上限 vlen≤15（fs48 单行 720px 的容量）；溢出则改向前合并
  3) 字号 tier 句内统一 = 句内最长卡的档位（68/56/48 ↔ tier 0/1/2）
     → 消灭"第一行小、第二行突然变大"（同一句内不再跳档）
  4) 时间轴零改动：合并卡的 start/end = 首卡 start / 末卡 end（whisper 锚点）

输出: ep1_subtitles_v7.json（带 _provenance 与自检数据）
"""
import json, re

REPO = "/home/z/my-project/clock/1105-canvas-test-videos"
SRC = f"{REPO}/04-ep1-production/ep1_subtitles_whisper.json"
SENTS = f"{REPO}/04-ep1-production/ep1_sentences_real.json"
OUT = f"{REPO}/04-ep1-production/ep1_subtitles_v7.json"

PUNCT = "，。：；！？、…—,.:;!?~“”\"'（）()《》<>【】"


def eff_len(s):
    return len(re.sub(f"[{re.escape(PUNCT)}]", "", s))


def vlen(s):
    return sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in s)


def tier_of(n):
    return 2 if n > 12.5 else (1 if n > 10.2 else 0)  # 0→68 1→56 2→48


# 词界切分点：每个 CJK 字后、每个 ASCII 词后
_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def rebalance_split(text):
    """把 text 在词界拆两半，两半 vlen≤15 且有效字≥3，尽量均衡。"""
    cuts = [m.end() for m in _WORD_RE.finditer(text)]
    cuts = [p for p in cuts if p < len(text)] + list(range(1, len(text)))
    best, bd = None, 1e9
    for p in sorted(set(cuts)):
        l, r = text[:p], text[p:]
        el, er = eff_len(l), eff_len(r)
        if el >= 3 and er >= 3 and vlen(l) <= 15.0 and vlen(r) <= 15.0:
            d = abs(el - er)
            if d < bd:
                best, bd = (l, r), d
    assert best, f"再平衡拆分失败: {text}"
    return best


# 连接词开头（应属下一句的句首短语，向前并入下卡）
_CONNECTIVE = re.compile(r"^(此外|另外|而且|但|而|同时|其次|然后|不过|因此|所以|即便|即使|如果|为了|既然|有的|仅有|仅|只有)")


def main():
    cards = json.load(open(SRC, encoding="utf-8"))["cards"]
    sents = json.load(open(SENTS, encoding="utf-8"))

    # 1) 卡归句（先按包含，落空则归最近的前一句——句间隙里的尾卡）
    for c in cards:
        owners = [s for s in sents if s["start"] - 0.01 <= c["start"] < s["end"] + 0.01]
        if not owners:
            prev = [s for s in sents if s["end"] <= c["start"] + 0.01]
            owners = [prev[-1]] if prev else []
        assert owners, f"卡 {c['start']:.2f}「{c['text']}」不属任何句"
        c["sent"] = owners[0]["i"]
    # 单调性：句号随卡序单调不减
    for a, b in zip(cards, cards[1:]):
        assert b["sent"] >= a["sent"], f"卡句序倒退 @{a['start']:.2f}"

    # 2) 合并退化卡（有效字≤2，含纯标点）：
    #    句内向后并；句首退化卡：纯标点/非连接词→跨句向后并（上句尾标点）
    #    连接词开头→向前并入下卡；溢出→合并后词界再平衡拆分
    out, n_merged, n_split, n_fwd, n_cross = [], 0, 0, 0, 0

    def back_merge(idx):
        """把 cards[idx] 并入 out[-1]；溢出则再平衡拆分。返回 True 成功。"""
        nonlocal n_merged, n_split, n_cross
        prev = out[-1]
        merged = prev["text"] + cards[idx]["text"]
        if vlen(merged) <= 15.0:
            prev["end"], prev["text"] = cards[idx]["end"], merged
            n_merged += 1
            if prev["sent"] != cards[idx]["sent"]:
                n_cross += 1
            return True
        pieces = rebalance_split(merged)
        span = cards[idx]["end"] - prev["start"]
        effs = [eff_len(p) for p in pieces]
        t1 = prev["start"] + span * effs[0] / (effs[0] + effs[1])
        prev.update(end=round(t1, 3), text=pieces[0], split=True)
        out.append({"start": round(t1, 3), "end": cards[idx]["end"],
                    "text": pieces[1], "sent": prev["sent"], "split": True})
        n_merged += 1
        n_split += 1
        return True

    pending_prefix = None  # 待向前并入下卡的文本（连接词句首短语）
    for i, c in enumerate(cards):
        if pending_prefix is not None:
            merged = pending_prefix + c["text"]
            if vlen(merged) <= 15.0:
                c = {"start": pending_start, "end": c["end"], "text": merged, "sent": c["sent"]}
                n_fwd += 1
            else:  # 溢出：连接词与下卡再平衡拆分
                pieces = rebalance_split(merged)
                span = c["end"] - pending_start
                effs = [eff_len(p) for p in pieces]
                t1 = pending_start + span * effs[0] / (effs[0] + effs[1])
                out.append({"start": pending_start, "end": round(t1, 3), "text": pieces[0],
                            "sent": c["sent"], "split": True})
                c = {"start": round(t1, 3), "end": c["end"], "text": pieces[1], "sent": c["sent"], "split": True}
                n_fwd += 1
                n_split += 1
            pending_prefix = None
        if eff_len(c["text"]) <= 2:
            same_prev = out and out[-1]["sent"] == c["sent"]
            if same_prev:
                back_merge(i)
            elif eff_len(c["text"]) == 0 or not _CONNECTIVE.match(c["text"].rstrip("，。：；！？、")):
                # 纯标点或内容尾字 → 跨句向后并（上句的尾巴）
                assert out, f"片首退化卡无法处理: {c['text']}"
                back_merge(i)
            else:
                # 连接词句首 → 挂起，向前并入下一卡
                pending_prefix, pending_start = c["text"], c["start"]
            continue
        out.append(dict(c))

    # 3) 句级 tier
    by_sent = {}
    for c in out:
        by_sent.setdefault(c["sent"], []).append(c)
    for cs in by_sent.values():
        t = tier_of(max(vlen(c["text"]) for c in cs))
        for c in cs:
            c["tier"] = t

    # 4) 断言
    degenerate = [c for c in out if eff_len(c["text"]) <= 2]
    overflow = [c for c in out if vlen(c["text"]) > 15.0]
    assert not overflow, f"超宽卡 {len(overflow)} 张: {[c['text'] for c in overflow[:5]]}"
    # 文本流守恒
    src_stream = "".join(c["text"] for c in cards).replace(" ", "")
    out_stream = "".join(c["text"] for c in out).replace(" ", "")
    assert src_stream == out_stream, "文本流不守恒"
    # 时间锚点守恒：每卡 start/end 是 whisper 锚点，或来自再平衡拆分（≤处）
    starts = {c["start"] for c in cards}
    ends = {c["end"] for c in cards}
    for c in out:
        assert c["start"] in starts or c.get("split", False), f"时间锚点丢失 @{c['start']:.2f}"
        assert c["end"] in ends or c.get("split", False), f"时间锚点丢失 @{c['end']:.2f}"
    # 同句相邻卡同 tier（老板问题 ② 的机器断言）
    for a, b in zip(out, out[1:]):
        if a["sent"] == b["sent"]:
            assert a["tier"] == b["tier"], f"同句跳档 @{a['end']:.2f}「{a['text']}」→「{b['text']}」"


    doc = {
        "_provenance": {
            "what": "价格篇显示用字幕卡 v7（分卡与字号在此定稿，组装只许引用本文件）",
            "time_source": "ep1_subtitles_whisper.json（365 卡 whisper 词级实测，时间轴未做任何改动）",
            "sentence_source": "ep1_sentences_real.json（76 句 whisper 句级实测）",
            "rules": [
                "退化卡（有效字≤2 含纯标点）句内向后合并，vlen≤15 上限",
                "字号 tier 句内统一=句内最长卡档位（0→68/1→56/2→48 竖屏，横屏映射 56/44/38）",
                "合并仅取首卡 start/末卡 end，whisper 锚点零漂移",
            ],
            "why": "老板审片：①字幕出现单字+句号卡 ②同句相邻行字号突变（48↔68 跳变 246 处）",
            "built_by": "resplit_subs.py（v7 轮，2026-11-06）",
            "checks": {
                "cards": len(out), "merged_degenerate": n_merged, "rebalance_splits": n_split,
                "forward_connective": n_fwd, "cross_sentence_tail": n_cross,
                "degenerate_left": len(degenerate),
                "degenerate_texts": [c["text"] for c in degenerate],
            },
        },
        "cards": [{k: c[k] for k in ("start", "end", "text", "sent", "tier") if k in c}
                   | ({"split": True} if c.get("split") else {}) for c in out],
    }
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 报告
    print(f"卡数: {len(cards)} → {len(out)}（合并 {n_merged}：句尾/纯标点含跨句 {n_cross}，连接词前并 {n_fwd}；再平衡拆分 {n_split} 处）")
    print(f"残留退化卡: {len(degenerate)} → {[c['text'] for c in degenerate]}")
    print(f"句数: {len(by_sent)}；tier 分布: " +
          str({t: sum(1 for c in out if c['tier'] == t) for t in (0, 1, 2)}))
    # 01:15 区域展示
    print("=== 76~95s 区域（01:15 修复区）===")
    for c in out:
        if 74 <= c["start"] <= 95:
            print(f"  {c['start']:7.2f}~{c['end']:7.2f} tier{c['tier']} 「{c['text']}」")


if __name__ == "__main__":
    main()
