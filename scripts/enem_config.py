"""Caminhos e constantes - pipeline ENEM MS (pasta pipeline_dashboard)."""
from pathlib import Path
import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(name: str = __name__, level: str | int | None = None) -> logging.Logger:
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    if isinstance(log_level, str):
        log_level = log_level.upper()
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
        force=True,
    )
    return logging.getLogger(name)

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DASHBOARD = PIPELINE_ROOT.parent
REPO_ROOT = PIPELINE_DASHBOARD.parent

ANOS = list(range(2019, 2026))
ANO_INICIAL = ANOS[0]
ANO_FINAL = ANOS[-1]

# Paths com valores default, podem ser sobrescritos por variáveis de ambiente
# Prioriza a pasta `dados/` do próprio repositório, onde estão os microdados 2025.
_dados_default = PIPELINE_ROOT / "dados"
_brutos_legacy = REPO_ROOT / "dados_brutos"
PASTA_DADOS = Path(os.getenv('PASTA_DADOS', _dados_default))
PASTA_BRUTOS = Path(os.getenv('PASTA_BRUTOS', _dados_default if _dados_default.exists() else _brutos_legacy))
PARQUET = PASTA_DADOS / f"enem_completo_{ANO_INICIAL}_{ANO_FINAL}_.parquet"
PASTA_AGREGADOS = Path(os.getenv('PASTA_AGREGADOS', PASTA_DADOS / "agregados"))
# WEB_DATA: onde os assets do frontend são escritos (docs/data)
WEB_DATA = Path(os.getenv('WEB_DATA', PIPELINE_ROOT / "docs" / "data"))

AUX = PIPELINE_ROOT / "auxiliar"
CRES_XLSX = AUX / "cres.xlsx"
CONCLUINTES_XLSX = Path(
    os.getenv(
        'CONCLUINTES_XLSX',
        PASTA_DADOS / f"Concluintes EM {ANO_INICIAL} a {ANO_FINAL}.xlsx",
    )
)
CONCLUINTES_CSV = Path(
    os.getenv(
        'CONCLUINTES_CSV',
        REPO_ROOT / "dados_processados" / f"concluintes_3ano_ms_{ANO_INICIAL}_{ANO_FINAL}.csv",
    )
)
COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
PRES_COLS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]

# População de referência do painel (textos exibidos no frontend)
POP_REF_RESUMO = (
    "Participantes que concluíram a prova em ao menos uma área objetiva "
    "(TP_PRESENCA = 1 em CN, CH, LC ou MT), excluindo eliminados."
)
POP_REF_PARTICIPANTES = (
    "Concluintes do recorte + presentes em ≥1 área objetiva, "
    "sem eliminação objetiva (TP_PRESENCA = 2) nem na redação (TP_STATUS = 2)."
)
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
