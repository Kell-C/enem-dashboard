import pandas as pd, os, json, unicodedata, re

P = 'data/agregados'
def L(f): return pd.read_parquet(os.path.join(P, f + '.parquet'))

def norm(s):
    s = str(s).upper()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'^(EE|EM|E E|ESCOLA ESTADUAL|ESCOLA)\s+', '', s)
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

CLEAN = {1:'Aquidauana',2:'CG Metrop.',3:'Corumbá',4:'Coxim',5:'Dourados',
         6:'Iguatemi',7:'Jardim',8:'Naviraí',9:'Nova Andradina',10:'Paranaíba',
         11:'Ponta Porã',12:'Três Lagoas'}
def clean_cre(raw):
    s = str(raw)
    if s.strip().upper().endswith('SED') or s.strip().upper() == 'SED':
        return 'SED/Capital'
    m = re.search(r'CRE\s*(\d+)', s)
    if m:
        return CLEAN.get(int(m.group(1)), 'CRE ' + m.group(1))
    return '—'

AREAS = [('CN','media_cn'),('CH','media_ch'),('LC','media_lc'),('MT','media_mt'),('RED','media_redacao')]

# ---------- CRE (estadual) ----------
pc = L('participacao_cre')
pc = pc[pc.dependencia == 'Estadual'].copy()
pc['CREc'] = pc['CRE'].map(clean_cre)
cre = {}
for name, g in pc.groupby('CREc'):
    g = g.sort_values('ano')
    cre[name] = {
        'med': [round(float(x),1) for x in g.media_geral],
        'tx':  [round(float(x),1) for x in g.tx_part_efetiva],
        'n':   [int(x) for x in g.estudantes],
        'areas': {k: [round(float(x),1) for x in g[col]] for k,col in AREAS}
    }

# ---------- municipio -> CRE (de escolas_2024 estadual) ----------
e = L('escolas_2024'); est = e[e.dependencia == 'Estadual'].copy()
mun2cre = {}
for _, r in est.dropna(subset=['cre']).iterrows():
    mun2cre[norm(r['municipio'])] = clean_cre(r['cre'])

# ---------- municipios (estadual) series ----------
mu = L('municipios'); mu = mu[mu.dependencia == 'Estadual'].copy()
mun = {}
cre_to_muns = {}
# concluintes por municipio/ano da planilha SED (fonte canonica do projeto),
# casados por nome normalizado. Corrige municipios com acento que falhavam no
# merge do parquet (Corumba/Ladario/Anastacio...).
import sys as _sys, os as _os
if _os.getcwd() not in _sys.path:
    _sys.path.insert(0, _os.getcwd())
import concluintes_loader as _cl
_cm = _cl.carregar_concluintes_municipio()
muni_concl = {}
for _, _row in _cm.iterrows():
    muni_concl[(norm(_row['MUNICIPIO']), int(_row['NU_ANO']))] = int(_row['Concluintes'])
for name, g in mu.groupby('NO_MUNICIPIO_ESC'):
    g = g.sort_values('ano')
    k = norm(name)
    crek = mun2cre.get(k, '—')
    _years = [int(a) for a in g.ano]
    _ests = list(g.estudantes)
    _txs = []
    for _yr, _est in zip(_years, _ests):
        _c = muni_concl.get((k, _yr))
        _txs.append(round(float(_est)/_c*100, 1) if (_c and not pd.isna(_est)) else None)
    _concl2024 = muni_concl.get((k, 2024))
    rec = {
        'cre': crek,
        'med': [round(float(x),1) for x in g.media_geral],
        'tx':  _txs,
        'n':   [None if pd.isna(x) else int(x) for x in g.estudantes],
        'concl': _concl2024,
        'part2024': int(g[g.ano==2024]['estudantes'].iloc[0]) if (g.ano==2024).any() else None,
        'a2024': {kk: (round(float(g[g.ano==2024][col].iloc[0]),0) if (g.ano==2024).any() and not pd.isna(g[g.ano==2024][col].iloc[0]) else None) for kk,col in AREAS},
        'areas': {kk: [round(float(x),1) for x in g[col]] for kk,col in AREAS}
    }
    mun[name] = rec
    cre_to_muns.setdefault(crek, []).append(name)

# ---------- escolas 2024 (estadual) com tx via concluintes excel ----------
xl = pd.read_excel(r'data/Concluintes EM 2019 a 2024.xlsx', sheet_name='2024-2019')
mcol = [c for c in xl.columns if 'unic' in c.lower()][0]
xl = xl[xl.NU_ANO == 2024].copy()
xl['k'] = xl[mcol].map(norm) + '|' + xl['Unidade Escolar'].map(norm)
cg = xl.groupby('k')['Concluintes'].sum()

