"""Tema Plotly e helpers de cor/legenda — painel ENEM v15."""

from __future__ import annotations

from viz.chart_layout import (
    CHART_H_STANDARD,
    hover_padrao,
    margem_detalhe,
    margem_hub,
)

from app.v15.theme import (
    AZUL_PRINCIPAL,
    FONT_AXIS,
    FONT_CHART,
    FONT_HOVER,
    FONT_LEGEND,
    TEMA,
)


def _legenda_padrao(y_pos: float = 1.02, font_size: int = FONT_LEGEND, entry_width: int = 150):
    """Retorna dict de legenda padronizado para evitar sobreposição."""
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


def aplicar_tema(
    fig,
    altura: int = CHART_H_STANDARD,
    *,
    limpar_titulo: bool = False,
    modo_hub: bool = False,
):
    """Aplica identidade visual institucional aos gráficos Plotly."""
    titulo_atual = ""
    if fig.layout.title and fig.layout.title.text:
        titulo_atual = str(fig.layout.title.text)

    layout_kw: dict = dict(
        template=TEMA["plot_template"],
        height=altura,
        margin=margem_hub() if modo_hub else margem_detalhe(),
        font=dict(
            family="Source Sans 3, system-ui, sans-serif",
            size=FONT_CHART,
            color=TEMA["texto"],
        ),
        title_font=dict(
            family="Plus Jakarta Sans, sans-serif",
            size=15,
            color=AZUL_PRINCIPAL,
        ),
        hoverlabel=hover_padrao(
            bgcolor=TEMA["bg_card"],
            texto=TEMA["texto"],
            borda=TEMA["borda"],
            font_size=FONT_HOVER,
        ),
        paper_bgcolor=TEMA["plot_paper"],
        plot_bgcolor=TEMA["plot_plot"],
        hovermode="closest",
        bargap=0.22,
        bargroupgap=0.06,
    )
    if modo_hub:
        layout_kw["showlegend"] = False
    else:
        layout_kw["legend"] = _legenda_padrao(y_pos=-0.28, font_size=FONT_LEGEND)
    if limpar_titulo:
        layout_kw["title"] = dict(text="")
    elif titulo_atual:
        layout_kw["title"] = dict(text=titulo_atual)
    fig.update_layout(**layout_kw)
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor=TEMA["linha_eixo"],
        linewidth=1,
        ticks="outside",
        tickcolor=TEMA["linha_eixo"],
        ticklen=4,
        tickfont=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
        title_font=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
    )
    y_kw = dict(
        showgrid=False,
        gridcolor=TEMA["grid_sutil"],
        gridwidth=1,
        zeroline=False,
        showline=False,
        title_font=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
    )
    if modo_hub:
        y_kw.update(showticklabels=False, ticks="", ticklen=0)
    else:
        y_kw.update(
            ticks="outside",
            tickcolor=TEMA["linha_eixo"],
            ticklen=4,
            tickfont=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
        )
    fig.update_yaxes(**y_kw)
    return fig


def _hex_rgba(hex_color: str, alpha: float) -> str:
    """Converte cor hex para rgba, lidando com nomes de cores Plotly."""
    if isinstance(hex_color, str) and hex_color.startswith("rgb("):
        vals = hex_color.strip("rgb()").split(",")
        r, g, b = int(vals[0]), int(vals[1]), int(vals[2])
        return f"rgba({r},{g},{b},{alpha})"
    if isinstance(hex_color, str) and not hex_color.startswith("#"):
        nome_para_hex = {
            "red": "#FF0000",
            "green": "#008000",
            "blue": "#0000FF",
            "orange": "#FFA500",
            "purple": "#800080",
            "brown": "#A52A2A",
            "pink": "#FFC0CB",
            "gray": "#808080",
            "grey": "#808080",
            "black": "#000000",
            "white": "#FFFFFF",
            "yellow": "#FFFF00",
            "cyan": "#00FFFF",
            "magenta": "#FF00FF",
            "lime": "#00FF00",
            "navy": "#000080",
            "teal": "#008080",
            "olive": "#808000",
            "maroon": "#800000",
            "silver": "#C0C0C0",
            "coral": "#FF7F50",
        }
        hex_color = nome_para_hex.get(hex_color.lower(), "#999999")
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    if len(h) != 6:
        return f"rgba(153,153,153,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
