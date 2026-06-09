"""Componentes reutilizáveis de UI."""

from __future__ import annotations

import html as html_mod

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.theme import AZUL_PRINCIPAL, COR_POSITIVO, TEMA
from viz.chart_layout import PLOTLY_HUB_CONFIG


def render_html(texto: str) -> None:
    st.markdown(texto.strip(), unsafe_allow_html=True)


def titulo_secao(texto: str, subtitulo: str = "") -> None:
    sub = (
        f'<p style="color:{TEMA["texto_secundario"]}; margin:4px 0 0 0; font-size:13px;">{subtitulo}</p>'
        if subtitulo
        else ""
    )
    st.markdown(
        f"""
        <div style="background-color:{TEMA['bg_subtle']}; padding:12px 20px; border-radius:8px; margin:16px 0 12px 0;">
            <h3 style="color:{AZUL_PRINCIPAL}; margin:0; font-size:18px;">{texto}</h3>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(titulo: str, valor: str, cor: str = AZUL_PRINCIPAL, subtitulo: str = "") -> None:
    st.markdown(
        f"""
        <div style="background-color:{TEMA['bg_principal']}; border:1px solid {TEMA['borda']};
                    border-radius:10px; padding:14px; text-align:center;">
            <p style="color:{TEMA['texto_secundario']}; font-size:11px; margin:0;
                      text-transform:uppercase; letter-spacing:1px;">{titulo}</p>
            <h2 style="color:{cor}; margin:5px 0; font-size:26px; font-weight:700;">{valor}</h2>
            <p style="color:{TEMA['texto_secundario']}; font-size:11px; margin:0;">{subtitulo}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fmt_int(n: float | int) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_float(n: float, casas: int = 1) -> str:
    try:
        return f"{float(n):.{casas}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(n: float, casas: int = 1) -> str:
    try:
        return f"{float(n):.{casas}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_delta(n: float, casas: int = 1) -> str:
    try:
        v = float(n)
        if pd.isna(v):
            return "—"
        sinal = "+" if v >= 0 else ""
        return f"{sinal}{v:.{casas}f} pts"
    except (TypeError, ValueError):
        return "—"


def classificar_tendencia(variacao: float) -> str:
    try:
        v = float(variacao)
        if pd.isna(v):
            return ""
        if v >= 3:
            return "positivo"
        if v <= -3:
            return "critico"
        return ""
    except (TypeError, ValueError):
        return ""


def classificar_posicao(pos: int | None, total: int) -> str:
    if not pos or not total:
        return ""
    pct = pos / total
    if pct <= 0.35:
        return "positivo"
    if pct >= 0.7:
        return "critico"
    return ""


def _kpi_html(rotulo: str, valor: str, sub: str = "", status: str = "", extra: str = "") -> str:
    cls = f"kpi-claro {status}".strip()
    if extra:
        cls = f"{cls} {extra}"
    return (
        f'<div class="{cls}">'
        f'<span class="kpi-claro-lbl">{html_mod.escape(rotulo)}</span>'
        f'<span class="kpi-claro-val">{html_mod.escape(valor)}</span>'
        f'<span class="kpi-claro-sub">{html_mod.escape(sub)}</span>'
        f"</div>"
    )


def _funil_kpi_html(diag: dict, periodo: str) -> str:
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    n_insc = diag.get("n_inscritos")
    tx_efet = diag.get("tx_part_efetiva")
    tx_insc = diag.get("tx_inscricao")
    if not n_conc or not n_pres:
        return _kpi_html(
            f"Participação · {periodo}",
            fmt_int(n_pres) if n_pres else "—",
            "participantes efetivos",
            extra="kpi-funil-inline",
        )

    pct_insc = min(100.0, float(tx_insc)) if tx_insc is not None else 0.0
    pct_efet = min(100.0, float(tx_efet)) if tx_efet is not None else 0.0

    def barra(pct: float, cor: str, label: str | None) -> str:
        w = max(min(pct, 100.0), 0.0)
        inner = f'<span class="fk-pct">{html_mod.escape(label)}</span>' if label and w >= 14 else ""
        outer = f'<span class="fk-pct-out">{html_mod.escape(label)}</span>' if label and w < 14 else ""
        return f'<span class="fk-track"><span class="fk-fill {cor}" style="width:{w:.0f}%">{inner}</span>{outer}</span>'

    def linha(lbl: str, val: str, pct: float, cor: str, label: str | None) -> str:
        return (
            f'<div class="fk-line"><span class="fk-l">{html_mod.escape(lbl)}</span>'
            f'<span class="fk-n">{val}</span>{barra(pct, cor, label)}</div>'
        )

    linhas = [linha("Concluintes", fmt_int(n_conc), 100.0, "azul", None)]
    if n_insc:
        linhas.append(
            linha(
                "Inscritos", fmt_int(n_insc), pct_insc, "laranja",
                fmt_pct(tx_insc) if tx_insc is not None else None,
            )
        )
    linhas.append(
        linha(
            "Participação efetiva", fmt_int(n_pres), pct_efet, "verde",
            fmt_pct(tx_efet) if tx_efet is not None else None,
        )
    )
    return (
        f'<div class="kpi-claro kpi-funil-inline">'
        f'<span class="kpi-claro-lbl">Participação · {html_mod.escape(periodo)}</span>'
        f'<div class="fk-lines">{"".join(linhas)}</div></div>'
    )


def render_cabecalho_kpis(diag: dict, periodo: str) -> None:
    status_var = classificar_tendencia(diag.get("variacao_inicio_fim", 0))
    pos = diag.get("pos_ms_recente") or diag.get("pos_ms")
    total = diag.get("total_ufs_recente") or diag.get("total_ufs") or 27
    ano_ref = diag.get("ano_referencia_pos") or diag.get("ano_fim")
    sub_var = (
        f"{diag.get('ano_inicio')} → {diag.get('ano_fim')}"
        if diag.get("ano_inicio") and diag.get("ano_fim")
        else periodo
    )
    diff = diag.get("diff_vs_nacional", float("nan"))
    status_diff = "positivo" if pd.notna(diff) and diff >= 0 else ("critico" if pd.notna(diff) else "")

    kpis = [
        _kpi_html("Média geral · rede estadual", fmt_float(diag["media_estadual_ms"]), f"Média ponderada · {periodo}"),
        _kpi_html(
            "Variação da média · rede estadual",
            fmt_delta(diag.get("variacao_inicio_fim", 0)),
            sub_var,
            status_var,
        ),
        _kpi_html(
            "Posição nacional · rede estadual",
            f"{pos}º de {total}" if pos else "—",
            f"{ano_ref} · ranking entre UFs" if ano_ref else f"Ranking entre UFs · {periodo}",
            classificar_posicao(pos, total),
        ),
        _kpi_html(
            "Diferença vs Brasil · rede estadual",
            fmt_delta(diff) if pd.notna(diff) else "—",
            f"Média ponderada · {periodo}",
            status_diff,
            extra="kpi-delta-br",
        ),
        _funil_kpi_html(diag, periodo),
    ]
    render_html(
        f'<div class="cab-claro cab-claro--com-kpis"><div class="cab-claro-row">'
        f'<div class="cab-claro-brand"><div class="cab-claro-text">'
        f"<h1>Painel ENEM MS</h1>"
        f"<p>Desempenho e participação da rede estadual · {html_mod.escape(periodo)}</p>"
        f"</div></div>"
        f'<div class="cab-claro-kpis">{"".join(kpis)}</div>'
        f"</div></div>"
    )


def render_populacao_referencia() -> None:
    render_html(
        '<div class="ref-pop-bar">'
        '<span class="ref-pop-tag">População de referência</span>'
        "<span class=\"ref-pop-item\">Presentes nos dois dias de prova; "
        "Concluintes do Ensino Médio na rede estadual</span>"
        '<span class="ref-pop-sep">·</span>'
        "<span class=\"ref-pop-item\"><strong>2019–2023</strong> concluintes do Ensino Médio · "
        "<strong>2024</strong> inscritos na rede estadual</span>"
        '<span class="ref-pop-sep">·</span>'
        "<span class=\"ref-pop-item\"><strong>Taxa de participação efetiva</strong> = presentes ÷ concluintes</span>"
        "</div>"
    )


def render_hub_widget(titulo: str, fig: go.Figure | None, legenda: str = "", *, chart_key: str) -> None:
    if fig is None or not fig.data:
        return
    render_html(
        f'<div class="widget-chart-zone"><div class="widget-head">{html_mod.escape(titulo)}</div>'
        f'<div class="widget-chart-body">'
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_HUB_CONFIG, key=chart_key)
    if legenda.strip():
        render_html(f'<div class="widget-chart-nota">{html_mod.escape(legenda)}</div>')
    render_html("</div></div>")


def linha_por_ano(df: pd.DataFrame, ano: int) -> pd.Series | None:
    if df.empty or "ano" not in df.columns:
        return None
    sub = df[df["ano"] == int(ano)]
    if sub.empty:
        sub = df[df["ano"].astype(str) == str(ano)]
    return sub.iloc[0] if not sub.empty else None


def valor_numerico(linha: pd.Series, *colunas: str, default: float = 0.0) -> float:
    for col in colunas:
        if col not in linha.index:
            continue
        val = linha[col]
        if pd.isna(val):
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return default


def coluna_existente(linha: pd.Series, *candidatos: str) -> str:
    for col in candidatos:
        if col in linha.index and pd.notna(linha[col]):
            return col
    return candidatos[0]


def nome_cre_curto(cre: str) -> str:
    if not cre or pd.isna(cre):
        return "—"
    texto = str(cre).strip()
    if texto.upper().startswith("CRE "):
        return texto[4:].strip()
    return texto
