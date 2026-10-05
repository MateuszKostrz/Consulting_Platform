#!/usr/bin/env python3
"""Shared backtest utilities, benchmarks, and strategy parameter definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

import pandas as pd

DEFAULT_DATA = Path(__file__).resolve().parent / "data" / "universe" / "combined_daily_ohlcv.csv"
DEFAULT_UNIVERSE = Path(__file__).resolve().parent / "universe.csv"
DEFAULT_PARAMS = Path(__file__).resolve().parent / "strategy_params.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "backtest"


@dataclass
class StrategyParams:
    strategy: str = "trend_pullback"
    trend_ma: int = 50
    pullback_ma: int = 20
    exit_ma: int = 20
    regime_ma: int = 200
    regime_symbol: str = "SPY"
    rsi_period: int = 14
    rsi_min: float = 40.0
    rsi_max: float = 55.0
    pullback_pct: float = 3.0
    entry_logic: str = "and"
    use_trend_break_exit: bool = False
    max_hold_days: int = 7
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 6.0
    max_positions: int = 3
    risk_per_trade_pct: float = 2.0
    initial_capital: float = 10_000.0
    use_regime_filter: bool = True
    slippage_pct: float = 0.05
    min_history_days: int = 210
    momentum_lookback: int = 5
    momentum_trend_ma: int = 20
    momentum_min_return_pct: float = 0.5

    @classmethod
    def from_json(cls, path: Path) -> StrategyParams:
        payload = json.loads(path.read_text(encoding="utf-8"))
        allowed = {field.name for field in fields(cls)}
        return cls(**{key: payload[key] for key in payload if key in allowed})


@dataclass
class OpenPosition:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    stop_price: float
    take_profit_price: float
    bars_held: int = 0


def load_trade_symbols(universe_file: Path) -> list[str]:
    universe = pd.read_csv(universe_file)
    return universe.loc[universe["role"].str.lower() == "trade", "symbol"].str.upper().tolist()


def load_price_panel(data_file: Path, symbols: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(data_file, parse_dates=["datetime_utc"])
    frame["symbol"] = frame["symbol"].str.upper()
    frame = frame.loc[frame["symbol"].isin(symbols)].copy()
    frame.sort_values(["symbol", "datetime_utc"], inplace=True)
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def enrich_indicators(frame: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    lookbacks = {
        params.trend_ma,
        params.pullback_ma,
        params.exit_ma,
        params.momentum_trend_ma,
        params.momentum_lookback,
        params.regime_ma,
    }
    max_lookback = max(lookbacks)

    enriched_frames: list[pd.DataFrame] = []
    for _, group in frame.groupby("symbol", sort=False):
        data = group.copy()
        data["ma_trend"] = data["close"].rolling(params.trend_ma).mean()
        data["ma_pullback"] = data["close"].rolling(params.pullback_ma).mean()
        data["ma_exit"] = data["close"].rolling(params.exit_ma).mean()
        data["ma_momentum"] = data["close"].rolling(params.momentum_trend_ma).mean()
        data["rsi"] = compute_rsi(data["close"], params.rsi_period)
        data["dist_to_pullback_ma_pct"] = (
            (data["close"] - data["ma_pullback"]).abs() / data["ma_pullback"] * 100
        )
        data["return_lookback_pct"] = (
            data["close"] / data["close"].shift(params.momentum_lookback) - 1
        ) * 100
        data["history_ok"] = data["close"].rolling(max_lookback).count() >= max_lookback
        enriched_frames.append(data)

    return pd.concat(enriched_frames, ignore_index=True)


def build_regime_series(frame: pd.DataFrame, params: StrategyParams) -> pd.Series:
    spy = frame.loc[frame["symbol"] == params.regime_symbol.upper()].copy()
    if spy.empty:
        raise RuntimeError(f"Regime symbol {params.regime_symbol} not found in price data")
    spy.sort_values("datetime_utc", inplace=True)
    spy["regime_ma"] = spy["close"].rolling(params.regime_ma).mean()
    spy["regime_ok"] = spy["close"] > spy["regime_ma"]
    return spy.set_index("datetime_utc")["regime_ok"]


def apply_slippage(price: float, *, side: str, slippage_pct: float) -> float:
    multiplier = 1 + slippage_pct / 100 if side == "buy" else 1 - slippage_pct / 100
    return price * multiplier


def position_size(equity: float, entry_price: float, params: StrategyParams) -> float:
    risk_budget = equity * (params.risk_per_trade_pct / 100)
    stop_distance = entry_price * (params.stop_loss_pct / 100)
    if stop_distance <= 0:
        return 0.0
    shares_by_risk = risk_budget / stop_distance
    max_allocation = equity / params.max_positions
    shares_by_cap = max_allocation / entry_price
    return max(0.0, min(shares_by_risk, shares_by_cap))


def try_exit(
    position: OpenPosition,
    bar: pd.Series,
    params: StrategyParams,
) -> tuple[float, str] | None:
    position.bars_held += 1

    if bar["low"] <= position.stop_price:
        return position.stop_price, "stop_loss"
    if bar["high"] >= position.take_profit_price:
        return position.take_profit_price, "take_profit"
    if position.bars_held >= params.max_hold_days:
        return float(bar["close"]), "max_hold"
    if params.use_trend_break_exit and not pd.isna(bar["ma_exit"]) and bar["close"] < bar["ma_exit"]:
        return float(bar["close"]), "trend_break"
    return None


def compute_spy_benchmark(
    prices: pd.DataFrame,
    params: StrategyParams,
    tradable_dates: list[pd.Timestamp],
) -> dict[str, float | str]:
    spy = prices.loc[prices["symbol"] == params.regime_symbol.upper()].copy()
    spy.sort_values("datetime_utc", inplace=True)
    spy_by_date = spy.set_index("datetime_utc")

    if not tradable_dates:
        return {
            "spy_buy_hold_return_pct": 0.0,
            "spy_max_drawdown_pct": 0.0,
            "spy_final_equity": params.initial_capital,
            "benchmark_start": "",
            "benchmark_end": "",
        }

    all_dates = sorted(spy["datetime_utc"].drop_duplicates())
    start_date = tradable_dates[0]
    end_date = all_dates[-1]
    start_idx = all_dates.index(start_date)
    entry_date = all_dates[start_idx + 1] if start_idx + 1 < len(all_dates) else start_date

    entry_open = float(spy_by_date.loc[entry_date, "open"])
    shares = params.initial_capital / entry_open

    equity_rows: list[float] = []
    for date in tradable_dates:
        if date not in spy_by_date.index:
            continue
        equity_rows.append(shares * float(spy_by_date.loc[date, "close"]))

    if not equity_rows:
        return {
            "spy_buy_hold_return_pct": 0.0,
            "spy_max_drawdown_pct": 0.0,
            "spy_final_equity": params.initial_capital,
            "benchmark_start": entry_date.date().isoformat(),
            "benchmark_end": end_date.date().isoformat(),
        }

    equity_series = pd.Series(equity_rows)
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max * 100
    final_equity = round(float(equity_series.iloc[-1]), 2)
    total_return = round((final_equity / params.initial_capital - 1) * 100, 2)

    return {
        "spy_buy_hold_return_pct": total_return,
        "spy_max_drawdown_pct": round(float(drawdown.min()), 2),
        "spy_final_equity": final_equity,
        "benchmark_start": entry_date.date().isoformat(),
        "benchmark_end": end_date.date().isoformat(),
    }


def summarize(
    trades: pd.DataFrame,
    equity: pd.DataFrame,
    params: StrategyParams,
    benchmark: dict[str, float | str],
) -> dict[str, float | int | str | bool]:
    base = {
        "strategy": params.strategy,
        "total_trades": 0,
        "win_rate_pct": 0.0,
        "total_pnl": 0.0,
        "avg_return_pct": 0.0,
        "median_hold_days": 0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "final_equity": params.initial_capital,
        "total_return_pct": 0.0,
        "spy_buy_hold_return_pct": benchmark["spy_buy_hold_return_pct"],
        "spy_max_drawdown_pct": benchmark["spy_max_drawdown_pct"],
        "alpha_vs_spy_pct": 0.0,
        "beat_spy": False,
        "benchmark_start": benchmark["benchmark_start"],
        "benchmark_end": benchmark["benchmark_end"],
    }

    if trades.empty:
        spy_return = float(benchmark["spy_buy_hold_return_pct"])
        base["alpha_vs_spy_pct"] = round(-spy_return, 2)
        return base

    wins = trades.loc[trades["pnl"] > 0, "pnl"].sum()
    losses = trades.loc[trades["pnl"] < 0, "pnl"].sum()
    profit_factor = round(wins / abs(losses), 2) if losses < 0 else float("inf")

    if not equity.empty:
        rolling_max = equity["equity"].cummax()
        drawdown = (equity["equity"] - rolling_max) / rolling_max * 100
        max_drawdown = round(float(drawdown.min()), 2)
        final_equity = round(float(equity["equity"].iloc[-1]), 2)
    else:
        max_drawdown = 0.0
        final_equity = round(params.initial_capital + trades["pnl"].sum(), 2)

    total_return_pct = round((final_equity / params.initial_capital - 1) * 100, 2)
    spy_return = float(benchmark["spy_buy_hold_return_pct"])
    alpha = round(total_return_pct - spy_return, 2)

    return {
        "strategy": params.strategy,
        "total_trades": int(len(trades)),
        "win_rate_pct": round((trades["pnl"] > 0).mean() * 100, 2),
        "total_pnl": round(trades["pnl"].sum(), 2),
        "avg_return_pct": round(trades["return_pct"].mean(), 2),
        "median_hold_days": int(trades["bars_held"].median()),
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown,
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "spy_buy_hold_return_pct": spy_return,
        "spy_max_drawdown_pct": benchmark["spy_max_drawdown_pct"],
        "alpha_vs_spy_pct": alpha,
        "beat_spy": alpha > 0,
        "benchmark_start": benchmark["benchmark_start"],
        "benchmark_end": benchmark["benchmark_end"],
    }
