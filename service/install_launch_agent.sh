#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LABEL="com.finance-node-openclaw"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$LABEL.plist"
UID_VALUE="$(id -u)"
SERVICE_APP="${FINANCE_NODE_INSTALL_DIR:-$ROOT_DIR}"
OUT_LOG="$SERVICE_APP/logs/finance-node.launchd.out.log"
ERR_LOG="$SERVICE_APP/logs/finance-node.launchd.err.log"

mkdir -p "$LAUNCH_AGENTS_DIR" "$SERVICE_APP/runtime" "$SERVICE_APP/logs"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$SERVICE_APP/launch_finance_node_foreground.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$SERVICE_APP</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
  <key>ProcessType</key>
  <string>Background</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$UID_VALUE" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID_VALUE" "$PLIST_PATH"
launchctl enable "gui/$UID_VALUE/$LABEL"
launchctl kickstart -k "gui/$UID_VALUE/$LABEL"

sleep 2

echo "LaunchAgent 已安装:"
echo "$PLIST_PATH"
echo "Service app path:"
echo "$SERVICE_APP"
echo ""
bash "$SERVICE_APP/status_launch_agent.sh"
