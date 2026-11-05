"""Fetch edonna.pl data and build customer_summary in memory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

API_BASE_URL = "https://www.edonna.pl/api/v1"
DEFAULT_TIMEZONE = "Europe/Warsaw"
DEFAULT_SYNC_LANG = "pl"

LIST_COLUMNS = [
    "user_id",
    "user_name",
    "company",
    "email",
    "lang",
    "registration_date",
    "days_since_registration",
    "order_count",
    "total_ordered",
    "days_since_last_order",
]

SEGMENTS = {
    "never_ordered_day_3": {
        "type": "registration_milestone",
        "days": 3,
        "never_ordered_only": True,
    },
    "day_7_from_registration": {
        "type": "registration_milestone",
        "days": 7,
        "never_ordered_only": False,
    },
    "day_14_from_registration": {
        "type": "registration_milestone",
        "days": 14,
        "never_ordered_only": False,
    },
    "never_ordered_day_60": {
        "type": "registration_milestone",
        "days": 60,
        "never_ordered_only": True,
    },
    "never_ordered_day_90": {
        "type": "registration_milestone",
        "days": 90,
        "never_ordered_only": True,
    },
    "never_ordered_all": {"type": "never_ordered_all"},
    "ordered_once_day_60": {
        "type": "registration_milestone",
        "days": 60,
        "never_ordered_only": False,
        "min_order_count": 1,
        "max_order_count": 1,
    },
    "inactive_90_days": {
        "type": "inactive",
        "min_days_since_last_order": 90,
        "max_days_since_last_order": 119,
    },
    "inactive_120_days": {
        "type": "inactive",
        "min_days_since_last_order": 120,
    },
    "all_customers": {"type": "all"},
}


def _edonna_headers() -> dict[str, str]:
    api_key = os.environ.get("EDONNA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("EDONNA_API_KEY is not set")
    return {
        "X-API-KEY": api_key,
        "User-Agent": "Donna-Integration/1.0",
    }


def _fetch_paginated(path: str, collection_key: str) -> list[dict[str, Any]]:
    page = 1
    items: list[dict[str, Any]] = []

    while True:
        response = requests.get(
            f"{API_BASE_URL}/{path}",
            headers=_edonna_headers(),
            params={"page": page},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        items.extend(data[collection_key])

        if len(items) >= data["total"]:
            break

        page += 1

    return items


def fetch_all_users() -> list[dict[str, Any]]:
    return _fetch_paginated("users", "users")


def fetch_all_orders() -> list[dict[str, Any]]:
    return _fetch_paginated("orders", "orders")


def build_customer_summary(
    users: list[dict[str, Any]] | None = None,
    orders: list[dict[str, Any]] | None = None,
    *,
    reference_time: pd.Timestamp | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> pd.DataFrame:
    users = users if users is not None else fetch_all_users()
    orders = orders if orders is not None else fetch_all_orders()

    users_df = pd.DataFrame(users).rename(columns={"id": "user_id"})
    orders_df = pd.DataFrame(orders).rename(columns={"sum": "order_total"})

    users_df["registration_date"] = pd.to_datetime(users_df["insert_date"], utc=True)
    orders_df["order_date"] = pd.to_datetime(orders_df["order_date"], utc=True)

    order_stats = (
        orders_df.groupby("user_id")
        .agg(
            total_ordered=("order_total", "sum"),
            order_count=("id", "count"),
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
        )
        .reset_index()
    )

    customer_summary = users_df.merge(order_stats, on="user_id", how="left")
    customer_summary["total_ordered"] = customer_summary["total_ordered"].fillna(0)
    customer_summary["order_count"] = customer_summary["order_count"].fillna(0).astype(int)

    customer_summary["first_order_date"] = pd.to_datetime(
        customer_summary["first_order_date"],
        utc=True,
        errors="coerce",
    )
    customer_summary["last_order_date"] = pd.to_datetime(
        customer_summary["last_order_date"],
        utc=True,
        errors="coerce",
    )

    if reference_time is None:
        reference_time = pd.Timestamp.now(tz=timezone)
    else:
        reference_time = reference_time.tz_convert(timezone)

    customer_summary["days_since_last_order"] = (
        reference_time.normalize()
        - customer_summary["last_order_date"].dt.tz_convert(timezone).dt.normalize()
    ).dt.days

    customer_summary["days_since_registration"] = (
        reference_time.normalize()
        - customer_summary["registration_date"].dt.tz_convert(timezone).dt.normalize()
    ).dt.days

    customer_summary["is_new_user"] = customer_summary["days_since_registration"] <= 7
    customer_summary["never_ordered"] = customer_summary["order_count"] == 0
    customer_summary["inactive_30d"] = (customer_summary["order_count"] > 0) & (
        customer_summary["days_since_last_order"] >= 30
    )
    customer_summary["inactive_60d"] = (customer_summary["order_count"] > 0) & (
        customer_summary["days_since_last_order"] >= 60
    )

    customer_summary = customer_summary.rename(columns={"name": "user_name"})
    customer_summary = customer_summary[
        [
            "user_id",
            "user_name",
            "company",
            "email",
            "lang",
            "group_id",
            "price_level_id",
            "registration_date",
            "days_since_registration",
            "total_ordered",
            "order_count",
            "first_order_date",
            "last_order_date",
            "days_since_last_order",
            "is_new_user",
            "never_ordered",
            "inactive_30d",
            "inactive_60d",
        ]
    ]

    return customer_summary.sort_values("total_ordered", ascending=False).reset_index(drop=True)


def normalize_lang(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower().split("_", maxsplit=1)[0]


def filter_by_lang(
    frame: pd.DataFrame,
    lang: str = DEFAULT_SYNC_LANG,
) -> pd.DataFrame:
    if frame.empty or "lang" not in frame.columns:
        return frame.iloc[0:0].copy()
    mask = frame["lang"].map(normalize_lang) == lang.strip().lower()
    return frame.loc[mask].copy()


def filter_registration_milestone(
    customer_summary: pd.DataFrame,
    *,
    days_since_registration: int,
    never_ordered_only: bool = True,
    min_order_count: int | None = None,
    max_order_count: int | None = None,
) -> pd.DataFrame:
    mask = customer_summary["days_since_registration"] == days_since_registration
    if never_ordered_only:
        mask &= customer_summary["never_ordered"]
    if min_order_count is not None:
        mask &= customer_summary["order_count"] >= min_order_count
    if max_order_count is not None:
        mask &= customer_summary["order_count"] <= max_order_count
    return customer_summary.loc[mask, LIST_COLUMNS].copy()


def filter_never_ordered(customer_summary: pd.DataFrame) -> pd.DataFrame:
    return customer_summary.loc[customer_summary["never_ordered"], LIST_COLUMNS].copy()


def filter_inactive_customers(
    customer_summary: pd.DataFrame,
    *,
    min_days_since_last_order: int,
    max_days_since_last_order: int | None = None,
) -> pd.DataFrame:
    mask = customer_summary["order_count"] > 0
    mask &= customer_summary["days_since_last_order"] >= min_days_since_last_order
    if max_days_since_last_order is not None:
        mask &= customer_summary["days_since_last_order"] <= max_days_since_last_order
    return customer_summary.loc[mask, LIST_COLUMNS].copy()


def filter_all_customers(customer_summary: pd.DataFrame) -> pd.DataFrame:
    return customer_summary.loc[:, LIST_COLUMNS].copy()


def build_segment(
    customer_summary: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    segment_type = config.get("type", "registration_milestone")

    if segment_type == "never_ordered_all":
        return filter_never_ordered(customer_summary)
    if segment_type == "all":
        return filter_all_customers(customer_summary)
    if segment_type == "registration_milestone":
        return filter_registration_milestone(
            customer_summary,
            days_since_registration=config["days"],
            never_ordered_only=config.get("never_ordered_only", True),
            min_order_count=config.get("min_order_count"),
            max_order_count=config.get("max_order_count"),
        )
    if segment_type == "inactive":
        return filter_inactive_customers(
            customer_summary,
            min_days_since_last_order=config["min_days_since_last_order"],
            max_days_since_last_order=config.get("max_days_since_last_order"),
        )

    raise ValueError(f"Unknown segment type: {segment_type}")


def generate_daily_lists(
    customer_summary: pd.DataFrame,
    *,
    segments: dict | None = None,
    lang: str | None = DEFAULT_SYNC_LANG,
) -> dict[str, pd.DataFrame]:
    segments = segments or SEGMENTS
    lists: dict[str, pd.DataFrame] = {}

    for name, config in segments.items():
        segment = build_segment(customer_summary, config)
        if lang is not None:
            segment = filter_by_lang(segment, lang)
        lists[name] = segment

    return lists


def default_env_file() -> Path:
    return Path(__file__).resolve().parents[1] / "platform_edu" / ".env"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch edonna data and print customer_summary stats (no files written).",
    )
    parser.add_argument(
        "--date",
        type=str,
        default="",
        help="Reference date YYYY-MM-DD (default: today in Europe/Warsaw)",
    )
    parser.add_argument("--env-file", type=Path, default=default_env_file())
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    if args.date:
        reference_time = pd.Timestamp(args.date, tz=DEFAULT_TIMEZONE)
        run_date = reference_time.date()
    else:
        reference_time = pd.Timestamp.now(tz=DEFAULT_TIMEZONE)
        run_date = reference_time.date()

    customer_summary = build_customer_summary(reference_time=reference_time)
    lists = generate_daily_lists(customer_summary)

    print(f"Reference date: {run_date.isoformat()} ({DEFAULT_TIMEZONE})")
    print(f"Total customers: {len(customer_summary)}")
    print(f"Language filter: {DEFAULT_SYNC_LANG}")
    print(f"Never ordered: {customer_summary['never_ordered'].sum()}")
    for name, frame in lists.items():
        print(f"{name}: {len(frame)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
