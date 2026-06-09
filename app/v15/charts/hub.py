"""Gráficos e layout do hub denso — painel ENEM v15."""

from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from viz.chart_layout import CHART_H_HUB, CHART_H_HUB_DELTA_ROW, CHART_H_HUB_EVOL, CHART_H_HUB_RANK

from app.v15.boxplots import _anotacao_hub, _aplicar_hover_hub
from app.v15.charts_render import _chart_hub
from app.v15.constants import HUB_BUILD_ID
from app.v15.formatting import fmt_delta, fmt_float, fmt_int, fmt_pct
from app.v15.hub_charts import (
    _aplicar_eixos_hub,
    _aplicar_legenda_interna_combo_ms,
    _altura_hub_ranking,
    _classificar_cor_media_referencia,
    _cor_posicao_terco,
    _cores_ranking_presentes,
    _fechar_fig_hub,
    _legenda_fig,
    _margem_hub,
    _texto_posicao_barra,
)
from app.v15.plotly_theme import _legenda_padrao, aplicar_tema
from app.v15.territory_data import _participacao_cre_tabela
from app.v15.theme import *
from app.v15.ui import _render_html


def _render_widget_grafico_hub(titulo: str, fig, legenda: str = "") -> None:
    legenda = getattr(fig, "_hub_legenda", None) or legenda
    _render_html(
        f'<div class="widget-chart-zone">'
        f'<div class="widget-head">{_html.escape(titulo)}</div>'
        f'<div class="widget-chart-body">'
    )
    _chart_hub(fig)
    if legenda and legenda.strip():
        corpo = (
            legenda if legenda.lstrip().startswith("<")
            else _html.escape(legenda)
        )
        _render_html(f'<div class="widget-chart-nota">{corpo}</div>')
    _render_html("</div></div>")


def _render_hub_linha(
    cards: list[tuple[str, go.Figure | None, str]],
) -> None:
    """Uma linha do grid hub (até 3 gráficos)."""
    cols = st.columns(HUB_COL_LAYOUT, gap="small")
    for col, card in zip(cols, cards):
        with col:
            titulo, fig, legenda = card
            if fig is not None:
                _render_widget_grafico_hub(titulo, fig, legenda)


@st.fragment
def _fragment_hub_coluna(
    cards: list[tuple[str, go.Figure | None, str]],
    *,
    key: str = "hub_col",
) -> None:
    """Coluna do hub isolada em fragment (evita reruns desnecessários)."""
    _render_hub_coluna(cards)


@st.fragment
def _fragment_hub_delta(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
) -> None:
    """Painel Δ vs BR isolado em fragment."""
    _render_hub_delta_br_por_ano(df_dist_est, tabelas)


def _render_hub_coluna(
    cards: list[tuple[str, go.Figure | None, str]],
) -> None:
    """Empilha widgets hub verticalmente numa coluna."""
    for titulo, fig, legenda in cards:
        if fig is not None:
            _render_widget_grafico_hub(titulo, fig, legenda)


def _legenda_padrao(y_pos: float = 1.02, font_size: int = FONT_LEGEND, entry_width: int = 150):
    """Retorna dict de legenda padronizado para evitar sobreposição.

    - ``y_pos``: posição vertical (1.02 = acima do plot, -0.22 = abaixo).
    - ``font_size``: tamanho da fonte dos itens.
    - ``trace_gap``: espaçamento entre as traces na legenda.
    - ``entry_width``: largura fixa para cada item da legenda, evitando
      sobreposição quando há muitos itens. Ajustar conforme necessário.
    """
    return dict(
        orientation="h",
        yanchor="bottom" if y_pos > 0 else "top",
        y=y_pos,
        xanchor="center",
        x=0.5,
        entrywidth=entry_width,
        entrywidthmode="pixels",
        tracegroupgap=6,
        font=dict(size=font_size, color=TEMA["texto"]),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor=TEMA["borda"],
        borderwidth=1,
    )


def _fig_combo_media_participacao(
    *,
    anos: list[int],
    media_map: dict[int, float],
    tx_part_map: dict[int, float],
    delta_map: dict[int, float] | None = None,
    rotulo_media: str,
    rotulo_part: str,
    cor_linha: str,
    cor_texto_media: str,
    cor_barra: str,
    cor_borda_barra: str,
    cor_texto_barra: str,
    altura: int = ALTURA_HUB_MS,
    rotulos_part_na_base: bool = False,
    mostrar_rotulo_media: bool = True,
    legenda_interna: bool = False,
) -> go.Figure:
    """Combo hub: média (linha) + participação efetiva (barra) + Δ opcional."""
    from plotly.subplots import make_subplots

    if not anos or not media_map:
        return go.Figure()

    delta_map = delta_map or {}
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    y_media = [media_map.get(a, np.nan) for a in anos]
    y_valid = [v for v in y_media if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 12) if y_valid else 12
    tem_delta = any(pd.notna(delta_map.get(a, np.nan)) for a in anos)
    folga_topo = 1.22 if tem_delta else 0.72
    y_min = max(0, min(y_valid) - y_span * 0.45) if y_valid else 0
    y_max = min(1000, max(y_valid) + y_span * folga_topo) if y_valid else 1000

    if tx_part_map:
        y_part = [tx_part_map.get(a, np.nan) for a in anos]
        fig.add_trace(
            go.Bar(
                x=anos,
                y=y_part,
                name=rotulo_part,
                marker=dict(
                    color=cor_barra,
                    line=dict(color=cor_borda_barra, width=0.5),
                ),
                opacity=1.0,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"{rotulo_part}: %{{y:.1f}}%"
                    "<extra></extra>"
                ),
            ),
            secondary_y=True,
        )
        if rotulos_part_na_base:
            y_lbl_part = 1.5
            for ano in anos:
                v = tx_part_map.get(ano, np.nan)
                if pd.notna(v):
                    _anotacao_hub(
                        fig,
                        x=ano, xref="x",
                        y=y_lbl_part, yref="y2",
                        text=f"<b>{float(v):.0f}%</b>",
                        showarrow=False,
                        yanchor="bottom",
                        font=dict(
                            size=FONT_HUB_DATA, color=cor_texto_barra,
                            family="Plus Jakarta Sans, sans-serif",
                        ),
                    )
        else:
            txt_part, pos_part = _texto_posicao_barra(y_part)
            fig.update_traces(
                text=txt_part,
                textposition=pos_part,
                insidetextanchor="end",
                outsidetextfont=dict(
                    size=FONT_HUB_DATA, color=AZUL_ESCURO,
                    family="Plus Jakarta Sans, sans-serif",
                ),
                textfont=dict(
                    size=FONT_HUB_DATA, color=cor_texto_barra,
                    family="Plus Jakarta Sans, sans-serif",
                ),
                selector=dict(type="bar"),
            )

    txt_media = [
        f"<b>{media_map.get(a, np.nan):.0f}</b>"
        if mostrar_rotulo_media and pd.notna(media_map.get(a, np.nan)) else ""
        for a in anos
    ]
    fig.add_trace(
        go.Scatter(
            x=anos, y=y_media,
            name=rotulo_media,
            mode="lines+markers+text",
            text=txt_media,
            textposition="top center",
            textfont=dict(
                size=FONT_HUB_DATA, color=cor_texto_media,
                family="Plus Jakarta Sans, sans-serif",
            ),
            line=dict(color=cor_linha, width=2.5, shape="spline"),
            marker=dict(size=8, color=cor_linha, line=dict(width=1.5, color="white")),
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"{rotulo_media}: %{{y:.1f}}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    for ano in anos:
        media_val = media_map.get(ano, np.nan)
        delta = delta_map.get(ano, np.nan)
        if pd.notna(media_val) and pd.notna(delta):
            cor = COR_POSITIVO if delta >= 0 else COR_CRITICO
            _anotacao_hub(
                fig,
                x=ano, xref="x", y=media_val, yref="y",
                text=f"<b>Δ {delta:+.1f}</b>",
                showarrow=False, yanchor="bottom", yshift=34,
                font=dict(size=9, color=cor, family="Plus Jakarta Sans, sans-serif"),
            )

    y_part_max = max(
        (float(v) for v in tx_part_map.values() if pd.notna(v)),
        default=50.0,
    ) if tx_part_map else 50.0
    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, max(y_part_max * 1.22, 40)], secondary_y=True)
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(bargap=0.32, showlegend=legenda_interna)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(fig, topo=tem_delta)
    _aplicar_eixos_hub(fig, secondary_y=bool(tx_part_map))
    _aplicar_hover_hub(fig)
    return fig


