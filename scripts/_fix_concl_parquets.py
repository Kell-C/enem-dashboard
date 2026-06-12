import pandas as pd

# Concluintes corretos da SED (3o ano)
SED = {2019:21713, 2020:21628, 2021:23927, 2022:24370, 2023:21996, 2024:20891}

# Corrigir participacao_ano
df = pd.read_parquet('data/agregados/participacao_ano.parquet')
print('--- participacao_ano Antes ---')
print(df[df.dependencia=='Estadual'][['ano','concluintes','presentes_filt']].to_string(index=False))
mask_est = df['dependencia'] == 'Estadual'
df.loc[mask_est, 'concluintes'] = df.loc[mask_est, 'ano'].map(SED)
# Calcular nova taxa
est = df[mask_est].copy()
est['tx_part_efetiva'] = (est['presentes_filt'] / est['concluintes'] * 100).round(1)
print()
print('--- participacao_ano Depois ---')
print(est[['ano','concluintes','presentes_filt','tx_part_efetiva']].to_string(index=False))
# Atualizar coluna no df principal
df['tx_part_efetiva'] = 0.0
for _, r in est.iterrows():
    df.loc[(df['ano']==r['ano'])&(df['dependencia']==r['dependencia']), 'tx_part_efetiva'] = r['tx_part_efetiva']
df.to_parquet('data/agregados/participacao_ano.parquet')
print('participacao_ano.parquet salvo.\n')

# Corrigir sumario_executivo
se = pd.read_parquet('data/agregados/sumario_executivo.parquet')
print('--- sumario_executivo Antes ---')
print(se[['ano','total_concluintes','total_presentes']].to_string(index=False))
se['total_concluintes'] = se['ano'].map(SED)
print()
print('--- sumario_executivo Depois ---')
print(se[['ano','total_concluintes','total_presentes']].to_string(index=False))
se.to_parquet('data/agregados/sumario_executivo.parquet')
print('sumario_executivo.parquet salvo.\n')

# Corrigir municipios
mu = pd.read_parquet('data/agregados/municipios.parquet')
conc_mun = pd.read_csv('data/processed/concluintes_por_municipio_ano.csv')
import unicodedata, re
def norm(s):
    s = str(s).upper().strip()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return re.sub(r'[^A-Z0-9 ]', ' ', s).strip()
# Agrupar concluintes SED por municipio ANO
conc_mun['MUN_NORM'] = conc_mun['MUN_NORM'].apply(norm)
gm = conc_mun.groupby(['MUN_NORM','NU_ANO'], as_index=False)['Concluintes'].sum()
mapa_concl = {}
for _,r in gm.iterrows():
    mapa_concl[(r['MUN_NORM'],int(r['NU_ANO']))] = int(r['Concluintes'])
# Normalizar municipios dos microdados
mu['MUN_NORM'] = mu['NO_MUNICIPIO_ESC'].apply(norm)
# Atribuir concluintes SED onde possivel
mu['concl_sed'] = mu.apply(lambda r: mapa_concl.get((r['MUN_NORM'],r['ano']), None), axis=1)
# Para municipios sem match, propagar do ultimo ano disponivel
for m in mu['MUN_NORM'].unique():
    rows = mu[(mu['MUN_NORM']==m) & (mu['concl_sed'].notna())]
    if len(rows)>0:
        last = rows.sort_values('ano').iloc[-1]['concl_sed']
        mu.loc[(mu['MUN_NORM']==m) & (mu['concl_sed'].isna()), 'concl_sed'] = last
print('municipios SEM match SED (Estadual):', mu[(mu.dependencia=='Estadual') & mu['concl_sed'].isna()]['MUN_NORM'].nunique())
# Atualizar apenas estadual
est_mask = mu['dependencia'] == 'Estadual'
mu.loc[est_mask, 'Concluintes'] = mu.loc[est_mask, 'concl_sed']
mu['tx_part_efetiva'] = (mu['estudantes'] / mu['Concluintes'] * 100).round(1)
mu = mu.drop(columns=['MUN_NORM','concl_sed'])
mu.to_parquet('data/agregados/municipios.parquet')
print('municipios.parquet salvo.\n')

print('=== TX corretas MS Estadual ===')
for a in [2019,2020,2021,2022,2023,2024]:
    pf = est[est.ano==a]['presentes_filt'].iloc[0]
    print(f'{a}: {round(pf/SED[a]*100,1)}% ({pf}/{SED[a]})')
