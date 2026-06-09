"""Fase 5: importa módulos extraídos e remove blocos inline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
text = path.read_text(encoding="utf-8")

# HUB_BUILD_ID → app.v15.constants
text = text.replace(
    'HUB_BUILD_ID = "20260607j"\n\nimport base64',
    "from app.v15.constants import HUB_BUILD_ID\n\nimport base64",
    1,
)

needle = "from app.v15.hub_charts import (\n"
if needle not in text:
    raise SystemExit("hub_charts import missing")
insert = (
    needle
    + "    _aplicar_eixos_hub,\n"  # duplicate check - read file first
)
# Better: insert after hub_charts block
hub_end = "    _texto_posicao_barra,\n)\n"
if hub_end not in text:
    raise SystemExit("hub_charts block end missing")
new_imports = hub_end + (
    "from app.v15.nav_constants import (\n"
    "    _NIVEIS_TERRITORIO,\n"
    "    _NIVEL_TERRITORIO_CRE,\n"
    "    _NIVEL_TERRITORIO_ESC,\n"
    "    _NIVEL_TERRITORIO_ESTADO,\n"
    "    _NIVEL_TERRITORIO_MUN,\n"
    "    _SUBABA_DESEMPENHO,\n"
    "    _SUBABA_HUB,\n"
    "    _SUBABA_NACIONAL,\n"
    "    _SUBABA_PANORAMA,\n"
    "    _SUBABA_TERRITORIO,\n"
    "    _SUBABAS_GESTAO,\n"
    ")\n"
    "from app.v15.components import (\n"
    "    achado,\n"
    "    estatisticas_dict,\n"
    "    insight_box,\n"
    "    kpi_card,\n"
    "    nome_area,\n"
    "    nome_area_ext,\n"
    "    titulo_leve,\n"
    "    titulo_secao,\n"
    ")\n"
    "from app.v15.classifiers import (\n"
    "    classificar_participacao,\n"
    "    classificar_posicao,\n"
    "    classificar_tendencia,\n"
    ")\n"
    "from app.v15.charts_render import _chart, _chart_hub\n"
)
text = text.replace(hub_end, new_imports, 1)

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


remove_block(
    lambda ln: ln.strip() == "_CK = [0]",
    lambda ln: ln.startswith("def _estilizar_tabela("),
    "_chart",
)
remove_block(
    lambda ln: ln.startswith("def titulo_leve("),
    lambda ln: ln.startswith("def _fig_histogram_notas("),
    "components",
)
remove_block(
    lambda ln: ln.startswith("def classificar_tendencia("),
    lambda ln: ln.strip() == "# ============================================================",
    "classifiers",
)

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 5 patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
