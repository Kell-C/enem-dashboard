import pandas as pd

df = pd.read_parquet(r'C:\enem_analise\dados_processados\2024\enem_resultados_2024.parquet', columns=['SG_UF_ESC','TP_DEPENDENCIA_ADM_ESC','TP_PRESENCA_CN','TP_PRESENCA_CH','TP_PRESENCA_LC','TP_PRESENCA_MT','TP_STATUS_REDACAO','CO_ESCOLA'])
print('Shape:', df.shape)

# Filtro igual ao ETL
f = (df['SG_UF_ESC'] == 'MS') & (df['TP_DEPENDENCIA_ADM_ESC'] == 2)
f &= (df['TP_PRESENCA_CN'] == 1) & (df['TP_PRESENCA_CH'] == 1) & (df['TP_PRESENCA_LC'] == 1) & (df['TP_PRESENCA_MT'] == 1)
f &= (df['TP_STATUS_REDACAO'] != 4)
print('Filtrados MS estadual presentes nao eliminados:', f.sum())

# Verificar escolas problematicas
codes = [50001124, 50011383, 50012975, 50017373, 50021028, 50026852, 50028456, 50029827]
for co in codes:
    fc = f & (df['CO_ESCOLA'] == co)
    print(f'{co}: {fc.sum()} participantes')
