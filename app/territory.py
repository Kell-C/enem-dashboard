"""Drill-down territorial: Estado → CRE → Município → Escola."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components import (
    fmt_float,
    fmt_int,
    nome_cre_curto,
    titulo_secao,
    valor_numerico,
)
from app.data import ir_para_hub, ir_para_territorio
from app.theme import (
    AZUL_PRINCIPAL,
    DEP_PADRAO,
    NIVEL_CRE,
    NIVEL_ESCOLA,
    NIVEL_ESTADO,
    NIVEL_MUNICIPIO,
    NIVEIS_TERRITORIO,
    NIVEL_LABELS,
)
from viz.chart_layout import CHART_H_STANDARD, PLOTLY_HUB_CONFIG


def _media_col(df: pd.DataFrame) -> str:
    if "media_geral" in df.columns:
        return "media_geral"
    if "media_media_geral" in df.columns:
        return "media_media_geral"
    return "media_geral"


def _municipio_col(df: pd.DataFrame) -> str:
    if "NO_MUNICIPIO_ESC" in df.columns:
        return "NO_MUNICIPIO_ESC"
    if "municipio" in df.columns:
        return "municipio"
    return "NO_MUNICIPIO_ESC"


def _render_breadcrumb() -> None:
    cre = st.session_state.get("selected_cre")
    mun = st.session_state.get("selected_municipio")
    escola = st.session_state.get("selected_escola")

    trail: list[str] = []
    if cre:
        trail.append(f"CRE: {nome_cre_curto(cre)}")
    if mun:
        trail.append(f"Município: {mun}")
    if escola:
        trail.append(f"Escola: {escola}")

    if trail:
        st.caption("Navegação: Hub › " + " › ".join(trail))

    nav_cols = st.columns(min(4, 1 + int(bool(cre)) + int(bool(mun))))
    with nav_cols[0]:
        if st.button("Hub", key="bc_hub", use_container_width=True):
            ir_para_hub()
            st.rerun()
    i = 1
    if cre and i < len(nav_cols):
        with nav_cols[i]:
            if st.button(f"CRE", key="bc_cre", use_container_width=True):
                ir_para_territorio(NIVEL_CRE, cre=cre, municipio=None, escola=None)
                st.rerun()
        i += 1
    if mun and i < len(nav_cols):
        with nav_cols[i]:
            if st.button("Município", key="bc_mun", use_container_width=True):
                ir_para_territorio(NIVEL_MUNICIPIO, cre=cre, municipio=mun, escola=None)
                st.rerun()


def _ano_ref(tabelas: dict) -> int:
    if st.session_state.get("ano_ref"):
        return int(st.session_state.ano_ref)
    df = tabelas.get("sumario_executivo", pd.DataFrame())
    if df.empty:
        return 2024
    return int(df["ano"].max())


def _vista_estado(tabelas: dict, ano: int) -> None:
    titulo_secao(
        "Visão estadual — CREs",
        f"Ranking das coordenadorias · rede {DEP_PADRAO} · ano {ano}.",
    )
    df = tabelas.get("evolucao_cre", pd.DataFrame())
    if df.empty:
        st.info("Dados de evolução por CRE indisponíveis.")
        return

    col_media = _media_col(df)
    sub = df[(df["ano"] == ano) & (df["dependencia"] == DEP_PADRAO)].copy()
    if sub.empty:
        st.info(f"Sem dados de CRE para {ano}.")
        return

    sub = sub.dropna(subset=[col_media]).sort_values(col_media, ascending=False)
    exibir = sub[["CRE", col_media, "estudantes"]].copy()
    exibir.columns = ["CRE", "Média geral", "Estudantes"]
    exibir["CRE"] = exibir["CRE"].map(nome_cre_curto)
    exibir["Média geral"] = exibir["Média geral"].round(1)

    fig = px.bar(
        exibir.sort_values("Média geral"),
        x="Média geral",
        y="CRE",
        orientation="h",
        title=f"Média geral por CRE — {ano}",
        color_discrete_sequence=[AZUL_PRINCIPAL],
    )
    fig.update_layout(height=CHART_H_STANDARD, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_HUB_CONFIG)

    st.caption("Selecione uma CRE para detalhar:")
    sub_full = sub.reset_index(drop=True)
    event = st.dataframe(
        exibir.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="terr_estado_cre_select",
    )
    if event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        cre = sub_full.iloc[idx]["CRE"]
        ir_para_territorio(NIVEL_CRE, cre=str(cre))
        st.rerun()

    if len(sub) >= 2:
        st.markdown(
            f"**Extremos:** maior — **{nome_cre_curto(sub.iloc[0]['CRE'])}** "
            f"({fmt_float(sub.iloc[0][col_media])}); "
            f"menor — **{nome_cre_curto(sub.iloc[-1]['CRE'])}** "
            f"({fmt_float(sub.iloc[-1][col_media])})."
        )


def _municipios_da_cre(tabelas: dict, cre: str) -> list[str]:
    df_esc = tabelas.get("escolas_2024", pd.DataFrame())
    if df_esc.empty or "cre" not in df_esc.columns:
        return []
    col_mun = _municipio_col(df_esc)
    sub = df_esc[df_esc["cre"] == cre]
    if sub.empty:
        sub = df_esc[df_esc["cre"].astype(str).str.strip() == str(cre).strip()]
    return sorted(sub[col_mun].dropna().astype(str).unique())


def _vista_cre(tabelas: dict, cre: str) -> None:
    titulo_secao(f"CRE — {nome_cre_curto(cre)}", "Evolução e municípios vinculados.")

    df_ter = tabelas.get("territorial", pd.DataFrame())
    col_media = _media_col(df_ter) if not df_ter.empty else "media_geral"

    sub = df_ter[
        (df_ter["CRE"] == cre) & (df_ter["dependencia"] == DEP_PADRAO)
    ].sort_values("ano")
    if sub.empty:
        sub = df_ter[
            df_ter["CRE"].astype(str).str.strip() == str(cre).strip()
        ].sort_values("ano")

    if not sub.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=sub["ano"],
                y=sub[col_media],
                mode="lines+markers",
                name="Média geral",
                line=dict(color=AZUL_PRINCIPAL, width=2),
            )
        )
        if "tx_part_efetiva" in sub.columns:
            fig.add_trace(
                go.Scatter(
                    x=sub["ano"],
                    y=sub["tx_part_efetiva"],
                    mode="lines+markers",
                    name="Tx. participação (%)",
                    yaxis="y2",
                    line=dict(dash="dot", color="#0F8A5F"),
                )
            )
            fig.update_layout(
                yaxis2=dict(title="Participação (%)", overlaying="y", side="right"),
            )
        fig.update_layout(
            title=f"Evolução — {nome_cre_curto(cre)}",
            height=CHART_H_STANDARD,
            xaxis_title="Ano",
            yaxis_title="Média geral",
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_HUB_CONFIG)
    else:
        st.info("Sem série temporal para esta CRE em `territorial`.")

    municipios = _municipios_da_cre(tabelas, cre)
    ano = _ano_ref(tabelas)
    df_mun = tabelas.get("municipios", pd.DataFrame())
    if municipios and not df_mun.empty:
        col_m = _municipio_col(df_mun)
        sub_m = df_mun[
            (df_mun[col_m].astype(str).isin(municipios))
            & (df_mun["ano"] == ano)
            & (df_mun["dependencia"] == DEP_PADRAO)
        ].copy()
        if not sub_m.empty:
            exibir = sub_m[[col_m, col_media, "estudantes"]].copy()
            exibir.columns = ["Município", "Média geral", "Estudantes"]
            exibir = exibir.sort_values("Média geral", ascending=False).reset_index(drop=True)
            exibir["Média geral"] = exibir["Média geral"].round(1)
            st.caption(f"Municípios da CRE · {ano} — selecione para detalhar:")
            event = st.dataframe(
                exibir,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="terr_cre_mun_select",
            )
            if event.selection and event.selection.rows:
                idx = event.selection.rows[0]
                mun = exibir.iloc[idx]["Município"]
                ir_para_territorio(NIVEL_MUNICIPIO, cre=cre, municipio=str(mun))
                st.rerun()
        else:
            st.info("Sem dados de municípios para esta CRE no ano de referência.")
    elif not municipios:
        st.info("Cadastro de municípios por CRE indisponível em `escolas_2024`.")


def _vista_municipio(tabelas: dict, municipio: str, cre: str | None) -> None:
    titulo_secao(f"Município — {municipio}", "Evolução de desempenho e escolas em 2024.")

    df_evol = tabelas.get("evolucao_municipios", pd.DataFrame())
    df_mun = tabelas.get("municipios", pd.DataFrame())
    col_m = _municipio_col(df_evol if not df_evol.empty else df_mun)
    col_media = _media_col(df_evol if not df_evol.empty else df_mun)

    sub = pd.DataFrame()
    if not df_evol.empty:
        sub = df_evol[
            (df_evol[col_m].astype(str) == str(municipio))
            & (df_evol["dependencia"] == DEP_PADRAO)
        ].sort_values("ano")

    if not sub.empty:
        fig = px.line(
            sub,
            x="ano",
            y=col_media,
            markers=True,
            title=f"Média geral — {municipio}",
            color_discrete_sequence=[AZUL_PRINCIPAL],
        )
        fig.update_layout(height=360, yaxis_title="Média geral")
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_HUB_CONFIG)

    ano = _ano_ref(tabelas)
    if not df_mun.empty:
        row = df_mun[
            (df_mun[col_m].astype(str) == str(municipio))
            & (df_mun["ano"] == ano)
            & (df_mun["dependencia"] == DEP_PADRAO)
        ]
        if not row.empty:
            r = row.iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Média geral", fmt_float(valor_numerico(r, col_media)))
            with c2:
                st.metric("Estudantes", fmt_int(valor_numerico(r, "estudantes")))
            with c3:
                tx = r.get("tx_part_efetiva")
                st.metric(
                    "Tx. participação",
                    fmt_float(tx) + "%" if pd.notna(tx) else "—",
                )

    df_esc = tabelas.get("escolas_2024", pd.DataFrame())
    if df_esc.empty:
        st.info("Tabela de escolas 2024 indisponível.")
        return

    col_mun_esc = _municipio_col(df_esc)
    sub_esc = df_esc[df_esc[col_mun_esc].astype(str) == str(municipio)].copy()
    if cre and "cre" in sub_esc.columns:
        sub_esc = sub_esc[
            sub_esc["cre"].astype(str).str.strip() == str(cre).strip()
        ]
    if sub_esc.empty:
        st.info("Nenhuma escola encontrada para este município em 2024.")
        return

    col_media_esc = _media_col(sub_esc)
    cols_show = [c for c in ["NOME_ESCOLA", "cre", col_media_esc, "estudantes", "tx_part_efetiva", "CO_ESCOLA"] if c in sub_esc.columns]
    exibir = sub_esc[cols_show].sort_values(col_media_esc, ascending=False).reset_index(drop=True)
    rename = {
        "NOME_ESCOLA": "Escola",
        "cre": "CRE",
        col_media_esc: "Média geral",
        "estudantes": "Estudantes",
        "tx_part_efetiva": "Tx. part. (%)",
        "CO_ESCOLA": "Código",
    }
    exibir = exibir.rename(columns={k: v for k, v in rename.items() if k in exibir.columns})
    if "Média geral" in exibir.columns:
        exibir["Média geral"] = exibir["Média geral"].round(1)

    st.caption("Escolas do município (2024) — selecione para detalhar:")
    event = st.dataframe(
        exibir,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="terr_mun_esc_select",
    )
    if event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        codigo = sub_esc.iloc[idx].get("CO_ESCOLA")
        ir_para_territorio(
            NIVEL_ESCOLA,
            cre=cre,
            municipio=municipio,
            escola=int(codigo) if pd.notna(codigo) else None,
        )
        st.rerun()


def _vista_escola(tabelas: dict, escola_id: int, municipio: str | None, cre: str | None) -> None:
    df_esc = tabelas.get("escolas_2024", pd.DataFrame())
    if df_esc.empty:
        st.info("Dados de escolas 2024 indisponíveis.")
        return

    sub = df_esc[df_esc["CO_ESCOLA"] == escola_id]
    if sub.empty:
        st.warning(f"Escola {escola_id} não encontrada.")
        return

    row = sub.iloc[0]
    nome = row.get("NOME_ESCOLA", f"Escola {escola_id}")
    titulo_secao(str(nome), f"Código INEP: {escola_id} · 2024")

    col_media = _media_col(sub)
    areas = [
        ("CN", "media_cn"),
        ("CH", "media_ch"),
        ("LC", "media_lc"),
        ("Mat.", "media_mt"),
        ("Redação", "media_redacao"),
        ("Média geral", col_media),
    ]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Média geral", fmt_float(valor_numerico(row, col_media)))
    with c2:
        st.metric("Estudantes", fmt_int(valor_numerico(row, "estudantes")))
    with c3:
        tx = row.get("tx_part_efetiva")
        st.metric("Tx. participação", fmt_float(tx) + "%" if pd.notna(tx) else "—")
    with c4:
        st.metric("Município", str(row.get(_municipio_col(sub), municipio or "—")))

    if cre or row.get("cre"):
        st.caption(f"CRE: **{nome_cre_curto(str(row.get('cre', cre or '—')))}**")

    nomes = [a[0] for a in areas if a[1] in row.index and pd.notna(row.get(a[1]))]
    vals = [float(row[a[1]]) for a in areas if a[1] in row.index and pd.notna(row.get(a[1]))]
    if nomes:
        fig = go.Figure(go.Bar(x=nomes, y=vals, marker_color=AZUL_PRINCIPAL))
        fig.update_layout(title="Notas por área — escola", height=360, yaxis_range=[0, 1000])
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_HUB_CONFIG)

    st.dataframe(
        pd.DataFrame([{
            "Escola": nome,
            "CRE": nome_cre_curto(str(row.get("cre", ""))),
            "Município": row.get(_municipio_col(sub)),
            "Estudantes": int(valor_numerico(row, "estudantes")),
            "Inscritos": int(valor_numerico(row, "inscritos")) if "inscritos" in row.index else None,
            "Média geral": round(valor_numerico(row, col_media), 1),
        }]),
        use_container_width=True,
        hide_index=True,
    )


def render_territory(tabelas: dict) -> None:
    titulo_secao("Território", "Drill-down Estado → CRE → Município → Escola (2024).")

    bc_cols = st.columns([1, 6])
    with bc_cols[0]:
        if st.button("← Voltar ao Hub", key="terr_voltar_hub"):
            ir_para_hub()
            st.rerun()
    with bc_cols[1]:
        _render_breadcrumb()

    labels = [NIVEL_LABELS[n] for n in NIVEIS_TERRITORIO]
    nivel_atual = st.session_state.get("territory_level", NIVEL_ESTADO)
    idx = NIVEIS_TERRITORIO.index(nivel_atual) if nivel_atual in NIVEIS_TERRITORIO else 0

    nivel = st.radio(
        "Nível de detalhe",
        labels,
        index=idx,
        horizontal=True,
        key="terr_nivel_radio",
        label_visibility="collapsed",
    )
    nivel_key = NIVEIS_TERRITORIO[labels.index(nivel)]
    st.session_state.territory_level = nivel_key

    st.caption(
        "**Estado** — ranking de CREs · **CRE** — evolução e municípios · "
        "**Município** — série temporal e escolas · **Escola** — detalhe 2024."
    )

    ano = _ano_ref(tabelas)
    cre = st.session_state.get("selected_cre")
    municipio = st.session_state.get("selected_municipio")
    escola = st.session_state.get("selected_escola")

    if nivel_key == NIVEL_ESTADO:
        _vista_estado(tabelas, ano)
    elif nivel_key == NIVEL_CRE:
        if not cre:
            st.info("Selecione uma CRE na visão Estado ou no Hub.")
            _vista_estado(tabelas, ano)
        else:
            _vista_cre(tabelas, str(cre))
    elif nivel_key == NIVEL_MUNICIPIO:
        if not municipio:
            st.info("Selecione um município na visão CRE.")
            if cre:
                _vista_cre(tabelas, str(cre))
            else:
                _vista_estado(tabelas, ano)
        else:
            _vista_municipio(tabelas, str(municipio), cre)
    elif nivel_key == NIVEL_ESCOLA:
        if not escola:
            st.info("Selecione uma escola na visão Município.")
            if municipio:
                _vista_municipio(tabelas, str(municipio), cre)
            elif cre:
                _vista_cre(tabelas, str(cre))
            else:
                _vista_estado(tabelas, ano)
        else:
            _vista_escola(tabelas, int(escola), municipio, cre)
