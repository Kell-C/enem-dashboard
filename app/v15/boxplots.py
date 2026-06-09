"""Boxplots, hover e finalização de gráficos de detalhe — painel ENEM v15."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from viz.chart_layout import (
    CHART_H_BOX_WIDE,
    CHART_H_STANDARD,
    hover_padrao,
    legenda_inferior,
    margem_detalhe,
    texto_hover_box,
)

from app.v15.theme import (  # noqa: F401
    AZUL_ESCURO,
    AZUL_PRINCIPAL,
    FONT_AXIS,
    FONT_CHART,
    FONT_HOVER,
    FONT_HUB_DATA,
    FONT_LEGEND,
    TEMA,
)
from app.v15.plotly_theme import aplicar_tema


def _stats_box(s: pd.Series) -> Optional[dict]:
    s = s.dropna()
    if len(s) < 5:
        return None
    q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
    iqr = q3 - q1
    return dict(
        q1=q1, median=float(s.median()), q3=q3,
        mean=float(s.mean()), std=float(s.std()), n=int(len(s)),
        low=max(float(s.min()), q1 - 1.5 * iqr),
        up=min(float(s.max()), q3 + 1.5 * iqr),
    )


def _texto_hover_box(rotulo: str, stats: dict) -> str:
    """Hover do boxplot: delega ao padrão centralizado em viz.chart_layout."""
    return texto_hover_box(rotulo, stats)


def _add_rotulos_box_visiveis(
    fig: go.Figure,
    x_vals: list,
    stats_list: list[dict],
    *,
    cor: str,
    font_size: int = FONT_HUB_DATA,
    compacto: bool = False,
) -> None:
    """Rótulos fixos nos boxplots; modo compacto = máximo, mediana e mínimo."""
    if not stats_list:
        return
    gap = 9 if compacto else 11
    xs = [str(x) for x in x_vals]
    skip = dict(showlegend=False, hoverinfo="skip")
    sec = dict(
        size=max(font_size - 1, 8),
        color=TEMA["texto_secundario"],
        family="Source Sans 3, sans-serif",
    )

    fig.add_trace(go.Scatter(
        x=xs, y=[s["up"] + gap for s in stats_list],
        mode="text", text=[f"{s['up']:.0f}" for s in stats_list],
        textposition="top center",
        textfont=dict(size=font_size, color=cor, family="Source Sans 3, sans-serif"),
        **skip,
    ))
    if not compacto:
        fig.add_trace(go.Scatter(
            x=xs, y=[s["q3"] + 4 for s in stats_list],
            mode="text", text=[f"{s['q3']:.0f}" for s in stats_list],
            textposition="top center", textfont=sec, **skip,
        ))
    fig.add_trace(go.Scatter(
        x=xs, y=[s["median"] for s in stats_list],
        mode="text", text=[f"{s['median']:.0f}" for s in stats_list],
        textposition="middle left",
        textfont=dict(
            size=font_size, color=AZUL_ESCURO,
            family="Plus Jakarta Sans, sans-serif",
        ),
        **skip,
    ))
    if not compacto:
        fig.add_trace(go.Scatter(
            x=xs, y=[s["q1"] - 4 for s in stats_list],
            mode="text", text=[f"{s['q1']:.0f}" for s in stats_list],
            textposition="bottom center", textfont=sec, **skip,
        ))
    fig.add_trace(go.Scatter(
        x=xs, y=[max(0.0, s["low"] - gap) for s in stats_list],
        mode="text", text=[f"{s['low']:.0f}" for s in stats_list],
        textposition="bottom center",
        textfont=dict(size=font_size, color=cor, family="Source Sans 3, sans-serif"),
        **skip,
    ))


def _range_y_box_stats(stats_list: list[dict], *, pad: float = 28) -> tuple[float, float]:
    """Faixa Y com folga para rótulos externos do boxplot."""
    lows = [s["low"] for s in stats_list]
    ups = [s["up"] for s in stats_list]
    if not lows:
        return 0.0, 1000.0
    return max(0.0, min(lows) - pad), min(1000.0, max(ups) + pad)


def _neutralizar_hover_rotulos(fig: go.Figure) -> None:
    """Traces só-texto (rótulos auxiliares) não devem roubar o hover dos dados."""
    for tr in fig.data:
        mode = str(getattr(tr, "mode", "") or "")
        partes = {p.strip() for p in mode.split("+") if p.strip()}
        if partes != {"text"}:
            continue
        tr.hoverinfo = "skip"
        tr.update(marker=dict(size=0.001, opacity=0, color="rgba(0,0,0,0)"))


def _anotacao_hub(fig: go.Figure, **kwargs) -> None:
    """Anotação de rótulo que não intercepta o hover do Plotly."""
    kwargs.setdefault("captureevents", False)
    fig.add_annotation(**kwargs)


def _neutralizar_hover_anotacoes(fig: go.Figure) -> None:
    """Garante que anotações de layout não bloqueiem tooltips."""
    for ann in list(fig.layout.annotations or []):
        ann.captureevents = False


def _preparar_hover_fig(fig: go.Figure) -> None:
    """Ajustes finais de hover antes de renderizar no Streamlit."""
    _neutralizar_hover_anotacoes(fig)
    _neutralizar_hover_rotulos(fig)
    fig.update_layout(
        hovermode="closest",
        dragmode=False,
        hoverdistance=48,
        spikedistance=-1,
    )


def _aplicar_hover_hub(
    fig,
    *,
    unified: bool = False,
    horizontal: bool = False,
) -> None:
    """Hover nos gráficos hub; ``closest`` é mais confiável no Streamlit."""
    if horizontal:
        hovermode = "closest"
    elif unified:
        hovermode = "x unified"
    else:
        hovermode = "closest"
    fig.update_layout(
        hovermode=hovermode,
        hoverdistance=32,
        spikedistance=-1,
        dragmode=False,
        showlegend=False,
        hoverlabel=hover_padrao(
            bgcolor=TEMA["bg_card"],
            texto=TEMA["texto"],
            borda=TEMA["borda"],
            font_size=FONT_HOVER,
        ),
    )
    _preparar_hover_fig(fig)
    for tr in fig.data:
        if getattr(tr, "hoverinfo", None) == "skip":
            continue
        if getattr(tr, "hovertemplate", None) or getattr(tr, "hovertext", None):
            continue
        if getattr(tr, "type", None) == "box":
            tr.hoverinfo = "text"


def _finalizar_boxplot(
    fig: go.Figure,
    titulo: str,
    *,
    altura: int = CHART_H_BOX_WIDE,
    n_legend: int = 4,
    eixo_x: str = "Área de conhecimento",
    eixo_y: str = "Nota",
    y_range: tuple[float, float] = (0, 1000),
) -> go.Figure:
    """Layout padronizado para boxplots de detalhe (legenda, margem, hover, título)."""
    fig.update_layout(
        title=titulo,
        boxmode="group",
        yaxis=dict(title=eixo_y, range=list(y_range)),
        xaxis=dict(title=eixo_x),
    )
    fig = aplicar_tema(fig, altura, limpar_titulo=False)
    fig.update_layout(
        showlegend=True,
        margin=margem_detalhe(legenda_inferior=True, n_legend=n_legend),
        legend=legenda_inferior(n_legend, font_size=FONT_LEGEND),
    )
    _aplicar_hover_hub(fig)
    return fig


def _finalizar_grafico(
    fig: go.Figure,
    *,
    altura: int = CHART_H_STANDARD,
    n_legend: int = 0,
    titulo: str | None = None,
    hover_unified: bool = False,
    margin: dict | None = None,
) -> go.Figure:
    """Layout padronizado para barras/linhas (preserva legenda inferior após o tema)."""
    if titulo:
        fig.update_layout(title=titulo)
    fig = aplicar_tema(fig, altura)
    layout_kw: dict = {}
    if n_legend > 0:
        layout_kw["showlegend"] = True
        layout_kw["legend"] = legenda_inferior(n_legend, font_size=FONT_LEGEND)
        m = margem_detalhe(legenda_inferior=True, n_legend=n_legend)
        if margin:
            m.update(margin)
        layout_kw["margin"] = m
    elif margin:
        layout_kw["margin"] = margin
    if layout_kw:
        fig.update_layout(**layout_kw)
    _aplicar_hover_hub(fig, unified=hover_unified)
    return fig


def _add_rotulo_mediana_box(
    fig: go.Figure,
    median: float,
    upper: float,
    x_val,
    *,
    cor: Optional[str] = None,
) -> None:
    """Rótulo discreto da mediana, centralizado acima da caixa.

    Implementado como trace ``go.Scatter(mode="text")`` — e NÃO como
    ``fig.add_annotation`` — de propósito: anotações de layout com ``xref="x"``
    sobre um eixo categórico colapsam boxplots de quantis pré-computados no
    Plotly (todas as caixas são empurradas para a 1ª categoria). O texto como
    trace respeita as posições categóricas e evita o colapso.
    """
    if x_val is None:
        return
    fig.add_trace(
        go.Scatter(
            x=[str(x_val)],
            y=[upper + 12],
            mode="text",
            text=[f"<b>{median:.0f}</b>"],
            textposition="top center",
            textfont=dict(
                size=FONT_HUB_DATA, color=cor or TEMA["texto"],
                family="Source Sans 3, sans-serif",
            ),
            showlegend=False,
            hoverinfo="skip",
        )
    )


def _add_box_stats(fig, stats: dict, name: str, color: str, x_val=None,
                   legendgroup=None, showlegend=True,
                   offsetgroup=None, alignmentgroup=None, *,
                   rotulo_mediana: bool = False,
                   rotulos_quantis: bool = False,
                   rotulos_compactos: bool = False,
                   box_width: float = 0.72,
                   hover_titulo: Optional[str] = None):
    """Adiciona um boxplot (uma caixa) a partir de estatísticas pré-calculadas."""
    rotulo = hover_titulo or (str(x_val) if x_val is not None else name)
    kw = dict(
        name=name,
        q1=[stats["q1"]], median=[stats["median"]], q3=[stats["q3"]],
        mean=[stats["mean"]],
        lowerfence=[stats["low"]], upperfence=[stats["up"]],
        marker_color=color,
        line=dict(color=color, width=2),
        fillcolor=_hex_to_rgba(color, 0.32),
        boxmean=False,
        width=box_width,
        hoverinfo="text",
        hovertext=[_texto_hover_box(rotulo, stats)],
        legendgroup=legendgroup or name, showlegend=showlegend,
    )
    if x_val is not None:
        kw["x"] = [str(x_val)]
    if offsetgroup is not None:
        kw["offsetgroup"] = offsetgroup
    if alignmentgroup is not None:
        kw["alignmentgroup"] = alignmentgroup
    fig.add_trace(go.Box(**kw))
    if rotulos_quantis and x_val is not None:
        _add_rotulos_box_visiveis(
            fig, [x_val], [stats], cor=color, compacto=rotulos_compactos,
        )
    elif rotulo_mediana:
        _add_rotulo_mediana_box(fig, stats["median"], stats["up"], x_val, cor=color)


def _add_box_series(
    fig: go.Figure,
    *,
    name: str,
    color: str,
    x_vals: list,
    stats_list: list[dict],
    showlegend: bool = True,
    legendgroup: Optional[str] = None,
    rotulo_mediana: bool = False,
    rotulos_quantis: bool = False,
    rotulos_compactos: bool = False,
    box_width: float = 0.72,
) -> None:
    """Adiciona UMA série de boxplots (um trace, várias caixas) com arrays de x."""
    if not stats_list:
        return
    xs = [str(x) for x in x_vals]
    hovertext = [_texto_hover_box(x, s) for x, s in zip(xs, stats_list)]
    fig.add_trace(go.Box(
        name=name,
        x=xs,
        q1=[s["q1"] for s in stats_list],
        median=[s["median"] for s in stats_list],
        q3=[s["q3"] for s in stats_list],
        mean=[s["mean"] for s in stats_list],
        lowerfence=[s["low"] for s in stats_list],
        upperfence=[s["up"] for s in stats_list],
        marker_color=color,
        line=dict(color=color, width=2),
        fillcolor=_hex_to_rgba(color, 0.32),
        boxmean=False,
        width=box_width,
        hoverinfo="text",
        hovertext=hovertext,
        legendgroup=legendgroup or name, showlegend=showlegend,
    ))
    if rotulos_quantis:
        _add_rotulos_box_visiveis(
            fig, x_vals, stats_list, cor=color, compacto=rotulos_compactos,
        )
    elif rotulo_mediana:
        for x, s in zip(xs, stats_list):
            _add_rotulo_mediana_box(fig, s["median"], s["up"], x, cor=color)


def _add_box(fig, s: pd.Series, name: str, color: str, x_val=None,
             legendgroup=None, showlegend=True, *,
             rotulo_mediana: bool = False,
             hover_titulo: Optional[str] = None):
    st_ = _stats_box(s)
    if st_ is None:
        return
    _add_box_stats(
        fig, st_, name, color, x_val=x_val,
        legendgroup=legendgroup, showlegend=showlegend,
        rotulo_mediana=rotulo_mediana, hover_titulo=hover_titulo,
    )


def _categorias_eixo_x(fig: go.Figure, x_val=None, fallback: str = "") -> list[str]:
    """Ordem das categorias no eixo X a partir dos boxplots já desenhados."""
    cats: list[str] = []
    for tr in fig.data:
        if getattr(tr, "type", None) == "box" and getattr(tr, "x", None) is not None:
            for v in tr.x:
                sv = str(v)
                if sv not in cats:
                    cats.append(sv)
    if x_val is not None:
        sv = str(x_val)
        if sv not in cats:
            cats.append(sv)
    elif fallback and fallback not in cats:
        cats.append(fallback)
    return cats


def _remap_traces_x_numeric(fig: go.Figure, categorias: list[str]) -> None:
    """Converte eixo X categórico em índices numéricos (permite jitter no scatter)."""
    if not categorias:
        return
    cat_index = {c: i for i, c in enumerate(categorias)}
    for i, tr in enumerate(fig.data):
        if getattr(tr, "type", None) == "box" and getattr(tr, "x", None) is not None:
            fig.data[i].x = [cat_index.get(str(v), 0) for v in tr.x]
    fig.update_xaxes(
        type="linear",
        tickmode="array",
        tickvals=list(range(len(categorias))),
        ticktext=categorias,
    )


def _add_scatter_notas(
    fig: go.Figure,
    x_val,
    notas: pd.Series,
    *,
    color: str = "rgba(13,110,253,0.35)",
    name: str = "Estudantes",
    max_pontos: int = 400,
    showlegend: bool = False,
    legendgroup: Optional[str] = None,
) -> None:
    """Pontos individuais com jitter horizontal (strip plot sobre boxplot)."""
    if notas is None or notas.empty:
        return
    s = pd.to_numeric(notas, errors="coerce").dropna()
    s = s[s > 0]
    if s.empty:
        return
    if len(s) > max_pontos:
        s = s.sample(max_pontos, random_state=42)
    rng = np.random.default_rng(42)
    jitter = rng.uniform(-0.22, 0.22, size=len(s))
    rotulo = str(x_val) if x_val is not None else name
    cats = _categorias_eixo_x(fig, x_val, fallback=name)
    if not cats:
        cats = [rotulo]
    _remap_traces_x_numeric(fig, cats)
    idx = cats.index(rotulo) if rotulo in cats else 0
    fig.add_trace(go.Scatter(
        x=[idx + float(j) for j in jitter],
        y=s.tolist(),
        mode="markers",
        name=name,
        legendgroup=legendgroup or name,
        showlegend=showlegend,
        marker=dict(size=5, color=color, line=dict(width=0), opacity=0.55),
        hovertemplate=f"<b>{rotulo}</b><br>Nota: %{{y:.1f}}<extra></extra>",
        xaxis="x",
    ))


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Converte '#RRGGBB' em 'rgba(r,g,b,alpha)' para uso em bgcolor translúcido."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
