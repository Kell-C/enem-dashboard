"""
==========================================================================
PAINEL ANALÍTICO DO ENEM 2019-2024 — ESCOLAS ESTADUAIS
Versão 15.0 — Dados agregados (parquet local ou Supabase), pronto para
publicação no Streamlit Community Cloud. Mantém layout e funcionalidades
do v14_26mai14h33.
==========================================================================
"""

# Bump ao alterar layout/hover do hub — força refresh de widgets Plotly.
from app.v15.constants import HUB_BUILD_ID

import base64
import re as _re
import html as _html
import os
from os.path import exists
import warnings
from typing import Optional

import unicodedata
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from viz.chart_layout import (
    CHART_H_BOX,
    CHART_H_BOX_WIDE,
    CHART_H_EVOLUCAO,
    CHART_H_HIST,
    CHART_H_HIST_GRID,
    CHART_H_HIST_ROW,
    CHART_H_HUB,
    CHART_H_HUB_DELTA_ROW,
    CHART_H_HUB_EVOL,
    CHART_H_HUB_RANK,
    PLOTLY_HUB_CONFIG,
    legenda_hub_interna,
    margem_hub,
    CHART_H_PARTICIPACAO,
    CHART_H_RANKING,
    CHART_H_STANDARD,
    hover_padrao,
    legenda_inferior,
    margem_detalhe,
    texto_hover_box,
)

from dados_agregados_loader import (
    carregar_notas_individuais,
    carregar_todas_tabelas,
    filtrar_distribuicao,
    filtrar_notas_individuais,
    get_data_source,
    get_pasta_agregados,
    histograma_area_ano,
    presentes_filt_estadual_ano,
    inscritos_estadual_ms,
    inscritos_por_escola_2024,
    linha_distribuicao,
    linha_escola_2024,
    media_ms_area_ano,
    medias_referencia_por_ano,
    medias_br_serie_por_area,
    media_nacional_ponderada,
    serie_media_nacional_dep,
    anos_com_desempenho_uf,
    tabela_ranking_uf,
    notas_area,
    reconstruir_bases_nacionais,
    reconstruir_escolas_2024_ms,
    participacao_ms_por_ano,
    reconstruir_ms_enriquecido,
    reconstruir_participacao_ms,
    stats_box_quantis,
    anos_com_notas_individuais,
    tem_notas_individuais_ano,
    verificar_dados_disponiveis,
)

from app.v15.theme import *  # noqa: F403
from app.v15.styles import inject_v15_filter_styles, inject_v15_styles
from app.v15.formatting import fmt_int, fmt_float, fmt_pct, fmt_delta, _safe_int_val, _pct_taxa
from app.v15.ui import _render_html, _logo_data_uri
from app.v15.plotly_theme import aplicar_tema, _hex_rgba, _legenda_padrao
from app.v15.boxplots import (
    _add_box,
    _add_box_series,
    _add_box_stats,
    _add_scatter_notas,
    _anotacao_hub,
    _aplicar_hover_hub,
    _finalizar_boxplot,
    _finalizar_grafico,
    _hex_to_rgba,
    _preparar_hover_fig,
    _range_y_box_stats,
    _stats_box,
)
from app.v15.hub_charts import (
    _aplicar_eixos_hub,
    _aplicar_legenda_interna_combo_ms,
    _altura_hub_ranking,
    _classificar_cor_media_referencia,
    _cor_posicao_terco,
    _cores_ranking_presentes,
    _fechar_fig_hub,
    _legenda_fig,
    _margem_hub,
    _texto_posicao_barra,
)
from app.v15.nav_constants import (
    _NIVEIS_TERRITORIO,
    _NIVEL_TERRITORIO_CRE,
    _NIVEL_TERRITORIO_ESC,
    _NIVEL_TERRITORIO_ESTADO,
    _NIVEL_TERRITORIO_MUN,
    _SUBABA_DESEMPENHO,
    _SUBABA_HUB,
    _SUBABA_NACIONAL,
    _SUBABA_PANORAMA,
    _SUBABA_TERRITORIO,
    _SUBABAS_GESTAO,
)
from app.v15.components import (
    achado,
    estatisticas_dict,
    insight_box,
    kpi_card,
    nome_area,
    nome_area_ext,
    titulo_leve,
    titulo_secao,
)
from app.v15.classifiers import (
    classificar_participacao,
    classificar_posicao,
    classificar_tendencia,
)
from app.v15.charts_render import _chart, _chart_hub
from app.v15.participation import _enriquecer_participacao_taxas
from app.v15.concluintes_data import carregar_concluintes_cre
from app.v15.ms_enrich import (
    _coluna_municipio,
    _mapa_municipio_por_escola,
    aplicar_cre_por_municipio,
    carregar_cres,
    carregar_mapa_municipio_cre,
    enriquecer_ms,
    normalizar_texto,
)
from app.v15 import territory_data as _v15_territory_data
from app.v15.charts import hub as _v15_hub_charts

for _v15_mod in (_v15_territory_data, _v15_hub_charts):
    for _v15_name in dir(_v15_mod):
        if _v15_name.startswith("_") and not _v15_name.startswith("__"):
            globals()[_v15_name] = getattr(_v15_mod, _v15_name)
del _v15_mod, _v15_name, _v15_territory_data, _v15_hub_charts
from app.v15.charts import detail as _v15_detail_charts
from app.v15.page_helpers import (
    _estilizar_tabela,
    _faixa_concluintes_participantes,
    _legenda_populacoes_secao_html,
    _populacao_estadual_ano,
    _secao_detalhe_ano_desempenho,
    _normalizar_nome_municipio,
    carregar_concluintes,
    carregar_concluintes_municipio,
)

for _v15_name in dir(_v15_detail_charts):
    if _v15_name.startswith("__"):
        continue
    globals()[_v15_name] = getattr(_v15_detail_charts, _v15_name)
del _v15_name, _v15_detail_charts

try:
    from dados_agregados_loader import (
        filtrar_participacao_cre,
        filtrar_participacao_municipio,
    )
