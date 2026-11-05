"""Export PrestaShop (donna.pl) order line items to XLSX for a date range."""

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

DEFAULT_API_URL = "https://donna.pl/api"
DEFAULT_PAID_STATES = (2, 4)
DEFAULT_PAGE_SIZE = 100
DISCOUNT_TOLERANCE = 0.01
DEFAULT_PARALLEL_WORKERS = 10

COLUMNS = [
    "order_date",
    "order_id",
    "order_reference",
    "order_status_id",
    "order_total_paid",
    "product_id",
    "product_reference",
    "product_ean",
    "product_name",
    "quantity",
    "original_price_unit",
    "sold_price_unit",
    "unit_price_diff",
    "has_discount",
    "discount_percent",
    "pricing",
    "original_price_line",
    "sold_price_line",
    "line_price_diff",
]


def default_env_file() -> Path:
    return Path(__file__).resolve().parents[1] / "platform_edu" / ".env"


def _api_auth() -> HTTPBasicAuth:
    api_key = os.environ.get("PRESTASHOP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PRESTASHOP_API_KEY is not set")
    return HTTPBasicAuth(api_key, "")


def _api_url() -> str:
    return os.environ.get("PRESTASHOP_API_URL", DEFAULT_API_URL).rstrip("/")


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def original_unit_price_tax_incl(row: dict[str, Any]) -> float | None:
    """Catalog unit price incl. tax, derived from PrestaShop product_price."""
    product_price = _as_float(row.get("product_price"))
    unit_excl = _as_float(row.get("unit_price_tax_excl"))
    unit_incl = _as_float(row.get("unit_price_tax_incl"))
    if product_price is None or unit_incl is None:
        return None
    if unit_excl and unit_excl > 0:
        return round(product_price * (unit_incl / unit_excl), 2)
    return round(unit_incl, 2)


