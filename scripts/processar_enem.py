"""
Processamento dos microdados ENEM 2019-2025 para parquet consolidado.

Regimes:
  2019-2023: PARTICIPANTES (NU_INSCRICAO, TP_ST_CONCLUSAO, sem CO_ESCOLA)
  2024+:     RESULTADOS (NU_SEQUENCIAL, CO_ESCOLA, sem TP_ST_CONCLUSAO)

Saida em pipeline_dashboard/dados/ (nao altera dados_processados/ legado).
"""
from __future__ import annotations

import glob
import os
import time
import json
import logging
import datetime

import pandas as pd

from enem_config import ANOS, ANO_FINAL, PASTA_BRUTOS, PASTA_DADOS, PARQUET, WEB_DATA, configure_logging

logger = configure_logging(__name__)

CHUNK_SIZE = 500_000

COLS_2019_2023 = [
    "NU_ANO",
    "NU_INSCRICAO",
    "TP_ST_CONCLUSAO",
    "IN_TREINEIRO",
    "TP_PRESENCA_CN",
    "TP_PRESENCA_CH",
    "TP_PRESENCA_LC",
    "TP_PRESENCA_MT",
    "NU_NOTA_CN",
    "NU_NOTA_CH",
    "NU_NOTA_LC",
    "NU_NOTA_MT",
    "NU_NOTA_REDACAO",
    "TP_STATUS_REDACAO",
    "SG_UF_ESC",
    "NO_MUNICIPIO_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
]

COLS_RESULTADOS = [
    "NU_SEQUENCIAL",
    "NU_ANO",
    "CO_ESCOLA",
    "NO_MUNICIPIO_ESC",
    "SG_UF_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
    "TP_PRESENCA_CN",
    "TP_PRESENCA_CH",
    "TP_PRESENCA_LC",
    "TP_PRESENCA_MT",
    "NU_NOTA_CN",
    "NU_NOTA_CH",
    "NU_NOTA_LC",
    "NU_NOTA_MT",
    "NU_NOTA_REDACAO",
    "TP_STATUS_REDACAO",
]


def tratar_notas(df: pd.DataFrame) -> pd.DataFrame:
    for prova in ("CN", "CH", "LC", "MT"):
        col_p = f"TP_PRESENCA_{prova}"
        col_n = f"NU_NOTA_{prova}"
        if col_p in df.columns and col_n in df.columns:
            df.loc[df[col_p] != 1, col_n] = pd.NA
    if "TP_STATUS_REDACAO" in df.columns and "NU_NOTA_REDACAO" in df.columns:
        df.loc[df["TP_STATUS_REDACAO"] == 2, "NU_NOTA_REDACAO"] = pd.NA
    return df


def detectar_separador(caminho: str, encoding: str = "latin-1") -> str | None:
    for sep in (";", ","):
        try:
            pd.read_csv(caminho, sep=sep, encoding=encoding, nrows=0)
            return sep
        except Exception:
            continue
    return None


