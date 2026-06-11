import pandas as pd

# Verificar se ha duplicatas na planilha original
df = pd.read_csv(r'C:\enem_analise\dados_processados\concluintes_3ano_ms_2019_2024.csv')
c2024 = df[df['NU_ANO'] == 2024]
print('Total 2024:', len(c2024))
print('Duplicatas CO_ESCOLA:', c2024['CO_ESCOLA'].duplicated().sum())

# Verificar se CO_ESCOLA 50012975 aparece mais de uma vez
dup = c2024[c2024['CO_ESCOLA'] == 50012975]
print('Ocorrencias de 50012975:', len(dup))
if len(dup) > 0:
    print(dup.to_string())

# Verificar todas as escolas problematicas
codes = [50001124, 50011383, 50012975, 50017373, 50021028, 50026852, 50028456, 50029827]
print('\nVerificando escolas problematicas:')
for co in codes:
    rows = c2024[c2024['CO_ESCOLA'] == co]
    print(f'{co}: {len(rows)} ocorrencias, concluintes={rows["Concluintes"].tolist() if len(rows) > 0 else "NAO ENCONTRADO"}')
