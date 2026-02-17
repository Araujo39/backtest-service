#!/usr/bin/env python3
import requests
import csv
from datetime import datetime
import time

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
           'ATOMUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT', 'MATICUSDT']

def download_2000_candles(symbol, interval='15m'):
    """Baixa 2000 candles (2 lotes de 1000)"""
    url = 'https://api.binance.us/api/v3/klines'
    
    print(f"📥 Baixando {symbol} (2000 candles)...", end=' ')
    
    # Lote 1: últimos 1000 candles
    response = requests.get(url, params={'symbol': symbol, 'interval': interval, 'limit': 1000}, timeout=10)
    response.raise_for_status()
    batch1 = response.json()
    end_time = batch1[0][0] - 1  # Timestamp antes do primeiro candle
    
    time.sleep(0.2)
    
    # Lote 2: 1000 candles anteriores
    response = requests.get(url, params={'symbol': symbol, 'interval': interval, 'limit': 1000, 'endTime': end_time}, timeout=10)
    response.raise_for_status()
    batch2 = response.json()
    
    # Combinar (batch2 primeiro, depois batch1 = ordem cronológica)
    all_candles = batch2 + batch1
    
    # Converter para formato CSV
    candles = []
    for candle in all_candles:
        timestamp = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        candles.append([
            timestamp,
            float(candle[1]),  # open
            float(candle[2]),  # high
            float(candle[3]),  # low
            float(candle[4]),  # close
            float(candle[5])   # volume
        ])
    
    # Salvar
    filename = f'DATA_spot/{symbol}.csv'
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        writer.writerows(candles)
    
    print(f"✅ {len(candles)} candles ({candles[0][0]} → {candles[-1][0]})")
    return len(candles)

if __name__ == '__main__':
    print("🚀 Baixando 2000 candles por símbolo...\n")
    
    total = 0
    for symbol in SYMBOLS:
        try:
            count = download_2000_candles(symbol)
            total += count
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ {symbol}: {str(e)[:80]}")
    
    print(f"\n✅ Total: {total} candles ({len(SYMBOLS)} símbolos)")
