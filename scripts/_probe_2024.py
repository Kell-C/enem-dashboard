import pandas as pd, numpy as np, json, sys

sys.stdout.reconfigure(line_buffering=True)
print('Lendo 2024...', flush=True)

# Verificar colunas disponiveis
df = pd.read_parquet(r'C:\enem_analise\dados_processados\2024\enem_resultados_2024.parquet')
print(f'Shape: {df.shape}', flush=True)
print(f'Cols: {list(df.columns)}', flush=True)

# Verificar se tem colunas de UF e dependencia
uf_cols = [c for c in df.columns if 'UF' in c.upper()]
dep_cols = [c for c in df.columns if 'DEP' in c.upper() or 'ADM' in c.upper()]
print(f'UF cols: {uf_cols}', flush=True)
print(f'Dep cols: {dep_cols}', flush=True)

# Verificar presenca
pres_cols = [c for c in df.columns if 'PRESENCA' in c.upper()]
print(f'Presenca cols: {pres_cols}', flush=True)

# Verificar notas
nota_cols = [c for c in df.columns if 'NOTA' in c.upper()]
print(f'Nota cols: {nota_cols}', flush=True)
