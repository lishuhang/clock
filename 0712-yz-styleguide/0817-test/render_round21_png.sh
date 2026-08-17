#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
for input in "$ROOT"/round2.1/*.html; do
  output="${input%.html}.png"
  chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1080,1080 \
    --screenshot="$output" "file://$input" >/dev/null 2>&1
  printf 'Rendered %s\n' "${output#$ROOT/}"
done
