---
name: finance-node-bookkeeper
description: Use this skill when __AGENT_NAME__ needs to read or write bookkeeping data through the local Finance Node that powers the current web dashboard.
---

# Finance Node Bookkeeper

Use this skill whenever the user asks __AGENT_NAME__ to:

- 记一笔
- 查最近流水
- 看本月汇总
- 更新报销状态
- 验证财务节点是否可用

This skill auto-discovers the installed Finance Node runtime via the installer pointer file under:

- `${XDG_CONFIG_HOME:-~/.config}/finance-node-openclaw/install.json`

The helper CLI auto-loads:

- local node base URL for same-machine calls
- Tailscale hostname or IP
- bearer token

## Commands

Use these commands via the agent shell:

```bash
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py health
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py config
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py list
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py summary
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py add --title "午饭" --amount 32 --type expense --account-name "生活账户" --project-name "必要开销" --category-name "外卖饮食" --tag "节点测试"
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py reimburse --id <transaction-id> --status submitted
python3 skills/finance-node-bookkeeper/scripts/finance_node_cli.py --remote health
```

## Rules

- If the user is clearly asking to记账 and there is enough information to write, do not ask for confirmation unless a critical field is missing.
- Missing `amount` means do not write. Ask a follow-up instead.
- Default `type` to `expense` unless the user clearly describes income or transfer.
- If the user does not provide a specific time, default `occurredAt` to the current local time instead of `00:00`.
- Before writing, read the current node configuration and match against existing:
  - accounts
  - funding sources
  - projects
  - categories
- Treat them as four separate master-data sets:
  - 资金来源 = 桑基图第 1 层
  - 账户 = 桑基图第 2/3 层
  - 项目 = 桑基图第 4 层
  - 类别 = 桑基图第 5 层
- Always prefer the closest configured value instead of inventing a new one.
- Reuse the user's confirmed historical habits when possible:
  - same merchant/title -> reuse the last confirmed account/project/category/source mapping
  - same source phrase -> reuse the last confirmed funding source
  - same spending phrase -> reuse the last confirmed project + category pairing
- If the closest match is still ambiguous, ask follow-up questions until the mapping is stable instead of guessing.
- Always echo back the structured result after writing:
  - title
  - amount
  - type
  - account
  - project
  - category or funding source
  - reimbursementStatus
- On the same machine, prefer the default local mode.
- Only use `--remote` when testing the Tailscale address itself.
- When testing connectivity, prefer `health`, then `summary`, then one real `add`.
- Before matching fields for a real add, prefer `config` once in the same session.

## Default mappings

- category name default: `未分类`
- account default: `生活账户`
- source default: `openClaw`
- merchant default: same as title

## Validation flow

For a full node check:

1. `health`
2. `summary`
3. `add` one small tagged transaction
4. `list` and verify the tagged transaction appears

If any step fails, report the exact command and error.
