"""Export edonna.pl order line items to XLSX for a date range."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

API_BASE_URL = "https://www.edonna.pl/api/v1"

COLUMNS = [
    "order_date",
    "order_number",
    "order_status",
    "customer_name",
    "customer_email",
    "currency",
    "product_name",
    "symbol",
    "ean",
    "variant_id",
    "quantity",
    "original_price_unit",
    "sold_price_unit",
    "original_price_line",
    "sold_price_line",
    "rebate_percent",
]


def default_env_file() -> Path:
    return Path(__file__).resolve().parents[1] / "platform_edu" / ".env"


def _edonna_headers() -> dict[str, str]:
    api_key = os.environ.get("EDONNA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("EDONNA_API_KEY is not set")
    return {
        "X-API-KEY": api_key,
        "User-Agent": "Donna-Integration/1.0",
    }


def fetch_orders_in_range(date_from: str, date_to: str) -> list[dict[str, Any]]:
    page = 1
    orders: list[dict[str, Any]] = []

    while True:
        response = requests.get(
            f"{API_BASE_URL}/orders",
            headers=_edonna_headers(),
            params={"page": page, "date_from": date_from, "date_to": date_to},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        orders.extend(data["orders"])

        if len(orders) >= data["total"]:
            break
        page += 1

    return orders


def fetch_order_detail(order_id: int) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}/orders/{order_id}",
        headers=_edonna_headers(),
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


def build_order_lines(
    orders: list[dict[str, Any]],
    *,
    pause_seconds: float = 0.05,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for index, order in enumerate(orders, start=1):
        detail = fetch_order_detail(order["id"])
        customer = detail.get("customer") or {}
        currency = detail.get("currency_iso") or order.get("currency_iso") or ""

        for product in detail.get("products") or []:
            quantity = int(product.get("count") or 0)
            sold_unit = _as_float(product.get("price_gross"))
            original_unit = original_unit_price(product)
            rebate = _as_float(product.get("rebate")) or 0.0

            rows.append(
                {
                    "order_date": detail.get("order_date") or order.get("order_date"),
                    "order_number": detail.get("number") or order.get("number"),
                    "order_status": detail.get("status") or order.get("status"),
                    "customer_name": customer.get("name") or order.get("customer_name"),
                    "customer_email": customer.get("email") or order.get("customer_email"),
                    "currency": currency,
                    "product_name": (product.get("name") or "").replace("\n", " — "),
                    "symbol": product.get("symbol") or "",
                    "ean": product.get("ean") or "",
                    "variant_id": product.get("variant_id") or "",
                    "quantity": quantity,
                    "original_price_unit": original_unit,
                    "sold_price_unit": sold_unit,
                    "original_price_line": round(original_unit * quantity, 2)
                    if original_unit is not None
                    else None,
                    "sold_price_line": _as_float(product.get("price_gross_sum"))
                    or (round(sold_unit * quantity, 2) if sold_unit is not None else None),
                    "rebate_percent": rebate,
                }
            )

        if pause_seconds and index < len(orders):
            time.sleep(pause_seconds)

    return rows


def export_order_lines_xlsx(
    rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame = frame.sort_values(["order_date", "order_number", "product_name"]).reset_index(
        drop=True
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(output_path, index=False, sheet_name="order_lines", engine="openpyxl")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export edonna order line items to XLSX.",
    )
    parser.add_argument("--date-from", default="2026-05-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--date-to", default="2026-05-31", help="End date YYYY-MM-DD")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.home() / "Downloads" / "donna_order_lines_2026-05.xlsx",
    )
    parser.add_argument("--env-file", type=Path, default=default_env_file())
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    print(f"Fetching orders {args.date_from} .. {args.date_to} ...")
    orders = fetch_orders_in_range(args.date_from, args.date_to)
    print(f"Orders found: {len(orders):,}")

    if not orders:
        print("No orders in range.")
        return 1

    print("Fetching order details and building line items ...")
    rows = build_order_lines(orders)
    export_order_lines_xlsx(rows, args.output)

    print(f"Line items: {len(rows):,}")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
