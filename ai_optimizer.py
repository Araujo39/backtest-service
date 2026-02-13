#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Optimizer Engine - OpenAI GPT-4 Integration
Analyzes trading strategies and generates optimized versions
"""

import os
import re
from typing import Dict, Any, List

# OpenAI API will be passed as parameter to avoid storing key in file

# ===========================================================================
# SYSTEM PROMPT FOR OPTIMIZATION
# ===========================================================================

OPTIMIZER_SYSTEM_PROMPT = """
Você é um especialista em trading algorítmico com 20 anos de experiência em mercados financeiros.
Sua missão é analisar estratégias de trading em Python e otimizá-las para alcançar:

TARGETS OBRIGATÓRIOS:
- Win rate > 80%
- Max drawdown < 15%
- Profit consistente e positivo
- Mínimo 30 trades para validação estatística

REGRAS CRÍTICAS QUE VOCÊ DEVE SEGUIR:
1. PRESERVE a assinatura da função: def run_strategy(df, capital, **params)
2. MANTENHA o formato de retorno exato (dict com keys específicas)
3. OTIMIZE indicadores técnicos (ajuste períodos de EMAs, RSI, MACD, ATR, etc)
4. AJUSTE parâmetros de risco (stop_loss_atr_mult, take_profit_atr_mult)
5. ADICIONE filtros de confirmação quando necessário (volume, tendência, volatilidade)
6. DOCUMENTE todas as mudanças importantes com comentários no código
7. Use APENAS bibliotecas já disponíveis: pandas, numpy, ta (technical analysis)

ANÁLISE OBRIGATÓRIA QUE VOCÊ DEVE FAZER:
- Identifique especificamente por que a estratégia está falhando
- Considere o contexto do mercado (bull, bear, sideways)
- Balance risco vs retorno de forma inteligente
- Adicione filtros de qualidade para entradas
- Melhore gestão de risco (stop loss, take profit)

IMPORTANTE: Retorne APENAS o código Python otimizado, sem explicações adicionais.
Use comentários no código para explicar as mudanças importantes.
"""

# ===========================================================================
# PROMPT BUILDER
# ===========================================================================

def build_optimization_prompt(
    code: str,
    metrics: Dict[str, float],
    problems: List[Dict[str, Any]]
) -> str:
    """
    Build intelligent prompt for GPT-4 optimization
    """
    
    # Format problems
    problems_text = ""
    for i, problem in enumerate(problems, 1):
        problems_text += f"\n{i}. {problem['type'].upper()}: {problem['description']}\n"
        problems_text += f"   Valor atual: {problem.get('current_value', 'N/A')}\n"
        problems_text += f"   Valor target: {problem.get('target_value', 'N/A')}\n"
        problems_text += f"   Sugestões:\n"
        for suggestion in problem.get('suggestions', [])[:3]:  # Top 3 suggestions
            problems_text += f"   - {suggestion}\n"
    
    prompt = f"""
# CÓDIGO DA ESTRATÉGIA ATUAL
```python
{code}
```

# PERFORMANCE ATUAL (ABAIXO DO ESPERADO)
- Win Rate: {metrics.get('avg_win_rate', 0):.2%} (target: ≥ 80%)
- Profit: {metrics.get('avg_profit', 0):.2f}% (target: > 0%)
- Max Drawdown: {metrics.get('avg_drawdown', 0):.2%} (target: ≤ 15%)
- Total Trades: {metrics.get('avg_trades', 0):.0f} (target: ≥ 30)
- Performance Score: {metrics.get('avg_score', 0):.1f}/100 (target: ≥ 80)

# PROBLEMAS IDENTIFICADOS
{problems_text}

# SUA TAREFA
Otimize essa estratégia de trading para atingir os targets acima.

FOQUE EM:
1. Aumentar win rate acima de 80%
2. Reduzir drawdown abaixo de 15%
3. Garantir profit positivo e consistente
4. Manter pelo menos 30 trades

