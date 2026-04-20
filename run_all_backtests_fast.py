#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAST BATCH BACKTEST - Executa apenas estratégias built-in (5) para evitar timeout
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

MAX_DD_ACCEPTABLE = 0.15
MIN_TRADES = 5

# Apenas estratégias built-in para execução rápida
STRATEGIES = ["swing", "fast", "sniper", "spot", "hybrid"]

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
        "python3", "backtest_lab.py",
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
    except Exception:
        return None

def _normalize(result: dict) -> dict:
    """Support both old (profit/win_rate/n_trades) and new (roi_pct/win_rate_pct/total_trades) schemas."""
    profit   = result.get('roi_pct',   result.get('profit',   0)) or 0
    n_trades = result.get('total_trades', result.get('n_trades', 0)) or 0
    max_dd   = result.get('max_drawdown_pct', result.get('max_dd', 0)) or 0
    win_rate = result.get('win_rate_pct', result.get('win_rate', 0)) or 0
    if 0 < win_rate <= 1.0:
        win_rate *= 100
    return {'profit': profit, 'win_rate': win_rate, 'max_dd': max_dd, 'n_trades': n_trades}

def calculate_asset_score(result):
    if result is None:
        return None

    r = _normalize(result)
    if r['n_trades'] < MIN_TRADES:
        return None

    score = (r['profit'] * 1.0) + (r['win_rate'] * 0.3) - (r['max_dd'] * 1.2)
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
    print("FAST BATCH BACKTEST - Built-in Strategies Only")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    assets = discover_assets()
    print(f"\n📊 ATIVOS: {len(assets)}")
    
    print(f"\n📈 ESTRATÉGIAS: {len(STRATEGIES)}")
    for s in STRATEGIES:
        print(f"   - {s}")
    
    print(f"\n⚡ Total de combinações: {len(STRATEGIES)} × {len(assets)} = {len(STRATEGIES) * len(assets)}")
    print("\n🚀 Iniciando execução...")
    
    all_results = {}
    
    for strategy in STRATEGIES:
        print(f"\n{'='*70}")
        print(f"Processando estratégia: {strategy.upper()}")
        print(f"{'='*70}")
        
        results = []
        for i, symbol in enumerate(assets, 1):
            print(f"  [{i}/{len(assets)}] {symbol}...", end=" ", flush=True)
            
            backtest_result = run_backtest(symbol, strategy)
            score = calculate_asset_score(backtest_result)
            
            results.append({
                'symbol': symbol,
                'score': score,
                'result': backtest_result or {}
            })
            
            if score is not None:
                print(f"✓ Score: {score:.2f}")
            else:
                print(f"✗ Falhou")
        
        all_results[strategy] = results
    
    print("\n" + "=" * 70)
    print("CALCULANDO RANKING")
    print("=" * 70)
    
    strategy_rankings = []
    
    for strategy in STRATEGIES:
        results = all_results[strategy]
        valid_results = [r for r in results if r['score'] is not None]
        
        final_score, valid_count = calculate_strategy_score(valid_results)
        
        negative_assets = len([r for r in valid_results if r['score'] < 0])
        norm = [_normalize(r['result']) for r in valid_results] if valid_results else []
        avg_profit = np.mean([n['profit']   for n in norm]) if norm else 0
        avg_wr     = np.mean([n['win_rate'] for n in norm]) if norm else 0
        avg_dd     = np.mean([n['max_dd']   for n in norm]) if norm else 0
        
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
