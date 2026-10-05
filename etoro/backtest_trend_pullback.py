#!/usr/bin/env python3
"""Compatibility wrapper — use backtest_strategies.py for new work."""

from backtest_strategies import main, run_backtest, write_outputs
from backtest_common import StrategyParams, enrich_indicators, load_price_panel, load_trade_symbols

__all__ = [
    "main",
    "run_backtest",
    "write_outputs",
    "StrategyParams",
    "enrich_indicators",
    "load_price_panel",
    "load_trade_symbols",
]

if __name__ == "__main__":
    raise SystemExit(main())
