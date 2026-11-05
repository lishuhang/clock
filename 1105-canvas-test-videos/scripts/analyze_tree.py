#!/usr/bin/env python3
"""分析网盘目录树: 顶层结构、时间线、关键文件识别（文案/调研/skill候选）。"""
import json
import re
import sys
from datetime import datetime

tree = json.load(open("/home/z/my-project/netdisk_pull/tree.json"))
ROOT = "/202610-AI视频画布横评"

def ts(v):
    return datetime.fromtimestamp(v).strftime("%m-%d %H:%M") if v else "?"

def depth(p):
    return p.replace(ROOT, "").count("/")

# ---- 1. 顶层结构 ----
print("=" * 90)
print("【顶层结构】(根下直接子项)")
for e in sorted(tree, key=lambda x: (x.get("isdir", 0) == 0, x.get("server_mtime", 0))):
    if e["path"].rsplit("/", 1)[0] == ROOT:
        kind = "DIR " if e.get("isdir") else "FILE"
        size = f"{e.get('size', 0)/2**20:8.1f}MB" if not e.get("isdir") else "          "
        print(f"  [{kind}] {ts(e.get('server_mtime'))}  {e.get('server_filename', ''):60s} {size}")

# ---- 2. 各一级/二级目录的文件统计 ----
print("=" * 90)
print("【一级目录汇总】")
from collections import defaultdict
stats = defaultdict(lambda: {"n": 0, "dirs": 0, "mb": 0.0, "newest": 0})
for e in tree:
    rel = e["path"].replace(ROOT + "/", "")
    if not rel:
        continue
    top = rel.split("/")[0]
    s = stats[top]
    if e.get("isdir"):
        s["dirs"] += 1
    else:
        s["n"] += 1
        s["mb"] += e.get("size", 0) / 2**20
        s["newest"] = max(s["newest"], e.get("server_mtime", 0) or 0)
for top, s in sorted(stats.items(), key=lambda kv: -kv[1]["newest"]):
    print(f"  {ts(s['newest'])}  {top[:55]:55s} {s['n']:5d}文件 {s['mb']:9.1f}MB {s['dirs']:3d}子目录")

# ---- 3. 文档类文件时间线 (md/txt/docx/pdf/html，排除深层素材) ----
print("=" * 90)
print("【文档类文件时间线】(md/txt/docx/pdf/html/xmind/txt, 按修改时间)")
docs = [e for e in tree if not e.get("isdir")
        and re.search(r"\.(md|txt|docx?|pdf|html?|xmind|csv|json|srt)$", e.get("server_filename", ""), re.I)]
for e in sorted(docs, key=lambda x: x.get("server_mtime", 0)):
    print(f"  {ts(e.get('server_mtime'))}  {e.get('size',0)/2**10:8.0f}KB  {e['path'].replace(ROOT+'/','')}")

# ---- 4. 重点: 视频改编-1105-1200 全子树 ----
print("=" * 90)
print("【视频改编-1105-1200 全子树】")
sub = [e for e in tree if e["path"].startswith(ROOT + "/视频改编-1105-1200")]
for e in sorted(sub, key=lambda x: (x.get("isdir", 0) == 0, x["path"])):
    kind = "DIR " if e.get("isdir") else "FILE"
    size = f"{e.get('size', 0)/2**10:8.0f}KB" if not e.get("isdir") else "        "
    print(f"  [{kind}] {ts(e.get('server_mtime'))} {size}  {e['path'].replace(ROOT+'/视频改编-1105-1200/','')}")

# ---- 5. mmdd-hhmm 命名模式的文件 ----
print("=" * 90)
print("【文件名含 mmdd-hhmm 时间戳的路径】(去重到父目录级)")
seen = set()
for e in sorted(tree, key=lambda x: x.get("server_mtime", 0)):
    m = re.search(r"(\d{4})-(\d{4})", e.get("server_filename", ""))
    if m:
        p = e["path"].replace(ROOT + "/", "")
        key = p.rsplit("/", 1)[0] if e.get("isdir") else p
        if key not in seen:
            seen.add(key)
            print(f"  {ts(e.get('server_mtime'))}  {p[:100]}")
print(f"\n总计: {len(tree)} 项")
