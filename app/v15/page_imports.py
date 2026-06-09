"""Imports compartilhados pelos corpos de página v15 (fase 5d)."""

from __future__ import annotations

import html as _html
import re as _re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from viz.chart_layout import (
    CHART_H_BOX,
    CHART_H_BOX_WIDE,
    CHART_H_EVOLUCAO,
    CHART_H_HIST,
    CHART_H_HIST_GRID,
    CHART_H_HIST_ROW,
    CHART_H_PARTICIPACAO,
    CHART_H_RANKING,
    CHART_H_STANDARD,
)

from dados_agregados_loader import (
    anos_com_desempenho_uf,
    anos_com_notas_individuais,
    carregar_notas_individuais,
    filtrar_distribuicao,
    filtrar_notas_individuais,
    filtrar_participacao_cre,
    filtrar_participacao_municipio,
    get_data_source,
    histograma_area_ano,
    inscritos_estadual_ms,
    inscritos_por_escola_2024,
    linha_distribuicao,
    linha_escola_2024,
    media_nacional_ponderada,
    media_ms_area_ano,
    medias_referencia_por_ano,
    notas_area,
    participacao_ms_por_ano,
    presentes_filt_estadual_ano,
    reconstruir_escolas_2024_ms,
    reconstruir_ms_enriquecido,
    serie_media_nacional_dep,
    stats_box_quantis,
    tabela_ranking_uf,
    tem_notas_individuais_ano,
)

from app.v15.boxplots import (
    _add_box,
    _add_box_series,
    _add_box_stats,
    _add_scatter_notas,
    _finalizar_boxplot,
    _finalizar_grafico,
)
from app.v15.charts.detail import (
    _fig_box_distribuicao_areas,
    _fig_evolucao_unificada,
    _fig_histogram_notas,
    _fig_histogramas_multiarea_coloridos,
    _mini_legenda_medias_html,
    fig_combo_participacao_desempenho,
    fig_evolucao_area,
    fig_media_area_deps,
    fig_ms_participacao_desempenho,
    fig_participacao_por_ano,
    fig_quadrante_desempenho_participacao,
    fig_ranking_horizontal,
    fig_uf_barras,
)
from app.v15.charts.hub import (
    _fig_posicao_ms_nacional,
    _render_hub_panorama,
)
from app.v15.charts_render import _chart, _chart_hub
from app.v15.classifiers import (
    classificar_participacao,
    classificar_posicao,
    classificar_tendencia,
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
from app.v15.formatting import fmt_delta, fmt_float, fmt_int, fmt_pct
from cres_loader import nome_cre_curto
from app.v15.ms_enrich import (
    aplicar_cre_por_municipio,
    carregar_cres,
    carregar_mapa_municipio_cre,
    enriquecer_ms,
)
from app.v15.nav_constants import (
    _NIVEIS_TERRITORIO,
    _NIVEL_TERRITORIO_CRE,
    _NIVEL_TERRITORIO_ESC,
    _NIVEL_TERRITORIO_ESTADO,
    _NIVEL_TERRITORIO_MUN,
)
from app.v15.page_helpers import (
    _estilizar_tabela,
    _faixa_concluintes_participantes,
    _legenda_populacoes_secao_html,
    _normalizar_nome_municipio,
    _populacao_estadual_ano,
    _secao_detalhe_ano_desempenho,
    carregar_concluintes,
    carregar_concluintes_municipio,
)
from app.v15.participation import _enriquecer_participacao_taxas
from app.v15.territory_data import (
    _participacao_cre_tabela,
    _participacao_municipio_tabela,
    _reconstruir_bases_territoriais,
    _vista_territorio_estado,
)
from app.v15.theme import *
from app.v15.ui import _legenda_inline, _render_html

# `import *` nos *_body.py precisa incluir símbolos com prefixo `_`.
__all__ = [name for name in globals() if not name.startswith("__")]
