#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_PATH="$ROOT_DIR/runtime/finance-node.pid"
CONFIG_PATH="$ROOT_DIR/runtime/config.json"

if [[ -f "$CONFIG_PATH" ]]; then
  echo "Config:"
  cat "$CONFIG_PATH"
  echo ""
else
  echo "No config generated yet."
fi

if [[ -f "$PID_PATH" ]] && kill -0 "$(cat "$PID_PATH")" >/dev/null 2>&1; then
  echo "Finance Node is running with PID $(cat "$PID_PATH")"
else
  LISTENING_PID="$(lsof -tiTCP:31888 -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -n "$LISTENING_PID" ]]; then
    echo "Finance Node is listening on port 31888 with PID $LISTENING_PID (PID file may be stale)."
  else
    echo "Finance Node is not running."
  fi
fi
