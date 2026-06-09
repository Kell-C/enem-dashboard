"""Carregamento de concluintes por CRE — painel ENEM v15."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from app.v15.paths import ARQUIVO_CONCLUINTES, ARQUIVO_CRES


def carregar_concluintes_cre() -> pd.DataFrame:
    """Carrega dados de concluintes agregados por CRE e ano."""
    from concluintes_loader import carregar_concluintes_cre as _carregar_concluintes_cre

    arquivo = os.getenv("ARQUIVO_CONCLUINTES", ARQUIVO_CONCLUINTES)
    if not arquivo or not os.path.exists(arquivo):
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])

    try:
        return _carregar_concluintes_cre(arquivo=arquivo, arquivo_cres=ARQUIVO_CRES)
    except Exception as e:
        st.warning(f"Não foi possível carregar dados de concluintes por CRE: {e}")
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])
