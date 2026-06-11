import pandas as pd

# Verificar planilha original de concluintes
df = pd.read_csv(r'C:\enem_analise\dados_processados\concluintes_3ano_ms_2019_2024.csv')
c2024 = df[df['NU_ANO'] == 2024]

# Escolas problematicas
codes = [50001124, 50011383, 50012975, 50017373, 50021028, 50026852, 50028456, 50029827]
for co in codes:
    row = c2024[c2024['CO_ESCOLA'] == co]
    if len(row) > 0:
        r = row.iloc[0]
        print(f'{r["NOME_ESCOLA"]}: concluintes={r["Concluintes"]}')
    else:
        print(f'{co}: NAO ENCONTRADO')

# Verificar se ha duplicatas de CO_ESCOLA em 2024
print('\nDuplicatas CO_ESCOLA em 2024:', c2024['CO_ESCOLA'].duplicated().sum())
print('Total escolas 2024:', len(c2024))

# Verificar escolas com tx > 100 no escolas_2024
esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
alta = esc[esc['tx_part_efetiva'] > 100]
print('\nEscolas tx>100 no escolas_2024:')
print(alta[['CO_ESCOLA','NOME_ESCOLA','estudantes','Concluintes','tx_part_efetiva']].to_string())
