#!/bin/bash
# cruise-bot 部署脚本（凭据从 scripts/.cruise_secrets.env 读取，本文件零凭据可入 git）
set -euo pipefail
source /home/z/my-project/scripts/.cruise_secrets.env

API="https://api.cloudflare.com/client/v4/accounts/$CF_ACC"
WORKER_DIR="/home/z/my-project/clock/cruise-bot"
NAME="cruise-bot"

# ---------- 1. 部署 worker（multipart: metadata + module） ----------
# ⚠️ 绑定语义（2026-10-14 实测）：metadata 里列出的绑定会被整表替换；
#    未列出的 secret_text 会被 CF 自动保留（值不可读所以不会被覆盖），
#    但未列出的 kv_namespace / plain_text 会直接丢失！
#    META_TOKEN 的裸值已遗失（仅在 CF secrets 里），因此永远不要把它写进本文件——
#    只要 metadata 不含它，CF 就自动保留。若哪天它真丢了，让用户在
#    API Setup 点 Generate access token 给新临时 token 再 fb_exchange_token 换新。
# ⚠️ 绑定红线（1014 定稿）：META_TOKEN 与 META_APP_SECRET 永不出现在下方 JSON——
#    裸值已遗失，未列出的 secret_text 会被 CF 自动保留；一旦列进 metadata 会用
#    空值覆盖、永久损毁。iMessage 上线时在 WIFE_WA 行后追加三行：
#    {"type": "secret_text", "name": "BB_BASE", "text": "$BB_BASE"},
#    {"type": "secret_text", "name": "BB_PASSWORD", "text": "$BB_PASSWORD"},
#    {"type": "secret_text", "name": "WIFE_IGUID", "text": "$WIFE_IGUID"}
cat > /tmp/.cb_meta.json << EOF
{
  "main_module": "worker.js",
  "compatibility_date": "2025-09-01",
  "bindings": [
    {"type": "kv_namespace", "name": "CKV", "namespace_id": "$KV_ID"},
    {"type": "plain_text", "name": "DEFAULT_CITY", "text": "上海"},
    {"type": "plain_text", "name": "META_APP_ID", "text": "$META_APP_ID"},
    {"type": "plain_text", "name": "WABA_ID", "text": "$WABA_ID"},
    {"type": "secret_text", "name": "GLM_API_KEY", "text": "$GLM_KEY"},
    {"type": "secret_text", "name": "AGENT_KEY", "text": "$AGENT_KEY"},
    {"type": "secret_text", "name": "OWNER_WA", "text": "$OWNER_WA"},
    {"type": "secret_text", "name": "WIFE_WA", "text": "$WIFE_WA"},
    {"type": "secret_text", "name": "META_VERIFY_TOKEN", "text": "$META_VERIFY"},
    {"type": "secret_text", "name": "META_PHONE_NUMBER_ID", "text": "$META_PHONE_NUMBER_ID"}
  ]
}
EOF

echo "== 上传 worker script =="
curl -s -m 60 -X PUT "$API/workers/scripts/$NAME" \
  -H "authorization: Bearer $CF_TOKEN" \
  -F "metadata=@/tmp/.cb_meta.json;type=application/json" \
  -F "worker.js=@$WORKER_DIR/worker.js;type=application/javascript+module" \
  | python3 -c "import json,sys; j=json.load(sys.stdin); print('upload:', j.get('success'), [e.get('message') for e in j.get('errors',[])][:2])"

rm -f /tmp/.cb_meta.json

# ---------- 2. workers.dev 子域启用 ----------
echo "== workers.dev =="
SUB=$(curl -s -m 20 "$API/workers/subdomain" -H "authorization: Bearer $CF_TOKEN" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['subdomain'])")
echo "subdomain: $SUB"
curl -s -m 20 -X POST "$API/workers/scripts/$NAME/subdomain" \
  -H "authorization: Bearer $CF_TOKEN" -H "content-type: application/json" \
  -d '{"enabled":true,"previews_enabled":false}' \
  | python3 -c "import json,sys; j=json.load(sys.stdin); print('route enabled:', j.get('success'), [e.get('message') for e in j.get('errors',[])][:2])"

echo "$SUB" > /home/z/my-project/scripts/.cruise_subdomain.txt
echo "DONE. URL: https://$NAME.$SUB.workers.dev"
