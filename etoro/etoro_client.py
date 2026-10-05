"""Shared eToro Public API client helpers."""

from __future__ import annotations

import uuid
from pathlib import Path

import requests

BASE_URL = "https://public-api.etoro.com/api/v1"
MAX_CANDLES = 1000

CANDLE_FIELDS = [
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


def resolve_env_file(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "platform_edu" / ".env"


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


def candle_rows(
    candles: list[dict],
    *,
    interval: str,
    symbol: str,
    instrument_id: int,
) -> list[dict]:
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
