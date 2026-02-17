#!/usr/bin/env python3
"""Teste rápido do endpoint /update-data"""
import requests

# Criar CSV de teste
csv_content = """timestamp,open,high,low,close,volume
2026-02-17 00:00:00,69000.0,69100.0,68900.0,69050.0,10.5
2026-02-17 00:15:00,69050.0,69150.0,68950.0,69100.0,12.3
"""

with open('/tmp/test.csv', 'w') as f:
    f.write(csv_content)

# Enviar para localhost (se Railway estivesse rodando local)
print("CSV de teste criado: /tmp/test.csv")
print("Conteúdo:")
print(csv_content)
