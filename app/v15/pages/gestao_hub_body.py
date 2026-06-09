"""Corpo das funções de `gestao_hub` (fase 5d)."""

from __future__ import annotations

from app.v15.pages.sumario_executivo import aba_sumario_executivo
from app.v15.page_imports import *

def render_gestao_hub(
    diag,
    anos_sel,
    dep_selecionadas,
    tabelas: dict,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
):
    """Hub único de gestão: capa em 3 colunas (participação · desempenho · território)."""
    aba_sumario_executivo(
        diag, anos_sel, modo_hub=True,
        tabelas=tabelas,
        df_bruta_ms=df_bruta_ms,
        df_filt_ms=df_filt_ms,
    )

