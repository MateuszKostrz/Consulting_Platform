"""Monthly discount vs full-price revenue share from PrestaShop orders."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from export_prestashop_order_lines import (
    DEFAULT_PAID_STATES,
    build_order_lines,
    default_env_file,
    enrich_discount_columns,
    fetch_orders_in_range,
    filter_paid_orders,
)


def month_ranges(year: int, month_from: int, month_to: int) -> list[tuple[str, str, str]]:
    ranges: list[tuple[str, str, str]] = []
    for month in range(month_from, month_to + 1):
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year}-12-31"
        else:
            next_month = pd.Timestamp(year=year, month=month + 1, day=1)
            end = (next_month - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        label = f"{year}-{month:02d}"
        ranges.append((label, start, end))
    return ranges


def summarize_month(frame: pd.DataFrame, *, label: str) -> dict[str, object]:
    discounted = frame[frame["has_discount"]]
    full_price = frame[~frame["has_discount"]]

    sold_disc = discounted["sold_price_line"].sum()
    sold_full = full_price["sold_price_line"].sum()
    sold_total = frame["sold_price_line"].sum()
    orig_total = frame["original_price_line"].sum()

    def pct(part: float, whole: float) -> float:
        return round(part / whole * 100, 1) if whole else 0.0

    return {
        "month": label,
        "paid_orders": frame["order_id"].nunique(),
        "line_items": len(frame),
        "discounted_lines": len(discounted),
        "full_price_lines": len(full_price),
        "discounted_lines_pct": pct(len(discounted), len(frame)),
        "total_revenue_pln": round(sold_total, 2),
        "discounted_revenue_pln": round(sold_disc, 2),
        "full_price_revenue_pln": round(sold_full, 2),
        "discounted_revenue_share_pct": pct(sold_disc, sold_total),
        "full_price_revenue_share_pct": pct(sold_full, sold_total),
        "catalog_value_pln": round(orig_total, 2),
        "customer_savings_pln": round(orig_total - sold_total, 2),
        "avg_discount_on_discounted_lines_pct": round(discounted["discount_percent"].mean(), 1)
        if len(discounted)
        else 0.0,
    }


def print_month_summary(row: dict[str, object]) -> None:
    print(f"\n{row['month']}")
    print(f"  Paid orders:              {row['paid_orders']:,}")
    print(f"  Line items:               {row['line_items']:,}")
    print(
        f"  Discounted revenue share: {row['discounted_revenue_share_pct']}%  "
        f"({row['discounted_revenue_pln']:,.2f} PLN)"
    )
    print(
        f"  Full price revenue share: {row['full_price_revenue_share_pct']}%  "
        f"({row['full_price_revenue_pln']:,.2f} PLN)"
    )
    print(f"  Total revenue:            {row['total_revenue_pln']:,.2f} PLN")


def empty_summary(label: str) -> dict[str, object]:
    return {
        "month": label,
        "paid_orders": 0,
        "line_items": 0,
        "discounted_lines": 0,
        "full_price_lines": 0,
        "discounted_lines_pct": 0.0,
        "total_revenue_pln": 0.0,
        "discounted_revenue_pln": 0.0,
        "full_price_revenue_pln": 0.0,
        "discounted_revenue_share_pct": 0.0,
        "full_price_revenue_share_pct": 0.0,
        "catalog_value_pln": 0.0,
        "customer_savings_pln": 0.0,
        "avg_discount_on_discounted_lines_pct": 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Monthly PrestaShop revenue share (discount vs full price).",
    )
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month-from", type=int, default=1)
    parser.add_argument("--month-to", type=int, default=6)
    parser.add_argument(
        "--paid-states",
        default=",".join(str(state) for state in DEFAULT_PAID_STATES),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.home() / "Downloads" / "donna_revenue_share_2026_jan_jun.xlsx",
    )
    parser.add_argument("--env-file", type=Path, default=default_env_file())
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    paid_states = tuple(
        int(value.strip()) for value in args.paid_states.split(",") if value.strip()
    )
    ranges = month_ranges(args.year, args.month_from, args.month_to)
    date_from = ranges[0][1]
    date_to = ranges[-1][2]

    print(f"Fetching paid orders {date_from} .. {date_to} (parallel, {args.workers} workers) ...")
    orders = fetch_orders_in_range(date_from, date_to)
    paid_orders = filter_paid_orders(orders, paid_states)
    print(f"Paid orders: {len(paid_orders):,}")

    if not paid_orders:
        print("No paid orders in range.")
        return 1

    rows = build_order_lines(paid_orders, max_workers=args.workers)
    frame = enrich_discount_columns(pd.DataFrame(rows))
    frame["order_date"] = pd.to_datetime(frame["order_date"], errors="coerce")
    frame["month"] = frame["order_date"].dt.to_period("M").astype(str)

    summaries: list[dict[str, object]] = []
    for label, _, _ in ranges:
        month_frame = frame[frame["month"] == label]
        if month_frame.empty:
            summaries.append(empty_summary(label))
            continue
        summary = summarize_month(month_frame, label=label)
        summaries.append(summary)
        print_month_summary(summary)

    summary_df = pd.DataFrame(summaries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="revenue_by_month")

    print(f"\nWrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
