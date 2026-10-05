#!/usr/bin/env python3
"""Fetch Microsoft (MSFT) market data from the eToro Public API into CSV sheets."""

from __future__ import annotations

import argparse
import csv
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://public-api.etoro.com/api/v1"
DEFAULT_SYMBOL = "MSFT"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "data"
MAX_CANDLES = 1000

CANDLE_INTERVALS = [
    "OneMinute",
    "FiveMinutes",
    "TenMinutes",
    "FifteenMinutes",
    "ThirtyMinutes",
    "OneHour",
    "FourHours",
    "OneDay",
    "OneWeek",
]

EXTRACTABLE_DATA = [
    {
        "category": "Live quote",
        "endpoint": "GET /market-data/instruments/rates",
        "granularity": "Real-time snapshot",
        "max_history": "Current only",
        "fields": "bid, ask, lastExecution, spread, quote timestamp",
        "notes": "Best for current price; poll for updates.",
    },
    {
        "category": "Instrument metadata",
        "endpoint": "GET /market-data/instruments",
        "granularity": "Static / slow-changing",
        "max_history": "N/A",
        "fields": "display name, symbol, exchange, industry, logos",
        "notes": "Resolve instrumentId once and cache it.",
    },
    {
        "category": "Symbol search",
        "endpoint": "GET /market-data/search",
        "granularity": "Lookup",
        "max_history": "N/A",
        "fields": "instrumentId, internalSymbolFull, displayname",
        "notes": "Use internalSymbolFull=MSFT for exact US listing.",
    },
    {
        "category": "OHLCV candles",
        "endpoint": "GET /market-data/instruments/{id}/history/candles/{direction}/{interval}/{count}",
        "granularity": "OneMinute to OneWeek",
        "max_history": "Up to 1000 bars per request",
        "fields": "fromDate, open, high, low, close, volume",
        "notes": "No date-range paging. OneDay ~4 years; OneHour ~42 days.",
    },
    {
        "category": "Exchange reference",
        "endpoint": "GET /market-data/exchanges",
        "granularity": "Reference",
        "max_history": "N/A",
        "fields": "exchangeID, exchangeDescription",
        "notes": "Map exchange IDs from instrument metadata.",
    },
    {
        "category": "Your portfolio (account)",
        "endpoint": "GET /trading/info/demo/pnl or /trading/info/real/pnl",
        "granularity": "Current positions",
        "max_history": "Open positions only",
        "fields": "positions, credit, P&L",
        "notes": "Requires Demo or Real user key matching environment.",
    },
    {
        "category": "Your trade history (account)",
        "endpoint": "GET /trading/info/trade/history",
        "granularity": "Closed trades",
        "max_history": "Filterable by date",
        "fields": "open/close rate, timestamps, profit, fees",
        "notes": "Your trades only, not public MSFT history.",
    },
]


