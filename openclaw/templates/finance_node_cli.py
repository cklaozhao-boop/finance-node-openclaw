#!/usr/bin/env python3
"""Finance Node helper CLI for a user-selected OpenClaw agent."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


CONFIG_POINTER = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "finance-node-openclaw" / "install.json"


def candidate_configs() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("FINANCE_NODE_CONFIG")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    if CONFIG_POINTER.exists():
        try:
            pointer = json.loads(CONFIG_POINTER.read_text(encoding="utf-8"))
            config_path = pointer.get("configPath")
            if config_path:
                candidates.append(Path(config_path).expanduser())
        except Exception:
            pass

    candidates.extend(
        [
            Path.home() / "Library" / "Application Support" / "finance-node-openclaw" / "app" / "runtime" / "config.json",
            Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "finance-node-openclaw" / "app" / "runtime" / "config.json",
            Path.cwd() / "runtime" / "config.json",
        ]
    )
    return candidates


def load_config():
    for path in candidate_configs():
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            host = data.get("host") or "127.0.0.1"
            port = data.get("port") or 31888
            if "baseUrl" not in data:
                local_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
                data["baseUrl"] = f"http://{local_host}:{port}"
            if "tailscaleUrl" not in data:
                tailscale_host = data.get("tailscaleHostname") or data.get("tailscaleIP")
                if tailscale_host:
                    data["tailscaleUrl"] = f"http://{tailscale_host}:{port}"
            if "token" not in data:
                data["token"] = data.get("accessToken")
            data["_config_path"] = str(path)
            return data
    tried = "\n".join(str(path) for path in candidate_configs())
    raise SystemExit(f"Missing Finance Node config. Tried:\n{tried}")


def ensure_slash(base_url: str) -> str:
    return base_url.rstrip("/")


def request_json(config, method: str, path: str, payload=None, remote=False):
    base_url = config.get("baseUrl") or "http://127.0.0.1:31888"
    remote_url = config.get("tailscaleUrl") or config.get("publicBaseUrl") or base_url
    target_base = remote_url if remote else base_url
    url = ensure_slash(target_base) + path

    data = None
    headers = {
        "Authorization": f"Bearer {config['token']}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {exc.reason} for {url}\n{details}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"URL error for {url}: {exc}") from exc


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def cmd_health(args):
    config = load_config()
    data = request_json(config, "GET", "/v1/health", remote=args.remote)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_list(args):
    config = load_config()
    params = {}
    if args.limit:
        params["limit"] = str(args.limit)
    if args.tag:
        params["tag"] = args.tag
    path = "/v1/transactions"
    if params:
        path += "?" + urllib.parse.urlencode(params)
    data = request_json(config, "GET", path, remote=args.remote)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_summary(args):
    config = load_config()
    path = "/v1/dashboard/overview"
    data = request_json(config, "GET", path, remote=args.remote)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_config(args):
    config = load_config()
    data = request_json(config, "GET", "/v1/configuration", remote=args.remote)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_add(args):
    config = load_config()
    occurred_at = args.occurred_at or now_iso()
    payload = {
        "title": args.title,
        "amount": float(args.amount),
        "kind": args.type,
        "accountName": args.account_name or "生活账户",
        "fromAccountName": args.from_account_name,
        "toAccountName": args.to_account_name,
        "projectName": args.project_name,
        "sourceName": args.source_name,
        "merchant": args.merchant or args.title,
        "note": args.note or "",
        "occurredAt": occurred_at,
        "tags": args.tags or [],
        "source": "openClaw",
        "category": {
            "id": args.category_id or args.category_name or "未分类",
            "name": args.category_name or "未分类",
        },
        "reimbursementStatus": args.reimbursement_status or "draft",
    }
    data = request_json(config, "POST", "/v1/transactions", payload=payload, remote=args.remote)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_reimburse(args):
    config = load_config()
    payload = {"status": args.status}
    path = f"/v1/transactions/{args.id}/reimbursement"
    data = request_json(config, "PATCH", path, payload=payload, remote=args.remote)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Finance Node helper CLI for OpenClaw.")
    parser.add_argument("--remote", action="store_true", help="Use the Tailscale URL instead of local baseUrl.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Check Finance Node health.")
    health.set_defaults(func=cmd_health)

    list_parser = subparsers.add_parser("list", help="List recent transactions.")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--tag")
    list_parser.set_defaults(func=cmd_list)

    summary = subparsers.add_parser("summary", help="Read dashboard overview.")
    summary.set_defaults(func=cmd_summary)

    config_parser = subparsers.add_parser("config", help="Read current accounts, sources, projects and categories.")
    config_parser.set_defaults(func=cmd_config)

    add = subparsers.add_parser("add", help="Add one transaction.")
    add.add_argument("--title", required=True)
    add.add_argument("--amount", required=True, type=float)
    add.add_argument("--type", choices=["expense", "income", "transfer"], default="expense")
    add.add_argument("--account-name")
    add.add_argument("--from-account-name")
    add.add_argument("--to-account-name")
    add.add_argument("--project-name")
    add.add_argument("--source-name")
    add.add_argument("--merchant")
    add.add_argument("--note")
    add.add_argument("--occurred-at")
    add.add_argument("--category-id")
    add.add_argument("--category-name")
    add.add_argument("--reimbursement-status", choices=["draft", "submitted", "received"])
    add.add_argument("--tag", dest="tags", action="append")
    add.set_defaults(func=cmd_add)

    reimburse = subparsers.add_parser("reimburse", help="Update reimbursement status.")
    reimburse.add_argument("--id", required=True)
    reimburse.add_argument("--status", required=True, choices=["draft", "submitted", "received"])
    reimburse.set_defaults(func=cmd_reimburse)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
