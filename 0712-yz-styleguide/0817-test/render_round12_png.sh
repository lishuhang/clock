#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
render_one(){
  local input="$1" width="$2" height="$3" output="${1%.html}.png"
  chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size="$width,$height" \
    --screenshot="$output" "file://$input" >/dev/null 2>&1
  printf 'Rendered %s\n' "${output#$ROOT/}"
}
for html in "$ROOT"/round1.2/*-styled.html; do height="$(grep -oE -- '--chart-height:[0-9]+px' "$html" | head -1 | sed -E 's/.*:([0-9]+)px/\1/')"; : "${height:=2600}"; render_one "$html" 1800 "$height"; done
for html in "$ROOT"/round2.2/*-styled.html; do render_one "$html" 1080 1080; done