def resolve_env_file(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "platform_edu" / ".env"


def log(message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


class EtoroClient:
    def __init__(self, api_key: str, user_key: str) -> None:
        self.api_key = api_key.strip()
        self.user_key = user_key.strip()
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "x-user-key": self.user_key,
            "x-request-id": str(uuid.uuid4()),
            "Accept": "application/json",
        }

    def get(self, path: str, params: dict | None = None) -> dict:
        response = self.session.get(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def search_symbol(self, symbol: str) -> dict:
        payload = self.get(
            "/market-data/search",
            {
                "internalSymbolFull": symbol,
                "fields": "instrumentId,internalSymbolFull,displayname,symbolFull,marketId",
            },
        )
        items = payload.get("items") or []
        exact = next(
            (item for item in items if item.get("internalSymbolFull") == symbol),
            items[0] if items else None,
        )
        if not exact:
            raise RuntimeError(f"No instrument found for symbol {symbol!r}")
        return exact

    def instrument_metadata(self, instrument_id: int) -> dict:
        payload = self.get("/market-data/instruments", {"instrumentIds": str(instrument_id)})
        rows = payload.get("instrumentDisplayDatas") or []
        if not rows:
            raise RuntimeError(f"No metadata for instrument {instrument_id}")
        return rows[0]

    def live_rate(self, instrument_id: int) -> dict:
        payload = self.get("/market-data/instruments/rates", {"instrumentIds": str(instrument_id)})
        rows = payload.get("rates") or []
        if not rows:
            raise RuntimeError(f"No live rate for instrument {instrument_id}")
        return rows[0]

    def exchange_name(self, exchange_id: int) -> str:
        payload = self.get("/market-data/exchanges", {"exchangeIds": str(exchange_id)})
        rows = payload.get("exchangeInfo") or []
        if not rows:
            return str(exchange_id)
        return rows[0].get("exchangeDescription") or str(exchange_id)

    def candles(
        self,
        instrument_id: int,
        *,
        interval: str,
        count: int,
        direction: str = "asc",
    ) -> list[dict]:
        count = max(1, min(count, MAX_CANDLES))
        payload = self.get(
            f"/market-data/instruments/{instrument_id}/history/candles/{direction}/{interval}/{count}",
        )
        groups = payload.get("candles") or []
        if not groups:
            return []
        return groups[0].get("candles") or []


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def candle_rows(candles: list[dict], *, interval: str, symbol: str, instrument_id: int) -> list[dict]:
    rows: list[dict] = []
    for candle in candles:
        rows.append(
            {
                "symbol": symbol,
                "instrument_id": instrument_id,
                "interval": interval,
                "datetime_utc": candle.get("fromDate"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": candle.get("volume"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Microsoft market data from eToro to CSV.")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--daily-bars", type=int, default=MAX_CANDLES)
    parser.add_argument("--hourly-bars", type=int, default=MAX_CANDLES)
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

    output_dir = args.output_dir
    symbol = args.symbol.upper()
    client = EtoroClient(api_key, user_key)
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        search = client.search_symbol(symbol)
        instrument_id = int(search["instrumentId"])
        metadata = client.instrument_metadata(instrument_id)
        rate = client.live_rate(instrument_id)
        exchange = client.exchange_name(int(metadata.get("exchangeID") or 0))

        snapshot = {
            "fetched_at_utc": fetched_at,
            "symbol": symbol,
            "instrument_id": instrument_id,
            "display_name": metadata.get("instrumentDisplayName"),
            "exchange": exchange,
            "price_source": metadata.get("priceSource"),
            "industry_id": metadata.get("stocksIndustryID"),
            "bid": rate.get("bid"),
            "ask": rate.get("ask"),
            "last_execution": rate.get("lastExecution"),
            "spread": round(float(rate.get("ask") or 0) - float(rate.get("bid") or 0), 4),
            "quote_time_utc": rate.get("date"),
            "related_symbols": "; ".join(
                f"{item.get('internalSymbolFull')} ({item.get('instrumentId')})"
                for item in (client.get(
                    "/market-data/search",
                    {
                        "internalSymbolFull": symbol,
                        "fields": "instrumentId,internalSymbolFull,displayname",
                    },
                ).get("items") or [])
            ),
        }

        daily = client.candles(
            instrument_id,
            interval="OneDay",
            count=args.daily_bars,
            direction="asc",
        )
        hourly = client.candles(
            instrument_id,
            interval="OneHour",
            count=args.hourly_bars,
            direction="asc",
        )

        candle_fields = [
            "symbol",
            "instrument_id",
            "interval",
            "datetime_utc",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        write_csv(output_dir / "msft_snapshot.csv", list(snapshot.keys()), [snapshot])
        write_csv(
            output_dir / "msft_daily_ohlcv.csv",
            candle_fields,
            candle_rows(daily, interval="OneDay", symbol=symbol, instrument_id=instrument_id),
        )
        write_csv(
            output_dir / "msft_hourly_ohlcv.csv",
            candle_fields,
            candle_rows(hourly, interval="OneHour", symbol=symbol, instrument_id=instrument_id),
        )
        write_csv(
            output_dir / "what_you_can_extract.csv",
            ["category", "endpoint", "granularity", "max_history", "fields", "notes"],
            EXTRACTABLE_DATA,
        )

        log(f"Wrote snapshot -> {output_dir / 'msft_snapshot.csv'}")
        log(f"Wrote daily OHLCV ({len(daily)} bars) -> {output_dir / 'msft_daily_ohlcv.csv'}")
        log(f"Wrote hourly OHLCV ({len(hourly)} bars) -> {output_dir / 'msft_hourly_ohlcv.csv'}")
        log(f"Wrote API guide -> {output_dir / 'what_you_can_extract.csv'}")
        if daily:
            log(f"Daily range: {daily[0].get('fromDate')} -> {daily[-1].get('fromDate')}")
        if hourly:
            log(f"Hourly range: {hourly[0].get('fromDate')} -> {hourly[-1].get('fromDate')}")
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
