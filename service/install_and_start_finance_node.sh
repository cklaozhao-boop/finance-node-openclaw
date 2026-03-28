#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_PATH="$ROOT_DIR/runtime/finance-node.pid"
LOG_PATH="$ROOT_DIR/logs/finance-node.log"

"$ROOT_DIR/prepare_finance_node_runtime.sh" >/dev/null

if [[ -f "$PID_PATH" ]] && kill -0 "$(cat "$PID_PATH")" >/dev/null 2>&1; then
  echo "Finance Node is already running with PID $(cat "$PID_PATH")"
else
  rm -f "$PID_PATH"
  nohup python3 "$ROOT_DIR/finance_node_server.py" > "$LOG_PATH" 2>&1 &
  echo $! > "$PID_PATH"
  sleep 1

  if ! kill -0 "$(cat "$PID_PATH")" >/dev/null 2>&1; then
    echo "Finance Node failed to start. Recent log output:"
    tail -n 40 "$LOG_PATH" || true
    exit 1
  fi
fi

echo ""
cat "$ROOT_DIR/runtime/connection-info.txt"
echo ""
echo "OpenClaw 工具清单已生成:"
echo "$ROOT_DIR/runtime/openclaw_finance_tools.json"
