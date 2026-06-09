"""Fase 5c: importa charts/detail e remove blocos inline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

hub_loop = "del _v15_mod, _v15_name, _v15_territory_data, _v15_hub_charts\n"
if hub_loop not in "".join(lines):
    raise SystemExit("phase 5b hub reexport missing")

insert = hub_loop + (
    "from app.v15.charts import detail as _v15_detail_charts\n"
    "\n"
    "for _v15_name in dir(_v15_detail_charts):\n"
    "    if _v15_name.startswith(\"__\"):\n"
    "        continue\n"
    "    globals()[_v15_name] = getattr(_v15_detail_charts, _v15_name)\n"
    "del _v15_name, _v15_detail_charts\n"
)
text = "".join(lines).replace(hub_loop, insert, 1)
lines = text.splitlines(keepends=True)


def remove_block(start_pred, end_pred, label: str) -> None:
    global lines
    start = end = None
    for i, ln in enumerate(lines):
        if start is None and start_pred(ln):
            start = i
        if start is not None and end_pred(ln):
            end = i
            break
    if start is None or end is None:
        raise SystemExit(f"{label} not found: {start} {end}")
    del lines[start:end]


# bottom-up
remove_block(
    lambda ln: ln.startswith("def _abreviar_escola("),
    lambda ln: ln.startswith("def _secao_detalhe_ano_desempenho("),
    "detail figs main",
)
remove_block(
    lambda ln: ln.startswith("def _adicionar_referencias_ms_br("),
    lambda ln: ln.startswith("def _diagnostico_ranking_desempenho_uf("),
    "detail refs",
)
remove_block(
    lambda ln: ln.startswith("def _fig_histogram_notas("),
    lambda ln: ln.startswith("def _legenda_inline("),
    "detail histograms",
)
remove_block(
    lambda ln: ln.startswith("def range_dinamico("),
    lambda ln: ln.startswith("def _kpi_titulo("),
    "range_dinamico",
)

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 5c patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