def _fig_destaque_evolucao_ms(
    diag: dict,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure:
    """Destaque hub: média MS (linha) + tx part. efetiva (barra) e ΔBR."""
    serie_ms = diag.get("serie_medias", pd.Series(dtype=float))
    if serie_ms.empty:
        return go.Figure()

    ms_map = {int(k): float(v) for k, v in serie_ms.items() if pd.notna(v)}
    anos = sorted(ms_map.keys())
    serie_tx_efet = diag.get("serie_tx_part_efetiva", pd.Series(dtype=float))
    tx_efet_map = (
        {int(k): float(v) for k, v in serie_tx_efet.items() if pd.notna(v)}
        if not serie_tx_efet.empty else {}
    )
    serie_delta = diag.get("serie_delta_br", pd.Series(dtype=float))
    delta_map = (
        {int(k): float(v) for k, v in serie_delta.items() if pd.notna(v)}
        if not serie_delta.empty else {}
    )
    return _fig_combo_media_participacao(
        anos=anos,
        media_map=ms_map,
        tx_part_map=tx_efet_map,
        delta_map=delta_map,
        rotulo_media="Média estadual",
        rotulo_part="Participação efetiva",
        cor_linha=AZUL_PRINCIPAL,
        cor_texto_media=AZUL_ESCURO,
        cor_barra="rgba(46, 173, 110, 0.42)",
        cor_borda_barra="rgba(15, 100, 62, 0.55)",
        cor_texto_barra=COR_TEXTO_DENTRO_BARRA,
        altura=altura,
        rotulos_part_na_base=True,
        legenda_interna=False,
    )


def _fig_combo_ranking_ms_uf(
    anos: list[int],
    rank_part_map: dict[int, int],
    rank_des_map: dict[int, int],
    n_total: int,
    *,
    altura: int = ALTURA_HUB_RANK,
) -> go.Figure:
    """Combo hub espelhando média/part.: barras = pos. participação, linha = pos. média geral."""
    from plotly.subplots import make_subplots

    if not anos:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    y_part = [int(rank_part_map[a]) for a in anos]
    y_bar = [float(n_total + 1 - p) for p in y_part]
    y_des = [float(rank_des_map.get(a, np.nan)) for a in anos]
    y_valid = [v for v in y_des if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 3) if y_valid else 3
    y_min = max(0.5, min(y_valid) - y_span * 0.45) if y_valid else 0.5
    y_max = min(n_total + 0.5, max(y_valid) + y_span * 0.55) if y_valid else n_total + 0.5

    fig.add_trace(
        go.Scatter(
            x=anos, y=y_des,
            name="Posição na média",
            mode="lines+markers",
            customdata=np.array([
                [int(rank_des_map[a]), n_total] if pd.notna(rank_des_map.get(a))
                else [np.nan, n_total]
                for a in anos
            ]),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Posição na média: %{customdata[0]}º de %{customdata[1]}"
                "<extra></extra>"
            ),
            line=dict(color=AZUL_PRINCIPAL, width=2.5, shape="spline"),
            marker=dict(size=8, color=AZUL_PRINCIPAL, line=dict(width=1.5, color="white")),
        ),
        secondary_y=False,
    )
    txt_rank = [
        f"<b>{int(rank_des_map.get(a, np.nan))}º</b>"
        if pd.notna(rank_des_map.get(a, np.nan)) else ""
        for a in anos
    ]
    fig.data[0].update(
        mode="lines+markers+text",
        text=txt_rank,
        textposition="top center",
        textfont=dict(
            size=FONT_HUB_DATA, color=AZUL_ESCURO,
            family="Plus Jakarta Sans, sans-serif",
        ),
    )

    fig.add_trace(
        go.Bar(
            x=anos,
            y=y_bar,
            name="Posição na participação",
            customdata=np.array([[p, n_total] for p in y_part]),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Posição na participação: %{customdata[0]}º de %{customdata[1]}"
                "<extra></extra>"
            ),
            marker=dict(
                color="rgba(46, 173, 110, 0.42)",
                line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5),
            ),
            opacity=1.0,
        ),
        secondary_y=True,
    )
    fig.update_traces(
        text=[f"<b>{pos}º</b>" for pos in y_part],
        textposition="outside",
        textfont=dict(
            size=FONT_HUB_DATA, color=COR_TEXTO_DENTRO_BARRA,
            family="Plus Jakarta Sans, sans-serif",
        ),
        selector=dict(type="bar", name="Posição na participação"),
    )

    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, max(n_total * 1.22, 10)], secondary_y=True)
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(bargap=0.32)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(fig)
    _aplicar_eixos_hub(fig, secondary_y=True)
    _aplicar_hover_hub(fig)
    return fig


