"""Gráficos das abas detalhe — painel ENEM v15."""

from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from viz.chart_layout import (
    CHART_H_BOX_WIDE,
    CHART_H_EVOLUCAO,
    CHART_H_HIST,
    CHART_H_HIST_GRID,
    CHART_H_HIST_ROW,
    CHART_H_PARTICIPACAO,
    CHART_H_RANKING,
    CHART_H_STANDARD,
)

from app.v15.boxplots import (
    _add_box_series,
    _finalizar_boxplot,
    _finalizar_grafico,
)
from app.v15.formatting import fmt_delta, fmt_float, fmt_int, fmt_pct
from app.v15.hub_charts import _classificar_cor_media_referencia
from app.v15.plotly_theme import aplicar_tema
from app.v15.theme import *
from dados_agregados_loader import (
    media_nacional_ponderada,
    medias_br_serie_por_area,
    medias_referencia_por_ano,
    stats_box_quantis,
)


def range_dinamico(*series, padding: float = 0.05,
                   lo_min: float = 0, hi_max: float = 1000,
                   referencias=()) -> list:
    """Calcula um range visualmente útil para eixos de notas.

    Considera todos os valores das séries e referências fornecidas,
    aplicando uma margem de `padding` (proporcional à amplitude)
    e respeitando os limites absolutos [lo_min, hi_max].
    """
    valores = []
    for s in series:
        if s is None:
            continue
        try:
            arr = pd.Series(s).dropna()
            if len(arr) > 0:
                valores.extend([float(arr.min()), float(arr.max())])
        except Exception:
            continue
    for r in referencias:
        if r is None:
            continue
        try:
            valores.append(float(r))
        except (TypeError, ValueError):
            continue
    if not valores:
        return [lo_min, hi_max]
    lo, hi = min(valores), max(valores)
    if lo == hi:
        # Evita range degenerado: cria janela de ±5% em torno do valor.
        delta = max(5.0, abs(lo) * 0.05)
        lo, hi = lo - delta, hi + delta
    margem = (hi - lo) * padding
    lo_final = max(lo_min, lo - margem)
    hi_final = min(hi_max, hi + margem)
    return [round(lo_final, 1), round(hi_final, 1)]


def range_dinamico_quartis(df, x_col, y_col, group_col=None,
                           *series_extras, padding: float = 0.08,
                           lo_min: float = 0, hi_max: float = 1000,
                           referencias=()) -> list:
    """Calcula range Y a partir dos Q1/Q3 das caixas, em vez dos valores brutos.

    Mantém a variação anual das médias visível ao não permitir que outliers
    individuais (notas próximas de 0 ou 1000) dominem o eixo Y. Considera
    também as séries extras (ex.: médias anuais) e referências fornecidas.
    Faz fallback para ``range_dinamico`` sobre a coluna bruta caso os
    quartis não possam ser calculados.
    """
    quartis = []
    try:
        if group_col is not None:
            agg = (df.groupby([x_col, group_col], observed=True)[y_col]
                     .quantile([0.25, 0.75]).unstack())
        else:
            agg = (df.groupby(x_col, observed=True)[y_col]
                     .quantile([0.25, 0.75]).unstack())
        if agg is not None and not agg.empty and 0.25 in agg.columns and 0.75 in agg.columns:
            q1 = pd.Series(agg[0.25]).dropna()
            q3 = pd.Series(agg[0.75]).dropna()
            if not q1.empty and not q3.empty:
                q1_min = float(q1.min())
                q3_max = float(q3.max())
                if np.isfinite(q1_min) and np.isfinite(q3_max):
                    quartis = [q1_min, q3_max]
    except Exception:
        quartis = []
    if not quartis:
        # Fallback: usa a coluna bruta se não foi possível calcular quartis
        try:
            return range_dinamico(df[y_col], *series_extras,
                                  padding=padding, lo_min=lo_min,
                                  hi_max=hi_max, referencias=referencias)
        except Exception:
            return [lo_min, hi_max]
    return range_dinamico(quartis, *series_extras, padding=padding,
                          lo_min=lo_min, hi_max=hi_max,
                          referencias=referencias)
def _fig_histogram_notas(
    notas: pd.Series,
    titulo: str,
    *,
    cor: str = AZUL_PRINCIPAL,
    nbins: int = 30,
    altura: int = CHART_H_HIST,
    media_ref: Optional[float] = None,
    mediana_ref: Optional[float] = None,
) -> go.Figure:
    """Histograma de distribuição de notas com linhas de referência."""
    s = pd.to_numeric(notas, errors="coerce").dropna()
    s = s[s > 0]
    fig = go.Figure()
    if s.empty:
        fig.update_layout(title=titulo, height=altura)
        return aplicar_tema(fig, altura)

    fig.add_trace(go.Histogram(
        x=s,
        nbinsx=nbins,
        marker=dict(color=cor, line=dict(color="white", width=0.5)),
        name="Estudantes",
        hovertemplate="Faixa: %{x}<br>Quantidade: %{y}<extra></extra>",
    ))
    media = float(s.mean())
    mediana = float(s.median())
    fig.add_vline(
        x=media, line_dash="solid", line_color=LARANJA_DESTAQUE, line_width=2,
        annotation_text=f"Média {media:.1f}", annotation_position="top right",
    )
    fig.add_vline(
        x=mediana, line_dash="dash", line_color=TEMA["texto_secundario"], line_width=1.5,
        annotation_text=f"Mediana {mediana:.1f}", annotation_position="top left",
    )
    if media_ref is not None and pd.notna(media_ref):
        fig.add_vline(
            x=float(media_ref), line_dash="dot", line_color=COR_BRASIL, line_width=1.5,
            annotation_text=f"Ref. {media_ref:.1f}", annotation_position="bottom right",
        )
    fig.update_layout(
        title=titulo,
        xaxis=dict(title="Nota", range=[0, 1000]),
        yaxis=dict(title="Quantidade de estudantes"),
        bargap=0.05,
        showlegend=False,
    )
    return aplicar_tema(fig, altura)


def _label_faixa_histograma(bin_lo: float, bin_hi: float) -> str:
    """Rótulo legível para faixa do histograma (NA, Zero, >0–50, 50–100, …)."""
    lo, hi = float(bin_lo), float(bin_hi)
    if lo == HIST_BIN_NA and hi == HIST_BIN_NA:
        return "NA"
    if lo == 0 and hi == 0:
        return "Zero"
    if lo == 0 and hi == 50:
        return ">0–50"
    return f"{int(lo)}–{int(hi)}"


def _centro_largura_faixa(bin_lo: float, bin_hi: float) -> tuple[float, float]:
    """Centro e largura da barra (NA à esquerda; Zero em x=0)."""
    lo, hi = float(bin_lo), float(bin_hi)
    if lo == HIST_BIN_NA and hi == HIST_BIN_NA:
        return -75.0, 40.0
    if lo == 0 and hi == 0:
        return 0.0, 25.0
    return (lo + hi) / 2, (hi - lo) * 0.92


def _fig_histogramas_multiarea_coloridos(
    bins_por_area: dict[str, pd.DataFrame],
    refs_ano: dict[str, dict[str, float]],
    ano: int,
    *,
    altura_por_linha: int = CHART_H_HIST_ROW,
) -> go.Figure:
    """Grade 2×3 de histogramas por área com barras coloridas vs referências MS/BR."""
    areas_keys = list(AREAS.keys())
    n_cols = 3
    n_rows = (len(areas_keys) + n_cols - 1) // n_cols

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[AREAS_COMPLETO.get(k, k) for k in areas_keys],
        horizontal_spacing=0.06,
        vertical_spacing=0.14,
        shared_xaxes=True,
    )

    for i, key in enumerate(areas_keys):
        r = i // n_cols + 1
        c = i % n_cols + 1
        df_bins = bins_por_area.get(key, pd.DataFrame())
        ref = refs_ano.get(key, {})
        ref_ms = ref.get("ms")
        ref_br = ref.get("br")

        if df_bins.empty:
            fig.add_annotation(
                text="Sem dados",
                xref="x domain", yref="y domain",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=12, color=TEMA["texto_secundario"]),
                row=r, col=c,
            )
            fig.update_xaxes(range=[-100, 1000], row=r, col=c)
            fig.update_yaxes(row=r, col=c)
            continue

        df_bins = df_bins.sort_values("bin_lo").reset_index(drop=True)
        centers = []
        widths = []
        labels = []
        for _, row in df_bins.iterrows():
            center, w = _centro_largura_faixa(row["bin_lo"], row["bin_hi"])
            centers.append(center)
            widths.append(w)
            labels.append(_label_faixa_histograma(row["bin_lo"], row["bin_hi"]))
        colors = [
            COR_HIST_NA if lbl == "NA" else _classificar_cor_media_referencia(center, ref_ms, ref_br)
            for lbl, center in zip(labels, centers)
        ]
        total_n = int(df_bins["count"].sum())

        fig.add_trace(
            go.Bar(
                x=centers,
                y=df_bins["count"].tolist(),
                width=widths,
                marker_color=colors,
                marker_line=dict(color="white", width=0.5),
                showlegend=False,
                customdata=labels,
                hovertemplate=(
                    f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                    "Faixa: %{customdata}<br>"
                    "Estudantes: %{y:,}<br>"
                    f"Total área: {total_n:,}"
                    "<extra></extra>"
                ),
            ),
            row=r, col=c,
        )

        if ref_ms is not None and pd.notna(ref_ms):
            fig.add_vline(
                x=float(ref_ms), line_dash="solid", line_color=AZUL_PRINCIPAL,
                line_width=1.5, row=r, col=c,
            )
        if ref_br is not None and pd.notna(ref_br):
            fig.add_vline(
                x=float(ref_br), line_dash="dot", line_color=COR_BRASIL,
                line_width=1.5, row=r, col=c,
            )

        fig.update_xaxes(
            range=[-100, 1000],
            tickvals=[-75, 0, 250, 500, 750, 1000],
            ticktext=["NA", "0", "250", "500", "750", "1000"],
            tickfont=dict(size=9, color=TEMA["texto_secundario"]),
            showgrid=False,
            row=r, col=c,
        )
        fig.update_yaxes(
            title_text="N" if c == 1 else "",
            tickfont=dict(size=9, color=TEMA["texto_secundario"]),
            gridcolor="rgba(200,200,200,0.3)",
            row=r, col=c,
        )

    altura_total = max(CHART_H_HIST_GRID, altura_por_linha * n_rows)
    fig.update_layout(
        title=dict(text=f"Distribuição de notas por área — rede estadual MS ({ano})", font=dict(size=14)),
        bargap=0.02,
        showlegend=False,
    )
    for ann in getattr(fig.layout, "annotations", []) or []:
        if ann.text and ann.text in {AREAS_COMPLETO.get(k, k) for k in areas_keys}:
            ann.font = dict(
                size=12, color=AZUL_PRINCIPAL, family="Plus Jakarta Sans, sans-serif",
            )
    return aplicar_tema(fig, altura_total)

