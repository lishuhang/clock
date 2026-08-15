#!/usr/bin/env python3
"""Extract the first JavaScript module from a Cloudflare Worker download result.

Input is the JSON result emitted by the configured Cloudflare client. The script
never prints source code or any values from it; it only writes a local JS file
and reports byte count plus SHA-256 for audit and reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: extract_worker_download.py <mcp-result.json> <output.js>", file=sys.stderr)
        return 2

    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        raw = payload["result"]
        if not isinstance(raw, str):
            raise ValueError("result is not a string")

        normalized = raw.replace("\r\n", "\n")
        parts = normalized.split("\n\n", 1)
        if len(parts) != 2:
            raise ValueError("multipart preamble has no header/body separator")
        module_and_tail = parts[1]
        boundary_index = module_and_tail.rfind("\n--")
        if boundary_index == -1:
            raise ValueError("multipart closing boundary not found")
        code = module_and_tail[:boundary_index]
        if not code.strip():
            raise ValueError("empty Worker module")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding="utf-8")
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
        print(f"extracted_bytes={len(code.encode('utf-8'))}")
        print(f"sha256={digest}")
        print(f"output={output_path}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
