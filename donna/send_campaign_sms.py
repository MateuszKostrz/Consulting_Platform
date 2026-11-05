"""Send Donna promo SMS to filtered customers from a corrected CSV export.

Default is dry-run only (no API calls, no SMS sent).

Examples:
    python send_campaign_sms.py
    python send_campaign_sms.py --csv ~/Downloads/request_sql_11_corrected.csv
    python send_campaign_sms.py --send          # real send — requires SMSPLANET_API_TOKEN
    python send_campaign_sms.py --test            # SMS Planet API dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from send_sms import dedupe_phones, default_env_file, normalize_phone, send_sms

DEFAULT_CSV = Path.home() / "Downloads" / "request_sql_11_corrected.csv"
DEFAULT_MESSAGE = (
    "Gorący tydzień w DONNA! Promocja -20% na cały asortyment. Tylko do niedzieli.\n\n"
    "Sprawdź: https://donna.pl"
)
PROGRESS_EVERY = 1000
API_BATCH_SIZE = 1000
MAX_DAYS_SINCE_LAST_ORDER = 365  # only customers who ordered within the last 12 months
EXTRA_CAMPAIGN_PHONES = [
    "663337793",
    "601451220",
    "796123330",
    "603859885",
    "515131278",
]


def load_campaign_phones(
    csv_path: Path,
    *,
    max_days_since_last_order: int = MAX_DAYS_SINCE_LAST_ORDER,
) -> tuple[list[str], dict[str, int]]:
    rows_total = 0
    rows_eligible = 0
    duplicate_rows_skipped = 0
    rows_skipped_outside_window = 0
    rows_skipped_no_phone = 0
    rows_skipped_bad_status = 0
    seen: set[str] = set()
    phones: list[str] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            rows_total += 1

            if row.get("SMS gotowy") != "tak":
                if (row.get("Poprawiony numer telefonu") or "").strip():
                    rows_skipped_bad_status += 1
                else:
                    rows_skipped_no_phone += 1
                continue

            days_raw = (row.get("Dni od ostatniego zamówienia") or "").strip()
            try:
                days = int(float(days_raw)) if days_raw else None
            except ValueError:
                days = None

            if days is None or days > max_days_since_last_order:
                rows_skipped_outside_window += 1
                continue

            phone = normalize_phone(row.get("Poprawiony numer telefonu", ""))
            if not phone:
                rows_skipped_bad_status += 1
                continue

            rows_eligible += 1
            if phone in seen:
                duplicate_rows_skipped += 1
                continue

            seen.add(phone)
            phones.append(phone)

    phones = dedupe_phones(phones)
    if len(phones) != len(seen):
        raise RuntimeError("Internal error: duplicate phones remained after deduplication.")

    stats = {
        "rows_total": rows_total,
        "rows_eligible": rows_eligible,
        "unique_phones": len(phones),
        "duplicate_rows_skipped": duplicate_rows_skipped,
        "rows_skipped_outside_window": rows_skipped_outside_window,
        "rows_skipped_no_phone": rows_skipped_no_phone,
        "rows_skipped_bad_status": rows_skipped_bad_status,
    }
    return phones, stats


def add_extra_campaign_phones(
    phones: list[str],
    extra: list[str],
) -> tuple[list[str], int, int]:
    """Append extra numbers; skip any already in the CSV list (still one SMS each)."""
    existing = set(phones)
    added = 0
    already_present = 0
    merged = list(phones)

    for phone in dedupe_phones(extra):
        if phone in existing:
            already_present += 1
            continue
        existing.add(phone)
        merged.append(phone)
        added += 1

    return merged, added, already_present


def _print_progress(sent_count: int, *, mode_label: str) -> None:
    print(f"{mode_label}: processed {sent_count:,} people")


def run_campaign(
    phones: list[str],
    message: str,
    *,
    sender: str,
    mode: str,
    campaign_name: str = "",
    clear_polish: bool = False,
    pause_seconds: float = 0.1,
) -> None:
    total = len(phones)
    if total == 0:
        raise ValueError("No recipients to send to.")
    if len(set(phones)) != total:
        raise RuntimeError("Duplicate phone numbers detected before send.")

    print(f"Sending to {total:,} unique phone numbers (one SMS per number).")

    next_progress_at = PROGRESS_EVERY
    sent_so_far = 0

    if mode == "dry-run":
        print("DRY RUN — no API calls, no SMS will be sent.")
        for phone in phones:
            sent_so_far += 1
            if sent_so_far >= next_progress_at or sent_so_far == total:
                _print_progress(sent_so_far, mode_label="Dry run")
                while next_progress_at <= sent_so_far:
                    next_progress_at += PROGRESS_EVERY
        print(f"Dry run complete. Would send to {total:,} unique numbers.")
        return

    mode_label = "Test mode" if mode == "test" else "Sent"
    print(f"{mode_label} — calling SMS Planet API in batches of {API_BATCH_SIZE}.")

    for start in range(0, total, API_BATCH_SIZE):
        batch = phones[start : start + API_BATCH_SIZE]
        result = send_sms(
            batch,
            message,
            sender=sender,
            test_mode=(mode == "test"),
            clear_polish=clear_polish,
            campaign_name=campaign_name,
        )
        sent_so_far += len(batch)
        print(
            f"  API batch {start // API_BATCH_SIZE + 1}: "
            f"{len(batch)} recipient(s) -> messageId={result.get('messageId')}"
        )
        while sent_so_far >= next_progress_at:
            _print_progress(min(sent_so_far, total), mode_label=mode_label)
            next_progress_at += PROGRESS_EVERY
        if pause_seconds and start + API_BATCH_SIZE < total:
            time.sleep(pause_seconds)

    print(f"Done. {mode_label.lower()} to {total:,} unique numbers.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send Donna SMS campaign from corrected customer CSV.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Corrected CSV path (default: {DEFAULT_CSV})",
    )
    parser.add_argument("--env-file", type=Path, default=default_env_file())
    parser.add_argument("--from", dest="sender", default="DONNA")
    parser.add_argument("--message", "-m", default=DEFAULT_MESSAGE)
    parser.add_argument(
        "--max-days-since-order",
        type=int,
        default=MAX_DAYS_SINCE_LAST_ORDER,
        help=(
            "Only send if last order was within this many days "
            f"(default: {MAX_DAYS_SINCE_LAST_ORDER} = 12 months)"
        ),
    )
    parser.add_argument("--campaign-name", default="donna-promo-20")
    parser.add_argument("--clear-polish", action="store_true")
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send SMS (default is dry-run with no API calls)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Use SMS Planet test mode (API call, but no SMS delivered)",
    )
    args = parser.parse_args()

    if args.send and args.test:
        print("Choose either --send or --test, not both.", file=sys.stderr)
        return 1

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 1

    if args.env_file.exists():
        load_dotenv(args.env_file)

    phones, stats = load_campaign_phones(
        args.csv,
        max_days_since_last_order=args.max_days_since_order,
    )
    phones, extra_added, extra_already_present = add_extra_campaign_phones(
        phones,
        EXTRA_CAMPAIGN_PHONES,
    )

    print(f"CSV: {args.csv}")
    print(f"Total rows: {stats['rows_total']:,}")
    window_label = (
        f"last {args.max_days_since_order} days (12 months)"
        if args.max_days_since_order == MAX_DAYS_SINCE_LAST_ORDER
        else f"last {args.max_days_since_order} days"
    )
    print(f"Eligible rows (phone + ordered within {window_label}): {stats['rows_eligible']:,}")
    print(f"Skipped (no order or ordered more than {window_label} ago): {stats['rows_skipped_outside_window']:,}")
    print(f"Unique phones from CSV: {stats['unique_phones']:,}")
    print(f"Extra phones added: {extra_added:,}")
    if extra_already_present:
        print(f"Extra phones already in CSV (not duplicated): {extra_already_present:,}")
    print(f"Unique phones to send (ONE SMS EACH): {len(phones):,}")
    print(f"Duplicate rows skipped: {stats['duplicate_rows_skipped']:,}")
    print(f"Sender: {args.sender}")
    print(f"Message:\n{args.message}\n")

    if args.send:
        mode = "send"
        print("MODE: LIVE SEND")
    elif args.test:
        mode = "test"
        print("MODE: SMS Planet test (API dry-run)")
    else:
        mode = "dry-run"
        print("MODE: Dry run (safe preview — no SMS sent)")

    try:
        run_campaign(
            phones,
            args.message,
            sender=args.sender,
            mode=mode,
            campaign_name=args.campaign_name,
            clear_polish=args.clear_polish,
        )
        return 0
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
