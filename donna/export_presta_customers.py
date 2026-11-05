#!/usr/bin/env python3
"""Export PrestaShop customers with order totals, email, and phone."""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

DEFAULT_API_URL = "https://donna.pl/api"
DEFAULT_DB_NAME = "test_don"
BATCH_SIZE = 80

# PrestaShop order status mapping (from presta_orders.current_state):
#   4  — shipped/sent (main, ~18k orders)
#   5  — shipped variant (~949)
#   19 — cancelled (valid=0)
#   6, 10 — cancelled/refunded (valid=0)
# Revenue counts only valid=1 orders (excludes all cancelled).


def resolve_env_file() -> Path:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / "platform_edu" / ".env",
        Path("/home/ubuntu/Edunade_Platform/platform_edu/.env"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def connect(db_name: str):
    return psycopg2.connect(
        host=os.environ["DB_HOST"].strip("'"),
        user=os.environ.get("DB_USER", "mateuszkostrz"),
        password=os.environ["DB_PASSWORD"].strip("'"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=db_name,
    )


def load_order_stats(db_name: str) -> pd.DataFrame:
    sql = """
        SELECT
            id_customer,
            COUNT(*) AS order_count,
            ROUND(SUM(COALESCE(total_paid_tax_incl, total_paid, 0))::numeric, 2) AS total_ordered,
            MIN(date_add) AS first_order,
            MAX(date_add) AS last_order
        FROM presta_orders
        WHERE id_customer IS NOT NULL AND id_customer > 0
          AND valid = 1
        GROUP BY id_customer
    """
    with connect(db_name) as conn:
        return pd.read_sql(sql, conn)


def chunked(values: list[int], size: int) -> list[list[int]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def fetch_customers_batch(
    customer_ids: list[int],
    *,
    api_url: str,
    auth: HTTPBasicAuth,
    session: requests.Session,
) -> list[dict]:
    if not customer_ids:
        return []
    filter_value = "|".join(str(cid) for cid in customer_ids)
    response = session.get(
        f"{api_url}/customers",
        auth=auth,
        params={
            "output_format": "JSON",
            "display": "[id,email,firstname,lastname,newsletter]",
            "filter[id]": f"[{filter_value}]",
            "limit": len(customer_ids),
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("customers") or []


def fetch_addresses_batch(
    customer_ids: list[int],
    *,
    api_url: str,
    auth: HTTPBasicAuth,
    session: requests.Session,
) -> list[dict]:
    if not customer_ids:
        return []
    filter_value = "|".join(str(cid) for cid in customer_ids)
    response = session.get(
        f"{api_url}/addresses",
        auth=auth,
        params={
            "output_format": "JSON",
            "display": "[id,id_customer,phone,phone_mobile,date_upd,deleted]",
            "filter[id_customer]": f"[{filter_value}]",
            "limit": 1000,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("addresses") or []


def pick_phone(addresses: list[dict]) -> str | None:
    active = [row for row in addresses if str(row.get("deleted", "0")) != "1"]
    rows = active or addresses
    if not rows:
        return None

    def phone_value(row: dict) -> str:
        mobile = str(row.get("phone_mobile") or "").strip()
        phone = str(row.get("phone") or "").strip()
        return mobile or phone

    rows = sorted(rows, key=lambda row: str(row.get("date_upd") or ""), reverse=True)
    for row in rows:
        value = phone_value(row)
        if value:
            return value
    return None


def enrich_customers(
    order_stats: pd.DataFrame,
    *,
    api_url: str,
    auth: HTTPBasicAuth,
) -> pd.DataFrame:
    customer_ids = order_stats["id_customer"].astype(int).tolist()
    batches = chunked(customer_ids, BATCH_SIZE)
    session = requests.Session()

    customer_rows: list[dict] = []
    phone_by_customer: dict[int, str] = {}

    started = time.time()
    for index, batch in enumerate(batches, start=1):
        for row in fetch_customers_batch(batch, api_url=api_url, auth=auth, session=session):
            customer_rows.append(row)

        addresses = fetch_addresses_batch(batch, api_url=api_url, auth=auth, session=session)
        by_customer: dict[int, list[dict]] = {}
        for address in addresses:
            cid = int(address["id_customer"])
            by_customer.setdefault(cid, []).append(address)

        for cid, rows in by_customer.items():
            phone = pick_phone(rows)
            if phone:
                phone_by_customer[cid] = phone

        if index % 25 == 0 or index == len(batches):
            print(f"  enriched {min(index * BATCH_SIZE, len(customer_ids)):,}/{len(customer_ids):,} customers")

    print(f"API enrichment done in {time.time() - started:.1f}s")

    customers = pd.DataFrame(customer_rows)
    if customers.empty:
        raise RuntimeError("No customer records returned from PrestaShop API")

    customers["id_customer"] = customers["id"].astype(int)
    customers["email"] = customers["email"].astype(str).str.strip().str.lower()
    customers["first_name"] = customers.get("firstname")
    customers["last_name"] = customers.get("lastname")
    customers["phone"] = customers["id_customer"].map(phone_by_customer)
    customers["newsletter_agreed"] = customers["newsletter"].map(
        lambda value: "Yes" if str(value).strip() in {"1", "true", "True"} else "No"
    )

    merged = order_stats.merge(
        customers[["id_customer", "email", "first_name", "last_name", "phone", "newsletter_agreed"]],
        on="id_customer",
        how="left",
    )

    result = (
        merged.dropna(subset=["email"])
        .groupby("email", as_index=False)
        .agg(
            first_name=("first_name", "first"),
            last_name=("last_name", "first"),
            phone=("phone", "first"),
            newsletter_agreed=("newsletter_agreed", lambda values: "Yes" if "Yes" in set(values) else "No"),
            order_count=("order_count", "sum"),
            total_ordered=("total_ordered", "sum"),
            first_order=("first_order", "min"),
            last_order=("last_order", "max"),
            customer_ids=("id_customer", lambda values: ", ".join(map(str, sorted(set(map(int, values)))))),
        )
        .sort_values(["total_ordered", "order_count"], ascending=[False, False])
        .reset_index(drop=True)
    )

    return result[
        [
            "email",
            "newsletter_agreed",
            "phone",
            "first_name",
            "last_name",
            "order_count",
            "total_ordered",
            "first_order",
            "last_order",
            "customer_ids",
        ]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Presta customers with email and phone.")
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", DEFAULT_DB_NAME))
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / f"presta_customers_{datetime.now():%Y%m%d}.xlsx",
    )
    parser.add_argument("--env-file", type=Path, default=resolve_env_file())
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    api_url = os.environ.get("PRESTASHOP_API_URL", DEFAULT_API_URL).strip().rstrip("/")
    api_key = os.environ.get("PRESTASHOP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PRESTASHOP_API_KEY is not set")

    print("Loading order stats from Postgres...")
    order_stats = load_order_stats(args.db_name)
    print(f"  {len(order_stats):,} customers with orders")

    print("Fetching emails and phones from PrestaShop API...")
    result = enrich_customers(
        order_stats,
        api_url=api_url,
        auth=HTTPBasicAuth(api_key, ""),
    )

    result.to_excel(args.output, index=False, sheet_name="customers")
    print(f"Exported {len(result):,} emails -> {args.output}")
    print(result.head(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
