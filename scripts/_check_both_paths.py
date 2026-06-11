import pandas as pd
import os

# Verificar ambos os arquivos
p1 = r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet'
p2 = r'C:\enem_analise\dados_processados\agregados\escolas_2024.parquet'

print('p1 existe:', os.path.exists(p1))
print('p2 existe:', os.path.exists(p2))

if os.path.exists(p1):
    d1 = pd.read_parquet(p1)
    print('p1 shape:', d1.shape)
    print('p1 estudantes > 0:', (d1['estudantes'] > 0).sum())

if os.path.exists(p2):
    d2 = pd.read_parquet(p2)
    print('p2 shape:', d2.shape)
    print('p2 estudantes > 0:', (d2['estudantes'] > 0).sum())
