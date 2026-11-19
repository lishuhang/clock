#!/usr/bin/env bash
# rapi 通道全流程实测：trial-session → generations → tasks/batch → 图床
BASE="https://gpt2.lishuhang.com"
OUT="$(dirname "$0")/rapi-flow-test-$(date +%Y%m%d%H%M%S).txt"
exec > >(tee -a "$OUT") 2>&1
echo "=== rapi flow test @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "--- 1. trial-session (via worker) ---"
S1=$(curl -s -X POST "$BASE/api/rapi/trial-session" -H "Content-Type: application/json" -d '{}' --max-time 60)
echo "$S1" | head -c 400; echo
CRED=$(echo "$S1" | python3 -c "import json,sys;print(json.load(sys.stdin).get('credential',''))" 2>/dev/null)
if [ -z "$CRED" ]; then echo "FATAL: no credential"; exit 1; fi
echo "cred OK: ${CRED:0:36}..."

echo "--- 2. generations (via worker) ---"
G=$(curl -s -w "\nHTTP:%{http_code}" -X POST "$BASE/api/rapi/generations" \
  -H "Content-Type: application/json" -H "Cookie: rapi_trial=$CRED" \
  -d '{"prompt":"a cute orange cat sitting on a windowsill, watercolor style","model":"gpt-image-2","size":"1024x1024","n":1}' --max-time 90)
echo "$G" | head -c 600; echo
GH=$(echo "$G" | tail -1)
BODY=$(echo "$G" | sed '$d')
TID=$(echo "$BODY" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('task_id') or (d.get('tasks') or [{}])[0].get('task_id',''))" 2>/dev/null)
if [ -z "$TID" ]; then echo "no task_id, stop"; exit 1; fi
echo "task_id: $TID"

echo "--- 3. poll tasks/batch up to ~100s ---"
for i in $(seq 1 20); do
  sleep 5
  B=$(curl -s -X POST "$BASE/api/rapi/tasks/batch" -H "Content-Type: application/json" \
    -H "Cookie: rapi_trial=$CRED" -d "{\"task_ids\":[\"$TID\"]}" --max-time 60)
  ST=$(echo "$B" | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin)
  t=(d.get('tasks') or d.get('data') or [None])[0] or {}
  print(t.get('status','')+'|'+str(t.get('image_url') or t.get('url') or ''))
except Exception as e:
  print('parse_err|'+str(e)[:80])")
  echo "[$i] $ST"
  case "$ST" in succeeded*|completed*|done*) break;; esac
  case "$ST" in failed*|error*|parse_err*) echo "B body: $(echo "$B" | head -c 400)"; break;; esac
done

echo "--- 4. result body dump (last poll) ---"
echo "$B" | head -c 1200; echo
echo "=== done, log: $OUT ==="