def _fig_ranking_participacao_nacional(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
    diag: dict,
    *,
    altura: int = ALTURA_HUB_RANK,
) -> go.Figure | None:
    """Ranking UF: posição MS em participação (barra) e média geral (linha)."""
    pos_part = _posicoes_ms_participacao_uf(
        tabelas, anos_sel, df_bruta_ms, df_filt_ms,
    )
    if not pos_part:
        return None

    pos_des = _posicoes_ms_desempenho_uf_por_ano(tabelas, anos_sel)
    part_map = {int(d["Ano"]): int(d["Posição"]) for d in pos_part}
    des_map = {int(d["Ano"]): int(d["Posição"]) for d in pos_des}
    anos = sorted(part_map.keys())
    n_total = max(
        max(int(d["Total"]) for d in pos_part),
        max((int(d["Total"]) for d in pos_des), default=0),
    )
    return _fig_combo_ranking_ms_uf(
        anos, part_map, des_map, n_total, altura=altura,
    )


def _df_dist_estadual_hub(tabelas: dict, df_filt_ms: pd.DataFrame) -> pd.DataFrame:
    """Distribuição agregada da rede estadual MS para gráficos hub."""
    df_est = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    anos = sorted(int(a) for a in df_est["NU_ANO"].dropna().unique())
    if not anos:
        return pd.DataFrame()
    return filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=anos,
        dependencia="Estadual",
    )


def _range_y_hub_evolucao(valores: list, *, folga: float = 0.012) -> tuple[float, float]:
    """Faixa Y com zoom máximo para evidenciar trajetória das áreas."""
    vals = [float(v) for v in valores if v is not None and pd.notna(v)]
    if not vals:
        return 0.0, 1000.0
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 4.0)
    pad_b = max(span * folga, 1.5)
    pad_t = max(span * (folga + 0.08), 3.0)
    return lo - pad_b, hi + pad_t


def _dtick_hub_evolucao(y0: float, y1: float) -> float:
    """Tick do eixo Y proporcional à faixa (passos menores = leitura mais nítida)."""
    span = max(y1 - y0, 5.0)
    if span <= 12:
        return 2.0
    if span <= 25:
        return 3.0
    if span <= 45:
        return 5.0
    return max(5.0, round(span / 7 / 5) * 5)


def _fig_hub_evolucao_areas_linhas(
    df_dist_est: pd.DataFrame,
    tabelas: dict | None = None,
    *,
    altura: int = ALTURA_HUB_EVOL,
) -> go.Figure | None:
    """Evolução compacta: média MS por área de conhecimento (sem média geral/BR)."""
    if df_dist_est is None or df_dist_est.empty:
        return None
    anos_int = sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
    if not anos_int:
        return None

    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    y_objetivas: list[float] = []
    y_redacao: list[float] = []

    for key in COLS_NOTAS:
        xs, ys = [], []
        for ano in anos_int:
            rows = df_dist_est[df_dist_est["ano"] == ano]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], key)
            if stats is None:
                continue
            xs.append(ano)
            ys.append(float(stats["mean"]))
        if not xs:
            continue

        cor = CORES_AREAS.get(key, AZUL_PRINCIPAL)
        sec = key == "NU_NOTA_REDACAO"
        if sec:
            y_redacao.extend(ys)
        else:
            y_objetivas.extend(ys)

        trace = go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            name=AREAS.get(key, key),
            line=dict(color=cor, width=2.0 if sec else 1.9),
            marker=dict(size=7, color=cor, line=dict(width=1, color="white")),
            hovertemplate=(
                f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                "Ano: %{x}<br>Média: %{y:.1f}<extra></extra>"
            ),
        )
        fig.add_trace(trace, secondary_y=sec)

    if not fig.data:
        return None

    if y_objetivas:
        y0, y1 = _range_y_hub_evolucao(y_objetivas)
        dtick = _dtick_hub_evolucao(y0, y1)
        fig.update_yaxes(
            range=[y0, y1],
            dtick=dtick,
            showticklabels=False,
            ticks="",
            secondary_y=False,
        )
    if y_redacao:
        yr0, yr1 = _range_y_hub_evolucao(y_redacao)
        fig.update_yaxes(
            range=[yr0, yr1],
            dtick=_dtick_hub_evolucao(yr0, yr1),
            showticklabels=False,
            ticks="",
            secondary_y=True,
        )
    elif y_objetivas:
        fig.update_yaxes(showticklabels=False, ticks="", secondary_y=True)

    fig.update_xaxes(tickmode="linear", dtick=1)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(fig, topo=True, legenda_traces=False, legenda_areas=True)
    _aplicar_eixos_hub(fig, secondary_y=bool(y_redacao))
    _aplicar_hover_hub(fig)
    return fig


def _fig_hub_box_media_geral(
    df_dist_est: pd.DataFrame,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure | None:
    """Boxplot anual compacto — média geral (rede estadual)."""
    if df_dist_est is None or df_dist_est.empty:
        return None
    anos = sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
    xs, stats_list = [], []
    for ano in anos:
        rows = df_dist_est[df_dist_est["ano"] == ano]
        if rows.empty:
            continue
        stats = stats_box_quantis(rows.iloc[0], "MEDIA_GERAL")
        if stats is None:
            continue
        xs.append(str(ano))
        stats_list.append(stats)
    if not xs:
        return None

    fig = go.Figure()
    _add_box_series(
        fig, name="Média geral", color=AZUL_PRINCIPAL,
        x_vals=xs, stats_list=stats_list,
        showlegend=False, rotulos_quantis=False,
        box_width=0.72,
    )
    y0, y1 = _range_y_box_stats(stats_list, pad=38)
    fig.update_layout(
        yaxis=dict(range=[y0, y1]),
        boxmode="group",
    )
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=xs)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        notas=["Passe o mouse na caixa para ver quartis"],
        legenda_traces=False,
    )
    _aplicar_eixos_hub(fig)
    _aplicar_hover_hub(fig)
    return fig


