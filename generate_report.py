#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RELATÓRIO FINAL DE BACKTESTING
"""

import json
from datetime import datetime

def generate_final_report():
    with open('reports/full_report.json', 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("                    RELATÓRIO FINAL DE BACKTESTING")
    print("=" * 80)
    print(f"\nData: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n{'='*80}")
    print("RANKING DE ESTRATÉGIAS")
    print(f"{'='*80}")
    
    rankings = sorted(data['strategy_rankings'], key=lambda x: x['final_score'], reverse=True)
    
    for i, s in enumerate(rankings, 1):
        status_icon = "✅" if s['final_score'] >= 0 else "❌"
        print(f"\n  {i}º {s['strategy'].upper()}: {status_icon}")
        print(f"     Score Final: {s['final_score']:.2f}")
        print(f"     Ativos Válidos: {s['valid_assets']}/{s['total_assets']}")
        if s['valid_assets'] > 0:
            print(f"     Profit Médio: ${s['avg_profit']:.2f}")
            print(f"     Win Rate Médio: {s['avg_win_rate']*100:.1f}%")
            print(f"     Drawdown Médio: {s['avg_dd']*100:.1f}%")
    
    print(f"\n{'='*80}")
    print("MELHORES COMBINAÇÕES")
    print(f"{'='*80}")
    
    all_combos = []
    for strategy, results in data['detailed_results'].items():
        for r in results:
            if r['score'] is not None and r['score'] > 0:
                all_combos.append({
                    'strategy': strategy,
                    'symbol': r['symbol'],
                    'score': r['score'],
                    'profit': r['result']['profit'],
                    'win_rate': r['result']['win_rate'],
                    'max_dd': r['result']['max_dd'],
                })
    
    all_combos.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n  TOP 10:")
    for i, c in enumerate(all_combos[:10], 1):
        dd_status = "✅" if c['max_dd'] <= 0.15 else "⚠️"
        print(f"  {i}. {c['strategy'].upper()}/{c['symbol']}: Score={c['score']:.2f} P=${c['profit']:.2f} WR={c['win_rate']*100:.0f}% DD={c['max_dd']*100:.1f}% {dd_status}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    generate_final_report()
