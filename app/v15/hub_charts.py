"""Eixos hub, legendas e fechamento de figuras hub — painel ENEM v15."""

from __future__ import annotations

import html as _html

import pandas as pd
import plotly.graph_objects as go

from viz.chart_layout import CHART_H_HUB

from app.v15.theme import (  # noqa: F401
    AREAS,
    AZUL_PRINCIPAL,
    COLS_NOTAS,
    CORES_AREAS,
    CORES_DEP,
    COR_ATENCAO,
    COR_BAR_NEUTRA,
    COR_BRASIL,
    COR_CRITICO,
    COR_POSITIVO,
    FONT_HUB_AXIS,
    FONT_HUB_LEGEND,
    FONT_HUB_LEGEND_WIDE,
    HUB_CHART_MARGIN,
    LARANJA_DESTAQUE,
    TEMA,
)


def _cor_posicao_terco(pos: int, n_total: int) -> str:
    terco = n_total / 3 if n_total else 9
    if pos <= terco:
        return COR_POSITIVO
    if pos <= 2 * terco:
        return COR_ATENCAO
    return COR_CRITICO


def _aplicar_eixos_hub(
    fig,
    *,
    secondary_y: bool = False,
    y_categorico: bool = False,
    manter_linha_x: bool = False,
) -> None:
    """Eixos compactos hub: X com anos; Y sem escala numérica (só categorias em rankings)."""
    fig.update_xaxes(
        showgrid=False, zeroline=False,
        showline=manter_linha_x,
        linecolor=TEMA["borda"] if manter_linha_x else None,
        linewidth=1 if manter_linha_x else 0,
        title_text="",
        tickfont=dict(size=FONT_HUB_AXIS, color=TEMA["texto_secundario"]),
    )
    y_opts: dict = dict(
        showgrid=False, zeroline=False,
        showline=False, title_text="",
        showticklabels=y_categorico,
        ticks="" if not y_categorico else "outside",
        ticklen=0 if not y_categorico else 4,
    )
    if y_categorico:
        y_opts["tickfont"] = dict(size=FONT_HUB_AXIS, color=TEMA["texto_secundario"])
    tem_y2 = getattr(fig.layout, "yaxis2", None) is not None
    if tem_y2:
        fig.update_yaxes(**y_opts, secondary_y=False)
        if secondary_y:
            y_sec = {**y_opts, "showticklabels": False, "ticks": "", "ticklen": 0}
            fig.update_yaxes(**y_sec, secondary_y=True)
    else:
        fig.update_yaxes(**y_opts)


def _texto_posicao_barra(valores: list) -> tuple[list[str], list[str]]:
    """Texto e posição dos rótulos de barra (%): dentro se couber, senão fora."""
    textos, posicoes = [], []
    for v in valores:
        if pd.isna(v):
            textos.append("")
            posicoes.append("none")
        elif float(v) >= 10:
            textos.append(f"{float(v):.0f}%")
            posicoes.append("inside")
        else:
            textos.append(f"{float(v):.0f}%")
            posicoes.append("outside")
    return textos, posicoes


def _altura_hub_ranking(n_itens: int) -> int:
    """Altura hub CRE: cresce com o nº de barras para rótulos legíveis."""
    n = max(1, int(n_itens))
    return int(max(CHART_H_HUB, min(400, 22 * n + 72)))


def _contar_itens_legenda(fig: go.Figure) -> int:
    """Traces visíveis na legenda Plotly."""
    return sum(
        1 for tr in fig.data
        if getattr(tr, "showlegend", None) is not False
        and getattr(tr, "name", None)
    )


def _y_nota_legenda_hub(n_leg: int) -> float:
    """Posição vertical (paper) da nota explicativa, abaixo da legenda Plotly."""
    if n_leg >= 7:
        return -0.38
    if n_leg >= 5:
        return -0.34
    if n_leg >= 3:
        return -0.30
    if n_leg >= 1:
        return -0.26
    return -0.08


