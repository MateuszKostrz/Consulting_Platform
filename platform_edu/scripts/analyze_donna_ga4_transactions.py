#!/usr/bin/env python3
"""Analyze donna.pl GA4 transaction exports by month and traffic channel."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

CHANNELS = ['Meta', 'Google Ads', 'SEO', 'Direct', 'Other']

DEFAULT_MONTHLY_FILES = {
    '2026-05': Path('/Users/mateuszkostrz/Downloads/Transactions_Transaction_ID-2.csv'),
    '2026-06': Path('/Users/mateuszkostrz/Downloads/Transactions_Transaction_ID-3.csv'),
    '2026-07': Path('/Users/mateuszkostrz/Downloads/Transactions_Transaction_ID-4.csv'),
}


def categorize(source_medium: str) -> str:
    parts = [part.strip() for part in source_medium.split(' / ', 1)]
    source = parts[0].lower()
    medium = parts[1].lower() if len(parts) > 1 else ''

    if source == '(direct)':
        return 'Direct'
    if source == 'google' and medium == 'cpc':
        return 'Google Ads'
    if medium == 'paid' and source in {'fb', 'ig', 'an', 'facebook', 'instagram'}:
        return 'Meta'
    if 'facebook' in source or source in {
        'm.facebook.com',
        'l.facebook.com',
        'lm.facebook.com',
        'facebook.com',
    }:
        return 'Meta'
    if source == 'ig' and medium in {'social', 'paid'}:
        return 'Meta'
    if medium == 'organic':
        return 'SEO'
    return 'Other'


def parse_ga4_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline='', encoding='utf-8') as handle:
        for raw in csv.reader(handle):
            if not raw or raw[0].startswith('#') or raw[0] == 'Transaction ID':
                continue
            if len(raw) < 4 or not raw[0].isdigit():
                continue
            source_medium = raw[1]
            rows.append(
                {
                    'transaction_id': raw[0],
                    'source_medium': source_medium,
                    'purchases': float(raw[2]),
                    'revenue': float(raw[3]),
                    'category': categorize(source_medium),
                }
            )
    return rows


def aggregate(rows: list[dict]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {'orders': 0, 'revenue': 0.0, 'rows': 0}
    )
    for row in rows:
        bucket = grouped[row['category']]
        bucket['rows'] += 1
        bucket['revenue'] += row['revenue']
        if row['purchases'] > 0:
            bucket['orders'] += int(row['purchases'])
    return grouped


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_paid_traffic(source_medium: str) -> bool:
    parts = [part.strip() for part in source_medium.split(' / ', 1)]
    source = parts[0].lower()
    medium = parts[1].lower() if len(parts) > 1 else ''

    if source == 'google' and medium == 'cpc':
        return True
    if medium == 'paid' and source in {'fb', 'ig', 'an', 'facebook', 'instagram'}:
        return True
    if 'facebook' in source or source in {
        'm.facebook.com',
        'l.facebook.com',
        'lm.facebook.com',
        'facebook.com',
    }:
        return True
    return source == 'ig' and medium in {'social', 'paid'}


def aggregate_paid_split(rows: list[dict]) -> dict[str, float | int]:
    grouped = {
        'Paid': {'orders': 0, 'revenue': 0.0},
        'Non-paid': {'orders': 0, 'revenue': 0.0},
    }
    for row in rows:
        bucket = 'Paid' if is_paid_traffic(row['source_medium']) else 'Non-paid'
        grouped[bucket]['revenue'] += row['revenue']
        if row['purchases'] > 0:
            grouped[bucket]['orders'] += int(row['purchases'])
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--may',
        type=Path,
        default=DEFAULT_MONTHLY_FILES['2026-05'],
    )
    parser.add_argument(
        '--june',
        type=Path,
        default=DEFAULT_MONTHLY_FILES['2026-06'],
    )
    parser.add_argument(
        '--july',
        type=Path,
        default=DEFAULT_MONTHLY_FILES['2026-07'],
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).resolve().parents[2] / 'data',
    )
    args = parser.parse_args()

    monthly_files = {
        '2026-05': args.may,
        '2026-06': args.june,
        '2026-07': args.july,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)

    month_source_rows: list[dict] = []
    paid_split_rows: list[dict] = []
    source_totals = defaultdict(lambda: {'orders': 0, 'revenue': 0.0, 'rows': 0})

    for month, csv_path in monthly_files.items():
        parsed_rows = parse_ga4_csv(csv_path)
        grouped = aggregate(parsed_rows)
        paid_split = aggregate_paid_split(parsed_rows)
        month_total = sum(values['revenue'] for values in paid_split.values())

        for traffic_type, values in paid_split.items():
            paid_split_rows.append(
                {
                    'month': month,
                    'traffic_type': traffic_type,
                    'purchase_count': values['orders'],
                    'net_revenue': round(values['revenue'], 2),
                    'revenue_share_pct': round(
                        (values['revenue'] / month_total * 100) if month_total else 0,
                        1,
                    ),
                }
            )

        for channel in CHANNELS:
            values = grouped.get(channel, {'orders': 0, 'revenue': 0.0, 'rows': 0})
            month_source_rows.append(
                {
                    'month': month,
                    'channel': channel,
                    'purchase_count': values['orders'],
                    'net_revenue': round(values['revenue'], 2),
                    'transaction_rows': values['rows'],
                }
            )
            source_totals[channel]['orders'] += values['orders']
            source_totals[channel]['revenue'] += values['revenue']
            source_totals[channel]['rows'] += values['rows']

    source_rows = [
        {
            'channel': channel,
            'purchase_count': source_totals[channel]['orders'],
            'net_revenue': round(source_totals[channel]['revenue'], 2),
            'transaction_rows': source_totals[channel]['rows'],
        }
        for channel in CHANNELS
    ]

    write_csv(
        args.output_dir / 'donna_transactions_by_month_and_channel.csv',
        ['month', 'channel', 'purchase_count', 'net_revenue', 'transaction_rows'],
        month_source_rows,
    )
    write_csv(
        args.output_dir / 'donna_transactions_by_channel.csv',
        ['channel', 'purchase_count', 'net_revenue', 'transaction_rows'],
        source_rows,
    )
    write_csv(
        args.output_dir / 'donna_transactions_paid_vs_nonpaid_by_month.csv',
        ['month', 'traffic_type', 'purchase_count', 'net_revenue', 'revenue_share_pct'],
        paid_split_rows,
    )

    net_revenue = round(sum(row['net_revenue'] for row in source_rows), 2)
    print('Wrote monthly breakdown:', args.output_dir / 'donna_transactions_by_month_and_channel.csv')
    print('Wrote channel totals:', args.output_dir / 'donna_transactions_by_channel.csv')
    print('Wrote paid split:', args.output_dir / 'donna_transactions_paid_vs_nonpaid_by_month.csv')
    print(f'Net revenue (May–Jul 2026): {net_revenue:,.2f} PLN')
    for row in source_rows:
        print(
            f"  {row['channel']:12} "
            f"{row['purchase_count']:4} purchases  "
            f"{row['net_revenue']:,.2f} PLN"
        )


if __name__ == '__main__':
    main()
