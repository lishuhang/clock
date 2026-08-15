#!/usr/bin/env python3
"""Normalize user-facing IPTV list URLs without changing channel order or labels."""

from __future__ import annotations

import argparse
from pathlib import Path

OLD = "https://iptv345.lishuhang.workers.dev/"
NEW = "https://345.lishuhang.com/"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.input.read_text(encoding="utf-8")
    replaced = source.count(OLD)
    normalized = source.replace(OLD, NEW)
    args.output.write_text(normalized, encoding="utf-8")
    print(f"replaced_workers_dev={replaced}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
