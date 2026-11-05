#!/usr/bin/env python3
"""Sync triso_users segment flags to Brevo lists.

Standalone server script — copy to:
  /home/ubuntu/scheduled_tasks/dn_sync_brevo_lists.py

Cron (daily at 5am Warsaw / 3am UTC in summer):
  0 3 * * * /usr/bin/python3 /home/ubuntu/scheduled_tasks/dn_sync_brevo_lists.py >> /home/ubuntu/scheduled_tasks/brevo_lists.log 2>&1
"""

from __future__ import annotations

import argparse
import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv

BREVO_API_BASE = "https://api.brevo.com/v3"
DEFAULT_TIMEZONE = "Europe/Warsaw"
DEFAULT_DB_NAME = "test_don"
DEFAULT_SYNC_LANG = "pl"
TABLE_NAME = "triso_users"
PROCESS_POLL_INTERVAL_SECONDS = 2
PROCESS_TIMEOUT_SECONDS = 120

# Brevo list ID -> triso_users flag column (or __all_users__ for full list)
ALL_USERS_SEGMENT = "__all_users__"
ALL_USERS_LIST_ID = 37
NEVER_ORDERED_ALL_TRISO_LIST_ID = 39
NEVER_ORDERED_ALL_TRISO_SEGMENT = "never_ordered_all_triso"
ORDERED_ALL_TRISO_LIST_ID = 40
ORDERED_ALL_TRISO_SEGMENT = "ordered_all_triso"
ALL_TRISO_LIST_ID = 41
ALL_TRISO_SEGMENT = "all_triso"

SPECIAL_BREVO_LISTS: dict[str, int] = {
    ALL_USERS_SEGMENT: ALL_USERS_LIST_ID,
    NEVER_ORDERED_ALL_TRISO_SEGMENT: NEVER_ORDERED_ALL_TRISO_LIST_ID,
    ORDERED_ALL_TRISO_SEGMENT: ORDERED_ALL_TRISO_LIST_ID,
    ALL_TRISO_SEGMENT: ALL_TRISO_LIST_ID,
}

FLAG_BREVO_LISTS: dict[str, int] = {
    ALL_USERS_SEGMENT: ALL_USERS_LIST_ID,
    "flag_reg_3d_never_ordered": 22,
    "flag_reg_10d_never_ordered": 23,
    "flag_reg_24d_never_ordered": 24,
    "flag_reg_60d_never_ordered": 25,
    "flag_reg_90d_never_ordered": 26,
    "flag_reg_120d_never_ordered": 27,
    "flag_reg_150d_never_ordered": 28,
    "flag_reg_180d_never_ordered": 29,
    "flag_reg_210d_never_ordered": 30,
    "never_ordered": 31,
    "flag_repeat_order_within_360d": 32,
    "flag_repeat_last_order_120_240_360d": 33,
    "flag_repeat_last_order_361d": 34,
    "flag_first_order_5d_ago": 35,
}

BREVO_LIST_NAMES: dict[int, str] = {
    22: "TRISO | Bez zamówienia | 3 dni",
    23: "TRISO | Bez zamówienia | 10 dni",
    24: "TRISO | Bez zamówienia | 24 dni",
    25: "TRISO | Bez zamówienia | 60 dni",
    26: "TRISO | Bez zamówienia | 90 dni",
    27: "TRISO | Bez zamówienia | 120 dni",
    28: "TRISO | Bez zamówienia | 150 dni",
    29: "TRISO | Bez zamówienia | 180 dni",
    30: "TRISO | Bez zamówienia | 210 dni",
    31: "TRISO | Bez zamówienia | WSZYSCY",
    32: "TRISO | Zamówienia | do 360",
    33: "TRISO | Zamówienia | 120/240/360 dni",
    34: "TRISO | Zamówienia | 361 dni",
    35: "TRISO | Pierwsze zamówienie 5 dni temu",
    37: "TRISO | WSZYSCY",
    39: "TRISO | Bez zamówienia | WSZYSCY (lista 39)",
    40: "TRISO | Zamówienia | WSZYSCY (lista 40)",
    41: "TRISO | WSZYSCY (lista 41)",
}


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


