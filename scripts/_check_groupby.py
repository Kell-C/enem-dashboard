import pandas as pd

df = pd.read_parquet(r'C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet', filters=[('NU_ANO', '==', 2024)])
dep_map = {1: 'Federal', 2: 'Estadual', 3: 'Municipal', 4: 'Privada'}
df['DEP_ADM'] = df['TP_DEPENDENCIA_ADM_ESC'].map(dep_map)
df['PRESENTE_2_DIAS'] = (df['TP_PRESENCA_CN'] == 1) & (df['TP_PRESENCA_CH'] == 1) & (df['TP_PRESENCA_LC'] == 1) & (df['TP_PRESENCA_MT'] == 1)
df['ELIMINADO'] = df['TP_STATUS_REDACAO'] == 4
df['CONCLUINTE'] = df['CO_ESCOLA'].notna()
mask_filt = df['PRESENTE_2_DIAS'] & ~df['ELIMINADO']
df_filt = df[mask_filt]
ms = df_filt[(df_filt['SG_UF_ESC'] == 'MS') & (df_filt['DEP_ADM'] == 'Estadual')]

print('MS shape:', ms.shape)
print('CO_ESCOLA nulos:', ms['CO_ESCOLA'].isna().sum())
print('CO_ESCOLA nao-nulos:', ms['CO_ESCOLA'].notna().sum())
print('CO_ESCOLA unicos:', ms['CO_ESCOLA'].nunique())

# Agrupar incluindo nulos
esc = ms.groupby('CO_ESCOLA', dropna=False).agg(estudantes=('NU_INSCRICAO', 'count')).reset_index()
print('Escolas (com nulos):', esc.shape)
print('Escolas com estudantes > 0:', (esc['estudantes'] > 0).sum())
print('Primeiras escolas:')
print(esc.head(10).to_string())
