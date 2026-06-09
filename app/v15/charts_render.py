"""Renderização Plotly no Streamlit — painel ENEM v15."""

from __future__ import annotations

import streamlit as st

from app.v15.boxplots import _preparar_hover_fig
from app.v15.constants import HUB_BUILD_ID
from viz.chart_layout import PLOTLY_HUB_CONFIG

_CK = [0]


def _chart(fig, **kw):
    _CK[0] += 1
    _preparar_hover_fig(fig)
    st.plotly_chart(
        fig, key=f"_c{_CK[0]}", width="stretch", theme=None, on_select="ignore", **kw,
    )


def _chart_hub(fig, **kw) -> None:
    """Render hub com widget Plotly nativo (leve; evita travar o navegador)."""
    _CK[0] += 1
    cfg = dict(PLOTLY_HUB_CONFIG)
    if kw.get("config"):
        cfg.update(kw.pop("config"))
    fig.update_layout(uirevision=f"hub-{HUB_BUILD_ID}")
    _preparar_hover_fig(fig)
    st.plotly_chart(
        fig,
        key=f"hub_{HUB_BUILD_ID}_{_CK[0]}",
        width="stretch",
        theme=None,
        config=cfg,
        on_select="ignore",
        **kw,
    )