except ImportError:
    def filtrar_participacao_cre(
        tabelas: dict,
        *,
        anos: list[int] | None = None,
        dependencia: str | None = None,
    ) -> pd.DataFrame:
        df = tabelas.get("participacao_cre", pd.DataFrame())
        if df.empty:
            return df
        out = df.copy()
        if anos:
            out = out[out["ano"].isin(anos)]
        if dependencia:
            out = out[out["dependencia"] == dependencia]
        return out

    def filtrar_participacao_municipio(
        tabelas: dict,
        *,
        anos: list[int] | None = None,
        dependencia: str | None = None,
    ) -> pd.DataFrame:
        df = tabelas.get("municipios", pd.DataFrame())
        if df.empty:
            return df
        out = df.copy()
        if anos:
            out = out[out["ano"].isin(anos)]
        if dependencia:
            out = out[out["dependencia"] == dependencia]
        return out

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Painel ENEM MS",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_v15_filter_styles()


# ------------------------------------------------------------
# FONTE DE DADOS — agregados (gerar_dados_agregados.py)
# DATA_SOURCE=local  → parquet em PASTA_AGREGADOS
# DATA_SOURCE=supabase → PostgreSQL (secrets ou env vars)
# ------------------------------------------------------------
PASTA_AGREGADOS = get_pasta_agregados()

# Cadastro CRE (opcional — enriquece nomes quando disponível localmente)
from cres_loader import (
    carregar_cres_escolas,
    carregar_mapa_municipio_cre as _carregar_mapa_municipio_cre,
    construir_mapa_cre_completo,
    nome_cre_curto,
    resolve_arquivo_cres,
)

from app.v15.paths import ARQUIVO_CRES, ARQUIVO_CONCLUINTES

# ------------------------------------------------------------
# DADOS DE CONCLUINTES (3º ano) — estrutura para integração futura
# ------------------------------------------------------------


inject_v15_styles()


def _totais_participacao_recorte(
    tabelas: dict,
    anos_sel: list,
    dependencia: str = "Estadual",
) -> dict[str, Optional[int | float]]:
    """Soma inscritos, concluintes e presentes_filt no recorte (participacao_ano)."""
    df_part = tabelas.get("participacao_ano", pd.DataFrame())
    vazio = {
        "inscritos": None,
        "concluintes": None,
        "presentes_filt": None,
        "tx_part_efetiva": None,
        "tx_part_inscritos": None,
    }
    if df_part.empty or not anos_sel:
        return vazio
    anos_int = [int(a) for a in anos_sel]
    sub = df_part[
        (df_part["ano"].isin(anos_int)) & (df_part["dependencia"] == dependencia)
    ]
    if sub.empty:
        return vazio
    n_insc = int(sub["inscritos"].fillna(0).sum()) if "inscritos" in sub.columns else None
    n_conc = int(sub["concluintes"].fillna(0).sum()) if "concluintes" in sub.columns else None
    n_pres = (
        int(sub["presentes_filt"].fillna(0).sum())
        if "presentes_filt" in sub.columns else None
    )
    if n_conc is not None and n_conc <= 0:
        n_conc = None
    if n_insc is not None and n_insc <= 0:
        n_insc = None
    if n_pres is not None and n_pres <= 0:
        n_pres = None
    tx_efet = (
        round(100 * n_pres / n_conc, 1)
        if n_conc and n_pres else None
    )
    tx_insc_pres = (
        round(100 * n_pres / n_insc, 1)
        if n_insc and n_pres else None
    )
    tx_insc_conc = (
        round(100 * n_insc / n_conc, 1)
        if n_conc and n_insc else None
    )
    return {
        "inscritos": n_insc,
        "concluintes": n_conc,
        "presentes_filt": n_pres,
        "tx_part_efetiva": tx_efet,
        "tx_part_inscritos": tx_insc_pres,
        "tx_inscricao": tx_insc_conc,
    }


def _serie_tx_part_efetiva_br(
    tabelas: dict,
    anos_sel: list,
    dependencia: str = "Estadual",
) -> pd.Series:
    """Taxa de participação efetiva nacional (soma UFs, rede estadual)."""
    df = tabelas.get("participacao_uf", pd.DataFrame())
    if df.empty or not anos_sel:
        return pd.Series(dtype=float)
    out: dict[int, float] = {}
    for ano in anos_sel:
        sub = df[
            (df["ano"] == int(ano)) & (df["dependencia"] == dependencia)
        ]
        if sub.empty:
            continue
        pres = pd.to_numeric(
            sub.get("presentes_filt", sub.get("presentes")),
            errors="coerce",
        ).fillna(0).sum()
        conc = (
            pd.to_numeric(sub["concluintes"], errors="coerce").fillna(0).sum()
            if "concluintes" in sub.columns else 0
        )
        if conc > 0:
            out[int(ano)] = round(100 * pres / conc, 1)
        else:
            insc = pd.to_numeric(sub["inscritos"], errors="coerce").fillna(0).sum()
            if insc > 0:
                out[int(ano)] = round(100 * pres / insc, 1)
    return pd.Series(out).sort_index()


