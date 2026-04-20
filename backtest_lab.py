#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Engine — Canonical Metrics
All outputs use fixed scales: win_rate_pct (0-100), roi_pct (0-100),
max_drawdown_pct (positive %), fees modeled, Sortino/Calmar included.
"""

import argparse
import json
import math
import pandas as pd
import numpy as np
import importlib
import importlib.util
from pathlib import Path
from typing import Union

# ─── Config defaults ──────────────────────────────────────────────────────────
DEFAULT_COMMISSION_PCT = 0.1   # 0.1% per side (Binance taker)
DEFAULT_SLIPPAGE_PCT   = 0.05  # 0.05% slippage estimate
RISK_FREE_RATE_ANNUAL  = 0.05  # 5% annual (for Sharpe/Sortino)

CANDLES_PER_YEAR = {
    '1m':  525600, '3m': 175200, '5m': 105120, '15m': 35040,
    '30m': 17520,  '1h': 8760,   '2h': 4380,   '4h': 2190,
    '6h':  1460,   '8h': 1095,   '12h': 730,   '1d': 365,
}


def _load_strategy_by_path(name: str):
    """Load a strategy module from strategies/{name}.py using file path (supports dots/hyphens in name)."""
    strategy_path = Path('strategies') / f'{name}.py'
    if not strategy_path.exists():
        raise FileNotFoundError(f'Strategy not found: {name}')
    spec = importlib.util.spec_from_file_location(f'strategy_{id(name)}', strategy_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_dataframe_from_candles(ohlcv: list) -> pd.DataFrame:
    """Convert [{t,o,h,l,c,v}, ...] inline payload to DataFrame."""
    df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    df = df.rename(columns={'t': 'timestamp', 'o': 'open', 'h': 'high',
                             'l': 'low', 'c': 'close', 'v': 'volume'})
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ('open', 'high', 'low', 'close', 'volume'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna(subset=['close']).reset_index(drop=True)


def load_dataframe_from_csv(data_dir: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(f"{data_dir}/{symbol}.csv")
    # Normalise column names
    df.columns = [c.lower().strip() for c in df.columns]
    rename = {'time': 'timestamp', 'date': 'timestamp',
              'open_price': 'open', 'close_price': 'close'}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if 'timestamp' in df.columns:
        try:
            ts = pd.to_numeric(df['timestamp'], errors='coerce')
            if ts.notna().all():
                df['timestamp'] = pd.to_datetime(ts, unit='ms')
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
        except Exception:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    for col in ('open', 'high', 'low', 'close', 'volume'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna(subset=['close']).reset_index(drop=True)


def calculate_sortino(returns: pd.Series, rf_per_period: float) -> float:
    excess = returns - rf_per_period
    downside = excess[excess < 0]
    downside_std = math.sqrt((downside ** 2).mean()) if len(downside) > 0 else 0
    return float(excess.mean() / downside_std) if downside_std > 0 else 0.0


def calculate_calmar(roi_pct: float, max_dd_pct: float, periods: int, tf: str) -> float:
    if max_dd_pct <= 0 or periods <= 0:
        return 0.0
    cpy = CANDLES_PER_YEAR.get(tf, 35040)
    years = periods / cpy
    annual_roi = roi_pct / max(years, 0.01)
    return round(annual_roi / max_dd_pct, 3)


def simulate_trades(df: pd.DataFrame, capital: float, commission_pct: float, slippage_pct: float):
    """
    Walk through signals: 1=buy, -1=sell, 0=hold.
    Models commission + slippage on both entry and exit.
    Returns (trades, equity_curve, final_equity).
    """
    cost_per_side = (commission_pct + slippage_pct) / 100.0

    trades = []
    equity = capital
    equity_curve = []
    position_qty = 0.0
    entry_price = 0.0
    entry_time = None

    signals = df['signal'].values
    closes = df['close'].values
    timestamps = df['timestamp'].values if 'timestamp' in df.columns else np.arange(len(df))

    for i in range(len(df)):
        sig = signals[i]
        price = float(closes[i])
        ts = str(timestamps[i])

        if sig == 1 and position_qty == 0:
            # Entry: pay slippage + commission on the way in
            effective_entry = price * (1 + cost_per_side)
            position_qty = equity / effective_entry
            entry_price = effective_entry
            entry_time = ts

        elif sig == -1 and position_qty > 0:
            # Exit: pay slippage + commission on the way out
            effective_exit = price * (1 - cost_per_side)
            pnl = (effective_exit - entry_price) * position_qty
            equity += pnl
            gross_pnl = (price - entry_price / (1 + cost_per_side)) * position_qty
            fee_paid = abs(gross_pnl - pnl)

            trades.append({
                'entry_time':  entry_time,
                'exit_time':   ts,
                'entry_price': round(entry_price / (1 + cost_per_side), 6),
                'exit_price':  round(price, 6),
                'direction':   'LONG',
                'pnl_usd':     round(pnl, 4),
                'pnl_pct':     round((effective_exit - entry_price) / entry_price * 100, 4),
                'fee_paid':    round(fee_paid, 4),
            })
            position_qty = 0.0
            entry_price = 0.0

        # Mark-to-market equity for curve
        if position_qty > 0:
            mtm = equity + (price * (1 - cost_per_side) - entry_price) * position_qty
            equity_curve.append({'timestamp': ts, 'equity': round(mtm, 4)})
        else:
            equity_curve.append({'timestamp': ts, 'equity': round(equity, 4)})

    # Force-close open position at last price
    if position_qty > 0:
        price = float(closes[-1])
        effective_exit = price * (1 - cost_per_side)
        pnl = (effective_exit - entry_price) * position_qty
        equity += pnl
        gross_pnl = (price - entry_price / (1 + cost_per_side)) * position_qty
        fee_paid = abs(gross_pnl - pnl)
        trades.append({
            'entry_time':  entry_time,
            'exit_time':   str(timestamps[-1]),
            'entry_price': round(entry_price / (1 + cost_per_side), 6),
            'exit_price':  round(price, 6),
            'direction':   'LONG',
            'pnl_usd':     round(pnl, 4),
            'pnl_pct':     round((effective_exit - entry_price) / entry_price * 100, 4),
            'fee_paid':    round(fee_paid, 4),
        })
        equity_curve[-1]['equity'] = round(equity, 4)

    return trades, equity_curve, equity


def calculate_backtest_metrics(
    df_result: Union[pd.DataFrame, dict],
    capital: float,
    symbol: str = '',
    strategy: str = '',
    timeframe: str = '15m',
    config: dict = None,
) -> dict:
    """
    Canonical output — always consistent scales:
      win_rate_pct  in [0, 100]
      roi_pct       can be negative
      max_drawdown_pct positive %
    """
    cfg = config or {}
    commission_pct = float(cfg.get('commission_pct', DEFAULT_COMMISSION_PCT))
    slippage_pct   = float(cfg.get('slippage_pct',   DEFAULT_SLIPPAGE_PCT))

    # ── Handle legacy dict return from old strategies ──────────────────────
    if isinstance(df_result, dict):
        raw = df_result
        win_rate_raw = float(raw.get('win_rate', 0))
        win_rate_pct = win_rate_raw if win_rate_raw > 1 else win_rate_raw * 100
        max_dd_raw = float(raw.get('max_dd', raw.get('max_drawdown', 0)))
        max_dd_pct = max_dd_raw if max_dd_raw > 1 else max_dd_raw * 100
        roi_raw = float(raw.get('roi', raw.get('return', 0)))
        roi_pct = roi_raw if abs(roi_raw) > 1 else roi_raw * 100
        return {
            'success': True, 'symbol': symbol, 'strategy': strategy, 'timeframe': timeframe,
            'capital_start': capital, 'capital_end': round(float(raw.get('final_equity', capital)), 2),
            'roi_pct': round(roi_pct, 2), 'win_rate_pct': round(win_rate_pct, 2),
            'max_drawdown_pct': round(abs(max_dd_pct), 2),
            'total_trades': int(raw.get('n_trades', raw.get('total_trades', 0))),
            'winning_trades': int(raw.get('profitable_trades', 0)),
            'losing_trades': int(raw.get('losing_trades', 0)),
            'profit_factor': round(float(raw.get('profit_factor', 0)), 3),
            'sharpe_ratio': round(float(raw.get('sharpe_ratio', 0)), 3),
            'sortino_ratio': 0.0, 'calmar_ratio': 0.0,
            'total_fees_paid': 0.0,
            'equity_curve': [], 'trades': raw.get('trades', []),
        }

    # ── DataFrame path ─────────────────────────────────────────────────────
    df = df_result
    if 'signal' not in df.columns:
        return {'success': False, 'error': "DataFrame missing 'signal' column"}

    trades, equity_curve, final_equity = simulate_trades(df, capital, commission_pct, slippage_pct)

    if not trades:
        return {
            'success': True, 'symbol': symbol, 'strategy': strategy, 'timeframe': timeframe,
            'capital_start': capital, 'capital_end': round(capital, 2),
            'roi_pct': 0.0, 'win_rate_pct': 0.0, 'max_drawdown_pct': 0.0,
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
            'profit_factor': 0.0, 'sharpe_ratio': 0.0, 'sortino_ratio': 0.0, 'calmar_ratio': 0.0,
            'avg_trade_pct': 0.0, 'avg_win_pct': 0.0, 'avg_loss_pct': 0.0,
            'best_trade_pct': 0.0, 'worst_trade_pct': 0.0,
            'total_fees_paid': 0.0, 'equity_curve': equity_curve, 'trades': [],
        }

    winning = [t for t in trades if t['pnl_usd'] > 0]
    losing  = [t for t in trades if t['pnl_usd'] <= 0]

    gross_profit = sum(t['pnl_usd'] for t in winning)
    gross_loss   = abs(sum(t['pnl_usd'] for t in losing))
    total_fees   = sum(t['fee_paid'] for t in trades)
    roi_pct      = (final_equity - capital) / capital * 100

    # Drawdown from equity curve
    eq_series = pd.Series([e['equity'] for e in equity_curve])
    running_max = eq_series.expanding().max()
    dd_series = (eq_series - running_max) / running_max * 100
    max_dd_pct = abs(float(dd_series.min()))

    # Per-trade returns for Sharpe / Sortino
    trade_returns = pd.Series([t['pnl_pct'] for t in trades])
    cpy = CANDLES_PER_YEAR.get(timeframe, 35040)
    rf_per_trade = (RISK_FREE_RATE_ANNUAL / (cpy / max(len(df), 1))) / 100

    std = trade_returns.std()
    sharpe  = float(trade_returns.mean() / std) if std > 0 else 0.0
    sortino = calculate_sortino(trade_returns, rf_per_trade)
    calmar  = calculate_calmar(roi_pct, max_dd_pct, len(df), timeframe)

    pnl_pcts = [t['pnl_pct'] for t in trades]
    win_pcts  = [t['pnl_pct'] for t in winning]
    loss_pcts = [t['pnl_pct'] for t in losing]

    return {
        'success': True,
        'symbol': symbol, 'strategy': strategy, 'timeframe': timeframe,
        # Capital
        'capital_start':    round(capital, 2),
        'capital_end':      round(final_equity, 2),
        'net_profit':       round(final_equity - capital, 2),
        'roi_pct':          round(roi_pct, 2),
        # Trades
        'total_trades':     len(trades),
        'winning_trades':   len(winning),
        'losing_trades':    len(losing),
        'win_rate_pct':     round(len(winning) / len(trades) * 100, 2),
        # P&L breakdown
        'gross_profit':     round(gross_profit, 2),
        'gross_loss':       round(gross_loss, 2),
        'profit_factor':    round(gross_profit / gross_loss, 3) if gross_loss > 0 else 999.0,
        # Averages
        'avg_trade_pct':    round(float(np.mean(pnl_pcts)), 3),
        'avg_win_pct':      round(float(np.mean(win_pcts)), 3) if win_pcts else 0.0,
        'avg_loss_pct':     round(float(np.mean(loss_pcts)), 3) if loss_pcts else 0.0,
        'best_trade_pct':   round(float(max(pnl_pcts)), 3),
        'worst_trade_pct':  round(float(min(pnl_pcts)), 3),
        # Risk metrics
        'max_drawdown_pct': round(max_dd_pct, 2),
        'sharpe_ratio':     round(sharpe, 3),
        'sortino_ratio':    round(sortino, 3),
        'calmar_ratio':     round(calmar, 3),
        # Costs
        'total_fees_paid':  round(total_fees, 4),
        'commission_pct':   commission_pct,
        'slippage_pct':     slippage_pct,
        # Series (trimmed to 200 points for JSON size)
        'equity_curve': equity_curve[::max(1, len(equity_curve)//200)],
        'trades': trades[:100],
    }


def run_backtest_from_df(
    df: pd.DataFrame,
    strategy_module,
    capital: float,
    symbol: str,
    strategy: str,
    timeframe: str,
    config: dict,
) -> dict:
    """High-level: run_strategy → calculate_metrics."""
    result_df = strategy_module.run_strategy(df, capital=capital)
    return calculate_backtest_metrics(result_df, capital, symbol, strategy, timeframe, config)


# ─── CLI entrypoint ────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description='Backtest Lab — Canonical Metrics')
    p.add_argument('--data_dir', required=True)
    p.add_argument('--symbol',   required=True)
    p.add_argument('--tf',       default='15m')
    p.add_argument('--strategy', required=True)
    p.add_argument('--capital',  type=float, default=1000.0)
    p.add_argument('--commission', type=float, default=DEFAULT_COMMISSION_PCT)
    p.add_argument('--slippage',   type=float, default=DEFAULT_SLIPPAGE_PCT)
    p.add_argument('--out',      default='reports/report.json')
    args = p.parse_args()

    df = load_dataframe_from_csv(args.data_dir, args.symbol)
    mod = _load_strategy_by_path(args.strategy)
    config = {'commission_pct': args.commission, 'slippage_pct': args.slippage}

    metrics = run_backtest_from_df(df, mod, args.capital, args.symbol, args.strategy, args.tf, config)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    print(f'OK — {args.symbol}/{args.strategy} → {metrics["total_trades"]} trades, ROI {metrics["roi_pct"]}%')


def run_strategy(df, capital=1000, **params):
    raise NotImplementedError('backtest_lab.py is not a strategy module')


if __name__ == '__main__':
    main()
