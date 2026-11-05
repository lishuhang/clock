#!/usr/bin/env python3
"""按正则从 tree.json 匹配网盘文件并批量下载（复用 netdisk.py 的三步下载逻辑）。
用法: BAIDU_NETDISK_ACCESS_TOKEN=xxx python3 batch_download.py <regex1> <regex2> ... -d <目标目录>
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, "/home/z/my-project/skills/remotion-video-studio/scripts")
import netdisk  # noqa: E402

TREE_JSON = "/home/z/my-project/netdisk_pull/tree.json"


def follow_download(url, out):
    """跟随 302 下载（每跳带 UA）。"""
    redirects = 0
    while True:
        netdisk.throttle()
        req = urllib.request.Request(url, headers={"User-Agent": netdisk.UA_NETDISK})
        resp = urllib.request.urlopen(req, timeout=180)
        if resp.status in (301, 302, 303, 307, 308):
            url = resp.headers.get("Location")
            redirects += 1
            if redirects > 5:
                raise RuntimeError("重定向超过 5 次")
            continue
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        with open(out, "wb") as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
        return done, total


def main():
    args = sys.argv[1:]
    dest = "downloads"
    if "-d" in args:
        i = args.index("-d")
        dest = args[i + 1]
        args = args[:i] + args[i + 2:]
    patterns = args
    os.makedirs(dest, exist_ok=True)

    tree = [e for e in json.load(open(TREE_JSON)) if not e.get("isdir")]
    matched = []
    for e in tree:
        if any(re.search(p, e["path"]) for p in patterns):
            matched.append(e)
    if not matched:
        sys.exit("没有匹配到文件")
    print(f"匹配 {len(matched)} 个文件，开始下载 -> {dest}")
    total_mb = sum(e.get("size", 0) for e in matched) / 2**20
    print(f"合计 {total_mb:.1f} MB")

    ok, fail = 0, []
    for e in matched:
        name = e.get("server_filename", e["path"].rsplit("/", 1)[-1])
        out = os.path.join(dest, name)
        if os.path.exists(out) and abs(os.path.getsize(out) - e.get("size", 0)) < 1024:
            print(f"  跳过(已存在) {name}")
            ok += 1
            continue
        try:
            dlink = netdisk._get_dlink(e["fs_id"])
            url = f"{dlink}&access_token={netdisk.get_token()}"
            done, total = follow_download(url, out)
            mark = "OK " if abs(done - e.get("size", done)) < 1024 else "SIZE_MISMATCH"
            print(f"  [{mark}] {name}  {done/2**20:.2f} MB")
            ok += 1
        except Exception as ex:  # noqa: BLE001
            print(f"  [FAIL] {name}: {ex}")
            fail.append(name)
    print(f"\n完成: {ok} 成功 / {len(fail)} 失败")
    if fail:
        print("失败清单:", fail)


if __name__ == "__main__":
    main()