def _enriquecer_diag_participacao(diag: dict, tabelas: dict, anos_sel: list) -> dict:
    """Inclui concluintes, presentes efetivos, taxas e séries anuais no diagnóstico."""
    tot = _totais_participacao_recorte(tabelas, anos_sel, "Estadual")
    diag["n_concluintes"] = tot["concluintes"]
    diag["n_presentes_filt"] = tot["presentes_filt"] or diag.get("n_part")
    diag["tx_part_efetiva"] = tot["tx_part_efetiva"]
    diag["tx_part_inscritos"] = tot["tx_part_inscritos"]
    diag["tx_inscricao"] = tot["tx_inscricao"]
    if tot["tx_part_efetiva"] is not None:
        diag["tx_part"] = tot["tx_part_efetiva"]
    if tot["inscritos"] is not None:
        diag["n_inscritos"] = tot["inscritos"]

    part_serie = participacao_ms_por_ano(tabelas, list(anos_sel), "Estadual")
    if not part_serie.empty:
        diag["serie_tx_part_efetiva"] = (
            part_serie.set_index(part_serie["ano"].astype(int))["Tx_Part_Efetiva"]
        )
        diag["serie_tx_inscricao"] = (
            part_serie.set_index(part_serie["ano"].astype(int))["Tx_Inscrição"]
        )

    br_por_ano: dict[int, float] = {}
    for ano in anos_sel:
        refs = medias_referencia_por_ano(tabelas, int(ano))
        mg = refs.get("MEDIA_GERAL", {})
        br = mg.get("br")
        if br is not None and pd.notna(br):
            br_por_ano[int(ano)] = float(br)
    if br_por_ano:
        diag["serie_media_br"] = pd.Series(br_por_ano).sort_index()

    serie_br_part = _serie_tx_part_efetiva_br(tabelas, anos_sel)
    if not serie_br_part.empty:
        diag["serie_tx_part_efetiva_br"] = serie_br_part

    serie_ms = diag.get("serie_medias", pd.Series(dtype=float))
    serie_br = diag.get("serie_media_br", pd.Series(dtype=float))
    if not serie_ms.empty and not serie_br.empty:
        ms_map = {int(k): float(v) for k, v in serie_ms.items() if pd.notna(v)}
        br_map = {int(k): float(v) for k, v in serie_br.items() if pd.notna(v)}
        diag["serie_delta_br"] = pd.Series(
            {a: ms_map[a] - br_map[a] for a in sorted(set(ms_map) & set(br_map))},
        ).sort_index()
    return diag


def _html_funil_vertical(diag: dict, periodo: str) -> str:
    """Funil em coluna com barras de proporção — painel lateral compacto."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    n_insc = diag.get("n_inscritos")
    tx_efet = diag.get("tx_part_efetiva")
    tx_insc = diag.get("tx_inscricao")
    if not n_conc or not n_pres:
        return (
            f'<div class="widget-card"><div class="widget-head">Participação · '
            f'{_html.escape(periodo)}</div><div class="widget-body">'
            f'<div class="insight" style="margin:0">'
            f'<b>{fmt_int(n_pres)}</b> participantes efetivos. '
            f'Concluintes indisponíveis.</div></div></div>'
        )

    status_efet = classificar_participacao(tx_efet if tx_efet is not None else 0)
    classe_efet = status_efet if status_efet in ("positivo", "atencao", "critico") else ""
    classe_insc = ""
    if tx_insc is not None:
        classe_insc = (
            "positivo" if tx_insc >= 70
            else ("atencao" if tx_insc >= 50 else "critico")
        )

    pct_conc = 100.0
    pct_insc = min(100.0, float(tx_insc)) if tx_insc is not None else 0.0
    pct_efet = min(100.0, float(tx_efet)) if tx_efet is not None else 0.0

    rows = [
        (
            f'<div class="funil-v-row">'
            f'<div class="fv-top"><span class="fv-lbl">Concluintes do Ensino Médio</span>'
            f'<span class="fv-val">{fmt_int(n_conc)}</span></div>'
            f'<div class="fv-bar"><div class="fv-fill azul" style="width:{pct_conc:.0f}%"></div></div>'
            f'</div>'
        ),
    ]
    if n_insc:
        tx_html = (
            f'<div class="fv-tx insc {classe_insc}">{fmt_pct(tx_insc)} dos concluintes</div>'
            if tx_insc is not None else ""
        )
        rows.append(
            f'<div class="funil-v-row">'
            f'<div class="fv-top"><span class="fv-lbl">Inscritos ENEM</span>'
            f'<span class="fv-val">{fmt_int(n_insc)}</span></div>'
            f'{tx_html}'
            f'<div class="fv-bar"><div class="fv-fill laranja" style="width:{pct_insc:.0f}%"></div></div>'
            f'</div>'
        )
    rows.append(
        f'<div class="funil-v-row">'
        f'<div class="fv-top"><span class="fv-lbl">Participantes efetivos</span>'
        f'<span class="fv-val">{fmt_int(n_pres)}</span></div>'
        f'<div class="fv-tx efet {classe_efet}">{fmt_pct(tx_efet)} dos concluintes</div>'
        f'<div class="fv-bar"><div class="fv-fill verde" style="width:{pct_efet:.0f}%"></div></div>'
        f'</div>'
    )
    return (
        f'<div class="widget-card"><div class="widget-head">Participação · '
        f'{_html.escape(periodo)}</div><div class="widget-body">'
        f'{"".join(rows)}</div></div>'
    )


def _html_funil_kpi_inline(diag: dict, periodo: str) -> str:
    """Participação no formato KPI: uma linha por etapa, barra + % sobrepostos."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    n_insc = diag.get("n_inscritos")
    tx_efet = diag.get("tx_part_efetiva")
    tx_insc = diag.get("tx_inscricao")
    if not n_conc or not n_pres:
        return (
            f'<div class="kpi-claro kpi-funil-inline">'
            f'<span class="kpi-claro-lbl">Participação · {_html.escape(periodo)}</span>'
            f'<span class="kpi-claro-val" style="font-size:0.95rem">{fmt_int(n_pres)}</span>'
            f'<span class="kpi-claro-sub">participantes efetivos</span></div>'
        )

    pct_insc = min(100.0, float(tx_insc)) if tx_insc is not None else 0.0
    pct_efet = min(100.0, float(tx_efet)) if tx_efet is not None else 0.0

    def _barra(pct: float, cor: str, pct_label: str | None) -> str:
        w = max(min(pct, 100.0), 0.0)
        if pct_label and w >= 14:
            inner = f'<span class="fk-pct">{_html.escape(pct_label)}</span>'
            outer = ""
        elif pct_label:
            inner = ""
            outer = f'<span class="fk-pct-out">{_html.escape(pct_label)}</span>'
        else:
            inner = ""
            outer = ""
        return (
            f'<span class="fk-track">'
            f'<span class="fk-fill {cor}" style="width:{w:.0f}%">{inner}</span>'
            f'{outer}</span>'
        )

    def _linha(lbl: str, val: str, pct: float, cor: str, pct_label: str | None) -> str:
        return (
            f'<div class="fk-line">'
            f'<span class="fk-l">{lbl}</span>'
            f'<span class="fk-n">{val}</span>'
            f'{_barra(pct, cor, pct_label)}'
            f'</div>'
        )

    linhas = [_linha("Concluintes", fmt_int(n_conc), 100.0, "azul", None)]
    if n_insc:
        linhas.append(
            _linha(
                "Inscritos", fmt_int(n_insc), pct_insc, "laranja",
                fmt_pct(tx_insc) if tx_insc is not None else None,
            )
        )
    linhas.append(
        _linha(
            "Participação efetiva", fmt_int(n_pres), pct_efet, "verde",
            fmt_pct(tx_efet) if tx_efet is not None else None,
        )
    )

    return (
        f'<div class="kpi-claro kpi-funil-inline">'
        f'<span class="kpi-claro-lbl">Participação · {_html.escape(periodo)}</span>'
        f'<div class="fk-lines">{"".join(linhas)}</div>'
        f'</div>'
    )


