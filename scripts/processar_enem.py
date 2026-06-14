"""
Processamento dos microdados ENEM 2019-2024 para parquet consolidado.

Regimes:
  2019-2023: PARTICIPANTES (NU_INSCRICAO, TP_ST_CONCLUSAO, sem CO_ESCOLA)
  2024:      RESULTADOS (NU_SEQUENCIAL, CO_ESCOLA, sem TP_ST_CONCLUSAO)

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

from enem_config import PASTA_BRUTOS, PASTA_DADOS, PARQUET, WEB_DATA, configure_logging

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

COLS_2024 = [
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


def _padronizar_2024(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "NU_ANO" not in df.columns:
        df["NU_ANO"] = 2024
    df["NU_INSCRICAO"] = pd.NA
    df["TP_ST_CONCLUSAO"] = pd.NA
    df["IN_TREINEIRO"] = pd.NA
    if "CO_ESCOLA" in df.columns:
        df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")
    return df


def processar_2019_2023() -> pd.DataFrame | None:
    logger.info("%s", "=" * 70)
    logger.info("2019-2023 - PARTICIPANTES (todos os estados)")
    logger.info("%s", "=" * 70)

    arquivos: list[tuple[int, str]] = []
    for ano in range(2019, 2024):
        pasta = PASTA_BRUTOS / str(ano)
        if not pasta.is_dir():
            logger.warning("Pasta ausente: %s", pasta)
            continue
        matches = glob.glob(str(pasta / f"*{ano}*.csv"))
        if matches:
            arquivos.append((ano, matches[0]))
            logger.info("[ok] %s: %s", ano, os.path.basename(matches[0]))
        else:
            logger.warning("%s: CSV nao encontrado", ano)

    if not arquivos:
        return None

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
    out = PASTA_DADOS / "2019_2023" / "enem_completo_2019_2023_.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    logger.info("[salvo] %s (%s linhas)", out, len(df))
    return df


def processar_2024_resultados() -> pd.DataFrame | None:
    logger.info("%s", "=" * 70)
    logger.info("2024 - RESULTADOS (sem merge com PARTICIPANTES)")
    logger.info("%s", "=" * 70)

    pasta = PASTA_BRUTOS / "2024"
    if not pasta.is_dir():
        logger.error("Pasta ausente: %s", pasta)
        return None

    caminho = None
    for nome in ("RESULTADOS_2024.csv", "resultados_2024.csv"):
        p = pasta / nome
        if p.exists():
            caminho = p
            break
    if caminho is None:
        logger.error("RESULTADOS_2024.csv nao encontrado")
        return None

    sep = detectar_separador(str(caminho))
    if sep is None:
        logger.error("Separador nao detectado")
        return None

    cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
    cols_ler = [c for c in COLS_2024 if c in cols_reais]
    logger.info("%s: %s/%s colunas", caminho.name, len(cols_ler), len(COLS_2024))

    chunks: list[pd.DataFrame] = []
    for i, chunk in enumerate(
        pd.read_csv(caminho, sep=sep, encoding="latin-1", usecols=cols_ler, chunksize=CHUNK_SIZE, low_memory=False)
    ):
        chunk = tratar_notas(chunk)
        chunk = _padronizar_2024(chunk)
        chunks.append(chunk)
        logger.info("chunk %s: %s linhas", i + 1, len(chunk))
    logger.info("")

    if not chunks:
        return None

    df = pd.concat(chunks, ignore_index=True)
    com_escola = df["CO_ESCOLA"].notna().sum() if "CO_ESCOLA" in df.columns else 0
    logger.info("[ok] 2024: %s registros (%s com CO_ESCOLA)", len(df), com_escola)

    out = PASTA_DADOS / "2024" / "enem_resultados_2024_.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    logger.info("[salvo] %s", out)
    return df


def consolidar(df_hist: pd.DataFrame | None, df_2024: pd.DataFrame | None) -> None:
    bases = [b for b in (df_hist, df_2024) if b is not None]
    if not bases:
        logger.error("Nenhuma base para consolidar")
        return

    logger.info("%s", "=" * 70)
    logger.info("CONSOLIDACAO 2019-2024")
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
    df_2024 = processar_2024_resultados()
    consolidar(df_hist, df_2024)

    logger.info("Tempo: %.1f min", (time.time() - t0) / 60)
    logger.info("%s", "=" * 70)


if __name__ == "__main__":
    main()