def _adicionar_referencias_ms_br(fig, media_ms, media_br, *,
                                 sufixo_legenda: str = "rede estadual",
                                 x_dominio_min=None, x_dominio_max=None,
                                 limiar_colisao: float = 8.0):
    """Adiciona linhas de referência MS e BR + pinos numéricos à direita.

    Modos de desenho da linha horizontal:

    - **Modo domínio** (``x_dominio_min`` e ``x_dominio_max`` informados):
      desenhada via ``go.Scatter`` com ``x=[xmin, xmax]`` no domínio do eixo
      X — apropriado para eixos numéricos contínuos.
    - **Modo paper** (default): a linha é desenhada via
      ``fig.add_shape(type="line", xref="paper", ...)`` para cobrir toda a
      largura do plot independente do tipo do eixo X (categórico ou
      numérico). Um ``go.Scatter`` "fantasma" (``x=[None], y=[None]``) é
      adicionado APENAS para preservar o item correspondente na legenda
      nativa do Plotly.

    AVISO: nunca atribuir ``xref`` a ``go.Scatter`` — essa propriedade só
    existe em ``annotations`` e ``shapes``. Para linhas horizontais em
    coordenadas "paper" use sempre ``add_shape``.

    Demais comportamentos:
    - Aplica anti-colisão (``yshift``) quando ``|MS − BR| < limiar_colisao``.
    - Trata ``NaN``/``None`` omitindo a linha/pino correspondente.
    - Itens MS e BR compartilham ``legendgroup="medias_ref"`` para toggle
      conjunto.
    """
    tem_ms = media_ms is not None and not (
        isinstance(media_ms, float) and np.isnan(media_ms))
    tem_br = media_br is not None and not (
        isinstance(media_br, float) and np.isnan(media_br))
    if not tem_ms and not tem_br:
        return

    modo_paper = x_dominio_min is None or x_dominio_max is None
    proximas = tem_ms and tem_br and abs(
        float(media_ms) - float(media_br)) < limiar_colisao
    yshift_ms = 10 if proximas else 0
    yshift_br = -10 if proximas else 0

    def _desenhar_linha_ref(valor, cor, dash, nome_legenda, bg_alpha, yshift):
        v = float(valor)
        if modo_paper:
            # Linha que cobre toda a largura do plot, compatível com eixo X
            # categórico ou numérico. layer="above" garante que fique sobre
            # os boxes do px.box.
            fig.add_shape(
                type="line", xref="paper", yref="y",
                x0=0, x1=1, y0=v, y1=v,
                line=dict(color=cor, dash=dash, width=2),
                layer="above",
            )
            # Ghost trace apenas para a legenda nativa.
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="lines",
                line=dict(color=cor, dash=dash, width=2),
                name=nome_legenda,
                legendgroup="medias_ref",
                hoverinfo="skip",
                showlegend=True,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=[float(x_dominio_min), float(x_dominio_max)],
                y=[v, v],
                mode="lines",
                line=dict(color=cor, dash=dash, width=2),
                name=nome_legenda,
                legendgroup="medias_ref",
                hoverinfo="skip",
                showlegend=True,
            ))
        fig.add_annotation(
            xref="paper", x=1.0, xanchor="left",
            yref="y", y=v,
            text=f"<b>{fmt_float(valor)}</b>",
            showarrow=False,
            font=dict(size=11, color=cor,
                      family="Source Sans 3, system-ui, sans-serif"),
            bgcolor=_hex_to_rgba(cor, bg_alpha),
            bordercolor=cor,
            borderwidth=1, borderpad=3,
            yshift=yshift,
        )

    if tem_ms:
        _desenhar_linha_ref(
            media_ms, AZUL_PRINCIPAL, "dash",
            f"Média MS — {sufixo_legenda}: {fmt_float(media_ms)}",
            0.10, yshift_ms,
        )
    if tem_br:
        _desenhar_linha_ref(
            media_br, COR_BRASIL, "dot",
            f"Média BR — {sufixo_legenda}: {fmt_float(media_br)}",
            0.12, yshift_br,
        )


def _adicionar_series_medias_ms_br(fig, serie_ms, serie_br, sufixo_legenda, mostrar_rotulos):
    """Conecta as médias anuais MS e BR com linha + marcadores, ano a ano.

    Diferente de ``_adicionar_referencias_ms_br`` (que desenha linhas
    horizontais constantes), esta função recebe duas ``pd.Series`` indexadas
    por ano e desenha uma curva que varia ao longo do eixo X. Cada marcador
    pode receber um rótulo com o valor da média daquele ano.
    """
 # Série MS
    if serie_ms is not None and not serie_ms.empty:
        anos = serie_ms.index.tolist()   # já são strings
        valores = serie_ms.values
        fig.add_trace(go.Scatter(
            x=anos,
            y=valores,
            mode='lines+markers' + ('+text' if mostrar_rotulos else ''),
            text=[f'{v:.1f}' for v in valores] if mostrar_rotulos else None,
            textposition='top center',
            textfont=dict(size=10, color='#1f77b4'),
            name=f'Média MS — {sufixo_legenda}',
            line=dict(color='#1f77b4', width=2.5),
            marker=dict(size=6, color='#1f77b4'),
            legendgroup='medias',
            showlegend=True,
        ))

    # Série BR
    if serie_br is not None and not serie_br.empty:
        anos = serie_br.index.tolist()
        valores = serie_br.values
        fig.add_trace(go.Scatter(
            x=anos,
            y=valores,
            mode='lines+markers' + ('+text' if mostrar_rotulos else ''),
            text=[f'{v:.1f}' for v in valores] if mostrar_rotulos else None,
            textposition='top center',
            # cor diferente para distinguir
            textfont=dict(size=10, color="#636161"),
            name=f'Média BR — {sufixo_legenda}',
            line=dict(color="#636161", width=2.5, dash='dot'),
            marker=dict(size=6, color="#636161"),
            legendgroup='medias',
            showlegend=True,
        ))