def _padronizar_historico(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    df = df.copy()
    if "NU_ANO" not in df.columns:
        df["NU_ANO"] = ano
    df["NU_SEQUENCIAL"] = pd.NA
    df["CO_ESCOLA"] = pd.NA
    return df


def _padronizar_resultados(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    df = df.copy()
    if "NU_ANO" not in df.columns:
        df["NU_ANO"] = ano
    df["NU_INSCRICAO"] = pd.NA
    df["TP_ST_CONCLUSAO"] = pd.NA
    df["IN_TREINEIRO"] = pd.NA
    if "CO_ESCOLA" in df.columns:
        df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")
    return df


def _ler_cache(path, label: str) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    logger.info("[cache] %s: %s (%s linhas)", label, path, len(df))
    return df


def _buscar_csv_ano(ano: int, nomes: tuple[str, ...]) -> Path | None:
    pasta = PASTA_BRUTOS / str(ano)
    candidatos = []
    for nome in nomes:
        candidatos.extend([
            pasta / nome,
            pasta / "DADOS" / nome,
            pasta / nome.lower(),
            pasta / "DADOS" / nome.lower(),
        ])
    for path in candidatos:
        if path.exists():
            return path
    return None


def processar_2019_2023() -> pd.DataFrame | None:
    logger.info("%s", "=" * 70)
    logger.info("2019-2023 - PARTICIPANTES (todos os estados)")
    logger.info("%s", "=" * 70)

    cache = PASTA_DADOS / "2019_2023" / "enem_completo_2019_2023_.parquet"

    arquivos: list[tuple[int, str]] = []
    for ano in range(2019, 2024):
        caminho = _buscar_csv_ano(ano, (f"MICRODADOS_ENEM_{ano}.csv", f"PARTICIPANTES_{ano}.csv"))
        if caminho is None:
            logger.warning("%s: CSV nao encontrado nos brutos", ano)
            continue
        arquivos.append((ano, str(caminho)))
        logger.info("[ok] %s: %s", ano, os.path.basename(caminho))

    if not arquivos:
        return _ler_cache(cache, "historico 2019-2023")

    partes: list[pd.DataFrame] = []
    for ano, caminho in arquivos:
        sep = detectar_separador(caminho)
        if sep is None:
            logger.error("Separador nao detectado: %s", caminho)
            continue
        cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
        cols_ler = [c for c in COLS_2019_2023 if c in cols_reais]
        logger.info("%s: %s/%s colunas", ano, len(cols_ler), len(COLS_2019_2023))

        chunks: list[pd.DataFrame] = []
        for i, chunk in enumerate(
            pd.read_csv(caminho, sep=sep, encoding="latin-1", usecols=cols_ler, chunksize=CHUNK_SIZE, low_memory=False)
        ):
            chunk = tratar_notas(chunk)
            chunk = _padronizar_historico(chunk, ano)
            chunks.append(chunk)
            logger.info("chunk %s: %s linhas", i + 1, len(chunk))
        logger.info("")
        if chunks:
            df_ano = pd.concat(chunks, ignore_index=True)
            logger.info("[ok] %s: %s registros", ano, len(df_ano))
            partes.append(df_ano)

    if not partes:
        return None

    df = pd.concat(partes, ignore_index=True, sort=False)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    logger.info("[salvo] %s (%s linhas)", cache, len(df))
    return df


def processar_resultados_ano(ano: int) -> pd.DataFrame | None:
    logger.info("%s", "=" * 70)
    logger.info("%s - RESULTADOS (sem merge com PARTICIPANTES)", ano)
    logger.info("%s", "=" * 70)

    cache = PASTA_DADOS / str(ano) / f"enem_resultados_{ano}_.parquet"
    caminho = _buscar_csv_ano(ano, (f"RESULTADOS_{ano}.csv",))

    if caminho is None:
        logger.warning("RESULTADOS_%s.csv nao encontrado nos brutos", ano)
        return _ler_cache(cache, f"resultados {ano}")

    sep = detectar_separador(str(caminho))
    if sep is None:
        logger.error("Separador nao detectado")
        return None

    cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
    cols_ler = [c for c in COLS_RESULTADOS if c in cols_reais]
    logger.info("%s: %s/%s colunas", caminho.name, len(cols_ler), len(COLS_RESULTADOS))

    chunks: list[pd.DataFrame] = []
    for i, chunk in enumerate(
        pd.read_csv(caminho, sep=sep, encoding="latin-1", usecols=cols_ler, chunksize=CHUNK_SIZE, low_memory=False)
    ):
        chunk = tratar_notas(chunk)
        chunk = _padronizar_resultados(chunk, ano)
        chunks.append(chunk)
        logger.info("chunk %s: %s linhas", i + 1, len(chunk))
    logger.info("")

    if not chunks:
        return None

    df = pd.concat(chunks, ignore_index=True)
    com_escola = df["CO_ESCOLA"].notna().sum() if "CO_ESCOLA" in df.columns else 0
    logger.info("[ok] %s: %s registros (%s com CO_ESCOLA)", ano, len(df), com_escola)

    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    logger.info("[salvo] %s", cache)
    return df


def consolidar(*partes: pd.DataFrame | None) -> None:
    bases = [b for b in partes if b is not None]
    if not bases:
        logger.error("Nenhuma base para consolidar")
        return

    logger.info("%s", "=" * 70)
    logger.info("CONSOLIDACAO %s-%s", ANOS[0], ANO_FINAL)
    logger.info("%s", "=" * 70)
    for b in bases:
        anos = sorted(b["NU_ANO"].dropna().unique())
        logger.info("bloco anos %s: %s linhas", list(anos), len(b))

    df_final = pd.concat(bases, ignore_index=True, sort=False)
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    df_final.to_parquet(PARQUET, index=False)
    logger.info("[salvo] Consolidado: %s", PARQUET)
    logger.info("Total: %s registros", len(df_final))
    logger.info("Colunas: %s", list(df_final.columns))
    # Escrever metadados básicos para o frontend / auditoria
    try:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        meta = {
            "script": "processar_enem.py",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "parquet": str(PARQUET),
            "total_rows": int(len(df_final)),
        }
        meta_path = WEB_DATA / "meta_processar_enem.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        logger.info("[meta] gravado: %s", meta_path)
    except Exception as e:
        logger.warning("[aviso] nao foi possivel gravar meta: %s", e)


def main():
    t0 = time.time()
    logger.info("%s", "=" * 70)
    logger.info("ETL ENEM -> pipeline_dashboard/dados/")
    logger.info("%s", "=" * 70)

    df_hist = processar_2019_2023()
    resultados = [processar_resultados_ano(ano) for ano in ANOS if ano >= 2024]
    consolidar(df_hist, *resultados)

    logger.info("Tempo: %.1f min", (time.time() - t0) / 60)
    logger.info("%s", "=" * 70)


if __name__ == "__main__":
    main()
