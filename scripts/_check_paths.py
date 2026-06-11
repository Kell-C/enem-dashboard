import pandas as pd

# Verificar o parquet atual no data/agregados
esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
row = esc[esc['CO_ESCOLA'] == 50012975.0]
print('data/agregados/escolas_2024.parquet:')
print(row[['CO_ESCOLA','NOME_ESCOLA','estudantes','Concluintes','tx_part_efetiva']].to_string())

# Verificar o parquet gerado pelo ETL
esc2 = pd.read_parquet(r'C:\enem_analise\dados_processados\agregados\escolas_2024.parquet')
row2 = esc2[esc2['CO_ESCOLA'] == 50012975.0]
print('\nC:\\enem_analise\\dados_processados\\agregados\\escolas_2024.parquet:')
print(row2[['CO_ESCOLA','NOME_ESCOLA','estudantes','Concluintes','tx_part_efetiva']].to_string())
