#!/usr/bin/env python3
"""Build user-facing IPTV outputs from the latest HLS probe results.

Rules encoded from the task:
* use the custom 345 domain, never workers.dev;
* include transport-verified entries in the main list;
* record failures only for non-345 direct entries in the broken list;
* retain successful historical 345 lines as a distinct, traceable fallback group.

"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

OK = {"transport_ok", "transport_ok_encrypted_hint"}
CUSTOM_345 = "345.lishuhang.com"
WORKERS_DEV = "iptv345.lishuhang.workers.dev"


def read_probe(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_345(url: str) -> bool:
    return (urlparse(url).hostname or "") in {CUSTOM_345, WORKERS_DEV}


def safe_url(url: str) -> str:
    return url.replace(f"https://{WORKERS_DEV}/", f"https://{CUSTOM_345}/")


def render_entry(name: str, url: str) -> str:
    return f"{name},{safe_url(url)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-probe", type=Path, required=True)
    parser.add_argument("--historical-345-probe", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--broken", type=Path, required=True)
    args = parser.parse_args()

    user_rows = read_probe(args.user_probe)
    history_rows = read_probe(args.historical_345_probe)
    user_sections: dict[str, list[dict]] = defaultdict(list)
    for row in user_rows:
        user_sections[row.get("section", "未分类")].append(row)

    main_lines = [
        "#EXTM3U",
        "# 生成：2026-08-15 GMT+8；仅保留已取得有效 HLS 清单及连续媒体资源的线路。",
        "# 345 中转统一使用 https://345.lishuhang.com/；不会使用 workers.dev 域名。",
        "# 传输可用不等于对 DRM、私有加扰或特定地区限制的画面/音频解码保证；请在目标播放器复核。",
        "",
    ]
    seen: set[str] = set()
    kept_user = 0
    for section, rows in user_sections.items():
        usable = [row for row in rows if row["classification"] in OK]
        if not usable:
            continue
        main_lines.append(f"## {section}")
        main_lines.append("")
        for row in usable:
            item = render_entry(row["name"], row["url"])
            if item not in seen:
                main_lines.append(item)
                seen.add(item)
                kept_user += 1
        main_lines.append("")

    historical_ok = [row for row in history_rows if row["classification"] in OK]
    if historical_ok:
        main_lines.extend([
            "## 345 历史目录中本轮传输可用的补充线路",
            "# 频道名沿用源目录的原始标识，用于高级替换与追溯；不保证与用户面向频道名一一对应。",
            "",
        ])
        for row in historical_ok:
            item = render_entry(row["name"], row["url"])
            if item not in seen:
                main_lines.append(item)
                seen.add(item)
        main_lines.append("")

    broken_rows = [row for row in user_rows if not is_345(row["url"]) and row["classification"] not in OK]
    broken_lines = [
        "# 非 345 直连源失效清单",
        "# 生成：2026-08-15 GMT+8。仅包含本轮 HLS 传输探测失败的非 345 中转线路。",
        "# 分类含义：http_error=上游 HTTP 失败；request_exception=连接/超时；not_hls=非 HLS 响应；segment_failure/partial_segment_failure=媒体资源不完整。",
        "",
    ]
    for row in broken_rows:
        broken_lines.append(f"# {row['classification']}; HTTP={row.get('status')}; {row.get('error') or '无额外错误信息'}")
        broken_lines.append(render_entry(row["name"], row["url"]))

    args.main.write_text("\n".join(main_lines).rstrip() + "\n", encoding="utf-8")
    args.broken.write_text("\n".join(broken_lines).rstrip() + "\n", encoding="utf-8")
    print(f"main_entries={len(seen)} user_entries={kept_user} historical_added={len(seen) - kept_user}")
    print(f"broken_direct_entries={len(broken_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
