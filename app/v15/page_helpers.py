"""Helpers compartilhados pelas páginas v15 (extraídos do monolito)."""

from __future__ import annotations

import html as _html
import os
import unicodedata
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados_agregados_loader import (
    histograma_area_ano,
    media_nacional_ponderada,
    medias_referencia_por_ano,
    stats_box_quantis,
)
from app.v15.boxplots import _add_box_series, _finalizar_boxplot
from app.v15.charts.detail import _fig_histogramas_multiarea_coloridos
from app.v15.charts_render import _chart
from app.v15.classifiers import classificar_participacao
from app.v15.components import titulo_secao
from app.v15.formatting import fmt_int, fmt_pct
from app.v15.paths import ARQUIVO_CONCLUINTES
from app.v15.plotly_theme import _hex_rgba
from app.v15.theme import (
    AREAS,
    AZUL_PRINCIPAL,
    COR_HIST_NA,
    CORES_DEP,
    TEMA,
)
from app.v15.ui import _legenda_inline, _render_html


def carregar_concluintes() -> pd.DataFrame:
    """Carrega dados de concluintes do 3º ano por escola e ano."""
    from concluintes_loader import carregar_concluintes_escola

    if ARQUIVO_CONCLUINTES is None or not os.path.exists(ARQUIVO_CONCLUINTES):
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "Concluintes"])
    try:
        return carregar_concluintes_escola(ARQUIVO_CONCLUINTES)
    except Exception as e:
        st.warning(f"Não foi possível carregar os dados de concluintes: {e}")
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "Concluintes"])


def _normalizar_nome_municipio(nome: str) -> str:
    """Normaliza nome de município para comparação: remove acentos, converte
    para maiúsculas, remove espaços extras e caracteres especiais.
    """
    if pd.isna(nome):
        return ""
    nome = str(nome).strip().upper()
    # Remove acentos usando NFKD + filtro de caracteres não-ASCII
    nome = "".join(c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c))
    # Remove espaços múltiplos
    nome = " ".join(nome.split())
    return nome


