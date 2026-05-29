# AGENTS.md

## Cursor Cloud specific instructions

### Product

Single Python **Streamlit** app: ENEM 2019–2024 analytics for Mato Grosso do Sul (SED/MS). Two run modes:

| Mode | Entry | Data |
|------|--------|------|
| **Supabase (recommended in cloud)** | `dashboard_enem_supabase.py` | Pre-aggregated tables on hosted PostgreSQL |
| **Local files** | `dashboard_enem_v14.py` (and dated variants) | Large local `.parquet` + optional `cres.xlsx` — paths in those files are **Windows** and must be edited before use |

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
