# 🚂 GUIA PASSO A PASSO: Deploy no Railway

**Tempo estimado**: 10-15 minutos  
**Dificuldade**: Fácil ⭐⭐☆☆☆

---

## 📦 PREPARAÇÃO (JÁ FEITA!)

✅ Já criei todos os arquivos necessários em `/home/user/webapp/railway-setup/`:

```
railway-setup/
├── Dockerfile              ✅ Container Python 3.12
├── requirements.txt        ✅ Dependências (pandas, fastapi, etc)
├── app.py                 ✅ FastAPI com 6 endpoints
├── backtest_lab.py        ✅ Engine de backtest
├── run_all_backtests.py   ✅ Orchestrador
├── generate_report.py     ✅ Gerador de relatórios
├── strategies/            ✅ 5 estratégias (fast, sniper, spot, swing, hybrid)
├── DATA/                  ✅ 10 símbolos CSV
├── reports/               ✅ Pasta para relatórios
├── README.md              ✅ Documentação
└── .gitignore             ✅ Arquivos a ignorar
```

---

## 🎯 OPÇÃO 1: Deploy via GitHub (RECOMENDADO)

Esta é a forma **MAIS FÁCIL** e **MAIS RÁPIDA**!

### Passo 1: Criar Repositório no GitHub

1. **Acesse**: https://github.com/new
2. **Nome do repositório**: `backtest-service`
3. **Descrição**: `Python service for backtesting trading strategies`
4. **Visibilidade**: Pode ser **Private** (recomendado) ou Public
5. **NÃO marque**: "Add README", "Add .gitignore", "Choose license"
6. Clique em **"Create repository"**

### Passo 2: Baixar os Arquivos

**Vou criar um arquivo ZIP para você baixar:**

```bash
# O arquivo já está em: /home/user/webapp/railway-setup/backtest-service.tar.gz
```

**Como baixar**:
1. No GenSpark, clique em "Files" no menu lateral
2. Navegue até `/home/user/webapp/railway-setup/`
3. Clique com botão direito em `backtest-service.tar.gz`
4. Selecione "Download"

### Passo 3: Fazer Upload para o GitHub

**Opção A: Via interface web do GitHub** (mais fácil)

1. No repositório recém-criado, clique em **"uploading an existing file"**
2. **Descompacte** o arquivo `backtest-service.tar.gz` no seu computador
3. **Arraste todos os arquivos** para a área de upload
4. Na mensagem de commit, escreva: `Initial commit - Backtest service`
5. Clique em **"Commit changes"**

**Opção B: Via linha de comando** (se preferir)

```bash
# No seu computador, descompacte o arquivo
tar -xzf backtest-service.tar.gz
cd backtest-service

# Inicializar git
git init
git add .
git commit -m "Initial commit - Backtest service"

# Adicionar remote (substitua SEU_USUARIO)
git remote add origin https://github.com/SEU_USUARIO/backtest-service.git

# Push
git branch -M main
git push -u origin main
```

### Passo 4: Conectar ao Railway

1. **Acesse Railway**: https://railway.app
2. Clique em **"Start a New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. **Autorize o Railway** a acessar seus repositórios (se necessário)
5. Selecione o repositório **`backtest-service`**
6. Clique em **"Deploy Now"**

### Passo 5: Aguardar Deploy (2-5 minutos)

O Railway vai:
- ✅ Detectar o `Dockerfile`
- ✅ Build da imagem Docker
- ✅ Instalar dependências
- ✅ Iniciar o serviço

Você verá logs no console do Railway:
```
Building...
[+] Building 45.2s
Successfully built abc123def456
Deploying...
✓ Service is live!
```

### Passo 6: Obter a URL do Serviço

1. No Railway, clique na aba **"Settings"**
2. Role até **"Networking"**
3. Clique em **"Generate Domain"**
4. Copie a URL gerada (algo como):
   ```
   https://backtest-service-production-abc123.up.railway.app
   ```

### Passo 7: Testar o Serviço

**Abra uma nova aba do navegador** e acesse:

```
https://SUA-URL-RAILWAY.up.railway.app/health
```

Você deve ver:
```json
{"status": "healthy"}
```

**Teste os endpoints**:

```
https://SUA-URL-RAILWAY.up.railway.app/strategies
https://SUA-URL-RAILWAY.up.railway.app/symbols
```

---

## 🎯 OPÇÃO 2: Deploy via Railway CLI (Alternativa)

Se você preferir usar a linha de comando:

### Passo 1: Instalar Railway CLI

```bash
# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh

# Windows
iwr https://railway.app/install.ps1 | iex
```

### Passo 2: Login no Railway

```bash
railway login
```

Isso abrirá o navegador para você autorizar.

### Passo 3: Fazer Deploy

```bash
cd /home/user/webapp/railway-setup
railway init
railway up
```

### Passo 4: Obter URL

```bash
railway domain
```

---

## 🔧 CONFIGURAR CLOUDFLARE (Após Deploy)

Agora você precisa conectar o Railway ao seu frontend no Cloudflare.

### Passo 1: Adicionar Variável de Ambiente

