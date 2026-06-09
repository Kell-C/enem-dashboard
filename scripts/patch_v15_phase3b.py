"""Fase 3b: remove boxplots/hub_charts inline e importa de app/v15/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

needle = "from app.v15.plotly_theme import aplicar_tema, _hex_rgba, _legenda_padrao\n"
if needle not in "".join(lines):
    raise SystemExit("Phase 3a imports missing")

insert = needle + (
    "from app.v15.boxplots import (\n"
    "    _add_box,\n"
    "    _add_box_series,\n"
    "    _add_box_stats,\n"
    "    _add_scatter_notas,\n"
    "    _anotacao_hub,\n"
    "    _aplicar_hover_hub,\n"
    "    _finalizar_boxplot,\n"
    "    _finalizar_grafico,\n"
    "    _hex_to_rgba,\n"
    "    _preparar_hover_fig,\n"
    "    _range_y_box_stats,\n"
    "    _stats_box,\n"
    ")\n"
    "from app.v15.hub_charts import (\n"
    "    _aplicar_eixos_hub,\n"
    "    _aplicar_legenda_interna_combo_ms,\n"
    "    _altura_hub_ranking,\n"
    "    _classificar_cor_media_referencia,\n"
    "    _cores_ranking_presentes,\n"
    "    _fechar_fig_hub,\n"
    "    _legenda_fig,\n"
    "    _margem_hub,\n"
    "    _texto_posicao_barra,\n"
    ")\n"
)
text = "".join(lines).replace(needle, insert, 1)
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


# Boxplots block: _stats_box .. _add_scatter_notas (before _fig_histogram_notas)
remove_block(
    lambda ln: ln.startswith("def _stats_box("),
    lambda ln: ln.startswith("def _fig_histogram_notas("),
    "boxplots",
)

# _hex_to_rgba (before _aplicar_eixos_hub)
remove_block(
    lambda ln: ln.startswith("def _hex_to_rgba("),
    lambda ln: ln.startswith("def _aplicar_eixos_hub("),
    "_hex_to_rgba",
)

# Hub eixos/nota (before _render_widget_grafico_hub)
remove_block(
    lambda ln: ln.startswith("def _aplicar_eixos_hub("),
    lambda ln: ln.startswith("def _render_widget_grafico_hub("),
    "hub eixos",
)

# _classificar_cor_media_referencia (before _html_legenda_cores_ms_br)
remove_block(
    lambda ln: ln.startswith("def _classificar_cor_media_referencia("),
    lambda ln: ln.startswith("def _html_legenda_cores_ms_br("),
    "_classificar_cor_media_referencia",
)

# Hub legends through _fechar_fig_hub (before _fig_barras_areas_referencia)
remove_block(
    lambda ln: ln.startswith("def _html_legenda_cores_ms_br("),
    lambda ln: ln.startswith("def _fig_barras_areas_referencia("),
    "hub legends",
)

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 3b patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
