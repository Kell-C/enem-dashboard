"""Análises detalhadas opcionais — participação, desempenho e panorama nacional."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import coluna_existente, titulo_secao
from app.theme import DEPENDENCIAS, DEP_PADRAO


def _aba_participacao(tabelas: dict) -> None:
    st.subheader("Participação")
    df = tabelas.get("participacao_ano", pd.DataFrame())
    if df.empty:
        st.warning("Nenhum dado de participação disponível.")
        return

    dep = st.multiselect(
        "Dependências",
        DEPENDENCIAS,
        default=[DEP_PADRAO],
        key="detail_participacao_dep",
    )
    df_filt = df[df["dependencia"].isin(dep)]
    col_media = (
        coluna_existente(df_filt.iloc[0], "presentes_filt", "presentes")
        if not df_filt.empty
        else "presentes_filt"
    )

    fig = px.line(
        df_filt,
        x="ano",
        y=col_media,
        color="dependencia",
        title="Evolução de presentes efetivos por dependência",
        labels={col_media: "Presentes", "ano": "Ano"},
    )
    st.plotly_chart(fig, use_container_width=True)

    df_cre = tabelas.get("participacao_cre", pd.DataFrame())
    if not df_cre.empty:
        ano = int(df_cre["ano"].max())
        sub = df_cre[
            (df_cre["ano"] == ano) & (df_cre["dependencia"] == DEP_PADRAO)
        ].sort_values("media_geral", ascending=False)
        if not sub.empty and "tx_part_efetiva" in sub.columns:
            st.caption(f"Participação por CRE — {ano}")
            st.dataframe(
                sub[["CRE", "estudantes", "tx_part_efetiva", "media_geral"]].rename(
                    columns={
                        "tx_part_efetiva": "Tx. part. (%)",
                        "media_geral": "Média geral",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.dataframe(df_filt.sort_values(["ano", "dependencia"]), use_container_width=True)


def _aba_desempenho(tabelas: dict) -> None:
    st.subheader("Desempenho")
    df = tabelas.get("desempenho", pd.DataFrame())
    if df.empty:
        st.warning("Nenhum dado de desempenho disponível.")
        return

    dep = st.multiselect(
        "Dependências",
        DEPENDENCIAS,
        default=[DEP_PADRAO],
        key="detail_desempenho_dep",
    )
    df_filt = df[df["dependencia"].isin(dep)]
    col_media = (
        coluna_existente(df_filt.iloc[0], "media_media_geral", "media_geral")
        if not df_filt.empty
        else "media_media_geral"
    )

    fig = px.line(
        df_filt,
        x="ano",
        y=col_media,
        color="dependencia",
        title="Evolução da média geral",
        labels={col_media: "Média geral", "ano": "Ano"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_filt, use_container_width=True)


def _aba_panorama(tabelas: dict) -> None:
    st.subheader("Panorama nacional")
    df = tabelas.get("panorama_nacional", pd.DataFrame())
    if df.empty:
        st.warning("Panorama nacional indisponível.")
        return

    dep = st.multiselect(
        "Dependências",
        DEPENDENCIAS,
        default=DEPENDENCIAS,
        key="detail_panorama_dep",
    )
    df_filt = df[df["dependencia"].isin(dep)]
    col_y = coluna_existente(
        df_filt.iloc[0] if not df_filt.empty else pd.Series(),
        "presentes_filt",
        "presentes",
    )

    fig = px.line(
        df_filt,
        x="ano",
        y=col_y,
        color="dependencia",
        title="Evolução de presentes — panorama nacional",
        labels={col_y: "Presentes", "ano": "Ano"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_filt, use_container_width=True)


def render_detail(tabelas: dict) -> None:
    titulo_secao(
        "Análises detalhadas",
        "Gráficos e tabelas complementares carregados sob demanda.",
    )
    abas = st.tabs(["Participação", "Desempenho", "Panorama nacional"])
    with abas[0]:
        _aba_participacao(tabelas)
    with abas[1]:
        _aba_desempenho(tabelas)
    with abas[2]:
        _aba_panorama(tabelas)
