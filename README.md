# Enem Dashboard — pipeline_dashboard/enem-dashboard

Breve guia de setup e execução local do painel ENEM MS (2019–2024).

Pré-requisitos
- Python 3.10+

Instalação (venv local — recomendado no Debian/Ubuntu)

```bash
cd pipeline_dashboard/enem-dashboard
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Executar pipeline (processa microdados, gera agregados e export para web):

```bash
bash run_pipeline.sh
```

Só regenerar agregados + `painel_data.js` (sem reprocessar microdados):

```bash
bash gerar_dados.sh
```

Ou manualmente com o venv (não use `python3` do sistema se faltar pacotes):

```bash
.venv/bin/python scripts/gerar_agregados.py
.venv/bin/python scripts/gerar_web_data.py
```

Servir o painel localmente (abre servidor na porta 8765):

```bash
bash abrir_painel.sh
# então abra http://127.0.0.1:8765/index.html
```

Arquivos relevantes
- `scripts/processar_enem.py` — ETL e consolidação parquet
- `scripts/gerar_agregados.py` — computa agregados e métricas
- `scripts/gerar_web_data.py` — serializa `docs/data/painel_data.js`
- `docs/index.html` — frontend (HTML) carregando `docs/style.css`, módulos em `docs/js/` e `docs/data/painel_data.js`
- `docs/js/` — módulos JS (`config`, `data-utils`, `chart-factory`, seções por aba, `app.js` orquestrador)

Notas
- Se você mover o diretório `docs/`, atualize `scripts/enem_config.py`.
- Para desenvolvimento iterativo, gere `docs/data/painel_data.js` e use `bash abrir_painel.sh` para evitar bloqueios do navegador ao abrir arquivos via `file://`.
