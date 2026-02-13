# 📝 GUIA MANUAL - Upload no GitHub

## ✅ **O QUE VOCÊ JÁ FEZ**
- Criou o repositório `backtest-service` ✅
- Fez upload dos arquivos da raiz ✅

---

## 📁 **FALTAM 3 PASTAS**

Você precisa criar:
1. **strategies/** (6 arquivos)
2. **DATA/** (10 arquivos CSV)
3. **reports/** (pasta vazia)

---

## 🎯 **SOLUÇÃO MAIS RÁPIDA**

Como são muitos arquivos (16 no total), **recomendo fortemente usar o terminal**.

Mas se quiser fazer manual mesmo, vou te dar um **atalho**:

### **OPÇÃO A: Fazer apenas o essencial**

Para o Railway funcionar, você **só precisa** de:

1. ✅ Dockerfile (já tem)
2. ✅ app.py (já tem)
3. ✅ requirements.txt (já tem)
4. ✅ backtest_lab.py (já tem)
5. ⚠️ **strategies/** (OBRIGATÓRIO - 6 arquivos)
6. ⚠️ **DATA/** (OBRIGATÓRIO - 10 arquivos)

Os arquivos `run_all_backtests.py` e `generate_report.py` são opcionais (apenas para batch).

---

## 🚀 **RECOMENDAÇÃO FINAL**

**Use o terminal! É 100x mais rápido:**

```bash
# 1. Navegue até a pasta onde descompactou os arquivos
cd caminho/para/backtest-service

# 2. Configure git (se ainda não fez)
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# 3. Inicialize e faça push
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/SEU_USUARIO/backtest-service.git
git branch -M main
git push -u origin main
```

Vai pedir senha → use um **Personal Access Token** (veja abaixo como criar).

---

## 🔑 **CRIAR TOKEN DO GITHUB (1 minuto)**

1. GitHub → Settings (seu perfil) → Developer settings (final da página)
2. Personal access tokens → Tokens (classic)
3. **Generate new token (classic)**
4. Nome: `Railway Deploy`
5. Marque: **`repo`** (todos os subitens)
6. **Generate token**
7. **COPIE O TOKEN** (ele só aparece uma vez!)
8. Use esse token como "senha" no `git push`

---

## 📊 **COMPARAÇÃO**

| Método | Tempo | Dificuldade | Arquivos |
|--------|-------|-------------|----------|
| **Terminal** | 2 min | ⭐⭐☆☆☆ | Todos (16) |
| **Manual** | 30-40 min | ⭐⭐⭐⭐⭐ | Arquivo por arquivo |

---

## 💡 **MINHA SUGESTÃO**

**Tente o terminal!** É muito mais rápido. Se tiver algum problema, eu te ajudo a resolver.

Me diga:
1. Qual sistema operacional? (Windows/Mac/Linux)
2. Onde descompactou os arquivos?
3. Já usou terminal/git antes?

E eu te dou comandos **personalizados** que você só precisa copiar e colar! 😊

---

## 🆘 **AINDA QUER FAZER MANUAL?**

Se **realmente** quiser fazer manual, eu posso:

**Opção 1**: Te dar os conteúdos dos 16 arquivos aqui (vai ser MUITO texto)

**Opção 2**: Criar um script que você roda localmente e ele faz tudo automaticamente

**Opção 3**: Te ajudar com o terminal passo a passo (mais rápido!)

**Qual você prefere?** 🤔
