#!/usr/bin/env python3
"""Fetch daily OHLCV history for a large-cap universe from the eToro Public API."""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from etoro_client import (
    CANDLE_FIELDS,
    EtoroClient,
    MAX_CANDLES,
    candle_rows,
    resolve_env_file,
)

DEFAULT_UNIVERSE = Path(__file__).resolve().parent / "universe.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "universe"


def log(message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_universe(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fetch_symbol(
    client: EtoroClient,
    *,
    symbol: str,
    company: str,
    role: str,
    daily_bars: int,
    fetched_at: str,
) -> tuple[list[dict], dict, dict]:
    search = client.search_symbol(symbol)
    instrument_id = int(search["instrumentId"])
    metadata = client.instrument_metadata(instrument_id)
    rate = client.live_rate(instrument_id)
    exchange = client.exchange_name(int(metadata.get("exchangeID") or 0))
    daily = client.candles(
        instrument_id,
        interval="OneDay",
        count=daily_bars,
        direction="asc",
    )

    rows = candle_rows(
        daily,
        interval="OneDay",
        symbol=symbol,
        instrument_id=instrument_id,
    )
    snapshot = {
        "fetched_at_utc": fetched_at,
        "symbol": symbol,
        "company": company,
        "role": role,
        "instrument_id": instrument_id,
        "display_name": metadata.get("instrumentDisplayName"),
        "exchange": exchange,
        "price_source": metadata.get("priceSource"),
        "bid": rate.get("bid"),
        "ask": rate.get("ask"),
        "last_execution": rate.get("lastExecution"),
        "spread": round(float(rate.get("ask") or 0) - float(rate.get("bid") or 0), 4),
        "quote_time_utc": rate.get("date"),
    }
    manifest = {
        "symbol": symbol,
        "company": company,
        "role": role,
        "instrument_id": instrument_id,
        "display_name": metadata.get("instrumentDisplayName"),
        "exchange": exchange,
        "daily_bars": len(daily),
        "date_from": daily[0].get("fromDate") if daily else "",
        "date_to": daily[-1].get("fromDate") if daily else "",
        "fetched_at_utc": fetched_at,
    }
    return rows, snapshot, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download daily OHLCV for a large-cap stock universe.",
    )
    parser.add_argument("--universe-file", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument(
        "--daily-bars",
        type=int,
        default=MAX_CANDLES,
        help="Daily bars per symbol (max 1000, roughly 4 years on eToro).",
    )
    args = parser.parse_args()

    env_file = resolve_env_file(args.env_file)
    if env_file.exists():
        load_dotenv(env_file)
        log(f"Loaded env from {env_file}")
    else:
        log(f"WARNING: env file not found at {env_file}")

    api_key = os.environ.get("ETORO_API_KEY", "").strip()
    user_key = os.environ.get("ETORO_USER_KEY", "").strip()
    missing = [name for name, value in [("ETORO_API_KEY", api_key), ("ETORO_USER_KEY", user_key)] if not value]
    if missing:
        log(f"ERROR: missing env vars: {', '.join(missing)}")
        log("Add ETORO_API_KEY and ETORO_USER_KEY to platform_edu/.env")
        return 1

    universe = load_universe(args.universe_file)
    if not universe:
        log(f"ERROR: no symbols found in {args.universe_file}")
        return 1

    output_dir = args.output_dir
    daily_dir = output_dir / "daily"
    client = EtoroClient(api_key, user_key)
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    combined_rows: list[dict] = []
    snapshots: list[dict] = []
    manifest_rows: list[dict] = []
    failures: list[str] = []

    log(
        f"Fetching {len(universe)} symbols, {args.daily_bars} daily bars each "
        f"(~4 years max) -> {output_dir}"
    )

    for entry in universe:
        symbol = entry["symbol"].strip().upper()
        company = entry.get("company", "").strip()
        role = entry.get("role", "trade").strip()
        try:
            rows, snapshot, manifest = fetch_symbol(
                client,
                symbol=symbol,
                company=company,
                role=role,
                daily_bars=args.daily_bars,
                fetched_at=fetched_at,
            )
            write_csv(daily_dir / f"{symbol.lower()}_daily.csv", CANDLE_FIELDS, rows)
            combined_rows.extend(rows)
            snapshots.append(snapshot)
            manifest_rows.append(manifest)
            log(
                f"  {symbol}: {manifest['daily_bars']} bars "
                f"({manifest['date_from'][:10]} -> {manifest['date_to'][:10]})"
            )
        except Exception as exc:
            failures.append(f"{symbol}: {exc}")
            log(f"  {symbol}: FAILED - {exc}")

    if combined_rows:
        write_csv(output_dir / "combined_daily_ohlcv.csv", CANDLE_FIELDS, combined_rows)
    if snapshots:
        write_csv(output_dir / "snapshot.csv", list(snapshots[0].keys()), snapshots)
    if manifest_rows:
        write_csv(output_dir / "manifest.csv", list(manifest_rows[0].keys()), manifest_rows)

    write_csv(
        output_dir / "collection_notes.csv",
        ["topic", "value"],
        [
            {"topic": "strategy_target", "value": "Trend + pullback swing (2-7 day holds)"},
            {"topic": "bar_interval", "value": "OneDay"},
            {"topic": "bars_per_symbol", "value": str(args.daily_bars)},
            {"topic": "approx_history", "value": "~4 years (eToro max 1000 daily bars per request)"},
            {"topic": "symbols_requested", "value": str(len(universe))},
            {"topic": "symbols_downloaded", "value": str(len(manifest_rows))},
            {"topic": "symbols_failed", "value": str(len(failures))},
            {"topic": "fetched_at_utc", "value": fetched_at},
            {"topic": "regime_benchmark", "value": "SPY (role=regime in universe.csv)"},
        ],
    )

    log(f"Wrote combined daily -> {output_dir / 'combined_daily_ohlcv.csv'}")
    log(f"Wrote per-symbol files -> {daily_dir}/")
    log(f"Wrote snapshot -> {output_dir / 'snapshot.csv'}")
    log(f"Wrote manifest -> {output_dir / 'manifest.csv'}")

    if failures:
        log(f"Completed with {len(failures)} failure(s):")
        for failure in failures:
            log(f"  - {failure}")
        return 1 if not manifest_rows else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
