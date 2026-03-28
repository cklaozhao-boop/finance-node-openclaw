#!/usr/bin/env python3
from collections import defaultdict
import gzip
import json
import mimetypes
import os
import sqlite3
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Union
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

mimetypes.add_type("application/manifest+json", ".webmanifest")

ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "runtime"
CONFIG_PATH = RUNTIME_DIR / "config.json"
DB_PATH = RUNTIME_DIR / "finance.sqlite3"
WEB_DIR = ROOT / "web"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_iso8601(value: Optional[str], fallback: Optional[str] = None) -> str:
    if not value:
        return fallback or utc_now_iso()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return fallback or utc_now_iso()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Missing config file: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def default_categories() -> list:
    return [
        {
            "id": "category-food",
            "name": "餐饮",
            "systemImage": "fork.knife",
            "tintHex": "#FF8C42",
            "keywords": ["饭", "午饭", "晚饭", "咖啡", "奶茶", "早餐", "餐", "火锅"],
        },
        {
            "id": "category-transport",
            "name": "交通",
            "systemImage": "tram.fill",
            "tintHex": "#4F7CFF",
            "keywords": ["打车", "地铁", "高铁", "机票", "机场", "滴滴", "车费"],
        },
        {
            "id": "category-housing",
            "name": "住房",
            "systemImage": "house.fill",
            "tintHex": "#6F5BD3",
            "keywords": ["房租", "物业", "水电", "酒店", "住宿"],
        },
        {
            "id": "category-shopping",
            "name": "购物",
            "systemImage": "bag.fill",
            "tintHex": "#E64980",
            "keywords": ["购物", "淘宝", "衣服", "鞋", "日用", "京东"],
        },
        {
            "id": "category-office",
            "name": "办公",
            "systemImage": "briefcase.fill",
            "tintHex": "#009688",
            "keywords": ["办公", "文具", "打印", "耗材", "客户", "招待"],
        },
        {
            "id": "category-entertainment",
            "name": "娱乐",
            "systemImage": "gamecontroller.fill",
            "tintHex": "#F06543",
            "keywords": ["电影", "游戏", "聚餐", "娱乐", "门票"],
        },
        {
            "id": "category-health",
            "name": "医疗",
            "systemImage": "cross.case.fill",
            "tintHex": "#FF5D73",
            "keywords": ["医院", "药", "体检", "挂号"],
        },
        {
            "id": "category-income",
            "name": "收入",
            "systemImage": "banknote.fill",
            "tintHex": "#2F9E44",
            "keywords": ["工资", "收入", "奖金", "报销到账", "收款"],
        },
        {
            "id": "category-transfer",
            "name": "转账",
            "systemImage": "arrow.left.arrow.right.square.fill",
            "tintHex": "#546E7A",
            "keywords": ["转账", "转入", "转出"],
        },
    ]


def default_accounts() -> list:
    return [
        {
            "id": "account-wechat",
            "name": "微信支付",
            "type": "digitalWallet",
            "currency": "CNY",
            "openingBalance": 0.0,
            "brand": "wechat",
            "tintHex": "#07C160",
            "symbolName": "message.fill",
            "keywords": ["微信", "wechat"],
        },
        {
            "id": "account-alipay",
            "name": "支付宝",
            "type": "digitalWallet",
            "currency": "CNY",
            "openingBalance": 0.0,
            "brand": "alipay",
            "tintHex": "#1677FF",
            "symbolName": "qrcode",
            "keywords": ["支付宝", "alipay"],
        },
        {
            "id": "account-cmb",
            "name": "招商银行卡",
            "type": "debitCard",
            "currency": "CNY",
            "openingBalance": 0.0,
            "brand": "cmb",
            "tintHex": "#D81E06",
            "symbolName": "building.columns.fill",
            "keywords": ["招行", "招商", "银行卡"],
        },
        {
            "id": "account-credit-card",
            "name": "信用卡",
            "type": "creditCard",
            "currency": "CNY",
            "openingBalance": 0.0,
            "brand": "unionpay",
            "tintHex": "#3F51B5",
            "symbolName": "creditcard.fill",
            "keywords": ["信用卡"],
        },
    ]


def default_ledger_settings() -> dict:
    return {
        "bookMode": "personalAssistant",
        "defaultCurrency": "CNY",
        "timezone": "Asia/Shanghai",
        "allowManualEntry": True,
    }


def ensure_schema() -> None:
    connection = connect_db()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                kind TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                category_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                account_name TEXT NOT NULL,
                from_account_name TEXT,
                to_account_name TEXT,
                merchant TEXT NOT NULL,
                note TEXT NOT NULL,
                reimbursement_status TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ledger_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        ensure_column(connection, "transactions", "from_account_name", "TEXT")
        ensure_column(connection, "transactions", "to_account_name", "TEXT")
        connection.commit()
    finally:
        connection.close()


