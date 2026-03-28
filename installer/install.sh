#!/usr/bin/env bash
set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-cklaozhao-boop/finance-node-openclaw}"
GITHUB_REF="${GITHUB_REF:-main}"
SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
BOOTSTRAP_TMP_DIR=""

bootstrap_from_github() {
  local tmp_dir archive_url extracted_dir
  if ! command -v curl >/dev/null 2>&1; then
    echo "Missing required command: curl" >&2
    exit 1
  fi
  if ! command -v tar >/dev/null 2>&1; then
    echo "Missing required command: tar" >&2
    exit 1
  fi

  tmp_dir="$(mktemp -d)"
  BOOTSTRAP_TMP_DIR="$tmp_dir"
  trap 'rm -rf "$BOOTSTRAP_TMP_DIR"' EXIT
  archive_url="https://codeload.github.com/${GITHUB_REPO}/tar.gz/${GITHUB_REF}"

  curl -fsSL "$archive_url" -o "$tmp_dir/repo.tar.gz"
  tar -xzf "$tmp_dir/repo.tar.gz" -C "$tmp_dir"
  extracted_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

  if [[ -z "$extracted_dir" ]] || [[ ! -f "$extracted_dir/installer/install.sh" ]]; then
    echo "Failed to bootstrap installer from ${archive_url}" >&2
    exit 1
  fi

  bash "$extracted_dir/installer/install.sh" "$@"
  trap - EXIT
  rm -rf "$BOOTSTRAP_TMP_DIR"
}

if [[ -z "$SCRIPT_SOURCE" ]] || [[ "$SCRIPT_SOURCE" == "bash" ]] || [[ "$SCRIPT_SOURCE" == "-bash" ]]; then
  bootstrap_from_github "$@"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_SRC="$REPO_ROOT/service"

if [[ ! -d "$SERVICE_SRC" ]]; then
  bootstrap_from_github "$@"
  exit 0
fi

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
APP_CONFIG_DIR="$CONFIG_HOME/finance-node-openclaw"
INSTALL_INFO_PATH="$APP_CONFIG_DIR/install.json"

detect_platform() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux) echo "linux" ;;
    *)
      echo "Unsupported platform: $(uname -s)" >&2
      exit 1
      ;;
  esac
}

platform="$(detect_platform)"
SKIP_AUTOSTART="${FINANCE_NODE_SKIP_AUTOSTART:-0}"

if [[ -n "${FINANCE_NODE_INSTALL_ROOT:-}" ]]; then
  INSTALL_ROOT="$FINANCE_NODE_INSTALL_ROOT"
elif [[ "$platform" == "macos" ]]; then
  INSTALL_ROOT="$HOME/Library/Application Support/finance-node-openclaw"
else
  INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/finance-node-openclaw"
fi

APP_DIR="$INSTALL_ROOT/app"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd python3
require_cmd rsync

mkdir -p "$APP_DIR" "$APP_CONFIG_DIR"

rsync -a --delete \
  --exclude 'runtime' \
  --exclude 'logs' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  "$SERVICE_SRC/" "$APP_DIR/"

mkdir -p "$APP_DIR/runtime" "$APP_DIR/logs"

python3 - <<PY
import json
from pathlib import Path

install_info = {
    "platform": "$platform",
    "installRoot": "$INSTALL_ROOT",
    "appDir": "$APP_DIR",
    "configPath": "$APP_DIR/runtime/config.json",
}
path = Path("$INSTALL_INFO_PATH")
path.write_text(json.dumps(install_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

export FINANCE_NODE_INSTALL_DIR="$APP_DIR"
export FINANCE_NODE_CONFIG_POINTER="$INSTALL_INFO_PATH"

if [[ "$SKIP_AUTOSTART" == "1" ]]; then
  bash "$APP_DIR/prepare_finance_node_runtime.sh" >/dev/null
elif [[ "$platform" == "macos" ]]; then
  bash "$APP_DIR/install_launch_agent.sh"
else
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  UNIT_PATH="$UNIT_DIR/finance-node-openclaw.service"
  mkdir -p "$UNIT_DIR"

  cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Finance Node OpenClaw
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=/bin/bash $APP_DIR/launch_finance_node_foreground.sh
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
UNIT

  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now finance-node-openclaw.service
  else
    echo "systemctl not found, falling back to background mode."
    bash "$APP_DIR/install_and_start_finance_node.sh"
  fi
fi

echo ""
echo "Install pointer:"
echo "$INSTALL_INFO_PATH"
echo ""
if [[ -f "$APP_DIR/runtime/connection-info.txt" ]]; then
  cat "$APP_DIR/runtime/connection-info.txt"
else
  echo "Connection info file not found yet:"
  echo "$APP_DIR/runtime/connection-info.txt"
fi