```bash
# No terminal do GenSpark
cd /home/user/webapp
npx wrangler secret put RAILWAY_BACKTEST_URL
```

Quando pedir o valor, cole a URL do Railway:
```
https://backtest-service-production-abc123.up.railway.app
```

### Passo 2: Atualizar o Código (Proxy)

Vou criar um arquivo atualizado de `backtest-routes.ts` que chama o Railway:

```typescript
// Arquivo: src/backtest-routes.ts
import { Hono } from 'hono';

type Bindings = {
  DB: D1Database;
  RAILWAY_BACKTEST_URL?: string;
};

const backtestRoutes = new Hono<{ Bindings: Bindings }>();

// Helper para chamar Railway API
async function callRailway(env: any, endpoint: string, options: RequestInit = {}) {
  const baseUrl = env.RAILWAY_BACKTEST_URL || 'http://localhost:8080';
  const url = `${baseUrl}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  
  return response.json();
}

// GET /strategies
backtestRoutes.get('/strategies', async (c) => {
  try {
    const data = await callRailway(c.env, '/strategies');
    return c.json(data);
  } catch (error: any) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// GET /symbols
backtestRoutes.get('/symbols', async (c) => {
  try {
    const data = await callRailway(c.env, '/symbols');
    return c.json(data);
  } catch (error: any) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// POST /run
backtestRoutes.post('/run', async (c) => {
  try {
    const body = await c.req.json();
    const data = await callRailway(c.env, '/run', {
      method: 'POST',
      body: JSON.stringify(body)
    });
    return c.json(data);
  } catch (error: any) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// POST /run-all
backtestRoutes.post('/run-all', async (c) => {
  try {
    const data = await callRailway(c.env, '/run-all', { method: 'POST' });
    return c.json(data);
  } catch (error: any) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// GET /reports
backtestRoutes.get('/reports', async (c) => {
  try {
    const data = await callRailway(c.env, '/reports');
    return c.json(data);
  } catch (error: any) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

// GET /reports/:filename
backtestRoutes.get('/reports/:filename', async (c) => {
  try {
    const filename = c.req.param('filename');
    const data = await callRailway(c.env, `/reports/${filename}`);
    return c.json(data);
  } catch (error: any) {
    return c.json({ success: false, error: error.message }, 500);
  }
});

export default backtestRoutes;
```

### Passo 3: Reativar as Rotas no index.tsx

```typescript
// Adicionar import no topo
import backtestRoutes from './backtest-routes';

// Adicionar rota (onde estava antes)
app.route('/api/backtests', backtestRoutes);
```

### Passo 4: Build e Deploy

```bash
npm run build
npx wrangler pages deploy dist --project-name investing-agent
```

---

## ✅ VERIFICAÇÃO FINAL

### 1. Testar Railway

```bash
# Health check
curl https://SUA-URL-RAILWAY.up.railway.app/health

# Listar estratégias
curl https://SUA-URL-RAILWAY.up.railway.app/strategies

# Listar símbolos
curl https://SUA-URL-RAILWAY.up.railway.app/symbols
```

### 2. Testar Frontend

Acesse: https://ainvestingpro.com/backtest

- Cards devem mostrar números (não mais `-`)
- Selects devem ter opções
- Executar backtest deve funcionar!

---

## 📊 MONITORAMENTO

### Railway Dashboard

No Railway, você pode ver:
- **Logs**: Todos os requests e erros
- **Metrics**: CPU, RAM, Network
- **Deployments**: Histórico de deploys

### Cloudflare Analytics

No Cloudflare, você pode ver:
- **Requests**: Quantidade de chamadas à API
- **Errors**: Taxa de erro
- **Performance**: Tempo de resposta

---

## 💰 CUSTOS

### Railway Free Tier
- **$5 de crédito/mês** (suficiente para testes)
- **500 horas de execução**
- Após esgotar, o serviço pausa automaticamente

### Upgrade (se necessário)
- **Hobby Plan**: $5/mês (uso ilimitado)
- **Pro Plan**: $20/mês (features avançadas)

---

## 🆘 TROUBLESHOOTING

### Erro: "Port already in use"
**Solução**: O Dockerfile já usa `${PORT:-8080}` que funciona com Railway

### Erro: "Module not found"
**Solução**: Verifique se `requirements.txt` está correto

### Erro: "Health check failed"
**Solução**: Verifique logs no Railway Dashboard

### Frontend não conecta
**Solução**: Verifique se `RAILWAY_BACKTEST_URL` está configurada corretamente

---

## 📞 PRÓXIMOS PASSOS

1. ✅ **Deploy no Railway** (seguir este guia)
2. ✅ **Obter URL do serviço**
3. ✅ **Configurar Cloudflare**
4. ✅ **Atualizar código (proxy)**
5. ✅ **Build e deploy final**
6. ✅ **Testar end-to-end**

---

**Tempo total**: 10-15 minutos  
**Dificuldade**: Fácil ⭐⭐☆☆☆  
**Custo**: $0 (usando free tier)

🎉 **Boa sorte com o deploy!**
