"""Corpo das funções de `escolas_2024` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_escolas_2024(df_ms_enriq_2024, ano=2024, df_br=None, df_bruta_ms=None, df_concluintes=None, tabelas=None, df_notas_individuais=None):
    titulo_secao(
        f"Escolas estaduais em {ano}",
        "Detalhamento por unidade escolar, com nome, município e CRE."
    )

    df_est = df_ms_enriq_2024[df_ms_enriq_2024["DEP_ADM"] == "Estadual"].copy()
    if df_est.empty:
        st.warning(f"Sem dados de escolas estaduais em {ano}.")
        return

    st.markdown("### Análise por escola")
    col_filt_area, col_filt_min = st.columns(2)
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_escola_2024"
        )
    with col_filt_min:
        min_part = st.slider(
            "Mínimo de participantes por escola",
            3, 50, 10,
            key="min_part_escola_2024"
        )

    refs_ano = medias_referencia_por_ano(tabelas or {}, int(ano)) if tabelas else {}
    medias_ref = refs_ano.get(area, {})
    if not medias_ref:
        df_br_est = (
            df_br[(df_br["DEP_ADM"] == "Estadual") & (df_br["NU_ANO"] == ano)]
            if df_br is not None else None
        )
        medias_ref = (
            calcular_medias_referencia(df_est, df_br_est, area)
            if df_br_est is not None else {"ms": None, "br": None}
        )

    medias_ref_ms_area = {}
    medias_ref_br_area = {}
    for col in COLS_NOTAS:
        ref_col = refs_ano.get(col, {}) if refs_ano else {}
        medias_ref_ms_area[col] = (
            float(ref_col.get("ms")) if ref_col.get("ms") is not None and pd.notna(ref_col.get("ms"))
            else (float(df_est[col].dropna().mean()) if not df_est.empty else np.nan)
        )
        if ref_col.get("br") is not None and pd.notna(ref_col.get("br")):
            medias_ref_br_area[col] = float(ref_col["br"])
        elif df_br is not None:
            df_br_est = df_br[(df_br["DEP_ADM"] == "Estadual") & (df_br["NU_ANO"] == ano)]
            medias_ref_br_area[col] = (
                float(df_br_est[col].dropna().mean()) if not df_br_est.empty else np.nan
            )
        else:
            medias_ref_br_area[col] = np.nan
    if "MEDIA_GERAL" in df_est.columns:
        mg_ref = refs_ano.get("MEDIA_GERAL", {}) if refs_ano else {}
        medias_ref_ms_area["MEDIA_GERAL"] = (
            float(mg_ref["ms"]) if mg_ref.get("ms") is not None and pd.notna(mg_ref.get("ms"))
            else (float(df_est["MEDIA_GERAL"].dropna().mean()) if not df_est.empty else np.nan)
        )
        if mg_ref.get("br") is not None and pd.notna(mg_ref.get("br")):
            medias_ref_br_area["MEDIA_GERAL"] = float(mg_ref["br"])
        else:
            medias_ref_br_area["MEDIA_GERAL"] = media_nacional_ponderada(
                tabelas or {}, int(ano), "MEDIA_GERAL", "Estadual",
            )

    # Construir dict de agregação incluindo MEDIA_GERAL se existir
    agg_dict = {AREAS_COMPLETO[col]: (col, "mean") for col in COLS_NOTAS}
    if "MEDIA_GERAL" in df_est.columns:
        agg_dict[AREAS_COMPLETO["MEDIA_GERAL"]] = ("MEDIA_GERAL", "mean")

    g = (df_est.groupby(
            ["CO_ESCOLA", "NOME_ESCOLA", "MUNICIPIO_CRES", "CRE"], dropna=False
         )
         .agg(
             **agg_dict,
             Estudantes=(area, "count")
         )
         .reset_index())
    g = g[g["Estudantes"] >= min_part].copy()
    for col in COLS_NOTAS:
        g[AREAS_COMPLETO[col]] = g[AREAS_COMPLETO[col]].round(1)
    if "MEDIA_GERAL" in df_est.columns and AREAS_COMPLETO["MEDIA_GERAL"] in g.columns:
        g[AREAS_COMPLETO["MEDIA_GERAL"]] = g[AREAS_COMPLETO["MEDIA_GERAL"]].round(1)

    g["NOME_ESCOLA"] = g["NOME_ESCOLA"].fillna("Escola sem cadastro")
    mun_por_escola = _mapa_municipio_por_escola(df_est)
    if not mun_por_escola.empty:
        g["MUNICIPIO_CRES"] = g["MUNICIPIO_CRES"].fillna(g["CO_ESCOLA"].map(mun_por_escola))
    g["MUNICIPIO_CRES"] = g["MUNICIPIO_CRES"].fillna("—")

    if tabelas is not None:
        inscritos_por_escola = inscritos_por_escola_2024(tabelas, dep="Estadual")
    elif (
        df_bruta_ms is not None
        and not df_bruta_ms.empty
        and "CO_ESCOLA" in df_bruta_ms.columns
    ):
        bruta_est_2024 = df_bruta_ms[
            (df_bruta_ms["DEP_ADM"] == "Estadual") &
            (df_bruta_ms["NU_ANO"] == ano)
        ]
        if bruta_est_2024.empty or "CO_ESCOLA" not in bruta_est_2024.columns:
            inscritos_por_escola = pd.DataFrame(columns=["CO_ESCOLA", "Inscritos"])
        else:
            inscritos_por_escola = (
                bruta_est_2024.groupby("CO_ESCOLA", dropna=False)
                .size()
                .rename("Inscritos")
                .reset_index()
            )
    else:
        inscritos_por_escola = pd.DataFrame(columns=["CO_ESCOLA", "Inscritos"])

    if not inscritos_por_escola.empty:
        g = g.merge(inscritos_por_escola, on="CO_ESCOLA", how="left")
        g["Inscritos"] = g["Inscritos"].fillna(0).astype(int)
        g["Taxa"] = (g["Estudantes"] / g["Inscritos"].replace(0, pd.NA) * 100).round(1)
    else:
        g["Inscritos"] = pd.NA
        g["Taxa"] = pd.NA

    # ------------------------------------------------------------
    # INTEGRAÇÃO: Concluintes do 3º ano e Taxa de participação efetiva
    # ------------------------------------------------------------
    # Quando df_concluintes estiver disponível, faz merge; caso contrário,
    # as colunas aparecem como "—" (dados não disponíveis).
    if df_concluintes is not None and not df_concluintes.empty:
        # Tentar merge por CO_ESCOLA primeiro
        concl_ano = df_concluintes[df_concluintes["NU_ANO"] == ano][["CO_ESCOLA", "Concluintes", "TURNOS"]].copy()
        if not concl_ano.empty:
            g = g.merge(concl_ano, on="CO_ESCOLA", how="left")

        # Se ainda houver valores nulos, tentar merge por nome + município
        if g["Concluintes"].isna().sum() > 0:
            # Normalizar nomes para matching (remover acentos e padronizar)
            def _norm(s):
                if pd.isna(s):
                    return ""
                import unicodedata
                s = str(s).strip().upper()
                s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
                return s

            g['NOME_ESCOLA_NORM'] = g['NOME_ESCOLA'].apply(_norm)
            g['MUNICIPIO_NORM'] = g['MUNICIPIO_CRES'].apply(_norm)

            # Carregar dados de concluintes com nome da escola
            concl_ano_full = df_concluintes[df_concluintes["NU_ANO"] == ano][["CO_ESCOLA", "Concluintes", "TURNOS", "NOME_ESCOLA", "MUNICIPIO"]].copy()
            concl_ano_full['NOME_ESCOLA_NORM'] = concl_ano_full['NOME_ESCOLA'].apply(_norm)
            concl_ano_full['MUNICIPIO_NORM'] = concl_ano_full['MUNICIPIO'].apply(_norm)

            # Fazer merge por nome + município para os que não encontraram por CO_ESCOLA
            mask_na = g["Concluintes"].isna()
            if mask_na.sum() > 0:
                g_na = g[mask_na].merge(
                    concl_ano_full[['NOME_ESCOLA_NORM', 'MUNICIPIO_NORM', 'Concluintes', 'TURNOS']],
                    on=['NOME_ESCOLA_NORM', 'MUNICIPIO_NORM'],
                    how='left',
                    suffixes=('', '_y')
                )
                # Atualizar valores
                g.loc[mask_na, 'Concluintes'] = g_na['Concluintes_y'].values
                g.loc[mask_na, 'TURNOS'] = g_na['TURNOS_y'].values

            # Limpar colunas temporárias
            g = g.drop(columns=['NOME_ESCOLA_NORM', 'MUNICIPIO_NORM'], errors='ignore')

        # Preencher valores não encontrados
        g["Concluintes"] = g["Concluintes"].fillna(0).astype(int)
        g["TURNOS"] = g["TURNOS"].fillna("—")
    else:
        g["Concluintes"] = 0
        g["TURNOS"] = "—"

    g["Concluintes"] = pd.to_numeric(g["Concluintes"], errors="coerce")
    g["Taxa_Efetiva"] = (g["Estudantes"] / g["Concluintes"].replace(0, pd.NA) * 100)
    g["Taxa_Efetiva"] = g["Taxa_Efetiva"].apply(lambda x: round(x, 1) if pd.notna(x) else pd.NA)
    if "Inscritos" in g.columns:
        g["Tx_Inscrição"] = (
            g["Inscritos"] / g["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)

    if g.empty:
        st.info("Nenhuma escola atende ao mínimo de participantes selecionado.")
        return

    c1, c2, c3, c4 = st.columns(4)
    media_col_principal = AREAS_COMPLETO[area]
    kpi_card(c1, "Escolas analisadas", fmt_int(len(g)))
    kpi_card(c2, f"Média entre escolas — {nome_area_ext(area)}", fmt_float(g[media_col_principal].mean()))
    kpi_card(c3, "Maior média", fmt_float(g[media_col_principal].max()), status="positivo")
    kpi_card(c4, "Menor média", fmt_float(g[media_col_principal].min()), status="critico")

    st.markdown(" ")
    top_n = 15
    top = g.sort_values(media_col_principal, ascending=False).head(top_n)
    bot = g.sort_values(media_col_principal, ascending=True).head(top_n)

    _x_range_escolas = [0, 1000]

    col_top, col_bot = st.columns(2)
    with col_top:
        d_plot = top.copy()
        d_plot["Rótulo"] = (d_plot["NOME_ESCOLA"] + " (" +
                            d_plot["MUNICIPIO_CRES"] + ")")
        d_plot = d_plot.merge(g[["CO_ESCOLA", "Inscritos", "Taxa"]], on="CO_ESCOLA", how="left")
        _chart(fig_ranking_horizontal(
            d_plot, col_label="Rótulo", col_valor=media_col_principal,
            titulo=f"Top {top_n} — maiores médias ({nome_area_ext(area)})",
            cor=COR_POSITIVO, altura=CHART_H_HIST_GRID, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=_x_range_escolas,
            col_n="Inscritos", col_taxa="Taxa",
        ))
    with col_bot:
        d_plot = bot.copy()
        d_plot["Rótulo"] = (d_plot["NOME_ESCOLA"] + " (" +
                            d_plot["MUNICIPIO_CRES"] + ")")
        d_plot = d_plot.merge(g[["CO_ESCOLA", "Inscritos", "Taxa"]], on="CO_ESCOLA", how="left")
        _chart(fig_ranking_horizontal(
            d_plot, col_label="Rótulo", col_valor=media_col_principal,
            titulo=f"{top_n} menores médias ({nome_area_ext(area)})",
            cor=COR_CRITICO, altura=CHART_H_HIST_GRID, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=_x_range_escolas,
            col_n="Inscritos", col_taxa="Taxa",
        ))

    st.markdown("### Distribuição das notas — escolas com maiores e menores notas")
    dados_top = df_est[df_est["CO_ESCOLA"].isin(top["CO_ESCOLA"])].copy()
    dados_bot = df_est[df_est["CO_ESCOLA"].isin(bot["CO_ESCOLA"])].copy()

    mapa_escolas_top = dict(zip(
        top["CO_ESCOLA"],
        top["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + top["MUNICIPIO_CRES"].apply(_abreviar_cidade)))
    mapa_escolas_bot = dict(zip(
        bot["CO_ESCOLA"],
        bot["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + bot["MUNICIPIO_CRES"].apply(_abreviar_cidade)))

    dados_top["Escola"] = dados_top["CO_ESCOLA"].map(mapa_escolas_top)
    dados_bot["Escola"] = dados_bot["CO_ESCOLA"].map(mapa_escolas_bot)

    dados_top["NomeCompleto"] = dados_top["CO_ESCOLA"].map(
        dict(zip(top["CO_ESCOLA"], top["NOME_ESCOLA"])))
    dados_top["Municipio"] = dados_top["CO_ESCOLA"].map(
        dict(zip(top["CO_ESCOLA"], top["MUNICIPIO_CRES"])))
    dados_bot["NomeCompleto"] = dados_bot["CO_ESCOLA"].map(
        dict(zip(bot["CO_ESCOLA"], bot["NOME_ESCOLA"])))
    dados_bot["Municipio"] = dados_bot["CO_ESCOLA"].map(
        dict(zip(bot["CO_ESCOLA"], bot["MUNICIPIO_CRES"])))

    _top_ord = top.sort_values(media_col_principal, ascending=False)
    ordem_top = (
        _top_ord["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + _top_ord["MUNICIPIO_CRES"].apply(_abreviar_cidade)
    ).tolist()

    _bot_ord = bot.sort_values(media_col_principal, ascending=True)
    ordem_bot = (
        _bot_ord["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + _bot_ord["MUNICIPIO_CRES"].apply(_abreviar_cidade)
    ).tolist()

    y_range_escolas = [0, 1000]

    col_box1, col_box2 = st.columns(2)
    with col_box1:
        if not dados_top.empty:
            fig_top_box = go.Figure()
            for esc in ordem_top:
                sub = dados_top[dados_top["Escola"] == esc]
                if sub.empty:
                    continue
                co_esc = sub["CO_ESCOLA"].iloc[0]
                nome_comp = sub["NomeCompleto"].iloc[0]
                municipio = sub["Municipio"].iloc[0]
                row_esc = linha_escola_2024(tabelas or {}, co_esc) if tabelas else None
                if row_esc is None:
                    continue
                stats = stats_box_quantis(row_esc, area)
                if stats is None:
                    continue
                _add_box_stats(
                    fig_top_box, stats, name=esc, color="#1E5FAD",
                    x_val=esc, rotulo_mediana=True,
                    hover_titulo=f"{nome_comp} — {municipio}",
                )
            _adicionar_referencias_ms_br(
                fig_top_box, medias_ref["ms"], medias_ref["br"],
                sufixo_legenda="rede estadual",
            )
            fig_top_box.update_layout(
                title=dict(text=f"Top {top_n} — maiores notas", x=0.5),
                xaxis=dict(
                    tickangle=0, tickfont=dict(size=8), showgrid=False,
                    categoryorder="array", categoryarray=ordem_top,
                    title="",
                ),
                yaxis=dict(
                    range=y_range_escolas,
                    gridcolor="#EEF2F6",
                    gridwidth=1,
                    zeroline=False,
                    title="Nota",
                ),
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
                showlegend=False,
                margin=dict(b=100, t=72),
                hovermode="closest",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_top_box, "Top escolas", altura=CHART_H_STANDARD, n_legend=1))
        else:
            st.info("Sem dados para as escolas com maiores notas.")
    with col_box2:
        if not dados_bot.empty:
            fig_bot_box = go.Figure()
            for esc in ordem_bot:
                sub = dados_bot[dados_bot["Escola"] == esc]
                if sub.empty:
                    continue
                co_esc = sub["CO_ESCOLA"].iloc[0]
                nome_comp = sub["NomeCompleto"].iloc[0]
                municipio = sub["Municipio"].iloc[0]
                row_esc = linha_escola_2024(tabelas or {}, co_esc) if tabelas else None
                if row_esc is None:
                    continue
                stats = stats_box_quantis(row_esc, area)
                if stats is None:
                    continue
                _add_box_stats(
                    fig_bot_box, stats, name=esc, color="#C03A2B",
                    x_val=esc, rotulo_mediana=True,
                    hover_titulo=f"{nome_comp} — {municipio}",
                )
            _adicionar_referencias_ms_br(
                fig_bot_box, medias_ref["ms"], medias_ref["br"],
                sufixo_legenda="rede estadual",
            )
            fig_bot_box.update_layout(
                title=dict(text=f"{top_n} — menores notas", x=0.5),
                xaxis=dict(
                    tickangle=0, tickfont=dict(size=8), showgrid=False,
                    categoryorder="array", categoryarray=ordem_bot,
                    title="",
                ),
                yaxis=dict(
                    range=y_range_escolas,
                    gridcolor="#EEF2F6",
                    gridwidth=1,
                    zeroline=False,
                    title="Nota",
                ),
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
                showlegend=False,
                margin=dict(b=100, t=72),
                hovermode="closest",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_bot_box, "Escolas em atenção", altura=CHART_H_STANDARD, n_legend=1))
        else:
            st.info("Sem dados para as escolas com menores notas.")

    st.markdown(" ")
    st.markdown(
        f"""<div style="
            background:{TEMA['insight_bg']};
            border-left:4px solid {AZUL_PRINCIPAL};
            border-radius:10px;
            padding:18px 22px 6px 22px;
            margin-bottom:10px;">
            <span style="font-family:'Plus Jakarta Sans',sans-serif;
                         font-size:1.05rem;font-weight:700;
                         color:{AZUL_PRINCIPAL};">
                Análise individual de escola
            </span>
        </div>""",
        unsafe_allow_html=True,
    )

    def _label_escola_sel(row):
        taxa_str = f" | TX={row['Taxa']:.1f}%" if pd.notna(row.get("Taxa")) else ""
        media_val = row.get(media_col_principal, np.nan)
        media_str = f" | Média: {media_val:.1f}" if pd.notna(media_val) else ""
        return (
            f"{row['NOME_ESCOLA']} ({row['MUNICIPIO_CRES']})"
            f"{media_str}"
            f" | N={row['Estudantes']}{taxa_str}"
        )

    opcoes_escola = g.sort_values(media_col_principal, ascending=False).copy()
    opcoes_escola["_label"] = opcoes_escola.apply(_label_escola_sel, axis=1)
    label_to_co = dict(zip(opcoes_escola["_label"], opcoes_escola["CO_ESCOLA"]))

    escola_sel_label = st.selectbox(
        "Selecione uma escola para análise detalhada:",
        options=list(label_to_co.keys()),
        key="escola_detalhe_sel",
    )
    escola_sel_co = label_to_co[escola_sel_label]
    escola_sel_row = g[g["CO_ESCOLA"] == escola_sel_co].iloc[0]

    tx_val = escola_sel_row.get("Taxa")
    insc_val = escola_sel_row.get("Inscritos")
    conc_val = escola_sel_row.get("Concluintes")
    tx_ef_val = escola_sel_row.get("Taxa_Efetiva")

    tx_insc_val = escola_sel_row.get("Tx_Inscrição")
    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    media_val_sel = escola_sel_row.get(media_col_principal, np.nan)
    kpi_card(kc1, f"Nota Média — {nome_area_ext(area)}", fmt_float(media_val_sel),
             status="positivo" if media_val_sel >= (medias_ref["ms"] or 0) else "critico")
    kpi_card(kc2, "Participantes", fmt_int(int(escola_sel_row.get("Estudantes", 0))))
    kpi_card(kc3, "Concluintes 3º ano E.M", fmt_int(int(conc_val)) if pd.notna(conc_val) and conc_val > 0 else "—")
    kpi_card(kc4, "Tx inscrição",
             f"{tx_insc_val:.1f}%" if pd.notna(tx_insc_val) else "—",
             f"{fmt_int(int(insc_val)) if pd.notna(insc_val) else '—'} inscritos" if pd.notna(insc_val) else "")
    if pd.notna(tx_ef_val) and pd.notna(conc_val) and conc_val > 0:
        kpi_card(kc5, "Tx part. efetiva",
                 f"{tx_ef_val:.1f}%",
                 status="positivo" if tx_ef_val >= 80 else ("atencao" if tx_ef_val >= 60 else "critico"))
    else:
        kpi_card(kc5, "Tx part. efetiva", "—")

    df_escola = df_est[df_est["CO_ESCOLA"] == escola_sel_co].copy()
    if df_notas_individuais is not None and not df_notas_individuais.empty:
        df_escola_ind = filtrar_notas_individuais(
            df_notas_individuais, ano=ano, co_escola=escola_sel_co, dependencia="Estadual",
        )
        if not df_escola_ind.empty:
            df_escola = df_escola_ind
    nome_escola_display = f"{escola_sel_row['NOME_ESCOLA']} — {escola_sel_row['MUNICIPIO_CRES']}"
    usar_individual = (
        df_notas_individuais is not None
        and not df_notas_individuais.empty
        and tem_notas_individuais_ano(df_notas_individuais, ano)
        and not filtrar_notas_individuais(
            df_notas_individuais, ano=ano, co_escola=escola_sel_co, dependencia="Estadual",
        ).empty
    )

    if not df_escola.empty or (tabelas and linha_escola_2024(tabelas, escola_sel_co) is not None):
        medias_ms_area = {col: float(df_est[col].dropna().mean())
                          for col in COLS_NOTAS if col in df_est.columns}
        medias_br_area = {}
        if df_br_est is not None and not df_br_est.empty:
            medias_br_area = {col: float(df_br_est[col].dropna().mean())
                              for col in COLS_NOTAS if col in df_br_est.columns}

        fig_escola = go.Figure()
        row_esc_det = linha_escola_2024(tabelas or {}, escola_sel_co) if tabelas else None
        if not usar_individual and row_esc_det is None:
            st.warning(
                "Quantis por escola indisponíveis. Regenere os agregados: "
                "python gerar_dados_agregados.py"
            )
        for col in COLS_NOTAS:
            nome_area_lbl = AREAS_COMPLETO[col]
            if usar_individual:
                s_area = notas_area(df_escola, col)
                if s_area.empty:
                    continue
                stats = _stats_box(s_area)
                _add_box(
                    fig_escola, s_area, nome_area_lbl, CORES_AREAS[col],
                    x_val=nome_area_lbl, rotulo_mediana=True,
                    hover_titulo=nome_area_lbl,
                )
                _add_scatter_notas(
                    fig_escola, nome_area_lbl, s_area,
                    color=_hex_to_rgba(CORES_AREAS[col], 0.4),
                )
            elif row_esc_det is not None:
                stats = stats_box_quantis(row_esc_det, col)
                if stats is None:
                    continue
                _add_box_stats(
                    fig_escola, stats, name=nome_area_lbl,
                    color=CORES_AREAS[col], x_val=nome_area_lbl,
                    rotulo_mediana=True, hover_titulo=nome_area_lbl,
                )

        xs_ms = [AREAS_COMPLETO[col] for col in COLS_NOTAS if col in medias_ms_area]
        ys_ms = [medias_ms_area[col] for col in COLS_NOTAS if col in medias_ms_area]
        if xs_ms:
            fig_escola.add_trace(go.Scatter(
                x=xs_ms, y=ys_ms,
                mode="markers",
                name="Média MS — rede estadual",
                legendgroup="medias_ref",
                marker=dict(symbol="line-ew", size=22,
                            color=LARANJA_DESTAQUE,
                            line=dict(color=LARANJA_DESTAQUE, width=3)),
                hovertemplate="<b>Média MS</b><br>%{x}: %{y:.1f}<extra></extra>",
            ))

        xs_br = [AREAS_COMPLETO[col] for col in COLS_NOTAS if col in medias_br_area]
        ys_br = [medias_br_area[col] for col in COLS_NOTAS if col in medias_br_area]
        if xs_br:
            fig_escola.add_trace(go.Scatter(
                x=xs_br, y=ys_br,
                mode="markers",
                name="Média BR — rede estadual",
                legendgroup="medias_ref",
                marker=dict(symbol="line-ew", size=22,
                            color=COR_BRASIL,
                            line=dict(color=COR_BRASIL, width=2.5)),
                hovertemplate="<b>Média BR</b><br>%{x}: %{y:.1f}<extra></extra>",
            ))

        fig_escola = _finalizar_boxplot(
            fig_escola,
            f"Distribuição das notas — {nome_escola_display}",
            altura=CHART_H_STANDARD,
            eixo_x="",
            n_legend=5,
        )
        fig_escola.update_xaxes(showticklabels=False)
        _chart(fig_escola)

        if usar_individual:
            s_hist = notas_area(df_escola, area)
            if not s_hist.empty:
                titulo_secao(
                    f"Histograma — {nome_area_ext(area)}",
                    f"Distribuição individual dos {len(s_hist):,} estudantes da escola selecionada."
                )
                _chart(_fig_histogram_notas(
                    s_hist,
                    f"Distribuição de notas — {nome_escola_display} ({nome_area_ext(area)})",
                    cor=CORES_AREAS.get(area, AZUL_PRINCIPAL),
                    media_ref=medias_ref.get("ms"),
                ))
    else:
        st.info("Sem dados individuais para a escola selecionada.")

    if not g.empty and "Tx_Inscrição" in g.columns:
        g_vis = g.rename(columns={
            "NOME_ESCOLA": "Escola", media_col_principal: "Média",
        })
        part_esc = g_vis[["Escola", "Concluintes", "Inscritos", "Estudantes", "Tx_Inscrição", "Taxa_Efetiva"]].rename(
            columns={"Estudantes": "Presentes", "Taxa_Efetiva": "Tx_Part_Efetiva"},
        )
        titulo_secao("Desempenho × Participação — escolas")
        col_e1, col_e2 = st.columns([1.55, 1])
        top_esc = g_vis.nlargest(min(12, len(g_vis)), "Média")
        with col_e1:
            _chart(fig_combo_participacao_desempenho(
                part_esc[part_esc["Escola"].isin(top_esc["Escola"])],
                top_esc, "Escola", "Média",
                titulo=f"Top escolas — {nome_area_ext(area)}",
            ))
        with col_e2:
            _chart(fig_quadrante_desempenho_participacao(
                part_esc.rename(columns={"Tx_Part_Efetiva": "Tx_Part_Efetiva"}),
                g_vis, "Escola", "Média",
                titulo="Quadrante escolar",
            ))

    titulo_secao("Tabela completa por escola")
    tabela = g.rename(columns={
        "NOME_ESCOLA": "Escola", "MUNICIPIO_CRES": "Município",
        "CRE": "Coordenadoria Regional",
        "Estudantes": "Participantes",
    }).copy()

    tabela["Tx_Part_Efetiva"] = (tabela["Participantes"] / tabela["Concluintes"].replace(0, pd.NA) * 100)
    tabela["Tx_Part_Efetiva"] = tabela["Tx_Part_Efetiva"].apply(lambda x: round(x, 1) if pd.notna(x) else pd.NA)
    if "Inscritos" in tabela.columns:
        tabela["Tx_Inscrição"] = (
            tabela["Inscritos"] / tabela["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)

    # Garantir que Concluintes, TURNOS existam
    if "Concluintes" not in tabela.columns:
        tabela["Concluintes"] = pd.NA
    if "TURNOS" not in tabela.columns:
        tabela["TURNOS"] = "—"

    # Selecionar colunas finais: remover Inscritos, Presentes, Mediana, Participantes
    COLS_NOTAS_COMPLETO = [AREAS_COMPLETO[col] for col in COLS_NOTAS]
    # Adicionar Média Geral se existir
    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela.columns:
        COLS_NOTAS_COMPLETO = [AREAS_COMPLETO["MEDIA_GERAL"]] + COLS_NOTAS_COMPLETO

    cols_esc = ["Escola", "Município", "Coordenadoria Regional", "TURNOS",
                "Tx_Inscrição", "Tx_Part_Efetiva", "Inscritos", "Concluintes"]
    tabela = tabela[[c for c in cols_esc if c in tabela.columns] + COLS_NOTAS_COMPLETO]
    tabela = tabela.sort_values(media_col_principal, ascending=False)
    tabela["Coordenadoria Regional"] = tabela["Coordenadoria Regional"].fillna("—")

    for txc in ("Tx_Inscrição", "Tx_Part_Efetiva"):
        if txc in tabela.columns:
            tabela[f"{txc}_fmt"] = tabela[txc].apply(
                lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—"
            )
    tabela_display = tabela.copy()
    for txc in ("Tx_Inscrição", "Tx_Part_Efetiva"):
        if f"{txc}_fmt" in tabela_display.columns:
            tabela_display[txc] = tabela_display[f"{txc}_fmt"]
            tabela_display = tabela_display.drop(columns=[f"{txc}_fmt"])
    for col in tabela_display.columns:
        if col in ("Concluintes", "Inscritos"):
            tabela_display[col] = tabela_display[col].apply(lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—")
        elif col in COLS_NOTAS_COMPLETO:
            tabela_display[col] = tabela_display[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—")

    # ============================================================
    # ESTILIZAÇÃO VIA FUNÇÃO UTILITÁRIA
    # ============================================================
    area_labels = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela_display.columns:
        area_labels["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

    styled, css_cabecalho = _estilizar_tabela(
        df_display=tabela_display,
        df_raw=tabela,
        colunas_area=COLS_NOTAS_COMPLETO,
        cores_area=CORES_AREAS,
        medias_ms=medias_ref_ms_area,
        medias_br=medias_ref_br_area,
        area_labels=area_labels,
    )

    # CSS customizado para cabeçalhos coloridos (pandas styler não suporta seletores de coluna)
    if css_cabecalho:
        st.markdown(f"""
        <style>
        {css_cabecalho}
        </style>
        """, unsafe_allow_html=True)

    # Legenda explicativa
    st.markdown("""
    <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
        <b>Tx inscrição</b> = inscritos ÷ concluintes · <b>Tx part. efetiva</b> = presentes ÷ concluintes |
        <b>Tx part. efetiva:</b> <span style='color: #059669;'>■</span> ≥80%
        <span style='color: #D97706;'>■</span> 70-79%
        <span style='color: #DC2626;'>■</span> &lt;70% |
        <b>Cores das áreas:</b> fundo colorido conforme legenda dos gráficos | 
        <b>Fonte das médias:</b> <span style='color: #059669;'>verde</span> = acima MS e BR, 
        <span style='color: #2563EB;'>azul</span> = acima de MS e abaixo de BR, 
        <span style='color: #DC2626;'>vermelho</span> = abaixo de ambos
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(styled, width="stretch", hide_index=True, height=520)

