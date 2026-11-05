#!/usr/bin/env python3
"""Incrementally sync new/updated PrestaShop orders into presta_orders.

Standalone script — safe to deploy as a single file, e.g.:
  /home/ubuntu/scheduled_tasks/dn_presta_orders.py
"""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from requests.auth import HTTPBasicAuth

DEFAULT_API_URL = "https://donna.pl/api"
DEFAULT_DB_NAME = "test_don"
DEFAULT_PAGE_SIZE = 100
DEFAULT_PARALLEL_WORKERS = 10
DEFAULT_LOOKBACK_HOURS = 3
ORDERS_TABLE = "presta_orders"

ORDER_COLUMNS = [
    "id",
    "id_address_delivery",
    "id_address_invoice",
    "id_cart",
    "id_currency",
    "id_lang",
    "id_customer",
    "id_carrier",
    "current_state",
    "module",
    "invoice_number",
    "invoice_date",
    "delivery_number",
    "delivery_date",
    "valid",
    "date_add",
    "date_upd",
    "shipping_number",
    "inpost_point",
    "id_shop_group",
    "id_shop",
    "secure_key",
    "payment",
    "recyclable",
    "gift",
    "gift_message",
    "mobile_theme",
    "total_discounts",
    "total_discounts_tax_incl",
    "total_discounts_tax_excl",
    "total_paid",
    "total_paid_tax_incl",
    "total_paid_tax_excl",
    "total_paid_real",
    "total_products",
    "total_products_wt",
    "total_shipping",
    "total_shipping_tax_incl",
    "total_shipping_tax_excl",
    "carrier_tax_rate",
    "total_wrapping",
    "total_wrapping_tax_incl",
    "total_wrapping_tax_excl",
    "round_mode",
    "round_type",
    "conversion_rate",
    "reference",
]

