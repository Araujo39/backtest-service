#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROGRESSIVE BATCH BACKTEST - Executa e salva resultados progressivamente
Permite que o frontend consulte os resultados enquanto executa
"""

import os
import sys
import json
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import threading
import time

DATA_DIR = "DATA_spot"
REPORTS_DIR = "reports"
PROGRESS_FILE = "reports/batch_progress.json"
CAPITAL = 100.0
TF = "15m"

MAX_DD_ACCEPTABLE = 0.15
MIN_TRADES = 30

def discover_strategies():
    """Descobre todas as estratégias .py no diretório strategies/"""
    strategies = []
    strategies_dir = "strategies"
    
    if not os.path.exists(strategies_dir):
        return ["swing", "fast", "sniper", "spot", "hybrid"]
    
    for f in os.listdir(strategies_dir):
        if f.endswith('.py') and f != '__init__.py':
            strategy_name = f.replace('.py', '')
            strategies.append(strategy_name)
    
    if not strategies:
        return ["swing", "fast", "sniper", "spot", "hybrid"]
    
    return sorted(strategies)

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

def update_progress(status, current, total, strategy=None, results=None):
    """Atualiza arquivo de progresso para o frontend consultar"""
    progress = {
        'status': status,
        'current': current,
        'total': total,
        'percentage': int((current / total) * 100) if total > 0 else 0,
        'current_strategy': strategy,
        'timestamp': datetime.now().isoformat(),
        'results': results or []
    }
    
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def calculate_strategy_rankings(all_results, assets):
    """Calcula ranking de estratégias"""
    strategy_rankings = []
    
    for strategy, results in all_results.items():
        valid_results = [r for r in results if r['score'] is not None]
        
        if not valid_results:
            final_score = -999
            valid_count = 0
            avg_profit = 0
            avg_wr = 0
            avg_dd = 0
            negative_assets = 0
        else:
            scores = [r['score'] for r in valid_results]
            avg_score = sum(scores) / len(scores)
            negative_penalty = sum(abs(s) for s in scores if s < 0) * 0.5
            final_score = avg_score - negative_penalty
            valid_count = len(valid_results)
            
            negative_assets = len([r for r in valid_results if r['score'] < 0])
            avg_profit = np.mean([r['result']['profit'] for r in valid_results])
            avg_wr = np.mean([r['result']['win_rate'] for r in valid_results])
            avg_dd = np.mean([r['result']['max_dd'] for r in valid_results])
        
        strategy_rankings.append({
            'strategy': strategy,
            'final_score': final_score,
            'valid_assets': valid_count,
            'total_assets': len(assets),
            'avg_profit': avg_profit,
            'avg_win_rate': avg_wr,
            'avg_dd': avg_dd,
            'negative_assets': negative_assets,
            'penalty': negative_assets * 5.0,
            'status': '✅ APROVADA' if final_score >= 0 else '❌ REJEITADA'
        })
    
    return sorted(strategy_rankings, key=lambda x: x['final_score'], reverse=True)

def main():
    print("=" * 70)
    print("PROGRESSIVE BATCH BACKTEST")
    print("=" * 70)
    
    assets = discover_assets()
    strategies = discover_strategies()
    
    total_combinations = len(strategies) * len(assets)
    
    print(f"📊 Ativos: {len(assets)}")
    print(f"📈 Estratégias: {len(strategies)}")
    print(f"🎯 Total: {total_combinations} combinações")
    print(f"\n🚀 Iniciando execução progressiva...")
    
    # Inicializar progresso
    update_progress('running', 0, total_combinations)
    
    all_results = {}
    current = 0
    
    for strategy in strategies:
        print(f"\n{'='*70}")
        print(f"Estratégia: {strategy.upper()}")
        print(f"{'='*70}")
        
        results = []
        
        for symbol in assets:
            current += 1
            print(f"  [{current}/{total_combinations}] {symbol}...", end=" ", flush=True)
            
            backtest_result = run_backtest(symbol, strategy)
            score = calculate_asset_score(backtest_result)
            
            results.append({
                'symbol': symbol,
                'score': score,
                'result': backtest_result or {}
            })
            
            # Atualizar progresso após cada backtest
            all_results[strategy] = results
            rankings = calculate_strategy_rankings(all_results, assets)
            
            update_progress(
                'running',
                current,
                total_combinations,
                strategy,
                rankings
            )
            
            if score is not None:
                print(f"✓ Score: {score:.2f}")
            else:
                print(f"✗ Falhou")
        
        all_results[strategy] = results
    
    # Calcular ranking final
    final_rankings = calculate_strategy_rankings(all_results, assets)
    
    final_report = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'capital': CAPITAL,
            'max_dd_acceptable': MAX_DD_ACCEPTABLE,
            'min_trades': MIN_TRADES
        },
        'assets': assets,
        'strategies': strategies,
        'strategy_rankings': final_rankings,
        'detailed_results': {k: [{'symbol': r['symbol'], 'score': r['score'], 
                                  'result': r['result']} for r in v] 
                            for k, v in all_results.items()}
    }
    
    # Salvar relatório final
    with open(f"{REPORTS_DIR}/full_report.json", 'w') as f:
        json.dump(final_report, f, indent=2)
    
    # Atualizar progresso como completo
    update_progress('completed', total_combinations, total_combinations, None, final_rankings)
    
    print(f"\n📁 Relatório salvo: {REPORTS_DIR}/full_report.json")
    print(f"📊 Progresso salvo: {PROGRESS_FILE}")
    print("\n" + "=" * 70)
    print("✅ ANÁLISE CONCLUÍDA")
    print("=" * 70)
    
    return final_report

if __name__ == "__main__":
    main()
