#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_PATH="$ROOT_DIR/runtime/config.json"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Finance Node config not found: $CONFIG_PATH"
  exit 1
fi

CONFIG_VALUES="$(python3 - <<PY
import json
from pathlib import Path

config = json.loads(Path("$CONFIG_PATH").read_text(encoding="utf-8"))
print(config.get("port", 31888))
print(config.get("accessToken", ""))
PY
)"

PORT="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '1p')"
TOKEN="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '2p')"
BASE_URL="http://127.0.0.1:$PORT"

AUTH_HEADER=()
if [[ -n "$TOKEN" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
fi

echo "Finance Node: $BASE_URL"
echo ""

echo "== Health =="
curl -sS "${AUTH_HEADER[@]}" "$BASE_URL/v1/health" | python3 -m json.tool
echo ""

echo "== This Month Summary =="
curl -sS "${AUTH_HEADER[@]}" "$BASE_URL/v1/summary/month" | python3 -m json.tool
echo ""

echo "== Recent Transactions =="
TRANSACTIONS_JSON="$(curl -sS "${AUTH_HEADER[@]}" "$BASE_URL/v1/transactions")"
python3 -c '
import json
import sys

items = json.loads(sys.argv[1])
if not items:
    print("No transactions.")
    raise SystemExit(0)

for item in items[:20]:
    occurred_at = item.get("occurredAt", "")
    title = item.get("title", "")
    amount = item.get("amount", 0)
    kind = item.get("kind", "")
    source = item.get("source", "")
    reimbursement = item.get("reimbursementStatus", "")
    print(f"{occurred_at} | {kind:<8} | {amount:>8.2f} | {source:<10} | {reimbursement:<14} | {title}")
' "$TRANSACTIONS_JSON"
