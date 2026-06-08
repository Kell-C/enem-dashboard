"""
Padrões de tamanho, margem, legenda e hover para gráficos Plotly do painel ENEM.
"""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go

# --- Alturas padronizadas (px) ---
# Hub: altura única por slot para alinhar colunas da capa
CHART_H_HUB = 276
CHART_H_HUB_EVOL = 276
CHART_H_HUB_RANK = 276
CHART_H_HUB_DELTA_ROW = 88
CHART_H_STANDARD = 420
CHART_H_BOX = 460
CHART_H_BOX_WIDE = 540
CHART_H_HIST = 400
CHART_H_HIST_GRID = 520
CHART_H_RANKING = 480
CHART_H_EVOLUCAO = 440
CHART_H_PARTICIPACAO = 540
CHART_H_HIST_ROW = 260

# Aliases legados do hub (compatibilidade)
ALTURA_HUB_MS = CHART_H_HUB
ALTURA_HUB_RANK = CHART_H_HUB_RANK
ALTURA_HUB_EVOL = CHART_H_HUB_EVOL
ALTURA_HUB_TERR = CHART_H_HUB
ALTURA_HUB_TERR_MAX = CHART_H_HUB

PLOTLY_HUB_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "responsive": True,
    "staticPlot": False,
    "doubleClick": False,
}


CHART_H_HUB_SLOT = CHART_H_HUB


def margem_hub(*, rank: bool = False, topo: bool = False, com_legenda: bool = False) -> dict:
    """Margens compactas para gráficos da capa hub."""
    if rank:
        return dict(t=8, b=48 if com_legenda else 28, r=8, l=64)
    t = 28 if topo else 6
    b = 56 if com_legenda else 32
    return dict(t=t, b=b, r=10, l=40)


def legenda_hub_interna(
    n_itens: int = 2,
    *,
    font_size: int = 10,
    y_paper: float = 0.06,
) -> dict:
    """Legenda horizontal na faixa inferior (paper), empilhada a partir da base."""
    n = max(1, min(n_itens, 7))
    ew = max(30, 44 - n * 2) if n >= 5 else max(44, 72 - n * 8)
    return dict(
        orientation="h",
        yanchor="bottom",
        y=y_paper,
        yref="paper",
        x=0.5,
        xanchor="center",
        entrywidth=ew,
        entrywidthmode="pixels",
        tracegroupgap=3 if n >= 5 else 6,
        itemsizing="constant",
        font=dict(size=font_size),
        bgcolor="rgba(255,255,255,0.88)",
        borderwidth=0,
    )


def margem_detalhe(*, legenda_inferior: bool = False, n_legend: int = 0) -> dict:
    """Margens para gráficos de detalhe (não-hub)."""
    b = 80 + (min(n_legend, 8) * 14 if legenda_inferior else 0)
    return dict(l=24, r=48, t=56, b=b)


def legenda_inferior(n_itens: int = 4, *, font_size: int = 12, entry_width: int = 115) -> dict:
    """Legenda horizontal abaixo do plot, com espaçamento proporcional ao nº de itens."""
    n = max(1, min(n_itens, 8))
    y = -0.16 - (n - 1) * 0.032
    return dict(
        orientation="h",
        yanchor="top",
        y=y,
        xanchor="center",
        x=0.5,
        entrywidth=entry_width,
        entrywidthmode="pixels",
        tracegroupgap=8,
        font=dict(size=font_size),
        bgcolor="rgba(255,255,255,0.9)",
        borderwidth=0,
    )


def texto_hover_box(rotulo: str, stats: dict) -> str:
    """Hover padronizado para boxplots (quantis + n + desvio quando disponível)."""
    linhas = [
        f"<b>{rotulo}</b>",
        f"Média: {stats['mean']:.1f}",
        f"Mediana: {stats['median']:.0f}",
    ]
    if stats.get("std") is not None and not _is_nan(stats.get("std")):
        linhas.append(f"Desvio padrão: {stats['std']:.1f}")
    linhas.extend([
        f"Quartil superior: {stats['q3']:.0f}",
        f"Quartil inferior: {stats['q1']:.0f}",
        f"Máximo: {stats['up']:.0f}",
        f"Mínimo: {stats['low']:.0f}",
    ])
    if stats.get("n"):
        linhas.append(f"n = {stats['n']}")
    return "<br>".join(linhas)


def _is_nan(val) -> bool:
    try:
        import math
        return val is None or (isinstance(val, float) and math.isnan(val))
    except Exception:
        return False


def indice_categoria(fig: go.Figure, x_val) -> Optional[float]:
    """Índice numérico de uma categoria no eixo X (para jitter em strip plots)."""
    if x_val is None:
        return None
    alvo = str(x_val)
    catarray = getattr(fig.layout.xaxis, "categoryarray", None)
    if catarray:
        cats = list(catarray)
        if alvo in cats:
            return float(cats.index(alvo))
    for tr in fig.data:
        xs = getattr(tr, "x", None)
        if xs is None:
            continue
        cats = list(dict.fromkeys(str(x) for x in xs))
        if alvo in cats:
            return float(cats.index(alvo))
    return 0.0


def hover_padrao(*, bgcolor: str, texto: str, borda: str, font_size: int = 13) -> dict:
    return dict(
        bgcolor=bgcolor,
        font_size=font_size,
        font_color=texto,
        bordercolor=borda,
        align="left",
    )
