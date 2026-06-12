import pandas as pd, os

for name in ['participacao_ano','sumario_executivo','referencias','desempenho','desempenho_uf']:
    path = f'data/agregados/{name}.parquet'
    if os.path.exists(path):
        df = pd.read_parquet(path)
        print(f'=== {name} ===')
        print(df.to_string(index=False))
        print()
    else:
        print(f'{name}: NOT FOUND')
        print()