def _cores_traces_ranking(fig: go.Figure) -> set[str] | None:
    """Cores das barras horizontais (para legenda dinâmica)."""
    for tr in fig.data:
        if getattr(tr, "type", None) != "bar":
            continue
        mc = getattr(getattr(tr, "marker", None), "color", None)
        if isinstance(mc, (list, tuple)):
            return set(mc)
    return None


def _estilo_fig_hub_ranking(
    fig: go.Figure,
    *,
    cores_ms_br: bool = False,
    refs_vline_ms_br: bool = False,
    notas: list[str] | None = None,
    cores_ranking: set[str] | None = None,
) -> go.Figure:
    """Tipografia legível para rankings horizontais compactos (CREs, etc.)."""
    fig.update_layout(title=dict(text=""))
    fig.update_xaxes(tickfont=dict(size=FONT_HUB_AXIS, color=TEMA["texto_secundario"]))
    fig.update_yaxes(
        tickfont=dict(size=FONT_HUB_AXIS, color=TEMA["texto_secundario"]),
        automargin=True,
        ticklabelstandoff=4,
    )
    fig.update_traces(
        textfont=dict(size=FONT_HUB_DATA, color=TEMA["texto"]),
        selector=dict(type="bar"),
    )
    cores_ranking = cores_ranking or _cores_traces_ranking(fig)
    nota_rank = notas[0] if notas else ""
    _fechar_fig_hub(
        fig,
        rank=True,
        notas=[nota_rank] if nota_rank else None,
        cores_ms_br=cores_ms_br,
        refs_vline=refs_vline_ms_br,
        legenda_traces=False,
        rank_compacto=bool(cores_ms_br or refs_vline_ms_br),
        cores_ranking=cores_ranking,
    )
    _aplicar_eixos_hub(fig, y_categorico=True)
    fig.update_xaxes(showticklabels=False, ticks="", showgrid=False)
    _aplicar_hover_hub(fig, horizontal=True)
    return fig


def _fig_hub_cre_combo_media_participacao(
    tabelas: dict,
    anos_sel: list,
    *,
    altura: int | None = None,
) -> go.Figure | None:
    """CREs em colunas: barras = participação %, linha = média geral."""
    from plotly.subplots import make_subplots

    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        return None
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        return None
    ano_ref = anos_validos[-1]
    sub_media = df_evol[
        (df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == "Estadual")
    ].copy()
    if "media_geral" not in sub_media.columns:
        return None
    sub_media = sub_media.dropna(subset=["media_geral"])

    cres = sorted(
        df_evol.loc[df_evol["dependencia"] == "Estadual", "CRE"].dropna().unique()
    )
    if not cres or sub_media.empty:
        return None
    part = _participacao_cre_tabela(tabelas, cres, ano_ref, "Estadual")
    if part.empty or "Tx_Part_Efetiva" not in part.columns:
        return None

    merged = sub_media[["CRE", "media_geral"]].merge(
        part[["CRE", "Tx_Part_Efetiva"]], on="CRE", how="inner",
    )
    merged = merged.dropna(subset=["media_geral", "Tx_Part_Efetiva"])
    if merged.empty:
        return None
    merged["_lbl"] = merged["CRE"].map(nome_cre_curto)
    merged = merged.sort_values("media_geral", ascending=True)

    labels = merged["_lbl"].astype(str).tolist()
    media_vals = merged["media_geral"].astype(float).tolist()
    tx_vals = merged["Tx_Part_Efetiva"].astype(float).tolist()

    refs = medias_referencia_por_ano(tabelas, ano_ref)
    mg = refs.get("MEDIA_GERAL", {}) if refs else {}
    media_ms = mg.get("ms")
    media_br = mg.get("br")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=labels,
            y=tx_vals,
            name="Participação",
            text=[f"<b>{tx:.0f}%</b>" for tx in tx_vals],
            textposition="outside",
            textfont=dict(
                size=FONT_HUB_DATA, color=COR_TEXTO_DENTRO_BARRA,
                family="Plus Jakarta Sans, sans-serif",
            ),
            marker=dict(
                color="rgba(46, 173, 110, 0.42)",
                line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5),
            ),
            hovertemplate=(
                "<b>%{x}</b><br>Participação: %{y:.1f}%<extra></extra>"
            ),
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=media_vals,
            mode="lines+markers+text",
            name="Média",
            text=[f"<b>{med:.0f}</b>" for med in media_vals],
            textposition="top center",
            textfont=dict(
                size=FONT_HUB_DATA, color=AZUL_ESCURO,
                family="Plus Jakarta Sans, sans-serif",
            ),
            line=dict(color=AZUL_PRINCIPAL, width=2.5, shape="spline"),
            marker=dict(
                size=8, color=AZUL_PRINCIPAL,
                line=dict(width=1.5, color="white"),
            ),
            hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
        ),
        secondary_y=False,
    )

    if media_ms is not None:
        fig.add_hline(
            y=media_ms, line_dash="dash", line_color=LARANJA_DESTAQUE, line_width=2.5,
        )
    if media_br is not None:
        fig.add_hline(
            y=media_br, line_dash="dot", line_color=COR_BRASIL, line_width=2,
        )

    y_valid = [v for v in media_vals if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 12) if y_valid else 12
    y_min = max(0, min(y_valid) - y_span * 0.45) if y_valid else 0
    y_max = min(1000, max(y_valid) + y_span * 0.72) if y_valid else 1000
    for ref in (media_ms, media_br):
        if ref is not None:
            y_min = min(y_min, float(ref) - 8.0)
            y_max = max(y_max, float(ref) + 8.0)

    tx_max = max(max(tx_vals) * 1.22, 40.0) if tx_vals else 60.0
    angulo = -48 if len(labels) > 6 else -32

    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, tx_max], secondary_y=True)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=labels,
        tickangle=angulo,
        tickfont=dict(size=8 if len(labels) > 8 else FONT_HUB_AXIS),
    )
    fig.update_layout(bargap=0.32)

    altura = altura or max(CHART_H_HUB, 300 if len(labels) > 8 else CHART_H_HUB)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        legenda_traces=True,
        refs_vline=True,
        notas=["Presentes 2 dias ÷ concluintes"],
    )
    _aplicar_eixos_hub(fig, secondary_y=True)
    fig.update_xaxes(showticklabels=True, ticks="outside", ticklen=4)
    fig.update_layout(margin=dict(b=max(52, 28 + len(labels) * 2)))
    _aplicar_hover_hub(fig)
    return fig


