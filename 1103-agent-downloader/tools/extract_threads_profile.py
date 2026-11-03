#!/usr/bin/env python3
# 从 Threads 主页 Googlebot-SSR HTML 中抽取: video_versions / 帖子code / 文案
import re, json, sys

for h in ("mosseri", "zuck"):
    p = f"/tmp/th_{h}.html"
    try:
        html = open(p, encoding="utf-8", errors="ignore").read()
    except FileNotFoundError:
        print(f"@{h}: 文件不存在")
        continue
    print(f"===== @{h} (bytes={len(html)}) =====")
    # 1) video_versions (括号配平解析)
    i = html.find('"video_versions":')
    if i >= 0:
        j = html.find("[", i)
        depth, k = 0, j
        while k < len(html):
            if html[k] == "[":
                depth += 1
            elif html[k] == "]":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        try:
            vs = json.loads(html[j:k + 1])
            for v in vs:
                print(f"  video: width={v.get('width')} height={v.get('height')} url={str(v.get('url'))[:130]}")
        except Exception as e:
            print(f"  video_versions解析失败: {e}")
    else:
        print("  (无 video_versions)")
    # 2) 帖子 code
    codes = re.findall(r'"code"\s*:\s*"([A-Za-z0-9_-]{6,25})"', html)
    print(f"  codes: {codes[:8]}")
    # 3) 主页里第一条文案(粗略)
    m = re.search(r'"text"\s*:\s*"([^"]{10,150})"', html)
    if m:
        print(f"  text样例: {m.group(1)[:120]}")
