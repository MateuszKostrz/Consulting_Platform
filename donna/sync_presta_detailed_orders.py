#!/usr/bin/env python3
"""Sync presta_detailed_orders from PrestaShop API order line items.

Default mode incrementally syncs orders that are missing from detailed or
updated in presta_orders since the last detailed load. Use --full-rebuild to
truncate and reload the entire table.

Standalone script — safe to deploy as a single file, e.g.:
  /home/ubuntu/scheduled_tasks/dn_presta_detailed_orders.py
"""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
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
ORDERS_TABLE = "presta_orders"
DETAILED_TABLE = "presta_detailed_orders"
DEFAULT_PARALLEL_WORKERS = 10
DEFAULT_INSERT_BATCH = 500

CREATE_DETAILED_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {DETAILED_TABLE} (
    line_id BIGINT PRIMARY KEY,
    order_id BIGINT,
    order_id_address_delivery BIGINT,
    order_id_address_invoice BIGINT,
    order_id_cart BIGINT,
    order_id_currency BIGINT,
    order_id_lang BIGINT,
    order_id_customer BIGINT,
    order_id_carrier BIGINT,
    order_current_state BIGINT,
    order_module TEXT,
    order_invoice_number BIGINT,
    order_invoice_date TIMESTAMP,
    order_delivery_number BIGINT,
    order_delivery_date TIMESTAMP,
    order_valid BIGINT,
    order_date_add TIMESTAMP,
    order_date_upd TIMESTAMP,
    order_shipping_number TEXT,
    order_inpost_point TEXT,
    order_id_shop_group BIGINT,
    order_id_shop BIGINT,
    order_secure_key TEXT,
    order_payment TEXT,
    order_recyclable BIGINT,
    order_gift BIGINT,
    order_gift_message TEXT,
    order_mobile_theme BIGINT,
    order_total_discounts NUMERIC(18, 6),
    order_total_discounts_tax_incl NUMERIC(18, 6),
    order_total_discounts_tax_excl NUMERIC(18, 6),
    order_total_paid NUMERIC(18, 6),
    order_total_paid_tax_incl NUMERIC(18, 6),
    order_total_paid_tax_excl NUMERIC(18, 6),
    order_total_paid_real NUMERIC(18, 6),
    order_total_products NUMERIC(18, 6),
    order_total_products_wt NUMERIC(18, 6),
    order_total_shipping NUMERIC(18, 6),
    order_total_shipping_tax_incl NUMERIC(18, 6),
    order_total_shipping_tax_excl NUMERIC(18, 6),
    order_carrier_tax_rate NUMERIC(18, 6),
    order_total_wrapping NUMERIC(18, 6),
    order_total_wrapping_tax_incl NUMERIC(18, 6),
    order_total_wrapping_tax_excl NUMERIC(18, 6),
    order_round_mode BIGINT,
    order_round_type BIGINT,
    order_conversion_rate NUMERIC(18, 6),
    order_reference BIGINT,
    line_product_id BIGINT,
    line_product_attribute_id BIGINT,
    line_product_quantity BIGINT,
    line_product_name TEXT,
    line_product_reference TEXT,
    line_product_ean13 TEXT,
    line_product_isbn TEXT,
    line_product_upc TEXT,
    line_product_price NUMERIC(18, 6),
    line_id_customization BIGINT,
    line_unit_price_tax_incl NUMERIC(18, 6),
    line_unit_price_tax_excl NUMERIC(18, 6)
);
"""

ORDER_HEADER_FIELDS = [
    ("order_id", "id"),
    ("order_id_address_delivery", "id_address_delivery"),
    ("order_id_address_invoice", "id_address_invoice"),
    ("order_id_cart", "id_cart"),
    ("order_id_currency", "id_currency"),
    ("order_id_lang", "id_lang"),
    ("order_id_customer", "id_customer"),
    ("order_id_carrier", "id_carrier"),
    ("order_current_state", "current_state"),
    ("order_module", "module"),
    ("order_invoice_number", "invoice_number"),
    ("order_invoice_date", "invoice_date"),
    ("order_delivery_number", "delivery_number"),
    ("order_delivery_date", "delivery_date"),
    ("order_valid", "valid"),
    ("order_date_add", "date_add"),
    ("order_date_upd", "date_upd"),
    ("order_shipping_number", "shipping_number"),
    ("order_inpost_point", "inpost_point"),
    ("order_id_shop_group", "id_shop_group"),
    ("order_id_shop", "id_shop"),
    ("order_secure_key", "secure_key"),
    ("order_payment", "payment"),
    ("order_recyclable", "recyclable"),
    ("order_gift", "gift"),
    ("order_gift_message", "gift_message"),
    ("order_mobile_theme", "mobile_theme"),
    ("order_total_discounts", "total_discounts"),
    ("order_total_discounts_tax_incl", "total_discounts_tax_incl"),
    ("order_total_discounts_tax_excl", "total_discounts_tax_excl"),
    ("order_total_paid", "total_paid"),
    ("order_total_paid_tax_incl", "total_paid_tax_incl"),
    ("order_total_paid_tax_excl", "total_paid_tax_excl"),
    ("order_total_paid_real", "total_paid_real"),
    ("order_total_products", "total_products"),
    ("order_total_products_wt", "total_products_wt"),
    ("order_total_shipping", "total_shipping"),
    ("order_total_shipping_tax_incl", "total_shipping_tax_incl"),
    ("order_total_shipping_tax_excl", "total_shipping_tax_excl"),
    ("order_carrier_tax_rate", "carrier_tax_rate"),
    ("order_total_wrapping", "total_wrapping"),
    ("order_total_wrapping_tax_incl", "total_wrapping_tax_incl"),
    ("order_total_wrapping_tax_excl", "total_wrapping_tax_excl"),
    ("order_round_mode", "round_mode"),
    ("order_round_type", "round_type"),
    ("order_conversion_rate", "conversion_rate"),
    ("order_reference", "reference"),
]

LINE_FIELDS = [
    ("line_id", "id"),
    ("line_product_id", "product_id"),
    ("line_product_attribute_id", "product_attribute_id"),
    ("line_product_quantity", "product_quantity"),
    ("line_product_name", "product_name"),
    ("line_product_reference", "product_reference"),
    ("line_product_ean13", "product_ean13"),
    ("line_product_isbn", "product_isbn"),
    ("line_product_upc", "product_upc"),
    ("line_product_price", "product_price"),
    ("line_id_customization", "id_customization"),
    ("line_unit_price_tax_incl", "unit_price_tax_incl"),
    ("line_unit_price_tax_excl", "unit_price_tax_excl"),
]

DETAILED_COLUMNS = [name for name, _ in ORDER_HEADER_FIELDS] + [name for name, _ in LINE_FIELDS]


def resolve_env_file() -> Path:
    explicit = os.environ.get("ENV_FILE", "").strip()
    if explicit:
        return Path(explicit)

    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / ".env",
        Path("/home/ubuntu/scheduled_tasks/.env"),
        Path("/home/ubuntu/Edunade_Platform/platform_edu/.env"),
        Path("/home/ubuntu/Consulting_Platform/platform_edu/.env"),
        script_dir.parent / "platform_edu" / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def log(message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


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


def load_order_ids(db_name: str) -> list[int]:
    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {ORDERS_TABLE} ORDER BY id")
            return [int(row[0]) for row in cur.fetchall()]


def load_order_ids_to_sync(db_name: str) -> list[int]:
    """Orders missing from detailed or updated in presta_orders since last sync."""
    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT o.id
                FROM {ORDERS_TABLE} o
                LEFT JOIN (
                    SELECT order_id, MAX(order_date_upd) AS detailed_upd
                    FROM {DETAILED_TABLE}
                    GROUP BY order_id
                ) d ON d.order_id = o.id
                WHERE d.order_id IS NULL
                   OR o.date_upd > d.detailed_upd
                ORDER BY o.id
                """
            )
            return [int(row[0]) for row in cur.fetchall()]


