"""Corpo das funções de `municipios` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_municipios(
    df_ms_enriq,
    df_filt_ms_full=None,
    df_br=None,
    dep_selecionadas=None,
    df_bruta_ms_enriq=None,
    tabelas=None,
    df_notas_individuais=None,
    anos_sel=None,
):
    if dep_selecionadas is None:
        dep_selecionadas = ["Estadual", "Federal", "Municipal", "Privada"]
    tabelas = tabelas or {}
    if anos_sel:
        df_ms_enriq, df_filt_ms_full = _reconstruir_bases_territoriais(
            tabelas, list(anos_sel), dep_selecionadas, df_ms_enriq, df_filt_ms_full,
        )

    titulo_secao(
        "Análise por município",
        "Desempenho municipal com destaques, pontos de atenção e identificação da CRE."
    )

    st.markdown("### Filtros de análise municipal")
    col_filt_dep, col_filt_area = st.columns(2)
    with col_filt_dep:
        dep_escolhido = st.selectbox(
            "Selecione a dependência administrativa",
            options=dep_selecionadas,
            key="dep_municipios"
        )
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_municipios"
        )

    df_base = _df_base_territorial(df_ms_enriq, df_filt_ms_full)
    if "DEP_ADM" not in df_base.columns:
        st.warning("Dados municipais indisponíveis no recorte atual. Recarregue a página ou ajuste os filtros laterais.")
        return
    df_dep = df_base[df_base["DEP_ADM"] == dep_escolhido].copy()
    df_dep_muni = _linhas_nivel_municipio(df_dep)
    tabelas = tabelas or {}
    df_dist_muni = filtrar_distribuicao(
        tabelas.get("distribuicao_municipio", pd.DataFrame()),
        dependencia=dep_escolhido,
    )
    if "CRE" not in df_dep.columns:
        df_dep["CRE"] = pd.NA
    if "CRE" not in df_dep_muni.columns:
        df_dep_muni["CRE"] = pd.NA

    if df_dep_muni.empty and df_dep.empty:
        st.warning(f"Sem dados para {dep_escolhido} no recorte.")
        return

    medias_ref = calcular_medias_referencia(
        df_dep_muni if not df_dep_muni.empty else df_dep,
        df_br, area,
    ) if df_br is not None else {"ms": None, "br": None}

    anos_disponiveis = sorted(df_dep_muni["NU_ANO"].unique()) if not df_dep_muni.empty else sorted(df_dep["NU_ANO"].unique())
    ano_opcoes = [str(ano) for ano in anos_disponiveis] + ["Todos os anos"]
    default_index = len(anos_disponiveis) - 1 if anos_disponiveis else 0

    st.markdown("### Filtro de ano")
    ano_escolhido = st.selectbox(
        "Selecione o ano para análise municipal",
        options=ano_opcoes,
        index=default_index,
        key="ano_municipios"
    )

    if ano_escolhido == "Todos os anos":
        df_filt = df_dep_muni if not df_dep_muni.empty else df_dep
        ano_ref = "Todos os anos"
    else:
        ano_ref = int(ano_escolhido)
        base_muni = df_dep_muni if not df_dep_muni.empty else df_dep
        df_filt = base_muni[base_muni["NU_ANO"] == ano_ref].copy()

    if df_filt.empty:
        st.warning(f"Sem dados para o ano {ano_escolhido}.")
        return

    muni_col = _coluna_municipio(df_filt) or "NO_MUNICIPIO_ESC"
    if muni_col not in df_filt.columns:
        st.warning("Coluna de município indisponível nos dados.")
        return

    m = (df_filt.dropna(subset=[muni_col])
         .groupby(muni_col)
         .agg(
             **{AREAS_COMPLETO[k]: (k, "mean") for k in AREAS.keys()},
             Mediana=(area, "median"),
             Estudantes=(area, "count")
         ).reset_index())
    for k in COLS_NOTAS:
        m[AREAS_COMPLETO[k]] = m[AREAS_COMPLETO[k]].round(1)
    m["Mediana"] = m["Mediana"].round(2)
    m = m[m["Estudantes"] >= 10].sort_values(AREAS_COMPLETO[area], ascending=False)

    part_muni_vis = _participacao_municipio_tabela(
        tabelas, m[muni_col].tolist(), ano_ref, dep_escolhido, col_municipio=muni_col,
    )
    if not part_muni_vis.empty and not m.empty:
        part_muni_vis = _enriquecer_participacao_taxas(part_muni_vis)
        m_vis = m.rename(columns={muni_col: "Município"}).rename(
            columns={AREAS_COMPLETO[area]: "Média"},
        )
        top_vis = m_vis.head(min(15, len(m_vis)))
        part_top = part_muni_vis[part_muni_vis["Município"].isin(top_vis["Município"])]
        if not part_top.empty:
            titulo_secao(f"Desempenho × Participação — municípios ({ano_ref})")
            col_m_c, col_m_q = st.columns([1.55, 1])
            with col_m_c:
                _chart(fig_combo_participacao_desempenho(
                    part_top, top_vis, "Município", "Média",
                    titulo=f"Top municípios — {nome_area_ext(area)}",
                ))
            with col_m_q:
                _chart(fig_quadrante_desempenho_participacao(
                    part_muni_vis, m_vis, "Município", "Média",
                    titulo="Quadrante municipal",
                ))

    st.markdown("### Destaques")
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    if not m.empty:
        media_col = AREAS_COMPLETO[area]
        kpi_card(col_d1, "Maior média", fmt_float(m[media_col].iloc[0]),
                 m.iloc[0][muni_col][:25], status="positivo")
        kpi_card(col_d2, "Menor média", fmt_float(m[media_col].iloc[-1]),
                 m.iloc[-1][muni_col][:25], status="critico")
        idx_max_est = m["Estudantes"].idxmax()
        kpi_card(col_d3, "Mais estudantes", fmt_int(m.loc[idx_max_est, "Estudantes"]),
                 m.loc[idx_max_est, muni_col][:25])
        if medias_ref["ms"] is not None:
            n_abaixo = int((m[media_col] < medias_ref["ms"]).sum())
            kpi_card(col_d4, "Abaixo da média MS", f"{n_abaixo} municípios",
                     f"de {len(m)} analisados", status="atencao" if n_abaixo > len(m)//2 else "neutro")
        else:
            kpi_card(col_d4, "Municípios analisados", fmt_int(len(m)), "")
    else:
        st.info("Sem dados suficientes para destaques.")

    if not m.empty and medias_ref["ms"] is not None:
        st.markdown("### Pontos de atenção")
        idx_max_est = m["Estudantes"].idxmax()
        muni_mais_est = m.loc[idx_max_est]
        media_col = AREAS_COMPLETO[area]
        if muni_mais_est[media_col] < medias_ref["ms"]:
            achado("atencao", "Município com maior volume está abaixo da média",
                   f"{muni_mais_est[muni_col]} tem {fmt_int(muni_mais_est['Estudantes'])} "
                   f"estudantes e média {fmt_float(muni_mais_est[media_col])} (média: {fmt_float(medias_ref['ms'])}).")
        abaixo = m[m[media_col] < medias_ref["ms"]]
        if len(abaixo) > len(m) * 0.5:
            achado("critico", "Maioria dos municípios abaixo da média",
                   f"{len(abaixo)} de {len(m)} ({fmt_float(100*len(abaixo)/len(m))}%).")
        elif len(abaixo) > len(m) * 0.25:
            achado("atencao", "Parte significativa abaixo da média",
                   f"{len(abaixo)} de {len(m)} ({fmt_float(100*len(abaixo)/len(m))}%).")

    col_top, col_bot = st.columns(2)
    with col_top:
        top15 = m.head(15).rename(columns={muni_col: "Município"})
        _chart(fig_ranking_horizontal(
            top15, "Município", AREAS_COMPLETO[area],
            f"Top 15 municípios — {nome_area_ext(area)}",
            cor=COR_POSITIVO, altura=CHART_H_RANKING, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=[0, 1000],
        ))
    with col_bot:
        bot15 = m.tail(15).sort_values(AREAS_COMPLETO[area], ascending=True).rename(columns={muni_col: "Município"})
        _chart(fig_ranking_horizontal(
            bot15, "Município", AREAS_COMPLETO[area],
            f"15 menores médias — {nome_area_ext(area)}",
            cor=COR_CRITICO, altura=CHART_H_RANKING, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=[0, 1000],
        ))

    # ============================================================
    # GRÁFICO DE PARTICIPAÇÃO POR MUNICÍPIO (abaixo do 1º gráfico)
    # ============================================================
    # Construir tabela com concluintes, inscritos (base bruta) e presentes (base filtrada)
    tabela = m.copy().rename(columns={muni_col: "Município"})
    cre_por_muni = (df_filt.dropna(subset=[muni_col, "CRE"])
                    .groupby(muni_col)["CRE"]
                    .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else pd.NA)
                    .reset_index()
                    .rename(columns={muni_col: "Município", "CRE": "CRE"}))
    tabela = tabela.merge(cre_por_muni, on="Município", how="left")

    # Participação municipal via municipios.parquet (presentes, concluintes, taxa efetiva)
    part_muni_agg = _participacao_municipio_tabela(
        tabelas,
        tabela["Município"].tolist(),
        ano_ref,
        dep_escolhido,
        col_municipio=muni_col,
    )
    if not part_muni_agg.empty:
        tabela = tabela.drop(
            columns=["Presentes", "Concluintes", "Inscritos", "Taxa_Efetiva", "Taxa_Part"],
            errors="ignore",
        ).merge(part_muni_agg, on="Município", how="left")
        tabela["Presentes"] = tabela["Presentes"].fillna(tabela["Estudantes"]).astype(int)
        tabela["Concluintes"] = pd.to_numeric(tabela["Concluintes"], errors="coerce").fillna(0).astype(int)
        if "Inscritos" not in tabela.columns:
            tabela["Inscritos"] = tabela["Concluintes"]
        else:
            tabela["Inscritos"] = pd.to_numeric(tabela["Inscritos"], errors="coerce").fillna(0).astype(int)
        tabela["Taxa_Efetiva"] = pd.to_numeric(tabela["Taxa_Efetiva"], errors="coerce")
        tabela["Taxa_Efetiva"] = tabela["Taxa_Efetiva"].fillna(
            tabela["Presentes"] / tabela["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)
    else:
        presentes_muni = (
            df_filt.dropna(subset=[muni_col])
            .groupby(muni_col)
            .agg(Presentes=(area, "count"))
            .reset_index()
            .rename(columns={muni_col: "Município"})
        )
        tabela = tabela.merge(presentes_muni, on="Município", how="left")
        tabela["Presentes"] = tabela["Presentes"].fillna(tabela["Estudantes"]).astype(int)
        tabela["Inscritos"] = tabela["Estudantes"]
        df_conc_muni = carregar_concluintes_municipio()
        if not df_conc_muni.empty and "NU_ANO" in df_conc_muni.columns:
            if ano_escolhido != "Todos os anos":
                df_conc_muni_ano = df_conc_muni[df_conc_muni["NU_ANO"] == int(ano_escolhido)]
            else:
                df_conc_muni_ano = df_conc_muni[df_conc_muni["NU_ANO"] == df_conc_muni["NU_ANO"].max()]
            if not df_conc_muni_ano.empty:
                tabela["_MUNI_KEY"] = tabela["Município"].apply(_normalizar_nome_municipio)
                df_conc_merge = df_conc_muni_ano[["MUNICIPIO", "Concluintes"]].copy()
                df_conc_merge["_MUNI_KEY"] = df_conc_merge["MUNICIPIO"].apply(_normalizar_nome_municipio)
                tabela = tabela.merge(df_conc_merge[["_MUNI_KEY", "Concluintes"]], on="_MUNI_KEY", how="left")
                tabela["Concluintes"] = tabela["Concluintes"].fillna(0).astype(int)
                tabela = tabela.drop(columns=["_MUNI_KEY"])
            else:
                tabela["Concluintes"] = 0
        else:
            tabela["Concluintes"] = 0
        tabela["Taxa_Efetiva"] = (
            tabela["Presentes"] / tabela["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)

    tabela["Taxa_Part"] = tabela["Taxa_Efetiva"]

    tabela["CRE"] = tabela["CRE"].fillna("—").apply(
        lambda x: nome_cre_curto(x) if x != "—" else "—"
    )

    st.markdown("---")
    # Mostrar todos os municípios com inscritos > 0, ordenados por Tx Part. Efetiva (menor primeiro)
    part_muni = tabela[tabela["Inscritos"] > 0].copy()
    if not part_muni.empty:
        # Recalcular taxas para garantir consistência
        part_muni["Diferença"] = (part_muni["Concluintes"] - part_muni["Presentes"]).clip(lower=0)
        part_muni["Dif_Pct"] = (part_muni["Diferença"] / part_muni["Concluintes"].replace(0, pd.NA) * 100).round(1)
        part_muni["Tx_Inscrição"] = (part_muni["Inscritos"] / part_muni["Concluintes"].replace(0, pd.NA) * 100).round(1)
        part_muni["Tx_Part_Efetiva"] = (part_muni["Presentes"] / part_muni["Concluintes"].replace(0, pd.NA) * 100).round(1)

        # Ordenar: primeiro os com menor taxa de participação efetiva (mais críticos)
        part_muni = part_muni.sort_values("Tx_Part_Efetiva", ascending=True, na_position="last")
        n_municipios = len(part_muni)

        titulo_secao(f"Participação por município ({ano_ref}) — {n_municipios} municípios")

        # Identificar municípios com maior diferença (top 3)
        top_dif = part_muni.nlargest(3, "Diferença")[["Município", "Diferença", "Dif_Pct"]]

        fig_part_muni = go.Figure()
        fig_part_muni.add_trace(go.Bar(
            x=part_muni["Município"], y=part_muni["Concluintes"],
            name="Concluintes", marker_color="#6C757D",
            text=part_muni["Concluintes"],
            textposition="outside",
            textfont=dict(size=9, color=TEMA["texto"]),
            hovertemplate="<b>%{x}</b><br>Concluintes: %{y}<extra></extra>",
        ))
        fig_part_muni.add_trace(go.Bar(
            x=part_muni["Município"], y=part_muni["Inscritos"],
            name="Inscritos", marker_color="#0D6EFD",
            text=part_muni["Inscritos"],
            textposition="outside",
            textfont=dict(size=9, color=TEMA["texto"]),
            hovertemplate="<b>%{x}</b><br>Inscritos: %{y}<extra></extra>",
        ))
        fig_part_muni.add_trace(go.Bar(
            x=part_muni["Município"], y=part_muni["Presentes"],
            name="Presentes 2 dias", marker_color="#198754",
            text=part_muni["Presentes"],
            textposition="outside",
            textfont=dict(size=9, color=TEMA["texto"]),
            hovertemplate="<b>%{x}</b><br>Presentes: %{y}<extra></extra>",
        ))
        # Linha de diferença absoluta (Concluintes - Presentes) no eixo y2
        fig_part_muni.add_trace(go.Scatter(
            x=part_muni["Município"], y=part_muni["Diferença"],
            name="Diferença (estudantes)", mode="lines+markers+text",
            line=dict(color=COR_NEGATIVO, width=3),
            marker=dict(size=10, color=COR_NEGATIVO, symbol="diamond"),
            text=[f"{int(v)}" for v in part_muni["Diferença"]],
            textposition="top center",
            textfont=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Diferença: %{y} estudantes<extra></extra>",
        ))
        # Linha Tx_Inscrição (eixo y3 - porcentagem)
        fig_part_muni.add_trace(go.Scatter(
            x=part_muni["Município"], y=part_muni["Tx_Inscrição"],
            name="Tx Inscrição (%)", mode="lines+markers",
            line=dict(color=LARANJA_DESTAQUE, width=2.5),
            marker=dict(size=8, color=LARANJA_DESTAQUE),
            text=[f"{v:.1f}%" for v in part_muni["Tx_Inscrição"]],
            textposition="top center",
            textfont=dict(size=9, color=LARANJA_DESTAQUE),
            yaxis="y3",
            hovertemplate="<b>%{x}</b><br>Tx Inscrição: %{y:.1f}%<extra></extra>",
        ))
        # Linha Tx_Part_Efetiva (eixo y3 - porcentagem)
        fig_part_muni.add_trace(go.Scatter(
            x=part_muni["Município"], y=part_muni["Tx_Part_Efetiva"],
            name="Tx Part. Efetiva (%)", mode="lines+markers",
            line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
            marker=dict(size=8, color=COR_POSITIVO),
            text=[f"{v:.1f}%" for v in part_muni["Tx_Part_Efetiva"]],
            textposition="bottom center",
            textfont=dict(size=9, color=COR_POSITIVO),
            yaxis="y3",
            hovertemplate="<b>%{x}</b><br>Tx Part. Efetiva: %{y:.1f}%<extra></extra>",
        ))
        # Anotações para maiores diferenças (apenas Dif_Pct >= 20% para evitar poluição)
        THRESHOLD_DIF_PCT = 20  # só destaca diferenças >= 20% dos concluintes
        top_dif_criticos = part_muni[part_muni["Dif_Pct"] >= THRESHOLD_DIF_PCT].nlargest(5, "Diferença")
        for idx, (_, row) in enumerate(top_dif_criticos.iterrows()):
            fig_part_muni.add_annotation(
                x=row["Município"],
                y=row["Diferença"],
                text=f"⚠️ {int(row['Diferença'])} ({row['Dif_Pct']:.0f}%)",
                showarrow=True,
                arrowhead=2,
                arrowcolor=COR_NEGATIVO,
                ax=0,
                ay=-35 - (idx * 20),  # stagger vertical para evitar sobreposição
                font=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor=COR_NEGATIVO,
                borderwidth=1,
                yref="y2",
            )

        # Calcular escalas
        max_dif = part_muni["Diferença"].max()
        y2_max = max_dif * 1.3 if pd.notna(max_dif) else 100

        # Configurar largura do gráfico baseada no número de municípios
        # Largura mínima 1000px, +110px por município para boa legibilidade
        chart_width = max(1000, n_municipios * 110)

        # Definir range inicial: mostrar os ~12 primeiros municípios (menor taxa part. efetiva)
        n_inicial = min(12, n_municipios)
        x_inicial = part_muni["Município"].tolist()
        range_x_inicial = [x_inicial[0], x_inicial[n_inicial - 1]] if n_inicial > 1 else None

        fig_part_muni.update_layout(
            title="",
            xaxis=dict(
                title="",
                tickangle=45,
                tickfont=dict(size=11),
                range=range_x_inicial,
                rangeslider=dict(
                    visible=True,
                    thickness=0.06,
                    bgcolor="rgba(200,200,200,0.3)",
                    bordercolor="rgba(200,200,200,0.5)",
                    borderwidth=1,
                ),
            ),
            yaxis=dict(title="Estudantes", side="left", range=[0, part_muni["Concluintes"].max() * 1.15]),
            yaxis2=dict(title="Diferença (estudantes)", overlaying="y", side="right", position=0.98,
                        showgrid=False, range=[0, y2_max], tickfont=dict(size=9)),
            yaxis3=dict(title="Taxa (%)", overlaying="y", side="right", position=1.0,
                        showgrid=False, range=[0, 105], tickfont=dict(size=9),
                        tickvals=[0, 25, 50, 75, 100]),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor=COR_NEUTRO,
                borderwidth=1,
            ),
            margin=dict(t=60, b=140),
            barmode="group",
            bargap=0.25,
            bargroupgap=0.1,
            dragmode=False,
        )

        # Renderizar com scroll desabilitado, apenas range slider
        st.plotly_chart(
            _finalizar_grafico(
                fig_part_muni,
                altura=CHART_H_PARTICIPACAO,
                n_legend=4,
                margin=dict(t=60, r=80, b=140, l=24),
            ),
            config=dict(
                scrollZoom=False,
                displayModeBar=True,
                modeBarButtonsToAdd=["resetScale2d", "select2d", "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d"],
                modeBarButtonsToRemove=["pan2d", "lasso2d"],
            ),
            width=chart_width,
        )

        # Destacar municípios com maior diferença em cards (apenas críticos >= 20%)
        if not top_dif_criticos.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"**🚨 Municípios com diferença crítica (>= {THRESHOLD_DIF_PCT}% dos concluintes):**")
            cols = st.columns(min(len(top_dif_criticos), 3))
            for i, (_, row) in enumerate(top_dif_criticos.iterrows()):
                with cols[i % 3]:
                    st.markdown(
                        f"""
                        <div style="padding:12px; border-radius:8px; background-color:#FFF3F3; border-left:4px solid {COR_NEGATIVO}; margin-bottom:8px;">
                            <strong>{row['Município']}</strong><br>
                            <span style="color:{COR_NEGATIVO}; font-size:1.3em;">⚠️ {int(row['Diferença'])} estudantes</span> não participaram efetivamente<br>
                            <small>({row['Dif_Pct']:.1f}% dos concluintes)</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ============================================================
    # BOXPLOT POR MUNICÍPIO (similar à aba CREs)
    # ============================================================
    st.markdown("---")
    titulo_secao(f"Distribuição das notas por município — {nome_area_ext(area)} ({ano_ref})")

    # Seletor de municípios (top 15 por média como default)
    muni_medias = tabela.sort_values([AREAS_COMPLETO[area]], ascending=False)
    lista_munis = muni_medias["Município"].tolist()

    col_preset_muni, col_sel_muni = st.columns([1, 3])
    with col_preset_muni:
        preset_muni = st.selectbox(
            "Presets de seleção",
            options=["Top 10", "Top 15", "Top 20", "Todos", "Personalizado"],
            key="muni_preset_box",
        )
    with col_sel_muni:
        if preset_muni == "Top 10":
            default_munis = lista_munis[:10]
        elif preset_muni == "Top 15":
            default_munis = lista_munis[:15]
        elif preset_muni == "Top 20":
            default_munis = lista_munis[:20]
        elif preset_muni == "Todos":
            default_munis = lista_munis
        else:
            default_munis = []

        muni_selecionados = st.multiselect(
            "Selecione os municípios",
            options=lista_munis,
            default=default_munis,
            key="muni_boxplot_sel"
        )

    if muni_selecionados:
        df_muni_filt = df_filt[df_filt[muni_col].isin(muni_selecionados)].copy()
        if not df_muni_filt.empty:
            fig_box_muni = go.Figure()
            # Paleta fixa de cores hex
            cores_muni = [
                "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
                "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
                "#3366CC", "#DC3912", "#FF9900", "#109618", "#990099",
                "#0099C6", "#DD4477", "#66AA00", "#B82E2E", "#316395",
            ]
            for i, muni in enumerate(sorted(muni_selecionados)):
                row = linha_distribuicao(
                    df_dist_muni, ano=int(ano_ref),
                    dependencia=dep_escolhido, municipio=muni,
                ) if ano_ref != "Todos os anos" else None
                if row is None:
                    continue
                stats = stats_box_quantis(row, area)
                if stats is None:
                    continue
                cor = cores_muni[i % len(cores_muni)]
                _add_box_stats(
                    fig_box_muni, stats, name=str(muni), color=cor,
                    x_val=str(muni), rotulo_mediana=True,
                    hover_titulo=str(muni),
                )

            if pd.notna(medias_ref["ms"]):
                _adicionar_referencias_ms_br(
                    fig_box_muni, medias_ref["ms"], medias_ref["br"],
                    sufixo_legenda="rede estadual",
                )
            fig_box_muni.update_layout(
                title=f"Distribuição das notas por município — {nome_area_ext(area)} ({ano_ref})",
                yaxis=dict(range=[0, 1000], title="Nota"),
                xaxis=dict(title="", showticklabels=False),
                showlegend=True,
                legend=_legenda_padrao(y_pos=0.98, font_size=11.5),
                margin=dict(t=60, b=60),
                hovermode="closest",
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_box_muni, "Distribuição municipal", altura=CHART_H_BOX, n_legend=2))

    # ============================================================
    # DETALHES POR MUNICÍPIO
    # ============================================================
    st.markdown("---")
    titulo_secao(f"Detalhes por município — {nome_area_ext(area)}")

    # Filtros de seleção
    col_det_muni, col_det_ano, col_det_dep = st.columns(3)
    with col_det_muni:
        muni_detalhe = st.selectbox(
            "Selecione o município",
            options=sorted(tabela["Município"].unique()),
            key="muni_detalhe"
        )
    with col_det_ano:
        anos_muni_disp = sorted(df_dep_muni["NU_ANO"].dropna().unique()) if not df_dep_muni.empty else []
        ano_detalhe = st.selectbox(
            "Selecione o ano",
            options=anos_muni_disp,
            index=len(anos_muni_disp)-1 if anos_muni_disp else 0,
            key="ano_detalhe"
        )
    with col_det_dep:
        dep_detalhe = st.selectbox(
            "Selecione a dependência administrativa",
            options=dep_selecionadas,
            key="dep_detalhe"
        )

    # Filtrar dados para o município selecionado (nível município, sem linhas CRE)
    base_muni_det = df_dep_muni if not df_dep_muni.empty else df_dep
    df_muni_det = base_muni_det[
        (base_muni_det[muni_col] == muni_detalhe) &
        (base_muni_det["NU_ANO"] == ano_detalhe) &
        (base_muni_det["DEP_ADM"] == dep_detalhe)
    ].copy()

    part_muni_det = _participacao_municipio_tabela(
        tabelas, [muni_detalhe], int(ano_detalhe), dep_detalhe, col_municipio=muni_col,
    )
    if not part_muni_det.empty:
        part_muni_det = _enriquecer_participacao_taxas(part_muni_det)
    n_estudantes = (
        int(part_muni_det.iloc[0]["Presentes"])
        if not part_muni_det.empty else len(df_muni_det)
    )
    n_inscritos_muni = (
        int(part_muni_det.iloc[0]["Inscritos"])
        if not part_muni_det.empty and "Inscritos" in part_muni_det.columns else 0
    )
    if dep_detalhe == "Estadual" and not part_muni_det.empty:
        conc_muni_val = int(part_muni_det.iloc[0]["Concluintes"])
        tx_part_efetiva = part_muni_det.iloc[0].get("Tx_Part_Efetiva", part_muni_det.iloc[0].get("Taxa_Efetiva"))
        tx_inscricao_muni = part_muni_det.iloc[0].get("Tx_Inscrição")
        if pd.isna(tx_part_efetiva) and conc_muni_val > 0:
            tx_part_efetiva = round(100 * n_estudantes / conc_muni_val, 1)
        if pd.isna(tx_inscricao_muni) and conc_muni_val > 0 and n_inscritos_muni > 0:
            tx_inscricao_muni = round(100 * n_inscritos_muni / conc_muni_val, 1)
    elif dep_detalhe == "Estadual":
        df_conc_muni = carregar_concluintes_municipio()
        conc_muni_val = 0
        tx_part_efetiva = pd.NA
        if not df_conc_muni.empty:
            conc_row = df_conc_muni[
                (df_conc_muni["MUNICIPIO"].apply(_normalizar_nome_municipio) == _normalizar_nome_municipio(muni_detalhe))
                & (df_conc_muni["NU_ANO"] == ano_detalhe)
            ]
            if not conc_row.empty:
                conc_muni_val = int(conc_row.iloc[0]["Concluintes"])
                if conc_muni_val > 0:
                    tx_part_efetiva = round(100 * n_estudantes / conc_muni_val, 1)
    else:
        conc_muni_val = 0
        tx_part_efetiva = pd.NA
        tx_inscricao_muni = pd.NA

    if not df_muni_det.empty or n_estudantes > 0 or conc_muni_val > 0:
        # ── Calcular Média Geral (média das 5 áreas) ──
        areas_cols = list(AREAS.keys())
        if not df_muni_det.empty:
            df_muni_det["MEDIA_GERAL"] = df_muni_det[areas_cols].mean(axis=1)
            media_geral_muni = df_muni_det["MEDIA_GERAL"].mean()
            mediana_geral_muni = df_muni_det["MEDIA_GERAL"].median()
        else:
            media_geral_muni = np.nan
            mediana_geral_muni = np.nan

        # Cor da borda KPI baseada na taxa de participação
        cor_borda_kpi = COR_POSITIVO if (pd.notna(tx_part_efetiva) and tx_part_efetiva >= 80) else (
            COR_ATENCAO if pd.notna(tx_part_efetiva) and tx_part_efetiva >= 60 else COR_CRITICO
        )

        col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
        media_muni_txt = f"{media_geral_muni:.1f}" if pd.notna(media_geral_muni) else "—"
        mediana_muni_txt = f"{mediana_geral_muni:.1f}" if pd.notna(mediana_geral_muni) else "—"
        with col_kpi1:
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MÉDIA GERAL</div>
                    <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{media_muni_txt}</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi2:
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MEDIANA DA MÉDIA GERAL</div>
                    <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{mediana_muni_txt}</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi3:
            conc_muni_txt = str(conc_muni_val) if dep_detalhe == "Estadual" else "—"
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">CONCLUINTES 3º ANO E.M</div>
                    <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{conc_muni_txt}</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi4:
            tx_insc_str = f"{tx_inscricao_muni:.1f}%".replace(".", ",") if pd.notna(tx_inscricao_muni) else "—"
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {LARANJA_DESTAQUE}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX INSCRIÇÃO</div>
                    <div style="font-size:28px; font-weight:700; color:{LARANJA_DESTAQUE}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_insc_str}</div>
                    <div style="font-size:9px; color:#6c757d; margin-top:4px;">{n_inscritos_muni} inscritos / concluintes</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi5:
            tx_str = f"{tx_part_efetiva:.1f}%".replace(".", ",") if pd.notna(tx_part_efetiva) else "—"
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {cor_borda_kpi}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX PART. EFETIVA</div>
                    <div style="font-size:28px; font-weight:700; color:{cor_borda_kpi}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_str}</div>
                    <div style="font-size:9px; color:#6c757d; margin-top:4px; line-height:1.3;">
                        {n_estudantes} presentes nos 2 dias
                        {f"/ {conc_muni_val} concluintes" if dep_detalhe == "Estadual" else ""}<br>
                        (escolas {dep_detalhe.lower()} do município)
                    </div>
                </div>""", unsafe_allow_html=True)

        # ── Boxplot com todas as áreas ──
        st.markdown(f"**Distribuição das notas — {muni_detalhe} — {ano_detalhe}**")

        fig_box_muni_det = go.Figure()
        cores_areas = {
            "CN": "#2E8B57", "CH": "#FF8C00", "LC": "#1E90FF",
            "MT": "#DC143C", "REDACAO": "#DAA520"
        }

        # Calcular médias de referência MS (estado) e BR
        medias_ref_ms = {}
        medias_ref_br = {}
        if df_br is not None:
            df_br_ano = df_br[(df_br["NU_ANO"] == ano_detalhe) & (df_br["DEP_ADM"] == dep_detalhe)]
            df_ms_ano = base_muni_det[
                (base_muni_det["NU_ANO"] == ano_detalhe) & (base_muni_det["DEP_ADM"] == dep_detalhe)
            ]
            for key in AREAS.keys():
                if not df_ms_ano.empty:
                    medias_ref_ms[key] = df_ms_ano[key].mean()
                if not df_br_ano.empty:
                    medias_ref_br[key] = df_br_ano[key].mean()

        usar_ind_muni = (
            df_notas_individuais is not None
            and not df_notas_individuais.empty
            and tem_notas_individuais_ano(df_notas_individuais, int(ano_detalhe))
        )
        df_muni_ind = (
            filtrar_notas_individuais(
                df_notas_individuais,
                ano=int(ano_detalhe),
                municipio=muni_detalhe,
                dependencia=dep_detalhe,
            )
            if usar_ind_muni else pd.DataFrame()
        )
        row_muni_det = linha_distribuicao(
            df_dist_muni,
            ano=int(ano_detalhe),
            dependencia=dep_detalhe,
            municipio=muni_detalhe,
        )

        for i, (key, nome) in enumerate(AREAS_COMPLETO.items()):
            cor = cores_areas.get(key, CORES_AREAS.get(key, AZUL_PRINCIPAL))
            stats = None
            media_muni_area = np.nan

            if usar_ind_muni and not df_muni_ind.empty:
                s_area = notas_area(df_muni_ind, key)
                if s_area.empty:
                    continue
                stats = _stats_box(s_area)
                if stats is None:
                    continue
                media_muni_area = stats["mean"]
                _add_box(
                    fig_box_muni_det, s_area, nome, cor, x_val=nome,
                    rotulo_mediana=True, hover_titulo=nome,
                )
                _add_scatter_notas(
                    fig_box_muni_det, nome, s_area,
                    color=_hex_to_rgba(cor, 0.35),
                )
            elif row_muni_det is not None:
                stats = stats_box_quantis(row_muni_det, key)
                if stats is None:
                    continue
                media_muni_area = stats["mean"]
                _add_box_stats(
                    fig_box_muni_det, stats, name=nome, color=cor,
                    x_val=nome, rotulo_mediana=True, hover_titulo=nome,
                )
            else:
                continue

            # Delta MS (Estado) - à ESQUERDA
            if key in medias_ref_ms and pd.notna(medias_ref_ms[key]) and medias_ref_ms[key] > 0:
                delta_ms = media_muni_area - medias_ref_ms[key]
                sinal_ms = "+" if delta_ms >= 0 else ""
                cor_delta_ms = COR_POSITIVO if delta_ms >= 0 else COR_CRITICO
                fig_box_muni_det.add_annotation(
                    x=nome,
                    y=stats["up"] + 45,
                    text=f"<b>ΔMS {sinal_ms}{delta_ms:.1f}</b>",
                    showarrow=False,
                    xanchor="right",
                    xshift=-25,
                    font=dict(size=9, color=cor_delta_ms, family="Arial Black"),
                    bgcolor="rgba(255,255,255,0.85)",
                    hovertext=(
                        f"Média {muni_detalhe}: {media_muni_area:.1f}<br>"
                        f"Média Estado (MS): {medias_ref_ms[key]:.1f}<br>"
                        f"Diferença: {sinal_ms}{delta_ms:.1f}"
                    ),
                    hoverlabel=dict(bgcolor="white", font_size=10),
                )

            # Delta BR - à DIREITA
            if key in medias_ref_br and pd.notna(medias_ref_br[key]) and medias_ref_br[key] > 0:
                delta_br = media_muni_area - medias_ref_br[key]
                sinal_br = "+" if delta_br >= 0 else ""
                cor_delta_br = COR_POSITIVO if delta_br >= 0 else COR_CRITICO
                fig_box_muni_det.add_annotation(
                    x=nome,
                    y=stats["up"] + 45,
                    text=f"<b>ΔBR {sinal_br}{delta_br:.1f}</b>",
                    showarrow=False,
                    xanchor="left",
                    xshift=25,
                    font=dict(size=9, color=cor_delta_br, family="Arial Black"),
                    bgcolor="rgba(255,255,255,0.85)",
                    hovertext=(
                        f"Média {muni_detalhe}: {media_muni_area:.1f}<br>"
                        f"Média Brasil: {medias_ref_br[key]:.1f}<br>"
                        f"Diferença: {sinal_br}{delta_br:.1f}"
                    ),
                    hoverlabel=dict(bgcolor="white", font_size=10),
                )

        # Linhas de referência MS e BR para legenda
        fig_box_muni_det.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            line=dict(color=LARANJA_DESTAQUE, width=2, dash="dash"),
            name="Média MS — rede estadual",
            hoverinfo="skip",
        ))
        fig_box_muni_det.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
            name="Média BR — rede estadual",
            hoverinfo="skip",
        ))

        fig_box_muni_det.update_layout(
            title=dict(text=""),
            yaxis=dict(range=[0, 1000], title="Nota"),
            xaxis=dict(title="", showticklabels=False),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=10, color=TEMA["texto"]),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor=COR_NEUTRO,
                borderwidth=1,
                itemsizing="constant",
            ),
            margin=dict(t=60, b=140),
            plot_bgcolor="rgba(250,252,255,1)",
            paper_bgcolor="#FFFFFF",
        )
        _chart(_finalizar_boxplot(fig_box_muni_det, f"Detalhe — {muni_detalhe}", altura=CHART_H_BOX, n_legend=1))

        if usar_ind_muni and not df_muni_ind.empty:
            s_hist_muni = notas_area(df_muni_ind, area)
            if not s_hist_muni.empty:
                titulo_secao(
                    f"Histograma — {nome_area_ext(area)}",
                    f"Distribuição individual dos estudantes do município ({len(s_hist_muni):,} com nota válida)."
                )
                _chart(_fig_histogram_notas(
                    s_hist_muni,
                    f"Distribuição — {muni_detalhe} ({nome_area_ext(area)}, 2024)",
                    cor=CORES_AREAS.get(area, AZUL_PRINCIPAL),
                    media_ref=medias_ref_ms.get(area),
                ))

        # ── Legendas explicativas ──
        st.markdown(
            """<div style="display: flex; gap: 20px; margin: 8px 0 12px; font-size: 12px; flex-wrap: wrap;">
                <div><span style="color: #198754; font-weight: bold;">ΔMS</span> = diferença vs média do Estado</div>
                <div><span style="color: #198754; font-weight: bold;">ΔBR</span> = diferença vs média do Brasil</div>
                <div><span style="color: #198754;">■</span> acima da média <span style="color: #DC2626;">■</span> abaixo da média</div>
            </div>""", unsafe_allow_html=True
        )

        # ── Legenda de cores das áreas ──
        cores_legenda = " ".join([
            f"<span style='color: {cores_areas.get(k, CORES_AREAS.get(k, AZUL_PRINCIPAL))}; font-weight: bold;'>●</span> {nome_area_ext(k)}"
            for k in AREAS.keys()
        ])
        st.markdown(
            f"""<div style="display: flex; gap: 16px; margin: 4px 0 16px; font-size: 11px; flex-wrap: wrap; color: #6c757d;">
                {cores_legenda}
            </div>""", unsafe_allow_html=True
        )
        if ano_detalhe == 2024 and ("NOME_ESCOLA" in df_muni_det.columns or "NO_ENTIDADE" in df_muni_det.columns):
            st.markdown(f"**Escolas em {muni_detalhe} ({ano_detalhe}) — {dep_detalhe}**")
            st.markdown(
                "<div style='font-size:12px; color:#6B7280; margin-bottom:8px;'>"
                "🟢↑ Acima da média &nbsp;|&nbsp; 🔴↓ Abaixo da média &nbsp;|&nbsp; "
                "MS=Média MS estadual &nbsp;|&nbsp; BR=Média BR estadual"
                "</div>",
                unsafe_allow_html=True
            )
            col_escola = "NOME_ESCOLA" if "NOME_ESCOLA" in df_muni_det.columns else "NO_ENTIDADE"

            # Agregar por escola com todas as áreas
            escolas_agg = df_muni_det.groupby(col_escola).agg(
                Estudantes=(area, "count"),
                **{AREAS_COMPLETO[k]: (k, "mean") for k in COLS_NOTAS},
            ).reset_index()

            # Calcular Média Geral
            areas_cols_agg = [AREAS_COMPLETO[k] for k in COLS_NOTAS]
            escolas_agg["Média Geral"] = escolas_agg[areas_cols_agg].mean(axis=1)

            # Buscar concluintes por escola
            df_conc_esc = carregar_concluintes()
            if not df_conc_esc.empty and "CO_ESCOLA" in df_muni_det.columns:
                # Mapear escolas por código
                escolas_conc = df_muni_det[[col_escola, "CO_ESCOLA"]].drop_duplicates()
                conc_por_escola = df_conc_esc[
                    (df_conc_esc["NU_ANO"] == 2024) &
                    (df_conc_esc["CO_ESCOLA"].isin(escolas_conc["CO_ESCOLA"]))
                ][["CO_ESCOLA", "Concluintes"]].set_index("CO_ESCOLA")["Concluintes"].to_dict()

                escolas_agg["Concluintes"] = escolas_agg[col_escola].map(
                    escolas_conc.set_index(col_escola)["CO_ESCOLA"].map(conc_por_escola)
                ).fillna(0).astype(int)
            else:
                escolas_agg["Concluintes"] = 0

            # Calcular taxa de participação efetiva
            escolas_agg["Tx_Part_Efetiva"] = (
                escolas_agg["Estudantes"] / escolas_agg["Concluintes"].replace(0, pd.NA) * 100
            )

            # Arredondar médias
            for k in COLS_NOTAS:
                escolas_agg[AREAS_COMPLETO[k]] = escolas_agg[AREAS_COMPLETO[k]].apply(lambda x: round(x, 1) if pd.notna(x) else pd.NA)

            # Renomear colunas para exibição
            rename_map = {col_escola: "Escola", "Estudantes": "Participantes"}
            escolas_display = escolas_agg.rename(columns=rename_map)

            # Reordenar colunas: Escola → Concluintes → Participantes → Tx Part. Efetiva → [áreas] → Média Geral
            colunas_ordem = ["Escola", "Concluintes", "Participantes", "Tx_Part_Efetiva"]
            for k in COLS_NOTAS:
                colunas_ordem.append(AREAS_COMPLETO[k])
            colunas_ordem.append("Média Geral")

            # Garantir que todas as colunas existam
            colunas_final = [c for c in colunas_ordem if c in escolas_display.columns]
            escolas_display = escolas_display[colunas_final]

            # Ordenar por média da área principal
            escolas_display = escolas_display.sort_values(AREAS_COMPLETO[area], ascending=False)

            # Criar cópia para estilização
            escolas_styled = escolas_display.copy()

            # Formatar para exibição
            for col in escolas_styled.columns:
                if col == "Concluintes":
                    escolas_styled[col] = escolas_styled[col].apply(lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—")
                elif col == "Tx_Part_Efetiva":
                    escolas_styled[col] = escolas_styled[col].apply(lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—")
                elif col in [AREAS_COMPLETO[k] for k in AREAS.keys()]:
                    escolas_styled[col] = escolas_styled[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—")

            # ============================================================
            # ESTILIZAÇÃO VIA FUNÇÃO UTILITÁRIA
            # ============================================================
            area_labels_muni = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
            if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in escolas_display.columns:
                area_labels_muni["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

            styled_muni, css_cabecalho_muni = _estilizar_tabela(
                df_display=escolas_styled,
                df_raw=escolas_display,
                colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in escolas_styled.columns],
                cores_area=CORES_AREAS,
                medias_ms=medias_ref_ms,
                medias_br=medias_ref_br,
                area_labels=area_labels_muni,
            )

            # CSS customizado para cabeçalhos coloridos
            if css_cabecalho_muni:
                st.markdown(f"""
                <style>
                {css_cabecalho_muni}
                </style>
                """, unsafe_allow_html=True)

            n_escolas = len(escolas_styled)
            altura_escolas = min(max(n_escolas * 35 + 45, 100), 520)
            st.dataframe(styled_muni, width="stretch", hide_index=True, height=altura_escolas)

    else:
        st.info(f"Sem dados para {muni_detalhe} em {ano_detalhe} — {dep_detalhe}.")

    st.markdown("---")
    titulo_secao("Tabela completa — municípios")
    st.markdown(
        "<div style='font-size:12px; color:#6B7280; margin-bottom:8px;'>"
        "🟢↑ Acima da média &nbsp;|&nbsp; 🔴↓ Abaixo da média &nbsp;|&nbsp; "
        "MS=Média MS estadual &nbsp;|&nbsp; BR=Média BR estadual"
        "</div>",
        unsafe_allow_html=True
    )

    # Selecionar colunas para exibição: Município, CRE, Concluintes, Taxa_Efetiva, e todas as áreas
    cols_display = ["Município", "CRE", "Concluintes", "Taxa_Efetiva"]
    for k in COLS_NOTAS:
        col_nome = AREAS_COMPLETO[k]
        if col_nome in tabela.columns:
            cols_display.append(col_nome)
    tabela_raw = tabela[cols_display].copy()
    tabela_display = tabela_raw.copy()
    # Formatar Taxa_Efetiva como string com %
    tabela_display["Taxa_Efetiva"] = tabela_raw["Taxa_Efetiva"].apply(lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—")

    # Formatar colunas numéricas (áreas) com vírgula decimal
    for k in COLS_NOTAS:
        col_name = AREAS_COMPLETO[k]
        if col_name in tabela_display.columns:
            tabela_display[col_name] = tabela_raw[col_name].apply(
                lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—"
        )
    # Calcular médias de referência MS e BR para TODAS as áreas
    medias_ref_ms_muni = {}
    medias_ref_br_muni = {}

    ano_ref_muni = int(ano_escolhido) if ano_escolhido != "Todos os anos" else None

    for k in COLS_NOTAS:
        # MS: média do estado (df_dep já filtrado por dependência)
        medias_ref_ms_muni[k] = float(df_dep_muni[k].dropna().mean()) if not df_dep_muni.empty else (
            float(df_dep[k].dropna().mean()) if not df_dep.empty else np.nan
        )

        # BR: média do Brasil (mesmo ano e dependência)
        if df_br is not None and ano_ref_muni is not None:
            df_br_ref = df_br[(df_br["NU_ANO"] == ano_ref_muni) & (df_br["DEP_ADM"] == dep_escolhido)]
            medias_ref_br_muni[k] = float(df_br_ref[k].dropna().mean()) if not df_br_ref.empty else np.nan
        else:
            medias_ref_br_muni[k] = np.nan



    # --- 3. Preparar area_labels ---
    area_labels_muni = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela.columns:
        area_labels_muni["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

    # --- 4. Chamar _estilizar_tabela ---
    styled_muni_total, css_cabecalho_muni_total = _estilizar_tabela(
        df_display=tabela_display,
        df_raw=tabela[cols_display],  # versão numérica bruta
        colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in tabela.columns],
        cores_area=CORES_AREAS,
        medias_ms=medias_ref_ms_muni,
        medias_br=medias_ref_br_muni,
        col_escola="Município",
        tx_col="Taxa_Efetiva",
        concluintes_col="Concluintes",
        area_labels=area_labels_muni,
    )

    # --- 5. Renderizar ---
    if css_cabecalho_muni_total:
        st.markdown(f"<style>{css_cabecalho_muni_total}</style>", unsafe_allow_html=True)

    n_muni_total = len(tabela_display)
    altura_muni_total = min(max(n_muni_total * 35 + 45, 100), 520)
    st.dataframe(styled_muni_total, width="stretch", hide_index=True, height=altura_muni_total)

