"""Constantes visuais e de domínio — painel ENEM v15."""

from viz.chart_layout import (
    CHART_H_HUB,
    CHART_H_HUB_DELTA_ROW,
    CHART_H_HUB_EVOL,
    CHART_H_HUB_RANK,
)

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
