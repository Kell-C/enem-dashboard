import pandas as pd, os
from datetime import datetime

# Verificar se o parquet atual tem os dados corretos
esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')

# Verificar se CO_ESCOLA 50012975 (EE Maria Jose) tem concluintes=23
row = esc[esc['CO_ESCOLA'] == 50012975.0]
if len(row) > 0:
    print('EE Maria Jose no parquet:')
    print(row[['CO_ESCOLA','NOME_ESCOLA','estudantes','Concluintes','tx_part_efetiva']].to_string())
else:
    print('EE Maria Jose NAO encontrado no parquet')

# Verificar data de modificacao do parquet
stat = os.stat(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
print(f'\nData: {datetime.fromtimestamp(stat.st_mtime)}')

# Verificar se a planilha de concluintes tem valores diferentes
conc = pd.read_csv(r'C:\enem_analise\dados_processados\concluintes_3ano_ms_2019_2024.csv')
c2024 = conc[conc['NU_ANO'] == 2024]
row2 = c2024[c2024['CO_ESCOLA'] == 50012975]
if len(row2) > 0:
    print(f'\nEE Maria Jose na planilha: concluintes={row2.iloc[0]["Concluintes"]}')
else:
    print('\nEE Maria Jose NAO encontrado na planilha')
