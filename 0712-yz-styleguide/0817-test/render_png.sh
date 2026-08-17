#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
render() {
  local input="$1"
  local output="${input%.html}.png"
  local height
  height="$(grep -oE '<svg[^>]*height="[0-9]+"' "$input" | head -1 | sed -E 's/.*height="([0-9]+).*/\1/')"
  : "${height:?无法从 SVG 读取高度}"
  chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --virtual-time-budget=1200 --window-size=1080,"$height" \
    --screenshot="$output" "file://$input" >/dev/null 2>&1
  printf 'Rendered %s\n' "${output#$ROOT/}"
}

while IFS= read -r file; do
  render "$file"
done < <(find "$ROOT/round1" "$ROOT/round2" "$ROOT/round3" -maxdepth 1 -type f -name '*.html' | sort)
