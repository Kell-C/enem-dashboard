import pandas as pd

# Simular o que o ETL faz
df = pd.read_parquet(r'C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet', filters=[('NU_ANO', '==', 2024)])
print('Shape 2024:', df.shape)
print('Colunas:', list(df.columns))

# Verificar se tem as colunas necessarias
print('TP_PRESENCA_CN:', 'TP_PRESENCA_CN' in df.columns)
print('TP_STATUS_REDACAO:', 'TP_STATUS_REDACAO' in df.columns)
print('SG_UF_ESC:', 'SG_UF_ESC' in df.columns)
print('TP_DEPENDENCIA_ADM_ESC:', 'TP_DEPENDENCIA_ADM_ESC' in df.columns)
print('CO_ESCOLA:', 'CO_ESCOLA' in df.columns)

# Verificar valores
print('SG_UF_ESC unicos:', df['SG_UF_ESC'].unique()[:10])
print('TP_DEPENDENCIA_ADM_ESC unicos:', df['TP_DEPENDENCIA_ADM_ESC'].unique())
