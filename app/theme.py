"""Constantes visuais e de domínio do dashboard."""

TEMA = {
    "bg_app": "#DCE3EC",
    "bg_principal": "#FFFFFF",
    "bg_card": "#FFFFFF",
    "bg_secundario": "#F8F9FA",
    "bg_subtle": "#E8EDF3",
    "insight_bg": "#F1F5F9",
    "texto": "#0F172A",
    "texto_secundario": "#334155",
    "texto_muted": "#475569",
    "borda": "#B8C4D4",
}

AZUL_SED = "#1B7FD6"
AZUL_PRINCIPAL = "#0A4D8C"
AZUL_CLARO = "#3BA4E8"
AZUL_ESCURO = "#053B71"
VERDE_MS = "#2EAD6E"
LARANJA_DESTAQUE = "#F07A28"
DOURADO_MS = "#F2C230"

COR_POSITIVO = VERDE_MS
COR_ATENCAO = "#E8A317"
COR_CRITICO = "#D6453D"
COR_NEUTRO = "#5C6B7E"
COR_BRASIL = "#7B8794"
COR_TEXTO_BARRA = "#0A4A32"

DEPENDENCIAS = ["Federal", "Estadual", "Municipal", "Privada"]
ORDEM_DEP = ["Estadual", "Federal", "Municipal", "Privada"]
DEP_PADRAO = "Estadual"

COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]

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
    "NU_NOTA_LC": "Linguagens",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}

CORES_AREAS = {
    "MEDIA_GERAL": COR_NEUTRO,
    "NU_NOTA_CN": COR_POSITIVO,
    "NU_NOTA_CH": LARANJA_DESTAQUE,
    "NU_NOTA_LC": AZUL_PRINCIPAL,
    "NU_NOTA_MT": COR_CRITICO,
    "NU_NOTA_REDACAO": DOURADO_MS,
}

CORES_DEP = {
    "Estadual": AZUL_PRINCIPAL,
    "Federal": "#9C2A26",
    "Municipal": DOURADO_MS,
    "Privada": "#6B4A9F",
}

COLS_MEDIA_MS_SUMARIO = [
    "media_nu_nota_cn", "media_nu_nota_ch", "media_nu_nota_lc",
    "media_nu_nota_mt", "media_nu_nota_redacao", "media_media_geral",
]
COLS_MEDIA_BR_SUMARIO = [
    "media_br_nu_nota_cn", "media_br_nu_nota_ch", "media_br_nu_nota_lc",
    "media_br_nu_nota_mt", "media_br_nu_nota_redacao", "media_br_media_geral",
]
NOMES_AREAS_SUMARIO = ["CN", "CH", "LC", "Mat.", "Redação", "Média Geral"]

NIVEL_ESTADO = "estado"
NIVEL_CRE = "cre"
NIVEL_MUNICIPIO = "municipio"
NIVEL_ESCOLA = "escola"
NIVEIS_TERRITORIO = (NIVEL_ESTADO, NIVEL_CRE, NIVEL_MUNICIPIO, NIVEL_ESCOLA)

NIVEL_LABELS = {
    NIVEL_ESTADO: "Estado (visão CREs)",
    NIVEL_CRE: "CRE",
    NIVEL_MUNICIPIO: "Município",
    NIVEL_ESCOLA: "Escola (2024)",
}

HUB_COL_LAYOUT = [1, 1, 1]
