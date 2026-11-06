#!/usr/bin/env python3
"""素材切片机 v1（2026-11-07 用户原则固化的通用基建）：

原则（用户原话归纳，同步入 skill B 组铁律）：
  1. 大素材只在【第一次】下载时碰原件；下载完立刻按需切成小片段；
  2. 之后任何会话/崩溃恢复只引用切片，绝不重新下载大文件；
  3. 单个切片硬上限 20MB（GitHub 友好），目标几百 KB ~ 几 MB；
  4. 每个切片在 MANIFEST.json 里标好：来源、时间窗、用途、被哪些镜头引用；
  5. 切片只做等比缩放（force_original_aspect_ratio=decrease），绝不拉伸变形。

用法:
  python3 slice_materials.py <manifest.json>
  manifest JSON 结构见 repo clips/ep1_slices.json 等；
  源用 "local:<path>"（本地已下载原件）。

产物:
  repo clips/<name>.mp4 + clips/MANIFEST.json 索引（幂等：已存在且校验通过则跳过）
"""
import json
import os
import subprocess
import sys

REPO = "/home/z/my-project/repo/1105-canvas-test-videos"
CLIPS = f"{REPO}/clips"
MANIFEST = f"{CLIPS}/MANIFEST.json"
HARD_LIMIT = 20 * 2**20          # 用户硬上限：单个素材不得大于 20MB
WARN_LIMIT = 6 * 2**20           # 超过这个值打个招呼（目标应是几百KB~几MB）


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path, entries="format=duration"):
    r = sh("ffprobe", "-v", "error", "-show_entries", entries,
           "-of", "default=noprint_wrappers=1:nokey=1", path)
    return r.stdout.strip()


def load_index():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST, encoding="utf-8"))
    return {"slices": {}}


def cut(src, w0, w1, out, box=None, fps=30):
    """精确窗切割 + 可选等比缩放进目标框（不拉伸）。返回 (ok, err)。"""
    vf = "fps=%d,format=yuv420p" % fps
    if box:
        # force_divisible_by=2：yuv420p 编码要求偶数尺寸（2880x1800→1080x675 奇数高会炸 x264）
        vf = ("scale=%d:%d:force_original_aspect_ratio=decrease:force_divisible_by=2," % box) + vf
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-ss", f"{w0:.3f}", "-to", f"{w1:.3f}",
         "-i", src, "-vf", vf,
         "-c:v", "libx264", "-crf", "18", "-preset", "fast",
         "-an", "-movflags", "+faststart", out],
        capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr[-400:]
    return True, ""


def main():
    mpath = sys.argv[1]
    spec = json.load(open(mpath, encoding="utf-8"))
    os.makedirs(CLIPS, exist_ok=True)
    idx = load_index()
    changed = False
    for s in spec["slices"]:
        name = s["name"]
        out = f"{CLIPS}/{name}.mp4"
        ent = idx["slices"].get(name, {})
        # 幂等：存在 + 时长对 + 索引里用途一致 → 跳过
        if os.path.exists(out) and ent.get("window") == s["window"] and ent.get("purpose") == s["purpose"]:
            dur = probe(out)
            try:
                if abs(float(dur) - (s["window"][1] - s["window"][0])) < 0.5:
                    print(f"[skip] {name}（已切片）")
                    continue
            except ValueError:
                pass
        src = s["source"]
        assert src.startswith("local:"), f"{name}: 暂只支持 local: 源（原件应已一次性下载到本地）"
        spath = src[6:]
        if not os.path.exists(spath):
            print(f"[MISS] {name}: 源不存在 {spath} —— 先跑一次性下载（para_dl / netdisk.py / dl_bili_v2）")
            continue
        w0, w1 = s["window"]
        src_dur = float(probe(spath) or -1)
        assert src_dur <= 0 or w1 <= src_dur + 0.2, \
            f"{name}: 窗 {w1}s 超出源时长 {src_dur:.1f}s"
        box = tuple(s["box"]) if s.get("box") else None
        ok, err = cut(spath, w0, w1, out, box)
        if not ok:
            print(f"[FAIL] {name}: {err}")
            continue
        size = os.path.getsize(out)
        dur = float(probe(out) or -1)
        assert size < HARD_LIMIT, \
            f"{name}: {size/2**20:.1f}MB 违反 20MB 硬上限 —— 缩短窗口或加 box 缩放"
        if size > WARN_LIMIT:
            print(f"[warn] {name}: {size/2**20:.1f}MB 偏大（目标几百KB~几MB）")
        idx["slices"][name] = {
            "file": f"clips/{name}.mp4", "source": s.get("src_note", src),
            "window": s["window"], "box": box, "duration": round(dur, 2),
            "size_mb": round(size / 2**20, 2), "purpose": s["purpose"],
            "used_by": s.get("used_by", []), "episode": s.get("episode", ""),
        }
        changed = True
        print(f"[ok] {name}: {dur:.2f}s {size/2**20:.2f}MB ← {os.path.basename(spath)} [{w0}-{w1}]")
    if changed:
        json.dump(idx, open(MANIFEST, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"[manifest] {MANIFEST} 已更新（{len(idx['slices'])} 条切片）")
    else:
        print("[manifest] 无变更")


if __name__ == "__main__":
    main()
