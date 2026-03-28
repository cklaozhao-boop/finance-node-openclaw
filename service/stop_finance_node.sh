#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_PATH="$ROOT_DIR/runtime/finance-node.pid"

if [[ ! -f "$PID_PATH" ]]; then
  echo "Finance Node is not running."
  exit 0
fi

PID="$(cat "$PID_PATH")"
if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "Stopped Finance Node ($PID)"
else
  echo "Finance Node process not found."
fi

rm -f "$PID_PATH"
