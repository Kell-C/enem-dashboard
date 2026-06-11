import pandas as pd

# Verificar o parquet gerado pelo ETL
esc2 = pd.read_parquet(r'C:\enem_analise\dados_processados\agregados\escolas_2024.parquet')
print('Colunas:', list(esc2.columns))
print('Shape:', esc2.shape)

# Verificar se CO_ESCOLA 50012975 existe
row2 = esc2[esc2['CO_ESCOLA'] == 50012975.0]
print('EE Maria Jose:')
print(row2.to_string())

# Verificar todas as escolas problematicas
codes = [50001124, 50011383, 50012975, 50017373, 50021028, 50026852, 50028456, 50029827]
print('\nEscolas problematicas no NOVO parquet:')
for co in codes:
    rows = esc2[esc2['CO_ESCOLA'] == co]
    if len(rows) > 0:
        r = rows.iloc[0]
        print(f'{co}: estudantes={r.estudantes}, Concluintes={r.get("Concluintes", "N/A")}, tx={r.get("tx_part_efetiva", "N/A")}')
    else:
        print(f'{co}: NAO ENCONTRADO')
