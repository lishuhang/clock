#!/usr/bin/env python3
"""三集分镜表生成器。
台词直接从网盘文案终稿按段落/句子切片提取（零抄写误差），时间码按字数权重线性分配：
- V1 有真实配音(740.36s)，rate 由实测反推
- V2/V3 按同一语速估算
同时输出制作用 timeline JSON（投产后供 TTS 对齐/截帧脚本消费）。
"""
import json
import os
import re
import sys

BASE = "/home/z/my-project"
SRC = f"{BASE}/netdisk_pull/key_files/评测视频文案终稿-1104-1800.md"
OUT_DIR = f"{BASE}/github-work/1105-canvas-test-videos/02-storyboards"
DL_DIR = f"{BASE}/download"
V1_AUDIO_SEC = 740.362438

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_v1 import SHOTS as SHOTS_V1, EP_TITLE as T1  # noqa: E402
from data_v2 import SHOTS as SHOTS_V2, EP_TITLE as T2  # noqa: E402
from data_v3 import SHOTS as SHOTS_V3, EP_TITLE as T3  # noqa: E402


def load_episodes():
    """把文案终稿解析成 {集名: [段落...]}。"""
    eps, cur = {}, None
    for line in open(SRC, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^## (第[一二三]集[^#]*?)$", line)
        if m:
            cur = m.group(1).strip()
            eps[cur] = []
            continue
        if cur is None:
            continue
        if line.startswith("## "):        # 风格微调报告等后续章节
            cur = None
            continue
        if line.strip():
            eps[cur].append(line.strip())
    return eps


def split_sentences(para):
    """中文句切分（保留标点）。"""
    parts = re.split(r"(?<=[。！？；])", para)
    return [p for p in parts if p.strip()]


def fmt_mmss(sec):
    m, s = divmod(int(round(sec)), 60)
    return f"{m:02d}:{s:02d}"


def build_episode(ep_key, para_list, shots, audio_sec=None, rate=None):
    """返回 (shots_enriched, total_sec)。shots_enriched 每项含台词与时间码。"""
    out = []
    for (pid, sl, visual, material, pace, note) in shots:
        para = para_list[pid - 1]
        sents = split_sentences(para)
        if sl is None:
            text = para
        elif isinstance(sl, tuple):
            text = "".join(sents[sl[0]:sl[1]])
        else:
            text = "".join(sents[i] for i in sl)
        n = len(re.sub(r"\s", "", text))
        out.append({"para": pid, "text": text, "chars": n,
                    "visual": visual, "material": material,
                    "pace": pace, "note": note or ""})
    total_chars = sum(s["chars"] for s in out)
    if audio_sec is not None:
        rate = audio_sec / total_chars
    total = 0.0
    for s in out:
        dur = s["chars"] * rate
        s["start"] = total
        s["dur"] = dur
        total += dur
    for s in out:
        s["t"] = f"{fmt_mmss(s['start'])}-{fmt_mmss(s['start'] + s['dur'])}"
    return out, total, rate


def render_md(ep_no, ep_title, shots, total, audio_note):
    rows = []
    for i, s in enumerate(shots, 1):
        note = f"　{note_txt}" if (note_txt := s["note"]) else ""
        rows.append(
            f"| {i:02d} | {s['t']} | {s['text']} | {s['visual']} | {s['material']}{note} |")
    return f"""### 第{ep_no}集 · {ep_title}

**时长口径**：{audio_note}（预计成片 {fmt_mmss(total)}，{len(shots)} 个镜头）

| # | 时段 | 台词（口播原文，直接取自终稿） | 画面设计（4:3 安全框内） | 素材来源 / 节奏备注 |
|---|---|---|---|---|
{chr(10).join(rows)}
""", total


def main():
    eps = load_episodes()
    keys = list(eps.keys())
    print("文案解析:", {k: len(v) for k, v in eps.items()})

    v1, total1, rate = build_episode(keys[0], eps[keys[0]], SHOTS_V1, audio_sec=V1_AUDIO_SEC)
    v2, total2, _ = build_episode(keys[1], eps[keys[1]], SHOTS_V2, rate=rate)
    v3, total3, _ = build_episode(keys[2], eps[keys[2]], SHOTS_V3, rate=rate)

    md1, _ = render_md(1, T1, v1, total1, "已按真实配音 740.36s 反推语速对齐")
    md2, _ = render_md(2, T2, v2, total2, f"按第一集实测语速 {1/rate:.1f} 字/秒估算")
    md3, _ = render_md(3, T3, v3, total3, f"按第一集实测语速 {1/rate:.1f} 字/秒估算")

    header = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "header.md"), encoding="utf-8").read()
    header = header.replace("{{TOTAL1}}", fmt_mmss(total1)).replace("{{TOTAL2}}", fmt_mmss(total2)).replace("{{TOTAL3}}", fmt_mmss(total3))
    header = header.replace("{{SHOTS1}}", str(len(v1))).replace("{{SHOTS2}}", str(len(v2))).replace("{{SHOTS3}}", str(len(v3)))
    header = header.replace("{{RATE}}", f"{1/rate:.2f}")
    header = header.replace("{{D1}}", "740.36s（实测）").replace("{{D2}}", fmt_mmss(total2) + "（估算）").replace("{{D3}}", fmt_mmss(total3) + "（估算）")

    md = header + md1 + "\n---\n\n" + md2 + "\n---\n\n" + md3
    for d in (OUT_DIR, DL_DIR):
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "storyboard-trilogy.md" if d == OUT_DIR else "AI视频画布横评_三集分镜表_1105.md"), "w", encoding="utf-8").write(md)

    # 制作用 timeline JSON（投产种子）
    for tag, shots, total in (("ep1", v1, total1), ("ep2", v2, total2), ("ep3", v3, total3)):
        payload = {"episode": tag, "fps": 30, "canvas": [1080, 1920],
                   "safe_frame": [1080, 1440, 240, 1680], "total_sec": round(total, 2),
                   "shots": [{"id": f"S{i:02d}", "start": round(s['start'], 2), "dur": round(s['dur'], 2),
                              "narration": s['text'], "visual": s['visual'], "material": s['material'],
                              "pace": s['pace']} for i, s in enumerate(shots, 1)]}
        json.dump(payload, open(os.path.join(OUT_DIR, f"timeline-{tag}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"OK 分镜表: V1 {len(v1)}镜/{fmt_mmss(total1)}  V2 {len(v2)}镜/{fmt_mmss(total2)}  V3 {len(v3)}镜/{fmt_mmss(total3)}  语速 {1/rate:.2f}字/秒")
    print(f"输出: {OUT_DIR}/storyboard-trilogy.md + {DL_DIR}/AI视频画布横评_三集分镜表_1105.md + timeline-ep*.json")


if __name__ == "__main__":
    main()
