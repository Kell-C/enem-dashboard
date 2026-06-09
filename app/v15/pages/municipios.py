"""Páginas `municipios` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.municipios_body import render_municipios

def aba_municipios(
    df_ms_enriq,
    df_filt_ms_full=None,
    df_br=None,
    dep_selecionadas=None,
    df_bruta_ms_enriq=None,
    tabelas=None,
    df_notas_individuais=None,
    anos_sel=None,
):
    render_municipios(**locals())

