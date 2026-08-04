"""Compara a metodologia do painel ENEM MS com a divulgada pela AIO.

Uso:
    .venv/bin/python scripts/diag_aio_vs_painel.py
    .venv/bin/python scripts/diag_aio_vs_painel.py --co-escola 50011413 --ano 2024
    .venv/bin/python scripts/diag_aio_vs_painel.py --co-escola 50011413 --ano 2024 --debug

A AIO (https://www.aio.com.br/enem-por-escola) declara:
  "Para cada Área do Conhecimento e Redação foram considerados na média
   todos os participantes da escola que concluíram cada prova."
  -> filtro POR PROVA (1 conjunto por área).

O painel calcula sobre o conjunto VALIDO:
   CONCLUINTE (CO_ESCOLA preenchido p/ 2024+)
   & PRESENTE_2_DIAS (TP_PRESENCA_* = 1 em CN, CH, LC, MT)
   & ~ELIM_OBJ (TP_PRESENCA_* != 2 em nenhuma objetiva)
   & ~ELIM_RED (TP_STATUS_REDACAO != 2)
   -> filtro GLOBAL (1 único conjunto para as 5 áreas).

Como dia 1 = CH+LC+RED e dia 2 = CN+MT, quem comparece só ao dia 1
entra na média AIO de CH/LC/RED mas NÃO entra na média do painel
(pois falta CN ou MT). Esse grupo costuma ter REDACAO baixa
(inclusive `branco`/`cópia` = 0), o que explica o gap maior em RED.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import PASTA_DADOS

PRES = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]
AREAS = [
    ("CN", "NU_NOTA_CN"),
    ("CH", "NU_NOTA_CH"),
    ("LC", "NU_NOTA_LC"),
    ("MT", "NU_NOTA_MT"),
    ("RED", "NU_NOTA_REDACAO"),
]


def _parquet_do_ano(ano: int) -> Path:
    """Procura o parquet adequado: 2024+ usa RESULTADOS por ano; <=2023 usa o consolidado."""
    candidatos = [
        PASTA_DADOS / str(ano) / f"enem_resultados_{ano}_.parquet",
        PASTA_DADOS / f"enem_completo_2019_{ano}_.parquet",
        PASTA_DADOS / "enem_completo_2019_2024_.parquet",
        PASTA_DADOS / "enem_completo_2019_2025_.parquet",
    ]
    for p in candidatos:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Nenhum parquet encontrado para o ano {ano}. Esperei um destes: {candidatos}"
    )


def carregar(ano: int, co_escola: int) -> pd.DataFrame:
    p = _parquet_do_ano(ano)
    filtros = [("CO_ESCOLA", "==", co_escola)]
    if "completo" in p.name:
        filtros.append(("NU_ANO", "==", ano))
    df = pd.read_parquet(p, filters=filtros)
    if df.empty:
        return df

    for area in ("CN", "CH", "LC", "MT"):
        df.loc[df[f"TP_PRESENCA_{area}"] != 1, f"NU_NOTA_{area}"] = np.nan
    if "TP_STATUS_REDACAO" in df.columns and "NU_NOTA_REDACAO" in df.columns:
        df.loc[df["TP_STATUS_REDACAO"] == 2, "NU_NOTA_REDACAO"] = np.nan

    df["PRESENTE_2D"] = df[PRES].eq(1).all(axis=1)
    df["ELIM_OBJ"] = df[PRES].eq(2).any(axis=1)
    df["ELIM_RED"] = df.get("TP_STATUS_REDACAO") == 2
    df["VALIDO"] = df["PRESENTE_2D"] & ~df["ELIM_OBJ"] & ~df["ELIM_RED"]
    return df


def _stats(serie: pd.Series) -> tuple[int, float | None, int]:
    s = pd.to_numeric(serie, errors="coerce").dropna()
    if s.empty:
        return 0, None, 0
    return len(s), float(s.mean()), int((s == 0).sum())


def comparar(ano: int, co_escola: int, debug: bool = False) -> pd.DataFrame:
    df = carregar(ano, co_escola)
    if df.empty:
        raise SystemExit(f"Sem registros para CO_ESCOLA={co_escola} em {ano}.")

    presentes_dia1 = int((df[["TP_PRESENCA_CH", "TP_PRESENCA_LC"]].eq(1).all(axis=1)).sum())
    presentes_dia2 = int((df[["TP_PRESENCA_CN", "TP_PRESENCA_MT"]].eq(1).all(axis=1)).sum())
    presentes_2d = int(df["PRESENTE_2D"].sum())
    apenas_dia1 = int(
        (df[["TP_PRESENCA_CH", "TP_PRESENCA_LC"]].eq(1).all(axis=1)
         & ~df[["TP_PRESENCA_CN", "TP_PRESENCA_MT"]].eq(1).all(axis=1)).sum()
    )
    apenas_dia2 = int(
        (df[["TP_PRESENCA_CN", "TP_PRESENCA_MT"]].eq(1).all(axis=1)
         & ~df[["TP_PRESENCA_CH", "TP_PRESENCA_LC"]].eq(1).all(axis=1)).sum()
    )
    print(f"\n=== CO_ESCOLA={co_escola} · ano={ano} ===")
    print(f"Registros associados à escola .........: {len(df)}")
    print(f"Presentes dia 1 (CH+LC) ...............: {presentes_dia1}")
    print(f"Presentes dia 2 (CN+MT) ...............: {presentes_dia2}")
    print(f"Presentes nos 2 dias (filtro do painel): {presentes_2d}")
    print(f"Compareceu só ao dia 1 ................: {apenas_dia1}  (entra no AIO p/ CH/LC/RED, FORA do painel)")
    print(f"Compareceu só ao dia 2 ................: {apenas_dia2}  (entra no AIO p/ CN/MT, FORA do painel)")
    if "TP_STATUS_REDACAO" in df.columns:
        print("Distribuição TP_STATUS_REDACAO:")
        print(df["TP_STATUS_REDACAO"].value_counts(dropna=False).sort_index().to_string())

    rows = []
    valido = df[df["VALIDO"]]
    for area, col in AREAS:
        n_p, mu_p, z_p = _stats(valido[col])
        n_a, mu_a, z_a = _stats(df[col])
        delta = (mu_p - mu_a) if (mu_p is not None and mu_a is not None) else None
        rows.append({
            "area": area,
            "painel_N": n_p,
            "painel_media": round(mu_p, 2) if mu_p is not None else None,
            "painel_zeros": z_p,
            "aio_N": n_a,
            "aio_media": round(mu_a, 2) if mu_a is not None else None,
            "aio_zeros": z_a,
            "delta_painel_menos_aio": round(delta, 2) if delta is not None else None,
        })
    res = pd.DataFrame(rows)

    print("\n=== Médias ===")
    print(res.to_string(index=False))

    if debug:
        print("\n=== Detalhe dos registros extras na ótica AIO (não-VALIDOS) ===")
        extras = df[~df["VALIDO"]]
        print(f"Total não-VALIDOS: {len(extras)}")
        if not extras.empty:
            print(extras[PRES + ["TP_STATUS_REDACAO", "NU_NOTA_REDACAO", "NU_NOTA_LC", "NU_NOTA_CH"]].to_string())

    return res


def cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--co-escola", type=int, default=50011413, help="Código INEP da escola (default: 50011413 = EE MANOEL GARCIA LEAL, Paranaíba)")
    ap.add_argument("--ano", type=int, default=2024, help="Ano (default: 2024 — único ano com microdado por escola disponível localmente)")
    ap.add_argument("--debug", action="store_true", help="Mostra detalhe dos registros não-VALIDOS")
    args = ap.parse_args()
    comparar(ano=args.ano, co_escola=args.co_escola, debug=args.debug)


if __name__ == "__main__":
    cli()
