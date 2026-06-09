"""Fase 3a: substitui aplicar_tema, _hex_rgba e _legenda_padrao por app/v15/plotly_theme."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

needle = "from app.v15.ui import _render_html, _logo_data_uri\n"
if needle not in "".join(lines):
    raise SystemExit("Phase 2 imports missing")
insert = (
    needle
    + "from app.v15.plotly_theme import aplicar_tema, _hex_rgba, _legenda_padrao\n"
)
text = "".join(lines).replace(needle, insert, 1)
lines = text.splitlines(keepends=True)

# Remove aplicar_tema + _hex_rgba (between _chart_hub and _estilizar_tabela)
start = end = None
for i, ln in enumerate(lines):
    if ln.startswith("def aplicar_tema("):
        start = i
    if start is not None and ln.startswith("def _estilizar_tabela("):
        end = i
        break
if start is None or end is None:
    raise SystemExit(f"plotly_theme block not found: {start} {end}")
lines[start:end] = []

# Remove _legenda_padrao (standalone, before _legenda_inline)
start = end = None
for i, ln in enumerate(lines):
    if ln.startswith("def _legenda_padrao("):
        start = i
    if start is not None and ln.startswith("def _legenda_inline("):
        end = i
        break
if start is None or end is None:
    raise SystemExit(f"_legenda_padrao block not found: {start} {end}")
lines[start:end] = []

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 3a patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
