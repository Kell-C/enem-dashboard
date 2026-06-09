"""Páginas `gestao_hub` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.gestao_hub_body import render_gestao_hub

def aba_gestao_hub(
    diag,
    anos_sel,
    dep_selecionadas,
    tabelas: dict,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
):
    render_gestao_hub(**locals())