def _fig_hub_ranking_cre(
    tabelas: dict,
    anos_sel: list,
    *,
    altura: int = ALTURA_HUB_TERR,
) -> go.Figure | None:
    """Ranking horizontal de CREs por média geral (ano mais recente)."""
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        return None
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        return None
    ano_ref = anos_validos[-1]
    sub = df_evol[
        (df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == "Estadual")
    ].copy()
    col_media = "media_geral"
    if col_media not in sub.columns:
        return None
    sub = sub.dropna(subset=[col_media]).sort_values(col_media, ascending=True)
    if sub.empty:
        return None

    refs = medias_referencia_por_ano(tabelas, ano_ref)
    mg = refs.get("MEDIA_GERAL", {}) if refs else {}
    media_ms = mg.get("ms")
    media_br = mg.get("br")
    altura = _altura_hub_ranking(len(sub))
    fig = fig_ranking_horizontal(
        sub, "CRE", col_media,
        titulo="",
        cor=AZUL_PRINCIPAL,
        altura=altura,
        casas_decimais=1,
        media_ms=media_ms,
        media_br=media_br,
        x_range=[0, 1000],
        rotulo_media_ms="Média MS",
        rotulo_media_br="Média BR",
        modo_hub=True,
    )
    cores_usadas = _cores_ranking_presentes(
        sub[col_media].tolist(), media_ms, media_br,
    )
    return _estilo_fig_hub_ranking(
        fig, cores_ms_br=True, refs_vline_ms_br=True, cores_ranking=cores_usadas,
    )


def _fig_hub_participacao_cre(
    tabelas: dict,
    anos_sel: list,
    *,
    altura: int = ALTURA_HUB_TERR,
) -> go.Figure | None:
    """Taxa de participação efetiva por CRE (ano mais recente)."""
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        return None
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        return None
    ano_ref = anos_validos[-1]
    cres = sorted(
        df_evol.loc[df_evol["dependencia"] == "Estadual", "CRE"].dropna().unique()
    )
    if not cres:
        return None

    part = _participacao_cre_tabela(tabelas, cres, ano_ref, "Estadual")
    if part.empty or "Tx_Part_Efetiva" not in part.columns:
        return None
    sub = part.dropna(subset=["Tx_Part_Efetiva"]).sort_values(
        "Tx_Part_Efetiva", ascending=True,
    )
    if sub.empty:
        return None

    part_ms_df = participacao_ms_por_ano(tabelas, [ano_ref], "Estadual")
    media_ms = (
        float(part_ms_df.iloc[0]["Tx_Part_Efetiva"])
        if not part_ms_df.empty and pd.notna(part_ms_df.iloc[0]["Tx_Part_Efetiva"])
        else None
    )
    serie_br = _serie_tx_part_efetiva_br(tabelas, [ano_ref])
    media_br = float(serie_br.iloc[-1]) if not serie_br.empty else None
    altura = _altura_hub_ranking(len(sub))
    fig = fig_ranking_horizontal(
        sub, "CRE", "Tx_Part_Efetiva",
        titulo="",
        cor=COR_POSITIVO,
        altura=altura,
        casas_decimais=1,
        media_ms=media_ms,
        media_br=media_br,
        x_range=[0, 105],
        rotulo_media_ms="Média MS",
        rotulo_media_br="Média BR",
        modo_hub=True,
    )
    cores_usadas = _cores_ranking_presentes(
        sub["Tx_Part_Efetiva"].tolist(), media_ms, media_br,
    )
    return _estilo_fig_hub_ranking(
        fig,
        cores_ms_br=True,
        refs_vline_ms_br=True,
        cores_ranking=cores_usadas,
        notas=["Presentes 2 dias ÷ concluintes"],
    )


def _registros_delta_br_areas(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
    ano: int,
) -> pd.DataFrame | None:
    """Δ MS − BR por área em um ano (tabela ordenável por Delta)."""
    rows = df_dist_est[df_dist_est["ano"] == ano]
    if rows.empty:
        return None
    refs = medias_referencia_por_ano(tabelas, ano) if tabelas else {}
    registros = []
    for key in COLS_NOTAS:
        stats = stats_box_quantis(rows.iloc[0], key)
        if stats is None:
            continue
        ms = float(stats["mean"])
        br = None
        if refs and key in refs:
            br = refs[key].get("br")
        if (br is None or pd.isna(br)) and tabelas:
            br = media_nacional_ponderada(tabelas, ano, key, "Estadual")
        if br is None or pd.isna(br):
            continue
        registros.append({
            "AreaKey": key,
            "Abbr": AREAS.get(key, key),
            "Area": AREAS_COMPLETO.get(key, AREAS.get(key, key)),
            "Delta": ms - float(br),
            "MS": ms,
            "BR": float(br),
        })
    if not registros:
        return None
    return pd.DataFrame(registros)


def _ordenar_delta_br_areas(df: pd.DataFrame) -> pd.DataFrame:
    """Ordem fixa das áreas (CN→Redação) para comparar anos lado a lado."""
    ordem = {k: i for i, k in enumerate(COLS_NOTAS)}
    out = df.copy()
    out["_ord"] = out["AreaKey"].map(ordem)
    return out.sort_values("_ord", ascending=True).drop(columns=["_ord"])


def _x_range_delta_br_areas(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
    anos: list[int],
) -> list[float]:
    """Intervalo X comum (com folga para rótulos fora das barras)."""
    deltas: list[float] = []
    for ano in anos:
        df = _registros_delta_br_areas(df_dist_est, tabelas, ano)
        if df is not None and not df.empty:
            deltas.extend(df["Delta"].tolist())
    if not deltas:
        return [-22.0, 6.0]
    x_min = float(min(deltas))
    x_max = float(max(deltas))
    nucleo = max(x_max - x_min, 4.0)
    pad_rotulo = max(5.0, nucleo * 0.22)
    return [min(x_min - pad_rotulo, -2.0), max(x_max + pad_rotulo, 2.0)]


def _textpos_delta_br(valor: float, x_range: list[float]) -> str:
    """Rótulo dentro da barra quando há espaço; fora quando a barra é curta."""
    span = x_range[1] - x_range[0]
    return "inside" if abs(valor) >= span * 0.17 else "outside"


