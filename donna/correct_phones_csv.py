"""Add corrected SMS phone columns to a semicolon-separated customer export."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from send_sms import pick_sms_phone


def correct_csv(input_path: Path, output_path: Path) -> dict[str, int]:
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")

        fieldnames = list(reader.fieldnames)
        corrected_col = "Poprawiony numer telefonu"
        status_col = "SMS gotowy"
        for col in (corrected_col, status_col):
            if col not in fieldnames:
                fieldnames.append(col)

        rows = list(reader)

    stats = {
        "rows": len(rows),
        "ready": 0,
        "no_phone": 0,
        "invalid_phone": 0,
    }

    for row in rows:
        mobile = row.get("Telefon komórkowy", "")
        landline = row.get("Numer telefonu", "")
        corrected = pick_sms_phone(mobile, landline)
        if not mobile.strip() and not landline.strip():
            status = "brak numeru"
            stats["no_phone"] += 1
        elif corrected:
            status = "tak"
            stats["ready"] += 1
        else:
            status = "niepoprawny numer"
            stats["invalid_phone"] += 1
        row[corrected_col] = corrected
        row[status_col] = status

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Add corrected SMS phone columns to a CSV export.")
    parser.add_argument("input", type=Path, help="Input CSV path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output CSV path (default: input stem + _corrected.csv)",
    )
    args = parser.parse_args()

    output = args.output or args.input.with_name(f"{args.input.stem}_corrected.csv")
    stats = correct_csv(args.input, output)

    print(f"Wrote: {output}")
    print(f"Rows: {stats['rows']}")
    print(f"SMS gotowy (tak): {stats['ready']}")
    print(f"Brak numeru: {stats['no_phone']}")
    print(f"Niepoprawny numer: {stats['invalid_phone']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
