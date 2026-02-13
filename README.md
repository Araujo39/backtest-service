# Backtest Service - Railway

Serviço Python para execução de backtests de estratégias de trading.

## 🚀 Deploy no Railway

### Método 1: Via GitHub (RECOMENDADO)

1. Criar repositório no GitHub
2. Push dos arquivos
3. Conectar ao Railway
4. Deploy automático

### Método 2: Via Railway CLI

```bash
railway login
railway init
railway up
```

## 📦 Estrutura

```
.
├── Dockerfile              # Configuração do container
├── requirements.txt        # Dependências Python
├── app.py                 # FastAPI application
├── backtest_lab.py        # Engine de backtest
├── run_all_backtests.py   # Orchestrador batch
├── generate_report.py     # Gerador de relatórios
├── strategies/            # 5 estratégias
├── DATA/                  # 10 símbolos CSV
└── reports/               # Relatórios JSON (gerados)
```

## 🔌 Endpoints

- `GET /` - Info do serviço
- `GET /health` - Health check
- `GET /strategies` - Lista estratégias
- `GET /symbols` - Lista símbolos
- `POST /run` - Executa backtest individual
- `POST /run-all` - Executa todos os backtests
- `GET /reports` - Lista relatórios
- `GET /reports/{filename}` - Obtém relatório específico

## 🧪 Testar Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
uvicorn app:app --host 0.0.0.0 --port 8080

# Testar
curl http://localhost:8080/health
curl http://localhost:8080/strategies
```

## 🌐 Após Deploy

A URL do serviço será algo como:
```
https://backtest-service-production.up.railway.app
```

Configure essa URL no Cloudflare Pages como variável `RAILWAY_BACKTEST_URL`.
