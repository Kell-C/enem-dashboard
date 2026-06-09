"""Componentes de UI reutilizáveis — painel ENEM v15."""

from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import streamlit as st

from app.v15.theme import AREAS, AREAS_COMPLETO
from app.v15.ui import _render_html


def titulo_leve(titulo: str) -> None:
    t = _html.escape(str(titulo))
    _render_html(
        f'<div class="secao-head"><span class="secao-eyebrow">{t}</span></div>'
    )


def titulo_secao(titulo: str, subtitulo: str = ""):
    t = _html.escape(str(titulo))
    s = _html.escape(str(subtitulo)) if subtitulo else ""
    _render_html(
        f"<div class='bloco-titulo'><h3>{t}</h3>"
        f"{'<p>' + s + '</p>' if s else ''}</div>"
    )


def achado(tipo: str, titulo: str, texto: str):
    icones = {"positivo": "✓", "atencao": "⚠", "critico": "✗", "neutro": "ℹ"}
    tipos_validos = {"positivo", "atencao", "critico", "neutro"}
    tipo_seguro = tipo if tipo in tipos_validos else "neutro"
    icone = icones.get(tipo_seguro, "ℹ")
    t = _html.escape(str(titulo))
    x = _html.escape(str(texto))
    st.markdown(
        f"""<div class='achado achado-{tipo_seguro}'>
        <div class='titulo'>{icone} {t}</div>
        <div class='corpo'>{x}</div></div>""",
        unsafe_allow_html=True,
    )


def insight_box(texto: str):
    st.markdown(f"<div class='insight'>{texto}</div>", unsafe_allow_html=True)


def kpi_card(col, rotulo: str, valor: str, sub: str = "", status: str = ""):
    status_validos = {"positivo", "atencao", "critico", ""}
    status_seguro = status if status in status_validos else ""
    classe = f"kpi-card {status_seguro}" if status_seguro else "kpi-card"
    r = _html.escape(str(rotulo))
    v = _html.escape(str(valor))
    s = _html.escape(str(sub))
    col.markdown(
        f"""<div class='{classe}'>
          <div class='rotulo'>{r}</div>
          <div class='valor'>{v}</div>
          <div class='sub'>{s}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def nome_area(col: str) -> str:
    return AREAS.get(col, col)


def nome_area_ext(col: str) -> str:
    return AREAS_COMPLETO.get(col, col)


def estatisticas_dict(series: pd.Series) -> dict:
    s = series.dropna()
    if s.empty:
        return dict(Estudantes=0, Média=np.nan, Mediana=np.nan)
    return dict(
        Estudantes=int(len(s)),
        Média=round(float(s.mean()), 2),
        Mediana=round(float(s.median()), 2),
    )