def _adicionar_series_medias_por_dep(fig,
                                     series_por_dep: dict,
                                     serie_br=None,
                                     *,
                                     cores_dep: dict,
                                     sufixo_legenda: str = "rede estadual",
                                     mostrar_rotulos: bool = True,
                                     mostrar_delta_anotacao: bool = True,
                                     x_categorico: bool = True):
    """Sobrepõe uma curva de média anual por dependência sobre um boxplot.

    Parâmetros
    ----------
    fig : go.Figure
        Figura Plotly que já contém o boxplot (px.box) agrupado por DEP_ADM.
    series_por_dep : dict[str, pd.Series]
        Mapeia o nome da dependência para a série de médias anuais
        (índice = anos; valores = média da nota naquele ano).
    serie_br : pd.Series, opcional
        Série de médias anuais nacional (rede estadual) para referência.
    cores_dep : dict[str, str]
        Mapeia o nome da dependência para sua cor hexadecimal.
    sufixo_legenda : str
        Sufixo aplicado aos nomes das legendas (ex.: "rede estadual").
    mostrar_rotulos : bool
        Quando True, desenha o valor da média acima de cada marcador.
    mostrar_delta_anotacao : bool
        Quando True, adiciona uma anotação Δ (último − primeiro ano) à
        direita da última observação de cada série, com cor baseada no
        sinal/magnitude do delta.
    x_categorico : bool
        Quando True, converte o índice para ``str(int(x))`` para alinhar
        com eixos categóricos de px.box.
    """
    def _cor_delta(d):
        if d is None or (isinstance(d, float) and np.isnan(d)):
            return TEMA["texto_secundario"]
        if d >= 0:
            return COR_POSITIVO
        if d >= -10:
            return COR_ATENCAO
        return COR_CRITICO

    def _coerce_x(s):
        idx = s.index.tolist()
        if x_categorico:
            out = []
            for x in idx:
                try:
                    out.append(str(int(float(x))))
                except (TypeError, ValueError):
                    out.append(str(x))
            return out
        return [int(x) if float(x).is_integer() else x for x in idx]

    # --- Curvas por dependência ---
    for dep, serie in series_por_dep.items():
        if serie is None:
            continue
        try:
            s = pd.Series(serie).dropna()
        except Exception:
            continue
        if s.empty:
            continue
        cor = cores_dep.get(dep, AZUL_PRINCIPAL)
        x_vals = _coerce_x(s)
        y_vals = [float(v) for v in s.values]
        textos = [f"<b>{fmt_float(v)}</b>" for v in y_vals]
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="lines+markers+text" if mostrar_rotulos else "lines+markers",
            line=dict(color=cor, width=2.4),
            marker=dict(color=cor, size=9,
                        line=dict(color="#ffffff", width=1.4)),
            text=textos if mostrar_rotulos else None,
            textposition="top center",
            textfont=dict(size=10.5, color=cor,
                          family="Source Sans 3, system-ui, sans-serif"),
            name=f"Média {dep}",
            legendgroup="medias_dep",
            hovertemplate=(
                f"<b>Média {dep}</b><br>"
                "Ano: %{x}<br>Média: %{y:.1f}<extra></extra>"
            ),
            showlegend=True,
            cliponaxis=False,
        ))

        if mostrar_delta_anotacao and len(y_vals) >= 2:
            delta = y_vals[-1] - y_vals[0]
            cor_delta = _cor_delta(delta)
            sinal = "+" if delta >= 0 else "−"
            fig.add_annotation(
                x=x_vals[-1], y=y_vals[-1],
                xref="x", yref="y",
                text=f"<b>Δ {sinal}{fmt_float(abs(delta))}</b>",
                showarrow=False,
                xanchor="left", yanchor="middle",
                xshift=10,
                font=dict(size=11, color=cor_delta,
                          family="Source Sans 3, system-ui, sans-serif"),
                bgcolor=_hex_to_rgba(cor_delta, 0.10),
                bordercolor=cor_delta,
                borderwidth=1, borderpad=3,
            )

    # --- Linha BR de referência ---
    if serie_br is not None:
        try:
            s_br = pd.Series(serie_br).dropna()
        except Exception:
            s_br = pd.Series(dtype=float)
        if not s_br.empty:
            x_vals = _coerce_x(s_br)
            y_vals = [float(v) for v in s_br.values]
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                mode="lines+markers",
                line=dict(color=COR_BRASIL, dash="dot", width=2.0),
                marker=dict(color=COR_BRASIL, size=7,
                            line=dict(color="#ffffff", width=1.0)),
                name=f"Média BR — {sufixo_legenda}",
                legendgroup="medias_dep",
                hovertemplate=(
                    f"<b>Média BR — {sufixo_legenda}</b><br>"
                    "Ano: %{x}<br>Média: %{y:.1f}<extra></extra>"
                ),
                showlegend=True,
                cliponaxis=False,
            ))


def _mini_legenda_medias_html(media_ms, media_br, sufixo: str = "rede estadual") -> str:
    """Mini-legenda HTML acima dos boxplots, no padrão das seções já existentes.

    Omite o chip correspondente quando a média é NaN. Retorna string vazia se
    ambas estiverem indisponíveis.
    """
    tem_ms = media_ms is not None and not (
        isinstance(media_ms, float) and np.isnan(media_ms))
    tem_br = media_br is not None and not (
        isinstance(media_br, float) and np.isnan(media_br))
    if not tem_ms and not tem_br:
        return ""
    chips = []
    if tem_ms:
        chips.append(
            f'<div style="display:inline-flex; align-items:center; gap:8px;">'
            f'<span style="color:{AZUL_PRINCIPAL}; font-weight:700; letter-spacing:-1px;">━━</span>'
            f'<span style="color:{TEMA["texto"]};">Média MS — {sufixo}: '
            f'<b style="color:{AZUL_PRINCIPAL};">{fmt_float(media_ms)}</b></span>'
            f'</div>'
        )
    if tem_br:
        chips.append(
            f'<div style="display:inline-flex; align-items:center; gap:8px;">'
            f'<span style="color:{COR_BRASIL}; font-weight:700; letter-spacing:-1px;">┄┄</span>'
            f'<span style="color:{TEMA["texto"]};">Média BR — {sufixo}: '
            f'<b style="color:{COR_BRASIL};">{fmt_float(media_br)}</b></span>'
            f'</div>'
        )
    return (
        '<div style="display:flex; gap:24px; flex-wrap:wrap; margin:4px 0 10px; '
        'font-size:13px;">'
        + "".join(chips) +
        '</div>'
    )
def _abreviar_escola(nome: str, max_siglas: int = 3) -> str:
    if not isinstance(nome, str) or not nome.strip():
        return nome
    palavras = nome.upper().split()
    resultado, i = [], 0
    if palavras and palavras[0] in _PREFIXOS_ESC:
        resultado.append(palavras[0])
        i = 1
    siglas = []
    for p in palavras[i:]:
        p_clean = _re.sub(r"[^A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", "", p)
        if p_clean and p_clean not in _STOP_ABR:
            siglas.append(p_clean[0])
        if len(siglas) >= max_siglas:
            break
    if siglas:
        resultado.append("".join(siglas))
    return " ".join(resultado) if resultado else nome


def _abreviar_cidade(cidade: str) -> str:
    if not isinstance(cidade, str) or not cidade.strip():
        return cidade
    palavras = cidade.upper().split()
    siglas = [p[0] for p in palavras if p not in _STOP_ABR and p]
    return "".join(siglas) if siglas else cidade


def calcular_medias_referencia(df_ms, df_br, area_col):
    """Calcula médias de referência MS e BR para a área selecionada.

    A média BR considera apenas estudantes de escolas ESTADUAIS
    (DEP_ADM == 'Estadual'), concluintes do 3º ano, não treineiros,
    com participação efetiva (já filtrado em carregar_base_filtrada).
    """
    ms = float(df_ms[area_col].mean()) if not df_ms.empty else np.nan
    br = np.nan
    if not df_br.empty:
        # Filtrar apenas escolas estaduais para a média BR
        df_br_estadual = df_br[df_br["DEP_ADM"] == "Estadual"] if "DEP_ADM" in df_br.columns else df_br
        br = float(df_br_estadual[area_col].mean()) if not df_br_estadual.empty else np.nan
    return {"ms": ms, "br": br}


def _fig_barras_areas_referencia(
    registros: list[dict],
    ano: int,
    *,
    altura: int = 440,
) -> go.Figure:
    """Gráfico de barras com todas as áreas e cores por referência MS/BR."""
    if not registros:
        fig = go.Figure()
        fig.update_layout(title=f"Médias por área — rede estadual MS ({ano})", height=altura)
        return aplicar_tema(fig, altura)

    df = pd.DataFrame(registros)
    fig = go.Figure(go.Bar(
        x=df["AreaNome"],
        y=df["Media"],
        marker_color=df["Cor"],
        text=[f"{v:.1f}" if pd.notna(v) else "" for v in df["Media"]],
        textposition="outside",
        textfont=dict(size=11, color=TEMA["texto"]),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Média MS: %{y:.1f}<br>"
            "Ref. MS: %{customdata[0]:.1f}<br>"
            "Ref. BR: %{customdata[1]:.1f}"
            "<extra></extra>"
        ),
        customdata=df[["RefMS", "RefBR"]].values,
    ))

    fig.update_layout(
        title=f"Médias por área — rede estadual MS ({ano})",
        xaxis=dict(title="Área de conhecimento"),
        yaxis=dict(title="Nota média", range=[0, max(df["Media"].max() * 1.15, 1000)]),
        bargap=0.25,
        showlegend=False,
    )
    return aplicar_tema(fig, altura)


# ============================================================
# GRÁFICOS
# ============================================================


