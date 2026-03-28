#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_PATH="$ROOT_DIR/runtime/finance-node.pid"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

mkdir -p "$ROOT_DIR/runtime" "$ROOT_DIR/logs"

cleanup() {
  rm -f "$PID_PATH"
}

trap cleanup EXIT INT TERM

"$ROOT_DIR/prepare_finance_node_runtime.sh"
echo $$ > "$PID_PATH"

cd "$ROOT_DIR"
"$PYTHON_BIN" "$ROOT_DIR/finance_node_server.py"
