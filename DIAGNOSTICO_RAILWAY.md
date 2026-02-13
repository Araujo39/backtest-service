# 🔧 GUIA DE DIAGNÓSTICO E CORREÇÃO - Railway Travando

## ✅ CORREÇÕES APLICADAS

### **1. Lazy Imports** 
- Movido imports de `ai_optimizer` e `strategy_validator` para dentro das funções
- Evita erro de inicialização se módulos tiverem problemas

### **2. Diretórios Corrigidos**
- Mudado `DATA_DIR` de `DATA/` para `DATA_spot/` (onde estão os dados reais)
- Adicionado criação automática de diretórios `reports/` e `strategies/`

### **3. Health Check Melhorado**
- Agora retorna diagnóstico completo:
  - Status do OpenAI API Key
  - Disponibilidade dos módulos AI
  - Status dos diretórios
  
### **4. Tratamento de Erro Robusto**
- Todos os endpoints com tratamento de exceção apropriado
- Mensagens de erro descritivas

---

## 📋 PASSO A PASSO DE DIAGNÓSTICO

### **PASSO 1: Aguardar Deploy (2 minutos)**

Após o push, o Railway demora ~1-2 minutos para fazer rebuild e deploy.

```bash
# Aguarde 90 segundos
sleep 90
```

---

### **PASSO 2: Testar Health Check Detalhado**

```bash
curl -s https://backtest-service-production.up.railway.app/health | python -m json.tool
```

**Resultado esperado:**
```json
{
  "status": "healthy",
  "python_version": "3.x.x",
  "openai_configured": true,
  "data_dir_exists": true,
  "reports_dir_exists": true,
  "strategies_dir_exists": true,
  "ai_optimizer_available": true,
  "validator_available": true
}
```

**Se `openai_configured: false`:**
- A variável `OPENAI_API_KEY` não está configurada no Railway
- Vá em Railway Dashboard → Variables → Verifique

**Se `data_dir_exists: false`:**
- Os arquivos CSV não foram commitados
- Verifique se `DATA_spot/` está no repositório

**Se `ai_optimizer_available: false`:**
- Verifique o erro em `ai_optimizer_error`
- Provavelmente falta a biblioteca `openai` no `requirements.txt`

---

### **PASSO 3: Verificar Logs do Railway**

1. Acesse: https://railway.app
2. Selecione o projeto `backtest-service`
3. Clique na aba **"Deployments"**
4. Clique no deploy mais recente
5. Veja os **logs** em tempo real

**Procure por erros como:**
- `ModuleNotFoundError: No module named 'openai'`
- `FileNotFoundError: [Errno 2] No such file or directory: 'DATA_spot'`
- `ImportError: cannot import name`

---

### **PASSO 4: Verificar Variáveis de Ambiente**

```bash
# No Railway Dashboard:
# Settings → Variables

# Deve ter:
OPENAI_API_KEY = sk-proj-XXXXXXXXXXXXXXXXXXXXXXXX
```

Se não tiver, adicione agora.

---

### **PASSO 5: Testar Endpoints Básicos**

```bash
# Teste 1: Root
curl https://backtest-service-production.up.railway.app/

# Teste 2: Estratégias
curl https://backtest-service-production.up.railway.app/strategies

# Teste 3: Símbolos
curl https://backtest-service-production.up.railway.app/symbols
```

---

## 🛠️ SOLUÇÕES PARA PROBLEMAS COMUNS

### **Problema 1: Erro 502 (Application failed to respond)**

**Causas possíveis:**
1. Aplicação não iniciou (erro no código)
2. Porta errada configurada
3. Timeout muito curto

**Solução:**
```bash
# Verificar logs do Railway
# Procurar por stack trace do Python

# Se for problema de porta:
# Railway detecta automaticamente a porta do FastAPI
# Não precisa configurar nada
```

---

### **Problema 2: ModuleNotFoundError: No module named 'openai'**

**Solução:**
```bash
# Verificar se openai está no requirements.txt
cd /home/user/webapp/railway-setup
grep openai requirements.txt

# Se não estiver, adicionar:
echo "openai==1.12.0" >> requirements.txt
git add requirements.txt
git commit -m "fix: Adicionar openai ao requirements"
git push origin main
```

---

### **Problema 3: FileNotFoundError: DATA_spot not found**

**Solução:**
```bash
# Verificar se os arquivos CSV foram commitados
cd /home/user/webapp/railway-setup
ls -la DATA_spot/

# Se não existirem, adicionar ao git:
git add DATA_spot/
git commit -m "fix: Adicionar dados CSV reais"
git push origin main
```

---

### **Problema 4: ImportError nos módulos AI**

**Solução:**
```bash
# Verificar se os arquivos Python existem
cd /home/user/webapp/railway-setup
ls -la ai_optimizer.py strategy_validator.py

# Se não existirem, foram perdidos no commit
# Precisam ser recriados ou recuperados
```

---

## 🔍 COMANDO DE DIAGNÓSTICO COMPLETO

Execute este comando para diagnóstico completo:

```bash
echo "=== DIAGNÓSTICO RAILWAY BACKTEST SERVICE ===" && \
echo "" && \
echo "1. Health Check:" && \
curl -s https://backtest-service-production.up.railway.app/health | python -m json.tool && \
echo "" && \
echo "2. Root Endpoint:" && \
curl -s https://backtest-service-production.up.railway.app/ | python -m json.tool && \
echo "" && \
echo "3. Estratégias:" && \
curl -s https://backtest-service-production.up.railway.app/strategies | python -m json.tool && \
echo "" && \
echo "=== FIM DO DIAGNÓSTICO ==="
```

---

## 📞 PRÓXIMOS PASSOS

Depois que o deploy terminar (~2 minutos após o último push), execute:

```bash
# Aguardar deploy
sleep 120

# Teste completo
curl -s https://backtest-service-production.up.railway.app/health | python -m json.tool
```

**Me envie a saída completa deste comando** para eu analisar o problema exato.

---

## ⚡ HOTFIX SE NADA FUNCIONAR

Se mesmo após todas as correções ainda estiver travando:

### **Opção 1: Rebuild Forçado no Railway**

1. Railway Dashboard → Deployments
2. Clique nos três pontos do deploy atual
3. Selecione **"Redeploy"**
4. Aguarde 2-3 minutos

### **Opção 2: Criar app.py Minimalista Temporário**

Se precisar, posso criar uma versão ultra-simplificada do app.py que funciona garantido, sem os endpoints de IA temporariamente, apenas para garantir que o serviço suba.

---

**Me informe o resultado do health check após 2 minutos do último push!** 🚀
