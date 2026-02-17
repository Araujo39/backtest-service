#!/usr/bin/env python3
import requests
import csv
from datetime import datetime
import time

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
           'ATOMUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT', 'MATICUSDT']

def download_candles(symbol, interval='15m', limit=1000):
    """Baixa via Binance.US (sem geo-blocking)"""
    url = 'https://api.binance.us/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    print(f"📥 Baixando {symbol}...", end=' ')
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    candles = []
    for candle in data:
        timestamp = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        candles.append([
            timestamp,
            float(candle[1]),  # open
            float(candle[2]),  # high
            float(candle[3]),  # low
            float(candle[4]),  # close
            float(candle[5])   # volume
        ])
    
    filename = f'DATA_spot/{symbol}.csv'
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        writer.writerows(candles)
    
    print(f"✅ {len(candles)} candles ({candles[0][0]} → {candles[-1][0]})")
    return len(candles)

if __name__ == '__main__':
    print("🚀 Tentando Binance.US API...\n")
    
    total = 0
    for symbol in SYMBOLS:
        try:
            count = download_candles(symbol)
            total += count
            time.sleep(0.3)
        except Exception as e:
            print(f"❌ {symbol}: {str(e)[:80]}")
    
    print(f"\n✅ Total: {total} candles")
