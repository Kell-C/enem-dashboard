import pandas as pd

df = pd.read_parquet(r'C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet', filters=[('NU_ANO', '==', 2024)])
print('NU_SEQUENCIAL nulos:', df['NU_SEQUENCIAL'].isna().sum())
print('NU_SEQUENCIAL tipo:', df['NU_SEQUENCIAL'].dtype)
print('Primeiros valores:', df['NU_SEQUENCIAL'].head().tolist())
