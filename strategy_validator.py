#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Validator - Tests optimized strategies and compares with original
"""

import subprocess
import tempfile
import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any

# ===========================================================================
# VALIDATOR
# ===========================================================================

def validate_new_version(
    strategy_name: str,
    old_code: str,
    new_code: str,
    symbols: List[str],
    timeframe: str = '15m',
    initial_capital: float = 100.0,
    data_dir: str = 'DATA_spot'
) -> Dict[str, Any]:
    """
    Validate a new strategy version by comparing with the old one.
    Executes backtests on ALL available symbols.
    
    Args:
        strategy_name: Strategy name (e.g., 'sniper')
        old_code: Python code of old version
        new_code: Python code of new version
        symbols: List of symbols to test
        timeframe: Timeframe (e.g., '15m')
        initial_capital: Initial capital for backtests
        data_dir: Directory with CSV data
    
    Returns:
        Dict with validation results and approval decision
    """
    
    print(f"\n{'='*70}")
    print(f"🧪 VALIDATOR - Testing {strategy_name.upper()}")
    print(f"{'='*70}")
    print(f"Symbols: {len(symbols)}")
    print(f"Timeframe: {timeframe}")
    print(f"Capital: ${initial_capital}")
    print(f"{'='*70}\n")
    
    # Create temporary strategy files
    strategies_dir = Path('strategies')
    backup_file = strategies_dir / f"{strategy_name}_backup.py"
    original_file = strategies_dir / f"{strategy_name}.py"
    
    # Backup original
    if original_file.exists():
        shutil.copy(original_file, backup_file)
        print(f"✅ Original backed up: {backup_file}")
    
    try:
        # Test OLD version
        print(f"\n📊 Testing OLD version...")
        print("-" * 70)
        
        # Write old code
        with open(original_file, 'w') as f:
            f.write(old_code)
        
        old_results = []
        for symbol in symbols:
            result = run_single_backtest(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                initial_capital=initial_capital,
                data_dir=data_dir
            )
            if result:
                old_results.append(result)
                print(f"  ✅ {symbol}: Score {result['score']:.1f}, WR {result['win_rate']:.1f}%")
        
        # Test NEW version
        print(f"\n📊 Testing NEW version...")
        print("-" * 70)
        
        # Write new code
        with open(original_file, 'w') as f:
            f.write(new_code)
        
        new_results = []
        for symbol in symbols:
            result = run_single_backtest(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                initial_capital=initial_capital,
                data_dir=data_dir
            )
            if result:
                new_results.append(result)
                print(f"  ✅ {symbol}: Score {result['score']:.1f}, WR {result['win_rate']:.1f}%")
        
        # Calculate averages
        old_avg = calculate_averages(old_results)
        new_avg = calculate_averages(new_results)
        
        print(f"\n{'='*70}")
        print(f"📊 COMPARISON RESULTS")
        print(f"{'='*70}")
        print(f"\nOLD VERSION:")
        print(f"  Win Rate: {old_avg['win_rate']:.1f}%")
        print(f"  Profit: {old_avg['profit']:.2f}%")
        print(f"  Drawdown: {old_avg['max_drawdown']:.2f}%")
        print(f"  Trades: {old_avg['total_trades']:.0f}")
        print(f"  Score: {old_avg['score']:.1f}")
        
        print(f"\nNEW VERSION:")
        print(f"  Win Rate: {new_avg['win_rate']:.1f}% ({format_diff(new_avg['win_rate'] - old_avg['win_rate'])})")
        print(f"  Profit: {new_avg['profit']:.2f}% ({format_diff(new_avg['profit'] - old_avg['profit'])})")
        print(f"  Drawdown: {new_avg['max_drawdown']:.2f}% ({format_diff(old_avg['max_drawdown'] - new_avg['max_drawdown'])})")
        print(f"  Trades: {new_avg['total_trades']:.0f} ({format_diff(new_avg['total_trades'] - old_avg['total_trades'], is_count=True)})")
        print(f"  Score: {new_avg['score']:.1f} ({format_diff(new_avg['score'] - old_avg['score'])})")
        
        # Comparison metrics
        comparison = {
            'win_rate': {
                'old': old_avg['win_rate'],
                'new': new_avg['win_rate'],
                'improved': new_avg['win_rate'] > old_avg['win_rate'],
                'diff': new_avg['win_rate'] - old_avg['win_rate']
            },
            'profit': {
                'old': old_avg['profit'],
                'new': new_avg['profit'],
                'improved': new_avg['profit'] > old_avg['profit'],
                'diff': new_avg['profit'] - old_avg['profit']
            },
            'drawdown': {
                'old': old_avg['max_drawdown'],
                'new': new_avg['max_drawdown'],
                'improved': new_avg['max_drawdown'] < old_avg['max_drawdown'],
                'diff': old_avg['max_drawdown'] - new_avg['max_drawdown']  # Lower is better
            },
            'score': {
                'old': old_avg['score'],
                'new': new_avg['score'],
                'improved': new_avg['score'] > old_avg['score'],
                'diff': new_avg['score'] - old_avg['score']
            }
        }
        
        # Approval criteria
        approval_criteria = {
            'win_rate_threshold': new_avg['win_rate'] >= 80.0,
            'min_improvement': new_avg['score'] > old_avg['score'] * 1.05,  # +5% improvement
            'drawdown_limit': new_avg['max_drawdown'] <= 15.0,
            'positive_profit': new_avg['profit'] > 0,
            'sufficient_trades': new_avg['total_trades'] >= 30
        }
        
        # Decide approval
        approved = all(approval_criteria.values())
        
        # Calculate improvement percentage
        improvement_pct = ((new_avg['score'] - old_avg['score']) / old_avg['score']) * 100 if old_avg['score'] > 0 else 0
        
        print(f"\n{'='*70}")
        print(f"🎯 APPROVAL CRITERIA")
        print(f"{'='*70}")
        for criterion, passed in approval_criteria.items():
            icon = "✅" if passed else "❌"
            print(f"  {icon} {criterion}: {passed}")
        
        print(f"\n{'='*70}")
        if approved:
            print(f"✅ APPROVED - New version is better!")
            print(f"   Improvement: {improvement_pct:+.1f}%")
        else:
            print(f"❌ REJECTED - New version doesn't meet criteria")
            print(f"   Improvement: {improvement_pct:+.1f}%")
        print(f"{'='*70}\n")
        
        return {
            'approved': approved,
            'old_metrics': old_avg,
            'new_metrics': new_avg,
            'comparison': comparison,
            'approval_criteria': approval_criteria,
            'improvement_pct': round(improvement_pct, 2),
            'tests_run': len(new_results),
            'symbols_tested': symbols
        }
        
    finally:
        # Restore original file
        if backup_file.exists():
            shutil.copy(backup_file, original_file)
            backup_file.unlink()
            print(f"✅ Original restored from backup")

# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def run_single_backtest(
    strategy_name: str,
    symbol: str,
    timeframe: str,
    initial_capital: float,
    data_dir: str
) -> Dict[str, Any]:
    """
    Run a single backtest using backtest_lab.py
    """
    try:
        cmd = [
            'python', 'backtest_lab.py',
            '--data_dir', data_dir,
            '--symbol', symbol,
            '--strategy', strategy_name,
            '--capital', str(initial_capital),
            '--tf', timeframe,
            '--out', '/dev/null'  # Discard report file
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        # Parse output (backtest_lab.py prints JSON to stdout)
        # We need to extract the JSON from output
        output = result.stdout.strip()
        
        # Try to find JSON in output
        try:
            # If output contains multiple lines, get the last line with JSON
            for line in reversed(output.split('\n')):
                if line.strip().startswith('{'):
                    data = json.loads(line.strip())
                    break
            else:
                # Fallback: parse entire output
                data = json.loads(output)
        except:
            # If JSON parsing fails, return None
            return None
        
        # Calculate score
        score = calculate_score(data)
        data['score'] = score
        
        return data
        
    except Exception as e:
        print(f"    ⚠️  {symbol}: Error - {e}")
        return None

def calculate_averages(results: List[Dict]) -> Dict[str, float]:
    """Calculate average metrics from multiple backtest results"""
    if not results:
        return {
            'win_rate': 0,
            'profit': 0,
            'max_drawdown': 0,
            'total_trades': 0,
            'score': 0
        }
    
    n = len(results)
    return {
        'win_rate': sum(r['win_rate'] for r in results) / n,
        'profit': sum(r['profit'] for r in results) / n,
        'max_drawdown': sum(r['max_dd'] for r in results) / n,
        'total_trades': sum(r['n_trades'] for r in results) / n,
        'score': sum(r['score'] for r in results) / n
    }

def calculate_score(data: Dict) -> float:
    """
    Calculate performance score (0-100)
    Same formula as used in scheduler
    """
    win_rate_score = (data['win_rate'] / 100) * 40
    profit_score = min(max(data['profit'], 0), 100) * 0.3
    drawdown_score = (1 - (data['max_dd'] / 100)) * 20
    trades_score = min(data['n_trades'] / 30, 1) * 10
    
    return round(win_rate_score + profit_score + drawdown_score + trades_score, 1)

def format_diff(value: float, is_count: bool = False) -> str:
    """Format difference with + or - sign and color"""
    if is_count:
        return f"{value:+.0f}"
    return f"{value:+.2f}"

# ===========================================================================
# MAIN (for testing)
# ===========================================================================

if __name__ == "__main__":
    print("Strategy Validator - Test Mode")
    print("=" * 70)
    
    # Example: Test with dummy codes
    old_code = """
def run_strategy(df, capital, **params):
    return {
        'capital_start': 100,
        'capital_end': 95,
        'profit': -5,
        'win_rate': 30,
        'max_dd': 10,
        'n_trades': 50
    }
"""
    
    new_code = """
def run_strategy(df, capital, **params):
    return {
        'capital_start': 100,
        'capital_end': 110,
        'profit': 10,
        'win_rate': 85,
        'max_dd': 8,
        'n_trades': 45
    }
"""
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    result = validate_new_version(
        strategy_name='test',
        old_code=old_code,
        new_code=new_code,
        symbols=symbols
    )
    
    print(f"\n✅ Validation completed!")
    print(f"   Approved: {result['approved']}")
    print(f"   Improvement: {result['improvement_pct']:.1f}%")
