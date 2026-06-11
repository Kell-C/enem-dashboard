import pandas as pd

df = pd.read_csv(r'C:\enem_analise\dados_processados\concluintes_3ano_ms_2019_2024.csv')
print('Shape:', df.shape)
print('Cols:', list(df.columns))
print('Anos:', sorted(df['NU_ANO'].unique()))

c2024 = df[df['NU_ANO'] == 2024]
print('Concluintes 2024:', len(c2024))
print(c2024.head().to_string())
print('Max concluintes:', c2024['Concluintes'].max())
print('Escolas com concluintes > 0:', (c2024['Concluintes'] > 0).sum())

# Verificar escolas problematicas do escolas_2024
esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
alta = esc[esc['tx_part_efetiva'] > 100]
print('\nEscolas tx>100 no escolas_2024:')
print(alta[['CO_ESCOLA','NOME_ESCOLA','municipio','estudantes','Concluintes','tx_part_efetiva']].to_string())

# Verificar se essas escolas existem na planilha de concluintes
print('\nVerificando na planilha de concluintes:')
for _, r in alta.iterrows():
    co = r['CO_ESCOLA']
    conc = c2024[c2024['CO_ESCOLA'] == co]
    if len(conc) > 0:
        print(f'{r["NOME_ESCOLA"]} ({co}): concluintes={conc.iloc[0]["Concluintes"]}')
    else:
        print(f'{r["NOME_ESCOLA"]} ({co}): NAO ENCONTRADA na planilha')
