import pandas as pd

df = pd.read_parquet(r'C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet', filters=[('NU_ANO', '==', 2024)])
print('NU_INSCRICAO nulos:', df['NU_INSCRICAO'].isna().sum())
print('NU_INSCRICAO tipo:', df['NU_INSCRICAO'].dtype)
print('Primeiros valores:', df['NU_INSCRICAO'].head().tolist())
