#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import pandas as pd
import numpy as np
import importlib

def normalize_strategy_result(result, capital):
    """
    Normaliza o resultado de estratégias customizadas para formato esperado.
    Compatível com múltiplos formatos de retorno.
    
    Args:
        result: Retorno da estratégia (dict ou DataFrame)
        capital: Capital inicial
        
    Returns:
        dict normalizado com campos obrigatórios
    """
    if isinstance(result, dict):
        # Detectar e normalizar diferentes formatos
        normalized = {
            'success': result.get('success', True),
            'capital_start': capital,
            'capital_end': 0,
            'profit': 0,
            'win_rate': 0,
            'max_dd': 0,
            'n_trades': 0,
            'strategy': '',
            'symbol': '',
            'timeframe': ''
        }
        
        # Mapeamentos de campos comuns
        field_mappings = {
            # Capital
            'capital_end': ['capital_end', 'capital_final', 'final_equity', 'final_capital', 'equity'],
            'capital_start': ['capital_start', 'capital_inicial', 'initial_capital', 'capital'],
            
            # Profit
            'profit': ['profit', 'net_profit', 'roi', 'return', 'lucro'],
            
            # Win Rate (pode vir como 0.45 ou 45.0)
            'win_rate': ['win_rate', 'winrate', 'wr', 'taxa_acerto'],
            
            # Max Drawdown (pode vir como 0.15 ou 15.0)
            'max_dd': ['max_dd', 'max_drawdown', 'drawdown', 'dd'],
            
            # Trades
            'n_trades': ['n_trades', 'total_trades', 'num_trades', 'trades_count'],
        }
        
        # Aplicar mapeamentos
        for target_field, possible_names in field_mappings.items():
            for name in possible_names:
                if name in result and result[name] is not None:
                    value = result[name]
                    
                    # Normalizar win_rate (converter de 0-100 para 0-1 se necessário)
                    if target_field == 'win_rate' and value > 1:
                        value = value / 100.0
                    
                    # Normalizar max_dd (converter de 0-100 para 0-1 se necessário)
                    if target_field == 'max_dd' and value > 1:
                        value = value / 100.0
                    
                    normalized[target_field] = float(value) if value else 0
                    break
        
        # Calcular capital_end se não existir
        if normalized['capital_end'] == 0 and normalized['profit'] != 0:
            # Se profit é percentual
            if abs(normalized['profit']) < 10:  # Provavelmente já é percentual
                normalized['capital_end'] = capital * (1 + normalized['profit'] / 100)
            else:  # Profit absoluto
                normalized['capital_end'] = capital + normalized['profit']
        
        # Garantir que profit está em percentual
        if normalized['capital_end'] > 0:
            normalized['profit'] = ((normalized['capital_end'] - capital) / capital) * 100
        
        # Copiar outros campos úteis
        if 'trades' in result:
            normalized['trades'] = result['trades'][:50]  # Limitar a 50
        
        return normalized
    
    # Se não é dict, retornar None para processar como DataFrame
    return None

