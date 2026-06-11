import pandas as pd

esc = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')

# Escolas com tx > 100
alta = esc[esc['tx_part_efetiva'] > 100]
print('Escolas tx>100:')
print(alta[['NOME_ESCOLA','municipio','estudantes','Concluintes','tx_part_efetiva']].to_string())

# Escolas sem nome
sem_nome = esc[esc['NOME_ESCOLA'].isna()]
print(f'\nEscolas sem nome: {len(sem_nome)}')
print(sem_nome[['CO_ESCOLA','municipio','estudantes','Concluintes','tx_part_efetiva']].head(10).to_string())