def fig_participacao_por_ano(df_bruta_ms, df_filt_ms, anos_sel, dep="Estadual", df_concluintes=None):
    linhas = []
    for ano in sorted(anos_sel):
        insc = len(df_bruta_ms[(df_bruta_ms["NU_ANO"] == ano) & (
            df_bruta_ms["DEP_ADM"] == dep)])
        part = len(df_filt_ms[(df_filt_ms["NU_ANO"] == ano)
                   & (df_filt_ms["DEP_ADM"] == dep)])
        
        # Buscar concluintes do ano
        concl = 0
        if df_concluintes is not None and not df_concluintes.empty:
            concl_ano = df_concluintes[df_concluintes["NU_ANO"] == ano]
            if not concl_ano.empty:
                concl = int(concl_ano["Concluintes"].sum())
        
        pct = round(100 * part / concl, 1) if concl else 0.0
        tx_insc = round(100 * insc / concl, 1) if concl else 0.0
        linhas.append(dict(
            Ano=int(ano), Inscritos=insc, Participantes=part,
            Concluintes=concl, Pct=pct, Tx_Inscrição=tx_insc,
        ))
    d = pd.DataFrame(linhas)

    fig = go.Figure()
    fig.add_bar(x=d["Ano"], y=d["Inscritos"], name="Inscritos",
                marker_color=COR_BAR_NEUTRA,
                text=[fmt_int(v) for v in d["Inscritos"]],
                textposition="inside")
    fig.add_bar(x=d["Ano"], y=d["Concluintes"], name="Concluintes",
                marker_color="#6C757D",
                text=[fmt_int(v) for v in d["Concluintes"]],
                textposition="inside")
    fig.add_bar(x=d["Ano"], y=d["Participantes"],
                name="Presentes nos 2 dias",
                marker_color=CORES_DEP[dep],
                text=[fmt_int(v) for v in d["Participantes"]],
                textposition="outside")
    fig.add_trace(go.Scatter(
        x=d["Ano"], y=d["Tx_Inscrição"], name="Tx inscrição (%)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color=LARANJA_DESTAQUE, width=2.5),
        marker=dict(size=8),
    ))
    fig.add_trace(go.Scatter(
        x=d["Ano"], y=d["Pct"], name="Taxa part. efetiva (%)",
        mode="lines+markers+text",
        text=[fmt_pct(v) for v in d["Pct"]],
        textposition="top center",
        yaxis="y2",
        line=dict(color=AZUL_PRINCIPAL, width=3),
        marker=dict(size=10, symbol="diamond"),
    ))
    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Quantidade"),
        yaxis2=dict(title="Taxa (%)", overlaying="y", side="right",
                    range=[0, 110], showgrid=False),
        xaxis=dict(tickmode="linear", dtick=1),
        title="Inscritos, concluintes, presentes e taxas sobre concluintes — rede estadual",
        legend=dict(tracegroupgap=10),
    )
    return aplicar_tema(fig, CHART_H_EVOLUCAO)

def fig_ms_participacao_desempenho(
    tabelas: dict,
    anos_sel: list,
    dep: str = "Estadual",
    area: str = "MEDIA_GERAL",
) -> go.Figure:
    """MS: funil de participação (por ano) + média estadual no mesmo painel."""
    from plotly.subplots import make_subplots

    part = participacao_ms_por_ano(tabelas, list(anos_sel), dep)
    if part.empty:
        return go.Figure()

    df_des = tabelas.get("desempenho", pd.DataFrame())
    medias = []
    if not df_des.empty:
        if area == "MEDIA_GERAL":
            col_media = "media_media_geral"
        elif area in COLS_NOTAS:
            col_media = f"media_{area.lower()}"
        else:
            col_media = f"media_nu_nota_{area.lower()}"
        for _, r in part.iterrows():
            hit = df_des[
                (df_des["ano"] == int(r["ano"])) & (df_des["dependencia"] == dep)
            ]
            medias.append(
                float(hit.iloc[0][col_media]) if not hit.empty and col_media in hit.columns else np.nan
            )
    else:
        medias = [np.nan] * len(part)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.58, 0.42],
        vertical_spacing=0.1,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        subplot_titles=(
            "Participação — concluintes, inscritos e presentes",
            f"Desempenho — média {nome_area_ext(area)} (MS)",
        ),
    )
    anos = part["ano"].astype(int)
    fig.add_bar(
        x=anos, y=part["Concluintes"], name="Concluintes",
        marker_color="#6C757D", row=1, col=1,
        text=[fmt_int(v) for v in part["Concluintes"]], textposition="inside",
    )
    fig.add_bar(
        x=anos, y=part["Inscritos"], name="Inscritos",
        marker_color="#0D6EFD", row=1, col=1,
        text=[fmt_int(v) for v in part["Inscritos"]], textposition="inside",
    )
    fig.add_bar(
        x=anos, y=part["Presentes"], name="Presentes 2 dias",
        marker_color="#198754", row=1, col=1,
        text=[fmt_int(v) for v in part["Presentes"]], textposition="outside",
    )
    fig.add_trace(
        go.Scatter(
            x=anos, y=part["Tx_Inscrição"], name="Tx inscrição (%)",
            mode="lines+markers+text",
            line=dict(color=LARANJA_DESTAQUE, width=2.5),
            marker=dict(size=8),
            text=[fmt_pct(v) for v in part["Tx_Inscrição"]],
            textposition="top center",
        ),
        row=1, col=1, secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=anos, y=part["Tx_Part_Efetiva"], name="Tx part. efetiva (%)",
            mode="lines+markers",
            line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
            marker=dict(size=8),
        ),
        row=1, col=1, secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=anos, y=medias, name=f"Média {nome_area_ext(area)}",
            mode="lines+markers+text",
            line=dict(color=AZUL_PRINCIPAL, width=3),
            marker=dict(size=10),
            text=[f"{v:.1f}" if pd.notna(v) else "" for v in medias],
            textposition="top center",
        ),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="Estudantes", row=1, col=1)
    fig.update_yaxes(title_text="Taxa (%)", range=[0, 110], row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Nota", range=[0, 1000], row=2, col=1)
    fig.update_xaxes(tickmode="linear", dtick=1, row=2, col=1)
    fig.update_layout(
        barmode="group",
        title="Participação e desempenho — evolução anual (MS)",
        legend=_legenda_padrao(y_pos=-0.18, font_size=10),
        margin=dict(t=80, b=120),
    )
    return _finalizar_grafico(fig, altura=CHART_H_HIST_GRID, n_legend=3)


def fig_combo_participacao_desempenho(
    part_df: pd.DataFrame,
    perf_df: pd.DataFrame,
    id_col: str,
    media_col: str,
    titulo: str = "",
) -> go.Figure:
    """Barras de funil + linhas de taxa + média (eixo direito) por entidade."""
    if part_df.empty or perf_df.empty:
        return go.Figure()
    combo = perf_df[[id_col, media_col]].merge(part_df, on=id_col, how="inner")
    if combo.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=combo[id_col], y=combo.get("Concluintes", pd.Series(dtype=float)),
        name="Concluintes", marker_color="#6C757D",
        text=[fmt_int(v) if pd.notna(v) else "—" for v in combo.get("Concluintes", [])],
        textposition="inside",
    ))
    if "Inscritos" in combo.columns:
        fig.add_trace(go.Bar(
            x=combo[id_col], y=combo["Inscritos"],
            name="Inscritos", marker_color="#0D6EFD",
            text=[fmt_int(v) if pd.notna(v) else "—" for v in combo["Inscritos"]],
            textposition="inside",
        ))
    fig.add_trace(go.Bar(
        x=combo[id_col], y=combo.get("Presentes", combo.get("Estudantes", 0)),
        name="Presentes 2 dias", marker_color="#198754",
        text=[fmt_int(v) if pd.notna(v) else "—" for v in combo.get("Presentes", combo.get("Estudantes", []))],
        textposition="outside",
    ))
    if "Tx_Inscrição" in combo.columns:
        fig.add_trace(go.Scatter(
            x=combo[id_col], y=combo["Tx_Inscrição"],
            name="Tx inscrição (%)", mode="lines+markers",
            line=dict(color=LARANJA_DESTAQUE, width=2.5),
            marker=dict(size=7), yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Tx inscrição: %{y:.1f}%<extra></extra>",
        ))
    if "Tx_Part_Efetiva" in combo.columns:
        fig.add_trace(go.Scatter(
            x=combo[id_col], y=combo["Tx_Part_Efetiva"],
            name="Tx part. efetiva (%)", mode="lines+markers",
            line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
            marker=dict(size=7), yaxis="y2",
        ))
    elif "Taxa_Efetiva" in combo.columns:
        fig.add_trace(go.Scatter(
            x=combo[id_col], y=combo["Taxa_Efetiva"],
            name="Tx part. efetiva (%)", mode="lines+markers",
            line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
            marker=dict(size=7), yaxis="y2",
        ))
    fig.add_trace(go.Scatter(
        x=combo[id_col], y=combo[media_col],
        name="Média", mode="markers+text",
        marker=dict(size=12, color=AZUL_PRINCIPAL, symbol="diamond"),
        text=[f"{v:.0f}" if pd.notna(v) else "" for v in combo[media_col]],
        textposition="top center",
        yaxis="y3",
        hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
    ))
    y1_max = max(
        combo.get("Concluintes", pd.Series([0])).max() or 0,
        combo.get("Inscritos", pd.Series([0])).max() or 0,
        combo.get("Presentes", combo.get("Estudantes", pd.Series([0]))).max() or 0,
    ) * 1.2 or 100
    fig.update_layout(
        title=titulo,
        barmode="group",
        yaxis=dict(title="Estudantes", range=[0, y1_max]),
        yaxis2=dict(title="Taxa (%)", overlaying="y", side="right", range=[0, 110], showgrid=False),
        yaxis3=dict(
            title="Média", overlaying="y", side="right", position=1.0,
            range=[0, 1000], showgrid=False, tickfont=dict(size=9),
        ),
        legend=_legenda_padrao(y_pos=-0.28, font_size=10),
        margin=dict(t=60, b=140, r=80),
    )
    return aplicar_tema(fig, CHART_H_RANKING)