def _html_funil_estreito(diag: dict, periodo: str) -> str:
    """Funil lateral compacto (coluna estreita ao lado do ranking nacional)."""
    html = _html_funil_vertical(diag, periodo)
    return html.replace('class="widget-card"', 'class="widget-card funil-estreito"', 1)


def _render_funil_widget(diag: dict, periodo: str, *, estreito: bool = False) -> None:
    if estreito:
        _render_html(_html_funil_estreito(diag, periodo))
    else:
        _render_html(_html_funil_vertical(diag, periodo))


def carregar_bases_nacionais() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bases nacionais sintéticas (UF) — operação pesada (~20s); cache único bruta+filtrada."""
    if not verificar_dados_disponiveis():
        st.error(
            f"Dados agregados não encontrados. Configure PASTA_AGREGADOS "
            f"({PASTA_AGREGADOS}) ou DATA_SOURCE=supabase com credenciais válidas. "
            f"Gere os arquivos com: python gerar_dados_agregados.py"
        )
        st.stop()
    tabelas = carregar_todas_tabelas()
    df_bruta, df_filt = reconstruir_bases_nacionais(tabelas, ANOS_DISPONIVEIS)
    if df_bruta.empty:
        st.error("Nenhum dado agregado nacional carregado. Verifique os arquivos parquet.")
        st.stop()
    return df_bruta, df_filt.reset_index(drop=True)


def carregar_base_bruta() -> pd.DataFrame:
    return carregar_bases_nacionais()[0]


def carregar_base_filtrada(df_bruta: pd.DataFrame) -> pd.DataFrame:
    return carregar_bases_nacionais()[1]


@st.cache_data(show_spinner=False, ttl=3600)
def _kpi_titulo(indicador: str) -> str:
    """Título padronizado dos KPIs do cabeçalho."""
    return f"{indicador} · rede estadual"


def _kpi_claro_html(
    rotulo: str,
    valor: str,
    sub: str = "",
    status: str = "",
    *,
    extra_class: str = "",
) -> str:
    status_validos = {"positivo", "atencao", "critico"}
    cls = f"kpi-claro {status}" if status in status_validos else "kpi-claro"
    if extra_class:
        cls = f"{cls} {extra_class}"
    return (
        f'<div class="{cls}">'
        f'<span class="kpi-claro-lbl">{_html.escape(rotulo)}</span>'
        f'<span class="kpi-claro-val">{_html.escape(valor)}</span>'
        f'<span class="kpi-claro-sub">{_html.escape(sub)}</span>'
        f'</div>'
    )


def _kpi_strip_items(diag: dict, periodo: str) -> list[str]:
    """Itens HTML dos KPIs compactos (padrão: título · escopo | valor | contexto · período)."""
    status_var = classificar_tendencia(diag.get("variacao_inicio_fim", 0))
    pos_recente = diag.get("pos_ms_recente")
    total_recente = diag.get("total_ufs_recente", 0)
    pos_hist = diag.get("pos_ms")
    total_hist = diag.get("total_ufs", 0)
    ano_inicio = diag.get("ano_inicio")
    ano_fim = diag.get("ano_fim")
    ano_ref_pos = diag.get("ano_referencia_pos") or ano_fim
    sub_variacao = (
        f"{ano_inicio} → {ano_fim}"
        if ano_inicio is not None and ano_fim is not None
        else periodo
    )

    itens = [
        _kpi_claro_html(
            _kpi_titulo("Média geral"),
            fmt_float(diag["media_estadual_ms"]),
            f"Média ponderada · {periodo}",
            extra_class="kpi-media",
        ),
        _kpi_claro_html(
            _kpi_titulo("Variação da média"),
            fmt_delta(diag.get("variacao_inicio_fim", 0)),
            sub_variacao,
            status=status_var,
            extra_class="kpi-variacao",
        ),
    ]
    if pos_recente:
        itens.append(
            _kpi_claro_html(
                _kpi_titulo("Posição nacional"),
                f"{pos_recente}º de {total_recente}",
                (
                    f"{ano_ref_pos} · ranking entre UFs"
                    if ano_ref_pos is not None
                    else f"Ranking entre UFs · {periodo}"
                ),
                status=classificar_posicao(pos_recente, total_recente),
                extra_class="kpi-posicao",
            )
        )
    elif pos_hist:
        itens.append(
            _kpi_claro_html(
                _kpi_titulo("Posição nacional"),
                f"{pos_hist}º de {total_hist}",
                f"Ranking entre UFs · {periodo}",
                status=classificar_posicao(pos_hist, total_hist),
                extra_class="kpi-posicao",
            )
        )
    else:
        itens.append(
            _kpi_claro_html(
                _kpi_titulo("Posição nacional"),
                "—",
                "Sem dados no recorte",
                extra_class="kpi-posicao",
            )
        )

    diff_br = diag.get("diff_vs_nacional", float("nan"))
    status_diff = ""
    if pd.notna(diff_br):
        status_diff = "positivo" if diff_br >= 0 else "critico"
    itens.append(
        _kpi_claro_html(
            _kpi_titulo("Diferença vs Brasil"),
            fmt_delta(diff_br) if pd.notna(diff_br) else "—",
            f"Média ponderada · {periodo}",
            status=status_diff,
            extra_class="kpi-delta-br",
        )
    )
    return itens


def _html_faixa_kpis(diag: dict, periodo: str, *, no_cabecalho: bool = False) -> str:
    """HTML dos KPIs + funil inline (opcional)."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    funil = (
        _html_funil_kpi_inline(diag, periodo)
        if n_conc and n_pres else ""
    )
    itens = "".join(_kpi_strip_items(diag, periodo))
    if no_cabecalho:
        return f'<div class="cab-claro-kpis">{itens}{funil}</div>'
    return (
        f'<div class="kpi-funil-row kpi-strip-tight">{itens}{funil}</div>'
    )


