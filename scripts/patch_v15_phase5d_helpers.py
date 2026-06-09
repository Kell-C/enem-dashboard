"""Fase 5d: importa page_helpers e remove blocos inline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

needle = "from app.v15.charts import detail as _v15_detail_charts\n"
if needle not in "".join(lines):
    raise SystemExit("phase 5c detail import missing")

insert = needle + (
    "from app.v15.page_helpers import (\n"
    "    _estilizar_tabela,\n"
    "    _faixa_concluintes_participantes,\n"
    "    _legenda_populacoes_secao_html,\n"
    "    _populacao_estadual_ano,\n"
    "    _secao_detalhe_ano_desempenho,\n"
    "    _normalizar_nome_municipio,\n"
    "    carregar_concluintes,\n"
    "    carregar_concluintes_municipio,\n"
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


remove_block(
    lambda ln: ln.startswith("def _secao_detalhe_ano_desempenho("),
    lambda ln: ln.startswith("def _fragment_camada_status("),
    "secao_detalhe",
)
remove_block(
    lambda ln: ln.startswith("def _legenda_inline("),
    lambda ln: ln.startswith("def _diagnostico_ranking_desempenho_uf("),
    "legenda_inline",
)
remove_block(
    lambda ln: ln.startswith("def _estilizar_tabela("),
    lambda ln: ln.startswith("def _kpi_titulo("),
    "estilizar_tabela",
)
remove_block(
    lambda ln: ln.startswith("def _legenda_populacoes_secao_html("),
    lambda ln: ln.startswith("def carregar_bases_nacionais("),
    "legenda_populacoes",
)
remove_block(
    lambda ln: ln.startswith("def _faixa_concluintes_participantes("),
    lambda ln: ln.startswith("def _html_funil_vertical("),
    "faixa_concluintes",
)
remove_block(
    lambda ln: ln.startswith("def _populacao_estadual_ano("),
    lambda ln: ln.startswith("def _totais_participacao_recorte("),
    "populacao_estadual",
)
remove_block(
    lambda ln: ln.startswith("def carregar_concluintes("),
    lambda ln: ln.startswith("inject_v15_styles("),
    "concluintes",
)

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 5d helpers patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