CREATE_ORDERS_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {ORDERS_TABLE} (
    id BIGINT PRIMARY KEY,
    id_address_delivery BIGINT,
    id_address_invoice BIGINT,
    id_cart BIGINT,
    id_currency BIGINT,
    id_lang BIGINT,
    id_customer BIGINT,
    id_carrier BIGINT,
    current_state BIGINT,
    module TEXT,
    invoice_number BIGINT,
    invoice_date TIMESTAMP,
    delivery_number BIGINT,
    delivery_date TIMESTAMP,
    valid BIGINT,
    date_add TIMESTAMP,
    date_upd TIMESTAMP,
    shipping_number TEXT,
    inpost_point TEXT,
    id_shop_group BIGINT,
    id_shop BIGINT,
    secure_key TEXT,
    payment TEXT,
    recyclable BIGINT,
    gift BIGINT,
    gift_message TEXT,
    mobile_theme BIGINT,
    total_discounts NUMERIC(18, 6),
    total_discounts_tax_incl NUMERIC(18, 6),
    total_discounts_tax_excl NUMERIC(18, 6),
    total_paid NUMERIC(18, 6),
    total_paid_tax_incl NUMERIC(18, 6),
    total_paid_tax_excl NUMERIC(18, 6),
    total_paid_real NUMERIC(18, 6),
    total_products NUMERIC(18, 6),
    total_products_wt NUMERIC(18, 6),
    total_shipping NUMERIC(18, 6),
    total_shipping_tax_incl NUMERIC(18, 6),
    total_shipping_tax_excl NUMERIC(18, 6),
    carrier_tax_rate NUMERIC(18, 6),
    total_wrapping NUMERIC(18, 6),
    total_wrapping_tax_incl NUMERIC(18, 6),
    total_wrapping_tax_excl NUMERIC(18, 6),
    round_mode BIGINT,
    round_type BIGINT,
    conversion_rate NUMERIC(18, 6),
    reference BIGINT
);
"""


def resolve_env_file() -> Path:
    explicit = os.environ.get("ENV_FILE", "").strip()
    if explicit:
        return Path(explicit)

    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / ".env",
        Path("/home/ubuntu/Edunade_Platform/platform_edu/.env"),
        Path("/home/ubuntu/Consulting_Platform/platform_edu/.env"),
        Path("/home/ubuntu/scheduled_tasks/.env"),
        script_dir.parent / "Edunade_Platform" / "platform_edu" / ".env",
        script_dir.parent / "Consulting_Platform" / "platform_edu" / ".env",
        script_dir.parent / "platform_edu" / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[1]


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def connect(db_name: str):
    return psycopg2.connect(
        host=os.environ["DB_HOST"].strip("'"),
        user=os.environ.get("DB_USER", "mateuszkostrz"),
        password=os.environ["DB_PASSWORD"].strip("'"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=db_name,
    )


def _api_auth() -> HTTPBasicAuth:
    api_key = os.environ.get("PRESTASHOP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PRESTASHOP_API_KEY is not set")
    return HTTPBasicAuth(api_key, "")


def _api_url() -> str:
    return os.environ.get("PRESTASHOP_API_URL", DEFAULT_API_URL).rstrip("/")


def fetch_order_detail(order_id: int) -> dict[str, Any]:
    response = requests.get(
        f"{_api_url()}/orders/{order_id}",
        params={"output_format": "JSON"},
        auth=_api_auth(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("order") or {}


def fetch_order_ids_since(
    *,
    date_field: str,
    date_from: str,
    date_to: str,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[int]:
    if date_field not in {"date_add", "date_upd"}:
        raise ValueError("date_field must be date_add or date_upd")

    order_ids: list[int] = []
    offset = 0

    while True:
        response = requests.get(
            f"{_api_url()}/orders",
            params={
                "output_format": "JSON",
                "display": "[id]",
                f"filter[{date_field}]": f"[{date_from},{date_to}]",
                "date": 1,
                "limit": f"{offset},{page_size}",
            },
            auth=_api_auth(),
            timeout=60,
        )
        response.raise_for_status()
        chunk = response.json().get("orders") or []
        if not chunk:
            break

        order_ids.extend(int(order["id"]) for order in chunk)
        if len(chunk) < page_size:
            break
        offset += page_size

    return order_ids


def get_sync_window(
    db_name: str,
    *,
    lookback_hours: int,
) -> tuple[str, str, str, str]:
    now = datetime.now()
    date_to = now.strftime("%Y-%m-%d %H:%M:%S")
    lookback = timedelta(hours=lookback_hours)

    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT MAX(date_add), MAX(date_upd), COUNT(*) FROM {ORDERS_TABLE}"
            )
            max_date_add, max_date_upd, row_count = cur.fetchone()

    if not row_count:
        date_from = "2022-01-01 00:00:00"
        return date_from, date_from, date_to, "initial"

    add_from_dt = (max_date_add - lookback) if max_date_add else (now - lookback)
    upd_from_dt = (max_date_upd - lookback) if max_date_upd else (now - lookback)
    return (
        add_from_dt.strftime("%Y-%m-%d %H:%M:%S"),
        upd_from_dt.strftime("%Y-%m-%d %H:%M:%S"),
        date_to,
        "incremental",
    )


def normalize_orders_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for col in ORDER_COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    frame = frame[ORDER_COLUMNS]

    for col in ("date_add", "date_upd", "invoice_date", "delivery_date"):
        frame[col] = pd.to_datetime(frame[col], errors="coerce")

    for col in ORDER_COLUMNS:
        if col.startswith("id_") or col in {
            "id",
            "current_state",
            "invoice_number",
            "delivery_number",
            "valid",
            "recyclable",
            "gift",
            "mobile_theme",
            "round_mode",
            "round_type",
            "reference",
        }:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("Int64")

    for col in (
        "total_discounts",
        "total_discounts_tax_incl",
        "total_discounts_tax_excl",
        "total_paid",
        "total_paid_tax_incl",
        "total_paid_tax_excl",
        "total_paid_real",
        "total_products",
        "total_products_wt",
        "total_shipping",
        "total_shipping_tax_incl",
        "total_shipping_tax_excl",
        "carrier_tax_rate",
        "total_wrapping",
        "total_wrapping_tax_incl",
        "total_wrapping_tax_excl",
        "conversion_rate",
    ):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    for col in ("module", "shipping_number", "inpost_point", "secure_key", "payment", "gift_message"):
        frame[col] = frame[col].replace("", None)

    return frame.replace({pd.NaT: None}).where(pd.notna(frame), None)


def fetch_orders_by_ids(
    order_ids: list[int],
    *,
    max_workers: int = DEFAULT_PARALLEL_WORKERS,
) -> pd.DataFrame:
    if not order_ids:
        return pd.DataFrame(columns=ORDER_COLUMNS)

    rows: list[dict[str, Any]] = []
    done = 0
    total = len(order_ids)

    log(f"Fetching details for {total:,} orders ...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_order_detail, order_id): order_id
            for order_id in order_ids
        }
        for future in as_completed(futures):
            detail = future.result()
            rows.append({key: detail.get(key) for key in ORDER_COLUMNS})
            done += 1
            if done % 100 == 0 or done == total:
                log(f"  Details fetched: {done:,}/{total:,}")

    return normalize_orders_frame(rows)


def upsert_orders_frame(frame: pd.DataFrame, *, db_name: str) -> int:
    if frame.empty:
        return 0

    columns = list(frame.columns)
    update_columns = [col for col in columns if col != "id"]
    set_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_columns)

    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_ORDERS_TABLE_SQL)
            rows = [tuple(row[col] for col in columns) for _, row in frame.iterrows()]
            upsert_sql = f"""
                INSERT INTO {ORDERS_TABLE} ({', '.join(columns)})
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET {set_clause}
            """
            execute_values(cur, upsert_sql, rows, page_size=200)
        conn.commit()

    return len(frame)


def update_orders(
    *,
    db_name: str,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    max_workers: int = DEFAULT_PARALLEL_WORKERS,
) -> dict[str, Any]:
    add_from, upd_from, date_to, mode = get_sync_window(
        db_name,
        lookback_hours=lookback_hours,
    )
    log(f"Sync mode: {mode}")
    log(f"Window date_add >= {add_from}")
    log(f"Window date_upd >= {upd_from}")
    log(f"Window date_to = {date_to}")

    new_ids = fetch_order_ids_since(
        date_field="date_add",
        date_from=add_from,
        date_to=date_to,
    )
    updated_ids = fetch_order_ids_since(
        date_field="date_upd",
        date_from=upd_from,
        date_to=date_to,
    )
    order_ids = sorted(set(new_ids) | set(updated_ids))

    log(
        f"Order IDs to sync: {len(order_ids):,} "
        f"(new={len(new_ids):,}, updated={len(updated_ids):,})"
    )

    if not order_ids:
        log("No orders to sync.")
        return {"mode": mode, "synced": 0, "new_ids": 0, "updated_ids": 0}

    frame = fetch_orders_by_ids(order_ids, max_workers=max_workers)
    upserted = upsert_orders_frame(frame, db_name=db_name)
    log(f"Upserted {upserted:,} rows into {db_name}.{ORDERS_TABLE}")

    return {
        "mode": mode,
        "synced": upserted,
        "new_ids": len(new_ids),
        "updated_ids": len(updated_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Incrementally update presta_orders from PrestaShop API.",
    )
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", DEFAULT_DB_NAME))
    parser.add_argument("--lookback-hours", type=int, default=DEFAULT_LOOKBACK_HOURS)
    parser.add_argument("--workers", type=int, default=DEFAULT_PARALLEL_WORKERS)
    parser.add_argument("--env-file", type=Path, default=None)
    args = parser.parse_args()

    env_file = args.env_file or resolve_env_file()
    if env_file.exists():
        load_dotenv(env_file)
        log(f"Loaded env from {env_file}")
    else:
        log(f"WARNING: env file not found at {env_file}")

    required = ("DB_HOST", "DB_PASSWORD", "PRESTASHOP_API_KEY")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        log(
            f"ERROR: missing env vars: {', '.join(missing)}. "
            f"Set them in {env_file} or pass --env-file /path/to/.env"
        )
        return 1

    started = time.time()
    try:
        result = update_orders(
            db_name=args.db_name,
            lookback_hours=args.lookback_hours,
            max_workers=args.workers,
        )
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1

    elapsed = time.time() - started
    log(
        f"Done in {elapsed:.1f}s — synced={result['synced']:,}, "
        f"new={result['new_ids']:,}, updated={result['updated_ids']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
