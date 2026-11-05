"""Add registration-milestone contacts to Brevo lists."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from build_customer_summary import (
    DEFAULT_SYNC_LANG,
    build_customer_summary,
    default_env_file,
    generate_daily_lists,
    normalize_lang,
)

BREVO_API_BASE = "https://api.brevo.com/v3"
DEFAULT_TIMEZONE = "Europe/Warsaw"
PROCESS_POLL_INTERVAL_SECONDS = 2
PROCESS_TIMEOUT_SECONDS = 120

SEGMENT_BREVO_LISTS = {
    "never_ordered_day_3": 12,
    "day_7_from_registration": 13,
    "day_14_from_registration": 14,
    "never_ordered_day_60": 15,
    "never_ordered_day_90": 16,
    "never_ordered_all": 17,
    "ordered_once_day_60": 18,
    "inactive_90_days": 19,
    "inactive_120_days": 20,
    "all_customers": 21,
}


def _brevo_headers() -> dict[str, str]:
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not set")
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }


def _wait_for_brevo_process(process_id: int, *, session: requests.Session) -> None:
    deadline = time.time() + PROCESS_TIMEOUT_SECONDS
    url = f"{BREVO_API_BASE}/processes/{process_id}"

    while time.time() < deadline:
        response = session.get(url, headers=_brevo_headers(), timeout=30)
        response.raise_for_status()
        status = response.json().get("status")

        if status == "completed":
            return
        if status in {"error", "failed"}:
            raise RuntimeError(f"Brevo process {process_id} failed")

        time.sleep(PROCESS_POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Brevo process {process_id} did not complete in time")


def _list_already_empty_response(response: requests.Response) -> bool:
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


def _parse_remove_all_response(payload: dict) -> tuple[int | None, int]:
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
    response = session.get(url, headers=_brevo_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    return int(data.get("uniqueSubscribers") or data.get("totalSubscribers") or 0)


def clear_brevo_list(
    list_id: int,
    *,
    session: requests.Session,
) -> tuple[bool, str, int, int, int]:
    """Remove all contacts from a Brevo list.

    Returns (ok, error, removed_count, before_count, after_count).
    """
    before_count = get_list_subscriber_count(list_id, session=session)

    url = f"{BREVO_API_BASE}/contacts/lists/{list_id}/contacts/remove"
    response = session.post(
        url,
        json={"all": True},
        headers=_brevo_headers(),
        timeout=30,
    )

    if _list_already_empty_response(response):
        return True, "", 0, before_count, before_count

    if response.status_code not in (200, 201, 204):
        return False, f"{response.status_code} {response.text}", 0, before_count, before_count

    payload = response.json() if response.content else {}
    process_id, reported_removed = _parse_remove_all_response(payload)
    if process_id is not None:
        _wait_for_brevo_process(process_id, session=session)

    after_count = get_list_subscriber_count(list_id, session=session)
    removed = max(before_count - after_count, reported_removed)
    return True, "", removed, before_count, after_count


def clear_all_lists(
    segment_lists: dict[str, int] | None = None,
) -> dict[str, dict[str, int | str]]:
    segment_lists = segment_lists or SEGMENT_BREVO_LISTS
    unique_list_ids = sorted(set(segment_lists.values()))
    results: dict[str, dict[str, int | str]] = {}

    with requests.Session() as session:
        for list_id in unique_list_ids:
            ok, error, removed, before_count, after_count = clear_brevo_list(
                list_id,
                session=session,
            )
            results[str(list_id)] = {
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


def _contact_attributes(row: pd.Series) -> dict[str, object]:
    attributes: dict[str, object] = {
        "FIRSTNAME": row.get("user_name") or "",
        "TOTAL_ORDERED": float(row.get("total_ordered") or 0),
        "ORDER_COUNT": int(row.get("order_count") or 0),
        "DAYS_SINCE_REGISTRATION": int(row.get("days_since_registration") or 0),
    }

    lang = normalize_lang(row.get("lang"))
    if lang:
        attributes["LANGUAGE"] = lang

    if pd.notna(row.get("company")) and str(row.get("company")).strip():
        attributes["COMPANY"] = str(row["company"])

    days_since_last_order = row.get("days_since_last_order")
    if pd.notna(days_since_last_order):
        attributes["DAYS_SINCE_LAST_ORDER"] = int(days_since_last_order)

    return attributes


def upsert_contact_to_list(
    row: pd.Series,
    list_id: int,
    *,
    session: requests.Session | None = None,
) -> tuple[bool, str]:
    email = row.get("email")
    if pd.isna(email) or not str(email).strip():
        return False, "missing email"

    payload = {
        "email": str(email).strip(),
        "attributes": _contact_attributes(row),
        "updateEnabled": True,
        "listIds": [list_id],
    }

    client = session or requests
    response = client.post(
        f"{BREVO_API_BASE}/contacts",
        json=payload,
        headers=_brevo_headers(),
        timeout=30,
    )

    if response.status_code in (200, 201, 204):
        return True, ""

    return False, f"{response.status_code} {response.text}"


def sync_lists(
    customer_summary: pd.DataFrame,
    *,
    segment_lists: dict[str, int] | None = None,
    lang: str | None = DEFAULT_SYNC_LANG,
) -> dict[str, dict[str, int | list[str]]]:
    segment_lists = segment_lists or SEGMENT_BREVO_LISTS
    daily_lists = generate_daily_lists(customer_summary, lang=lang)
    results: dict[str, dict[str, int | list[str]]] = {}

    with requests.Session() as session:
        for segment_name, list_id in segment_lists.items():
            segment_df = daily_lists.get(segment_name)
            if segment_df is None:
                raise KeyError(f"Unknown segment: {segment_name}")

            uploaded = 0
            failed: list[str] = []

            for _, row in segment_df.iterrows():
                ok, error = upsert_contact_to_list(row, list_id, session=session)
                if ok:
                    uploaded += 1
                else:
                    failed.append(f"{row.get('email', '?')}: {error}")

            results[segment_name] = {
                "list_id": list_id,
                "matched": len(segment_df),
                "uploaded": uploaded,
                "failed": failed,
            }

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch edonna data and sync registration-milestone contacts to Brevo.",
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
    else:
        reference_time = pd.Timestamp.now(tz=DEFAULT_TIMEZONE)

    print("Step 1: clearing Brevo lists...")
    clear_results = clear_all_lists()
    for list_id, stats in clear_results.items():
        print(
            f"  list {stats['list_id']}: "
            f"{stats['before']} -> {stats['after']} contacts"
        )

    print("Step 2: fetching edonna data and calculating segments...")
    customer_summary = build_customer_summary(reference_time=reference_time)
    daily_lists = generate_daily_lists(customer_summary, lang=DEFAULT_SYNC_LANG)
    print(f"  language filter: {DEFAULT_SYNC_LANG}")
    for segment_name, frame in daily_lists.items():
        print(f"  {segment_name}: {len(frame)}")

    print("Step 3: uploading contacts to Brevo...")
    results = sync_lists(customer_summary, lang=DEFAULT_SYNC_LANG)

    print(f"\nReference date: {reference_time.date().isoformat()} ({DEFAULT_TIMEZONE})")
    print(f"Total customers: {len(customer_summary)}")
    print("Brevo sync complete")
    for segment_name, stats in results.items():
        print(
            f"{segment_name} -> list {stats['list_id']}: "
            f"{stats['uploaded']}/{stats['matched']} uploaded"
        )
        for failure in stats["failed"]:
            print(f"  failed: {failure}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
