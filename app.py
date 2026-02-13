from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import json
import os
from pathlib import Path
from binance_data_downloader import BinanceDataDownloader

app = FastAPI(title="Backtest Service", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "DATA_spot"  # Usar DATA_spot onde estão os dados reais
REPORTS_DIR = BASE_DIR / "reports"
STRATEGIES_DIR = BASE_DIR / "strategies"

# Criar diretórios se não existirem
REPORTS_DIR.mkdir(exist_ok=True)

# Se strategies dir não existe, criar e adicionar __init__.py
if not STRATEGIES_DIR.exists():
    STRATEGIES_DIR.mkdir(exist_ok=True)
    (STRATEGIES_DIR / "__init__.py").touch()

# Models
class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    capital: float = 100.0
    timeframe: str = "15m"

# ==================== ENDPOINTS ====================

@app.get("/")
def root():
    return {
        "service": "Backtest Service",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    """Health check with diagnostics"""
    import sys
    
    diagnostics = {
        "status": "healthy",
        "python_version": sys.version,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "data_dir_exists": DATA_DIR.exists(),
        "reports_dir_exists": REPORTS_DIR.exists(),
        "strategies_dir_exists": STRATEGIES_DIR.exists()
    }
    
    # Check if ai_optimizer is importable
    try:
        import ai_optimizer
        diagnostics["ai_optimizer_available"] = True
    except ImportError as e:
        diagnostics["ai_optimizer_available"] = False
        diagnostics["ai_optimizer_error"] = str(e)
    
    # Check if strategy_validator is importable
    try:
        import strategy_validator
        diagnostics["validator_available"] = True
    except ImportError as e:
        diagnostics["validator_available"] = False
        diagnostics["validator_error"] = str(e)
    
    return diagnostics

@app.get("/strategies")
def list_strategies():
    """Lista todas as estratégias disponíveis"""
    try:
        strategies = [
            f.stem for f in STRATEGIES_DIR.glob("*.py")
            if f.stem != "__init__"
        ]
        return {
            "success": True,
            "strategies": strategies,
            "count": len(strategies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/symbols")
def list_symbols():
    """Lista todos os símbolos com dados"""
    try:
        if not DATA_DIR.exists():
            return {
                "success": False,
                "error": f"Data directory not found: {DATA_DIR}",
                "symbols": [],
                "count": 0
            }
        
        symbols = []
        for csv_file in DATA_DIR.glob("*.csv"):
            try:
                symbol = csv_file.stem
                size = csv_file.stat().st_size
                
                # Contar linhas (candles)
                with open(csv_file) as f:
                    candles = sum(1 for _ in f) - 1  # -1 para header
                
                symbols.append({
                    "symbol": symbol,
                    "candles": candles,
                    "size": size
                })
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
                continue
        
        return {
            "success": True,
            "symbols": symbols,
            "count": len(symbols)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
def run_backtest(request: BacktestRequest):
    """Executa um backtest individual"""
    try:
        # Validar símbolo
        csv_path = DATA_DIR / f"{request.symbol}.csv"
        if not csv_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found for symbol: {request.symbol}"
            )
        
        # Validar estratégia
        strategy_path = STRATEGIES_DIR / f"{request.strategy}.py"
        if not strategy_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Strategy not found: {request.strategy}"
            )
        
        # Executar backtest
        output_file = f"{request.symbol}_{request.strategy}_{os.urandom(4).hex()}.json"
        output_path = REPORTS_DIR / output_file
        
        command = [
            "python3",
            "backtest_lab.py",
            "--data_dir", "DATA",
            "--symbol", request.symbol,
            "--tf", request.timeframe,
            "--strategy", request.strategy,
            "--capital", str(request.capital),
            "--out", str(output_path)
        ]
        
        # Executar comando
        result = subprocess.run(
            command,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise Exception(f"Backtest failed: {result.stderr}")
        
        # Ler resultado
        with open(output_path) as f:
            data = json.load(f)
        
        return {
            "success": True,
            "data": data,
            "file": output_file
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Backtest timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-all")
def run_all_backtests():
    """Executa todos os backtests (50 combinações)"""
    try:
        # Executar script orchestrator
        result = subprocess.run(
            ["python3", "run_all_backtests.py"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos
        )
        
        if result.returncode != 0:
            raise Exception(f"Batch execution failed: {result.stderr}")
        
        # Gerar relatório consolidado
        subprocess.run(
            ["python3", "generate_report.py"],
            cwd=BASE_DIR,
            check=True
        )
        
        # Ler relatório
        report_path = REPORTS_DIR / "full_report.json"
        with open(report_path) as f:
            data = json.load(f)
        
        return {
            "success": True,
            "data": data
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Batch execution timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports")
def list_reports():
    """Lista todos os relatórios salvos"""
    try:
        reports = []
        
        for json_file in REPORTS_DIR.glob("*.json"):
            stat = json_file.stat()
            
            # Ler preview
            with open(json_file) as f:
                data = json.load(f)
            
            reports.append({
                "filename": json_file.name,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "preview": {
                    "strategy": data.get("strategy", "N/A"),
                    "profit": data.get("profit", 0),
                    "win_rate": data.get("win_rate", 0),
                    "max_dd": data.get("max_dd", 0)
                }
            })
        
        # Ordenar por data de modificação
        reports.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "success": True,
            "reports": reports,
            "count": len(reports)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{filename}")
def get_report(filename: str):
    """Obtém um relatório específico"""
    try:
        report_path = REPORTS_DIR / filename
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        with open(report_path) as f:
            data = json.load(f)
        
        return {
            "success": True,
            "data": data,
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI OPTIMIZATION ENDPOINTS
# ============================================================================

@app.post("/optimize")
def optimize_strategy_endpoint(request: dict):
    """
    AI Optimization endpoint using OpenAI GPT-4.
    
    Payload:
    {
        "strategy_name": "sniper",
        "current_code": "def run_strategy...",
        "performance_metrics": {
            "avg_win_rate": 0.31,
            "avg_profit": -4.24,
            "avg_drawdown": 0.0637,
            "avg_trades": 54,
            "avg_score": 65.3
        },
        "problems": [
            {
                "type": "low_win_rate",
                "description": "...",
                "current_value": 0.31,
                "target_value": 0.80,
                "suggestions": ["...", "..."]
            }
        ],
        "openai_api_key": "sk-..."
    }
    
    Returns:
    {
        "success": true,
        "optimized_code": "def run_strategy...",
        "parameters": {...},
        "ai_response": "...",
        "tokens_used": 3500,
        "cost_usd": 0.0945
    }
    """
    try:
        # Import lazy para evitar travamento no startup
        try:
            from ai_optimizer import optimize_strategy
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"AI Optimizer module not available: {str(e)}"
            )
        
        strategy_name = request.get("strategy_name")
        current_code = request.get("current_code")
        performance_metrics = request.get("performance_metrics")
        problems = request.get("problems", [])
        
        # Pegar API key da variável de ambiente OU do request
        openai_api_key = os.getenv("OPENAI_API_KEY") or request.get("openai_api_key")
        
        if not all([strategy_name, current_code, performance_metrics]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: strategy_name, current_code, performance_metrics"
            )
        
        if not openai_api_key:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key not found. Set OPENAI_API_KEY environment variable or pass in request."
            )
        
        result = optimize_strategy(
            strategy_name=strategy_name,
            current_code=current_code,
            performance_metrics=performance_metrics,
            problems=problems,
            openai_api_key=openai_api_key
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization error: {str(e)}")


@app.post("/validate")
def validate_strategy_endpoint(request: dict):
    """
    Validate a new strategy version against the old one.
    
    Payload:
    {
        "strategy_name": "sniper",
        "old_code": "def run_strategy...",
        "new_code": "def run_strategy...",
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        "timeframe": "15m",
        "initial_capital": 100,
        "data_dir": "DATA_spot"
    }
    
    Returns:
    {
        "approved": true/false,
        "old_metrics": {...},
        "new_metrics": {...},
        "comparison": {...},
        "approval_criteria": {...},
        "improvement_pct": 15.5,
        "tests_run": 10,
        "symbols_tested": ["..."]
    }
    """
    try:
        # Import lazy para evitar travamento no startup
        try:
            from strategy_validator import validate_new_version
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Validator module not available: {str(e)}"
            )
        
        strategy_name = request.get("strategy_name")
        old_code = request.get("old_code")
        new_code = request.get("new_code")
        symbols = request.get("symbols", [])
        timeframe = request.get("timeframe", "15m")
        initial_capital = request.get("initial_capital", 100.0)
        data_dir = request.get("data_dir", "DATA_spot")
        
        if not all([strategy_name, old_code, new_code, symbols]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: strategy_name, old_code, new_code, symbols"
            )
        
        result = validate_new_version(
            strategy_name=strategy_name,
            old_code=old_code,
            new_code=new_code,
            symbols=symbols,
            timeframe=timeframe,
            initial_capital=initial_capital,
            data_dir=data_dir
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@app.post("/deploy-strategy")
def deploy_strategy_endpoint(request: dict):
    """
    Deploy a new strategy version by updating the Python file.
    
    Payload:
    {
        "strategy_name": "sniper",
        "code": "def run_strategy..."
    }
    
    Returns:
    {
        "success": true,
        "strategy": "sniper",
        "file_path": "strategies/sniper.py"
    }
    """
    try:
        strategy_name = request.get("strategy_name")
        code = request.get("code")
        
        if not all([strategy_name, code]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: strategy_name, code"
            )
        
        strategy_file = STRATEGIES_DIR / f"{strategy_name}.py"
        
        # Write new code
        with open(strategy_file, 'w') as f:
            f.write(code)
        
        return {
            "success": True,
            "strategy": strategy_name,
            "file_path": str(strategy_file)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BINANCE DATA ENDPOINTS
# ============================================================================

@app.post("/binance/download-symbol")
def download_binance_symbol(request: dict):
    """
    Download real OHLCV data from Binance Public Data for a single symbol.
    
    Payload:
    {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "max_candles": 2000,
        "market_type": "spot"
    }
    """
    symbol = request.get("symbol")
    interval = request.get("interval", "15m")
    max_candles = request.get("max_candles", 2000)
    market_type = request.get("market_type", "spot")
    
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    
    try:
        downloader = BinanceDataDownloader(market_type=market_type)
        
        success = downloader.save_symbol_data(
            symbol=symbol,
            interval=interval,
            max_candles=max_candles
        )
        
        if success:
            # Check file
            csv_file = downloader.base_path / f"{symbol}.csv"
            file_size = csv_file.stat().st_size if csv_file.exists() else 0
            
            # Count candles
            with open(csv_file) as f:
                candles = sum(1 for _ in f) - 1
            
            return {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "candles": candles,
                "file_size": file_size,
                "file_path": str(csv_file)
            }
        else:
            return {
                "success": False,
                "error": "Failed to download data"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/binance/download-multiple")
def download_binance_multiple(request: dict):
    """
    Download real OHLCV data from Binance for multiple symbols.
    
    Payload:
    {
        "symbols": ["BTCUSDT", "ETHUSDT", ...],
        "interval": "15m",
        "max_candles": 2000,
        "market_type": "spot"
    }
    """
    symbols = request.get("symbols", [])
    interval = request.get("interval", "15m")
    max_candles = request.get("max_candles", 2000)
    market_type = request.get("market_type", "spot")
    
    if not symbols:
        raise HTTPException(status_code=400, detail="Symbols list is required")
    
    try:
        downloader = BinanceDataDownloader(market_type=market_type)
        
        results = downloader.download_multiple_symbols(
            symbols=symbols,
            interval=interval,
            max_candles=max_candles
        )
        
        return {
            "success": True,
            "total_symbols": len(symbols),
            "successful": len(results['success']),
            "failed": len(results['failed']),
            "success_list": results['success'],
            "failed_list": results['failed']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/binance/available-intervals")
def get_available_intervals():
    """Lista os intervalos disponíveis na Binance"""
    return {
        "intervals": [
            "1m", "3m", "5m", "15m", "30m",
            "1h", "2h", "4h", "6h", "8h", "12h",
            "1d", "3d", "1w", "1mo"
        ],
        "recommended": {
            "scalping": ["1m", "3m", "5m"],
            "day_trading": ["15m", "30m", "1h"],
            "swing_trading": ["4h", "1d"],
            "position_trading": ["1d", "1w"]
        }
    }


@app.get("/data-source")
def get_data_source():
    """Retorna informações sobre a fonte dos dados"""
    data_spot_exists = (DATA_DIR / "BTCUSDT.csv").exists()
    data_binance_exists = Path("DATA_spot").exists()
    
    binance_candles = 0
    if data_binance_exists:
        try:
            with open("DATA_spot/BTCUSDT.csv") as f:
                binance_candles = sum(1 for _ in f) - 1
        except:
            pass
    
    return {
        "current_data": "synthetic" if data_spot_exists and not data_binance_exists else "binance",
        "synthetic_data_available": data_spot_exists,
        "binance_data_available": data_binance_exists,
        "binance_candles": binance_candles,
        "data_directory": str(DATA_DIR),
        "binance_directory": "DATA_spot",
        "binance_vision_url": "https://data.binance.vision/",
        "recommendation": "Use /binance/download-multiple to get real Binance data"
    }
