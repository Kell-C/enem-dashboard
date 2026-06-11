import pandas as pd, numpy as np, json, sys

sys.stdout.reconfigure(line_buffering=True)
print('Lendo 2024...', flush=True)

cols = ['NU_ANO','SG_UF_ESC','TP_DEPENDENCIA_ADM_ESC','TP_ST_CONCLUSAO',
        'TP_PRESENCA_CN','TP_PRESENCA_CH','TP_PRESENCA_LC','TP_PRESENCA_MT',
        'TP_STATUS_REDACAO','NU_NOTA_CN','NU_NOTA_CH','NU_NOTA_LC','NU_NOTA_MT','NU_NOTA_REDACAO']

df = pd.read_parquet(r'C:\enem_analise\dados_processados\2024\enem_resultados_2024.parquet', columns=cols)
print(f'Shape: {df.shape}', flush=True)

# 2024: nao temos conclusao por aluno, usar todos presentes 2 dias nao eliminados como referencia
f = (df['SG_UF_ESC'] == 'MS') & (df['TP_DEPENDENCIA_ADM_ESC'] == 2)
f &= (df['TP_PRESENCA_CN'] == 1) & (df['TP_PRESENCA_CH'] == 1) & (df['TP_PRESENCA_LC'] == 1) & (df['TP_PRESENCA_MT'] == 1)
f &= (df['TP_STATUS_REDACAO'] == 1)
print(f'Filtrados 2024: {f.sum()}', flush=True)

areas = {'CN':'NU_NOTA_CN','CH':'NU_NOTA_CH','LC':'NU_NOTA_LC','MT':'NU_NOTA_MT','RED':'NU_NOTA_REDACAO'}
result = {}
for area, col in areas.items():
    sub = df[f][col].dropna()
    if len(sub) == 0:
        continue
    result[area] = {
        'n': int(len(sub)),
        'media': round(float(sub.mean()), 1),
        'mediana': round(float(sub.median()), 1),
        'std': round(float(sub.std()), 1),
        'min': round(float(sub.min()), 1),
        'q1': round(float(sub.quantile(0.25)), 1),
        'q3': round(float(sub.quantile(0.75)), 1),
        'max': round(float(sub.max()), 1)
    }
    bins = [0, 200, 400, 500, 600, 800, 1000]
    hist, _ = np.histogram(sub, bins=bins)
    result[area]['hist'] = [round(float(h)/len(sub)*100, 1) for h in hist]
    print(f'  {area} OK (n={len(sub)})', flush=True)

with open(r'C:\enem-dashboard\.worktrees\claude-opus-4-8-1781034975013\stats_2024.json', 'w') as f:
    json.dump(result, f)
print('Salvo stats_2024.json', flush=True)