def _fig_hub_delta_br_painel_anual(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
) -> go.Figure | None:
    """Linha temporal: 30 barras verticais finas (6 anos × 5 áreas) — Δ MS − BR."""
    anos_plot = [
        ano for ano in ANOS_DISPONIVEIS
        if _registros_delta_br_areas(df_dist_est, tabelas, ano) is not None
    ]
    if not anos_plot:
        return None

    registros: list[dict] = []
    for ano in anos_plot:
        df_raw = _registros_delta_br_areas(df_dist_est, tabelas, ano)
        if df_raw is None or df_raw.empty:
            continue
        for _, row in _ordenar_delta_br_areas(df_raw).iterrows():
            registros.append({
                "ano": int(ano),
                "area_key": row["AreaKey"],
                "abbr": row["Abbr"],
                "area": row["Area"],
                "delta": float(row["Delta"]),
                "ms": float(row["MS"]),
                "br": float(row["BR"]),
            })
    if not registros:
        return None

    xs: list[int] = []
    ys: list[float] = []
    cores: list[str] = []
    abbrs: list[str] = []
    custom: list[list] = []
    for i, rec in enumerate(registros):
        xs.append(i)
        ys.append(rec["delta"])
        cores.append(CORES_AREAS.get(rec["area_key"], AZUL_PRINCIPAL))
        abbrs.append(rec["abbr"])
        custom.append([rec["area"], rec["ano"], rec["ms"], rec["br"]])

    max_abs = max(abs(v) for v in ys) if ys else 10.0
    y_lim = max(max_abs * 1.18, 6.0)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            marker_color=cores,
            marker_line=dict(width=0),
            width=0.62,
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                "Δ vs BR: %{y:+.1f} pts<br>"
                "MS: %{customdata[2]:.1f} · BR: %{customdata[3]:.1f}"
                "<extra></extra>"
            ),
            customdata=custom,
            showlegend=False,
        ),
    )
    fig.add_hline(
        y=0,
        line_color=TEMA["texto_muted"],
        line_width=1.5,
        opacity=0.65,
    )

    for x_i, delta in zip(xs, ys):
        if abs(delta) < 0.4:
            continue
        cor_txt = COR_POSITIVO if delta >= 0 else COR_CRITICO
        _anotacao_hub(
            fig,
            x=x_i,
            y=delta,
            text=f"<b>{delta:+.0f}</b>",
            showarrow=False,
            yanchor="bottom" if delta >= 0 else "top",
            yshift=4 if delta >= 0 else -4,
            font=dict(
                size=7,
                color=cor_txt,
                family="Plus Jakarta Sans, sans-serif",
            ),
        )

    fig.update_xaxes(
        tickvals=[],
        ticktext=[],
        showticklabels=False,
        showline=True,
        linecolor=TEMA["borda"],
        linewidth=1,
        showgrid=False,
    )

    anos_unicos = sorted({r["ano"] for r in registros})
    n_por_ano = len(COLS_NOTAS)
    for j, ano in enumerate(anos_unicos):
        idxs = [i for i, r in enumerate(registros) if r["ano"] == ano]
        if not idxs:
            continue
        x_centro = (min(idxs) + max(idxs)) / 2
        _anotacao_hub(
            fig,
            x=x_centro,
            xref="x",
            yref="paper",
            y=0.02,
            text=f"<b>{ano}</b>",
            showarrow=False,
            font=dict(
                size=9,
                color=AZUL_ESCURO,
                family="Plus Jakarta Sans, sans-serif",
            ),
        )
        if j > 0:
            sep = min(idxs) - 0.5
            fig.add_shape(
                type="line",
                x0=sep, x1=sep,
                xref="x",
                y0=-y_lim, y1=y_lim,
                yref="y",
                line=dict(color=TEMA["borda"], width=1, dash="dot"),
            )

    fig.update_yaxes(
        range=[-y_lim, y_lim],
        showticklabels=False,
        ticks="",
        showgrid=False,
        zeroline=False,
        showline=False,
    )

    fig = aplicar_tema(fig, CHART_H_HUB, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        legenda_traces=False,
        legenda_areas=True,
        cores_delta_br=True,
    )
    _aplicar_eixos_hub(fig, manter_linha_x=True)
    fig.update_layout(bargap=0.04, bargroupgap=0.02)
    _aplicar_hover_hub(fig, unified=False, horizontal=False)
    return fig


def _hub_tem_delta_br_areas(df_dist_est: pd.DataFrame, tabelas: dict) -> bool:
    for ano in ANOS_DISPONIVEIS:
        df = _registros_delta_br_areas(df_dist_est, tabelas, ano)
        if df is not None and not df.empty:
            return True
    return False


def _render_hub_delta_br_por_ano(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
) -> bool:
    """Painel anual compacto: Δ vs BR (2019–2024), só rótulos de dados."""
    fig = _fig_hub_delta_br_painel_anual(df_dist_est, tabelas)
    if fig is None:
        return False
    _render_widget_grafico_hub("Diferença vs Brasil por área", fig)
    return True


def _fig_hub_medias_dependencia(
    df_filt_ms: pd.DataFrame,
    ano_ref: int,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure | None:
    """Média geral por dependência administrativa (ano de referência)."""
    df = df_filt_ms[df_filt_ms["NU_ANO"] == ano_ref]
    if df.empty:
        return None
    deps = [d for d in ORDEM_DEP if d in df["DEP_ADM"].dropna().unique()]
    if not deps:
        return None
    registros = []
    for dep in deps:
        sub = df[df["DEP_ADM"] == dep]
        if sub.empty:
            continue
        if "MEDIA_GERAL" in sub.columns and sub["MEDIA_GERAL"].notna().any():
            media = float(sub["MEDIA_GERAL"].mean())
        else:
            cols = [c for c in COLS_NOTAS if c in sub.columns]
            if not cols:
                continue
            media = float(sub[cols].mean(axis=1).mean())
        registros.append({"Dep": dep, "Média": round(media, 1)})
    if not registros:
        return None
    g = pd.DataFrame(registros)
    y_max = min(1000, float(g["Média"].max()) * 1.14)
    fig = go.Figure(go.Bar(
        x=g["Dep"], y=g["Média"],
        marker_color=[CORES_DEP.get(d, AZUL_PRINCIPAL) for d in g["Dep"]],
        text=g["Média"].apply(lambda x: f"{x:.0f}"),
        textposition="outside",
        textfont=dict(size=FONT_HUB_DATA),
        hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
    ))
    fig.update_yaxes(range=[0, y_max])
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        deps=deps,
        legenda_traces=False,
    )
    fig.update_xaxes(
        type="category",
        tickangle=-18,
        categoryorder="array",
        categoryarray=deps,
    )
    _aplicar_eixos_hub(fig)
    fig.update_xaxes(tickangle=-18)
    _aplicar_hover_hub(fig)
    return fig


