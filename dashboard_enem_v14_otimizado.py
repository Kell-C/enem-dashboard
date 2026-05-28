"""
==========================================================================
PAINEL ANALÍTICO DO ENEM 2019-2024 — ESCOLAS ESTADUAIS
Versão 12.0 — Ajustes finais: referências estaduais/nacionais, seletor de
dependência nas abas territoriais, destaque do grupo analisado, ano
selecionável no panorama nacional.
==========================================================================
"""

import re as _re
import html as _html
import os
from os.path import exists
import warnings
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Painel ENEM | Escolas Estaduais",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

ARQUIVO_PARQUET = r"C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet"

ARQUIVO_CRES = r"C:\enem_analise\scripts\V14\cres.xlsx"


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
    # Superfícies
    "bg_app":          "#F4F6FA",   # cinza azulado muito sutil de fundo
    "bg_card":         "#FFFFFF",   # cards e blocos
    "bg_sidebar":      "#FFFFFF",
    "bg_subtle":       "#F8FAFC",   # blocos secundários
    "insight_bg":      "#EFF4FB",   # box de destaque
    # Texto
    "texto":           "#1A2332",   # quase preto, alto contraste em fundo claro
    "texto_secundario": "#5C6B7E",   # cinza azulado para legendas
    "texto_muted":     "#94A3B8",   # ainda mais discreto
    "texto_inv":       "#FFFFFF",   # sobre superfícies escuras
    # Bordas e linhas
    "borda":           "#E3E8EF",
    "borda_sutil":     "#EEF2F6",
    "linha_eixo":      "#CBD5E1",
    "grid_sutil":      "#F1F5F9",
    # Plotly
    "plot_template":   "plotly_white",
    "plot_paper":      "#FFFFFF",
    "plot_plot":       "#FFFFFF",
}

# ------------------------------------------------------------
# Paleta de cores (semântica + identidade visual MS)
# ------------------------------------------------------------
# Azul institucional SED/MS — tom mais sóbrio que o azul-genérico anterior.
AZUL_PRINCIPAL = "#003F7F"   # azul institucional MS (cabeçalhos, ênfase)
AZUL_CLARO = "#1E5FAD"   # azul médio (links, destaques)
AZUL_ACCENT = "#3B82F6"   # azul vivo (acentos, marcadores)
LARANJA_DESTAQUE = "#E87722"   # laranja institucional (destaque MS)
DOURADO_MS = "#C8A951"   # dourado discreto (selos, separadores nobres)

# Semáforo (status)
COR_POSITIVO = "#0F8A5F"   # verde esmeralda mais sóbrio
COR_ATENCAO = "#D97706"   # âmbar mais escuro (melhor contraste)
COR_CRITICO = "#C03A2B"   # vermelho institucional menos saturado
COR_NEUTRO = "#5C6B7E"

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
    "NU_NOTA_CN": "Ciências da Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens e Códigos",
    "NU_NOTA_MT": "Matemática",
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
        --ms-azul-1: {AZUL_PRINCIPAL};
        --ms-azul-2: {AZUL_CLARO};
        --ms-azul-3: {AZUL_ACCENT};
        --ms-laranja: {LARANJA_DESTAQUE};
        --ms-dourado: {DOURADO_MS};
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

      .stApp {{
        background-color: {TEMA['bg_app']} !important;
        color: {TEMA['texto']} !important;
      }}

      /* Cabeçalho institucional */
      .cab-painel {{
          background: linear-gradient(120deg, {AZUL_PRINCIPAL} 0%, {AZUL_CLARO} 70%, {AZUL_ACCENT} 100%);
          color: {TEMA['texto_inv']};
          padding: 22px 26px; border-radius: 14px;
          margin-bottom: 22px;
          box-shadow: 0 4px 14px rgba(0, 63, 127, 0.18);
          border: 1px solid rgba(255,255,255,0.06);
      }}
      .cab-painel .titulo {{
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 1.7rem; font-weight: 800; color: #FFFFFF;
          letter-spacing: -0.01em;
      }}
      .cab-painel .subtitulo {{
          font-size: 0.98rem; color: rgba(255,255,255,0.86); margin-top: 4px;
          font-weight: 500;
      }}
      .cab-painel .badge-row {{
          margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;
      }}
      .cab-painel .badge {{
          background: rgba(255,255,255,0.14);
          border: 1px solid rgba(255,255,255,0.22);
          color: #FFFFFF; font-size: 0.78rem; font-weight: 600;
          padding: 4px 12px; border-radius: 999px;
      }}

      /* Bloco de título de seção */
      .bloco-titulo {{
          border-left: 5px solid {AZUL_PRINCIPAL};
          padding: 10px 16px; margin: 22px 0 14px 0;
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
          margin: 4px 0 0 0; font-size: 0.92rem;
      }}

      /* Cards KPI */
      .kpi-card {{
          background: {TEMA['bg_card']};
          padding: 16px 18px; border-radius: 12px;
          border: 1px solid {TEMA['borda']};
          border-left: 4px solid {TEMA['borda']};
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
          height: 100%;
          transition: box-shadow 0.18s ease, transform 0.18s ease;
      }}
      .kpi-card:hover {{
          box-shadow: 0 4px 14px rgba(0, 63, 127, 0.10);
          transform: translateY(-1px);
      }}
      .kpi-card .rotulo {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.74rem; text-transform: uppercase;
          letter-spacing: 0.6px; font-weight: 700;
      }}
      .kpi-card .valor {{
          color: {AZUL_PRINCIPAL} !important;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 2rem; font-weight: 800;
          line-height: 1.1; margin-top: 4px;
      }}
      .kpi-card .sub {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.84rem; margin-top: 2px;
      }}
      .kpi-card.positivo {{ border-left-color: {COR_POSITIVO}; }}
      .kpi-card.positivo .valor {{ color: {COR_POSITIVO} !important; }}
      .kpi-card.atencao  {{ border-left-color: {COR_ATENCAO}; }}
      .kpi-card.atencao .valor {{ color: {COR_ATENCAO} !important; }}
      .kpi-card.critico  {{ border-left-color: {COR_CRITICO}; }}
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

      /* Rodapé */
      .rodape {{
          color: {TEMA['texto_secundario']} !important;
          font-size: 0.82rem; margin-top: 28px; text-align: center;
          padding-top: 14px; border-top: 1px solid {TEMA['borda_sutil']};
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
          background: {TEMA['bg_sidebar']} !important;
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


def fmt_delta(n, casas: int = 1, unidade: str = " pts") -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    sinal = "+" if n >= 0 else "−"
    return f"{sinal}{fmt_float(abs(n), casas)}{unidade}"

# ============================================================
# CARGA DE DADOS
# ============================================================


@st.cache_data(show_spinner="Carregando microdados do ENEM...", max_entries=1)
def carregar_base_bruta() -> pd.DataFrame:
    if not exists(ARQUIVO_PARQUET):
        st.error(f"Arquivo não encontrado: {ARQUIVO_PARQUET}")
        st.stop()

    cols: Optional[list[str]]
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
        schema_cols = pq.read_schema(ARQUIVO_PARQUET).names
        cols = [c for c in COLS_BASE if c in schema_cols]
    except ImportError:
        st.warning(
            "Pacote 'pyarrow' não encontrado. Instale com `pip install pyarrow` "
            "para leitura otimizada. Tentando fallback…"
        )
        cols = None

    try:
        if cols is not None:
            df = pd.read_parquet(ARQUIVO_PARQUET, columns=cols)
        else:
            df = pd.read_parquet(ARQUIVO_PARQUET)
            df = df[[c for c in COLS_BASE if c in df.columns]]
    except ImportError as e:
        st.error(
            "Não foi possível ler o arquivo parquet: nenhum engine disponível. "
            f"Instale `pyarrow` ou `fastparquet`. Detalhe: {e}"
        )
        st.stop()

    # Tipos enxutos e diretos — sem convert_dtypes nem conversões redundantes
    df["NU_ANO"] = pd.to_numeric(df["NU_ANO"], errors="coerce").astype("int16")
    df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")

    for col_uf in ("SG_UF_ESC", "SG_UF_PROVA"):
        if col_uf in df.columns:
            df[col_uf] = (
                df[col_uf].astype(str).str.strip().str.upper()
                .replace({"NAN": None, "": None, pd.NA: None})
            )

    df["DEP_ADM"] = df["TP_DEPENDENCIA_ADM_ESC"].map(DEP_MAP)

    for c in COLS_NOTAS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")

    df["MEDIA_GERAL"] = df[COLS_NOTAS].mean(axis=1, skipna=True).astype("float32")

    return df


def carregar_base_filtrada(df_bruta: pd.DataFrame) -> pd.DataFrame:
    df = df_bruta.copy()
    mask = df["CATEGORIA_PARTICIPACAO"] == "presente_ambos_dias"
    if "TP_ST_CONCLUSAO" in df.columns:
        mask &= (df["TP_ST_CONCLUSAO"] == 2) | (df["TP_ST_CONCLUSAO"].isna())
    if "IN_TREINEIRO" in df.columns:
        mask &= (df["IN_TREINEIRO"] == 0) | (df["IN_TREINEIRO"].isna())
    return df[mask].reset_index(drop=True)


def _construir_mapa_cre_completo() -> dict:
    """Retorna dict mapeando 'CRE 01' -> 'CRE 01 - AQUIDAUANA', etc.
    Lê a aba 'CREs' do arquivo CRES e, para cada código curto,
    encontra o nome completo correspondente.
    """
    if not os.path.exists(ARQUIVO_CRES):
        return {}
    try:
        df_cres = pd.read_excel(ARQUIVO_CRES, sheet_name="CREs")
    except ValueError:
        return {}
    if "CRE" not in df_cres.columns:
        return {}
    mapa = {}
    for val in df_cres["CRE"].dropna().unique():
        val = str(val).strip()
        if " - " in val:
            codigo = val.split(" - ")[0].strip()
            mapa[codigo] = val
            mapa[val] = val
        else:
            if val not in mapa:
                mapa[val] = val
    return mapa


def carregar_cres() -> pd.DataFrame:
    if not os.path.exists(ARQUIVO_CRES):
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])
    try:
        cres = pd.read_excel(ARQUIVO_CRES, sheet_name="Cód.INEP-CREs")
    except ValueError:
        cres = pd.read_excel(ARQUIVO_CRES, sheet_name=0)

    col_cod = None
    for possivel in ["CÓD INEP", "COD INEP", "CÓD.INEP", "COD.INEP"]:
        if possivel in cres.columns:
            col_cod = possivel
            break

    if col_cod is None:
        st.error("Coluna de código INEP não encontrada no arquivo CRES")
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])

    col_esc = "UNIDADE ESCOLAR " if "UNIDADE ESCOLAR " in cres.columns else "UNIDADE ESCOLAR"
    col_mun = "MUNICÍPIO" if "MUNICÍPIO" in cres.columns else "MUNICIPIO"

    cres[col_cod] = pd.to_numeric(
        cres[col_cod], errors="coerce").astype("Int64")
    cres = cres[[col_cod, "CRE", col_mun, col_esc]].dropna(subset=[col_cod])
    cres = cres.drop_duplicates(subset=[col_cod])

    # Normalizar CRE: usar sempre nome completo (CRE XX - NOME)
    mapa_cre_completo = _construir_mapa_cre_completo()
    cres["CRE"] = cres["CRE"].map(mapa_cre_completo).fillna(cres["CRE"])

    cres = cres.rename(columns={
        col_cod: "CO_ESCOLA", col_mun: "MUNICIPIO_CRES", col_esc: "NOME_ESCOLA",
    })
    return cres


def carregar_mapa_municipio_cre() -> dict:
    if not os.path.exists(ARQUIVO_CRES):
        return {}
    try:
        df_cres = pd.read_excel(ARQUIVO_CRES, sheet_name="CREs")
    except ValueError:
        st.warning(
            "Aba 'CREs' não encontrada no arquivo de cadastro. "
            "O mapeamento município → CRE não estará disponível."
        )
        return {}
    mapa_cre_completo = _construir_mapa_cre_completo()
    mapa = {}
    for _, row in df_cres.iterrows():
        municipio = str(row.get("MUNICÍPIO", "")).strip().upper()
        cre = str(row.get("CRE", "")).strip()
        if municipio and cre:
            municipio_norm = municipio.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Â", "A").replace(
                "Ê", "E").replace("Î", "I").replace("Ô", "O").replace("Û", "U").replace("Ã", "A").replace("Õ", "O").replace("Ç", "C").replace("À", "A")
            cre_normalizado = mapa_cre_completo.get(cre, cre)
            # Preferir o nome completo; sobrescrever o curto pelo completo
            mapa[municipio_norm] = cre_normalizado
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
    mapa_cre_completo = _construir_mapa_cre_completo()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df


