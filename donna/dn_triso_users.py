#!/usr/bin/env python3
"""Sync edonna users into triso_users with segment flags.

Standalone server script — copy to:
  /home/ubuntu/scheduled_tasks/dn_triso_users.py

Cron (every 6 hours):
  0 */6 * * * /usr/bin/python3 /home/ubuntu/scheduled_tasks/dn_triso_users.py >> /home/ubuntu/scheduled_tasks/triso_users.log 2>&1
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

API_BASE_URL = "https://www.edonna.pl/api/v1"
DEFAULT_TIMEZONE = "Europe/Warsaw"
DEFAULT_DB_NAME = "test_don"
TABLE_NAME = "triso_users"
# edonna user.status: 1 = active. Inactive / deleted accounts are excluded from sync.
ACTIVE_EDONNA_USER_STATUS = 1

NEVER_ORDERED_REG_DAYS = (3, 10, 24, 60, 90, 120, 150, 180, 210)
REPEAT_LAST_ORDER_MILESTONE_DAYS = (120, 240, 360)

NEVER_ORDERED_FLAG_COLUMNS = [
    *(f"flag_reg_{days}d_never_ordered" for days in NEVER_ORDERED_REG_DAYS),
]

ORDERED_FLAG_COLUMNS = [
    "flag_first_order_5d_ago",
    "flag_repeat_order_within_360d",
    "flag_repeat_last_order_120_240_360d",
    "flag_repeat_last_order_361d",
    "flag_repeat_last_order_364d",
]

FLAG_COLUMNS = [*NEVER_ORDERED_FLAG_COLUMNS, *ORDERED_FLAG_COLUMNS]

DEPRECATED_FLAG_COLUMNS = (
    "flag_ordered_within_360d",
    "flag_ordered_361_390d",
    "flag_ordered_over_390d",
)

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    user_id BIGINT PRIMARY KEY,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    email TEXT,
    phone TEXT,
    lang TEXT,
    registration_date TIMESTAMP,
    days_since_registration INTEGER,
    order_count INTEGER,
    total_ordered NUMERIC(18, 2),
    first_order_date TIMESTAMP,
    last_order_date TIMESTAMP,
    days_since_first_order INTEGER,
    days_since_last_order INTEGER,
    never_ordered BOOLEAN,
    flag_reg_3d_never_ordered BOOLEAN,
    flag_reg_10d_never_ordered BOOLEAN,
    flag_reg_24d_never_ordered BOOLEAN,
    flag_reg_60d_never_ordered BOOLEAN,
    flag_reg_90d_never_ordered BOOLEAN,
    flag_reg_120d_never_ordered BOOLEAN,
    flag_reg_150d_never_ordered BOOLEAN,
    flag_reg_180d_never_ordered BOOLEAN,
    flag_reg_210d_never_ordered BOOLEAN,
    flag_first_order_5d_ago BOOLEAN,
    flag_repeat_order_within_360d BOOLEAN,
    flag_repeat_last_order_120_240_360d BOOLEAN,
    flag_repeat_last_order_361d BOOLEAN,
    flag_repeat_last_order_364d BOOLEAN,
    last_update TIMESTAMP
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


def fetch_all_users() -> list[dict[str, Any]]:
    return fetch_paginated("users", "users")


def fetch_all_orders() -> list[dict[str, Any]]:
    return fetch_paginated("orders", "orders")


def filter_active_edonna_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    for user in users:
        try:
            status = int(user.get("status"))
        except (TypeError, ValueError):
            continue
        if status == ACTIVE_EDONNA_USER_STATUS:
            active.append(user)
    return active


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

    summary = users_df.merge(order_stats, on="user_id", how="left")
    summary["total_ordered"] = summary["total_ordered"].fillna(0)
    summary["order_count"] = summary["order_count"].fillna(0).astype(int)
    summary["first_order_date"] = pd.to_datetime(summary["first_order_date"], utc=True, errors="coerce")
    summary["last_order_date"] = pd.to_datetime(summary["last_order_date"], utc=True, errors="coerce")

    if reference_time is None:
        reference_time = pd.Timestamp.now(tz=timezone)
    else:
        reference_time = reference_time.tz_convert(timezone)

    summary["days_since_last_order"] = (
        reference_time.normalize()
        - summary["last_order_date"].dt.tz_convert(timezone).dt.normalize()
    ).dt.days
    summary["days_since_registration"] = (
        reference_time.normalize()
        - summary["registration_date"].dt.tz_convert(timezone).dt.normalize()
    ).dt.days
    summary["never_ordered"] = summary["order_count"] == 0
    return summary.rename(columns={"name": "user_name"})


def split_name(full_name: object) -> tuple[str | None, str | None]:
    if pd.isna(full_name):
        return None, None
    text = str(full_name).strip()
    if not text:
        return None, None
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def apply_ordered_flags(frame: pd.DataFrame) -> None:
    repeat_orders = frame["order_count"] > 1
    last_order_days = frame["days_since_last_order"]

    frame["flag_first_order_5d_ago"] = (
        (frame["order_count"] == 1) & (frame["days_since_first_order"] == 5)
    )
    frame["flag_repeat_order_within_360d"] = repeat_orders & last_order_days.le(360)
    frame["flag_repeat_last_order_120_240_360d"] = repeat_orders & last_order_days.isin(
        REPEAT_LAST_ORDER_MILESTONE_DAYS
    )
    frame["flag_repeat_last_order_361d"] = repeat_orders & (last_order_days == 361)
    frame["flag_repeat_last_order_364d"] = repeat_orders & (last_order_days == 364)


def build_triso_users_frame(
    *,
    reference_time: pd.Timestamp | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> pd.DataFrame:
    raw_users = fetch_all_users()
    users_list = filter_active_edonna_users(raw_users)
    if len(users_list) != len(raw_users):
        log(
            f"Excluded {len(raw_users) - len(users_list):,} non-active TRISO users "
            f"(only status={ACTIVE_EDONNA_USER_STATUS} is synced)"
        )
    orders_list = fetch_all_orders()
    summary = build_customer_summary(
        users_list,
        orders_list,
        reference_time=reference_time,
        timezone=timezone,
    )

    users = pd.DataFrame(users_list).rename(columns={"id": "user_id"})
    if "phone" not in users.columns:
        users["phone"] = None
    if "phone" in summary.columns:
        summary = summary.drop(columns=["phone"])

    frame = summary.merge(users[["user_id", "phone"]], on="user_id", how="left")
    first_last = frame["user_name"].map(split_name)
    frame["full_name"] = frame["user_name"]
    frame["first_name"] = [pair[0] for pair in first_last]
    frame["last_name"] = [pair[1] for pair in first_last]

    ref = reference_time or pd.Timestamp.now(tz=timezone)
    frame["days_since_first_order"] = (
        ref.normalize() - frame["first_order_date"].dt.tz_convert(timezone).dt.normalize()
    ).dt.days

    for days in NEVER_ORDERED_REG_DAYS:
        frame[f"flag_reg_{days}d_never_ordered"] = (
            frame["never_ordered"] & (frame["days_since_registration"] == days)
        )

    apply_ordered_flags(frame)
    frame["last_update"] = pd.Timestamp.utcnow().tz_localize(None)

    output = frame[
        [
            "user_id", "full_name", "first_name", "last_name", "company", "email", "phone", "lang",
            "registration_date", "days_since_registration", "order_count", "total_ordered",
            "first_order_date", "last_order_date", "days_since_first_order", "days_since_last_order",
            "never_ordered", *FLAG_COLUMNS, "last_update",
        ]
    ].copy()

    for col in FLAG_COLUMNS + ["never_ordered"]:
        output[col] = output[col].fillna(False).astype(bool)

    for col in ("days_since_registration", "order_count", "days_since_first_order", "days_since_last_order"):
        output[col] = pd.to_numeric(output[col], errors="coerce").astype("Int64")

    for col in ("registration_date", "first_order_date", "last_order_date", "last_update"):
        output[col] = pd.to_datetime(output[col], errors="coerce")

    output["total_ordered"] = pd.to_numeric(output["total_ordered"], errors="coerce")
    return output.replace({pd.NaT: None}).where(pd.notna(output), None)


def ensure_table_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        cur.execute(
            f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS last_update TIMESTAMP"
        )
        for column in ORDERED_FLAG_COLUMNS:
            cur.execute(
                f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS {column} BOOLEAN"
            )
        for column in DEPRECATED_FLAG_COLUMNS:
            cur.execute(f"ALTER TABLE {TABLE_NAME} DROP COLUMN IF EXISTS {column}")
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = 'synced_at'
            """,
            (TABLE_NAME,),
        )
        if cur.fetchone():
            cur.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET last_update = synced_at
                WHERE last_update IS NULL AND synced_at IS NOT NULL
                """
            )
            cur.execute(f"ALTER TABLE {TABLE_NAME} DROP COLUMN IF EXISTS synced_at")


def upsert_triso_users(frame: pd.DataFrame, *, db_name: str, replace: bool = False) -> int:
    if frame.empty:
        return 0

    columns = list(frame.columns)
    update_columns = [col for col in columns if col != "user_id"]
    set_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_columns)

    with connect(db_name) as conn:
        ensure_table_schema(conn)
        with conn.cursor() as cur:
            if replace:
                cur.execute(f"TRUNCATE TABLE {TABLE_NAME}")
            rows = [tuple(row[col] for col in columns) for _, row in frame.iterrows()]
            upsert_sql = f"""
                INSERT INTO {TABLE_NAME} ({', '.join(columns)})
                VALUES %s
                ON CONFLICT (user_id) DO UPDATE SET {set_clause}
            """
            execute_values(cur, upsert_sql, rows, page_size=200)
        conn.commit()

    return len(frame)


def prune_stale_users(active_user_ids: list[int], *, db_name: str) -> int:
    """Remove DB rows no longer in live edonna (deleted / deactivated)."""
    if not active_user_ids:
        return 0

    with connect(db_name) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {TABLE_NAME} WHERE NOT (user_id = ANY(%s))",
                (active_user_ids,),
            )
            deleted = cur.rowcount
        conn.commit()

    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync edonna users into triso_users.")
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", DEFAULT_DB_NAME))
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate triso_users before inserting fresh data.",
    )
    parser.add_argument("--env-file", type=Path, default=None)
    args = parser.parse_args()

    env_file = args.env_file or resolve_env_file()
    if env_file.exists():
        load_dotenv(env_file)
        log(f"Loaded env from {env_file}")
    else:
        log(f"WARNING: env file not found at {env_file}")

    required = ("DB_HOST", "DB_PASSWORD", "EDONNA_API_KEY")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        log(
            f"ERROR: missing env vars: {', '.join(missing)}. "
            f"Set them in {env_file} or pass --env-file /path/to/.env"
        )
        return 1

    started = time.time()
    reference_time = pd.Timestamp.now(tz=DEFAULT_TIMEZONE)
    try:
        frame = build_triso_users_frame(reference_time=reference_time)
        count = upsert_triso_users(frame, db_name=args.db_name, replace=args.replace)
        if args.replace:
            pruned = 0
        else:
            pruned = prune_stale_users(
                frame["user_id"].astype(int).tolist(),
                db_name=args.db_name,
            )
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1

    log(f"Reference date: {reference_time.date().isoformat()} ({DEFAULT_TIMEZONE})")
    log(f"Upserted {count:,} rows into {args.db_name}.{TABLE_NAME}")
    if not args.replace:
        log(f"Removed {pruned:,} stale rows not in live edonna")
    log(f"Total active users fetched: {len(frame):,}")
    for col in FLAG_COLUMNS:
        log(f"  {col}: {int(frame[col].sum()):,}")
    log(f"Done in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
