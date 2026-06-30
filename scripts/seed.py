"""Seed the LEDGR database with realistic demo data and export DB source files.

Run from the project root:  python scripts/seed.py

It will:
  1. Reset all LEDGR tables (FK-safe order).
  2. Insert a faithful demo dataset (Vatsal + flatmates, categories, rollover
     budgets, ~6 months of transactions, an itemised grocery split, and a
     trip group with simplified settlements). All IDs are explicit and
     human-readable so the exported files are easy to read.
  3. Write db/seed.json and db/seed.sql from the same dataset.

Demo login:  vatsal.ghoghari@dal.ca  /  Ledgr@2026
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prisma import Prisma  # noqa: E402

from app.core.security import hash_password  # noqa: E402

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"

PW_HASH = hash_password("Ledgr@2026")


def d(value: str) -> Decimal:
    return Decimal(value)


def ts(y: int, m: int, day: int) -> dt.datetime:
    return dt.datetime(y, m, day, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# 1. Build the dataset (explicit IDs)
# ---------------------------------------------------------------------------

users = [
    {"id": "user_vatsal", "email": "vatsal.ghoghari@dal.ca", "passwordHash": PW_HASH,
     "name": "Vatsal Ghoghari", "role": "USER", "avatarColor": "#7C3AED"},
    {"id": "user_marcus", "email": "marcus.bennett@ledgr.app", "passwordHash": PW_HASH,
     "name": "Marcus Bennett", "role": "USER", "avatarColor": "#0EA5E9"},
    {"id": "user_admin", "email": "admin@ledgr.app", "passwordHash": PW_HASH,
     "name": "LEDGR Admin", "role": "ADMIN", "avatarColor": "#111827"},
]

CATS = [
    ("cat_groceries", "Groceries", "#22C55E", "shopping-cart"),
    ("cat_dining", "Dining out", "#F59E0B", "utensils"),
    ("cat_transit", "Transit", "#3B82F6", "bus"),
    ("cat_housing", "Housing", "#8B5CF6", "home"),
    ("cat_utilities", "Utilities", "#06B6D4", "bolt"),
    ("cat_shopping", "Shopping", "#EC4899", "bag"),
    ("cat_entertainment", "Entertainment", "#6366F1", "film"),
    ("cat_income", "Income", "#10B981", "wallet"),
]
categories = [
    {"id": cid, "userId": "user_vatsal", "name": name, "color": color, "icon": icon,
     "parentId": None, "isDefault": True}
    for cid, name, color, icon in CATS
]
# a subcategory to exercise the self-relation
categories.append({"id": "cat_coffee", "userId": "user_vatsal", "name": "Coffee",
                   "color": "#A16207", "icon": "coffee", "parentId": "cat_dining",
                   "isDefault": False})

budgets = [
    {"id": "bud_groceries", "userId": "user_vatsal", "categoryId": "cat_groceries",
     "month": "2026-06", "targetAmount": d("400.00"), "rolloverEnabled": True},
    {"id": "bud_dining", "userId": "user_vatsal", "categoryId": "cat_dining",
     "month": "2026-06", "targetAmount": d("200.00"), "rolloverEnabled": True},
    {"id": "bud_transit", "userId": "user_vatsal", "categoryId": "cat_transit",
     "month": "2026-06", "targetAmount": d("120.00"), "rolloverEnabled": False},
    {"id": "bud_housing", "userId": "user_vatsal", "categoryId": "cat_housing",
     "month": "2026-06", "targetAmount": d("700.00"), "rolloverEnabled": False},
    {"id": "bud_utilities", "userId": "user_vatsal", "categoryId": "cat_utilities",
     "month": "2026-06", "targetAmount": d("150.00"), "rolloverEnabled": True},
]

# ---- Transactions: Jan-May generated, June matches the prototype ----
transactions: list[dict] = []
_seq = 0


def add_txn(date, type_, amount, vendor, cat, pay, shared=False, note=None, split=None):
    global _seq
    _seq += 1
    transactions.append({
        "id": f"txn_{_seq:04d}", "userId": "user_vatsal", "type": type_,
        "amount": d(amount), "vendor": vendor, "categoryId": cat, "date": date,
        "paymentMethod": pay, "note": note, "isShared": shared, "splitId": split,
        "receiptId": None,
    })


_MONTHLY = [
    ("75.40", "Atlantic Superstore", "cat_groceries", "DEBIT_CARD"),
    ("88.10", "Sobeys", "cat_groceries", "DEBIT_CARD"),
    ("36.50", "Pete's Frootique", "cat_groceries", "DEBIT_CARD"),
    ("41.20", "The Bicycle Thief", "cat_dining", "CREDIT_CARD"),
    ("24.75", "Cabin Coffee", "cat_coffee", "CREDIT_CARD"),
    ("78.00", "Halifax Transit", "cat_transit", "CREDIT_CARD"),
    ("41.10", "Nova Scotia Power", "cat_utilities", "PRE_AUTH"),
    ("78.90", "Eastlink Internet", "cat_utilities", "PRE_AUTH"),
]
for month in range(1, 6):  # Jan..May 2026
    add_txn(ts(2026, month, 1), "INCOME", "1240.00", "Payroll deposit", "cat_income",
            "DIRECT_DEPOSIT", note="Bi-weekly salary")
    add_txn(ts(2026, month, 1), "EXPENSE", "650.00", "Apartment 4B Rent", "cat_housing",
            "E_TRANSFER", shared=True, note="Shared rent")
    for i, (amt, vendor, cat, pay) in enumerate(_MONTHLY):
        shared = cat == "cat_utilities"
        add_txn(ts(2026, month, 3 + i * 3), "EXPENSE", amt, vendor, cat, pay, shared=shared)

# June 2026 — the month shown in the prototype dashboard / analytics
add_txn(ts(2026, 6, 1), "INCOME", "1240.00", "Payroll deposit", "cat_income",
        "DIRECT_DEPOSIT", note="Bi-weekly salary")
add_txn(ts(2026, 6, 1), "EXPENSE", "650.00", "Apartment 4B Rent", "cat_housing",
        "E_TRANSFER", shared=True, note="June rent — Apartment 4B")
add_txn(ts(2026, 6, 9), "EXPENSE", "84.20", "Sobeys", "cat_groceries", "DEBIT_CARD")
add_txn(ts(2026, 6, 14), "EXPENSE", "92.30", "Atlantic Superstore", "cat_groceries", "DEBIT_CARD")
add_txn(ts(2026, 6, 21), "EXPENSE", "75.40", "Sobeys", "cat_groceries", "DEBIT_CARD")
add_txn(ts(2026, 6, 27), "EXPENSE", "64.10", "Pete's Frootique", "cat_groceries", "DEBIT_CARD")
add_txn(ts(2026, 6, 6), "EXPENSE", "52.40", "The Bicycle Thief", "cat_dining", "CREDIT_CARD")
add_txn(ts(2026, 6, 12), "EXPENSE", "38.60", "Darrell's", "cat_dining", "CREDIT_CARD")
add_txn(ts(2026, 6, 18), "EXPENSE", "59.00", "Doraku Sushi", "cat_dining", "CREDIT_CARD")
add_txn(ts(2026, 6, 24), "EXPENSE", "64.00", "Salty's", "cat_dining", "CREDIT_CARD")
add_txn(ts(2026, 6, 5), "EXPENSE", "78.00", "Halifax Transit", "cat_transit", "CREDIT_CARD",
        note="Monthly transit pass")
add_txn(ts(2026, 6, 2), "EXPENSE", "41.10", "Nova Scotia Power", "cat_utilities", "PRE_AUTH", shared=True)
add_txn(ts(2026, 6, 2), "EXPENSE", "78.90", "Eastlink Internet", "cat_utilities", "PRE_AUTH", shared=True)
add_txn(ts(2026, 6, 15), "EXPENSE", "129.99", "Amazon", "cat_shopping", "CREDIT_CARD")
add_txn(ts(2026, 6, 20), "EXPENSE", "16.99", "Netflix", "cat_entertainment", "CREDIT_CARD")

# ---- A receipt (OCR import) that backs the grocery split ----
receipts = [{
    "id": "rcp_sobeys", "userId": "user_vatsal", "merchant": "Sobeys",
    "date": ts(2026, 6, 9), "subtotal": d("42.12"), "tax": d("2.52"), "total": d("44.64"),
    "imageUrl": None, "source": "OCR", "status": "CONFIRMED",
}]
receipt_items = [
    {"id": "rli_milk", "receiptId": "rcp_sobeys", "label": "Milk 2L", "amount": d("5.49"), "quantity": 1},
    {"id": "rli_eggs", "receiptId": "rcp_sobeys", "label": "Eggs (dozen)", "amount": d("4.29"), "quantity": 1},
    {"id": "rli_shampoo", "receiptId": "rcp_sobeys", "label": "Shampoo", "amount": d("8.99"), "quantity": 1},
    {"id": "rli_pasta", "receiptId": "rcp_sobeys", "label": "Pasta x3", "amount": d("6.57"), "quantity": 3},
    {"id": "rli_bars", "receiptId": "rcp_sobeys", "label": "Rahul's protein bars", "amount": d("12.99"), "quantity": 1},
    {"id": "rli_soap", "receiptId": "rcp_sobeys", "label": "Dish soap", "amount": d("3.79"), "quantity": 1},
]

# ---- Groups & members ----
groups = [
    {"id": "grp_apt4b", "name": "Apartment 4B", "ownerId": "user_vatsal", "status": "ACTIVE"},
    {"id": "grp_cabin", "name": "Cabin Trip 2026", "ownerId": "user_vatsal", "status": "ACTIVE"},
]
group_members = [
    {"id": "gm_apt_vatsal", "groupId": "grp_apt4b", "userId": "user_vatsal",
     "displayName": "Vatsal", "avatarColor": "#7C3AED", "role": "OWNER"},
    {"id": "gm_apt_rahul", "groupId": "grp_apt4b", "userId": None,
     "displayName": "Rahul", "avatarColor": "#06B6D4", "role": "MEMBER"},
    {"id": "gm_apt_anik", "groupId": "grp_apt4b", "userId": None,
     "displayName": "Anik", "avatarColor": "#F59E0B", "role": "MEMBER"},
    {"id": "gm_cab_vatsal", "groupId": "grp_cabin", "userId": "user_vatsal",
     "displayName": "Vatsal", "avatarColor": "#7C3AED", "role": "OWNER"},
    {"id": "gm_cab_jordan", "groupId": "grp_cabin", "userId": None,
     "displayName": "Jordan", "avatarColor": "#06B6D4", "role": "MEMBER"},
    {"id": "gm_cab_sam", "groupId": "grp_cabin", "userId": None,
     "displayName": "Sam", "avatarColor": "#F59E0B", "role": "MEMBER"},
    {"id": "gm_cab_dana", "groupId": "grp_cabin", "userId": None,
     "displayName": "Dana", "avatarColor": "#EC4899", "role": "MEMBER"},
]

# ---- Split (itemised grocery run, matches the Split Studio screen) ----
splits = [{
    "id": "spl_sobeys", "groupId": "grp_apt4b", "receiptId": "rcp_sobeys",
    "createdById": "user_vatsal", "title": "Sobeys (grocery run)", "mode": "ITEMISED",
    "subtotal": d("42.12"), "tax": d("2.52"), "total": d("44.64"),
    "taxAllocation": "PROPORTIONAL", "date": ts(2026, 6, 9),
}]
split_items = [
    {"id": "si_milk", "splitId": "spl_sobeys", "label": "Milk 2L", "amount": d("5.49"), "quantity": 1},
    {"id": "si_eggs", "splitId": "spl_sobeys", "label": "Eggs (dozen)", "amount": d("4.29"), "quantity": 1},
    {"id": "si_shampoo", "splitId": "spl_sobeys", "label": "Shampoo", "amount": d("8.99"), "quantity": 1},
    {"id": "si_pasta", "splitId": "spl_sobeys", "label": "Pasta x3", "amount": d("6.57"), "quantity": 3},
    {"id": "si_bars", "splitId": "spl_sobeys", "label": "Rahul's protein bars", "amount": d("12.99"), "quantity": 1},
    {"id": "si_soap", "splitId": "spl_sobeys", "label": "Dish soap", "amount": d("3.79"), "quantity": 1},
]
# who shared each item (matches the avatars in the prototype)
_ALL = ["gm_apt_vatsal", "gm_apt_rahul", "gm_apt_anik"]
_shares_map = {
    "si_milk": _ALL, "si_eggs": _ALL, "si_pasta": _ALL, "si_soap": _ALL,
    "si_shampoo": ["gm_apt_vatsal"], "si_bars": ["gm_apt_rahul"],
}
split_item_shares = []
for item_id, members in _shares_map.items():
    for mid in members:
        split_item_shares.append({
            "id": f"sis_{item_id}_{mid.split('_')[-1]}", "splitItemId": item_id,
            "memberId": mid, "weight": 1.0,
        })
split_participant_shares = [
    {"id": "sps_vatsal", "splitId": "spl_sobeys", "memberId": "gm_apt_vatsal", "amount": d("10.55")},
    {"id": "sps_rahul", "splitId": "spl_sobeys", "memberId": "gm_apt_rahul", "amount": d("23.54")},
    {"id": "sps_anik", "splitId": "spl_sobeys", "memberId": "gm_apt_anik", "amount": d("10.55")},
]

# ---- Settlements (debt-simplified Cabin Trip balances) ----
settlements = [
    {"id": "set_jordan", "groupId": "grp_cabin", "fromMemberId": "gm_cab_jordan",
     "toMemberId": "gm_cab_vatsal", "amount": d("182.50"), "status": "PENDING", "settledAt": None},
    {"id": "set_sam", "groupId": "grp_cabin", "fromMemberId": "gm_cab_sam",
     "toMemberId": "gm_cab_vatsal", "amount": d("96.00"), "status": "PENDING", "settledAt": None},
    {"id": "set_dana", "groupId": "grp_cabin", "fromMemberId": "gm_cab_vatsal",
     "toMemberId": "gm_cab_dana", "amount": d("54.25"), "status": "PENDING", "settledAt": None},
]

# table name -> (rows, ordered column list) — order is FK-safe for insertion
DATASET: list[tuple[str, list[dict]]] = [
    ("users", users),
    ("categories", categories),
    ("budgets", budgets),
    ("receipts", receipts),
    ("receipt_line_items", receipt_items),
    ("transactions", transactions),
    ("groups", groups),
    ("group_members", group_members),
    ("splits", splits),
    ("split_items", split_items),
    ("split_item_shares", split_item_shares),
    ("split_participant_shares", split_participant_shares),
    ("settlements", settlements),
]

# Prisma model accessor for each table
MODEL = {
    "users": "user", "categories": "category", "budgets": "budget", "receipts": "receipt",
    "receipt_line_items": "receiptlineitem", "transactions": "transaction", "groups": "group",
    "group_members": "groupmember", "splits": "split", "split_items": "splititem",
    "split_item_shares": "splititemshare", "split_participant_shares": "splitparticipantshare",
    "settlements": "settlement",
}


# ---------------------------------------------------------------------------
# 2. Insert into the live database
# ---------------------------------------------------------------------------

async def reset(db: Prisma) -> None:
    # delete children before parents
    await db.settlement.delete_many()
    await db.splitparticipantshare.delete_many()
    await db.splititemshare.delete_many()
    await db.splititem.delete_many()
    await db.transaction.delete_many()
    await db.split.delete_many()
    await db.receiptlineitem.delete_many()
    await db.receipt.delete_many()
    await db.groupmember.delete_many()
    await db.group.delete_many()
    await db.budget.delete_many()
    await db.category.delete_many()
    await db.refreshtoken.delete_many()
    await db.passwordresettoken.delete_many()
    await db.user.delete_many()


async def insert(db: Prisma) -> None:
    for table, rows in DATASET:
        if not rows:
            continue
        accessor = getattr(db, MODEL[table])
        if table == "categories":
            # parents first (subcategories reference a parent in the same table)
            parents = [r for r in rows if r.get("parentId") is None]
            children = [r for r in rows if r.get("parentId") is not None]
            await accessor.create_many(data=parents)
            if children:
                await accessor.create_many(data=children)
        else:
            await accessor.create_many(data=rows)


# ---------------------------------------------------------------------------
# 3. Export db/seed.json and db/seed.sql
# ---------------------------------------------------------------------------

def _json_default(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, dt.datetime):
        return o.isoformat()
    raise TypeError(type(o))


def write_json() -> None:
    payload = {table: rows for table, rows in DATASET}
    (DB_DIR / "seed.json").write_text(
        json.dumps(payload, indent=2, default=_json_default), encoding="utf-8"
    )


def _sql_value(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, dt.datetime):
        return "'" + v.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S") + "+00'"
    return "'" + str(v).replace("'", "''") + "'"


def write_sql() -> None:
    lines = [
        "-- LEDGR seed data (generated by scripts/seed.py)",
        "-- Demo login: vatsal.ghoghari@dal.ca / Ledgr@2026",
        "-- Load order is foreign-key safe. Run after schema.sql.",
        "BEGIN;",
        "",
    ]
    for table, rows in DATASET:
        if not rows:
            continue
        cols = list(rows[0].keys())
        col_sql = ", ".join(f'"{c}"' for c in cols)
        lines.append(f"-- {table} ({len(rows)} rows)")
        for r in rows:
            vals = ", ".join(_sql_value(r.get(c)) for c in cols)
            lines.append(f'INSERT INTO "{table}" ({col_sql}) VALUES ({vals});')
        lines.append("")
    lines.append("COMMIT;")
    (DB_DIR / "seed.sql").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db = Prisma()
    await db.connect()
    try:
        print("Resetting tables...")
        await reset(db)
        print("Inserting demo dataset...")
        await insert(db)
        counts = {
            "users": await db.user.count(),
            "categories": await db.category.count(),
            "budgets": await db.budget.count(),
            "transactions": await db.transaction.count(),
            "groups": await db.group.count(),
            "group_members": await db.groupmember.count(),
            "splits": await db.split.count(),
            "settlements": await db.settlement.count(),
        }
        print("Row counts:", counts)
    finally:
        await db.disconnect()

    print("Writing db/seed.json and db/seed.sql ...")
    write_json()
    write_sql()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