def normalize_lang(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower().split("_", maxsplit=1)[0]


def brevo_headers() -> dict[str, str]:
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not set")
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }


def wait_for_brevo_process(process_id: int, *, session: requests.Session) -> None:
    deadline = time.time() + PROCESS_TIMEOUT_SECONDS
    url = f"{BREVO_API_BASE}/processes/{process_id}"

    while time.time() < deadline:
        response = session.get(url, headers=brevo_headers(), timeout=30)
        if response.status_code == 404:
            # Process already completed and was purged from Brevo's queue.
            return
        response.raise_for_status()
        status = response.json().get("status")

        if status == "completed":
            return
        if status in {"error", "failed"}:
            raise RuntimeError(f"Brevo process {process_id} failed")

        time.sleep(PROCESS_POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Brevo process {process_id} did not complete in time")


def wait_for_list_empty(
    list_id: int,
    *,
    session: requests.Session,
    timeout_seconds: int = PROCESS_TIMEOUT_SECONDS,
) -> None:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if get_list_subscriber_count(list_id, session=session) == 0:
            return
        time.sleep(PROCESS_POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Brevo list {list_id} still has contacts after {timeout_seconds}s")


def list_already_empty_response(response: requests.Response) -> bool:
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    message = str(payload.get("message", "")).lower()
    return payload.get("code") == "invalid_parameter" and (
        "already removed" in message or "does not exist" in message
    )


def parse_remove_all_response(payload: dict) -> tuple[int | None, int]:
    contacts_info = payload.get("contacts")
    if isinstance(contacts_info, dict):
        process_id = contacts_info.get("processId")
        total = int(contacts_info.get("total") or 0)
        return (int(process_id) if process_id is not None else None), total

    process_id = payload.get("processId")
    total = int(payload.get("total", payload.get("count", 0)) or 0)
    return (int(process_id) if process_id is not None else None), total


def get_list_subscriber_count(list_id: int, *, session: requests.Session) -> int:
    url = f"{BREVO_API_BASE}/contacts/lists/{list_id}"
    response = session.get(url, headers=brevo_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    return int(data.get("uniqueSubscribers") or data.get("totalSubscribers") or 0)


def clear_brevo_list(
    list_id: int,
    *,
    session: requests.Session,
) -> tuple[bool, str, int, int, int]:
    before_count = get_list_subscriber_count(list_id, session=session)

    url = f"{BREVO_API_BASE}/contacts/lists/{list_id}/contacts/remove"
    response = session.post(
        url,
        json={"all": True},
        headers=brevo_headers(),
        timeout=30,
    )

    if list_already_empty_response(response):
        return True, "", 0, before_count, before_count

    if response.status_code not in (200, 201, 204):
        return False, f"{response.status_code} {response.text}", 0, before_count, before_count

    payload = response.json() if response.content else {}
    process_id, reported_removed = parse_remove_all_response(payload)

    if before_count > 0:
        if process_id is not None:
            try:
                wait_for_brevo_process(process_id, session=session)
            except TimeoutError:
                wait_for_list_empty(list_id, session=session)
        else:
            wait_for_list_empty(list_id, session=session)

    after_count = get_list_subscriber_count(list_id, session=session)
    removed = max(before_count - after_count, reported_removed)
    return True, "", removed, before_count, after_count


def clear_all_lists(list_ids: list[int]) -> dict[int, dict[str, int | str | bool]]:
    results: dict[int, dict[str, int | str | bool]] = {}

    with requests.Session() as session:
        for list_id in list_ids:
            ok, error, removed, before_count, after_count = clear_brevo_list(
                list_id,
                session=session,
            )
            results[list_id] = {
                "list_id": list_id,
                "cleared": ok,
                "before": before_count,
                "after": after_count,
                "removed": removed,
                "error": error,
            }
            if not ok:
                raise RuntimeError(f"Failed to clear Brevo list {list_id}: {error}")

    return results


def load_triso_users(*, db_name: str) -> pd.DataFrame:
    query = f"""
        SELECT
            user_id,
            full_name,
            first_name,
            last_name,
            company,
            email,
            phone,
            lang,
            registration_date,
            days_since_registration,
            order_count,
            total_ordered,
            first_order_date,
            last_order_date,
            days_since_first_order,
            days_since_last_order,
            never_ordered,
            flag_reg_3d_never_ordered,
            flag_reg_10d_never_ordered,
            flag_reg_24d_never_ordered,
            flag_reg_60d_never_ordered,
            flag_reg_90d_never_ordered,
            flag_reg_120d_never_ordered,
            flag_reg_150d_never_ordered,
            flag_reg_180d_never_ordered,
            flag_reg_210d_never_ordered,
            flag_first_order_5d_ago,
            flag_repeat_order_within_360d,
            flag_repeat_last_order_120_240_360d,
            flag_repeat_last_order_361d,
            flag_repeat_last_order_364d,
            last_update
        FROM {TABLE_NAME}
    """
    with connect(db_name) as conn:
        return pd.read_sql(query, conn)


def filter_by_lang(frame: pd.DataFrame, lang: str | None) -> pd.DataFrame:
    if not lang or frame.empty:
        return frame
    mask = frame["lang"].map(normalize_lang) == lang.strip().lower()
    return frame.loc[mask].copy()


def format_brevo_date(value: object) -> str | None:
    if pd.isna(value):
        return None
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def brevo_sms_value(phone: object) -> str | None:
    if pd.isna(phone) or not str(phone).strip():
        return None
    raw = re.sub(r"[\s\-().]", "", str(phone).strip())
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    elif not raw.startswith("+"):
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 9 and digits[0] in "456789":
            raw = "+48" + digits
        elif digits:
            raw = "+" + digits.lstrip("0")
        else:
            return None
    if not re.fullmatch(r"\+[1-9]\d{6,14}", raw):
        return None
    return raw


def contact_attributes(row: pd.Series) -> dict[str, object]:
    first_name = row.get("first_name") or row.get("full_name") or ""
    attributes: dict[str, object] = {
        "FIRSTNAME": first_name,
        "TOTAL_ORDERED": float(row.get("total_ordered") or 0),
        "ORDER_COUNT": int(row.get("order_count") or 0),
        "DAYS_SINCE_REGISTRATION": int(row.get("days_since_registration") or 0),
    }

    last_name = row.get("last_name")
    if pd.notna(last_name) and str(last_name).strip():
        attributes["LASTNAME"] = str(last_name).strip()

    lang = normalize_lang(row.get("lang"))
    if lang:
        attributes["LANG"] = lang

    registration_date = format_brevo_date(row.get("registration_date"))
    if registration_date:
        attributes["REGISTRATION_DATE"] = registration_date
        attributes["CREATION DATE"] = registration_date

    first_order_date = format_brevo_date(row.get("first_order_date"))
    if first_order_date:
        attributes["FIRST_ORDER_DATE"] = first_order_date

    last_order_date = format_brevo_date(row.get("last_order_date"))
    if last_order_date:
        attributes["LAST_ORDER_DATE"] = last_order_date

    days_since_first_order = row.get("days_since_first_order")
    if pd.notna(days_since_first_order):
        attributes["DAYS_SINCE_FIRST_ORDER"] = int(days_since_first_order)

    days_since_last_order = row.get("days_since_last_order")
    if pd.notna(days_since_last_order):
        attributes["DAYS_SINCE_LAST_ORDER"] = int(days_since_last_order)

    last_changed = format_brevo_date(row.get("last_update"))
    if last_changed:
        attributes["LAST_CHANGED"] = last_changed

    sms = brevo_sms_value(row.get("phone"))
    if sms:
        attributes["SMS"] = sms

    return attributes


def upsert_contact_to_list(
    row: pd.Series,
    list_id: int,
    *,
    session: requests.Session,
) -> tuple[bool, str]:
    email = row.get("email")
    if pd.isna(email) or not str(email).strip():
        return False, "missing email"

    payload = {
        "email": str(email).strip(),
        "attributes": contact_attributes(row),
        "updateEnabled": True,
        "listIds": [list_id],
    }

    response = session.post(
        f"{BREVO_API_BASE}/contacts",
        json=payload,
        headers=brevo_headers(),
        timeout=30,
    )

    if response.status_code in (200, 201, 204):
        return True, ""

    error_text = response.text
    if (
        response.status_code == 400
        and "Invalid phone number" in error_text
        and "SMS" in payload.get("attributes", {})
    ):
        retry_payload = {
            **payload,
            "attributes": {
                key: value
                for key, value in payload["attributes"].items()
                if key != "SMS"
            },
        }
        retry = session.post(
            f"{BREVO_API_BASE}/contacts",
            json=retry_payload,
            headers=brevo_headers(),
            timeout=30,
        )
        if retry.status_code in (200, 201, 204):
            return True, ""

    return False, f"{response.status_code} {error_text}"


def build_segment_frames(
    users: pd.DataFrame,
    *,
    lang: str | None = DEFAULT_SYNC_LANG,
) -> dict[str, pd.DataFrame]:
    filtered = filter_by_lang(users, lang)
    segments: dict[str, pd.DataFrame] = {}

    all_users = users.copy()
    all_users["brevo_list_id"] = ALL_USERS_LIST_ID
    segments[ALL_USERS_SEGMENT] = all_users

    never_ordered_all = users.loc[users["never_ordered"].fillna(False).astype(bool)].copy()
    never_ordered_all["brevo_list_id"] = NEVER_ORDERED_ALL_TRISO_LIST_ID
    segments[NEVER_ORDERED_ALL_TRISO_SEGMENT] = never_ordered_all

    ordered_all = users.loc[~users["never_ordered"].fillna(False).astype(bool)].copy()
    ordered_all["brevo_list_id"] = ORDERED_ALL_TRISO_LIST_ID
    segments[ORDERED_ALL_TRISO_SEGMENT] = ordered_all

    all_triso = users.copy()
    all_triso["brevo_list_id"] = ALL_TRISO_LIST_ID
    segments[ALL_TRISO_SEGMENT] = all_triso

    for flag_column, list_id in FLAG_BREVO_LISTS.items():
        if flag_column == ALL_USERS_SEGMENT:
            continue
        if flag_column not in filtered.columns:
            raise KeyError(f"Missing column in {TABLE_NAME}: {flag_column}")

        mask = filtered[flag_column].fillna(False).astype(bool)
        segment = filtered.loc[mask].copy()
        segment["brevo_list_id"] = list_id
        segments[flag_column] = segment

    return segments


def sync_segments_to_brevo(
    segments: dict[str, pd.DataFrame],
) -> dict[str, dict[str, int | list[str]]]:
    results: dict[str, dict[str, int | list[str]]] = {}

    with requests.Session() as session:
        for flag_column, frame in segments.items():
            if not frame.empty:
                list_id = int(frame["brevo_list_id"].iloc[0])
            elif flag_column in SPECIAL_BREVO_LISTS:
                list_id = SPECIAL_BREVO_LISTS[flag_column]
            else:
                list_id = FLAG_BREVO_LISTS[flag_column]
            uploaded = 0
            failed: list[str] = []

            for _, row in frame.iterrows():
                ok, error = upsert_contact_to_list(row, list_id, session=session)
                if ok:
                    uploaded += 1
                else:
                    failed.append(f"{row.get('email', '?')}: {error}")

            results[flag_column] = {
                "list_id": list_id,
                "matched": len(frame),
                "uploaded": uploaded,
                "failed": failed,
            }

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync triso_users segment flags to Brevo lists.",
    )
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", DEFAULT_DB_NAME))
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument(
        "--lang",
        default=DEFAULT_SYNC_LANG,
        help="Only sync contacts with this language (default: pl). Pass empty string for all.",
    )
    parser.add_argument(
        "--skip-clear",
        action="store_true",
        help="Skip clearing lists before upload (not recommended).",
    )
    parser.add_argument(
        "--list-id",
        type=int,
        default=None,
        help="Sync only this Brevo list ID (e.g. 37 for all TRISO users).",
    )
    args = parser.parse_args()

    env_file = args.env_file or resolve_env_file()
    if env_file.exists():
        load_dotenv(env_file)
        log(f"Loaded env from {env_file}")
    else:
        log(f"WARNING: env file not found at {env_file}")

    required = ("DB_HOST", "DB_PASSWORD", "BREVO_API_KEY")
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    if missing:
        log(
            f"ERROR: missing env vars: {', '.join(missing)}. "
            f"Set them in {env_file} or pass --env-file /path/to/.env"
        )
        return 1

    started = time.time()
    lang = args.lang.strip() or None

    try:
        users = load_triso_users(db_name=args.db_name)
        if users.empty:
            log(f"WARNING: no rows found in {args.db_name}.{TABLE_NAME}")
            return 0

        log(f"Loaded {len(users):,} users from {args.db_name}.{TABLE_NAME}")
        if users["last_update"].notna().any():
            log(f"Latest triso_users update: {users['last_update'].max()}")

        segments = build_segment_frames(users, lang=lang)

        if args.list_id is not None:
            if args.list_id == ALL_USERS_LIST_ID:
                segments = {ALL_USERS_SEGMENT: segments[ALL_USERS_SEGMENT]}
            elif args.list_id == NEVER_ORDERED_ALL_TRISO_LIST_ID:
                segments = {
                    NEVER_ORDERED_ALL_TRISO_SEGMENT: segments[NEVER_ORDERED_ALL_TRISO_SEGMENT],
                }
            elif args.list_id == ORDERED_ALL_TRISO_LIST_ID:
                segments = {ORDERED_ALL_TRISO_SEGMENT: segments[ORDERED_ALL_TRISO_SEGMENT]}
            elif args.list_id == ALL_TRISO_LIST_ID:
                segments = {ALL_TRISO_SEGMENT: segments[ALL_TRISO_SEGMENT]}
            else:
                segments = {
                    flag_column: frame
                    for flag_column, frame in segments.items()
                    if flag_column != ALL_USERS_SEGMENT
                    and not frame.empty
                    and int(frame["brevo_list_id"].iloc[0]) == args.list_id
                }
                if not segments:
                    matching = [
                        (flag, lid)
                        for flag, lid in FLAG_BREVO_LISTS.items()
                        if lid == args.list_id
                    ]
                    if not matching:
                        raise RuntimeError(f"Unknown Brevo list ID: {args.list_id}")
                    flag_column = matching[0][0]
                    empty = users.copy()
                    empty["brevo_list_id"] = args.list_id
                    segments = {flag_column: empty.iloc[0:0]}

            list_ids = [args.list_id]
            log(f"Single-list mode: #{args.list_id} {BREVO_LIST_NAMES.get(args.list_id, '')}")
        else:
            list_ids = sorted(set(FLAG_BREVO_LISTS.values()))

        if not args.skip_clear:
            log("Step 1: clearing Brevo lists...")
            clear_results = clear_all_lists(list_ids)
            for list_id in list_ids:
                stats = clear_results[list_id]
                name = BREVO_LIST_NAMES.get(list_id, str(list_id))
                log(f"  #{list_id} {name}: {stats['before']} -> {stats['after']} contacts")

        log("Step 2: segment counts...")
        if lang:
            log(f"  language filter for flag lists: {lang}")
        for flag_column, frame in segments.items():
            if flag_column in SPECIAL_BREVO_LISTS:
                list_id = SPECIAL_BREVO_LISTS[flag_column]
            else:
                list_id = FLAG_BREVO_LISTS[flag_column]
            name = BREVO_LIST_NAMES.get(list_id, flag_column)
            log(f"  #{list_id} {name}: {len(frame):,}")

        log("Step 3: uploading contacts to Brevo...")
        results = sync_segments_to_brevo(segments)

        for flag_column, stats in results.items():
            list_id = int(stats["list_id"])
            name = BREVO_LIST_NAMES.get(list_id, flag_column)
            log(
                f"  #{list_id} {name}: "
                f"{stats['uploaded']}/{stats['matched']} uploaded"
            )
            for failure in stats["failed"][:5]:
                log(f"    failed: {failure}")
            if len(stats["failed"]) > 5:
                log(f"    ... and {len(stats['failed']) - 5} more failures")

    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1

    log(f"Done in {time.time() - started:.1f}s ({DEFAULT_TIMEZONE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