def calculate_backtest_metrics(df_or_dict, capital):
    """
    Calcula métricas de backtest a partir do DataFrame com sinais OU de um dict já processado.
    
    Args:
        df_or_dict: DataFrame com coluna 'signal' OU dict com métricas já calculadas
        capital: Capital inicial
    
    Returns:
        dict com métricas do backtest
    """
    # Se já é um dict (estratégias antigas), normalizar e retornar
    if isinstance(df_or_dict, dict):
        normalized = normalize_strategy_result(df_or_dict, capital)
        if normalized:
            return normalized
        return df_or_dict
    
    # Se é DataFrame, processar
    df = df_or_dict
    
    if 'signal' not in df.columns:
        return {
            "error": "DataFrame não contém coluna 'signal'",
            "success": False
        }
    
    # Calcular retornos
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    
    # Criar posição: 1 quando compramos, 0 quando não temos posição
    df['position'] = 0
    position = 0
    entry_price = 0
    
    trades = []
    equity = capital
    equity_curve = [capital]
    
    for i in range(len(df)):
        signal = df.iloc[i]['signal']
        current_price = df.iloc[i]['close']
        
        # Compra
        if signal == 1 and position == 0:
            position = equity / current_price  # Quantidade de moedas
            entry_price = current_price
            df.loc[df.index[i], 'position'] = 1
            
        # Venda
        elif signal == -1 and position > 0:
            exit_price = current_price
            pnl = (exit_price - entry_price) * position
            equity += pnl
            
            trades.append({
                'entry_price': float(entry_price),
                'exit_price': float(exit_price),
                'pnl': float(pnl),
                'return': float((exit_price - entry_price) / entry_price * 100)
            })
            
            position = 0
            entry_price = 0
            df.loc[df.index[i], 'position'] = 0
        
        # Manter posição
        elif position > 0:
            df.loc[df.index[i], 'position'] = 1
            # Atualizar equity com preço atual
            equity_curve.append(capital + (current_price - entry_price) * position)
        else:
            equity_curve.append(equity)
    
    # Fechar posição aberta no final
    if position > 0:
        exit_price = df.iloc[-1]['close']
        pnl = (exit_price - entry_price) * position
        equity += pnl
        trades.append({
            'entry_price': float(entry_price),
            'exit_price': float(exit_price),
            'pnl': float(pnl),
            'return': float((exit_price - entry_price) / entry_price * 100)
        })
    
    # Calcular métricas
    if len(trades) == 0:
        return {
            "success": True,
            "total_trades": 0,
            "profitable_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "net_profit": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "final_equity": float(capital),
            "roi": 0.0,
            "trades": []
        }
    
    profitable_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    
    total_profit = sum(t['pnl'] for t in profitable_trades) if profitable_trades else 0
    total_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
    net_profit = equity - capital
    
    # Calcular drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = abs(drawdown.min()) * 100
    
    # Sharpe Ratio (simplificado)
    returns = pd.Series([t['return'] for t in trades])
    sharpe_ratio = returns.mean() / returns.std() if len(returns) > 1 and returns.std() != 0 else 0
    
    return {
        "success": True,
        "total_trades": len(trades),
        "profitable_trades": len(profitable_trades),
        "losing_trades": len(losing_trades),
        "win_rate": float(len(profitable_trades) / len(trades) * 100) if trades else 0,
        "total_profit": float(total_profit),
        "total_loss": float(total_loss),
        "net_profit": float(net_profit),
        "profit_factor": float(total_profit / total_loss) if total_loss > 0 else float('inf'),
        "max_drawdown": float(max_drawdown),
        "sharpe_ratio": float(sharpe_ratio),
        "final_equity": float(equity),
        "initial_capital": float(capital),
        "roi": float((equity - capital) / capital * 100),
        "trades": trades[:50]  # Limitar a 50 trades para não sobrecarregar JSON
    }

def main():
    p = argparse.ArgumentParser(description="Backtest Lab - Multi Strategy")
    p.add_argument('--data_dir', required=True)
    p.add_argument('--symbol', required=True)
    p.add_argument('--tf', default='15m')
    p.add_argument('--strategy', required=True)
    p.add_argument('--capital', type=float, default=100.0)
    p.add_argument('--out', default='reports/report.json')
    args = p.parse_args()

    # Carregar dados
    df = pd.read_csv(f"{args.data_dir}/{args.symbol}.csv")
    
    # Importar e executar estratégia
    mod = importlib.import_module(f"strategies.{args.strategy}")
    run_strategy = getattr(mod, "run_strategy")
    
    # Executar estratégia (retorna DataFrame com coluna 'signal')
    result_df = run_strategy(df, capital=args.capital)
    
    # Calcular métricas do backtest
    metrics = calculate_backtest_metrics(result_df, args.capital)
    
    # Adicionar informações extras
    metrics['symbol'] = args.symbol
    metrics['strategy'] = args.strategy
    metrics['timeframe'] = args.tf
    
    # Salvar resultado
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print("OK. Relatório salvo em:", args.out)

if __name__ == "__main__":
    main()