def aplicar_cre_por_municipio(df: pd.DataFrame, mapa_muni_cre: dict) -> pd.DataFrame:
    df = df.copy()
    if "CRE" not in df.columns:
        df["CRE"] = pd.NA
    col_mun = None
    if "MUNICIPIO_CRES" in df.columns and df["MUNICIPIO_CRES"].notna().any():
        col_mun = "MUNICIPIO_CRES"
    elif "NO_MUNICIPIO_ESC" in df.columns and df["NO_MUNICIPIO_ESC"].notna().any():
        col_mun = "NO_MUNICIPIO_ESC"
    if col_mun and mapa_muni_cre:
        mask_sem_cre = df["CRE"].isna()
        municipios_normalizados = df.loc[mask_sem_cre, col_mun].apply(
            normalizar_texto)
        df.loc[mask_sem_cre, "CRE"] = municipios_normalizados.map(
            mapa_muni_cre)

    # Normalizar nomes curtos de CRE para nomes completos
    mapa_cre_completo = _construir_mapa_cre_completo()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df


# ============================================================
# HELPERS DE UI E GRÁFICO
# ============================================================
_CK = [0]


def _chart(fig, **kw):
    _CK[0] += 1
    st.plotly_chart(fig, key=f"_c{_CK[0]}", width="stretch", **kw)


def aplicar_tema(fig, altura: int = 400):
    """Aplica identidade visual institucional aos gráficos Plotly.

    - Sem grade no eixo X (linhas verticais removidas).
    - Eixo Y com grid sutil (apenas referência horizontal).
    - Linhas de eixo finas, em tom neutro.
    - Tipografia Source Sans 3 / Plus Jakarta Sans.
    """
    fig.update_layout(
        template=TEMA["plot_template"],
        height=altura,
        margin=dict(l=24, r=24, t=56, b=44),
        font=dict(family="Source Sans 3, system-ui, sans-serif",
                  size=12.5, color=TEMA["texto"]),
        title_font=dict(family="Plus Jakarta Sans, sans-serif",
                        size=15, color=AZUL_PRINCIPAL),
        legend=_legenda_padrao(y_pos=-0.22, font_size=11.5),
        hoverlabel=dict(
            bgcolor=TEMA["bg_card"], font_size=12.5,
            font_color=TEMA["texto"],
            bordercolor=TEMA["borda"],
        ),
        paper_bgcolor=TEMA["plot_paper"],
        plot_bgcolor=TEMA["plot_plot"],
        hovermode="closest",
        bargap=0.22, bargroupgap=0.06,
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False,
        showline=True, linecolor=TEMA["linha_eixo"], linewidth=1,
        ticks="outside", tickcolor=TEMA["linha_eixo"], ticklen=4,
        tickfont=dict(color=TEMA["texto_secundario"], size=11.5),
        title_font=dict(color=TEMA["texto_secundario"], size=12),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=TEMA["grid_sutil"], gridwidth=1,
        zeroline=False,
        showline=False,
        ticks="outside", tickcolor=TEMA["linha_eixo"], ticklen=4,
        tickfont=dict(color=TEMA["texto_secundario"], size=11.5),
        title_font=dict(color=TEMA["texto_secundario"], size=12),
    )
    return fig


def _hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


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


def titulo_secao(titulo: str, subtitulo: str = ""):
    t = _html.escape(str(titulo))
    s = _html.escape(str(subtitulo)) if subtitulo else ""
    st.markdown(
        f"""<div class='bloco-titulo'><h3>{t}</h3>"""
        f"""{"<p>" + s + "</p>" if s else ""}</div>""",
        unsafe_allow_html=True,
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


def _add_box(fig, s: pd.Series, name: str, color: str, x_val=None,
             legendgroup=None, showlegend=True):
    st_ = _stats_box(s)
    if st_ is None:
        return
    kw = dict(
        name=name,
        q1=[st_["q1"]], median=[st_["median"]], q3=[st_["q3"]],
        mean=[st_["mean"]],
        lowerfence=[st_["low"]], upperfence=[st_["up"]],
        marker_color=color, boxmean=True,
        legendgroup=legendgroup or name, showlegend=showlegend,
    )
    if x_val is not None:
        kw["x"] = [str(x_val)]
    fig.add_trace(go.Box(**kw))


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Converte '#RRGGBB' em 'rgba(r,g,b,alpha)' para uso em bgcolor translúcido."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _legenda_padrao(y_pos: float = 1.02, font_size: int = 11, entry_width: int = 150):
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
        tracegroupgap=10,
        font=dict(size=font_size, color=TEMA["texto"]),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor=TEMA["borda"],
        borderwidth=1,
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
def diagnostico_estadual(df_filt_ms, df_bruta_ms, df_br_filt) -> dict:
    d = {}
    df_est = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    df_est_br = df_br_filt[df_br_filt["DEP_ADM"] == "Estadual"]
    df_est_bruta = df_bruta_ms[df_bruta_ms["DEP_ADM"] == "Estadual"]

    d["n_inscritos"] = len(df_est_bruta)
    d["n_part"] = len(df_est)
    d["tx_part"] = round(100 * d["n_part"] / d["n_inscritos"],
                         1) if d["n_inscritos"] else 0.0
    d["media_estadual_ms"] = float(
        df_est["MEDIA_GERAL"].mean()) if not df_est.empty else np.nan
    d["media_estadual_br"] = float(
        df_est_br["MEDIA_GERAL"].mean()) if not df_est_br.empty else np.nan
    d["diff_vs_nacional"] = d["media_estadual_ms"] - d["media_estadual_br"]

    serie = df_est.groupby("NU_ANO")["MEDIA_GERAL"].mean().round(2)
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

    col_uf = "SG_UF_ESC" if "SG_UF_ESC" in df_br_filt.columns else "SG_UF_PROVA"
    ranking_ufs = (df_est_br.groupby(col_uf)["MEDIA_GERAL"].mean()
                   .dropna().round(2).sort_values(ascending=False))
    ranking_ufs = ranking_ufs[ranking_ufs.index.to_series().str.len() == 2]
    d["ranking_ufs"] = ranking_ufs
    if "MS" in ranking_ufs.index:
        pos = int(list(ranking_ufs.index).index("MS")) + 1
        total = int(len(ranking_ufs))
        d["pos_ms"] = pos
        d["total_ufs"] = total
    else:
        d["pos_ms"] = None
        d["total_ufs"] = int(len(ranking_ufs))

    # Posição do MS apenas no ano mais recente disponível no recorte
    # (melhor proxy do diagnóstico atual, complementar à média histórica).
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
            ranking_ano = ranking_ano[ranking_ano.index.to_series(
            ).str.len() == 2]
            d["ranking_ufs_recente"] = ranking_ano
            d["total_ufs_recente"] = int(len(ranking_ano))
            if "MS" in ranking_ano.index:
                d["pos_ms_recente"] = int(
                    list(ranking_ano.index).index("MS")) + 1
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
    return {
        "ms": float(df_ms[area_col].mean()) if not df_ms.empty else np.nan,
        "br": float(df_br[area_col].mean()) if not df_br.empty else np.nan,
    }


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


def fig_participacao_por_ano(df_bruta_ms, df_filt_ms, anos_sel, dep="Estadual"):
    linhas = []
    for ano in sorted(anos_sel):
        insc = len(df_bruta_ms[(df_bruta_ms["NU_ANO"] == ano) & (
            df_bruta_ms["DEP_ADM"] == dep)])
        part = len(df_filt_ms[(df_filt_ms["NU_ANO"] == ano)
                   & (df_filt_ms["DEP_ADM"] == dep)])
        pct = round(100 * part / insc, 1) if insc else 0.0
        linhas.append(dict(Ano=int(ano), Inscritos=insc,
                      Participantes=part, Pct=pct))
    d = pd.DataFrame(linhas)

    fig = go.Figure()
    fig.add_bar(x=d["Ano"], y=d["Inscritos"], name="Inscritos",
                marker_color=COR_BAR_NEUTRA,
                text=[fmt_int(v) for v in d["Inscritos"]],
                textposition="inside")
    fig.add_bar(x=d["Ano"], y=d["Participantes"],
                name="Presentes nos 2 dias",
                marker_color=CORES_DEP[dep],
                text=[fmt_int(v) for v in d["Participantes"]],
                textposition="outside")
    fig.add_trace(go.Scatter(
        x=d["Ano"], y=d["Pct"], name="Taxa de participação (%)",
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
        title="Inscritos, presentes e taxa de participação — rede estadual",
        legend=dict(tracegroupgap=10),
    )
    return aplicar_tema(fig, 430)


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
    fig.update_yaxes(range=range_dinamico(dfv["Valor"], padding=0.08))
    return aplicar_tema(fig, 430)


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
            range=range_dinamico(*series_eixo, padding=0.08,
                                 referencias=(media_ms_ref, media_br_ref)),
            title="Nota média",
        ),
        hovermode="x unified",
    )
    return aplicar_tema(fig, 430)


def fig_ranking_horizontal(df, col_label, col_valor, titulo, cor=AZUL_PRINCIPAL,
                           altura=500, casas_decimais=2, media_ms=None, media_br=None,
                           x_range=None, col_n=None, col_taxa=None):
    d = df.copy().sort_values(col_valor, ascending=True)
    d[col_valor] = d[col_valor].round(casas_decimais)
    cores = []
    for v in d[col_valor]:
        if media_ms is not None and v < media_ms:
            cores.append(COR_ATENCAO)
        else:
            cores.append(cor)
    customdata = None
    hovertemplate = None
    if col_n is not None and col_taxa is not None and col_n in d.columns and col_taxa in d.columns:
        customdata = d[[col_n, col_taxa]].values
        hovertemplate = (
            "<b>%{y}</b><br>"
            f"Média: %{{x:.{casas_decimais}f}}<br>"
            "Participantes: %{customdata[0]}<br>"
            "Taxa: %{customdata[1]:.1f}%"
            "<extra></extra>"
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
        fig.add_annotation(
            x=media_ms, xref="x", y=1.0, yref="paper", yanchor="bottom",
            text=f"<b>MS</b> {media_ms:.1f}", showarrow=False, yshift=6,
            font=dict(size=11, color=LARANJA_DESTAQUE),
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor=LARANJA_DESTAQUE, borderpad=4,
        )
    if media_br is not None:
        fig.add_vline(
            x=media_br, line_dash="dot", line_color=COR_BRASIL, line_width=2,
        )
        fig.add_annotation(
            x=media_br, xref="x", y=0.0, yref="paper", yanchor="top",
            text=f"<b>BR</b> {media_br:.1f}", showarrow=False, yshift=-38,
            font=dict(size=11, color=COR_BRASIL),
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor=COR_BRASIL, borderpad=4,
        )
    fig.update_layout(
        title=titulo,
        xaxis=dict(
            title="",
            range=x_range if x_range is not None else range_dinamico(d[col_valor], padding=0.05,
                                 referencias=(media_ms, media_br)),
        ),
        yaxis=dict(title=""),
        margin=dict(t=52, b=80),
    )
    return aplicar_tema(fig, altura)


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
                   range=range_dinamico(g[col], padding=0.05)),
    )
    return aplicar_tema(fig, 440)

# ============================================================
# SIDEBAR
# ============================================================


def render_sidebar():
    with st.sidebar:
        st.markdown("## 📊 Painel ENEM")
        st.markdown("Edições 2019 a 2024")
        st.markdown("---")

        with st.expander("ℹ️ Sobre o grupo analisado", expanded=True):
            st.markdown("""
            **Critérios de inclusão aplicados:**
            - Presentes nos dois dias de prova
            - Concluintes do Ensino Médio no ano da edição
            - Em 2024 os dois últimos critérios não estão disponíveis nos microdados
            """)

        st.markdown("---")
        st.caption("**Fonte:** INEP — Microdados do ENEM")
        st.caption("**Cadastro de escolas:** CRES")
    return ANOS_DISPONIVEIS, ORDEM_DEP

# ============================================================
# ABA 1 - SUMÁRIO EXECUTIVO
# ============================================================


