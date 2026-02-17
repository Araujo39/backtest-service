#!/usr/bin/env python3
"""
Envia os dados atualizados (CSV) para o serviço Railway
usando o endpoint /upload-data
"""
import requests
import os

RAILWAY_URL = "https://backtest-service-production.up.railway.app"
DATA_DIR = "DATA_spot"

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
           'ATOMUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT', 'MATICUSDT']

def upload_csv(symbol):
    """Envia arquivo CSV para Railway"""
    filepath = f"{DATA_DIR}/{symbol}.csv"
    
    if not os.path.exists(filepath):
        print(f"❌ Arquivo não encontrado: {filepath}")
        return False
    
    print(f"📤 Enviando {symbol}...", end=' ')
    
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (f'{symbol}.csv', f, 'text/csv')}
            data = {'symbol': symbol}
            
            response = requests.post(
                f"{RAILWAY_URL}/upload-data",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result.get('candles_loaded', 0)} candles carregados")
                return True
            else:
                print(f"❌ Erro {response.status_code}: {response.text[:100]}")
                return False
                
    except Exception as e:
        print(f"❌ Erro: {str(e)[:80]}")
        return False

if __name__ == '__main__':
    print("🚀 Enviando dados atualizados para Railway...\n")
    
    success = 0
    failed = 0
    
    for symbol in SYMBOLS:
        if upload_csv(symbol):
            success += 1
        else:
            failed += 1
    
    print(f"\n📊 Resultado: {success} sucessos, {failed} falhas")
    
    if success > 0:
        print("\n✅ Dados atualizados no Railway!")
        print("   Agora pode rodar backtests com dados de 2026")
