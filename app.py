from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import json
import os
from pathlib import Path

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
DATA_DIR = BASE_DIR / "DATA"
REPORTS_DIR = BASE_DIR / "reports"
STRATEGIES_DIR = BASE_DIR / "strategies"

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
    return {"status": "healthy"}

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
        symbols = []
        for csv_file in DATA_DIR.glob("*.csv"):
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
