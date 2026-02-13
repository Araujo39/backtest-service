#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWING Strategy - Swing trading otimizado
"""

import pandas as pd
import numpy as np

def run_strategy(df, capital=100.0, **params):
    data = df.copy()
    
    data['sma_20'] = data['close'].rolling(window=20).mean()
    data['sma_50'] = data['close'].rolling(window=50).mean()
    data['ema_9'] = data['close'].ewm(span=9, adjust=False).mean()
    
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    data['high_low'] = data['high'] - data['low']
    data['high_close'] = abs(data['high'] - data['close'].shift())
    data['low_close'] = abs(data['low'] - data['close'].shift())
    data['tr'] = data[['high_low', 'high_close', 'low_close']].max(axis=1)
    data['atr'] = data['tr'].rolling(window=14).mean()
    
    data['signal'] = 0
    buy_cond = (
        (data['ema_9'] > data['sma_20']) & 
        (data['rsi'] < 65) &
        (data['rsi'] > 25)
    )
    data.loc[buy_cond & (data['ema_9'].shift(1) <= data['sma_20'].shift(1)), 'signal'] = 1
    
    sell_cond = (
        (data['ema_9'] < data['sma_20']) & 
        (data['ema_9'].shift(1) >= data['sma_20'].shift(1))
    )
    data.loc[sell_cond, 'signal'] = -1
    
    trades = []
    position = None
    
    for i, row in data.iterrows():
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            continue
            
        if position is None:
            if row['signal'] == 1:
                entry_price = row['close']
                stop_loss = entry_price - 1.2 * row['atr']
                take_profit = entry_price + 2.4 * row['atr']
                position = {'entry': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'entry_idx': i}
        else:
            exit_price = None
            exit_reason = None
            
            if row['low'] <= position['stop_loss']:
                exit_price = position['stop_loss']
                exit_reason = 'stop_loss'
            elif row['high'] >= position['take_profit']:
                exit_price = position['take_profit']
                exit_reason = 'take_profit'
            elif row['signal'] == -1:
                exit_price = row['close']
                exit_reason = 'signal'
            
            if exit_price:
                pnl_pct = (exit_price - position['entry']) / position['entry']
                trades.append({'entry': position['entry'], 'exit': exit_price, 'pnl_pct': pnl_pct, 'exit_reason': exit_reason})
                position = None
    
    if position:
        last_price = data.iloc[-1]['close']
        pnl_pct = (last_price - position['entry']) / position['entry']
        trades.append({'entry': position['entry'], 'exit': last_price, 'pnl_pct': pnl_pct, 'exit_reason': 'end_of_data'})
    
    if not trades:
        return {"strategy": "SWING", "capital_start": capital, "capital_end": capital, "profit": 0, "win_rate": 0, "max_dd": 0, "n_trades": 0}
    
    equity = capital
    equity_values = [capital]
    for t in trades:
        equity = equity * (1 + t['pnl_pct'])
        equity_values.append(equity)
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    win_rate = len(wins) / len(trades) if trades else 0
    
    peak = capital
    max_dd = 0
    for eq in equity_values:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd: max_dd = dd
    
    return {
        "strategy": "SWING",
        "capital_start": capital,
        "capital_end": round(equity_values[-1], 2),
        "profit": round(equity_values[-1] - capital, 2),
        "win_rate": round(win_rate, 4),
        "max_dd": round(max_dd, 4),
        "n_trades": len(trades)
    }