def _html_kpi_strip(diag: dict, periodo: str) -> str:
    """Faixa de KPIs em cards brancos abaixo do cabeçalho."""
    return (
        f'<div class="kpi-strip-claro kpi-strip-tight">'
        f'{"".join(_kpi_strip_items(diag, periodo))}</div>'
    )


def _html_cabecalho_com_kpis(diag: dict, periodo: str) -> str:
    """Cabeçalho com logo/título à esquerda e KPIs à direita."""
    logo = _logo_data_uri()
    img = (
        f'<img class="cab-claro-logo" src="{logo}" alt="Governo de MS — SED" />'
        if logo else ""
    )
    kpis = _html_faixa_kpis(diag, periodo, no_cabecalho=True)
    return (
        f'<div class="cab-claro cab-claro--com-kpis">'
        f'<div class="cab-claro-row">'
        f'<div class="cab-claro-brand">{img}'
        f'<div class="cab-claro-text"><h1>Painel ENEM MS</h1>'
        f'<p>Desempenho e participação da rede estadual · 2019–2025</p>'
        f'</div></div>'
        f'{kpis}'
        f'</div></div>'
    )


def _render_cabecalho_claro() -> None:
    """Cabeçalho branco — logo e título (sem KPIs)."""
    logo = _logo_data_uri()
    img = (
        f'<img class="cab-claro-logo" src="{logo}" alt="Governo de MS — SED" />'
        if logo else ""
    )
    _render_html(
        f'<div class="cab-claro"><div class="cab-claro-row">{img}'
        f'<div class="cab-claro-text"><h1>Painel ENEM MS</h1>'
        f'<p>Desempenho e participação da rede estadual · 2019–2025</p>'
        f'</div></div></div>'
    )


def _render_cabecalho_com_kpis(diag: dict, periodo: str) -> None:
    """Cabeçalho integrado: marca à esquerda, KPIs à direita."""
    _render_html(_html_cabecalho_com_kpis(diag, periodo))


def _html_populacao_referencia_resumo() -> str:
    """Resumo inline da população de referência (substitui aba Metodologia no topo)."""
    return (
        '<div class="ref-pop-bar">'
        '<span class="ref-pop-tag">População de referência</span>'
        '<span class="ref-pop-item">Presentes nos dois dias de prova; '
        'Concluintes do Ensino Médio na rede estadual</span>'
        '<span class="ref-pop-sep">·</span>'
        '<span class="ref-pop-item"><strong>2019–2023</strong> concluintes do Ensino Médio · '
        '<strong>2024</strong> inscritos na rede estadual</span>'
        '<span class="ref-pop-sep">·</span>'
        '<span class="ref-pop-item"><strong>Taxa de participação efetiva</strong> = presentes ÷ concluintes</span>'
        '</div>'
    )


def _render_populacao_referencia_compacta() -> None:
    _render_html(_html_populacao_referencia_resumo())


def _render_faixa_kpis_claro(diag: dict, periodo: str) -> None:
    """KPIs + card de participação na mesma faixa (legado / uso externo)."""
    _render_html(_html_faixa_kpis(diag, periodo, no_cabecalho=False))


def _diagnostico_ranking_desempenho_uf(
    tabelas: dict,
    anos_sel: list,
) -> dict:
    """Ranking e média BR via desempenho_uf.parquet (evita ~4,6M linhas sintéticas)."""
    out = {
        "media_estadual_br": np.nan,
        "ranking_ufs": pd.Series(dtype=float),
        "pos_ms": None,
        "total_ufs": 0,
        "pos_ms_recente": None,
        "total_ufs_recente": 0,
        "ano_referencia_pos": None,
        "ranking_ufs_recente": pd.Series(dtype=float),
        "media_br_ano_recente": np.nan,
    }
    df_desemp = tabelas.get("desempenho_uf", pd.DataFrame())
    if df_desemp.empty or not anos_sel:
        return out
    anos_int = [int(a) for a in anos_sel]
    sub = df_desemp[
        (df_desemp["dependencia"] == "Estadual") & (df_desemp["ano"].isin(anos_int))
    ].copy()
    if sub.empty:
        return out
    col_media = "media_media_geral" if "media_media_geral" in sub.columns else "media_geral"
    pesos = sub["estudantes"].fillna(0).astype(float)
    if pesos.sum() > 0:
        out["media_estadual_br"] = float(
            np.average(sub[col_media], weights=pesos)
        )
    def _media_pond(g):
        w = g["estudantes"].fillna(0).astype(float)
        return np.average(g[col_media], weights=w) if w.sum() > 0 else np.nan

    ranking = (
        sub.groupby("uf", observed=True)
        .apply(_media_pond)
        .dropna()
        .round(2)
        .sort_values(ascending=False)
    )
    ranking.index = ranking.index.astype(str).str.upper()
    ranking = ranking[ranking.index.str.len() == 2]
    out["ranking_ufs"] = ranking
    out["total_ufs"] = int(len(ranking))
    if "MS" in ranking.index:
        out["pos_ms"] = int(list(ranking.index).index("MS")) + 1
    ano_ref = max(anos_int)
    out["ano_referencia_pos"] = ano_ref
    sub_ano = sub[sub["ano"] == ano_ref]
    if not sub_ano.empty:
        ranking_ano = (
            sub_ano.set_index(sub_ano["uf"].astype(str).str.upper())[col_media]
            .dropna()
            .round(2)
            .sort_values(ascending=False)
        )
        ranking_ano = ranking_ano[ranking_ano.index.str.len() == 2]
        out["ranking_ufs_recente"] = ranking_ano
        out["total_ufs_recente"] = int(len(ranking_ano))
        if "MS" in ranking_ano.index:
            out["pos_ms_recente"] = int(list(ranking_ano.index).index("MS")) + 1
        refs = medias_referencia_por_ano(tabelas, ano_ref)
        mg = refs.get("MEDIA_GERAL", {})
        if mg.get("br") is not None and pd.notna(mg["br"]):
            out["media_br_ano_recente"] = float(mg["br"])
    return out


