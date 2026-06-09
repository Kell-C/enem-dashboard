"""Corpo das funções de `desempenho` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_desempenho(df_filt_ms, tabelas=None, df_notas_individuais=None, anos_sel=None):
    titulo_secao(
        "Desempenho pedagógico — evolução temporal e distribuição",
        "Acompanhamento das notas por área: médias, medianas e dispersão ao longo dos anos."
    )

    # ----- DATAFRAMES DE REFERÊNCIA (agregados; sem bases nacionais sintéticas) -----
    df_est_ms = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    deps_exibir = [
        d for d in ORDEM_DEP if d in df_filt_ms["DEP_ADM"].dropna().unique()]
    tabelas = tabelas or {}
    anos_sel_dist = sorted(df_est_ms["NU_ANO"].dropna().unique())
    df_dist_est = filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=[int(a) for a in anos_sel_dist],
        dependencia="Estadual",
    )
    df_dist_todos = filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=[int(a) for a in anos_sel_dist],
    )

    # Cobertura do agregado de distribuição vs. microdados. Os boxplots leem o
    # parquet distribuicao_ms; se ele cobre menos anos, o gráfico "colapsa" para
    # os poucos anos disponíveis — sinalizamos isso explicitamente nas seções.
    anos_micro_dist = sorted(int(a) for a in anos_sel_dist)
    anos_dist_disp = (
        sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
        if not df_dist_est.empty else []
    )
    anos_faltantes_dist = [a for a in anos_micro_dist if a not in anos_dist_disp]

    def _aviso_cobertura_distribuicao() -> None:
        if anos_faltantes_dist and anos_dist_disp:
            st.warning(
                "O agregado de distribuição (`distribuicao_ms.parquet`) cobre apenas "
                f"{', '.join(str(a) for a in anos_dist_disp)}, mas os microdados têm "
                f"{', '.join(str(a) for a in anos_micro_dist)}. Por isso os boxplots "
                "mostram menos anos que os demais gráficos. Para corrigir, regenere os "
                "agregados: `python gerar_dados_agregados.py`."
            )

    # ===== BARRA DE FILTROS UNIFICADA (camada de status — topo da aba) =====
    anos_disp = sorted(int(a) for a in df_est_ms["NU_ANO"].dropna().unique())
    if not anos_disp:
        st.info("Sem dados de desempenho para o recorte selecionado.")
        return
    area_keys_bar = list(AREAS.keys())
    deps_bar = deps_exibir or ["Estadual"]

    cbar1, cbar2, cbar3 = st.columns(3)
    with cbar1:
        ano_foco = int(st.selectbox(
            "Ano", options=sorted(anos_disp, reverse=True), index=0,
            key="desemp_ano",
        ))
    with cbar2:
        idx_area = area_keys_bar.index("MEDIA_GERAL") if "MEDIA_GERAL" in area_keys_bar else 0
        area_foco = st.selectbox(
            "Área de conhecimento", options=area_keys_bar,
            index=idx_area, format_func=nome_area_ext, key="desemp_area",
        )
    with cbar3:
        idx_dep = deps_bar.index("Estadual") if "Estadual" in deps_bar else 0
        dep_foco = st.selectbox(
            "Dependência", options=deps_bar, index=idx_dep, key="desemp_dep",
        )
    label_area_foco = nome_area_ext(area_foco)

    st.caption(
        "Os indicadores abaixo refletem **ano · área · dependência** selecionados acima. "
        "As distribuições detalhadas e estatísticas anuais referem-se à **rede estadual**; "
        "a comparação entre dependências aparece em seção própria."
    )

    # ===== FAIXA DE KPIs (status) =====
    _df_dep_ms = df_filt_ms[df_filt_ms["DEP_ADM"] == dep_foco]

    def _coluna_notas(df, ano):
        if area_foco not in df.columns:
            return pd.Series(dtype=float)
        return pd.to_numeric(
            df.loc[df["NU_ANO"] == ano, area_foco], errors="coerce"
        ).dropna()

    _col_ms = _coluna_notas(_df_dep_ms, ano_foco)
    _row_dist = df_dist_est[df_dist_est["ano"] == ano_foco] if not df_dist_est.empty else pd.DataFrame()
    _stats_foco = (
        stats_box_quantis(_row_dist.iloc[0], area_foco)
        if not _row_dist.empty and dep_foco == "Estadual" else None
    )
    kpi_media = (
        float(_stats_foco["mean"]) if _stats_foco
        else (_col_ms.mean() if not _col_ms.empty else float("nan"))
    )
    kpi_mediana = (
        float(_stats_foco["median"]) if _stats_foco
        else (_col_ms.median() if not _col_ms.empty else float("nan"))
    )
    kpi_n = int(_stats_foco["n"]) if _stats_foco else int(_col_ms.shape[0])
    kpi_media_br = media_nacional_ponderada(tabelas, ano_foco, area_foco, dep_foco)
    kpi_delta = (
        kpi_media - kpi_media_br
        if (pd.notna(kpi_media) and pd.notna(kpi_media_br)) else float("nan")
    )

    _ano_prev = max((a for a in anos_disp if a < ano_foco), default=None)
    kpi_var = float("nan")
    if _ano_prev is not None and not _col_ms.empty:
        _col_prev = _coluna_notas(_df_dep_ms, _ano_prev)
        if not _col_prev.empty:
            kpi_var = kpi_media - _col_prev.mean()

    def _status_delta(d):
        if pd.isna(d):
            return ""
        if d >= 0:
            return "positivo"
        if d >= -10:
            return "atencao"
        return "critico"

    def _txt_sinal(v):
        if pd.isna(v):
            return "—"
        return ("+" if v >= 0 else "−") + fmt_float(abs(v))

    _sd = _status_delta(kpi_delta)
    _sv = "positivo" if (pd.notna(kpi_var) and kpi_var >= 0) else (
        "critico" if pd.notna(kpi_var) else "")

    _pop_foco = (
        _populacao_estadual_ano(tabelas, ano_foco)
        if dep_foco == "Estadual"
        else {"presentes_filt": None, "taxa_part": None}
    )
    if _pop_foco.get("presentes_filt"):
        _pres_txt = fmt_int(_pop_foco["presentes_filt"])
        _pres_sub = (
            fmt_pct(_pop_foco["taxa_part"]) + " dos concluintes"
            if _pop_foco.get("taxa_part") is not None
            else "presentes 2 dias, sem eliminados"
        )
    else:
        _pres_txt = fmt_int(kpi_n)
        _pres_sub = "estudantes com nota na área"

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    kpi_card(kc1, f"Média · {label_area_foco}", fmt_float(kpi_media),
             f"{ano_foco} · {dep_foco}", _sd)
    kpi_card(kc2, "Δ vs Brasil", _txt_sinal(kpi_delta), "pontos na média", _sd)
    kpi_card(kc3, "Mediana", fmt_float(kpi_mediana), label_area_foco, "")
    kpi_card(kc4, f"Variação vs {_ano_prev if _ano_prev is not None else '—'}",
             _txt_sinal(kpi_var), "na média anual", _sv)
    kpi_card(kc5, "Presentes (estadual)" if dep_foco == "Estadual" else "Estudantes",
             _pres_txt, _pres_sub, "")

    # ----- 1. EVOLUÇÃO POR ÁREA — rede estadual (média + dispersão + Brasil, unificado) -----
    titulo_secao(
        "Evolução por área — rede estadual",
        "Nota média anual por área de conhecimento, com a dispersão interna (faixa "
        "Q1–Q3) e a comparação com o Brasil, em uma única visão."
    )
    st.markdown(
        _legenda_inline([
            f"<span style='color:{AZUL_PRINCIPAL};font-weight:bold;'>━━━</span> Média MS (rede estadual)",
            "<span style='color:#7e8fa6;font-weight:bold;'>- - -</span> Mediana MS",
            "<span style='background:rgba(0,63,127,0.14);padding:2px 6px;border-radius:3px;font-weight:bold;'>▓▓▓</span> Faixa Q1–Q3 (MS)",
            "<span style='color:#5C6B7E;font-weight:bold;'>- ✕ -</span> Média Brasil",
            "<b>Δ%</b> Variação da média no período",
        ]),
        unsafe_allow_html=True,
    )
    _aviso_cobertura_distribuicao()
    fig_evol = _fig_evolucao_unificada(df_dist_est, tabelas=tabelas)
    if fig_evol is None:
        st.info("Sem dados de evolução por área para o período selecionado.")
    else:
        _chart(fig_evol)

    # ----- 3. DISTRIBUIÇÃO DAS NOTAS AO LONGO DOS ANOS — área selecionada | todas as áreas -----
    titulo_secao(
        "Distribuição das notas ao longo dos anos — rede estadual MS",
        "Boxplots por ano (quantis agregados dos microdados): caixa = Q1–Q3, linha central = "
        "mediana, × = média; hastes = limites não-discrepantes (1,5×IQR). Exclui eliminados."
    )
    _aviso_cobertura_distribuicao()
    MODO_DIST_AREA = f"Área selecionada — {label_area_foco}"
    MODO_DIST_TODAS = "Todas as áreas"
    modo_dist = st.radio(
        "Visualização da distribuição",
        [MODO_DIST_AREA, MODO_DIST_TODAS],
        horizontal=True,
        key="desemp_distribuicao_modo",
        label_visibility="collapsed",
    )

    if df_dist_est.empty:
        st.info(
            "Sem dados de distribuição disponíveis para a rede estadual MS. "
            "Regenere os agregados com: python gerar_dados_agregados.py"
        )
    elif modo_dist == MODO_DIST_TODAS:
        st.markdown(
            _legenda_inline([
                "<b>▢</b> Caixa: Q1, mediana, Q3 (×: média)",
                "<b>━</b> Bigodes: limites não-discrepantes (1,5×IQR)",
                "<b>Hover</b>: Máx · Q3 · mediana · Q1 · Mín · n",
                "<em>Recorte:</em> escolas estaduais do MS · presentes 2 dias · sem eliminados",
            ]),
            unsafe_allow_html=True,
        )
        fig_dist_todas = _fig_box_distribuicao_areas(df_dist_est)
        if fig_dist_todas is None:
            st.info("Sem dados de distribuição por área para o período selecionado.")
        else:
            _chart(fig_dist_todas)
    else:
        area_sel = area_foco
        label_area_sel = label_area_foco
        anos_box_area = [str(int(a)) for a in sorted(df_dist_est["ano"].unique().tolist())]

        serie_ms_anual = pd.Series(
            {
                int(r["ano"]): stats_box_quantis(r, area_sel)["mean"]
                for _, r in df_dist_est.iterrows()
                if stats_box_quantis(r, area_sel) is not None
            },
            dtype=float,
        ).sort_index()
        serie_br_anual = serie_media_nacional_dep(
            tabelas,
            [int(a) for a in anos_box_area],
            area_sel,
            "Estadual",
        )

        # Converte índices para string e alinha ao eixo X das caixas
        if not serie_ms_anual.empty:
            serie_ms_anual.index = serie_ms_anual.index.astype(str)
            serie_ms_anual = serie_ms_anual.reindex(anos_box_area).dropna()
        if not serie_br_anual.empty:
            serie_br_anual.index = serie_br_anual.index.astype(str)
            serie_br_anual = serie_br_anual.reindex(anos_box_area).dropna()

        cor_area = AZUL_PRINCIPAL
        fig_box_area = go.Figure()

        # Série única (área selecionada) — um trace com x = anos (evita colapso)
        xs_ano: list[str] = []
        stats_ano: list[dict] = []
        for ano in anos_box_area:
            rows = df_dist_est[df_dist_est["ano"] == int(ano)]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], area_sel)
            if stats is None:
                continue
            xs_ano.append(str(int(ano)))
            stats_ano.append(stats)
        _add_box_series(
            fig_box_area, name=label_area_sel, color=cor_area,
            x_vals=xs_ano, stats_list=stats_ano,
            legendgroup="caixas", showlegend=True, rotulo_mediana=True,
        )

        # Configura eixo X categórico ANTES de adicionar os Scatter
        fig_box_area.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_area,
        )

        # Referências MS/BR — linhas sem rótulo no ponto (evita sobrepor rótulos da caixa)
        if not serie_ms_anual.empty:
            fig_box_area.add_trace(
                go.Scatter(
                    x=serie_ms_anual.index.tolist(),
                    y=serie_ms_anual.values.tolist(),
                    mode="lines+markers",
                    name="Média MS — rede estadual",
                    line=dict(color=AZUL_PRINCIPAL, width=2.5),
                    marker=dict(size=7, color=AZUL_PRINCIPAL, symbol="circle"),
                    legendgroup="medias_ms",
                    showlegend=True,
                    hovertemplate="Média MS: %{y:.1f}<extra></extra>",
                )
            )

        if not serie_br_anual.empty:
            fig_box_area.add_trace(
                go.Scatter(
                    x=serie_br_anual.index.tolist(),
                    y=serie_br_anual.values.tolist(),
                    mode="lines+markers",
                    name="Média BR — rede estadual",
                    line=dict(color=COR_BRASIL, width=2, dash="dot"),
                    marker=dict(size=6, color=COR_BRASIL, symbol="x"),
                    legendgroup="medias_br",
                    showlegend=True,
                    hovertemplate="Média BR: %{y:.1f}<extra></extra>",
                )
            )

        # Range Y fixo (quantis já definem a escala)
        fig_box_area.update_layout(
            title=f"Boxplot anual — {label_area_sel} (rede estadual MS)",
            yaxis=dict(range=[0, 1000], title="Nota"),
            xaxis=dict(title="Ano", type="category"),
            boxmode="group",
        )

        media_ms_global = float(serie_ms_anual.mean()) if not serie_ms_anual.empty else None
        media_br_global = float(serie_br_anual.mean()) if not serie_br_anual.empty else None
        st.markdown(
            _mini_legenda_medias_html(
                media_ms_global, media_br_global,
                sufixo="variação anual",
            ),
            unsafe_allow_html=True,
        )

        fig_box_area = _finalizar_boxplot(
            fig_box_area,
            f"Boxplot anual — {label_area_sel} (rede estadual MS)",
            altura=CHART_H_BOX_WIDE,
            eixo_x="Ano",
            n_legend=3,
        )
        fig_box_area.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_area,
        )
        st.caption(
            "Número acima de cada caixa: mediana do ano. "
            "Passe o mouse para ver Máx, Q3, mediana, Q1, Mín e n. "
            "Linhas: média anual MS (azul) e BR (cinza tracejado)."
        )
        _chart(fig_box_area)

    # ----- 3b. Histogramas + comparação por dependência (camada de detalhe) -----
    anos_presentes = sorted(df_dist_est["ano"].unique()) if not df_dist_est.empty else []
    if not anos_presentes:
        st.info("Nenhum ano disponível para análise por área.")
    else:
        titulo_secao(
            "Distribuição de notas por ano — histogramas e dependências",
            "O ano da barra de filtros (topo da aba) define os histogramas por área "
            "e a comparação entre dependências administrativas. Conteúdo detalhado — "
            "abra o painel abaixo para explorar."
        )
        with st.expander(
            "Abrir histogramas por área e comparação entre dependências",
            expanded=False,
        ):
            _secao_detalhe_ano_desempenho(
                tabelas, ano_foco, df_est_ms,
                df_dist_est, df_dist_todos, deps_exibir, df_notas_individuais,
            )

    # ----- 4. Estatísticas anuais (camada de detalhe — divulgação progressiva) -----
    with st.expander("Estatísticas anuais — rede estadual (tabela detalhada)", expanded=False):
        st.caption(
            f"Indicadores por ano para **{nome_area_ext(area_foco)}**. "
            "Concluintes: rede estadual de MS (planilha SED, quando disponível nos agregados). "
            "Presentes: estudantes presentes nos 2 dias e não eliminados em nenhuma área ou redação."
        )
        if not anos_presentes:
            st.info("Nenhum ano disponível para a área selecionada.")
        else:
            col_media = f"Média · {label_area_foco}"
            linhas_tab = []
            for ano in anos_presentes:
                rows = df_dist_est[df_dist_est["ano"] == ano]
                stats = stats_box_quantis(rows.iloc[0], area_foco) if not rows.empty else None
                pop = _populacao_estadual_ano(tabelas, int(ano))
                part_ano = participacao_ms_por_ano(tabelas, [int(ano)], dep_foco)
                insc_ano = (
                    int(part_ano.iloc[0]["Inscritos"])
                    if not part_ano.empty and pd.notna(part_ano.iloc[0].get("Inscritos")) else None
                )
                tx_insc_ano = (
                    float(part_ano.iloc[0]["Tx_Inscrição"])
                    if not part_ano.empty and pd.notna(part_ano.iloc[0].get("Tx_Inscrição")) else None
                )
                linhas_tab.append({
                    "Ano": str(int(ano)),
                    "Concluintes (estadual)": fmt_int(pop["concluintes"]) if pop["concluintes"] else "—",
                    "Inscritos": fmt_int(insc_ano) if insc_ano else "—",
                    "Tx inscrição": fmt_pct(tx_insc_ano) if tx_insc_ano is not None else "—",
                    "Presentes (2 dias, sem elim.)": fmt_int(pop["presentes_filt"]) if pop["presentes_filt"] else "—",
                    "Tx part. efetiva": fmt_pct(pop["taxa_part"]) if pop["taxa_part"] is not None else "—",
                    col_media: fmt_float(stats["mean"]) if stats is not None else "—",
                    "Mediana": fmt_float(stats["median"]) if stats is not None else "—",
                })
            df_estat_anual = pd.DataFrame(linhas_tab).set_index("Ano")
            st.dataframe(df_estat_anual, width="stretch")

