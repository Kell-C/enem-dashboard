"""Carregamento de dados e estado de sessão."""

from __future__ import annotations

import streamlit as st

from dados_agregados_loader import (
    carregar_tabela,
    carregar_todas_tabelas,
    get_data_source,
    get_pasta_agregados,
    verificar_dados_disponiveis,
)

from app.theme import NIVEL_ESTADO


def init_session_state() -> None:
    defaults = {
        "view": "hub",
        "territory_level": NIVEL_ESTADO,
        "selected_cre": None,
        "selected_municipio": None,
        "selected_escola": None,
        "ano_ref": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


@st.cache_data(show_spinner="Carregando dados agregados...", ttl=3600)
def load_all() -> dict:
    return carregar_todas_tabelas()


def load_table(nome: str):
    return carregar_tabela(nome)


def validar_dados(tabelas: dict) -> bool:
    if not verificar_dados_disponiveis():
        st.error(
            f"Nenhum agregado encontrado em `{get_pasta_agregados()}`. "
            "Execute `python gerar_dados_agregados.py` para gerar os parquets."
        )
        return False
    if tabelas.get("sumario_executivo", __import__("pandas").DataFrame()).empty:
        st.error(
            "`sumario_executivo` vazio ou ausente. "
            "Regenere os agregados com `python gerar_dados_agregados.py`."
        )
        return False
    return True


def ir_para_hub() -> None:
    st.session_state.view = "hub"
    st.session_state.territory_level = NIVEL_ESTADO
    st.session_state.selected_cre = None
    st.session_state.selected_municipio = None
    st.session_state.selected_escola = None


def ir_para_territorio(
    nivel: str,
    *,
    cre: str | None = None,
    municipio: str | None = None,
    escola: int | None = None,
) -> None:
    st.session_state.view = "territory"
    st.session_state.territory_level = nivel
    if cre is not None:
        st.session_state.selected_cre = cre
    if municipio is not None:
        st.session_state.selected_municipio = municipio
    if escola is not None:
        st.session_state.selected_escola = escola


def anos_disponiveis(tabelas: dict) -> list[int]:
    df = tabelas.get("sumario_executivo")
    if df is None or df.empty or "ano" not in df.columns:
        return []
    return sorted(int(a) for a in df["ano"].unique())


def fonte_dados_caption() -> str:
    return f"Fonte: `data/agregados/` · modo **{get_data_source().upper()}**"