RETORNE APENAS O CÓDIGO PYTHON OTIMIZADO.
Use comentários para explicar mudanças importantes.
"""
    
    return prompt

# ===========================================================================
# AI OPTIMIZER
# ===========================================================================

def optimize_strategy(
    strategy_name: str,
    current_code: str,
    performance_metrics: Dict[str, float],
    problems: List[Dict[str, Any]],
    openai_api_key: str,
    model: str = "gpt-4-turbo-preview"
) -> Dict[str, Any]:
    """
    Use OpenAI GPT-4 to optimize a trading strategy.
    
    Args:
        strategy_name: Name of the strategy
        current_code: Current Python code
        performance_metrics: Dict with avg_win_rate, avg_profit, etc
        problems: List of identified problems
        openai_api_key: OpenAI API key
        model: OpenAI model to use
    
    Returns:
        Dict with success, optimized_code, parameters, tokens_used, cost_usd
    """
    
    try:
        # Import OpenAI (lazy import)
        import openai
        
        # Set API key
        openai.api_key = openai_api_key
        
        # Build prompt
        user_prompt = build_optimization_prompt(
            code=current_code,
            metrics=performance_metrics,
            problems=problems
        )
        
        print(f"🤖 Calling OpenAI {model}...")
        print(f"   Strategy: {strategy_name}")
        print(f"   Problems: {len(problems)}")
        
        # Call OpenAI GPT-4
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": OPTIMIZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent code
            max_tokens=2500
        )
        
        # Extract optimized code
        optimized_code = response.choices[0].message.content
        
        # Clean up markdown code blocks if present
        optimized_code = re.sub(r'^```python\n|^```\n|```$', '', optimized_code, flags=re.MULTILINE)
        optimized_code = optimized_code.strip()
        
        print(f"   ✅ Code generated ({len(optimized_code)} chars)")
        
        # Validate Python syntax
        try:
            compile(optimized_code, '<string>', 'exec')
            print(f"   ✅ Syntax validated")
        except SyntaxError as e:
            print(f"   ⚠️  Syntax warning: {e}")
            # Don't fail, let validator catch it
        
        # Extract parameters from code (simplified)
        parameters = extract_parameters_from_code(optimized_code)
        
        # Calculate cost
        usage = response.usage
        # GPT-4 Turbo pricing: $0.01 per 1K input tokens, $0.03 per 1K output tokens
        cost = (usage.prompt_tokens * 0.01 / 1000) + (usage.completion_tokens * 0.03 / 1000)
        
        print(f"   💰 Cost: ${cost:.4f}")
        print(f"   📊 Tokens: {usage.total_tokens} ({usage.prompt_tokens} in, {usage.completion_tokens} out)")
        
        return {
            "success": True,
            "optimized_code": optimized_code,
            "parameters": parameters,
            "ai_response": response.choices[0].message.content,
            "tokens_used": usage.total_tokens,
            "cost_usd": round(cost, 4),
            "model": model
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "optimized_code": None,
            "parameters": {},
            "tokens_used": 0,
            "cost_usd": 0.0
        }

# ===========================================================================
# PARAMETER EXTRACTION
# ===========================================================================

def extract_parameters_from_code(code: str) -> Dict[str, Any]:
    """
    Extract default parameters from strategy code.
    Looks for common patterns like:
    - stop_loss_atr_mult = 1.5
    - take_profit_atr_mult = 2.0
    - ema_fast = 5
    - rsi_period = 14
    """
    
    parameters = {}
    
    # Common parameter patterns
    patterns = {
        'stop_loss_atr_mult': r'stop_loss.*?=\s*([\d.]+)',
        'take_profit_atr_mult': r'take_profit.*?=\s*([\d.]+)',
        'ema_fast': r'ema.*?fast.*?=\s*(\d+)',
        'ema_slow': r'ema.*?slow.*?=\s*(\d+)',
        'rsi_period': r'rsi.*?period.*?=\s*(\d+)',
        'atr_period': r'atr.*?period.*?=\s*(\d+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                parameters[key] = value
            except:
                pass
    
    # Default parameters if none found
    if not parameters:
        parameters = {
            "stop_loss_atr_mult": 1.5,
            "take_profit_atr_mult": 2.25
        }
    
    return parameters

# ===========================================================================
# MAIN (for testing)
# ===========================================================================

if __name__ == "__main__":
    # Example usage
    print("AI Optimizer Engine - Test Mode")
    print("=" * 60)
    
    # Example strategy code (simplified)
    example_code = """
def run_strategy(df, capital, **params):
    # Simple EMA crossover strategy
    df['ema_5'] = df['close'].ewm(span=5).mean()
    df['ema_13'] = df['close'].ewm(span=13).mean()
    
    # Buy when EMA 5 crosses above EMA 13
    df['signal'] = 0
    df.loc[df['ema_5'] > df['ema_13'], 'signal'] = 1
    
    # Simulate trades
    capital_current = capital
    trades = []
    
    for i in range(1, len(df)):
        if df['signal'].iloc[i] == 1 and df['signal'].iloc[i-1] == 0:
            # Buy
            trades.append({'entry': df['close'].iloc[i], 'exit': None})
        elif df['signal'].iloc[i] == 0 and df['signal'].iloc[i-1] == 1:
            # Sell
            if trades and trades[-1]['exit'] is None:
                trades[-1]['exit'] = df['close'].iloc[i]
    
    # Calculate results
    wins = sum(1 for t in trades if t['exit'] and t['exit'] > t['entry'])
    win_rate = wins / len(trades) if trades else 0
    
    return {
        'capital_start': capital,
        'capital_end': capital_current,
        'profit': ((capital_current - capital) / capital) * 100,
        'win_rate': win_rate * 100,
        'max_dd': 10.0,
        'n_trades': len(trades)
    }
"""
    
    # Example metrics and problems
    metrics = {
        'avg_win_rate': 0.31,
        'avg_profit': -4.24,
        'avg_drawdown': 0.0637,
        'avg_trades': 54,
        'avg_score': 65.3
    }
    
    problems = [
        {
            'type': 'low_win_rate',
            'description': 'Win rate muito baixo',
            'current_value': 0.31,
            'target_value': 0.80,
            'suggestions': ['Adicionar filtros', 'Ajustar stop loss']
        }
    ]
    
    print("\n📋 Input:")
    print(f"   Code length: {len(example_code)} chars")
    print(f"   Win rate: {metrics['avg_win_rate']:.1%}")
    print(f"   Problems: {len(problems)}")
    
    # Note: This requires OPENAI_API_KEY environment variable
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n⚠️  OPENAI_API_KEY not set. Skipping actual API call.")
        print("   Set environment variable to test: export OPENAI_API_KEY=your-key")
    else:
        result = optimize_strategy(
            strategy_name="SNIPER",
            current_code=example_code,
            performance_metrics=metrics,
            problems=problems,
            openai_api_key=api_key
        )
        
        if result['success']:
            print(f"\n✅ Optimization successful!")
            print(f"   Tokens: {result['tokens_used']}")
            print(f"   Cost: ${result['cost_usd']}")
            print(f"   Code length: {len(result['optimized_code'])} chars")
        else:
            print(f"\n❌ Optimization failed: {result['error']}")