def _medias_periodo_kpi_rede_estadual(
    tabelas: dict,
    anos_sel: list[int],
    df_est: pd.DataFrame,
) -> dict[str, float]:
    """Médias MS/BR do período via referencias.parquet (mesma base dos gráficos Δ).

    População: presentes 2 dias, não eliminados, rede estadual. Ponderação
    anual pelo nº de participantes MS em cada ano.
    """
    if not tabelas or not anos_sel:
        return {}
    ms_v, br_v, pesos = [], [], []
    for ano in anos_sel:
        refs = medias_referencia_por_ano(tabelas, int(ano))
        mg = refs.get("MEDIA_GERAL", {})
        ms, br = mg.get("ms"), mg.get("br")
        if ms is None or br is None or pd.isna(ms) or pd.isna(br):
            continue
        n = int((df_est["NU_ANO"] == int(ano)).sum()) if not df_est.empty else 0
        if n <= 0:
            df_part = tabelas.get("participacao_ano", pd.DataFrame())
            if not df_part.empty:
                hit = df_part[
                    (df_part["ano"] == int(ano))
                    & (df_part["dependencia"] == "Estadual")
                ]
                if not hit.empty:
                    n = _safe_int_val(
                        hit.iloc[0].get("presentes_filt", hit.iloc[0].get("presentes")),
                    )
        if n <= 0:
            n = 1
        ms_v.append(float(ms))
        br_v.append(float(br))
        pesos.append(n)
    if not pesos or sum(pesos) <= 0:
        return {}
    media_ms = float(np.average(ms_v, weights=pesos))
    media_br = float(np.average(br_v, weights=pesos))
    return {
        "media_ms": media_ms,
        "media_br": media_br,
        "diff": media_ms - media_br,
    }


def diagnostico_estadual(
    df_filt_ms,
    df_bruta_ms,
    df_br_filt=None,
    *,
    tabelas: dict | None = None,
    anos_sel: list | None = None,
) -> dict:
    d = {}
    df_est = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    df_est_bruta = df_bruta_ms[df_bruta_ms["DEP_ADM"] == "Estadual"]
    usar_agregado = (
        (df_br_filt is None or df_br_filt.empty)
        and tabelas is not None
        and anos_sel
    )
    if usar_agregado:
        df_est_br = pd.DataFrame()
        rank = _diagnostico_ranking_desempenho_uf(tabelas, anos_sel)
    else:
        df_est_br = df_br_filt[df_br_filt["DEP_ADM"] == "Estadual"]
        rank = None

    # n_inscritos: soma participacao_ano.inscritos (ajustado em main via inscritos_estadual_ms)
    d["n_inscritos"] = len(df_est_bruta)
    d["n_part"] = len(df_est)
    d["tx_part"] = round(100 * d["n_part"] / d["n_inscritos"],
                         1) if d["n_inscritos"] else 0.0
    # Média ponderada pelo nº de participantes de cada ano no recorte
    # (cada estudante sintético herda a média anual; .mean() = ponderação).
    d["media_estadual_ms"] = float(
        df_est["MEDIA_GERAL"].mean()) if not df_est.empty else np.nan
    if rank is not None:
        d["media_estadual_br"] = rank["media_estadual_br"]
    else:
        d["media_estadual_br"] = float(
            df_est_br["MEDIA_GERAL"].mean()) if not df_est_br.empty else np.nan

    # KPI Δ: alinhar média BR à referencias.parquet (mesma fonte dos gráficos).
    # MS permanece a média direta dos participantes MS no recorte.
    if usar_agregado and anos_sel:
        kpi_ref = _medias_periodo_kpi_rede_estadual(tabelas, list(anos_sel), df_est)
        if kpi_ref:
            d["media_estadual_br"] = kpi_ref["media_br"]
    d["diff_vs_nacional"] = (
        d["media_estadual_ms"] - d["media_estadual_br"]
        if pd.notna(d["media_estadual_ms"]) and pd.notna(d["media_estadual_br"])
        else np.nan
    )

    serie = df_est.groupby("NU_ANO")["MEDIA_GERAL"].mean().round(2)
    d["media_ms_ano_recente"] = np.nan
    d["media_br_ano_recente"] = np.nan
    if not serie.empty:
        ano_recente = int(serie.index.max())
        d["media_ms_ano_recente"] = float(serie.loc[ano_recente])
        if rank is not None:
            d["media_br_ano_recente"] = rank.get("media_br_ano_recente", np.nan)
        elif not df_est_br.empty and "NU_ANO" in df_est_br.columns:
            br_ano = df_est_br[df_est_br["NU_ANO"] == ano_recente]
            if not br_ano.empty:
                d["media_br_ano_recente"] = float(br_ano["MEDIA_GERAL"].mean())
    d["serie_medias"] = serie
    if len(serie) >= 2:
        d["variacao_inicio_fim"] = float(serie.iloc[-1] - serie.iloc[0])
        d["ano_inicio"] = int(serie.index[0])
        d["ano_fim"] = int(serie.index[-1])
        d["melhor_ano"] = int(serie.idxmax())
        d["pior_ano"] = int(serie.idxmin())
        d["valor_melhor_ano"] = float(serie.max())
        d["valor_pior_ano"] = float(serie.min())
    else:
        d["variacao_inicio_fim"] = np.nan

    medias_areas = {}
    for c in COLS_NOTAS:
        v = df_est[c].mean()
        if pd.notna(v):
            medias_areas[c] = float(v)
    d["medias_areas"] = medias_areas
    if medias_areas:
        d["area_mais_forte"] = max(medias_areas, key=medias_areas.get)
        d["area_mais_fraca"] = min(medias_areas, key=medias_areas.get)

    if rank is not None:
        d["ranking_ufs"] = rank["ranking_ufs"]
        d["pos_ms"] = rank["pos_ms"]
        d["total_ufs"] = rank["total_ufs"]
        d["pos_ms_recente"] = rank["pos_ms_recente"]
        d["total_ufs_recente"] = rank["total_ufs_recente"]
        d["ano_referencia_pos"] = rank["ano_referencia_pos"]
        d["ranking_ufs_recente"] = rank["ranking_ufs_recente"]
    else:
        col_uf = "SG_UF_ESC" if "SG_UF_ESC" in df_br_filt.columns else "SG_UF_PROVA"
        ranking_ufs = (df_est_br.groupby(col_uf)["MEDIA_GERAL"].mean()
                       .dropna().round(2).sort_values(ascending=False))
        ranking_ufs = ranking_ufs[ranking_ufs.index.to_series().str.len() == 2]
        d["ranking_ufs"] = ranking_ufs
        if "MS" in ranking_ufs.index:
            d["pos_ms"] = int(list(ranking_ufs.index).index("MS")) + 1
            d["total_ufs"] = int(len(ranking_ufs))
        else:
            d["pos_ms"] = None
            d["total_ufs"] = int(len(ranking_ufs))
        d["pos_ms_recente"] = None
        d["total_ufs_recente"] = 0
        d["ano_referencia_pos"] = None
        d["ranking_ufs_recente"] = pd.Series(dtype=float)
        if not df_est_br.empty and "NU_ANO" in df_est_br.columns:
            anos_disp = sorted(df_est_br["NU_ANO"].dropna().unique())
            if anos_disp:
                ano_ref = int(anos_disp[-1])
                d["ano_referencia_pos"] = ano_ref
                df_est_br_ano = df_est_br[df_est_br["NU_ANO"] == ano_ref]
                ranking_ano = (df_est_br_ano.groupby(col_uf)["MEDIA_GERAL"].mean()
                               .dropna().round(2).sort_values(ascending=False))
                ranking_ano = ranking_ano[ranking_ano.index.to_series().str.len() == 2]
                d["ranking_ufs_recente"] = ranking_ano
                d["total_ufs_recente"] = int(len(ranking_ano))
                if "MS" in ranking_ano.index:
                    d["pos_ms_recente"] = int(list(ranking_ano.index).index("MS")) + 1
    return d


