"""Corpo das funções de `contexto_nacional` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_contexto_nacional(tabelas, anos_sel):
    titulo_secao(
        "Panorama nacional",
        "Posicionamento entre as unidades federativas. Selecione o ano e a área desejados."
    )
    tabelas = tabelas or {}
    anos_validos = anos_com_desempenho_uf(tabelas, anos_sel)
    if not anos_validos:
        st.warning("Nenhum ano disponível para o panorama nacional.")
        return

    st.markdown("### Filtros de análise")
    col_filt_ano, col_filt_area, col_filt_dep = st.columns(3)
    with col_filt_ano:
        ano_nac = st.selectbox(
            "Selecione o ano",
            options=anos_validos,
            index=len(anos_validos) - 1,
            key="ano_nac",
        )
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_nac",
        )
    with col_filt_dep:
        dep = st.selectbox(
            "Selecione a dependência administrativa",
            options=["Todas", "Estadual", "Federal", "Municipal", "Privada"],
            index=1,
            key="dep_nac",
        )

    dep_filtro = None if dep == "Todas" else dep
    g_base = tabela_ranking_uf(tabelas, int(ano_nac), dep_filtro)

    if g_base.empty or area not in g_base.columns:
        st.warning("Sem dados para o recorte selecionado.")
        return

    g_chart = g_base[["UF", area]].dropna().copy()
    g_chart[area] = g_chart[area].round(2)
    g_chart = g_chart.sort_values(area, ascending=False).reset_index(drop=True)
    g_chart["Posição"] = g_chart.index + 1

    media_br = media_nacional_ponderada(tabelas, int(ano_nac), area, "Estadual")
    row_ms = g_base[g_base["UF"] == "MS"]
    media_ms = float(row_ms[area].iloc[0]) if not row_ms.empty else media_br

    def _cor_barra(row):
        if row["UF"] == "MS":
            return LARANJA_DESTAQUE
        val = row[area]
        if val >= media_br:
            return COR_POSITIVO
        elif val >= media_ms:
            return AZUL_PRINCIPAL
        return COR_CRITICO

    g_chart["Cor"] = g_chart.apply(_cor_barra, axis=1)

    # Destaque visual para MS (borda mais grossa)
    marker_line_colors = ["black" if uf == "MS" else "rgba(0,0,0,0)" for uf in g_chart["UF"]]
    marker_line_widths = [3 if uf == "MS" else 0 for uf in g_chart["UF"]]

    fig = go.Figure(go.Bar(
        x=g_chart["UF"],
        y=g_chart[area],
        marker_color=g_chart["Cor"],
        marker_line_color=marker_line_colors,
        marker_line_width=marker_line_widths,
        text=[f"<b>{row['Posição']}º</b><br>{row[area]:.2f}".replace(".", ",") for _, row in g_chart.iterrows()],
        textposition="outside",
        textfont=dict(size=12, color="#333333"),
        hovertemplate="<b>%{x}</b><br>Posição: %{customdata}º<br>Média: %{y:.2f}<extra></extra>",
        customdata=g_chart["Posição"],
    ))

    fig.add_hline(
        y=media_br, line_dash="dash", line_color=TEMA["texto_secundario"], line_width=2,
        annotation_text=f"Média BR: {media_br:.2f}".replace(".", ","),
        annotation_position="top right",
        annotation_font=dict(size=10, color=TEMA["texto_secundario"]),
    )
    if abs(media_ms - media_br) > 0.5:
        fig.add_hline(
            y=media_ms, line_dash="dot", line_color=LARANJA_DESTAQUE, line_width=2,
            annotation_text=f"Média MS: {media_ms:.2f}".replace(".", ","),
            annotation_position="bottom right",
            annotation_font=dict(size=10, color=LARANJA_DESTAQUE),
        )

    fig.update_layout(
        title=dict(
            text=f"Média por UF — {nome_area_ext(area)} ({dep}) — {ano_nac}",
            font=dict(size=16),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(title="UF", categoryorder="array", categoryarray=g_chart["UF"].tolist(), tickfont=dict(size=11)),
        yaxis=dict(title="Nota média", range=[0, max(g_chart[area].max() * 1.25, media_br * 1.25, 100)], tickfont=dict(size=11)),
        margin=dict(t=100, b=60, l=60, r=40),
        plot_bgcolor="rgba(250,252,255,1)",
        paper_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
    )

    # Legenda em HTML acima do gráfico para melhor legibilidade
    st.markdown(
        f"""
        <div style='font-size: 13px; margin-bottom: 8px; display: flex; gap: 20px; flex-wrap: wrap; align-items: center;'>
            <span><b>Legenda de cores:</b></span>
            <span><span style='color:{COR_POSITIVO}; font-size: 16px;'>■</span> Acima da média nacional (BR)</span>
            <span><span style='color:{AZUL_PRINCIPAL}; font-size: 16px;'>■</span> Acima da média de MS e abaixo de BR</span>
            <span><span style='color:{COR_CRITICO}; font-size: 16px;'>■</span> Abaixo da média de MS</span>
            <span><span style='color:{LARANJA_DESTAQUE}; font-size: 16px;'>■</span> <b>Mato Grosso do Sul</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _chart(aplicar_tema(fig, CHART_H_HIST_GRID))

    # ============================================================
    # TABELA COMPLETA
    # ============================================================
    st.markdown("---")
    titulo_secao(f"Ranking completo por UF — {ano_nac}")

    g_todos = g_base.copy()
    areas_cols_names = [AREAS_COMPLETO[k] for k in COLS_NOTAS if k in g_todos.columns]
    for k in COLS_NOTAS:
        col_nome = AREAS_COMPLETO[k]
        if col_nome not in g_todos.columns and k in g_todos.columns:
            g_todos[col_nome] = g_todos[k].round(2)
        elif col_nome in g_todos.columns:
            g_todos[col_nome] = g_todos[col_nome].round(2)
    if "Média Geral" not in g_todos.columns and "MEDIA_GERAL" in g_todos.columns:
        g_todos["Média Geral"] = g_todos["MEDIA_GERAL"].round(2)

    col_rank = AREAS_COMPLETO.get(area, area)
    if col_rank not in g_todos.columns and area in g_todos.columns:
        col_rank = area
    g_todos = g_todos.sort_values(col_rank, ascending=False).reset_index(drop=True)
    g_todos.insert(0, "Posição", g_todos.index + 1)

    cols_finais = ["Posição", "UF"] + areas_cols_names + ["Média Geral", "Inscritos", "Tx_Participação"]
    g_todos = g_todos[[c for c in cols_finais if c in g_todos.columns]]
    g_todos = g_todos.loc[:, ~g_todos.columns.duplicated()]

    tabela_display = g_todos.copy()
    for col in list(tabela_display.columns):
        if col in areas_cols_names or col == "Média Geral":
            tabela_display[col] = pd.to_numeric(tabela_display[col], errors="coerce").apply(
                lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—"
            )
        elif col == "Tx_Participação":
            tabela_display[col] = pd.to_numeric(tabela_display[col], errors="coerce").apply(
                lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—"
            )
        elif col in ("Inscritos", "Presentes_Est"):
            tabela_display[col] = pd.to_numeric(tabela_display[col], errors="coerce").apply(
                lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"
            )

    medias_ref_ms_nac = {}
    medias_ref_br_nac = {}
    for k in COLS_NOTAS:
        medias_ref_br_nac[k] = media_nacional_ponderada(tabelas, int(ano_nac), k, "Estadual")
        ms_row = g_base[g_base["UF"] == "MS"]
        medias_ref_ms_nac[k] = (
            float(ms_row[k].iloc[0]) if not ms_row.empty and k in ms_row.columns
            else medias_ref_br_nac[k]
        )
    medias_ref_br_nac["MEDIA_GERAL"] = media_nacional_ponderada(
        tabelas, int(ano_nac), "MEDIA_GERAL", "Estadual",
    )
    ms_mg = g_base[g_base["UF"] == "MS"]
    medias_ref_ms_nac["MEDIA_GERAL"] = (
        float(ms_mg["MEDIA_GERAL"].iloc[0]) if not ms_mg.empty and "MEDIA_GERAL" in ms_mg.columns
        else medias_ref_br_nac["MEDIA_GERAL"]
    )

    area_labels_nac = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
    area_labels_nac["MEDIA_GERAL"] = "Média Geral"

    styled_nac, css_cabecalho_nac = _estilizar_tabela(
        df_display=tabela_display,
        df_raw=g_todos,
        colunas_area=areas_cols_names + ["Média Geral"],
        cores_area={**CORES_AREAS, "MEDIA_GERAL": "#7B8794"},
        medias_ms=medias_ref_ms_nac,
        medias_br=medias_ref_br_nac,
        col_escola="UF",
        tx_col="Tx_Participação",
        concluintes_col="Inscritos",
        area_labels=area_labels_nac,
        tx_threshold_vermelho=70.0,
        tx_threshold_laranja=70.0,
        tx_threshold_verde=80.0,
        colorir_linha_tx=True,
    )

    if css_cabecalho_nac:
        st.markdown(f"<style>{css_cabecalho_nac}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
        <b>Legenda Taxa Part. Efetiva:</b> 
        <span style='color: #059669;'>■</span> ≥80% 
        <span style='color: #D97706;'>■</span> 70-79% 
        <span style='color: #DC2626;'>■</span> &lt;70% | 
        <b>Fonte das médias:</b> 
        <span style='color: #0F8A5F;'>verde</span> = acima BR, 
        <span style='color: #003F7F;'>azul</span> = acima MS e abaixo de BR, 
        <span style='color: #C03A2B;'>vermelho</span> = abaixo de ambos
    </div>
    """, unsafe_allow_html=True)

    n_ufs = len(tabela_display)
    altura_ufs = min(max(n_ufs * 35 + 45, 100), 520)
    st.dataframe(styled_nac, width="stretch", hide_index=True, height=altura_ufs)

