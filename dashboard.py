"""
Dashboard ENEM MS — entry point local.

Lê agregados de data/agregados/ via dados_agregados_loader.py.

Uso:
    streamlit run dashboard.py
"""

import streamlit as st

from app.components import render_cabecalho_kpis, render_populacao_referencia
from app.data import fonte_dados_caption, init_session_state, load_all, validar_dados
from app.detail import render_detail
from app.diagnostics import build_diag
from app.hub import render_hub
from app.styles import inject_styles
from app.territory import render_territory


def main() -> None:
    st.set_page_config(
        page_title="Painel ENEM — MS",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    inject_styles()
    init_session_state()

    tabelas = load_all()
    if not validar_dados(tabelas):
        return

    diag = build_diag(tabelas)
    anos_sel = diag.get("anos_sel", [])
    periodo = (
        f"{min(anos_sel)}–{max(anos_sel)}"
        if len(anos_sel) >= 2
        else (str(anos_sel[0]) if anos_sel else "2019–2024")
    )

    render_cabecalho_kpis(diag, periodo)
    render_populacao_referencia()

    if st.session_state.view == "hub":
        render_hub(tabelas, diag)
    else:
        render_territory(tabelas)

    st.markdown("---")
    if st.checkbox(
        "Carregar análises detalhadas",
        value=False,
        key="carregar_detalhe",
        help="Participação, desempenho e panorama nacional.",
    ):
        render_detail(tabelas)

    st.caption(fonte_dados_caption())


if __name__ == "__main__":
    main()
