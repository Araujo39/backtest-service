from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import importlib, importlib.util, json, math, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

from backtest_lab import (
    load_dataframe_from_candles,
    load_dataframe_from_csv,
    run_backtest_from_df,
    calculate_backtest_metrics,
    DEFAULT_COMMISSION_PCT,
    DEFAULT_SLIPPAGE_PCT,
)

app = FastAPI(title='Backtest Service v2', version='2.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

BASE_DIR       = Path(__file__).parent
DATA_DIR       = BASE_DIR / 'DATA_spot'
REPORTS_DIR    = BASE_DIR / 'reports'
STRATEGIES_DIR = BASE_DIR / 'strategies'

REPORTS_DIR.mkdir(exist_ok=True)
if not STRATEGIES_DIR.exists():
    STRATEGIES_DIR.mkdir(exist_ok=True)
    (STRATEGIES_DIR / '__init__.py').touch()

# ─── Models ───────────────────────────────────────────────────────────────────

class BacktestConfig(BaseModel):
    commission_pct: float = DEFAULT_COMMISSION_PCT
    slippage_pct:   float = DEFAULT_SLIPPAGE_PCT

class BacktestRequest(BaseModel):
    symbol:     str
    strategy:   str
    capital:    float = 1000.0
    timeframe:  str   = '15m'
    ohlcv:      Optional[List[Dict[str, Any]]] = None   # inline candles from D1
    config:     Optional[BacktestConfig]        = None

class WalkForwardRequest(BaseModel):
    symbol:    str
    strategy:  str
    capital:   float = 1000.0
    timeframe: str   = '15m'
    windows:   int   = 5
    train_pct: float = 70.0
    ohlcv:     Optional[List[Dict[str, Any]]] = None
    config:    Optional[BacktestConfig]        = None

class GridSearchRequest(BaseModel):
    symbol:       str
    strategy:     str
    capital:      float = 1000.0
    timeframe:    str   = '15m'
    param_grid:   Dict[str, List[Any]] = {}
    optimize_for: str   = 'sharpe_ratio'   # roi_pct | win_rate_pct | profit_factor | calmar_ratio
    ohlcv:        Optional[List[Dict[str, Any]]] = None
    config:       Optional[BacktestConfig]        = None

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_df(request_ohlcv, symbol: str) -> pd.DataFrame:
    """Load DataFrame: prefer inline ohlcv, fall back to CSV."""
    if request_ohlcv:
        return load_dataframe_from_candles(request_ohlcv)
    csv_path = DATA_DIR / f'{symbol}.csv'
    if not csv_path.exists():
        raise HTTPException(404, f'Data not found for symbol: {symbol}')
    return load_dataframe_from_csv(str(DATA_DIR), symbol)


def _load_strategy(name: str):
    strategy_path = STRATEGIES_DIR / f'{name}.py'
    if not strategy_path.exists():
        raise HTTPException(404, f'Strategy not found: {name}')
    spec = importlib.util.spec_from_file_location(f'strategy_{abs(hash(name))}', strategy_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg(config: Optional[BacktestConfig]) -> dict:
    if config:
        return {'commission_pct': config.commission_pct, 'slippage_pct': config.slippage_pct}
    return {}


# ─── Core endpoints ───────────────────────────────────────────────────────────

@app.get('/')
def root():
    return {'service': 'Backtest Service', 'version': '2.0.0', 'status': 'running'}


@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'python': sys.version,
        'data_dir': str(DATA_DIR),
        'data_dir_exists': DATA_DIR.exists(),
        'strategies': [f.stem for f in STRATEGIES_DIR.glob('*.py') if f.stem != '__init__'],
    }


@app.get('/strategies')
def list_strategies():
    strategies = [f.stem for f in STRATEGIES_DIR.glob('*.py') if f.stem != '__init__']
    return {'success': True, 'strategies': strategies, 'count': len(strategies)}


@app.get('/symbols')
def list_symbols():
    if not DATA_DIR.exists():
        return {'success': False, 'symbols': [], 'count': 0}
    symbols = []
    for csv_file in DATA_DIR.glob('*.csv'):
        try:
            with open(csv_file) as f:
                candles = sum(1 for _ in f) - 1
            symbols.append({'symbol': csv_file.stem, 'candles': candles})
        except Exception:
            pass
    return {'success': True, 'symbols': symbols, 'count': len(symbols)}


# ─── POST /run ────────────────────────────────────────────────────────────────

@app.post('/run')
def run_backtest(req: BacktestRequest):
    """
    Single backtest. Accepts optional inline `ohlcv` from Cloudflare D1.
    If omitted, reads from DATA_spot/{symbol}.csv (backward compat).
    Returns canonical metric schema (all scales fixed).
    """
    try:
        df  = _load_df(req.ohlcv, req.symbol)
        mod = _load_strategy(req.strategy)
        cfg = _cfg(req.config)

        metrics = run_backtest_from_df(df, mod, req.capital, req.symbol, req.strategy, req.timeframe, cfg)
        return {'success': True, 'data': metrics}

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(408, 'Backtest timeout')
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── POST /walk-forward ───────────────────────────────────────────────────────

@app.post('/walk-forward')
def walk_forward(req: WalkForwardRequest):
    """
    Walk-forward test: divide the data into `windows` rolling segments.
    Each segment's last (100-train_pct)% is the out-of-sample test period.
    Returns per-window metrics + stability_score + overfitting_risk.
    """
    try:
        df  = _load_df(req.ohlcv, req.symbol)
        mod = _load_strategy(req.strategy)
        cfg = _cfg(req.config)

        n = len(df)
        w = req.windows
        seg = n // w
        if seg < 50:
            raise HTTPException(400, f'Not enough candles ({n}) for {w} windows — need at least {w*50}')

        window_results = []
        for i in range(w):
            start = i * seg
            end   = start + seg if i < w - 1 else n
            chunk = df.iloc[start:end].reset_index(drop=True)

            # Split into train/test
            split = int(len(chunk) * req.train_pct / 100)
            test_df = chunk.iloc[split:].reset_index(drop=True)

            try:
                result = run_backtest_from_df(
                    test_df, mod, req.capital, req.symbol, req.strategy, req.timeframe, cfg
                )
                window_results.append({
                    'window':        i + 1,
                    'candles_total': len(chunk),
                    'candles_test':  len(test_df),
                    'roi_pct':       result.get('roi_pct', 0),
                    'win_rate_pct':  result.get('win_rate_pct', 0),
                    'total_trades':  result.get('total_trades', 0),
                    'max_dd_pct':    result.get('max_drawdown_pct', 0),
                    'sharpe':        result.get('sharpe_ratio', 0),
                    'sortino':       result.get('sortino_ratio', 0),
                })
            except Exception as e:
                window_results.append({'window': i + 1, 'error': str(e)})

        # Stability score based on std of win_rate across windows that had trades
        valid = [r for r in window_results if 'win_rate_pct' in r and r.get('total_trades', 0) > 0]
        if valid:
            win_rates = [r['win_rate_pct'] for r in valid]
            std_wr    = float(np.std(win_rates))
            stability = max(0.0, round(100 - std_wr * 3, 1))
        else:
            std_wr, stability = 0.0, 0.0

        if std_wr > 15:
            overfitting_risk = 'HIGH'
        elif std_wr > 8:
            overfitting_risk = 'MEDIUM'
        else:
            overfitting_risk = 'LOW'

        return {
            'success':          True,
            'symbol':           req.symbol,
            'strategy':         req.strategy,
            'timeframe':        req.timeframe,
            'windows':          window_results,
            'stability_score':  stability,
            'overfitting_risk': overfitting_risk,
            'win_rate_std':     round(std_wr, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── POST /grid-search ────────────────────────────────────────────────────────

@app.post('/grid-search')
def grid_search(req: GridSearchRequest):
    """
    Parameter grid search. Runs strategy with each param combination.
    Strategy's run_strategy() must accept **params.
    Returns ranked results + best combination.
    """
    try:
        df  = _load_df(req.ohlcv, req.symbol)
        cfg = _cfg(req.config)

        # Build combinations
        import itertools
        keys   = list(req.param_grid.keys())
        values = list(req.param_grid.values())
        combos = list(itertools.product(*values)) if keys else [()]
        if len(combos) > 50:
            raise HTTPException(400, f'Too many combinations ({len(combos)}), max 50')

        mod = _load_strategy(req.strategy)

        results = []
        for combo in combos:
            params = dict(zip(keys, combo)) if keys else {}
            try:
                result_df = mod.run_strategy(df.copy(), capital=req.capital, **params)
                metrics = calculate_backtest_metrics(
                    result_df, req.capital, req.symbol, req.strategy, req.timeframe, cfg
                )
                results.append({
                    'params':  params,
                    'metrics': {
                        k: metrics.get(k)
                        for k in ('roi_pct', 'win_rate_pct', 'max_drawdown_pct',
                                  'profit_factor', 'sharpe_ratio', 'sortino_ratio',
                                  'calmar_ratio', 'total_trades', 'total_fees_paid')
                    }
                })
            except Exception as e:
                results.append({'params': params, 'error': str(e)})

        # Sort by optimize_for
        scored = [r for r in results if 'metrics' in r]
        scored.sort(key=lambda r: r['metrics'].get(req.optimize_for, 0), reverse=True)

        return {
            'success':      True,
            'symbol':       req.symbol,
            'strategy':     req.strategy,
            'optimize_for': req.optimize_for,
            'total_runs':   len(combos),
            'results':      scored,
            'best':         scored[0] if scored else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── POST /deploy-strategy ────────────────────────────────────────────────────

from fastapi import Body

@app.post('/deploy-strategy')
def deploy_strategy(body: dict = Body(...)):
    """Deploy a strategy Python file to the strategies/ directory."""
    name           = body.get('name', '').lower().replace(' ', '_')
    script_content = body.get('script_content', '')

    if not name or not script_content:
        raise HTTPException(400, 'name and script_content required')
    if 'def run_strategy(' not in script_content:
        raise HTTPException(400, 'Script must contain def run_strategy(df, capital, **params)')

    strategy_file = STRATEGIES_DIR / f'{name}.py'
    strategy_file.write_text(script_content, encoding='utf-8')

    # Invalidate module cache so next import picks up new file
    full_module = f'strategies.{name}'
    if full_module in sys.modules:
        del sys.modules[full_module]

    return {'success': True, 'name': name, 'path': str(strategy_file)}


# ─── Legacy batch endpoints (kept for backward compat) ────────────────────────

@app.post('/run-all')
def run_all_backtests():
    try:
        result = subprocess.run(
            ['python3', 'run_all_backtests_fast.py'],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise Exception(result.stderr)
        report_path = REPORTS_DIR / 'full_report.json'
        data = json.loads(report_path.read_text()) if report_path.exists() else {}
        return {'success': True, 'data': data}
    except subprocess.TimeoutExpired:
        raise HTTPException(408, 'Batch timeout')
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post('/run-all-progressive')
def run_all_progressive():
    import threading
    def _run():
        subprocess.run(['python3', 'run_all_progressive.py'], cwd=BASE_DIR,
                       capture_output=True, text=True)
    threading.Thread(target=_run, daemon=True).start()
    return {'success': True, 'status': 'running', 'progress_endpoint': '/batch-progress'}


@app.get('/batch-progress')
def batch_progress():
    p = REPORTS_DIR / 'batch_progress.json'
    if not p.exists():
        return {'success': True, 'status': 'idle'}
    return {'success': True, **json.loads(p.read_text())}


@app.get('/reports')
def list_reports():
    files = [{'filename': f.name, 'size': f.stat().st_size}
             for f in sorted(REPORTS_DIR.glob('*.json'))
             if f.name not in ('full_report.json', 'batch_progress.json')]
    return {'success': True, 'reports': files}


@app.get('/reports/{filename}')
def get_report(filename: str):
    p = REPORTS_DIR / filename
    if not p.exists():
        raise HTTPException(404, 'Report not found')
    return json.loads(p.read_text())


@app.post('/validate-strategy')
def validate_strategy(body: dict = Body(...)):
    code = body.get('script_content', '')
    if 'def run_strategy(' not in code:
        return {'valid': False, 'error': 'Missing def run_strategy(df, capital, **params)'}
    try:
        compile(code, '<strategy>', 'exec')
        return {'valid': True}
    except SyntaxError as e:
        return {'valid': False, 'error': str(e)}
