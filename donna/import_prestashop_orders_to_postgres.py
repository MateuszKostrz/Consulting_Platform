"""Load PrestaShop orders XLSX sheets into PostgreSQL."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / "platform_edu" / ".env"
DEFAULT_XLSX = Path.home() / "Downloads" / "prestashop_orders_full_2026-06-01.xlsx"
DEFAULT_DB_NAME = "test_don"
ORDERS_TABLE = "presta_orders"
DETAILED_TABLE = "presta_detailed_orders"

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


def connect(db_name: str):
    return psycopg2.connect(
        host=os.environ["DB_HOST"].strip("'"),
        user=os.environ.get("DB_USER", "mateuszkostrz"),
        password=os.environ["DB_PASSWORD"].strip("'"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=db_name,
    )


def load_orders_frame(xlsx_path: Path) -> pd.DataFrame:
    frame = pd.read_excel(xlsx_path, sheet_name="orders")
    for col in ("date_add", "date_upd", "invoice_date", "delivery_date"):
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame.replace({pd.NaT: None}).where(pd.notna(frame), None)


def load_detailed_frame(xlsx_path: Path) -> pd.DataFrame:
    frame = pd.read_excel(xlsx_path, sheet_name="order_lines")
    for col in (
        "order_date_add",
        "order_date_upd",
        "order_invoice_date",
        "order_delivery_date",
    ):
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")

    text_cols = (
        "line_product_reference",
        "line_product_ean13",
        "line_product_isbn",
        "line_product_upc",
        "order_shipping_number",
        "order_inpost_point",
    )
    for col in text_cols:
        if col in frame.columns:
            frame[col] = frame[col].apply(
                lambda value: None
                if pd.isna(value)
                else str(int(value))
                if isinstance(value, float) and value.is_integer()
                else str(value)
            )

    return frame.replace({pd.NaT: None}).where(pd.notna(frame), None)


def _import_frame(
    frame: pd.DataFrame,
    *,
    db_name: str,
    table_name: str,
    create_sql: str,
    replace: bool,
) -> int:
    columns = list(frame.columns)

    with connect(db_name) as conn:
        with conn.cursor() as cur:
            if replace:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            cur.execute(create_sql)
            if replace:
                cur.execute(f"TRUNCATE TABLE {table_name}")
            else:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                existing = cur.fetchone()[0]
                if existing:
                    raise RuntimeError(
                        f"{table_name} already has {existing} rows. "
                        "Use --replace to reload."
                    )

            rows = [tuple(row[col] for col in columns) for _, row in frame.iterrows()]
            insert_sql = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES %s
            """
            execute_values(cur, insert_sql, rows, page_size=200)
        conn.commit()

    return len(frame)


def upsert_orders_frame(
    frame: pd.DataFrame,
    *,
    db_name: str,
) -> tuple[int, int]:
    """Insert or update orders by primary key. Returns (upserted, total)."""
    if frame.empty:
        return 0, 0

    columns = list(frame.columns)
    if "id" not in columns:
        raise ValueError("orders frame must include id column")

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

    return len(frame), len(frame)


def import_orders(
    xlsx_path: Path,
    *,
    db_name: str,
    replace: bool = False,
) -> int:
    return _import_frame(
        load_orders_frame(xlsx_path),
        db_name=db_name,
        table_name=ORDERS_TABLE,
        create_sql=CREATE_ORDERS_TABLE_SQL,
        replace=replace,
    )


def import_detailed_orders(
    xlsx_path: Path,
    *,
    db_name: str,
    replace: bool = False,
) -> int:
    return _import_frame(
        load_detailed_frame(xlsx_path),
        db_name=db_name,
        table_name=DETAILED_TABLE,
        create_sql=CREATE_DETAILED_TABLE_SQL,
        replace=replace,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import PrestaShop XLSX sheets into PostgreSQL.",
    )
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument(
        "--sheet",
        choices=("orders", "detailed", "all"),
        default="orders",
        help="Which sheet to import (default: orders).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Drop and recreate table before import.",
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    if not args.xlsx.exists():
        raise SystemExit(f"XLSX not found: {args.xlsx}")

    if args.sheet in ("orders", "all"):
        count = import_orders(args.xlsx, db_name=args.db_name, replace=args.replace)
        print(f"Imported {count:,} rows into {args.db_name}.{ORDERS_TABLE}")

    if args.sheet in ("detailed", "all"):
        count = import_detailed_orders(
            args.xlsx,
            db_name=args.db_name,
            replace=args.replace,
        )
        print(f"Imported {count:,} rows into {args.db_name}.{DETAILED_TABLE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