esc = {}
for _, r in est.iterrows():
    if pd.isna(r['NOME_ESCOLA']) or pd.isna(r['media_geral']):
        continue
    k = norm(r['municipio']) + '|' + norm(r['NOME_ESCOLA'])
    concl = cg.get(k)
    tx = None
    if concl and concl > 0:
        t = r['estudantes'] / concl * 100
        tx = round(float(t),1) if t <= 100 else None
        concl = int(concl)
    else:
        concl = None
    esc.setdefault(r['municipio'], []).append({
        'nome': re.sub(r'^E\.?E\.?\s+','', str(r['NOME_ESCOLA']))[:34],
        'part': int(r['estudantes']),
        'concl': concl, 'tx': tx,
        'cn': round(float(r['media_cn']),0), 'ch': round(float(r['media_ch']),0),
        'lc': round(float(r['media_lc']),0), 'mt': round(float(r['media_mt']),0),
        'red': round(float(r['media_redacao']),0), 'geral': round(float(r['media_geral']),1)
    })

# medias MS por area (referencia) p/ destaque de atencao
ref = L('referencias')
msarea = {}
for kk, col in [('CN','NU_NOTA_CN'),('CH','NU_NOTA_CH'),('LC','NU_NOTA_LC'),('MT','NU_NOTA_MT'),('RED','NU_NOTA_REDACAO')]:
    s = ref[ref.area==col].sort_values('ano')
    msarea[kk] = {'ms':[round(float(x),1) for x in s.media_ms], 'br':[round(float(x),1) for x in s.media_br]}

# ---------- redes DE MS (por dependencia) p/ comparacao entre redes ----------
dz = L('desempenho_uf')
dz = dz[dz.uf == 'MS']
DCOLS = [('CN','media_nu_nota_cn'),('CH','media_nu_nota_ch'),('LC','media_nu_nota_lc'),('MT','media_nu_nota_mt'),('RED','media_nu_nota_redacao')]
redes = {}
for dep in ['Estadual','Municipal','Federal','Privada']:
    g = dz[dz.dependencia == dep].sort_values('ano')
    if g.empty:
        continue
    redes[dep] = {
        'med': [round(float(x),1) for x in g.media_media_geral],
        'areas': {k: [round(float(x),1) for x in g[col]] for k,col in DCOLS},
        'n': [int(x) for x in g.estudantes]
    }

# ---------- funil 2024 (universo concluintes -> presentes) por rede ----------
pa = L('participacao_ano')
pa24 = pa[pa.ano == 2024]
funil = {}
for _, r in pa24.iterrows():
    funil[str(r['dependencia'])] = {
        'inscritos': int(r['inscritos']), 'presentes': int(r['presentes']),
        'eliminados': int(r['eliminados']), 'concluintes': int(r['concluintes']),
        'presfilt': int(r['presentes_filt'])
    }

# ---------- serie anual de validos (estadual MS) p/ dimensao absoluta ----------
ANOS_ORD = [2019,2020,2021,2022,2023,2024]
pae = pa[pa.dependencia == 'Estadual'].set_index('ano')
estadualN = [int(pae.loc[a,'presentes_filt']) if a in pae.index else None for a in ANOS_ORD]
estadualConcl = [int(pae.loc[a,'concluintes']) if a in pae.index else None for a in ANOS_ORD]

# ======================================================================
# INTEGRIDADE / QUALIDADE DA PARTICIPACAO
# ======================================================================
IAREAS = ['CN','CH','LC','MT']
def _ser(g, col):
    g = g.set_index('ano')
    out = []
    for a in ANOS_ORD:
        if a not in g.index:
            out.append(None); continue
        v = g.loc[a, col]
        if isinstance(v, pd.Series):
            v = v.iloc[0]
        out.append(None if pd.isna(v) else round(float(v), 2))
    return out
def _seri(g, col):
    g = g.set_index('ano')
    out = []
    for a in ANOS_ORD:
        if a not in g.index:
            out.append(None); continue
        v = g.loc[a, col]
        if isinstance(v, pd.Series):
            v = v.iloc[0]
        out.append(None if pd.isna(v) else int(v))
    return out

