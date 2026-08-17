#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
for html in "$ROOT"/round2.3/*-styled.html; do
  png="${html%.html}.png"
  chromium --headless --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=1080,1080 --screenshot="$png" "file://$html" >/dev/null 2>&1
  printf 'Rendered %s\n' "${png#$ROOT/}"
done
