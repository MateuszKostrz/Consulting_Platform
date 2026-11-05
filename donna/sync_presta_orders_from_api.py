"""Fetch PrestaShop orders from API and load into PostgreSQL presta_orders."""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from import_prestashop_orders_to_postgres import (
    CREATE_ORDERS_TABLE_SQL,
    DEFAULT_DB_NAME,
    DEFAULT_ENV_FILE,
    ORDERS_TABLE,
    _import_frame,
)

DEFAULT_API_URL = "https://donna.pl/api"
DEFAULT_DATE_FROM = "2022-01-01"
DEFAULT_DATE_TO = "2026-07-08"
DEFAULT_PAGE_SIZE = 100
DEFAULT_PARALLEL_WORKERS = 10
ORDER_SKIP = {"associations"}

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


def _api_auth() -> HTTPBasicAuth:
    api_key = os.environ.get("PRESTASHOP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PRESTASHOP_API_KEY is not set")
    return HTTPBasicAuth(api_key, "")


def _api_url() -> str:
    return os.environ.get("PRESTASHOP_API_URL", DEFAULT_API_URL).rstrip("/")


def fetch_order_ids(
    date_from: str,
    date_to: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[int]:
    order_ids: list[int] = []
    offset = 0

    while True:
        response = requests.get(
            f"{_api_url()}/orders",
            params={
                "output_format": "JSON",
                "display": "[id]",
                "filter[date_add]": f"[{date_from} 00:00:00,{date_to} 23:59:59]",
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
        if offset % 1000 == 0:
            print(f"  Listed {len(order_ids):,} order IDs ...")

    return order_ids


def fetch_order_detail(order_id: int) -> dict[str, Any]:
    response = requests.get(
        f"{_api_url()}/orders/{order_id}",
        params={"output_format": "JSON"},
        auth=_api_auth(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("order") or {}


def fetch_orders_frame(
    date_from: str,
    date_to: str,
    *,
    max_workers: int = DEFAULT_PARALLEL_WORKERS,
) -> pd.DataFrame:
    print(f"Listing orders {date_from} .. {date_to} ...")
    order_ids = fetch_order_ids(date_from, date_to)
    print(f"Order IDs found: {len(order_ids):,}")
    if not order_ids:
        return pd.DataFrame(columns=ORDER_COLUMNS)

    rows: list[dict[str, Any]] = []
    done = 0
    total = len(order_ids)

    print("Fetching full order details ...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_order_detail, order_id): order_id
            for order_id in order_ids
        }
        for future in as_completed(futures):
            detail = future.result()
            row = {key: detail.get(key) for key in ORDER_COLUMNS if key in detail}
            rows.append(row)
            done += 1
            if done % 500 == 0 or done == total:
                print(f"  Details fetched: {done:,}/{total:,}")

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


def sync_orders(
    *,
    date_from: str,
    date_to: str,
    db_name: str,
    replace: bool = True,
    max_workers: int = DEFAULT_PARALLEL_WORKERS,
) -> int:
    frame = fetch_orders_frame(date_from, date_to, max_workers=max_workers)
    return _import_frame(
        frame,
        db_name=db_name,
        table_name=ORDERS_TABLE,
        create_sql=CREATE_ORDERS_TABLE_SQL,
        replace=replace,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync PrestaShop orders from API into PostgreSQL.",
    )
    parser.add_argument("--date-from", default=DEFAULT_DATE_FROM)
    parser.add_argument("--date-to", default=DEFAULT_DATE_TO)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--workers", type=int, default=DEFAULT_PARALLEL_WORKERS)
    parser.add_argument(
        "--replace",
        action="store_true",
        default=True,
        help="Replace existing presta_orders table contents (default: true).",
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    started = time.time()
    count = sync_orders(
        date_from=args.date_from,
        date_to=args.date_to,
        db_name=args.db_name,
        replace=args.replace,
        max_workers=args.workers,
    )
    elapsed = time.time() - started
    print(f"Imported {count:,} rows into {args.db_name}.{ORDERS_TABLE}")
    print(f"Done in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