def fig_quadrante_desempenho_participacao(
    part_df: pd.DataFrame,
    perf_df: pd.DataFrame,
    id_col: str,
    media_col: str,
    titulo: str = "Desempenho × participação efetiva",
) -> go.Figure:
    """Dispersão: eixo X = tx part. efetiva, eixo Y = média."""
    if part_df.empty or perf_df.empty:
        return go.Figure()
    tx_col = "Tx_Part_Efetiva" if "Tx_Part_Efetiva" in part_df.columns else "Taxa_Efetiva"
    combo = perf_df[[id_col, media_col]].merge(
        part_df[[id_col, tx_col]].dropna(subset=[tx_col]),
        on=id_col, how="inner",
    )
    if combo.empty:
        return go.Figure()
    med_x = combo[tx_col].median()
    med_y = combo[media_col].median()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=combo[tx_col], y=combo[media_col],
        mode="markers+text",
        text=combo[id_col].map(
            nome_cre_curto if id_col == "CRE" else lambda x: str(x)[:18]
        ),
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(size=11, color=AZUL_PRINCIPAL, opacity=0.75, line=dict(width=1, color="#fff")),
        hovertemplate=(
            f"<b>%{{customdata}}</b><br>"
            f"Tx part. efetiva: %{{x:.1f}}%<br>"
            f"Média: %{{y:.1f}}<extra></extra>"
        ),
        customdata=combo[id_col],
    ))
    fig.add_hline(y=med_y, line_dash="dash", line_color=COR_NEUTRO, opacity=0.6)
    fig.add_vline(x=med_x, line_dash="dash", line_color=COR_NEUTRO, opacity=0.6)
    fig.update_layout(
        title=titulo,
        xaxis=dict(title="Taxa de participação efetiva (%)", range=[0, 105]),
        yaxis=dict(title="Média", range=[0, 1000]),
        margin=dict(t=60, b=60),
        showlegend=False,
    )
    return aplicar_tema(fig, CHART_H_HIST)




def fig_media_area_deps(df, deps, titulo):
    dados = []
    for dep in deps:
        d = df[df["DEP_ADM"] == dep]
        for col, nome in AREAS.items():
            dados.append(dict(Dependência=dep, Área=nome,
                              Valor=round(float(d[col].mean()), 2)))
    dfv = pd.DataFrame(dados)
    fig = px.bar(
        dfv, x="Área", y="Valor", color="Dependência", barmode="group",
        color_discrete_map=CORES_DEP,
        category_orders={"Dependência": [d for d in ORDEM_DEP if d in deps]},
        text_auto=".1f",
        labels={"Valor": "Nota média"},
        title=titulo,
    )
    fig.update_yaxes(range=[0, 1000])
    return aplicar_tema(fig, CHART_H_EVOLUCAO)


def fig_evolucao_area(df, col, deps, titulo, df_contexto=None,
                      media_ms_ref=None, media_br_ref=None):
    fig = go.Figure()
    for dep in deps:
        s = (df[df["DEP_ADM"] == dep]
             .groupby("NU_ANO", observed=True)[col].mean().reset_index())
        destaque = (dep == "Estadual")
        fig.add_trace(go.Scatter(
            x=s["NU_ANO"], y=s[col].round(2),
            name=f"{dep}", mode="lines+markers+text" if destaque else "lines+markers",
            text=[fmt_float(v) for v in s[col]] if destaque else None,
            textposition="top center",
            line=dict(color=CORES_DEP[dep], width=3 if destaque else 2),
            marker=dict(size=8 if destaque else 5),
        ))
    if df_contexto is not None and not df_contexto.empty:
        s_br = df_contexto.groupby("NU_ANO", observed=True)[
                                   col].mean().reset_index()
        fig.add_trace(go.Scatter(
            x=s_br["NU_ANO"], y=s_br[col].round(2),
            name="Contexto nacional", mode="lines+markers",
            line=dict(color=COR_BRASIL, width=2, dash="dot"),
            marker=dict(size=6, symbol="diamond"),
        ))
    # Linhas de referência da média MS e BR
    if media_ms_ref is not None:
        fig.add_hline(y=media_ms_ref, line_dash="dash", line_color=AZUL_PRINCIPAL,
                      annotation_text="Média MS", annotation_position="left")
    if media_br_ref is not None:
        fig.add_hline(y=media_br_ref, line_dash="dot", line_color=COR_BRASIL,
                      annotation_text="Média BR", annotation_position="right")

    series_eixo = []
    for dep in deps:
        s = (df[df["DEP_ADM"] == dep]
             .groupby("NU_ANO", observed=True)[col].mean())
        series_eixo.append(s)
    if df_contexto is not None and not df_contexto.empty:
        series_eixo.append(df_contexto.groupby(
            "NU_ANO", observed=True)[col].mean())
    fig.update_layout(
        title=titulo,
        xaxis=dict(tickmode="linear", dtick=1, title="Ano"),
        yaxis=dict(
            range=[0, 1000],
            title="Nota média",
        ),
        hovermode="x unified",
    )
    return aplicar_tema(fig, CHART_H_EVOLUCAO)


def fig_ranking_horizontal(df, col_label, col_valor, titulo, cor=AZUL_PRINCIPAL,
                           altura=CHART_H_RANKING, casas_decimais=2, media_ms=None, media_br=None,
                           x_range=None, col_n=None, col_taxa=None,
                           rotulo_media_ms: str = "Média estadual",
                           rotulo_media_br: str = "Média nacional",
                           *, modo_hub: bool = False):
    d = df.copy().sort_values(col_valor, ascending=True)
    d[col_valor] = d[col_valor].round(casas_decimais)
    col_hover_cre = None
    if col_label == "CRE" and col_label in d.columns:
        d["_cre_nome_completo"] = d[col_label].astype(str)
        d[col_label] = d[col_label].map(nome_cre_curto)
        col_hover_cre = "_cre_nome_completo"
    cores = []
    for v in d[col_valor]:
        if media_ms is not None or media_br is not None:
            cores.append(_classificar_cor_media_referencia(v, media_ms, media_br))
        else:
            cores.append(cor)
    customdata = None
    hovertemplate = None
    if col_n is not None and col_taxa is not None and col_n in d.columns and col_taxa in d.columns:
        if col_hover_cre:
            customdata = d[[col_hover_cre, col_n, col_taxa]].values
            hovertemplate = (
                "<b>%{customdata[0]}</b><br>"
                f"Média: %{{x:.{casas_decimais}f}}<br>"
                "Participantes: %{customdata[1]}<br>"
                "Taxa: %{customdata[2]:.1f}%"
                "<extra></extra>"
            )
        else:
            customdata = d[[col_n, col_taxa]].values
            hovertemplate = (
                "<b>%{y}</b><br>"
                f"Média: %{{x:.{casas_decimais}f}}<br>"
                "Participantes: %{customdata[0]}<br>"
                "Taxa: %{customdata[1]:.1f}%"
                "<extra></extra>"
            )
    elif col_hover_cre:
        customdata = d[[col_hover_cre]].values
        rotulo_valor = (
            "Participação"
            if "part" in str(col_valor).lower() or "tx_" in str(col_valor).lower()
            else "Média"
        )
        hovertemplate = (
            "<b>%{customdata[0]}</b><br>"
            f"{rotulo_valor}: %{{x:.{casas_decimais}f}}<extra></extra>"
        )
    fig = go.Figure(go.Bar(
        x=d[col_valor], y=d[col_label], orientation="h",
        marker_color=cores, text=d[col_valor].apply(lambda x: f"{x:.{casas_decimais}f}"), textposition="outside",
        customdata=customdata,
        hovertemplate=hovertemplate,
    ))
    if media_ms is not None:
        fig.add_vline(
            x=media_ms, line_dash="dash", line_color=LARANJA_DESTAQUE, line_width=2.5,
        )
        if not modo_hub:
            fig.add_annotation(
                x=media_ms, xref="x", y=1.0, yref="paper", yanchor="bottom",
                text=f"<b>{rotulo_media_ms}</b> {media_ms:.1f}", showarrow=False, yshift=6,
                font=dict(size=FONT_AXIS, color=LARANJA_DESTAQUE),
                bgcolor="rgba(255,255,255,0.88)",
                bordercolor=LARANJA_DESTAQUE, borderpad=4,
            )
    if media_br is not None:
        fig.add_vline(
            x=media_br, line_dash="dot", line_color=COR_BRASIL, line_width=2,
        )
        if not modo_hub:
            fig.add_annotation(
                x=media_br, xref="x", y=0.0, yref="paper", yanchor="top",
                text=f"<b>{rotulo_media_br}</b> {media_br:.1f}", showarrow=False, yshift=-38,
                font=dict(size=FONT_AXIS, color=COR_BRASIL),
                bgcolor="rgba(255,255,255,0.88)",
                bordercolor=COR_BRASIL, borderpad=4,
            )
    cats = [str(v) for v in d[col_label]]
    yaxis_kw: dict = dict(title="")
    if modo_hub:
        yaxis_kw.update(
            type="category",
            categoryorder="array",
            categoryarray=cats,
            tickmode="array",
            tickvals=cats,
            ticktext=cats,
            automargin=True,
            ticklabelstandoff=4,
        )
    fig.update_layout(
        title=titulo,
        xaxis=dict(
            title="",
            range=x_range if x_range is not None else range_dinamico(d[col_valor], padding=0.05,
                                 referencias=(media_ms, media_br)),
            showticklabels=not modo_hub,
            ticks="" if modo_hub else "outside",
        ),
        yaxis=yaxis_kw,
        margin=margem_hub(rank=modo_hub) if modo_hub else dict(t=52, b=80),
        bargap=0.22 if modo_hub else 0.15,
    )
    return aplicar_tema(fig, altura, limpar_titulo=modo_hub, modo_hub=modo_hub)


