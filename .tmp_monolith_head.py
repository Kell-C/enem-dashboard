"""
==========================================================================
PAINEL ANALÍTICO DO ENEM 2019-2024 — ESCOLAS ESTADUAIS
Versão 15.0 — Dados agregados (parquet local ou Supabase), pronto para
publicação no Streamlit Community Cloud. Mantém layout e funcionalidades
do v14_26mai14h33.
==========================================================================
"""

# Bump ao alterar layout/hover do hub — força refresh de widgets Plotly.
HUB_BUILD_ID = "20260607j"

import base64
import re as _re
import html as _html
import os
from os.path import exists
import warnings
from typing import Optional

import unicodedata
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from viz.chart_layout import (
    CHART_H_BOX,
    CHART_H_BOX_WIDE,
    CHART_H_EVOLUCAO,
    CHART_H_HIST,
    CHART_H_HIST_GRID,
    CHART_H_HIST_ROW,
    CHART_H_HUB,
    CHART_H_HUB_DELTA_ROW,
    CHART_H_HUB_EVOL,
    CHART_H_HUB_RANK,
    PLOTLY_HUB_CONFIG,
    legenda_hub_interna,
    margem_hub,
    CHART_H_PARTICIPACAO,
    CHART_H_RANKING,
    CHART_H_STANDARD,
    hover_padrao,
    legenda_inferior,
    margem_detalhe,
    texto_hover_box,
)

from dados_agregados_loader import (
    carregar_notas_individuais,
    carregar_todas_tabelas,
    filtrar_distribuicao,
    filtrar_notas_individuais,
    get_data_source,
    get_pasta_agregados,
    histograma_area_ano,
    presentes_filt_estadual_ano,
    inscritos_estadual_ms,
    inscritos_por_escola_2024,
    linha_distribuicao,
    linha_escola_2024,
    media_ms_area_ano,
    medias_referencia_por_ano,
    medias_br_serie_por_area,
    media_nacional_ponderada,
    serie_media_nacional_dep,
    anos_com_desempenho_uf,
    tabela_ranking_uf,
    notas_area,
    reconstruir_bases_nacionais,
    reconstruir_escolas_2024_ms,
    participacao_ms_por_ano,
    reconstruir_ms_enriquecido,
    reconstruir_participacao_ms,
    stats_box_quantis,
    anos_com_notas_individuais,
    tem_notas_individuais_ano,
    verificar_dados_disponiveis,
)

try:
    from dados_agregados_loader import (
        filtrar_participacao_cre,
        filtrar_participacao_municipio,
    )
except ImportError:
    def filtrar_participacao_cre(
        tabelas: dict,
        *,
        anos: list[int] | None = None,
        dependencia: str | None = None,
    ) -> pd.DataFrame:
        df = tabelas.get("participacao_cre", pd.DataFrame())
        if df.empty:
            return df
        out = df.copy()
        if anos:
            out = out[out["ano"].isin(anos)]
        if dependencia:
            out = out[out["dependencia"] == dependencia]
        return out

    def filtrar_participacao_municipio(
        tabelas: dict,
        *,
        anos: list[int] | None = None,
        dependencia: str | None = None,
    ) -> pd.DataFrame:
        df = tabelas.get("municipios", pd.DataFrame())
        if df.empty:
            return df
        out = df.copy()
        if anos:
            out = out[out["ano"].isin(anos)]
        if dependencia:
            out = out[out["dependencia"] == dependencia]
        return out

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Painel ENEM MS",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_DIR_DASHBOARD = os.path.dirname(os.path.abspath(__file__))
_LOGO_MS_CANDIDATES = (
    os.path.join(_DIR_DASHBOARD, "assets", "logo_governo_ms.png"),
    os.path.join(_DIR_DASHBOARD, "assets", "logo_governo_ms.svg"),
    os.path.join(_DIR_DASHBOARD, "assets", "logo_sed_ms.svg"),
    os.path.join(_DIR_DASHBOARD, "assets", "logo_sed_ms.png"),
)

# CSS customizado para destacar os filtros (selectbox, multiselect, slider)
st.markdown("""
<style>
/* Container do selectbox */
div[data-testid="stSelectbox"] {
    background: linear-gradient(135deg, rgba(27, 127, 214, 0.08), rgba(27, 127, 214, 0.03));
    border: 1px solid rgba(10, 77, 140, 0.18);
    border-radius: 10px;
    padding: 8px 12px 4px 12px;
    margin-bottom: 12px;
}
/* Label do selectbox */
div[data-testid="stSelectbox"] label {
    color: #0A4D8C !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600 !important;
}
/* Container do multiselect */
div[data-testid="stMultiSelect"] {
    background: linear-gradient(135deg, rgba(27, 127, 214, 0.08), rgba(27, 127, 214, 0.03));
    border: 1px solid rgba(10, 77, 140, 0.18);
    border-radius: 10px;
    padding: 8px 12px 4px 12px;
    margin-bottom: 12px;
}
/* Label do multiselect */
div[data-testid="stMultiSelect"] label {
    color: #0A4D8C !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600 !important;
}
/* Container do slider */
div[data-testid="stSlider"] {
    background: linear-gradient(135deg, rgba(27, 127, 214, 0.08), rgba(27, 127, 214, 0.03));
    border: 1px solid rgba(10, 77, 140, 0.18);
    border-radius: 10px;
    padding: 8px 12px 4px 12px;
    margin-bottom: 12px;
}
/* Label do slider */
div[data-testid="stSlider"] label {
    color: #0A4D8C !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# FONTE DE DADOS — agregados (gerar_dados_agregados.py)
# DATA_SOURCE=local  → parquet em PASTA_AGREGADOS
# DATA_SOURCE=supabase → PostgreSQL (secrets ou env vars)
# ------------------------------------------------------------
PASTA_AGREGADOS = get_pasta_agregados()

# Cadastro CRE (opcional — enriquece nomes quando disponível localmente)
from cres_loader import (
    carregar_cres_escolas,
    carregar_mapa_municipio_cre as _carregar_mapa_municipio_cre,
    construir_mapa_cre_completo,
    nome_cre_curto,
    resolve_arquivo_cres,
)

ARQUIVO_CRES = os.getenv("ARQUIVO_CRES") or resolve_arquivo_cres() or os.path.join(
    os.path.dirname(__file__), "cres.xlsx"
)

# ------------------------------------------------------------
# DADOS DE CONCLUINTES (3º ano) — estrutura para integração futura
# ------------------------------------------------------------
# Fonte: planilha Google Sheets com dados de estudantes do 3º ano
# da rede estadual de MS (2019-2024).
# Quando os dados estiverem disponíveis, atualize o caminho abaixo
# ou descomente a função carregar_concluintes() e ajuste conforme
# o formato real da planilha/arquivo local.
ARQUIVO_CONCLUINTES: Optional[str] = os.getenv(
    "ARQUIVO_CONCLUINTES",
    os.path.join(os.path.dirname(__file__), "data", "Concluintes EM 2019 a 2024.xlsx"),
)


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


def carregar_concluintes_cre() -> pd.DataFrame:
    """Carrega dados de concluintes agregados por CRE e ano."""
    from concluintes_loader import carregar_concluintes_cre as _carregar_concluintes_cre

    arquivo = os.getenv("ARQUIVO_CONCLUINTES", ARQUIVO_CONCLUINTES)
    if not arquivo or not os.path.exists(arquivo):
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])

    try:
        return _carregar_concluintes_cre(arquivo=arquivo, arquivo_cres=ARQUIVO_CRES)
    except Exception as e:
        st.warning(f"Não foi possível carregar dados de concluintes por CRE: {e}")
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])


# ------------------------------------------------------------
# IDENTIDADE INSTITUCIONAL — SED/MS (tema claro único, profissional)
# ------------------------------------------------------------
# Decisão: tema CLARO institucional fixo. Eliminamos a detecção via
# st.get_option("theme.base") porque a API é instável em modo headless e
# não reflete a preferência efetiva do navegador. Para ambientes que
# exigem dark, usar .streamlit/config.toml.
TEMA_BASE = "light"

# Paleta institucional baseada em azul SED/MS, com tokens semânticos.
TEMA = {
    # MS Grid Executivo — contraste reforçado (People Analytics + Opsview)
    "bg_app":          "#DCE3EC",
    "bg_card":         "#FFFFFF",
    "bg_sidebar":      "#F7FAFD",
    "bg_subtle":       "#E8EDF3",
    "insight_bg":      "#F1F5F9",
    # Texto
    "texto":           "#0F172A",
    "texto_secundario": "#334155",
    "texto_muted":     "#475569",
    "texto_inv":       "#FFFFFF",   # sobre superfícies escuras
    # Bordas e linhas
    "borda":           "#B8C4D4",
    "borda_sutil":     "#CBD5E1",
    "linha_eixo":      "#94A3B8",
    "grid_sutil":      "#F1F5F9",
    # Plotly
    "plot_template":   "plotly_white",
    "plot_paper":      "rgba(0,0,0,0)",
    "plot_plot":       "#FFFFFF",
}

# ------------------------------------------------------------
# Paleta de cores (semântica + identidade visual MS)
# ------------------------------------------------------------
# Paleta SED/MS — guia ENEM 2026 (azul vibrante, verde e dourado do brasão)
AZUL_SED = "#1B7FD6"
AZUL_PRINCIPAL = "#0A4D8C"
AZUL_CLARO = "#3BA4E8"
AZUL_ACCENT = "#5CB8F0"
AZUL_ESCURO = "#053B71"
VERDE_MS = "#2EAD6E"
LARANJA_DESTAQUE = "#F07A28"
DOURADO_MS = "#F2C230"

# Semáforo (status)
COR_POSITIVO = VERDE_MS
COR_ATENCAO = "#E8A317"
COR_CRITICO = "#D6453D"
COR_NEGATIVO = "#DC2626"  # vermelho forte (destaque negativo)
COR_NEUTRO = "#5C6B7E"
COR_TEXTO_DENTRO_BARRA = "#0A4A32"
ALTURA_HUB_MS = CHART_H_HUB
ALTURA_HUB_RANK = CHART_H_HUB_RANK
ALTURA_HUB_EVOL = CHART_H_HUB_EVOL
ALTURA_HUB_DELTA_LINHA = CHART_H_HUB_DELTA_ROW
ALTURA_HUB_TERR = CHART_H_HUB
ALTURA_HUB_TERR_MAX = CHART_H_HUB
HUB_COL_LAYOUT = [1, 1, 1]
HUB_GRID_ROWS = 3
# Margens hub: base para legenda abaixo do eixo X (ver _margem_hub)
HUB_CHART_MARGIN = dict(t=14, b=54, r=12, l=40)
HUB_CHART_MARGIN_TOPO = dict(t=30, b=54, r=12, l=40)
HUB_CHART_MARGIN_RANK = dict(t=10, b=36, r=12, l=68)
# Tipografia — escala dashboard executivo (base 16px; mínimo legível 12px)
FONT_HOVER = 13
FONT_CHART = 13
FONT_AXIS = 12
FONT_LEGEND = 12
FONT_HUB_DATA = 11
FONT_HUB_DELTA = 10
FONT_HUB_AXIS = 11
FONT_HUB_LEGEND = 11
FONT_HUB_LEGEND_WIDE = 10

# Dependências administrativas
CORES_DEP = {
    "Estadual":  AZUL_PRINCIPAL,
    "Federal":   "#9C2A26",
    "Municipal": DOURADO_MS,
    "Privada":   "#6B4A9F",
}
# Áreas de conhecimento (paleta categórica usando tokens institucionais)
CORES_AREAS = {
    # Média Geral — cinza grafite (composto/agregado)
    "MEDIA_GERAL":     COR_NEUTRO,
    "NU_NOTA_CN":      COR_POSITIVO,       # Ciências da Natureza — verde
    "NU_NOTA_CH":      LARANJA_DESTAQUE,   # Ciências Humanas — laranja
    # Linguagens e Códigos — azul institucional
    "NU_NOTA_LC":      AZUL_PRINCIPAL,
    "NU_NOTA_MT":      COR_CRITICO,        # Matemática — vermelho institucional
    "NU_NOTA_REDACAO": DOURADO_MS,         # Redação — dourado
}
COR_BRASIL = "#7B8794"   # neutro nacional (referência contextual)
COR_BAR_NEUTRA = "#D1D9E2"   # barras de fundo / referência
HIST_BIN_NA = -1.0  # sentinel alinhado a gerar_dados_agregados.HIST_BIN_NA
COR_HIST_NA = "#9aa5b4"

# Aliases legados (manter compatibilidade com restante do código)
VERDE = COR_POSITIVO
CINZA_TEXTO = TEMA["texto"]
CINZA_CLARO = TEMA["bg_subtle"]

# Nomes curtos para gráficos e completos para textos
AREAS = {
    "MEDIA_GERAL": "Média Geral",
    "NU_NOTA_CN": "CN",
    "NU_NOTA_CH": "CH",
    "NU_NOTA_LC": "LC",
    "NU_NOTA_MT": "Mat.",
    "NU_NOTA_REDACAO": "Redação",
}
AREAS_COMPLETO = {
    "MEDIA_GERAL": "Média Geral",
    "NU_NOTA_CN": "CN",
    "NU_NOTA_CH": "CH",
    "NU_NOTA_LC": "LC",
    "NU_NOTA_MT": "Mat.",
    "NU_NOTA_REDACAO": "Redação",
}
COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH",
    "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
DEP_MAP = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
ORDEM_DEP = ["Estadual", "Federal", "Municipal", "Privada"]
ANOS_DISPONIVEIS = list(range(2019, 2025))
NOTA_MIN, NOTA_MAX = 0, 1000

COLS_BASE = [
    "NU_ANO",
    "SG_UF_ESC",
    "SG_UF_PROVA",
    "CO_ESCOLA",
    "NO_MUNICIPIO_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
    "TP_ST_CONCLUSAO",
    "IN_TREINEIRO",
    "CATEGORIA_PARTICIPACAO",
] + COLS_NOTAS

# ============================================================
# CSS INSTITUCIONAL — tema claro fixo, alto contraste, governamental
# ============================================================
st.markdown(
    f"""
    <style>
      /* Fontes institucionais: Plus Jakarta Sans (display) + Source Sans 3 (corpo) */
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap');

      :root {{
        --ms-navy: {AZUL_ESCURO};
        --ms-sed: {AZUL_SED};
        --ms-azul-2: {AZUL_PRINCIPAL};
        --ms-azul-3: {AZUL_CLARO};
        --ms-verde: {VERDE_MS};
        --ms-laranja: {LARANJA_DESTAQUE};
        --ms-dourado: {DOURADO_MS};
        --ms-surface: {TEMA['bg_card']};
        --ms-tint: {TEMA['insight_bg']};
        --texto:     {TEMA['texto']};
        --texto-sec: {TEMA['texto_secundario']};
        --texto-mut: {TEMA['texto_muted']};
        --bg-app:    {TEMA['bg_app']};
        --bg-card:   {TEMA['bg_card']};
        --borda:     {TEMA['borda']};
      }}

      html, body, [class*="css"], .stApp, .stMarkdown, .stMarkdown p, .stMarkdown li {{
        font-family: 'Source Sans 3', system-ui, -apple-system, Segoe UI, sans-serif;
        color: {TEMA['texto']} !important;
      }}

      h1, h2, h3, h4, h5, h6,
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {{
        font-family: 'Plus Jakarta Sans', 'Source Sans 3', sans-serif;
        color: {TEMA['texto']} !important;
        letter-spacing: -0.01em;
        font-weight: 700;
      }}

      /* Corpo de texto: mínimo 16px e entrelinha confortável (legibilidade/AA) */
      .stMarkdown p, .stMarkdown li {{
        font-size: 1rem;
        line-height: 1.55;
      }}

      .stApp {{
        background: {TEMA['bg_app']} !important;
        color: {TEMA['texto']} !important;
        margin-top: 0 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        height: auto !important;
        min-height: 100vh;
      }}
      /* Faixa decorativa / reserva de topo do Streamlit */
      [data-testid="stDecoration"],
      [data-testid="stStatusWidget"] {{
          display: none !important;
          height: 0 !important;
          min-height: 0 !important;
      }}
      [data-testid="stMain"] {{
          padding-top: 1 !important;
          margin-top: 1 !important;
      }}
      [data-testid="stSidebar"],
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="collapsedControl"] {{
          display: none !important;
      }}
      .main .block-container {{
          padding: 0 0 0.25rem 0 !important;
          max-width: 100% !important;
      }}
      .appview-container .main .block-container {{
          padding-top: 0 !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
      }}
      /* Streamlit reserva padding-top em section.main para o header fixo — zerar */
      section.main,
      .stApp [data-testid="stAppViewContainer"] > section.main {{
          padding-top: 0 !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
          margin-top: 0 !important;
      }}
      .stApp [data-testid="stAppViewContainer"] {{
          padding-top: 0 !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
          margin-top: 0 !important;
          overflow-x: hidden !important;
          overflow-y: auto !important;
          height: auto !important;
          min-height: 100vh;
      }}
      .stApp [data-testid="stAppViewContainer"] > .main {{
          padding-top: 0 !important;
          overflow: visible !important;
          height: auto !important;
          min-height: 100vh;
      }}
      section.main {{
          overflow: visible !important;
          height: auto !important;
      }}
      section.main > div {{
          padding-left: 0 !important;
          padding-right: 0 !important;
          padding-top: 0 !important;
          margin-top: 0 !important;
      }}
      [data-testid="stMainBlockContainer"] {{
          padding-top: 0 !important;
          padding-left: 0.35rem !important;
          padding-right: 0.35rem !important;
          padding-bottom: 2.5rem !important;
          max-width: 100% !important;
          margin-top: 0 !important;
          overflow: visible !important;
          height: auto !important;
      }}
      [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] {{
          gap: 0.2rem !important;
          padding-top: 0 !important;
          margin-top: 0 !important;
      }}
      [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] > div {{
          padding-top: 0 !important;
          margin-top: 0 !important;
      }}
      /* Header nativo: colapsar altura; menu permanece clicável no canto */
      header[data-testid="stHeader"] {{
          background: transparent !important;
          height: 0 !important;
          min-height: 0 !important;
          max-height: 0 !important;
          overflow: visible;
          visibility: hidden;
          pointer-events: none;
          border: none !important;
          box-shadow: none !important;
      }}
      header[data-testid="stHeader"] [data-testid="stToolbar"],
      header[data-testid="stHeader"] [data-testid="stToolbarActions"] {{
          visibility: visible;
          pointer-events: auto;
      }}
      [data-testid="stToolbar"] {{
          position: fixed;
          top: 0.35rem;
          right: 0.5rem;
          z-index: 999;
      }}
      [data-testid="stVerticalBlockBorderWrapper"] {{
          gap: 0.1rem !important;
          padding-top: 0 !important;
      }}
      [data-testid="stElementContainer"] {{
          margin: 0 !important;
      }}
      div[data-testid="stMarkdownContainer"]:first-child {{
          margin-top: 0 !important;
          padding-top: 0 !important;
      }}
      [data-testid="column"] {{
          padding: 0 2px !important;
          overflow: visible !important;
      }}
      [data-testid="stHorizontalBlock"] {{
          overflow: visible !important;
          gap: 0.35rem !important;
      }}
      [data-testid="stVerticalBlock"] > div:first-child {{
          gap: 0.15rem;
      }}
      [data-testid="stVerticalBlock"] > div:first-child > div:first-child {{
          margin-top: 0 !important;
          padding-top: 0 !important;
      }}

      /* ── Cabeçalho principal — colado ao topo, marca em destaque ── */
      .cab-claro {{
          background: linear-gradient(135deg, {TEMA['bg_card']} 0%, #F1F5F9 100%);
          border: 1px solid {TEMA['borda']};
          border-top: none;
          border-left: none;
          border-right: none;
          border-radius: 0 0 12px 12px;
          padding: 8px 14px 9px 14px;
          margin: 0 -0.35rem 4px -0.35rem;
          box-shadow: 0 3px 14px rgba(15, 23, 42, 0.08);
          border-bottom: 3px solid {DOURADO_MS};
          position: relative;
          z-index: 2;
      }}
      .cab-claro::before {{
          content: "";
          position: absolute;
          left: 0; top: 0; bottom: 0;
          width: 6px;
          background: linear-gradient(180deg, {AZUL_SED} 0%, {AZUL_PRINCIPAL} 100%);
          border-radius: 0 2px 2px 0;
      }}
      .cab-claro--com-kpis {{
          padding-right: 2.5rem;
      }}
      .cab-claro-row {{
          display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
          padding-left: 10px;
      }}
      .cab-claro--com-kpis .cab-claro-row {{
          flex-wrap: nowrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding-left: 10px;
          padding-right: 4px;
          min-height: 62px;
      }}
      .cab-claro-brand {{
          display: flex;
          align-items: center;
          gap: 16px;
          flex: 0 0 auto;
          min-width: 0;
          max-width: 42%;
      }}
      .cab-claro--com-kpis .cab-claro-brand {{
          max-width: min(360px, 34vw);
          flex-shrink: 0;
      }}
      .cab-claro-kpis {{
          display: flex;
          flex-wrap: wrap;
          align-items: stretch;
          justify-content: flex-end;
          gap: 6px;
          flex: 1 1 auto;
          min-width: 0;
      }}
      .cab-claro-kpis .kpi-claro {{
          flex: 0 0 auto;
          width: max-content;
          min-width: max-content;
          max-width: none;
          padding: 4px 9px 3px 9px;
          border-radius: 6px;
      }}
      .cab-claro-kpis .kpi-claro-val {{
          font-size: 1.05rem;
          line-height: 1.05;
      }}
      .cab-claro-kpis .kpi-claro-lbl {{
          font-size: 0.6875rem;
          letter-spacing: 0.05em;
          white-space: normal;
          line-height: 1.2;
      }}
      .cab-claro-kpis .kpi-claro-sub {{
          font-size: 0.6875rem;
          max-width: none;
          overflow: visible;
          text-overflow: clip;
          white-space: normal;
          line-height: 1.3;
      }}
      .cab-claro-kpis .kpi-delta-br {{
          min-width: max-content;
      }}
      .cab-claro-kpis .kpi-funil-inline {{
          min-width: 248px;
          max-width: none;
          flex: 1 1 248px;
          padding: 4px 9px 3px 9px;
      }}
      .cab-claro-kpis .kpi-funil-inline .fk-line {{
          grid-template-columns: minmax(7.25rem, auto) 4.2rem minmax(52px, 1fr);
          gap: 4px;
      }}
      .cab-claro-kpis .kpi-funil-inline .fk-l {{
          font-size: 0.625rem;
          white-space: nowrap;
      }}
      @media (max-width: 1100px) {{
          .cab-claro--com-kpis .cab-claro-row {{
              flex-wrap: wrap;
          }}
          .cab-claro-brand, .cab-claro--com-kpis .cab-claro-brand {{
              max-width: 100%;
              flex: 1 1 100%;
          }}
          .cab-claro-kpis {{
              justify-content: flex-start;
              flex: 1 1 100%;
          }}
      }}
      .cab-claro-logo {{
          height: 64px; width: auto; max-width: min(300px, 38vw);
          object-fit: contain; flex-shrink: 0;
          filter: drop-shadow(0 1px 2px rgba(15, 23, 42, 0.06));
      }}
      .cab-claro-brand .cab-claro-text {{
          flex: 1 1 auto;
          min-width: 0;
      }}
      .cab-claro-text h1 {{
          margin: 0; padding: 0;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 1.55rem; font-weight: 800;
          color: {AZUL_ESCURO} !important;
          letter-spacing: -0.03em; line-height: 1.1;
      }}
      .cab-claro-text p {{
          margin: 4px 0 0 0; padding: 0;
          font-size: 0.9rem; line-height: 1.35;
          color: {TEMA['texto_secundario']} !important;
          font-weight: 600;
      }}
      .cab-claro--com-kpis .cab-claro-logo {{
          height: 58px;
          max-width: min(280px, 32vw);
      }}
      .cab-claro--com-kpis .cab-claro-text h1 {{
          font-size: 1.42rem;
          letter-spacing: -0.028em;
      }}
      .cab-claro--com-kpis .cab-claro-text p {{
          font-size: 0.84rem;
          margin-top: 3px;
          font-weight: 600;
      }}

      /* População de referência — faixa compacta abaixo do cabeçalho */
      .ref-pop-bar {{
          display: flex;
          flex-wrap: wrap;
          align-items: baseline;
          gap: 5px 10px;
          padding: 7px 12px 8px 14px;
          margin: 14px 0 14px 0;
          background: linear-gradient(135deg, #F8FAFC 0%, {TEMA['insight_bg']} 100%);
          border: 1px solid {TEMA['borda']};
          border-left: 4px solid {AZUL_SED};
          border-radius: 8px;
          font-size: 0.875rem;
          line-height: 1.5;
          color: {TEMA['texto_secundario']} !important;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
      }}
      .ref-pop-bar .ref-pop-tag {{
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-weight: 800;
          font-size: 0.8125rem;
          text-transform: uppercase;
          letter-spacing: 0.07em;
          color: {AZUL_ESCURO} !important;
          white-space: nowrap;
          background: rgba(0, 63, 127, 0.08);
          padding: 2px 8px;
          border-radius: 4px;
      }}
      .ref-pop-bar .ref-pop-item {{
          color: {TEMA['texto']} !important;
          font-weight: 500;
      }}
      .ref-pop-bar .ref-pop-item strong {{
          color: {AZUL_ESCURO} !important;
          font-weight: 700;
      }}
      .ref-pop-bar .ref-pop-sep {{
          color: {TEMA['texto_muted']} !important;
          user-select: none;
      }}
      .ref-pop-bar code {{
          font-size: 0.75rem;
          background: rgba(46, 173, 110, 0.1);
          color: {COR_TEXTO_DENTRO_BARRA} !important;
          padding: 0 4px;
          border-radius: 3px;
      }}

      /* KPIs — largura conforme conteúdo */
      .kpi-strip-claro {{
          display: flex;
          flex-wrap: wrap;
          align-items: stretch;
          gap: 4px;
          margin-bottom: 3px;
      }}
      .kpi-strip-claro .kpi-claro {{
          flex: 0 0 auto;
          width: max-content;
          max-width: 100%;
      }}
      .kpi-strip-tight .kpi-claro {{
          padding: 4px 8px 3px 8px;
          border-radius: 6px;
      }}
      .kpi-funil-row {{
          display: flex;
          flex-wrap: wrap;
          align-items: stretch;
          gap: 5px;
          margin-bottom: 4px;
      }}
      .kpi-funil-row .kpi-claro {{
          flex: 0 0 auto;
          width: max-content;
      }}
      .kpi-funil-inline {{
          min-width: 248px;
          max-width: none;
          border-top-color: {AZUL_PRINCIPAL};
      }}
      .kpi-funil-inline .fk-lines {{
          margin-top: 2px;
          display: flex;
          flex-direction: column;
          gap: 2px;
      }}
      .kpi-funil-inline .fk-line {{
          display: grid;
          grid-template-columns: minmax(7.25rem, auto) 4.2rem minmax(52px, 1fr);
          align-items: center;
          gap: 4px;
          line-height: 1;
      }}
      .kpi-funil-inline .fk-l {{
          font-size: 0.6875rem;
          font-weight: 600;
          color: {TEMA['texto_secundario']} !important;
          white-space: nowrap;
      }}
      .kpi-funil-inline .fk-n {{
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 0.75rem;
          font-weight: 800;
          color: {AZUL_ESCURO} !important;
          text-align: right;
          font-variant-numeric: tabular-nums;
      }}
      .kpi-funil-inline .fk-track {{
          position: relative;
          height: 12px;
          background: {TEMA['bg_subtle']};
          border-radius: 2px;
          overflow: hidden;
      }}
      .kpi-funil-inline .fk-fill {{
          position: absolute;
          left: 0; top: 0; bottom: 0;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          padding-right: 3px;
          border-radius: 2px;
          min-width: 2px;
      }}
      .kpi-funil-inline .fk-fill.azul {{ background: {AZUL_SED}; }}
      .kpi-funil-inline .fk-fill.laranja {{ background: {LARANJA_DESTAQUE}; }}
      .kpi-funil-inline .fk-fill.verde {{ background: {VERDE_MS}; }}
      .kpi-funil-inline .fk-pct {{
          font-size: 0.6875rem;
          font-weight: 700;
          color: #FFFFFF !important;
          line-height: 1;
          white-space: nowrap;
      }}
      .kpi-funil-inline .fk-pct-out {{
          position: absolute;
          right: 3px;
          top: 50%;
          transform: translateY(-50%);
          font-size: 0.6875rem;
          font-weight: 700;
          color: {TEMA['texto_secundario']} !important;
      }}
      .hub-col-graficos {{
          display: flex;
          flex-direction: column;
          gap: 4px;
      }}
      .funil-estreito.widget-card .widget-head {{
          font-size: 0.5rem;
          padding: 4px 6px;
          letter-spacing: 0.05em;
      }}
      .funil-estreito .widget-body {{
          padding: 4px 6px 5px 6px;
      }}
      .funil-estreito .funil-v-row {{
          margin-bottom: 3px;
      }}
      .funil-estreito .fv-top {{
          gap: 4px;
      }}
      .funil-estreito .fv-lbl {{
          font-size: 0.58rem !important;
          line-height: 1.15;
      }}
      .funil-estreito .fv-val {{
          font-size: 0.78rem !important;
      }}
      .funil-estreito .fv-tx {{
          font-size: 0.56rem !important;
          margin: 0 0 2px 0;
      }}
      .funil-estreito .fv-bar {{
          height: 4px;
      }}
      .kpi-claro {{
          background: {TEMA['bg_card']};
          border: 1px solid {TEMA['borda']};
          border-radius: 6px;
          padding: 5px 10px 4px 10px;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
          border-top: 2px solid {AZUL_SED};
      }}
      .kpi-claro-lbl {{
          display: block; font-size: 0.75rem; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.06em;
          color: {TEMA['texto_muted']} !important;
          white-space: nowrap;
      }}
      .kpi-claro-val {{
          display: block; margin-top: 1px;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 1.22rem; font-weight: 800;
          color: {AZUL_ESCURO} !important;
          letter-spacing: -0.03em; line-height: 1.05;
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
      }}
      .kpi-claro-sub {{
          display: block; margin-top: 1px;
          font-size: 0.8125rem;
          color: {TEMA['texto_secundario']} !important;
          white-space: nowrap;
      }}
      .kpi-claro.positivo {{ border-top-color: {COR_POSITIVO}; }}
      .kpi-claro.positivo .kpi-claro-val {{ color: {COR_POSITIVO} !important; }}
      .kpi-claro.atencao  {{ border-top-color: {COR_ATENCAO}; }}
      .kpi-claro.atencao .kpi-claro-val  {{ color: {COR_ATENCAO} !important; }}
      .kpi-claro.critico  {{ border-top-color: {COR_CRITICO}; }}
      .kpi-claro.critico .kpi-claro-val  {{ color: {COR_CRITICO} !important; }}

      /* Widget card — faixa cinza no topo (Opsview) */
      .widget-card {{
          background: {TEMA['bg_card']};
          border: 1px solid {TEMA['borda']};
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
          height: 100%;
      }}
      .widget-head {{
          background: linear-gradient(135deg, {AZUL_ESCURO} 0%, {AZUL_PRINCIPAL} 100%);
          padding: 5px 8px;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 0.72rem; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.03em;
          color: #FFFFFF !important;
          border-bottom: 2px solid {DOURADO_MS};
          line-height: 1.35;
          white-space: normal;
          word-break: break-word;
          overflow: visible;
      }}
      .widget-body {{ padding: 6px 8px 8px 8px; }}
      .chart-legenda-delta.hub-mini {{
          margin: 0; padding: 2px 6px 4px 6px;
          font-size: 0.75rem; line-height: 1.3;
          color: {TEMA['texto_secundario']} !important;
          border-top: none;
      }}
      .widget-chart-zone {{
          margin-bottom: 4px;
          margin-top: 0;
          background: {TEMA['bg_card']};
          border: 1px solid {TEMA['borda']};
          border-radius: 6px;
          overflow: visible;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
          position: relative;
          z-index: 1;
      }}
      .widget-chart-body {{
          overflow: visible;
          border-radius: 0 0 6px 6px;
      }}
      .widget-chart-nota {{
          padding: 8px 12px 10px;
          font-family: 'Source Sans 3', sans-serif;
          font-size: 0.82rem;
          line-height: 1.5;
          color: {TEMA['texto_secundario']} !important;
          text-align: center;
          border-top: 1px solid {TEMA['borda']};
          background: {TEMA['bg_subtle']};
      }}
      .hub-legenda-linha .leg-traces,
      .widget-chart-nota .leg-traces {{
          display: flex;
          flex-wrap: wrap;
          gap: 6px 16px;
          justify-content: center;
          align-items: center;
          margin-bottom: 2px;
      }}
      .hub-legenda-linha .leg-trace,
      .widget-chart-nota .leg-trace {{
          display: inline-flex;
          align-items: center;
          gap: 5px;
          white-space: nowrap;
          font-size: 0.8rem;
          font-weight: 500;
      }}
      .widget-chart-nota .leg-nota {{
          margin-top: 6px;
          font-size: 0.72rem;
          color: {TEMA['texto_muted']} !important;
      }}
      .widget-chart-zone [data-testid="stPlotlyChart"] iframe {{
          pointer-events: auto !important;
      }}
      div[data-testid="stMarkdownContainer"]:has(.ref-pop-bar) {{
          margin-bottom: 0 !important;
          padding-bottom: 0 !important;
      }}
      div[data-testid="stMarkdownContainer"]:has(.ref-pop-bar) + div {{
          margin-top: 0 !important;
          padding-top: 0 !important;
      }}
      .hub-panorama-grid {{
          padding-top: 0 !important;
          margin-top: 0 !important;
          padding-bottom: 48px;
          overflow: visible;
      }}
      .hub-panorama-grid [data-testid="stHorizontalBlock"] {{
          align-items: flex-start !important;
          overflow: visible !important;
          height: auto !important;
          min-height: 0 !important;
      }}
      .hub-panorama-grid [data-testid="column"] {{
          overflow: visible !important;
          height: auto !important;
          align-self: flex-start !important;
      }}
      .hub-panorama-grid [data-testid="stVerticalBlock"] {{
          overflow: visible !important;
          height: auto !important;
      }}
      .hub-panorama-grid [data-testid="stPlotlyChart"] {{
          overflow: visible !important;
      }}
      .widget-chart-zone [data-testid="stPlotlyChart"],
      .widget-chart-zone [data-testid="stPlotlyChart"] > div,
      .widget-chart-zone .js-plotly-plot,
      .widget-chart-zone .plotly {{
          overflow: visible !important;
      }}
      .widget-chart-zone [data-testid="stPlotlyChart"] {{
          border-radius: 0 !important;
          border: none !important;
          border-top: none !important;
          margin-top: 0 !important;
          margin-bottom: 0 !important;
          padding: 0 !important;
          box-shadow: none !important;
      }}
      .stAppDeployButton, [data-testid="stAppDeployButton"] {{
          display: none !important;
      }}
      .widget-chart-zone .widget-head {{
          border-radius: 8px 8px 0 0;
      }}
      .hub-delta-anos-grid {{
          padding: 0 4px 2px 4px;
      }}
      .hub-delta-anos-grid [data-testid="stPlotlyChart"] {{
          margin: 0 !important;
          padding: 0 !important;
          min-height: 0 !important;
      }}

      /* Funil vertical compacto */
      .funil-v-row {{ margin-bottom: 6px; }}
      .funil-v-row:last-child {{ margin-bottom: 0; }}
      .fv-top {{
          display: flex; justify-content: space-between; align-items: baseline;
          gap: 8px;
      }}
      .fv-lbl {{
          font-size: 0.72rem; font-weight: 600;
          color: {TEMA['texto_secundario']} !important;
      }}
      .fv-val {{
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 0.98rem; font-weight: 800;
          color: {AZUL_ESCURO} !important;
          font-variant-numeric: tabular-nums;
      }}

      /* Ranking UF compacto (Opsview) */
      .rank-panel {{ margin-top: 8px; }}
      .rank-scroll {{
          max-height: 228px; overflow-y: auto;
          margin: 0 -2px; padding-right: 2px;
      }}
      .rank-tbl {{
          width: 100%; border-collapse: collapse;
          font-size: 0.72rem; line-height: 1.3;
      }}
      .rank-tbl th {{
          position: sticky; top: 0; z-index: 1;
          background: {TEMA['bg_subtle']};
          color: {TEMA['texto_secundario']} !important;
          font-weight: 700; text-transform: uppercase;
          letter-spacing: 0.05em; font-size: 0.6rem;
          padding: 5px 6px; text-align: left;
          border-bottom: 1px solid {TEMA['borda']};
      }}
      .rank-tbl td {{
          padding: 4px 6px; border-bottom: 1px solid {TEMA['borda_sutil']};
          color: {TEMA['texto']} !important;
          vertical-align: middle;
      }}
      .rank-tbl tr.rank-ms td {{
          background: rgba(27, 127, 214, 0.12);
          font-weight: 700;
      }}
      .rank-tbl tr.rank-ms td.uf {{
          color: {AZUL_ESCURO} !important;
      }}
      .rank-tbl .pos {{
          width: 26px; color: {TEMA['texto_muted']} !important;
          font-variant-numeric: tabular-nums;
      }}
      .rank-tbl .uf {{ width: 30px; font-weight: 700; }}
      .rank-tbl .tx {{
          width: 42px; text-align: right;
          font-variant-numeric: tabular-nums; font-weight: 700;
      }}
      .rank-bar-cell {{ width: 38%; }}
      .rank-bar {{
          height: 6px; background: {TEMA['bg_subtle']};
          border-radius: 3px; overflow: hidden;
      }}
      .rank-bar > span {{
          display: block; height: 100%;
          background: {AZUL_SED}; border-radius: 3px;
      }}
      .rank-tbl tr.rank-ms .rank-bar > span {{ background: {AZUL_PRINCIPAL}; }}
      .rank-ms-badge {{
          display: inline-block; margin-top: 6px; padding: 4px 8px;
          background: {TEMA['bg_subtle']}; border-radius: 6px;
          font-size: 0.7rem; font-weight: 700;
          color: {AZUL_ESCURO} !important;
          border: 1px solid {TEMA['borda']};
      }}
      .fv-tx {{
          font-size: 0.68rem; font-weight: 700; margin-top: 2px;
      }}
      .fv-bar {{
          height: 4px; background: {TEMA['bg_subtle']};
          border-radius: 2px; margin-top: 4px; overflow: hidden;
      }}
      .fv-fill {{ height: 100%; border-radius: 2px; }}
      .fv-fill.azul {{ background: {AZUL_SED}; }}
      .fv-fill.laranja {{ background: {LARANJA_DESTAQUE}; }}
      .fv-fill.verde {{ background: {VERDE_MS}; }}
      .fv-tx.insc {{ color: {LARANJA_DESTAQUE} !important; }}
      .fv-tx.insc.atencao {{ color: {COR_ATENCAO} !important; }}
      .fv-tx.insc.critico {{ color: {COR_CRITICO} !important; }}
      .fv-tx.insc.positivo {{ color: {COR_POSITIVO} !important; }}
      .fv-tx.efet {{ color: {AZUL_PRINCIPAL} !important; }}
      .fv-tx.efet.atencao {{ color: {COR_ATENCAO} !important; }}
      .fv-tx.efet.critico {{ color: {COR_CRITICO} !important; }}
      .fv-tx.efet.positivo {{ color: {COR_POSITIVO} !important; }}

      /* Card shell unificado */
      .dash-card {{
          background: {TEMA['bg_card']};
          border: 1px solid {TEMA['borda']};
          border-radius: 8px;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      }}
      .hub-sep {{
          border: none; border-top: 1px solid {TEMA['borda']};
          margin: 8px 0 10px 0;
      }}
      .secao-head {{
          margin: 0 0 14px 0;
      }}
      .secao-eyebrow {{
          display: block;
          font-size: 0.68rem; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.11em;
          color: {TEMA['texto_muted']} !important;
          margin-bottom: 2px;
      }}
      .secao-nome {{
          display: block;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 1rem; font-weight: 700;
          color: {AZUL_ESCURO} !important;
          letter-spacing: -0.01em;
      }}

      /* Bloco de título de seção */
      .bloco-titulo {{
          border-left: 5px solid {AZUL_PRINCIPAL};
          padding: 10px 16px; margin: 24px 0 16px 0;
          background: {TEMA['bg_card']};
          border-radius: 0 10px 10px 0;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
      }}
      .bloco-titulo h3 {{
          color: {AZUL_PRINCIPAL} !important;
          margin: 0; font-weight: 700; font-size: 1.18rem;
          font-family: 'Plus Jakarta Sans', sans-serif;
      }}
      .bloco-titulo p {{
          color: {TEMA['texto_secundario']} !important;
          margin: 5px 0 0 0; font-size: 0.95rem; line-height: 1.5;
      }}
      /* Cards KPI (demais abas) */
      .kpi-card {{
          position: relative; overflow: hidden;
          background: {TEMA['bg_card']};
          padding: 18px 18px 16px 18px; border-radius: 14px;
          border: 1px solid {TEMA['borda']};
          box-shadow: 0 2px 10px rgba(5, 59, 113, 0.05);
          height: 100%;
      }}
      .kpi-card::before {{
          content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
          background: {AZUL_SED};
          border-radius: 14px 14px 0 0;
      }}
      .kpi-card .rotulo {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.7rem; text-transform: uppercase;
          letter-spacing: 0.08em; font-weight: 700;
      }}
      .kpi-card .valor {{
          color: {AZUL_PRINCIPAL} !important;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 1.85rem; font-weight: 800;
          line-height: 1.15; margin-top: 6px;
          letter-spacing: -0.02em;
      }}
      .kpi-card .sub {{
          color: {TEMA['texto_muted']} !important;
          font-size: 0.8rem; margin-top: 4px;
      }}
      .kpi-card.positivo::before {{ background: linear-gradient(90deg, {COR_POSITIVO}, #3CB88A); }}
      .kpi-card.positivo .valor {{ color: {COR_POSITIVO} !important; }}
      .kpi-card.atencao::before  {{ background: linear-gradient(90deg, {COR_ATENCAO}, #F5B041); }}
      .kpi-card.atencao .valor {{ color: {COR_ATENCAO} !important; }}
      .kpi-card.critico::before  {{ background: linear-gradient(90deg, {COR_CRITICO}, #E85D4C); }}
      .kpi-card.critico .valor {{ color: {COR_CRITICO} !important; }}

      /* Boxes de achado */
      .achado {{
          padding: 14px 18px; border-radius: 10px;
          margin: 10px 0; font-size: 0.94rem;
          line-height: 1.45;
          color: {TEMA['texto']} !important;
          border-left: 5px solid;
          background: {TEMA['bg_card']};
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
      }}
      .achado .titulo {{ font-weight: 700; margin-bottom: 4px; font-size: 0.96rem; }}
      .achado .corpo  {{ color: {TEMA['texto']} !important; }}
      .achado-positivo {{ border-left-color: {COR_POSITIVO}; }}
      .achado-positivo .titulo {{ color: {COR_POSITIVO} !important; }}
      .achado-atencao  {{ border-left-color: {COR_ATENCAO}; }}
      .achado-atencao .titulo {{ color: {COR_ATENCAO} !important; }}
      .achado-critico  {{ border-left-color: {COR_CRITICO}; }}
      .achado-critico .titulo {{ color: {COR_CRITICO} !important; }}
      .achado-neutro   {{ border-left-color: {COR_NEUTRO}; }}
      .achado-neutro .titulo {{ color: {COR_NEUTRO} !important; }}

      /* Insight box */
      .insight {{
          border-left: 5px solid {AZUL_CLARO};
          background: {TEMA['insight_bg']};
          color: {TEMA['texto']} !important;
          padding: 12px 16px; border-radius: 8px;
          margin: 8px 0 16px 0; font-size: 0.94rem;
          line-height: 1.45;
      }}
      .insight strong {{ color: {AZUL_PRINCIPAL} !important; }}

      /* Faixa participação — funil em etapas */
      .faixa-populacao {{
          padding: 16px 18px 14px 18px;
          margin: 0 0 16px 0;
      }}
      .faixa-populacao.dash-card {{
          border-radius: 14px;
      }}
      .faixa-populacao .fp-steps {{
          display: flex; flex-wrap: wrap; align-items: stretch;
          gap: 6px; justify-content: space-between;
      }}
      .faixa-populacao .fp-step {{
          flex: 1 1 140px; min-width: 120px;
          background: {TEMA['bg_card']};
          border: 1px solid {TEMA['borda']};
          border-left-width: 3px;
          border-radius: 10px; padding: 14px 16px;
          text-align: left;
      }}
      .faixa-populacao .fp-step-conc {{ border-left-color: {AZUL_SED}; }}
      .faixa-populacao .fp-step-insc {{ border-left-color: {LARANJA_DESTAQUE}; }}
      .faixa-populacao .fp-step-efet {{ border-left-color: {VERDE_MS}; }}
      .faixa-populacao .fp-step-val {{
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-weight: 800; font-size: 1.42rem; line-height: 1.1;
          letter-spacing: -0.02em;
      }}
      .faixa-populacao .fp-step-val.azul {{ color: {AZUL_PRINCIPAL} !important; }}
      .faixa-populacao .fp-step-val.laranja {{ color: {LARANJA_DESTAQUE} !important; }}
      .faixa-populacao .fp-step-val.verde {{ color: {COR_POSITIVO} !important; }}
      .faixa-populacao .fp-step-lbl {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.78rem; margin-top: 4px; font-weight: 600;
      }}
      .faixa-populacao .fp-step-tx {{
          font-size: 0.76rem; font-weight: 700; margin-top: 6px;
      }}
      .faixa-populacao .fp-step-tx.insc {{ color: {LARANJA_DESTAQUE} !important; }}
      .faixa-populacao .fp-step-tx.insc.atencao {{ color: {COR_ATENCAO} !important; }}
      .faixa-populacao .fp-step-tx.insc.critico {{ color: {COR_CRITICO} !important; }}
      .faixa-populacao .fp-step-tx.insc.positivo {{ color: {COR_POSITIVO} !important; }}
      .faixa-populacao .fp-step-tx.efet {{ color: {AZUL_PRINCIPAL} !important; }}
      .faixa-populacao .fp-step-tx.efet.atencao {{ color: {COR_ATENCAO} !important; }}
      .faixa-populacao .fp-step-tx.efet.critico {{ color: {COR_CRITICO} !important; }}
      .faixa-populacao .fp-step-tx.efet.positivo {{ color: {COR_POSITIVO} !important; }}
      .faixa-populacao .fp-arrow {{
          display: flex; align-items: center; justify-content: center;
          color: {TEMA['texto_muted']} !important; font-size: 1.4rem;
          font-weight: 300; opacity: 0.55; flex: 0 0 20px;
          align-self: center;
      }}

      /* Gráficos Plotly em card */
      [data-testid="stPlotlyChart"] {{
          background: {TEMA['bg_card']};
          border: 1px solid {TEMA['borda']};
          border-radius: 12px;
          padding: 2px 0 0 0;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
          margin-bottom: 3px;
      }}
      .stCaption {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.8125rem !important;
          line-height: 1.45 !important;
      }}
      .chart-legenda-delta {{
          display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
          margin: 4px 2px 14px 2px; padding: 8px 0 0 0;
          border-top: 1px solid {TEMA['borda_sutil']};
          font-size: 0.8125rem; color: {TEMA['texto_secundario']} !important;
          line-height: 1.45;
      }}
      .chart-legenda-delta strong {{
          color: {AZUL_PRINCIPAL} !important; font-weight: 800;
          font-family: 'Plus Jakarta Sans', sans-serif;
      }}
      .chart-legenda-delta .delta-pos {{ color: {COR_POSITIVO} !important; font-weight: 700; }}
      .chart-legenda-delta .delta-neg {{ color: {COR_CRITICO} !important; font-weight: 700; }}

      /* Rodapé */
      .rodape {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.8125rem; line-height: 1.45;
          margin-top: 28px; text-align: center;
          padding-top: 14px; border-top: 1px solid {TEMA['borda_sutil']};
      }}

      /* Radio horizontal — abas com sublinhado */
      div[data-testid="stRadio"] {{
          margin-bottom: 0 !important;
      }}
      div[data-testid="stRadio"] > div[role="radiogroup"] {{
          gap: 4px !important;
          background: {TEMA['bg_card']} !important;
          border: 1px solid {TEMA['borda']} !important;
          border-radius: 8px !important;
          padding: 3px !important;
          box-shadow: none !important;
          margin-bottom: 4px !important;
      }}
      div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
          background: transparent !important;
          border-radius: 6px !important;
          padding: 6px 14px !important;
          font-weight: 600 !important;
          font-family: 'Plus Jakarta Sans', sans-serif !important;
          font-size: 0.8rem !important;
          color: {TEMA['texto_secundario']} !important;
          border-bottom: none !important;
          margin-bottom: 0 !important;
      }}
      div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {{
          background: #DBEAFE !important;
          color: {AZUL_ESCURO} !important;
          border: 1px solid {AZUL_SED} !important;
          box-shadow: none !important;
      }}
      div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked),
      div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) * {{
          color: {AZUL_ESCURO} !important;
      }}

      /* Tabs do Streamlit */
      .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
      .stTabs [data-baseweb="tab"] {{
          padding: 10px 18px; font-weight: 600;
          color: {TEMA['texto_secundario']} !important;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 0.88rem;
      }}
      .stTabs [aria-selected="true"] {{
          color: {AZUL_PRINCIPAL} !important;
          border-bottom-color: {AZUL_PRINCIPAL} !important;
      }}

      /* Sidebar institucional */
      [data-testid="stSidebar"] {{
          background: linear-gradient(180deg, {TEMA['bg_sidebar']} 0%, #EEF3FA 100%) !important;
          border-right: 1px solid {TEMA['borda']};
      }}
      [data-testid="stSidebar"] .stMarkdown,
      [data-testid="stSidebar"] .stMarkdown p,
      [data-testid="stSidebar"] label {{
          color: {TEMA['texto']} !important;
      }}
      [data-testid="stSidebar"] .stMarkdown h1,
      [data-testid="stSidebar"] .stMarkdown h2,
      [data-testid="stSidebar"] .stMarkdown h3 {{
          color: {AZUL_PRINCIPAL} !important;
          font-family: 'Plus Jakarta Sans', sans-serif;
      }}

      /* Componentes nativos: dataframe, selectbox, etc. */
      .stDataFrame, .stDataFrame [role="grid"] {{
          color: {TEMA['texto']} !important;
      }}
      [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
          color: {TEMA['texto']} !important;
      }}

      /* Inputs / select / multiselect: garantir contraste */
      .stSelectbox label, .stMultiSelect label, .stSlider label, .stRadio label,
      .stTextInput label, .stNumberInput label, .stCheckbox label {{
          color: {TEMA['texto']} !important;
          font-weight: 600;
      }}

      /* Mensagens informativas (st.info, st.warning, st.error) — manter
         o estilo nativo, apenas garantir cor de texto legível */
      [data-testid="stAlert"] {{ color: {TEMA['texto']}; }}

      /* Plotly embutido no DOM principal (hover + roda do mouse) */
      .hub-plotly-embed {{
          width: 100%;
          overflow: visible;
          pointer-events: auto !important;
      }}
      .hub-plotly-embed .plotly-graph-div,
      .hub-plotly-embed .js-plotly-plot {{
          width: 100% !important;
          pointer-events: auto !important;
      }}
      .js-plotly-plot,
      .plotly-graph-div,
      [data-testid="stPlotlyChart"],
      [data-testid="stPlotlyChart"] iframe {{
          touch-action: pan-y;
          pointer-events: auto !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FORMATAÇÃO
# ============================================================


def fmt_int(n) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    return f"{int(n):,}".replace(",", ".")


def fmt_float(n, casas: int = 1) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    s = f"{n:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(n, casas: int = 1) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    return f"{fmt_float(n, casas)}%"


def _safe_int_val(n, default: int = 0) -> int:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return default
    v = pd.to_numeric(n, errors="coerce")
    return int(v) if pd.notna(v) else default


def _pct_taxa(numerador: pd.Series, concluintes: pd.Series, casas: int = 1) -> pd.Series:
    denom = pd.to_numeric(concluintes, errors="coerce").replace(0, pd.NA)
    tx = numerador / denom * 100
    return tx.apply(lambda x: round(x, casas) if pd.notna(x) else pd.NA)


def fmt_delta(n, casas: int = 1, unidade: str = " pts") -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    sinal = "+" if n >= 0 else "−"
    return f"{sinal}{fmt_float(abs(n), casas)}{unidade}"


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


def _totais_participacao_recorte(
    tabelas: dict,
    anos_sel: list,
    dependencia: str = "Estadual",
) -> dict[str, Optional[int | float]]:
    """Soma inscritos, concluintes e presentes_filt no recorte (participacao_ano)."""
    df_part = tabelas.get("participacao_ano", pd.DataFrame())
    vazio = {
        "inscritos": None,
        "concluintes": None,
        "presentes_filt": None,
        "tx_part_efetiva": None,
        "tx_part_inscritos": None,
    }
    if df_part.empty or not anos_sel:
        return vazio
    anos_int = [int(a) for a in anos_sel]
    sub = df_part[
        (df_part["ano"].isin(anos_int)) & (df_part["dependencia"] == dependencia)
    ]
    if sub.empty:
        return vazio
    n_insc = int(sub["inscritos"].fillna(0).sum()) if "inscritos" in sub.columns else None
    n_conc = int(sub["concluintes"].fillna(0).sum()) if "concluintes" in sub.columns else None
    n_pres = (
        int(sub["presentes_filt"].fillna(0).sum())
        if "presentes_filt" in sub.columns else None
    )
    if n_conc is not None and n_conc <= 0:
        n_conc = None
    if n_insc is not None and n_insc <= 0:
        n_insc = None
    if n_pres is not None and n_pres <= 0:
        n_pres = None
    tx_efet = (
        round(100 * n_pres / n_conc, 1)
        if n_conc and n_pres else None
    )
    tx_insc_pres = (
        round(100 * n_pres / n_insc, 1)
        if n_insc and n_pres else None
    )
    tx_insc_conc = (
        round(100 * n_insc / n_conc, 1)
        if n_conc and n_insc else None
    )
    return {
        "inscritos": n_insc,
        "concluintes": n_conc,
        "presentes_filt": n_pres,
        "tx_part_efetiva": tx_efet,
        "tx_part_inscritos": tx_insc_pres,
        "tx_inscricao": tx_insc_conc,
    }


def _serie_tx_part_efetiva_br(
    tabelas: dict,
    anos_sel: list,
    dependencia: str = "Estadual",
) -> pd.Series:
    """Taxa de participação efetiva nacional (soma UFs, rede estadual)."""
    df = tabelas.get("participacao_uf", pd.DataFrame())
    if df.empty or not anos_sel:
        return pd.Series(dtype=float)
    out: dict[int, float] = {}
    for ano in anos_sel:
        sub = df[
            (df["ano"] == int(ano)) & (df["dependencia"] == dependencia)
        ]
        if sub.empty:
            continue
        pres = pd.to_numeric(
            sub.get("presentes_filt", sub.get("presentes")),
            errors="coerce",
        ).fillna(0).sum()
        conc = (
            pd.to_numeric(sub["concluintes"], errors="coerce").fillna(0).sum()
            if "concluintes" in sub.columns else 0
        )
        if conc > 0:
            out[int(ano)] = round(100 * pres / conc, 1)
        else:
            insc = pd.to_numeric(sub["inscritos"], errors="coerce").fillna(0).sum()
            if insc > 0:
                out[int(ano)] = round(100 * pres / insc, 1)
    return pd.Series(out).sort_index()


def _enriquecer_diag_participacao(diag: dict, tabelas: dict, anos_sel: list) -> dict:
    """Inclui concluintes, presentes efetivos, taxas e séries anuais no diagnóstico."""
    tot = _totais_participacao_recorte(tabelas, anos_sel, "Estadual")
    diag["n_concluintes"] = tot["concluintes"]
    diag["n_presentes_filt"] = tot["presentes_filt"] or diag.get("n_part")
    diag["tx_part_efetiva"] = tot["tx_part_efetiva"]
    diag["tx_part_inscritos"] = tot["tx_part_inscritos"]
    diag["tx_inscricao"] = tot["tx_inscricao"]
    if tot["tx_part_efetiva"] is not None:
        diag["tx_part"] = tot["tx_part_efetiva"]
    if tot["inscritos"] is not None:
        diag["n_inscritos"] = tot["inscritos"]

    part_serie = participacao_ms_por_ano(tabelas, list(anos_sel), "Estadual")
    if not part_serie.empty:
        diag["serie_tx_part_efetiva"] = (
            part_serie.set_index(part_serie["ano"].astype(int))["Tx_Part_Efetiva"]
        )
        diag["serie_tx_inscricao"] = (
            part_serie.set_index(part_serie["ano"].astype(int))["Tx_Inscrição"]
        )

    br_por_ano: dict[int, float] = {}
    for ano in anos_sel:
        refs = medias_referencia_por_ano(tabelas, int(ano))
        mg = refs.get("MEDIA_GERAL", {})
        br = mg.get("br")
        if br is not None and pd.notna(br):
            br_por_ano[int(ano)] = float(br)
    if br_por_ano:
        diag["serie_media_br"] = pd.Series(br_por_ano).sort_index()

    serie_br_part = _serie_tx_part_efetiva_br(tabelas, anos_sel)
    if not serie_br_part.empty:
        diag["serie_tx_part_efetiva_br"] = serie_br_part

    serie_ms = diag.get("serie_medias", pd.Series(dtype=float))
    serie_br = diag.get("serie_media_br", pd.Series(dtype=float))
    if not serie_ms.empty and not serie_br.empty:
        ms_map = {int(k): float(v) for k, v in serie_ms.items() if pd.notna(v)}
        br_map = {int(k): float(v) for k, v in serie_br.items() if pd.notna(v)}
        diag["serie_delta_br"] = pd.Series(
            {a: ms_map[a] - br_map[a] for a in sorted(set(ms_map) & set(br_map))},
        ).sort_index()
    return diag


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


def _html_funil_vertical(diag: dict, periodo: str) -> str:
    """Funil em coluna com barras de proporção — painel lateral compacto."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    n_insc = diag.get("n_inscritos")
    tx_efet = diag.get("tx_part_efetiva")
    tx_insc = diag.get("tx_inscricao")
    if not n_conc or not n_pres:
        return (
            f'<div class="widget-card"><div class="widget-head">Participação · '
            f'{_html.escape(periodo)}</div><div class="widget-body">'
            f'<div class="insight" style="margin:0">'
            f'<b>{fmt_int(n_pres)}</b> participantes efetivos. '
            f'Concluintes indisponíveis.</div></div></div>'
        )

    status_efet = classificar_participacao(tx_efet if tx_efet is not None else 0)
    classe_efet = status_efet if status_efet in ("positivo", "atencao", "critico") else ""
    classe_insc = ""
    if tx_insc is not None:
        classe_insc = (
            "positivo" if tx_insc >= 70
            else ("atencao" if tx_insc >= 50 else "critico")
        )

    pct_conc = 100.0
    pct_insc = min(100.0, float(tx_insc)) if tx_insc is not None else 0.0
    pct_efet = min(100.0, float(tx_efet)) if tx_efet is not None else 0.0

    rows = [
        (
            f'<div class="funil-v-row">'
            f'<div class="fv-top"><span class="fv-lbl">Concluintes do Ensino Médio</span>'
            f'<span class="fv-val">{fmt_int(n_conc)}</span></div>'
            f'<div class="fv-bar"><div class="fv-fill azul" style="width:{pct_conc:.0f}%"></div></div>'
            f'</div>'
        ),
    ]
    if n_insc:
        tx_html = (
            f'<div class="fv-tx insc {classe_insc}">{fmt_pct(tx_insc)} dos concluintes</div>'
            if tx_insc is not None else ""
        )
        rows.append(
            f'<div class="funil-v-row">'
            f'<div class="fv-top"><span class="fv-lbl">Inscritos ENEM</span>'
            f'<span class="fv-val">{fmt_int(n_insc)}</span></div>'
            f'{tx_html}'
            f'<div class="fv-bar"><div class="fv-fill laranja" style="width:{pct_insc:.0f}%"></div></div>'
            f'</div>'
        )
    rows.append(
        f'<div class="funil-v-row">'
        f'<div class="fv-top"><span class="fv-lbl">Participantes efetivos</span>'
        f'<span class="fv-val">{fmt_int(n_pres)}</span></div>'
        f'<div class="fv-tx efet {classe_efet}">{fmt_pct(tx_efet)} dos concluintes</div>'
        f'<div class="fv-bar"><div class="fv-fill verde" style="width:{pct_efet:.0f}%"></div></div>'
        f'</div>'
    )
    return (
        f'<div class="widget-card"><div class="widget-head">Participação · '
        f'{_html.escape(periodo)}</div><div class="widget-body">'
        f'{"".join(rows)}</div></div>'
    )


def _html_funil_kpi_inline(diag: dict, periodo: str) -> str:
    """Participação no formato KPI: uma linha por etapa, barra + % sobrepostos."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    n_insc = diag.get("n_inscritos")
    tx_efet = diag.get("tx_part_efetiva")
    tx_insc = diag.get("tx_inscricao")
    if not n_conc or not n_pres:
        return (
            f'<div class="kpi-claro kpi-funil-inline">'
            f'<span class="kpi-claro-lbl">Participação · {_html.escape(periodo)}</span>'
            f'<span class="kpi-claro-val" style="font-size:0.95rem">{fmt_int(n_pres)}</span>'
            f'<span class="kpi-claro-sub">participantes efetivos</span></div>'
        )

    pct_insc = min(100.0, float(tx_insc)) if tx_insc is not None else 0.0
    pct_efet = min(100.0, float(tx_efet)) if tx_efet is not None else 0.0

    def _barra(pct: float, cor: str, pct_label: str | None) -> str:
        w = max(min(pct, 100.0), 0.0)
        if pct_label and w >= 14:
            inner = f'<span class="fk-pct">{_html.escape(pct_label)}</span>'
            outer = ""
        elif pct_label:
            inner = ""
            outer = f'<span class="fk-pct-out">{_html.escape(pct_label)}</span>'
        else:
            inner = ""
            outer = ""
        return (
            f'<span class="fk-track">'
            f'<span class="fk-fill {cor}" style="width:{w:.0f}%">{inner}</span>'
            f'{outer}</span>'
        )

    def _linha(lbl: str, val: str, pct: float, cor: str, pct_label: str | None) -> str:
        return (
            f'<div class="fk-line">'
            f'<span class="fk-l">{lbl}</span>'
            f'<span class="fk-n">{val}</span>'
            f'{_barra(pct, cor, pct_label)}'
            f'</div>'
        )

    linhas = [_linha("Concluintes", fmt_int(n_conc), 100.0, "azul", None)]
    if n_insc:
        linhas.append(
            _linha(
                "Inscritos", fmt_int(n_insc), pct_insc, "laranja",
                fmt_pct(tx_insc) if tx_insc is not None else None,
            )
        )
    linhas.append(
        _linha(
            "Participação efetiva", fmt_int(n_pres), pct_efet, "verde",
            fmt_pct(tx_efet) if tx_efet is not None else None,
        )
    )

    return (
        f'<div class="kpi-claro kpi-funil-inline">'
        f'<span class="kpi-claro-lbl">Participação · {_html.escape(periodo)}</span>'
        f'<div class="fk-lines">{"".join(linhas)}</div>'
        f'</div>'
    )


def _html_funil_estreito(diag: dict, periodo: str) -> str:
    """Funil lateral compacto (coluna estreita ao lado do ranking nacional)."""
    html = _html_funil_vertical(diag, periodo)
    return html.replace('class="widget-card"', 'class="widget-card funil-estreito"', 1)


def _render_funil_widget(diag: dict, periodo: str, *, estreito: bool = False) -> None:
    if estreito:
        _render_html(_html_funil_estreito(diag, periodo))
    else:
        _render_html(_html_funil_vertical(diag, periodo))


def _cor_posicao_terco(pos: int, n_total: int) -> str:
    terco = n_total / 3 if n_total else 9
    if pos <= terco:
        return COR_POSITIVO
    if pos <= 2 * terco:
        return COR_ATENCAO
    return COR_CRITICO


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

# ============================================================
# CARGA DE DADOS
# ============================================================


@st.cache_data(show_spinner="Preparando bases nacionais...", ttl=3600, max_entries=1)
def carregar_bases_nacionais() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bases nacionais sintéticas (UF) — operação pesada (~20s); cache único bruta+filtrada."""
    if not verificar_dados_disponiveis():
        st.error(
            f"Dados agregados não encontrados. Configure PASTA_AGREGADOS "
            f"({PASTA_AGREGADOS}) ou DATA_SOURCE=supabase com credenciais válidas. "
            f"Gere os arquivos com: python gerar_dados_agregados.py"
        )
        st.stop()
    tabelas = carregar_todas_tabelas()
    df_bruta, df_filt = reconstruir_bases_nacionais(tabelas, ANOS_DISPONIVEIS)
    if df_bruta.empty:
        st.error("Nenhum dado agregado nacional carregado. Verifique os arquivos parquet.")
        st.stop()
    return df_bruta, df_filt.reset_index(drop=True)


def carregar_base_bruta() -> pd.DataFrame:
    return carregar_bases_nacionais()[0]


def carregar_base_filtrada(df_bruta: pd.DataFrame) -> pd.DataFrame:
    return carregar_bases_nacionais()[1]


@st.cache_data(show_spinner=False, ttl=3600)
def carregar_cres() -> pd.DataFrame:
    cres = carregar_cres_escolas(ARQUIVO_CRES)
    if cres.empty and ARQUIVO_CRES and os.path.exists(ARQUIVO_CRES):
        st.error(
            "Coluna de código INEP não encontrada na 1ª aba do arquivo CRES. "
            "Use cres.xlsx (aba Cód.INEP-CREs) ou defina ARQUIVO_CRES."
        )
    return cres


@st.cache_data(show_spinner=False, ttl=3600)
def _mapa_cre_completo_cached() -> dict:
    return construir_mapa_cre_completo(ARQUIVO_CRES)


@st.cache_data(show_spinner=False, ttl=3600)
def carregar_mapa_municipio_cre() -> dict:
    mapa = _carregar_mapa_municipio_cre(ARQUIVO_CRES)
    if not mapa and ARQUIVO_CRES and os.path.exists(ARQUIVO_CRES):
        st.warning(
            "Mapeamento município → CRE indisponível na planilha CRES. "
            "Verifique a 1ª aba ou a aba 'CREs'."
        )
    return mapa


def normalizar_texto(texto: str) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = (texto
             .replace("Á", "A").replace("É", "E").replace("Í", "I")
             .replace("Ó", "O").replace("Ú", "U").replace("Â", "A")
             .replace("Ê", "E").replace("Î", "I").replace("Ô", "O")
             .replace("Û", "U").replace("Ã", "A").replace("Õ", "O")
             .replace("Ç", "C").replace("À", "A"))
    return texto


def enriquecer_ms(df_ms: pd.DataFrame, cres: pd.DataFrame, mapa_muni_cre: dict = None) -> pd.DataFrame:
    df = df_ms.copy()
    if "NOME_ESCOLA" not in df.columns:
        df["NOME_ESCOLA"] = pd.NA
    if "MUNICIPIO_CRES" not in df.columns:
        df["MUNICIPIO_CRES"] = df.get("NO_MUNICIPIO_ESC", pd.NA)
    if "CRE" not in df.columns:
        df["CRE"] = pd.NA

    if cres is not None and not cres.empty and "CO_ESCOLA" in df.columns:
        mask_com_escola = df["CO_ESCOLA"].notna()
        if mask_com_escola.any():
            df_com_escola = df[mask_com_escola].merge(
                cres, on="CO_ESCOLA", how="left", validate="m:1", suffixes=("_old", ""),
            )
            for col in ["NOME_ESCOLA", "MUNICIPIO_CRES", "CRE"]:
                if col not in df_com_escola.columns:
                    df_com_escola[col] = pd.NA
            df.loc[mask_com_escola,
                "NOME_ESCOLA"] = df_com_escola["NOME_ESCOLA"].values
            df.loc[mask_com_escola,
                "MUNICIPIO_CRES"] = df_com_escola["MUNICIPIO_CRES"].values
            df.loc[mask_com_escola, "CRE"] = df_com_escola["CRE"].values

    if mapa_muni_cre and df["CRE"].isna().any():
        mask_sem_cre = df["CRE"].isna()
        col_mun = "MUNICIPIO_CRES" if df["MUNICIPIO_CRES"].notna(
        ).any() else "NO_MUNICIPIO_ESC"
        if col_mun in df.columns:
            municipios_normalizados = df.loc[mask_sem_cre, col_mun].apply(
                normalizar_texto)
            df.loc[mask_sem_cre, "CRE"] = municipios_normalizados.map(
                mapa_muni_cre)

    # Normalizar nomes curtos de CRE para nomes completos
    mapa_cre_completo = _mapa_cre_completo_cached()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df


def _coluna_municipio(df: pd.DataFrame) -> Optional[str]:
    """Primeira coluna de município disponível e preenchida."""
    for col in ("MUNICIPIO_CRES", "NO_MUNICIPIO_ESC", "municipio"):
        if col in df.columns and df[col].notna().any():
            return col
    return None


def _mapa_municipio_por_escola(df: pd.DataFrame) -> pd.Series:
    col = _coluna_municipio(df)
    if col is None or "CO_ESCOLA" not in df.columns:
        return pd.Series(dtype=object)
    return (
        df[["CO_ESCOLA", col]]
        .drop_duplicates(subset=["CO_ESCOLA"])
        .set_index("CO_ESCOLA")[col]
    )


def aplicar_cre_por_municipio(df: pd.DataFrame, mapa_muni_cre: dict) -> pd.DataFrame:
    df = df.copy()
    if "CRE" not in df.columns:
        df["CRE"] = pd.NA
    col_mun = _coluna_municipio(df)
    if col_mun and mapa_muni_cre:
        mask_sem_cre = df["CRE"].isna()
        municipios_normalizados = df.loc[mask_sem_cre, col_mun].apply(
            normalizar_texto)
        df.loc[mask_sem_cre, "CRE"] = municipios_normalizados.map(
            mapa_muni_cre)

    # Normalizar nomes curtos de CRE para nomes completos
    mapa_cre_completo = _mapa_cre_completo_cached()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df


# ============================================================
# HELPERS DE UI E GRÁFICO
# ============================================================
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


def aplicar_tema(
    fig,
    altura: int = CHART_H_STANDARD,
    *,
    limpar_titulo: bool = False,
    modo_hub: bool = False,
):
    """Aplica identidade visual institucional aos gráficos Plotly.

    - Sem grade no eixo X (linhas verticais removidas).
    - Eixo Y com grid sutil (apenas referência horizontal).
    - Preserva título já definido no fig, salvo ``limpar_titulo=True`` (hub).
    - ``modo_hub=True``: margens compactas; legenda fica fora (rodapé interno).
    """
    titulo_atual = ""
    if fig.layout.title and fig.layout.title.text:
        titulo_atual = str(fig.layout.title.text)

    layout_kw: dict = dict(
        template=TEMA["plot_template"],
        height=altura,
        margin=margem_hub() if modo_hub else margem_detalhe(),
        font=dict(family="Source Sans 3, system-ui, sans-serif",
                  size=FONT_CHART, color=TEMA["texto"]),
        title_font=dict(family="Plus Jakarta Sans, sans-serif",
                        size=15, color=AZUL_PRINCIPAL),
        hoverlabel=hover_padrao(
            bgcolor=TEMA["bg_card"],
            texto=TEMA["texto"],
            borda=TEMA["borda"],
            font_size=FONT_HOVER,
        ),
        paper_bgcolor=TEMA["plot_paper"],
        plot_bgcolor=TEMA["plot_plot"],
        hovermode="closest",
        bargap=0.22, bargroupgap=0.06,
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
        showgrid=False, zeroline=False,
        showline=True, linecolor=TEMA["linha_eixo"], linewidth=1,
        ticks="outside", tickcolor=TEMA["linha_eixo"], ticklen=4,
        tickfont=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
        title_font=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
    )
    y_kw = dict(
        showgrid=False, gridcolor=TEMA["grid_sutil"], gridwidth=1,
        zeroline=False,
        showline=False,
        title_font=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
    )
    if modo_hub:
        y_kw.update(showticklabels=False, ticks="", ticklen=0)
    else:
        y_kw.update(
            ticks="outside", tickcolor=TEMA["linha_eixo"], ticklen=4,
            tickfont=dict(color=TEMA["texto_secundario"], size=FONT_AXIS),
        )
    fig.update_yaxes(**y_kw)
    return fig


def _hex_rgba(hex_color: str, alpha: float) -> str:
    """Converte cor hex para rgba, lidando com nomes de cores Plotly."""
    # Se for nome de cor Plotly (ex: 'rgb(31, 119, 180)'), extrair valores
    if isinstance(hex_color, str) and hex_color.startswith("rgb("):
        vals = hex_color.strip("rgb()").split(",")
        r, g, b = int(vals[0]), int(vals[1]), int(vals[2])
        return f"rgba({r},{g},{b},{alpha})"
    # Se for nome de cor, usar mapeamento basico
    if isinstance(hex_color, str) and not hex_color.startswith("#"):
        nome_para_hex = {
            "red": "#FF0000", "green": "#008000", "blue": "#0000FF",
            "orange": "#FFA500", "purple": "#800080", "brown": "#A52A2A",
            "pink": "#FFC0CB", "gray": "#808080", "grey": "#808080",
            "black": "#000000", "white": "#FFFFFF", "yellow": "#FFFF00",
            "cyan": "#00FFFF", "magenta": "#FF00FF", "lime": "#00FF00",
            "navy": "#000080", "teal": "#008080", "olive": "#808000",
            "maroon": "#800000", "silver": "#C0C0C0", "coral": "#FF7F50",
        }
        hex_color = nome_para_hex.get(hex_color.lower(), "#999999")
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    if len(h) != 6:
        return f"rgba(153,153,153,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ============================================================
# FUNÇÃO UTILITÁRIA PARA ESTILIZAÇÃO DE TABELAS
# ============================================================
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


def _render_html(html: str) -> None:
    """Renderiza HTML sem indentação que o Streamlit interpreta como bloco de código."""
    st.markdown(html.strip(), unsafe_allow_html=True)


def _logo_data_uri() -> str:
    """Logo oficial Governo/SED MS (SVG preferencial, site sed.ms.gov.br)."""
    for path in _LOGO_MS_CANDIDATES:
        if not os.path.isfile(path):
            continue
        mime = (
            "image/svg+xml" if path.lower().endswith(".svg")
            else "image/png"
        )
        with open(path, "rb") as f:
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    return ""


def _kpi_titulo(indicador: str) -> str:
    """Título padronizado dos KPIs do cabeçalho."""
    return f"{indicador} · rede estadual"


def _kpi_claro_html(
    rotulo: str,
    valor: str,
    sub: str = "",
    status: str = "",
    *,
    extra_class: str = "",
) -> str:
    status_validos = {"positivo", "atencao", "critico"}
    cls = f"kpi-claro {status}" if status in status_validos else "kpi-claro"
    if extra_class:
        cls = f"{cls} {extra_class}"
    return (
        f'<div class="{cls}">'
        f'<span class="kpi-claro-lbl">{_html.escape(rotulo)}</span>'
        f'<span class="kpi-claro-val">{_html.escape(valor)}</span>'
        f'<span class="kpi-claro-sub">{_html.escape(sub)}</span>'
        f'</div>'
    )


def _kpi_strip_items(diag: dict, periodo: str) -> list[str]:
    """Itens HTML dos KPIs compactos (padrão: título · escopo | valor | contexto · período)."""
    status_var = classificar_tendencia(diag.get("variacao_inicio_fim", 0))
    pos_recente = diag.get("pos_ms_recente")
    total_recente = diag.get("total_ufs_recente", 0)
    pos_hist = diag.get("pos_ms")
    total_hist = diag.get("total_ufs", 0)
    ano_inicio = diag.get("ano_inicio")
    ano_fim = diag.get("ano_fim")
    ano_ref_pos = diag.get("ano_referencia_pos") or ano_fim
    sub_variacao = (
        f"{ano_inicio} → {ano_fim}"
        if ano_inicio is not None and ano_fim is not None
        else periodo
    )

    itens = [
        _kpi_claro_html(
            _kpi_titulo("Média geral"),
            fmt_float(diag["media_estadual_ms"]),
            f"Média ponderada · {periodo}",
            extra_class="kpi-media",
        ),
        _kpi_claro_html(
            _kpi_titulo("Variação da média"),
            fmt_delta(diag.get("variacao_inicio_fim", 0)),
            sub_variacao,
            status=status_var,
            extra_class="kpi-variacao",
        ),
    ]
    if pos_recente:
        itens.append(
            _kpi_claro_html(
                _kpi_titulo("Posição nacional"),
                f"{pos_recente}º de {total_recente}",
                (
                    f"{ano_ref_pos} · ranking entre UFs"
                    if ano_ref_pos is not None
                    else f"Ranking entre UFs · {periodo}"
                ),
                status=classificar_posicao(pos_recente, total_recente),
                extra_class="kpi-posicao",
            )
        )
    elif pos_hist:
        itens.append(
            _kpi_claro_html(
                _kpi_titulo("Posição nacional"),
                f"{pos_hist}º de {total_hist}",
                f"Ranking entre UFs · {periodo}",
                status=classificar_posicao(pos_hist, total_hist),
                extra_class="kpi-posicao",
            )
        )
    else:
        itens.append(
            _kpi_claro_html(
                _kpi_titulo("Posição nacional"),
                "—",
                "Sem dados no recorte",
                extra_class="kpi-posicao",
            )
        )

    diff_br = diag.get("diff_vs_nacional", float("nan"))
    status_diff = ""
    if pd.notna(diff_br):
        status_diff = "positivo" if diff_br >= 0 else "critico"
    itens.append(
        _kpi_claro_html(
            _kpi_titulo("Diferença vs Brasil"),
            fmt_delta(diff_br) if pd.notna(diff_br) else "—",
            f"Média ponderada · {periodo}",
            status=status_diff,
            extra_class="kpi-delta-br",
        )
    )
    return itens


def _html_faixa_kpis(diag: dict, periodo: str, *, no_cabecalho: bool = False) -> str:
    """HTML dos KPIs + funil inline (opcional)."""
    n_conc = diag.get("n_concluintes")
    n_pres = diag.get("n_presentes_filt") or diag.get("n_part")
    funil = (
        _html_funil_kpi_inline(diag, periodo)
        if n_conc and n_pres else ""
    )
    itens = "".join(_kpi_strip_items(diag, periodo))
    if no_cabecalho:
        return f'<div class="cab-claro-kpis">{itens}{funil}</div>'
    return (
        f'<div class="kpi-funil-row kpi-strip-tight">{itens}{funil}</div>'
    )


def _html_kpi_strip(diag: dict, periodo: str) -> str:
    """Faixa de KPIs em cards brancos abaixo do cabeçalho."""
    return (
        f'<div class="kpi-strip-claro kpi-strip-tight">'
        f'{"".join(_kpi_strip_items(diag, periodo))}</div>'
    )


def _html_cabecalho_com_kpis(diag: dict, periodo: str) -> str:
    """Cabeçalho com logo/título à esquerda e KPIs à direita."""
    logo = _logo_data_uri()
    img = (
        f'<img class="cab-claro-logo" src="{logo}" alt="Governo de MS — SED" />'
        if logo else ""
    )
    kpis = _html_faixa_kpis(diag, periodo, no_cabecalho=True)
    return (
        f'<div class="cab-claro cab-claro--com-kpis">'
        f'<div class="cab-claro-row">'
        f'<div class="cab-claro-brand">{img}'
        f'<div class="cab-claro-text"><h1>Painel ENEM MS</h1>'
        f'<p>Desempenho e participação da rede estadual · 2019–2025</p>'
        f'</div></div>'
        f'{kpis}'
        f'</div></div>'
    )


def _render_cabecalho_claro() -> None:
    """Cabeçalho branco — logo e título (sem KPIs)."""
    logo = _logo_data_uri()
    img = (
        f'<img class="cab-claro-logo" src="{logo}" alt="Governo de MS — SED" />'
        if logo else ""
    )
    _render_html(
        f'<div class="cab-claro"><div class="cab-claro-row">{img}'
        f'<div class="cab-claro-text"><h1>Painel ENEM MS</h1>'
        f'<p>Desempenho e participação da rede estadual · 2019–2025</p>'
        f'</div></div></div>'
    )


def _render_cabecalho_com_kpis(diag: dict, periodo: str) -> None:
    """Cabeçalho integrado: marca à esquerda, KPIs à direita."""
    _render_html(_html_cabecalho_com_kpis(diag, periodo))


def _html_populacao_referencia_resumo() -> str:
    """Resumo inline da população de referência (substitui aba Metodologia no topo)."""
    return (
        '<div class="ref-pop-bar">'
        '<span class="ref-pop-tag">População de referência</span>'
        '<span class="ref-pop-item">Presentes nos dois dias de prova; '
        'Concluintes do Ensino Médio na rede estadual</span>'
        '<span class="ref-pop-sep">·</span>'
        '<span class="ref-pop-item"><strong>2019–2023</strong> concluintes do Ensino Médio · '
        '<strong>2024</strong> inscritos na rede estadual</span>'
        '<span class="ref-pop-sep">·</span>'
        '<span class="ref-pop-item"><strong>Taxa de participação efetiva</strong> = presentes ÷ concluintes</span>'
        '</div>'
    )


def _render_populacao_referencia_compacta() -> None:
    _render_html(_html_populacao_referencia_resumo())


def _render_faixa_kpis_claro(diag: dict, periodo: str) -> None:
    """KPIs + card de participação na mesma faixa (legado / uso externo)."""
    _render_html(_html_faixa_kpis(diag, periodo, no_cabecalho=False))


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


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Converte '#RRGGBB' em 'rgba(r,g,b,alpha)' para uso em bgcolor translúcido."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


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


def _render_widget_grafico_hub(titulo: str, fig, legenda: str = "") -> None:
    legenda = getattr(fig, "_hub_legenda", None) or legenda
    _render_html(
        f'<div class="widget-chart-zone">'
        f'<div class="widget-head">{_html.escape(titulo)}</div>'
        f'<div class="widget-chart-body">'
    )
    _chart_hub(fig)
    if legenda and legenda.strip():
        corpo = (
            legenda if legenda.lstrip().startswith("<")
            else _html.escape(legenda)
        )
        _render_html(f'<div class="widget-chart-nota">{corpo}</div>')
    _render_html("</div></div>")


def _render_hub_linha(
    cards: list[tuple[str, go.Figure | None, str]],
) -> None:
    """Uma linha do grid hub (até 3 gráficos)."""
    cols = st.columns(HUB_COL_LAYOUT, gap="small")
    for col, card in zip(cols, cards):
        with col:
            titulo, fig, legenda = card
            if fig is not None:
                _render_widget_grafico_hub(titulo, fig, legenda)


@st.fragment
def _fragment_hub_coluna(
    cards: list[tuple[str, go.Figure | None, str]],
    *,
    key: str = "hub_col",
) -> None:
    """Coluna do hub isolada em fragment (evita reruns desnecessários)."""
    _render_hub_coluna(cards)


@st.fragment
def _fragment_hub_delta(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
) -> None:
    """Painel Δ vs BR isolado em fragment."""
    _render_hub_delta_br_por_ano(df_dist_est, tabelas)


def _render_hub_coluna(
    cards: list[tuple[str, go.Figure | None, str]],
) -> None:
    """Empilha widgets hub verticalmente numa coluna."""
    for titulo, fig, legenda in cards:
        if fig is not None:
            _render_widget_grafico_hub(titulo, fig, legenda)


def _legenda_padrao(y_pos: float = 1.02, font_size: int = FONT_LEGEND, entry_width: int = 150):
    """Retorna dict de legenda padronizado para evitar sobreposição.

    - ``y_pos``: posição vertical (1.02 = acima do plot, -0.22 = abaixo).
    - ``font_size``: tamanho da fonte dos itens.
    - ``trace_gap``: espaçamento entre as traces na legenda.
    - ``entry_width``: largura fixa para cada item da legenda, evitando
      sobreposição quando há muitos itens. Ajustar conforme necessário.
    """
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


# ============================================================
# FUNÇÕES ANALÍTICAS
# ============================================================
def _diagnostico_ranking_desempenho_uf(
    tabelas: dict,
    anos_sel: list,
) -> dict:
    """Ranking e média BR via desempenho_uf.parquet (evita ~4,6M linhas sintéticas)."""
    out = {
        "media_estadual_br": np.nan,
        "ranking_ufs": pd.Series(dtype=float),
        "pos_ms": None,
        "total_ufs": 0,
        "pos_ms_recente": None,
        "total_ufs_recente": 0,
        "ano_referencia_pos": None,
        "ranking_ufs_recente": pd.Series(dtype=float),
        "media_br_ano_recente": np.nan,
    }
    df_desemp = tabelas.get("desempenho_uf", pd.DataFrame())
    if df_desemp.empty or not anos_sel:
        return out
    anos_int = [int(a) for a in anos_sel]
    sub = df_desemp[
        (df_desemp["dependencia"] == "Estadual") & (df_desemp["ano"].isin(anos_int))
    ].copy()
    if sub.empty:
        return out
    col_media = "media_media_geral" if "media_media_geral" in sub.columns else "media_geral"
    pesos = sub["estudantes"].fillna(0).astype(float)
    if pesos.sum() > 0:
        out["media_estadual_br"] = float(
            np.average(sub[col_media], weights=pesos)
        )
    def _media_pond(g):
        w = g["estudantes"].fillna(0).astype(float)
        return np.average(g[col_media], weights=w) if w.sum() > 0 else np.nan

    ranking = (
        sub.groupby("uf", observed=True)
        .apply(_media_pond)
        .dropna()
        .round(2)
        .sort_values(ascending=False)
    )
    ranking.index = ranking.index.astype(str).str.upper()
    ranking = ranking[ranking.index.str.len() == 2]
    out["ranking_ufs"] = ranking
    out["total_ufs"] = int(len(ranking))
    if "MS" in ranking.index:
        out["pos_ms"] = int(list(ranking.index).index("MS")) + 1
    ano_ref = max(anos_int)
    out["ano_referencia_pos"] = ano_ref
    sub_ano = sub[sub["ano"] == ano_ref]
    if not sub_ano.empty:
        ranking_ano = (
            sub_ano.set_index(sub_ano["uf"].astype(str).str.upper())[col_media]
            .dropna()
            .round(2)
            .sort_values(ascending=False)
        )
        ranking_ano = ranking_ano[ranking_ano.index.str.len() == 2]
        out["ranking_ufs_recente"] = ranking_ano
        out["total_ufs_recente"] = int(len(ranking_ano))
        if "MS" in ranking_ano.index:
            out["pos_ms_recente"] = int(list(ranking_ano.index).index("MS")) + 1
        refs = medias_referencia_por_ano(tabelas, ano_ref)
        mg = refs.get("MEDIA_GERAL", {})
        if mg.get("br") is not None and pd.notna(mg["br"]):
            out["media_br_ano_recente"] = float(mg["br"])
    return out


def _medias_periodo_kpi_rede_estadual(
    tabelas: dict,
    anos_sel: list[int],
    df_est: pd.DataFrame,
) -> dict[str, float]:
    """Médias MS/BR do período via referencias.parquet (mesma base dos gráficos Δ).

    População: presentes 2 dias, não eliminados, rede estadual. Ponderação
    anual pelo nº de participantes MS em cada ano.
    """
    if not tabelas or not anos_sel:
        return {}
    ms_v, br_v, pesos = [], [], []
    for ano in anos_sel:
        refs = medias_referencia_por_ano(tabelas, int(ano))
        mg = refs.get("MEDIA_GERAL", {})
        ms, br = mg.get("ms"), mg.get("br")
        if ms is None or br is None or pd.isna(ms) or pd.isna(br):
            continue
        n = int((df_est["NU_ANO"] == int(ano)).sum()) if not df_est.empty else 0
        if n <= 0:
            df_part = tabelas.get("participacao_ano", pd.DataFrame())
            if not df_part.empty:
                hit = df_part[
                    (df_part["ano"] == int(ano))
                    & (df_part["dependencia"] == "Estadual")
                ]
                if not hit.empty:
                    n = _safe_int_val(
                        hit.iloc[0].get("presentes_filt", hit.iloc[0].get("presentes")),
                    )
        if n <= 0:
            n = 1
        ms_v.append(float(ms))
        br_v.append(float(br))
        pesos.append(n)
    if not pesos or sum(pesos) <= 0:
        return {}
    media_ms = float(np.average(ms_v, weights=pesos))
    media_br = float(np.average(br_v, weights=pesos))
    return {
        "media_ms": media_ms,
        "media_br": media_br,
        "diff": media_ms - media_br,
    }


def diagnostico_estadual(
    df_filt_ms,
    df_bruta_ms,
    df_br_filt=None,
    *,
    tabelas: dict | None = None,
    anos_sel: list | None = None,
) -> dict:
    d = {}
    df_est = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    df_est_bruta = df_bruta_ms[df_bruta_ms["DEP_ADM"] == "Estadual"]
    usar_agregado = (
        (df_br_filt is None or df_br_filt.empty)
        and tabelas is not None
        and anos_sel
    )
    if usar_agregado:
        df_est_br = pd.DataFrame()
        rank = _diagnostico_ranking_desempenho_uf(tabelas, anos_sel)
    else:
        df_est_br = df_br_filt[df_br_filt["DEP_ADM"] == "Estadual"]
        rank = None

    # n_inscritos: soma participacao_ano.inscritos (ajustado em main via inscritos_estadual_ms)
    d["n_inscritos"] = len(df_est_bruta)
    d["n_part"] = len(df_est)
    d["tx_part"] = round(100 * d["n_part"] / d["n_inscritos"],
                         1) if d["n_inscritos"] else 0.0
    # Média ponderada pelo nº de participantes de cada ano no recorte
    # (cada estudante sintético herda a média anual; .mean() = ponderação).
    d["media_estadual_ms"] = float(
        df_est["MEDIA_GERAL"].mean()) if not df_est.empty else np.nan
    if rank is not None:
        d["media_estadual_br"] = rank["media_estadual_br"]
    else:
        d["media_estadual_br"] = float(
            df_est_br["MEDIA_GERAL"].mean()) if not df_est_br.empty else np.nan

    # KPI Δ: alinhar média BR à referencias.parquet (mesma fonte dos gráficos).
    # MS permanece a média direta dos participantes MS no recorte.
    if usar_agregado and anos_sel:
        kpi_ref = _medias_periodo_kpi_rede_estadual(tabelas, list(anos_sel), df_est)
        if kpi_ref:
            d["media_estadual_br"] = kpi_ref["media_br"]
    d["diff_vs_nacional"] = (
        d["media_estadual_ms"] - d["media_estadual_br"]
        if pd.notna(d["media_estadual_ms"]) and pd.notna(d["media_estadual_br"])
        else np.nan
    )

    serie = df_est.groupby("NU_ANO")["MEDIA_GERAL"].mean().round(2)
    d["media_ms_ano_recente"] = np.nan
    d["media_br_ano_recente"] = np.nan
    if not serie.empty:
        ano_recente = int(serie.index.max())
        d["media_ms_ano_recente"] = float(serie.loc[ano_recente])
        if rank is not None:
            d["media_br_ano_recente"] = rank.get("media_br_ano_recente", np.nan)
        elif not df_est_br.empty and "NU_ANO" in df_est_br.columns:
            br_ano = df_est_br[df_est_br["NU_ANO"] == ano_recente]
            if not br_ano.empty:
                d["media_br_ano_recente"] = float(br_ano["MEDIA_GERAL"].mean())
    d["serie_medias"] = serie
    if len(serie) >= 2:
        d["variacao_inicio_fim"] = float(serie.iloc[-1] - serie.iloc[0])
        d["ano_inicio"] = int(serie.index[0])
        d["ano_fim"] = int(serie.index[-1])
        d["melhor_ano"] = int(serie.idxmax())
        d["pior_ano"] = int(serie.idxmin())
        d["valor_melhor_ano"] = float(serie.max())
        d["valor_pior_ano"] = float(serie.min())
    else:
        d["variacao_inicio_fim"] = np.nan

    medias_areas = {}
    for c in COLS_NOTAS:
        v = df_est[c].mean()
        if pd.notna(v):
            medias_areas[c] = float(v)
    d["medias_areas"] = medias_areas
    if medias_areas:
        d["area_mais_forte"] = max(medias_areas, key=medias_areas.get)
        d["area_mais_fraca"] = min(medias_areas, key=medias_areas.get)

    if rank is not None:
        d["ranking_ufs"] = rank["ranking_ufs"]
        d["pos_ms"] = rank["pos_ms"]
        d["total_ufs"] = rank["total_ufs"]
        d["pos_ms_recente"] = rank["pos_ms_recente"]
        d["total_ufs_recente"] = rank["total_ufs_recente"]
        d["ano_referencia_pos"] = rank["ano_referencia_pos"]
        d["ranking_ufs_recente"] = rank["ranking_ufs_recente"]
    else:
        col_uf = "SG_UF_ESC" if "SG_UF_ESC" in df_br_filt.columns else "SG_UF_PROVA"
        ranking_ufs = (df_est_br.groupby(col_uf)["MEDIA_GERAL"].mean()
                       .dropna().round(2).sort_values(ascending=False))
        ranking_ufs = ranking_ufs[ranking_ufs.index.to_series().str.len() == 2]
        d["ranking_ufs"] = ranking_ufs
        if "MS" in ranking_ufs.index:
            d["pos_ms"] = int(list(ranking_ufs.index).index("MS")) + 1
            d["total_ufs"] = int(len(ranking_ufs))
        else:
            d["pos_ms"] = None
            d["total_ufs"] = int(len(ranking_ufs))
        d["pos_ms_recente"] = None
        d["total_ufs_recente"] = 0
        d["ano_referencia_pos"] = None
        d["ranking_ufs_recente"] = pd.Series(dtype=float)
        if not df_est_br.empty and "NU_ANO" in df_est_br.columns:
            anos_disp = sorted(df_est_br["NU_ANO"].dropna().unique())
            if anos_disp:
                ano_ref = int(anos_disp[-1])
                d["ano_referencia_pos"] = ano_ref
                df_est_br_ano = df_est_br[df_est_br["NU_ANO"] == ano_ref]
                ranking_ano = (df_est_br_ano.groupby(col_uf)["MEDIA_GERAL"].mean()
                               .dropna().round(2).sort_values(ascending=False))
                ranking_ano = ranking_ano[ranking_ano.index.to_series().str.len() == 2]
                d["ranking_ufs_recente"] = ranking_ano
                d["total_ufs_recente"] = int(len(ranking_ano))
                if "MS" in ranking_ano.index:
                    d["pos_ms_recente"] = int(list(ranking_ano.index).index("MS")) + 1
    return d


_PREFIXOS_ESC = {"EE", "CEJA", "CEE", "CEEJA", "EEF", "EEFM", "CE"}
_STOP_ABR = {"DE", "DA", "DO", "DAS", "DOS",
    "E", "EM", "A", "O", "AS", "OS", "NO", "NA"}


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


def classificar_tendencia(variacao: float) -> str:
    if variacao is None or np.isnan(variacao):
        return "neutro"
    if variacao >= 5:
        return "positivo"
    if variacao > -5:
        return "atencao"
    return "critico"


def classificar_participacao(pct: float) -> str:
    if pct >= 80:
        return "positivo"
    if pct >= 60:
        return "atencao"
    return "critico"


def classificar_posicao(pos: Optional[int], total: int) -> str:
    if pos is None or total <= 0:
        return "neutro"
    pct = pos / total
    if pct <= 0.33:
        return "positivo"
    if pct <= 0.66:
        return "atencao"
    return "critico"

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


def _fig_combo_media_participacao(
    *,
    anos: list[int],
    media_map: dict[int, float],
    tx_part_map: dict[int, float],
    delta_map: dict[int, float] | None = None,
    rotulo_media: str,
    rotulo_part: str,
    cor_linha: str,
    cor_texto_media: str,
    cor_barra: str,
    cor_borda_barra: str,
    cor_texto_barra: str,
    altura: int = ALTURA_HUB_MS,
    rotulos_part_na_base: bool = False,
    mostrar_rotulo_media: bool = True,
    legenda_interna: bool = False,
) -> go.Figure:
    """Combo hub: média (linha) + participação efetiva (barra) + Δ opcional."""
    from plotly.subplots import make_subplots

    if not anos or not media_map:
        return go.Figure()

    delta_map = delta_map or {}
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    y_media = [media_map.get(a, np.nan) for a in anos]
    y_valid = [v for v in y_media if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 12) if y_valid else 12
    tem_delta = any(pd.notna(delta_map.get(a, np.nan)) for a in anos)
    folga_topo = 1.22 if tem_delta else 0.72
    y_min = max(0, min(y_valid) - y_span * 0.45) if y_valid else 0
    y_max = min(1000, max(y_valid) + y_span * folga_topo) if y_valid else 1000

    if tx_part_map:
        y_part = [tx_part_map.get(a, np.nan) for a in anos]
        fig.add_trace(
            go.Bar(
                x=anos,
                y=y_part,
                name=rotulo_part,
                marker=dict(
                    color=cor_barra,
                    line=dict(color=cor_borda_barra, width=0.5),
                ),
                opacity=1.0,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"{rotulo_part}: %{{y:.1f}}%"
                    "<extra></extra>"
                ),
            ),
            secondary_y=True,
        )
        if rotulos_part_na_base:
            y_lbl_part = 1.5
            for ano in anos:
                v = tx_part_map.get(ano, np.nan)
                if pd.notna(v):
                    _anotacao_hub(
                        fig,
                        x=ano, xref="x",
                        y=y_lbl_part, yref="y2",
                        text=f"<b>{float(v):.0f}%</b>",
                        showarrow=False,
                        yanchor="bottom",
                        font=dict(
                            size=FONT_HUB_DATA, color=cor_texto_barra,
                            family="Plus Jakarta Sans, sans-serif",
                        ),
                    )
        else:
            txt_part, pos_part = _texto_posicao_barra(y_part)
            fig.update_traces(
                text=txt_part,
                textposition=pos_part,
                insidetextanchor="end",
                outsidetextfont=dict(
                    size=FONT_HUB_DATA, color=AZUL_ESCURO,
                    family="Plus Jakarta Sans, sans-serif",
                ),
                textfont=dict(
                    size=FONT_HUB_DATA, color=cor_texto_barra,
                    family="Plus Jakarta Sans, sans-serif",
                ),
                selector=dict(type="bar"),
            )

    txt_media = [
        f"<b>{media_map.get(a, np.nan):.0f}</b>"
        if mostrar_rotulo_media and pd.notna(media_map.get(a, np.nan)) else ""
        for a in anos
    ]
    fig.add_trace(
        go.Scatter(
            x=anos, y=y_media,
            name=rotulo_media,
            mode="lines+markers+text",
            text=txt_media,
            textposition="top center",
            textfont=dict(
                size=FONT_HUB_DATA, color=cor_texto_media,
                family="Plus Jakarta Sans, sans-serif",
            ),
            line=dict(color=cor_linha, width=2.5, shape="spline"),
            marker=dict(size=8, color=cor_linha, line=dict(width=1.5, color="white")),
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"{rotulo_media}: %{{y:.1f}}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    for ano in anos:
        media_val = media_map.get(ano, np.nan)
        delta = delta_map.get(ano, np.nan)
        if pd.notna(media_val) and pd.notna(delta):
            cor = COR_POSITIVO if delta >= 0 else COR_CRITICO
            _anotacao_hub(
                fig,
                x=ano, xref="x", y=media_val, yref="y",
                text=f"<b>Δ {delta:+.1f}</b>",
                showarrow=False, yanchor="bottom", yshift=34,
                font=dict(size=9, color=cor, family="Plus Jakarta Sans, sans-serif"),
            )

    y_part_max = max(
        (float(v) for v in tx_part_map.values() if pd.notna(v)),
        default=50.0,
    ) if tx_part_map else 50.0
    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, max(y_part_max * 1.22, 40)], secondary_y=True)
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(bargap=0.32, showlegend=legenda_interna)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(fig, topo=tem_delta)
    _aplicar_eixos_hub(fig, secondary_y=bool(tx_part_map))
    _aplicar_hover_hub(fig)
    return fig


def _fig_destaque_evolucao_ms(
    diag: dict,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure:
    """Destaque hub: média MS (linha) + tx part. efetiva (barra) e ΔBR."""
    serie_ms = diag.get("serie_medias", pd.Series(dtype=float))
    if serie_ms.empty:
        return go.Figure()

    ms_map = {int(k): float(v) for k, v in serie_ms.items() if pd.notna(v)}
    anos = sorted(ms_map.keys())
    serie_tx_efet = diag.get("serie_tx_part_efetiva", pd.Series(dtype=float))
    tx_efet_map = (
        {int(k): float(v) for k, v in serie_tx_efet.items() if pd.notna(v)}
        if not serie_tx_efet.empty else {}
    )
    serie_delta = diag.get("serie_delta_br", pd.Series(dtype=float))
    delta_map = (
        {int(k): float(v) for k, v in serie_delta.items() if pd.notna(v)}
        if not serie_delta.empty else {}
    )
    return _fig_combo_media_participacao(
        anos=anos,
        media_map=ms_map,
        tx_part_map=tx_efet_map,
        delta_map=delta_map,
        rotulo_media="Média estadual",
        rotulo_part="Participação efetiva",
        cor_linha=AZUL_PRINCIPAL,
        cor_texto_media=AZUL_ESCURO,
        cor_barra="rgba(46, 173, 110, 0.42)",
        cor_borda_barra="rgba(15, 100, 62, 0.55)",
        cor_texto_barra=COR_TEXTO_DENTRO_BARRA,
        altura=altura,
        rotulos_part_na_base=True,
        legenda_interna=False,
    )


def _fig_combo_ranking_ms_uf(
    anos: list[int],
    rank_part_map: dict[int, int],
    rank_des_map: dict[int, int],
    n_total: int,
    *,
    altura: int = ALTURA_HUB_RANK,
) -> go.Figure:
    """Combo hub espelhando média/part.: barras = pos. participação, linha = pos. média geral."""
    from plotly.subplots import make_subplots

    if not anos:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    y_part = [int(rank_part_map[a]) for a in anos]
    y_bar = [float(n_total + 1 - p) for p in y_part]
    y_des = [float(rank_des_map.get(a, np.nan)) for a in anos]
    y_valid = [v for v in y_des if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 3) if y_valid else 3
    y_min = max(0.5, min(y_valid) - y_span * 0.45) if y_valid else 0.5
    y_max = min(n_total + 0.5, max(y_valid) + y_span * 0.55) if y_valid else n_total + 0.5

    fig.add_trace(
        go.Scatter(
            x=anos, y=y_des,
            name="Posição na média",
            mode="lines+markers",
            customdata=np.array([
                [int(rank_des_map[a]), n_total] if pd.notna(rank_des_map.get(a))
                else [np.nan, n_total]
                for a in anos
            ]),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Posição na média: %{customdata[0]}º de %{customdata[1]}"
                "<extra></extra>"
            ),
            line=dict(color=AZUL_PRINCIPAL, width=2.5, shape="spline"),
            marker=dict(size=8, color=AZUL_PRINCIPAL, line=dict(width=1.5, color="white")),
        ),
        secondary_y=False,
    )
    txt_rank = [
        f"<b>{int(rank_des_map.get(a, np.nan))}º</b>"
        if pd.notna(rank_des_map.get(a, np.nan)) else ""
        for a in anos
    ]
    fig.data[0].update(
        mode="lines+markers+text",
        text=txt_rank,
        textposition="top center",
        textfont=dict(
            size=FONT_HUB_DATA, color=AZUL_ESCURO,
            family="Plus Jakarta Sans, sans-serif",
        ),
    )

    fig.add_trace(
        go.Bar(
            x=anos,
            y=y_bar,
            name="Posição na participação",
            customdata=np.array([[p, n_total] for p in y_part]),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Posição na participação: %{customdata[0]}º de %{customdata[1]}"
                "<extra></extra>"
            ),
            marker=dict(
                color="rgba(46, 173, 110, 0.42)",
                line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5),
            ),
            opacity=1.0,
        ),
        secondary_y=True,
    )
    fig.update_traces(
        text=[f"<b>{pos}º</b>" for pos in y_part],
        textposition="outside",
        textfont=dict(
            size=FONT_HUB_DATA, color=COR_TEXTO_DENTRO_BARRA,
            family="Plus Jakarta Sans, sans-serif",
        ),
        selector=dict(type="bar", name="Posição na participação"),
    )

    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, max(n_total * 1.22, 10)], secondary_y=True)
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(bargap=0.32)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(fig)
    _aplicar_eixos_hub(fig, secondary_y=True)
    _aplicar_hover_hub(fig)
    return fig


def _fig_ranking_participacao_nacional(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
    diag: dict,
    *,
    altura: int = ALTURA_HUB_RANK,
) -> go.Figure | None:
    """Ranking UF: posição MS em participação (barra) e média geral (linha)."""
    pos_part = _posicoes_ms_participacao_uf(
        tabelas, anos_sel, df_bruta_ms, df_filt_ms,
    )
    if not pos_part:
        return None

    pos_des = _posicoes_ms_desempenho_uf_por_ano(tabelas, anos_sel)
    part_map = {int(d["Ano"]): int(d["Posição"]) for d in pos_part}
    des_map = {int(d["Ano"]): int(d["Posição"]) for d in pos_des}
    anos = sorted(part_map.keys())
    n_total = max(
        max(int(d["Total"]) for d in pos_part),
        max((int(d["Total"]) for d in pos_des), default=0),
    )
    return _fig_combo_ranking_ms_uf(
        anos, part_map, des_map, n_total, altura=altura,
    )


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


def _enriquecer_participacao_taxas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante Inscritos e Tx_Inscrição em tabelas de participação."""
    out = df.copy()
    if "inscritos" in out.columns and "Inscritos" not in out.columns:
        out["Inscritos"] = pd.to_numeric(out["inscritos"], errors="coerce").fillna(0).astype(int)
    if "Inscritos" not in out.columns:
        out["Inscritos"] = pd.NA
    if "tx_inscricao" in out.columns and "Tx_Inscrição" not in out.columns:
        out["Tx_Inscrição"] = pd.to_numeric(out["tx_inscricao"], errors="coerce")
    if "Tx_Inscrição" not in out.columns or out["Tx_Inscrição"].isna().all():
        out["Tx_Inscrição"] = _pct_taxa(out["Inscritos"], out.get("Concluintes", pd.NA), casas=1)
    if "Tx_Part_Efetiva" not in out.columns:
        pres = out.get("Presentes", out.get("Estudantes", pd.NA))
        out["Tx_Part_Efetiva"] = _pct_taxa(pres, out.get("Concluintes", pd.NA), casas=1)
    return out


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

# ============================================================
# ABA 1 - SUMÁRIO EXECUTIVO
# ============================================================


def _df_dist_estadual_hub(tabelas: dict, df_filt_ms: pd.DataFrame) -> pd.DataFrame:
    """Distribuição agregada da rede estadual MS para gráficos hub."""
    df_est = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    anos = sorted(int(a) for a in df_est["NU_ANO"].dropna().unique())
    if not anos:
        return pd.DataFrame()
    return filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=anos,
        dependencia="Estadual",
    )


def _range_y_hub_evolucao(valores: list, *, folga: float = 0.012) -> tuple[float, float]:
    """Faixa Y com zoom máximo para evidenciar trajetória das áreas."""
    vals = [float(v) for v in valores if v is not None and pd.notna(v)]
    if not vals:
        return 0.0, 1000.0
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 4.0)
    pad_b = max(span * folga, 1.5)
    pad_t = max(span * (folga + 0.08), 3.0)
    return lo - pad_b, hi + pad_t


def _dtick_hub_evolucao(y0: float, y1: float) -> float:
    """Tick do eixo Y proporcional à faixa (passos menores = leitura mais nítida)."""
    span = max(y1 - y0, 5.0)
    if span <= 12:
        return 2.0
    if span <= 25:
        return 3.0
    if span <= 45:
        return 5.0
    return max(5.0, round(span / 7 / 5) * 5)


def _fig_hub_evolucao_areas_linhas(
    df_dist_est: pd.DataFrame,
    tabelas: dict | None = None,
    *,
    altura: int = ALTURA_HUB_EVOL,
) -> go.Figure | None:
    """Evolução compacta: média MS por área de conhecimento (sem média geral/BR)."""
    if df_dist_est is None or df_dist_est.empty:
        return None
    anos_int = sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
    if not anos_int:
        return None

    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    y_objetivas: list[float] = []
    y_redacao: list[float] = []

    for key in COLS_NOTAS:
        xs, ys = [], []
        for ano in anos_int:
            rows = df_dist_est[df_dist_est["ano"] == ano]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], key)
            if stats is None:
                continue
            xs.append(ano)
            ys.append(float(stats["mean"]))
        if not xs:
            continue

        cor = CORES_AREAS.get(key, AZUL_PRINCIPAL)
        sec = key == "NU_NOTA_REDACAO"
        if sec:
            y_redacao.extend(ys)
        else:
            y_objetivas.extend(ys)

        trace = go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            name=AREAS.get(key, key),
            line=dict(color=cor, width=2.0 if sec else 1.9),
            marker=dict(size=7, color=cor, line=dict(width=1, color="white")),
            hovertemplate=(
                f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>"
                "Ano: %{x}<br>Média: %{y:.1f}<extra></extra>"
            ),
        )
        fig.add_trace(trace, secondary_y=sec)

    if not fig.data:
        return None

    if y_objetivas:
        y0, y1 = _range_y_hub_evolucao(y_objetivas)
        dtick = _dtick_hub_evolucao(y0, y1)
        fig.update_yaxes(
            range=[y0, y1],
            dtick=dtick,
            showticklabels=False,
            ticks="",
            secondary_y=False,
        )
    if y_redacao:
        yr0, yr1 = _range_y_hub_evolucao(y_redacao)
        fig.update_yaxes(
            range=[yr0, yr1],
            dtick=_dtick_hub_evolucao(yr0, yr1),
            showticklabels=False,
            ticks="",
            secondary_y=True,
        )
    elif y_objetivas:
        fig.update_yaxes(showticklabels=False, ticks="", secondary_y=True)

    fig.update_xaxes(tickmode="linear", dtick=1)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(fig, topo=True, legenda_traces=False, legenda_areas=True)
    _aplicar_eixos_hub(fig, secondary_y=bool(y_redacao))
    _aplicar_hover_hub(fig)
    return fig


def _fig_hub_box_media_geral(
    df_dist_est: pd.DataFrame,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure | None:
    """Boxplot anual compacto — média geral (rede estadual)."""
    if df_dist_est is None or df_dist_est.empty:
        return None
    anos = sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
    xs, stats_list = [], []
    for ano in anos:
        rows = df_dist_est[df_dist_est["ano"] == ano]
        if rows.empty:
            continue
        stats = stats_box_quantis(rows.iloc[0], "MEDIA_GERAL")
        if stats is None:
            continue
        xs.append(str(ano))
        stats_list.append(stats)
    if not xs:
        return None

    fig = go.Figure()
    _add_box_series(
        fig, name="Média geral", color=AZUL_PRINCIPAL,
        x_vals=xs, stats_list=stats_list,
        showlegend=False, rotulos_quantis=False,
        box_width=0.72,
    )
    y0, y1 = _range_y_box_stats(stats_list, pad=38)
    fig.update_layout(
        yaxis=dict(range=[y0, y1]),
        boxmode="group",
    )
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=xs)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        notas=["Passe o mouse na caixa para ver quartis"],
        legenda_traces=False,
    )
    _aplicar_eixos_hub(fig)
    _aplicar_hover_hub(fig)
    return fig


def _cores_traces_ranking(fig: go.Figure) -> set[str] | None:
    """Cores das barras horizontais (para legenda dinâmica)."""
    for tr in fig.data:
        if getattr(tr, "type", None) != "bar":
            continue
        mc = getattr(getattr(tr, "marker", None), "color", None)
        if isinstance(mc, (list, tuple)):
            return set(mc)
    return None


def _estilo_fig_hub_ranking(
    fig: go.Figure,
    *,
    cores_ms_br: bool = False,
    refs_vline_ms_br: bool = False,
    notas: list[str] | None = None,
    cores_ranking: set[str] | None = None,
) -> go.Figure:
    """Tipografia legível para rankings horizontais compactos (CREs, etc.)."""
    fig.update_layout(title=dict(text=""))
    fig.update_xaxes(tickfont=dict(size=FONT_HUB_AXIS, color=TEMA["texto_secundario"]))
    fig.update_yaxes(
        tickfont=dict(size=FONT_HUB_AXIS, color=TEMA["texto_secundario"]),
        automargin=True,
        ticklabelstandoff=4,
    )
    fig.update_traces(
        textfont=dict(size=FONT_HUB_DATA, color=TEMA["texto"]),
        selector=dict(type="bar"),
    )
    cores_ranking = cores_ranking or _cores_traces_ranking(fig)
    nota_rank = notas[0] if notas else ""
    _fechar_fig_hub(
        fig,
        rank=True,
        notas=[nota_rank] if nota_rank else None,
        cores_ms_br=cores_ms_br,
        refs_vline=refs_vline_ms_br,
        legenda_traces=False,
        rank_compacto=bool(cores_ms_br or refs_vline_ms_br),
        cores_ranking=cores_ranking,
    )
    _aplicar_eixos_hub(fig, y_categorico=True)
    fig.update_xaxes(showticklabels=False, ticks="", showgrid=False)
    _aplicar_hover_hub(fig, horizontal=True)
    return fig


def _fig_hub_cre_combo_media_participacao(
    tabelas: dict,
    anos_sel: list,
    *,
    altura: int | None = None,
) -> go.Figure | None:
    """CREs em colunas: barras = participação %, linha = média geral."""
    from plotly.subplots import make_subplots

    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        return None
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        return None
    ano_ref = anos_validos[-1]
    sub_media = df_evol[
        (df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == "Estadual")
    ].copy()
    if "media_geral" not in sub_media.columns:
        return None
    sub_media = sub_media.dropna(subset=["media_geral"])

    cres = sorted(
        df_evol.loc[df_evol["dependencia"] == "Estadual", "CRE"].dropna().unique()
    )
    if not cres or sub_media.empty:
        return None
    part = _participacao_cre_tabela(tabelas, cres, ano_ref, "Estadual")
    if part.empty or "Tx_Part_Efetiva" not in part.columns:
        return None

    merged = sub_media[["CRE", "media_geral"]].merge(
        part[["CRE", "Tx_Part_Efetiva"]], on="CRE", how="inner",
    )
    merged = merged.dropna(subset=["media_geral", "Tx_Part_Efetiva"])
    if merged.empty:
        return None
    merged["_lbl"] = merged["CRE"].map(nome_cre_curto)
    merged = merged.sort_values("media_geral", ascending=True)

    labels = merged["_lbl"].astype(str).tolist()
    media_vals = merged["media_geral"].astype(float).tolist()
    tx_vals = merged["Tx_Part_Efetiva"].astype(float).tolist()

    refs = medias_referencia_por_ano(tabelas, ano_ref)
    mg = refs.get("MEDIA_GERAL", {}) if refs else {}
    media_ms = mg.get("ms")
    media_br = mg.get("br")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=labels,
            y=tx_vals,
            name="Participação",
            text=[f"<b>{tx:.0f}%</b>" for tx in tx_vals],
            textposition="outside",
            textfont=dict(
                size=FONT_HUB_DATA, color=COR_TEXTO_DENTRO_BARRA,
                family="Plus Jakarta Sans, sans-serif",
            ),
            marker=dict(
                color="rgba(46, 173, 110, 0.42)",
                line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5),
            ),
            hovertemplate=(
                "<b>%{x}</b><br>Participação: %{y:.1f}%<extra></extra>"
            ),
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=media_vals,
            mode="lines+markers+text",
            name="Média",
            text=[f"<b>{med:.0f}</b>" for med in media_vals],
            textposition="top center",
            textfont=dict(
                size=FONT_HUB_DATA, color=AZUL_ESCURO,
                family="Plus Jakarta Sans, sans-serif",
            ),
            line=dict(color=AZUL_PRINCIPAL, width=2.5, shape="spline"),
            marker=dict(
                size=8, color=AZUL_PRINCIPAL,
                line=dict(width=1.5, color="white"),
            ),
            hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
        ),
        secondary_y=False,
    )

    if media_ms is not None:
        fig.add_hline(
            y=media_ms, line_dash="dash", line_color=LARANJA_DESTAQUE, line_width=2.5,
        )
    if media_br is not None:
        fig.add_hline(
            y=media_br, line_dash="dot", line_color=COR_BRASIL, line_width=2,
        )

    y_valid = [v for v in media_vals if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 12) if y_valid else 12
    y_min = max(0, min(y_valid) - y_span * 0.45) if y_valid else 0
    y_max = min(1000, max(y_valid) + y_span * 0.72) if y_valid else 1000
    for ref in (media_ms, media_br):
        if ref is not None:
            y_min = min(y_min, float(ref) - 8.0)
            y_max = max(y_max, float(ref) + 8.0)

    tx_max = max(max(tx_vals) * 1.22, 40.0) if tx_vals else 60.0
    angulo = -48 if len(labels) > 6 else -32

    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, tx_max], secondary_y=True)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=labels,
        tickangle=angulo,
        tickfont=dict(size=8 if len(labels) > 8 else FONT_HUB_AXIS),
    )
    fig.update_layout(bargap=0.32)

    altura = altura or max(CHART_H_HUB, 300 if len(labels) > 8 else CHART_H_HUB)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        legenda_traces=True,
        refs_vline=True,
        notas=["Presentes 2 dias ÷ concluintes"],
    )
    _aplicar_eixos_hub(fig, secondary_y=True)
    fig.update_xaxes(showticklabels=True, ticks="outside", ticklen=4)
    fig.update_layout(margin=dict(b=max(52, 28 + len(labels) * 2)))
    _aplicar_hover_hub(fig)
    return fig


def _fig_hub_ranking_cre(
    tabelas: dict,
    anos_sel: list,
    *,
    altura: int = ALTURA_HUB_TERR,
) -> go.Figure | None:
    """Ranking horizontal de CREs por média geral (ano mais recente)."""
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        return None
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        return None
    ano_ref = anos_validos[-1]
    sub = df_evol[
        (df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == "Estadual")
    ].copy()
    col_media = "media_geral"
    if col_media not in sub.columns:
        return None
    sub = sub.dropna(subset=[col_media]).sort_values(col_media, ascending=True)
    if sub.empty:
        return None

    refs = medias_referencia_por_ano(tabelas, ano_ref)
    mg = refs.get("MEDIA_GERAL", {}) if refs else {}
    media_ms = mg.get("ms")
    media_br = mg.get("br")
    altura = _altura_hub_ranking(len(sub))
    fig = fig_ranking_horizontal(
        sub, "CRE", col_media,
        titulo="",
        cor=AZUL_PRINCIPAL,
        altura=altura,
        casas_decimais=1,
        media_ms=media_ms,
        media_br=media_br,
        x_range=[0, 1000],
        rotulo_media_ms="Média MS",
        rotulo_media_br="Média BR",
        modo_hub=True,
    )
    cores_usadas = _cores_ranking_presentes(
        sub[col_media].tolist(), media_ms, media_br,
    )
    return _estilo_fig_hub_ranking(
        fig, cores_ms_br=True, refs_vline_ms_br=True, cores_ranking=cores_usadas,
    )


def _fig_hub_participacao_cre(
    tabelas: dict,
    anos_sel: list,
    *,
    altura: int = ALTURA_HUB_TERR,
) -> go.Figure | None:
    """Taxa de participação efetiva por CRE (ano mais recente)."""
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        return None
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        return None
    ano_ref = anos_validos[-1]
    cres = sorted(
        df_evol.loc[df_evol["dependencia"] == "Estadual", "CRE"].dropna().unique()
    )
    if not cres:
        return None

    part = _participacao_cre_tabela(tabelas, cres, ano_ref, "Estadual")
    if part.empty or "Tx_Part_Efetiva" not in part.columns:
        return None
    sub = part.dropna(subset=["Tx_Part_Efetiva"]).sort_values(
        "Tx_Part_Efetiva", ascending=True,
    )
    if sub.empty:
        return None

    part_ms_df = participacao_ms_por_ano(tabelas, [ano_ref], "Estadual")
    media_ms = (
        float(part_ms_df.iloc[0]["Tx_Part_Efetiva"])
        if not part_ms_df.empty and pd.notna(part_ms_df.iloc[0]["Tx_Part_Efetiva"])
        else None
    )
    serie_br = _serie_tx_part_efetiva_br(tabelas, [ano_ref])
    media_br = float(serie_br.iloc[-1]) if not serie_br.empty else None
    altura = _altura_hub_ranking(len(sub))
    fig = fig_ranking_horizontal(
        sub, "CRE", "Tx_Part_Efetiva",
        titulo="",
        cor=COR_POSITIVO,
        altura=altura,
        casas_decimais=1,
        media_ms=media_ms,
        media_br=media_br,
        x_range=[0, 105],
        rotulo_media_ms="Média MS",
        rotulo_media_br="Média BR",
        modo_hub=True,
    )
    cores_usadas = _cores_ranking_presentes(
        sub["Tx_Part_Efetiva"].tolist(), media_ms, media_br,
    )
    return _estilo_fig_hub_ranking(
        fig,
        cores_ms_br=True,
        refs_vline_ms_br=True,
        cores_ranking=cores_usadas,
        notas=["Presentes 2 dias ÷ concluintes"],
    )


def _registros_delta_br_areas(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
    ano: int,
) -> pd.DataFrame | None:
    """Δ MS − BR por área em um ano (tabela ordenável por Delta)."""
    rows = df_dist_est[df_dist_est["ano"] == ano]
    if rows.empty:
        return None
    refs = medias_referencia_por_ano(tabelas, ano) if tabelas else {}
    registros = []
    for key in COLS_NOTAS:
        stats = stats_box_quantis(rows.iloc[0], key)
        if stats is None:
            continue
        ms = float(stats["mean"])
        br = None
        if refs and key in refs:
            br = refs[key].get("br")
        if (br is None or pd.isna(br)) and tabelas:
            br = media_nacional_ponderada(tabelas, ano, key, "Estadual")
        if br is None or pd.isna(br):
            continue
        registros.append({
            "AreaKey": key,
            "Abbr": AREAS.get(key, key),
            "Area": AREAS_COMPLETO.get(key, AREAS.get(key, key)),
            "Delta": ms - float(br),
            "MS": ms,
            "BR": float(br),
        })
    if not registros:
        return None
    return pd.DataFrame(registros)


def _ordenar_delta_br_areas(df: pd.DataFrame) -> pd.DataFrame:
    """Ordem fixa das áreas (CN→Redação) para comparar anos lado a lado."""
    ordem = {k: i for i, k in enumerate(COLS_NOTAS)}
    out = df.copy()
    out["_ord"] = out["AreaKey"].map(ordem)
    return out.sort_values("_ord", ascending=True).drop(columns=["_ord"])


def _x_range_delta_br_areas(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
    anos: list[int],
) -> list[float]:
    """Intervalo X comum (com folga para rótulos fora das barras)."""
    deltas: list[float] = []
    for ano in anos:
        df = _registros_delta_br_areas(df_dist_est, tabelas, ano)
        if df is not None and not df.empty:
            deltas.extend(df["Delta"].tolist())
    if not deltas:
        return [-22.0, 6.0]
    x_min = float(min(deltas))
    x_max = float(max(deltas))
    nucleo = max(x_max - x_min, 4.0)
    pad_rotulo = max(5.0, nucleo * 0.22)
    return [min(x_min - pad_rotulo, -2.0), max(x_max + pad_rotulo, 2.0)]


def _textpos_delta_br(valor: float, x_range: list[float]) -> str:
    """Rótulo dentro da barra quando há espaço; fora quando a barra é curta."""
    span = x_range[1] - x_range[0]
    return "inside" if abs(valor) >= span * 0.17 else "outside"


def _fig_hub_delta_br_painel_anual(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
) -> go.Figure | None:
    """Linha temporal: 30 barras verticais finas (6 anos × 5 áreas) — Δ MS − BR."""
    anos_plot = [
        ano for ano in ANOS_DISPONIVEIS
        if _registros_delta_br_areas(df_dist_est, tabelas, ano) is not None
    ]
    if not anos_plot:
        return None

    registros: list[dict] = []
    for ano in anos_plot:
        df_raw = _registros_delta_br_areas(df_dist_est, tabelas, ano)
        if df_raw is None or df_raw.empty:
            continue
        for _, row in _ordenar_delta_br_areas(df_raw).iterrows():
            registros.append({
                "ano": int(ano),
                "area_key": row["AreaKey"],
                "abbr": row["Abbr"],
                "area": row["Area"],
                "delta": float(row["Delta"]),
                "ms": float(row["MS"]),
                "br": float(row["BR"]),
            })
    if not registros:
        return None

    xs: list[int] = []
    ys: list[float] = []
    cores: list[str] = []
    abbrs: list[str] = []
    custom: list[list] = []
    for i, rec in enumerate(registros):
        xs.append(i)
        ys.append(rec["delta"])
        cores.append(CORES_AREAS.get(rec["area_key"], AZUL_PRINCIPAL))
        abbrs.append(rec["abbr"])
        custom.append([rec["area"], rec["ano"], rec["ms"], rec["br"]])

    max_abs = max(abs(v) for v in ys) if ys else 10.0
    y_lim = max(max_abs * 1.18, 6.0)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            marker_color=cores,
            marker_line=dict(width=0),
            width=0.62,
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                "Δ vs BR: %{y:+.1f} pts<br>"
                "MS: %{customdata[2]:.1f} · BR: %{customdata[3]:.1f}"
                "<extra></extra>"
            ),
            customdata=custom,
            showlegend=False,
        ),
    )
    fig.add_hline(
        y=0,
        line_color=TEMA["texto_muted"],
        line_width=1.5,
        opacity=0.65,
    )

    for x_i, delta in zip(xs, ys):
        if abs(delta) < 0.4:
            continue
        cor_txt = COR_POSITIVO if delta >= 0 else COR_CRITICO
        _anotacao_hub(
            fig,
            x=x_i,
            y=delta,
            text=f"<b>{delta:+.0f}</b>",
            showarrow=False,
            yanchor="bottom" if delta >= 0 else "top",
            yshift=4 if delta >= 0 else -4,
            font=dict(
                size=7,
                color=cor_txt,
                family="Plus Jakarta Sans, sans-serif",
            ),
        )

    fig.update_xaxes(
        tickvals=[],
        ticktext=[],
        showticklabels=False,
        showline=True,
        linecolor=TEMA["borda"],
        linewidth=1,
        showgrid=False,
    )

    anos_unicos = sorted({r["ano"] for r in registros})
    n_por_ano = len(COLS_NOTAS)
    for j, ano in enumerate(anos_unicos):
        idxs = [i for i, r in enumerate(registros) if r["ano"] == ano]
        if not idxs:
            continue
        x_centro = (min(idxs) + max(idxs)) / 2
        _anotacao_hub(
            fig,
            x=x_centro,
            xref="x",
            yref="paper",
            y=0.02,
            text=f"<b>{ano}</b>",
            showarrow=False,
            font=dict(
                size=9,
                color=AZUL_ESCURO,
                family="Plus Jakarta Sans, sans-serif",
            ),
        )
        if j > 0:
            sep = min(idxs) - 0.5
            fig.add_shape(
                type="line",
                x0=sep, x1=sep,
                xref="x",
                y0=-y_lim, y1=y_lim,
                yref="y",
                line=dict(color=TEMA["borda"], width=1, dash="dot"),
            )

    fig.update_yaxes(
        range=[-y_lim, y_lim],
        showticklabels=False,
        ticks="",
        showgrid=False,
        zeroline=False,
        showline=False,
    )

    fig = aplicar_tema(fig, CHART_H_HUB, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        legenda_traces=False,
        legenda_areas=True,
        cores_delta_br=True,
    )
    _aplicar_eixos_hub(fig, manter_linha_x=True)
    fig.update_layout(bargap=0.04, bargroupgap=0.02)
    _aplicar_hover_hub(fig, unified=False, horizontal=False)
    return fig


def _hub_tem_delta_br_areas(df_dist_est: pd.DataFrame, tabelas: dict) -> bool:
    for ano in ANOS_DISPONIVEIS:
        df = _registros_delta_br_areas(df_dist_est, tabelas, ano)
        if df is not None and not df.empty:
            return True
    return False


def _render_hub_delta_br_por_ano(
    df_dist_est: pd.DataFrame,
    tabelas: dict,
) -> bool:
    """Painel anual compacto: Δ vs BR (2019–2024), só rótulos de dados."""
    fig = _fig_hub_delta_br_painel_anual(df_dist_est, tabelas)
    if fig is None:
        return False
    _render_widget_grafico_hub("Diferença vs Brasil por área", fig)
    return True


def _fig_hub_medias_dependencia(
    df_filt_ms: pd.DataFrame,
    ano_ref: int,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure | None:
    """Média geral por dependência administrativa (ano de referência)."""
    df = df_filt_ms[df_filt_ms["NU_ANO"] == ano_ref]
    if df.empty:
        return None
    deps = [d for d in ORDEM_DEP if d in df["DEP_ADM"].dropna().unique()]
    if not deps:
        return None
    registros = []
    for dep in deps:
        sub = df[df["DEP_ADM"] == dep]
        if sub.empty:
            continue
        if "MEDIA_GERAL" in sub.columns and sub["MEDIA_GERAL"].notna().any():
            media = float(sub["MEDIA_GERAL"].mean())
        else:
            cols = [c for c in COLS_NOTAS if c in sub.columns]
            if not cols:
                continue
            media = float(sub[cols].mean(axis=1).mean())
        registros.append({"Dep": dep, "Média": round(media, 1)})
    if not registros:
        return None
    g = pd.DataFrame(registros)
    y_max = min(1000, float(g["Média"].max()) * 1.14)
    fig = go.Figure(go.Bar(
        x=g["Dep"], y=g["Média"],
        marker_color=[CORES_DEP.get(d, AZUL_PRINCIPAL) for d in g["Dep"]],
        text=g["Média"].apply(lambda x: f"{x:.0f}"),
        textposition="outside",
        textfont=dict(size=FONT_HUB_DATA),
        hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
    ))
    fig.update_yaxes(range=[0, y_max])
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        deps=deps,
        legenda_traces=False,
    )
    fig.update_xaxes(
        type="category",
        tickangle=-18,
        categoryorder="array",
        categoryarray=deps,
    )
    _aplicar_eixos_hub(fig)
    fig.update_xaxes(tickangle=-18)
    _aplicar_hover_hub(fig)
    return fig


def _fig_hub_box_areas_ano(
    df_dist_est: pd.DataFrame,
    ano_ref: int,
    *,
    altura: int = ALTURA_HUB_MS,
) -> go.Figure | None:
    """Boxplots das 5 áreas — ano de referência (rede estadual)."""
    rows = df_dist_est[df_dist_est["ano"] == ano_ref]
    if rows.empty:
        return None
    fig = go.Figure()
    all_stats: list[dict] = []
    for col in COLS_NOTAS:
        stats = stats_box_quantis(rows.iloc[0], col)
        if stats is None:
            continue
        nome = AREAS_COMPLETO.get(col, AREAS.get(col, col))
        all_stats.append(stats)
        _add_box_series(
            fig, name=nome, color=CORES_AREAS[col],
            x_vals=[nome], stats_list=[stats],
            showlegend=False, rotulos_quantis=False,
            box_width=0.55,
        )
    if not all_stats:
        return None
    y0, y1 = _range_y_box_stats(all_stats, pad=38)
    fig.update_layout(
        yaxis=dict(range=[y0, y1]),
        boxmode="group",
    )
    fig.update_xaxes(tickangle=-22)
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _fechar_fig_hub(
        fig,
        legenda_areas=True,
        notas=["Passe o mouse na caixa para ver quartis"],
        legenda_traces=False,
    )
    _aplicar_eixos_hub(fig)
    _aplicar_hover_hub(fig)
    return fig


def _render_hub_panorama(
    diag: dict,
    periodo: str,
    *,
    tabelas: dict | None = None,
    anos_sel: list | None = None,
    df_bruta_ms: pd.DataFrame | None = None,
    df_filt_ms: pd.DataFrame | None = None,
) -> None:
    """Grid 3×3 denso: participação, desempenho e território (padrão BI)."""
    tem_ms = len(diag.get("serie_medias", [])) > 0
    tem_rank = (
        tabelas is not None
        and anos_sel
        and df_bruta_ms is not None
        and df_filt_ms is not None
        and not df_bruta_ms.empty
    )
    tem_desemp = (
        tabelas is not None
        and df_filt_ms is not None
        and not df_filt_ms.empty
    )
    tem_terr = tabelas is not None and anos_sel

    df_dist_est = (
        _df_dist_estadual_hub(tabelas, df_filt_ms)
        if tem_desemp and df_filt_ms is not None and tabelas is not None
        else pd.DataFrame()
    )
    anos_validos = sorted(int(a) for a in (anos_sel or []))
    ano_ref = (
        int(max(df_dist_est["ano"]))
        if not df_dist_est.empty
        else (anos_validos[-1] if anos_validos else None)
    )

    fig_ms = _fig_destaque_evolucao_ms(diag) if tem_ms else None
    fig_rank_uf = (
        _fig_ranking_participacao_nacional(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms, diag,
        )
        if tem_rank else None
    )
    fig_evol = (
        _fig_hub_evolucao_areas_linhas(df_dist_est, tabelas)
        if tem_desemp and not df_dist_est.empty else None
    )
    fig_box_mg = (
        _fig_hub_box_media_geral(df_dist_est)
        if not df_dist_est.empty else None
    )
    fig_cre_combo = (
        _fig_hub_cre_combo_media_participacao(tabelas, anos_sel)
        if tem_terr else None
    )
    tem_delta = (
        not df_dist_est.empty and tabelas
        and _hub_tem_delta_br_areas(df_dist_est, tabelas)
    )
    fig_deps = (
        _fig_hub_medias_dependencia(df_filt_ms, ano_ref)
        if tem_desemp and ano_ref is not None and df_filt_ms is not None else None
    )
    fig_box_areas = (
        _fig_hub_box_areas_ano(df_dist_est, ano_ref)
        if not df_dist_est.empty and ano_ref is not None else None
    )

    if not any((
        fig_ms, fig_rank_uf, fig_evol, fig_box_mg,
        fig_cre_combo, tem_delta, fig_deps, fig_box_areas,
    )):
        return

    ano_lbl = ano_ref if ano_ref is not None else "—"

    card_ms = ("Rede estadual · média e participação", fig_ms, "")
    card_rank = ("Ranking entre estados · média e participação", fig_rank_uf, "")
    card_box_mg = ("Distribuição · média geral", fig_box_mg, "")
    card_evol = ("Evolução por área de conhecimento", fig_evol, "")
    card_cre_combo = (
        f"Coordenadorias · média e participação ({ano_lbl})", fig_cre_combo, "",
    )
    card_deps = (f"Média por dependência administrativa ({ano_lbl})", fig_deps, "")
    card_box_areas = (f"Distribuição por área ({ano_lbl})", fig_box_areas, "")

    _render_html(
        f'<div class="hub-panorama-grid" data-hub-build="{HUB_BUILD_ID}">'
    )
    col_esq, col_meio, col_dir = st.columns(HUB_COL_LAYOUT, gap="small")
    with col_esq:
        _fragment_hub_coluna(
            [c for c in (card_ms, card_rank, card_box_mg) if c[1] is not None],
            key="hub_col_esq",
        )
    with col_meio:
        _fragment_hub_coluna(
            [c for c in (card_evol,) if c[1] is not None],
            key="hub_col_meio",
        )
        if tem_delta:
            _fragment_hub_delta(df_dist_est, tabelas)
    with col_dir:
        _fragment_hub_coluna(
            [c for c in (card_cre_combo, card_deps, card_box_areas) if c[1] is not None],
            key="hub_col_dir",
        )
    _render_html("</div>")


def aba_sumario_executivo(
    diag: dict,
    anos_sel: list,
    *,
    modo_hub: bool = False,
    tabelas: dict | None = None,
    df_bruta_ms: pd.DataFrame | None = None,
    df_filt_ms: pd.DataFrame | None = None,
):
    periodo = (
        f"{min(anos_sel)}–{max(anos_sel)}"
        if anos_sel and len(anos_sel) >= 2
        else (str(anos_sel[0]) if anos_sel else "—")
    )
    if modo_hub:
        _render_hub_panorama(
            diag, periodo,
            tabelas=tabelas,
            anos_sel=anos_sel,
            df_bruta_ms=df_bruta_ms,
            df_filt_ms=df_filt_ms,
        )
        return

    titulo_secao(
        "Sumário executivo",
        "Leitura rápida dos principais indicadores da rede estadual.",
    )
    _faixa_concluintes_participantes(diag, periodo)

    tx_part_ref = diag.get("tx_part_efetiva") or diag.get("tx_part", 0)
    status_part = classificar_participacao(tx_part_ref)
    status_var = classificar_tendencia(diag.get("variacao_inicio_fim", 0))
    status_pos = classificar_posicao(
        diag.get("pos_ms"), diag.get("total_ufs", 0))

    c1, c2 = st.columns(2)
    kpi_card(c1,
             "Média geral (período)",
             fmt_float(diag["media_estadual_ms"]),
             f"Ponderada · BR: {fmt_float(diag['media_estadual_br'])}")
    kpi_card(c2,
             "Variação no período",
             fmt_delta(diag.get("variacao_inicio_fim", 0)),
             f"{diag.get('ano_inicio', '—')} → {diag.get('ano_fim', '—')}",
             status=status_var)

    titulo_secao("Principais achados",
                 "Destaques das análises de participação, desempenho e posicionamento da rede estadual de MS.")

    medias_areas = diag.get("medias_areas", {})

    # ── Linha 1: Participação · Desempenho Geral · Ranking Nacional ────────
    c1, c2, c3 = st.columns(3)

    with c1:
        _titulos_part = {
            "positivo": "Alta participação",
            "atencao":  "Participação intermediária",
            "critico":  "Baixa participação",
        }
        n_base = diag.get("n_concluintes") or diag.get("n_inscritos")
        label_base = "concluintes" if diag.get("n_concluintes") else "inscritos"
        n_efet = diag.get("n_presentes_filt") or diag.get("n_part")
        tx_txt = fmt_pct(tx_part_ref)
        tx_insc_txt = fmt_pct(diag.get("tx_inscricao")) if diag.get("tx_inscricao") is not None else None
        sufixo_insc = (
            f" Tx inscrição no período: {tx_insc_txt} (inscritos ÷ concluintes)."
            if tx_insc_txt else ""
        )
        _txt_part = {
            "positivo": (
                f"{tx_txt} dos {label_base} são participantes efetivos "
                f"({fmt_int(n_efet)} de {fmt_int(n_base)} — presentes nos 2 dias, sem eliminação)."
                f"{sufixo_insc}"
            ),
            "atencao": (
                f"Taxa de participação efetiva de {tx_txt} "
                f"({fmt_int(n_efet)} de {fmt_int(n_base)} {label_base}) — margem para ampliar cobertura."
                f"{sufixo_insc}"
            ),
            "critico": (
                f"Apenas {tx_txt} dos {label_base} são participantes efetivos "
                f"({fmt_int(n_efet)} de {fmt_int(n_base)}); a maioria não integra a análise de notas."
                f"{sufixo_insc}"
            ),
        }
        achado(status_part, _titulos_part[status_part], _txt_part[status_part])

    with c2:
        diff = diag.get("diff_vs_nacional", float("nan"))
        media_ms_val = diag.get("media_estadual_ms", float("nan"))
        if pd.isna(diff) or pd.isna(media_ms_val):
            achado("neutro", "Desempenho geral",
                   "Dados insuficientes para o período selecionado.")
        else:
            if diff > 2:
                status_desemp, titulo_desemp = "positivo", "Acima da média nacional"
            elif diff >= -2:
                status_desemp, titulo_desemp = "atencao", "Próximo à média nacional"
            else:
                status_desemp, titulo_desemp = "critico", "Abaixo da média nacional"
            achado(
                status_desemp, titulo_desemp,
                f"Média ponderada de MS ({periodo}): {fmt_float(media_ms_val)} pts — "
                f"{fmt_delta(diff)} em relação à rede estadual brasileira no mesmo período.",
            )

    with c3:
        pos_r = diag.get("pos_ms_recente")
        total_r = diag.get("total_ufs_recente", 0)
        ano_r = diag.get("ano_referencia_pos")
        pos_h = diag.get("pos_ms")
        total_h = diag.get("total_ufs", 0)
        if pos_r is not None:
            status_rank = classificar_posicao(pos_r, total_r)
            label_rank = f"Posição nacional · {ano_r}" if ano_r else "Posição nacional"
            achado(
                status_rank, label_rank,
                f"MS ocupa a {pos_r}ª posição entre {total_r} UFs na rede estadual "
                f"(referência: {ano_r}).",
            )
        elif pos_h is not None:
            status_rank = classificar_posicao(pos_h, total_h)
            achado(
                status_rank, "Posição histórica média",
                f"MS ocupa a {pos_h}ª posição entre {total_h} UFs na rede estadual "
                f"(média do período selecionado).",
            )
        else:
            achado("neutro", "Ranking nacional",
                   "Dados de posicionamento não disponíveis para o período selecionado.")

    st.markdown(" ")

    # ── Linha 2: Área Forte · Área Fraca · Tendência do Período ───────────
    d1, d2, d3 = st.columns(3)

    with d1:
        area_forte = diag.get("area_mais_forte")
        if area_forte and area_forte in medias_areas:
            nome_forte = AREAS_COMPLETO.get(area_forte, area_forte)
            val_forte = medias_areas[area_forte]
            achado(
                "positivo", f"Destaque: {nome_forte}",
                f"Melhor desempenho da rede estadual em {nome_forte} "
                f"(média {fmt_float(val_forte)} pts).",
            )
        else:
            achado("neutro", "Área de destaque",
                   "Dados insuficientes para o período selecionado.")

    with d2:
        area_fraca = diag.get("area_mais_fraca")
        if area_fraca and area_fraca in medias_areas:
            nome_fraca = AREAS_COMPLETO.get(area_fraca, area_fraca)
            val_fraca = medias_areas[area_fraca]
            achado(
                "critico", f"Atenção: {nome_fraca}",
                f"Maior desafio em {nome_fraca} (média {fmt_float(val_fraca)} pts) "
                f"— alvo prioritário de intervenção pedagógica.",
            )
        else:
            achado("neutro", "Área de atenção",
                   "Dados insuficientes para o período selecionado.")

    with d3:
        var = diag.get("variacao_inicio_fim", float("nan"))
        if pd.isna(var):
            achado("neutro", "Tendência do período",
                   "Selecione mais de um ano para ver a variação do período.")
        else:
            status_tend = classificar_tendencia(var)
            _titulos_tend = {
                "positivo": "Crescimento no período",
                "atencao":  "Estabilidade no período",
                "critico":  "Queda no período",
                "neutro":   "Tendência do período",
            }
            ano_ini = diag.get("ano_inicio", "—")
            ano_fim_d = diag.get("ano_fim", "—")
            melhor_a = diag.get("melhor_ano", "—")
            val_melhor = diag.get("valor_melhor_ano")
            pior_a = diag.get("pior_ano", "—")
            val_pior = diag.get("valor_pior_ano")
            achado(
                status_tend, _titulos_tend.get(status_tend, "Tendência"),
                f"Variação de {fmt_delta(var)} de {ano_ini} a {ano_fim_d}. "
                f"Melhor resultado em {melhor_a} ({fmt_float(val_melhor)} pts); "
                f"menor em {pior_a} ({fmt_float(val_pior)} pts).",
            )

# ============================================================
# ABA 2 - PANORAMA DE PARTICIPAÇÃO
# ============================================================


def _posicoes_ms_desempenho_uf_por_ano(
    tabelas: dict,
    anos_sel: list,
) -> list[dict]:
    """Posição do MS no ranking de média geral por UF (rede estadual), por ano."""
    df_des = tabelas.get("desempenho_uf", pd.DataFrame())
    if df_des.empty or not anos_sel:
        return []
    col_media = (
        "media_media_geral" if "media_media_geral" in df_des.columns else "media_geral"
    )
    if col_media not in df_des.columns:
        return []

    def _media_pond(g: pd.DataFrame) -> float:
        w = g["estudantes"].fillna(0).astype(float)
        return float(np.average(g[col_media], weights=w)) if w.sum() > 0 else np.nan

    posicoes: list[dict] = []
    for ano in sorted(int(a) for a in anos_sel):
        sub = df_des[
            (df_des["ano"] == ano) & (df_des["dependencia"] == "Estadual")
        ]
        if sub.empty:
            continue
        ranking = (
            sub.groupby("uf", observed=True)
            .apply(_media_pond)
            .dropna()
            .round(1)
            .sort_values(ascending=False)
        )
        ranking.index = ranking.index.astype(str).str.upper()
        ranking = ranking[ranking.index.str.len() == 2]
        if "MS" not in ranking.index:
            continue
        posicoes.append(dict(
            Ano=ano,
            Posição=int(list(ranking.index).index("MS")) + 1,
            Total=len(ranking),
            Media=float(ranking["MS"]),
        ))
    return posicoes


def _fig_hub_posicao_uf(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
    *,
    metrica: str = "part",
    altura: int = ALTURA_HUB_RANK,
) -> go.Figure | None:
    """Posição do MS entre UFs — um indicador por painel (capa em 4 colunas)."""
    if metrica == "part":
        dados = _posicoes_ms_participacao_uf(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms,
        )
        nome = "Participação"
        cor_linha = VERDE_MS
        cor_texto = COR_TEXTO_DENTRO_BARRA
        rotulos = [
            f"{int(d['Posição'])}º · {d['Taxa']:.0f}%"
            for d in dados
        ]
    else:
        dados = _posicoes_ms_desempenho_uf_por_ano(tabelas, anos_sel)
        nome = "Média geral"
        cor_linha = AZUL_PRINCIPAL
        cor_texto = AZUL_ESCURO
        rotulos = [
            f"{int(d['Posição'])}º · {d['Media']:.0f}"
            for d in dados
        ]

    if not dados:
        return None

    df = pd.DataFrame(dados)
    n_total = int(df["Total"].max()) if "Total" in df.columns else 27
    terco = n_total / 3
    cores = [_cor_posicao_terco(int(r["Posição"]), n_total) for _, r in df.iterrows()]

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=terco, fillcolor=COR_POSITIVO, opacity=0.07, line_width=0)
    fig.add_hrect(y0=terco, y1=2 * terco, fillcolor=COR_ATENCAO, opacity=0.06, line_width=0)
    fig.add_hrect(y0=2 * terco, y1=n_total + 1, fillcolor=COR_CRITICO, opacity=0.05, line_width=0)
    fig.add_trace(go.Scatter(
        x=df["Ano"], y=df["Posição"],
        mode="lines+markers+text",
        name=nome,
        text=rotulos,
        textposition="top center",
        textfont=dict(
            size=8, color=cor_texto,
            family="Plus Jakarta Sans, sans-serif",
        ),
        line=dict(color=cor_linha, width=2.2),
        marker=dict(size=7, color=cores, line=dict(width=1.2, color="white")),
    ))
    fig.update_yaxes(autorange="reversed", range=[0.5, n_total + 0.5])
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(
        showlegend=False,
        margin=dict(t=12, b=36, r=6, l=6),
        hovermode="x unified",
    )
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _aplicar_eixos_hub(fig)
    return fig


def _fig_posicao_ms_nacional(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
    *,
    altura: int = 360,
) -> go.Figure | None:
    """Versão combinada (sub-aba): participação + média geral."""
    pos_part = _posicoes_ms_participacao_uf(tabelas, anos_sel, df_bruta_ms, df_filt_ms)
    pos_des = _posicoes_ms_desempenho_uf_por_ano(tabelas, anos_sel)
    if not pos_part and not pos_des:
        return None

    n_total = 27
    if pos_part:
        n_total = max(n_total, max(p["Total"] for p in pos_part))
    if pos_des:
        n_total = max(n_total, max(p["Total"] for p in pos_des))
    terco = n_total / 3

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=terco, fillcolor=COR_POSITIVO, opacity=0.07, line_width=0)
    fig.add_hrect(y0=terco, y1=2 * terco, fillcolor=COR_ATENCAO, opacity=0.06, line_width=0)
    fig.add_hrect(y0=2 * terco, y1=n_total + 1, fillcolor=COR_CRITICO, opacity=0.05, line_width=0)

    if pos_part:
        df_p = pd.DataFrame(pos_part)
        cores_p = [_cor_posicao_terco(int(r["Posição"]), n_total) for _, r in df_p.iterrows()]
        fig.add_trace(go.Scatter(
            x=df_p["Ano"], y=df_p["Posição"],
            mode="lines+markers+text",
            name="Posição · participação",
            text=[f"{int(r['Posição'])}º · {r['Taxa']:.0f}%" for _, r in df_p.iterrows()],
            textposition="top center",
            textfont=dict(size=9, color=COR_TEXTO_DENTRO_BARRA, family="Plus Jakarta Sans, sans-serif"),
            line=dict(color=VERDE_MS, width=2.2),
            marker=dict(size=8, color=cores_p, line=dict(width=1.2, color="white")),
        ))

    if pos_des:
        df_d = pd.DataFrame(pos_des)
        cores_d = [_cor_posicao_terco(int(r["Posição"]), n_total) for _, r in df_d.iterrows()]
        fig.add_trace(go.Scatter(
            x=df_d["Ano"], y=df_d["Posição"],
            mode="lines+markers+text",
            name="Posição · média geral",
            text=[f"{int(r['Posição'])}º · {r['Media']:.0f}" for _, r in df_d.iterrows()],
            textposition="bottom center",
            textfont=dict(size=9, color=AZUL_ESCURO, family="Plus Jakarta Sans, sans-serif"),
            line=dict(color=AZUL_PRINCIPAL, width=2.2),
            marker=dict(size=8, color=cores_d, line=dict(width=1.2, color="white")),
        ))

    fig.update_yaxes(autorange="reversed", range=[0.5, n_total + 0.5])
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(
        legend=_legenda_padrao(y_pos=-0.22, font_size=9, entry_width=110),
        margin=dict(t=14, b=56, r=12, l=12),
        hovermode="x unified",
    )
    fig = aplicar_tema(fig, altura, limpar_titulo=True, modo_hub=True)
    _aplicar_eixos_hub(fig)
    return fig


def _posicoes_ms_participacao_uf(
    tabelas: dict,
    anos_sel: list,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
) -> list[dict]:
    """Ranking de participação por UF via participacao_uf.parquet (sem bases nacionais sintéticas)."""
    df_part = tabelas.get("participacao_uf", pd.DataFrame())
    if df_part.empty:
        return []
    posicoes_ms = []
    for ano in sorted(anos_sel):
        sub = df_part[
            (df_part["ano"] == int(ano)) & (df_part["dependencia"] == "Estadual")
        ].copy()
        if sub.empty:
            continue
        sub["taxa"] = np.where(
            sub["inscritos"] > 0,
            100 * sub["presentes_filt"] / sub["inscritos"],
            0.0,
        )
        sub = sub.sort_values("taxa", ascending=False)
        ranking = sub["uf"].astype(str).str.upper().tolist()
        insc_ms = len(df_bruta_ms[
            (df_bruta_ms["NU_ANO"] == ano) & (df_bruta_ms["DEP_ADM"] == "Estadual")
        ])
        part_ms = len(df_filt_ms[
            (df_filt_ms["NU_ANO"] == ano) & (df_filt_ms["DEP_ADM"] == "Estadual")
        ])
        taxa_ms = round(100 * part_ms / insc_ms, 1) if insc_ms else 0.0
        if "MS" in ranking:
            posicoes_ms.append(dict(
                Ano=int(ano),
                Posição=ranking.index("MS") + 1,
                Total=len(ranking),
                Taxa=taxa_ms,
            ))
    return posicoes_ms


def aba_panorama_participacao(df_bruta_ms, df_filt_ms, anos_sel,
                              df_bruta_ms_enriq=None, df_filt_ms_enriq=None,
                              df_bruta_nacional=None, df_filt_nacional=None,
                              df_concluintes=None, tabelas=None):
    titulo_secao(
        "Participação em relação aos demais estados",
        "Posição de Mato Grosso do Sul no ranking nacional da taxa de participação "
        "efetiva (presentes nos 2 dias ÷ concluintes do 3º ano, rede estadual). "
        "O funil e as taxas por ano estão no panorama geral acima.",
    )

    posicoes_ms: list[dict] = []
    if df_bruta_nacional is not None and df_filt_nacional is not None:
        col_uf_nac = "SG_UF_ESC" if "SG_UF_ESC" in df_bruta_nacional.columns else "SG_UF_PROVA"
        for ano in sorted(anos_sel):
            df_br_ano = df_bruta_nacional[(df_bruta_nacional["NU_ANO"] == ano) & (
                df_bruta_nacional["DEP_ADM"] == "Estadual")]
            df_fi_ano = df_filt_nacional[(df_filt_nacional["NU_ANO"] == ano) & (
                df_filt_nacional["DEP_ADM"] == "Estadual")]
            taxas_uf = []
            for uf in df_br_ano[col_uf_nac].dropna().unique():
                if len(str(uf)) != 2:
                    continue
                insc = len(df_br_ano[df_br_ano[col_uf_nac] == uf])
                part = len(df_fi_ano[df_fi_ano[col_uf_nac] == uf])
                pct = round(100 * part / insc, 1) if insc else 0.0
                taxas_uf.append(dict(UF=uf, Taxa=pct))
            taxas_uf.sort(key=lambda x: x["Taxa"], reverse=True)
            ranking = [t["UF"] for t in taxas_uf]
            insc_ms = len(df_bruta_ms[(df_bruta_ms["NU_ANO"] == ano) & (
                df_bruta_ms["DEP_ADM"] == "Estadual")])
            part_ms = len(df_filt_ms[(df_filt_ms["NU_ANO"] == ano) & (
                df_filt_ms["DEP_ADM"] == "Estadual")])
            taxa_ms = round(100 * part_ms / insc_ms, 1) if insc_ms else 0.0
            if "MS" in ranking:
                posicoes_ms.append(
                    dict(Ano=ano, Posição=ranking.index("MS") + 1,
                         Total=len(ranking), Taxa=taxa_ms))
    elif tabelas is not None:
        posicoes_ms = _posicoes_ms_participacao_uf(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms)

    if tabelas is not None and not df_bruta_ms.empty and not df_filt_ms.empty:
        fig_pos = _fig_posicao_ms_nacional(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms, altura=400,
        )
        if fig_pos is not None:
            _chart(fig_pos)
            st.caption(
                "Versão ampliada do gráfico da capa. "
                "1º lugar = melhor posição entre as UFs (rede estadual)."
            )
        else:
            st.info("Não foi possível calcular a posição nacional do MS.")
    elif posicoes_ms:
        st.info("Dados de posição disponíveis apenas via agregados participacao_uf.")
    else:
        st.info("Não foi possível calcular a posição nacional do MS.")

# ============================================================
# ABA 3 - DESEMPENHO PEDAGÓGICO
# ============================================================


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


def aba_desempenho(df_filt_ms, tabelas=None, df_notas_individuais=None, anos_sel=None):
    titulo_secao(
        "Desempenho pedagógico — evolução temporal e distribuição",
        "Acompanhamento das notas por área: médias, medianas e dispersão ao longo dos anos."
    )

    # ----- DATAFRAMES DE REFERÊNCIA (agregados; sem bases nacionais sintéticas) -----
    df_est_ms = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    deps_exibir = [
        d for d in ORDEM_DEP if d in df_filt_ms["DEP_ADM"].dropna().unique()]
    tabelas = tabelas or {}
    anos_sel_dist = sorted(df_est_ms["NU_ANO"].dropna().unique())
    df_dist_est = filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=[int(a) for a in anos_sel_dist],
        dependencia="Estadual",
    )
    df_dist_todos = filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=[int(a) for a in anos_sel_dist],
    )

    # Cobertura do agregado de distribuição vs. microdados. Os boxplots leem o
    # parquet distribuicao_ms; se ele cobre menos anos, o gráfico "colapsa" para
    # os poucos anos disponíveis — sinalizamos isso explicitamente nas seções.
    anos_micro_dist = sorted(int(a) for a in anos_sel_dist)
    anos_dist_disp = (
        sorted(int(a) for a in df_dist_est["ano"].dropna().unique())
        if not df_dist_est.empty else []
    )
    anos_faltantes_dist = [a for a in anos_micro_dist if a not in anos_dist_disp]

    def _aviso_cobertura_distribuicao() -> None:
        if anos_faltantes_dist and anos_dist_disp:
            st.warning(
                "O agregado de distribuição (`distribuicao_ms.parquet`) cobre apenas "
                f"{', '.join(str(a) for a in anos_dist_disp)}, mas os microdados têm "
                f"{', '.join(str(a) for a in anos_micro_dist)}. Por isso os boxplots "
                "mostram menos anos que os demais gráficos. Para corrigir, regenere os "
                "agregados: `python gerar_dados_agregados.py`."
            )

    # ===== BARRA DE FILTROS UNIFICADA (camada de status — topo da aba) =====
    anos_disp = sorted(int(a) for a in df_est_ms["NU_ANO"].dropna().unique())
    if not anos_disp:
        st.info("Sem dados de desempenho para o recorte selecionado.")
        return
    area_keys_bar = list(AREAS.keys())
    deps_bar = deps_exibir or ["Estadual"]

    cbar1, cbar2, cbar3 = st.columns(3)
    with cbar1:
        ano_foco = int(st.selectbox(
            "Ano", options=sorted(anos_disp, reverse=True), index=0,
            key="desemp_ano",
        ))
    with cbar2:
        idx_area = area_keys_bar.index("MEDIA_GERAL") if "MEDIA_GERAL" in area_keys_bar else 0
        area_foco = st.selectbox(
            "Área de conhecimento", options=area_keys_bar,
            index=idx_area, format_func=nome_area_ext, key="desemp_area",
        )
    with cbar3:
        idx_dep = deps_bar.index("Estadual") if "Estadual" in deps_bar else 0
        dep_foco = st.selectbox(
            "Dependência", options=deps_bar, index=idx_dep, key="desemp_dep",
        )
    label_area_foco = nome_area_ext(area_foco)

    st.caption(
        "Os indicadores abaixo refletem **ano · área · dependência** selecionados acima. "
        "As distribuições detalhadas e estatísticas anuais referem-se à **rede estadual**; "
        "a comparação entre dependências aparece em seção própria."
    )

    # ===== FAIXA DE KPIs (status) =====
    _df_dep_ms = df_filt_ms[df_filt_ms["DEP_ADM"] == dep_foco]

    def _coluna_notas(df, ano):
        if area_foco not in df.columns:
            return pd.Series(dtype=float)
        return pd.to_numeric(
            df.loc[df["NU_ANO"] == ano, area_foco], errors="coerce"
        ).dropna()

    _col_ms = _coluna_notas(_df_dep_ms, ano_foco)
    _row_dist = df_dist_est[df_dist_est["ano"] == ano_foco] if not df_dist_est.empty else pd.DataFrame()
    _stats_foco = (
        stats_box_quantis(_row_dist.iloc[0], area_foco)
        if not _row_dist.empty and dep_foco == "Estadual" else None
    )
    kpi_media = (
        float(_stats_foco["mean"]) if _stats_foco
        else (_col_ms.mean() if not _col_ms.empty else float("nan"))
    )
    kpi_mediana = (
        float(_stats_foco["median"]) if _stats_foco
        else (_col_ms.median() if not _col_ms.empty else float("nan"))
    )
    kpi_n = int(_stats_foco["n"]) if _stats_foco else int(_col_ms.shape[0])
    kpi_media_br = media_nacional_ponderada(tabelas, ano_foco, area_foco, dep_foco)
    kpi_delta = (
        kpi_media - kpi_media_br
        if (pd.notna(kpi_media) and pd.notna(kpi_media_br)) else float("nan")
    )

    _ano_prev = max((a for a in anos_disp if a < ano_foco), default=None)
    kpi_var = float("nan")
    if _ano_prev is not None and not _col_ms.empty:
        _col_prev = _coluna_notas(_df_dep_ms, _ano_prev)
        if not _col_prev.empty:
            kpi_var = kpi_media - _col_prev.mean()

    def _status_delta(d):
        if pd.isna(d):
            return ""
        if d >= 0:
            return "positivo"
        if d >= -10:
            return "atencao"
        return "critico"

    def _txt_sinal(v):
        if pd.isna(v):
            return "—"
        return ("+" if v >= 0 else "−") + fmt_float(abs(v))

    _sd = _status_delta(kpi_delta)
    _sv = "positivo" if (pd.notna(kpi_var) and kpi_var >= 0) else (
        "critico" if pd.notna(kpi_var) else "")

    _pop_foco = (
        _populacao_estadual_ano(tabelas, ano_foco)
        if dep_foco == "Estadual"
        else {"presentes_filt": None, "taxa_part": None}
    )
    if _pop_foco.get("presentes_filt"):
        _pres_txt = fmt_int(_pop_foco["presentes_filt"])
        _pres_sub = (
            fmt_pct(_pop_foco["taxa_part"]) + " dos concluintes"
            if _pop_foco.get("taxa_part") is not None
            else "presentes 2 dias, sem eliminados"
        )
    else:
        _pres_txt = fmt_int(kpi_n)
        _pres_sub = "estudantes com nota na área"

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    kpi_card(kc1, f"Média · {label_area_foco}", fmt_float(kpi_media),
             f"{ano_foco} · {dep_foco}", _sd)
    kpi_card(kc2, "Δ vs Brasil", _txt_sinal(kpi_delta), "pontos na média", _sd)
    kpi_card(kc3, "Mediana", fmt_float(kpi_mediana), label_area_foco, "")
    kpi_card(kc4, f"Variação vs {_ano_prev if _ano_prev is not None else '—'}",
             _txt_sinal(kpi_var), "na média anual", _sv)
    kpi_card(kc5, "Presentes (estadual)" if dep_foco == "Estadual" else "Estudantes",
             _pres_txt, _pres_sub, "")

    # ----- 1. EVOLUÇÃO POR ÁREA — rede estadual (média + dispersão + Brasil, unificado) -----
    titulo_secao(
        "Evolução por área — rede estadual",
        "Nota média anual por área de conhecimento, com a dispersão interna (faixa "
        "Q1–Q3) e a comparação com o Brasil, em uma única visão."
    )
    st.markdown(
        _legenda_inline([
            f"<span style='color:{AZUL_PRINCIPAL};font-weight:bold;'>━━━</span> Média MS (rede estadual)",
            "<span style='color:#7e8fa6;font-weight:bold;'>- - -</span> Mediana MS",
            "<span style='background:rgba(0,63,127,0.14);padding:2px 6px;border-radius:3px;font-weight:bold;'>▓▓▓</span> Faixa Q1–Q3 (MS)",
            "<span style='color:#5C6B7E;font-weight:bold;'>- ✕ -</span> Média Brasil",
            "<b>Δ%</b> Variação da média no período",
        ]),
        unsafe_allow_html=True,
    )
    _aviso_cobertura_distribuicao()
    fig_evol = _fig_evolucao_unificada(df_dist_est, tabelas=tabelas)
    if fig_evol is None:
        st.info("Sem dados de evolução por área para o período selecionado.")
    else:
        _chart(fig_evol)

    # ----- 3. DISTRIBUIÇÃO DAS NOTAS AO LONGO DOS ANOS — área selecionada | todas as áreas -----
    titulo_secao(
        "Distribuição das notas ao longo dos anos — rede estadual MS",
        "Boxplots por ano (quantis agregados dos microdados): caixa = Q1–Q3, linha central = "
        "mediana, × = média; hastes = limites não-discrepantes (1,5×IQR). Exclui eliminados."
    )
    _aviso_cobertura_distribuicao()
    MODO_DIST_AREA = f"Área selecionada — {label_area_foco}"
    MODO_DIST_TODAS = "Todas as áreas"
    modo_dist = st.radio(
        "Visualização da distribuição",
        [MODO_DIST_AREA, MODO_DIST_TODAS],
        horizontal=True,
        key="desemp_distribuicao_modo",
        label_visibility="collapsed",
    )

    if df_dist_est.empty:
        st.info(
            "Sem dados de distribuição disponíveis para a rede estadual MS. "
            "Regenere os agregados com: python gerar_dados_agregados.py"
        )
    elif modo_dist == MODO_DIST_TODAS:
        st.markdown(
            _legenda_inline([
                "<b>▢</b> Caixa: Q1, mediana, Q3 (×: média)",
                "<b>━</b> Bigodes: limites não-discrepantes (1,5×IQR)",
                "<b>Hover</b>: Máx · Q3 · mediana · Q1 · Mín · n",
                "<em>Recorte:</em> escolas estaduais do MS · presentes 2 dias · sem eliminados",
            ]),
            unsafe_allow_html=True,
        )
        fig_dist_todas = _fig_box_distribuicao_areas(df_dist_est)
        if fig_dist_todas is None:
            st.info("Sem dados de distribuição por área para o período selecionado.")
        else:
            _chart(fig_dist_todas)
    else:
        area_sel = area_foco
        label_area_sel = label_area_foco
        anos_box_area = [str(int(a)) for a in sorted(df_dist_est["ano"].unique().tolist())]

        serie_ms_anual = pd.Series(
            {
                int(r["ano"]): stats_box_quantis(r, area_sel)["mean"]
                for _, r in df_dist_est.iterrows()
                if stats_box_quantis(r, area_sel) is not None
            },
            dtype=float,
        ).sort_index()
        serie_br_anual = serie_media_nacional_dep(
            tabelas,
            [int(a) for a in anos_box_area],
            area_sel,
            "Estadual",
        )

        # Converte índices para string e alinha ao eixo X das caixas
        if not serie_ms_anual.empty:
            serie_ms_anual.index = serie_ms_anual.index.astype(str)
            serie_ms_anual = serie_ms_anual.reindex(anos_box_area).dropna()
        if not serie_br_anual.empty:
            serie_br_anual.index = serie_br_anual.index.astype(str)
            serie_br_anual = serie_br_anual.reindex(anos_box_area).dropna()

        cor_area = AZUL_PRINCIPAL
        fig_box_area = go.Figure()

        # Série única (área selecionada) — um trace com x = anos (evita colapso)
        xs_ano: list[str] = []
        stats_ano: list[dict] = []
        for ano in anos_box_area:
            rows = df_dist_est[df_dist_est["ano"] == int(ano)]
            if rows.empty:
                continue
            stats = stats_box_quantis(rows.iloc[0], area_sel)
            if stats is None:
                continue
            xs_ano.append(str(int(ano)))
            stats_ano.append(stats)
        _add_box_series(
            fig_box_area, name=label_area_sel, color=cor_area,
            x_vals=xs_ano, stats_list=stats_ano,
            legendgroup="caixas", showlegend=True, rotulo_mediana=True,
        )

        # Configura eixo X categórico ANTES de adicionar os Scatter
        fig_box_area.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_area,
        )

        # Referências MS/BR — linhas sem rótulo no ponto (evita sobrepor rótulos da caixa)
        if not serie_ms_anual.empty:
            fig_box_area.add_trace(
                go.Scatter(
                    x=serie_ms_anual.index.tolist(),
                    y=serie_ms_anual.values.tolist(),
                    mode="lines+markers",
                    name="Média MS — rede estadual",
                    line=dict(color=AZUL_PRINCIPAL, width=2.5),
                    marker=dict(size=7, color=AZUL_PRINCIPAL, symbol="circle"),
                    legendgroup="medias_ms",
                    showlegend=True,
                    hovertemplate="Média MS: %{y:.1f}<extra></extra>",
                )
            )

        if not serie_br_anual.empty:
            fig_box_area.add_trace(
                go.Scatter(
                    x=serie_br_anual.index.tolist(),
                    y=serie_br_anual.values.tolist(),
                    mode="lines+markers",
                    name="Média BR — rede estadual",
                    line=dict(color=COR_BRASIL, width=2, dash="dot"),
                    marker=dict(size=6, color=COR_BRASIL, symbol="x"),
                    legendgroup="medias_br",
                    showlegend=True,
                    hovertemplate="Média BR: %{y:.1f}<extra></extra>",
                )
            )

        # Range Y fixo (quantis já definem a escala)
        fig_box_area.update_layout(
            title=f"Boxplot anual — {label_area_sel} (rede estadual MS)",
            yaxis=dict(range=[0, 1000], title="Nota"),
            xaxis=dict(title="Ano", type="category"),
            boxmode="group",
        )

        media_ms_global = float(serie_ms_anual.mean()) if not serie_ms_anual.empty else None
        media_br_global = float(serie_br_anual.mean()) if not serie_br_anual.empty else None
        st.markdown(
            _mini_legenda_medias_html(
                media_ms_global, media_br_global,
                sufixo="variação anual",
            ),
            unsafe_allow_html=True,
        )

        fig_box_area = _finalizar_boxplot(
            fig_box_area,
            f"Boxplot anual — {label_area_sel} (rede estadual MS)",
            altura=CHART_H_BOX_WIDE,
            eixo_x="Ano",
            n_legend=3,
        )
        fig_box_area.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_area,
        )
        st.caption(
            "Número acima de cada caixa: mediana do ano. "
            "Passe o mouse para ver Máx, Q3, mediana, Q1, Mín e n. "
            "Linhas: média anual MS (azul) e BR (cinza tracejado)."
        )
        _chart(fig_box_area)

    # ----- 3b. Histogramas + comparação por dependência (camada de detalhe) -----
    anos_presentes = sorted(df_dist_est["ano"].unique()) if not df_dist_est.empty else []
    if not anos_presentes:
        st.info("Nenhum ano disponível para análise por área.")
    else:
        titulo_secao(
            "Distribuição de notas por ano — histogramas e dependências",
            "O ano da barra de filtros (topo da aba) define os histogramas por área "
            "e a comparação entre dependências administrativas. Conteúdo detalhado — "
            "abra o painel abaixo para explorar."
        )
        with st.expander(
            "Abrir histogramas por área e comparação entre dependências",
            expanded=False,
        ):
            _secao_detalhe_ano_desempenho(
                tabelas, ano_foco, df_est_ms,
                df_dist_est, df_dist_todos, deps_exibir, df_notas_individuais,
            )

    # ----- 4. Estatísticas anuais (camada de detalhe — divulgação progressiva) -----
    with st.expander("Estatísticas anuais — rede estadual (tabela detalhada)", expanded=False):
        st.caption(
            f"Indicadores por ano para **{nome_area_ext(area_foco)}**. "
            "Concluintes: rede estadual de MS (planilha SED, quando disponível nos agregados). "
            "Presentes: estudantes presentes nos 2 dias e não eliminados em nenhuma área ou redação."
        )
        if not anos_presentes:
            st.info("Nenhum ano disponível para a área selecionada.")
        else:
            col_media = f"Média · {label_area_foco}"
            linhas_tab = []
            for ano in anos_presentes:
                rows = df_dist_est[df_dist_est["ano"] == ano]
                stats = stats_box_quantis(rows.iloc[0], area_foco) if not rows.empty else None
                pop = _populacao_estadual_ano(tabelas, int(ano))
                part_ano = participacao_ms_por_ano(tabelas, [int(ano)], dep_foco)
                insc_ano = (
                    int(part_ano.iloc[0]["Inscritos"])
                    if not part_ano.empty and pd.notna(part_ano.iloc[0].get("Inscritos")) else None
                )
                tx_insc_ano = (
                    float(part_ano.iloc[0]["Tx_Inscrição"])
                    if not part_ano.empty and pd.notna(part_ano.iloc[0].get("Tx_Inscrição")) else None
                )
                linhas_tab.append({
                    "Ano": str(int(ano)),
                    "Concluintes (estadual)": fmt_int(pop["concluintes"]) if pop["concluintes"] else "—",
                    "Inscritos": fmt_int(insc_ano) if insc_ano else "—",
                    "Tx inscrição": fmt_pct(tx_insc_ano) if tx_insc_ano is not None else "—",
                    "Presentes (2 dias, sem elim.)": fmt_int(pop["presentes_filt"]) if pop["presentes_filt"] else "—",
                    "Tx part. efetiva": fmt_pct(pop["taxa_part"]) if pop["taxa_part"] is not None else "—",
                    col_media: fmt_float(stats["mean"]) if stats is not None else "—",
                    "Mediana": fmt_float(stats["median"]) if stats is not None else "—",
                })
            df_estat_anual = pd.DataFrame(linhas_tab).set_index("Ano")
            st.dataframe(df_estat_anual, width="stretch")
# ============================================================
# ABA 4 - ESCOLAS 2024
# ============================================================
def aba_escolas_2024(df_ms_enriq_2024, ano=2024, df_br=None, df_bruta_ms=None, df_concluintes=None, tabelas=None, df_notas_individuais=None):
    titulo_secao(
        f"Escolas estaduais em {ano}",
        "Detalhamento por unidade escolar, com nome, município e CRE."
    )

    df_est = df_ms_enriq_2024[df_ms_enriq_2024["DEP_ADM"] == "Estadual"].copy()
    if df_est.empty:
        st.warning(f"Sem dados de escolas estaduais em {ano}.")
        return

    st.markdown("### Análise por escola")
    col_filt_area, col_filt_min = st.columns(2)
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_escola_2024"
        )
    with col_filt_min:
        min_part = st.slider(
            "Mínimo de participantes por escola",
            3, 50, 10,
            key="min_part_escola_2024"
        )

    refs_ano = medias_referencia_por_ano(tabelas or {}, int(ano)) if tabelas else {}
    medias_ref = refs_ano.get(area, {})
    if not medias_ref:
        df_br_est = (
            df_br[(df_br["DEP_ADM"] == "Estadual") & (df_br["NU_ANO"] == ano)]
            if df_br is not None else None
        )
        medias_ref = (
            calcular_medias_referencia(df_est, df_br_est, area)
            if df_br_est is not None else {"ms": None, "br": None}
        )

    medias_ref_ms_area = {}
    medias_ref_br_area = {}
    for col in COLS_NOTAS:
        ref_col = refs_ano.get(col, {}) if refs_ano else {}
        medias_ref_ms_area[col] = (
            float(ref_col.get("ms")) if ref_col.get("ms") is not None and pd.notna(ref_col.get("ms"))
            else (float(df_est[col].dropna().mean()) if not df_est.empty else np.nan)
        )
        if ref_col.get("br") is not None and pd.notna(ref_col.get("br")):
            medias_ref_br_area[col] = float(ref_col["br"])
        elif df_br is not None:
            df_br_est = df_br[(df_br["DEP_ADM"] == "Estadual") & (df_br["NU_ANO"] == ano)]
            medias_ref_br_area[col] = (
                float(df_br_est[col].dropna().mean()) if not df_br_est.empty else np.nan
            )
        else:
            medias_ref_br_area[col] = np.nan
    if "MEDIA_GERAL" in df_est.columns:
        mg_ref = refs_ano.get("MEDIA_GERAL", {}) if refs_ano else {}
        medias_ref_ms_area["MEDIA_GERAL"] = (
            float(mg_ref["ms"]) if mg_ref.get("ms") is not None and pd.notna(mg_ref.get("ms"))
            else (float(df_est["MEDIA_GERAL"].dropna().mean()) if not df_est.empty else np.nan)
        )
        if mg_ref.get("br") is not None and pd.notna(mg_ref.get("br")):
            medias_ref_br_area["MEDIA_GERAL"] = float(mg_ref["br"])
        else:
            medias_ref_br_area["MEDIA_GERAL"] = media_nacional_ponderada(
                tabelas or {}, int(ano), "MEDIA_GERAL", "Estadual",
            )

    # Construir dict de agregação incluindo MEDIA_GERAL se existir
    agg_dict = {AREAS_COMPLETO[col]: (col, "mean") for col in COLS_NOTAS}
    if "MEDIA_GERAL" in df_est.columns:
        agg_dict[AREAS_COMPLETO["MEDIA_GERAL"]] = ("MEDIA_GERAL", "mean")

    g = (df_est.groupby(
            ["CO_ESCOLA", "NOME_ESCOLA", "MUNICIPIO_CRES", "CRE"], dropna=False
         )
         .agg(
             **agg_dict,
             Estudantes=(area, "count")
         )
         .reset_index())
    g = g[g["Estudantes"] >= min_part].copy()
    for col in COLS_NOTAS:
        g[AREAS_COMPLETO[col]] = g[AREAS_COMPLETO[col]].round(1)
    if "MEDIA_GERAL" in df_est.columns and AREAS_COMPLETO["MEDIA_GERAL"] in g.columns:
        g[AREAS_COMPLETO["MEDIA_GERAL"]] = g[AREAS_COMPLETO["MEDIA_GERAL"]].round(1)
    
    g["NOME_ESCOLA"] = g["NOME_ESCOLA"].fillna("Escola sem cadastro")
    mun_por_escola = _mapa_municipio_por_escola(df_est)
    if not mun_por_escola.empty:
        g["MUNICIPIO_CRES"] = g["MUNICIPIO_CRES"].fillna(g["CO_ESCOLA"].map(mun_por_escola))
    g["MUNICIPIO_CRES"] = g["MUNICIPIO_CRES"].fillna("—")

    if tabelas is not None:
        inscritos_por_escola = inscritos_por_escola_2024(tabelas, dep="Estadual")
    elif (
        df_bruta_ms is not None
        and not df_bruta_ms.empty
        and "CO_ESCOLA" in df_bruta_ms.columns
    ):
        bruta_est_2024 = df_bruta_ms[
            (df_bruta_ms["DEP_ADM"] == "Estadual") &
            (df_bruta_ms["NU_ANO"] == ano)
        ]
        if bruta_est_2024.empty or "CO_ESCOLA" not in bruta_est_2024.columns:
            inscritos_por_escola = pd.DataFrame(columns=["CO_ESCOLA", "Inscritos"])
        else:
            inscritos_por_escola = (
                bruta_est_2024.groupby("CO_ESCOLA", dropna=False)
                .size()
                .rename("Inscritos")
                .reset_index()
            )
    else:
        inscritos_por_escola = pd.DataFrame(columns=["CO_ESCOLA", "Inscritos"])

    if not inscritos_por_escola.empty:
        g = g.merge(inscritos_por_escola, on="CO_ESCOLA", how="left")
        g["Inscritos"] = g["Inscritos"].fillna(0).astype(int)
        g["Taxa"] = (g["Estudantes"] / g["Inscritos"].replace(0, pd.NA) * 100).round(1)
    else:
        g["Inscritos"] = pd.NA
        g["Taxa"] = pd.NA

    # ------------------------------------------------------------
    # INTEGRAÇÃO: Concluintes do 3º ano e Taxa de participação efetiva
    # ------------------------------------------------------------
    # Quando df_concluintes estiver disponível, faz merge; caso contrário,
    # as colunas aparecem como "—" (dados não disponíveis).
    if df_concluintes is not None and not df_concluintes.empty:
        # Tentar merge por CO_ESCOLA primeiro
        concl_ano = df_concluintes[df_concluintes["NU_ANO"] == ano][["CO_ESCOLA", "Concluintes", "TURNOS"]].copy()
        if not concl_ano.empty:
            g = g.merge(concl_ano, on="CO_ESCOLA", how="left")
        
        # Se ainda houver valores nulos, tentar merge por nome + município
        if g["Concluintes"].isna().sum() > 0:
            # Normalizar nomes para matching (remover acentos e padronizar)
            def _norm(s):
                if pd.isna(s):
                    return ""
                import unicodedata
                s = str(s).strip().upper()
                s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
                return s
            
            g['NOME_ESCOLA_NORM'] = g['NOME_ESCOLA'].apply(_norm)
            g['MUNICIPIO_NORM'] = g['MUNICIPIO_CRES'].apply(_norm)
            
            # Carregar dados de concluintes com nome da escola
            concl_ano_full = df_concluintes[df_concluintes["NU_ANO"] == ano][["CO_ESCOLA", "Concluintes", "TURNOS", "NOME_ESCOLA", "MUNICIPIO"]].copy()
            concl_ano_full['NOME_ESCOLA_NORM'] = concl_ano_full['NOME_ESCOLA'].apply(_norm)
            concl_ano_full['MUNICIPIO_NORM'] = concl_ano_full['MUNICIPIO'].apply(_norm)
            
            # Fazer merge por nome + município para os que não encontraram por CO_ESCOLA
            mask_na = g["Concluintes"].isna()
            if mask_na.sum() > 0:
                g_na = g[mask_na].merge(
                    concl_ano_full[['NOME_ESCOLA_NORM', 'MUNICIPIO_NORM', 'Concluintes', 'TURNOS']],
                    on=['NOME_ESCOLA_NORM', 'MUNICIPIO_NORM'],
                    how='left',
                    suffixes=('', '_y')
                )
                # Atualizar valores
                g.loc[mask_na, 'Concluintes'] = g_na['Concluintes_y'].values
                g.loc[mask_na, 'TURNOS'] = g_na['TURNOS_y'].values
            
            # Limpar colunas temporárias
            g = g.drop(columns=['NOME_ESCOLA_NORM', 'MUNICIPIO_NORM'], errors='ignore')
        
        # Preencher valores não encontrados
        g["Concluintes"] = g["Concluintes"].fillna(0).astype(int)
        g["TURNOS"] = g["TURNOS"].fillna("—")
    else:
        g["Concluintes"] = 0
        g["TURNOS"] = "—"

    g["Concluintes"] = pd.to_numeric(g["Concluintes"], errors="coerce")
    g["Taxa_Efetiva"] = (g["Estudantes"] / g["Concluintes"].replace(0, pd.NA) * 100)
    g["Taxa_Efetiva"] = g["Taxa_Efetiva"].apply(lambda x: round(x, 1) if pd.notna(x) else pd.NA)
    if "Inscritos" in g.columns:
        g["Tx_Inscrição"] = (
            g["Inscritos"] / g["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)

    if g.empty:
        st.info("Nenhuma escola atende ao mínimo de participantes selecionado.")
        return

    c1, c2, c3, c4 = st.columns(4)
    media_col_principal = AREAS_COMPLETO[area]
    kpi_card(c1, "Escolas analisadas", fmt_int(len(g)))
    kpi_card(c2, f"Média entre escolas — {nome_area_ext(area)}", fmt_float(g[media_col_principal].mean()))
    kpi_card(c3, "Maior média", fmt_float(g[media_col_principal].max()), status="positivo")
    kpi_card(c4, "Menor média", fmt_float(g[media_col_principal].min()), status="critico")

    st.markdown(" ")
    top_n = 15
    top = g.sort_values(media_col_principal, ascending=False).head(top_n)
    bot = g.sort_values(media_col_principal, ascending=True).head(top_n)

    _x_range_escolas = [0, 1000]

    col_top, col_bot = st.columns(2)
    with col_top:
        d_plot = top.copy()
        d_plot["Rótulo"] = (d_plot["NOME_ESCOLA"] + " (" +
                            d_plot["MUNICIPIO_CRES"] + ")")
        d_plot = d_plot.merge(g[["CO_ESCOLA", "Inscritos", "Taxa"]], on="CO_ESCOLA", how="left")
        _chart(fig_ranking_horizontal(
            d_plot, col_label="Rótulo", col_valor=media_col_principal,
            titulo=f"Top {top_n} — maiores médias ({nome_area_ext(area)})",
            cor=COR_POSITIVO, altura=CHART_H_HIST_GRID, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=_x_range_escolas,
            col_n="Inscritos", col_taxa="Taxa",
        ))
    with col_bot:
        d_plot = bot.copy()
        d_plot["Rótulo"] = (d_plot["NOME_ESCOLA"] + " (" +
                            d_plot["MUNICIPIO_CRES"] + ")")
        d_plot = d_plot.merge(g[["CO_ESCOLA", "Inscritos", "Taxa"]], on="CO_ESCOLA", how="left")
        _chart(fig_ranking_horizontal(
            d_plot, col_label="Rótulo", col_valor=media_col_principal,
            titulo=f"{top_n} menores médias ({nome_area_ext(area)})",
            cor=COR_CRITICO, altura=CHART_H_HIST_GRID, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=_x_range_escolas,
            col_n="Inscritos", col_taxa="Taxa",
        ))

    st.markdown("### Distribuição das notas — escolas com maiores e menores notas")
    dados_top = df_est[df_est["CO_ESCOLA"].isin(top["CO_ESCOLA"])].copy()
    dados_bot = df_est[df_est["CO_ESCOLA"].isin(bot["CO_ESCOLA"])].copy()

    mapa_escolas_top = dict(zip(
        top["CO_ESCOLA"],
        top["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + top["MUNICIPIO_CRES"].apply(_abreviar_cidade)))
    mapa_escolas_bot = dict(zip(
        bot["CO_ESCOLA"],
        bot["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + bot["MUNICIPIO_CRES"].apply(_abreviar_cidade)))

    dados_top["Escola"] = dados_top["CO_ESCOLA"].map(mapa_escolas_top)
    dados_bot["Escola"] = dados_bot["CO_ESCOLA"].map(mapa_escolas_bot)

    dados_top["NomeCompleto"] = dados_top["CO_ESCOLA"].map(
        dict(zip(top["CO_ESCOLA"], top["NOME_ESCOLA"])))
    dados_top["Municipio"] = dados_top["CO_ESCOLA"].map(
        dict(zip(top["CO_ESCOLA"], top["MUNICIPIO_CRES"])))
    dados_bot["NomeCompleto"] = dados_bot["CO_ESCOLA"].map(
        dict(zip(bot["CO_ESCOLA"], bot["NOME_ESCOLA"])))
    dados_bot["Municipio"] = dados_bot["CO_ESCOLA"].map(
        dict(zip(bot["CO_ESCOLA"], bot["MUNICIPIO_CRES"])))

    _top_ord = top.sort_values(media_col_principal, ascending=False)
    ordem_top = (
        _top_ord["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + _top_ord["MUNICIPIO_CRES"].apply(_abreviar_cidade)
    ).tolist()

    _bot_ord = bot.sort_values(media_col_principal, ascending=True)
    ordem_bot = (
        _bot_ord["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + _bot_ord["MUNICIPIO_CRES"].apply(_abreviar_cidade)
    ).tolist()

    y_range_escolas = [0, 1000]

    col_box1, col_box2 = st.columns(2)
    with col_box1:
        if not dados_top.empty:
            fig_top_box = go.Figure()
            for esc in ordem_top:
                sub = dados_top[dados_top["Escola"] == esc]
                if sub.empty:
                    continue
                co_esc = sub["CO_ESCOLA"].iloc[0]
                nome_comp = sub["NomeCompleto"].iloc[0]
                municipio = sub["Municipio"].iloc[0]
                row_esc = linha_escola_2024(tabelas or {}, co_esc) if tabelas else None
                if row_esc is None:
                    continue
                stats = stats_box_quantis(row_esc, area)
                if stats is None:
                    continue
                _add_box_stats(
                    fig_top_box, stats, name=esc, color="#1E5FAD",
                    x_val=esc, rotulo_mediana=True,
                    hover_titulo=f"{nome_comp} — {municipio}",
                )
            _adicionar_referencias_ms_br(
                fig_top_box, medias_ref["ms"], medias_ref["br"],
                sufixo_legenda="rede estadual",
            )
            fig_top_box.update_layout(
                title=dict(text=f"Top {top_n} — maiores notas", x=0.5),
                xaxis=dict(
                    tickangle=0, tickfont=dict(size=8), showgrid=False,
                    categoryorder="array", categoryarray=ordem_top,
                    title="",
                ),
                yaxis=dict(
                    range=y_range_escolas,
                    gridcolor="#EEF2F6",
                    gridwidth=1,
                    zeroline=False,
                    title="Nota",
                ),
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
                showlegend=False,
                margin=dict(b=100, t=72),
                hovermode="closest",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_top_box, "Top escolas", altura=CHART_H_STANDARD, n_legend=1))
        else:
            st.info("Sem dados para as escolas com maiores notas.")
    with col_box2:
        if not dados_bot.empty:
            fig_bot_box = go.Figure()
            for esc in ordem_bot:
                sub = dados_bot[dados_bot["Escola"] == esc]
                if sub.empty:
                    continue
                co_esc = sub["CO_ESCOLA"].iloc[0]
                nome_comp = sub["NomeCompleto"].iloc[0]
                municipio = sub["Municipio"].iloc[0]
                row_esc = linha_escola_2024(tabelas or {}, co_esc) if tabelas else None
                if row_esc is None:
                    continue
                stats = stats_box_quantis(row_esc, area)
                if stats is None:
                    continue
                _add_box_stats(
                    fig_bot_box, stats, name=esc, color="#C03A2B",
                    x_val=esc, rotulo_mediana=True,
                    hover_titulo=f"{nome_comp} — {municipio}",
                )
            _adicionar_referencias_ms_br(
                fig_bot_box, medias_ref["ms"], medias_ref["br"],
                sufixo_legenda="rede estadual",
            )
            fig_bot_box.update_layout(
                title=dict(text=f"{top_n} — menores notas", x=0.5),
                xaxis=dict(
                    tickangle=0, tickfont=dict(size=8), showgrid=False,
                    categoryorder="array", categoryarray=ordem_bot,
                    title="",
                ),
                yaxis=dict(
                    range=y_range_escolas,
                    gridcolor="#EEF2F6",
                    gridwidth=1,
                    zeroline=False,
                    title="Nota",
                ),
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
                showlegend=False,
                margin=dict(b=100, t=72),
                hovermode="closest",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_bot_box, "Escolas em atenção", altura=CHART_H_STANDARD, n_legend=1))
        else:
            st.info("Sem dados para as escolas com menores notas.")

    st.markdown(" ")
    st.markdown(
        f"""<div style="
            background:{TEMA['insight_bg']};
            border-left:4px solid {AZUL_PRINCIPAL};
            border-radius:10px;
            padding:18px 22px 6px 22px;
            margin-bottom:10px;">
            <span style="font-family:'Plus Jakarta Sans',sans-serif;
                         font-size:1.05rem;font-weight:700;
                         color:{AZUL_PRINCIPAL};">
                Análise individual de escola
            </span>
        </div>""",
        unsafe_allow_html=True,
    )

    def _label_escola_sel(row):
        taxa_str = f" | TX={row['Taxa']:.1f}%" if pd.notna(row.get("Taxa")) else ""
        media_val = row.get(media_col_principal, np.nan)
        media_str = f" | Média: {media_val:.1f}" if pd.notna(media_val) else ""
        return (
            f"{row['NOME_ESCOLA']} ({row['MUNICIPIO_CRES']})"
            f"{media_str}"
            f" | N={row['Estudantes']}{taxa_str}"
        )

    opcoes_escola = g.sort_values(media_col_principal, ascending=False).copy()
    opcoes_escola["_label"] = opcoes_escola.apply(_label_escola_sel, axis=1)
    label_to_co = dict(zip(opcoes_escola["_label"], opcoes_escola["CO_ESCOLA"]))

    escola_sel_label = st.selectbox(
        "Selecione uma escola para análise detalhada:",
        options=list(label_to_co.keys()),
        key="escola_detalhe_sel",
    )
    escola_sel_co = label_to_co[escola_sel_label]
    escola_sel_row = g[g["CO_ESCOLA"] == escola_sel_co].iloc[0]

    tx_val = escola_sel_row.get("Taxa")
    insc_val = escola_sel_row.get("Inscritos")
    conc_val = escola_sel_row.get("Concluintes")
    tx_ef_val = escola_sel_row.get("Taxa_Efetiva")

    tx_insc_val = escola_sel_row.get("Tx_Inscrição")
    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    media_val_sel = escola_sel_row.get(media_col_principal, np.nan)
    kpi_card(kc1, f"Nota Média — {nome_area_ext(area)}", fmt_float(media_val_sel),
             status="positivo" if media_val_sel >= (medias_ref["ms"] or 0) else "critico")
    kpi_card(kc2, "Participantes", fmt_int(int(escola_sel_row.get("Estudantes", 0))))
    kpi_card(kc3, "Concluintes 3º ano E.M", fmt_int(int(conc_val)) if pd.notna(conc_val) and conc_val > 0 else "—")
    kpi_card(kc4, "Tx inscrição",
             f"{tx_insc_val:.1f}%" if pd.notna(tx_insc_val) else "—",
             f"{fmt_int(int(insc_val)) if pd.notna(insc_val) else '—'} inscritos" if pd.notna(insc_val) else "")
    if pd.notna(tx_ef_val) and pd.notna(conc_val) and conc_val > 0:
        kpi_card(kc5, "Tx part. efetiva",
                 f"{tx_ef_val:.1f}%",
                 status="positivo" if tx_ef_val >= 80 else ("atencao" if tx_ef_val >= 60 else "critico"))
    else:
        kpi_card(kc5, "Tx part. efetiva", "—")

    df_escola = df_est[df_est["CO_ESCOLA"] == escola_sel_co].copy()
    if df_notas_individuais is not None and not df_notas_individuais.empty:
        df_escola_ind = filtrar_notas_individuais(
            df_notas_individuais, ano=ano, co_escola=escola_sel_co, dependencia="Estadual",
        )
        if not df_escola_ind.empty:
            df_escola = df_escola_ind
    nome_escola_display = f"{escola_sel_row['NOME_ESCOLA']} — {escola_sel_row['MUNICIPIO_CRES']}"
    usar_individual = (
        df_notas_individuais is not None
        and not df_notas_individuais.empty
        and tem_notas_individuais_ano(df_notas_individuais, ano)
        and not filtrar_notas_individuais(
            df_notas_individuais, ano=ano, co_escola=escola_sel_co, dependencia="Estadual",
        ).empty
    )

    if not df_escola.empty or (tabelas and linha_escola_2024(tabelas, escola_sel_co) is not None):
        medias_ms_area = {col: float(df_est[col].dropna().mean())
                          for col in COLS_NOTAS if col in df_est.columns}
        medias_br_area = {}
        if df_br_est is not None and not df_br_est.empty:
            medias_br_area = {col: float(df_br_est[col].dropna().mean())
                              for col in COLS_NOTAS if col in df_br_est.columns}

        fig_escola = go.Figure()
        row_esc_det = linha_escola_2024(tabelas or {}, escola_sel_co) if tabelas else None
        if not usar_individual and row_esc_det is None:
            st.warning(
                "Quantis por escola indisponíveis. Regenere os agregados: "
                "python gerar_dados_agregados.py"
            )
        for col in COLS_NOTAS:
            nome_area_lbl = AREAS_COMPLETO[col]
            if usar_individual:
                s_area = notas_area(df_escola, col)
                if s_area.empty:
                    continue
                stats = _stats_box(s_area)
                _add_box(
                    fig_escola, s_area, nome_area_lbl, CORES_AREAS[col],
                    x_val=nome_area_lbl, rotulo_mediana=True,
                    hover_titulo=nome_area_lbl,
                )
                _add_scatter_notas(
                    fig_escola, nome_area_lbl, s_area,
                    color=_hex_to_rgba(CORES_AREAS[col], 0.4),
                )
            elif row_esc_det is not None:
                stats = stats_box_quantis(row_esc_det, col)
                if stats is None:
                    continue
                _add_box_stats(
                    fig_escola, stats, name=nome_area_lbl,
                    color=CORES_AREAS[col], x_val=nome_area_lbl,
                    rotulo_mediana=True, hover_titulo=nome_area_lbl,
                )

        xs_ms = [AREAS_COMPLETO[col] for col in COLS_NOTAS if col in medias_ms_area]
        ys_ms = [medias_ms_area[col] for col in COLS_NOTAS if col in medias_ms_area]
        if xs_ms:
            fig_escola.add_trace(go.Scatter(
                x=xs_ms, y=ys_ms,
                mode="markers",
                name="Média MS — rede estadual",
                legendgroup="medias_ref",
                marker=dict(symbol="line-ew", size=22,
                            color=LARANJA_DESTAQUE,
                            line=dict(color=LARANJA_DESTAQUE, width=3)),
                hovertemplate="<b>Média MS</b><br>%{x}: %{y:.1f}<extra></extra>",
            ))

        xs_br = [AREAS_COMPLETO[col] for col in COLS_NOTAS if col in medias_br_area]
        ys_br = [medias_br_area[col] for col in COLS_NOTAS if col in medias_br_area]
        if xs_br:
            fig_escola.add_trace(go.Scatter(
                x=xs_br, y=ys_br,
                mode="markers",
                name="Média BR — rede estadual",
                legendgroup="medias_ref",
                marker=dict(symbol="line-ew", size=22,
                            color=COR_BRASIL,
                            line=dict(color=COR_BRASIL, width=2.5)),
                hovertemplate="<b>Média BR</b><br>%{x}: %{y:.1f}<extra></extra>",
            ))

        fig_escola = _finalizar_boxplot(
            fig_escola,
            f"Distribuição das notas — {nome_escola_display}",
            altura=CHART_H_STANDARD,
            eixo_x="",
            n_legend=5,
        )
        fig_escola.update_xaxes(showticklabels=False)
        _chart(fig_escola)

        if usar_individual:
            s_hist = notas_area(df_escola, area)
            if not s_hist.empty:
                titulo_secao(
                    f"Histograma — {nome_area_ext(area)}",
                    f"Distribuição individual dos {len(s_hist):,} estudantes da escola selecionada."
                )
                _chart(_fig_histogram_notas(
                    s_hist,
                    f"Distribuição de notas — {nome_escola_display} ({nome_area_ext(area)})",
                    cor=CORES_AREAS.get(area, AZUL_PRINCIPAL),
                    media_ref=medias_ref.get("ms"),
                ))
    else:
        st.info("Sem dados individuais para a escola selecionada.")

    if not g.empty and "Tx_Inscrição" in g.columns:
        g_vis = g.rename(columns={
            "NOME_ESCOLA": "Escola", media_col_principal: "Média",
        })
        part_esc = g_vis[["Escola", "Concluintes", "Inscritos", "Estudantes", "Tx_Inscrição", "Taxa_Efetiva"]].rename(
            columns={"Estudantes": "Presentes", "Taxa_Efetiva": "Tx_Part_Efetiva"},
        )
        titulo_secao("Desempenho × Participação — escolas")
        col_e1, col_e2 = st.columns([1.55, 1])
        top_esc = g_vis.nlargest(min(12, len(g_vis)), "Média")
        with col_e1:
            _chart(fig_combo_participacao_desempenho(
                part_esc[part_esc["Escola"].isin(top_esc["Escola"])],
                top_esc, "Escola", "Média",
                titulo=f"Top escolas — {nome_area_ext(area)}",
            ))
        with col_e2:
            _chart(fig_quadrante_desempenho_participacao(
                part_esc.rename(columns={"Tx_Part_Efetiva": "Tx_Part_Efetiva"}),
                g_vis, "Escola", "Média",
                titulo="Quadrante escolar",
            ))

    titulo_secao("Tabela completa por escola")
    tabela = g.rename(columns={
        "NOME_ESCOLA": "Escola", "MUNICIPIO_CRES": "Município",
        "CRE": "Coordenadoria Regional",
        "Estudantes": "Participantes",
    }).copy()
    
    tabela["Tx_Part_Efetiva"] = (tabela["Participantes"] / tabela["Concluintes"].replace(0, pd.NA) * 100)
    tabela["Tx_Part_Efetiva"] = tabela["Tx_Part_Efetiva"].apply(lambda x: round(x, 1) if pd.notna(x) else pd.NA)
    if "Inscritos" in tabela.columns:
        tabela["Tx_Inscrição"] = (
            tabela["Inscritos"] / tabela["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)

    # Garantir que Concluintes, TURNOS existam
    if "Concluintes" not in tabela.columns:
        tabela["Concluintes"] = pd.NA
    if "TURNOS" not in tabela.columns:
        tabela["TURNOS"] = "—"

    # Selecionar colunas finais: remover Inscritos, Presentes, Mediana, Participantes
    COLS_NOTAS_COMPLETO = [AREAS_COMPLETO[col] for col in COLS_NOTAS]
    # Adicionar Média Geral se existir
    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela.columns:
        COLS_NOTAS_COMPLETO = [AREAS_COMPLETO["MEDIA_GERAL"]] + COLS_NOTAS_COMPLETO
    
    cols_esc = ["Escola", "Município", "Coordenadoria Regional", "TURNOS",
                "Tx_Inscrição", "Tx_Part_Efetiva", "Inscritos", "Concluintes"]
    tabela = tabela[[c for c in cols_esc if c in tabela.columns] + COLS_NOTAS_COMPLETO]
    tabela = tabela.sort_values(media_col_principal, ascending=False)
    tabela["Coordenadoria Regional"] = tabela["Coordenadoria Regional"].fillna("—")
    
    for txc in ("Tx_Inscrição", "Tx_Part_Efetiva"):
        if txc in tabela.columns:
            tabela[f"{txc}_fmt"] = tabela[txc].apply(
                lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—"
            )
    tabela_display = tabela.copy()
    for txc in ("Tx_Inscrição", "Tx_Part_Efetiva"):
        if f"{txc}_fmt" in tabela_display.columns:
            tabela_display[txc] = tabela_display[f"{txc}_fmt"]
            tabela_display = tabela_display.drop(columns=[f"{txc}_fmt"])
    for col in tabela_display.columns:
        if col in ("Concluintes", "Inscritos"):
            tabela_display[col] = tabela_display[col].apply(lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—")
        elif col in COLS_NOTAS_COMPLETO:
            tabela_display[col] = tabela_display[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—")
    
    # ============================================================
    # ESTILIZAÇÃO VIA FUNÇÃO UTILITÁRIA
    # ============================================================
    area_labels = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela_display.columns:
        area_labels["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]
    
    styled, css_cabecalho = _estilizar_tabela(
        df_display=tabela_display,
        df_raw=tabela,
        colunas_area=COLS_NOTAS_COMPLETO,
        cores_area=CORES_AREAS,
        medias_ms=medias_ref_ms_area,
        medias_br=medias_ref_br_area,
        area_labels=area_labels,
    )
    
    # CSS customizado para cabeçalhos coloridos (pandas styler não suporta seletores de coluna)
    if css_cabecalho:
        st.markdown(f"""
        <style>
        {css_cabecalho}
        </style>
        """, unsafe_allow_html=True)
    
    # Legenda explicativa
    st.markdown("""
    <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
        <b>Tx inscrição</b> = inscritos ÷ concluintes · <b>Tx part. efetiva</b> = presentes ÷ concluintes |
        <b>Tx part. efetiva:</b> <span style='color: #059669;'>■</span> ≥80%
        <span style='color: #D97706;'>■</span> 70-79%
        <span style='color: #DC2626;'>■</span> &lt;70% |
        <b>Cores das áreas:</b> fundo colorido conforme legenda dos gráficos | 
        <b>Fonte das médias:</b> <span style='color: #059669;'>verde</span> = acima MS e BR, 
        <span style='color: #2563EB;'>azul</span> = acima de MS e abaixo de BR, 
        <span style='color: #DC2626;'>vermelho</span> = abaixo de ambos
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(styled, width="stretch", hide_index=True, height=520)

def _df_base_territorial(
    df_ms_enriq: pd.DataFrame,
    df_filt_ms_full: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Série temporal completa (todos os anos) quando carregada; senão recorte lateral."""
    if (
        df_filt_ms_full is not None
        and not df_filt_ms_full.empty
        and "DEP_ADM" in df_filt_ms_full.columns
    ):
        return df_filt_ms_full
    if df_ms_enriq is not None and not df_ms_enriq.empty and "DEP_ADM" in df_ms_enriq.columns:
        return df_ms_enriq
    return pd.DataFrame()


def _linhas_nivel_cre(df: pd.DataFrame) -> pd.DataFrame:
    """Registros agregados por CRE (evolucao_cre) — sem duplicata municipal."""
    if df.empty:
        return df.copy()
    if "NO_MUNICIPIO_ESC" in df.columns:
        return df[df["CRE"].notna() & df["NO_MUNICIPIO_ESC"].isna()].copy()
    return df[df["CRE"].notna()].copy()


def _linhas_nivel_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """Registros agregados por município (evolucao_municipios) com CRE atribuída."""
    if df.empty or "NO_MUNICIPIO_ESC" not in df.columns:
        return pd.DataFrame()
    return df[df["NO_MUNICIPIO_ESC"].notna() & df["CRE"].notna()].copy()


def _presentes_cre_ano(
    tabelas: dict,
    cre: str,
    ano: int,
    dependencia: str,
) -> int:
    """Presentes nos 2 dias na CRE (participacao_cre.parquet)."""
    df = filtrar_participacao_cre(tabelas, anos=[int(ano)], dependencia=dependencia)
    hit = df[df["CRE"] == cre]
    if hit.empty:
        return 0
    return int(pd.to_numeric(hit.iloc[0]["estudantes"], errors="coerce") or 0)


def _inscritos_cre_ano(
    tabelas: dict,
    cre: str,
    ano: int,
    dependencia: str,
) -> int:
    """Inscritos na CRE (participacao_cre.parquet, coluna inscritos)."""
    df = filtrar_participacao_cre(tabelas, anos=[int(ano)], dependencia=dependencia)
    hit = df[df["CRE"] == cre]
    if hit.empty or "inscritos" not in hit.columns:
        return 0
    return int(pd.to_numeric(hit.iloc[0]["inscritos"], errors="coerce") or 0)


def _reconstruir_bases_territoriais(
    tabelas: dict,
    anos_sel: list,
    dep_selecionadas: list,
    df_ms_enriq: pd.DataFrame,
    df_filt_ms_full: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconstrói bases territoriais se o contexto cacheado chegou vazio."""
    df_base = _df_base_territorial(df_ms_enriq, df_filt_ms_full)
    if "DEP_ADM" in df_base.columns and not df_base.empty:
        full = df_filt_ms_full if (
            df_filt_ms_full is not None
            and not df_filt_ms_full.empty
            and "DEP_ADM" in df_filt_ms_full.columns
        ) else df_ms_enriq
        return df_ms_enriq, full

    if not tabelas:
        return df_ms_enriq, df_filt_ms_full or pd.DataFrame()

    deps = list(dep_selecionadas)
    anos_list = [int(a) for a in anos_sel]
    cres = carregar_cres()
    mapa = carregar_mapa_municipio_cre()
    df_todos = aplicar_cre_por_municipio(
        reconstruir_ms_enriquecido(tabelas, ANOS_DISPONIVEIS, deps), mapa,
    )
    df_recorte = reconstruir_ms_enriquecido(tabelas, anos_list, deps)
    return (
        enriquecer_ms(df_recorte, cres, mapa),
        enriquecer_ms(df_todos, cres, mapa),
    )


def _concluintes_cre_por_ano(
    cres: list[str],
    ano_ref: int | str,
) -> pd.DataFrame:
    """Concluintes por CRE a partir da planilha (escola → CRE via cres.xlsx)."""
    df_conc = carregar_concluintes_cre()
    if df_conc.empty or not cres:
        return pd.DataFrame(columns=["CRE", "Concluintes"])
    sub = df_conc[df_conc["CRE"].isin(cres)].copy()
    if ano_ref != "Todos os anos":
        sub = sub[sub["NU_ANO"] == int(ano_ref)]
    else:
        sub = sub.groupby("CRE", observed=True)["Concluintes"].sum().reset_index()
        return sub
    return sub[["CRE", "Concluintes"]].copy()


def _participacao_cre_tabela(
    tabelas: dict,
    cres: list[str],
    ano_ref: int | str,
    dependencia: str,
) -> pd.DataFrame:
    """CRE × presentes (agregados ENEM) + concluintes (planilha escola → CRE)."""
    if not cres:
        return pd.DataFrame()
    if ano_ref == "Todos os anos":
        df = filtrar_participacao_cre(tabelas, dependencia=dependencia)
    else:
        df = filtrar_participacao_cre(tabelas, anos=[int(ano_ref)], dependencia=dependencia)
    if df.empty:
        out = pd.DataFrame({"CRE": cres})
        out["Presentes"] = 0
    else:
        df = df[df["CRE"].isin(cres)].copy()
        if ano_ref == "Todos os anos":
            out = (
                df.groupby("CRE", observed=True)
                .agg(Presentes=("estudantes", "sum"))
                .reset_index()
            )
        else:
            out = df[["CRE", "estudantes"]].rename(columns={"estudantes": "Presentes"})
    out = out[out["CRE"].isin(cres)].copy()
    conc = _concluintes_cre_por_ano(cres, ano_ref)
    if not conc.empty:
        out = out.drop(columns=["Concluintes"], errors="ignore").merge(conc, on="CRE", how="left")
    else:
        out["Concluintes"] = pd.NA
    out["Presentes"] = pd.to_numeric(out["Presentes"], errors="coerce").fillna(0).astype(int)
    out["Concluintes"] = pd.to_numeric(out["Concluintes"], errors="coerce")
    if not df.empty and "inscritos" in df.columns:
        if ano_ref == "Todos os anos":
            insc = (
                df[df["CRE"].isin(cres)]
                .groupby("CRE", observed=True)["inscritos"]
                .sum()
                .reset_index()
            )
        else:
            insc = df[df["CRE"].isin(cres)][["CRE", "inscritos"]].copy()
        out = out.drop(columns=["Inscritos"], errors="ignore").merge(
            insc.rename(columns={"inscritos": "Inscritos"}), on="CRE", how="left",
        )
    else:
        out["Inscritos"] = pd.NA
    out = _enriquecer_participacao_taxas(out)
    return out.sort_values("CRE").reset_index(drop=True)


def _taxa_part_efetiva_ms(
    tabelas: dict,
    ano: int,
    dependencia: str,
) -> float | None:
    """Taxa de participação efetiva do estado (presentes ÷ concluintes).

    Usa participacao_ano.parquet; fallback na soma de participacao_cre.
    Não usa contagem de linhas sintéticas (evita duplicar CRE + município).
    """
    df_ano = tabelas.get("participacao_ano", pd.DataFrame())
    if not df_ano.empty:
        hit = df_ano[(df_ano["ano"] == int(ano)) & (df_ano["dependencia"] == dependencia)]
        if not hit.empty:
            row = hit.iloc[0]
            conc = pd.to_numeric(row.get("concluintes"), errors="coerce")
            part = pd.to_numeric(row.get("presentes_filt", row.get("presentes")), errors="coerce")
            if pd.notna(conc) and float(conc) > 0 and pd.notna(part):
                return round(100 * float(part) / float(conc), 1)
    df_cre = filtrar_participacao_cre(tabelas, anos=[int(ano)], dependencia=dependencia)
    if not df_cre.empty:
        pres = pd.to_numeric(df_cre["estudantes"], errors="coerce").sum()
        conc = pd.to_numeric(df_cre["Concluintes"], errors="coerce").sum()
        if conc > 0:
            return round(100 * pres / conc, 1)
    return None


def _participacao_municipio_tabela(
    tabelas: dict,
    municipios: list[str],
    ano_ref: int | str,
    dependencia: str,
    col_municipio: str = "NO_MUNICIPIO_ESC",
) -> pd.DataFrame:
    """Monta município × presentes/concluintes/taxas a partir de municipios.parquet."""
    if not municipios:
        return pd.DataFrame()
    if ano_ref == "Todos os anos":
        df = filtrar_participacao_municipio(tabelas, dependencia=dependencia)
    else:
        df = filtrar_participacao_municipio(tabelas, anos=[int(ano_ref)], dependencia=dependencia)
    if df.empty or col_municipio not in df.columns:
        return pd.DataFrame()
    df = df[df[col_municipio].isin(municipios)].copy()
    if df.empty:
        return pd.DataFrame()
    agg_cols = {"Presentes": ("estudantes", "sum"), "Concluintes": ("Concluintes", "sum")}
    if "inscritos" in df.columns:
        agg_cols["Inscritos"] = ("inscritos", "sum")
    if ano_ref == "Todos os anos":
        out = (
            df.groupby(col_municipio, observed=True)
            .agg(**agg_cols)
            .reset_index()
            .rename(columns={col_municipio: "Município"})
        )
    else:
        cols = [col_municipio, "estudantes", "Concluintes", "tx_part_efetiva"]
        if "inscritos" in df.columns:
            cols.append("inscritos")
        if "tx_inscricao" in df.columns:
            cols.append("tx_inscricao")
        out = df[cols].rename(
            columns={col_municipio: "Município", "estudantes": "Presentes", "inscritos": "Inscritos"},
        )
    out["Concluintes"] = pd.to_numeric(out["Concluintes"], errors="coerce").fillna(0).astype(int)
    out["Presentes"] = pd.to_numeric(out["Presentes"], errors="coerce").fillna(0).astype(int)
    if "Inscritos" in out.columns:
        out["Inscritos"] = pd.to_numeric(out["Inscritos"], errors="coerce").fillna(0).astype(int)
    out = _enriquecer_participacao_taxas(out.rename(columns={"Taxa_Efetiva": "Tx_Part_Efetiva"}))
    if "Taxa_Efetiva" not in out.columns and "Tx_Part_Efetiva" in out.columns:
        out["Taxa_Efetiva"] = out["Tx_Part_Efetiva"]
    return out


# ============================================================
# ABA 5 - TERRITORIAL (REORDENADA E CORRIGIDA)
# ============================================================
def aba_territorial(
    df_ms_enriq,
    df_filt_ms_full=None,
    df_br=None,
    dep_selecionadas=None,
    df_bruta_ms_enriq=None,
    tabelas=None,
    df_notas_individuais=None,
    anos_sel=None,
):
    if dep_selecionadas is None:
        dep_selecionadas = ["Estadual", "Federal", "Municipal", "Privada"]
    tabelas = tabelas or {}
    if anos_sel:
        df_ms_enriq, df_filt_ms_full = _reconstruir_bases_territoriais(
            tabelas, list(anos_sel), dep_selecionadas, df_ms_enriq, df_filt_ms_full,
        )

    titulo_secao(
        "Análise territorial",
        "Desempenho das escolas distribuído por CRE, com evolução temporal. "
        "Escolha a dependência administrativa abaixo."
    )

    st.markdown("### Filtros de análise territorial")
    col_filt_dep, col_filt_area = st.columns(2)
    with col_filt_dep:
        dep_escolhido = st.selectbox(
            "Selecione a dependência administrativa",
            options=dep_selecionadas,
            key="dep_territorial"
        )
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_territorial"
        )

    df_base = _df_base_territorial(df_ms_enriq, df_filt_ms_full)
    if "DEP_ADM" not in df_base.columns:
        st.warning("Dados territoriais indisponíveis no recorte atual. Recarregue a página ou ajuste os filtros laterais.")
        return
    df_dep = df_base[df_base["DEP_ADM"] == dep_escolhido].copy()
    df_dep_cre = _linhas_nivel_cre(df_dep)
    df_dep_muni = _linhas_nivel_municipio(df_dep)
    df_dist_cre = filtrar_distribuicao(
        tabelas.get("distribuicao_cre", pd.DataFrame()),
        dependencia=dep_escolhido,
    )

    if "CRE" not in df_dep.columns:
        df_dep["CRE"] = pd.NA
    if "CRE" not in df_dep_cre.columns:
        df_dep_cre["CRE"] = pd.NA

    if df_dep_cre.empty and df_dep.empty:
        st.warning(f"Sem dados para a dependência {dep_escolhido} no recorte atual.")
        return

    if tabelas:
        ano_ref_ini = int(df_dep_cre["NU_ANO"].max()) if not df_dep_cre.empty else (
            int(df_dep["NU_ANO"].max()) if not df_dep.empty else None
        )
        refs = medias_referencia_por_ano(tabelas, ano_ref_ini) if ano_ref_ini else {}
        medias_ref = refs.get(area, {})
        if not medias_ref:
            medias_ref = calcular_medias_referencia(
                df_dep_cre if not df_dep_cre.empty else df_dep,
                df_br[df_br["DEP_ADM"] == dep_escolhido] if df_br is not None else pd.DataFrame(),
                area,
            )
    elif df_br is not None:
        medias_ref = calcular_medias_referencia(
            df_dep_cre if not df_dep_cre.empty else df_dep,
            df_br[df_br["DEP_ADM"] == dep_escolhido], area,
        )
    else:
        medias_ref = {"ms": None, "br": None}

    titulo_secao("Evolução temporal das CREs")
    cre_selecionadas = []
    lista_cres = []
    if df_dep_cre.empty or df_dep_cre["CRE"].isna().all():
        st.info("Dados de CRE não encontrados. Verifique o arquivo CRES.")
    else:
        lista_cres = sorted(df_dep_cre["CRE"].dropna().unique())

    # Paleta de cores para até 12 CREs - alta saturacao e contraste
    _PALETA_CRE = [
        "#0033CC", "#FF4500", "#00AA44", "#CC0000",
        "#0099CC", "#FF8C00", "#8800CC", "#CC0066",
        "#0066FF", "#FFD700", "#444444", "#008080",
    ]

    if lista_cres:
        # Calcular médias gerais para ordenar e sugerir default
        ranking_cre = (df_dep_cre.groupby("CRE", observed=True)[area]
                       .mean().round(2).sort_values(ascending=False))

        # Seleção com presets
        col_preset, col_sel = st.columns([1, 3])
        with col_preset:
            preset = st.selectbox(
                "Presets de seleção",
                options=["Todas", "Top 5", "Top 3", "Bottom 5", "Personalizado"],
                key="cre_preset",
            )
        with col_sel:
            if preset == "Todas":
                default_cres = lista_cres
            elif preset == "Top 5":
                default_cres = ranking_cre.head(5).index.tolist()
            elif preset == "Top 3":
                default_cres = ranking_cre.head(3).index.tolist()
            elif preset == "Bottom 5":
                default_cres = ranking_cre.tail(5).index.tolist()
            else:
                default_cres = []

            cre_selecionadas = st.multiselect(
                "Selecione as CREs que deseja visualizar",
                options=lista_cres,
                default=default_cres,
                format_func=nome_cre_curto,
                key="cre_territorial"
            )

        if cre_selecionadas:
            df_cre_evol = df_dep_cre[df_dep_cre["CRE"].isin(cre_selecionadas)].copy()
            if not df_cre_evol.empty and df_cre_evol["NU_ANO"].nunique() > 0:
                evol = df_cre_evol.groupby(["CRE", "NU_ANO"], observed=True)[area].mean().reset_index(name="Média")
                evol = evol.dropna(subset=["Média"])
                if not evol.empty:
                    fig_evol_cre = go.Figure()
                    for idx, cre in enumerate(cre_selecionadas):
                        df_cre_evo = evol[evol["CRE"] == cre]
                        if df_cre_evo.empty:
                            continue
                        cor = _PALETA_CRE[idx % len(_PALETA_CRE)]
                        fig_evol_cre.add_trace(go.Bar(
                            x=df_cre_evo["NU_ANO"], y=df_cre_evo["Média"].round(2),
                            name=nome_cre_curto(cre),
                            marker=dict(color=_hex_rgba(cor, 0.7), line=dict(color=cor, width=2)),
                            hovertemplate=f"<b>{cre}</b><br>Ano: %{{x}}<br>Média: %{{y:.2f}}<extra></extra>",
                        ))

                    # Linhas dinâmicas de referência MS e BR (média por ano)
                    anos_plot = sorted(evol["NU_ANO"].unique())
                    if not df_dep_cre.empty:
                        media_ms_ano = (df_dep_cre.groupby("NU_ANO", observed=True)[area]
                                        .mean().round(2).reindex(anos_plot).dropna())
                        if not media_ms_ano.empty:
                            fig_evol_cre.add_trace(go.Scatter(
                                x=media_ms_ano.index, y=media_ms_ano.values,
                                name="Média MS", mode="lines+markers+text",
                                line=dict(color=AZUL_PRINCIPAL, width=2.5, dash="dash"),
                                marker=dict(size=8, color=AZUL_PRINCIPAL),
                                text=[f"{v:.1f}" for v in media_ms_ano.values],
                                textposition="top left",
                                textfont=dict(size=12, color=AZUL_PRINCIPAL, family="Arial Black"),
                                hovertemplate="<b>Média MS</b><br>Ano: %{x}<br>Média: %{y:.2f}<extra></extra>",
                            ))
                    if df_br is not None and not df_br.empty:
                        df_br_est = df_br[df_br["DEP_ADM"] == "Estadual"].copy()
                        media_br_ano = (df_br_est.groupby("NU_ANO", observed=True)[area]
                                        .mean().round(2).reindex(anos_plot).dropna())
                        if not media_br_ano.empty:
                            fig_evol_cre.add_trace(go.Scatter(
                                x=media_br_ano.index, y=media_br_ano.values,
                                name="Média BR", mode="lines+markers+text",
                                line=dict(color=COR_BRASIL, width=2.5, dash="dot"),
                                marker=dict(size=8, color=COR_BRASIL),
                                text=[f"{v:.1f}" for v in media_br_ano.values],
                                textposition="top right",
                                textfont=dict(size=12, color=COR_BRASIL, family="Arial Black"),
                                hovertemplate="<b>Média BR</b><br>Ano: %{x}<br>Média: %{y:.2f}<extra></extra>",
                            ))

                    fig_evol_cre.update_layout(
                        title=f"Evolução da média — {nome_area_ext(area)}",
                        xaxis=dict(tickmode="linear", dtick=1, title=""),
                        yaxis=dict(
                            title=dict(text="Nota", font=dict(size=14, color=TEMA["texto"])),
                            range=[0, 1000],
                            tickfont=dict(size=12),
                        ),
                        hovermode="x unified",
                        barmode="group",
                        bargap=0.15,
                        bargroupgap=0.1,
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.35,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=9),
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor=COR_NEUTRO,
                            borderwidth=1,
                        ),
                        margin=dict(t=60, r=120, b=180),
                        annotations=[
                            dict(
                                x=1.12, y=0.5, xref="paper", yref="paper",
                                text="Escala:<br><b>0 – 1000</b>",
                                showarrow=False,
                                font=dict(size=13, color=TEMA["texto"], family="Arial Black"),
                                align="center",
                                bgcolor="rgba(255,255,255,0.9)",
                                bordercolor=COR_NEUTRO,
                                borderwidth=1,
                                borderpad=6,
                            )
                        ],
                    )
                    _chart(_finalizar_grafico(fig_evol_cre, altura=CHART_H_EVOLUCAO, n_legend=4))

                    # ----- GRÁFICO DE EVOLUÇÃO DAS TAXAS DE PARTICIPAÇÃO POR CRE -----
                    titulo_secao(
                        "Evolução da taxa de participação efetiva por CRE",
                        "Percentual de concluintes do 3º ano que compareceram nos dois dias de prova, ao longo dos anos."
                    )

                    df_part_evol = filtrar_participacao_cre(
                        tabelas, dependencia=dep_escolhido,
                    )
                    taxas_evol = []
                    for cre in cre_selecionadas:
                        for ano in sorted(df_dep["NU_ANO"].dropna().unique()):
                            if df_part_evol.empty:
                                part = _presentes_cre_ano(
                                    tabelas, cre, int(ano), dep_escolhido,
                                ) or len(df_dep_cre[
                                    (df_dep_cre["CRE"] == cre)
                                    & (df_dep_cre["NU_ANO"] == ano)
                                ])
                                if part <= 0:
                                    continue
                                taxas_evol.append({
                                    "CRE": cre, "Ano": int(ano), "Taxa": pd.NA,
                                    "Concluintes": pd.NA, "Presentes": part,
                                })
                                continue
                            hit = df_part_evol[
                                (df_part_evol["CRE"] == cre) & (df_part_evol["ano"] == int(ano))
                            ]
                            if hit.empty:
                                continue
                            row = hit.iloc[0]
                            part = int(row.get("estudantes", 0) or 0)
                            conc_rows = _concluintes_cre_por_ano([cre], int(ano))
                            conc = (
                                conc_rows.iloc[0]["Concluintes"]
                                if not conc_rows.empty else pd.NA
                            )
                            taxa = (
                                round(100 * part / float(conc), 1)
                                if pd.notna(conc) and float(conc) > 0 else pd.NA
                            )
                            if part > 0 or (pd.notna(conc) and float(conc) > 0):
                                taxas_evol.append({
                                    "CRE": cre, "Ano": int(ano),
                                    "Taxa": float(taxa) if pd.notna(taxa) else pd.NA,
                                    "Concluintes": int(conc) if pd.notna(conc) else pd.NA,
                                    "Presentes": part,
                                })

                    if taxas_evol:
                        df_taxas_evol = pd.DataFrame(taxas_evol).dropna(subset=["Taxa"])
                    if taxas_evol and not df_taxas_evol.empty:
                        fig_taxas_evol = go.Figure()
                        for idx, cre in enumerate(cre_selecionadas):
                            df_cre_taxa = df_taxas_evol[df_taxas_evol["CRE"] == cre]
                            if df_cre_taxa.empty:
                                continue
                            cor = _PALETA_CRE[idx % len(_PALETA_CRE)]
                            fig_taxas_evol.add_trace(go.Bar(
                                x=df_cre_taxa["Ano"], y=df_cre_taxa["Taxa"],
                                name=nome_cre_curto(cre),
                                marker=dict(color=_hex_rgba(cor, 0.65), line=dict(color=cor, width=1.5)),
                                text=[f"{v:.1f}%" for v in df_cre_taxa["Taxa"]],
                                textposition="outside",
                                textfont=dict(size=10, color=cor,
                                              family="Source Sans 3, system-ui, sans-serif"),
                                hovertemplate=(
                                    f"<b>{cre}</b><br>"
                                    "Ano: %{x}<br>"
                                    "Taxa efetiva: %{y:.1f}%<br>"
                                    "Concluintes: %{customdata[0]}<br>"
                                    "Presentes: %{customdata[1]}"
                                    "<extra></extra>"
                                ),
                                customdata=df_cre_taxa[["Concluintes", "Presentes"]].values,
                            ))

                        # Linha de referência: taxa MS estadual (presentes ÷ concluintes)
                        taxas_ms_ano = []
                        for ano in sorted(df_dep["NU_ANO"].dropna().unique()):
                            taxa_ms = _taxa_part_efetiva_ms(tabelas, int(ano), dep_escolhido)
                            if taxa_ms is not None:
                                taxas_ms_ano.append({"Ano": int(ano), "Taxa": taxa_ms})
                        if taxas_ms_ano:
                            df_ms_taxa = pd.DataFrame(taxas_ms_ano)
                            fig_taxas_evol.add_trace(go.Scatter(
                                x=df_ms_taxa["Ano"], y=df_ms_taxa["Taxa"],
                                name="Taxa MS (rede)", mode="lines+markers",
                                line=dict(color=AZUL_PRINCIPAL, width=2.5, dash="dash"),
                                marker=dict(size=8, color=AZUL_PRINCIPAL),
                                hovertemplate=(
                                    "<b>Taxa MS (rede)</b><br>"
                                    "Ano: %{x}<br>Taxa efetiva: %{y:.1f}%<extra></extra>"
                                ),
                            ))

                        fig_taxas_evol.update_layout(
                            xaxis=dict(tickmode="linear", dtick=1, title="Ano", type="category"),
                            yaxis=dict(
                                title="Taxa (%)", range=[0, 105], ticksuffix="%",
                            ),
                            barmode="group",
                            bargap=0.15,
                            bargroupgap=0.1,
                        )
                        n_leg_taxa = min(len(cre_selecionadas) + 1, 6)
                        _chart(_finalizar_grafico(
                            fig_taxas_evol,
                            titulo="Taxa de participação efetiva por CRE — evolução temporal",
                            altura=CHART_H_RANKING,
                            n_legend=n_leg_taxa,
                            hover_unified=True,
                        ))
                    elif taxas_evol:
                        st.info("Taxa de participação efetiva indisponível para as CREs selecionadas.")
                    else:
                        st.info(
                            "Dados de participação por CRE indisponíveis. "
                            "Verifique participacao_cre.parquet nos agregados."
                        )
                else:
                    st.info("Sem dados de evolução para as CREs selecionadas.")
            else:
                st.info("Sem dados de evolução temporal para as CREs selecionadas.")
        else:
            st.warning("Selecione ao menos uma CRE.")
    else:
        st.info("Nenhuma CRE encontrada nos dados.")

    st.markdown("---")
    anos_disponiveis = sorted(df_dep_cre["NU_ANO"].unique()) if not df_dep_cre.empty else sorted(df_dep["NU_ANO"].unique())
    ano_opcoes = [str(ano) for ano in anos_disponiveis] + ["Todos os anos"]
    default_index = len(anos_disponiveis) - 1 if anos_disponiveis else 0

    st.markdown("### Filtro de ano")
    ano_escolhido = st.selectbox(
        "Selecione o ano para análise territorial",
        options=ano_opcoes,
        index=default_index,
        key="ano_territorial"
    )

    if ano_escolhido == "Todos os anos":
        df_dep_cre_filt = df_dep_cre
        ano_ref = "Todos os anos"
    else:
        ano_ref = int(ano_escolhido)
        df_dep_cre_filt = df_dep_cre[df_dep_cre["NU_ANO"] == ano_ref].copy()

    if df_dep_cre_filt.empty:
        st.warning(f"Sem dados para o ano {ano_escolhido}.")
        return

    # Recalcular médias de referência para o ano selecionado (alinha com o primeiro gráfico)
    df_br_ano = df_br[df_br["NU_ANO"] == ano_ref] if (df_br is not None and ano_ref != "Todos os anos") else df_br
    medias_ref = calcular_medias_referencia(
        df_dep_cre_filt,
        df_br_ano[df_br_ano["DEP_ADM"] == dep_escolhido] if df_br_ano is not None else None,
        area,
    ) if df_br is not None else {"ms": None, "br": None}

    # Gráfico de participação por CRE (concluintes / presentes / taxa efetiva)
    if lista_cres and cre_selecionadas and "CRE" in df_dep_cre_filt.columns:
        part_cre = _participacao_cre_tabela(
            tabelas, cre_selecionadas, ano_ref, dep_escolhido,
        )
        if part_cre.empty:
            presentes = (
                df_dep_cre_filt[df_dep_cre_filt["CRE"].isin(cre_selecionadas)]
                .groupby("CRE", observed=True)
                .agg(Presentes=(area, "count"))
                .reset_index()
            )
            part_cre = presentes.copy()
            part_cre["Concluintes"] = pd.NA
            part_cre["Tx_Part_Efetiva"] = pd.NA
        if not part_cre.empty:
            part_cre["Concluintes"] = pd.to_numeric(part_cre["Concluintes"], errors="coerce")
            part_cre["Presentes"] = pd.to_numeric(part_cre["Presentes"], errors="coerce").fillna(0).astype(int)
            part_cre = _enriquecer_participacao_taxas(part_cre)

            if not part_cre.empty:
                titulo_secao(f"Participação por CRE ({ano_ref})")
                st.caption(
                    "Concluintes: planilha do 3º ano (escola → CRE). "
                    "Inscritos e presentes: microdado ENEM. "
                    "Tx inscrição = inscritos ÷ concluintes · Tx part. efetiva = presentes ÷ concluintes. "
                    + (
                        "Barra de inscritos indisponível nos agregados — execute "
                        "`python gerar_dados_agregados.py` para atualizar."
                        if "Inscritos" not in part_cre.columns or part_cre["Inscritos"].isna().all()
                        else ""
                    )
                )
                
                # Calcular diferença Concluintes - Presentes
                part_cre["Diferença"] = (part_cre["Concluintes"] - part_cre["Presentes"]).clip(lower=0)
                part_cre["Dif_Pct"] = _pct_taxa(part_cre["Diferença"], part_cre["Concluintes"])
                part_cre["_cre_x"] = part_cre["CRE"].map(nome_cre_curto)
                
                # Identificar CREs com maior diferença (top 3; ignora CREs sem concluintes)
                top_dif = (
                    part_cre.dropna(subset=["Concluintes", "Diferença"])
                    .nlargest(3, "Diferença")[["CRE", "Diferença", "Dif_Pct"]]
                )
                
                fig_part_cre = go.Figure()
                fig_part_cre.add_trace(go.Bar(
                    x=part_cre["_cre_x"], y=part_cre["Concluintes"],
                    name="Concluintes", marker_color="#6C757D",
                    text=[fmt_int(v) if pd.notna(v) else "—" for v in part_cre["Concluintes"]],
                    textposition="outside",
                    textfont=dict(size=9, color=TEMA["texto"]),
                    hovertemplate="<b>%{x}</b><br>Concluintes: %{y}<extra></extra>",
                ))
                if "Inscritos" in part_cre.columns and part_cre["Inscritos"].notna().any():
                    fig_part_cre.add_trace(go.Bar(
                        x=part_cre["_cre_x"], y=part_cre["Inscritos"],
                        name="Inscritos", marker_color="#0D6EFD",
                        text=[fmt_int(v) if pd.notna(v) else "—" for v in part_cre["Inscritos"]],
                        textposition="inside",
                        textfont=dict(size=9, color=TEMA["texto"]),
                        hovertemplate="<b>%{x}</b><br>Inscritos: %{y}<extra></extra>",
                    ))
                fig_part_cre.add_trace(go.Bar(
                    x=part_cre["_cre_x"], y=part_cre["Presentes"],
                    name="Presentes 2 dias", marker_color="#198754",
                    text=part_cre["Presentes"],
                    textposition="outside",
                    textfont=dict(size=9, color=TEMA["texto"]),
                    hovertemplate="<b>%{x}</b><br>Presentes: %{y}<extra></extra>",
                ))
                # Linha de diferenca absoluta (Concluintes - Presentes) no eixo y2
                fig_part_cre.add_trace(go.Scatter(
                    x=part_cre["_cre_x"], y=part_cre["Diferença"],
                    name="Diferença (estudantes)", mode="lines+markers+text",
                    line=dict(color=COR_NEGATIVO, width=3),
                    marker=dict(size=10, color=COR_NEGATIVO, symbol="diamond"),
                    text=[fmt_int(v) for v in part_cre["Diferença"]],
                    textposition="top center",
                    textfont=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
                    yaxis="y2",
                    hovertemplate="<b>%{x}</b><br>Diferença: %{y} estudantes<extra></extra>",
                ))
                if "Tx_Inscrição" in part_cre.columns:
                    fig_part_cre.add_trace(go.Scatter(
                        x=part_cre["_cre_x"], y=part_cre["Tx_Inscrição"],
                        name="Tx inscrição (%)", mode="lines+markers",
                        line=dict(color=LARANJA_DESTAQUE, width=2.5),
                        marker=dict(size=8, color=LARANJA_DESTAQUE),
                        yaxis="y3",
                        hovertemplate="<b>%{x}</b><br>Tx inscrição: %{y:.1f}%<extra></extra>",
                    ))
                fig_part_cre.add_trace(go.Scatter(
                    x=part_cre["_cre_x"], y=part_cre["Tx_Part_Efetiva"],
                    name="Tx Part. Efetiva (%)", mode="lines+markers",
                    line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
                    marker=dict(size=8, color=COR_POSITIVO),
                    text=[fmt_pct(v) for v in part_cre["Tx_Part_Efetiva"]],
                    textposition="bottom center",
                    textfont=dict(size=9, color=COR_POSITIVO),
                    yaxis="y3",
                    hovertemplate="<b>%{x}</b><br>Tx Part. Efetiva: %{y:.1f}%<extra></extra>",
                ))
                # Anotacoes para maiores diferencas
                for _, row in top_dif.iterrows():
                    fig_part_cre.add_annotation(
                        x=nome_cre_curto(row["CRE"]),
                        y=row["Diferença"],
                        text=f"⚠️ {fmt_int(row['Diferença'])} ({fmt_pct(row['Dif_Pct'], 0)})",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor=COR_NEGATIVO,
                        ax=0,
                        ay=-40,
                        font=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
                        bgcolor="rgba(255,255,255,0.9)",
                        bordercolor=COR_NEGATIVO,
                        borderwidth=1,
                        yref="y2",
                    )
                
                # Calcular escalas
                max_dif = part_cre["Diferença"].max()
                y2_max = max_dif * 1.3 if pd.notna(max_dif) else 100
                max_conc = part_cre["Concluintes"].max()
                y1_max = max_conc * 1.15 if pd.notna(max_conc) else part_cre["Presentes"].max() * 1.15
                
                fig_part_cre.update_layout(
                    title="",
                    xaxis=dict(title="", tickangle=0, tickfont=dict(size=10)),
                    yaxis=dict(title="Estudantes", side="left", range=[0, y1_max]),
                    yaxis2=dict(title="Diferença (estudantes)", overlaying="y", side="right", position=0.98,
                                showgrid=False, range=[0, y2_max], tickfont=dict(size=9)),
                    yaxis3=dict(title="Taxa (%)", overlaying="y", side="right", position=1.0,
                                showgrid=False, range=[0, 105], tickfont=dict(size=9),
                                tickvals=[0, 25, 50, 75, 100]),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.35,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10),
                        bgcolor="rgba(255,255,255,0.8)",
                        bordercolor=COR_NEUTRO,
                        borderwidth=1,
                    ),
                    margin=dict(t=60, b=140),
                    barmode="group",
                )
                _chart(_finalizar_grafico(
                    fig_part_cre,
                    altura=CHART_H_BOX,
                    n_legend=4,
                    margin=dict(t=60, r=80, b=140, l=24),
                ))
                
                # Destacar CREs com maior diferenca em cards
                if not top_dif.empty:
                    st.markdown("<br>")
                    cols = st.columns(min(len(top_dif), 3))
                    for i, (_, row) in enumerate(top_dif.iterrows()):
                        with cols[i]:
                            st.markdown(
                                f"""
                                <div style="padding:10px; border-radius:8px; background-color:#FFF3F3; border-left:4px solid {COR_NEGATIVO};">
                                    <strong>{nome_cre_curto(row['CRE'])}</strong><br>
                                    <span style="color:{COR_NEGATIVO}; font-size:1.2em;">⚠️ {fmt_int(row['Diferença'])} estudantes</span> não participaram efetivamente<br>
                                    <small>({fmt_pct(row['Dif_Pct'])} dos concluintes)</small>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
        st.markdown("---")

    if lista_cres and cre_selecionadas and "CRE" in df_dep_cre_filt.columns:
        titulo_secao(f"Desempenho por CRE ({ano_ref})")
        df_cre_filt = df_dep_cre_filt[df_dep_cre_filt["CRE"].isin(cre_selecionadas)].copy()
        if not df_cre_filt.empty:
            c = (df_cre_filt.groupby("CRE", observed=True)[area]
                 .agg(Média="mean", Mediana="median", Estudantes="count").reset_index())
            c["Média"] = c["Média"].round(2)
            c["Mediana"] = c["Mediana"].round(2)
            c = c.sort_values("Média", ascending=False)

            part_integrada = _participacao_cre_tabela(
                tabelas, c["CRE"].tolist(), ano_ref, dep_escolhido,
            )
            if not part_integrada.empty:
                part_integrada = _enriquecer_participacao_taxas(part_integrada)
                titulo_secao(f"Desempenho × Participação — CREs ({ano_ref})")
                col_combo, col_quad = st.columns([1.55, 1])
                with col_combo:
                    _chart(fig_combo_participacao_desempenho(
                        part_integrada, c, "CRE", "Média",
                        titulo=f"Funil e média — {nome_area_ext(area)}",
                    ))
                with col_quad:
                    _chart(fig_quadrante_desempenho_participacao(
                        part_integrada, c, "CRE", "Média",
                        titulo="Quadrante: participação × desempenho",
                    ))
                st.caption(
                    "Quadrante: acima da mediana em ambos os eixos = CREs com boa adesão e bom desempenho."
                )

            col_cre_top, col_cre_bot = st.columns(2)
            with col_cre_top:
                cre_top = c.head(10).sort_values("Média", ascending=True)
                _chart(fig_ranking_horizontal(
                    cre_top, "CRE", "Média",
                    f"Top CREs — {nome_area_ext(area)}",
                    cor=AZUL_PRINCIPAL, altura=CHART_H_EVOLUCAO, casas_decimais=2,
                    media_ms=medias_ref["ms"], media_br=medias_ref["br"],
                    x_range=[0, 1000],
                ))
            with col_cre_bot:
                cre_bot = c.tail(10).sort_values("Média", ascending=True)
                _chart(fig_ranking_horizontal(
                    cre_bot, "CRE", "Média",
                    f"CREs com menores médias — {nome_area_ext(area)}",
                    cor=LARANJA_DESTAQUE, altura=CHART_H_EVOLUCAO, casas_decimais=2,
                    media_ms=medias_ref["ms"], media_br=medias_ref["br"],
                    x_range=[0, 1000],
                ))

            fig_box_cre = go.Figure()
            # Paleta fixa de cores hex (evita problemas com formatos rgb)
            cores_cre = [
                "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
                "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
                "#3366CC", "#DC3912", "#FF9900", "#109618", "#990099",
                "#0099C6", "#DD4477", "#66AA00", "#B82E2E", "#316395",
            ]
            for i, cre in enumerate(sorted(df_cre_filt["CRE"].unique())):
                row = linha_distribuicao(
                    df_dist_cre, ano=int(ano_ref),
                    dependencia=dep_escolhido, cre=cre,
                )
                if row is None:
                    continue
                stats = stats_box_quantis(row, area)
                if stats is None:
                    continue
                cor = cores_cre[i % len(cores_cre)]
                _add_box_stats(
                    fig_box_cre, stats, name=nome_cre_curto(cre), color=cor,
                    x_val=nome_cre_curto(cre), rotulo_mediana=True,
                    hover_titulo=str(cre),
                )

            if pd.notna(medias_ref["ms"]):
                _adicionar_referencias_ms_br(
                    fig_box_cre, medias_ref["ms"], medias_ref["br"],
                    sufixo_legenda="rede estadual",
                )
            fig_box_cre.update_layout(
                title=f"Distribuição das notas por CRE — {nome_area_ext(area)} ({ano_ref})",
                yaxis=dict(range=[0, 1000], title="Nota"),
                xaxis=dict(title="", showticklabels=False),
                showlegend=True,
                legend=_legenda_padrao(y_pos=-0.22, font_size=11.5),
                margin=dict(t=60, b=100),
                hovermode="closest",
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_box_cre, "Distribuição por CRE", altura=CHART_H_BOX, n_legend=2))
            
             # ============================================================
            # DETALHES DOS MUNICÍPIOS POR CRE
            # ============================================================
            st.markdown("---")
            titulo_secao(f"Detalhes dos municípios por CRE — {ano_ref}")

            # Seletores de CRE, ano e dependência
            col_det_cre, col_det_ano_cre, col_det_dep_cre = st.columns(3)
            with col_det_cre:
                cre_detalhe = st.selectbox(
                    "Selecione a CRE",
                    options=sorted(df_cre_filt["CRE"].dropna().unique()) if not df_cre_filt.empty else [],
                    format_func=nome_cre_curto,
                    key="cre_detalhe"
                )
            with col_det_ano_cre:
                anos_cre_disp = sorted(df_dep_cre["NU_ANO"].dropna().unique()) if not df_dep_cre.empty else []
                ano_detalhe_cre = st.selectbox(
                    "Selecione o ano",
                    options=anos_cre_disp,
                    index=len(anos_cre_disp)-1 if anos_cre_disp else 0,
                    key="ano_detalhe_cre"
                )
            with col_det_dep_cre:
                dep_detalhe_cre = st.selectbox(
                    "Selecione a dependência administrativa",
                    options=dep_selecionadas,
                    key="dep_detalhe_cre"
                )

            # CRE: linhas agregadas (evolucao_cre) — sem duplicar municípios
            df_cre_det = df_dep_cre[
                (df_dep_cre["CRE"] == cre_detalhe) &
                (df_dep_cre["NU_ANO"] == ano_detalhe_cre) &
                (df_dep_cre["DEP_ADM"] == dep_detalhe_cre)
            ].copy()
            df_muni_cre_det = df_dep_muni[
                (df_dep_muni["CRE"] == cre_detalhe) &
                (df_dep_muni["NU_ANO"] == ano_detalhe_cre) &
                (df_dep_muni["DEP_ADM"] == dep_detalhe_cre)
            ].copy()

            n_estudantes_cre = _presentes_cre_ano(
                tabelas, cre_detalhe, int(ano_detalhe_cre), dep_detalhe_cre,
            )
            n_inscritos_cre = _inscritos_cre_ano(
                tabelas, cre_detalhe, int(ano_detalhe_cre), dep_detalhe_cre,
            )
            if dep_detalhe_cre == "Estadual":
                conc_rows = _concluintes_cre_por_ano([cre_detalhe], int(ano_detalhe_cre))
                conc_cre_val = (
                    _safe_int_val(conc_rows.iloc[0]["Concluintes"])
                    if not conc_rows.empty else 0
                )
            else:
                conc_cre_val = 0
            tx_part_efetiva_cre = (
                round(100 * n_estudantes_cre / conc_cre_val, 1)
                if conc_cre_val > 0 else pd.NA
            )
            tx_inscricao_cre = (
                round(100 * n_inscritos_cre / conc_cre_val, 1)
                if conc_cre_val > 0 and n_inscritos_cre > 0 else pd.NA
            )

            if not df_cre_det.empty or n_estudantes_cre > 0 or conc_cre_val > 0:
                areas_cols = list(AREAS.keys())
                if not df_cre_det.empty:
                    df_cre_det["MEDIA_GERAL"] = df_cre_det[areas_cols].mean(axis=1)
                    media_geral_cre = df_cre_det["MEDIA_GERAL"].mean()
                    mediana_geral_cre = df_cre_det["MEDIA_GERAL"].median()
                else:
                    media_geral_cre = np.nan
                    mediana_geral_cre = np.nan

                # Cor da borda KPI
                cor_borda_kpi_cre = COR_POSITIVO if (pd.notna(tx_part_efetiva_cre) and tx_part_efetiva_cre >= 80) else (
                    COR_ATENCAO if pd.notna(tx_part_efetiva_cre) and tx_part_efetiva_cre >= 60 else COR_CRITICO
                )

                col_kpi1_cre, col_kpi2_cre, col_kpi3_cre, col_kpi4_cre, col_kpi5_cre = st.columns(5)
                media_geral_txt = f"{media_geral_cre:.1f}" if pd.notna(media_geral_cre) else "—"
                mediana_geral_txt = f"{mediana_geral_cre:.1f}" if pd.notna(mediana_geral_cre) else "—"
                with col_kpi1_cre:
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MÉDIA GERAL</div>
                            <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{media_geral_txt}</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi2_cre:
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MEDIANA DA MÉDIA GERAL</div>
                            <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{mediana_geral_txt}</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi3_cre:
                    conc_cre_txt = str(conc_cre_val) if dep_detalhe_cre == "Estadual" else "—"
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">CONCLUINTES 3º ANO E.M</div>
                            <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{conc_cre_txt}</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi4_cre:
                    tx_insc_str = f"{tx_inscricao_cre:.1f}%".replace(".", ",") if pd.notna(tx_inscricao_cre) else "—"
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {LARANJA_DESTAQUE}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX INSCRIÇÃO</div>
                            <div style="font-size:28px; font-weight:700; color:{LARANJA_DESTAQUE}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_insc_str}</div>
                            <div style="font-size:9px; color:#6c757d; margin-top:4px;">{n_inscritos_cre} inscritos / concluintes</div>
                        </div>""", unsafe_allow_html=True)
                with col_kpi5_cre:
                    tx_str_cre = f"{tx_part_efetiva_cre:.1f}%".replace(".", ",") if pd.notna(tx_part_efetiva_cre) else "—"
                    st.markdown(
                        f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {cor_borda_kpi_cre}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                            <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX PART. EFETIVA</div>
                            <div style="font-size:28px; font-weight:700; color:{cor_borda_kpi_cre}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_str_cre}</div>
                            <div style="font-size:9px; color:#6c757d; margin-top:4px; line-height:1.3;">
                                {n_estudantes_cre} presentes nos 2 dias
                                {f"/ {conc_cre_val} concluintes" if dep_detalhe_cre == "Estadual" else ""}<br>
                                (escolas {dep_detalhe_cre.lower()} da CRE)
                            </div>
                        </div>""", unsafe_allow_html=True)

                # Boxplot com todas as áreas
                st.markdown(f"**Distribuição das notas — {cre_detalhe} — {ano_detalhe_cre}**")

                fig_box_cre_det = go.Figure()
                cores_areas_cre = {
                    "CN": "#2E8B57", "CH": "#FF8C00", "LC": "#1E90FF",
                    "MT": "#DC143C", "REDACAO": "#DAA520"
                }

                # Calcular médias de referência MS e BR
                medias_ref_ms_cre_det = {}
                medias_ref_br_cre_det = {}
                if df_br is not None:
                    df_br_ano_cre = df_br[(df_br["NU_ANO"] == ano_detalhe_cre) & (df_br["DEP_ADM"] == dep_detalhe_cre)]
                    df_ms_ano_cre = df_dep_cre[
                        (df_dep_cre["NU_ANO"] == ano_detalhe_cre)
                        & (df_dep_cre["DEP_ADM"] == dep_detalhe_cre)
                    ]
                    for key in AREAS.keys():
                        if not df_ms_ano_cre.empty:
                            medias_ref_ms_cre_det[key] = df_ms_ano_cre[key].mean()
                        if not df_br_ano_cre.empty:
                            medias_ref_br_cre_det[key] = df_br_ano_cre[key].mean()

                usar_ind_cre = (
                    df_notas_individuais is not None
                    and not df_notas_individuais.empty
                    and tem_notas_individuais_ano(df_notas_individuais, int(ano_detalhe_cre))
                )
                df_cre_ind = (
                    filtrar_notas_individuais(
                        df_notas_individuais,
                        ano=int(ano_detalhe_cre),
                        cre=cre_detalhe,
                        dependencia=dep_detalhe_cre,
                    )
                    if usar_ind_cre else pd.DataFrame()
                )
                row_cre_det = linha_distribuicao(
                    df_dist_cre, ano=int(ano_detalhe_cre),
                    dependencia=dep_detalhe_cre, cre=cre_detalhe,
                )

                for i, (key, nome) in enumerate(AREAS_COMPLETO.items()):
                    cor_cre = cores_areas_cre.get(key, CORES_AREAS.get(key, AZUL_PRINCIPAL))
                    stats = None
                    media_cre_area = np.nan

                    if usar_ind_cre and not df_cre_ind.empty:
                        s_area = notas_area(df_cre_ind, key)
                        if s_area.empty:
                            continue
                        stats = _stats_box(s_area)
                        if stats is None:
                            continue
                        media_cre_area = stats["mean"]
                        _add_box(
                            fig_box_cre_det, s_area, nome, cor_cre, x_val=nome,
                            rotulo_mediana=True, hover_titulo=nome,
                        )
                        _add_scatter_notas(
                            fig_box_cre_det, nome, s_area,
                            color=_hex_to_rgba(cor_cre, 0.35),
                        )
                    elif row_cre_det is not None:
                        stats = stats_box_quantis(row_cre_det, key)
                        if stats is None:
                            continue
                        media_cre_area = stats["mean"]
                        _add_box_stats(
                            fig_box_cre_det, stats, name=nome, color=cor_cre,
                            x_val=nome, rotulo_mediana=True, hover_titulo=nome,
                        )
                    else:
                        continue

                    # Delta MS
                    if key in medias_ref_ms_cre_det and pd.notna(medias_ref_ms_cre_det[key]) and medias_ref_ms_cre_det[key] > 0:
                        delta_ms_cre = media_cre_area - medias_ref_ms_cre_det[key]
                        sinal_ms_cre = "+" if delta_ms_cre >= 0 else ""
                        cor_delta_ms_cre = COR_POSITIVO if delta_ms_cre >= 0 else COR_CRITICO
                        fig_box_cre_det.add_annotation(
                            x=nome,
                            y=stats["up"] + 45,
                            text=f"<b>ΔMS {sinal_ms_cre}{delta_ms_cre:.1f}</b>",
                            showarrow=False,
                            xanchor="right",
                            xshift=-25,
                            font=dict(size=9, color=cor_delta_ms_cre, family="Arial Black"),
                            bgcolor="rgba(255,255,255,0.85)",
                            hovertext=(
                                f"Média {cre_detalhe}: {media_cre_area:.1f}<br>"
                                f"Média Estado (MS): {medias_ref_ms_cre_det[key]:.1f}<br>"
                                f"Diferença: {sinal_ms_cre}{delta_ms_cre:.1f}"
                            ),
                            hoverlabel=dict(bgcolor="white", font_size=10),
                        )

                    # Delta BR
                    if key in medias_ref_br_cre_det and pd.notna(medias_ref_br_cre_det[key]) and medias_ref_br_cre_det[key] > 0:
                        delta_br_cre = media_cre_area - medias_ref_br_cre_det[key]
                        sinal_br_cre = "+" if delta_br_cre >= 0 else ""
                        cor_delta_br_cre = COR_POSITIVO if delta_br_cre >= 0 else COR_CRITICO
                        fig_box_cre_det.add_annotation(
                            x=nome,
                            y=stats["up"] + 45,
                            text=f"<b>ΔBR {sinal_br_cre}{delta_br_cre:.1f}</b>",
                            showarrow=False,
                            xanchor="left",
                            xshift=25,
                            font=dict(size=9, color=cor_delta_br_cre, family="Arial Black"),
                            bgcolor="rgba(255,255,255,0.85)",
                            hovertext=(
                                f"Média {cre_detalhe}: {media_cre_area:.1f}<br>"
                                f"Média Brasil: {medias_ref_br_cre_det[key]:.1f}<br>"
                                f"Diferença: {sinal_br_cre}{delta_br_cre:.1f}"
                            ),
                            hoverlabel=dict(bgcolor="white", font_size=10),
                        )

                # Linhas de referência MS e BR
                fig_box_cre_det.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode="lines",
                    line=dict(color=LARANJA_DESTAQUE, width=2, dash="dash"),
                    name="Média MS — rede estadual",
                    hoverinfo="skip",
                ))
                fig_box_cre_det.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode="lines",
                    line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
                    name="Média BR — rede estadual",
                    hoverinfo="skip",
                ))

                fig_box_cre_det.update_layout(
                    title=dict(text=""),
                    yaxis=dict(range=[0, 1000], title="Nota"),
                    xaxis=dict(title="", showticklabels=False),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.35,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10, color=TEMA["texto"]),
                        bgcolor="rgba(255,255,255,0.9)",
                        bordercolor=COR_NEUTRO,
                        borderwidth=1,
                        itemsizing="constant",
                    ),
                    margin=dict(t=60, b=140),
                    plot_bgcolor="rgba(250,252,255,1)",
                    paper_bgcolor="#FFFFFF",
                )
                _chart(_finalizar_boxplot(fig_box_cre_det, f"Detalhe CRE — {cre_detalhe}", altura=CHART_H_BOX, n_legend=1))

                if usar_ind_cre and not df_cre_ind.empty:
                    s_hist_cre = notas_area(df_cre_ind, area)
                    if not s_hist_cre.empty:
                        titulo_secao(
                            f"Histograma — {nome_area_ext(area)}",
                            f"Distribuição individual dos estudantes da CRE ({len(s_hist_cre):,} com nota válida)."
                        )
                        _chart(_fig_histogram_notas(
                            s_hist_cre,
                            f"Distribuição — {cre_detalhe} ({nome_area_ext(area)}, 2024)",
                            cor=CORES_AREAS.get(area, AZUL_PRINCIPAL),
                            media_ref=medias_ref_ms_cre_det.get(area),
                        ))

                # Legendas explicativas
                st.markdown(
                    """<div style="display: flex; gap: 20px; margin: 8px 0 12px; font-size: 12px; flex-wrap: wrap;">
                        <div><span style="color: #198754; font-weight: bold;">ΔMS</span> = diferença vs média do Estado</div>
                        <div><span style="color: #198754; font-weight: bold;">ΔBR</span> = diferença vs média do Brasil</div>
                        <div><span style="color: #198754;">■</span> acima da média <span style="color: #DC2626;">■</span> abaixo da média</div>
                    </div>""", unsafe_allow_html=True
                )

                # Legenda de cores das áreas
                cores_legenda_cre = " ".join([
                    f"<span style='color: {cores_areas_cre.get(k, CORES_AREAS.get(k, AZUL_PRINCIPAL))}; font-weight: bold;'>●</span> {nome_area_ext(k)}"
                    for k in AREAS.keys()
                ])
                st.markdown(
                    f"""<div style="display: flex; gap: 16px; margin: 4px 0 16px; font-size: 11px; flex-wrap: wrap; color: #6c757d;">
                        {cores_legenda_cre}
                    </div>""", unsafe_allow_html=True
                )

                # Tabela de municípios da CRE
                st.markdown(f"**Municípios da {cre_detalhe} ({ano_detalhe_cre}) — {dep_detalhe_cre}**")

                # Agregar por município
                muni_col_cre = "NO_MUNICIPIO_ESC"
                if not df_muni_cre_det.empty and muni_col_cre in df_muni_cre_det.columns:
                    muni_agg = df_muni_cre_det.groupby(muni_col_cre, observed=True).agg(
                        Estudantes=(area, "count"),
                        **{AREAS_COMPLETO[k]: (k, "mean") for k in AREAS.keys()},
                    ).reset_index()
                    muni_agg = muni_agg.rename(columns={muni_col_cre: "Município"})

                    part_muni_cre = _participacao_municipio_tabela(
                        tabelas,
                        muni_agg["Município"].tolist(),
                        int(ano_detalhe_cre),
                        dep_detalhe_cre,
                        col_municipio=muni_col_cre,
                    )
                    if not part_muni_cre.empty:
                        muni_agg = muni_agg.drop(
                            columns=["Concluintes", "Tx_Part_Efetiva", "Presentes"],
                            errors="ignore",
                        ).merge(
                            part_muni_cre[["Município", "Presentes", "Concluintes", "Taxa_Efetiva"]],
                            on="Município",
                            how="left",
                        )
                        muni_agg["Estudantes"] = muni_agg["Presentes"].fillna(muni_agg["Estudantes"]).astype(int)
                        muni_agg["Tx_Part_Efetiva"] = muni_agg.get("Tx_Part_Efetiva", muni_agg.get("Taxa_Efetiva"))
                        if "Tx_Inscrição" not in muni_agg.columns:
                            muni_agg["Tx_Inscrição"] = _pct_taxa(
                                muni_agg.get("Inscritos", pd.NA), muni_agg["Concluintes"],
                            )
                        muni_agg = muni_agg.drop(columns=["Presentes", "Taxa_Efetiva"], errors="ignore")
                    elif dep_detalhe_cre == "Estadual":
                        df_conc_muni_cre = carregar_concluintes_municipio()
                        if not df_conc_muni_cre.empty:
                            for idx_muni, row_muni in muni_agg.iterrows():
                                muni_nome = row_muni["Município"]
                                conc_row_muni = df_conc_muni_cre[
                                    (df_conc_muni_cre["MUNICIPIO"].apply(_normalizar_nome_municipio) == _normalizar_nome_municipio(muni_nome))
                                    & (df_conc_muni_cre["NU_ANO"] == ano_detalhe_cre)
                                ]
                                muni_agg.at[idx_muni, "Concluintes"] = (
                                    _safe_int_val(conc_row_muni.iloc[0]["Concluintes"])
                                    if not conc_row_muni.empty else 0
                                )
                        else:
                            muni_agg["Concluintes"] = 0
                        muni_agg["Concluintes"] = pd.to_numeric(muni_agg["Concluintes"], errors="coerce").fillna(0).astype(int)
                        muni_agg["Tx_Part_Efetiva"] = _pct_taxa(muni_agg["Estudantes"], muni_agg["Concluintes"])
                    else:
                        muni_agg["Concluintes"] = pd.NA
                        muni_agg["Tx_Part_Efetiva"] = pd.NA

                    # Arredondar médias
                    for k in COLS_NOTAS:
                        muni_agg[AREAS_COMPLETO[k]] = muni_agg[AREAS_COMPLETO[k]].round(1)

                    # Reordenar colunas
                    cols_muni = ["Município", "Concluintes", "Inscritos", "Tx_Inscrição", "Tx_Part_Efetiva"]
                    for k in COLS_NOTAS:
                        cols_muni.append(AREAS_COMPLETO[k])
                    muni_agg = muni_agg[[c for c in cols_muni if c in muni_agg.columns]]

                    # Ordenar por média geral
                    if AREAS_COMPLETO.get("MEDIA_GERAL") in muni_agg.columns:
                        muni_agg = muni_agg.sort_values(AREAS_COMPLETO["MEDIA_GERAL"], ascending=False)

                    # Calcular médias de referência para coloração
                    medias_ref_ms_muni = {}
                    medias_ref_br_muni = {}
                    for k in COLS_NOTAS:
                        medias_ref_ms_muni[k] = float(df_muni_cre_det[k].dropna().mean()) if not df_muni_cre_det.empty else (
                            float(df_cre_det[k].dropna().mean()) if not df_cre_det.empty else np.nan
                        )
                        if df_br is not None:
                            df_br_ano_muni = df_br[(df_br["NU_ANO"] == ano_detalhe_cre) & (df_br["DEP_ADM"] == dep_detalhe_cre)]
                            medias_ref_br_muni[k] = float(df_br_ano_muni[k].dropna().mean()) if not df_br_ano_muni.empty else np.nan
                        else:
                            medias_ref_br_muni[k] = np.nan

                    # Formatar para exibição
                    muni_display = muni_agg.copy()
                    for col in muni_display.columns:
                        if col in ("Concluintes", "Inscritos"):
                            muni_display[col] = muni_display[col].apply(lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—")
                        elif col in ("Tx_Part_Efetiva", "Tx_Inscrição"):
                            muni_display[col] = muni_display[col].apply(lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—")
                        elif col in [AREAS_COMPLETO[k] for k in AREAS.keys()]:
                            muni_display[col] = muni_display[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—")

                    # Estilização
                    area_labels_muni_cre = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
                    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in muni_agg.columns:
                        area_labels_muni_cre["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

                    styled_muni_cre, css_cabecalho_muni_cre = _estilizar_tabela(
                        df_display=muni_display,
                        df_raw=muni_agg,
                        colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in muni_agg.columns],
                        cores_area=CORES_AREAS,
                        medias_ms=medias_ref_ms_muni,
                        medias_br=medias_ref_br_muni,
                        col_escola="Município",
                        area_labels=area_labels_muni_cre,
                    )

                    if css_cabecalho_muni_cre:
                        st.markdown(f"""
                        <style>
                        {css_cabecalho_muni_cre}
                        </style>
                        """, unsafe_allow_html=True)

                    st.markdown("""
                    <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
                        <b>Fonte das médias:</b> <span style='color: #059669;'>verde</span> = acima MS e BR,
                        <span style='color: #2563EB;'>azul</span> = acima de MS e abaixo de BR,
                        <span style='color: #DC2626;'>vermelho</span> = abaixo de ambos |
                        <b>Cores das áreas:</b> fundo colorido conforme legenda dos gráficos
                    </div>
                    """, unsafe_allow_html=True)

                    n_muni = len(muni_display)
                    altura_muni = min(max(n_muni * 35 + 45, 100), 520)
                    st.dataframe(styled_muni_cre, width="stretch", hide_index=True, height=altura_muni)
                else:
                    st.info("Dados de município não disponíveis para esta CRE.")
            else:
                st.info(f"Sem dados para {cre_detalhe} em {ano_detalhe_cre} — {dep_detalhe_cre}.")
                
            st.markdown("---")
            titulo_secao(f"Tabela completa de desempenho — CREs ({ano_ref})")

            # Calcular médias de referência MS/BR por área para comparação
            # MS: df_dep_cre_filt (nível CRE, sem duplicar municípios) | BR: df_br no ano_ref e dep
            medias_ref_ms_cre = {}
            medias_ref_br_cre = {}
            for col in COLS_NOTAS:
                medias_ref_ms_cre[col] = float(df_dep_cre_filt[col].dropna().mean()) if not df_dep_cre_filt.empty else np.nan
                if df_br is not None and ano_ref != "Todos os anos":
                    df_br_ano_dep = df_br[(df_br["NU_ANO"] == ano_ref) & (df_br["DEP_ADM"] == dep_escolhido)]
                    medias_ref_br_cre[col] = float(df_br_ano_dep[col].dropna().mean()) if not df_br_ano_dep.empty else np.nan
                else:
                    medias_ref_br_cre[col] = np.nan
            if "MEDIA_GERAL" in df_dep_cre_filt.columns:
                medias_ref_ms_cre["MEDIA_GERAL"] = float(df_dep_cre_filt["MEDIA_GERAL"].dropna().mean()) if not df_dep_cre_filt.empty else np.nan
                if df_br is not None and ano_ref != "Todos os anos":
                    df_br_ano_dep = df_br[(df_br["NU_ANO"] == ano_ref) & (df_br["DEP_ADM"] == dep_escolhido)]
                    medias_ref_br_cre["MEDIA_GERAL"] = float(df_br_ano_dep["MEDIA_GERAL"].dropna().mean()) if not df_br_ano_dep.empty else np.nan
                else:
                    medias_ref_br_cre["MEDIA_GERAL"] = np.nan

            # Montar tabela com médias de TODAS as áreas de conhecimento (SEM medianas)
            agg_dict = {"Estudantes": (area, "count")}
            for col in COLS_NOTAS:
                agg_dict[AREAS_COMPLETO[col]] = (col, "mean")
            if "MEDIA_GERAL" in df_cre_filt.columns:
                agg_dict[AREAS_COMPLETO["MEDIA_GERAL"]] = ("MEDIA_GERAL", "mean")

            tabela_completa = df_cre_filt.groupby("CRE", observed=True).agg(**agg_dict).reset_index()
            
            part_tab = _participacao_cre_tabela(
                tabelas,
                tabela_completa["CRE"].tolist(),
                ano_ref,
                dep_escolhido,
            )
            if not part_tab.empty:
                tabela_completa = tabela_completa.drop(
                    columns=["Concluintes", "Tx_Part_Efetiva"],
                    errors="ignore",
                ).merge(
                    part_tab[[
                        c for c in [
                            "CRE", "Presentes", "Inscritos", "Concluintes",
                            "Tx_Inscrição", "Tx_Part_Efetiva",
                        ] if c in part_tab.columns
                    ]],
                    on="CRE",
                    how="left",
                )
                tabela_completa["Estudantes"] = tabela_completa["Presentes"].fillna(
                    tabela_completa["Estudantes"]
                ).astype(int)
                tabela_completa = tabela_completa.drop(columns=["Presentes"], errors="ignore")
            else:
                conc_tab = _concluintes_cre_por_ano(tabela_completa["CRE"].tolist(), ano_ref)
                if not conc_tab.empty:
                    tabela_completa = tabela_completa.merge(conc_tab, on="CRE", how="left")
                else:
                    tabela_completa["Concluintes"] = pd.NA
                tabela_completa["Concluintes"] = pd.to_numeric(tabela_completa["Concluintes"], errors="coerce")
                tabela_completa["Tx_Part_Efetiva"] = _pct_taxa(
                    tabela_completa["Estudantes"], tabela_completa["Concluintes"],
                )

            # Arredondar colunas numéricas para 1 casa decimal
            for col in tabela_completa.columns:
                if col not in ("CRE", "Estudantes", "Concluintes"):
                    tabela_completa[col] = tabela_completa[col].round(1)

            tabela_completa = tabela_completa.sort_values(AREAS_COMPLETO.get("MEDIA_GERAL", AREAS_COMPLETO[area]), ascending=False)

            cols_finais = ["CRE", "Tx_Inscrição", "Tx_Part_Efetiva", "Inscritos", "Concluintes"]
            for k in COLS_NOTAS:
                col_nome = AREAS_COMPLETO[k]
                if col_nome in tabela_completa.columns:
                    cols_finais.append(col_nome)
            tabela_completa = tabela_completa[[c for c in cols_finais if c in tabela_completa.columns]]
            
            for tx_col in ("Tx_Inscrição", "Tx_Part_Efetiva"):
                if tx_col in tabela_completa.columns:
                    tabela_completa[tx_col] = tabela_completa[tx_col].apply(
                        lambda x, c=tx_col: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—"
                    )

            tabela_display = tabela_completa.copy()
            if "CRE" in tabela_display.columns:
                tabela_display["CRE"] = tabela_display["CRE"].map(nome_cre_curto)
            for col in tabela_display.columns:
                if col in ("Concluintes", "Inscritos"):
                    tabela_display[col] = tabela_display[col].apply(
                        lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"
                    )
                elif col in [AREAS_COMPLETO[k] for k in AREAS.keys()]:
                    tabela_display[col] = tabela_display[col].apply(
                        lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—"
                    )

            # ============================================================
            # ESTILIZAÇÃO VIA FUNÇÃO UTILITÁRIA
            # ============================================================
            area_labels_cre = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
            if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela_completa.columns:
                area_labels_cre["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]
            
            styled_cre, css_cabecalho_cre = _estilizar_tabela(
                df_display=tabela_display,
                df_raw=tabela_completa,
                colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in tabela_completa.columns],
                cores_area=CORES_AREAS,
                medias_ms=medias_ref_ms_cre,
                medias_br=medias_ref_br_cre,
                col_escola="CRE",
                area_labels=area_labels_cre,
                tx_threshold_vermelho=70.0,
                tx_threshold_laranja=None,
                tx_threshold_verde=None,
                colorir_linha_tx=True,
            )
            
            # CSS customizado para cabeçalhos coloridos
            if css_cabecalho_cre:
                st.markdown(f"""
                <style>
                {css_cabecalho_cre}
                </style>
                """, unsafe_allow_html=True)
            
            # Legendas explicativas
            st.markdown("""
            <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
                <b>Tx inscrição</b> = inscritos ÷ concluintes · <b>Tx part. efetiva</b> = presentes ÷ concluintes |
                <b>Tx part. efetiva &lt; 70%:</b> <span style='color: #C03A2B; font-weight: 700;'>participação preocupante</span> |
                <b>Médias:</b> <span style='color: #0F8A5F; font-weight: 700;'>verde</span> = acima da média nacional (BR),
                <span style='color: #003F7F; font-weight: 700;'>azul</span> = acima da média estadual (MS) e abaixo de BR,
                <span style='color: #C03A2B; font-weight: 700;'>vermelho</span> = abaixo da média estadual (MS) |
                <b>Cores das áreas:</b> fundo colorido conforme legenda dos gráficos
            </div>
            """, unsafe_allow_html=True)

            n_cres = len(tabela_completa)  # ✅ DataFrame original
            altura_cre = min(max(n_cres * 35 + 45, 100), 520)
            st.dataframe(styled_cre, width="stretch", hide_index=True, height=altura_cre)
        else:
            st.info("Dados de CRE não disponíveis para o recorte selecionado.")
    else:
        st.info("Dados de CRE não disponíveis para a tabela.")

# ============================================================
# ABA 6 - MUNICÍPIOS (COM SELETOR DE DEPENDÊNCIA)
# ============================================================
def aba_municipios(
    df_ms_enriq,
    df_filt_ms_full=None,
    df_br=None,
    dep_selecionadas=None,
    df_bruta_ms_enriq=None,
    tabelas=None,
    df_notas_individuais=None,
    anos_sel=None,
):
    if dep_selecionadas is None:
        dep_selecionadas = ["Estadual", "Federal", "Municipal", "Privada"]
    tabelas = tabelas or {}
    if anos_sel:
        df_ms_enriq, df_filt_ms_full = _reconstruir_bases_territoriais(
            tabelas, list(anos_sel), dep_selecionadas, df_ms_enriq, df_filt_ms_full,
        )

    titulo_secao(
        "Análise por município",
        "Desempenho municipal com destaques, pontos de atenção e identificação da CRE."
    )

    st.markdown("### Filtros de análise municipal")
    col_filt_dep, col_filt_area = st.columns(2)
    with col_filt_dep:
        dep_escolhido = st.selectbox(
            "Selecione a dependência administrativa",
            options=dep_selecionadas,
            key="dep_municipios"
        )
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_municipios"
        )

    df_base = _df_base_territorial(df_ms_enriq, df_filt_ms_full)
    if "DEP_ADM" not in df_base.columns:
        st.warning("Dados municipais indisponíveis no recorte atual. Recarregue a página ou ajuste os filtros laterais.")
        return
    df_dep = df_base[df_base["DEP_ADM"] == dep_escolhido].copy()
    df_dep_muni = _linhas_nivel_municipio(df_dep)
    tabelas = tabelas or {}
    df_dist_muni = filtrar_distribuicao(
        tabelas.get("distribuicao_municipio", pd.DataFrame()),
        dependencia=dep_escolhido,
    )
    if "CRE" not in df_dep.columns:
        df_dep["CRE"] = pd.NA
    if "CRE" not in df_dep_muni.columns:
        df_dep_muni["CRE"] = pd.NA

    if df_dep_muni.empty and df_dep.empty:
        st.warning(f"Sem dados para {dep_escolhido} no recorte.")
        return

    medias_ref = calcular_medias_referencia(
        df_dep_muni if not df_dep_muni.empty else df_dep,
        df_br, area,
    ) if df_br is not None else {"ms": None, "br": None}

    anos_disponiveis = sorted(df_dep_muni["NU_ANO"].unique()) if not df_dep_muni.empty else sorted(df_dep["NU_ANO"].unique())
    ano_opcoes = [str(ano) for ano in anos_disponiveis] + ["Todos os anos"]
    default_index = len(anos_disponiveis) - 1 if anos_disponiveis else 0

    st.markdown("### Filtro de ano")
    ano_escolhido = st.selectbox(
        "Selecione o ano para análise municipal",
        options=ano_opcoes,
        index=default_index,
        key="ano_municipios"
    )

    if ano_escolhido == "Todos os anos":
        df_filt = df_dep_muni if not df_dep_muni.empty else df_dep
        ano_ref = "Todos os anos"
    else:
        ano_ref = int(ano_escolhido)
        base_muni = df_dep_muni if not df_dep_muni.empty else df_dep
        df_filt = base_muni[base_muni["NU_ANO"] == ano_ref].copy()

    if df_filt.empty:
        st.warning(f"Sem dados para o ano {ano_escolhido}.")
        return

    muni_col = _coluna_municipio(df_filt) or "NO_MUNICIPIO_ESC"
    if muni_col not in df_filt.columns:
        st.warning("Coluna de município indisponível nos dados.")
        return

    m = (df_filt.dropna(subset=[muni_col])
         .groupby(muni_col)
         .agg(
             **{AREAS_COMPLETO[k]: (k, "mean") for k in AREAS.keys()},
             Mediana=(area, "median"),
             Estudantes=(area, "count")
         ).reset_index())
    for k in COLS_NOTAS:
        m[AREAS_COMPLETO[k]] = m[AREAS_COMPLETO[k]].round(1)
    m["Mediana"] = m["Mediana"].round(2)
    m = m[m["Estudantes"] >= 10].sort_values(AREAS_COMPLETO[area], ascending=False)

    part_muni_vis = _participacao_municipio_tabela(
        tabelas, m[muni_col].tolist(), ano_ref, dep_escolhido, col_municipio=muni_col,
    )
    if not part_muni_vis.empty and not m.empty:
        part_muni_vis = _enriquecer_participacao_taxas(part_muni_vis)
        m_vis = m.rename(columns={muni_col: "Município"}).rename(
            columns={AREAS_COMPLETO[area]: "Média"},
        )
        top_vis = m_vis.head(min(15, len(m_vis)))
        part_top = part_muni_vis[part_muni_vis["Município"].isin(top_vis["Município"])]
        if not part_top.empty:
            titulo_secao(f"Desempenho × Participação — municípios ({ano_ref})")
            col_m_c, col_m_q = st.columns([1.55, 1])
            with col_m_c:
                _chart(fig_combo_participacao_desempenho(
                    part_top, top_vis, "Município", "Média",
                    titulo=f"Top municípios — {nome_area_ext(area)}",
                ))
            with col_m_q:
                _chart(fig_quadrante_desempenho_participacao(
                    part_muni_vis, m_vis, "Município", "Média",
                    titulo="Quadrante municipal",
                ))

    st.markdown("### Destaques")
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    if not m.empty:
        media_col = AREAS_COMPLETO[area]
        kpi_card(col_d1, "Maior média", fmt_float(m[media_col].iloc[0]),
                 m.iloc[0][muni_col][:25], status="positivo")
        kpi_card(col_d2, "Menor média", fmt_float(m[media_col].iloc[-1]),
                 m.iloc[-1][muni_col][:25], status="critico")
        idx_max_est = m["Estudantes"].idxmax()
        kpi_card(col_d3, "Mais estudantes", fmt_int(m.loc[idx_max_est, "Estudantes"]),
                 m.loc[idx_max_est, muni_col][:25])
        if medias_ref["ms"] is not None:
            n_abaixo = int((m[media_col] < medias_ref["ms"]).sum())
            kpi_card(col_d4, "Abaixo da média MS", f"{n_abaixo} municípios",
                     f"de {len(m)} analisados", status="atencao" if n_abaixo > len(m)//2 else "neutro")
        else:
            kpi_card(col_d4, "Municípios analisados", fmt_int(len(m)), "")
    else:
        st.info("Sem dados suficientes para destaques.")

    if not m.empty and medias_ref["ms"] is not None:
        st.markdown("### Pontos de atenção")
        idx_max_est = m["Estudantes"].idxmax()
        muni_mais_est = m.loc[idx_max_est]
        media_col = AREAS_COMPLETO[area]
        if muni_mais_est[media_col] < medias_ref["ms"]:
            achado("atencao", "Município com maior volume está abaixo da média",
                   f"{muni_mais_est[muni_col]} tem {fmt_int(muni_mais_est['Estudantes'])} "
                   f"estudantes e média {fmt_float(muni_mais_est[media_col])} (média: {fmt_float(medias_ref['ms'])}).")
        abaixo = m[m[media_col] < medias_ref["ms"]]
        if len(abaixo) > len(m) * 0.5:
            achado("critico", "Maioria dos municípios abaixo da média",
                   f"{len(abaixo)} de {len(m)} ({fmt_float(100*len(abaixo)/len(m))}%).")
        elif len(abaixo) > len(m) * 0.25:
            achado("atencao", "Parte significativa abaixo da média",
                   f"{len(abaixo)} de {len(m)} ({fmt_float(100*len(abaixo)/len(m))}%).")

    col_top, col_bot = st.columns(2)
    with col_top:
        top15 = m.head(15).rename(columns={muni_col: "Município"})
        _chart(fig_ranking_horizontal(
            top15, "Município", AREAS_COMPLETO[area],
            f"Top 15 municípios — {nome_area_ext(area)}",
            cor=COR_POSITIVO, altura=CHART_H_RANKING, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=[0, 1000],
        ))
    with col_bot:
        bot15 = m.tail(15).sort_values(AREAS_COMPLETO[area], ascending=True).rename(columns={muni_col: "Município"})
        _chart(fig_ranking_horizontal(
            bot15, "Município", AREAS_COMPLETO[area],
            f"15 menores médias — {nome_area_ext(area)}",
            cor=COR_CRITICO, altura=CHART_H_RANKING, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
            x_range=[0, 1000],
        ))

    # ============================================================
    # GRÁFICO DE PARTICIPAÇÃO POR MUNICÍPIO (abaixo do 1º gráfico)
    # ============================================================
    # Construir tabela com concluintes, inscritos (base bruta) e presentes (base filtrada)
    tabela = m.copy().rename(columns={muni_col: "Município"})
    cre_por_muni = (df_filt.dropna(subset=[muni_col, "CRE"])
                    .groupby(muni_col)["CRE"]
                    .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else pd.NA)
                    .reset_index()
                    .rename(columns={muni_col: "Município", "CRE": "CRE"}))
    tabela = tabela.merge(cre_por_muni, on="Município", how="left")

    # Participação municipal via municipios.parquet (presentes, concluintes, taxa efetiva)
    part_muni_agg = _participacao_municipio_tabela(
        tabelas,
        tabela["Município"].tolist(),
        ano_ref,
        dep_escolhido,
        col_municipio=muni_col,
    )
    if not part_muni_agg.empty:
        tabela = tabela.drop(
            columns=["Presentes", "Concluintes", "Inscritos", "Taxa_Efetiva", "Taxa_Part"],
            errors="ignore",
        ).merge(part_muni_agg, on="Município", how="left")
        tabela["Presentes"] = tabela["Presentes"].fillna(tabela["Estudantes"]).astype(int)
        tabela["Concluintes"] = pd.to_numeric(tabela["Concluintes"], errors="coerce").fillna(0).astype(int)
        if "Inscritos" not in tabela.columns:
            tabela["Inscritos"] = tabela["Concluintes"]
        else:
            tabela["Inscritos"] = pd.to_numeric(tabela["Inscritos"], errors="coerce").fillna(0).astype(int)
        tabela["Taxa_Efetiva"] = pd.to_numeric(tabela["Taxa_Efetiva"], errors="coerce")
        tabela["Taxa_Efetiva"] = tabela["Taxa_Efetiva"].fillna(
            tabela["Presentes"] / tabela["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)
    else:
        presentes_muni = (
            df_filt.dropna(subset=[muni_col])
            .groupby(muni_col)
            .agg(Presentes=(area, "count"))
            .reset_index()
            .rename(columns={muni_col: "Município"})
        )
        tabela = tabela.merge(presentes_muni, on="Município", how="left")
        tabela["Presentes"] = tabela["Presentes"].fillna(tabela["Estudantes"]).astype(int)
        tabela["Inscritos"] = tabela["Estudantes"]
        df_conc_muni = carregar_concluintes_municipio()
        if not df_conc_muni.empty and "NU_ANO" in df_conc_muni.columns:
            if ano_escolhido != "Todos os anos":
                df_conc_muni_ano = df_conc_muni[df_conc_muni["NU_ANO"] == int(ano_escolhido)]
            else:
                df_conc_muni_ano = df_conc_muni[df_conc_muni["NU_ANO"] == df_conc_muni["NU_ANO"].max()]
            if not df_conc_muni_ano.empty:
                tabela["_MUNI_KEY"] = tabela["Município"].apply(_normalizar_nome_municipio)
                df_conc_merge = df_conc_muni_ano[["MUNICIPIO", "Concluintes"]].copy()
                df_conc_merge["_MUNI_KEY"] = df_conc_merge["MUNICIPIO"].apply(_normalizar_nome_municipio)
                tabela = tabela.merge(df_conc_merge[["_MUNI_KEY", "Concluintes"]], on="_MUNI_KEY", how="left")
                tabela["Concluintes"] = tabela["Concluintes"].fillna(0).astype(int)
                tabela = tabela.drop(columns=["_MUNI_KEY"])
            else:
                tabela["Concluintes"] = 0
        else:
            tabela["Concluintes"] = 0
        tabela["Taxa_Efetiva"] = (
            tabela["Presentes"] / tabela["Concluintes"].replace(0, pd.NA) * 100
        ).round(1)

    tabela["Taxa_Part"] = tabela["Taxa_Efetiva"]

    tabela["CRE"] = tabela["CRE"].fillna("—").apply(
        lambda x: nome_cre_curto(x) if x != "—" else "—"
    )

    st.markdown("---")
    # Mostrar todos os municípios com inscritos > 0, ordenados por Tx Part. Efetiva (menor primeiro)
    part_muni = tabela[tabela["Inscritos"] > 0].copy()
    if not part_muni.empty:
        # Recalcular taxas para garantir consistência
        part_muni["Diferença"] = (part_muni["Concluintes"] - part_muni["Presentes"]).clip(lower=0)
        part_muni["Dif_Pct"] = (part_muni["Diferença"] / part_muni["Concluintes"].replace(0, pd.NA) * 100).round(1)
        part_muni["Tx_Inscrição"] = (part_muni["Inscritos"] / part_muni["Concluintes"].replace(0, pd.NA) * 100).round(1)
        part_muni["Tx_Part_Efetiva"] = (part_muni["Presentes"] / part_muni["Concluintes"].replace(0, pd.NA) * 100).round(1)

        # Ordenar: primeiro os com menor taxa de participação efetiva (mais críticos)
        part_muni = part_muni.sort_values("Tx_Part_Efetiva", ascending=True, na_position="last")
        n_municipios = len(part_muni)

        titulo_secao(f"Participação por município ({ano_ref}) — {n_municipios} municípios")

        # Identificar municípios com maior diferença (top 3)
        top_dif = part_muni.nlargest(3, "Diferença")[["Município", "Diferença", "Dif_Pct"]]

        fig_part_muni = go.Figure()
        fig_part_muni.add_trace(go.Bar(
            x=part_muni["Município"], y=part_muni["Concluintes"],
            name="Concluintes", marker_color="#6C757D",
            text=part_muni["Concluintes"],
            textposition="outside",
            textfont=dict(size=9, color=TEMA["texto"]),
            hovertemplate="<b>%{x}</b><br>Concluintes: %{y}<extra></extra>",
        ))
        fig_part_muni.add_trace(go.Bar(
            x=part_muni["Município"], y=part_muni["Inscritos"],
            name="Inscritos", marker_color="#0D6EFD",
            text=part_muni["Inscritos"],
            textposition="outside",
            textfont=dict(size=9, color=TEMA["texto"]),
            hovertemplate="<b>%{x}</b><br>Inscritos: %{y}<extra></extra>",
        ))
        fig_part_muni.add_trace(go.Bar(
            x=part_muni["Município"], y=part_muni["Presentes"],
            name="Presentes 2 dias", marker_color="#198754",
            text=part_muni["Presentes"],
            textposition="outside",
            textfont=dict(size=9, color=TEMA["texto"]),
            hovertemplate="<b>%{x}</b><br>Presentes: %{y}<extra></extra>",
        ))
        # Linha de diferença absoluta (Concluintes - Presentes) no eixo y2
        fig_part_muni.add_trace(go.Scatter(
            x=part_muni["Município"], y=part_muni["Diferença"],
            name="Diferença (estudantes)", mode="lines+markers+text",
            line=dict(color=COR_NEGATIVO, width=3),
            marker=dict(size=10, color=COR_NEGATIVO, symbol="diamond"),
            text=[f"{int(v)}" for v in part_muni["Diferença"]],
            textposition="top center",
            textfont=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Diferença: %{y} estudantes<extra></extra>",
        ))
        # Linha Tx_Inscrição (eixo y3 - porcentagem)
        fig_part_muni.add_trace(go.Scatter(
            x=part_muni["Município"], y=part_muni["Tx_Inscrição"],
            name="Tx Inscrição (%)", mode="lines+markers",
            line=dict(color=LARANJA_DESTAQUE, width=2.5),
            marker=dict(size=8, color=LARANJA_DESTAQUE),
            text=[f"{v:.1f}%" for v in part_muni["Tx_Inscrição"]],
            textposition="top center",
            textfont=dict(size=9, color=LARANJA_DESTAQUE),
            yaxis="y3",
            hovertemplate="<b>%{x}</b><br>Tx Inscrição: %{y:.1f}%<extra></extra>",
        ))
        # Linha Tx_Part_Efetiva (eixo y3 - porcentagem)
        fig_part_muni.add_trace(go.Scatter(
            x=part_muni["Município"], y=part_muni["Tx_Part_Efetiva"],
            name="Tx Part. Efetiva (%)", mode="lines+markers",
            line=dict(color=COR_POSITIVO, width=2.5, dash="dot"),
            marker=dict(size=8, color=COR_POSITIVO),
            text=[f"{v:.1f}%" for v in part_muni["Tx_Part_Efetiva"]],
            textposition="bottom center",
            textfont=dict(size=9, color=COR_POSITIVO),
            yaxis="y3",
            hovertemplate="<b>%{x}</b><br>Tx Part. Efetiva: %{y:.1f}%<extra></extra>",
        ))
        # Anotações para maiores diferenças (apenas Dif_Pct >= 20% para evitar poluição)
        THRESHOLD_DIF_PCT = 20  # só destaca diferenças >= 20% dos concluintes
        top_dif_criticos = part_muni[part_muni["Dif_Pct"] >= THRESHOLD_DIF_PCT].nlargest(5, "Diferença")
        for idx, (_, row) in enumerate(top_dif_criticos.iterrows()):
            fig_part_muni.add_annotation(
                x=row["Município"],
                y=row["Diferença"],
                text=f"⚠️ {int(row['Diferença'])} ({row['Dif_Pct']:.0f}%)",
                showarrow=True,
                arrowhead=2,
                arrowcolor=COR_NEGATIVO,
                ax=0,
                ay=-35 - (idx * 20),  # stagger vertical para evitar sobreposição
                font=dict(size=10, color=COR_NEGATIVO, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor=COR_NEGATIVO,
                borderwidth=1,
                yref="y2",
            )

        # Calcular escalas
        max_dif = part_muni["Diferença"].max()
        y2_max = max_dif * 1.3 if pd.notna(max_dif) else 100

        # Configurar largura do gráfico baseada no número de municípios
        # Largura mínima 1000px, +110px por município para boa legibilidade
        chart_width = max(1000, n_municipios * 110)

        # Definir range inicial: mostrar os ~12 primeiros municípios (menor taxa part. efetiva)
        n_inicial = min(12, n_municipios)
        x_inicial = part_muni["Município"].tolist()
        range_x_inicial = [x_inicial[0], x_inicial[n_inicial - 1]] if n_inicial > 1 else None

        fig_part_muni.update_layout(
            title="",
            xaxis=dict(
                title="",
                tickangle=45,
                tickfont=dict(size=11),
                range=range_x_inicial,
                rangeslider=dict(
                    visible=True,
                    thickness=0.06,
                    bgcolor="rgba(200,200,200,0.3)",
                    bordercolor="rgba(200,200,200,0.5)",
                    borderwidth=1,
                ),
            ),
            yaxis=dict(title="Estudantes", side="left", range=[0, part_muni["Concluintes"].max() * 1.15]),
            yaxis2=dict(title="Diferença (estudantes)", overlaying="y", side="right", position=0.98,
                        showgrid=False, range=[0, y2_max], tickfont=dict(size=9)),
            yaxis3=dict(title="Taxa (%)", overlaying="y", side="right", position=1.0,
                        showgrid=False, range=[0, 105], tickfont=dict(size=9),
                        tickvals=[0, 25, 50, 75, 100]),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor=COR_NEUTRO,
                borderwidth=1,
            ),
            margin=dict(t=60, b=140),
            barmode="group",
            bargap=0.25,
            bargroupgap=0.1,
            dragmode=False,
        )

        # Renderizar com scroll desabilitado, apenas range slider
        st.plotly_chart(
            _finalizar_grafico(
                fig_part_muni,
                altura=CHART_H_PARTICIPACAO,
                n_legend=4,
                margin=dict(t=60, r=80, b=140, l=24),
            ),
            config=dict(
                scrollZoom=False,
                displayModeBar=True,
                modeBarButtonsToAdd=["resetScale2d", "select2d", "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d"],
                modeBarButtonsToRemove=["pan2d", "lasso2d"],
            ),
            width=chart_width,
        )

        # Destacar municípios com maior diferença em cards (apenas críticos >= 20%)
        if not top_dif_criticos.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"**🚨 Municípios com diferença crítica (>= {THRESHOLD_DIF_PCT}% dos concluintes):**")
            cols = st.columns(min(len(top_dif_criticos), 3))
            for i, (_, row) in enumerate(top_dif_criticos.iterrows()):
                with cols[i % 3]:
                    st.markdown(
                        f"""
                        <div style="padding:12px; border-radius:8px; background-color:#FFF3F3; border-left:4px solid {COR_NEGATIVO}; margin-bottom:8px;">
                            <strong>{row['Município']}</strong><br>
                            <span style="color:{COR_NEGATIVO}; font-size:1.3em;">⚠️ {int(row['Diferença'])} estudantes</span> não participaram efetivamente<br>
                            <small>({row['Dif_Pct']:.1f}% dos concluintes)</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ============================================================
    # BOXPLOT POR MUNICÍPIO (similar à aba CREs)
    # ============================================================
    st.markdown("---")
    titulo_secao(f"Distribuição das notas por município — {nome_area_ext(area)} ({ano_ref})")

    # Seletor de municípios (top 15 por média como default)
    muni_medias = tabela.sort_values([AREAS_COMPLETO[area]], ascending=False)
    lista_munis = muni_medias["Município"].tolist()

    col_preset_muni, col_sel_muni = st.columns([1, 3])
    with col_preset_muni:
        preset_muni = st.selectbox(
            "Presets de seleção",
            options=["Top 10", "Top 15", "Top 20", "Todos", "Personalizado"],
            key="muni_preset_box",
        )
    with col_sel_muni:
        if preset_muni == "Top 10":
            default_munis = lista_munis[:10]
        elif preset_muni == "Top 15":
            default_munis = lista_munis[:15]
        elif preset_muni == "Top 20":
            default_munis = lista_munis[:20]
        elif preset_muni == "Todos":
            default_munis = lista_munis
        else:
            default_munis = []

        muni_selecionados = st.multiselect(
            "Selecione os municípios",
            options=lista_munis,
            default=default_munis,
            key="muni_boxplot_sel"
        )

    if muni_selecionados:
        df_muni_filt = df_filt[df_filt[muni_col].isin(muni_selecionados)].copy()
        if not df_muni_filt.empty:
            fig_box_muni = go.Figure()
            # Paleta fixa de cores hex
            cores_muni = [
                "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
                "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
                "#3366CC", "#DC3912", "#FF9900", "#109618", "#990099",
                "#0099C6", "#DD4477", "#66AA00", "#B82E2E", "#316395",
            ]
            for i, muni in enumerate(sorted(muni_selecionados)):
                row = linha_distribuicao(
                    df_dist_muni, ano=int(ano_ref),
                    dependencia=dep_escolhido, municipio=muni,
                ) if ano_ref != "Todos os anos" else None
                if row is None:
                    continue
                stats = stats_box_quantis(row, area)
                if stats is None:
                    continue
                cor = cores_muni[i % len(cores_muni)]
                _add_box_stats(
                    fig_box_muni, stats, name=str(muni), color=cor,
                    x_val=str(muni), rotulo_mediana=True,
                    hover_titulo=str(muni),
                )

            if pd.notna(medias_ref["ms"]):
                _adicionar_referencias_ms_br(
                    fig_box_muni, medias_ref["ms"], medias_ref["br"],
                    sufixo_legenda="rede estadual",
                )
            fig_box_muni.update_layout(
                title=f"Distribuição das notas por município — {nome_area_ext(area)} ({ano_ref})",
                yaxis=dict(range=[0, 1000], title="Nota"),
                xaxis=dict(title="", showticklabels=False),
                showlegend=True,
                legend=_legenda_padrao(y_pos=0.98, font_size=11.5),
                margin=dict(t=60, b=60),
                hovermode="closest",
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(_finalizar_boxplot(fig_box_muni, "Distribuição municipal", altura=CHART_H_BOX, n_legend=2))

    # ============================================================
    # DETALHES POR MUNICÍPIO
    # ============================================================
    st.markdown("---")
    titulo_secao(f"Detalhes por município — {nome_area_ext(area)}")

    # Filtros de seleção
    col_det_muni, col_det_ano, col_det_dep = st.columns(3)
    with col_det_muni:
        muni_detalhe = st.selectbox(
            "Selecione o município",
            options=sorted(tabela["Município"].unique()),
            key="muni_detalhe"
        )
    with col_det_ano:
        anos_muni_disp = sorted(df_dep_muni["NU_ANO"].dropna().unique()) if not df_dep_muni.empty else []
        ano_detalhe = st.selectbox(
            "Selecione o ano",
            options=anos_muni_disp,
            index=len(anos_muni_disp)-1 if anos_muni_disp else 0,
            key="ano_detalhe"
        )
    with col_det_dep:
        dep_detalhe = st.selectbox(
            "Selecione a dependência administrativa",
            options=dep_selecionadas,
            key="dep_detalhe"
        )

    # Filtrar dados para o município selecionado (nível município, sem linhas CRE)
    base_muni_det = df_dep_muni if not df_dep_muni.empty else df_dep
    df_muni_det = base_muni_det[
        (base_muni_det[muni_col] == muni_detalhe) &
        (base_muni_det["NU_ANO"] == ano_detalhe) &
        (base_muni_det["DEP_ADM"] == dep_detalhe)
    ].copy()

    part_muni_det = _participacao_municipio_tabela(
        tabelas, [muni_detalhe], int(ano_detalhe), dep_detalhe, col_municipio=muni_col,
    )
    if not part_muni_det.empty:
        part_muni_det = _enriquecer_participacao_taxas(part_muni_det)
    n_estudantes = (
        int(part_muni_det.iloc[0]["Presentes"])
        if not part_muni_det.empty else len(df_muni_det)
    )
    n_inscritos_muni = (
        int(part_muni_det.iloc[0]["Inscritos"])
        if not part_muni_det.empty and "Inscritos" in part_muni_det.columns else 0
    )
    if dep_detalhe == "Estadual" and not part_muni_det.empty:
        conc_muni_val = int(part_muni_det.iloc[0]["Concluintes"])
        tx_part_efetiva = part_muni_det.iloc[0].get("Tx_Part_Efetiva", part_muni_det.iloc[0].get("Taxa_Efetiva"))
        tx_inscricao_muni = part_muni_det.iloc[0].get("Tx_Inscrição")
        if pd.isna(tx_part_efetiva) and conc_muni_val > 0:
            tx_part_efetiva = round(100 * n_estudantes / conc_muni_val, 1)
        if pd.isna(tx_inscricao_muni) and conc_muni_val > 0 and n_inscritos_muni > 0:
            tx_inscricao_muni = round(100 * n_inscritos_muni / conc_muni_val, 1)
    elif dep_detalhe == "Estadual":
        df_conc_muni = carregar_concluintes_municipio()
        conc_muni_val = 0
        tx_part_efetiva = pd.NA
        if not df_conc_muni.empty:
            conc_row = df_conc_muni[
                (df_conc_muni["MUNICIPIO"].apply(_normalizar_nome_municipio) == _normalizar_nome_municipio(muni_detalhe))
                & (df_conc_muni["NU_ANO"] == ano_detalhe)
            ]
            if not conc_row.empty:
                conc_muni_val = int(conc_row.iloc[0]["Concluintes"])
                if conc_muni_val > 0:
                    tx_part_efetiva = round(100 * n_estudantes / conc_muni_val, 1)
    else:
        conc_muni_val = 0
        tx_part_efetiva = pd.NA
        tx_inscricao_muni = pd.NA

    if not df_muni_det.empty or n_estudantes > 0 or conc_muni_val > 0:
        # ── Calcular Média Geral (média das 5 áreas) ──
        areas_cols = list(AREAS.keys())
        if not df_muni_det.empty:
            df_muni_det["MEDIA_GERAL"] = df_muni_det[areas_cols].mean(axis=1)
            media_geral_muni = df_muni_det["MEDIA_GERAL"].mean()
            mediana_geral_muni = df_muni_det["MEDIA_GERAL"].median()
        else:
            media_geral_muni = np.nan
            mediana_geral_muni = np.nan

        # Cor da borda KPI baseada na taxa de participação
        cor_borda_kpi = COR_POSITIVO if (pd.notna(tx_part_efetiva) and tx_part_efetiva >= 80) else (
            COR_ATENCAO if pd.notna(tx_part_efetiva) and tx_part_efetiva >= 60 else COR_CRITICO
        )

        col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
        media_muni_txt = f"{media_geral_muni:.1f}" if pd.notna(media_geral_muni) else "—"
        mediana_muni_txt = f"{mediana_geral_muni:.1f}" if pd.notna(mediana_geral_muni) else "—"
        with col_kpi1:
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MÉDIA GERAL</div>
                    <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{media_muni_txt}</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi2:
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">MEDIANA DA MÉDIA GERAL</div>
                    <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{mediana_muni_txt}</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi3:
            conc_muni_txt = str(conc_muni_val) if dep_detalhe == "Estadual" else "—"
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {AZUL_PRINCIPAL}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">CONCLUINTES 3º ANO E.M</div>
                    <div style="font-size:28px; font-weight:700; color:{AZUL_PRINCIPAL}; font-family:'Plus Jakarta Sans',sans-serif;">{conc_muni_txt}</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi4:
            tx_insc_str = f"{tx_inscricao_muni:.1f}%".replace(".", ",") if pd.notna(tx_inscricao_muni) else "—"
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {LARANJA_DESTAQUE}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX INSCRIÇÃO</div>
                    <div style="font-size:28px; font-weight:700; color:{LARANJA_DESTAQUE}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_insc_str}</div>
                    <div style="font-size:9px; color:#6c757d; margin-top:4px;">{n_inscritos_muni} inscritos / concluintes</div>
                </div>""", unsafe_allow_html=True)
        with col_kpi5:
            tx_str = f"{tx_part_efetiva:.1f}%".replace(".", ",") if pd.notna(tx_part_efetiva) else "—"
            st.markdown(
                f"""<div style="padding:12px; border-radius:8px; background:#fff; border-left:4px solid {cor_borda_kpi}; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#6c757d; text-transform:uppercase; letter-spacing:0.5px;">TX PART. EFETIVA</div>
                    <div style="font-size:28px; font-weight:700; color:{cor_borda_kpi}; font-family:'Plus Jakarta Sans',sans-serif;">{tx_str}</div>
                    <div style="font-size:9px; color:#6c757d; margin-top:4px; line-height:1.3;">
                        {n_estudantes} presentes nos 2 dias
                        {f"/ {conc_muni_val} concluintes" if dep_detalhe == "Estadual" else ""}<br>
                        (escolas {dep_detalhe.lower()} do município)
                    </div>
                </div>""", unsafe_allow_html=True)

        # ── Boxplot com todas as áreas ──
        st.markdown(f"**Distribuição das notas — {muni_detalhe} — {ano_detalhe}**")

        fig_box_muni_det = go.Figure()
        cores_areas = {
            "CN": "#2E8B57", "CH": "#FF8C00", "LC": "#1E90FF",
            "MT": "#DC143C", "REDACAO": "#DAA520"
        }

        # Calcular médias de referência MS (estado) e BR
        medias_ref_ms = {}
        medias_ref_br = {}
        if df_br is not None:
            df_br_ano = df_br[(df_br["NU_ANO"] == ano_detalhe) & (df_br["DEP_ADM"] == dep_detalhe)]
            df_ms_ano = base_muni_det[
                (base_muni_det["NU_ANO"] == ano_detalhe) & (base_muni_det["DEP_ADM"] == dep_detalhe)
            ]
            for key in AREAS.keys():
                if not df_ms_ano.empty:
                    medias_ref_ms[key] = df_ms_ano[key].mean()
                if not df_br_ano.empty:
                    medias_ref_br[key] = df_br_ano[key].mean()

        usar_ind_muni = (
            df_notas_individuais is not None
            and not df_notas_individuais.empty
            and tem_notas_individuais_ano(df_notas_individuais, int(ano_detalhe))
        )
        df_muni_ind = (
            filtrar_notas_individuais(
                df_notas_individuais,
                ano=int(ano_detalhe),
                municipio=muni_detalhe,
                dependencia=dep_detalhe,
            )
            if usar_ind_muni else pd.DataFrame()
        )
        row_muni_det = linha_distribuicao(
            df_dist_muni,
            ano=int(ano_detalhe),
            dependencia=dep_detalhe,
            municipio=muni_detalhe,
        )

        for i, (key, nome) in enumerate(AREAS_COMPLETO.items()):
            cor = cores_areas.get(key, CORES_AREAS.get(key, AZUL_PRINCIPAL))
            stats = None
            media_muni_area = np.nan

            if usar_ind_muni and not df_muni_ind.empty:
                s_area = notas_area(df_muni_ind, key)
                if s_area.empty:
                    continue
                stats = _stats_box(s_area)
                if stats is None:
                    continue
                media_muni_area = stats["mean"]
                _add_box(
                    fig_box_muni_det, s_area, nome, cor, x_val=nome,
                    rotulo_mediana=True, hover_titulo=nome,
                )
                _add_scatter_notas(
                    fig_box_muni_det, nome, s_area,
                    color=_hex_to_rgba(cor, 0.35),
                )
            elif row_muni_det is not None:
                stats = stats_box_quantis(row_muni_det, key)
                if stats is None:
                    continue
                media_muni_area = stats["mean"]
                _add_box_stats(
                    fig_box_muni_det, stats, name=nome, color=cor,
                    x_val=nome, rotulo_mediana=True, hover_titulo=nome,
                )
            else:
                continue

            # Delta MS (Estado) - à ESQUERDA
            if key in medias_ref_ms and pd.notna(medias_ref_ms[key]) and medias_ref_ms[key] > 0:
                delta_ms = media_muni_area - medias_ref_ms[key]
                sinal_ms = "+" if delta_ms >= 0 else ""
                cor_delta_ms = COR_POSITIVO if delta_ms >= 0 else COR_CRITICO
                fig_box_muni_det.add_annotation(
                    x=nome,
                    y=stats["up"] + 45,
                    text=f"<b>ΔMS {sinal_ms}{delta_ms:.1f}</b>",
                    showarrow=False,
                    xanchor="right",
                    xshift=-25,
                    font=dict(size=9, color=cor_delta_ms, family="Arial Black"),
                    bgcolor="rgba(255,255,255,0.85)",
                    hovertext=(
                        f"Média {muni_detalhe}: {media_muni_area:.1f}<br>"
                        f"Média Estado (MS): {medias_ref_ms[key]:.1f}<br>"
                        f"Diferença: {sinal_ms}{delta_ms:.1f}"
                    ),
                    hoverlabel=dict(bgcolor="white", font_size=10),
                )

            # Delta BR - à DIREITA
            if key in medias_ref_br and pd.notna(medias_ref_br[key]) and medias_ref_br[key] > 0:
                delta_br = media_muni_area - medias_ref_br[key]
                sinal_br = "+" if delta_br >= 0 else ""
                cor_delta_br = COR_POSITIVO if delta_br >= 0 else COR_CRITICO
                fig_box_muni_det.add_annotation(
                    x=nome,
                    y=stats["up"] + 45,
                    text=f"<b>ΔBR {sinal_br}{delta_br:.1f}</b>",
                    showarrow=False,
                    xanchor="left",
                    xshift=25,
                    font=dict(size=9, color=cor_delta_br, family="Arial Black"),
                    bgcolor="rgba(255,255,255,0.85)",
                    hovertext=(
                        f"Média {muni_detalhe}: {media_muni_area:.1f}<br>"
                        f"Média Brasil: {medias_ref_br[key]:.1f}<br>"
                        f"Diferença: {sinal_br}{delta_br:.1f}"
                    ),
                    hoverlabel=dict(bgcolor="white", font_size=10),
                )

        # Linhas de referência MS e BR para legenda
        fig_box_muni_det.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            line=dict(color=LARANJA_DESTAQUE, width=2, dash="dash"),
            name="Média MS — rede estadual",
            hoverinfo="skip",
        ))
        fig_box_muni_det.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            line=dict(color=TEMA["texto_secundario"], width=2, dash="dash"),
            name="Média BR — rede estadual",
            hoverinfo="skip",
        ))

        fig_box_muni_det.update_layout(
            title=dict(text=""),
            yaxis=dict(range=[0, 1000], title="Nota"),
            xaxis=dict(title="", showticklabels=False),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=10, color=TEMA["texto"]),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor=COR_NEUTRO,
                borderwidth=1,
                itemsizing="constant",
            ),
            margin=dict(t=60, b=140),
            plot_bgcolor="rgba(250,252,255,1)",
            paper_bgcolor="#FFFFFF",
        )
        _chart(_finalizar_boxplot(fig_box_muni_det, f"Detalhe — {muni_detalhe}", altura=CHART_H_BOX, n_legend=1))

        if usar_ind_muni and not df_muni_ind.empty:
            s_hist_muni = notas_area(df_muni_ind, area)
            if not s_hist_muni.empty:
                titulo_secao(
                    f"Histograma — {nome_area_ext(area)}",
                    f"Distribuição individual dos estudantes do município ({len(s_hist_muni):,} com nota válida)."
                )
                _chart(_fig_histogram_notas(
                    s_hist_muni,
                    f"Distribuição — {muni_detalhe} ({nome_area_ext(area)}, 2024)",
                    cor=CORES_AREAS.get(area, AZUL_PRINCIPAL),
                    media_ref=medias_ref_ms.get(area),
                ))

        # ── Legendas explicativas ──
        st.markdown(
            """<div style="display: flex; gap: 20px; margin: 8px 0 12px; font-size: 12px; flex-wrap: wrap;">
                <div><span style="color: #198754; font-weight: bold;">ΔMS</span> = diferença vs média do Estado</div>
                <div><span style="color: #198754; font-weight: bold;">ΔBR</span> = diferença vs média do Brasil</div>
                <div><span style="color: #198754;">■</span> acima da média <span style="color: #DC2626;">■</span> abaixo da média</div>
            </div>""", unsafe_allow_html=True
        )

        # ── Legenda de cores das áreas ──
        cores_legenda = " ".join([
            f"<span style='color: {cores_areas.get(k, CORES_AREAS.get(k, AZUL_PRINCIPAL))}; font-weight: bold;'>●</span> {nome_area_ext(k)}"
            for k in AREAS.keys()
        ])
        st.markdown(
            f"""<div style="display: flex; gap: 16px; margin: 4px 0 16px; font-size: 11px; flex-wrap: wrap; color: #6c757d;">
                {cores_legenda}
            </div>""", unsafe_allow_html=True
        )
        if ano_detalhe == 2024 and ("NOME_ESCOLA" in df_muni_det.columns or "NO_ENTIDADE" in df_muni_det.columns):
            st.markdown(f"**Escolas em {muni_detalhe} ({ano_detalhe}) — {dep_detalhe}**")
            st.markdown(
                "<div style='font-size:12px; color:#6B7280; margin-bottom:8px;'>"
                "🟢↑ Acima da média &nbsp;|&nbsp; 🔴↓ Abaixo da média &nbsp;|&nbsp; "
                "MS=Média MS estadual &nbsp;|&nbsp; BR=Média BR estadual"
                "</div>",
                unsafe_allow_html=True
            )
            col_escola = "NOME_ESCOLA" if "NOME_ESCOLA" in df_muni_det.columns else "NO_ENTIDADE"

            # Agregar por escola com todas as áreas
            escolas_agg = df_muni_det.groupby(col_escola).agg(
                Estudantes=(area, "count"),
                **{AREAS_COMPLETO[k]: (k, "mean") for k in COLS_NOTAS},
            ).reset_index()

            # Calcular Média Geral
            areas_cols_agg = [AREAS_COMPLETO[k] for k in COLS_NOTAS]
            escolas_agg["Média Geral"] = escolas_agg[areas_cols_agg].mean(axis=1)

            # Buscar concluintes por escola
            df_conc_esc = carregar_concluintes()
            if not df_conc_esc.empty and "CO_ESCOLA" in df_muni_det.columns:
                # Mapear escolas por código
                escolas_conc = df_muni_det[[col_escola, "CO_ESCOLA"]].drop_duplicates()
                conc_por_escola = df_conc_esc[
                    (df_conc_esc["NU_ANO"] == 2024) &
                    (df_conc_esc["CO_ESCOLA"].isin(escolas_conc["CO_ESCOLA"]))
                ][["CO_ESCOLA", "Concluintes"]].set_index("CO_ESCOLA")["Concluintes"].to_dict()

                escolas_agg["Concluintes"] = escolas_agg[col_escola].map(
                    escolas_conc.set_index(col_escola)["CO_ESCOLA"].map(conc_por_escola)
                ).fillna(0).astype(int)
            else:
                escolas_agg["Concluintes"] = 0

            # Calcular taxa de participação efetiva
            escolas_agg["Tx_Part_Efetiva"] = (
                escolas_agg["Estudantes"] / escolas_agg["Concluintes"].replace(0, pd.NA) * 100
            )

            # Arredondar médias
            for k in COLS_NOTAS:
                escolas_agg[AREAS_COMPLETO[k]] = escolas_agg[AREAS_COMPLETO[k]].apply(lambda x: round(x, 1) if pd.notna(x) else pd.NA)

            # Renomear colunas para exibição
            rename_map = {col_escola: "Escola", "Estudantes": "Participantes"}
            escolas_display = escolas_agg.rename(columns=rename_map)

            # Reordenar colunas: Escola → Concluintes → Participantes → Tx Part. Efetiva → [áreas] → Média Geral
            colunas_ordem = ["Escola", "Concluintes", "Participantes", "Tx_Part_Efetiva"]
            for k in COLS_NOTAS:
                colunas_ordem.append(AREAS_COMPLETO[k])
            colunas_ordem.append("Média Geral")

            # Garantir que todas as colunas existam
            colunas_final = [c for c in colunas_ordem if c in escolas_display.columns]
            escolas_display = escolas_display[colunas_final]

            # Ordenar por média da área principal
            escolas_display = escolas_display.sort_values(AREAS_COMPLETO[area], ascending=False)

            # Criar cópia para estilização
            escolas_styled = escolas_display.copy()

            # Formatar para exibição
            for col in escolas_styled.columns:
                if col == "Concluintes":
                    escolas_styled[col] = escolas_styled[col].apply(lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—")
                elif col == "Tx_Part_Efetiva":
                    escolas_styled[col] = escolas_styled[col].apply(lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—")
                elif col in [AREAS_COMPLETO[k] for k in AREAS.keys()]:
                    escolas_styled[col] = escolas_styled[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—")

            # ============================================================
            # ESTILIZAÇÃO VIA FUNÇÃO UTILITÁRIA
            # ============================================================
            area_labels_muni = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
            if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in escolas_display.columns:
                area_labels_muni["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]
            
            styled_muni, css_cabecalho_muni = _estilizar_tabela(
                df_display=escolas_styled,
                df_raw=escolas_display,
                colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in escolas_styled.columns],
                cores_area=CORES_AREAS,
                medias_ms=medias_ref_ms,
                medias_br=medias_ref_br,
                area_labels=area_labels_muni,
            )
            
            # CSS customizado para cabeçalhos coloridos
            if css_cabecalho_muni:
                st.markdown(f"""
                <style>
                {css_cabecalho_muni}
                </style>
                """, unsafe_allow_html=True)
            
            n_escolas = len(escolas_styled)
            altura_escolas = min(max(n_escolas * 35 + 45, 100), 520)
            st.dataframe(styled_muni, width="stretch", hide_index=True, height=altura_escolas)

    else:
        st.info(f"Sem dados para {muni_detalhe} em {ano_detalhe} — {dep_detalhe}.")

    st.markdown("---")
    titulo_secao("Tabela completa — municípios")
    st.markdown(
        "<div style='font-size:12px; color:#6B7280; margin-bottom:8px;'>"
        "🟢↑ Acima da média &nbsp;|&nbsp; 🔴↓ Abaixo da média &nbsp;|&nbsp; "
        "MS=Média MS estadual &nbsp;|&nbsp; BR=Média BR estadual"
        "</div>",
        unsafe_allow_html=True
    )

    # Selecionar colunas para exibição: Município, CRE, Concluintes, Taxa_Efetiva, e todas as áreas
    cols_display = ["Município", "CRE", "Concluintes", "Taxa_Efetiva"]
    for k in COLS_NOTAS:
        col_nome = AREAS_COMPLETO[k]
        if col_nome in tabela.columns:
            cols_display.append(col_nome)
    tabela_raw = tabela[cols_display].copy()
    tabela_display = tabela_raw.copy()
    # Formatar Taxa_Efetiva como string com %
    tabela_display["Taxa_Efetiva"] = tabela_raw["Taxa_Efetiva"].apply(lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—")

    # Formatar colunas numéricas (áreas) com vírgula decimal
    for k in COLS_NOTAS:
        col_name = AREAS_COMPLETO[k]
        if col_name in tabela_display.columns:
            tabela_display[col_name] = tabela_raw[col_name].apply(
                lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—"
        )
    # Calcular médias de referência MS e BR para TODAS as áreas
    medias_ref_ms_muni = {}
    medias_ref_br_muni = {}

    ano_ref_muni = int(ano_escolhido) if ano_escolhido != "Todos os anos" else None

    for k in COLS_NOTAS:
        # MS: média do estado (df_dep já filtrado por dependência)
        medias_ref_ms_muni[k] = float(df_dep_muni[k].dropna().mean()) if not df_dep_muni.empty else (
            float(df_dep[k].dropna().mean()) if not df_dep.empty else np.nan
        )
    
        # BR: média do Brasil (mesmo ano e dependência)
        if df_br is not None and ano_ref_muni is not None:
            df_br_ref = df_br[(df_br["NU_ANO"] == ano_ref_muni) & (df_br["DEP_ADM"] == dep_escolhido)]
            medias_ref_br_muni[k] = float(df_br_ref[k].dropna().mean()) if not df_br_ref.empty else np.nan
        else:
            medias_ref_br_muni[k] = np.nan



    # --- 3. Preparar area_labels ---
    area_labels_muni = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
    if AREAS_COMPLETO.get("MEDIA_GERAL") and AREAS_COMPLETO["MEDIA_GERAL"] in tabela.columns:
        area_labels_muni["MEDIA_GERAL"] = AREAS_COMPLETO["MEDIA_GERAL"]

    # --- 4. Chamar _estilizar_tabela ---
    styled_muni_total, css_cabecalho_muni_total = _estilizar_tabela(
        df_display=tabela_display,
        df_raw=tabela[cols_display],  # versão numérica bruta
        colunas_area=[AREAS_COMPLETO[k] for k in AREAS.keys() if AREAS_COMPLETO[k] in tabela.columns],
        cores_area=CORES_AREAS,
        medias_ms=medias_ref_ms_muni,
        medias_br=medias_ref_br_muni,
        col_escola="Município",
        tx_col="Taxa_Efetiva",
        concluintes_col="Concluintes",
        area_labels=area_labels_muni,
    )

    # --- 5. Renderizar ---
    if css_cabecalho_muni_total:
        st.markdown(f"<style>{css_cabecalho_muni_total}</style>", unsafe_allow_html=True)
    
    n_muni_total = len(tabela_display)
    altura_muni_total = min(max(n_muni_total * 35 + 45, 100), 520)
    st.dataframe(styled_muni_total, width="stretch", hide_index=True, height=altura_muni_total)


# ============================================================
# ABA 8 - CONTEXTO NACIONAL (COM SELETOR DE ANO E ÁREA)
# ============================================================
# ============================================================
# ABA 8 - CONTEXTO NACIONAL
# ============================================================
def aba_contexto_nacional(tabelas, anos_sel):
    titulo_secao(
        "Panorama nacional",
        "Posicionamento entre as unidades federativas. Selecione o ano e a área desejados."
    )
    tabelas = tabelas or {}
    anos_validos = anos_com_desempenho_uf(tabelas, anos_sel)
    if not anos_validos:
        st.warning("Nenhum ano disponível para o panorama nacional.")
        return

    st.markdown("### Filtros de análise")
    col_filt_ano, col_filt_area, col_filt_dep = st.columns(3)
    with col_filt_ano:
        ano_nac = st.selectbox(
            "Selecione o ano",
            options=anos_validos,
            index=len(anos_validos) - 1,
            key="ano_nac",
        )
    with col_filt_area:
        area = st.selectbox(
            "Selecione a área de conhecimento",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_nac",
        )
    with col_filt_dep:
        dep = st.selectbox(
            "Selecione a dependência administrativa",
            options=["Todas", "Estadual", "Federal", "Municipal", "Privada"],
            index=1,
            key="dep_nac",
        )

    dep_filtro = None if dep == "Todas" else dep
    g_base = tabela_ranking_uf(tabelas, int(ano_nac), dep_filtro)

    if g_base.empty or area not in g_base.columns:
        st.warning("Sem dados para o recorte selecionado.")
        return

    g_chart = g_base[["UF", area]].dropna().copy()
    g_chart[area] = g_chart[area].round(2)
    g_chart = g_chart.sort_values(area, ascending=False).reset_index(drop=True)
    g_chart["Posição"] = g_chart.index + 1

    media_br = media_nacional_ponderada(tabelas, int(ano_nac), area, "Estadual")
    row_ms = g_base[g_base["UF"] == "MS"]
    media_ms = float(row_ms[area].iloc[0]) if not row_ms.empty else media_br

    def _cor_barra(row):
        if row["UF"] == "MS":
            return LARANJA_DESTAQUE
        val = row[area]
        if val >= media_br:
            return COR_POSITIVO
        elif val >= media_ms:
            return AZUL_PRINCIPAL
        return COR_CRITICO

    g_chart["Cor"] = g_chart.apply(_cor_barra, axis=1)

    # Destaque visual para MS (borda mais grossa)
    marker_line_colors = ["black" if uf == "MS" else "rgba(0,0,0,0)" for uf in g_chart["UF"]]
    marker_line_widths = [3 if uf == "MS" else 0 for uf in g_chart["UF"]]

    fig = go.Figure(go.Bar(
        x=g_chart["UF"],
        y=g_chart[area],
        marker_color=g_chart["Cor"],
        marker_line_color=marker_line_colors,
        marker_line_width=marker_line_widths,
        text=[f"<b>{row['Posição']}º</b><br>{row[area]:.2f}".replace(".", ",") for _, row in g_chart.iterrows()],
        textposition="outside",
        textfont=dict(size=12, color="#333333"),
        hovertemplate="<b>%{x}</b><br>Posição: %{customdata}º<br>Média: %{y:.2f}<extra></extra>",
        customdata=g_chart["Posição"],
    ))

    fig.add_hline(
        y=media_br, line_dash="dash", line_color=TEMA["texto_secundario"], line_width=2,
        annotation_text=f"Média BR: {media_br:.2f}".replace(".", ","),
        annotation_position="top right",
        annotation_font=dict(size=10, color=TEMA["texto_secundario"]),
    )
    if abs(media_ms - media_br) > 0.5:
        fig.add_hline(
            y=media_ms, line_dash="dot", line_color=LARANJA_DESTAQUE, line_width=2,
            annotation_text=f"Média MS: {media_ms:.2f}".replace(".", ","),
            annotation_position="bottom right",
            annotation_font=dict(size=10, color=LARANJA_DESTAQUE),
        )

    fig.update_layout(
        title=dict(
            text=f"Média por UF — {nome_area_ext(area)} ({dep}) — {ano_nac}",
            font=dict(size=16),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(title="UF", categoryorder="array", categoryarray=g_chart["UF"].tolist(), tickfont=dict(size=11)),
        yaxis=dict(title="Nota média", range=[0, max(g_chart[area].max() * 1.25, media_br * 1.25, 100)], tickfont=dict(size=11)),
        margin=dict(t=100, b=60, l=60, r=40),
        plot_bgcolor="rgba(250,252,255,1)",
        paper_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
    )

    # Legenda em HTML acima do gráfico para melhor legibilidade
    st.markdown(
        f"""
        <div style='font-size: 13px; margin-bottom: 8px; display: flex; gap: 20px; flex-wrap: wrap; align-items: center;'>
            <span><b>Legenda de cores:</b></span>
            <span><span style='color:{COR_POSITIVO}; font-size: 16px;'>■</span> Acima da média nacional (BR)</span>
            <span><span style='color:{AZUL_PRINCIPAL}; font-size: 16px;'>■</span> Acima da média de MS e abaixo de BR</span>
            <span><span style='color:{COR_CRITICO}; font-size: 16px;'>■</span> Abaixo da média de MS</span>
            <span><span style='color:{LARANJA_DESTAQUE}; font-size: 16px;'>■</span> <b>Mato Grosso do Sul</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _chart(aplicar_tema(fig, CHART_H_HIST_GRID))

    # ============================================================
    # TABELA COMPLETA
    # ============================================================
    st.markdown("---")
    titulo_secao(f"Ranking completo por UF — {ano_nac}")

    g_todos = g_base.copy()
    areas_cols_names = [AREAS_COMPLETO[k] for k in COLS_NOTAS if k in g_todos.columns]
    for k in COLS_NOTAS:
        col_nome = AREAS_COMPLETO[k]
        if col_nome not in g_todos.columns and k in g_todos.columns:
            g_todos[col_nome] = g_todos[k].round(2)
        elif col_nome in g_todos.columns:
            g_todos[col_nome] = g_todos[col_nome].round(2)
    if "Média Geral" not in g_todos.columns and "MEDIA_GERAL" in g_todos.columns:
        g_todos["Média Geral"] = g_todos["MEDIA_GERAL"].round(2)

    col_rank = AREAS_COMPLETO.get(area, area)
    if col_rank not in g_todos.columns and area in g_todos.columns:
        col_rank = area
    g_todos = g_todos.sort_values(col_rank, ascending=False).reset_index(drop=True)
    g_todos.insert(0, "Posição", g_todos.index + 1)

    cols_finais = ["Posição", "UF"] + areas_cols_names + ["Média Geral", "Inscritos", "Tx_Participação"]
    g_todos = g_todos[[c for c in cols_finais if c in g_todos.columns]]
    g_todos = g_todos.loc[:, ~g_todos.columns.duplicated()]

    tabela_display = g_todos.copy()
    for col in list(tabela_display.columns):
        if col in areas_cols_names or col == "Média Geral":
            tabela_display[col] = pd.to_numeric(tabela_display[col], errors="coerce").apply(
                lambda x: f"{x:.2f}".replace(".", ",") if pd.notna(x) else "—"
            )
        elif col == "Tx_Participação":
            tabela_display[col] = pd.to_numeric(tabela_display[col], errors="coerce").apply(
                lambda x: f"{x:.2f}%".replace(".", ",") if pd.notna(x) else "—"
            )
        elif col in ("Inscritos", "Presentes_Est"):
            tabela_display[col] = pd.to_numeric(tabela_display[col], errors="coerce").apply(
                lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"
            )

    medias_ref_ms_nac = {}
    medias_ref_br_nac = {}
    for k in COLS_NOTAS:
        medias_ref_br_nac[k] = media_nacional_ponderada(tabelas, int(ano_nac), k, "Estadual")
        ms_row = g_base[g_base["UF"] == "MS"]
        medias_ref_ms_nac[k] = (
            float(ms_row[k].iloc[0]) if not ms_row.empty and k in ms_row.columns
            else medias_ref_br_nac[k]
        )
    medias_ref_br_nac["MEDIA_GERAL"] = media_nacional_ponderada(
        tabelas, int(ano_nac), "MEDIA_GERAL", "Estadual",
    )
    ms_mg = g_base[g_base["UF"] == "MS"]
    medias_ref_ms_nac["MEDIA_GERAL"] = (
        float(ms_mg["MEDIA_GERAL"].iloc[0]) if not ms_mg.empty and "MEDIA_GERAL" in ms_mg.columns
        else medias_ref_br_nac["MEDIA_GERAL"]
    )

    area_labels_nac = {col: AREAS_COMPLETO[col] for col in COLS_NOTAS}
    area_labels_nac["MEDIA_GERAL"] = "Média Geral"

    styled_nac, css_cabecalho_nac = _estilizar_tabela(
        df_display=tabela_display,
        df_raw=g_todos,
        colunas_area=areas_cols_names + ["Média Geral"],
        cores_area={**CORES_AREAS, "MEDIA_GERAL": "#7B8794"},
        medias_ms=medias_ref_ms_nac,
        medias_br=medias_ref_br_nac,
        col_escola="UF",
        tx_col="Tx_Participação",
        concluintes_col="Inscritos",
        area_labels=area_labels_nac,
        tx_threshold_vermelho=70.0,
        tx_threshold_laranja=70.0,
        tx_threshold_verde=80.0,
        colorir_linha_tx=True,
    )

    if css_cabecalho_nac:
        st.markdown(f"<style>{css_cabecalho_nac}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size: 11px; color: #6B7280; margin-bottom: 10px;'>
        <b>Legenda Taxa Part. Efetiva:</b> 
        <span style='color: #059669;'>■</span> ≥80% 
        <span style='color: #D97706;'>■</span> 70-79% 
        <span style='color: #DC2626;'>■</span> &lt;70% | 
        <b>Fonte das médias:</b> 
        <span style='color: #0F8A5F;'>verde</span> = acima BR, 
        <span style='color: #003F7F;'>azul</span> = acima MS e abaixo de BR, 
        <span style='color: #C03A2B;'>vermelho</span> = abaixo de ambos
    </div>
    """, unsafe_allow_html=True)

    n_ufs = len(tabela_display)
    altura_ufs = min(max(n_ufs * 35 + 45, 100), 520)
    st.dataframe(styled_nac, width="stretch", hide_index=True, height=altura_ufs)


# ============================================================
# HUB DE GESTÃO — Modelo B (camadas) + Território Modelo C
# ============================================================

_NIVEL_TERRITORIO_ESTADO = "Estado (visão CREs)"
_NIVEL_TERRITORIO_CRE = "CRE"
_NIVEL_TERRITORIO_MUN = "Município"
_NIVEL_TERRITORIO_ESC = "Escola (2024)"
_NIVEIS_TERRITORIO = (
    _NIVEL_TERRITORIO_ESTADO,
    _NIVEL_TERRITORIO_CRE,
    _NIVEL_TERRITORIO_MUN,
    _NIVEL_TERRITORIO_ESC,
)

_SUBABA_PANORAMA = "Participação"
_SUBABA_DESEMPENHO = "Desempenho"
_SUBABA_TERRITORIO = "Território"
_SUBABA_NACIONAL = "Nacional"
_SUBABA_HUB = "__hub__"
_SUBABAS_GESTAO = (
    _SUBABA_PANORAMA,
    _SUBABA_DESEMPENHO,
    _SUBABA_TERRITORIO,
    _SUBABA_NACIONAL,
)


def _vista_territorio_estado(tabelas: dict, anos_sel: list) -> None:
    """Nível Estado: ranking de CREs no ano mais recente do recorte."""
    titulo_secao(
        "Visão estadual — CREs",
        "Ranking das Coordenadorias Regionais de Educação (rede estadual). "
        "Selecione CRE, Município ou Escola no seletor acima para detalhar.",
    )
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        st.info(
            "Dados de evolução por CRE indisponíveis. "
            "Regenere agregados com: `python gerar_dados_agregados.py`."
        )
        return
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        st.info("Nenhum ano do recorte possui dados por CRE.")
        return
    ano_ref = anos_validos[-1]
    sub = df_evol[
        (df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == "Estadual")
    ].copy()
    if sub.empty:
        st.info(f"Sem dados de CRE estadual para {ano_ref}.")
        return
    col_media = "media_geral" if "media_geral" in sub.columns else None
    if col_media is None:
        st.info("Coluna de média geral não encontrada em evolucao_cre.")
        return
    sub = sub.dropna(subset=[col_media]).sort_values(col_media, ascending=False)
    exibir = sub[["CRE", col_media, "estudantes"]].copy()
    exibir.columns = ["CRE", "Média geral", "Estudantes"]
    exibir["CRE"] = exibir["CRE"].map(nome_cre_curto)
    exibir["Média geral"] = exibir["Média geral"].round(1)
    st.caption(f"Ano de referência: **{ano_ref}** · Rede estadual · ordenado por média geral.")
    st.dataframe(exibir.reset_index(drop=True), width="stretch", hide_index=True)
    if len(sub) >= 2:
        st.markdown(
            f"<div class='insight'><strong>Extremos:</strong> maior média — "
            f"<b>{nome_cre_curto(sub.iloc[0]['CRE'])}</b> ({fmt_float(sub.iloc[0][col_media])}); "
            f"menor — <b>{nome_cre_curto(sub.iloc[-1]['CRE'])}</b> ({fmt_float(sub.iloc[-1][col_media])}).</div>",
            unsafe_allow_html=True,
        )


def aba_territorio_drilldown(
    df_ms_enriq,
    df_ms_enriq_todos,
    df_br_nacional_estadual,
    dep_selecionadas,
    df_bruta_ms_enriq,
    df_ms_enriq_2024,
    df_concluintes,
    tabelas,
    df_notas_individuais,
    anos_sel,
):
    """Drill-down territorial: Estado → CRE → Município → Escola (2024)."""
    nivel = st.radio(
        "Nível de detalhe",
        _NIVEIS_TERRITORIO,
        horizontal=True,
        key="hub_nivel_territorio",
        label_visibility="collapsed",
    )
    st.caption(
        "**Estado** — ranking de CREs · **CRE** — evolução e distribuição por coordenadoria · "
        "**Município** — detalhe por cidade · **Escola** — unidades em 2024."
    )

    if nivel == _NIVEL_TERRITORIO_ESTADO:
        _vista_territorio_estado(tabelas, anos_sel)
    elif nivel == _NIVEL_TERRITORIO_CRE:
        aba_territorial(
            df_ms_enriq, df_ms_enriq_todos, df_br_nacional_estadual, dep_selecionadas,
            df_bruta_ms_enriq=df_bruta_ms_enriq, tabelas=tabelas,
            df_notas_individuais=df_notas_individuais, anos_sel=anos_sel,
        )
    elif nivel == _NIVEL_TERRITORIO_MUN:
        aba_municipios(
            df_ms_enriq, df_ms_enriq_todos, df_br_nacional_estadual, dep_selecionadas,
            df_bruta_ms_enriq=df_bruta_ms_enriq, tabelas=tabelas,
            df_notas_individuais=df_notas_individuais, anos_sel=anos_sel,
        )
    else:
        if df_ms_enriq_2024.empty:
            st.info(
                "Detalhamento por escola requer dados de 2024 no recorte lateral. "
                "Inclua 2024 nos anos selecionados e regenere agregados/notas individuais."
            )
        else:
            aba_escolas_2024(
                df_ms_enriq_2024, 2024, df_br_nacional_estadual,
                df_bruta_ms=df_bruta_ms_enriq, df_concluintes=df_concluintes,
                tabelas=tabelas, df_notas_individuais=df_notas_individuais,
            )


def _render_metodologia_detalhe() -> None:
    """Conteúdo técnico completo (expander no rodapé)."""
    st.markdown(
        f"""
        <div class="insight">
        <strong>Público-alvo:</strong> Secretário de Educação (panorama e evolução comparativa),
        Coordenadoria do Ensino Médio e assessoramento pedagógico (diagnóstico e priorização),
        equipe técnica SED (detalhamento e auditoria de dados).
        </div>
        """,
        unsafe_allow_html=True,
    )
    titulo_secao("População de referência")
    st.markdown(
        """
        - **Concluintes do Ensino Médio** na rede estadual de MS (planilha SED / `participacao_ano`).
        - **Presentes nos 2 dias** de prova e **não eliminados** em qualquer área ou redação (`presentes_filt`).
        - **2019–2023:** concluintes EM (`TP_ST_CONCLUSAO == 2`).
        - **2024:** todos os inscritos estaduais (microdado sem distinção de concluinte).
        - **Taxa de participação efetiva:** presentes filtrados ÷ concluintes × 100 — indicador central do painel.
        """
    )
    titulo_secao("Período analítico")
    st.markdown(
        """
        - **Recorte temporal:** 2019–2024 (evolução comparativa da rede estadual no ENEM).
        - **Marco institucional:** a gestão do secretário atual teve início em **2023**; o painel não atribui
          causalmente resultados a gestões específicas, mas permite comparar períodos antes e depois desse ano.
        - **Desempenho:** calculado apenas sobre **participantes efetivos** (não sobre o total de concluintes).
        """
    )
    titulo_secao("Fontes de dados")
    st.markdown(
        """
        | Camada | Fonte | Uso |
        |--------|-------|-----|
        | Agregados | `gerar_dados_agregados.py` → parquets em `data/agregados/` | KPIs, evolução, participação, quantis |
        | Notas individuais | `gerar_notas_individuais.py` → `notas_individuais_ms.parquet` | Boxplot, histograma, desvio por CRE/município/escola |
        | Microdado bruto | `enem_completo_2019_2024_.parquet` (offline) | Geração dos agregados; não carregado no painel em produção |
        | Cadastro | `cres.xlsx` | CRE, município, nome de escola |
        """
    )
    titulo_secao("Estrutura do painel (Modelo B)")
    st.markdown(
        """
        1. **Camada Status** — KPIs e principais achados (aba Gestão, topo).
        2. **Camada Contexto** — sub-abas Participação, Desempenho, Território, Nacional.
        3. **Camada Detalhe** — expanders, tabelas completas, histogramas e boxplots finos.

        **Território (Modelo C):** drill-down Estado → CRE → Município → Escola (2024).
        """
    )
    titulo_secao("Performance e atualização")
    st.markdown(
        f"""
        - Dados locais: `PASTA_AGREGADOS` (padrão `data/agregados/`).
        - Após regerar parquets: **Clear cache → Rerun** no Streamlit (cache TTL 1h).
        - Modo Supabase: variável `DATA_SOURCE=supabase` e credenciais configuradas.
        - Versão do painel: **v15 · dados agregados** · fonte: **{get_data_source().upper()}**.
        """
    )


def aba_metodologia():
    """Referência técnica: população, fontes, camadas e limitações."""
    titulo_secao(
        "Metodologia e fontes",
        "Definições analíticas, população de referência e estrutura do painel.",
    )
    _render_metodologia_detalhe()


@st.fragment
def _fragment_camada_status(
    diag: dict,
    anos_sel: list,
    tabelas: dict,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
) -> None:
    """Camada 1 — não reroda ao trocar sub-aba (fragment isolado)."""
    aba_sumario_executivo(
        diag, anos_sel, modo_hub=True,
        tabelas=tabelas,
        df_bruta_ms=df_bruta_ms,
        df_filt_ms=df_filt_ms,
    )


@st.fragment
def _fragment_camada_detalhe(
    anos_sel: list,
    dep_selecionadas: list,
) -> None:
    """Camada 2 — só esta seção reroda ao trocar eixo de análise."""
    _render_html(
        '<div class="widget-head" style="border-radius:8px 8px 0 0;margin-top:4px">'
        'Análises detalhadas</div>'
    )
    st.caption("Selecione o eixo de análise. Apenas a seção ativa é carregada.")
    sub_aba = st.radio(
        "Eixo de análise",
        _SUBABAS_GESTAO,
        horizontal=True,
        key="hub_sub_aba",
        label_visibility="collapsed",
    )
    ctx = build_dashboard_context(
        tuple(int(a) for a in anos_sel),
        tuple(dep_selecionadas),
        sub_aba,
    )
    if sub_aba in (_SUBABA_DESEMPENHO, _SUBABA_TERRITORIO):
        anos_ind = anos_com_notas_individuais(ctx["df_notas_individuais"])
        if not anos_ind and sub_aba == _SUBABA_DESEMPENHO:
            st.info(
                "ℹ️ Notas individuais não encontradas — histogramas usam quantis agregados."
            )
        elif anos_ind and set(anos_ind) != set(ANOS_DISPONIVEIS):
            faltam = sorted(set(ANOS_DISPONIVEIS) - set(anos_ind))
            st.info(
                f"ℹ️ Notas individuais: {', '.join(str(a) for a in anos_ind)}. "
                f"Anos {', '.join(str(a) for a in faltam)} usam quantis agregados."
            )
    if ctx["df_concluintes"].empty and sub_aba == _SUBABA_PANORAMA:
        st.info(
            "ℹ️ Dados de concluintes do 3º ano não disponíveis. "
            "Taxa de participação efetiva pode aparecer como '—'."
        )
    tabelas = ctx["tabelas"]
    if sub_aba == _SUBABA_PANORAMA:
        aba_panorama_participacao(
            ctx["df_bruta_ms"], ctx["df_filt_ms"], anos_sel,
            df_concluintes=ctx["df_concluintes"],
            tabelas=tabelas,
        )
    elif sub_aba == _SUBABA_DESEMPENHO:
        aba_desempenho(
            ctx["df_filt_ms"],
            tabelas=tabelas,
            df_notas_individuais=ctx["df_notas_individuais"],
            anos_sel=anos_sel,
        )
    elif sub_aba == _SUBABA_TERRITORIO:
        aba_territorio_drilldown(
            ctx["df_ms_enriq"], ctx["df_ms_enriq_todos"], None, dep_selecionadas,
            ctx["df_bruta_ms_enriq"], ctx["df_ms_enriq_2024"], ctx["df_concluintes"],
            tabelas, ctx["df_notas_individuais"], anos_sel,
        )
    else:
        aba_contexto_nacional(tabelas, anos_sel)


def aba_gestao_hub(
    diag,
    anos_sel,
    dep_selecionadas,
    tabelas: dict,
    df_bruta_ms: pd.DataFrame,
    df_filt_ms: pd.DataFrame,
):
    """Hub único de gestão: capa em 3 colunas (participação · desempenho · território)."""
    aba_sumario_executivo(
        diag, anos_sel, modo_hub=True,
        tabelas=tabelas,
        df_bruta_ms=df_bruta_ms,
        df_filt_ms=df_filt_ms,
    )


@st.cache_data(show_spinner="Preparando contexto do painel…", ttl=3600)
def build_dashboard_context(
    anos_sel: tuple[int, ...],
    dep_selecionadas: tuple[str, ...],
    sub_aba: str,
) -> dict:
    """Contexto cacheado: tabelas + dados MS + cargas condicionais por sub-aba."""
    tabelas = carregar_todas_tabelas()
    anos_list = list(anos_sel)
    deps = list(dep_selecionadas)

    df_bruta_ms, df_filt_ms = reconstruir_participacao_ms(tabelas, anos_list, deps)
    diag = diagnostico_estadual(
        df_filt_ms, df_bruta_ms, tabelas=tabelas, anos_sel=anos_list,
    )
    diag = _enriquecer_diag_participacao(diag, tabelas, anos_list)
    n_insc = inscritos_estadual_ms(tabelas, anos_list)
    if n_insc:
        diag["n_inscritos"] = n_insc

    ctx: dict = {
        "tabelas": tabelas,
        "diag": diag,
        "df_bruta_ms": df_bruta_ms,
        "df_filt_ms": df_filt_ms,
        "df_bruta_ms_enriq": pd.DataFrame(),
        "df_ms_enriq": pd.DataFrame(),
        "df_ms_enriq_todos": pd.DataFrame(),
        "df_ms_enriq_2024": pd.DataFrame(),
        "df_notas_individuais": pd.DataFrame(),
        "df_concluintes": pd.DataFrame(),
    }

    if sub_aba in (_SUBABA_PANORAMA, _SUBABA_TERRITORIO, _SUBABA_HUB):
        ctx["df_concluintes"] = carregar_concluintes()

    if sub_aba == _SUBABA_TERRITORIO:
        cres = carregar_cres()
        mapa = carregar_mapa_municipio_cre()
        ctx["df_bruta_ms_enriq"] = enriquecer_ms(df_bruta_ms, cres, mapa)
        df_todos = reconstruir_ms_enriquecido(tabelas, ANOS_DISPONIVEIS, deps)
        df_todos = aplicar_cre_por_municipio(df_todos, mapa)
        ctx["df_ms_enriq"] = enriquecer_ms(
            reconstruir_ms_enriquecido(tabelas, anos_list, deps), cres, mapa,
        )
        ctx["df_ms_enriq_todos"] = enriquecer_ms(df_todos, cres, mapa)
        df_2024 = reconstruir_escolas_2024_ms(tabelas, deps)
        if 2024 in anos_list and df_2024.empty:
            sub = ctx["df_ms_enriq"][ctx["df_ms_enriq"]["NU_ANO"] == 2024]
            if "CO_ESCOLA" in sub.columns:
                df_2024 = sub[sub["CO_ESCOLA"].notna()].copy()
        ctx["df_ms_enriq_2024"] = enriquecer_ms(df_2024, cres, mapa)

    if sub_aba in (_SUBABA_DESEMPENHO, _SUBABA_TERRITORIO):
        ctx["df_notas_individuais"] = carregar_notas_individuais(anos=tuple(int(a) for a in anos_list))
        if (
            sub_aba == _SUBABA_TERRITORIO
            and not ctx["df_notas_individuais"].empty
            and "Estadual" in deps
            and tem_notas_individuais_ano(ctx["df_notas_individuais"], 2024)
        ):
            df_2024 = filtrar_notas_individuais(
                ctx["df_notas_individuais"], ano=2024, dependencia="Estadual",
            )
            cres = carregar_cres()
            mapa = carregar_mapa_municipio_cre()
            ctx["df_ms_enriq_2024"] = enriquecer_ms(df_2024, cres, mapa)

    return ctx


def main():
    if st.session_state.get("_hub_build_loaded") != HUB_BUILD_ID:
        st.session_state["_hub_build_loaded"] = HUB_BUILD_ID
        st.session_state["_fig_ck"] = 0

    anos_sel, dep_selecionadas = ANOS_DISPONIVEIS, ORDEM_DEP
    periodo = (
        f"{min(anos_sel)}–{max(anos_sel)}"
        if anos_sel and len(anos_sel) >= 2
        else (str(anos_sel[0]) if anos_sel else "—")
    )

    ctx_base = build_dashboard_context(
        tuple(int(a) for a in anos_sel),
        tuple(dep_selecionadas),
        _SUBABA_HUB,
    )
    if ctx_base["df_filt_ms"].empty:
        st.error("Nenhum participante encontrado no recorte selecionado.")
        return

    _render_cabecalho_com_kpis(ctx_base["diag"], periodo)
    _render_populacao_referencia_compacta()

    _fragment_camada_status(
        ctx_base["diag"],
        anos_sel,
        ctx_base["tabelas"],
        ctx_base["df_bruta_ms"],
        ctx_base["df_filt_ms"],
    )

    st.markdown("---")
    mostrar_detalhe = st.checkbox(
        "Carregar análises detalhadas",
        value=False,
        key="hub_carregar_detalhe",
        help="Ative para abrir a seção inferior (mais gráficos e tabelas).",
    )
    if mostrar_detalhe:
        _fragment_camada_detalhe(anos_sel, dep_selecionadas)

    with st.expander("Metodologia, fontes e camadas técnicas"):
        _render_metodologia_detalhe()

    st.markdown(
        f"<div class='rodape'>Fonte: INEP — Microdados do ENEM. Cadastro de escolas: CRES."
        f" · hub {HUB_BUILD_ID}</div>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
    
