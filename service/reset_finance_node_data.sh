#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
DB_PATH="$RUNTIME_DIR/finance.sqlite3"
BACKUP_DIR="$RUNTIME_DIR/backups"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
BACKUP_PATH="$BACKUP_DIR/finance-$TIMESTAMP.sqlite3"

if [[ ! -f "$DB_PATH" ]]; then
  echo "Finance Node database not found: $DB_PATH"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_PATH"

sqlite3 "$DB_PATH" "DELETE FROM transactions;"

echo "Finance Node transactions cleared."
echo "Backup saved to: $BACKUP_PATH"
