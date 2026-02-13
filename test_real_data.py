#!/usr/bin/env python3
"""
Test backtest with real Binance data
"""
import sys
import subprocess

# Test with real Binance data
result = subprocess.run([
    'python', 'backtest_lab.py',
    '--data_dir', 'DATA_spot',
    '--symbol', 'BTCUSDT',
    '--strategy', 'sniper',
    '--capital', '100',
    '--tf', '15m'
], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print(f"\nExit code: {result.returncode}")
