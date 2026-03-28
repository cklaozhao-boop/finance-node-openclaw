#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LABEL="com.finance-node-openclaw"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$LABEL.plist"
UID_VALUE="$(id -u)"
SERVICE_APP="${FINANCE_NODE_INSTALL_DIR:-$ROOT_DIR}"

launchctl bootout "gui/$UID_VALUE" "$PLIST_PATH" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"
rm -f "$ROOT_DIR/runtime/finance-node.pid"

echo "LaunchAgent 已卸载:"
echo "$PLIST_PATH"
echo "Service files preserved at:"
echo "$SERVICE_APP"
