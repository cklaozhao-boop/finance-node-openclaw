#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.finance-node-openclaw"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
UID_VALUE="$(id -u)"
SERVICE_APP="${FINANCE_NODE_INSTALL_DIR:-$ROOT_DIR}"

if [[ -f "$PLIST_PATH" ]]; then
  echo "LaunchAgent plist:"
  echo "$PLIST_PATH"
else
  echo "LaunchAgent plist not found:"
  echo "$PLIST_PATH"
fi

echo ""
echo "launchctl status:"
launchctl print "gui/$UID_VALUE/$LABEL" 2>/dev/null || echo "Service not loaded."

echo ""
echo "port 31888:"
lsof -nP -iTCP:31888 -sTCP:LISTEN || echo "Port 31888 is not listening."

echo ""
echo "service app path:"
echo "$SERVICE_APP"

echo ""
echo "recent service logs:"
tail -n 20 "$SERVICE_APP/logs/finance-node.launchd.out.log" 2>/dev/null || true
tail -n 20 "$SERVICE_APP/logs/finance-node.launchd.err.log" 2>/dev/null || true