def aba_sumario_executivo(diag: dict, anos_sel: list):
    titulo_secao(
        "Sumário executivo",
        "Leitura rápida dos principais indicadores da rede estadual.",
    )

    status_part = classificar_participacao(diag["tx_part"])
    status_var = classificar_tendencia(diag.get("variacao_inicio_fim", 0))
    status_pos = classificar_posicao(
        diag.get("pos_ms"), diag.get("total_ufs", 0))

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1,
             "Estudantes inscritos",
             fmt_int(diag["n_inscritos"]),
             f"Participantes: {fmt_int(diag['n_part'])}")
    kpi_card(c2,
             "Taxa de participação",
             fmt_pct(diag["tx_part"]),
             status=status_part)
    kpi_card(c3,
             "Média geral",
             fmt_float(diag["media_estadual_ms"]),
             f"Nacional: {fmt_float(diag['media_estadual_br'])}")
    kpi_card(c4,
             "Variação no período",
             fmt_delta(diag.get("variacao_inicio_fim", 0)),
             f"De {diag.get('ano_inicio', '—')} a {diag.get('ano_fim', '—')}",
             status=status_var)

    st.markdown(" ")
    colA, colB = st.columns(2)
    with colA:
        if len(diag["serie_medias"]) > 0:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=diag["serie_medias"].index, y=diag["serie_medias"].values,
                mode="lines+markers+text",
                text=[fmt_float(v) for v in diag["serie_medias"].values],
                textposition="top center",
                line=dict(color=AZUL_PRINCIPAL, width=3),
                marker=dict(size=8),
            ))
            fig.update_layout(
                title="Evolução da média geral",
                xaxis=dict(title="Ano", tickmode="linear", dtick=1),
                yaxis=dict(title="Nota média", range=[NOTA_MIN, NOTA_MAX]),
            )
            _chart(aplicar_tema(fig, 350))
    with colB:
        pos_recente = diag.get("pos_ms_recente")
        total_recente = diag.get("total_ufs_recente", 0)
        ano_ref_pos = diag.get("ano_referencia_pos")
        pos_hist = diag.get("pos_ms")
        total_hist = diag.get("total_ufs", 0)

        # KPI principal: posição NO ANO MAIS RECENTE (mais informativa
        # para gestão). Microbadge no sub: posição histórica agregada.
        if pos_recente:
            status_pos_atual = classificar_posicao(pos_recente, total_recente)
            if pos_hist and anos_sel and len(anos_sel) >= 2:
                periodo = f"{min(anos_sel)}–{max(anos_sel)}"
                sub_hist = f"Histórico: {pos_hist}º de {total_hist} (média {periodo})"
            elif pos_hist:
                sub_hist = f"Histórico: {pos_hist}º de {total_hist}"
            else:
                sub_hist = ""
            rotulo = (f"Posição nacional · {ano_ref_pos}"
                      if ano_ref_pos else "Posição nacional")
            kpi_card(st.container(),
                     rotulo,
                     f"{pos_recente}º de {total_recente}",
                     sub=sub_hist,
                     status=status_pos_atual)
            st.markdown(
                f"<div class='insight'>Diferença de "
                f"<strong>{fmt_delta(diag['diff_vs_nacional'])}</strong> "
                f"em relação à média nacional das escolas estaduais.</div>",
                unsafe_allow_html=True,
            )
        elif pos_hist:
            # Fallback: se não houver ano de referência, mostra apenas histórico.
            kpi_card(st.container(),
                     "Posição nacional",
                     f"{pos_hist}º de {total_hist}",
                     status=status_pos)
            st.markdown(
                f"<div class='insight'>Diferença de "
                f"<strong>{fmt_delta(diag['diff_vs_nacional'])}</strong> "
                f"em relação à média nacional das escolas estaduais.</div>",
                unsafe_allow_html=True,
            )

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
        _txt_part = {
            "positivo": (
                f"{fmt_pct(diag['tx_part'])} dos inscritos compareceram aos dois dias de provas "
                f"({fmt_int(diag['n_part'])} participantes)."
            ),
            "atencao": (
                f"Taxa de {fmt_pct(diag['tx_part'])} sugere margem para melhoria "
                f"({fmt_int(diag['n_part'])} de {fmt_int(diag['n_inscritos'])} inscritos)."
            ),
            "critico": (
                f"Apenas {fmt_pct(diag['tx_part'])} dos inscritos compareceram aos dois dias "
                f"({fmt_int(diag['n_part'])} de {fmt_int(diag['n_inscritos'])})."
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
                f"Média geral de MS: {fmt_float(media_ms_val)} pts — "
                f"{fmt_delta(diff)} em relação à média nacional das escolas estaduais.",
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


def aba_panorama_participacao(df_bruta_ms, df_filt_ms, anos_sel,
                              df_bruta_ms_enriq=None, df_filt_ms_enriq=None,
                              df_bruta_nacional=None, df_filt_nacional=None):
    titulo_secao(
        "Panorama da participação no ENEM",
        "Adesão por ano"
    )

    _chart(fig_participacao_por_ano(
        df_bruta_ms, df_filt_ms, anos_sel, "Estadual"))

    # --- Gráfico de posição nacional do MS ---
    if df_bruta_nacional is not None and df_filt_nacional is not None:
        st.markdown(
            "### Posição do MS na taxa de participação nacional (rede estadual)")
        col_uf_nac = "SG_UF_ESC" if "SG_UF_ESC" in df_bruta_nacional.columns else "SG_UF_PROVA"
        posicoes_ms = []
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
            # Calcular taxa do MS com dados locais para consistência
            insc_ms = len(df_bruta_ms[(df_bruta_ms["NU_ANO"] == ano) & (
                df_bruta_ms["DEP_ADM"] == "Estadual")])
            part_ms = len(df_filt_ms[(df_filt_ms["NU_ANO"] == ano) & (
                df_filt_ms["DEP_ADM"] == "Estadual")])
            taxa_ms = round(100 * part_ms / insc_ms, 1) if insc_ms else 0.0
            if "MS" in ranking:
                pos_ms = ranking.index("MS") + 1
                posicoes_ms.append(
                    dict(Ano=ano, Posição=pos_ms, Total=len(ranking), Taxa=taxa_ms))

        if posicoes_ms:
            df_pos = pd.DataFrame(posicoes_ms)
            fig_pos = go.Figure()

            n_total = df_pos["Total"].iloc[0] if len(df_pos) > 0 else 27
            terco = n_total / 3
            fig_pos.add_hrect(
                y0=0, y1=terco, fillcolor=COR_POSITIVO, opacity=0.08, line_width=0)
            fig_pos.add_hrect(y0=terco, y1=2*terco,
                              fillcolor=COR_ATENCAO, opacity=0.08, line_width=0)
            fig_pos.add_hrect(y0=2*terco, y1=n_total+1,
                              fillcolor=COR_CRITICO, opacity=0.08, line_width=0)

            cores = []
            for _, row in df_pos.iterrows():
                if row["Posição"] <= terco:
                    cores.append(COR_POSITIVO)
                elif row["Posição"] <= 2*terco:
                    cores.append(COR_ATENCAO)
                else:
                    cores.append(COR_CRITICO)

            fig_pos.add_trace(go.Scatter(
                x=df_pos["Ano"], y=df_pos["Posição"],
                mode="lines+markers+text",
                text=[
                    f"{int(r['Posição'])}º de {int(r['Total'])} ({r['Taxa']:.1f}%)" for _, r in df_pos.iterrows()],
                textposition="top center",
                line=dict(color=AZUL_PRINCIPAL, width=3),
                marker=dict(size=12, color=cores,
                            line=dict(width=2, color="white")),
            ))
            fig_pos.update_yaxes(autorange="reversed",
                                 title="Posição (1º = melhor)")
            fig_pos.update_xaxes(title="Ano", tickmode="linear", dtick=1)
            fig_pos.update_layout(
                title="Posição do MS entre as UFs — taxa de participação (rede estadual)",
                hovermode="x unified",
            )
            _chart(aplicar_tema(fig_pos, 420))
        else:
            st.info("Não foi possível calcular a posição nacional do MS.")

    st.markdown("### Resumo por ano e dependência")
    linhas_cards = []
    for ano in sorted(anos_sel):
        bruta_ano = df_bruta_ms[df_bruta_ms["NU_ANO"] == ano]
        filt_ano = df_filt_ms[df_filt_ms["NU_ANO"] == ano]
        for dep in ORDEM_DEP:
            n_insc = len(bruta_ano[bruta_ano["DEP_ADM"] == dep])
            n_part = len(filt_ano[filt_ano["DEP_ADM"] == dep])
            pct = round(100 * n_part / n_insc, 1) if n_insc else 0.0
            linhas_cards.append(dict(
                Ano=int(ano),
                Dependência=dep,
                Inscritos=int(n_insc),
                Participantes=int(n_part),
                Taxa=pct,
            ))

    df_cards = pd.DataFrame(linhas_cards)
    anos_unicos = sorted(df_cards["Ano"].unique())

    if not anos_unicos:
        st.info("Nenhum ano disponível no recorte atual.")
        return
    cols = st.columns(len(anos_unicos))
    for i, ano in enumerate(anos_unicos):
        with cols[i]:
            st.markdown(f"**{ano}**")
            sub_df = df_cards[df_cards["Ano"] == ano]
            for _, row in sub_df.iterrows():
                dep = row["Dependência"]
                cor_dep = CORES_DEP.get(dep, COR_NEUTRO)
                dep_safe = _html.escape(str(dep))
                insc_safe = _html.escape(fmt_int(row['Inscritos']))
                part_safe = _html.escape(fmt_int(row['Participantes']))
                taxa_safe = f"{row['Taxa']:.1f}%"
                st.markdown(
                    f"""
                    <div style="margin-bottom:12px; border-left:3px solid {cor_dep}; padding-left:8px;">
                        <div style="font-weight:700; color:{cor_dep};">{dep_safe}</div>
                        <div style="font-size:0.88rem; color:{TEMA['texto']};">
                            <span style="color:{TEMA['texto_secundario']};">📋 {insc_safe} insc.</span><br>
                            <span style="color:{AZUL_PRINCIPAL}; font-weight:600;">✅ {part_safe} part. ({taxa_safe})</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    total_insc_est = len(df_bruta_ms[df_bruta_ms["DEP_ADM"] == "Estadual"])
    total_part_est = len(df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"])
    taxa_est = round(100 * total_part_est / total_insc_est,
                     1) if total_insc_est else 0
    insight_box(
        f"No período selecionado, <strong>{fmt_int(total_insc_est)}</strong> estudantes "
        f"da rede estadual foram inscritos; <strong>{fmt_int(total_part_est)}</strong> "
        f"({fmt_pct(taxa_est)}) compareceram aos dois dias de prova."
    )

# ============================================================
# ABA 3 - DESEMPENHO PEDAGÓGICO
# ============================================================


def aba_desempenho(df_filt_ms, df_br_filt):
    titulo_secao(
        "Desempenho pedagógico — evolução temporal e distribuição",
        "Acompanhamento das notas por área: médias, medianas e dispersão ao longo dos anos."
    )

    # ----- DATAFRAMES DE REFERÊNCIA -----
    df_est_ms = df_filt_ms[df_filt_ms["DEP_ADM"] == "Estadual"]
    df_est_br = df_br_filt[df_br_filt["DEP_ADM"] == "Estadual"]
    deps_exibir = [
        d for d in ORDEM_DEP if d in df_filt_ms["DEP_ADM"].dropna().unique()]

    # ----- 1. MÉDIAS POR ÁREA — MS vs. BRASIL (linhas + marcadores, facetas 2x3) -----
    titulo_secao(
        "Médias por área — MS vs. Brasil (rede estadual)",
        "Linhas mostram a evolução anual da nota média de MS (azul) e do Brasil (cinza tracejado). "
        "Δ no último ano resume a diferença em relação ao Brasil; cor indica situação."
    )

    st.markdown(
        """<div style="display: flex; gap: 30px; margin: 10px 0 15px; font-size: 13px; flex-wrap: wrap;">
        <div><span style="color: #003F7F; font-weight: bold;">━━━</span> Média MS (rede estadual)</div>
        <div><span style="color: #7e8fa6; font-weight: bold;">- - -</span> Média Brasil</div>
        <div><span style="font-weight: bold;">Δ</span> Variação em relação ao Brasil</div>
        </div>""", unsafe_allow_html=True
    )

    def _classifica_delta(d):
        if pd.isna(d):
            return TEMA["texto_secundario"]
        if d >= 0:
            return COR_POSITIVO
        if d >= -10:
            return COR_ATENCAO
        return COR_CRITICO

    anos = sorted(df_est_ms["NU_ANO"].dropna().unique())
    anos_int = [int(a) for a in anos]
    anos_str = [str(a) for a in anos_int]
    areas_keys = list(AREAS.keys())

    dados = []
    for ano in anos:
        for key in areas_keys:
            media_ms = df_est_ms[df_est_ms["NU_ANO"] == ano][key].mean()
            media_br = df_est_br[df_est_br["NU_ANO"] == ano][key].mean()
            delta = media_ms - \
                media_br if (pd.notna(media_ms) and pd.notna(
                    media_br)) else float("nan")
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
        st.info("Sem dados de médias por área para o período selecionado.")
    else:
        n_areas = len(areas_keys)
        n_cols = 3
        n_rows = (n_areas + n_cols - 1) // n_cols

        # Escala Y global (mesma para todas as facetas)
        serie_global = pd.concat(
            [df_plot["MediaMS"], df_plot["MediaBR"]]).dropna()
        if not serie_global.empty:
            amp_g = float(serie_global.max() - serie_global.min())
            y_min_global = max(0, float(serie_global.min()) -
                               max(15, 0.12 * (amp_g + 1)))
            y_max_global = min(1000, float(
                serie_global.max()) + max(25, 0.18 * (amp_g + 1)))
        else:
            y_min_global, y_max_global = 0, 1000

        fig = make_subplots(
            rows=n_rows, cols=n_cols,
            subplot_titles=[AREAS_COMPLETO.get(k, k) for k in areas_keys],
            horizontal_spacing=0.08,
            vertical_spacing=0.20,
            shared_xaxes=False,
            shared_yaxes=False,
        )

        for i, key in enumerate(areas_keys):
            r = i // n_cols + 1
            c = i % n_cols + 1
            d_area = df_plot[df_plot["AreaKey"] == key].sort_values("Ano")
            if d_area.empty:
                continue

            # Linha Brasil (atrás)
            fig.add_trace(
                go.Scatter(
                    x=d_area["Ano"].tolist(),
                    y=d_area["MediaBR"].tolist(),
                    mode="lines+markers",
                    line=dict(color=TEMA["texto_secundario"],
                              width=2, dash="dash"),
                    marker=dict(symbol="x", size=8,
                                color=TEMA["texto_secundario"]),
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

            # Linha MS (na frente, com rótulos)
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
                    text=[f"{v:.0f}" if pd.notna(
                        v) else "" for v in d_area["MediaMS"]],
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

            # Anotação Δ apenas no último ano com dados válidos
            d_valid = d_area.dropna(subset=["MediaMS", "Delta"])
            if not d_valid.empty:
                last = d_valid.iloc[-1]
                cor_d = _classifica_delta(last["Delta"])
                sinal = "+" if last["Delta"] >= 0 else "−"
                fig.add_annotation(
                    x=int(last["Ano"]),
                    y=float(last["MediaMS"]),
                    text=f"<b>Δ {sinal}{abs(last['Delta']):.1f}</b>",
                    showarrow=False,
                    xshift=0,
                    yshift=26,
                    xanchor="center",
                    font=dict(size=11, color=cor_d,
                              family="Plus Jakarta Sans, sans-serif"),
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor=cor_d,
                    borderwidth=1,
                    borderpad=2,
                    row=r, col=c,
                )

            fig.update_yaxes(range=[y_min_global, y_max_global], row=r, col=c)
            fig.update_xaxes(
                tickmode="array",
                tickvals=anos_int,
                ticktext=anos_str,
                range=[anos_int[0] - 0.4, anos_int[-1] + 0.4],
                tickangle=0,
                tickfont=dict(size=11, color=TEMA["texto_secundario"]),
                row=r, col=c,
            )

        # Legenda fantasma (2 entradas únicas)
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
                line=dict(color=TEMA["texto_secundario"],
                          width=2, dash="dash"),
                marker=dict(symbol="x", size=8,
                            color=TEMA["texto_secundario"]),
                name="Brasil",
                legendgroup="br",
                showlegend=True,
                hoverinfo="skip",
            ),
            row=1, col=1,
        )

        altura_total = max(580, 300 * n_rows)
        fig.update_layout(height=altura_total)
        fig = aplicar_tema(fig, altura_total)
        fig.update_layout(
            title=dict(text="", font=dict(size=1)),
            margin=dict(l=24, r=24, t=90, b=50),
            showlegend=True,
            legend=_legenda_padrao(y_pos=1.05, font_size=11),
        )
        nomes_subtitulos = {AREAS_COMPLETO.get(k, k) for k in areas_keys}
        for ann in getattr(fig.layout, 'annotations', []) or []:
            if ann.text and ann.text in nomes_subtitulos:
                ann.font = dict(
                    size=12.5, color=TEMA["texto"], family="Plus Jakarta Sans, sans-serif")

        _chart(fig)

    # ----- 1b. BOXPLOT TEMPORAL POR ÁREA DE CONHECIMENTO — rede Estadual MS -----
    titulo_secao(
        "Distribuição das notas por área de conhecimento ao longo dos anos — rede estadual MS",
        "Cada caixa representa a distribuição das notas no ano: caixa = Q1 ao Q3, "
        "linha central = mediana, marcador × = média; hastes = limites não-discrepantes "
        "(1,5×IQR); marcadores soltos = outliers."
    )

    st.markdown(
        """<div style="display: flex; gap: 24px; margin: 10px 0 15px; font-size: 13px; flex-wrap: wrap;">
        <div><span style="font-weight: bold;">▢</span> Caixa: Q1, mediana, Q3 (×: média)</div>
        <div><span style="font-weight: bold;">━</span> Bigodes: limites não-discrepantes (1,5×IQR)</div>
        <div><span style="font-weight: bold;">●</span> Outliers: notas fora de 1,5×IQR</div>
        <div><em>Recorte:</em> escolas estaduais do Mato Grosso do Sul</div>
        </div>""",
        unsafe_allow_html=True,
    )

    if df_est_ms.empty or df_est_ms["NU_ANO"].dropna().empty:
        st.info("Sem dados disponíveis para a rede estadual MS no recorte selecionado.")
    else:
        df_box_tmp = df_est_ms.copy()
        df_box_tmp["AnoCat"] = df_box_tmp["NU_ANO"].astype(int).astype(str)
        anos_box_temp = sorted(df_box_tmp["AnoCat"].unique().tolist())

        fig_box_temporal = go.Figure()
        areas_plot = [(col, AREAS[col]) for col in COLS_NOTAS]
        for col, nome in areas_plot:
            d_area = df_box_tmp[df_box_tmp[col] > 0]
            for i, ano in enumerate(anos_box_temp):
                sub = d_area[d_area["AnoCat"] == ano][col].dropna()
                if sub.empty:
                    continue
                fig_box_temporal.add_trace(
                    go.Box(
                        y=sub.tolist(),
                        x=[ano] * len(sub),
                        name=nome,
                        marker_color=CORES_AREAS[col],
                        line=dict(color=CORES_AREAS[col], width=2.5),
                        fillcolor=_hex_rgba(CORES_AREAS[col], 0.15),
                        boxmean=True,
                        boxpoints="outliers",
                        marker=dict(
                            color=CORES_AREAS[col],
                            size=3,
                            opacity=0.45,
                            symbol="circle",
                        ),
                        legendgroup=nome,
                        showlegend=(i == 0),
                        hovertemplate=(
                            f"<b>{nome}</b><br>"
                            f"Ano: {ano}<br>"
                            "Mediana: %{median:.1f}<br>"
                            "Q1: %{q1:.1f}<br>"
                            "Q3: %{q3:.1f}<br>"
                            "Mín (haste): %{lowerfence:.1f}<br>"
                            "Máx (haste): %{upperfence:.1f}"
                            "<extra></extra>"
                        ),
                    )
                )

        fig_box_temporal.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_temp,
        )

        series_por_area = [df_box_tmp[df_box_tmp[col] > 0][col]
            for col in COLS_NOTAS]
        y_range = range_dinamico(*series_por_area, padding=0.05)

        fig_box_temporal.update_layout(
            title="Boxplot anual por área de conhecimento — rede estadual MS",
            yaxis=dict(range=y_range, title="Nota"),
            xaxis=dict(title="Ano"),
            boxmode="group",
        )
        fig_box_temporal = aplicar_tema(fig_box_temporal, 580)
        fig_box_temporal.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_temp,
        )
        fig_box_temporal.update_layout(
            showlegend=True,
            margin=dict(l=24, r=80, t=72, b=44),
            legend=_legenda_padrao(y_pos=1.02, font_size=11.5),
        )
        _chart(fig_box_temporal)

    # ----- 1c. EVOLUÇÃO DA MÉDIA E DISPERSÃO POR ÁREA — MS (rede estadual) -----
    titulo_secao(
        "Evolução da média e dispersão por área — MS (rede estadual)",
        "Linha sólida: média anual. Linha tracejada: mediana. "
        "Banda sombreada: faixa de ±1 desvio padrão ao redor da média (cerca de 68% dos candidatos, se a distribuição for próxima da normal)."
    )

    st.markdown(
        """<div style="display: flex; gap: 30px; margin: 10px 0 15px; font-size: 13px; flex-wrap: wrap;">
        <div><span style="color: #003F7F; font-weight: bold;">━━━</span> Média anual</div>
        <div><span style="color: #7e8fa6; font-weight: bold;">- - -</span> Mediana anual</div>
        <div style="background: rgba(0,63,127,0.18); padding: 2px 6px; border-radius: 3px;"><span style="font-weight: bold;">▓▓▓</span> Faixa μ±1σ</div>
        <div><span style="font-weight: bold;">Δ</span> Variação da média</div>
        </div>""", unsafe_allow_html=True
    )

    if df_est_ms.empty or df_est_ms["NU_ANO"].dropna().empty:
        st.info("Sem dados para o gráfico de média e dispersão no período selecionado.")
    else:
        stats_por_area: dict[str, pd.DataFrame] = {}
        for key in areas_keys:
            registros = []
            for ano in anos_int:
                notas_ano = df_est_ms[df_est_ms["NU_ANO"] == ano][key].dropna()
                notas_ano = notas_ano[notas_ano > 0]
                if notas_ano.empty:
                    continue
                _mean = float(notas_ano.mean())
                _std = float(notas_ano.std(ddof=1)) if len(
                    notas_ano) > 1 else 0.0
                registros.append({
                    "Ano": ano,
                    "Media": _mean,
                    "Mediana": float(notas_ano.median()),
                    "Std": _std,
                    "Lo": max(0.0, _mean - _std),
                    "Hi": min(1000.0, _mean + _std),
                    "N": int(len(notas_ano)),
                })
            stats_por_area[key] = pd.DataFrame(registros)

        todos_lo = pd.concat([df["Lo"] for df in stats_por_area.values() if not df.empty]) \
                   if any(not df.empty for df in stats_por_area.values()) else pd.Series(dtype=float)
        todos_hi = pd.concat([df["Hi"] for df in stats_por_area.values() if not df.empty]) \
                   if any(not df.empty for df in stats_por_area.values()) else pd.Series(dtype=float)
        if not todos_lo.empty and not todos_hi.empty:
            amp_fan = float(todos_hi.max() - todos_lo.min())
            y_min_fan = max(0.0, float(todos_lo.min()) -
                            max(15, 0.08 * (amp_fan + 1)))
            y_max_fan = min(1000.0, float(todos_hi.max()) +
                            max(20, 0.10 * (amp_fan + 1)))
        else:
            y_min_fan, y_max_fan = 0, 1000

        fig_fan = make_subplots(
            rows=n_rows, cols=n_cols,
            subplot_titles=[AREAS_COMPLETO.get(k, k) for k in areas_keys],
            horizontal_spacing=0.08,
            vertical_spacing=0.20,
            shared_xaxes=False,
            shared_yaxes=False,
        )

        COR_MEDIANA = "#7e8fa6"

        for i, key in enumerate(areas_keys):
            r = i // n_cols + 1
            c = i % n_cols + 1
            df_stats = stats_por_area.get(key, pd.DataFrame())
            cor_area_fan = CORES_AREAS.get(key, AZUL_PRINCIPAL)
            cor_banda_area = _hex_to_rgba(cor_area_fan, 0.18)

            if df_stats.empty:
                fig_fan.update_yaxes(
                    range=[y_min_fan, y_max_fan], row=r, col=c)
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

        altura_fan = max(580, 300 * n_rows)
        fig_fan.update_layout(height=altura_fan)
        fig_fan = aplicar_tema(fig_fan, altura_fan)
        fig_fan.update_layout(
            title=dict(text="", font=dict(size=1)),
            margin=dict(l=24, r=24, t=90, b=50),
            showlegend=False,
        )
        for ann in getattr(fig_fan.layout, 'annotations', []) or []:
            if ann.text and ann.text in nomes_subtitulos:
                ann.font = dict(
                    size=12.5, color=TEMA["texto"], family="Plus Jakarta Sans, sans-serif")

        _chart(fig_fan)

    # ----- 2. Selectbox de área (para os gráficos seguintes) -----
    area_sel = st.selectbox(
        "Selecione a área de conhecimento",
        options=list(AREAS.keys()),
        format_func=nome_area_ext,
        key="area_desempenho"
    )

    # ----- 3. Boxplot anual da área selecionada — rede estadual MS -----
   
    nome_area = nome_area_ext(area_sel)
    st.markdown(
        f"### Distribuição de {_html.escape(nome_area)} ao longo dos anos — rede estadual MS"
    )

    d_ms_area = df_est_ms[df_est_ms[area_sel] > 0].copy()
    d_br_area = df_est_br[df_est_br[area_sel] > 0].copy()

    if d_ms_area.empty:
        st.info("Sem dados disponíveis para a rede estadual MS na área selecionada.")
    else:
        d_ms_area["AnoCat"] = d_ms_area["NU_ANO"].astype(int).astype(str)
        anos_box_area = sorted(d_ms_area["AnoCat"].unique().tolist())

        # Séries anuais de média (índice = ano int) — variação ao longo do tempo
        serie_ms_anual = (
            d_ms_area.groupby(d_ms_area["NU_ANO"].astype(int))[area_sel]
                    .mean()
                    .sort_index()
        )
        serie_br_anual = (
            d_br_area.groupby(d_br_area["NU_ANO"].astype(int))[area_sel]
                    .mean()
                    .sort_index()
            if not d_br_area.empty else pd.Series(dtype=float)
        )

        # Converte índices para string (para alinhar com eixo X categórico)
        if not serie_ms_anual.empty:
            serie_ms_anual.index = serie_ms_anual.index.astype(str)
        if not serie_br_anual.empty:
            serie_br_anual.index = serie_br_anual.index.astype(str)

        cor_area = AZUL_PRINCIPAL
        fig_box_area = go.Figure()

        # Adiciona um trace go.Box por ano
        for i, ano in enumerate(anos_box_area):
            vals = d_ms_area[d_ms_area["AnoCat"] == ano][area_sel].dropna()
            if vals.empty:
                continue
            fig_box_area.add_trace(
                go.Box(
                    y=vals.tolist(),          # valores das notas
                    x=[ano] * len(vals),      # string do ano (categórico)
                    name=nome_area,
                    marker_color=cor_area,
                    line=dict(color=cor_area, width=2.6),
                    fillcolor=_hex_to_rgba(cor_area, 0.28),
                    boxmean=True,
                    boxpoints="outliers",
                    marker=dict(color=cor_area, size=3.5, opacity=0.55, symbol="circle"),
                    legendgroup="caixas",
                    showlegend=(i == 0),
                    hovertemplate=(
                        f"<b>{_html.escape(nome_area)}</b> — Ano: %{{x}}<br>"
                        "Mediana: %{median:.1f}<br>"
                        "Q1–Q3: %{q1:.1f} – %{q3:.1f}<br>"
                        "Média: %{mean:.1f}<br>"
                        "n = " + str(len(vals)) +
                        "<extra></extra>"
                    ),
                )
            )

        # Configura eixo X categórico ANTES de adicionar os Scatter
        fig_box_area.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_area,
        )

        # Série de médias MS (linha + marcadores + rótulos)
        if not serie_ms_anual.empty:
            fig_box_area.add_trace(
                go.Scatter(
                    x=serie_ms_anual.index.tolist(),
                    y=serie_ms_anual.values.tolist(),
                    mode='lines+markers+text',
                    text=[f'{v:.1f}' for v in serie_ms_anual.values],
                    textposition='top center',
                    textfont=dict(size=10, color=AZUL_PRINCIPAL),
                    name='Média MS — rede estadual',
                    line=dict(color=AZUL_PRINCIPAL, width=2.5),
                    marker=dict(size=7, color=AZUL_PRINCIPAL, symbol='circle'),
                    legendgroup='medias_ms',
                    showlegend=True,
                    hovertemplate='MS: %{y:.1f}<extra></extra>'
                )
            )

        # Série de médias BR (linha + marcadores + rótulos)
        if not serie_br_anual.empty:
            fig_box_area.add_trace(
                go.Scatter(
                    x=serie_br_anual.index.tolist(),
                    y=serie_br_anual.values.tolist(),
                    mode='lines+markers+text',
                    text=[f'{v:.1f}' for v in serie_br_anual.values],
                    textposition='top center',
                    textfont=dict(size=10, color='#d62728'),
                    name='Média BR — rede estadual',
                    line=dict(color='#d62728', width=2, dash='dot'),
                    marker=dict(size=6, color='#d62728', symbol='x'),
                    legendgroup='medias_br',
                    showlegend=True,
                    hovertemplate='Brasil: %{y:.1f}<extra></extra>'
                )
            )

        # Range Y dinâmico
        series_para_range = [d_ms_area[d_ms_area["AnoCat"] == a][area_sel] for a in anos_box_area]
        ref_ms = serie_ms_anual.tolist() if not serie_ms_anual.empty else None
        ref_br = serie_br_anual.tolist() if not serie_br_anual.empty else None
        y_range = range_dinamico(
            *series_para_range,
            padding=0.05,
            referencias=(ref_ms, ref_br),
        )

        fig_box_area.update_layout(
            title=f"Boxplot anual — {nome_area} (rede estadual MS)",
            yaxis=dict(range=y_range, title="Nota"),
            xaxis=dict(title="Ano"),
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

        fig_box_area = aplicar_tema(fig_box_area, 560)
        # Reafirma eixo X categórico DEPOIS do tema
        fig_box_area.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=anos_box_area,
        )
        fig_box_area.update_layout(
            showlegend=True,
            margin=dict(l=24, r=80, t=72, b=44),
            legend=_legenda_padrao(y_pos=1.02, font_size=11.5),
        )
        _chart(fig_box_area)

    # ----- 4. Estatísticas anuais -----
    st.markdown("### Estatísticas anuais — rede estadual")
    anos_presentes = sorted(df_est_ms["NU_ANO"].unique())
    if not anos_presentes:
        st.info("Nenhum ano disponível para a área selecionada.")
        st.stop()
        
    cols = st.columns(len(anos_presentes))
    for i, ano in enumerate(anos_presentes):
        sub = df_est_ms[df_est_ms["NU_ANO"] == ano]
        stats = estatisticas_dict(sub[area_sel])
        with cols[i]:
            st.markdown(
                f"""
                <div style="margin-bottom:12px; border-left:3px solid {AZUL_PRINCIPAL}; padding-left:8px;">
                    <div style="font-weight:700; color:{AZUL_PRINCIPAL};">{_html.escape(str(ano))}</div>
                    <div style="font-size:0.88rem; color:{TEMA['texto']};">
                        <span style="color:{TEMA['texto_secundario']};">👥 Estudantes: {_html.escape(fmt_int(stats['Estudantes']))}</span><br>
                        <span style="color:{COR_POSITIVO};">📊 Média: {_html.escape(fmt_float(stats['Média']))}</span><br>
                        <span style="color:{LARANJA_DESTAQUE};">📐 Mediana: {_html.escape(fmt_float(stats['Mediana']))}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ----- 5. Comparação entre dependências em um ano específico -----
    if anos_presentes:
        ano_comparacao = st.selectbox(
            "Selecione o ano para comparação entre dependências",
            options=sorted(anos_presentes, reverse=True),
            index=0,
            key="ano_comparacao"
        )
        st.markdown(f"### Comparação entre dependências em {ano_comparacao} — todas as áreas")
        df_ult = df_filt_ms[df_filt_ms["NU_ANO"] == ano_comparacao]

        fig_box_areas = go.Figure()
        for dep in deps_exibir:
            d_dep = df_ult[df_ult["DEP_ADM"] == dep]
            for i, (col, nome) in enumerate(AREAS.items()):
                _add_box(fig_box_areas, d_dep[col], name=dep, color=CORES_DEP[dep],
                         x_val=nome, legendgroup=dep, showlegend=(i == 0))
        _series_box = [df_ult[df_ult["DEP_ADM"] == dep][c]
                       for dep in deps_exibir for c in AREAS.keys()]
        fig_box_areas.update_layout(
            title=f"Distribuição das notas por área e dependência — {ano_comparacao}",
            boxmode="group",
            yaxis=dict(title="Nota",
                       range=range_dinamico(*_series_box, padding=0.05)),
            xaxis=dict(title="Área de conhecimento"),
        )
        fig_box_areas = aplicar_tema(fig_box_areas, 550)
        fig_box_areas.update_layout(
            showlegend=True,
            margin=dict(l=24, r=72, t=56, b=44),
            legend=_legenda_padrao(y_pos=1.02, font_size=11.5),
        )
        _chart(fig_box_areas)
    else:
        st.info("Nenhum ano disponível para comparação.")
# ============================================================
# ABA 4 - ESCOLAS 2024
# ============================================================
def aba_escolas_2024(df_ms_enriq_2024, ano=2024, df_br=None, df_bruta_ms=None):
    titulo_secao(
        f"Escolas estaduais em {ano}",
        "Detalhamento por unidade escolar, com nome, município e CRE."
    )

    df_est = df_ms_enriq_2024[df_ms_enriq_2024["DEP_ADM"] == "Estadual"].copy()
    if df_est.empty:
        st.warning(f"Sem dados de escolas estaduais em {ano}.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        area = st.selectbox(
            "Área para análise",
            options=list(AREAS.keys()),
            format_func=nome_area_ext,
            key="area_escola_2024",
        )
    with col_b:
        min_part = st.slider("Mínimo de participantes por escola", 3, 50, 10,
                             key="min_part_escola_2024")

    df_br_est = (
        df_br[(df_br["DEP_ADM"] == "Estadual") & (df_br["NU_ANO"] == ano)]
        if df_br is not None else None
    )
    medias_ref = calcular_medias_referencia(df_est, df_br_est, area) if df_br_est is not None else {"ms": None, "br": None}

    g = (df_est.groupby(
            ["CO_ESCOLA", "NOME_ESCOLA", "MUNICIPIO_CRES", "CRE"], dropna=False
         )[area]
         .agg(Média="mean", Mediana="median", Estudantes="count")
         .reset_index())
    g = g[g["Estudantes"] >= min_part].copy()
    g["Média"] = g["Média"].round(2)
    g["Mediana"] = g["Mediana"].round(2)
    
    g["NOME_ESCOLA"] = g["NOME_ESCOLA"].fillna("Escola sem cadastro")
    g["MUNICIPIO_CRES"] = g["MUNICIPIO_CRES"].fillna(g["CO_ESCOLA"].map(
        df_est[["CO_ESCOLA", "NO_MUNICIPIO_ESC"]].drop_duplicates(subset=["CO_ESCOLA"]).set_index("CO_ESCOLA")["NO_MUNICIPIO_ESC"]
    )).fillna("—")

    if df_bruta_ms is not None:
        bruta_est_2024 = df_bruta_ms[
            (df_bruta_ms["DEP_ADM"] == "Estadual") &
            (df_bruta_ms["NU_ANO"] == ano)
        ]
        inscritos_por_escola = (
            bruta_est_2024.groupby("CO_ESCOLA")
            .size()
            .rename("Inscritos")
            .reset_index()
        )
        g = g.merge(inscritos_por_escola, on="CO_ESCOLA", how="left")
        g["Inscritos"] = g["Inscritos"].fillna(0).astype(int)
        g["Taxa"] = (g["Estudantes"] / g["Inscritos"].replace(0, pd.NA) * 100).round(1)
    else:
        g["Inscritos"] = pd.NA
        g["Taxa"] = pd.NA

    if g.empty:
        st.info("Nenhuma escola atende ao mínimo de participantes selecionado.")
        return

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Escolas analisadas", fmt_int(len(g)))
    kpi_card(c2, "Média entre escolas", fmt_float(g["Média"].mean()))
    kpi_card(c3, "Maior média", fmt_float(g["Média"].max()), status="positivo")
    kpi_card(c4, "Menor média", fmt_float(g["Média"].min()), status="critico")

    st.markdown(" ")
    top_n = 15
    top = g.sort_values("Média", ascending=False).head(top_n)
    bot = g.sort_values("Média", ascending=True).head(top_n)

    _x_range_escolas = [0, 1000]

    col_top, col_bot = st.columns(2)
    with col_top:
        d_plot = top.copy()
        d_plot["Rótulo"] = (d_plot["NOME_ESCOLA"] + " (" +
                            d_plot["MUNICIPIO_CRES"] + ")")
        d_plot = d_plot.merge(g[["CO_ESCOLA", "Inscritos", "Taxa"]], on="CO_ESCOLA", how="left")
        _chart(fig_ranking_horizontal(
            d_plot, col_label="Rótulo", col_valor="Média",
            titulo=f"Top {top_n} — maiores médias",
            cor=COR_POSITIVO, altura=520, casas_decimais=2,
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
            d_plot, col_label="Rótulo", col_valor="Média",
            titulo=f"{top_n} menores médias",
            cor=COR_CRITICO, altura=520, casas_decimais=2,
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

    _top_ord = top.sort_values("Média", ascending=False)
    ordem_top = (
        _top_ord["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + _top_ord["MUNICIPIO_CRES"].apply(_abreviar_cidade)
    ).tolist()

    _bot_ord = bot.sort_values("Média", ascending=True)
    ordem_bot = (
        _bot_ord["NOME_ESCOLA"].apply(_abreviar_escola)
        + "<br>" + _bot_ord["MUNICIPIO_CRES"].apply(_abreviar_cidade)
    ).tolist()

    y_range_escolas = [0, 1000]

    col_box1, col_box2 = st.columns(2)
    with col_box1:
        if not dados_top.empty:
            fig_top_box = px.box(
                dados_top,
                x="Escola",
                y=area,
                points="all",
                custom_data=["NomeCompleto", "Municipio"],
                title=f"Top {top_n} — maiores notas",
                labels={"Escola": "", area: "Nota"},
                category_orders={"Escola": ordem_top}
            )
            fig_top_box.update_traces(
                marker=dict(color="#3B82F6", size=3, opacity=0.55),
                fillcolor="rgba(30,95,173,0.18)",
                line=dict(color="#1E5FAD", width=1.5),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]}<br>"
                    "Mediana: <b>%{median:.1f}</b><br>"
                    "Q1: %{q1:.1f} — Q3: %{q3:.1f}<br>"
                    "Mín: %{lowerfence:.1f} — Máx: %{upperfence:.1f}"
                    "<extra></extra>"
                ),
                selector=dict(type="box"),
            )
            _adicionar_referencias_ms_br(
                fig_top_box, medias_ref["ms"], medias_ref["br"],
                sufixo_legenda="rede estadual",
            )
            fig_top_box.update_layout(
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
                yaxis=dict(
                    range=y_range_escolas,
                    gridcolor="#EEF2F6",
                    gridwidth=1,
                    zeroline=False,
                ),
                xaxis=dict(tickangle=0, tickfont=dict(size=8), showgrid=False),
                showlegend=True,
                legend=_legenda_padrao(y_pos=-0.15, font_size=12),
                margin=dict(b=100, t=72),
                hovermode="closest"
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(aplicar_tema(fig_top_box, 420))
        else:
            st.info("Sem dados para as escolas com maiores notas.")
    with col_box2:
        if not dados_bot.empty:
            fig_bot_box = px.box(
                dados_bot,
                x="Escola",
                y=area,
                points="all",
                custom_data=["NomeCompleto", "Municipio"],
                title=f"{top_n} — menores notas",
                labels={"Escola": "", area: "Nota"},
                category_orders={"Escola": ordem_bot}
            )
            fig_bot_box.update_traces(
                marker=dict(color="#E87722", size=3, opacity=0.55),
                fillcolor="rgba(192,58,43,0.18)",
                line=dict(color="#C03A2B", width=1.5),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]}<br>"
                    "Mediana: <b>%{median:.1f}</b><br>"
                    "Q1: %{q1:.1f} — Q3: %{q3:.1f}<br>"
                    "Mín: %{lowerfence:.1f} — Máx: %{upperfence:.1f}"
                    "<extra></extra>"
                ),
                selector=dict(type="box"),
            )
            _adicionar_referencias_ms_br(
                fig_bot_box, medias_ref["ms"], medias_ref["br"],
                sufixo_legenda="rede estadual",
            )
            fig_bot_box.update_layout(
                plot_bgcolor="rgba(250,252,255,1)",
                paper_bgcolor="#FFFFFF",
                yaxis=dict(
                    range=y_range_escolas,
                    gridcolor="#EEF2F6",
                    gridwidth=1,
                    zeroline=False,
                ),
                xaxis=dict(tickangle=0, tickfont=dict(size=8), showgrid=False),
                showlegend=True,
                legend=_legenda_padrao(y_pos=-0.15, font_size=12),
                margin=dict(b=100, t=72),
                hovermode="closest"
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(aplicar_tema(fig_bot_box, 420))
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
        return (
            f"{row['NOME_ESCOLA']} ({row['MUNICIPIO_CRES']})"
            f" | Média: {row['Média']:.1f}"
            f" | N={row['Estudantes']}{taxa_str}"
        )

    opcoes_escola = g.sort_values("Média", ascending=False).copy()
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

    kc1, kc2, kc3, kc4 = st.columns(4)
    kpi_card(kc1, "Nota Média", fmt_float(escola_sel_row["Média"]),
             status="positivo" if escola_sel_row["Média"] >= (medias_ref["ms"] or 0) else "critico")
    kpi_card(kc2, "Mediana", fmt_float(escola_sel_row["Mediana"]))
    kpi_card(kc3, "Participantes válidos", fmt_int(int(escola_sel_row["Estudantes"])))
    if pd.notna(tx_val) and pd.notna(insc_val):
        kpi_card(kc4, f"Taxa de participação (de {fmt_int(int(insc_val))} inscritos)",
                 f"{tx_val:.1f}%",
                 status="positivo" if tx_val >= 75 else ("atencao" if tx_val >= 55 else "critico"))
    else:
        kpi_card(kc4, "Participantes válidos", fmt_int(int(escola_sel_row["Estudantes"])))

    df_escola = df_est[df_est["CO_ESCOLA"] == escola_sel_co].copy()
    nome_escola_display = f"{escola_sel_row['NOME_ESCOLA']} — {escola_sel_row['MUNICIPIO_CRES']}"

    if not df_escola.empty:
        medias_ms_area = {col: float(df_est[col].dropna().mean())
                          for col in COLS_NOTAS if col in df_est.columns}
        medias_br_area = {}
        if df_br_est is not None and not df_br_est.empty:
            medias_br_area = {col: float(df_br_est[col].dropna().mean())
                              for col in COLS_NOTAS if col in df_br_est.columns}

        fig_escola = go.Figure()
        for col in COLS_NOTAS:
            serie = df_escola[col].dropna()
            serie = serie[serie > 0]
            if serie.empty:
                continue
            fig_escola.add_trace(go.Box(
                y=serie.tolist(),
                name=AREAS_COMPLETO[col],
                marker_color=CORES_AREAS[col],
                line=dict(color=CORES_AREAS[col], width=2.5),
                fillcolor=_hex_rgba(CORES_AREAS[col], 0.15),
                boxmean=True,
                boxpoints="all",
                jitter=0.3,
                marker=dict(size=4, opacity=0.5),
                hovertemplate=(
                    f"<b>{AREAS_COMPLETO[col]}</b><br>"
                    "Nota: %{y:.1f}<extra></extra>"
                ),
            ))

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

        fig_escola.update_layout(
            title=f"Distribuição das notas — {nome_escola_display}",
            plot_bgcolor="rgba(250,252,255,1)",
            paper_bgcolor="#FFFFFF",
            yaxis=dict(
                range=[0, 1000], title="Nota",
                gridcolor="#EEF2F6", gridwidth=1, zeroline=False,
            ),
            xaxis=dict(title="", showgrid=False, showticklabels=False),
            showlegend=True,
            legend=_legenda_padrao(y_pos=1.02, font_size=11),
            margin=dict(b=16, t=64, l=24, r=24),
            hovermode="closest",
        )
        _chart(aplicar_tema(fig_escola, 420))
    else:
        st.info("Sem dados individuais para a escola selecionada.")

    titulo_secao("Tabela completa por escola")
    tabela = g.rename(columns={
        "NOME_ESCOLA": "Escola", "MUNICIPIO_CRES": "Município",
        "CRE": "Coordenadoria Regional",
    })[["Escola", "Município", "Coordenadoria Regional", "Estudantes", "Média", "Mediana"]]
    tabela = tabela.sort_values("Média", ascending=False)
    tabela["Coordenadoria Regional"] = tabela["Coordenadoria Regional"].fillna("—")
    st.dataframe(tabela, width="stretch", hide_index=True, height=520)

# ============================================================
# ABA 5 - TERRITORIAL (REORDENADA E CORRIGIDA)
# ============================================================
def aba_territorial(df_ms_enriq, df_filt_ms_full=None, df_br=None, dep_selecionadas=None, df_bruta_ms_enriq=None):
    if dep_selecionadas is None:
        dep_selecionadas = ["Estadual", "Federal", "Municipal", "Privada"]

    titulo_secao(
        "Análise territorial",
        "Desempenho das escolas distribuído por CRE, com evolução temporal. "
        "Escolha a dependência administrativa abaixo."
    )

    dep_escolhido = st.selectbox(
        "Dependência administrativa",
        options=dep_selecionadas,
        key="dep_territorial"
    )

    df_base = df_filt_ms_full if df_filt_ms_full is not None else df_ms_enriq
    df_dep = df_base[df_base["DEP_ADM"] == dep_escolhido].copy()

    if "CRE" not in df_dep.columns:
        df_dep["CRE"] = pd.NA

    if df_dep.empty:
        st.warning(f"Sem dados para a dependência {dep_escolhido} no recorte atual.")
        return

    area = st.selectbox(
        "Área para análise territorial",
        options=list(AREAS.keys()),
        format_func=nome_area_ext,
        key="area_territorial",
    )

    medias_ref = calcular_medias_referencia(df_dep, df_br[df_br["DEP_ADM"] == dep_escolhido] if df_br is not None else None, area) if df_br is not None else {"ms": None, "br": None}

    titulo_secao("Evolução temporal das CREs")
    cre_selecionadas = []
    lista_cres = []
    if "CRE" not in df_dep.columns or df_dep["CRE"].isna().all():
        st.info("Dados de CRE não encontrados. Verifique o arquivo CRES.")
    else:
        df_cre = df_dep.dropna(subset=["CRE"]).copy()
        lista_cres = sorted(df_cre["CRE"].unique())

    # Paleta de cores para até 12 CREs
    _PALETA_CRE = [
        AZUL_PRINCIPAL, LARANJA_DESTAQUE, COR_POSITIVO, "#9C2A26",
        AZUL_CLARO, DOURADO_MS, "#6B4A9F", COR_CRITICO,
        AZUL_ACCENT, COR_ATENCAO, COR_NEUTRO, "#2D6A4F",
    ]

    if lista_cres:
        # Calcular médias gerais para ordenar e sugerir default
        df_cre_all = df_dep.dropna(subset=["CRE"]).copy()
        ranking_cre = (df_cre_all.groupby("CRE", observed=True)[area]
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
                key="cre_territorial"
            )

        if cre_selecionadas:
            df_cre_evol = df_dep[df_dep["CRE"].isin(cre_selecionadas)].copy()
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
                            name=cre,
                            marker=dict(color=_hex_rgba(cor, 0.55), line=dict(color=cor, width=1.5)),
                            hovertemplate=f"<b>{cre}</b><br>Ano: %{{x}}<br>Média: %{{y:.2f}}<extra></extra>",
                        ))

                    # Linhas dinâmicas de referência MS e BR (média por ano)
                    anos_plot = sorted(evol["NU_ANO"].unique())
                    if df_dep is not None and not df_dep.empty:
                        media_ms_ano = (df_dep.groupby("NU_ANO", observed=True)[area]
                                        .mean().round(2).reindex(anos_plot).dropna())
                        if not media_ms_ano.empty:
                            fig_evol_cre.add_trace(go.Scatter(
                                x=media_ms_ano.index, y=media_ms_ano.values,
                                name="Média MS", mode="lines+markers+text",
                                line=dict(color=AZUL_PRINCIPAL, width=2.5, dash="dash"),
                                marker=dict(size=8, color=AZUL_PRINCIPAL),
                                text=[f"{v:.1f}" for v in media_ms_ano.values],
                                textposition="top center",
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
                                textposition="top center",
                                textfont=dict(size=12, color=COR_BRASIL, family="Arial Black"),
                                hovertemplate="<b>Média BR</b><br>Ano: %{x}<br>Média: %{y:.2f}<extra></extra>",
                            ))

                    fig_evol_cre.update_layout(
                        title=f"Evolução da média — {nome_area_ext(area)}",
                        xaxis=dict(tickmode="linear", dtick=1, title=""),
                        yaxis=dict(
                            title=dict(text="Nota", font=dict(size=14, color=TEMA["texto"])),
                            range=[300, 700],
                            tickfont=dict(size=12),
                        ),
                        hovermode="x unified",
                        barmode="group",
                        bargap=0.15,
                        bargroupgap=0.1,
                        legend=_legenda_padrao(y_pos=1.02, font_size=11),
                        margin=dict(t=80, r=120),
                        annotations=[
                            dict(
                                x=1.12, y=0.5, xref="paper", yref="paper",
                                text="Escala:<br><b>300 – 700</b>",
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
                    _chart(aplicar_tema(fig_evol_cre, 500))

                    # ----- GRÁFICO DE EVOLUÇÃO DAS TAXAS DE PARTICIPAÇÃO POR CRE -----
                    titulo_secao(
                        "Evolução da taxa de participação por CRE",
                        "Percentual de estudantes presentes nos dois dias de prova ao longo dos anos."
                    )

                    # Calcular taxas de participação por CRE e ano
                    # Inscritos: df_bruta_ms_enriq (brutos, já enriquecido com CRE)
                    # Presentes: df_dep (filtrados, presentes 2 dias, já enriquecido com CRE)
                    taxas_evol = []
                    for cre in cre_selecionadas:
                        for ano in sorted(df_dep["NU_ANO"].dropna().unique()):
                            insc = 0
                            if df_bruta_ms_enriq is not None and not df_bruta_ms_enriq.empty:
                                insc = len(df_bruta_ms_enriq[
                                    (df_bruta_ms_enriq["CRE"] == cre) &
                                    (df_bruta_ms_enriq["NU_ANO"] == ano) &
                                    (df_bruta_ms_enriq["DEP_ADM"] == dep_escolhido)
                                ])
                            part = len(df_dep[
                                (df_dep["CRE"] == cre) &
                                (df_dep["NU_ANO"] == ano)
                            ])
                            if insc > 0:
                                taxa = round(100 * part / insc, 1)
                                taxas_evol.append({
                                    "CRE": cre, "Ano": int(ano), "Taxa": taxa,
                                    "Inscritos": insc, "Presentes": part,
                                })

                    if taxas_evol:
                        df_taxas_evol = pd.DataFrame(taxas_evol)
                        fig_taxas_evol = go.Figure()
                        for idx, cre in enumerate(cre_selecionadas):
                            df_cre_taxa = df_taxas_evol[df_taxas_evol["CRE"] == cre]
                            if df_cre_taxa.empty:
                                continue
                            cor = _PALETA_CRE[idx % len(_PALETA_CRE)]
                            fig_taxas_evol.add_trace(go.Bar(
                                x=df_cre_taxa["Ano"], y=df_cre_taxa["Taxa"],
                                name=cre,
                                marker=dict(color=_hex_rgba(cor, 0.65), line=dict(color=cor, width=1.5)),
                                text=[f"{v:.1f}%" for v in df_cre_taxa["Taxa"]],
                                textposition="outside",
                                textfont=dict(size=10, color=cor,
                                              family="Source Sans 3, system-ui, sans-serif"),
                                hovertemplate=(
                                    f"<b>{cre}</b><br>"
                                    "Ano: %{x}<br>"
                                    "Taxa: %{y:.1f}%<br>"
                                    "Inscritos: %{customdata[0]}<br>"
                                    "Presentes: %{customdata[1]}"
                                    "<extra></extra>"
                                ),
                                customdata=df_cre_taxa[["Inscritos", "Presentes"]].values,
                            ))

                        # Linha de referência: taxa MS (média estadual por ano)
                        taxas_ms_ano = []
                        for ano in sorted(df_dep["NU_ANO"].dropna().unique()):
                            insc_ms = 0
                            if df_bruta_ms_enriq is not None and not df_bruta_ms_enriq.empty:
                                insc_ms = len(df_bruta_ms_enriq[
                                    (df_bruta_ms_enriq["NU_ANO"] == ano) &
                                    (df_bruta_ms_enriq["DEP_ADM"] == dep_escolhido)
                                ])
                            part_ms = len(df_dep[df_dep["NU_ANO"] == ano])
                            if insc_ms > 0:
                                taxas_ms_ano.append({
                                    "Ano": int(ano),
                                    "Taxa": round(100 * part_ms / insc_ms, 1),
                                })
                        if taxas_ms_ano:
                            df_ms_taxa = pd.DataFrame(taxas_ms_ano)
                            fig_taxas_evol.add_trace(go.Scatter(
                                x=df_ms_taxa["Ano"], y=df_ms_taxa["Taxa"],
                                name="Média MS", mode="lines+markers",
                                line=dict(color=AZUL_PRINCIPAL, width=2.5, dash="dash"),
                                marker=dict(size=8, color=AZUL_PRINCIPAL),
                                hovertemplate="<b>Média MS</b><br>Ano: %{x}<br>Taxa: %{y:.1f}%<extra></extra>",
                            ))

                        fig_taxas_evol.update_layout(
                            title="Taxa de participação por CRE — evolução temporal",
                            xaxis=dict(tickmode="linear", dtick=1, title="Ano", type="category"),
                            yaxis=dict(
                                title="Taxa (%)", range=[0, 105], ticksuffix="%",
                            ),
                            hovermode="x unified",
                            barmode="group",
                            bargap=0.15,
                            bargroupgap=0.1,
                            legend=_legenda_padrao(y_pos=1.02, font_size=11),
                            margin=dict(t=80, r=80),
                        )
                        _chart(aplicar_tema(fig_taxas_evol, 480))
                    else:
                        st.info("Dados de inscrição não disponíveis para calcular taxas de participação por CRE.")
                else:
                    st.info("Sem dados de evolução para as CREs selecionadas.")
            else:
                st.info("Sem dados de evolução temporal para as CREs selecionadas.")
        else:
            st.warning("Selecione ao menos uma CRE.")
    else:
        st.info("Nenhuma CRE encontrada nos dados.")

    st.markdown("---")
    anos_disponiveis = sorted(df_dep["NU_ANO"].unique())
    ano_opcoes = [str(ano) for ano in anos_disponiveis] + ["Todos os anos"]
    default_index = len(anos_disponiveis) - 1 if anos_disponiveis else 0
    ano_escolhido = st.selectbox(
        "Selecione o ano para análise dos municípios e CREs",
        options=ano_opcoes,
        index=default_index,
        key="ano_territorial"
    )

    if ano_escolhido == "Todos os anos":
        df_dep_filt = df_dep
        ano_ref = "Todos os anos"
    else:
        ano_ref = int(ano_escolhido)
        df_dep_filt = df_dep[df_dep["NU_ANO"] == ano_ref].copy()

    if df_dep_filt.empty:
        st.warning(f"Sem dados para o ano {ano_escolhido}.")
        return

    # Recalcular médias de referência para o ano selecionado (alinha com o primeiro gráfico)
    df_br_ano = df_br[df_br["NU_ANO"] == ano_ref] if (df_br is not None and ano_ref != "Todos os anos") else df_br
    medias_ref = calcular_medias_referencia(
        df_dep_filt,
        df_br_ano[df_br_ano["DEP_ADM"] == dep_escolhido] if df_br_ano is not None else None,
        area,
    ) if df_br is not None else {"ms": None, "br": None}

    # Gráfico de participação por CRE (barras inscritos/presentes + linha taxa)
    if lista_cres and cre_selecionadas and "CRE" in df_dep_filt.columns:
        df_part_cre = df_dep_filt[df_dep_filt["CRE"].isin(cre_selecionadas)].copy()
        if not df_part_cre.empty:
            # Presentes nos dois dias (já filtrado em df_dep_filt)
            presentes = (df_part_cre.groupby("CRE")
                         .agg(Presentes=(area, "count"))
                         .reset_index())
            # Inscritos: buscar no df_bruta_ms_enriq (dados brutos com CRE)
            if df_bruta_ms_enriq is not None and not df_bruta_ms_enriq.empty:
                df_inscritos_base = df_bruta_ms_enriq[
                    (df_bruta_ms_enriq["DEP_ADM"] == dep_escolhido) &
                    (df_bruta_ms_enriq["CRE"])
                ].copy()
                if ano_ref != "Todos os anos":
                    df_inscritos_base = df_inscritos_base[df_inscritos_base["NU_ANO"] == ano_ref]
                inscritos = (df_inscritos_base
                             .groupby("CRE")
                             .agg(Inscritos=(area, "count"))
                             .reset_index())
                part_cre = presentes.merge(inscritos, on="CRE", how="left")
            else:
                part_cre = presentes.copy()
                part_cre["Inscritos"] = part_cre["Presentes"]

            part_cre["Taxa"] = (part_cre["Presentes"] / part_cre["Inscritos"] * 100).round(1)

            if not part_cre.empty:
                titulo_secao(f"Participação por CRE ({ano_ref})")
                fig_part_cre = go.Figure()
                fig_part_cre.add_trace(go.Bar(
                    x=part_cre["CRE"], y=part_cre["Inscritos"],
                    name="Inscritos", marker_color=COR_NEUTRO,
                    hovertemplate="<b>%{x}</b><br>Inscritos: %{y}<extra></extra>",
                ))
                fig_part_cre.add_trace(go.Bar(
                    x=part_cre["CRE"], y=part_cre["Presentes"],
                    name="Presentes 2 dias", marker_color=AZUL_PRINCIPAL,
                    hovertemplate="<b>%{x}</b><br>Presentes: %{y}<extra></extra>",
                ))
                fig_part_cre.add_trace(go.Scatter(
                    x=part_cre["CRE"], y=part_cre["Taxa"],
                    name="Taxa (%)", mode="lines+markers+text",
                    line=dict(color=LARANJA_DESTAQUE, width=2.5),
                    marker=dict(size=8, color=LARANJA_DESTAQUE),
                    text=[f"{v:.1f}%" for v in part_cre["Taxa"]],
                    textposition="top center",
                    textfont=dict(size=10, color=LARANJA_DESTAQUE, family="Arial Black"),
                    yaxis="y2",
                    hovertemplate="<b>%{x}</b><br>Taxa: %{y:.1f}% <extra></extra>",
                ))
                fig_part_cre.update_layout(
                    title="",
                    xaxis=dict(title="", tickangle=0, tickfont=dict(size=10)),
                    yaxis=dict(title="Estudantes", side="left"),
                    yaxis2=dict(title="Taxa (%)", overlaying="y", side="right",
                                showgrid=False, range=[0, 105]),
                    legend=_legenda_padrao(y_pos=1.02, font_size=11),
                    margin=dict(t=80),
                    barmode="group",
                )
                _chart(aplicar_tema(fig_part_cre, 450))
        st.markdown("---")

    if lista_cres and cre_selecionadas and "CRE" in df_dep_filt.columns:
        titulo_secao(f"Desempenho por CRE ({ano_ref})")
        df_cre_filt = df_dep_filt[df_dep_filt["CRE"].isin(cre_selecionadas)].copy()
        if not df_cre_filt.empty:
            c = (df_cre_filt.groupby("CRE")[area]
                 .agg(Média="mean", Mediana="median", Estudantes="count").reset_index())
            c["Média"] = c["Média"].round(2)
            c["Mediana"] = c["Mediana"].round(2)
            c = c.sort_values("Média", ascending=False)

            col_cre_top, col_cre_bot = st.columns(2)
            with col_cre_top:
                cre_top = c.head(10).sort_values("Média", ascending=True)
                _chart(fig_ranking_horizontal(
                    cre_top, "CRE", "Média",
                    f"Top CREs — {nome_area_ext(area)}",
                    cor=AZUL_PRINCIPAL, altura=400, casas_decimais=2,
                    media_ms=medias_ref["ms"], media_br=medias_ref["br"],
                    x_range=[300, 700],
                ))
            with col_cre_bot:
                cre_bot = c.tail(10).sort_values("Média", ascending=True)
                _chart(fig_ranking_horizontal(
                    cre_bot, "CRE", "Média",
                    f"CREs com menores médias — {nome_area_ext(area)}",
                    cor=LARANJA_DESTAQUE, altura=400, casas_decimais=2,
                    media_ms=medias_ref["ms"], media_br=medias_ref["br"],
                    x_range=[300, 700],
                ))

            fig_box_cre = px.box(
                df_cre_filt,
                x="CRE",
                y=area,
                color="CRE",
                title=f"Distribuição das notas por CRE — {nome_area_ext(area)} ({ano_ref})",
                labels={"CRE": "", area: "Nota"},
                points="outliers"
            )
            fig_box_cre.update_xaxes(showticklabels=False)
            if pd.notna(medias_ref["ms"]):
                _adicionar_referencias_ms_br(
                    fig_box_cre, medias_ref["ms"], medias_ref["br"],
                    sufixo_legenda="rede estadual",
                )
            fig_box_cre.update_layout(
                yaxis=dict(range=[0, 1000]),
                xaxis=dict(tickangle=45),
                showlegend=True,
                legend=_legenda_padrao(y_pos=1.02, font_size=11.5),
                margin=dict(t=72),
            )
            st.markdown(
                _mini_legenda_medias_html(medias_ref["ms"], medias_ref["br"],
                                          sufixo="rede estadual"),
                unsafe_allow_html=True,
            )
            _chart(aplicar_tema(fig_box_cre, 450))

            st.markdown("---")
            titulo_secao(f"Tabela completa de desempenho — CREs ({ano_ref})")

            # Montar tabela com médias e medianas de TODAS as áreas de conhecimento
            # Ordem: para cada área, colocar Média e Mediana lado a lado
            agg_dict = {"Estudantes": (area, "count")}
            for col in COLS_NOTAS:
                agg_dict[f"Média {AREAS[col]}"] = (col, "mean")
                agg_dict[f"Mediana {AREAS[col]}"] = (col, "median")
            agg_dict[f"Média {AREAS['MEDIA_GERAL']}"] = ("MEDIA_GERAL", "mean")
            agg_dict[f"Mediana {AREAS['MEDIA_GERAL']}"] = ("MEDIA_GERAL", "median")

            tabela_completa = df_cre_filt.groupby("CRE").agg(**agg_dict).reset_index()

            # Arredondar colunas numéricas para 2 casas decimais
            for col in tabela_completa.columns:
                if col not in ("CRE", "Estudantes"):
                    tabela_completa[col] = tabela_completa[col].round(2)

            tabela_completa = tabela_completa.sort_values(f"Média {AREAS['MEDIA_GERAL']}", ascending=False)

            # Função para colorir células por área
            def _colorir_tabela_cres(val, col_name):
                if pd.isna(val):
                    return ""
                for key, nome in AREAS.items():
                    if nome in col_name:
                        cor = CORES_AREAS.get(key, TEMA["texto"])
                        return f"color: {cor}; font-weight: 600;"
                return ""

            styled = tabela_completa.style
            for col in tabela_completa.columns:
                if col not in ("CRE", "Estudantes"):
                    styled = styled.map(lambda v, c=col: _colorir_tabela_cres(v, c), subset=[col])

            styled = styled.format(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(x, (int, float)) and col not in ("CRE", "Estudantes") else x)

            styled = styled.set_properties(**{
                "text-align": "center",
                "font-size": "13px",
            }).set_properties(subset=["CRE"], **{
                "text-align": "left",
                "font-weight": "700",
                "color": AZUL_PRINCIPAL,
            }).set_table_styles([
                {"selector": "th", "props": [
                    ("background-color", TEMA["bg_subtle"]),
                    ("color", TEMA["texto"]),
                    ("font-weight", "700"),
                    ("font-size", "12px"),
                    ("text-align", "center"),
                    ("border-bottom", f"2px solid {TEMA['borda']}"),
                ]},
                {"selector": "td", "props": [
                    ("border-bottom", f"1px solid {TEMA['borda_sutil']}"),
                ]},
                {"selector": "tr:hover", "props": [
                    ("background-color", TEMA["insight_bg"]),
                ]},
            ])

            st.dataframe(styled, use_container_width=True, hide_index=True, height=520)
        else:
            st.info("Dados de CRE não disponíveis para o recorte selecionado.")
    else:
        st.info("Dados de CRE não disponíveis para a tabela.")

# ============================================================
# ABA 6 - MUNICÍPIOS (COM SELETOR DE DEPENDÊNCIA)
# ============================================================
def aba_municipios(df_ms_enriq, df_filt_ms_full=None, df_br=None, dep_selecionadas=None):
    if dep_selecionadas is None:
        dep_selecionadas = ["Estadual", "Federal", "Municipal", "Privada"]

    titulo_secao(
        "Análise por município",
        "Desempenho municipal com destaques, pontos de atenção e identificação da CRE."
    )

    dep_escolhido = st.selectbox(
        "Dependência administrativa",
        options=dep_selecionadas,
        key="dep_municipios"
    )

    df_base = df_filt_ms_full if df_filt_ms_full is not None else df_ms_enriq
    df_dep = df_base[df_base["DEP_ADM"] == dep_escolhido].copy()
    if "CRE" not in df_dep.columns:
        df_dep["CRE"] = pd.NA

    if df_dep.empty:
        st.warning(f"Sem dados para {dep_escolhido} no recorte.")
        return

    area = st.selectbox(
        "Área para análise municipal",
        options=list(AREAS.keys()),
        format_func=nome_area_ext,
        key="area_municipios",
    )

    medias_ref = calcular_medias_referencia(df_dep, df_br, area) if df_br is not None else {"ms": None, "br": None}

    anos_disponiveis = sorted(df_dep["NU_ANO"].unique())
    ano_opcoes = [str(ano) for ano in anos_disponiveis] + ["Todos os anos"]
    default_index = len(anos_disponiveis) - 1 if anos_disponiveis else 0
    ano_escolhido = st.selectbox(
        "Selecione o ano para análise dos municípios",
        options=ano_opcoes,
        index=default_index,
        key="ano_municipios"
    )

    if ano_escolhido == "Todos os anos":
        df_filt = df_dep
        ano_ref = "Todos os anos"
    else:
        ano_ref = int(ano_escolhido)
        df_filt = df_dep[df_dep["NU_ANO"] == ano_ref].copy()

    if df_filt.empty:
        st.warning(f"Sem dados para o ano {ano_escolhido}.")
        return

    muni_col = "MUNICIPIO_CRES"
    if muni_col not in df_filt.columns or df_filt[muni_col].isna().all():
        muni_col = "NO_MUNICIPIO_ESC"

    m = (df_filt.dropna(subset=[muni_col])
         .groupby(muni_col)[area]
         .agg(Média="mean", Mediana="median", Estudantes="count").reset_index())
    m["Média"] = m["Média"].round(2)
    m["Mediana"] = m["Mediana"].round(2)
    m = m[m["Estudantes"] >= 10].sort_values("Média", ascending=False)

    st.markdown("### Destaques")
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    if not m.empty:
        kpi_card(col_d1, "Maior média", fmt_float(m["Média"].iloc[0]),
                 m.iloc[0][muni_col][:25], status="positivo")
        kpi_card(col_d2, "Menor média", fmt_float(m["Média"].iloc[-1]),
                 m.iloc[-1][muni_col][:25], status="critico")
        idx_max_est = m["Estudantes"].idxmax()
        kpi_card(col_d3, "Mais estudantes", fmt_int(m.loc[idx_max_est, "Estudantes"]),
                 m.loc[idx_max_est, muni_col][:25])
        if medias_ref["ms"] is not None:
            n_abaixo = int((m["Média"] < medias_ref["ms"]).sum())
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
        if muni_mais_est["Média"] < medias_ref["ms"]:
            achado("atencao", "Município com maior volume está abaixo da média",
                   f"{muni_mais_est[muni_col]} tem {fmt_int(muni_mais_est['Estudantes'])} "
                   f"estudantes e média {fmt_float(muni_mais_est['Média'])} (média: {fmt_float(medias_ref['ms'])}).")
        abaixo = m[m["Média"] < medias_ref["ms"]]
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
            top15, "Município", "Média",
            f"Top 15 municípios — {nome_area_ext(area)}",
            cor=COR_POSITIVO, altura=500, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
        ))
    with col_bot:
        bot15 = m.tail(15).sort_values("Média", ascending=True).rename(columns={muni_col: "Município"})
        _chart(fig_ranking_horizontal(
            bot15, "Município", "Média",
            f"15 menores médias — {nome_area_ext(area)}",
            cor=COR_CRITICO, altura=500, casas_decimais=2,
            media_ms=medias_ref["ms"], media_br=medias_ref["br"],
        ))

    st.markdown("---")
    titulo_secao("Tabela completa — municípios")
    tabela = m.copy().rename(columns={muni_col: "Município"})
    cre_por_muni = (df_filt.dropna(subset=[muni_col, "CRE"])
                    .groupby(muni_col)["CRE"]
                    .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else pd.NA)
                    .reset_index()
                    .rename(columns={muni_col: "Município", "CRE": "CRE"}))
    tabela = tabela.merge(cre_por_muni, on="Município", how="left")
    tabela["CRE"] = tabela["CRE"].fillna("—")
    tabela = tabela[["Município", "CRE", "Estudantes", "Média", "Mediana"]]
    st.dataframe(tabela, width="stretch", hide_index=True, height=520)

