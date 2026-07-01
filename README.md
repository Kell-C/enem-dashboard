# Enem Dashboard — pipeline_dashboard/enem-dashboard

Breve guia de setup e execução local do painel ENEM MS (2019–2025).

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

Baixar histórico ENEM por escola no site AIO (2013–2025) e atualizar seção do painel:

```bash
bash baixar_aio.sh
# ou, com opções:
.venv/bin/python scripts/baixar_aio_escolas.py --limit 10 --delay 1.5
.venv/bin/python scripts/gerar_aio_web_data.py
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
- `scripts/baixar_aio_escolas.py` — scraping AIO por CO_INEP (MS)
- `scripts/gerar_aio_web_data.py` — serializa `docs/data/aio_data.js`
- `docs/index.html` — frontend (HTML) carregando `docs/style.css`, módulos em `docs/js/` e `docs/data/painel_data.js`
- `docs/js/aio-section.js` — trajetória 2013–2025 e ranking AIO 2025

Notas
- Se você mover o diretório `docs/`, atualize `scripts/enem_config.py`.
- Para desenvolvimento iterativo, gere `docs/data/painel_data.js` e use `bash abrir_painel.sh` para evitar bloqueios do navegador ao abrir arquivos via `file://`.
- O scraping AIO usa códigos INEP do `painel_data.js` (rede estadual MS). Cache HTML em `dados/aio/cache/` (ignorado pelo git).
