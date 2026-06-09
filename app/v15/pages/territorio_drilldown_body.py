"""Corpo das funções de `territorio_drilldown` (fase 5d)."""

from __future__ import annotations

from app.v15.pages.escolas_2024 import aba_escolas_2024
from app.v15.pages.municipios import aba_municipios
from app.v15.pages.territorial import aba_territorial
from app.v15.page_imports import *

def render_territorio_drilldown(
    df_ms_enriq,
    df_ms_enriq_todos,
    df_br_nacional_estadual,
    dep_selecionadas,
    df_bruta_ms_enriq,
    df_ms_enriq_2024,
    df_concluintes,
    tabelas,
    df_notas_individuais,
    anos_sel,
):
    """Drill-down territorial: Estado → CRE → Município → Escola (2024)."""
    nivel = st.radio(
        "Nível de detalhe",
        _NIVEIS_TERRITORIO,
        horizontal=True,
        key="hub_nivel_territorio",
        label_visibility="collapsed",
    )
    st.caption(
        "**Estado** — ranking de CREs · **CRE** — evolução e distribuição por coordenadoria · "
        "**Município** — detalhe por cidade · **Escola** — unidades em 2024."
    )

    if nivel == _NIVEL_TERRITORIO_ESTADO:
        _vista_territorio_estado(tabelas, anos_sel)
    elif nivel == _NIVEL_TERRITORIO_CRE:
        aba_territorial(
            df_ms_enriq, df_ms_enriq_todos, df_br_nacional_estadual, dep_selecionadas,
            df_bruta_ms_enriq=df_bruta_ms_enriq, tabelas=tabelas,
            df_notas_individuais=df_notas_individuais, anos_sel=anos_sel,
        )
    elif nivel == _NIVEL_TERRITORIO_MUN:
        aba_municipios(
            df_ms_enriq, df_ms_enriq_todos, df_br_nacional_estadual, dep_selecionadas,
            df_bruta_ms_enriq=df_bruta_ms_enriq, tabelas=tabelas,
            df_notas_individuais=df_notas_individuais, anos_sel=anos_sel,
        )
    else:
        if df_ms_enriq_2024.empty:
            st.info(
                "Detalhamento por escola requer dados de 2024 no recorte lateral. "
                "Inclua 2024 nos anos selecionados e regenere agregados/notas individuais."
            )
        else:
            aba_escolas_2024(
                df_ms_enriq_2024, 2024, df_br_nacional_estadual,
                df_bruta_ms=df_bruta_ms_enriq, df_concluintes=df_concluintes,
                tabelas=tabelas, df_notas_individuais=df_notas_individuais,
            )