# ============================================================
# ABA 8 - CONTEXTO NACIONAL (COM SELETOR DE ANO)
# ============================================================
def aba_contexto_nacional(df_br_filt, anos_sel):
    titulo_secao(
        "Panorama nacional",
        "Posicionamento entre as unidades federativas. Selecione o ano desejado."
    )

    # Seletor de ano, padrão o mais recente
    anos_validos = sorted([a for a in anos_sel if a in df_br_filt["NU_ANO"].unique()])
    if not anos_validos:
        st.warning("Nenhum ano disponível para o panorama nacional.")
        return
    ano_nac = st.selectbox(
        "Ano",
        options=anos_validos,
        index=len(anos_validos)-1,
        key="ano_nac"
    )

    df_ano = df_br_filt[df_br_filt["NU_ANO"] == ano_nac]

    c1, c2 = st.columns(2)
    with c1:
        area = st.selectbox("Área", options=list(AREAS.keys()),
                            format_func=nome_area_ext, key="area_nac")
    with c2:
        dep = st.selectbox(
            "Dependência administrativa",
            options=["Todas", "Estadual", "Federal", "Municipal", "Privada"],
            key="dep_nac",
        )
    dep_filtro = None if dep == "Todas" else dep

    _chart(fig_uf_barras(df_ano, area, dep_filtro,
                         f"Média por UF — {nome_area_ext(area)} ({dep}) — {ano_nac}"))

    col_uf = "SG_UF_ESC" if "SG_UF_ESC" in df_ano.columns else "SG_UF_PROVA"
    d = df_ano if dep_filtro is None else df_ano[df_ano["DEP_ADM"] == dep_filtro]
    g = d.groupby(col_uf)[area].agg(Média="mean", Mediana="median", Estudantes="count").reset_index()
    g = g[g[col_uf].notna() & g[col_uf].str.len().eq(2)].rename(columns={col_uf: "UF"})
    g["Média"] = g["Média"].round(2)
    g["Mediana"] = g["Mediana"].round(2)
    g = g.sort_values("Média", ascending=False).reset_index(drop=True)
    g.insert(0, "Posição", g.index + 1)

    st.dataframe(g, width="stretch", hide_index=True, height=500)