def fetch_orders_in_range(
    date_from: str,
    date_to: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    offset = 0

    while True:
        response = requests.get(
            f"{_api_url()}/orders",
            params={
                "output_format": "JSON",
                "display": "[id,date_add,total_paid_tax_incl,current_state,reference]",
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

        orders.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size

    return orders


def fetch_order_detail(order_id: int | str) -> dict[str, Any]:
    response = requests.get(
        f"{_api_url()}/orders/{order_id}",
        params={"output_format": "JSON"},
        auth=_api_auth(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("order") or {}


def filter_paid_orders(
    orders: list[dict[str, Any]],
    paid_states: tuple[int, ...],
) -> list[dict[str, Any]]:
    allowed = set(paid_states)
    return [order for order in orders if int(order.get("current_state") or 0) in allowed]


def _rows_from_order(
    order: dict[str, Any],
    detail: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    products = detail.get("associations", {}).get("order_rows") or []

    for product in products:
        quantity = int(_as_float(product.get("product_quantity")) or 0)
        sold_unit = _as_float(product.get("unit_price_tax_incl"))
        original_unit = original_unit_price_tax_incl(product)

        rows.append(
            {
                "order_date": order.get("date_add") or detail.get("date_add"),
                "order_id": order.get("id") or detail.get("id"),
                "order_reference": order.get("reference") or detail.get("reference") or "",
                "order_status_id": order.get("current_state") or detail.get("current_state"),
                "order_total_paid": _as_float(
                    order.get("total_paid_tax_incl") or detail.get("total_paid_tax_incl")
                ),
                "product_id": product.get("product_id") or "",
                "product_reference": product.get("product_reference") or "",
                "product_ean": product.get("product_ean13") or "",
                "product_name": (product.get("product_name") or "").replace("\n", " — "),
                "quantity": quantity,
                "original_price_unit": original_unit,
                "sold_price_unit": sold_unit,
                "original_price_line": round(original_unit * quantity, 2)
                if original_unit is not None
                else None,
                "sold_price_line": round(sold_unit * quantity, 2)
                if sold_unit is not None
                else None,
            }
        )

    return rows


def build_order_lines(
    orders: list[dict[str, Any]],
    *,
    pause_seconds: float = 0.0,
    max_workers: int = DEFAULT_PARALLEL_WORKERS,
    progress_every: int = 100,
) -> list[dict[str, Any]]:
    if not orders:
        return []

    rows: list[dict[str, Any]] = []
    total = len(orders)
    done = 0

    if max_workers <= 1:
        for index, order in enumerate(orders, start=1):
            detail = fetch_order_detail(order["id"])
            rows.extend(_rows_from_order(order, detail))
            done = index
            if progress_every and (done % progress_every == 0 or done == total):
                print(f"  Order details: {done:,}/{total:,}")
            if pause_seconds and index < total:
                time.sleep(pause_seconds)
        return rows

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_order_detail, order["id"]): order for order in orders
        }
        for future in as_completed(futures):
            order = futures[future]
            detail = future.result()
            rows.extend(_rows_from_order(order, detail))
            done += 1
            if progress_every and (done % progress_every == 0 or done == total):
                print(f"  Order details: {done:,}/{total:,}")

    return rows


def enrich_discount_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Mark discount when original_price_unit > sold_price_unit."""
    enriched = frame.copy()
    for col in (
        "original_price_unit",
        "sold_price_unit",
        "original_price_line",
        "sold_price_line",
    ):
        enriched[col] = pd.to_numeric(enriched[col], errors="coerce")

    enriched["unit_price_diff"] = (
        enriched["original_price_unit"] - enriched["sold_price_unit"]
    ).round(2)
    enriched["line_price_diff"] = (
        enriched["original_price_line"] - enriched["sold_price_line"]
    ).round(2)
    enriched["has_discount"] = enriched["unit_price_diff"] > DISCOUNT_TOLERANCE
    enriched["discount_percent"] = enriched.apply(
        lambda row: round(row["unit_price_diff"] / row["original_price_unit"] * 100, 1)
        if row["has_discount"] and row["original_price_unit"] > 0
        else 0.0,
        axis=1,
    )
    enriched["pricing"] = enriched["has_discount"].map(
        {True: "discount", False: "full price"}
    )
    return enriched


def build_revenue_summary(
    frame: pd.DataFrame,
    *,
    date_from: str,
    date_to: str,
) -> pd.DataFrame:
    discounted = frame[frame["has_discount"]]
    full_price = frame[~frame["has_discount"]]

    sold_disc = discounted["sold_price_line"].sum()
    sold_full = full_price["sold_price_line"].sum()
    sold_total = frame["sold_price_line"].sum()
    orig_total = frame["original_price_line"].sum()
    saved_total = orig_total - sold_total

    orders_total = frame["order_id"].nunique()
    orders_with_discount = frame.groupby("order_id")["has_discount"].any().sum()

    def pct(part: float, whole: float) -> float:
        return round(part / whole * 100, 1) if whole else 0.0

    rows = [
        ("Period", f"{date_from} to {date_to}"),
        ("", ""),
        ("LINE ITEMS", ""),
        ("Total line items", len(frame)),
        ("Discounted line items", len(discounted)),
        ("Full price line items", len(full_price)),
        ("Discounted lines (% of items)", pct(len(discounted), len(frame))),
        ("", ""),
        ("ORDERS", ""),
        ("Total paid orders", orders_total),
        ("Orders with at least 1 discount", int(orders_with_discount)),
        ("Orders with no discounts", int(orders_total - orders_with_discount)),
        ("", ""),
        ("REVENUE (sold_price_line)", ""),
        ("Total revenue (PLN)", round(sold_total, 2)),
        ("Revenue from discounted items (PLN)", round(sold_disc, 2)),
        ("Revenue from full price items (PLN)", round(sold_full, 2)),
        ("Discounted revenue share (%)", pct(sold_disc, sold_total)),
        ("Full price revenue share (%)", pct(sold_full, sold_total)),
        ("", ""),
        ("CATALOG VALUE (original_price_line)", ""),
        ("Total catalog value (PLN)", round(orig_total, 2)),
        ("Catalog value of discounted items (PLN)", round(discounted["original_price_line"].sum(), 2)),
        ("Catalog value of full price items (PLN)", round(full_price["original_price_line"].sum(), 2)),
        ("", ""),
        ("DISCOUNT IMPACT", ""),
        ("Total saved by customers (PLN)", round(saved_total, 2)),
        ("Total saved (% of catalog)", pct(saved_total, orig_total)),
        (
            "Avg discount on discounted lines (%)",
            round(discounted["discount_percent"].mean(), 1) if len(discounted) else 0.0,
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def export_order_lines_xlsx(
    rows: list[dict[str, Any]],
    output_path: Path,
    *,
    date_from: str,
    date_to: str,
) -> None:
    frame = pd.DataFrame(rows)
    frame["order_date"] = pd.to_datetime(frame["order_date"], errors="coerce")
    frame = enrich_discount_columns(frame)
    frame = frame.sort_values(["order_date", "order_id", "product_name"]).reset_index(
        drop=True
    )
    summary = build_revenue_summary(frame, date_from=date_from, date_to=date_to)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        frame[COLUMNS].to_excel(writer, index=False, sheet_name="order_lines")
        summary.to_excel(writer, index=False, sheet_name="revenue_summary")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export PrestaShop order line items to XLSX.",
    )
    parser.add_argument("--date-from", default="2026-05-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--date-to", default="2026-05-31", help="End date YYYY-MM-DD")
    parser.add_argument(
        "--paid-states",
        default=",".join(str(state) for state in DEFAULT_PAID_STATES),
        help="Comma-separated PrestaShop current_state IDs (default: 2,4)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.home() / "Downloads" / "donna_order_lines_prestashop_2026-05.xlsx",
    )
    parser.add_argument("--env-file", type=Path, default=default_env_file())
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    paid_states = tuple(
        int(value.strip())
        for value in args.paid_states.split(",")
        if value.strip()
    )

    print(f"Fetching PrestaShop orders {args.date_from} .. {args.date_to} ...")
    orders = fetch_orders_in_range(args.date_from, args.date_to)
    print(f"Orders in range: {len(orders):,}")

    paid_orders = filter_paid_orders(orders, paid_states)
    print(f"Paid orders (states {paid_states}): {len(paid_orders):,}")

    if not paid_orders:
        print("No paid orders in range.")
        return 1

    print("Fetching order details and building line items ...")
    rows = build_order_lines(paid_orders)
    export_order_lines_xlsx(rows, args.output, date_from=args.date_from, date_to=args.date_to)

    frame = enrich_discount_columns(pd.DataFrame(rows))
    sold_disc = frame.loc[frame["has_discount"], "sold_price_line"].sum()
    sold_total = frame["sold_price_line"].sum()
    print(f"Line items: {len(rows):,}")
    print(
        f"Revenue share — discount: {sold_disc / sold_total * 100:.1f}% | "
        f"full price: {(sold_total - sold_disc) / sold_total * 100:.1f}%"
    )
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
