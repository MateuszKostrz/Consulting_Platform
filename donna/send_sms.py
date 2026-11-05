"""Send SMS via SMS Planet API.

Edit the CONFIG section below, then run:

    python send_sms.py

Or override from the command line:

    python send_sms.py --to 663337793 --message "hello" --from DONNA
    python send_sms.py --list-senders
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

SMSPLANET_API_BASE = "https://api2.smsplanet.pl"
MAX_RECIPIENTS_PER_REQUEST = 10_000

# ---------------------------------------------------------------------------
# Edit these defaults, then run:  python send_sms.py
# ---------------------------------------------------------------------------
CONFIG = {
    "sender": "DONNA",           # must be approved in SMS Planet (see --list-senders)
    "message": "hello",
    "phones": [
        "663337793",
    ],
    "test_mode": False,          # True = API dry run, no SMS sent
    "clear_polish": False,       # replace ą, ć, ł... with ASCII
}
# ---------------------------------------------------------------------------


def default_env_file() -> Path:
    return Path(__file__).resolve().parents[1] / "platform_edu" / ".env"


def _api_token() -> str:
    token = os.environ.get("SMSPLANET_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "SMSPLANET_API_TOKEN is not set. Add it to platform_edu/.env"
        )
    return token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_token()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def _post(endpoint: str, data: list[tuple[str, str]]) -> dict:
    url = f"{SMSPLANET_API_BASE}/{endpoint.lstrip('/')}"
    response = requests.post(url, headers=_headers(), data=data, timeout=60)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Non-JSON response ({response.status_code}): {response.text}") from exc

    if response.status_code != 200 or "errorCode" in payload:
        code = payload.get("errorCode", response.status_code)
        msg = payload.get("errorMsg", response.text)
        raise RuntimeError(f"SMS Planet error {code}: {msg}")

    return payload


def list_sender_fields(*, product: str = "SMS") -> list[str]:
    payload = _post("getSenderFields", [("product", product)])
    raw = payload.get("senderFields", "")
    if not raw:
        return []
    return [field.strip() for field in raw.split(",") if field.strip()]


def register_sender_field(name: str) -> dict:
    return _post("addSenderField", [("senderField", name.strip())])


def normalize_phone(phone: str) -> str:
    """Normalize to a 9-digit Polish number for SMS Planet, or empty if invalid."""
    if not phone:
        return ""
    cleaned = str(phone).strip()
    if not cleaned:
        return ""
    cleaned = cleaned.replace(" ", "").replace("-", "")
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    if cleaned.startswith("00"):
        cleaned = cleaned[2:]
    cleaned = re.sub(r"[^\d]", "", cleaned)
    if cleaned.startswith("48") and len(cleaned) > 9:
        cleaned = cleaned[2:]
    if len(cleaned) == 9 and cleaned.isdigit():
        return cleaned
    return ""


def pick_sms_phone(*candidates: str) -> str:
    for candidate in candidates:
        normalized = normalize_phone(candidate)
        if normalized:
            return normalized
    return ""


def dedupe_phones(phones: list[str]) -> list[str]:
    """Return unique normalized phones, preserving first-seen order."""
    unique: list[str] = []
    seen: set[str] = set()
    for phone in phones:
        normalized = normalize_phone(phone)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def send_sms(
    phones: list[str],
    message: str,
    *,
    sender: str,
    test_mode: bool = False,
    clear_polish: bool = False,
    campaign_name: str = "",
) -> dict:
    cleaned_phones = dedupe_phones(phones)
    if not cleaned_phones:
        raise ValueError("No phone numbers provided")
    if not message.strip():
        raise ValueError("Message is empty")
    if not sender.strip():
        raise ValueError("Sender is empty")

    data: list[tuple[str, str]] = [
        ("from", sender.strip()),
        ("msg", message),
    ]
    if test_mode:
        data.append(("test", "1"))
    if clear_polish:
        data.append(("clear_polish", "1"))
    if campaign_name.strip():
        data.append(("name", campaign_name.strip()))
    for phone in cleaned_phones:
        data.append(("to", phone))

    return _post("sms", data)


def send_sms_in_batches(
    phones: list[str],
    message: str,
    *,
    sender: str,
    test_mode: bool = False,
    clear_polish: bool = False,
    campaign_name: str = "",
    batch_size: int = MAX_RECIPIENTS_PER_REQUEST,
    pause_seconds: float = 0.1,
) -> list[dict]:
    results: list[dict] = []
    unique_phones = dedupe_phones(phones)

    for start in range(0, len(unique_phones), batch_size):
        batch = unique_phones[start : start + batch_size]
        result = send_sms(
            batch,
            message,
            sender=sender,
            test_mode=test_mode,
            clear_polish=clear_polish,
            campaign_name=campaign_name,
        )
        results.append(result)
        print(f"  batch {start // batch_size + 1}: {len(batch)} recipient(s) -> messageId={result.get('messageId')}")
        if pause_seconds and start + batch_size < len(unique_phones):
            time.sleep(pause_seconds)

    return results


def _load_phones_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Send SMS via SMS Planet API.")
    parser.add_argument("--env-file", type=Path, default=default_env_file())
    parser.add_argument("--from", dest="sender", default=CONFIG["sender"], help="Sender name (approved field)")
    parser.add_argument("--message", "-m", default=CONFIG["message"], help="SMS text")
    parser.add_argument("--to", action="append", default=[], help="Recipient phone (repeatable)")
    parser.add_argument("--phones-file", type=Path, help="File with one phone per line")
    parser.add_argument("--test", action="store_true", default=CONFIG["test_mode"], help="Dry run")
    parser.add_argument("--clear-polish", action="store_true", default=CONFIG["clear_polish"])
    parser.add_argument("--campaign-name", default="", help="Optional label in SMS Planet history")
    parser.add_argument("--list-senders", action="store_true", help="Print approved sender fields and exit")
    parser.add_argument("--register-sender", metavar="NAME", help="Request a new sender field")
    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file)

    try:
        if args.list_senders:
            senders = list_sender_fields()
            print("Approved sender fields:", ", ".join(senders) if senders else "(none)")
            return 0

        if args.register_sender:
            result = register_sender_field(args.register_sender)
            print(f"Sender '{args.register_sender}' submitted for approval: {result}")
            return 0

        phones = [normalize_phone(p) for p in args.to]
        if args.phones_file:
            phones.extend(_load_phones_file(args.phones_file))
        if not phones:
            phones = [normalize_phone(p) for p in CONFIG["phones"]]

        print(f"Sender:   {args.sender}")
        print(f"Message:  {args.message}")
        print(f"Phones:   {len(phones)} recipient(s)")
        print(f"Test mode: {args.test}")

        results = send_sms_in_batches(
            phones,
            args.message,
            sender=args.sender,
            test_mode=args.test,
            clear_polish=args.clear_polish,
            campaign_name=args.campaign_name,
        )
        print(f"Done. {len(results)} API request(s) sent.")
        return 0

    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
