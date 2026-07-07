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

ANOS = list(range(2013, 2026))
ANO_INICIAL = ANOS[0]
ANO_FINAL = ANOS[-1]
# INEP MICRODADOS_ENEM_ESCOLA.csv — no painel usamos so 2013-2015 (matriculados/participantes/taxa).
ANOS_ESCOLA_INEP = list(range(2005, 2016))
ANOS_ESCOLA_PAINEL = [2013, 2014, 2015]
# Microdado INEP no parquet: 2013-2018 (com CO_ESCOLA) + 2019+ (sem escola 2019-2023).
ANOS_MICRO_HISTORICO = [2013, 2014, 2015]
ANOS_MICRO_INDIVIDUAIS = list(range(2013, 2019)) + list(range(2019, 2026))
ANOS_MICRODADOS = ANOS_MICRO_INDIVIDUAIS
# Anos sem microdado individual no parquet (fallback AIO, se necessario).
ANOS_EXTENSAO_AIO = [a for a in ANOS if a not in ANOS_MICRODADOS]
ANO_MICRO_INICIAL = ANOS_MICRODADOS[0]
ANOS_COM_CO_ESCOLA = list(range(2013, 2019))

# Paths com valores default, podem ser sobrescritos por variáveis de ambiente
# Prioriza a pasta `dados/` do próprio repositório, onde estão os microdados 2025.
_dados_default = PIPELINE_ROOT / "dados"
_brutos_legacy = REPO_ROOT / "dados_brutos"
PASTA_DADOS = Path(os.getenv('PASTA_DADOS', _dados_default))
PASTA_BRUTOS = Path(os.getenv('PASTA_BRUTOS', _dados_default if _dados_default.exists() else _brutos_legacy))
CSV_ESCOLA_HISTORICO = Path(
    os.getenv(
        "CSV_ESCOLA_HISTORICO",
        PASTA_DADOS / "2005_2015" / "microdados_enem_por_escola (1)" / "DADOS" / "MICRODADOS_ENEM_ESCOLA.csv",
    )
)
PARQUET_ESCOLA_HISTORICO = PASTA_DADOS / "enem_escola_historico.parquet"
PARQUET = PASTA_DADOS / f"enem_completo_{ANO_MICRO_INICIAL}_{ANO_FINAL}_.parquet"
PARQUET_LEGADO = PASTA_DADOS / f"enem_completo_2019_{ANO_FINAL}_.parquet"


def resolver_parquet() -> Path:
    """Retorna o parquet consolidado existente ou o caminho padrao de escrita."""
    for path in (PARQUET, PARQUET_LEGADO):
        if path.exists():
            return path
    return PARQUET
PASTA_AGREGADOS = Path(os.getenv('PASTA_AGREGADOS', PASTA_DADOS / "agregados"))
# WEB_DATA: onde os assets do frontend são escritos (docs/data)
WEB_DATA = Path(os.getenv('WEB_DATA', PIPELINE_ROOT / "docs" / "data"))

AUX = PIPELINE_ROOT / "auxiliar"
CRES_XLSX = AUX / "cres.xlsx"
# Planilha SED de matrícula: nome fixo 2019+ (não acompanha ANO_MICRO_INICIAL).
CONCLUINTES_ANO_PLANILHA = 2019


def resolver_concluintes_xlsx() -> Path:
    candidatos: list[Path] = []
    env = os.getenv("CONCLUINTES_XLSX")
    if env:
        candidatos.append(Path(env))
    candidatos.extend([
        PASTA_DADOS / f"Concluintes EM {CONCLUINTES_ANO_PLANILHA} a {ANO_FINAL}.xlsx",
        PASTA_DADOS / f"Concluintes EM {ANO_MICRO_INICIAL} a {ANO_FINAL}.xlsx",
        REPO_ROOT / "dados_processados" / f"Concluintes EM {CONCLUINTES_ANO_PLANILHA} a {ANO_FINAL}.xlsx",
    ])
    for path in candidatos:
        if path.exists():
            return path
    return candidatos[0]


CONCLUINTES_XLSX = resolver_concluintes_xlsx()
CONCLUINTES_CSV = Path(
    os.getenv(
        'CONCLUINTES_CSV',
        REPO_ROOT / "dados_processados" / f"concluintes_3ano_ms_{CONCLUINTES_ANO_PLANILHA}_{ANO_FINAL}.csv",
    )
)
COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
PRES_COLS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]

# População de referência do painel (textos exibidos no frontend)
# Escopo padrão: estudantes de escolas estaduais (TP_DEPENDENCIA_ADM_ESC = 2).
# Exceção: abas/seções de comparação entre redes (Estadual, Municipal, Federal, Privada).
REDE_REFERENCIA = "Estadual"
BRASIL_REFERENCIA = "Brasil-Estadual"
REDES_COMPARACAO_MS = ["Estadual", "Municipal", "Federal", "Privada"]
POP_REF_RESUMO = (
    "Participantes de escolas estaduais que concluíram a prova em ao menos uma área objetiva "
    "(TP_PRESENCA = 1 em CN, CH, LC ou MT), excluindo eliminados."
)
POP_REF_PARTICIPANTES = (
    "Estudantes de escolas estaduais (TP_DEPENDENCIA_ADM = 2) na população de referência: "
    "concluintes do recorte + presentes em ≥1 área objetiva, "
    "sem eliminação objetiva (TP_PRESENCA = 2) nem na redação (TP_STATUS_REDACAO = 2, anulada). "
    "Redação em branco (TP_STATUS_REDACAO = 4) permanece na população."
)
DEP_MAP = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
DEPENDENCIAS = list(REDES_COMPARACAO_MS)
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
