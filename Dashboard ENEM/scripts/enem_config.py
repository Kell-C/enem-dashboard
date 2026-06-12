"""Caminhos e constantes — pipeline ENEM MS."""
from pathlib import Path

BASE = Path(r"C:\Users\User\Documents\ENEM ANALISE - 12.06")
PARQUET = BASE / "enem_completo_2019_2024_.parquet"
CRES_XLSX = BASE / "cres.xlsx"
CONCLUINTES_XLSX = BASE / "Concluintes EM 2019 a 2024.xlsx"
PASTA_AGREGADOS = BASE / "data" / "agregados"
WEB_DATA = BASE / "web" / "data"

ANOS = list(range(2019, 2025))
COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
PRES_COLS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]
DEP_MAP = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
DEPENDENCIAS = ["Federal", "Estadual", "Municipal", "Privada"]
AREA_KEYS = ["CN", "CH", "LC", "MT", "RED"]
NOTA_MAP = {
    "CN": "NU_NOTA_CN",
    "CH": "NU_NOTA_CH",
    "LC": "NU_NOTA_LC",
    "MT": "NU_NOTA_MT",
    "RED": "NU_NOTA_REDACAO",
}

CRE_CURTO_FIX = {
    "CAMPO GRANDE": "CG Metrop.",
    "CG METROPOLITANA": "CG Metrop.",
    "CORUMBA": "Corumbá",
    "NAVIRAI": "Naviraí",
    "PARANAIBA": "Paranaíba",
    "PONTA PORA": "Ponta Porã",
    "TRES LAGOAS": "Três Lagoas",
    "NOVA ANDRADINA": "Nova Andradina",
}
