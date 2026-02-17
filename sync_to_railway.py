#!/usr/bin/env python3
"""
Script para sincronizar dados locais atualizados com o Railway
Envia CSVs via endpoint /update-data
"""
import requests
import os
from pathlib import Path
import time

RAILWAY_URL = "https://backtest-service-production.up.railway.app"
DATA_DIR = Path("DATA_spot")

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 
           'ATOMUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT', 'MATICUSDT']

def upload_symbol_data(symbol):
    """Envia dados de um símbolo para Railway"""
    csv_path = DATA_DIR / f"{symbol}.csv"
    
    if not csv_path.exists():
        print(f"❌ {symbol}: arquivo não encontrado")
        return False
    
    print(f"📤 Enviando {symbol}...", end=' ', flush=True)
    
    try:
        with open(csv_path, 'rb') as f:
            files = {'file': (f'{symbol}.csv', f, 'text/csv')}
            data = {'symbol': symbol}
            
            response = requests.post(
                f"{RAILWAY_URL}/update-data",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                candles = result.get('candles_loaded', 0)
                first_date = result.get('first_date', 'N/A')
                last_date = result.get('last_date', 'N/A')
                print(f"✅ {candles} candles ({first_date} → {last_date})")
                return True
            else:
                print(f"❌ Erro {response.status_code}: {response.text[:100]}")
                return False
                
    except Exception as e:
        print(f"❌ Erro: {str(e)[:80]}")
        return False

def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  🚀 SINCRONIZANDO DADOS COM RAILWAY                      ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    
    # Verificar se Railway está online
    try:
        response = requests.get(f"{RAILWAY_URL}/", timeout=5)
        print(f"✅ Railway online: {response.json()['status']}\n")
    except Exception as e:
        print(f"❌ Railway offline: {e}\n")
        return
    
    success_count = 0
    failed_count = 0
    
    start_time = time.time()
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"[{i}/{len(SYMBOLS)}] ", end='')
        
        if upload_symbol_data(symbol):
            success_count += 1
        else:
            failed_count += 1
        
        # Rate limiting
        if i < len(SYMBOLS):
            time.sleep(0.3)
    
    elapsed = time.time() - start_time
    
    print()
    print("═" * 60)
    print(f"✅ Sucesso: {success_count}/{len(SYMBOLS)}")
    print(f"❌ Falhas:  {failed_count}/{len(SYMBOLS)}")
    print(f"⏱️  Tempo:   {elapsed:.1f}s")
    print("═" * 60)
    
    if success_count > 0:
        print("\n✅ Dados atualizados no Railway!")
        print("   Os backtests agora usarão dados de 27 Jan → 17 Fev 2026")
        print("\n🧪 Teste agora:")
        print(f"   curl -X POST \"{RAILWAY_URL}/run\" \\")
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"symbol":"BTCUSDT","strategy":"sniper_v21","capital":1000,"timeframe":"15m"}\'')

if __name__ == '__main__':
    main()