def _fig_hub_box_areas_ano(
    df_dist_est: pd.DataFrame,
    ano_ref: int,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure | None:
    """Boxplots das 5 áreas — ano de referência (rede estadual)."""
    rows = df_dist_est[df_dist_est["ano"] == ano_ref]
    if rows.empty:
        return None
    fig = go.Figure()
    all_stats: list[dict] = []
    for col in COLS_NOTAS:
        stats = stats_box_quantis(rows.iloc[0], col)
        if stats is None:
            continue
        nome = AREAS_COMPLETO.get(col, AREAS.get(col, col))
        all_stats.append(stats)
        _add_box_series(
            fig, name=nome, color=CORES_AREAS[col],
            x_vals=[nome], stats_list=[stats],
            showlegend=False, rotulos_quantis=False,
            box_width=0.55,
        )
    if not all_stats:
        return None
    y0, y1 = _range_y_box_stats(all_stats, pad=38)
    fig.update_layout(
        yaxis=dict(range=[y0, y1]),
        boxmode="group",
    )
    fig.update_xaxes(tickangle=-22)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        legenda_areas=True,
        notas=["Passe o mouse na caixa para ver quartis"],
        legenda_traces=False,
    )
    _aplicar_eixos_hub(fig)
    _aplicar_hover_hub(fig)
    return fig


def _render_hub_panorama(
    diag: dict,
    periodo: str,
    *,
    tabelas: dict | None = None,
    anos_sel: list | None = None,
    df_bruta_ms: pd.DataFrame | None = None,
    df_filt_ms: pd.DataFrame | None = None,
) -> None:
    """Grid 3×3 denso: participação, desempenho e território (padrão BI)."""
    tem_ms = len(diag.get("serie_medias", [])) > 0
    tem_rank = (
        tabelas is not None
        and anos_sel
        and df_bruta_ms is not None
        and df_filt_ms is not None
        and not df_bruta_ms.empty
    )
    tem_desemp = (
        tabelas is not None
        and df_filt_ms is not None
        and not df_filt_ms.empty
    )
    tem_terr = tabelas is not None and anos_sel

    df_dist_est = (
        _df_dist_estadual_hub(tabelas, df_filt_ms)
        if tem_desemp and df_filt_ms is not None and tabelas is not None
        else pd.DataFrame()
    )
    anos_validos = sorted(int(a) for a in (anos_sel or []))
    ano_ref = (
        int(max(df_dist_est["ano"]))
        if not df_dist_est.empty
        else (anos_validos[-1] if anos_validos else None)
    )

    fig_ms = _fig_destaque_evolucao_ms(diag) if tem_ms else None
    fig_rank_uf = (
        _fig_ranking_participacao_nacional(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms, diag,
        )
        if tem_rank else None
    )
    fig_evol = (
        _fig_hub_evolucao_areas_linhas(df_dist_est, tabelas)
        if tem_desemp and not df_dist_est.empty else None
    )
    fig_box_mg = (
        _fig_hub_box_media_geral(df_dist_est)
        if not df_dist_est.empty else None
    )
    fig_cre_combo = (
        _fig_hub_cre_combo_media_participacao(tabelas, anos_sel)
        if tem_terr else None
    )
    tem_delta = (
        not df_dist_est.empty and tabelas
        and _hub_tem_delta_br_areas(df_dist_est, tabelas)
    )
    fig_deps = (
        _fig_hub_medias_dependencia(df_filt_ms, ano_ref)
        if tem_desemp and ano_ref is not None and df_filt_ms is not None else None
    )
    fig_box_areas = (
        _fig_hub_box_areas_ano(df_dist_est, ano_ref)
        if not df_dist_est.empty and ano_ref is not None else None
    )

    if not any((
        fig_ms, fig_rank_uf, fig_evol, fig_box_mg,
        fig_cre_combo, tem_delta, fig_deps, fig_box_areas,
    )):
        return

    ano_lbl = ano_ref if ano_ref is not None else "—"

    card_ms = ("Rede estadual · média e participação", fig_ms, "")
    card_rank = ("Ranking entre estados · média e participação", fig_rank_uf, "")
    card_box_mg = ("Distribuição · média geral", fig_box_mg, "")
    card_evol = ("Evolução por área de conhecimento", fig_evol, "")
    card_cre_combo = (
        f"Coordenadorias · média e participação ({ano_lbl})", fig_cre_combo, "",
    )
    card_deps = (f"Média por dependência administrativa ({ano_lbl})", fig_deps, "")
    card_box_areas = (f"Distribuição por área ({ano_lbl})", fig_box_areas, "")

    _render_html(
        f'<div class="hub-panorama-grid" data-hub-build="{HUB_BUILD_ID}">'
    )
    col_esq, col_meio, col_dir = st.columns(HUB_COL_LAYOUT, gap="small")
    with col_esq:
        _fragment_hub_coluna(
            [c for c in (card_ms, card_rank, card_box_mg) if c[1] is not None],
            key="hub_col_esq",
        )
    with col_meio:
        _fragment_hub_coluna(
            [c for c in (card_evol,) if c[1] is not None],
            key="hub_col_meio",
        )
        if tem_delta:
            _fragment_hub_delta(df_dist_est, tabelas)
    with col_dir:
        _fragment_hub_coluna(
            [c for c in (card_cre_combo, card_deps, card_box_areas) if c[1] is not None],
            key="hub_col_dir",
        )
    _render_html("</div>")


