"""Páginas `territorio_drilldown` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.territorio_drilldown_body import render_territorio_drilldown

def aba_territorio_drilldown(
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
    render_territorio_drilldown(**locals())

