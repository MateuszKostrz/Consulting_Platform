#!/usr/bin/env python3
"""Run multiple parameter sets and export a comparison CSV with SPY benchmark."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, fields
from datetime import datetime
from itertools import product
from pathlib import Path

import pandas as pd

from backtest_common import StrategyParams, enrich_indicators, load_price_panel, load_trade_symbols
from backtest_strategies import log, run_backtest

DEFAULT_SETS = Path(__file__).resolve().parent / "parameter_sets.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "backtest" / "parameter_sweep_results.csv"
DEFAULT_DETAIL_DIR = Path(__file__).resolve().parent / "data" / "backtest" / "sweep_runs"
DEFAULT_DATA = Path(__file__).resolve().parent / "data" / "universe" / "combined_daily_ohlcv.csv"
DEFAULT_UNIVERSE = Path(__file__).resolve().parent / "universe.csv"


def load_parameter_sets(path: Path) -> list[tuple[str, StrategyParams]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sets: list[tuple[str, StrategyParams]] = []

    for entry in payload:
        item = dict(entry)
        name = item.pop("name")
        base = asdict(StrategyParams())
        base.update(item)
        allowed = {field.name for field in fields(StrategyParams)}
        filtered = {key: value for key, value in base.items() if key in allowed}
        sets.append((name, StrategyParams(**filtered)))

    return sets


def build_default_parameter_sets() -> list[dict]:
    sets: list[dict] = []

    trend_grid = {
        "entry_logic": ["and"],
        "use_trend_break_exit": [False],
        "pullback_pct": [1.5, 2.0, 2.5, 3.0],
        "rsi_max": [48.0, 50.0, 52.0],
        "max_hold_days": [5, 7, 10],
        "take_profit_pct": [5.0, 6.0, 8.0],
        "stop_loss_pct": [2.5, 3.0],
        "max_positions": [2, 3],
    }

    idx = 1
    for pullback_pct, rsi_max, max_hold, take_profit, stop_loss, max_pos in product(
        trend_grid["pullback_pct"],
        trend_grid["rsi_max"],
        trend_grid["max_hold_days"],
        trend_grid["take_profit_pct"],
        trend_grid["stop_loss_pct"],
        trend_grid["max_positions"],
    ):
        sets.append(
            {
                "name": f"TP_{idx:02d}_strict",
                "strategy": "trend_pullback",
                "entry_logic": "and",
                "use_trend_break_exit": False,
                "pullback_pct": pullback_pct,
                "rsi_min": 40,
                "rsi_max": rsi_max,
                "max_hold_days": max_hold,
                "take_profit_pct": take_profit,
                "stop_loss_pct": stop_loss,
                "max_positions": max_pos,
            }
        )
        idx += 1
        if idx > 18:
            break

    sets.extend(
        [
            {
                "name": "TP_19_old_or_logic",
                "strategy": "trend_pullback",
                "entry_logic": "or",
                "use_trend_break_exit": True,
                "exit_ma": 20,
                "max_hold_days": 5,
            },
            {
                "name": "TP_20_strict_with_ma_exit",
                "strategy": "trend_pullback",
                "entry_logic": "and",
                "use_trend_break_exit": True,
                "exit_ma": 50,
                "pullback_pct": 2.0,
                "max_hold_days": 7,
            },
        ]
    )

    momentum_grid = {
        "momentum_lookback": [3, 5, 10],
        "momentum_min_return_pct": [0.0, 0.5, 1.0, 2.0],
        "max_hold_days": [5, 7, 10],
        "take_profit_pct": [6.0, 8.0],
        "max_positions": [2, 3],
    }

    midx = 1
    for lookback, min_ret, max_hold, take_profit, max_pos in product(
        momentum_grid["momentum_lookback"],
        momentum_grid["momentum_min_return_pct"],
        momentum_grid["max_hold_days"],
        momentum_grid["take_profit_pct"],
        momentum_grid["max_positions"],
    ):
        sets.append(
            {
                "name": f"MOM_{midx:02d}",
                "strategy": "momentum_rank",
                "use_trend_break_exit": False,
                "momentum_lookback": lookback,
                "momentum_trend_ma": 20,
                "momentum_min_return_pct": min_ret,
                "max_hold_days": max_hold,
                "take_profit_pct": take_profit,
                "stop_loss_pct": 3.0,
                "max_positions": max_pos,
            }
        )
        midx += 1
        if midx > 12:
            break

    return sets


def main() -> int:
    parser = argparse.ArgumentParser(description="Run strategy parameter sweep.")
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--universe-file", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--sets-file", type=Path, default=DEFAULT_SETS)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--detail-dir", type=Path, default=DEFAULT_DETAIL_DIR)
    parser.add_argument(
        "--regenerate-sets",
        action="store_true",
        help="Rebuild parameter_sets.json with the built-in wide grid before running.",
    )
    parser.add_argument("--save-trade-files", action="store_true")
    args = parser.parse_args()

    if args.regenerate_sets or not args.sets_file.exists():
        sets_payload = build_default_parameter_sets()
        args.sets_file.write_text(json.dumps(sets_payload, indent=2), encoding="utf-8")
        log(f"Wrote {len(sets_payload)} parameter sets -> {args.sets_file}")

    if not args.data_file.exists():
        log(f"ERROR: data file not found: {args.data_file}")
        return 1

    parameter_sets = load_parameter_sets(args.sets_file)
    trade_symbols = load_trade_symbols(args.universe_file)

    log(f"Running {len(parameter_sets)} parameter sets")

    rows: list[dict] = []
    for index, (name, params) in enumerate(parameter_sets, start=1):
        regime_symbols = [params.regime_symbol.upper()]
        raw_prices = load_price_panel(args.data_file, trade_symbols + regime_symbols)
        prices = enrich_indicators(raw_prices, params)
        trades, equity, summary = run_backtest(prices, trade_symbols, params)

        row = {"rank_by_alpha": 0, "set_name": name}
        row.update(summary)
        row.update(asdict(params))
        rows.append(row)

        log(
            f"  [{index}/{len(parameter_sets)}] {name}: "
            f"{summary['total_return_pct']}% vs SPY {summary['spy_buy_hold_return_pct']}% "
            f"(alpha {summary['alpha_vs_spy_pct']}%) | trades {summary['total_trades']}"
        )

        if args.save_trade_files:
            run_dir = args.detail_dir / name
            run_dir.mkdir(parents=True, exist_ok=True)
            trades.to_csv(run_dir / "trades.csv", index=False)
            equity.to_csv(run_dir / "equity_curve.csv", index=False)

    results = pd.DataFrame(rows)
    results.sort_values(
        ["alpha_vs_spy_pct", "total_return_pct"],
        ascending=[False, False],
        inplace=True,
    )
    results["rank_by_alpha"] = range(1, len(results) + 1)
    results["sweep_run_at"] = datetime.now().replace(microsecond=0).isoformat(sep=" ")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output_csv, index=False)

    benchmark_path = args.output_csv.parent / "benchmark_spy.csv"
    spy_row = results.iloc[0][
        ["benchmark_start", "benchmark_end", "spy_buy_hold_return_pct", "spy_max_drawdown_pct"]
    ].to_dict()
    pd.DataFrame([spy_row]).to_csv(benchmark_path, index=False)

    log(f"Wrote comparison CSV -> {args.output_csv}")
    best = results.iloc[0]
    winners = int(results["beat_spy"].sum()) if "beat_spy" in results else 0
    log(
        f"Best alpha: {best['set_name']} ({best['alpha_vs_spy_pct']}% vs SPY, "
        f"return {best['total_return_pct']}%)"
    )
    log(f"Sets beating SPY: {winners}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
