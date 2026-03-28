#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
LOG_DIR="$ROOT_DIR/logs"
CONFIG_PATH="$RUNTIME_DIR/config.json"
DB_PATH="$RUNTIME_DIR/finance.sqlite3"
INFO_PATH="$RUNTIME_DIR/connection-info.txt"
TOOLS_OUTPUT_PATH="$RUNTIME_DIR/openclaw_finance_tools.json"
PORT="${FINANCE_NODE_PORT:-31888}"
HOST="${FINANCE_NODE_HOST:-0.0.0.0}"
NODE_NAME="${FINANCE_NODE_NAME:-Finance Node}"

mkdir -p "$RUNTIME_DIR" "$LOG_DIR"

TAILSCALE_HOSTNAME=""
TAILSCALE_IP=""
REMOTE_ACCESS="局域网"
TAILSCALE_BIN=""

for candidate in \
  "$(command -v tailscale 2>/dev/null || true)" \
  "/Applications/Tailscale.app/Contents/MacOS/Tailscale" \
  "/Applications/Tailscale.app/Contents/MacOS/tailscale" \
  "/opt/homebrew/bin/tailscale" \
  "/usr/local/bin/tailscale"
do
  if [[ -n "$candidate" ]] && [[ -x "$candidate" ]]; then
    TAILSCALE_BIN="$candidate"
    break
  fi
done

if [[ -n "$TAILSCALE_BIN" ]]; then
  TAILSCALE_IP="$("$TAILSCALE_BIN" ip -4 2>/dev/null | head -n 1 || true)"
  TAILSCALE_HOSTNAME="$("$TAILSCALE_BIN" status --json 2>/dev/null | python3 -c 'import json,sys
try:
    data = json.load(sys.stdin)
    self_info = data.get("Self", {})
    print((self_info.get("DNSName") or "").rstrip("."))
except Exception:
    print("")
')"
  if [[ -n "$TAILSCALE_IP" || -n "$TAILSCALE_HOSTNAME" ]]; then
    REMOTE_ACCESS="Tailscale"
  fi
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  ACCESS_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"

  cat > "$CONFIG_PATH" <<JSON
{
  "nodeName": "$NODE_NAME",
  "host": "$HOST",
  "port": $PORT,
  "accessToken": "$ACCESS_TOKEN",
  "remoteAccess": "$REMOTE_ACCESS",
  "tailscaleIP": "$TAILSCALE_IP",
  "tailscaleHostname": "$TAILSCALE_HOSTNAME",
  "lastIngestedAt": null
}
JSON
else
  python3 - <<PY
import json
from pathlib import Path

config_path = Path("$CONFIG_PATH")
config = json.loads(config_path.read_text(encoding="utf-8"))
config["remoteAccess"] = "$REMOTE_ACCESS"
config["tailscaleIP"] = "$TAILSCALE_IP"
config["tailscaleHostname"] = "$TAILSCALE_HOSTNAME"
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
fi

python3 - <<PY
import json
from pathlib import Path

root = Path("$ROOT_DIR")
runtime = Path("$RUNTIME_DIR")
config = json.loads(Path("$CONFIG_PATH").read_text(encoding="utf-8"))
port = config["port"]
token = config["accessToken"]
tailscale_host = config.get("tailscaleHostname") or config.get("tailscaleIP") or ""

if tailscale_host:
    public_url = f"http://{tailscale_host}:{port}"
else:
    public_url = f"http://127.0.0.1:{port}"

info = f"""Finance Node 连接信息

节点名称: {config['nodeName']}
数据库: {Path("$DB_PATH")}
本机地址: http://127.0.0.1:{port}
远程地址: {public_url}
账单网页: {public_url}/dashboard
Token: {token}
健康检查:
curl -H "Authorization: Bearer {token}" {public_url}/v1/health

iPhone App 建议填写:
- 节点名称: {config['nodeName']}
- Finance Server 地址: {public_url}
- Token: {token}

手机浏览器建议打开:
- 账单网页: {public_url}/dashboard
- 首次打开后输入上面的 Token
"""
Path("$INFO_PATH").write_text(info, encoding="utf-8")

template = (root / "openclaw" / "finance_http_tools.template.json").read_text(encoding="utf-8")
template = template.replace("__BASE_URL__", public_url).replace("__TOKEN__", token)
(runtime / "openclaw_finance_tools.json").write_text(template, encoding="utf-8")
PY

echo ""
cat "$INFO_PATH"
echo ""
echo "OpenClaw 工具清单已生成:"
echo "$TOOLS_OUTPUT_PATH"