def _posicoes_ms_desempenho_uf_por_ano(
    tabelas: dict,
    anos_sel: list,
) -> list[dict]:
    """Posição do MS no ranking de média geral por UF (rede estadual), por ano."""
    df_des = tabelas.get("desempenho_uf", pd.DataFrame())
    if df_des.empty or not anos_sel:
        return []
    col_media = (
        "media_media_geral" if "media_media_geral" in df_des.columns else "media_geral"
    )
    if col_media not in df_des.columns:
        return []

    def _media_pond(g: pd.DataFrame) -> float:
        w = g["estudantes"].fillna(0).astype(float)
        return float(np.average(g[col_media], weights=w)) if w.sum() > 0 else np.nan

    posicoes: list[dict] = []
    for ano in sorted(int(a) for a in anos_sel):
        sub = df_des[
            (df_des["ano"] == ano) & (df_des["dependencia"] == "Estadual")
        ]
        if sub.empty:
            continue
        ranking = (
            sub.groupby("uf", observed=True)
            .apply(_media_pond)
            .dropna()
            .round(1)
            .sort_values(ascending=False)
        )
        ranking.index = ranking.index.astype(str).str.upper()
        ranking = ranking[ranking.index.str.len() == 2]
        if "MS" not in ranking.index:
            continue
        posicoes.append(dict(
            Ano=ano,
            Posição=int(list(ranking.index).index("MS")) + 1,
            Total=len(ranking),
            Media=float(ranking["MS"]),
        ))
    return posicoes


def _fig_hub_posicao_uf(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
    *,
    metrica: str = "part",
    altura: int = ALTURA_HUB_RANK,
) -> go.Figure | None:
    """Posição do MS entre UFs — um indicador por painel (capa em 4 colunas)."""
    if metrica == "part":
        dados = _posicoes_ms_participacao_uf(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms,
        )
        nome = "Participação"
        cor_linha = VERDE_MS
        cor_texto = COR_TEXTO_DENTRO_BARRA
        rotulos = [
            f"{int(d['Posição'])}º · {d['Taxa']:.0f}%"
            for d in dados
        ]
    else:
        dados = _posicoes_ms_desempenho_uf_por_ano(tabelas, anos_sel)
        nome = "Média geral"
        cor_linha = AZUL_PRINCIPAL
        cor_texto = AZUL_ESCURO
        rotulos = [
            f"{int(d['Posição'])}º · {d['Media']:.0f}"
            for d in dados
        ]

    if not dados:
        return None

    df = pd.DataFrame(dados)
    n_total = int(df["Total"].max()) if "Total" in df.columns else 27
    terco = n_total / 3
    cores = [_cor_posicao_terco(int(r["Posição"]), n_total) for _, r in df.iterrows()]

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=terco, fillcolor=COR_POSITIVO, opacity=0.07, line_width=0)
    fig.add_hrect(y0=terco, y1=2 * terco, fillcolor=COR_ATENCAO, opacity=0.06, line_width=0)
    fig.add_hrect(y0=2 * terco, y1=n_total + 1, fillcolor=COR_CRITICO, opacity=0.05, line_width=0)
    fig.add_trace(go.Scatter(
        x=df["Ano"], y=df["Posição"],
        mode="lines+markers+text",
        name=nome,
        text=rotulos,
        textposition="top center",
        textfont=dict(
            size=8, color=cor_texto,
            family="Plus Jakarta Sans, sans-serif",
        ),
        line=dict(color=cor_linha, width=2.2),
        marker=dict(size=7, color=cores, line=dict(width=1.2, color="white")),
    ))
    fig.update_yaxes(autorange="reversed", range=[0.5, n_total + 0.5])
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(
        showlegend=False,
        margin=dict(t=12, b=36, r=6, l=6),
        hovermode="x unified",
    )
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _aplicar_eixos_hub(fig)
    return fig


def _fig_posicao_ms_nacional(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
    *,
    altura: int = 360,
) -> go.Figure | None:
    """Versão combinada (sub-aba): participação + média geral."""
    pos_part = _posicoes_ms_participacao_uf(tabelas, anos_sel, df_bruta_ms, df_filt_ms)
    pos_des = _posicoes_ms_desempenho_uf_por_ano(tabelas, anos_sel)
    if not pos_part and not pos_des:
        return None

    n_total = 27
    if pos_part:
        n_total = max(n_total, max(p["Total"] for p in pos_part))
    if pos_des:
        n_total = max(n_total, max(p["Total"] for p in pos_des))
    terco = n_total / 3

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=terco, fillcolor=COR_POSITIVO, opacity=0.07, line_width=0)
    fig.add_hrect(y0=terco, y1=2 * terco, fillcolor=COR_ATENCAO, opacity=0.06, line_width=0)
    fig.add_hrect(y0=2 * terco, y1=n_total + 1, fillcolor=COR_CRITICO, opacity=0.05, line_width=0)

    if pos_part:
        df_p = pd.DataFrame(pos_part)
        cores_p = [_cor_posicao_terco(int(r["Posição"]), n_total) for _, r in df_p.iterrows()]
        fig.add_trace(go.Scatter(
            x=df_p["Ano"], y=df_p["Posição"],
            mode="lines+markers+text",
            name="Posição · participação",
            text=[f"{int(r['Posição'])}º · {r['Taxa']:.0f}%" for _, r in df_p.iterrows()],
            textposition="top center",
            textfont=dict(size=9, color=COR_TEXTO_DENTRO_BARRA, family="Plus Jakarta Sans, sans-serif"),
            line=dict(color=VERDE_MS, width=2.2),
            marker=dict(size=8, color=cores_p, line=dict(width=1.2, color="white")),
        ))

    if pos_des:
        df_d = pd.DataFrame(pos_des)
        cores_d = [_cor_posicao_terco(int(r["Posição"]), n_total) for _, r in df_d.iterrows()]
        fig.add_trace(go.Scatter(
            x=df_d["Ano"], y=df_d["Posição"],
            mode="lines+markers+text",
            name="Posição · média geral",
            text=[f"{int(r['Posição'])}º · {r['Media']:.0f}" for _, r in df_d.iterrows()],
            textposition="bottom center",
            textfont=dict(size=9, color=AZUL_ESCURO, family="Plus Jakarta Sans, sans-serif"),
            line=dict(color=AZUL_PRINCIPAL, width=2.2),
            marker=dict(size=8, color=cores_d, line=dict(width=1.2, color="white")),
        ))

    fig.update_yaxes(autorange="reversed", range=[0.5, n_total + 0.5])
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(
        legend=_legenda_padrao(y_pos=-0.22, font_size=9, entry_width=110),
        margin=dict(t=14, b=56, r=12, l=12),
        hovermode="x unified",
    )
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _aplicar_eixos_hub(fig)
    return fig


