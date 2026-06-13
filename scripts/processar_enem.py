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

import pandas as pd

from enem_config import PASTA_BRUTOS, PASTA_DADOS, PARQUET

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
    print("\n" + "=" * 70)
    print("2019-2023 - PARTICIPANTES (todos os estados)")
    print("=" * 70)

    arquivos: list[tuple[int, str]] = []
    for ano in range(2019, 2024):
        pasta = PASTA_BRUTOS / str(ano)
        if not pasta.is_dir():
            print(f"  [aviso] Pasta ausente: {pasta}")
            continue
        matches = glob.glob(str(pasta / f"*{ano}*.csv"))
        if matches:
            arquivos.append((ano, matches[0]))
            print(f"  [ok] {ano}: {os.path.basename(matches[0])}")
        else:
            print(f"  [aviso] {ano}: CSV nao encontrado")

    if not arquivos:
        return None

    partes: list[pd.DataFrame] = []
    for ano, caminho in arquivos:
        sep = detectar_separador(caminho)
        if sep is None:
            print(f"  [erro] Separador nao detectado: {caminho}")
            continue
        cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
        cols_ler = [c for c in COLS_2019_2023 if c in cols_reais]
        print(f"  {ano}: {len(cols_ler)}/{len(COLS_2019_2023)} colunas")

        chunks: list[pd.DataFrame] = []
        for i, chunk in enumerate(
            pd.read_csv(caminho, sep=sep, encoding="latin-1", usecols=cols_ler, chunksize=CHUNK_SIZE, low_memory=False)
        ):
            chunk = tratar_notas(chunk)
            chunk = _padronizar_historico(chunk, ano)
            chunks.append(chunk)
            print(f"     chunk {i + 1}: {len(chunk):,} linhas", end="\r")
        print()
        if chunks:
            df_ano = pd.concat(chunks, ignore_index=True)
            print(f"  [ok] {ano}: {len(df_ano):,} registros")
            partes.append(df_ano)

    if not partes:
        return None

    df = pd.concat(partes, ignore_index=True, sort=False)
    out = PASTA_DADOS / "2019_2023" / "enem_completo_2019_2023_.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"\n[salvo] {out} ({len(df):,} linhas)")
    return df


def processar_2024_resultados() -> pd.DataFrame | None:
    print("\n" + "=" * 70)
    print("2024 - RESULTADOS (sem merge com PARTICIPANTES)")
    print("=" * 70)

    pasta = PASTA_BRUTOS / "2024"
    if not pasta.is_dir():
        print(f"  [erro] Pasta ausente: {pasta}")
        return None

    caminho = None
    for nome in ("RESULTADOS_2024.csv", "resultados_2024.csv"):
        p = pasta / nome
        if p.exists():
            caminho = p
            break
    if caminho is None:
        print("  [erro] RESULTADOS_2024.csv nao encontrado")
        return None

    sep = detectar_separador(str(caminho))
    if sep is None:
        print("  [erro] Separador nao detectado")
        return None

    cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
    cols_ler = [c for c in COLS_2024 if c in cols_reais]
    print(f"  {caminho.name}: {len(cols_ler)}/{len(COLS_2024)} colunas")

    chunks: list[pd.DataFrame] = []
    for i, chunk in enumerate(
        pd.read_csv(caminho, sep=sep, encoding="latin-1", usecols=cols_ler, chunksize=CHUNK_SIZE, low_memory=False)
    ):
        chunk = tratar_notas(chunk)
        chunk = _padronizar_2024(chunk)
        chunks.append(chunk)
        print(f"     chunk {i + 1}: {len(chunk):,} linhas", end="\r")
    print()

    if not chunks:
        return None

    df = pd.concat(chunks, ignore_index=True)
    com_escola = df["CO_ESCOLA"].notna().sum() if "CO_ESCOLA" in df.columns else 0
    print(f"  [ok] 2024: {len(df):,} registros ({com_escola:,} com CO_ESCOLA)")

    out = PASTA_DADOS / "2024" / "enem_resultados_2024_.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"[salvo] {out}")
    return df


def consolidar(df_hist: pd.DataFrame | None, df_2024: pd.DataFrame | None) -> None:
    bases = [b for b in (df_hist, df_2024) if b is not None]
    if not bases:
        print("\n[erro] Nenhuma base para consolidar")
        return

    print("\n" + "=" * 70)
    print("CONSOLIDACAO 2019-2024")
    print("=" * 70)
    for b in bases:
        anos = sorted(b["NU_ANO"].dropna().unique())
        print(f"  bloco anos {list(anos)}: {len(b):,} linhas")

    df_final = pd.concat(bases, ignore_index=True, sort=False)
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    df_final.to_parquet(PARQUET, index=False)
    print(f"\n[salvo] Consolidado: {PARQUET}")
    print(f"   Total: {len(df_final):,} registros")
    print(f"   Colunas: {list(df_final.columns)}")


def main():
    t0 = time.time()
    print("=" * 70)
    print("ETL ENEM -> pipeline_dashboard/dados/")
    print("=" * 70)

    df_hist = processar_2019_2023()
    df_2024 = processar_2024_resultados()
    consolidar(df_hist, df_2024)

    print(f"\nTempo: {(time.time() - t0) / 60:.1f} min")
    print("=" * 70)


if __name__ == "__main__":
    main()