# --- rede (MS 4 deps + Brasil estadual) ---
ir = L('integridade_rede')
integRede = {}
def _rede_rec(g):
    g = g.sort_values('ano')
    rec = {'comp':_seri(g,'compareceu'),'filt':_seri(g,'presentes_filt'),
           'et':_seri(g,'elim_total'),'er':_seri(g,'elim_redacao'),
           'em':_seri(g,'elim_multi'),'zm':_seri(g,'zeros_multi'),'sm':_seri(g,'semnota_multi'),
           'sn':_seri(g,'semnota_redacao'),'txE':_ser(g,'tx_elim'),
           'txS':_ser(g,'tx_semnota_redacao'),
           'areaElim':{k:_seri(g,'elim_'+k.lower()) for k in IAREAS},
           'zeros':{k:_seri(g,'zeros_'+k.lower()) for k in IAREAS}}
    return rec
for dep in ['Estadual','Federal','Municipal','Privada']:
    g = ir[(ir.escopo=='MS')&(ir.dependencia==dep)]
    if not g.empty:
        integRede[dep] = _rede_rec(g)
gbr = ir[(ir.escopo=='Brasil')&(ir.dependencia=='Estadual')]
if not gbr.empty:
    integRede['Brasil-Estadual'] = _rede_rec(gbr)

# --- municipio (estadual, todas edicoes) + CRE consistente via mun2cre ---
im = L('integridade_municipio')
integMun = {}
cre_acc = {}   # cre limpa -> {ano: {met:soma}}
for name, g in im.groupby('MUNICIPIO'):
    if str(name).strip().lower().startswith('sem munic'):
        continue
    g = g.sort_values('ano')
    k = norm(name)
    crek = mun2cre.get(k, '—')
    integMun[name] = {'cre':crek,'filt':_seri(g,'presentes_filt'),
                      'et':_seri(g,'elim_total'),'er':_seri(g,'elim_redacao'),
                      'em':_seri(g,'elim_multi'),'zm':_seri(g,'zeros_multi'),'sm':_seri(g,'semnota_multi'),
                      'sn':_seri(g,'semnota_redacao'),'txE':_ser(g,'tx_elim'),
                      'txS':_ser(g,'tx_semnota_redacao')}
    for _, rr in g.iterrows():
        d = cre_acc.setdefault(crek, {}).setdefault(int(rr['ano']), {'comp':0,'filt':0,'et':0,'er':0,'em':0,'zm':0,'sm':0,'sn':0})
        for mm in ['comp','filt','et','er','em','zm','sm','sn']:
            src = {'comp':'compareceu','filt':'presentes_filt','et':'elim_total','er':'elim_redacao','em':'elim_multi','zm':'zeros_multi','sm':'semnota_multi','sn':'semnota_redacao'}[mm]
            d[mm] += int(rr[src])
# --- CRE (agregada a partir dos municipios -> nomes consistentes com o painel) ---
integCre = {}
for crek, byano in cre_acc.items():
    if crek == '—':
        continue
    rec = {'filt':[],'et':[],'er':[],'em':[],'zm':[],'sm':[],'sn':[],'txE':[],'txS':[]}
    for a in ANOS_ORD:
        d = byano.get(a)
        if not d:
            for kk in rec: rec[kk].append(None)
            continue
        rec['filt'].append(d['filt']); rec['et'].append(d['et']); rec['er'].append(d['er'])
        rec['em'].append(d['em']); rec['zm'].append(d['zm']); rec['sm'].append(d['sm']); rec['sn'].append(d['sn'])
        rec['txE'].append(round(d['et']/d['comp']*100,2) if d['comp'] else None)
        rec['txS'].append(round(d['sn']/d['filt']*100,2) if d['filt'] else None)
    integCre[crek] = rec

# --- escolas 2024 (estadual) por municipio ---
ie = L('integridade_escola_2024')
integEsc = {}
for _, r in ie.iterrows():
    mn = str(r['MUNICIPIO'])
    nome = re.sub(r'^E\.?E\.?\s+','', str(r['NOME_ESCOLA'])).strip()[:34] or '(escola sem nome)'
    integEsc.setdefault(mn, []).append({
        'nome':nome,'filt':int(r['presentes_filt']),'et':int(r['elim_total']),
        'er':int(r['elim_redacao']),'em':int(r['elim_multi']),'zm':int(r['zeros_multi']),'sm':int(r['semnota_multi']),
        'sn':int(r['semnota_redacao']),
        'txE':None if pd.isna(r['tx_elim']) else round(float(r['tx_elim']),1),
        'txS':None if pd.isna(r['tx_semnota_redacao']) else round(float(r['tx_semnota_redacao']),1)
    })

integ = {'rede':integRede,'cre':integCre,'mun':integMun,'esc':integEsc}

