#!/usr/bin/env python3
"""
Baixa os últimos 2000 candles de 15min da Binance (dados ATUALIZADOS)
"""
import requests
import csv
from datetime import datetime
import time

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
           'ATOMUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT', 'MATICUSDT']

def download_candles(symbol, interval='15m', limit=2000):
    """Baixa candles via API pública da Binance"""
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    print(f"📥 Baixando {symbol}...", end=' ')
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    # Converter timestamps para datetime
    candles = []
    for candle in data:
        timestamp = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        open_price = float(candle[1])
        high = float(candle[2])
        low = float(candle[3])
        close = float(candle[4])
        volume = float(candle[5])
        candles.append([timestamp, open_price, high, low, close, volume])
    
    # Salvar em CSV
    filename = f'DATA_spot/{symbol}.csv'
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        writer.writerows(candles)
    
    first_date = candles[0][0]
    last_date = candles[-1][0]
    print(f"✅ {len(candles)} candles ({first_date} → {last_date})")
    return len(candles)

if __name__ == '__main__':
    print("🚀 Baixando dados ATUALIZADOS da Binance API...\n")
    
    total = 0
    for symbol in SYMBOLS:
        try:
            count = download_candles(symbol)
            total += count
            time.sleep(0.2)  # Rate limit
        except Exception as e:
            print(f"❌ Erro em {symbol}: {e}")
    
    print(f"\n✅ Total: {total} candles baixados ({len(SYMBOLS)} símbolos)")
    print(f"📁 Salvos em: DATA_spot/")
