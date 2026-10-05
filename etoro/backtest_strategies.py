#!/usr/bin/env python3
"""Trend + pullback and momentum rank backtests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from backtest_common import (
    DEFAULT_DATA,
    DEFAULT_OUTPUT,
    DEFAULT_PARAMS,
    DEFAULT_UNIVERSE,
    OpenPosition,
    StrategyParams,
    apply_slippage,
    build_regime_series,
    compute_spy_benchmark,
    enrich_indicators,
    load_price_panel,
    load_trade_symbols,
    position_size,
    summarize,
    try_exit,
)


def log(message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def entry_signal_trend_pullback(row: pd.Series, params: StrategyParams) -> bool:
    if pd.isna(row["ma_trend"]) or pd.isna(row["ma_pullback"]) or pd.isna(row["rsi"]):
        return False
    if not bool(row.get("history_ok", True)):
        return False
    if row["close"] <= row["ma_trend"]:
        return False

    near_ma = row["dist_to_pullback_ma_pct"] <= params.pullback_pct
    rsi_pullback = params.rsi_min <= row["rsi"] <= params.rsi_max
    if params.entry_logic.lower() == "or":
        return bool(near_ma or rsi_pullback)
    return bool(near_ma and rsi_pullback)


def rank_momentum_candidates(
    trade_symbols: list[str],
    signal_date: pd.Timestamp,
    bars_by_symbol_date: dict[tuple[str, pd.Timestamp], pd.Series],
    open_positions: dict[str, OpenPosition],
    params: StrategyParams,
) -> list[tuple[str, float, pd.Series]]:
    ranked: list[tuple[str, float, pd.Series]] = []
    for symbol in trade_symbols:
        if symbol in open_positions:
            continue
        signal_bar = bars_by_symbol_date.get((symbol, signal_date))
        if signal_bar is None:
            continue
        if pd.isna(signal_bar["return_lookback_pct"]) or pd.isna(signal_bar["ma_momentum"]):
            continue
        if signal_bar["close"] <= signal_bar["ma_momentum"]:
            continue
        if signal_bar["return_lookback_pct"] < params.momentum_min_return_pct:
            continue
        ranked.append((symbol, float(signal_bar["return_lookback_pct"]), signal_bar))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def run_backtest(
    prices: pd.DataFrame,
    trade_symbols: list[str],
    params: StrategyParams,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if params.strategy == "momentum_rank":
        return _run_momentum_backtest(prices, trade_symbols, params)
    return _run_trend_pullback_backtest(prices, trade_symbols, params)


def _shared_setup(
    prices: pd.DataFrame,
    trade_symbols: list[str],
    params: StrategyParams,
) -> tuple[
    pd.Series | None,
    pd.DataFrame,
    list[pd.Timestamp],
    dict[tuple[str, pd.Timestamp], pd.Series],
    list[pd.Timestamp],
]:
    regime = build_regime_series(prices, params) if params.use_regime_filter else None
    trade_prices = prices.loc[prices["symbol"].isin(trade_symbols)].copy()
    dates = sorted(trade_prices["datetime_utc"].drop_duplicates())
    if len(dates) < params.min_history_days + 1:
        raise RuntimeError("Not enough history to run backtest")

    tradable_dates = dates[params.min_history_days : -1]
    bars_by_symbol_date: dict[tuple[str, pd.Timestamp], pd.Series] = {}
    for _, row in trade_prices.iterrows():
        bars_by_symbol_date[(row["symbol"], row["datetime_utc"])] = row

    return regime, trade_prices, dates, bars_by_symbol_date, tradable_dates


def _close_position(
    *,
    symbol: str,
    position: OpenPosition,
    exit_date: pd.Timestamp,
    exit_price: float,
    exit_reason: str,
    params: StrategyParams,
    cash: float,
    trades: list[dict],
) -> float:
    exit_price = apply_slippage(exit_price, side="sell", slippage_pct=params.slippage_pct)
    proceeds = position.shares * exit_price
    pnl = proceeds - (position.shares * position.entry_price)
    trades.append(
        {
            "symbol": symbol,
            "entry_date": position.entry_date.date().isoformat(),
            "exit_date": exit_date.date().isoformat(),
            "entry_price": round(position.entry_price, 4),
            "exit_price": round(exit_price, 4),
            "shares": round(position.shares, 6),
            "bars_held": position.bars_held,
            "pnl": round(pnl, 2),
            "return_pct": round((exit_price / position.entry_price - 1) * 100, 2),
            "exit_reason": exit_reason,
        }
    )
    return cash + proceeds


def _open_position(
    *,
    symbol: str,
    entry_date: pd.Timestamp,
    raw_entry_price: float,
    equity: float,
    cash: float,
    params: StrategyParams,
    open_positions: dict[str, OpenPosition],
) -> float:
    entry_price = apply_slippage(raw_entry_price, side="buy", slippage_pct=params.slippage_pct)
    shares = position_size(equity, entry_price, params)
    if shares <= 0:
        return cash
    cost = shares * entry_price
    if cost > cash:
        shares = cash / entry_price
        cost = shares * entry_price
    if shares <= 0:
        return cash

    cash -= cost
    open_positions[symbol] = OpenPosition(
        symbol=symbol,
        entry_date=entry_date,
        entry_price=entry_price,
        shares=shares,
        stop_price=entry_price * (1 - params.stop_loss_pct / 100),
        take_profit_price=entry_price * (1 + params.take_profit_pct / 100),
    )
    return cash


def _mark_equity(
    cash: float,
    open_positions: dict[str, OpenPosition],
    bars_by_symbol_date: dict[tuple[str, pd.Timestamp], pd.Series],
    mark_date: pd.Timestamp,
) -> float:
    equity = cash
    for symbol, position in open_positions.items():
        bar = bars_by_symbol_date.get((symbol, mark_date))
        if bar is not None:
            equity += position.shares * float(bar.close)
    return equity


def _run_trend_pullback_backtest(
    prices: pd.DataFrame,
    trade_symbols: list[str],
    params: StrategyParams,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    regime, _, dates, bars_by_symbol_date, tradable_dates = _shared_setup(
        prices, trade_symbols, params
    )
    benchmark = compute_spy_benchmark(prices, params, tradable_dates)

    open_positions: dict[str, OpenPosition] = {}
    trades: list[dict] = []
    equity_rows: list[dict] = []
    cash = params.initial_capital

    for signal_date in tradable_dates:
        next_date = dates[dates.index(signal_date) + 1]
        regime_ok = bool(regime.get(signal_date, False)) if regime is not None else True

        closed_symbols: list[str] = []
        for symbol, position in list(open_positions.items()):
            bar = bars_by_symbol_date.get((symbol, next_date))
            if bar is None:
                continue
            exit_result = try_exit(position, bar, params)
            if exit_result is None:
                continue
            exit_price, exit_reason = exit_result
            cash = _close_position(
                symbol=symbol,
                position=position,
                exit_date=next_date,
                exit_price=exit_price,
                exit_reason=exit_reason,
                params=params,
                cash=cash,
                trades=trades,
            )
            closed_symbols.append(symbol)

        for symbol in closed_symbols:
            open_positions.pop(symbol, None)

        equity = _mark_equity(cash, open_positions, bars_by_symbol_date, signal_date)
        if not regime_ok:
            equity_rows.append({"date": signal_date.date().isoformat(), "equity": round(equity, 2)})
            continue

        candidates: list[tuple[str, float, pd.Series]] = []
        for symbol in trade_symbols:
            if symbol in open_positions:
                continue
            signal_bar = bars_by_symbol_date.get((symbol, signal_date))
            entry_bar = bars_by_symbol_date.get((symbol, next_date))
            if signal_bar is None or entry_bar is None:
                continue
            if not entry_signal_trend_pullback(signal_bar, params):
                continue
            candidates.append((symbol, float(entry_bar.open), entry_bar))

        candidates.sort(key=lambda item: item[1])
        slots = max(0, params.max_positions - len(open_positions))
        for symbol, raw_entry_price, _entry_bar in candidates[:slots]:
            cash = _open_position(
                symbol=symbol,
                entry_date=next_date,
                raw_entry_price=raw_entry_price,
                equity=equity,
                cash=cash,
                params=params,
                open_positions=open_positions,
            )

        equity = _mark_equity(cash, open_positions, bars_by_symbol_date, signal_date)
        equity_rows.append({"date": signal_date.date().isoformat(), "equity": round(equity, 2)})

    final_date = dates[-1]
    for symbol, position in list(open_positions.items()):
        bar = bars_by_symbol_date.get((symbol, final_date))
        if bar is None:
            continue
        cash = _close_position(
            symbol=symbol,
            position=position,
            exit_date=final_date,
            exit_price=float(bar.close),
            exit_reason="final_close",
            params=params,
            cash=cash,
            trades=trades,
        )

    trades_frame = pd.DataFrame(trades)
    equity_frame = pd.DataFrame(equity_rows)
    summary = summarize(trades_frame, equity_frame, params, benchmark)
    return trades_frame, equity_frame, summary


def _run_momentum_backtest(
    prices: pd.DataFrame,
    trade_symbols: list[str],
    params: StrategyParams,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    regime, _, dates, bars_by_symbol_date, tradable_dates = _shared_setup(
        prices, trade_symbols, params
    )
    benchmark = compute_spy_benchmark(prices, params, tradable_dates)

    open_positions: dict[str, OpenPosition] = {}
    trades: list[dict] = []
    equity_rows: list[dict] = []
    cash = params.initial_capital

    for signal_date in tradable_dates:
        next_date = dates[dates.index(signal_date) + 1]
        regime_ok = bool(regime.get(signal_date, False)) if regime is not None else True

        closed_symbols: list[str] = []
        for symbol, position in list(open_positions.items()):
            bar = bars_by_symbol_date.get((symbol, next_date))
            if bar is None:
                continue
            exit_result = try_exit(position, bar, params)
            if exit_result is None:
                continue
            exit_price, exit_reason = exit_result
            cash = _close_position(
                symbol=symbol,
                position=position,
                exit_date=next_date,
                exit_price=exit_price,
                exit_reason=exit_reason,
                params=params,
                cash=cash,
                trades=trades,
            )
            closed_symbols.append(symbol)

        for symbol in closed_symbols:
            open_positions.pop(symbol, None)

        equity = _mark_equity(cash, open_positions, bars_by_symbol_date, signal_date)
        if not regime_ok:
            equity_rows.append({"date": signal_date.date().isoformat(), "equity": round(equity, 2)})
            continue

        ranked = rank_momentum_candidates(
            trade_symbols, signal_date, bars_by_symbol_date, open_positions, params
        )
        slots = max(0, params.max_positions - len(open_positions))
        for symbol, _score, signal_bar in ranked[:slots]:
            entry_bar = bars_by_symbol_date.get((symbol, next_date))
            if entry_bar is None:
                continue
            cash = _open_position(
                symbol=symbol,
                entry_date=next_date,
                raw_entry_price=float(entry_bar.open),
                equity=equity,
                cash=cash,
                params=params,
                open_positions=open_positions,
            )

        equity = _mark_equity(cash, open_positions, bars_by_symbol_date, signal_date)
        equity_rows.append({"date": signal_date.date().isoformat(), "equity": round(equity, 2)})

    final_date = dates[-1]
    for symbol, position in list(open_positions.items()):
        bar = bars_by_symbol_date.get((symbol, final_date))
        if bar is None:
            continue
        cash = _close_position(
            symbol=symbol,
            position=position,
            exit_date=final_date,
            exit_price=float(bar.close),
            exit_reason="final_close",
            params=params,
            cash=cash,
            trades=trades,
        )

    trades_frame = pd.DataFrame(trades)
    equity_frame = pd.DataFrame(equity_rows)
    summary = summarize(trades_frame, equity_frame, params, benchmark)
    return trades_frame, equity_frame, summary


def write_outputs(
    output_dir: Path,
    trades: pd.DataFrame,
    equity: pd.DataFrame,
    summary: dict,
    params: StrategyParams,
) -> None:
    from dataclasses import fields

    output_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(output_dir / "trades.csv", index=False)
    equity.to_csv(output_dir / "equity_curve.csv", index=False)

    params_rows = [{"parameter": field.name, "value": getattr(params, field.name)} for field in fields(params)]
    pd.DataFrame(params_rows).to_csv(output_dir / "parameters_used.csv", index=False)

    summary_rows = [{"metric": key, "value": value} for key, value in summary.items()]
    pd.DataFrame(summary_rows).to_csv(output_dir / "summary.csv", index=False)

    if not trades.empty:
        exit_mix = (
            trades.groupby("exit_reason", as_index=False)
            .agg(trades=("symbol", "count"), avg_return_pct=("return_pct", "mean"))
            .sort_values("trades", ascending=False)
        )
    else:
        exit_mix = pd.DataFrame(columns=["exit_reason", "trades", "avg_return_pct"])
    exit_mix.to_csv(output_dir / "exit_reasons.csv", index=False)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Backtest trading strategies.")
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--universe-file", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--params-file", type=Path, default=DEFAULT_PARAMS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.data_file.exists():
        log(f"ERROR: data file not found: {args.data_file}")
        return 1

    params = StrategyParams.from_json(args.params_file) if args.params_file.exists() else StrategyParams()
    trade_symbols = load_trade_symbols(args.universe_file)
    regime_symbols = [params.regime_symbol.upper()]
    prices = enrich_indicators(
        load_price_panel(args.data_file, trade_symbols + regime_symbols),
        params,
    )

    log(f"Backtesting {params.strategy} on {len(trade_symbols)} symbols")
    trades, equity, summary = run_backtest(prices, trade_symbols, params)
    write_outputs(args.output_dir, trades, equity, summary, params)

    log(
        f"Return {summary['total_return_pct']}% vs SPY {summary['spy_buy_hold_return_pct']}% "
        f"(alpha {summary['alpha_vs_spy_pct']}%)"
    )
    log(f"Trades: {summary['total_trades']} | Beat SPY: {summary['beat_spy']}")
    log(f"Wrote results -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
