"""
Le microdados INEP individuais (2013-2018) em chunks a partir do CSV local.

2016-2018 nao trazem CO_ESCOLA no arquivo publico; 2013-2015 trazem.
Serve para integridade (eliminados) e, quando aplicavel, participacao agregada.
"""
from __future__ import annotations

import logging

import pandas as pd

from enem_config import COLS_NOTAS, PASTA_BRUTOS, PASTA_DADOS, PRES_COLS
from enem_helpers import limpar, preparar_ano
from processar_enem import (
    CHUNK_SIZE,
    COL_ALIASES,
    NOMES_CSV_PARTICIPANTES,
    _aplicar_aliases,
    _buscar_csv_ano,
    detectar_separador,
    tratar_notas,
)

logger = logging.getLogger(__name__)

ANOS_INEP_CSV = list(range(2013, 2019))
CACHE_DIR = PASTA_DADOS / "inep_individual_cache"

COLS_LER = [
    "NU_ANO",
    "NU_INSCRICAO",
    "TP_ST_CONCLUSAO",
    "SG_UF_ESC",
    "NO_MUNICIPIO_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
    *PRES_COLS,
    "TP_STATUS_REDACAO",
    *COLS_NOTAS,
]


def _cols_disponiveis(cols_reais: list[str]) -> list[str]:
    ren = {k: v for k, v in COL_ALIASES.items() if k in cols_reais}
    normalizadas = [ren.get(c, c) for c in cols_reais]
    return [c for c in COLS_LER if c in normalizadas]


def _manter_linha(chunk: pd.DataFrame) -> pd.Series:
    """MS (todas as redes) + rede estadual nacional (Brasil-Estadual)."""
    ms = chunk["SG_UF_ESC"].astype(str).str.upper().eq("MS")
    est = pd.to_numeric(chunk["TP_DEPENDENCIA_ADM_ESC"], errors="coerce").eq(2)
    return ms | est


def _cache_path(ano: int):
    return CACHE_DIR / f"enem_inep_{ano}_filtrado.parquet"


def ler_ano_inep_csv(ano: int, force_csv: bool = False) -> pd.DataFrame:
    if ano not in ANOS_INEP_CSV:
        raise ValueError(f"Ano {ano} fora do escopo INEP CSV ({ANOS_INEP_CSV})")

    cache = _cache_path(ano)
    if cache.exists() and not force_csv:
        df = pd.read_parquet(cache)
        logger.info("[cache] %s: %s linhas (%s)", ano, len(df), cache)
        return preparar_ano(df)

    nomes = tuple(n.format(ano=ano) for n in NOMES_CSV_PARTICIPANTES)
    caminho = _buscar_csv_ano(ano, nomes)
    if caminho is None:
        logger.warning("%s: CSV INEP nao encontrado em %s", ano, PASTA_BRUTOS / str(ano))
        return pd.DataFrame()

    sep = detectar_separador(str(caminho))
    if sep is None:
        logger.error("Separador nao detectado: %s", caminho)
        return pd.DataFrame()

    cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
    cols_reais = _aplicar_aliases(pd.DataFrame(columns=cols_reais)).columns.tolist()
    cols_ok = _cols_disponiveis(cols_reais)
    usecols = [c for c in cols_reais if c in cols_ok]
    if "NU_INSCRICAO" not in cols_ok:
        logger.error("%s: NU_INSCRICAO ausente (%s)", ano, caminho)
        return pd.DataFrame()

    logger.info("%s: lendo CSV INEP %s (%s colunas)", ano, caminho.name, len(cols_ok))
    partes: list[pd.DataFrame] = []
    total_lido = 0
    total_mantido = 0

    for i, chunk in enumerate(
        pd.read_csv(
            caminho,
            sep=sep,
            encoding="latin-1",
            usecols=usecols,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        )
    ):
        chunk = _aplicar_aliases(chunk)
        total_lido += len(chunk)
        mask = _manter_linha(chunk)
        chunk = chunk.loc[mask].copy()
        total_mantido += len(chunk)
        if chunk.empty:
            continue
        if "NU_ANO" not in chunk.columns:
            chunk["NU_ANO"] = ano
        chunk = tratar_notas(chunk)
        chunk["CO_ESCOLA"] = pd.NA
        chunk["NU_SEQUENCIAL"] = pd.NA
        partes.append(chunk)
        if (i + 1) % 5 == 0:
            logger.info("  chunk %s: lidos %s, mantidos %s", i + 1, total_lido, total_mantido)

    if not partes:
        logger.warning("%s: nenhum registro apos filtro MS/estadual", ano)
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    limpar()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    logger.info("[cache] gravado %s (%s linhas)", cache, len(df))
    logger.info(
        "[ok] %s CSV: %s registros (de %s; MS+estadual BR)",
        ano,
        len(df),
        total_lido,
    )
    return preparar_ano(df)


def csv_disponivel(ano: int) -> bool:
    if ano not in ANOS_INEP_CSV:
        return False
    if _cache_path(ano).exists():
        return True
    nomes = tuple(n.format(ano=ano) for n in NOMES_CSV_PARTICIPANTES)
    return _buscar_csv_ano(ano, nomes) is not None
