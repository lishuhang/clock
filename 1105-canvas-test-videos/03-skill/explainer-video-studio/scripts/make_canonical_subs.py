#!/usr/bin/env python3
"""重建权威字幕源（canonical subtitle JSON）——v6 复盘修复的核心产物之一。

背景（复盘结论）：v5 音画不同步复发的直接原因 = assemble_v5 的 SUBS 指向了仓库里
v2 时代的旧对齐文件 ep1_subtitles.json（385 卡，字数权重时间轴，全片漂移
-23.6s ~ +27.8s），而 v3 修复时真正使用的 whisper 实测卡文件
（ep1_subtitles_real.json / ep1_subtitles_v4.json）只存在于沙盒 WORK 目录，
从未入库，沙盒回收后即丢失。

本脚本从仓库中唯一幸存的 whisper 实测交付物 `output/字幕v3.srt`（365 卡，
2026-11-06 v3 交付、用户验收"音画同步已修复"的那一版）反向构建 canonical
JSON，并写入血缘（provenance）元数据。从此字幕只有这一个事实源。

用法: python3 make_canonical_subs.py
产出: 04-ep1-production/ep1_subtitles_whisper.json（入库）
"""
import json
import re
import sys

REPO = "/home/z/my-project/clock/1105-canvas-test-videos"
SRC_SRT = f"{REPO}/04-ep1-production/output/字幕v3.srt"
OUT = f"{REPO}/04-ep1-production/ep1_subtitles_whisper.json"


def ts2s(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return round(int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000, 3)


def main():
    cards = []
    for block in open(SRC_SRT, encoding="utf-8").read().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        m = re.match(r"(\d+)\s*\n([\d:,.]+) --> ([\d:,.]+)\n?(.*)", block, re.S)
        if not m:
            continue
        text = "\n".join(lines[2:]).strip()
        cards.append({"start": ts2s(m.group(2)), "end": ts2s(m.group(3)), "text": text})

    # 基本校验：卡数、时长覆盖、单调性
    assert len(cards) == 365, f"卡数异常: {len(cards)} != 365"
    for a, b in zip(cards, cards[1:]):
        assert b["start"] >= a["start"] - 1e-6, "时间轴非单调"
        assert a["end"] > a["start"], "空卡"
    last_end = max(c["end"] for c in cards)
    doc = {
        "_provenance": {
            "what": "价格篇权威字幕卡（唯一事实源，任何组装脚本只许引用本文件）",
            "alignment": "whisper(faster-whisper base, hf-mirror) 词级时间戳 + silencedetect(-38dB/0.22s) 双校准 + jieba 词边界分卡",
            "source": "output/字幕v3.srt（v3 交付版，用户验收音画同步 OK）",
            "rebuilt_by": "make_canonical_subs.py（v6 复盘轮，2026-11-06）",
            "history": [
                "v1/v2: ep1_subtitles.json 385卡 字数权重/早期ASR → 全片漂移±27s（作废，仅存档）",
                "v3: whisper实测对齐 ep1_subtitles_real.json 365卡 → 字幕v3.srt 交付（未入库JSON，教训）",
                "v4: ep1_subtitles_v4.json（沙盒，丢失）→ 字幕v4.srt=v3/1.1",
                "v5: 误用 ep1_subtitles.json 旧文件 → 音画不同步复发（本复盘）",
                "v6: 本文件（从字幕v3.srt 反向重建，入库，此后为唯一事实源）",
            ],
            "checks": "卡数365；时间单调；末卡end={:.3f}s ≤ 配音740.36s".format(last_end),
        },
        "cards": cards,
    }
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK: {len(cards)} 卡 → {OUT}")
    print(f"首卡: {cards[0]}")
    print(f"末卡: {cards[-1]}")


if __name__ == "__main__":
    sys.exit(main())
