"""
Extrai matriculados, participantes e taxa de participacao por escola estadual MS
a partir de MICRODADOS_ENEM_ESCOLA.csv (INEP, 2005-2015).

Uso:
  python extrair_participacao_escola_historico.py
  python extrair_participacao_escola_historico.py --anos 2013 2014 2015
  python extrair_participacao_escola_historico.py --csv caminho/saida.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enem_config import PASTA_DADOS, REDE_REFERENCIA, configure_logging
from enem_escola_historico import participacao_ms_estadual

logger = configure_logging(__name__)

SAIDA_DIR = PASTA_DADOS / "processados"
SAIDA_BASE = "ms_escolas_estadual_participacao_2005_2015"


def resumo_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("ano", as_index=False).agg(
        escolas=("co_inep_escola", "nunique"),
        matriculados=("matriculados", "sum"),
        participantes=("participantes", "sum"),
    )
    g["taxa_participacao"] = (g["participantes"] / g["matriculados"].replace(0, pd.NA) * 100).round(2)
    return g.sort_values("ano")


def salvar(df: pd.DataFrame, csv_path: Path | None = None) -> dict[str, Path]:
    SAIDA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = Path(csv_path or SAIDA_DIR / f"{SAIDA_BASE}.csv")
    parquet_path = csv_path.with_suffix(".parquet")
    xlsx_path = csv_path.with_suffix(".xlsx")
    resumo_path = SAIDA_DIR / f"{SAIDA_BASE}_resumo_ano.csv"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig", sep=";")
    df.to_parquet(parquet_path, index=False)
    resumo = resumo_por_ano(df)
    resumo.to_csv(resumo_path, index=False, encoding="utf-8-sig", sep=";")

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="por_escola", index=False)
        resumo.to_excel(xl, sheet_name="resumo_ano", index=False)

    meta = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "fonte": "INEP MICRODADOS_ENEM_ESCOLA.csv (2005-2015)",
        "rede": REDE_REFERENCIA,
        "uf": "MS",
        "anos": sorted(int(a) for a in df["ano"].dropna().unique()),
        "linhas": len(df),
        "escolas": int(df["co_inep_escola"].nunique()),
        "arquivos": {
            "detalhe_csv": str(csv_path),
            "detalhe_parquet": str(parquet_path),
            "detalhe_xlsx": str(xlsx_path),
            "resumo_ano_csv": str(resumo_path),
        },
    }
    meta_path = SAIDA_DIR / f"{SAIDA_BASE}_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "csv": csv_path,
        "parquet": parquet_path,
        "xlsx": xlsx_path,
        "resumo": resumo_path,
        "meta": meta_path,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Extrai participacao ENEM por escola estadual MS (2005-2015)")
    ap.add_argument("--anos", type=int, nargs="*", help="Filtrar anos (padrao: todos disponiveis)")
    ap.add_argument("--csv", type=Path, help="Caminho do CSV de saida")
    args = ap.parse_args()

    df = participacao_ms_estadual(anos=args.anos)
    if df.empty:
        raise SystemExit("Microdados ENEM por escola (2005-2015) nao encontrados.")
    paths = salvar(df, args.csv)

    resumo = resumo_por_ano(df)
    logger.info("Extraidos %s registros (%s escolas, anos %s-%s)",
                len(df), df["co_inep_escola"].nunique(), df["ano"].min(), df["ano"].max())
    for _, r in resumo.iterrows():
        logger.info("  %s: %s escolas | mat=%s part=%s taxa=%.1f%%",
                    int(r["ano"]), int(r["escolas"]), int(r["matriculados"]),
                    int(r["participantes"]), r["taxa_participacao"])
    logger.info("Salvo: %s", paths["csv"])


if __name__ == "__main__":
    main()
