#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
CONFIG_PATH="$RUNTIME_DIR/config.json"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Missing config: $CONFIG_PATH" >&2
  exit 1
fi

read -r BASE_URL TOKEN <<EOF
$(python3 - <<PY
import json
from pathlib import Path

config = json.loads(Path("$CONFIG_PATH").read_text(encoding="utf-8"))
port = config.get("port", 31888)
token = config.get("accessToken", "")
print(f"http://127.0.0.1:{port} {token}")
PY
)
EOF

AUTH_HEADER="Authorization: Bearer $TOKEN"
NOW_ISO="$(python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat())
PY
)"
UNIQUE_TAG="node-test-$(date +%s)"
PAYLOAD="$(python3 - <<PY
import json
from datetime import datetime, timezone

payload = {
    "title": "节点完整性测试",
    "amount": 12.34,
    "type": "expense",
    "occurredAt": "$NOW_ISO",
    "category": {
        "id": "finance-node-test",
        "name": "测试",
        "systemImage": "checkmark.seal",
        "tintHex": "#2E7D32",
        "keywords": ["测试", "节点"],
    },
    "tags": ["$UNIQUE_TAG"],
    "accountName": "测试账户",
    "merchant": "节点完整性测试",
    "note": "由 test_finance_node.sh 自动写入",
    "reimbursementStatus": "draft",
    "source": "openClaw",
}
print(json.dumps(payload, ensure_ascii=False))
PY
)"

echo "== Health =="
curl -fsS -H "$AUTH_HEADER" "$BASE_URL/v1/health"
echo ""
echo ""

echo "== Create Transaction =="
CREATE_RESPONSE="$(curl -fsS \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$BASE_URL/v1/transactions")"
echo "$CREATE_RESPONSE"
TRANSACTION_ID="$(printf '%s' "$CREATE_RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
echo ""
echo ""

echo "== Update Reimbursement =="
curl -fsS \
  -X PATCH \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"status":"submitted"}' \
  "$BASE_URL/v1/transactions/$TRANSACTION_ID/reimbursement"
echo ""
echo ""

echo "== Month Summary =="
curl -fsS -H "$AUTH_HEADER" "$BASE_URL/v1/summary/month"
echo ""
echo ""

echo "== Filtered Transactions =="
curl -fsS -H "$AUTH_HEADER" "$BASE_URL/v1/transactions?tag=$UNIQUE_TAG"
echo ""
echo ""
echo "Finance Node test passed."
