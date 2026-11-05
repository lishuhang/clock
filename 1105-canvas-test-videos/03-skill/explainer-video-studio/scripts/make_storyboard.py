#!/usr/bin/env python3
"""分镜表生成器（Step 2）：口播稿 + 镜头数据 → 分镜表 md + timeline.json。
用法:
  python3 make_storyboard.py <script.md> <shots_data.py> <out_prefix> [--audio-sec 740.36] [--header header.md]

口播稿格式：非空行=段落（# 标题行跳过）。
镜头数据格式（shots_data.py，仿本 skill examples）：
  SHOTS = [ (段号, 句切片, 画面设计, 素材, 节奏, 备注), ... ]
  句切片：None=整段； (起,止)=句索引区间（左闭右开，按 。！？； 切句）
  EP_TITLE = "集名"
时间码：字数权重线性分配；--audio-sec 给出整条配音实测时长时反推语速（最准）。"""
import argparse
import importlib.util
import json
import os
import re
import sys


def load_script(path):
    paras = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            paras.append(line)
    return paras


def sents(para):
    return [p for p in re.split(r"(?<=[。！？；])", para) if p.strip()]


def mmss(sec):
    m, s = divmod(int(round(sec)), 60)
    return f"{m:02d}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("shots_data")
    ap.add_argument("out_prefix")
    ap.add_argument("--audio-sec", type=float, default=None)
    ap.add_argument("--header", default=None)
    args = ap.parse_args()

    spec = importlib.util.spec_from_file_location("shots_data", args.shots_data)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    paras = load_script(args.script)
    shots = []
    for (pid, sl, visual, material, pace, note) in mod.SHOTS:
        if pid > len(paras):
            sys.exit(f"ERROR: 镜头引用段号 {pid} 超出口播稿段落数 {len(paras)}")
        ss = sents(paras[pid - 1])
        text = paras[pid - 1] if sl is None else ("".join(ss[sl[0]:sl[1]]) if isinstance(sl, tuple) else "".join(ss[i] for i in sl))
        shots.append({"text": text, "chars": len(re.sub(r"\s", "", text)),
                      "visual": visual, "material": material, "pace": pace, "note": note or ""})

    total_chars = sum(s["chars"] for s in shots)
    rate = (args.audio_sec / total_chars) if args.audio_sec else 1 / 4.9  # 默认 4.9字/秒（B站解说常见语速）
    t = 0.0
    for s in shots:
        s["dur"] = s["chars"] * rate
        s["start"] = t
        t += s["dur"]
    total = t

    rows = [f"| {i:02d} | {mmss(s['start'])}-{mmss(s['start']+s['dur'])} | {s['text']} | {s['visual']} | {s['material']}{'　'+s['note'] if s['note'] else ''} |"
            for i, s in enumerate(shots, 1)]
    md = (open(args.header, encoding="utf-8").read() if args.header else "") + f"""
### {mod.EP_TITLE}

**时长口径**：{'配音实测 ' + f'{args.audio_sec:.1f}s' if args.audio_sec else '默认语速 4.9 字/秒估算'}（预计成片 {mmss(total)}，{len(shots)} 镜，{total_chars} 字）

| # | 时段 | 台词（口播原文） | 画面设计 | 素材来源 / 节奏备注 |
|---|---|---|---|---|
""" + "\n".join(rows) + "\n"
    open(args.out_prefix + ".md", "w", encoding="utf-8").write(md)

    payload = {"fps": 30, "canvas": [1080, 1920], "safe_frame": [1080, 1440, 240, 1680],
               "total_sec": round(total, 2),
               "shots": [{"id": f"S{i:02d}", "start": round(s['start'], 2), "dur": round(s['dur'], 2),
                          "narration": s['text'], "visual": s['visual'], "material": s['material'],
                          "pace": s['pace']} for i, s in enumerate(shots, 1)]}
    json.dump(payload, open(args.out_prefix + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"STORYBOARD OK: {len(shots)} 镜 / {mmss(total)} / 语速 {1/rate:.2f} 字/秒 -> {args.out_prefix}.md/.json")


if __name__ == "__main__":
    main()
