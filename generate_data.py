#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de dados sintéticos realistas para backtesting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_realistic_data(n_candles=2000, start_price=50000, volatility=0.02, trend=0.0001, seed=None):
    if seed is not None:
        np.random.seed(seed)
    
    returns = np.random.normal(trend, volatility, n_candles)
    prices = start_price * np.cumprod(1 + returns)
    
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(n_candles)]
    
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        intraday_var = abs(np.random.normal(0, volatility * close * 0.5))
        
        open_price = prices[i-1] if i > 0 else close
        high = max(open_price, close) + intraday_var
        low = min(open_price, close) - intraday_var
        
        base_volume = 1000
        volume = base_volume * (1 + abs(returns[i]) / volatility * 2)
        volume = int(volume * np.random.uniform(0.5, 1.5))
        
        data.append({
            'timestamp': ts,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
    
    return pd.DataFrame(data)

def main():
    assets_config = {
        'BTCUSDT': {'start_price': 45000, 'volatility': 0.015, 'trend': 0.0002},
        'ETHUSDT': {'start_price': 2500, 'volatility': 0.018, 'trend': 0.00015},
        'BNBUSDT': {'start_price': 300, 'volatility': 0.02, 'trend': 0.0001},
        'SOLUSDT': {'start_price': 100, 'volatility': 0.025, 'trend': 0.00025},
        'ADAUSDT': {'start_price': 0.45, 'volatility': 0.024, 'trend': 0.00008},
        'ATOMUSDT': {'start_price': 10, 'volatility': 0.023, 'trend': 0.00012},
        'AVAXUSDT': {'start_price': 35, 'volatility': 0.022, 'trend': 0.00018},
        'DOGEUSDT': {'start_price': 0.08, 'volatility': 0.03, 'trend': 0.00015},
        'MATICUSDT': {'start_price': 0.9, 'volatility': 0.021, 'trend': 0.0001},
        'XRPUSDT': {'start_price': 0.5, 'volatility': 0.022, 'trend': 0.00005},
    }
    
    n_candles = 2000
    
    print(f"Gerando {n_candles} candles para {len(assets_config)} ativos...")
    
    for i, (symbol, config) in enumerate(assets_config.items()):
        print(f"  [{i+1}/{len(assets_config)}] {symbol}...", end=" ")
        
        df = generate_realistic_data(
            n_candles=n_candles,
            start_price=config['start_price'],
            volatility=config['volatility'],
            trend=config['trend'],
            seed=42 + i
        )
        
        filename = f"DATA/{symbol}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ ({len(df)} candles)")
    
    print("\n✅ Dados gerados com sucesso!")

if __name__ == "__main__":
    main()
