"""Participantes por escola a partir do parquet INEP.

População de referência (alinhada ao painel):
  - presente em ao menos uma área objetiva (TP_PRESENCA_* == 1);
  - não eliminado por fraude/fuga (nenhum TP_PRESENCA_* == 2);
  - não eliminado na redação (TP_STATUS_REDACAO != 2).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from enem_config import ANOS, PARQUET, PRES_COLS, PIPELINE_ROOT, PASTA_BRUTOS, PASTA_DADOS, configure_logging
from enem_helpers import mascara_populacao_referencia

logger = logging.getLogger(__name__)

ANOS_COM_ESCOLA_NO_PARQUET = tuple(a for a in ANOS if a >= 2024)
CHUNK_SIZE = 500_000
COLS_RESULTADOS = [
    "NU_SEQUENCIAL",
    "NU_ANO",
    "CO_ESCOLA",
    "SG_UF_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
    *PRES_COLS,
]


def resolver_pasta_dados() -> Path:
    """Resolve PASTA_DADOS/PASTA_BRUTOS mesmo quando .env usa caminho relativo."""
    for candidato in (PASTA_BRUTOS, PASTA_DADOS, PIPELINE_ROOT / "dados"):
        path = Path(candidato)
        if not path.is_absolute():
            for base in (Path.cwd(), PIPELINE_ROOT):
                cand = (base / path).resolve()
                if cand.exists():
                    return cand
        elif path.exists():
            return path.resolve()
    return (PIPELINE_ROOT / "dados").resolve()


def resolver_parquet(parquet: Path | None = None) -> Path:
    alvo = Path(parquet or PARQUET)
    if alvo.exists():
        return alvo.resolve()
    nome = alvo.name
    for base in (Path.cwd(), PIPELINE_ROOT, resolver_pasta_dados()):
        for cand in (base / alvo, base / "dados" / nome, base / nome):
            if cand.exists():
                return cand.resolve()
    return alvo.resolve()


def _buscar_resultados_csv(ano: int, pasta: Path) -> Path | None:
    nomes = (f"RESULTADOS_{ano}.csv",)
    for nome in nomes:
        for path in (
            pasta / str(ano) / nome,
            pasta / str(ano) / "DADOS" / nome,
            pasta / str(ano) / nome.lower(),
            pasta / str(ano) / "DADOS" / nome.lower(),
        ):
            if path.exists():
                return path
    return None


def _detectar_separador(caminho: Path) -> str:
    for sep in (";", ","):
        try:
            pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0)
            return sep
        except Exception:
            continue
    return ";"


def mascara_participante_aio(df: pd.DataFrame) -> pd.Series:
    """Mascara booleana: população de referência do painel (+ vínculo com escola)."""
    com_escola = df["CO_ESCOLA"].notna()
    return com_escola & mascara_populacao_referencia(df)


def _colunas_disponiveis(parquet: Path) -> list[str]:
    desejadas = [
        "NU_ANO",
        "CO_ESCOLA",
        "NU_INSCRICAO",
        "SG_UF_ESC",
        "TP_DEPENDENCIA_ADM_ESC",
        *PRES_COLS,
    ]
    schema = pq.read_schema(parquet).names
    return [c for c in desejadas if c in schema]


def carregar_contagens_resultados_csv(
    anos: tuple[int, ...] | None = None,
    pasta: Path | None = None,
    uf: str | None = None,
    dependencia: int | None = None,
    ineps: set[int] | None = None,
) -> pd.DataFrame:
    """Fallback: agrega a partir de RESULTADOS_{ano}.csv quando parquet ausente."""
    anos_alvo = anos or ANOS_COM_ESCOLA_NO_PARQUET
    pasta = pasta or resolver_pasta_dados()
    partes: list[pd.DataFrame] = []

    for ano in anos_alvo:
        caminho = _buscar_resultados_csv(ano, pasta)
        if caminho is None:
            logger.warning("Ano %s: RESULTADOS CSV nao encontrado em %s", ano, pasta / str(ano))
            continue

        sep = _detectar_separador(caminho)
        cols_reais = pd.read_csv(caminho, sep=sep, encoding="latin-1", nrows=0).columns.tolist()
        cols_ler = [c for c in COLS_RESULTADOS if c in cols_reais]
        if "CO_ESCOLA" not in cols_ler:
            logger.warning("Ano %s: CSV sem CO_ESCOLA", ano)
            continue

        acumulo: dict[int, int] = {}
        for chunk in pd.read_csv(
            caminho,
            sep=sep,
            encoding="latin-1",
            usecols=cols_ler,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        ):
            if "NU_ANO" not in chunk.columns:
                chunk["NU_ANO"] = ano
            chunk["CO_ESCOLA"] = pd.to_numeric(chunk["CO_ESCOLA"], errors="coerce")
            chunk = chunk[chunk["CO_ESCOLA"].notna()].copy()
            chunk["CO_ESCOLA"] = chunk["CO_ESCOLA"].astype("int64")
            if uf and "SG_UF_ESC" in chunk.columns:
                chunk = chunk[chunk["SG_UF_ESC"] == uf]
            if dependencia is not None and "TP_DEPENDENCIA_ADM_ESC" in chunk.columns:
                chunk = chunk[chunk["TP_DEPENDENCIA_ADM_ESC"] == dependencia]
            if ineps:
                chunk = chunk[chunk["CO_ESCOLA"].isin(ineps)]
            mask = mascara_participante_aio(chunk)
            for co_escola, qtd in chunk.loc[mask].groupby("CO_ESCOLA").size().items():
                acumulo[int(co_escola)] = acumulo.get(int(co_escola), 0) + int(qtd)

        if acumulo:
            agg = pd.DataFrame(
                [{"CO_ESCOLA": co, "NU_ANO": ano, "N_PARTICIPANTES": n} for co, n in acumulo.items()]
            )
            partes.append(agg)
            logger.info("Ano %s (CSV): %s escolas com participantes", ano, len(agg))

    if not partes:
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "N_PARTICIPANTES"])
    return pd.concat(partes, ignore_index=True)


def carregar_contagens_parquet(
    parquet: Path = PARQUET,
    anos: tuple[int, ...] | None = None,
    uf: str | None = None,
    dependencia: int | None = None,
    ineps: set[int] | None = None,
) -> pd.DataFrame:
    """Agrega N_PARTICIPANTES por (CO_ESCOLA, NU_ANO) conforme metodologia AIO."""
    parquet_resolvido = resolver_parquet(parquet)
    if not parquet_resolvido.exists():
        logger.warning("Parquet nao encontrado (%s); usando RESULTADOS CSV", parquet_resolvido)
        return carregar_contagens_resultados_csv(
            anos=anos,
            uf=uf,
            dependencia=dependencia,
            ineps=ineps,
        )

    anos_alvo = anos or ANOS_COM_ESCOLA_NO_PARQUET
    cols = _colunas_disponiveis(parquet_resolvido)
    partes: list[pd.DataFrame] = []

    for ano in anos_alvo:
        df = pd.read_parquet(parquet_resolvido, columns=cols, filters=[("NU_ANO", "==", ano)])
        if df.empty:
            logger.warning("Ano %s: sem registros no parquet", ano)
            continue

        com_escola = int(df["CO_ESCOLA"].notna().sum())
        if com_escola == 0:
            logger.warning(
                "Ano %s: microdados sem CO_ESCOLA (2019-2023 no parquet consolidado)",
                ano,
            )
            continue

        df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")
        df = df[df["CO_ESCOLA"].notna()].copy()
        df["CO_ESCOLA"] = df["CO_ESCOLA"].astype("int64")

        if uf and "SG_UF_ESC" in df.columns:
            df = df[df["SG_UF_ESC"] == uf]
        if dependencia is not None and "TP_DEPENDENCIA_ADM_ESC" in df.columns:
            df = df[df["TP_DEPENDENCIA_ADM_ESC"] == dependencia]
        if ineps:
            df = df[df["CO_ESCOLA"].isin(ineps)]

        mask = mascara_participante_aio(df)
        agg = (
            df.loc[mask]
            .groupby(["CO_ESCOLA", "NU_ANO"], observed=True)
            .size()
            .reset_index(name="N_PARTICIPANTES")
        )
        agg["NU_ANO"] = agg["NU_ANO"].astype(int)
        partes.append(agg)
        logger.info("Ano %s: %s escolas com participantes no parquet", ano, len(agg))

    if not partes:
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "N_PARTICIPANTES"])
    return pd.concat(partes, ignore_index=True)


def _valor_participante_preenchido(valor) -> bool:
    if pd.isna(valor):
        return False
    texto = str(valor).strip()
    return texto != ""


def completar_historico_csv(
    csv_path: Path,
    parquet: Path = PARQUET,
    sobrescrever: bool = False,
    saida: Path | None = None,
    uf: str | None = None,
    dependencia: int | None = None,
) -> dict:
    """Preenche N_PARTICIPANTES no CSV historico AIO (CO_INEP = CO_ESCOLA)."""
    csv_path = Path(csv_path)
    saida = Path(saida or csv_path)
    hist = pd.read_csv(csv_path)
    hist["CO_INEP"] = pd.to_numeric(hist["CO_INEP"], errors="coerce").astype("Int64")
    hist["NU_ANO"] = pd.to_numeric(hist["NU_ANO"], errors="coerce").astype("Int64")

    ineps = set(hist["CO_INEP"].dropna().astype(int))
    contagens = carregar_contagens_parquet(
        parquet=parquet,
        uf=uf,
        dependencia=dependencia,
        ineps=ineps,
    )
    lookup = {
        (int(r.CO_ESCOLA), int(r.NU_ANO)): int(r.N_PARTICIPANTES)
        for r in contagens.itertuples()
    }

    preenchidos = 0
    ja_tinha = 0
    sem_match = 0
    for idx, row in hist.iterrows():
        if pd.isna(row["CO_INEP"]) or pd.isna(row["NU_ANO"]):
            continue
        if _valor_participante_preenchido(row.get("N_PARTICIPANTES")) and not sobrescrever:
            ja_tinha += 1
            continue
        key = (int(row["CO_INEP"]), int(row["NU_ANO"]))
        if key in lookup:
            hist.at[idx, "N_PARTICIPANTES"] = lookup[key]
            preenchidos += 1
        elif int(row["NU_ANO"]) in ANOS_COM_ESCOLA_NO_PARQUET:
            sem_match += 1

    hist["CO_INEP"] = hist["CO_INEP"].astype(int)
    hist["NU_ANO"] = hist["NU_ANO"].astype(int)
    saida.parent.mkdir(parents=True, exist_ok=True)
    hist.to_csv(saida, index=False, encoding="utf-8-sig")

    resumo_path = saida.parent / "enem_escolas_resumo.csv"
    if resumo_path.exists():
        _atualizar_resumo(resumo_path, hist)

    meta = {
        "fonte_participantes": "parquet_inep_metodologia_aio",
        "parquet": str(parquet),
        "csv": str(saida),
        "anos_com_co_escola_no_parquet": list(ANOS_COM_ESCOLA_NO_PARQUET),
        "anos_sem_co_escola_no_parquet": [a for a in ANOS if a < 2024],
        "metodologia": (
            "CO_ESCOLA vinculado + presente em >=1 area objetiva + nao eliminado (TP_PRESENCA!=2)"
        ),
        "linhas_preenchidas": preenchidos,
        "linhas_ja_com_participantes": ja_tinha,
        "linhas_2024_2025_sem_match": sem_match,
        "escolas_com_contagem_parquet": int(contagens["CO_ESCOLA"].nunique()) if not contagens.empty else 0,
        "filtro_uf": uf,
        "filtro_dependencia": dependencia,
    }
    meta_path = saida.parent / "meta_participantes_parquet.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Participantes: %s linhas preenchidas, %s sem match (2024-2025), %s ja tinham valor",
        preenchidos,
        sem_match,
        ja_tinha,
    )
    return meta


def _atualizar_resumo(resumo_path: Path, hist: pd.DataFrame) -> None:
    resumo = pd.read_csv(resumo_path)
    resumo["CO_INEP"] = pd.to_numeric(resumo["CO_INEP"], errors="coerce").astype("Int64")
    part = (
        hist[hist["N_PARTICIPANTES"].apply(_valor_participante_preenchido)]
        .groupby("CO_INEP")["NU_ANO"]
        .nunique()
        .reset_index(name="ANOS_COM_PARTICIPANTES")
    )
    if "ANOS_COM_PARTICIPANTES" in resumo.columns:
        resumo = resumo.drop(columns=["ANOS_COM_PARTICIPANTES"])
    resumo = resumo.merge(part, on="CO_INEP", how="left")
    resumo["ANOS_COM_PARTICIPANTES"] = resumo["ANOS_COM_PARTICIPANTES"].fillna(0).astype(int)
    resumo["CO_INEP"] = resumo["CO_INEP"].astype(int)
    resumo.to_csv(resumo_path, index=False, encoding="utf-8-sig")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Completa N_PARTICIPANTES no CSV historico AIO via parquet INEP (2024-2025).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dados" / "aio" / "enem_escolas_historico.csv",
        help="CSV historico AIO (saida do scrape_aio_escolas.py).",
    )
    parser.add_argument("--parquet", type=Path, default=PARQUET, help="Parquet consolidado INEP.")
    parser.add_argument("--saida", type=Path, default=None, help="CSV de saida (default: sobrescreve --csv).")
    parser.add_argument("--sobrescrever", action="store_true", help="Substituir N_PARTICIPANTES ja preenchidos.")
    parser.add_argument("--uf", default=None, help="Filtrar parquet por UF (ex.: MS). Default: sem filtro.")
    parser.add_argument(
        "--dependencia",
        type=int,
        default=None,
        help="Filtrar TP_DEPENDENCIA_ADM_ESC (2=Estadual). Default: sem filtro.",
    )
    args = parser.parse_args(argv)

    configure_logging(__name__)
    meta = completar_historico_csv(
        csv_path=args.csv,
        parquet=args.parquet,
        sobrescrever=args.sobrescrever,
        saida=args.saida,
        uf=args.uf or None,
        dependencia=args.dependencia,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
