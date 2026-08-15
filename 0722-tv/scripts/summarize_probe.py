#!/usr/bin/env python3
"""Summarize resumable HLS probe JSON into a compact, reproducible report."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


def source_kind(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host == "345.lishuhang.com":
        if "/ysp" in url:
            return "345-custom-ysp"
        if "/xuexi_" in url:
            return "345-custom-xuexi"
        if "/wso-" in url:
            return "345-custom-wso"
        return "345-custom-legacy"
    if host == "iptv345.lishuhang.workers.dev":
        return "345-workers-dev-legacy"
    return "direct-non345"


def percent(n: int, d: int) -> str:
    return "0.0%" if d == 0 else f"{n / d * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[source_kind(row["url"])].append(row)

    ok_statuses = {"transport_ok", "transport_ok_encrypted_hint"}
    lines = ["# IPTV HLS 探测汇总", "", f"总线路数：**{len(rows)}**。探测标准为可取得有效 HLS 清单并连续取得两个媒体资源；仅代表传输链路，不代表 DRM/私有加扰内容可被浏览器解码。", "", "| 来源类别 | 线路数 | 传输可用 | 可用率 | 主要失败分类 |", "|---|---:|---:|---:|---|"]
    for kind, items in sorted(groups.items()):
        counts = Counter(item["classification"] for item in items)
        usable = sum(counts[key] for key in ok_statuses)
        failures = ", ".join(f"{name}={count}" for name, count in counts.most_common(4))
        lines.append(f"| {kind} | {len(items)} | {usable} | {percent(usable, len(items))} | {failures} |")

    all_counts = Counter(row["classification"] for row in rows)
    lines.extend(["", "## 全部分类", "", "| 分类 | 数量 |", "|---|---:|"])
    lines.extend(f"| {name} | {count} |" for name, count in sorted(all_counts.items()))

    slow = sorted((row for row in rows if row.get("playlist_latency_ms") is not None), key=lambda row: row["playlist_latency_ms"], reverse=True)[:20]
    lines.extend(["", "## 最慢的清单请求（前 20）", "", "| 频道 | 来源类别 | 延迟（ms） | 探测分类 | URL |", "|---|---|---:|---|---|"])
    for row in slow:
        lines.append(f"| {row['name']} | {source_kind(row['url'])} | {row['playlist_latency_ms']} | {row['classification']} | `{row['url']}` |")

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
