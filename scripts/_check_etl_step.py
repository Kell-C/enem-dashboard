import pandas as pd

# Simular o ETL passo a passo
df = pd.read_parquet(r'C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet', filters=[('NU_ANO', '==', 2024)])
print('1. Shape inicial:', df.shape)

# DEP_ADM
dep_map = {1: 'Federal', 2: 'Estadual', 3: 'Municipal', 4: 'Privada'}
df['DEP_ADM'] = df['TP_DEPENDENCIA_ADM_ESC'].map(dep_map)
print('2. DEP_ADM ok')

# PRESENTE_2_DIAS
df['PRESENTE_2_DIAS'] = (
    (df['TP_PRESENCA_CN'] == 1) &
    (df['TP_PRESENCA_CH'] == 1) &
    (df['TP_PRESENCA_LC'] == 1) &
    (df['TP_PRESENCA_MT'] == 1)
)
print('3. PRESENTE_2_DIAS:', df['PRESENTE_2_DIAS'].sum())

# ELIMINADO
df['ELIMINADO'] = df['TP_STATUS_REDACAO'] == 4
print('4. ELIMINADO:', df['ELIMINADO'].sum())

# CONCLUINTE
df['CONCLUINTE'] = df['CO_ESCOLA'].notna()
print('5. CONCLUINTE:', df['CONCLUINTE'].sum())

# Filtro
mask_filt = df['PRESENTE_2_DIAS'] & ~df['ELIMINADO']
df_filt = df[mask_filt]
print('6. df_filt shape:', df_filt.shape)

# MS Estadual
ms = df_filt[(df_filt['SG_UF_ESC'] == 'MS') & (df_filt['DEP_ADM'] == 'Estadual')]
print('7. MS Estadual:', ms.shape)

# Agrupar por escola
esc = ms.groupby('CO_ESCOLA').agg(estudantes=('NU_INSCRICAO', 'count')).reset_index()
print('8. Escolas:', esc.shape)
print('9. Escolas com estudantes > 0:', (esc['estudantes'] > 0).sum())