_PREFIXOS_ESC = {"EE", "CEJA", "CEE", "CEEJA", "EEF", "EEFM", "CE"}
_STOP_ABR = {"DE", "DA", "DO", "DAS", "DOS",
    "E", "EM", "A", "O", "AS", "OS", "NO", "NA"}


def _fragment_camada_status(
    diag: dict,
    anos_sel: list,
    tabelas: dict,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
) -> None:
    """Camada 1 — não reroda ao trocar sub-aba (fragment isolado)."""
    aba_sumario_executivo(
        diag, anos_sel, modo_hub=True,
        tabelas=tabelas,
        df_bruta_ms=df_bruta_ms,
        df_filt_ms=df_filt_ms,
    )


@st.fragment
def _fragment_camada_detalhe(
    anos_sel: list,
    dep_selecionadas: list,
) -> None:
    """Camada 2 — só esta seção reroda ao trocar eixo de análise."""
    _render_html(
        '<div class="widget-head" style="border-radius:8px 8px 0 0;margin-top:4px">'
        'Análises detalhadas</div>'
    )
    st.caption("Selecione o eixo de análise. Apenas a seção ativa é carregada.")
    sub_aba = st.radio(
        "Eixo de análise",
        _SUBABAS_GESTAO,
        horizontal=True,
        key="hub_sub_aba",
        label_visibility="collapsed",
    )
    ctx = build_dashboard_context(
        tuple(int(a) for a in anos_sel),
        tuple(dep_selecionadas),
        sub_aba,
    )
    if sub_aba in (_SUBABA_DESEMPENHO, _SUBABA_TERRITORIO):
        anos_ind = anos_com_notas_individuais(ctx["df_notas_individuais"])
        if not anos_ind and sub_aba == _SUBABA_DESEMPENHO:
            st.info(
                "ℹ️ Notas individuais não encontradas — histogramas usam quantis agregados."
            )
        elif anos_ind and set(anos_ind) != set(ANOS_DISPONIVEIS):
            faltam = sorted(set(ANOS_DISPONIVEIS) - set(anos_ind))
            st.info(
                f"ℹ️ Notas individuais: {', '.join(str(a) for a in anos_ind)}. "
                f"Anos {', '.join(str(a) for a in faltam)} usam quantis agregados."
            )
    if ctx["df_concluintes"].empty and sub_aba == _SUBABA_PANORAMA:
        st.info(
            "ℹ️ Dados de concluintes do 3º ano não disponíveis. "
            "Taxa de participação efetiva pode aparecer como '—'."
        )
    tabelas = ctx["tabelas"]
    if sub_aba == _SUBABA_PANORAMA:
        aba_panorama_participacao(
            ctx["df_bruta_ms"], ctx["df_filt_ms"], anos_sel,
            df_concluintes=ctx["df_concluintes"],
            tabelas=tabelas,
        )
    elif sub_aba == _SUBABA_DESEMPENHO:
        aba_desempenho(
            ctx["df_filt_ms"],
            tabelas=tabelas,
            df_notas_individuais=ctx["df_notas_individuais"],
            anos_sel=anos_sel,
        )
    elif sub_aba == _SUBABA_TERRITORIO:
        aba_territorio_drilldown(
            ctx["df_ms_enriq"], ctx["df_ms_enriq_todos"], None, dep_selecionadas,
            ctx["df_bruta_ms_enriq"], ctx["df_ms_enriq_2024"], ctx["df_concluintes"],
            tabelas, ctx["df_notas_individuais"], anos_sel,
        )
    else:
        aba_contexto_nacional(tabelas, anos_sel)


