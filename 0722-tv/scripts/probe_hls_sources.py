#!/usr/bin/env python3
"""Probe IPTV HLS URLs at playlist and media-segment levels.

The tool is intentionally transport-level: it reports whether a URL returns a
valid HLS manifest and whether consecutive advertised media resources can be
retrieved. It does not claim video/audio decoding success; encrypted or DRM-like
streams are marked for separate playback verification.

Results are checkpointed after each source and include only response metadata,
latency, and short structural diagnostics. No credentials are read or written.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36"
MANIFEST_HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/vnd.apple.mpegurl,application/x-mpegURL,*/*;q=0.8"}
MEDIA_HEADERS = {"User-Agent": USER_AGENT, "Accept": "video/*,*/*;q=0.8"}
HLS_MARKER = "#EXTM3U"
LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_entries(path: Path) -> list[dict[str, str]]:
    section = "未分类"
    entries: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("# ") or line.startswith("#\t"):
            continue
        if line.startswith("##"):
            section = line.lstrip("#").strip()
            continue
        if line.startswith("#") or "," not in line:
            continue
        name, url = line.split(",", 1)
        url = url.strip()
        if url.startswith(("http://", "https://")):
            entries.append({"section": section, "name": name.strip(), "url": url})
    if not entries:
        raise ValueError(f"no comma-delimited HTTP(S) entries found in {path}")
    return entries


def get_prefix(data: bytes, limit: int = 240) -> str:
    return data[:limit].decode("utf-8", errors="replace").replace("\n", "\\n").replace("\r", "")


def fetch_limited(session: requests.Session, url: str, headers: dict[str, str], timeout: float, limit: int) -> dict[str, Any]:
    started = time.perf_counter()
    response = session.get(url, headers=headers, timeout=(min(5.0, timeout), timeout), allow_redirects=True, stream=True)
    chunks: list[bytes] = []
    remaining = limit
    for chunk in response.iter_content(chunk_size=min(16_384, remaining)):
        if not chunk:
            continue
        chunks.append(chunk)
        remaining -= len(chunk)
        if remaining <= 0:
            break
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "url": url,
        "final_url": response.url,
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type", ""),
        "bytes_read": sum(map(len, chunks)),
        "body": b"".join(chunks),
        "latency_ms": elapsed_ms,
    }


def media_uris(manifest: str) -> list[str]:
    uris: list[str] = []
    for raw in manifest.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            uris.append(line)
    return uris


def is_master(manifest: str) -> bool:
    return "#EXT-X-STREAM-INF" in manifest or "#EXT-X-I-FRAME-STREAM-INF" in manifest


def probe_one(entry: dict[str, str], timeout: float, segments: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        **entry,
        "checked_at": utc_now(),
        "classification": "error",
        "status": None,
        "final_url": "",
        "content_type": "",
        "playlist_latency_ms": None,
        "playlist_bytes": 0,
        "manifest_level": "none",
        "manifest_prefix": "",
        "segment_attempted": 0,
        "segment_ok": 0,
        "segment_latency_ms": [],
        "segment_statuses": [],
        "encrypted_hint": False,
        "error": "",
    }
    session = requests.Session()
    try:
        first = fetch_limited(session, entry["url"], MANIFEST_HEADERS, timeout, 1_500_000)
        result.update({
            "status": first["status"],
            "final_url": first["final_url"],
            "content_type": first["content_type"],
            "playlist_latency_ms": first["latency_ms"],
            "playlist_bytes": first["bytes_read"],
            "manifest_prefix": get_prefix(first["body"]),
        })
        if not (200 <= first["status"] < 300):
            result["classification"] = "http_error"
            return result
        manifest = first["body"].decode("utf-8", errors="replace")
        if HLS_MARKER not in manifest:
            result["classification"] = "not_hls"
            return result

        if is_master(manifest):
            result["manifest_level"] = "master"
            variants = media_uris(manifest)
            if not variants:
                result["classification"] = "invalid_manifest"
                return result
            second_url = urljoin(first["final_url"], variants[0])
            second = fetch_limited(session, second_url, MANIFEST_HEADERS, timeout, 1_500_000)
            if not (200 <= second["status"] < 300):
                result["classification"] = "variant_http_error"
                result["error"] = f"variant status {second['status']}"
                return result
            manifest = second["body"].decode("utf-8", errors="replace")
            result["manifest_level"] = "master+media"
            result["final_url"] = second["final_url"]
            result["playlist_latency_ms"] = round(first["latency_ms"] + second["latency_ms"], 1)
            result["playlist_bytes"] += second["bytes_read"]
            if HLS_MARKER not in manifest:
                result["classification"] = "invalid_manifest"
                return result
        else:
            result["manifest_level"] = "media"

        result["encrypted_hint"] = "#EXT-X-KEY" in manifest or "encrypt:2" in manifest.lower()
        uris = media_uris(manifest)[:segments]
        if not uris:
            result["classification"] = "playlist_only"
            return result

        for item in uris:
            segment_url = urljoin(result["final_url"], item)
            result["segment_attempted"] += 1
            try:
                sample = fetch_limited(session, segment_url, MEDIA_HEADERS, timeout, 262_144)
                result["segment_statuses"].append(sample["status"])
                result["segment_latency_ms"].append(sample["latency_ms"])
                if 200 <= sample["status"] < 300 and sample["bytes_read"] > 0:
                    result["segment_ok"] += 1
            except requests.RequestException as exc:
                result["segment_statuses"].append("exception")
                result["error"] = str(exc)[:240]

        if result["segment_ok"] == result["segment_attempted"]:
            result["classification"] = "transport_ok_encrypted_hint" if result["encrypted_hint"] else "transport_ok"
        elif result["segment_ok"]:
            result["classification"] = "partial_segment_failure"
        else:
            result["classification"] = "segment_failure"
        return result
    except requests.RequestException as exc:
        result["classification"] = "request_exception"
        result["error"] = str(exc)[:240]
        return result
    except Exception as exc:  # preserve audit progress rather than crash a long run
        result["classification"] = "probe_exception"
        result["error"] = repr(exc)[:240]
        return result
    finally:
        session.close()


def atomic_write_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = [
        "section", "name", "url", "classification", "status", "final_url", "content_type",
        "playlist_latency_ms", "playlist_bytes", "manifest_level", "segment_attempted", "segment_ok",
        "encrypted_hint", "segment_statuses", "segment_latency_ms", "error", "checked_at",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in results:
            row = dict(row)
            row["segment_statuses"] = json.dumps(row.get("segment_statuses", []), ensure_ascii=False)
            row["segment_latency_ms"] = json.dumps(row.get("segment_latency_ms", []), ensure_ascii=False)
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe HLS sources with resumable checkpoints.")
    parser.add_argument("input", type=Path, help="comma-delimited channel list")
    parser.add_argument("--json", dest="json_path", type=Path, required=True, help="checkpoint/final JSON output")
    parser.add_argument("--csv", dest="csv_path", type=Path, required=True, help="flat CSV output")
    parser.add_argument("--workers", type=int, default=8, help="maximum concurrent probes")
    parser.add_argument("--timeout", type=float, default=12.0, help="per-request read timeout in seconds")
    parser.add_argument("--segments", type=int, default=2, help="consecutive media objects per playlist")
    parser.add_argument("--limit", type=int, default=0, help="cap sources for smoke tests")
    parser.add_argument("--only-regex", default="", help="only URLs matching this Python regex")
    args = parser.parse_args()

    entries = parse_entries(args.input)
    if args.only_regex:
        pattern = re.compile(args.only_regex)
        entries = [entry for entry in entries if pattern.search(entry["url"])]
    if args.limit:
        entries = entries[:args.limit]
    if not entries:
        print("No entries selected", file=sys.stderr)
        return 2

    prior: dict[str, dict[str, Any]] = {}
    if args.json_path.exists():
        try:
            for item in json.loads(args.json_path.read_text(encoding="utf-8")):
                prior[item["url"]] = item
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    pending = [entry for entry in entries if entry["url"] not in prior]
    results = list(prior.values())
    print(f"selected={len(entries)} cached={len(results)} pending={len(pending)} workers={args.workers}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(probe_one, entry, args.timeout, args.segments): entry for entry in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            result = future.result()
            with LOCK:
                results.append(result)
                atomic_write_json(args.json_path, results)
            print(f"{index}/{len(pending)} {result['classification']} {result['status']} {result['name']} | {result['url']}", flush=True)

    result_by_url = {item["url"]: item for item in results}
    ordered = [result_by_url[entry["url"]] for entry in entries]
    atomic_write_json(args.json_path, ordered)
    write_csv(args.csv_path, ordered)
    summary = Counter(item["classification"] for item in ordered)
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
