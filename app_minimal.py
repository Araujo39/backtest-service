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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "DATA_spot"
REPORTS_DIR = BASE_DIR / "reports"
STRATEGIES_DIR = BASE_DIR / "strategies"

# Criar diretórios se não existirem
try:
    REPORTS_DIR.mkdir(exist_ok=True)
    if not STRATEGIES_DIR.exists():
        STRATEGIES_DIR.mkdir(exist_ok=True)
        (STRATEGIES_DIR / "__init__.py").touch()
except Exception as e:
    print(f"Warning: Could not create directories: {e}")

# Models
class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    capital: float = 100.0
    timeframe: str = "15m"

# ==================== BASIC ENDPOINTS ====================

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
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "data_dir_exists": DATA_DIR.exists(),
        "reports_dir_exists": REPORTS_DIR.exists(),
        "strategies_dir_exists": STRATEGIES_DIR.exists()
    }
    
    # Check if ai_optimizer is importable
    try:
        import ai_optimizer
        diagnostics["ai_optimizer_available"] = True
    except Exception as e:
        diagnostics["ai_optimizer_available"] = False
        diagnostics["ai_optimizer_error"] = str(e)
    
    # Check if strategy_validator is importable
    try:
        import strategy_validator
        diagnostics["validator_available"] = True
    except Exception as e:
        diagnostics["validator_available"] = False
        diagnostics["validator_error"] = str(e)
    
    return diagnostics

@app.get("/strategies")
def list_strategies():
    """Lista todas as estratégias disponíveis"""
    try:
        if not STRATEGIES_DIR.exists():
            return {
                "success": False,
                "error": "Strategies directory not found",
                "strategies": [],
                "count": 0
            }
        
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
        return {
            "success": False,
            "error": str(e),
            "strategies": [],
            "count": 0
        }

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
        return {
            "success": False,
            "error": str(e),
            "symbols": [],
            "count": 0
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
