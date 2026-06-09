"""Helpers de UI HTML — painel v15."""

import base64
import os

import streamlit as st

from app.v15.paths import LOGO_MS_CANDIDATES


def render_html(html: str) -> None:
    st.markdown(html.strip(), unsafe_allow_html=True)


def logo_data_uri() -> str:
    for path in LOGO_MS_CANDIDATES:
        p = str(path)
        if not os.path.isfile(p):
            continue
        mime = "image/svg+xml" if p.lower().endswith(".svg") else "image/png"
        with open(p, "rb") as f:
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    return ""

# Aliases legados
_render_html = render_html
_logo_data_uri = logo_data_uri


from app.v15.theme import TEMA

def _legenda_inline(itens_html, *, margem: str = "10px 0 16px") -> str:
    """Componente único de legenda inline (chips horizontais).

    ``itens_html`` é uma lista de trechos HTML (marcador + texto). Cada item é
    renderizado como um chip flex, com espaçamento e cor padronizados — evita as
    múltiplas ``<div>`` ad-hoc espalhadas pela aba.
    """
    corpo = "".join(
        "<span style='display:inline-flex;align-items:center;gap:6px;"
        f"white-space:nowrap;'>{it}</span>"
        for it in itens_html
    )
    return (
        f"<div style='display:flex;gap:18px;margin:{margem};font-size:13px;"
        f"flex-wrap:wrap;align-items:center;color:{TEMA['texto_secundario']};'>"
        f"{corpo}</div>"
    )