# --- escRank: ranking de escolas por área (mock a partir de escolas_2024) ---
escRank = {}
for area, col in AREAS:
    rows = []
    for _, r in est.iterrows():
        v = r.get(col)
        if pd.isna(v): continue
        rows.append({'nome': re.sub(r'^E\.?E\.?\s+','', str(r['NOME_ESCOLA'])).strip()[:34] or '(escola)', 'nota': round(float(v),1)})
    rows.sort(key=lambda x: x['nota'], reverse=True)
    escRank[area] = rows

out = {'anos':ANOS_ORD,'cre':cre,'creMuns':cre_to_muns,'mun':mun,'esc':esc,'msArea':msarea,'redes':redes,'funil2024':funil,'estadualN':estadualN,'estadualConcl':estadualConcl,'integ':integ,'escRank':escRank}

# --- estatisticas avancadas REAIS dos microdados ---
import json, os

# Carrega estatisticas reais calculadas dos microdados
STATS_2019_2023 = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'stats_2019_2023.json')))
STATS_2024 = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'stats_2024.json')))
STATS_BR_2019_2023 = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'stats_br_2019_2023.json')))
STATS_BR_2024 = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'stats_br_2024.json')))

# boxplot por area/ano: min, q1, mediana, q3, max
boxplot = {}
for area in ['CN','CH','LC','MT','RED']:
    boxplot[area] = {}
    for ano in ANOS_ORD:
        src = STATS_2024.get(area) if ano == 2024 else STATS_2019_2023.get(area, {}).get(str(ano))
        if not src:
            continue
        boxplot[area][ano] = {
            'min': src['min'], 'q1': src['q1'], 'med': src['mediana'],
            'q3': src['q3'], 'max': src['max'],
            'outliers': []
        }

# histograma por area/ano: 6 faixas (reais MS + BR)
histograma = {}
for area in ['CN','CH','LC','MT','RED']:
    histograma[area] = {}
    for ano in ANOS_ORD:
        src_ms = STATS_2024.get(area) if ano == 2024 else STATS_2019_2023.get(area, {}).get(str(ano))
        src_br = STATS_BR_2024.get(area) if ano == 2024 else STATS_BR_2019_2023.get(area, {}).get(str(ano))
        if not src_ms or not src_br:
            continue
        histograma[area][ano] = {'ms': src_ms['hist'], 'br': src_br['hist']}

# desvio padrao e CV por area/ano (reais)
desvio_padrao = {}
cv = {}
for area in ['CN','CH','LC','MT','RED']:
    desvio_padrao[area] = []
    cv[area] = []
    for ano in ANOS_ORD:
        src = STATS_2024.get(area) if ano == 2024 else STATS_2019_2023.get(area, {}).get(str(ano))
        if not src:
            desvio_padrao[area].append(None)
            cv[area].append(None)
            continue
        desvio_padrao[area].append(src['std'])
        cv[area].append(round(src['std']/src['media']*100, 1))

# dispersao escolas 2024: nota vs participacao (bubble) — so escolas com nome e tx valida
# Escolas sem nome, sem tx, ou com tx > 100% nao aparecem no grafico de dispersao
# (tx > 100% indica problema nos dados de concluintes: mais participantes efetivos
#  que concluintes registrados na planilha da SED/MS)
dispersao = []
for _, r in est.iterrows():
    if pd.isna(r['media_geral']) or pd.isna(r['estudantes']):
        continue
    if pd.isna(r['NOME_ESCOLA']):
        continue
    tx = r.get('tx_part_efetiva')
    if pd.isna(tx) or tx == 0 or tx > 100:
        continue
    dispersao.append({
        'nome': re.sub(r'^E\.?E\.?\s+','', str(r['NOME_ESCOLA'])).strip()[:34] or '(escola)',
        'mun': str(r['municipio']),
        'cre': clean_cre(r['cre']) if not pd.isna(r.get('cre')) else '—',
        'nota': round(float(r['media_geral']),1),
        'n': int(r['estudantes']),
        'tx': round(float(tx),1)
    })

out['boxplot'] = boxplot
out['histograma'] = histograma
out['dispersao'] = dispersao
out['desvio_padrao'] = desvio_padrao
out['cv'] = cv

with open('mock_data.js','w',encoding='utf-8') as f:
    f.write('window.MOCK=' + json.dumps(out, ensure_ascii=False) + ';')
print('OK municipios:', len(mun), '| CREs:', list(cre.keys()))
print('CRE->#muns:', {k:len(v) for k,v in cre_to_muns.items()})
print('escolas municipios:', len(esc), '| ex Dourados escolas:', len(esc.get('Dourados',[])))
print('sample mun Aquidauana cre:', mun.get('Aquidauana',{}).get('cre'))
