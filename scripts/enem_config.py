"""Caminhos e constantes - pipeline ENEM MS (pasta pipeline_dashboard)."""
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_ROOT.parent

PASTA_BRUTOS = REPO_ROOT / "dados_brutos"
PASTA_DADOS = PIPELINE_ROOT / "dados"
PARQUET = PASTA_DADOS / "enem_completo_2019_2024_.parquet"
PASTA_AGREGADOS = PASTA_DADOS / "agregados"
WEB_DATA = PIPELINE_ROOT / "web" / "data"

AUX = PIPELINE_ROOT / "auxiliar"
CRES_XLSX = AUX / "cres.xlsx"
CONCLUINTES_XLSX = AUX / "Concluintes EM 2019 a 2024.xlsx"
CONCLUINTES_CSV = REPO_ROOT / "dados_processados" / "concluintes_3ano_ms_2019_2024.csv"

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
    "CORUMBA": "Corumb\u00e1",
    "NAVIRAI": "Navira\u00ed",
    "PARANAIBA": "Parana\u00edba",
    "PONTA PORA": "Ponta Por\u00e3",
    "TRES LAGOAS": "Tr\u00eas Lagoas",
    "NOVA ANDRADINA": "Nova Andradina",
}
