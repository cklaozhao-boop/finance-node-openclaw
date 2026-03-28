#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_ROOT="$REPO_ROOT/openclaw/templates"

AGENT_NAME=""
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)
      AGENT_NAME="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$AGENT_NAME" ]]; then
  echo "Usage: ./installer/install-openclaw.sh --agent <agent-name>" >&2
  exit 1
fi

WORKSPACE_DIR="$OPENCLAW_HOME/workspace-$AGENT_NAME"
SKILL_DIR="$WORKSPACE_DIR/skills/finance-node-bookkeeper"
SCRIPT_DIR_OUT="$SKILL_DIR/scripts"
DOCS_DIR="$WORKSPACE_DIR/docs"

mkdir -p "$SCRIPT_DIR_OUT" "$DOCS_DIR"

install -m 755 "$TEMPLATE_ROOT/finance_node_cli.py" "$SCRIPT_DIR_OUT/finance_node_cli.py"

python3 - <<PY
from pathlib import Path

agent_name = "$AGENT_NAME"
skill_template = Path("$TEMPLATE_ROOT/SKILL.md").read_text(encoding="utf-8")
guide_template = Path("$TEMPLATE_ROOT/agent-bookkeeping-guide.md").read_text(encoding="utf-8")

skill_text = skill_template.replace("__AGENT_NAME__", agent_name)
guide_text = guide_template.replace("__AGENT_NAME__", agent_name)

Path("$SKILL_DIR/SKILL.md").write_text(skill_text, encoding="utf-8")
Path("$DOCS_DIR/finance-node-bookkeeping-guide.md").write_text(guide_text, encoding="utf-8")
PY

echo "OpenClaw binding installed."
echo "Agent workspace:"
echo "$WORKSPACE_DIR"
echo ""
echo "Skill:"
echo "$SKILL_DIR/SKILL.md"
echo ""
echo "CLI:"
echo "$SCRIPT_DIR_OUT/finance_node_cli.py"
echo ""
echo "Guide:"
echo "$DOCS_DIR/finance-node-bookkeeping-guide.md"