def fig_uf_barras(df, col, dep_filtro, titulo):
    d = df if dep_filtro is None else df[df["DEP_ADM"] == dep_filtro]
    col_uf = "SG_UF_ESC" if "SG_UF_ESC" in d.columns else "SG_UF_PROVA"
    g = d.groupby(col_uf)[col].mean().round(2).reset_index()
    g = g[g[col_uf].notna() & g[col_uf].str.len().eq(2)
                          ].rename(columns={col_uf: "UF"})
    g = g.sort_values(col, ascending=False)
    cores = [LARANJA_DESTAQUE if uf ==
        "MS" else COR_BAR_NEUTRA for uf in g["UF"]]
    fig = go.Figure(go.Bar(
        x=g["UF"], y=g[col], marker_color=cores,
        text=g[col].round(1), textposition="outside",
    ))
    fig.update_layout(
        title=titulo,
        xaxis=dict(title="UF", categoryorder="array",
                   categoryarray=g["UF"].tolist()),
        yaxis=dict(title="Nota média",
                   range=[0, 1000]),
    )
    return aplicar_tema(fig, CHART_H_EVOLUCAO)



def _fig_evolucao_medias_ms_br(df_est_ms, df_est_br):
    """Facetas 2×3 da média anual por área: MS (azul) vs Brasil (cinza), com Δ.

    Retorna a figura Plotly ou ``None`` quando não há dados no recorte.
    """
    def _classifica_delta(d):
        if pd.isna(d):
            return TEMA["texto_secundario"]
        if d >= 0:
            return COR_POSITIVO
        if d >= -10:
            return COR_ATENCAO
        return COR_CRITICO

    anos = sorted(df_est_ms["NU_ANO"].dropna().unique())
    if not anos:
        return None
    anos_int = [int(a) for a in anos]
    anos_str = [str(a) for a in anos_int]
    areas_keys = list(AREAS.keys())

    dados = []
    for ano in anos:
        for key in areas_keys:
            media_ms = df_est_ms[df_est_ms["NU_ANO"] == ano][key].mean()
            media_br = df_est_br[df_est_br["NU_ANO"] == ano][key].mean()
            delta = (
                media_ms - media_br
                if (pd.notna(media_ms) and pd.notna(media_br)) else float("nan")
            )
            dados.append({
                "Ano": int(ano),
                "AreaKey": key,
                "AreaNome": AREAS_COMPLETO.get(key, key),
                "MediaMS": media_ms,
                "MediaBR": media_br,
                "Delta": delta,
            })
    df_plot = pd.DataFrame(dados)
    if df_plot.empty or df_plot["MediaMS"].dropna().empty:
        return None

    n_areas = len(areas_keys)
    n_cols = 3
    n_rows = (n_areas + n_cols - 1) // n_cols
    y_min_global, y_max_global = 0, 1000

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[AREAS_COMPLETO.get(k, k) for k in areas_keys],
        horizontal_spacing=0.05,
        vertical_spacing=0.12,
        shared_xaxes=True,
        shared_yaxes=True,
    )

    for i, key in enumerate(areas_keys):
        r = i // n_cols + 1
        c = i % n_cols + 1
        d_area = df_plot[df_plot["AreaKey"] == key].sort_values("Ano")
        if d_area.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=d_area["Ano"].tolist(),
                y=d_area["MediaBR"].tolist(),
                mode="lines+markers",
                line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
                marker=dict(symbol="x", size=8, color=TEMA["texto_secundario"]),
                name="Brasil",
                legendgroup="br",
                showlegend=False,
                hovertemplate=(
                    f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                    "Ano: %{x}<br>"
                    "Brasil: %{y:.1f}"
                    "<extra></extra>"
                ),
            ),
            row=r, col=c,
        )

        fig.add_trace(
            go.Scatter(
                x=d_area["Ano"].tolist(),
                y=d_area["MediaMS"].tolist(),
                mode="lines+markers+text",
                line=dict(color=AZUL_PRINCIPAL, width=2.5),
                marker=dict(
                    symbol="circle", size=9, color=AZUL_PRINCIPAL,
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                text=[f"{v:.0f}" if pd.notna(v) else "" for v in d_area["MediaMS"]],
                textposition="top center",
                textfont=dict(
                    size=10, color=TEMA["texto"], family="Plus Jakarta Sans, sans-serif"),
                name="Mato Grosso do Sul",
                legendgroup="ms",
                showlegend=False,
                customdata=d_area[["MediaBR", "Delta"]].values,
                hovertemplate=(
                    f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                    "Ano: %{x}<br>"
                    "MS: %{y:.1f}<br>"
                    "Brasil: %{customdata[0]:.1f}<br>"
                    "Δ MS−BR: %{customdata[1]:+.1f}"
                    "<extra></extra>"
                ),
            ),
            row=r, col=c,
        )

        d_valid = d_area.dropna(subset=["MediaMS", "Delta"])
        for _, row_ano in d_valid.iterrows():
            cor_d = _classifica_delta(row_ano["Delta"])
            sinal = "+" if row_ano["Delta"] >= 0 else "−"
            fig.add_annotation(
                x=int(row_ano["Ano"]),
                y=float(row_ano["MediaMS"]),
                text=f"<b>Δ {sinal}{abs(row_ano['Delta']):.1f}</b>",
                showarrow=False,
                xshift=0,
                yshift=35,
                xanchor="center",
                font=dict(size=9, color=cor_d, family="Plus Jakarta Sans, sans-serif"),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor=cor_d,
                borderwidth=1,
                borderpad=2,
                row=r, col=c,
            )

        fig.update_yaxes(range=[y_min_global, y_max_global], row=r, col=c,
                         tickvals=[0, 250, 500, 750, 1000],
                         ticktext=["0", "250", "500", "750", "1000"],
                         tickfont=dict(size=10, color=TEMA["texto_secundario"]),
                         gridcolor="rgba(200,200,200,0.3)",
                         gridwidth=1,
                         showgrid=True)
        fig.update_xaxes(
            tickmode="array",
            tickvals=anos_int,
            ticktext=anos_str,
            range=[anos_int[0] - 0.4, anos_int[-1] + 0.4],
            tickangle=0,
            tickfont=dict(size=11, color=TEMA["texto_secundario"]),
            showgrid=False,
            row=r, col=c,
        )

    fig.add_trace(
        go.Scatter(
            x=[None], y=[None],
            mode="lines+markers",
            line=dict(color=AZUL_PRINCIPAL, width=2.5),
            marker=dict(symbol="circle", size=9, color=AZUL_PRINCIPAL),
            name="Mato Grosso do Sul",
            legendgroup="ms",
            showlegend=True,
            hoverinfo="skip",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[None], y=[None],
            mode="lines+markers",
            line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
            marker=dict(symbol="x", size=8, color=TEMA["texto_secundario"]),
            name="Brasil",
            legendgroup="br",
            showlegend=True,
            hoverinfo="skip",
        ),
        row=1, col=1,
    )

    altura_total = max(520, 260 * n_rows)
    fig.update_layout(height=altura_total)
    fig = aplicar_tema(fig, altura_total)
    fig.update_layout(
        title=dict(text="", font=dict(size=1)),
        margin=dict(l=24, r=24, t=90, b=60),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=TEMA["texto"], family="Plus Jakarta Sans, sans-serif"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=TEMA["borda"],
            borderwidth=1,
        ),
        plot_bgcolor="rgba(250,252,255,1)",
        paper_bgcolor="#FFFFFF",
    )
    for ann in getattr(fig.layout, 'annotations', []) or []:
        if ann.text and ann.text in {AREAS_COMPLETO.get(k, k) for k in areas_keys}:
            ann.font = dict(
                size=13, color=AZUL_PRINCIPAL, family="Plus Jakarta Sans, sans-serif")
            ann.bgcolor = "rgba(255,255,255,0.95)"
            ann.bordercolor = AZUL_PRINCIPAL
            ann.borderwidth = 1
            ann.borderpad = 4
    return fig