def fetch_order_detail(order_id: int, *, session: requests.Session) -> dict[str, Any]:
    response = session.get(
        f"{_api_url()}/orders/{order_id}",
        params={"output_format": "JSON"},
        auth=_api_auth(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("order") or {}


def _clean_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip() or None


def rows_from_order_detail(detail: dict[str, Any]) -> list[dict[str, Any]]:
    products = detail.get("associations", {}).get("order_rows") or []
    if not products:
        return []

    header = {dest: detail.get(src) for dest, src in ORDER_HEADER_FIELDS}
    rows: list[dict[str, Any]] = []

    for product in products:
        row = dict(header)
        for dest, src in LINE_FIELDS:
            row[dest] = product.get(src)
        if row.get("line_product_name"):
            row["line_product_name"] = str(row["line_product_name"]).replace("\n", " — ")
        for col in (
            "line_product_reference",
            "line_product_ean13",
            "line_product_isbn",
            "line_product_upc",
            "order_shipping_number",
            "order_inpost_point",
        ):
            if col in row:
                row[col] = _clean_text(row[col])
        rows.append(row)

    return rows


def normalize_detailed_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=DETAILED_COLUMNS)

    for col in ("order_date_add", "order_date_upd", "order_invoice_date", "order_delivery_date"):
        frame[col] = pd.to_datetime(frame[col], errors="coerce")

    int_cols = [
        col
        for col in DETAILED_COLUMNS
        if col.startswith(("order_id", "order_current_state", "order_invoice_number", "order_delivery_number", "order_valid", "order_recyclable", "order_gift", "order_mobile_theme", "order_round_mode", "order_round_type", "order_reference", "line_id", "line_product_id", "line_product_attribute_id", "line_product_quantity", "line_id_customization"))
    ]
    for col in int_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("Int64")

    numeric_cols = [
        col
        for col in DETAILED_COLUMNS
        if col.startswith(("order_total_", "order_carrier_", "order_conversion_", "line_product_price", "line_unit_price_"))
    ]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    for col in ("order_module", "order_secure_key", "order_payment", "order_gift_message", "line_product_name"):
        frame[col] = frame[col].replace("", None)

    return frame.replace({pd.NaT: None}).where(pd.notna(frame), None)


def fetch_all_line_rows(
    order_ids: list[int],
    *,
    max_workers: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(order_ids)
    done = 0
    started = time.time()
    session = requests.Session()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_order_detail, order_id, session=session): order_id
            for order_id in order_ids
        }
        for future in as_completed(futures):
            order_id = futures[future]
            try:
                detail = future.result()
                rows.extend(rows_from_order_detail(detail))
            except Exception as exc:
                log(f"WARNING: failed order {order_id}: {exc}")
            done += 1
            if done % 500 == 0 or done == total:
                log(f"  fetched {done:,}/{total:,} orders ({len(rows):,} line items)")

    log(f"API fetch done in {time.time() - started:.1f}s")
    return rows


