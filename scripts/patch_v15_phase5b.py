"""Fase 5b: importa territory/ms/hub e remove blocos inline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
text = path.read_text(encoding="utf-8")

# paths: ARQUIVO_CRES / ARQUIVO_CONCLUINTES
text = text.replace(
    "from cres_loader import (\n"
    "    carregar_cres_escolas,\n"
    "    carregar_mapa_municipio_cre as _carregar_mapa_municipio_cre,\n"
    "    construir_mapa_cre_completo,\n"
    "    nome_cre_curto,\n"
    "    resolve_arquivo_cres,\n"
    ")\n\n"
    "ARQUIVO_CRES = os.getenv(\"ARQUIVO_CRES\") or resolve_arquivo_cres() or os.path.join(\n"
    "    os.path.dirname(__file__), \"cres.xlsx\"\n"
    ")\n\n"
    "# ------------------------------------------------------------\n"
    "# DADOS DE CONCLUINTES (3º ano) — estrutura para integração futura\n"
    "# ------------------------------------------------------------\n"
    "# Fonte: planilha Google Sheets com dados de estudantes do 3º ano\n"
    "# da rede estadual de MS (2019-2024).\n"
    "# Quando os dados estiverem disponíveis, atualize o caminho abaixo\n"
    "# ou descomente a função carregar_concluintes() e ajuste conforme\n"
    "# o formato real da planilha/arquivo local.\n"
    "ARQUIVO_CONCLUINTES: Optional[str] = os.getenv(\n"
    "    \"ARQUIVO_CONCLUINTES\",\n"
    "    os.path.join(os.path.dirname(__file__), \"data\", \"Concluintes EM 2019 a 2024.xlsx\"),\n"
    ")\n",
    "from cres_loader import (\n"
    "    carregar_cres_escolas,\n"
    "    carregar_mapa_municipio_cre as _carregar_mapa_municipio_cre,\n"
    "    construir_mapa_cre_completo,\n"
    "    nome_cre_curto,\n"
    "    resolve_arquivo_cres,\n"
    ")\n\n"
    "from app.v15.paths import ARQUIVO_CRES, ARQUIVO_CONCLUINTES\n\n"
    "# ------------------------------------------------------------\n"
    "# DADOS DE CONCLUINTES (3º ano) — estrutura para integração futura\n"
    "# ------------------------------------------------------------\n",
    1,
)

hub_end = "from app.v15.charts_render import _chart, _chart_hub\n"
if hub_end not in text:
    raise SystemExit("charts_render import missing")

new_imports = hub_end + (
    "from app.v15.participation import _enriquecer_participacao_taxas\n"
    "from app.v15.concluintes_data import carregar_concluintes_cre\n"
    "from app.v15.ms_enrich import (\n"
    "    _coluna_municipio,\n"
    "    _mapa_municipio_por_escola,\n"
    "    aplicar_cre_por_municipio,\n"
    "    carregar_cres,\n"
    "    carregar_mapa_municipio_cre,\n"
    "    enriquecer_ms,\n"
    "    normalizar_texto,\n"
    ")\n"
    "from app.v15 import territory_data as _v15_territory_data\n"
    "from app.v15.charts import hub as _v15_hub_charts\n"
    "\n"
    "for _v15_mod in (_v15_territory_data, _v15_hub_charts):\n"
    "    for _v15_name in dir(_v15_mod):\n"
    "        if _v15_name.startswith(\"_\") and not _v15_name.startswith(\"__\"):\n"
    "            globals()[_v15_name] = getattr(_v15_mod, _v15_name)\n"
    "del _v15_mod, _v15_name, _v15_territory_data, _v15_hub_charts\n"
)
text = text.replace(hub_end, new_imports, 1)

# _cor_posicao_terco now in hub_charts
text = text.replace(
    "    _classificar_cor_media_referencia,\n"
    "    _cores_ranking_presentes,\n",
    "    _classificar_cor_media_referencia,\n"
    "    _cor_posicao_terco,\n"
    "    _cores_ranking_presentes,\n",
    1,
)

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


# bottom-up removals
remove_block(
    lambda ln: ln.startswith("def _df_base_territorial("),
    lambda ln: ln.startswith("def _fragment_camada_status("),
    "territory_data",
)
remove_block(
    lambda ln: ln.startswith("def _enriquecer_participacao_taxas("),
    lambda ln: ln.startswith("def fig_media_area_deps("),
    "participation",
)
remove_block(
    lambda ln: ln.startswith("def _fig_combo_media_participacao("),
    lambda ln: ln.startswith("def fig_ms_participacao_desempenho("),
    "hub figures part 1",
)
remove_block(
    lambda ln: ln.startswith("def _df_dist_estadual_hub("),
    lambda ln: ln.startswith("def _fig_evolucao_medias_ms_br("),
    "hub figures part 2",
)
remove_block(
    lambda ln: ln.startswith("def _render_widget_grafico_hub("),
    lambda ln: ln.startswith("def _legenda_inline("),
    "hub widgets",
)
remove_block(
    lambda ln: ln.startswith("def carregar_cres("),
    lambda ln: ln.startswith("def _estilizar_tabela("),
    "ms_enrich",
)
remove_block(
    lambda ln: ln.startswith("def carregar_concluintes_cre("),
    lambda ln: ln.startswith("inject_v15_styles("),
    "concluintes_cre",
)
remove_block(
    lambda ln: ln.startswith("def _cor_posicao_terco("),
    lambda ln: ln.startswith("def _legenda_populacoes_secao_html("),
    "_cor_posicao_terco",
)

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 5b patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
