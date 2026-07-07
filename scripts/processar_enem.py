"""
Processamento dos microdados ENEM para parquet consolidado.

Regimes:
  2013-2018: PARTICIPANTES (NU_INSCRICAO, CO_ESCOLA, TP_ST_CONCLUSAO)
  2019-2023: PARTICIPANTES (sem CO_ESCOLA no INEP)
  2024+:     RESULTADOS (NU_SEQUENCIAL, CO_ESCOLA, sem TP_ST_CONCLUSAO)

Saida em dados/enem_completo_{ano_inicial}_{ano_final}_.parquet.

Uso:
  python processar_enem.py                    # pipeline completo
  python processar_enem.py --anos 2013 2014 2015  # so historico 2013-2015
"""
from __future__ import annotations

import argparse
import os
import time
import json
import logging
import datetime
from pathlib import Path

import pandas as pd

from enem_config import (
    ANOS,
    ANO_FINAL,
    ANO_INICIAL,
    ANOS_COM_CO_ESCOLA,
    ANOS_MICRODADOS,
    ANOS_MICRO_HISTORICO,
    PASTA_BRUTOS,
    PASTA_DADOS,
    PARQUET,
    PARQUET_LEGADO,
    WEB_DATA,
    configure_logging,
    resolver_parquet,
)

logger = configure_logging(__name__)

CHUNK_SIZE = 500_000

# Aliases de colunas em edicoes antigas do INEP (2013-2015).
COL_ALIASES = {
    "SG_UF_ESCOLA": "SG_UF_ESC",
    "NO_MUNICIPIO_ESCOLA": "NO_MUNICIPIO_ESC",
    "TP_DEPENDENCIA_ADM": "TP_DEPENDENCIA_ADM_ESC",
}

