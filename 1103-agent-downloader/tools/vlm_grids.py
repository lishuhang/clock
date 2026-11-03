#!/usr/bin/env python3
# VLM批量复判九宫格: 切题性 + 推荐秒段(素材暂不切割, 仅标注用法)
# 完整输出留痕 materials/vlm/Sxxx.json; 对话仅打印每素材2行(内容摘要+推荐片段)
import json, os, subprocess, sys

MAT = "/home/z/my-project/clock/1103-agent-downloader/materials"
VLMD = os.path.join(MAT, "vlm")
os.makedirs(VLMD, exist_ok=True)
mats = json.load(open(os.path.join(MAT, "materials.json"), encoding="utf-8"))["materials"]

THEME = ("这是为一条孩之宝(Hasbro)Q3财经解说视频配的B-roll素材复判。文案要点: "
         "万智牌(MTG)卡片生意/孩之宝财报/IP矩阵(小猪佩奇、变形金刚、小马宝莉)/"
         "桌游店赛线下社交/卡牌印刷/关税与供应链/轻资产授权模式。")

for m in mats:
    if m["status"] == "fail":
        continue
    seq, dur = m["seq"], m.get("duration_sec") or 0
    grid = os.path.join(MAT, "thumbs", m.get("grid") or "")
    if not os.path.exists(grid):
        print(f"S{seq:03d} SKIP(无九宫格)")
        continue
    ts = [round(dur * k / 10, 1) for k in range(1, 10)]
    prompt = (f"{THEME}\n该素材为B站视频《{m['title']}》(UP:{m['author']}), 总长{dur:.0f}秒。"
              f"九宫格从左到右、从上到下依次是第{ts[0]}/{ts[1]}/{ts[2]}/{ts[3]}/{ts[4]}/{ts[5]}/{ts[6]}/{ts[7]}/{ts[8]}秒的画面。\n"
              "请输出(严格两行, 不要多余内容):\n"
              "第1行CONTENT: 九格内容概括, 每格≤12字, 分号分隔\n"
              "第2行CLIP: 针对上述文案要点, 推荐最值得用的片段, 最多3段, 格式=起s-止s|用途(≤10字), 分号分隔; 若画面与财经解说B-roll完全无关则输出NONE")
    out_json = os.path.join(VLMD, f"S{seq:03d}.json")
    r = subprocess.run(["z-ai", "vision", "-p", prompt, "-i", grid, "-o", out_json],
                       capture_output=True, text=True, timeout=180)
    try:
        j = json.load(open(out_json, encoding="utf-8"))
        content = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
    except Exception:
        content = f"(解析失败 rc={r.returncode}: {str(r.stderr)[-100:]})"
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()][:2]
    print(f"S{seq:03d} | " + " || ".join(lines[:2]))
print("DONE")