def _insert_detailed_frame(cur, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    columns = list(frame.columns)
    insert_sql = f"""
        INSERT INTO {DETAILED_TABLE} ({', '.join(columns)})
        VALUES %s
    """
    rows = [tuple(row[col] for col in columns) for _, row in frame.iterrows()]
    for start in range(0, len(rows), DEFAULT_INSERT_BATCH):
        execute_values(cur, insert_sql, rows[start : start + DEFAULT_INSERT_BATCH], page_size=200)
    return len(frame)


def reload_detailed_orders(
    frame: pd.DataFrame,
    *,
    db_name: str,
) -> int:
    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_DETAILED_TABLE_SQL)
            cur.execute(f"TRUNCATE TABLE {DETAILED_TABLE}")
            inserted = _insert_detailed_frame(cur, frame)
        conn.commit()
    return inserted


def upsert_detailed_orders(
    frame: pd.DataFrame,
    *,
    db_name: str,
    order_ids: list[int],
) -> int:
    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_DETAILED_TABLE_SQL)
            if order_ids:
                cur.execute(
                    f"DELETE FROM {DETAILED_TABLE} WHERE order_id = ANY(%s)",
                    (order_ids,),
                )
            inserted = _insert_detailed_frame(cur, frame)
        conn.commit()
    return inserted


def sync_detailed_orders(
    *,
    db_name: str,
    max_workers: int,
    full_rebuild: bool,
) -> dict[str, int]:
    if full_rebuild:
        order_ids = load_order_ids(db_name)
        log(f"Full rebuild: loading all {len(order_ids):,} order IDs from {ORDERS_TABLE} ...")
    else:
        order_ids = load_order_ids_to_sync(db_name)
        log(
            f"Incremental sync: {len(order_ids):,} orders to refresh "
            f"(missing or updated in {ORDERS_TABLE}) ..."
        )

    if not order_ids:
        log("Nothing to sync.")
        return {"orders": 0, "lines": 0}

    log("Fetching order line items from PrestaShop API ...")
    line_rows = fetch_all_line_rows(order_ids, max_workers=max_workers)
    frame = normalize_detailed_frame(line_rows) if line_rows else pd.DataFrame(columns=DETAILED_COLUMNS)

    empty_orders = len(order_ids) - frame["order_id"].nunique() if not frame.empty else len(order_ids)
    if empty_orders:
        log(f"  {empty_orders:,} order(s) returned no line items from API (skipped)")

    if full_rebuild:
        if frame.empty:
            raise SystemExit("No line items returned from PrestaShop API.")
        log(f"Truncating and reloading {db_name}.{DETAILED_TABLE} ...")
        inserted = reload_detailed_orders(frame, db_name=db_name)
    else:
        log(f"Upserting into {db_name}.{DETAILED_TABLE} ...")
        inserted = upsert_detailed_orders(frame, db_name=db_name, order_ids=order_ids)

    return {"orders": len(order_ids), "lines": inserted}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync presta_detailed_orders from PrestaShop API.",
    )
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", DEFAULT_DB_NAME))
    parser.add_argument("--workers", type=int, default=DEFAULT_PARALLEL_WORKERS)
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Truncate and reload the entire detailed table (slow).",
    )
    parser.add_argument("--env-file", type=Path, default=resolve_env_file())
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    required = ("DB_HOST", "DB_PASSWORD", "PRESTASHOP_API_KEY")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        log(f"ERROR: missing env vars: {', '.join(missing)}")
        return 1

    started = time.time()
    try:
        result = sync_detailed_orders(
            db_name=args.db_name,
            max_workers=args.workers,
            full_rebuild=args.full_rebuild,
        )
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1

    elapsed = time.time() - started
    log(
        f"Done in {elapsed:.1f}s — orders={result['orders']:,}, "
        f"lines={result['lines']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
