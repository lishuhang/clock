#!/usr/bin/env bash
# ============================================================
# deploy_v22.sh — kmage-kdr-rapi-zimage-2.2 部署脚本
# Worker 名: ai-image；域: gpt2.lishuhang.com / ai-image.lishuhang.workers.dev
#
# 凭据来源（优先级）:
#   1. 环境变量 CF_TOKEN（API Token）+ CF_ACC（Account ID）
#   2. /home/z/my-project/scripts/.cruise_secrets.env（沙箱约定位置，
#      在 git 仓库 clock/ 之外，token 严禁入 repo——沿袭 v2.0 部署纪律）
#
# 用法: bash debug/deploy_v22.sh
# 部署方式: CF API multipart PUT（metadata {"body_part":"worker.js"}），
#           与 v2.1 部署一致；部署后双域 /healthz 验证版本号。
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

# ---- 凭据 ----
if [ -z "${CF_TOKEN:-}" ] || [ -z "${CF_ACC:-}" ]; then
  SECRETS=/home/z/my-project/scripts/.cruise_secrets.env
  if [ -f "$SECRETS" ]; then
    # shellcheck disable=SC1090
    set -a; . "$SECRETS"; set +a
  fi
fi
if [ -z "${CF_TOKEN:-}" ] || [ -z "${CF_ACC:-}" ]; then
  echo "缺少凭据：请设置 CF_TOKEN 与 CF_ACC 环境变量（或写入 /home/z/my-project/scripts/.cruise_secrets.env）" >&2
  exit 1
fi

WORKER_NAME=ai-image
SRC=gpt2-worker-kmage-v2.2.js
EXPECT_VER='kmage-kdr-rapi-zimage-2.2'

# 部署前现网版本备份（回滚源）
curl -s --max-time 30 "https://gpt2.lishuhang.com/healthz" -o /tmp/pre_deploy_healthz.json || true
echo "== 部署前现网: $(cat /tmp/pre_deploy_healthz.json 2>/dev/null | head -c 200)"

echo "== 部署 $SRC -> $WORKER_NAME ..."
HTTP_CODE=$(cat "$SRC" | curl -s -o /tmp/deploy_resp.json -w '%{http_code}' -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/${CF_ACC}/workers/scripts/${WORKER_NAME}" \
  -H "Authorization: Bearer ${CF_TOKEN}" \
  -F 'metadata={"body_part":"worker.js"};type=application/json' \
  -F 'worker.js=@-;type=application/javascript')
echo "== 部署响应 HTTP $HTTP_CODE: $(head -c 300 /tmp/deploy_resp.json)"
[ "$HTTP_CODE" = "200" ] || { echo "部署失败"; exit 1; }

# 双域验证（SW 缓存可能短暂返回旧壳，重试几次）
sleep 3
for i in 1 2 3 4 5; do
  V1=$(curl -s --max-time 20 "https://gpt2.lishuhang.com/healthz" | grep -o "$EXPECT_VER" || true)
  V2=$(curl -s --max-time 20 "https://ai-image.lishuhang.workers.dev/healthz" | grep -o "$EXPECT_VER" || true)
  echo "== 域名验证 try#$i: gpt2.lishuhang.com=${V1:-旧版} workers.dev=${V2:-旧版}"
  if [ -n "$V1" ] && [ -n "$V2" ]; then
    echo "== 部署成功，双域均为 $EXPECT_VER"
    exit 0
  fi
  sleep 4
done
echo "!! 部署 API 已 200，但某域名尚未出现新版本号（可能是传播延迟），请手动复查 /healthz"
exit 2
