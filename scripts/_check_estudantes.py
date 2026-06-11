import pandas as pd

esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
print('Shape:', esc.shape)
print('Escolas com estudantes > 0:', (esc['estudantes'] > 0).sum())
print('Escolas com tx > 0:', (esc['tx_part_efetiva'] > 0).sum())
print('Escolas com tx > 100:', (esc['tx_part_efetiva'] > 100).sum())

# Amostra de escolas com estudantes > 0
print('\nAmostra escolas com estudantes > 0:')
print(esc[esc['estudantes'] > 0][['NOME_ESCOLA','municipio','estudantes','Concluintes','tx_part_efetiva']].head(10).to_string())