def _fig_evolucao_dispersao(df_dist_est):
    """Facetas 2×3 com média (linha), mediana (tracejada) e banda Q1–Q3 por área.

    Retorna a figura Plotly ou ``None`` quando não há dados no recorte.
    """
    if df_dist_est is None or df_dist_est.empty:
        return None
    areas_keys = list(AREAS.keys())
    anos_int = sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
    if not anos_int:
        return None
    anos_str = [str(a) for a in anos_int]
    n_cols = 3
    n_rows = (len(areas_keys) + n_cols - 1) // n_cols

    stats_por_area: dict[str, pd.DataFrame] = {}
    for key in areas_keys:
        registros = []
        for ano in anos_int:
            rows = df_dist_est[df_dist_est["ano"] == ano]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], key)
            if stats is None:
                continue
            registros.append({
                "Ano": ano,
                "Media": stats["mean"],
                "Mediana": stats["median"],
                "Std": (stats["q3"] - stats["q1"]) / 1.349,
                "Lo": stats["q1"],
                "Hi": stats["q3"],
                "N": stats["n"],
            })
        stats_por_area[key] = pd.DataFrame(registros)

    y_min_fan, y_max_fan = 0, 1000

    fig_fan = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[AREAS_COMPLETO.get(k, k) for k in areas_keys],
        horizontal_spacing=0.06,
        vertical_spacing=0.14,
        shared_xaxes=True,
        shared_yaxes=True,
    )

    COR_MEDIANA = "#7e8fa6"

    for i, key in enumerate(areas_keys):
        r = i // n_cols + 1
        c = i % n_cols + 1
        df_stats = stats_por_area.get(key, pd.DataFrame())
        cor_area_fan = CORES_AREAS.get(key, AZUL_PRINCIPAL)
        cor_banda_area = _hex_to_rgba(cor_area_fan, 0.18)

        if df_stats.empty:
            fig_fan.update_yaxes(range=[y_min_fan, y_max_fan], row=r, col=c)
            fig_fan.update_xaxes(
                tickmode="array",
                tickvals=anos_int,
                ticktext=anos_str,
                range=[anos_int[0] - 0.4, anos_int[-1] + 0.4],
                tickangle=0,
                tickfont=dict(size=11, color=TEMA["texto_secundario"]),
                row=r, col=c,
            )
            continue

        anos_f = df_stats["Ano"].tolist()

        fig_fan.add_trace(
            go.Scatter(
                x=anos_f,
                y=df_stats["Lo"].tolist(),
                mode="lines",
                line=dict(width=0, color=cor_banda_area),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=r, col=c,
        )
        fig_fan.add_trace(
            go.Scatter(
                x=anos_f,
                y=df_stats["Hi"].tolist(),
                mode="lines",
                line=dict(width=0, color=cor_banda_area),
                fill="tonexty",
                fillcolor=cor_banda_area,
                hoverinfo="skip",
                showlegend=False,
            ),
            row=r, col=c,
        )
        fig_fan.add_trace(
            go.Scatter(
                x=anos_f,
                y=df_stats["Mediana"].tolist(),
                mode="lines",
                line=dict(color=COR_MEDIANA, width=1.6, dash="dash"),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=r, col=c,
        )
        customdata = list(zip(
            df_stats["Mediana"].tolist(),
            df_stats["Std"].tolist(),
            df_stats["Lo"].tolist(),
            df_stats["Hi"].tolist(),
            df_stats["N"].tolist(),
        ))
        fig_fan.add_trace(
            go.Scatter(
                x=anos_f,
                y=df_stats["Media"].tolist(),
                customdata=customdata,
                mode="lines+markers",
                line=dict(color=cor_area_fan, width=2.4),
                marker=dict(color=cor_area_fan, size=7,
                            line=dict(color="white", width=1.2)),
                showlegend=False,
                hovertemplate=(
                    f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                    "Ano: %{x}<br>"
                    "Média: %{y:.1f}<br>"
                    "Mediana: %{customdata[0]:.1f}<br>"
                    "Desvio padrão: %{customdata[1]:.1f}<br>"
                    "Faixa μ±σ: %{customdata[2]:.1f} – %{customdata[3]:.1f}<br>"
                    "N candidatos: %{customdata[4]:,}"
                    "<extra></extra>"
                ),
            ),
            row=r, col=c,
        )

        if len(df_stats) >= 2:
            primeiro = float(df_stats.iloc[0]["Media"])
            ultimo = float(df_stats.iloc[-1]["Media"])
            if primeiro > 0:
                delta_pct = (ultimo - primeiro) / primeiro * 100
                sinal = "+" if delta_pct >= 0 else ""
                fig_fan.add_annotation(
                    x=int(df_stats.iloc[-1]["Ano"]),
                    y=ultimo,
                    text=f"<b>Δ {sinal}{delta_pct:.1f}%</b>",
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle",
                    xshift=10,
                    font=dict(size=10, color=TEMA["texto_secundario"]),
                    row=r, col=c,
                )

        fig_fan.update_yaxes(
            range=[y_min_fan, y_max_fan], row=r, col=c,
            tickvals=[0, 250, 500, 750, 1000],
            ticktext=["0", "250", "500", "750", "1000"],
            tickfont=dict(size=10, color=TEMA["texto_secundario"]),
            gridcolor="rgba(200,200,200,0.3)",
            gridwidth=1,
            showgrid=True,
        )
        fig_fan.update_xaxes(
            tickmode="array",
            tickvals=anos_int,
            ticktext=anos_str,
            range=[anos_int[0] - 0.4, anos_int[-1] + 0.4],
            tickangle=0,
            tickfont=dict(size=11, color=TEMA["texto_secundario"]),
            showgrid=False,
            row=r, col=c,
        )

    altura_fan = max(580, 290 * n_rows)
    fig_fan.update_layout(height=altura_fan)
    fig_fan = aplicar_tema(fig_fan, altura_fan)
    fig_fan.update_layout(
        title=dict(text="", font=dict(size=1)),
        margin=dict(l=24, r=24, t=100, b=50),
        showlegend=False,
        plot_bgcolor="rgba(250,252,255,1)",
        paper_bgcolor="#FFFFFF",
    )
    for ann in getattr(fig_fan.layout, 'annotations', []) or []:
        if ann.text and ann.text in {AREAS_COMPLETO.get(k, k) for k in areas_keys}:
            ann.font = dict(
                size=13, color=AZUL_PRINCIPAL, family="Plus Jakarta Sans, sans-serif")
            ann.bgcolor = "rgba(255,255,255,0.95)"
            ann.bordercolor = AZUL_PRINCIPAL
            ann.borderwidth = 1
            ann.borderpad = 4
    return fig_fan


def _fig_evolucao_unificada(df_dist_est, tabelas=None, df_est_br=None):
    """Visão única por área (2×3): faixa Q1–Q3 + mediana + média MS + média Brasil.

    Quantis de MS em ``df_dist_est``; médias BR via ``referencias.parquet``
    (``tabelas``) ou fallback em ``df_est_br`` legado.
    """
    if df_dist_est is None or df_dist_est.empty:
        return None
    areas_keys = list(AREAS.keys())
    anos_int = sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
    if not anos_int:
        return None
    anos_str = [str(a) for a in anos_int]
    n_cols = 3
    n_rows = (len(areas_keys) + n_cols - 1) // n_cols

    if tabelas is not None:
        br_por_area = medias_br_serie_por_area(tabelas, anos_int)
    else:
        br_por_area = {k: {} for k in areas_keys}
        if (
            df_est_br is not None and not df_est_br.empty
            and "NU_ANO" in df_est_br.columns
        ):
            for key in areas_keys:
                if key in df_est_br.columns:
                    g = df_est_br.groupby(df_est_br["NU_ANO"].astype(int))[key].mean()
                    br_por_area[key] = {int(a): float(v) for a, v in g.items() if pd.notna(v)}

    # Estatísticas de MS por ano/área — quantis agregados (média, mediana, Q1–Q3)
    stats_por_area: dict[str, pd.DataFrame] = {}
    for key in areas_keys:
        registros = []
        for ano in anos_int:
            rows = df_dist_est[df_dist_est["ano"] == ano]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], key)
            if stats is None:
                continue
            registros.append({
                "Ano": ano,
                "Media": stats["mean"],
                "Mediana": stats["median"],
                "Lo": stats["q1"],
                "Hi": stats["q3"],
                "N": stats["n"],
                "MediaBR": br_por_area[key].get(ano, float("nan")),
            })
        stats_por_area[key] = pd.DataFrame(registros)

    y_min, y_max = 0, 1000
    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[AREAS_COMPLETO.get(k, k) for k in areas_keys],
        horizontal_spacing=0.06,
        vertical_spacing=0.14,
        shared_xaxes=True,
        shared_yaxes=True,
    )
    COR_MEDIANA = "#7e8fa6"
    COR_BANDA = _hex_to_rgba(AZUL_PRINCIPAL, 0.14)

    for i, key in enumerate(areas_keys):
        r = i // n_cols + 1
        c = i % n_cols + 1
        df_stats = stats_por_area.get(key, pd.DataFrame())
        if df_stats.empty:
            fig.update_yaxes(range=[y_min, y_max], row=r, col=c)
            fig.update_xaxes(
                tickmode="array", tickvals=anos_int, ticktext=anos_str,
                range=[anos_int[0] - 0.4, anos_int[-1] + 0.4], tickangle=0,
                tickfont=dict(size=11, color=TEMA["texto_secundario"]),
                row=r, col=c,
            )
            continue

        anos_f = df_stats["Ano"].tolist()
        # Banda Q1–Q3 (dispersão)
        fig.add_trace(
            go.Scatter(x=anos_f, y=df_stats["Lo"].tolist(), mode="lines",
                       line=dict(width=0), hoverinfo="skip", showlegend=False),
            row=r, col=c,
        )
        fig.add_trace(
            go.Scatter(x=anos_f, y=df_stats["Hi"].tolist(), mode="lines",
                       line=dict(width=0), fill="tonexty", fillcolor=COR_BANDA,
                       hoverinfo="skip", showlegend=False),
            row=r, col=c,
        )
        # Mediana MS (tracejada)
        fig.add_trace(
            go.Scatter(x=anos_f, y=df_stats["Mediana"].tolist(), mode="lines",
                       line=dict(color=COR_MEDIANA, width=1.6, dash="dash"),
                       hoverinfo="skip", showlegend=False),
            row=r, col=c,
        )
        # Média do Brasil (referência)
        br_y = df_stats["MediaBR"].tolist()
        if any(pd.notna(v) for v in br_y):
            fig.add_trace(
                go.Scatter(x=anos_f, y=br_y, mode="lines+markers",
                           line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
                           marker=dict(symbol="x", size=7, color=TEMA["texto_secundario"]),
                           hoverinfo="skip", showlegend=False),
                row=r, col=c,
            )
        # Média MS (linha principal + rótulos)
        customdata = list(zip(
            df_stats["Mediana"].tolist(),
            df_stats["Lo"].tolist(),
            df_stats["Hi"].tolist(),
            df_stats["N"].tolist(),
            br_y,
            [(m - b) if (pd.notna(m) and pd.notna(b)) else None
             for m, b in zip(df_stats["Media"].tolist(), br_y)],
        ))
        fig.add_trace(
            go.Scatter(
                x=anos_f, y=df_stats["Media"].tolist(), customdata=customdata,
                mode="lines+markers+text",
                line=dict(color=AZUL_PRINCIPAL, width=2.6),
                marker=dict(color=AZUL_PRINCIPAL, size=8,
                            line=dict(color="white", width=1.3)),
                text=[f"{v:.0f}" if pd.notna(v) else "" for v in df_stats["Media"]],
                textposition="top center",
                textfont=dict(size=9.5, color=TEMA["texto"],
                              family="Plus Jakarta Sans, sans-serif"),
                showlegend=False,
                hovertemplate=(
                    f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                    "Ano: %{x}<br>"
                    "Média MS: %{y:.1f}<br>"
                    "Mediana MS: %{customdata[0]:.1f}<br>"
                    "Q1–Q3: %{customdata[1]:.1f} – %{customdata[2]:.1f}<br>"
                    "Média Brasil: %{customdata[4]:.1f}<br>"
                    "Δ MS−BR: %{customdata[5]:+.1f}<br>"
                    "N candidatos: %{customdata[3]:,}"
                    "<extra></extra>"
                ),
            ),
            row=r, col=c,
        )
        # Δ% no período (média MS)
        if len(df_stats) >= 2:
            primeiro = float(df_stats.iloc[0]["Media"])
            ultimo = float(df_stats.iloc[-1]["Media"])
            if primeiro > 0:
                delta_pct = (ultimo - primeiro) / primeiro * 100
                sinal = "+" if delta_pct >= 0 else ""
                fig.add_annotation(
                    x=int(df_stats.iloc[-1]["Ano"]), y=ultimo,
                    text=f"<b>Δ {sinal}{delta_pct:.1f}%</b>",
                    showarrow=False, xanchor="left", yanchor="middle", xshift=10,
                    font=dict(size=9.5, color=TEMA["texto_secundario"]),
                    row=r, col=c,
                )

        fig.update_yaxes(
            range=[y_min, y_max], row=r, col=c,
            tickvals=[0, 250, 500, 750, 1000],
            ticktext=["0", "250", "500", "750", "1000"],
            tickfont=dict(size=10, color=TEMA["texto_secundario"]),
            gridcolor="rgba(200,200,200,0.3)", gridwidth=1, showgrid=True,
        )
        fig.update_xaxes(
            tickmode="array", tickvals=anos_int, ticktext=anos_str,
            range=[anos_int[0] - 0.4, anos_int[-1] + 0.4], tickangle=0,
            tickfont=dict(size=11, color=TEMA["texto_secundario"]),
            showgrid=False, row=r, col=c,
        )

    # Legenda manual (uma entrada por série)
    fig.add_trace(
        go.Scatter(x=[None], y=[None], mode="lines+markers", name="Média MS (rede estadual)",
                   line=dict(color=AZUL_PRINCIPAL, width=2.6),
                   marker=dict(symbol="circle", size=8, color=AZUL_PRINCIPAL),
                   showlegend=True, hoverinfo="skip"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=[None], y=[None], mode="lines", name="Mediana MS",
                   line=dict(color=COR_MEDIANA, width=1.6, dash="dash"),
                   showlegend=True, hoverinfo="skip"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=[None], y=[None], mode="markers", name="Faixa Q1–Q3 (MS)",
                   marker=dict(symbol="square", size=14, color=COR_BANDA),
                   showlegend=True, hoverinfo="skip"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=[None], y=[None], mode="lines+markers", name="Média Brasil",
                   line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
                   marker=dict(symbol="x", size=7, color=TEMA["texto_secundario"]),
                   showlegend=True, hoverinfo="skip"),
        row=1, col=1,
    )

    altura = max(580, 290 * n_rows)
    fig.update_layout(height=altura)
    fig = aplicar_tema(fig, altura)
    fig.update_layout(
        title=dict(text="", font=dict(size=1)),
        margin=dict(l=24, r=24, t=100, b=60),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.10, xanchor="center", x=0.5,
            font=dict(size=12, color=TEMA["texto"], family="Plus Jakarta Sans, sans-serif"),
            bgcolor="rgba(255,255,255,0.9)", bordercolor=TEMA["borda"], borderwidth=1,
        ),
        plot_bgcolor="rgba(250,252,255,1)",
        paper_bgcolor="#FFFFFF",
    )
    for ann in getattr(fig.layout, 'annotations', []) or []:
        if ann.text and ann.text in {AREAS_COMPLETO.get(k, k) for k in areas_keys}:
            ann.font = dict(
                size=13, color=AZUL_PRINCIPAL, family="Plus Jakarta Sans, sans-serif")
            ann.bgcolor = "rgba(255,255,255,0.95)"
            ann.bordercolor = AZUL_PRINCIPAL
            ann.borderwidth = 1
            ann.borderpad = 4
    return fig


