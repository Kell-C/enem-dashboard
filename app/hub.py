"""Camada hub — visão executiva estilo v15."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.charts import (
    fig_box_media_geral,
    fig_combo_media_participacao,
    fig_cre_combo,
    fig_delta_br_areas,
    fig_evolucao_areas,
    fig_medias_dependencia,
    fig_ranking_uf,
)
from app.components import nome_cre_curto, render_hub_widget
from app.data import ir_para_territorio
from app.diagnostics import build_diag
from app.theme import HUB_COL_LAYOUT, NIVEL_CRE, NIVEL_ESTADO


def _df_ranking_cre(tabelas: dict, ano: int) -> pd.DataFrame:
    df = tabelas.get("evolucao_cre", pd.DataFrame())
    if df.empty or "CRE" not in df.columns:
        return pd.DataFrame()
    sub = df[(df["ano"] == ano) & (df["dependencia"] == "Estadual")].copy()
    if sub.empty or "media_geral" not in sub.columns:
        return pd.DataFrame()
    sub = sub.dropna(subset=["media_geral"]).sort_values("media_geral", ascending=False)
    out = sub[["CRE", "media_geral", "estudantes"]].copy()
    out.columns = ["CRE", "Média geral", "Estudantes"]
    out["CRE curto"] = out["CRE"].map(nome_cre_curto)
    out["Média geral"] = out["Média geral"].round(1)
    out["Estudantes"] = out["Estudantes"].astype(int)
    return out.reset_index(drop=True)


def _render_coluna(cards: list[tuple[str, object, str, str]]) -> None:
    for titulo, fig, legenda, key in cards:
        if fig is not None:
            render_hub_widget(titulo, fig, legenda, chart_key=key)


def _processar_selecao_cre(df_rank: pd.DataFrame, key: str) -> None:
    if df_rank.empty:
        return
    st.caption("Selecione uma CRE para detalhar:")
    event = st.dataframe(
        df_rank[["CRE curto", "Média geral", "Estudantes"]],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )
    if event.selection and event.selection.rows:
        cre = df_rank.iloc[event.selection.rows[0]]["CRE"]
        ir_para_territorio(NIVEL_CRE, cre=str(cre))
        st.rerun()


def render_hub(tabelas: dict, diag: dict | None = None) -> int:
    if diag is None:
        diag = build_diag(tabelas)
    anos_sel = diag.get("anos_sel") or sorted(
        int(a) for a in tabelas.get("sumario_executivo", pd.DataFrame()).get("ano", pd.Series()).unique()
    )
    if not anos_sel:
        st.warning("Nenhum ano disponível.")
        return 2024

    default_ano = st.session_state.get("ano_ref") or anos_sel[-1]
    if default_ano not in anos_sel:
        default_ano = anos_sel[-1]

    tb1, tb2 = st.columns([2, 3])
    with tb1:
        ano_ref = st.selectbox(
            "Ano de referência (CREs e dependência)",
            anos_sel,
            index=anos_sel.index(default_ano),
            key="hub_ano_select",
        )
    st.session_state.ano_ref = ano_ref
    with tb2:
        if st.button("Explorar território →", type="primary", key="hub_btn_territorio"):
            ir_para_territorio(NIVEL_ESTADO)
            st.rerun()

    periodo = f"{min(anos_sel)}–{max(anos_sel)}" if len(anos_sel) >= 2 else str(anos_sel[0])

    card_ms = ("Rede estadual · média e participação", fig_combo_media_participacao(diag), "Δ sobre a linha = diferença vs Brasil", "hub_ms")
    card_rank = ("Ranking entre estados · média e participação", fig_ranking_uf(diag), "Menor posição = melhor desempenho", "hub_rank_uf")
    card_box = ("Distribuição · média geral", fig_box_media_geral(tabelas, anos_sel), "Quartis da rede estadual por ano", "hub_box")

    card_evol = ("Evolução por área de conhecimento", fig_evolucao_areas(tabelas, anos_sel), "", "hub_evol")
    card_delta = ("Diferença vs Brasil por área", fig_delta_br_areas(tabelas, anos_sel), "Verde = acima do BR · Vermelho = abaixo", "hub_delta")

    card_cre = (
        f"Coordenadorias · média e participação ({ano_ref})",
        fig_cre_combo(tabelas, int(ano_ref)),
        "Tracejado = MS · Pontilhado = BR",
        "hub_cre",
    )
    card_deps = (
        f"Média por dependência administrativa ({ano_ref})",
        fig_medias_dependencia(tabelas, int(ano_ref)),
        "",
        "hub_deps",
    )

    st.markdown('<div class="hub-panorama-grid">', unsafe_allow_html=True)
    col_esq, col_meio, col_dir = st.columns(HUB_COL_LAYOUT, gap="small")

    with col_esq:
        _render_coluna([c for c in (card_ms, card_rank, card_box) if c[1] is not None])

    with col_meio:
        _render_coluna([c for c in (card_evol, card_delta) if c[1] is not None])

    with col_dir:
        _render_coluna([c for c in (card_cre, card_deps) if c[1] is not None])
        df_rank = _df_ranking_cre(tabelas, int(ano_ref))
        if not df_rank.empty:
            _processar_selecao_cre(df_rank, key="hub_cre_select")

    st.markdown("</div>", unsafe_allow_html=True)
    return int(ano_ref)