def build_dashboard_context(
    anos_sel: tuple[int, ...],
    dep_selecionadas: tuple[str, ...],
    sub_aba: str,
) -> dict:
    """Contexto cacheado: tabelas + dados MS + cargas condicionais por sub-aba."""
    tabelas = carregar_todas_tabelas()
    anos_list = list(anos_sel)
    deps = list(dep_selecionadas)

    df_bruta_ms, df_filt_ms = reconstruir_participacao_ms(tabelas, anos_list, deps)
    diag = diagnostico_estadual(
        df_filt_ms, df_bruta_ms, tabelas=tabelas, anos_sel=anos_list,
    )
    diag = _enriquecer_diag_participacao(diag, tabelas, anos_list)
    n_insc = inscritos_estadual_ms(tabelas, anos_list)
    if n_insc:
        diag["n_inscritos"] = n_insc

    ctx: dict = {
        "tabelas": tabelas,
        "diag": diag,
        "df_bruta_ms": df_bruta_ms,
        "df_filt_ms": df_filt_ms,
        "df_bruta_ms_enriq": pd.DataFrame(),
        "df_ms_enriq": pd.DataFrame(),
        "df_ms_enriq_todos": pd.DataFrame(),
        "df_ms_enriq_2024": pd.DataFrame(),
        "df_notas_individuais": pd.DataFrame(),
        "df_concluintes": pd.DataFrame(),
    }

    if sub_aba in (_SUBABA_PANORAMA, _SUBABA_TERRITORIO, _SUBABA_HUB):
        ctx["df_concluintes"] = carregar_concluintes()

    if sub_aba == _SUBABA_TERRITORIO:
        cres = carregar_cres()
        mapa = carregar_mapa_municipio_cre()
        ctx["df_bruta_ms_enriq"] = enriquecer_ms(df_bruta_ms, cres, mapa)
        df_todos = reconstruir_ms_enriquecido(tabelas, ANOS_DISPONIVEIS, deps)
        df_todos = aplicar_cre_por_municipio(df_todos, mapa)
        ctx["df_ms_enriq"] = enriquecer_ms(
            reconstruir_ms_enriquecido(tabelas, anos_list, deps), cres, mapa,
        )
        ctx["df_ms_enriq_todos"] = enriquecer_ms(df_todos, cres, mapa)
        df_2024 = reconstruir_escolas_2024_ms(tabelas, deps)
        if 2024 in anos_list and df_2024.empty:
            sub = ctx["df_ms_enriq"][ctx["df_ms_enriq"]["NU_ANO"] == 2024]
            if "CO_ESCOLA" in sub.columns:
                df_2024 = sub[sub["CO_ESCOLA"].notna()].copy()
        ctx["df_ms_enriq_2024"] = enriquecer_ms(df_2024, cres, mapa)

    if sub_aba in (_SUBABA_DESEMPENHO, _SUBABA_TERRITORIO):
        ctx["df_notas_individuais"] = carregar_notas_individuais(anos=tuple(int(a) for a in anos_list))
        if (
            sub_aba == _SUBABA_TERRITORIO
            and not ctx["df_notas_individuais"].empty
            and "Estadual" in deps
            and tem_notas_individuais_ano(ctx["df_notas_individuais"], 2024)
        ):
            df_2024 = filtrar_notas_individuais(
                ctx["df_notas_individuais"], ano=2024, dependencia="Estadual",
            )
            cres = carregar_cres()
            mapa = carregar_mapa_municipio_cre()
            ctx["df_ms_enriq_2024"] = enriquecer_ms(df_2024, cres, mapa)

    return ctx



# --- páginas (fase 4) ---
from app.v15.pages import (
    aba_contexto_nacional,
    aba_desempenho,
    aba_escolas_2024,
    aba_gestao_hub,
    aba_metodologia,
    aba_municipios,
    aba_panorama_participacao,
    aba_sumario_executivo,
    aba_territorial,
    aba_territorio_drilldown,
)
from app.v15.pages.metodologia import _render_metodologia_detalhe
def main():
    if st.session_state.get("_hub_build_loaded") != HUB_BUILD_ID:
        st.session_state["_hub_build_loaded"] = HUB_BUILD_ID
        st.session_state["_fig_ck"] = 0

    anos_sel, dep_selecionadas = ANOS_DISPONIVEIS, ORDEM_DEP
    periodo = (
        f"{min(anos_sel)}–{max(anos_sel)}"
        if anos_sel and len(anos_sel) >= 2
        else (str(anos_sel[0]) if anos_sel else "—")
    )

    ctx_base = build_dashboard_context(
        tuple(int(a) for a in anos_sel),
        tuple(dep_selecionadas),
        _SUBABA_HUB,
    )
    if ctx_base["df_filt_ms"].empty:
        st.error("Nenhum participante encontrado no recorte selecionado.")
        return

    _render_cabecalho_com_kpis(ctx_base["diag"], periodo)
    _render_populacao_referencia_compacta()

    _fragment_camada_status(
        ctx_base["diag"],
        anos_sel,
        ctx_base["tabelas"],
        ctx_base["df_bruta_ms"],
        ctx_base["df_filt_ms"],
    )

    st.markdown("---")
    mostrar_detalhe = st.checkbox(
        "Carregar análises detalhadas",
        value=False,
        key="hub_carregar_detalhe",
        help="Ative para abrir a seção inferior (mais gráficos e tabelas).",
    )
    if mostrar_detalhe:
        _fragment_camada_detalhe(anos_sel, dep_selecionadas)

    with st.expander("Metodologia, fontes e camadas técnicas"):
        _render_metodologia_detalhe()

    st.markdown(
        f"<div class='rodape'>Fonte: INEP — Microdados do ENEM. Cadastro de escolas: CRES."
        f" · hub {HUB_BUILD_ID}</div>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
    
