import pandas as pd

df = pd.read_parquet(r'C:\enem_analise\dados_processados\2024\enem_resultados_2024.parquet', columns=['TP_STATUS_REDACAO','TP_PRESENCA_CN','TP_PRESENCA_CH','TP_PRESENCA_LC','TP_PRESENCA_MT'])
print('Shape:', df.shape)
print('TP_STATUS_REDACAO:', df['TP_STATUS_REDACAO'].unique())
print('TP_PRESENCA_CN:', df['TP_PRESENCA_CN'].unique())
print('Presentes 2 dias:', ((df['TP_PRESENCA_CN']==1) & (df['TP_PRESENCA_CH']==1) & (df['TP_PRESENCA_LC']==1) & (df['TP_PRESENCA_MT']==1)).sum())
print('Eliminados redacao:', (df['TP_STATUS_REDACAO']==4).sum())