def ensure_column(connection: sqlite3.Connection, table: str, column_name: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}")


def seed_default_master_data() -> None:
    connection = connect_db()
    try:
        now = utc_now_iso()
        category_count = connection.execute("SELECT COUNT(*) AS count FROM categories").fetchone()["count"]
        if category_count == 0:
            connection.executemany(
                """
                INSERT INTO categories (id, payload_json, sort_order, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        item["id"],
                        json.dumps(item, ensure_ascii=False),
                        index,
                        now,
                    )
                    for index, item in enumerate(default_categories())
                ],
            )

        account_count = connection.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()["count"]
        if account_count == 0:
            connection.executemany(
                """
                INSERT INTO accounts (id, payload_json, sort_order, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        item["id"],
                        json.dumps(item, ensure_ascii=False),
                        index,
                        now,
                    )
                    for index, item in enumerate(default_accounts())
                ],
            )

        settings_count = connection.execute("SELECT COUNT(*) AS count FROM ledger_settings").fetchone()["count"]
        if settings_count == 0:
            connection.execute(
                """
                INSERT INTO ledger_settings (id, payload_json, updated_at)
                VALUES (1, ?, ?)
                """,
                (
                    json.dumps(default_ledger_settings(), ensure_ascii=False),
                    now,
                ),
            )
        connection.commit()
    finally:
        connection.close()


