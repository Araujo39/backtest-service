#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import pandas as pd
import importlib

def main():
    p = argparse.ArgumentParser(description="Backtest Lab - Multi Strategy")
    p.add_argument('--data_dir', required=True)
    p.add_argument('--symbol', required=True)
    p.add_argument('--tf', default='15m')
    p.add_argument('--strategy', required=True)
    p.add_argument('--capital', type=float, default=100.0)
    p.add_argument('--out', default='reports/report.json')
    args = p.parse_args()

    df = pd.read_csv(f"{args.data_dir}/{args.symbol}.csv")

    mod = importlib.import_module(f"strategies.{args.strategy}")
    run_strategy = getattr(mod, "run_strategy")

    result = run_strategy(df, capital=args.capital)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print("OK. Relatório salvo em:", args.out)

if __name__ == "__main__":
    main()
