"""Páginas `escolas_2024` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.escolas_2024_body import render_escolas_2024

def aba_escolas_2024(df_ms_enriq_2024, ano=2024, df_br=None, df_bruta_ms=None, df_concluintes=None, tabelas=None, df_notas_individuais=None):
    render_escolas_2024(**locals())