def list_categories(connection: sqlite3.Connection) -> list:
    rows = connection.execute(
        """
        SELECT payload_json
        FROM categories
        ORDER BY sort_order ASC, id ASC
        """
    ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def current_balance_for_account(connection: sqlite3.Connection, account_name: str, opening_balance: float) -> float:
    rows = connection.execute(
        """
        SELECT kind, amount, account_name, from_account_name, to_account_name
        FROM transactions
        WHERE account_name = ? OR from_account_name = ? OR to_account_name = ?
        """,
        (account_name, account_name, account_name),
    ).fetchall()
    delta = 0.0
    for row in rows:
        from_account_name, to_account_name = normalized_account_pair(row)
        amount = float(row["amount"] or 0)
        if row["kind"] == "income":
            if to_account_name == account_name:
                delta += amount
        elif row["kind"] == "expense":
            if from_account_name == account_name:
                delta -= amount
        elif row["kind"] == "transfer":
            if from_account_name == account_name:
                delta -= amount
            if to_account_name == account_name:
                delta += amount
    return opening_balance + delta


def list_accounts(connection: sqlite3.Connection) -> list:
    rows = connection.execute(
        """
        SELECT payload_json
        FROM accounts
        ORDER BY sort_order ASC, id ASC
        """
    ).fetchall()
    items = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        opening_balance = float(payload.get("openingBalance", 0.0))
        payload["currentBalance"] = current_balance_for_account(
            connection,
            payload.get("name", ""),
            opening_balance,
        )
        items.append(payload)
    return items


def load_ledger_settings(connection: sqlite3.Connection) -> dict:
    row = connection.execute(
        """
        SELECT payload_json
        FROM ledger_settings
        WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return default_ledger_settings()
    return json.loads(row["payload_json"])


def load_configuration_payload() -> dict:
    connection = connect_db()
    try:
        return {
            "categories": list_categories(connection),
            "accounts": list_accounts(connection),
            "settings": load_ledger_settings(connection),
        }
    finally:
        connection.close()


def row_to_transaction(row: sqlite3.Row) -> dict:
    from_account_name, to_account_name = normalized_account_pair(row)
    return {
        "id": row["id"],
        "title": row["title"],
        "amount": row["amount"],
        "kind": row["kind"],
        "occurredAt": row["occurred_at"],
        "category": json.loads(row["category_json"]),
        "tags": json.loads(row["tags_json"]),
        "accountName": row["account_name"],
        "fromAccountName": from_account_name,
        "toAccountName": to_account_name,
        "merchant": row["merchant"],
        "note": row["note"],
        "reimbursementStatus": row["reimbursement_status"],
        "source": row["source"],
    }


def dict_to_transaction(row: dict) -> dict:
    from_account_name, to_account_name = normalized_account_pair(row)
    return {
        "id": row["id"],
        "title": row["title"],
        "amount": row["amount"],
        "kind": row["kind"],
        "occurredAt": row["occurred_at"],
        "category": json.loads(row["category_json"]),
        "tags": json.loads(row["tags_json"]),
        "accountName": row["account_name"],
        "fromAccountName": from_account_name,
        "toAccountName": to_account_name,
        "merchant": row["merchant"],
        "note": row["note"],
        "reimbursementStatus": row["reimbursement_status"],
        "source": row["source"],
    }


def normalized_account_pair(row: Union[sqlite3.Row, dict]) -> tuple[Optional[str], Optional[str]]:
    kind = row["kind"]
    account_name = row.get("account_name") if isinstance(row, dict) else row["account_name"]
    from_account_name = row.get("from_account_name") if isinstance(row, dict) else row["from_account_name"]
    to_account_name = row.get("to_account_name") if isinstance(row, dict) else row["to_account_name"]

    if kind == "income":
        return (from_account_name, to_account_name or account_name)
    if kind == "expense":
        return (from_account_name or account_name, to_account_name)
    if kind == "transfer":
        return (from_account_name or account_name, to_account_name)
    return (from_account_name, to_account_name or account_name)


def parse_transaction_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now().astimezone()


def month_key_from_value(value: str) -> str:
    return value[:7]


def month_label_from_key(month_key: str) -> str:
    year, month = month_key.split("-")
    return f"{year[2:]}/{month}"


def format_currency(value: float) -> str:
    rounded = round(float(value or 0))
    return f"¥{rounded:,.0f}"


def month_keys_for_range(count: int) -> list[str]:
    cursor = datetime.now().astimezone().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    keys = []
    for _ in range(count):
        keys.append(f"{cursor.year:04d}-{cursor.month:02d}")
        if cursor.month == 1:
            cursor = cursor.replace(year=cursor.year - 1, month=12)
        else:
            cursor = cursor.replace(month=cursor.month - 1)
    keys.reverse()
    return keys


def category_group_name(transaction: dict) -> str:
    category_name = (transaction.get("category") or {}).get("name") or "未分类"
    tags = transaction.get("tags") or []
    reimbursement = transaction.get("reimbursementStatus")

    if reimbursement in {"draft", "submitted", "reimbursed"} or any(tag in {"出差", "客户", "办公", "公司"} for tag in tags):
        return "经营支出"
    if category_name in {"住房", "交通"}:
        return "固定成本"
    return "个人支出"


def group_color_map() -> dict:
    return {
        "经营支出": {
            "group": "#3B82F6",
            "children": ["#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"],
        },
        "固定成本": {
            "group": "#10B981",
            "children": ["#34D399", "#6EE7B7", "#A7F3D0", "#D1FAE5"],
        },
        "个人支出": {
            "group": "#F59E0B",
            "children": ["#FBBF24", "#FCD34D", "#FDE68A", "#FEF3C7"],
        },
    }


def metric_change(current: float, previous: float, suffix: str = "%") -> tuple[str, str]:
    if previous == 0:
        if current == 0:
            return ("0.0" + suffix, "up")
        return ("100.0" + suffix, "up")
    delta = ((current - previous) / abs(previous)) * 100
    trend = "up" if delta >= 0 else "down"
    return (f"{delta:+.1f}{suffix}", trend)


def runway_change(current: float, previous: float) -> tuple[str, str]:
    delta = current - previous
    trend = "up" if delta >= 0 else "down"
    return (f"{delta:+.1f}", trend)


def account_bar_color(tint_hex: Optional[str], index: int) -> str:
    palette = [
        "#3B82F6",
        "#60A5FA",
        "#4F46E5",
        "#0EA5E9",
        "#64748B",
        "#22C55E",
    ]
    if tint_hex:
        return tint_hex
    return palette[index % len(palette)]


def current_balance_from_transactions(transactions: list[dict], account_name: str, opening_balance: float = 0.0) -> float:
    delta = opening_balance
    for transaction in transactions:
        amount = float(transaction.get("amount") or 0)
        if transaction.get("kind") == "income":
            if (transaction.get("toAccountName") or transaction.get("accountName")) == account_name:
                delta += amount
        elif transaction.get("kind") == "expense":
            if (transaction.get("fromAccountName") or transaction.get("accountName")) == account_name:
                delta -= amount
        elif transaction.get("kind") == "transfer":
            if (transaction.get("fromAccountName") or transaction.get("accountName")) == account_name:
                delta -= amount
            if transaction.get("toAccountName") == account_name:
                delta += amount
    return delta


def build_dashboard_overview(server_config: dict) -> dict:
    connection = connect_db()
    try:
        transactions = [
            row_to_transaction(row)
            for row in connection.execute(
                """
                SELECT *
                FROM transactions
                ORDER BY occurred_at DESC, created_at DESC
                """
            ).fetchall()
        ]
        configuration = {
            "categories": list_categories(connection),
            "accounts": list_accounts(connection),
            "settings": load_ledger_settings(connection),
        }
    finally:
        connection.close()

    month_keys = month_keys_for_range(12)
    current_month_key = month_keys[-1]
    month_summary = {
        key: {"income": 0.0, "expense": 0.0}
        for key in month_keys
    }
    expense_children_by_group = defaultdict(lambda: defaultdict(float))
    income_links = defaultdict(float)
    expense_links = defaultdict(float)
    transfer_links = defaultdict(float)
    roi_groups = defaultdict(lambda: {"cost": 0.0, "revenue": 0.0})
    categories_from_transactions = set()
    transaction_accounts = set()

    for transaction in transactions:
        transaction_type = transaction["kind"]
        amount = float(transaction.get("amount") or 0)
        month_key = month_key_from_value(transaction["occurredAt"])
        category_name = (transaction.get("category") or {}).get("name") or "未分类"
        categories_from_transactions.add(category_name)
        if transaction.get("accountName"):
            transaction_accounts.add(transaction["accountName"])
        if transaction.get("fromAccountName"):
            transaction_accounts.add(transaction["fromAccountName"])
        if transaction.get("toAccountName"):
            transaction_accounts.add(transaction["toAccountName"])
        from_account_name = transaction.get("fromAccountName")
        to_account_name = transaction.get("toAccountName")

        if month_key in month_summary:
            if transaction_type == "income":
                month_summary[month_key]["income"] += amount
            elif transaction_type == "expense":
                month_summary[month_key]["expense"] += amount

        group_label = (transaction.get("tags") or [category_name])[0] if (transaction.get("tags") or []) else category_name
        if transaction_type == "income":
            roi_groups[group_label]["revenue"] += amount
            if month_key == current_month_key:
                source_node_label = transaction.get("merchant") or transaction.get("title") or "收入"
                target_label = to_account_name or transaction.get("accountName") or "未命名账户"
                income_links[(source_node_label, target_label)] += amount
        elif transaction_type == "expense":
            roi_groups[group_label]["cost"] += amount
            if month_key == current_month_key:
                group_name = category_group_name(transaction)
                expense_children_by_group[group_name][category_name] += amount
                source_node_label = from_account_name or transaction.get("accountName") or "未命名账户"
                expense_links[(source_node_label, category_name)] += amount
        elif transaction_type == "transfer":
            if month_key == current_month_key:
                source_node_label = from_account_name or transaction.get("accountName") or "转出账户"
                target_label = to_account_name or transaction.get("merchant") or transaction.get("note") or "其他账户"
                transfer_links[(source_node_label, target_label)] += amount

    previous_month_key = month_keys[-2] if len(month_keys) > 1 else current_month_key
    current_income = month_summary[current_month_key]["income"]
    current_expense = month_summary[current_month_key]["expense"]
    previous_income = month_summary[previous_month_key]["income"]
    previous_expense = month_summary[previous_month_key]["expense"]
    current_profit = current_income - current_expense
    previous_profit = previous_income - previous_expense

    account_lookup = {
        account["name"]: dict(account)
        for account in configuration["accounts"]
        if account.get("name")
    }

    for account_name in sorted(name for name in transaction_accounts if name and name not in account_lookup):
        account_lookup[account_name] = {
            "id": f"derived-{account_name}",
            "name": account_name,
            "type": "other",
            "currency": configuration["settings"].get("defaultCurrency", "CNY"),
            "openingBalance": 0.0,
            "currentBalance": current_balance_from_transactions(transactions, account_name, 0.0),
            "tintHex": None,
            "keywords": [],
        }

    accounts = []
    total_assets = 0.0
    balance_values = []
    sorted_account_items = sorted(
        account_lookup.values(),
        key=lambda item: float(item.get("currentBalance") or item.get("openingBalance") or 0),
        reverse=True,
    )
    for index, account in enumerate(sorted_account_items):
        balance = float(account.get("currentBalance") or account.get("openingBalance") or 0)
        total_assets += balance
        balance_values.append(balance)
        accounts.append(
            {
                "name": account.get("name") or "未命名账户",
                "amount": round(balance, 2),
                "color": account_bar_color(account.get("tintHex"), index),
            }
        )

    average_recent_expense = (
        sum(month_summary[key]["expense"] for key in month_keys[-6:]) / max(len(month_keys[-6:]), 1)
    )
    current_runway = total_assets / average_recent_expense if average_recent_expense else 0.0
    previous_expense_window = month_keys[-7:-1] if len(month_keys) >= 7 else month_keys[:-1]
    previous_average_expense = (
        sum(month_summary[key]["expense"] for key in previous_expense_window) / max(len(previous_expense_window), 1)
        if previous_expense_window
        else average_recent_expense
    )
    previous_runway = total_assets / previous_average_expense if previous_average_expense else current_runway
    opex_rate = (current_expense / current_income) * 100 if current_income else 0.0
    previous_opex_rate = (previous_expense / previous_income) * 100 if previous_income else opex_rate

    cashflow_change, cashflow_trend = metric_change(current_income + current_profit, previous_income + previous_profit)
    profit_change, profit_trend = metric_change(current_profit, previous_profit)
    opex_change, opex_trend = metric_change(opex_rate, previous_opex_rate)
    runway_delta, runway_trend = runway_change(current_runway, previous_runway)

    colors = group_color_map()
    sunburst_data = []
    for group_name in ["经营支出", "固定成本", "个人支出"]:
        children = expense_children_by_group.get(group_name, {})
        if not children:
            continue
        palette = colors[group_name]["children"]
        sunburst_data.append(
            {
                "name": group_name,
                "itemStyle": {"color": colors[group_name]["group"]},
                "children": [
                    {
                        "name": category_name,
                        "value": round(amount, 2),
                        "itemStyle": {"color": palette[index % len(palette)]},
                    }
                    for index, (category_name, amount) in enumerate(
                        sorted(children.items(), key=lambda item: item[1], reverse=True)
                    )
                ],
            }
        )

    roi_candidates = sorted(
        roi_groups.items(),
        key=lambda item: item[1]["cost"] + item[1]["revenue"],
        reverse=True,
    )[:5]
    roi_data = {
        "projects": [item[0] for item in roi_candidates] or ["暂无数据"],
        "cost": [round(item[1]["cost"], 2) for item in roi_candidates] or [0],
        "revenue": [round(item[1]["revenue"], 2) for item in roi_candidates] or [0],
    }

    sankey_nodes = []
    seen_nodes = set()
    for source, target in list(income_links.keys()) + list(expense_links.keys()) + list(transfer_links.keys()):
        if source and source not in seen_nodes:
            sankey_nodes.append({"name": source, "itemStyle": {"color": "#10B981" if source not in account_lookup else "#3B82F6"}})
            seen_nodes.add(source)
        if target and target not in seen_nodes:
            color = "#EF4444"
            if target in account_lookup:
                color = "#3B82F6"
            sankey_nodes.append({"name": target, "itemStyle": {"color": color}})
            seen_nodes.add(target)

    sankey_links = [
        {"source": source, "target": target, "value": round(value, 2)}
        for mapping in (income_links, transfer_links, expense_links)
        for (source, target), value in mapping.items()
        if source and target and value > 0
    ]

    categories = sorted(
        {category.get("name") for category in configuration["categories"] if category.get("name")} | categories_from_transactions
    )

    ui_transactions = []
    for transaction in transactions:
        transaction_type = transaction["kind"]
        from_account_name = transaction.get("fromAccountName")
        to_account_name = transaction.get("toAccountName")
        merchant = transaction.get("merchant") or transaction.get("title") or ""
        category_name = (transaction.get("category") or {}).get("name") or ""
        primary_tag = (transaction.get("tags") or [None])[0]

        if transaction_type == "income":
            from_label = merchant
            to_label = to_account_name or transaction.get("accountName") or "未命名账户"
            type_title = "收入"
        elif transaction_type == "expense":
            from_label = from_account_name or transaction.get("accountName") or "未命名账户"
            to_label = merchant or category_name or "支出"
            type_title = "支出"
        else:
            from_label = from_account_name or transaction.get("accountName") or "转出账户"
            to_label = to_account_name or merchant or transaction.get("note") or "转入账户"
            type_title = "转账"

        note_parts = [part for part in [transaction.get("note"), source_label(transaction), reimbursement_note(transaction)] if part]
        ui_transactions.append(
            {
                "id": transaction["id"],
                "date": transaction["occurredAt"][:10],
                "type": type_title,
                "amount": round(float(transaction.get("amount") or 0), 2) * (-1 if transaction_type == "expense" else 1),
                "from": from_label,
                "to": to_label,
                "note": " · ".join(dict.fromkeys(note_parts)),
                "category": category_name or None,
                "project": primary_tag,
                "tags": transaction.get("tags") or [],
                "accountName": transaction.get("accountName"),
                "merchant": merchant,
                "reimbursementStatus": transaction.get("reimbursementStatus"),
                "source": transaction.get("source"),
            }
        )

    suggestion = {
        "title": "智能财务建议",
        "description": (
            f"本月净现金流 {format_currency(current_profit)}。建议继续通过 OpenClaw 统一记账，并定期在手机端校准账户当前余额，网页与 iPhone 看板会同步更准确。"
        ),
        "actionLabel": "刷新看板",
    }

    return {
        "health": {
            "nodeName": server_config["nodeName"],
            "status": "ok",
            "openClawConnected": True,
            "remoteAccess": server_config.get("remoteAccess", "局域网"),
            "version": "0.2.0",
            "lastIngestedAt": server_config.get("lastIngestedAt"),
        },
        "dashboard": {
            "kpis": {
                "currentCashFlow": {"value": round(total_assets, 2), "display": format_currency(total_assets), "change": cashflow_change, "trend": cashflow_trend},
                "monthlyNetProfit": {"value": round(current_profit, 2), "display": format_currency(current_profit), "change": profit_change, "trend": profit_trend},
                "opexRate": {"value": round(opex_rate, 2), "display": f"{opex_rate:.1f}%", "change": opex_change, "trend": opex_trend},
                "emergencyRunway": {"value": round(current_runway, 2), "display": f"{current_runway:.1f} 个月", "change": runway_delta, "trend": runway_trend},
            },
            "trendData": {
                "months": [month_label_from_key(key) for key in month_keys],
                "income": [round(month_summary[key]["income"], 2) for key in month_keys],
                "expense": [round(month_summary[key]["expense"], 2) for key in month_keys],
            },
            "sunburstData": sunburst_data,
            "roiData": roi_data,
            "sankeyData": {
                "nodes": sankey_nodes,
                "links": sankey_links,
            },
            "accounts": accounts,
            "suggestion": suggestion,
        },
        "allTransactions": ui_transactions,
        "categories": categories,
        "meta": {
            "month": current_month_key,
            "transactionCount": len(ui_transactions),
            "rawTransactionCount": len(transactions),
            "bookMode": configuration["settings"].get("bookMode"),
        },
    }


def source_label(transaction: dict) -> Optional[str]:
    source = transaction.get("source")
    if not source:
        return None
    return {
        "openClaw": "OpenClaw",
        "manual": "手动录入",
        "imported": "导入",
        "localAPI": "本地 API",
        "openCrow": "OpenCrow",
    }.get(source, source)


def reimbursement_note(transaction: dict) -> Optional[str]:
    status = transaction.get("reimbursementStatus")
    if not status or status == "notApplicable":
        return None
    return {
        "draft": "待报销",
        "submitted": "报销中",
        "reimbursed": "已报销",
        "rejected": "已驳回",
    }.get(status, status)


class FinanceNodeHandler(BaseHTTPRequestHandler):
    server_version = "FinanceNode/0.1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if self._handle_public_file(parsed.path):
            return

        if not self._authenticate():
            return

        if parsed.path == "/v1/health":
            self._handle_health()
            return
        if parsed.path == "/v1/transactions":
            self._handle_list_transactions(parse_qs(parsed.query))
            return
        if parsed.path == "/v1/summary/month":
            self._handle_summary_month()
            return
        if parsed.path == "/v1/dashboard/overview":
            self._handle_dashboard_overview()
            return
        if parsed.path == "/v1/configuration":
            self._handle_get_configuration()
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self._authenticate():
            return

        parsed = urlparse(self.path)
        if parsed.path == "/v1/transactions":
            self._handle_create_transaction()
            return

        self._send_json(404, {"error": "Not found"})

    def do_PATCH(self) -> None:
        if not self._authenticate():
            return

        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 4 and parts[:2] == ["v1", "transactions"] and parts[3] == "reimbursement":
            self._handle_update_reimbursement(parts[2])
            return

        self._send_json(404, {"error": "Not found"})

    def do_PUT(self) -> None:
        if not self._authenticate():
            return

        parsed = urlparse(self.path)
        if parsed.path == "/v1/configuration":
            self._handle_put_configuration()
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format: str, *args) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def _handle_public_file(self, path: str) -> bool:
        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True

        if path in {"/", "/dashboard", "/dashboard/"}:
            self._send_file(WEB_DIR / "index.html")
            return True

        if path.startswith("/dashboard/"):
            relative = path.removeprefix("/dashboard/")
            if relative and "." in Path(relative).name:
                target = WEB_DIR / relative
                if target.exists() and target.is_file():
                    self._send_file(target)
                    return True
            self._send_file(WEB_DIR / "index.html")
            return True

        if path.startswith("/"):
            target = WEB_DIR / path.lstrip("/")
            if target.exists() and target.is_file():
                self._send_file(target)
                return True

        return False

    def _authenticate(self) -> bool:
        config = self.server.config
        token = config.get("accessToken", "").strip()
        if not token:
            return True

        authorization = self.headers.get("Authorization", "")
        if authorization == f"Bearer {token}":
            return True

        self._send_json(401, {"error": "Unauthorized"})
        return False

    def _handle_health(self) -> None:
        config = self.server.config
        response = {
            "nodeName": config["nodeName"],
            "status": "ok",
            "openClawConnected": True,
            "remoteAccess": config["remoteAccess"],
            "version": "0.1.0",
            "lastIngestedAt": config.get("lastIngestedAt"),
        }
        self._send_json(200, response)

    def _handle_list_transactions(self, query: dict) -> None:
        connection = connect_db()
        try:
            rows = connection.execute(
                """
                SELECT *
                FROM transactions
                ORDER BY occurred_at DESC, created_at DESC
                """
            ).fetchall()
        finally:
            connection.close()

        items = [row_to_transaction(row) for row in rows]
        kind = query.get("kind", [None])[0]
        reimbursement_status = query.get("reimbursementStatus", [None])[0]
        tag = query.get("tag", [None])[0]
        search = query.get("q", [None])[0]
        month = query.get("month", [None])[0]
        category_id = query.get("categoryId", [None])[0]
        account_name = query.get("accountName", [None])[0]
        limit = query.get("limit", [None])[0]

        if month and len(month) == 7 and month[4] == "-":
            items = [item for item in items if item["occurredAt"][:7] == month]
        if kind:
            items = [item for item in items if item["kind"] == kind]
        if reimbursement_status:
            items = [item for item in items if item["reimbursementStatus"] == reimbursement_status]
        if tag:
            items = [item for item in items if tag in item["tags"]]
        if category_id:
            items = [item for item in items if item["category"].get("id") == category_id]
        if account_name:
            items = [item for item in items if item["accountName"] == account_name]
        if search:
            needle = search.lower()
            items = [
                item
                for item in items
                if needle in " ".join(
                    [
                        item["title"],
                        item["category"]["name"],
                        item["accountName"],
                        item["merchant"],
                        item["note"],
                        " ".join(item["tags"]),
                    ]
                ).lower()
            ]
        if limit:
            try:
                items = items[: max(int(limit), 0)]
            except ValueError:
                pass

        self._send_json(200, items)

    def _handle_summary_month(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        prefix = query.get("month", [None])[0]
        if not prefix or len(prefix) != 7 or prefix[4] != "-":
            now = datetime.now().astimezone()
            prefix = f"{now.year:04d}-{now.month:02d}"
        connection = connect_db()
        try:
            rows = connection.execute(
                """
                SELECT kind, reimbursement_status, amount, occurred_at
                FROM transactions
                WHERE substr(occurred_at, 1, 7) = ?
                """,
                (prefix,),
            ).fetchall()
        finally:
            connection.close()

        income = sum(row["amount"] for row in rows if row["kind"] == "income")
        expense = sum(row["amount"] for row in rows if row["kind"] == "expense")
        pending = sum(
            row["amount"]
            for row in rows
            if row["reimbursement_status"] in {"draft", "submitted"}
        )
        self._send_json(
            200,
            {
                "month": prefix,
                "income": income,
                "expense": expense,
                "balance": income - expense,
                "pendingReimbursement": pending,
                "transactionCount": len(rows),
            },
        )

    def _handle_dashboard_overview(self) -> None:
        self._send_json(200, build_dashboard_overview(self.server.config))

    def _handle_get_configuration(self) -> None:
        self._send_json(200, load_configuration_payload())

    def _handle_put_configuration(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        categories = payload.get("categories") or []
        accounts = payload.get("accounts") or []
        settings = payload.get("settings") or default_ledger_settings()
        now = utc_now_iso()

        normalized_categories = []
        for index, item in enumerate(categories):
            category_id = item.get("id") or f"category-{index + 1}"
            normalized_categories.append(
                (
                    category_id,
                    json.dumps(
                        {
                            "id": category_id,
                            "name": item.get("name", "未分类"),
                            "systemImage": item.get("systemImage", "tray"),
                            "tintHex": item.get("tintHex", "#607D8B"),
                            "keywords": item.get("keywords") or [],
                        },
                        ensure_ascii=False,
                    ),
                    index,
                    now,
                )
            )

        normalized_accounts = []
        for index, item in enumerate(accounts):
            account_id = item.get("id") or f"account-{index + 1}"
            normalized_accounts.append(
                (
                    account_id,
                    json.dumps(
                        {
                            "id": account_id,
                            "name": item.get("name", f"账户{index + 1}"),
                            "type": item.get("type", "other"),
                            "currency": item.get("currency", "CNY"),
                            "openingBalance": float(item.get("openingBalance", 0.0)),
                            "brand": item.get("brand", "custom"),
                            "tintHex": item.get("tintHex", "#607D8B"),
                            "symbolName": item.get("symbolName", "creditcard.fill"),
                            "keywords": item.get("keywords") or [],
                        },
                        ensure_ascii=False,
                    ),
                    index,
                    now,
                )
            )

        normalized_settings = {
            "bookMode": settings.get("bookMode", "personalAssistant"),
            "defaultCurrency": settings.get("defaultCurrency", "CNY"),
            "timezone": settings.get("timezone", "Asia/Shanghai"),
            "allowManualEntry": bool(settings.get("allowManualEntry", True)),
        }

        connection = connect_db()
        try:
            connection.execute("DELETE FROM categories")
            connection.execute("DELETE FROM accounts")
            connection.execute("DELETE FROM ledger_settings")

            if normalized_categories:
                connection.executemany(
                    """
                    INSERT INTO categories (id, payload_json, sort_order, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    normalized_categories,
                )

            if normalized_accounts:
                connection.executemany(
                    """
                    INSERT INTO accounts (id, payload_json, sort_order, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    normalized_accounts,
                )

            connection.execute(
                """
                INSERT INTO ledger_settings (id, payload_json, updated_at)
                VALUES (1, ?, ?)
                """,
                (
                    json.dumps(normalized_settings, ensure_ascii=False),
                    now,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        self._send_json(200, load_configuration_payload())

    def _handle_create_transaction(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        now = utc_now_iso()
        transaction_id = payload.get("id") or str(uuid4())
        category = payload.get("category") or {
            "id": str(uuid4()),
            "name": "未分类",
            "systemImage": "tray",
            "tintHex": "#607D8B",
            "keywords": [],
        }
        tags = payload.get("tags") or []

        row = {
            "id": transaction_id,
            "title": payload.get("title", "未命名账单"),
            "amount": float(payload.get("amount", 0)),
            "kind": payload.get("type") or payload.get("kind") or "expense",
            "occurred_at": normalize_iso8601(payload.get("occurredAt"), now),
            "category_json": json.dumps(category, ensure_ascii=False),
            "tags_json": json.dumps(tags, ensure_ascii=False),
            "account_name": payload.get("accountName", "默认账户"),
            "from_account_name": payload.get("fromAccountName"),
            "to_account_name": payload.get("toAccountName"),
            "merchant": payload.get("merchant", payload.get("title", "")),
            "note": payload.get("note", ""),
            "reimbursement_status": payload.get("reimbursementStatus", "notApplicable"),
            "source": payload.get("source", "openClaw"),
            "created_at": now,
            "updated_at": now,
        }

        if row["kind"] == "income" and not row["to_account_name"]:
            row["to_account_name"] = row["account_name"]
        elif row["kind"] == "expense" and not row["from_account_name"]:
            row["from_account_name"] = row["account_name"]
        elif row["kind"] == "transfer":
            row["from_account_name"] = row["from_account_name"] or row["account_name"]
            row["to_account_name"] = row["to_account_name"] or payload.get("targetAccountName") or payload.get("merchant") or ""

        connection = connect_db()
        try:
            connection.execute(
                """
                INSERT INTO transactions (
                    id, title, amount, kind, occurred_at, category_json, tags_json,
                    account_name, from_account_name, to_account_name, merchant, note, reimbursement_status, source, created_at, updated_at
                ) VALUES (
                    :id, :title, :amount, :kind, :occurred_at, :category_json, :tags_json,
                    :account_name, :from_account_name, :to_account_name, :merchant, :note, :reimbursement_status, :source, :created_at, :updated_at
                )
                """,
                row,
            )
            connection.commit()
        finally:
            connection.close()

        self.server.config["lastIngestedAt"] = now
        self._persist_server_config()
        self._send_json(201, dict_to_transaction(row))

    def _handle_update_reimbursement(self, transaction_id: str) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        status = payload.get("status")
        if not status:
            self._send_json(400, {"error": "Missing status"})
            return

        connection = connect_db()
        try:
            cursor = connection.execute(
                """
                UPDATE transactions
                SET reimbursement_status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, utc_now_iso(), transaction_id),
            )
            connection.commit()
        finally:
            connection.close()

        if cursor.rowcount == 0:
            self._send_json(404, {"error": "Transaction not found"})
            return

        self._send_json(200, {"ok": True, "id": transaction_id, "status": status})

    def _read_json_body(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", "0"))
        try:
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return None

    def _persist_server_config(self) -> None:
        with CONFIG_PATH.open("w", encoding="utf-8") as file:
            json.dump(self.server.config, file, ensure_ascii=False, indent=2)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json(404, {"error": "Not found"})
            return

        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        cache_control = "no-cache"
        if "assets" in path.parts or path.suffix in {".woff", ".woff2"}:
            cache_control = "public, max-age=31536000, immutable"
        elif path.suffix == ".png":
            cache_control = "public, max-age=604800"

        accepted_encodings = self.headers.get("Accept-Encoding", "")
        should_gzip = (
            "gzip" in accepted_encodings.lower()
            and len(body) > 1024
            and (
                content_type.startswith("text/")
                or content_type in {
                    "application/javascript",
                    "text/javascript",
                    "application/json",
                    "application/manifest+json",
                    "image/svg+xml",
                }
            )
        )

        if should_gzip:
            body = gzip.compress(body, compresslevel=6)

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        if should_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status_code: int, payload: Union[dict, list]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FinanceNodeServer(ThreadingHTTPServer):
    def __init__(self, server_address, request_handler_class, config: dict):
        super().__init__(server_address, request_handler_class)
        self.config = config


def main() -> None:
    config = load_config()
    ensure_schema()
    seed_default_master_data()

    host = config.get("host", "0.0.0.0")
    port = int(config.get("port", 31888))
    server = FinanceNodeServer((host, port), FinanceNodeHandler, config)
    print(f"Finance Node running on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down Finance Node", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