def carregar_concluintes_municipio() -> pd.DataFrame:
    """Carrega dados de concluintes agregados por município e ano.
    
    Retorna DataFrame com colunas: MUNICIPIO, NU_ANO, Concluintes, N_ESCOLAS.
    Se o arquivo não existir, retorna DataFrame vazio.
    """
    arquivo = os.getenv(
        "ARQUIVO_CONCLUINTES_MUNICIPIO",
        os.path.join(os.path.dirname(__file__), "data", "concluintes_por_municipio_ano.csv"),
    )
    if not os.path.exists(arquivo):
        return pd.DataFrame(columns=["MUNICIPIO", "NU_ANO", "Concluintes", "N_ESCOLAS"])
    
    try:
        df = pd.read_csv(arquivo)
        df["NU_ANO"] = pd.to_numeric(df["NU_ANO"], errors="coerce").astype("int16")
        df["Concluintes"] = pd.to_numeric(df["Concluintes"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception as e:
        st.warning(f"Não foi possível carregar dados de concluintes por município: {e}")
        return pd.DataFrame(columns=["MUNICIPIO", "NU_ANO", "Concluintes", "N_ESCOLAS"])
def _populacao_estadual_ano(
    tabelas: dict,
    ano: int,
) -> dict[str, Optional[int | float]]:
    """Concluintes e presentes (filtro ENEM) da rede estadual MS em um ano.

    Retorna concluintes, presentes_filt (presentes 2 dias, sem eliminados em
    qualquer área ou redação) e taxa_part (% presentes sobre concluintes).
    """
    df_part = tabelas.get("participacao_ano", pd.DataFrame())
    if df_part.empty:
        return {"concluintes": None, "presentes_filt": None, "taxa_part": None}
    sub = df_part[
        (df_part["ano"] == int(ano)) & (df_part["dependencia"] == "Estadual")
    ]
    if sub.empty:
        return {"concluintes": None, "presentes_filt": None, "taxa_part": None}
    row = sub.iloc[0]
    conc_raw = row.get("concluintes")
    pres_raw = row.get("presentes_filt", row.get("presentes"))
    concluintes = (
        int(conc_raw) if pd.notna(conc_raw) and int(conc_raw) > 0 else None
    )
    presentes_filt = (
        int(pres_raw) if pd.notna(pres_raw) and int(pres_raw) > 0 else None
    )
    taxa_part = None
    if concluintes and presentes_filt:
        taxa_part = round(100 * presentes_filt / concluintes, 1)
    return {
        "concluintes": concluintes,
        "presentes_filt": presentes_filt,
        "taxa_part": taxa_part,
    }
def _faixa_concluintes_participantes(diag: dict, periodo: str) -> None:
    """Funil compacto: concluintes → inscritos → participantes efetivos."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    n_insc = diag.get("n_inscritos")
    tx_efet = diag.get("tx_part_efetiva")
    tx_insc = diag.get("tx_inscricao")
    if not n_conc or not n_pres:
        _render_html(
            f'<div class="insight"><strong>Participação ({periodo}):</strong> '
            f'<b>{fmt_int(n_pres)}</b> participantes efetivos '
            f'(presentes 2 dias, sem eliminação). '
            f'Dados de concluintes indisponíveis para o recorte.</div>'
        )
        return

    status_efet = classificar_participacao(tx_efet if tx_efet is not None else 0)
    classe_efet = status_efet if status_efet in ("positivo", "atencao", "critico") else ""
    classe_insc = ""
    if tx_insc is not None:
        classe_insc = (
            "positivo" if tx_insc >= 70
            else ("atencao" if tx_insc >= 50 else "critico")
        )

    partes = [
        '<div class="faixa-populacao dash-card">',
        (
            f'<div class="secao-head">'
            f'<span class="secao-eyebrow">Participação</span>'
            f'<span class="secao-nome">Rede estadual · {_html.escape(periodo)}</span>'
            f'</div>'
        ),
        '<div class="fp-steps">',
        (
            f'<div class="fp-step fp-step-conc"><div class="fp-step-val azul">{fmt_int(n_conc)}</div>'
            f'<div class="fp-step-lbl">concluintes do Ensino Médio</div></div>'
        ),
    ]
    if n_insc:
        partes.append('<div class="fp-arrow">›</div>')
        tx_insc_html = (
            f'<div class="fp-step-tx insc {classe_insc}">{fmt_pct(tx_insc)} dos concluintes</div>'
            if tx_insc is not None else ""
        )
        partes.append(
            f'<div class="fp-step fp-step-insc"><div class="fp-step-val laranja">{fmt_int(n_insc)}</div>'
            f'<div class="fp-step-lbl">inscritos ENEM</div>{tx_insc_html}</div>'
        )
    partes.extend([
        '<div class="fp-arrow">›</div>',
        (
            f'<div class="fp-step fp-step-efet"><div class="fp-step-val verde">{fmt_int(n_pres)}</div>'
            f'<div class="fp-step-lbl">participantes efetivos</div>'
            f'<div class="fp-step-tx efet {classe_efet}">{fmt_pct(tx_efet)} dos concluintes</div></div>'
        ),
        '</div></div>',
    ])
    _render_html("".join(partes))
def _legenda_populacoes_secao_html(
    ano: int,
    pop: dict[str, Optional[int | float]],
    *,
    n_histograma: Optional[int] = None,
    contexto: str = "histogramas",
) -> str:
    """Legenda da população e das faixas dos histogramas / boxplot por dependência."""
    n_pres = pop.get("presentes_filt")
    conc = pop.get("concluintes")
    tx = pop.get("taxa_part")
    n_hist_txt = (
        f" <span style='color:{TEMA['texto_secundario']};'>"
        f"(total por área no histograma: <b>{n_histograma:,}</b>)"
        f"</span>"
        if n_histograma and n_pres and n_histograma == n_pres else ""
    )
    linha_pop = (
        f"<li><b>População-base</b> — concluintes da rede estadual presentes nos "
        f"<b>2 dias</b> e <b>não eliminados</b> em nenhuma área nem redação"
        + (
            f": <b>{n_pres:,}</b> estudantes"
            + (
                f" ({fmt_pct(tx)} dos {conc:,} concluintes)"
                if conc and tx is not None else ""
            )
            if n_pres else ": —"
        )
        + f".{n_hist_txt}</li>"
    )
    linha_faixas = (
        f"<li><b>Faixas do histograma</b> — por área, cada estudante entra em "
        f"<b>uma</b> categoria: <span style='color:{COR_HIST_NA};'>■</span> <b>NA</b> "
        f"(nota ausente), <b>Zero</b>, <b>&gt;0–50</b>, <b>50–100</b>, …, <b>950–1000</b>. "
        f"Média Geral usa a média das notas preenchidas (NA se todas ausentes).</li>"
    )
    linha_box = (
        "<li><b>Boxplot por dependência</b> — mesma população-base por dependência; "
        "passe o mouse para ver Máx, Q3, mediana, Q1, Mín e n (nota &gt; 0 na área).</li>"
    )
    itens = [linha_pop, linha_faixas]
    if contexto == "dependencias":
        itens.append(linha_box)
    ctx = (
        "Histogramas e estatísticas anuais compartilham a população-base acima. "
        "Cores das barras (exceto NA) comparam cada faixa com as médias MS/BR."
        if contexto == "histogramas"
        else "Histogramas mostram NA, Zero e faixas de nota; o boxplot resume quantis "
        "apenas entre notas &gt; 0."
    )
    return (
        f"<div style='background:{TEMA['bg_card']}; border:1px solid {TEMA['borda']}; "
        f"border-radius:8px; padding:12px 16px; margin:12px 0 16px; font-size:13px;'>"
        f"<div style='font-weight:700; color:{AZUL_PRINCIPAL}; margin-bottom:8px;'>"
        f"População e faixas — rede estadual MS, {ano}</div>"
        f"<ul style='margin:0 0 8px 18px; padding:0; color:{TEMA['texto']};'>"
        f"{''.join(itens)}</ul>"
        f"<div style='color:{TEMA['texto_secundario']}; font-size:12px;'>{ctx}</div>"
        f"</div>"
    )
def _estilizar_tabela(
    df_display: pd.DataFrame,
    df_raw: pd.DataFrame,
    colunas_area: list[str],
    cores_area: dict[str, str],
    medias_ms: dict[str, float],
    medias_br: dict[str, float],
    col_escola: str = "Escola",
    tx_col: str = "Tx_Part_Efetiva",
    concluintes_col: str = "Concluintes",
    area_labels: dict[str, str] = None,
    tx_threshold_vermelho: float = 70.0,
    tx_threshold_laranja: float = 70.0,
    tx_threshold_verde: float = 80.0,
    colorir_linha_tx: bool = True,
) -> "pandas.io.formats.style.Styler":
    """
    Aplica estilização padronizada em tabelas de dados completos.

    - Fundo colorido por área do conhecimento
    - Fonte condicional (verde/azul/vermelho) vs médias MS/BR
    - Coloração de linha baseada na Taxa de Part. Efetiva
    - Cabeçalho com cores das áreas
    - Hover destacando a linha
    """
    if area_labels is None:
        area_labels = {}

    # Garantir DataFrames sem colunas duplicadas
    if df_display.columns.duplicated().any():
        df_display = df_display.loc[:, ~df_display.columns.duplicated()]
        df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]

    # --- Helpers puros ---
    def _hex_rgba_safe(hex_color, alpha):
        try:
            return _hex_rgba(hex_color, alpha)
        except Exception:
            return f"rgba(123, 135, 148, {alpha})"

    def _cor_fonte_media(val, media_ms, media_br, cor_padrao_area=None):
        try:
            if isinstance(val, (pd.Series, pd.DataFrame)):
                return f"color: {cor_padrao_area or '#1A2332'}; font-weight: 600;" if cor_padrao_area else "color: #9CA3AF;"
            if pd.isna(val):
                return "color: #9CA3AF;"
            if isinstance(media_ms, (pd.Series, pd.DataFrame)):
                media_ms = None
            if isinstance(media_br, (pd.Series, pd.DataFrame)):
                media_br = None
            ms_valido = media_ms is not None and pd.notna(media_ms)
            br_valido = media_br is not None and pd.notna(media_br)
            if not ms_valido or not br_valido:
                if cor_padrao_area:
                    return f"color: {cor_padrao_area}; font-weight: 600;"
                return "color: #1A2332;"
            acima_ms = val >= float(media_ms)
            acima_br = val >= float(media_br)
            if acima_br:
                return f"color: {COR_POSITIVO}; font-weight: 700;"
            elif acima_ms:
                return f"color: {AZUL_PRINCIPAL}; font-weight: 700;"
            else:
                return f"color: {COR_CRITICO}; font-weight: 700;"
        except Exception:
            if cor_padrao_area:
                return f"color: {cor_padrao_area}; font-weight: 600;"
            return "color: #9CA3AF;"

    def _cor_fundo_area(val, cor_area):
        try:
            if isinstance(val, (pd.Series, pd.DataFrame)):
                return ""
            if pd.isna(val):
                return ""
            return f"background-color: {_hex_rgba_safe(cor_area, 0.12)};"
        except Exception:
            return ""

    def _cor_fonte_tx(val):
        try:
            if isinstance(val, (pd.Series, pd.DataFrame)):
                return "color: #9CA3AF;"
            if pd.isna(val) or str(val) == "—":
                return "color: #9CA3AF;"
            num = float(str(val).replace("%", "").replace(",", "."))
            if tx_threshold_verde is not None and num >= tx_threshold_verde:
                return "color: #059669; font-weight: 700;"
            if tx_threshold_laranja is not None and num >= tx_threshold_laranja:
                return "color: #D97706; font-weight: 700;"
            if num < tx_threshold_vermelho:
                return "color: #DC2626; font-weight: 700;"
            return "color: inherit;"
        except Exception:
            return "color: #9CA3AF;"

    def _fundo_linha_tx(row):
        if not colorir_linha_tx:
            return ""
        try:
            tx = row.get(tx_col, pd.NA)
            if isinstance(tx, (pd.Series, pd.DataFrame)):
                return ""
            if pd.isna(tx) or str(tx) == "—":
                return ""
            num = float(str(tx).replace("%", "").replace(",", "."))
            if tx_threshold_verde is not None and num >= tx_threshold_verde:
                return "background-color: rgba(5, 150, 105, 0.05);"
            if tx_threshold_laranja is not None and num >= tx_threshold_laranja:
                return "background-color: rgba(217, 119, 6, 0.05);"
            if num < tx_threshold_vermelho:
                return "background-color: rgba(220, 38, 38, 0.05);"
            return ""
        except Exception:
            return ""

    # --- Estilo por linha (axis=1) — único método de estilização ---
    def _estilo_por_linha(row):
        idx = row.name
        raw_row = df_raw.loc[idx] if idx in df_raw.index else row
        styles = []
        fundo_tx = _fundo_linha_tx(raw_row)
        for col in df_display.columns:
            parts = []
            # Propriedades base
            parts.append("font-size: 13px;")
            parts.append("border-color: #E5E7EB;")
            # Fundo da linha por tx
            if fundo_tx:
                parts.append(fundo_tx)
            # Coluna escola
            if col == col_escola and col in df_display.columns:
                parts.append("font-weight: 600; color: #1E3A5F;")
                parts.append("text-align: left; padding-left: 12px;")
            # Tx Part. Efetiva
            if col == tx_col and col in df_display.columns:
                parts.append(_cor_fonte_tx(raw_row.get(col)))
                parts.append("text-align: center;")
            # Áreas de conhecimento
            for col_key, col_nome in area_labels.items():
                if col == col_nome and col in df_display.columns:
                    cor_area = cores_area.get(col_key, "#7B8794")
                    val = raw_row.get(col)
                    parts.append(_cor_fundo_area(val, cor_area))
                    ms = medias_ms.get(col_key)
                    br = medias_br.get(col_key)
                    parts.append(_cor_fonte_media(val, ms, br, cor_area))
            # Centralizar números
            if col in (concluintes_col, tx_col) or col in colunas_area:
                parts.append("text-align: center;")
            # Colunas especiais
            if col == "TURNOS":
                parts.append("text-align: center; font-size: 11px; color: #4B5563;")
            if col in ("Município", "Coordenadoria Regional"):
                parts.append("text-align: left; padding-left: 12px;")
            styles.append("; ".join(filter(None, parts)) if parts else "")
        return styles

    styled = df_display.style.apply(_estilo_por_linha, axis=1)

    # Cabeçalho
    header_styles = [
        {"selector": "th", "props": [
            ("background-color", "#1E3A5F"),
            ("color", "#FFFFFF"),
            ("font-weight", "700"),
            ("font-size", "11px"),
            ("text-align", "center"),
            ("padding", "10px 8px"),
            ("border-bottom", "2px solid #1E40AF"),
            ("white-space", "nowrap"),
        ]},
        {"selector": "td", "props": [
            ("border-bottom", "1px solid #E5E7EB"),
            ("padding", "8px 10px"),
            ("vertical-align", "middle"),
        ]},
        {"selector": "tr:hover", "props": [
            ("background-color", "#E0F2FE !important"),
            ("box-shadow", "inset 0 0 0 2px #1E40AF"),
        ]},
        {"selector": "tr:nth-child(even)", "props": [
            ("background-color", "#F9FAFB"),
        ]},
    ]
    styled = styled.set_table_styles(header_styles)

    # CSS customizado para cabeçalhos coloridos
    css_cabecalho = ""
    for col_key, col_nome in area_labels.items():
        if col_nome not in df_display.columns:
            continue
        cor_area = cores_area.get(col_key, "#7B8794")
        try:
            idx = df_display.columns.get_loc(col_nome)
            if isinstance(idx, slice):
                idx = idx.start if idx.start is not None else 0
            elif isinstance(idx, list):
                idx = idx[0] if idx else 0
            css_idx = idx + 1
            css_cabecalho += f"""
            .tabela-escolas thead th:nth-child({css_idx}) {{
                background-color: {cor_area} !important;
                color: #FFFFFF !important;
            }}
            """
        except (KeyError, TypeError):
            continue

    css_hover = """
    .tabela-escolas tbody tr:hover {
        background-color: #E0F2FE !important;
        box-shadow: inset 0 0 0 2px #1E40AF !important;
        cursor: pointer;
    }
    .tabela-escolas tbody tr:hover td {
        background-color: #E0F2FE !important;
    }
    """

    css_completo = css_cabecalho + css_hover
    if css_completo:
        styled = styled.set_table_attributes(f'style="border-collapse: collapse;" class="tabela-escolas"')

    return styled, css_completo
def _secao_detalhe_ano_desempenho(
    tabelas, ano_foco, df_est_ms,
    df_dist_est, df_dist_todos, deps_exibir, df_notas_individuais,
):
    """Camada de detalhe: histogramas por área + comparação entre dependências.

    Renderizada dentro de um ``st.expander`` (divulgação progressiva). Usa o ano
    da barra de filtros (``ano_foco``) como recorte; o restante vem dos agregados.
    """
    anos_presentes = sorted(df_dist_est["ano"].unique()) if not df_dist_est.empty else []
    if not anos_presentes:
        st.info("Nenhum ano disponível para análise por área.")
        return
    titulo_secao(
        "Histograma de distribuição de notas por área",
        "Contagem real de estudantes por faixa: NA (ausente), Zero, >0–50, 50–100, …, 950–1000. "
        "População: concluintes estaduais presentes nos 2 dias e não eliminados (legenda abaixo)."
    )
    _anos_presentes_int = [int(a) for a in anos_presentes]
    ano_sel = ano_foco if ano_foco in _anos_presentes_int else max(_anos_presentes_int)
    pop_ano = _populacao_estadual_ano(tabelas, ano_sel)

    refs_ano = medias_referencia_por_ano(tabelas, ano_sel)
    if not refs_ano:
        df_est_ano = df_est_ms[df_est_ms["NU_ANO"] == ano_sel]
        for key in list(AREAS.keys()):
            ms = float(df_est_ano[key].mean()) if not df_est_ano.empty and key in df_est_ano.columns else np.nan
            br = media_nacional_ponderada(tabelas, ano_sel, key, "Estadual")
            refs_ano[key] = {"ms": ms, "br": br}

    bins_por_area: dict[str, pd.DataFrame] = {}
    fontes_por_area: dict[str, str] = {}
    for key in list(AREAS.keys()):
        bins, fonte = histograma_area_ano(
            tabelas, ano_sel, key,
            dependencia="Estadual",
            df_notas_individuais=df_notas_individuais,
        )
        if not bins.empty:
            bins_por_area[key] = bins
            fontes_por_area[key] = fonte

    n_histograma = None
    if bins_por_area:
        totais = {k: int(v["count"].sum()) for k, v in bins_por_area.items() if not v.empty}
        if totais:
            n_histograma = next(iter(totais.values()))
    st.markdown(
        _legenda_populacoes_secao_html(
            ano_sel, pop_ano, n_histograma=n_histograma, contexto="histogramas",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        _legenda_inline([
            "<b>Cores (faixa de nota):</b>",
            f"<span style='color:{COR_HIST_NA};font-size:16px;'>■</span> NA (nota ausente)",
            f"<span style='color:{COR_POSITIVO};font-size:16px;'>■</span> Faixa ≥ média nacional (BR)",
            f"<span style='color:{AZUL_PRINCIPAL};font-size:16px;'>■</span> Faixa ≥ média MS e &lt; BR",
            f"<span style='color:{COR_CRITICO};font-size:16px;'>■</span> Faixa &lt; média MS",
            "| MS ━ BR · · ·",
        ]),
        unsafe_allow_html=True,
    )

    if not bins_por_area:
        st.info(
            f"Sem histogramas reais para {ano_sel}. "
            "Regenere agregados com: `python gerar_dados_agregados.py` "
            "(gera histograma_ms.parquet) ou disponibilize o microdado ENEM."
        )
    else:
        fontes_unicas = sorted(set(fontes_por_area.values()))
        st.caption(
            "Fonte: " + "; ".join(fontes_unicas)
            + ". Faixas: NA; Zero; >0–50; 50–100; …; 950–1000. "
            "Referências MS/BR: referencias.parquet (rede estadual)."
        )
        _chart(_fig_histogramas_multiarea_coloridos(
            bins_por_area, refs_ano, ano_sel,
        ))

    # Comparação entre dependências — mesmo ano dos histogramas
    titulo_secao(
        "Comparação entre dependências — todas as áreas",
        f"Distribuição das notas por área e dependência administrativa em {ano_sel}."
    )
    st.markdown(
        _legenda_populacoes_secao_html(
            ano_sel, pop_ano, n_histograma=n_histograma, contexto="dependencias",
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        f"Ano **{ano_sel}**: boxplots por dependência administrativa em MS. "
        "Cada caixa usa a população «Presentes 2 dias, sem eliminados» da respectiva dependência. "
        "Passe o mouse sobre uma caixa para ver Máx, Q3, mediana, Q1, Mín e n (nota &gt; 0). "
        "Média Geral exige as 5 notas válidas."
    )
    df_ult_dist = df_dist_todos[df_dist_todos["ano"] == ano_sel]

    fig_box_areas = go.Figure()
    for dep in deps_exibir:
        rows_dep = df_ult_dist[df_ult_dist["dependencia"] == dep]
        if rows_dep.empty:
            continue
        row_dep = rows_dep.iloc[0]
        xs_dep: list[str] = []
        stats_dep: list[dict] = []
        for col, nome in AREAS.items():
            stats = stats_box_quantis(row_dep, col)
            if stats is None:
                continue
            xs_dep.append(nome)
            stats_dep.append(stats)
        _add_box_series(
            fig_box_areas, name=dep, color=CORES_DEP[dep],
            x_vals=xs_dep, stats_list=stats_dep,
            legendgroup=dep, showlegend=True,
        )
    _chart(_finalizar_boxplot(
        fig_box_areas,
        f"Distribuição das notas por área e dependência — {ano_sel}",
        n_legend=len(deps_exibir),
    ))