# ============================================================
# MAIN
# ============================================================
def main():
    st.markdown(
        f"""
        <div class='cab-painel'>
          <div class='titulo'>📘 Painel Analítico ENEM — Escolas Estaduais</div>
          <div class='subtitulo'>Estado de Mato Grosso do Sul • Edições 2019 a 2024 • Diagnóstico pedagógico e de participação</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_bruta = carregar_base_bruta()
    df_filtrada = carregar_base_filtrada(df_bruta)
    cres = carregar_cres()
    mapa_muni_cre = carregar_mapa_municipio_cre()

    anos_sel, dep_selecionadas = render_sidebar()

    # Exibe resumo do recorte ativo
    st.markdown(
        f"""
        <div style="background:{TEMA['bg_card']}; border:1px solid {TEMA['borda']};
            border-radius:8px; padding:10px 16px; margin-bottom:16px; display:flex; gap:24px; flex-wrap:wrap;">
          <span style="color:{TEMA['texto_secundario']};"><strong>📅 Anos:</strong> {', '.join(str(a) for a in sorted(anos_sel))}</span>
          <span style="color:{TEMA['texto_secundario']};"><strong>🏫 Dependências:</strong> {', '.join(dep_selecionadas)}</span>
          <span style="color:{TEMA['texto_secundario']};"><strong>✅</strong> Presentes 2 dias</span>
          <span style="color:{TEMA['texto_secundario']};"><strong>🎓</strong> Concluintes </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_bruta_ms = df_bruta[(df_bruta["SG_UF_ESC"] == "MS")
                           & (df_bruta["NU_ANO"].isin(anos_sel))
                           & (df_bruta["DEP_ADM"].isin(dep_selecionadas))].copy()
    df_filt_ms = df_filtrada[(df_filtrada["SG_UF_ESC"] == "MS")
                             & (df_filtrada["NU_ANO"].isin(anos_sel))
                             & (df_filtrada["DEP_ADM"].isin(dep_selecionadas))].copy()
    df_br_filt = df_filtrada[(df_filtrada["NU_ANO"].isin(anos_sel))
                             & (df_filtrada["DEP_ADM"].isin(dep_selecionadas))].copy()

    df_filt_ms_todos_anos = df_filtrada[(df_filtrada["SG_UF_ESC"] == "MS")
                                        & (df_filtrada["DEP_ADM"].isin(dep_selecionadas))].copy()
    df_filt_ms_todos_anos = aplicar_cre_por_municipio(df_filt_ms_todos_anos, mapa_muni_cre)

    # Base bruta MS enriquecida com CRE para gráficos de participação
    df_bruta_ms_enriq = enriquecer_ms(df_bruta_ms, cres, mapa_muni_cre)

    if df_filt_ms.empty:
        st.error("Nenhum participante encontrado no recorte selecionado.")
        return

    df_ms_enriq = enriquecer_ms(df_filt_ms, cres, mapa_muni_cre)
    df_ms_enriq_todos = enriquecer_ms(df_filt_ms_todos_anos, cres, mapa_muni_cre)
    
    df_ms_2024 = df_filtrada[(df_filtrada["SG_UF_ESC"] == "MS")
                             & (df_filtrada["NU_ANO"] == 2024)
                             & (df_filtrada["DEP_ADM"].isin(dep_selecionadas))].copy()
    df_ms_enriq_2024 = enriquecer_ms(df_ms_2024, cres, mapa_muni_cre)

    diag = diagnostico_estadual(df_filt_ms, df_bruta_ms, df_br_filt)

    tabs = st.tabs([
        "📊 Sumário Executivo",
        "📈 Participação",
        "🎓 Desempenho Pedagógico",
        "🏫 Escolas (2024)",
        "🗺️ Análise Territorial",
        "🏘️ Municípios",
        "🇧🇷 Panorama Nacional",
    ])

    with tabs[0]:
        aba_sumario_executivo(diag, anos_sel)
    with tabs[1]:
        aba_panorama_participacao(
            df_bruta_ms, df_filt_ms, anos_sel,
            df_bruta_ms_enriq=df_bruta_ms_enriq,
            df_filt_ms_enriq=df_ms_enriq,
            df_bruta_nacional=df_bruta,
            df_filt_nacional=df_filtrada,
        )
    with tabs[2]:
        aba_desempenho(df_filt_ms, df_br_filt)
    with tabs[3]:
        if df_ms_enriq_2024.empty:
            st.info("Para o detalhamento por escola, inclua o ano de 2024 na seleção lateral.")
        else:
            aba_escolas_2024(df_ms_enriq_2024, 2024, df_br_filt, df_bruta_ms=df_bruta_ms_enriq)
    with tabs[4]:
        aba_territorial(df_ms_enriq, df_ms_enriq_todos, df_br_filt, dep_selecionadas, df_bruta_ms_enriq=df_bruta_ms_enriq)
    with tabs[5]:
        aba_municipios(df_ms_enriq, df_ms_enriq_todos, df_br_filt, dep_selecionadas)
    with tabs[6]:
        aba_contexto_nacional(df_br_filt, anos_sel)

    st.markdown(
        "<div class='rodape'>Fonte: INEP — Microdados do ENEM. Cadastro de escolas: CRES.</div>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
    