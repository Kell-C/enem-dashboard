"""Corpo das funções de `territorial` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_territorial(
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
        "Análise territorial",
        "Desempenho das escolas distribuído por CRE, com evolução temporal. "
        "Escolha a dependência administrativa abaixo."
    )

    st.markdown("### Filtros de análise territorial")
    col_filt_dep, col_filt_area = st.columns(2)
    with col_filt_dep:
        dep_escolhido = st.selectbox(
            "Selecione a dependência administrativa",
            options=dep_selecionadas,
            key="dep_territorial"
        )
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_territorial"
        )

    df_base = _df_base_territorial(df_ms_enriq, df_filt_ms_full)
    if "DEP_ADM" not in df_base.columns:
        st.warning("Dados territoriais indisponíveis no recorte atual. Recarregue a página ou ajuste os filtros laterais.")
        return
    df_dep = df_base[df_base["DEP_ADM"] == dep_escolhido].copy()
    df_dep_cre = _linhas_nivel_cre(df_dep)
    df_dep_muni = _linhas_nivel_municipio(df_dep)
    df_dist_cre = filtrar_distribuicao(
        tabelas.get("distribuicao_cre", pd.DataFrame()),
        dependencia=dep_escolhido,
    )

    if "CRE" not in df_dep.columns:
        df_dep["CRE"] = pd.NA
    if "CRE" not in df_dep_cre.columns:
        df_dep_cre["CRE"] = pd.NA

    if df_dep_cre.empty and df_dep.empty:
        st.warning(f"Sem dados para a dependência {dep_escolhido} no recorte atual.")
        return

    if tabelas:
        ano_ref_ini = int(df_dep_cre["NU_ANO"].max()) if not df_dep_cre.empty else (
            int(df_dep["NU_ANO"].max()) if not df_dep.empty else None
        )
        refs = medias_referencia_por_ano(tabelas, ano_ref_ini) if ano_ref_ini else {}
        medias_ref = refs.get(area, {})
        if not medias_ref:
            medias_ref = calcular_medias_referencia(
                df_dep_cre if not df_dep_cre.empty else df_dep,
                df_br[df_br["DEP_ADM"] == dep_escolhido] if df_br is not None else pd.DataFrame(),
                area,
            )
    elif df_br is not None:
        medias_ref = calcular_medias_referencia(
            df_dep_cre if not df_dep_cre.empty else df_dep,
            df_br[df_br["DEP_ADM"] == dep_escolhido], area,
        )
    else:
        medias_ref = {"ms": None, "br": None}

    titulo_secao("Evolução temporal das CREs")
    cre_selecionadas = []
    lista_cres = []
    if df_dep_cre.empty or df_dep_cre["CRE"].isna().all():
        st.info("Dados de CRE não encontrados. Verifique o arquivo CRES.")
    else:
        lista_cres = sorted(df_dep_cre["CRE"].dropna().unique())

    # Paleta de cores para até 12 CREs - alta saturacao e contraste
    _PALETA_CRE = [
        "#0033CC", "#FF4500", "#00AA44", "#CC0000",
        "#0099CC", "#FF8C00", "#8800CC", "#CC0066",
        "#0066FF", "#FFD700", "#444444", "#008080",
    ]

    if lista_cres:
        # Calcular médias gerais para ordenar e sugerir default
        ranking_cre = (df_dep_cre.groupby("CRE", observed=True)[area]
                       .mean().round(2).sort_values(ascending=False))

        # Seleção com presets
        col_preset, col_sel = st.columns([1, 3])
        with col_preset:
            preset = st.selectbox(
                "Presets de seleção",
                options=["Todas", "Top 5", "Top 3", "Bottom 5", "Personalizado"],
                key="cre_preset",
            )
        with col_sel:
            if preset == "Todas":
                default_cres = lista_cres
            elif preset == "Top 5":
                default_cres = ranking_cre.head(5).index.tolist()
            elif preset == "Top 3":
                default_cres = ranking_cre.head(3).index.tolist()
            elif preset == "Bottom 5":
                default_cres = ranking_cre.tail(5).index.tolist()
            else:
                default_cres = []

            cre_selecionadas = st.multiselect(
                "Selecione as CREs que deseja visualizar",
                options=lista_cres,
                default=default_cres,
                format_func=nome_cre_curto,
                key="cre_territorial"
            )

        if cre_selecionadas:
            df_cre_evol = df_dep_cre[df_dep_cre["CRE"].isin(cre_selecionadas)].copy()
            if not df_cre_evol.empty and df_cre_evol["NU_ANO"].nunique() > 0:
                evol = df_cre_evol.groupby(["CRE", "NU_ANO"], observed=True)[area].mean().reset_index(name="Média")
                evol = evol.dropna(subset=["Média"])
                if not evol.empty:
                    fig_evol_cre = go.Figure()
                    for idx, cre in enumerate(cre_selecionadas):
                        df_cre_evo = evol[evol["CRE"] == cre]
                        if df_cre_evo.empty:
                            continue
                        cor = _PALETA_CRE[idx % len(_PALETA_CRE)]
                        fig_evol_cre.add_trace(go.Bar(
                            x=df_cre_evo["NU_ANO"], y=df_cre_evo["Média"].round(2),
                            name=nome_cre_curto(cre),
                            marker=dict(color=_hex_rgba(cor, 0.7), line=dict(color=cor, width=2)),
                            hovertemplate=f"<b>{cre}</b><br>Ano: %{{x}}<br>Média: %{{y:.2f}}<extra></extra>",
                        ))

                    # Linhas dinâmicas de referência MS e BR (média por ano)
                    anos_plot = sorted(evol["NU_ANO"].unique())
                    if not df_dep_cre.empty:
                        media_ms_ano = (df_dep_cre.groupby("NU_ANO", observed=True)[area]
                                        .mean().round(2).reindex(anos_plot).dropna())
                        if not media_ms_ano.empty:
                            fig_evol_cre.add_trace(go.Scatter(
                                x=media_ms_ano.index, y=media_ms_ano.values,
                                name="Média MS", mode="lines+markers+text",
                                line=dict(color=AZUL_PRINCIPAL, width=2.5, dash="dash"),
                                marker=dict(size=8, color=AZUL_PRINCIPAL),
                                text=[f"{v:.1f}" for v in media_ms_ano.values],
                                textposition="top left",
                                textfont=dict(size=12, color=AZUL_PRINCIPAL, family="Arial Black"),
                                hovertemplate="<b>Média MS</b><br>Ano: %{x}<br>Média: %{y:.2f}<extra></extra>",
                            ))
                    if df_br is not None and not df_br.empty:
                        df_br_est = df_br[df_br["DEP_ADM"] == "Estadual"].copy()
                        media_br_ano = (df_br_est.groupby("NU_ANO", observed=True)[area]
                                        .mean().round(2).reindex(anos_plot).dropna())
                        if not media_br_ano.empty:
                            fig_evol_cre.add_trace(go.Scatter(
                                x=media_br_ano.index, y=media_br_ano.values,
                                name="Média BR", mode="lines+markers+text",
                                line=dict(color=COR_BRASIL, width=2.5, dash="dot"),
                                marker=dict(size=8, color=COR_BRASIL),
                                text=[f"{v:.1f}" for v in media_br_ano.values],
                                textposition="top right",
                                textfont=dict(size=12, color=COR_BRASIL, family="Arial Black"),
                                hovertemplate="<b>Média BR</b><br>Ano: %{x}<br>Média: %{y:.2f}<extra></extra>",
                            ))

                    fig_evol_cre.update_layout(
                        title=f"Evolução da média — {nome_area_ext(area)}",
                        xaxis=dict(tickmode="linear", dtick=1, title=""),
                        yaxis=dict(
                            title=dict(text="Nota", font=dict(size=14, color=TEMA["texto"])),
                            range=[0, 1000],
                            tickfont=dict(size=12),
                        ),
                        hovermode="x unified",
                        barmode="group",
                        bargap=0.15,
                        bargroupgap=0.1,
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.35,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=9),
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor=COR_NEUTRO,
                            borderwidth=1,
                        ),
                        margin=dict(t=60, r=120, b=180),
                        annotations=[
                            dict(
                                x=1.12, y=0.5, xref="paper", yref="paper",
                                text="Escala:<br><b>0 – 1000</b>",
                                showarrow=False,
                                font=dict(size=13, color=TEMA["texto"], family="Arial Black"),
                                align="center",
                                bgcolor="rgba(255,255,255,0.9)",
                                bordercolor=COR_NEUTRO,
                                borderwidth=1,
                                borderpad=6,
                            )
                        ],
                    )
                    _chart(_finalizar_grafico(fig_evol_cre, altura=CHART_H_EVOLUCAO, n_legend=4))

                    # ----- GRÁFICO DE EVOLUÇÃO DAS TAXAS DE PARTICIPAÇÃO POR CRE -----
                    titulo_secao(
                        "Evolução da taxa de participação efetiva por CRE",
                        "Percentual de concluintes do 3º ano que compareceram nos dois dias de prova, ao longo dos anos."
                    )

                    df_part_evol = filtrar_participacao_cre(
                        tabelas, dependencia=dep_escolhido,
                    )
                    taxas_evol = []
                    for cre in cre_selecionadas:
                        for ano in sorted(df_dep["NU_ANO"].dropna().unique()):
                            if df_part_evol.empty:
                                part = _presentes_cre_ano(
                                    tabelas, cre, int(ano), dep_escolhido,
                                ) or len(df_dep_cre[
                                    (df_dep_cre["CRE"] == cre)
                                    & (df_dep_cre["NU_ANO"] == ano)
                                ])
                                if part <= 0:
                                    continue
                                taxas_evol.append({
                                    "CRE": cre, "Ano": int(ano), "Taxa": pd.NA,
                                    "Concluintes": pd.NA, "Presentes": part,
                                })
                                continue
                            hit = df_part_evol[
                                (df_part_evol["CRE"] == cre) & (df_part_evol["ano"] == int(ano))
                            ]
                            if hit.empty:
                                continue
                            row = hit.iloc[0]
                            part = int(row.get("estudantes", 0) or 0)
                            conc_rows = _concluintes_cre_por_ano([cre], int(ano))
                            conc = (
                                conc_rows.iloc[0]["Concluintes"]
                                if not conc_rows.empty else pd.NA
                            )
                            taxa = (
                                round(100 * part / float(conc), 1)
                                if pd.notna(conc) and float(conc) > 0 else pd.NA
                            )
                            if part > 0 or (pd.notna(conc) and float(conc) > 0):
                                taxas_evol.append({
                                    "CRE": cre, "Ano": int(ano),
                                    "Taxa": float(taxa) if pd.notna(taxa) else pd.NA,
                                    "Concluintes": int(conc) if pd.notna(conc) else pd.NA,
                                    "Presentes": part,
                                })

                    if taxas_evol:
                        df_taxas_evol = pd.DataFrame(taxas_evol).dropna(subset=["Taxa"])
                    if taxas_evol and not df_taxas_evol.empty:
                        fig_taxas_evol = go.Figure()
                        for idx, cre in enumerate(cre_selecionadas):
                            df_cre_taxa = df_taxas_evol[df_taxas_evol["CRE"] == cre]
                            if df_cre_taxa.empty:
                                continue
                            cor = _PALETA_CRE[idx % len(_PALETA_CRE)]
                            fig_taxas_evol.add_trace(go.Bar(
                                x=df_cre_taxa["Ano"], y=df_cre_taxa["Taxa"],
                                name=nome_cre_curto(cre),
                                marker=dict(color=_hex_rgba(cor, 0.65), line=dict(color=cor, width=1.5)),
                                text=[f"{v:.1f}%" for v in df_cre_taxa["Taxa"]],
                                textposition="outside",
                                textfont=dict(size=10, color=cor,
                                              family="Source Sans 3, system-ui, sans-serif"),
                                hovertemplate=(
                                    f"<b>{cre}</b><br>"
                                    "Ano: %{x}<br>"
                                    "Taxa efetiva: %{y:.1f}%<br>"
                                    "Concluintes: %{customdata[0]}<br>"
                                    "Presentes: %{customdata[1]}"
                                    "<extra></extra>"
                                ),
                                customdata=df_cre_taxa[["Concluintes", "Presentes"]].values,
                            ))

                        # Linha de referência: taxa MS estadual (presentes ÷ concluintes)
                        taxas_ms_ano = []
                        for ano in sorted(df_dep["NU_ANO"].dropna().unique()):
                            taxa_ms = _taxa_part_efetiva_ms(tabelas, int(ano), dep_escolhido)
                            if taxa_ms is not None:
                                taxas_ms_ano.append({"Ano": int(ano), "Taxa": taxa_ms})
                        if taxas_ms_ano:
                            df_ms_taxa = pd.DataFrame(taxas_ms_ano)
                            fig_taxas_evol.add_trace(go.Scatter(
                                x=df_ms_taxa["Ano"], y=df_ms_taxa["Taxa"],
                                name="Taxa MS (rede)", mode="lines+markers",
                                line=dict(color=AZUL_PRINCIPAL, width=2.5, dash="dash"),
                                marker=dict(size=8, color=AZUL_PRINCIPAL),
                                hovertemplate=(
                                    "<b>Taxa MS (rede)</b><br>"
                                    "Ano: %{x}<br>Taxa efetiva: %{y:.1f}%<extra></extra>"
                                ),
                            ))

                        fig_taxas_evol.update_layout(
                            xaxis=dict(tickmode="linear", dtick=1, title="Ano", type="category"),
                            yaxis=dict(
                                title="Taxa (%)", range=[0, 105], ticksuffix="%",
                            ),
                            barmode="group",
                            bargap=0.15,
                            bargroupgap=0.1,
                        )
                        n_leg_taxa = min(len(cre_selecionadas) + 1, 6)
                        _chart(_finalizar_grafico(
                            fig_taxas_evol,
                            titulo="Taxa de participação efetiva por CRE — evolução temporal",
                            altura=CHART_H_RANKING,
                            n_legend=n_leg_taxa,
                            hover_unified=True,
                        ))
                    elif taxas_evol:
                        st.info("Taxa de participação efetiva indisponível para as CREs selecionadas.")
                    else:
                        st.info(
                            "Dados de participação por CRE indisponíveis. "
                            "Verifique participacao_cre.parquet nos agregados."
                        )
                else:
                    st.info("Sem dados de evolução para as CREs selecionadas.")
            else:
                st.info("Sem dados de evolução temporal para as CREs selecionadas.")
        else:
            st.warning("Selecione ao menos uma CRE.")
    else:
        st.info("Nenhuma CRE encontrada nos dados.")

    st.markdown("---")
    anos_disponiveis = sorted(df_dep_cre["NU_ANO"].unique()) if not df_dep_cre.empty else sorted(df_dep["NU_ANO"].unique())
    ano_opcoes = [str(ano) for ano in anos_disponiveis] + ["Todos os anos"]
    default_index = len(anos_disponiveis) - 1 if anos_disponiveis else 0

    st.markdown("### Filtro de ano")
    ano_escolhido = st.selectbox(
        "Selecione o ano para análise territorial",
        options=ano_opcoes,
        index=default_index,
        key="ano_territorial"
    )

    if ano_escolhido == "Todos os anos":
        df_dep_cre_filt = df_dep_cre
        ano_ref = "Todos os anos"
    else:
        ano_ref = int(ano_escolhido)
        df_dep_cre_filt = df_dep_cre[df_dep_cre["NU_ANO"] == ano_ref].copy()

    if df_dep_cre_filt.empty:
        st.warning(f"Sem dados para o ano {ano_escolhido}.")
        return

    # Recalcular médias de referência para o ano selecionado (alinha com o primeiro gráfico)
    df_br_ano = df_br[df_br["NU_ANO"] == ano_ref] if (df_br is not None and ano_ref != "Todos os anos") else df_br
    medias_ref = calcular_medias_referencia(
        df_dep_cre_filt,
        df_br_ano[df_br_ano["DEP_ADM"] == dep_escolhido] if df_br_ano is not None else None,
        area,
    ) if df_br is not None else {"ms": None, "br": None}

    # Gráfico de participação por CRE (concluintes / presentes / taxa efetiva)
    if lista_cres and cre_selecionadas and "CRE" in df_dep_cre_filt.columns:
        part_cre = _participacao_cre_tabela(
            tabelas, cre_selecionadas, ano_ref, dep_escolhido,
        )
        if part_cre.empty:
            presentes = (
                df_dep_cre_filt[df_dep_cre_filt["CRE"].isin(cre_selecionadas)]
                .groupby("CRE", observed=True)
                .agg(Presentes=(area, "count"))
                .reset_index()
            )
            part_cre = presentes.copy()
            part_cre["Concluintes"] = pd.NA
            part_cre["Tx_Part_Efetiva"] = pd.NA
        if not part_cre.empty:
            part_cre["Concluintes"] = pd.to_numeric(part_cre["Concluintes"], errors="coerce")
            part_cre["Presentes"] = pd.to_numeric(part_cre["Presentes"], errors="coerce").fillna(0).astype(int)
            part_cre = _enriquecer_participacao_taxas(part_cre)

            if not part_cre.empty:
                titulo_secao(f"Participação por CRE ({ano_ref})")
                st.caption(
                    "Concluintes: planilha do 3º ano (escola → CRE). "
                    "Inscritos e presentes: microdado ENEM. "
                    "Tx inscrição = inscritos ÷ concluintes · Tx part. efetiva = presentes ÷ concluintes. "
                    + (
                        "Barra de inscritos indisponível nos agregados — execute "
                        "`python gerar_dados_agregados.py` para atualizar."
                        if "Inscritos" not in part_cre.columns or part_cre["Inscritos"].isna().all()
                        else ""
                    )
                )

                # Calcular diferença Concluintes - Presentes
                part_cre["Diferença"] = (part_cre["Concluintes"] - part_cre["Presentes"]).clip(lower=0)
                part_cre["Dif_Pct"] = _pct_taxa(part_cre["Diferença"], part_cre["Concluintes"])
                part_cre["_cre_x"] = part_cre["CRE"].map(nome_cre_curto)

                # Identificar CREs com maior diferença (top 3; ignora CREs sem concluintes)
                top_dif = (
                    part_cre.dropna(subset=["Concluintes", "Diferença"])
                    .nlargest(3, "Diferença")[["CRE", "Diferença", "Dif_Pct"]]
                )

                fig_part_cre = go.Figure()
                fig_part_cre.add_trace(go.Bar(
                    x=part_cre["_cre_x"], y=part_cre["Concluintes"],
                    name="Concluintes", marker_color="#6C757D",
                    text=[fmt_int(v) if pd.notna(v) else "—" for v in part_cre["Concluintes"]],
                    textposition="outside",
                    textfont=dict(size=9, color=TEMA["texto"]),
                    hovertemplate="<b>%{x}</b><br>Concluintes: %{y}<extra></extra>",
                ))
                if "Inscritos" in part_cre.columns and part_cre["Inscritos"].notna().any():
                    fig_part_cre.add_trace(go.Bar(
                        x=part_cre["_cre_x"], y=part_cre["Inscritos"],
                        name="Inscritos", marker_color="#0D6EFD",
                        text=[fmt_int(v) if pd.notna(v) else "—" for v in part_cre["Inscritos"]],
                        textposition="inside",
                        textfont=dict(size=9, color=TEMA["texto"]),
                        hovertemplate="<b>%{x}</b><br>Inscritos: %{y}<extra></extra>",
                    ))
                fig_part_cre.add_trace(go.Bar(
                    x=part_cre["_cre_x"], y=part_cre["Presentes"],
                    name="Presentes 2 dias", marker_color="#198754",
                    text=part_cre["Presentes"],
                    textposition="outside",
                    textfont=dict(size=9, color=TEMA["texto"]),
                    hovertemplate="<b>%{x}</b><br>Presentes: %{y}<extra></extra>",
                ))
                # Linha de diferenca absoluta (Concluintes - Presentes) no eixo y2
                fig_part_cre.add_trace(go.Scatter(
                    x=part_cre["_cre_x"], y=part_cre["Diferença"],
                    name="Diferença (estudantes)", mode="lines+markers+text",
                    line=dict(color=COR_NEGATIVO, width=3),
                    marker=dict(size=10, color=COR_NEGATIVO, symbol="diamond"),
                    text=[fmt_int(v) for v in part_cre["Diferença"]],
                    textposition="top center",
                    textfont=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
                    yaxis="y2",
                    hovertemplate="<b>%{x}</b><br>Diferença: %{y} estudantes<extra></extra>",
                ))
                if "Tx_Inscrição" in part_cre.columns:
                    fig_part_cre.add_trace(go.Scatter(
                        x=part_cre["_cre_x"], y=part_cre["Tx_Inscrição"],
                        name="Tx inscrição (%)", mode="lines+markers",
                        line=dict(color=LARANJA_DESTAQUE, width=2.5),
                        marker=dict(size=8, color=LARANJA_DESTAQUE),
                        yaxis="y3",
                        hovertemplate="<b>%{x}</b><br>Tx inscrição: %{y:.1f}%<extra></extra>",
                    ))
                fig_part_cre.add_trace(go.Scatter(
                    x=part_cre["_cre_x"], y=part_cre["Tx_Part_Efetiva"],
                    name="Tx Part. Efetiva (%)", mode="lines+markers",
                    line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
                    marker=dict(size=8, color=COR_POSITIVO),
                    text=[fmt_pct(v) for v in part_cre["Tx_Part_Efetiva"]],
                    textposition="bottom center",
                    textfont=dict(size=9, color=COR_POSITIVO),
                    yaxis="y3",
                    hovertemplate="<b>%{x}</b><br>Tx Part. Efetiva: %{y:.1f}%<extra></extra>",
                ))
                # Anotacoes para maiores diferencas
                for _, row in top_dif.iterrows():
                    fig_part_cre.add_annotation(
                        x=nome_cre_curto(row["CRE"]),
                        y=row["Diferença"],
                        text=f"⚠️ {fmt_int(row['Diferença'])} ({fmt_pct(row['Dif_Pct'], 0)})",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor=COR_NEGATIVO,
                        ax=0,
                        ay=-40,
                        font=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
                        bgcolor="rgba(255,255,255,0.9)",
                        bordercolor=COR_NEGATIVO,
                        borderwidth=1,
                        yref="y2",
                    )

                # Calcular escalas
                max_dif = part_cre["Diferença"].max()
                y2_max = max_dif * 1.3 if pd.notna(max_dif) else 100
                max_conc = part_cre["Concluintes"].max()
                y1_max = max_conc * 1.15 if pd.notna(max_conc) else part_cre["Presentes"].max() * 1.15

                fig_part_cre.update_layout(
                    title="",
                    xaxis=dict(title="", tickangle=0, tickfont=dict(size=10)),
                    yaxis=dict(title="Estudantes", side="left", range=[0, y1_max]),
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
                        font=dict(size=10),
                        bgcolor="rgba(255,255,255,0.8)",
                        bordercolor=COR_NEUTRO,
                        borderwidth=1,
                    ),
                    margin=dict(t=60, b=140),
                    barmode="group",
                )
                _chart(_finalizar_grafico(
                    fig_part_cre,
                    altura=CHART_H_BOX,
                    n_legend=4,
                    margin=dict(t=60, r=80, b=140, l=24),
                ))

                # Destacar CREs com maior diferenca em cards
                if not top_dif.empty:
                    st.markdown("<br>")
                    cols = st.columns(min(len(top_dif), 3))
                    for i, (_, row) in enumerate(top_dif.iterrows()):
                        with cols[i]:
                            st.markdown(
                                f"""
                                <div style="padding:10px; border-radius:8px; background-color:#FFF3F3; border-left:4px solid {COR_NEGATIVO};">
                                    <strong>{nome_cre_curto(row['CRE'])}</strong><br>
                                    <span style="color:{COR_NEGATIVO}; font-size:1.2em;">⚠️ {fmt_int(row['Diferença'])} estudantes</span> não participaram efetivamente<br>
                                    <small>({fmt_pct(row['Dif_Pct'])} dos concluintes)</small>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
        st.markdown("---")

    if lista_cres and cre_selecionadas and "CRE" in df_dep_cre_filt.columns:
        titulo_secao(f"Desempenho por CRE ({ano_ref})")
        df_cre_filt = df_dep_cre_filt[df_dep_cre_filt["CRE"].isin(cre_selecionadas)].copy()
        if not df_cre_filt.empty:
            c = (df_cre_filt.groupby("CRE", observed=True)[area]
                 .agg(Média="mean", Mediana="median", Estudantes="count").reset_index())
            c["Média"] = c["Média"].round(2)
            c["Mediana"] = c["Mediana"].round(2)
            c = c.sort_values("Média", ascending=False)

            part_integrada = _participacao_cre_tabela(
                tabelas, c["CRE"].tolist(), ano_ref, dep_escolhido,
            )
            if not part_integrada.empty:
                part_integrada = _enriquecer_participacao_taxas(part_integrada)
                titulo_secao(f"Desempenho × Participação — CREs ({ano_ref})")
                col_combo, col_quad = st.columns([1.55, 1])
                with col_combo:
                    _chart(fig_combo_participacao_desempenho(
                        part_integrada, c, "CRE", "Média",
                        titulo=f"Funil e média — {nome_area_ext(area)}",
                    ))
                with col_quad:
                    _chart(fig_quadrante_desempenho_participacao(
                        part_integrada, c, "CRE", "Média",
                        titulo="Quadrante: participação × desempenho",
                    ))
                st.caption(
                    "Quadrante: acima da mediana em ambos os eixos = CREs com boa adesão e bom desempenho."
                )

            col_cre_top, col_cre_bot = st.columns(2)
            with col_cre_top:
                cre_top = c.head(10).sort_values("Média", ascending=True)
                _chart(fig_ranking_horizontal(
                    cre_top, "CRE", "Média",
                    f"Top CREs — {nome_area_ext(area)}",
                    cor=AZUL_PRINCIPAL, altura=CHART_H_EVOLUCAO, casas_decimais=2,
                    media_ms=medias_ref["ms"], media_br=medias_ref["br"],
                    x_range=[0, 1000],
                ))
            with col_cre_bot:
                cre_bot = c.tail(10).sort_values("Média", ascending=True)
                _chart(fig_ranking_horizontal(
                    cre_bot, "CRE", "Média",
                    f"CREs com menores médias — {nome_area_ext(area)}",
                    cor=LARANJA_DESTAQUE, altura=CHART_H_EVOLUCAO, casas_decimais=2,
                    media_ms=medias_ref["ms"], media_br=medias_ref["br"],
                    x_range=[0, 1000],
                ))

            fig_box_cre = go.Figure()
            # Paleta fixa de cores hex (evita problemas com formatos rgb)
            cores_cre = [
                "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
                "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
                "#3366CC", "#DC3912", "#FF9900", "#109618", "#990099",
                "#0099C6", "#DD4477", "#66AA00", "#B82E2E", "#316395",
            ]
            for i, cre in enumerate(sorted(df_cre_filt["CRE"].unique())):
                row = linha_distribuicao(
                    df_dist_cre, ano=int(ano_ref),
                    dependencia=dep_escolhido, cre=cre,
                )
                if row is None:
                    continue
                stats = stats_box_quantis(row, area)
                if stats is None:
                    continue
                cor = cores_cre[i % len(cores_cre)]
                _add_box_stats(
                    fig_box_cre, stats, name=nome_cre_curto(cre), color=cor,
                    x_val=nome_cre_curto(cre), rotulo_mediana=True,
                    hover_titulo=str(cre),
                )

            if pd.notna(medias_ref["ms"]):
                _adicionar_referencias_ms_br(
                    fig_box_cre, medias_ref["ms"], medias_ref["br"],
                    sufixo_legenda="rede estadual",
                )
            fig_box_cre.update_layout(
                title=f"Distribuição das notas por CRE — {nome_area_ext(area)} ({ano_ref})",
                yaxis=dict(range=[0, 1000], title="Nota"),
                xaxis=dict(title="", showticklabels=False),
                showlegend=True,
                legend=_legenda_padrao(y_pos=-0.22, font_size=11.5),
                margin=dict(t=60, b=100),
                hovermode="closest",
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_box_cre, "Distribuição por CRE", altura=CHART_H_BOX, n_legend=2))

             # ============================================================
            # DETALHES DOS MUNICÍPIOS POR CRE
            # ============================================================
            st.markdown("---")
            titulo_secao(f"Detalhes dos municípios por CRE — {ano_ref}")

            # Seletores de CRE, ano e dependência
            col_det_cre, col_det_ano_cre, col_det_dep_cre = st.columns(3)
            with col_det_cre:
                cre_detalhe = st.selectbox(
                    "Selecione a CRE",
                    options=sorted(df_cre_filt["CRE"].dropna().unique()) if not df_cre_filt.empty else [],
                    format_func=nome_cre_curto,
                    key="cre_detalhe"
                )
            with col_det_ano_cre:
                anos_cre_disp = sorted(df_dep_cre["NU_ANO"].dropna().unique()) if not df_dep_cre.empty else []
                ano_detalhe_cre = st.selectbox(
                    "Selecione o ano",
                    options=anos_cre_disp,
                    index=len(anos_cre_disp)-1 if anos_cre_disp else 0,
                    key="ano_detalhe_cre"
                )
            with col_det_dep_cre:
                dep_detalhe_cre = st.selectbox(
                    "Selecione a dependência administrativa",
                    options=dep_selecionadas,
                    key="dep_detalhe_cre"
                )

            # CRE: linhas agregadas (evolucao_cre) — sem duplicar municípios
            df_cre_det = df_dep_cre[
                (df_dep_cre["CRE"] == cre_detalhe) &
                (df_dep_cre["NU_ANO"] == ano_detalhe_cre) &
                (df_dep_cre["DEP_ADM"] == dep_detalhe_cre)
            ].copy()
            df_muni_cre_det = df_dep_muni[
                (df_dep_muni["CRE"] == cre_detalhe) &
                (df_dep_muni["NU_ANO"] == ano_detalhe_cre) &
                (df_dep_muni["DEP_ADM"] == dep_detalhe_cre)
            ].copy()

            n_estudantes_cre = _presentes_cre_ano(
                tabelas, cre_detalhe, int(ano_detalhe_cre), dep_detalhe_cre,
            )
            n_inscritos_cre = _inscritos_cre_ano(
                tabelas, cre_detalhe, int(ano_detalhe_cre), dep_detalhe_cre,
            )
            if dep_detalhe_cre == "Estadual":
                conc_rows = _concluintes_cre_por_ano([cre_detalhe], int(ano_detalhe_cre))
                conc_cre_val = (
                    _safe_int_val(conc_rows.iloc[0]["Concluintes"])
                    if not conc_rows.empty else 0
                )
            else:
                conc_cre_val = 0
            tx_part_efetiva_cre = (
                round(100 * n_estudantes_cre / conc_cre_val, 1)
                if conc_cre_val > 0 else pd.NA
            )
            tx_inscricao_cre = (
                round(100 * n_inscritos_cre / conc_cre_val, 1)
                if conc_cre_val > 0 and n_inscritos_cre > 0 else pd.NA
            )

            if not df_cre_det.empty or n_estudantes_cre > 0 or conc_cre_val > 0:
                areas_cols = list(AREAS.keys())
                if not df_cre_det.empty:
                    df_cre_det["MEDIA_GERAL"] = df_cre_det[areas_cols].mean(axis=1)
                    media_geral_cre = df_cre_det["MEDIA_GERAL"].mean()
                    mediana_geral_cre = df_cre_det["MEDIA_GERAL"].median()
                else:
                    media_geral_cre = np.nan
                    mediana_geral_cre = np.nan

                # Cor da borda KPI
                cor_borda_kpi_cre = COR_POSITIVO if (pd.notna(tx_part_efetiva_cre) and tx_part_efetiva_cre >= 80) else (
                    COR_ATENCAO if pd.notna(tx_part_efetiva_cre) and tx_part_efetiva_cre >= 60 else COR_CRITICO
                )

                col_kpi1_cre, col_kpi2_cre, col_kpi3_cre, col_kpi4_cre, col_kpi5_cre = st.columns(5)
                media_geral_txt = f"{media_geral_cre:.1f}" if pd.notna(media_geral_cre) else "—"
                mediana_geral_txt = f"{mediana_geral_cre:.1f}" if pd.notna(mediana_geral_cre) else "—"
                with col_kpi1_cre:
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MÉDIA GERAL</div>
                            <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{media_geral_txt}</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi2_cre:
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MEDIANA DA MÉDIA GERAL</div>
                            <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{mediana_geral_txt}</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi3_cre:
                    conc_cre_txt = str(conc_cre_val) if dep_detalhe_cre == "Estadual" else "—"
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">CONCLUINTES 3º ANO E.M</div>
                            <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{conc_cre_txt}</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi4_cre:
                    tx_insc_str = f"{tx_inscricao_cre:.1f}%".replace(".", ",") if pd.notna(tx_inscricao_cre) else "—"
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {LARANJA_DESTAQUE}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX INSCRIÇÃO</div>
                            <div style="font-size:28px; font-weight:700; color:{LARANJA_DESTAQUE}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_insc_str}</div>
                            <div style="font-size:9px; color:#6c757d; margin-top:4px;">{n_inscritos_cre} inscritos / concluintes</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi5_cre:
                    tx_str_cre = f"{tx_part_efetiva_cre:.1f}%".replace(".", ",") if pd.notna(tx_part_efetiva_cre) else "—"
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {cor_borda_kpi_cre}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX PART. EFETIVA</div>
                            <div style="font-size:28px; font-weight:700; color:{cor_borda_kpi_cre}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_str_cre}</div>
                            <div style="font-size:9px; color:#6c757d; margin-top:4px; line-height:1.3;">
                                {n_estudantes_cre} presentes nos 2 dias
                                {f"/ {conc_cre_val} concluintes" if dep_detalhe_cre == "Estadual" else ""}<br>
                                (escolas {dep_detalhe_cre.lower()} da CRE)
                            </div>
                        </div>""", unsafe_allow_html=True)

                # Boxplot com todas as áreas
                st.markdown(f"**Distribuição das notas — {cre_detalhe} — {ano_detalhe_cre}**")

                fig_box_cre_det = go.Figure()
                cores_areas_cre = {
                    "CN": "#2E8B57", "CH": "#FF8C00", "LC": "#1E90FF",
                    "MT": "#DC143C", "REDACAO": "#DAA520"
                }

                # Calcular médias de referência MS e BR
                medias_ref_ms_cre_det = {}
                medias_ref_br_cre_det = {}
                if df_br is not None:
                    df_br_ano_cre = df_br[(df_br["NU_ANO"] == ano_detalhe_cre) & (df_br["DEP_ADM"] == dep_detalhe_cre)]
                    df_ms_ano_cre = df_dep_cre[
                        (df_dep_cre["NU_ANO"] == ano_detalhe_cre)
                        & (df_dep_cre["DEP_ADM"] == dep_detalhe_cre)
                    ]
                    for key in AREAS.keys():
                        if not df_ms_ano_cre.empty:
                            medias_ref_ms_cre_det[key] = df_ms_ano_cre[key].mean()
                        if not df_br_ano_cre.empty:
                            medias_ref_br_cre_det[key] = df_br_ano_cre[key].mean()

                usar_ind_cre = (
                    df_notas_individuais is not None
                    and not df_notas_individuais.empty
                    and tem_notas_individuais_ano(df_notas_individuais, int(ano_detalhe_cre))
                )
                df_cre_ind = (
                    filtrar_notas_individuais(
                        df_notas_individuais,
                        ano=int(ano_detalhe_cre),
                        cre=cre_detalhe,
                        dependencia=dep_detalhe_cre,
                    )
                    if usar_ind_cre else pd.DataFrame()
                )
                row_cre_det = linha_distribuicao(
                    df_dist_cre, ano=int(ano_detalhe_cre),
                    dependencia=dep_detalhe_cre, cre=cre_detalhe,
                )

                for i, (key, nome) in enumerate(AREAS_COMPLETO.items()):
                    cor_cre = cores_areas_cre.get(key, CORES_AREAS.get(key, AZUL_PRINCIPAL))
                    stats = None
                    media_cre_area = np.nan

                    if usar_ind_cre and not df_cre_ind.empty:
                        s_area = notas_area(df_cre_ind, key)
                        if s_area.empty:
                            continue
                        stats = _stats_box(s_area)
                        if stats is None:
                            continue
                        media_cre_area = stats["mean"]
                        _add_box(
                            fig_box_cre_det, s_area, nome, cor_cre, x_val=nome,
                            rotulo_mediana=True, hover_titulo=nome,
                        )
                        _add_scatter_notas(
                            fig_box_cre_det, nome, s_area,
                            color=_hex_to_rgba(cor_cre, 0.35),
                        )
                    elif row_cre_det is not None:
                        stats = stats_box_quantis(row_cre_det, key)
                        if stats is None:
                            continue
                        media_cre_area = stats["mean"]
                        _add_box_stats(
                            fig_box_cre_det, stats, name=nome, color=cor_cre,
                            x_val=nome, rotulo_mediana=True, hover_titulo=nome,
                        )
                    else:
                        continue

                    # Delta MS
                    if key in medias_ref_ms_cre_det and pd.notna(medias_ref_ms_cre_det[key]) and medias_ref_ms_cre_det[key] > 0:
                        delta_ms_cre = media_cre_area - medias_ref_ms_cre_det[key]
                        sinal_ms_cre = "+" if delta_ms_cre >= 0 else ""
                        cor_delta_ms_cre = COR_POSITIVO if delta_ms_cre >= 0 else COR_CRITICO
                        fig_box_cre_det.add_annotation(
                            x=nome,
                            y=stats["up"] + 45,
                            text=f"<b>ΔMS {sinal_ms_cre}{delta_ms_cre:.1f}</b>",
                            showarrow=False,
                            xanchor="right",
                            xshift=-25,
                            font=dict(size=9, color=cor_delta_ms_cre, family="Arial Black"),
                            bgcolor="rgba(255,255,255,0.85)",
                            hovertext=(
                                f"Média {cre_detalhe}: {media_cre_area:.1f}<br>"
                                f"Média Estado (MS): {medias_ref_ms_cre_det[key]:.1f}<br>"
                                f"Diferença: {sinal_ms_cre}{delta_ms_cre:.1f}"
                            ),
                            hoverlabel=dict(bgcolor="white", font_size=10),
                        )

                    # Delta BR
                    if key in medias_ref_br_cre_det and pd.notna(medias_ref_br_cre_det[key]) and medias_ref_br_cre_det[key] > 0:
                        delta_br_cre = media_cre_area - medias_ref_br_cre_det[key]
                        sinal_br_cre = "+" if delta_br_cre >= 0 else ""
                        cor_delta_br_cre = COR_POSITIVO if delta_br_cre >= 0 else COR_CRITICO
                        fig_box_cre_det.add_annotation(
                            x=nome,
                            y=stats["up"] + 45,
                            text=f"<b>ΔBR {sinal_br_cre}{delta_br_cre:.1f}</b>",
                            showarrow=False,
                            xanchor="left",
                            xshift=25,
                            font=dict(size=9, color=cor_delta_br_cre, family="Arial Black"),
                            bgcolor="rgba(255,255,255,0.85)",
                            hovertext=(
                                f"Média {cre_detalhe}: {media_cre_area:.1f}<br>"
                                f"Média Brasil: {medias_ref_br_cre_det[key]:.1f}<br>"
                                f"Diferença: {sinal_br_cre}{delta_br_cre:.1f}"
                            ),
                            hoverlabel=dict(bgcolor="white", font_size=10),
                        )

                # Linhas de referência MS e BR
                fig_box_cre_det.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode="lines",
                    line=dict(color=LARANJA_DESTAQUE, width=2, dash="dash"),
                    name="Média MS — rede estadual",
                    hoverinfo="skip",
                ))
                fig_box_cre_det.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode="lines",
                    line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
                    name="Média BR — rede estadual",
                    hoverinfo="skip",
                ))

                fig_box_cre_det.update_layout(
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
                _chart(_finalizar_boxplot(fig_box_cre_det, f"Detalhe CRE — {cre_detalhe}", altura=CHART_H_BOX, n_legend=1))

                if usar_ind_cre and not df_cre_ind.empty:
                    s_hist_cre = notas_area(df_cre_ind, area)
                    if not s_hist_cre.empty:
                        titulo_secao(
                            f"Histograma — {nome_area_ext(area)}",
                            f"Distribuição individual dos estudantes da CRE ({len(s_hist_cre):,} com nota válida)."
                        )
                        _chart(_fig_histogram_notas(
                            s_hist_cre,
                            f"Distribuição — {cre_detalhe} ({nome_area_ext(area)}, 2024)",
                            cor=CORES_AREAS.get(area, AZUL_PRINCIPAL),
                            media_ref=medias_ref_ms_cre_det.get(area),
                        ))

                # Legendas explicativas
                st.markdown(
                    """<div style="display: flex; gap: 20px; margin: 8px 0 12px; font-size: 12px; flex-wrap: wrap;">
                        <div><span style="color: #198754; font-weight: bold;">ΔMS</span> = diferença vs média do Estado</div>
                        <div><span style="color: #198754; font-weight: bold;">ΔBR</span> = diferença vs média do Brasil</div>
                        <div><span style="color: #198754;">■</span> acima da média <span style="color: #DC2626;">■</span> abaixo da média</div>
                    </div>""", unsafe_allow_html=True
                )

                # Legenda de cores das áreas
                cores_legenda_cre = " ".join([
                    f"<span style='color: {cores_areas_cre.get(k, CORES_AREAS.get(k, AZUL_PRINCIPAL))}; font-weight: bold;'>●</span> {nome_area_ext(k)}"
                    for k in AREAS.keys()
                ])
                st.markdown(
                    f"""<div style="display: flex; gap: 16px; margin: 4px 0 16px; font-size: 11px; flex-wrap: wrap; color: #6c757d;">
                        {cores_legenda_cre}
                    </div>""", unsafe_allow_html=True
                )

                # Tabela de municípios da CRE
                st.markdown(f"**Municípios da {cre_detalhe} ({ano_detalhe_cre}) — {dep_detalhe_cre}**")

                # Agregar por município
                muni_col_cre = "NO_MUNICIPIO_ESC"
                if not df_muni_cre_det.empty and muni_col_cre in df_muni_cre_det.columns:
                    muni_agg = df_muni_cre_det.groupby(muni_col_cre, observed=True).agg(
                        Estudantes=(area, "count"),
                        **{AREAS_COMPLETO[k]: (k, "mean") for k in AREAS.keys()},
                    ).reset_index()
                    muni_agg = muni_agg.rename(columns={muni_col_cre: "Município"})

                    part_muni_cre = _participacao_municipio_tabela(
                        tabelas,
                        muni_agg["Município"].tolist(),
                        int(ano_detalhe_cre),
                        dep_detalhe_cre,
                        col_municipio=muni_col_cre,
                    )
                    if not part_muni_cre.empty:
                        muni_agg = muni_agg.drop(
                            columns=["Concluintes", "Tx_Part_Efetiva", "Presentes"],
                            errors="ignore",
                        ).merge(
                            part_muni_cre[["Município", "Presentes", "Concluintes", "Taxa_Efetiva"]],
                            on="Município",
                            how="left",
                        )
                        muni_agg["Estudantes"] = muni_agg["Presentes"].fillna(muni_agg["Estudantes"]).astype(int)
                        muni_agg["Tx_Part_Efetiva"] = muni_agg.get("Tx_Part_Efetiva", muni_agg.get("Taxa_Efetiva"))
                        if "Tx_Inscrição" not in muni_agg.columns:
                            muni_agg["Tx_Inscrição"] = _pct_taxa(
                                muni_agg.get("Inscritos", pd.NA), muni_agg["Concluintes"],
                            )
                        muni_agg = muni_agg.drop(columns=["Presentes", "Taxa_Efetiva"], errors="ignore")
                    elif dep_detalhe_cre == "Estadual":
                        df_conc_muni_cre = carregar_concluintes_municipio()
                        if not df_conc_muni_cre.empty:
                            for idx_muni, row_muni in muni_agg.iterrows():
                                muni_nome = row_muni["Município"]
                                conc_row_muni = df_conc_muni_cre[
                                    (df_conc_muni_cre["MUNICIPIO"].apply(_normalizar_nome_municipio) == _normalizar_nome_municipio(muni_nome))
                                    & (df_conc_muni_cre["NU_ANO"] == ano_detalhe_cre)
                                ]
                                muni_agg.at[idx_muni, "Concluintes"] = (
                                    _safe_int_val(conc_row_muni.iloc[0]["Concluintes"])
                                    if not conc_row_muni.empty else 0
                                )
                        else:
                            muni_agg["Concluintes"] = 0
                        muni_agg["Concluintes"] = pd.to_numeric(muni_agg["Concluintes"], errors="coerce").fillna(0).astype(int)
                        muni_agg["Tx_Part_Efetiva"] = _pct_taxa(muni_agg["Estudantes"], muni_agg["Concluintes"])
                    else:
                        muni_agg["Concluintes"] = pd.NA
                        muni_agg["Tx_Part_Efetiva"] = pd.NA

                    # Arredondar médias
                    for k in COLS_NOTAS:
                        muni_agg[AREAS_COMPLETO[k]] = muni_agg[AREAS_COMPLETO[k]].round(1)

                    # Reordenar colunas
                    cols_muni = ["Município", "Concluintes", "Inscritos", "Tx_Inscrição", "Tx_Part_Efetiva"]
                    for k in COLS_NOTAS:
                        cols_muni.append(AREAS_COMPLETO[k])
                    muni_agg = muni_agg[[c for c in cols_muni if c in muni_agg.columns]]

                    # Ordenar por média geral
                    if AREAS_COMPLETO.get("MEDIA_GERAL") in muni_agg.columns:
                        muni_agg = muni_agg.sort_values(AREAS_COMPLETO["MEDIA_GERAL"], ascending=False)

                    # Calcular médias de referência para coloração
                    medias_ref_ms_muni = {}
                    medias_ref_br_muni = {}
                    for k in COLS_NOTAS:
                        medias_ref_ms_muni[k] = float(df_muni_cre_det[k].dropna().mean()) if not df_muni_cre_det.empty else (
                            float(df_cre_det[k].dropna().mean()) if not df_cre_det.empty else np.nan
                        )
                        if df_br is not None:
                            df_br_ano_muni = df_br[(df_br["NU_ANO"] == ano_detalhe_cre) & (df_br["DEP_ADM"] == dep_detalhe_cre)]
                            medias_ref_br_muni[k] = float(df_br_ano_muni[k].dropna().mean()) if not df_br_ano_muni.empty else np.nan
                        else:
                            medias_ref_br_muni[k] = np.nan

                    # Formatar para exibição
                    muni_display = muni_agg.copy()
                    for col in muni_display.columns:
                        if col in ("Concluintes", "Inscritos"):
                            muni_display[col] = muni_display[col].apply(lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—")
                        elif col in ("Tx_Part_Efetiva", "Tx_Inscrição"):
                            muni_display[col] = muni_display[col].apply(lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—")
                        elif col in [AREAS_COMPLETO[k] for k in AREAS.keys()]:
                            muni_display[col] = muni_display[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—")

                    # Estilização
                    area_labels_muni_cre = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
                    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in muni_agg.columns:
                        area_labels_muni_cre["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

                    styled_muni_cre, css_cabecalho_muni_cre = _estilizar_tabela(
                        df_display=muni_display,
                        df_raw=muni_agg,
                        colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in muni_agg.columns],
                        cores_area=CORES_AREAS,
                        medias_ms=medias_ref_ms_muni,
                        medias_br=medias_ref_br_muni,
                        col_escola="Município",
                        area_labels=area_labels_muni_cre,
                    )

                    if css_cabecalho_muni_cre:
                        st.markdown(f"""
                        <style>
                        {css_cabecalho_muni_cre}
                        </style>
                        """, unsafe_allow_html=True)

                    st.markdown("""
                    <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
                        <b>Fonte das médias:</b> <span style='color: #059669;'>verde</span> = acima MS e BR,
                        <span style='color: #2563EB;'>azul</span> = acima de MS e abaixo de BR,
                        <span style='color: #DC2626;'>vermelho</span> = abaixo de ambos |
                        <b>Cores das áreas:</b> fundo colorido conforme legenda dos gráficos
                    </div>
                    """, unsafe_allow_html=True)

                    n_muni = len(muni_display)
                    altura_muni = min(max(n_muni * 35 + 45, 100), 520)
                    st.dataframe(styled_muni_cre, width="stretch", hide_index=True, height=altura_muni)
                else:
                    st.info("Dados de município não disponíveis para esta CRE.")
            else:
                st.info(f"Sem dados para {cre_detalhe} em {ano_detalhe_cre} — {dep_detalhe_cre}.")

            st.markdown("---")
            titulo_secao(f"Tabela completa de desempenho — CREs ({ano_ref})")

            # Calcular médias de referência MS/BR por área para comparação
            # MS: df_dep_cre_filt (nível CRE, sem duplicar municípios) | BR: df_br no ano_ref e dep
            medias_ref_ms_cre = {}
            medias_ref_br_cre = {}
            for col in COLS_NOTAS:
                medias_ref_ms_cre[col] = float(df_dep_cre_filt[col].dropna().mean()) if not df_dep_cre_filt.empty else np.nan
                if df_br is not None and ano_ref != "Todos os anos":
                    df_br_ano_dep = df_br[(df_br["NU_ANO"] == ano_ref) & (df_br["DEP_ADM"] == dep_escolhido)]
                    medias_ref_br_cre[col] = float(df_br_ano_dep[col].dropna().mean()) if not df_br_ano_dep.empty else np.nan
                else:
                    medias_ref_br_cre[col] = np.nan
            if "MEDIA_GERAL" in df_dep_cre_filt.columns:
                medias_ref_ms_cre["MEDIA_GERAL"] = float(df_dep_cre_filt["MEDIA_GERAL"].dropna().mean()) if not df_dep_cre_filt.empty else np.nan
                if df_br is not None and ano_ref != "Todos os anos":
                    df_br_ano_dep = df_br[(df_br["NU_ANO"] == ano_ref) & (df_br["DEP_ADM"] == dep_escolhido)]
                    medias_ref_br_cre["MEDIA_GERAL"] = float(df_br_ano_dep["MEDIA_GERAL"].dropna().mean()) if not df_br_ano_dep.empty else np.nan
                else:
                    medias_ref_br_cre["MEDIA_GERAL"] = np.nan

            # Montar tabela com médias de TODAS as áreas de conhecimento (SEM medianas)
            agg_dict = {"Estudantes": (area, "count")}
            for col in COLS_NOTAS:
                agg_dict[AREAS_COMPLETO[col]] = (col, "mean")
            if "MEDIA_GERAL" in df_cre_filt.columns:
                agg_dict[AREAS_COMPLETO["MEDIA_GERAL"]] = ("MEDIA_GERAL", "mean")

            tabela_completa = df_cre_filt.groupby("CRE", observed=True).agg(**agg_dict).reset_index()

            part_tab = _participacao_cre_tabela(
                tabelas,
                tabela_completa["CRE"].tolist(),
                ano_ref,
                dep_escolhido,
            )
            if not part_tab.empty:
                tabela_completa = tabela_completa.drop(
                    columns=["Concluintes", "Tx_Part_Efetiva"],
                    errors="ignore",
                ).merge(
                    part_tab[[
                        c for c in [
                            "CRE", "Presentes", "Inscritos", "Concluintes",
                            "Tx_Inscrição", "Tx_Part_Efetiva",
                        ] if c in part_tab.columns
                    ]],
                    on="CRE",
                    how="left",
                )
                tabela_completa["Estudantes"] = tabela_completa["Presentes"].fillna(
                    tabela_completa["Estudantes"]
                ).astype(int)
                tabela_completa = tabela_completa.drop(columns=["Presentes"], errors="ignore")
            else:
                conc_tab = _concluintes_cre_por_ano(tabela_completa["CRE"].tolist(), ano_ref)
                if not conc_tab.empty:
                    tabela_completa = tabela_completa.merge(conc_tab, on="CRE", how="left")
                else:
                    tabela_completa["Concluintes"] = pd.NA
                tabela_completa["Concluintes"] = pd.to_numeric(tabela_completa["Concluintes"], errors="coerce")
                tabela_completa["Tx_Part_Efetiva"] = _pct_taxa(
                    tabela_completa["Estudantes"], tabela_completa["Concluintes"],
                )

            # Arredondar colunas numéricas para 1 casa decimal
            for col in tabela_completa.columns:
                if col not in ("CRE", "Estudantes", "Concluintes"):
                    tabela_completa[col] = tabela_completa[col].round(1)

            tabela_completa = tabela_completa.sort_values(AREAS_COMPLETO.get("MEDIA_GERAL", AREAS_COMPLETO[area]), ascending=False)

            cols_finais = ["CRE", "Tx_Inscrição", "Tx_Part_Efetiva", "Inscritos", "Concluintes"]
            for k in COLS_NOTAS:
                col_nome = AREAS_COMPLETO[k]
                if col_nome in tabela_completa.columns:
                    cols_finais.append(col_nome)
            tabela_completa = tabela_completa[[c for c in cols_finais if c in tabela_completa.columns]]

            for tx_col in ("Tx_Inscrição", "Tx_Part_Efetiva"):
                if tx_col in tabela_completa.columns:
                    tabela_completa[tx_col] = tabela_completa[tx_col].apply(
                        lambda x, c=tx_col: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—"
                    )

            tabela_display = tabela_completa.copy()
            if "CRE" in tabela_display.columns:
                tabela_display["CRE"] = tabela_display["CRE"].map(nome_cre_curto)
            for col in tabela_display.columns:
                if col in ("Concluintes", "Inscritos"):
                    tabela_display[col] = tabela_display[col].apply(
                        lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"
                    )
                elif col in [AREAS_COMPLETO[k] for k in AREAS.keys()]:
                    tabela_display[col] = tabela_display[col].apply(
                        lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—"
                    )

            # ============================================================
            # ESTILIZAÇÃO VIA FUNÇÃO UTILITÁRIA
            # ============================================================
            area_labels_cre = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
            if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela_completa.columns:
                area_labels_cre["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

            styled_cre, css_cabecalho_cre = _estilizar_tabela(
                df_display=tabela_display,
                df_raw=tabela_completa,
                colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in tabela_completa.columns],
                cores_area=CORES_AREAS,
                medias_ms=medias_ref_ms_cre,
                medias_br=medias_ref_br_cre,
                col_escola="CRE",
                area_labels=area_labels_cre,
                tx_threshold_vermelho=70.0,
                tx_threshold_laranja=None,
                tx_threshold_verde=None,
                colorir_linha_tx=True,
            )

            # CSS customizado para cabeçalhos coloridos
            if css_cabecalho_cre:
                st.markdown(f"""
                <style>
                {css_cabecalho_cre}
                </style>
                """, unsafe_allow_html=True)

            # Legendas explicativas
            st.markdown("""
            <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
                <b>Tx inscrição</b> = inscritos ÷ concluintes · <b>Tx part. efetiva</b> = presentes ÷ concluintes |
                <b>Tx part. efetiva &lt; 70%:</b> <span style='color: #C03A2B; font-weight: 700;'>participação preocupante</span> |
                <b>Médias:</b> <span style='color: #0F8A5F; font-weight: 700;'>verde</span> = acima da média nacional (BR),
                <span style='color: #003F7F; font-weight: 700;'>azul</span> = acima da média estadual (MS) e abaixo de BR,
                <span style='color: #C03A2B; font-weight: 700;'>vermelho</span> = abaixo da média estadual (MS) |
                <b>Cores das áreas:</b> fundo colorido conforme legenda dos gráficos
            </div>
            """, unsafe_allow_html=True)

            n_cres = len(tabela_completa)  # ✅ DataFrame original
            altura_cre = min(max(n_cres * 35 + 45, 100), 520)
            st.dataframe(styled_cre, width="stretch", hide_index=True, height=altura_cre)
        else:
            st.info("Dados de CRE não disponíveis para o recorte selecionado.")
    else:
        st.info("Dados de CRE não disponíveis para a tabela.")