def _fig_box_distribuicao_areas(df_dist_est):
    """Boxplots por ano agrupados pelas 5 áreas de conhecimento — rede estadual MS.

    Retorna a figura Plotly ou ``None`` quando não há dados no recorte.
    """
    if df_dist_est is None or df_dist_est.empty:
        return None
    anos_box_temp = sorted(df_dist_est["ano"].unique().tolist())
    fig_box_temporal = go.Figure()
    areas_plot = [(col, AREAS[col]) for col in COLS_NOTAS]
    for col, nome in areas_plot:
        xs_area: list[str] = []
        stats_area: list[dict] = []
        for ano in anos_box_temp:
            rows = df_dist_est[df_dist_est["ano"] == ano]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], col)
            if stats is None:
                continue
            xs_area.append(str(int(ano)))
            stats_area.append(stats)
        _add_box_series(
            fig_box_temporal, name=nome, color=CORES_AREAS[col],
            x_vals=xs_area, stats_list=stats_area,
            legendgroup=nome, showlegend=True,
        )
    fig_box_temporal.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=[str(int(a)) for a in anos_box_temp],
    )
    return _finalizar_boxplot(
        fig_box_temporal,
        "Boxplot anual por área de conhecimento — rede estadual MS",
        altura=CHART_H_BOX_WIDE,
        eixo_x="Ano",
        n_legend=5,
    )
