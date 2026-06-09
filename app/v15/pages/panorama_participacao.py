"""Páginas `panorama_participacao` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.panorama_participacao_body import render_panorama_participacao

def aba_panorama_participacao(df_bruta_ms, df_filt_ms, anos_sel,
                              df_bruta_ms_enriq=None, df_filt_ms_enriq=None,
                              df_bruta_nacional=None, df_filt_nacional=None,
                              df_concluintes=None, tabelas=None):
    render_panorama_participacao(**locals())