def _anotar_nota_legenda_hub(fig: go.Figure, nota: str) -> None:
    """Inclui nota explicativa dentro da área branca do gráfico, abaixo da legenda."""
    if not nota:
        return
    n_leg = _contar_itens_legenda(fig)
    texto = nota.replace("<strong>", "<b>").replace("</strong>", "</b>")
    fig.add_annotation(
        text=texto,
        xref="paper",
        yref="paper",
        x=0.5,
        y=_y_nota_legenda_hub(n_leg),
        xanchor="center",
        yanchor="top",
        showarrow=False,
        font=dict(
            size=10,
            color=TEMA["texto_secundario"],
            family="Source Sans 3, sans-serif",
        ),
        align="center",
    )
    m = fig.layout.margin
    t = getattr(m, "t", None) or HUB_CHART_MARGIN["t"]
    l = getattr(m, "l", None) or HUB_CHART_MARGIN["l"]
    r = getattr(m, "r", None) or HUB_CHART_MARGIN["r"]
    b = getattr(m, "b", None) or HUB_CHART_MARGIN["b"]
    fig.update_layout(margin=dict(t=t, l=l, r=r, b=int(b) + (24 if n_leg else 20)))


def _classificar_cor_media_referencia(valor, media_ms, media_br) -> str:
    """Classifica cor da barra vs referências estaduais (MS/BR).

    Verde: média ≥ BR estadual · Azul: ≥ MS e < BR · Vermelho: < MS.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return COR_BAR_NEUTRA
    v = float(valor)
    br = float(media_br) if media_br is not None and pd.notna(media_br) else np.nan
    ms = float(media_ms) if media_ms is not None and pd.notna(media_ms) else np.nan
    if pd.notna(br) and v >= br:
        return COR_POSITIVO
    if pd.notna(ms) and v >= ms:
        return AZUL_PRINCIPAL
    return COR_CRITICO


def _html_legenda_cores_ms_br() -> str:
    """Legenda HTML das cores vs médias MS e BR."""
    return (
        f'<span class="leg-trace"><span style="color:{COR_POSITIVO};font-weight:700;">■</span>'
        f' ≥ média BR</span>'
        f'<span class="leg-trace"><span style="color:{AZUL_PRINCIPAL};font-weight:700;">■</span>'
        f' ≥ média MS</span>'
        f'<span class="leg-trace"><span style="color:{COR_CRITICO};font-weight:700;">■</span>'
        f' abaixo da média MS</span>'
    )


def _html_legenda_refs_vline() -> str:
    """Legenda HTML das linhas de referência MS/BR."""
    return (
        f'<span class="leg-trace"><span style="color:{LARANJA_DESTAQUE};font-weight:700;">- -</span>'
        f' Média MS</span>'
        f'<span class="leg-trace"><span style="color:{COR_BRASIL};font-weight:700;">···</span>'
        f' Média BR</span>'
    )


def _html_legenda_deps(deps: list[str]) -> str:
    """Legenda HTML das dependências administrativas."""
    spans = [
        f'<span class="leg-trace"><span style="color:{CORES_DEP.get(d, AZUL_PRINCIPAL)};'
        f'font-weight:700;">■</span> {_html.escape(d)}</span>'
        for d in deps
    ]
    return "".join(spans)


def _html_legenda_traces(fig: go.Figure) -> str:
    """Legenda HTML compacta a partir das traces nomeadas do gráfico."""
    itens = []
    for tr in fig.data:
        nome = getattr(tr, "name", None)
        if not nome:
            continue
        cor = None
        if getattr(tr, "line", None) and tr.line.color:
            cor = tr.line.color
        elif getattr(tr, "marker", None) and tr.marker.color:
            c = tr.marker.color
            cor = c[0] if isinstance(c, (list, tuple)) and c else c
        tr_type = getattr(tr, "type", "") or ""
        if tr_type == "scatter":
            sym = "━"
            line = getattr(tr, "line", None)
            if line is not None:
                dash = getattr(line, "dash", None)
                if dash is None and hasattr(line, "to_plotly_json"):
                    dash = line.to_plotly_json().get("dash")
                if dash and str(dash) not in ("solid", "none", ""):
                    sym = "···"
        elif tr_type == "box":
            sym = "▬"
        else:
            sym = "■"
        itens.append(
            f'<span class="leg-trace"><span style="color:{cor or TEMA["texto"]};'
            f'font-weight:700;">{sym}</span> {_html.escape(str(nome))}</span>'
        )
    if not itens:
        return ""
    return f'<div class="leg-traces">{"".join(itens)}</div>'


def _legenda_hub(*, n_items: int = 2) -> dict:
    """Legenda hub compacta acima da área do gráfico."""
    fs = FONT_HUB_LEGEND_WIDE if n_items >= 5 else FONT_HUB_LEGEND
    return dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        x=0.5,
        xanchor="center",
        font=dict(size=fs, color=TEMA["texto"]),
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=TEMA["borda"],
        borderwidth=0,
        tracegroupgap=4 if n_items >= 5 else 6,
    )


def _legenda_hub_baixo_eixo(*, n_items: int = 2, y: float = 0.12) -> dict:
    """Legenda horizontal na faixa inferior reservada do gráfico (paper y)."""
    fs = FONT_HUB_LEGEND_WIDE if n_items >= 5 else FONT_HUB_LEGEND
    ew = max(36, min(92, 56 - n_items * 2)) if n_items >= 5 else min(92, 48 + n_items * 10)
    return dict(
        orientation="h",
        yanchor="middle",
        y=y,
        x=0.5,
        xanchor="center",
        entrywidth=ew,
        entrywidthmode="pixels",
        tracegroupgap=4 if n_items >= 5 else 10,
        itemsizing="constant",
        font=dict(size=fs, color=TEMA["texto"]),
        bgcolor="rgba(255,255,255,0)",
        borderwidth=0,
    )


def _frac_rodape_legenda(
    n_linhas: int,
    *,
    rank: bool = False,
    topo: bool = False,
    com_areas: bool = False,
) -> float:
    """Fração inferior da figura reservada a legendas/notas (paper, 0–1)."""
    if n_linhas <= 0:
        return 0.0
    if com_areas:
        n_linhas += 1
    if rank:
        return min(0.26, 0.09 + n_linhas * 0.032)
    if topo:
        return min(0.38, 0.17 + n_linhas * 0.042)
    return min(0.36, 0.14 + n_linhas * 0.040)


def _y_rodape_paper(footer_frac: float, idx: int, n: int) -> float:
    """Posição vertical de uma linha do rodapé (paper; 0=base da figura)."""
    pad = 0.03
    faixa = max(footer_frac - pad, 0.08)
    step = faixa / max(n, 1)
    return pad + step * idx + step * 0.5


def _reservar_rodape_plotly(fig: go.Figure, footer_frac: float) -> None:
    """Encolhe domínio vertical (yaxis) para abrir faixa inferior à legenda."""
    if footer_frac <= 0:
        return
    scale = 1.0 - footer_frac
    layout_dict = fig.to_dict().get("layout", {})
    atualizou_y = False
    for key, val in layout_dict.items():
        if not key.startswith("yaxis"):
            continue
        dom = val.get("domain")
        if dom is None:
            continue
        d0, d1 = dom
        fig.update_layout(**{
            key: dict(domain=[footer_frac + scale * d0, footer_frac + scale * d1]),
        })
        atualizou_y = True
    if not atualizou_y:
        domain = [footer_frac, 1.0]
        fig.update_yaxes(domain=domain)
        if getattr(fig.layout, "yaxis2", None) is not None:
            fig.update_yaxes(domain=domain, secondary_y=True)


def _cores_ranking_presentes(
    valores: list,
    media_ms: float | None,
    media_br: float | None,
) -> set[str]:
    """Cores efetivamente usadas nas barras do ranking."""
    return {
        _classificar_cor_media_referencia(v, media_ms, media_br)
        for v in valores
        if pd.notna(v)
    }


def _anotar_legenda_cores_ms_br_plotly(
    fig: go.Figure,
    *,
    y: float,
    cores_usadas: set[str] | None = None,
) -> None:
    """Legenda de cores MS/BR — só categorias presentes nos dados."""
    partes: list[str] = []
    if cores_usadas is None or COR_POSITIVO in cores_usadas:
        partes.append(
            f'<span style="color:{COR_POSITIVO};font-size:10px;">&#9632;</span> ≥ média BR'
        )
    if cores_usadas is None or AZUL_PRINCIPAL in cores_usadas:
        partes.append(
            f'<span style="color:{AZUL_PRINCIPAL};font-size:10px;">&#9632;</span> ≥ média MS'
        )
    if cores_usadas is None or COR_CRITICO in cores_usadas:
        partes.append(
            f'<span style="color:{COR_CRITICO};font-size:10px;">&#9632;</span> abaixo MS'
        )
    if not partes:
        return
    fig.add_annotation(
        text="&nbsp;&nbsp;".join(partes),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_legenda_cores_delta_br_plotly(fig: go.Figure, *, y: float) -> None:
    """Legenda verde/vermelho — diferença vs Brasil por área."""
    fig.add_annotation(
        text=(
            f'<span style="color:{COR_POSITIVO};font-size:11px;">&#9632;</span> acima do Brasil'
            f'&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{COR_CRITICO};font-size:11px;">&#9632;</span> abaixo do Brasil'
        ),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_legenda_refs_vline_plotly(fig: go.Figure, *, y: float) -> None:
    """Legenda das linhas de referência MS (tracejada) e BR (pontilhada)."""
    fig.add_annotation(
        text=(
            f'<span style="color:{LARANJA_DESTAQUE};font-weight:700;">- -</span> Média MS'
            f'&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{COR_BRASIL};font-weight:700;">···</span> Média BR'
        ),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_legenda_ranking_cre_plotly(
    fig: go.Figure,
    *,
    y: float,
    cores_usadas: set[str] | None = None,
    nota: str = "",
) -> None:
    """Rodapé compacto CRE: cores + linhas de referência (+ nota opcional)."""
    blocos: list[str] = []
    cores_txt: list[str] = []
    if cores_usadas is None or COR_POSITIVO in cores_usadas:
        cores_txt.append(
            f'<span style="color:{COR_POSITIVO};font-size:10px;">&#9632;</span> ≥ BR'
        )
    if cores_usadas is None or AZUL_PRINCIPAL in cores_usadas:
        cores_txt.append(
            f'<span style="color:{AZUL_PRINCIPAL};font-size:10px;">&#9632;</span> ≥ MS'
        )
    if cores_usadas is None or COR_CRITICO in cores_usadas:
        cores_txt.append(
            f'<span style="color:{COR_CRITICO};font-size:10px;">&#9632;</span> &lt; MS'
        )
    if cores_txt:
        blocos.append("&nbsp;".join(cores_txt))
    blocos.append(
        f'<span style="color:{LARANJA_DESTAQUE};font-weight:700;">- -</span> MS'
        f'&nbsp;&nbsp;'
        f'<span style="color:{COR_BRASIL};font-weight:700;">···</span> BR'
    )
    if nota:
        blocos.append(
            f'<span style="font-size:8px;color:{TEMA["texto_muted"]};">{nota}</span>'
        )
    fig.add_annotation(
        text="&nbsp;&nbsp;|&nbsp;&nbsp;".join(blocos),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_legenda_traces_plotly(fig: go.Figure, *, y: float) -> None:
    """Legenda das séries (linha/barra) na faixa inferior — sem legend Plotly."""
    partes: list[str] = []
    for tr in fig.data:
        nome = getattr(tr, "name", None)
        if not nome:
            continue
        cor = None
        if getattr(tr, "line", None) and tr.line.color:
            cor = tr.line.color
        elif getattr(tr, "marker", None) and tr.marker.color:
            c = tr.marker.color
            cor = c[0] if isinstance(c, (list, tuple)) and c else c
        tr_type = getattr(tr, "type", "") or ""
        if tr_type == "scatter":
            sym = "●"
        elif tr_type == "box":
            sym = "▬"
        else:
            sym = "■"
        rotulo = str(nome)
        if "participação" in rotulo.lower():
            rotulo = "Participação"
        elif "média" in rotulo.lower():
            rotulo = "Média"
        partes.append(
            f'<span style="white-space:nowrap;">'
            f'<span style="color:{cor or TEMA["texto"]};font-size:12px;">{sym}</span>'
            f'&nbsp;{rotulo}</span>'
        )
    if not partes:
        return
    fig.add_annotation(
        text="&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join(partes),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_legenda_areas_plotly(fig: go.Figure, *, y: float) -> None:
    """Legenda das áreas de conhecimento (cores das linhas/barras)."""
    metade = (len(COLS_NOTAS) + 1) // 2
    linhas_txt = []
    for grupo in (COLS_NOTAS[:metade], COLS_NOTAS[metade:]):
        if not grupo:
            continue
        partes = [
            f'<span style="color:{CORES_AREAS[col]};font-size:10px;">&#9632;</span> {AREAS.get(col, col)}'
            for col in grupo
        ]
        linhas_txt.append("&nbsp;&nbsp;".join(partes))
    fig.add_annotation(
        text="<br>".join(linhas_txt),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=8, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_legenda_deps_plotly(fig: go.Figure, deps: list[str], *, y: float) -> None:
    """Legenda das dependências administrativas (cores das barras)."""
    partes = [
        f'<span style="color:{CORES_DEP.get(d, AZUL_PRINCIPAL)};font-size:11px;">&#9632;</span> {d}'
        for d in deps
    ]
    fig.add_annotation(
        text="&nbsp;&nbsp;&nbsp;".join(partes),
        xref="paper",
        yref="paper",
        x=0.5,
        y=y,
        xanchor="center",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color=TEMA["texto_secundario"], family="Source Sans 3, sans-serif"),
    )


def _anotar_notas_plotly(fig: go.Figure, notas: list[str], *, ys: list[float]) -> None:
    """Notas explicativas horizontais na faixa reservada do rodapé."""
    for nota, y in zip(notas, ys):
        fig.add_annotation(
            text=nota,
            xref="paper",
            yref="paper",
            x=0.5,
            y=y,
            xanchor="center",
            yanchor="bottom",
            showarrow=False,
            font=dict(
                size=9,
                color=TEMA["texto_secundario"],
                family="Source Sans 3, sans-serif",
            ),
        )


def _html_legenda_areas() -> str:
    """Legenda HTML das áreas de conhecimento (2 linhas, legível)."""
    rotulos = {
        "NU_NOTA_CN": "CN · Natureza",
        "NU_NOTA_CH": "CH · Humanas",
        "NU_NOTA_LC": "LC · Linguagens",
        "NU_NOTA_MT": "MT · Matemática",
        "NU_NOTA_REDACAO": "Redação",
    }
    itens = [
        f'<span class="leg-trace"><span style="color:{CORES_AREAS[col]};font-weight:700;">■</span>'
        f' {rotulos.get(col, AREAS.get(col, col))}</span>'
        for col in COLS_NOTAS
    ]
    return f'<div class="leg-traces">{"".join(itens)}</div>'


def _montar_legenda_hub_html(
    fig: go.Figure | None = None,
    *,
    legenda_traces: bool = False,
    legenda_areas: bool = False,
    cores_delta_br: bool = False,
    refs_vline: bool = False,
    legenda_deps: list[str] | None = None,
    notas: list[str] | None = None,
) -> str:
    """Legenda HTML abaixo do gráfico (mesmo padrão do combo rede estadual)."""
    blocos: list[str] = []
    if legenda_traces and fig is not None:
        tr = _html_legenda_traces(fig)
        if tr:
            blocos.append(tr)
    if legenda_areas:
        blocos.append(_html_legenda_areas())
    if cores_delta_br:
        blocos.append(
            f'<div class="leg-traces">'
            f'<span class="leg-trace"><span style="color:{COR_POSITIVO};font-weight:700;">■</span> acima do Brasil</span>'
            f'<span class="leg-trace"><span style="color:{COR_CRITICO};font-weight:700;">■</span> abaixo do Brasil</span>'
            f'</div>'
        )
    if refs_vline:
        blocos.append(_html_legenda_refs_vline())
    if legenda_deps:
        blocos.append(_html_legenda_deps(legenda_deps))
    for nota in (notas or []):
        if nota:
            blocos.append(f'<div class="leg-nota">{_html.escape(nota)}</div>')
    if not blocos:
        return ""
    return f'<div class="hub-legenda-linha">{"".join(blocos)}</div>'


def _aplicar_legenda_interna_hub(
    fig: go.Figure,
    *,
    notas: list[str] | None = None,
    cores_ms_br: bool = False,
    cores_delta_br: bool = False,
    refs_vline_ms_br: bool = False,
    legenda_deps: list[str] | None = None,
    legenda_areas: bool = False,
    legenda_traces: bool = True,
    tem_topo: bool = False,
    rank: bool = False,
    rank_compacto: bool = False,
    cores_ranking: set[str] | None = None,
    legenda_externa: bool = True,
) -> None:
    """Legenda hub: HTML abaixo do gráfico (padrão) ou anotações Plotly (legado)."""
    notas = [n for n in (notas or []) if n]
    if legenda_externa:
        fig._hub_legenda = _montar_legenda_hub_html(
            fig,
            legenda_traces=legenda_traces,
            legenda_areas=legenda_areas,
            cores_delta_br=cores_delta_br,
            refs_vline=refs_vline_ms_br,
            legenda_deps=legenda_deps,
            notas=notas,
        )
        fig.update_layout(showlegend=False)
        m = fig.layout.margin
        t = max(int(getattr(m, "t", 0) or 0), 8 if rank else 24)
        l = max(int(getattr(m, "l", 0) or 0), 78 if rank else 44)
        b = max(int(getattr(m, "b", 0) or 0), 24)
        r = int(getattr(m, "r", None) or 10)
        fig.update_layout(margin=dict(t=t, l=l, r=r, b=b))
        return

    n_traces = _contar_itens_legenda(fig) if legenda_traces else 0

    linhas: list[tuple[str, object]] = []
    if legenda_traces and n_traces > 0:
        linhas.append(("traces", n_traces))
    if rank_compacto and (cores_ms_br or refs_vline_ms_br):
        linhas.append((
            "rank_compact",
            {"cores": cores_ranking, "nota": notas[0] if notas else ""},
        ))
        notas = notas[1:] if notas else []
    else:
        if cores_ms_br:
            linhas.append(("cores_ms_br", cores_ranking))
        if cores_delta_br:
            linhas.append(("cores_delta_br", None))
        if refs_vline_ms_br:
            linhas.append(("refs_vline", None))
    if legenda_deps:
        linhas.append(("deps", legenda_deps))
    if legenda_areas:
        linhas.append(("areas", None))
    for nota in notas:
        linhas.append(("nota", nota))

    n_linhas = len(linhas)
    footer = _frac_rodape_legenda(
        n_linhas, rank=rank, topo=tem_topo, com_areas=legenda_areas,
    )
    _reservar_rodape_plotly(fig, footer)

    if not linhas:
        fig.update_layout(showlegend=False)
    else:
        idx = 0
        for kind, payload in linhas:
            y = _y_rodape_paper(footer, idx, n_linhas)
            if kind == "traces":
                for tr in fig.data:
                    if getattr(tr, "name", None):
                        tr.showlegend = False
                _anotar_legenda_traces_plotly(fig, y=y)
            elif kind == "rank_compact":
                payload = payload or {}
                _anotar_legenda_ranking_cre_plotly(
                    fig,
                    y=y,
                    cores_usadas=payload.get("cores"),
                    nota=str(payload.get("nota") or ""),
                )
            elif kind == "cores_ms_br":
                _anotar_legenda_cores_ms_br_plotly(fig, y=y, cores_usadas=payload)
            elif kind == "cores_delta_br":
                _anotar_legenda_cores_delta_br_plotly(fig, y=y)
            elif kind == "refs_vline":
                _anotar_legenda_refs_vline_plotly(fig, y=y)
            elif kind == "deps":
                _anotar_legenda_deps_plotly(fig, payload, y=y)
            elif kind == "areas":
                _anotar_legenda_areas_plotly(fig, y=y)
            elif kind == "nota":
                _anotar_notas_plotly(fig, [str(payload)], ys=[y])
            idx += 1

    if not (legenda_traces and n_traces > 0):
        fig.update_layout(showlegend=False)

    b = max(36, int(footer * 72) + 14) if rank else max(48, int(footer * 120) + 24)
    if rank:
        t, l, r = 8, 78, 10
    elif tem_topo:
        t, l, r = 42, 48, 12
    else:
        t, l, r = 28, 44, 12

    m = fig.layout.margin
    fig.update_layout(margin=dict(
        t=max(int(getattr(m, "t", 0) or 0), t),
        b=max(int(getattr(m, "b", 0) or 0), b),
        l=max(int(getattr(m, "l", 0) or 0), l),
        r=int(getattr(m, "r", None) or r),
    ))


def _aplicar_legenda_interna_combo_ms(
    fig: go.Figure,
    *,
    tem_delta: bool = False,
) -> None:
    """Atalho: combo média/participação MS."""
    _aplicar_legenda_interna_hub(
        fig,
        notas=["Δ = diferença em pontos vs Brasil"],
        cores_ms_br=True,
        tem_topo=tem_delta,
    )


def _margem_hub(
    *,
    rank: bool = False,
    n_legend: int = 0,
    topo: bool = False,
    nota: bool = False,
) -> dict:
    """Margem do gráfico hub; legenda HTML fica fora do Plotly."""
    if rank:
        return dict(t=12, b=32, r=14, l=72)
    t = 36 if (topo or n_legend >= 3) else (28 if n_legend else 18)
    b = 36 if nota else 28
    return dict(t=t, b=b, r=12, l=44)


def _nota_hub(
    *,
    traces: str = "",
    cores_ms_br: bool = False,
    refs_vline: bool = False,
    deps: list[str] | None = None,
    texto: str = "",
) -> str:
    """Monta nota HTML abaixo do gráfico (legendas + explicação)."""
    partes = []
    if traces:
        partes.append(traces)
    if cores_ms_br:
        partes.append(f'<div class="leg-traces">{_html_legenda_cores_ms_br()}</div>')
    if refs_vline:
        partes.append(f'<div class="leg-traces">{_html_legenda_refs_vline()}</div>')
    if deps:
        partes.append(f'<div class="leg-traces">{_html_legenda_deps(deps)}</div>')
    if texto:
        partes.append(f'<div class="leg-nota">{_html.escape(texto)}</div>')
    return "".join(partes)


def _legenda_fig(
    fig,
    *,
    cores_ms_br: bool = False,
    refs_vline: bool = False,
    deps: list[str] | None = None,
    texto: str = "",
) -> str:
    """Legenda HTML para footnote do widget hub."""
    if fig is None:
        return ""
    return _nota_hub(
        traces=_html_legenda_traces(fig),
        cores_ms_br=cores_ms_br,
        refs_vline=refs_vline,
        deps=deps,
        texto=texto,
    )


def _fechar_fig_hub(
    fig: go.Figure,
    *,
    rank: bool = False,
    topo: bool = False,
    notas: list[str] | None = None,
    cores_ms_br: bool = False,
    refs_vline: bool = False,
    legenda_traces: bool = True,
    legenda_areas: bool = False,
    cores_delta_br: bool = False,
    deps: list[str] | None = None,
    rank_compacto: bool = False,
    cores_ranking: set[str] | None = None,
    legenda_externa: bool = True,
) -> go.Figure:
    """Fecha figura hub com legenda HTML abaixo do plot e eixo Y sem escala."""
    _aplicar_legenda_interna_hub(
        fig,
        notas=notas,
        cores_ms_br=cores_ms_br,
        cores_delta_br=cores_delta_br,
        refs_vline_ms_br=refs_vline,
        legenda_deps=deps,
        legenda_areas=legenda_areas,
        legenda_traces=legenda_traces,
        tem_topo=topo,
        rank=rank,
        rank_compacto=rank_compacto,
        cores_ranking=cores_ranking,
        legenda_externa=legenda_externa,
    )
    return fig
