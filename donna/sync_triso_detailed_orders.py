#!/usr/bin/env python3
"""Rebuild triso_detailed_orders from edonna (Triso) API order line items.

Standalone script — safe to deploy as a single file, e.g.:
  /home/ubuntu/scheduled_tasks/dn_triso_detailed_orders.py
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

API_BASE_URL = "https://www.edonna.pl/api/v1"
DEFAULT_DB_NAME = "test_don"
TABLE_NAME = "triso_detailed_orders"
DEFAULT_PARALLEL_WORKERS = 10
DEFAULT_INSERT_BATCH = 500

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    variant_id BIGINT NOT NULL DEFAULT 0,
    line_no INTEGER NOT NULL DEFAULT 0,
    order_number TEXT,
    order_date TIMESTAMP,
    order_status TEXT,
    order_status_id BIGINT,
    order_status_kind TEXT,
    order_paid TEXT,
    order_sum NUMERIC(18, 2),
    order_sum_net NUMERIC(18, 2),
    user_id BIGINT,
    customer_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    customer_company TEXT,
    currency_iso TEXT,
    product_name TEXT,
    symbol TEXT,
    ean TEXT,
    quantity INTEGER,
    original_price_unit NUMERIC(18, 2),
    sold_price_unit NUMERIC(18, 2),
    original_price_line NUMERIC(18, 2),
    sold_price_line NUMERIC(18, 2),
    rebate_percent NUMERIC(8, 2),
    synced_at TIMESTAMP,
    PRIMARY KEY (order_id, product_id, variant_id, line_no)
);
"""

DETAILED_COLUMNS = [
    "order_id",
    "product_id",
    "variant_id",
    "line_no",
    "order_number",
    "order_date",
    "order_status",
    "order_status_id",
    "order_status_kind",
    "order_paid",
    "order_sum",
    "order_sum_net",
    "user_id",
    "customer_name",
    "customer_email",
    "customer_phone",
    "customer_company",
    "currency_iso",
    "product_name",
    "symbol",
    "ean",
    "quantity",
    "original_price_unit",
    "sold_price_unit",
    "original_price_line",
    "sold_price_line",
    "rebate_percent",
    "synced_at",
]


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


