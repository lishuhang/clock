#!/usr/bin/env python3
"""网盘大文件并行 Range 下载（para_dl v2，入库版）。
用法: BAIDU_NETDISK_ACCESS_TOKEN=xxx python3 para_dl.py <netdisk_path> <out_path> [分段数]

链路: filemetas 拿 dlink -> 跟 302 拿直链 -> N 路并行 Range 分段 -> 合并 + 大小断言。
（v1 随沙盒回收丢失，本版为重建，教训：脚本必须即时入库。）
"""
import json
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SKILL_SCRIPTS = "/home/z/my-project/skills/remotion-video-studio/scripts"
sys.path.insert(0, SKILL_SCRIPTS)
import netdisk  # noqa: E402

UA = netdisk.UA_NETDISK


def get_direct_url(path):
    fsid = netdisk._resolve_fsid(path)
    dlink = netdisk._get_dlink(fsid)
    url = f"{dlink}&access_token={netdisk.get_token()}"
    for _ in range(6):
        netdisk.throttle()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=60)
        if resp.status in (301, 302, 303, 307, 308):
            url = resp.headers.get("Location")
            continue
        resp.close()
        return url
    raise RuntimeError("重定向超过 5 次")


def head_size(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
    resp = urllib.request.urlopen(req, timeout=60)
    cr = resp.headers.get("Content-Range", "")  # bytes 0-0/123456
    resp.close()
    return int(cr.split("/")[-1])


def fetch_range(url, start, end, part_path):
    if os.path.exists(part_path) and os.path.getsize(part_path) == end - start + 1:
        return part_path  # 幂等续跑
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Range": f"bytes={start}-{end}"})
            resp = urllib.request.urlopen(req, timeout=300)
            with open(part_path + ".tmp", "wb") as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.getsize(part_path + ".tmp") == end - start + 1:
                os.replace(part_path + ".tmp", part_path)
                return part_path
        except Exception as e:
            print(f"  [retry {attempt+1}] {part_path}: {e}", file=sys.stderr)
    raise RuntimeError(f"分段失败: {part_path}")


def main():
    path, out = sys.argv[1], sys.argv[2]
    nseg = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    url = get_direct_url(path)
    total = head_size(url)
    print(f"文件大小: {total/2**20:.1f} MB, {nseg} 段并行")
    bounds = []
    step = total // nseg
    for i in range(nseg):
        s = i * step
        e = (i + 1) * step - 1 if i < nseg - 1 else total - 1
        bounds.append((s, e))
    parts = [f"{out}.part{i}" for i in range(nseg)]

    def run(i):
        return fetch_range(url, bounds[i][0], bounds[i][1], parts[i])

    with ThreadPoolExecutor(max_workers=nseg) as ex:
        list(ex.map(run, range(nseg)))
    with open(out, "wb") as f:
        for p in parts:
            with open(p, "rb") as pf:
                while True:
                    chunk = pf.read(1 << 22)
                    if not chunk:
                        break
                    f.write(chunk)
    size = os.path.getsize(out)
    assert size == total, f"合并后大小不符 {size} != {total}"
    for p in parts:
        os.remove(p)
    print(f"完成 ✅ {out} ({size/2**20:.1f} MB)")


if __name__ == "__main__":
    main()
