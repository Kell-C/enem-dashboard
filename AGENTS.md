# AGENTS.md

## Cursor Cloud specific instructions

### Product

Single Python **Streamlit** app: ENEM 2019–2024 analytics for Mato Grosso do Sul (SED/MS). Two run modes:

| Mode | Entry | Data |
|------|--------|------|
| **Local (recommended)** | `dashboard.py` | Pre-aggregated parquet in `data/agregados/` via `dados_agregados_loader.py` |
| **Supabase (cloud)** | `dashboard_enem_supabase.py` | Pre-aggregated tables on hosted PostgreSQL |
| **Full BI (local/Supabase)** | `dashboard_enem_v15.py` | Hub denso, boxplots, histogramas — same aggregates |

`cres.xlsx` / `cres__.xlsx` live at repo root for local/ETL use. The multi-GB ENEM parquet is **not** in the repo.

### One-time VM system package

If `python3 -m venv .venv` fails with `ensurepip is not available`, install once:

```bash
sudo apt-get update && sudo apt-get install -y python3.12-venv
```

### Dependencies

```bash
cd /workspace
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python smoke_imports.py
```

`importar_supabase.py` uses `tqdm`, which is not in `requirements.txt` — only needed for bulk ETL imports.

### Run the app (local path)

Reads `data/agregados/*.parquet` by default (`DATA_SOURCE=local`). Override folder with `PASTA_AGREGADOS`.

```bash
.venv/bin/streamlit run dashboard.py --server.headless true
```

```bash
.venv/bin/streamlit run dashboard_enem_v15.py --server.headless true
```

### Refatoração v15 (`app/v15/`)

Modularização incremental do monolito (layout inalterado):

| Fase | Módulo | Conteúdo |
|------|--------|----------|
| 1 ✅ | `app/v15/theme.py`, `styles.py` | Constantes + ~1100 linhas CSS |
| 2 ✅ | `app/v15/formatting.py`, `ui.py`, `paths.py` | fmt_*, render HTML, logo |
| 3a ✅ | `app/v15/plotly_theme.py` | aplicar_tema, _hex_rgba, _legenda_padrao |
| 3b ✅ | `app/v15/boxplots.py`, `hub_charts.py` | boxplots, hover, eixos/legendas hub, _fechar_fig_hub |
| 4 ✅ | `app/v15/pages/` | aba_* (wrappers + `*_body.py`; helpers ainda no monolito) |
| 5a ✅ | `nav_constants`, `constants`, `components`, `classifiers`, `charts_render`, `runtime` | helpers UI/classificação/render; wrappers usam `page_globals` |
| 5b ✅ | `paths`, `participation`, `ms_enrich`, `concluintes_data`, `territory_data`, `charts/hub` | dados territoriais + gráficos hub; monolito ~1.8k após 5c |
| 5c ✅ | `charts/detail` | figuras das abas detalhe (histogramas, rankings, evolução, boxplots) |
| 5d ✅ | `page_helpers`, `page_imports`, páginas sem `exec` | helpers compartilhados + funções Python normais nos `*_body.py` |

Reparar módulos 5b corrompidos: `python scripts/recover_phase5b.py` (fonte: monolito em `git HEAD`)

Regenerar páginas 5d: `python scripts/phase5d_from_git.py` (fonte: monolito em `git HEAD`)

Reextrair fase 5c: `python scripts/extract_v15_phase5c.py` + `python scripts/patch_v15_phase5c.py`

**Não** rodar `extract_v15_phase5b.py` / `patch_v15_phase5b.py` no monolito atual (~1.1k linhas): marcadores de linha desatualizados; use `recover_phase5b.py`.

`page_imports.py` define `__all__` para que `from app.v15.page_imports import *` nos `*_body.py` exporte símbolos com prefixo `_` (ex.: `_render_hub_panorama`).

Reextrair após editar helpers da fase 5: `python scripts/extract_v15_phase5.py` + `python scripts/patch_v15_phase5.py`

Reparar wrappers de página: `python scripts/fix_v15_phase5_pages.py`

Reextrair boxplots/hub após editar no monolito: `python scripts/extract_v15_phase3b.py` + `python scripts/patch_v15_phase3b.py`

Páginas (fase 4): corpos em `app/v15/pages/*_body.py`; reparar wrappers com `python scripts/fix_v15_phase4_pages.py`

### Run the app (Supabase path)

Default Supabase pooler settings are in `dashboard_enem_supabase.py` (env vars override). Optional: `.streamlit/secrets.toml` with flat keys `SUPABASE_HOST`, `SUPABASE_PORT`, `SUPABASE_DB`, `SUPABASE_USER`, `SUPABASE_PASS`.

```bash
.venv/bin/streamlit run dashboard_enem_supabase.py --server.headless true
```

Default URL: **http://127.0.0.1:8501**. Health: `http://127.0.0.1:8501/_stcore/health`.

Use **tmux** for long-running Streamlit (e.g. session `streamlit-enem`).

### Lint / tests

No project linter or pytest suite. Practical checks:

- `python smoke_imports.py` — dependency import smoke test
- `python -m compileall .` — syntax check on all `.py` files

### ETL (optional, not needed for Supabase dashboard runtime)

- `gerar_dados_agregados.py` — build aggregate parquet from raw ENEM data
- `importar_agregados_supabase.py` — load aggregates into Supabase

### Gotchas

- **Sumário Executivo** metric cards may show zeros while charts/tables still load from other aggregate tables — expected if `sumario_executivo` row shape differs for the latest year filter.
- Local dashboards hardcode `C:\enem_analise\...` paths; do not expect `dashboard_enem_v14.py` to work in Linux without path edits and local parquet.
- Streamlit `.streamlit/config.toml` sets `runOnSave = true` and `fileWatcherType = "poll"` (works better in container/VM file watchers).