def edonna_headers() -> dict[str, str]:
    api_key = os.environ.get("EDONNA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("EDONNA_API_KEY is not set")
    return {"X-API-KEY": api_key, "User-Agent": "Donna-Integration/1.0"}


def fetch_paginated(path: str, collection_key: str) -> list[dict[str, Any]]:
    page = 1
    items: list[dict[str, Any]] = []

    while True:
        response = requests.get(
            f"{API_BASE_URL}/{path}",
            headers=edonna_headers(),
            params={"page": page},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        items.extend(data[collection_key])
        if len(items) >= data["total"]:
            break
        page += 1

    return items


def fetch_all_orders() -> list[dict[str, Any]]:
    return fetch_paginated("orders", "orders")


def fetch_order_detail(order_id: int, *, session: requests.Session) -> dict[str, Any]:
    response = session.get(
        f"{API_BASE_URL}/orders/{order_id}",
        headers=edonna_headers(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def original_unit_price(product: dict[str, Any]) -> float | None:
    sold = _as_float(product.get("price_gross"))
    if sold is None:
        return None

    rebate = _as_float(product.get("rebate")) or 0.0
    if rebate > 0:
        return round(sold / (1 - rebate / 100), 2)

    wdt = product.get("wdt") or {}
    base = _as_float(wdt.get("price_gross_base"))
    if base is not None and base > sold:
        return round(base, 2)

    return round(sold, 2)


def rows_from_order_detail(detail: dict[str, Any], *, synced_at: datetime) -> list[dict[str, Any]]:
    customer = detail.get("customer") or {}
    currency = detail.get("currency_iso") or ""
    rows: list[dict[str, Any]] = []

    for line_no, product in enumerate(detail.get("products") or []):
        product_id = product.get("id")
        if product_id in (None, ""):
            continue

        quantity = int(_as_float(product.get("count")) or 0)
        sold_unit = _as_float(product.get("price_gross"))
        original_unit = original_unit_price(product)
        rebate = _as_float(product.get("rebate")) or 0.0
        variant_id = int(_as_float(product.get("variant_id")) or 0)

        rows.append(
            {
                "order_id": int(detail["id"]),
                "product_id": int(product_id),
                "variant_id": variant_id,
                "line_no": line_no,
                "order_number": detail.get("number"),
                "order_date": detail.get("order_date"),
                "order_status": detail.get("status"),
                "order_status_id": detail.get("status_id"),
                "order_status_kind": detail.get("status_kind"),
                "order_paid": detail.get("paid"),
                "order_sum": _as_float(detail.get("sum")),
                "order_sum_net": _as_float(detail.get("sum_net")),
                "user_id": detail.get("user_id"),
                "customer_name": customer.get("name"),
                "customer_email": customer.get("email"),
                "customer_phone": customer.get("phone"),
                "customer_company": customer.get("company"),
                "currency_iso": currency,
                "product_name": (product.get("name") or "").replace("\n", " — "),
                "symbol": product.get("symbol") or "",
                "ean": product.get("ean") or "",
                "quantity": quantity,
                "original_price_unit": original_unit,
                "sold_price_unit": sold_unit,
                "original_price_line": round(original_unit * quantity, 2)
                if original_unit is not None
                else None,
                "sold_price_line": _as_float(product.get("price_gross_sum"))
                or (round(sold_unit * quantity, 2) if sold_unit is not None else None),
                "rebate_percent": rebate,
                "synced_at": synced_at,
            }
        )

    return rows


def fetch_all_line_rows(
    orders: list[dict[str, Any]],
    *,
    max_workers: int,
) -> list[dict[str, Any]]:
    synced_at = datetime.now().astimezone()
    rows: list[dict[str, Any]] = []
    total = len(orders)
    done = 0
    started = time.time()
    session = requests.Session()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_order_detail, int(order["id"]), session=session): order
            for order in orders
        }
        for future in as_completed(futures):
            order = futures[future]
            try:
                detail = future.result()
                rows.extend(rows_from_order_detail(detail, synced_at=synced_at))
            except Exception as exc:
                log(f"WARNING: failed order {order.get('id')}: {exc}")
            done += 1
            if done % 200 == 0 or done == total:
                log(f"  fetched {done:,}/{total:,} orders ({len(rows):,} line items)")

    log(f"API fetch done in {time.time() - started:.1f}s")
    return rows


def normalize_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=DETAILED_COLUMNS)
    frame["order_date"] = pd.to_datetime(frame["order_date"], errors="coerce")
    frame["synced_at"] = pd.to_datetime(frame["synced_at"], errors="coerce")

    for col in ("order_id", "product_id", "variant_id", "line_no", "order_status_id", "user_id", "quantity"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("Int64")

    for col in (
        "order_sum",
        "order_sum_net",
        "original_price_unit",
        "sold_price_unit",
        "original_price_line",
        "sold_price_line",
        "rebate_percent",
    ):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    for col in ("order_number", "order_status", "order_status_kind", "order_paid", "customer_name", "customer_email", "customer_phone", "customer_company", "currency_iso", "product_name", "symbol", "ean"):
        frame[col] = frame[col].replace("", None)

    return frame.replace({pd.NaT: None}).where(pd.notna(frame), None)


def reload_detailed_orders(frame: pd.DataFrame, *, db_name: str, replace: bool) -> int:
    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            if replace:
                cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
                cur.execute(CREATE_TABLE_SQL)
            columns = list(frame.columns)
            update_columns = [col for col in columns if col not in {"order_id", "product_id", "variant_id", "line_no"}]
            insert_sql = f"""
                INSERT INTO {TABLE_NAME} ({', '.join(columns)})
                VALUES %s
                ON CONFLICT (order_id, product_id, variant_id, line_no) DO UPDATE SET
                {', '.join(f'{col} = EXCLUDED.{col}' for col in update_columns)}
            """
            rows = [tuple(row[col] for col in columns) for _, row in frame.iterrows()]
            for start in range(0, len(rows), DEFAULT_INSERT_BATCH):
                execute_values(cur, insert_sql, rows[start : start + DEFAULT_INSERT_BATCH], page_size=200)
        conn.commit()
    return len(frame)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync edonna (Triso) order line items into triso_detailed_orders.",
    )
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", DEFAULT_DB_NAME))
    parser.add_argument("--workers", type=int, default=DEFAULT_PARALLEL_WORKERS)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate triso_detailed_orders before loading.",
    )
    parser.add_argument("--env-file", type=Path, default=resolve_env_file())
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)
        log(f"Loaded env from {args.env_file}")

    required = ("DB_HOST", "DB_PASSWORD", "EDONNA_API_KEY")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        log(f"ERROR: missing env vars: {', '.join(missing)}")
        return 1

    log("Fetching all orders from edonna API ...")
    orders = fetch_all_orders()
    log(f"  {len(orders):,} orders to process")
    if not orders:
        raise SystemExit("No orders returned from edonna API.")

    log("Fetching order line items ...")
    line_rows = fetch_all_line_rows(orders, max_workers=args.workers)
    if not line_rows:
        raise SystemExit("No line items returned from edonna API.")

    log(f"Normalizing {len(line_rows):,} line items ...")
    frame = normalize_frame(line_rows)

    action = "Truncating and reloading" if args.replace else "Upserting into"
    log(f"{action} {args.db_name}.{TABLE_NAME} ...")
    inserted = reload_detailed_orders(frame, db_name=args.db_name, replace=args.replace)
    log(f"Done. Loaded {inserted:,} rows into {args.db_name}.{TABLE_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
