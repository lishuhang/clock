#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
for html in "$ROOT"/round1.4/*-styled.html; do
  png="${html%.html}.png"
  chromium --headless --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --virtual-time-budget=1600 --window-size=1100,4200 --screenshot="$png" "file://$html" >/dev/null 2>&1
  printf 'Rendered %s\n' "${png#$ROOT/}"
done
