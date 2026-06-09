"""Páginas `sumario_executivo` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.sumario_executivo_body import render_sumario_executivo

def aba_sumario_executivo(
    diag: dict,
    anos_sel: list,
    *,
    modo_hub: bool = False,
    tabelas: dict | None = None,
    df_bruta_ms: pd.DataFrame | None = None,
    df_filt_ms: pd.DataFrame | None = None,
):
    render_sumario_executivo(**locals())

