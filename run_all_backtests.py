#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QUANT RESEARCH & STRATEGY OPTIMIZATION AGENT
Executa backtests em todos os ativos, avalia múltiplas estratégias
"""

import os
import sys
import json
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

DATA_DIR = "DATA_spot"
REPORTS_DIR = "reports"
CAPITAL = 100.0
TF = "15m"
STRATEGIES_DIR = "strategies"  # Diretório de estratégias deployadas

MAX_DD_ACCEPTABLE = 0.15
MIN_TRADES = 30

# Descobrir dinamicamente todas as estratégias deployadas
def discover_strategies():
    """Descobre todas as estratégias .py no diretório strategies/"""
    strategies = []
    if not os.path.exists(STRATEGIES_DIR):
        print(f"⚠️  Diretório {STRATEGIES_DIR} não encontrado, usando estratégias padrão")
        return ["swing", "fast", "sniper", "spot", "hybrid"]
    
    for f in os.listdir(STRATEGIES_DIR):
        if f.endswith('.py') and f != '__init__.py':
            strategy_name = f.replace('.py', '')
            strategies.append(strategy_name)
    
    if not strategies:
        print(f"⚠️  Nenhuma estratégia encontrada em {STRATEGIES_DIR}, usando padrão")
        return ["swing", "fast", "sniper", "spot", "hybrid"]
    
    print(f"✅ Encontradas {len(strategies)} estratégias: {', '.join(strategies[:5])}...")
    return sorted(strategies)

STRATEGIES = discover_strategies()

def discover_assets():
    assets = []
    for f in os.listdir(DATA_DIR):
        if f.endswith('.csv'):
            symbol = f.replace('.csv', '')
            assets.append(symbol)
    return sorted(assets)

def run_backtest(symbol, strategy):
    out_file = f"{REPORTS_DIR}/{strategy}_{symbol}.json"
    cmd = [
        "python", "backtest_lab.py",
        "--data_dir", DATA_DIR,
        "--symbol", symbol,
        "--tf", TF,
        "--strategy", strategy,
        "--capital", str(CAPITAL),
        "--out", out_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            with open(out_file, 'r') as f:
                return json.load(f)
        else:
            return None
    except Exception as e:
        return None

def calculate_asset_score(result):
    if result is None:
        return None
    
    profit = result.get('profit', 0)
    win_rate = result.get('win_rate', 0)
    max_dd = result.get('max_dd', 0)
    n_trades = result.get('n_trades', 0)
    
    if n_trades < MIN_TRADES:
        return None
    
    score = (profit * 1.0) + (win_rate * 0.3) - (max_dd * 1.2)
    return score

def calculate_strategy_score(asset_results):
    scores = [r['score'] for r in asset_results if r['score'] is not None]
    
    if not scores:
        return None, 0
    
    avg_score = sum(scores) / len(scores)
    negative_penalty = sum(abs(s) for s in scores if s < 0) * 0.5
    
    final_score = avg_score - negative_penalty
    return final_score, len(scores)

def main():
    print("=" * 70)
    print("QUANT RESEARCH & STRATEGY OPTIMIZATION AGENT")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    assets = discover_assets()
    print(f"\n📊 ATIVOS DESCOBERTOS: {len(assets)}")
    for a in assets:
        print(f"   - {a}")
    
    print(f"\n📈 ESTRATÉGIAS: {len(STRATEGIES)}")
    for s in STRATEGIES:
        print(f"   - {s}")
    
    all_results = {}
    
    print("\n" + "=" * 70)
    print("EXECUTANDO BACKTESTS...")
    print("=" * 70)
    
    for strategy in STRATEGIES:
        all_results[strategy] = []
        print(f"\n{'='*30}")
        print(f"ESTRATÉGIA: {strategy.upper()}")
        print(f"{'='*30}")
        
        for symbol in assets:
            print(f"\n  🔄 Backtest: {strategy.upper()} / {symbol}")
            result = run_backtest(symbol, strategy)
            
            if result:
                score = calculate_asset_score(result)
                
                if score is None:
                    if result.get('n_trades', 0) < MIN_TRADES:
                        print(f"  ⚠️  Poucos trades: {result.get('n_trades', 0)} < {MIN_TRADES} - DESCARTADO")
                    print(f"     ✗ DESCARTADO (critérios não atendidos)")
                else:
                    dd_status = "⚠️" if result.get('max_dd', 1) > MAX_DD_ACCEPTABLE else "✓"
                    print(f"     {dd_status} Profit: {result.get('profit', 0):.2f}")
                    print(f"     {dd_status} Win Rate: {result.get('win_rate', 0)*100:.2f}%")
                    print(f"     {dd_status} Max DD: {result.get('max_dd', 0)*100:.2f}%")
                    print(f"     {dd_status} Trades: {result.get('n_trades', 0)}")
                    print(f"     {dd_status} SCORE: {score:.4f}")
                
                all_results[strategy].append({
                    'symbol': symbol,
                    'result': result,
                    'score': score
                })
            else:
                print(f"     ✗ ERRO no backtest")
    
    print("\n" + "=" * 70)
    print("RESULTADOS FINAIS")
    print("=" * 70)
    
    strategy_rankings = []
    
    for strategy in STRATEGIES:
        results = all_results[strategy]
        valid_results = [r for r in results if r['score'] is not None]
        
        final_score, valid_count = calculate_strategy_score(valid_results)
        
        negative_assets = len([r for r in valid_results if r['score'] < 0])
        avg_profit = np.mean([r['result']['profit'] for r in valid_results]) if valid_results else 0
        avg_wr = np.mean([r['result']['win_rate'] for r in valid_results]) if valid_results else 0
        avg_dd = np.mean([r['result']['max_dd'] for r in valid_results]) if valid_results else 0
        
        penalty = negative_assets * 5.0
        
        strategy_rankings.append({
            'strategy': strategy,
            'final_score': final_score if final_score else -999,
            'valid_assets': valid_count,
            'total_assets': len(assets),
            'avg_profit': avg_profit,
            'avg_win_rate': avg_wr,
            'avg_dd': avg_dd,
            'negative_assets': negative_assets,
            'penalty': penalty,
            'status': '✅ APROVADA' if final_score and final_score >= 0 else '❌ REJEITADA'
        })
        
        print(f"\n📊 ESTRATÉGIA: {strategy.upper()}")
        print(f"   Score Médio: {final_score:.4f}" if final_score else "   Score Médio: N/A")
        print(f"   Ativos Negativos: {negative_assets}")
        print(f"   Ativos Válidos: {valid_count}/{len(assets)}")
    
    print("\n" + "=" * 70)
    print("RANKING DE ESTRATÉGIAS")
    print("=" * 70)
    
    sorted_strategies = sorted(strategy_rankings, key=lambda x: x['final_score'], reverse=True)
    
    for i, s in enumerate(sorted_strategies, 1):
        if s['final_score'] >= 0:
            print(f"  {i}º - {s['strategy'].upper()}: {s['final_score']:.4f} {s['status']}")
        else:
            print(f"  {i}º - {s['strategy'].upper()}: REJEITADA {s['status']}")
    
    final_report = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'capital': CAPITAL,
            'max_dd_acceptable': MAX_DD_ACCEPTABLE,
            'min_trades': MIN_TRADES
        },
        'assets': assets,
        'strategies': STRATEGIES,
        'strategy_rankings': strategy_rankings,
        'detailed_results': {k: [{'symbol': r['symbol'], 'score': r['score'], 
                                  'result': r['result']} for r in v] 
                            for k, v in all_results.items()}
    }
    
    with open(f"{REPORTS_DIR}/full_report.json", 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print(f"\n📁 Relatório completo salvo em: {REPORTS_DIR}/full_report.json")
    print("\n" + "=" * 70)
    print("ANÁLISE CONCLUÍDA")
    print("=" * 70)
    
    return final_report

if __name__ == "__main__":
    main()