COLS_PARTICIPANTES = [
    "NU_ANO",
    "NU_INSCRICAO",
    "CO_ESCOLA",
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

NOMES_CSV_PARTICIPANTES = (
    "MICRODADOS_ENEM_{ano}.csv",
    "PARTICIPANTES_{ano}.csv",
    "microdados_enem_{ano}.csv",
)


def tratar_notas(df: pd.DataFrame) -> pd.DataFrame:
    for prova in ("CN", "CH", "LC", "MT"):
        col_p = f"TP_PRESENCA_{prova}"
        col_n = f"NU_NOTA_{prova}"
        if col_p in df.columns and col_n in df.columns:
            df.loc[df[col_p] != 1, col_n] = pd.NA
    if "TP_STATUS_REDACAO" in df.columns and "NU_NOTA_REDACAO" in df.columns:
        # 2 = anulada (eliminacao); 4 = em branco (sem nota) — sem nota valida no ETL
        df.loc[df["TP_STATUS_REDACAO"].isin([2, 4]), "NU_NOTA_REDACAO"] = pd.NA
    return df


def detectar_separador(caminho: str, encoding: str = "latin-1") -> str | None:
    for sep in (";", ","):
        try:
            pd.read_csv(caminho, sep=sep, encoding=encoding, nrows=0)
            return sep
        except Exception:
            continue
    return None


def _aplicar_aliases(df: pd.DataFrame) -> pd.DataFrame:
    ren = {k: v for k, v in COL_ALIASES.items() if k in df.columns and v not in df.columns}
    if ren:
        df = df.rename(columns=ren)
    return df


def _cols_para_ano(ano: int, cols_reais: list[str]) -> list[str]:
    candidatos = list(COLS_PARTICIPANTES)
    if ano >= 2019:
        candidatos = [c for c in candidatos if c != "CO_ESCOLA"]
    return [c for c in candidatos if c in cols_reais]


def _padronizar_historico(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    df = df.copy()
    if "NU_ANO" not in df.columns:
        df["NU_ANO"] = ano
    df["NU_SEQUENCIAL"] = pd.NA
    if ano in ANOS_COM_CO_ESCOLA and "CO_ESCOLA" in df.columns:
        df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")
    elif "CO_ESCOLA" not in df.columns:
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


def _ler_cache(path: Path, label: str) -> pd.DataFrame | None:
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


def _ler_csv_participantes(ano: int, caminho: Path) -> pd.DataFrame | None:
    sep = detectar_separador(str(caminho))
    if sep is None:
        logger.error("Separador nao detectado: %s", caminho)
        return None

    cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
    cols_reais = _aplicar_aliases(pd.DataFrame(columns=cols_reais)).columns.tolist()
    cols_ler = _cols_para_ano(ano, cols_reais)
    logger.info("%s: %s/%s colunas", ano, len(cols_ler), len(COLS_PARTICIPANTES))

    chunks: list[pd.DataFrame] = []
    for i, chunk in enumerate(
        pd.read_csv(caminho, sep=sep, encoding="latin-1", usecols=cols_ler, chunksize=CHUNK_SIZE, low_memory=False)
    ):
        chunk = _aplicar_aliases(chunk)
        chunk = tratar_notas(chunk)
        chunk = _padronizar_historico(chunk, ano)
        chunks.append(chunk)
        logger.info("chunk %s: %s linhas", i + 1, len(chunk))

    if not chunks:
        return None

    df_ano = pd.concat(chunks, ignore_index=True)
    com_escola = df_ano["CO_ESCOLA"].notna().sum() if "CO_ESCOLA" in df_ano.columns else 0
    logger.info("[ok] %s: %s registros (%s com CO_ESCOLA)", ano, len(df_ano), com_escola)
    return df_ano


def processar_participantes_anos(anos: list[int]) -> pd.DataFrame | None:
    """Processa CSVs PARTICIPANTES/MICRODADOS para os anos indicados."""
    if not anos:
        return None

    logger.info("%s", "=" * 70)
    logger.info("PARTICIPANTES %s-%s", min(anos), max(anos))
    logger.info("%s", "=" * 70)

    arquivos: list[tuple[int, Path]] = []
    for ano in anos:
        nomes = tuple(n.format(ano=ano) for n in NOMES_CSV_PARTICIPANTES)
        caminho = _buscar_csv_ano(ano, nomes)
        if caminho is None:
            logger.warning("%s: CSV nao encontrado em %s", ano, PASTA_BRUTOS / str(ano))
            continue
        arquivos.append((ano, caminho))
        logger.info("[ok] %s: %s", ano, caminho.name)

    if not arquivos:
        cache = PASTA_DADOS / f"{min(anos)}_{max(anos)}" / f"enem_completo_{min(anos)}_{max(anos)}_.parquet"
        return _ler_cache(cache, f"participantes {min(anos)}-{max(anos)}")

    partes: list[pd.DataFrame] = []
    for ano, caminho in arquivos:
        df_ano = _ler_csv_participantes(ano, caminho)
        if df_ano is not None:
            partes.append(df_ano)
        logger.info("")

    if not partes:
        return None

    df = pd.concat(partes, ignore_index=True, sort=False)
    cache_dir = PASTA_DADOS / f"{min(anos)}_{max(anos)}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"enem_completo_{min(anos)}_{max(anos)}_.parquet"
    df.to_parquet(cache, index=False)
    logger.info("[salvo] %s (%s linhas)", cache, len(df))
    return df


def processar_participantes_historico(anos: list[int] | None = None) -> pd.DataFrame | None:
    """2013-2023 por padrao; filtravel via --anos."""
    if anos is None:
        anos = list(range(ANO_INICIAL, 2024))
    return processar_participantes_anos(anos)


def processar_microdados_historico() -> pd.DataFrame | None:
    """Atalho: microdados INEP 2013-2015 (com CO_ESCOLA)."""
    return processar_participantes_anos(list(ANOS_MICRO_HISTORICO))


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


def consolidar(*partes: pd.DataFrame | None, substituir_anos: set[int] | None = None) -> None:
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

    df_novo = pd.concat(bases, ignore_index=True, sort=False)
    anos_novo = set(pd.to_numeric(df_novo["NU_ANO"], errors="coerce").dropna().astype(int))

    destino = PARQUET
    existente = resolver_parquet()
    if existente.exists() and existente != destino:
        logger.info("[merge] parquet legado: %s", existente)

    if existente.exists():
        df_old = pd.read_parquet(existente)
        anos_old = set(pd.to_numeric(df_old["NU_ANO"], errors="coerce").dropna().astype(int))
        remover = anos_novo if substituir_anos is None else (substituir_anos | anos_novo)
        df_old = df_old[~df_old["NU_ANO"].isin(remover)]
        logger.info(
            "[merge] preservando anos %s; substituindo %s",
            sorted(anos_old - remover),
            sorted(remover & anos_old),
        )
        df_final = pd.concat([df_old, df_novo], ignore_index=True, sort=False)
    else:
        df_final = df_novo

    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    df_final.to_parquet(destino, index=False)
    if PARQUET_LEGADO.exists() and PARQUET_LEGADO != destino and destino.exists():
        logger.info("[info] parquet atualizado em %s (legado %s mantido)", destino, PARQUET_LEGADO)

    logger.info("[salvo] Consolidado: %s", destino)
    logger.info("Total: %s registros", len(df_final))
    logger.info("Anos: %s", sorted(df_final["NU_ANO"].dropna().unique()))
    logger.info("Colunas: %s", list(df_final.columns))

    try:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        meta = {
            "script": "processar_enem.py",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "parquet": str(destino),
            "total_rows": int(len(df_final)),
            "anos": [int(a) for a in sorted(df_final["NU_ANO"].dropna().unique())],
        }
        meta_path = WEB_DATA / "meta_processar_enem.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        logger.info("[meta] gravado: %s", meta_path)
    except Exception as e:
        logger.warning("[aviso] nao foi possivel gravar meta: %s", e)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ETL microdados ENEM -> parquet consolidado")
    p.add_argument(
        "--anos",
        type=int,
        nargs="+",
        help="Processar apenas estes anos (ex.: --anos 2013 2014 2015). Default: pipeline completo.",
    )
    p.add_argument(
        "--escola-historico",
        action="store_true",
        help="Normaliza MICRODADOS_ENEM_ESCOLA.csv (2005-2015) para parquet cache",
    )
    p.add_argument(
        "--historico",
        action="store_true",
        help=f"Atalho para --anos {' '.join(str(a) for a in ANOS_MICRO_HISTORICO)} (microdados individuais)",
    )
    return p.parse_args()


def main():
    args = _parse_args()
    t0 = time.time()
    logger.info("%s", "=" * 70)
    logger.info("ETL ENEM -> %s", PASTA_DADOS)
    logger.info("%s", "=" * 70)

    if args.escola_historico:
        from enem_escola_historico import carregar_escola_historico
        df = carregar_escola_historico()
        if df.empty:
            logger.error("Nenhum dado escola historico carregado")
            return
        logger.info("Escola historico: %s linhas, anos %s", len(df), sorted(df["NU_ANO"].dropna().unique()))
        logger.info("Proximo passo: python gerar_agregados.py && python gerar_web_data.py")
        return

    if args.historico:
        anos_alvo = list(ANOS_MICRO_HISTORICO)
    elif args.anos:
        anos_alvo = sorted(set(args.anos))
    else:
        anos_alvo = None

    if anos_alvo is not None:
        df_part = processar_participantes_anos(anos_alvo)
        consolidar(df_part, substituir_anos=set(anos_alvo))
    else:
        df_hist = processar_participantes_historico()
        resultados = [processar_resultados_ano(ano) for ano in ANOS_MICRODADOS if ano >= 2024]
        consolidar(df_hist, *resultados)

    logger.info("Tempo: %.1f min", (time.time() - t0) / 60)
    logger.info("%s", "=" * 70)
    logger.info("Proximo passo: python gerar_agregados.py && python gerar_web_data.py")


if __name__ == "__main__":
    main()
