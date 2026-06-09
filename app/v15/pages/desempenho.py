"""Páginas `desempenho` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.desempenho_body import render_desempenho

def aba_desempenho(df_filt_ms, tabelas=None, df_notas_individuais=None, anos_sel=None):
    render_desempenho(**locals())

