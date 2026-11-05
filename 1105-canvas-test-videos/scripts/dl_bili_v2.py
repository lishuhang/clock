#!/usr/bin/env python3
"""B站下载 v2：pagelist 拿 cid → playurl 拿流 → 下载 + 体检（B9坏包/B31试看钳制）。
"""
import json
import os
import subprocess
import sys
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
OUT = "/home/z/my-project/ep1-work/materials/bili"
S = requests.Session()
S.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/",
                  "Accept": "application/json, text/plain, */*"})

TARGETS = {
    "paizi": {"bvid": "BV11mFLziEyP", "cid": 35817195845, "expect_dur": 465},
    "sss": {"bvid": "BV1FFRQB2Eqw", "cid": 38210570929, "expect_dur": 214},
}


def ffprobe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return -1


def ffcheck(path):
    """B9 体检：只拦致命错误。"""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"],
                       capture_output=True, text=True)
    fatal = [l for l in r.stderr.splitlines()
             if any(k in l for k in ("Invalid", "NAL", "moov", "corrupt", "EOF"))]
    return fatal


def download_stream(url, dst):
    with S.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dst + ".part", "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    os.replace(dst + ".part", dst)
    return os.path.getsize(dst)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, t in TARGETS.items():
        final = f"{OUT}/{name}.mp4"
        if os.path.exists(final) and os.path.getsize(final) > 5e6:
            dur = ffprobe_dur(final)
            if dur >= t["expect_dur"] * 0.9:
                print(f"[skip] {name} 已完整 ({dur:.0f}s)")
                continue
        r = S.get("https://api.bilibili.com/x/player/playurl",
                  params={"bvid": t["bvid"], "cid": t["cid"], "qn": 80,
                          "platform": "html5", "high_quality": 1}, timeout=15)
        j = r.json()
        if j.get("code") != 0:
            print(f"[FAIL] {name} playurl: {j.get('code')} {j.get('message')}")
            continue
        data = j["data"]
        durl = data.get("durl")
        print(f"[playurl] {name} quality={data.get('quality')} "
              f"timelength={data.get('timelength', 0)/1e6:.0f}s")
        if durl:
            d0 = durl[0]
            print(f"  durl: size={d0.get('size',0)/1e6:.1f}MB length={d0.get('length',0)/1e3:.0f}s")
            url = d0["url"]
            tries = 0
            while tries < 3:
                tries += 1
                sz = download_stream(url, final)
                dur = ffprobe_dur(final)
                fatal = ffcheck(final)
                print(f"  try{tries}: {sz/1e6:.1f}MB dur={dur:.0f}s fatal={len(fatal)}")
                if dur >= t["expect_dur"] * 0.85 and not fatal:
                    print(f"[ok] {final}")
                    break
                print(f"  [B31/B9] 不完整或坏包，重下 {tries}/3")
                if os.path.exists(final):
                    os.remove(final)
        else:
            print(f"  无 durl，data keys: {list(data.keys())}")


if __name__ == "__main__":
    main()
