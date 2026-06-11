import pandas as pd

df = pd.read_parquet(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\data\agregados\escolas_2024.parquet')
df['nome_limpo'] = df['NOME_ESCOLA'].astype(str).str.strip().str.upper()

alta = df[df['tx_part_efetiva'] > 100]
print('Escolas tx>100:')
for _, r in alta.iterrows():
    nome = str(r['NOME_ESCOLA']).strip().upper()
    mun = str(r['municipio'])
    outras = df[(df['nome_limpo'] == nome) & (df['municipio'] != mun)]
    dup = 'SIM' if len(outras) > 0 else 'NAO'
    print(f'{nome} ({mun}) tx={r["tx_part_efetiva"]}% dup={dup}')

print('\nNomes em multiplos municipios:')
nc = df.groupby('nome_limpo')['municipio'].nunique()
mn = nc[nc > 1]
for nome in mn.index:
    print(f'\n--- {nome} ---')
    print(df[df['nome_limpo'] == nome][['municipio','estudantes','Concluintes','tx_part_efetiva']].to_string())
