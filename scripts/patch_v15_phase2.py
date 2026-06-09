"""Fase 2: substitui formatação e UI helpers inline por app/v15/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

# Import block after styles import
needle = "from app.v15.styles import inject_v15_filter_styles, inject_v15_styles\n"
if needle not in "".join(lines):
    raise SystemExit("Phase 1 imports missing")
insert = (
    needle
    + "from app.v15.formatting import fmt_int, fmt_float, fmt_pct, fmt_delta, _safe_int_val, _pct_taxa\n"
    + "from app.v15.ui import _render_html, _logo_data_uri\n"
)
text = "".join(lines).replace(needle, insert, 1)
lines = text.splitlines(keepends=True)

# Remove FORMATAÇÃO section (find def fmt_int through fmt_delta)
start = end = None
for i, ln in enumerate(lines):
    if "# FORMATAÇÃO" in ln:
        start = i - 2
    if start is not None and ln.startswith("def _populacao_estadual_ano"):
        end = i
        break
if start is None or end is None:
    raise SystemExit(f"fmt block not found: {start} {end}")
lines[start:end] = []

# Remove _render_html and _logo_data_uri
start = end = None
for i, ln in enumerate(lines):
    if ln.startswith("def _render_html"):
        start = i
    if start is not None and ln.startswith("def _kpi_titulo"):
        end = i
        break
if start is None or end is None:
    raise SystemExit(f"ui block not found: {start} {end}")
lines[start:end] = []

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 2 patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
