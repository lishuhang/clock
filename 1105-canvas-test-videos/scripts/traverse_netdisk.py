#!/usr/bin/env python3
"""递归遍历百度网盘指定目录树，输出全量清单 JSON + MD 时间线表。

用法:
  BAIDU_NETDISK_ACCESS_TOKEN=xxx python3 traverse_netdisk.py "/202610-AI视频画布横评" /home/z/my-project/netdisk_pull/tree.json

特性: BFS + 分页(limit=1000) + 0.35s 限速 + 每个目录处理完即落盘(崩溃可续跑,已处理目录跳过)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

TOKEN = os.environ["BAIDU_NETDISK_ACCESS_TOKEN"]
UA = "pan.baidu.com"
API = "https://pan.baidu.com/rest/2.0/xpan/file"
_last = 0.0


def throttle():
    global _last
    dt = time.time() - _last
    if dt < 0.35:
        time.sleep(0.35 - dt)
    _last = time.time()


def list_dir(dir_path):
    """列单个目录（含分页），返回 (entries, errno)。失败不抛异常，交由调用方记录。"""
    out, start = [], 0
    while True:
        throttle()
        params = urllib.parse.urlencode({
            "access_token": TOKEN, "method": "list", "dir": dir_path,
            "order": "time", "desc": 0, "start": start, "limit": 1000,
        })
        req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            return out, f"HTTP_ERR {e}"
        errno = data.get("errno", 0)
        if errno != 0:
            return out, errno
        page = data.get("list", [])
        out.extend(page)
        if len(page) < 1000:
            return out, 0
        start += 1000


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/"
    out_json = sys.argv[2] if len(sys.argv) > 2 else "/home/z/my-project/netdisk_pull/tree.json"
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    # 崩溃续跑：加载已有结果
    results, done_dirs = [], set()
    if os.path.exists(out_json):
        try:
            results = json.load(open(out_json))
            done_dirs = {r["path"] for r in results if r.get("isdir")}
            print(f"续跑模式: 已有 {len(results)} 条记录, {len(done_dirs)} 个目录已处理")
        except Exception:  # noqa: BLE001
            pass

    queue = [root]
    errors = []
    n_calls = 0
    while queue:
        d = queue.pop(0)
        if d in done_dirs:
            continue
        entries, errno = list_dir(d)
        n_calls += 1
        if errno != 0:
            errors.append({"dir": d, "errno": errno})
            print(f"  !! {d} -> errno={errno}")
        new_sub = []
        for e in entries:
            results.append(e)
            if e.get("isdir") == 1:
                new_sub.append(e["path"])
        queue.extend(new_sub)
        print(f"[{len(queue):3d} 待处理] {d} ({len(entries)} 项)")
        # 增量落盘
        json.dump(results, open(out_json, "w"), ensure_ascii=False, indent=1)

    json.dump(results, open(out_json, "w"), ensure_ascii=False, indent=1)
    n_files = sum(1 for r in results if not r.get("isdir"))
    n_dirs = sum(1 for r in results if r.get("isdir"))
    print(f"\n完成: {n_dirs} 目录 / {n_files} 文件 / {n_calls} 次API / 错误 {len(errors)} 个")
    print(f"输出: {out_json}")
    if errors:
        print("错误目录:", json.dumps(errors, ensure_ascii=False))


if __name__ == "__main__":
    main()
