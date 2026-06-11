import pandas as pd

# Verificar se os CO_ESCOLA das escolas com tx>100 existem na planilha de concluintes
esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
alta = esc[esc['tx_part_efetiva'] > 100]

df_conc = pd.read_csv(r'C:\enem_analise\dados_processados\concluintes_3ano_ms_2019_2024.csv')
c2024 = df_conc[df_conc['NU_ANO'] == 2024]

print('Verificando escolas com tx>100:')
for _, r in alta.iterrows():
    co = r['CO_ESCOLA']
    conc = c2024[c2024['CO_ESCOLA'] == co]
    if len(conc) > 0:
        print(f'{r["NOME_ESCOLA"]} ({co}): planilha={conc.iloc[0]["Concluintes"]}, parquet={r["Concluintes"]}')
    else:
        print(f'{r["NOME_ESCOLA"]} ({co}): NAO ENCONTRADO na planilha')
