"""
Gera ranking_escolas_2025.js para o painel (escolas estaduais MS · ENEM 2025).

Fontes: microdados INEP (parquet) + cadastro de escolas MS.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(__file__))

from aio_participantes_parquet import mascara_participante_aio, resolver_parquet, resolver_pasta_dados
from enem_config import ANO_FINAL, COLS_NOTAS, PIPELINE_ROOT, PRES_COLS, WEB_DATA, configure_logging

logger = configure_logging(__name__)

AIO_DIR = resolver_pasta_dados() / "aio"
RESUMO_CSV = AIO_DIR / "enem_escolas_resumo.csv"
HISTORICO_CSV = AIO_DIR / "enem_escolas_historico.csv"
ANO = ANO_FINAL
ANOS_PARQUET_HIST = (2024, 2025)

NOTA_JS = {
    "NU_NOTA_LC": "LC",
    "NU_NOTA_CH": "CH",
    "NU_NOTA_CN": "CN",
    "NU_NOTA_MT": "MT",
    "NU_NOTA_REDACAO": "RED",
}


def resolver_web_data() -> Path:
    alvo = Path(WEB_DATA)
    if alvo.is_absolute():
        return alvo
    for base in (PIPELINE_ROOT, Path.cwd()):
        cand = (base / alvo).resolve()
        if cand.parent.exists() or base == PIPELINE_ROOT:
            return cand
    return (PIPELINE_ROOT / "docs" / "data").resolve()


SAIDA_JS = resolver_web_data() / "ranking_escolas_2025.js"


def _int_or_none(val) -> int | None:
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _float_or_none(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        v = float(val)
        return round(v, 1) if v == v else None
    except (TypeError, ValueError):
        return None


def _rank_desc(series: pd.Series) -> pd.Series:
    return series.rank(ascending=False, method="min")


def _agregar_escolas_parquet(
    ano: int,
    uf: str | None = None,
    dependencia: int = 2,
) -> pd.DataFrame:
    """Medias e participantes por CO_ESCOLA a partir do microdado INEP."""
    parquet = resolver_parquet()
    if not parquet.exists():
        raise FileNotFoundError(f"Parquet nao encontrado: {parquet}")

    cols = [
        "NU_ANO",
        "CO_ESCOLA",
        "SG_UF_ESC",
        "TP_DEPENDENCIA_ADM_ESC",
        *COLS_NOTAS,
        *PRES_COLS,
    ]
    schema = pq.read_schema(parquet).names
    cols_ok = [c for c in cols if c in schema]
    df = pd.read_parquet(parquet, columns=cols_ok, filters=[("NU_ANO", "==", ano)])
    if df.empty or "CO_ESCOLA" not in df.columns:
        return pd.DataFrame()

    df = df[df["TP_DEPENDENCIA_ADM_ESC"] == dependencia].copy()
    if uf and "SG_UF_ESC" in df.columns:
        df = df[df["SG_UF_ESC"] == uf]

    df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")
    df = df[df["CO_ESCOLA"].notna()].copy()
    df["CO_ESCOLA"] = df["CO_ESCOLA"].astype("int64")

    mask = mascara_participante_aio(df)
    sub = df.loc[mask].copy()
    for c in COLS_NOTAS:
        if c in sub.columns:
            sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub["_media_aluno"] = sub[COLS_NOTAS].mean(axis=1, skipna=True)
    sub = sub[sub["_media_aluno"].notna()]
    if sub.empty:
        return pd.DataFrame()

    agg = {"media_geral": ("_media_aluno", "mean"), "participantes": ("CO_ESCOLA", "size")}
    for col in COLS_NOTAS:
        if col in sub.columns:
            agg[col] = (col, "mean")

    esc = sub.groupby("CO_ESCOLA", observed=True).agg(**agg).reset_index()
    esc["media_geral"] = esc["media_geral"].round(1)
    for col in COLS_NOTAS:
        if col in esc.columns:
            esc[col] = esc[col].round(1)
    return esc


def _parquet_notas_por_ano(codigos: set[int], anos: tuple[int, ...] = ANOS_PARQUET_HIST) -> dict[int, dict[int, dict]]:
    """{ano: {co_inep: {LC, CH, ..., media}}} com notas do microdado INEP."""
    out: dict[int, dict[int, dict]] = {}
    for ano in anos:
        try:
            esc = _agregar_escolas_parquet(ano, uf="MS", dependencia=2)
        except FileNotFoundError:
            continue
        if esc.empty:
            continue
        ano_map: dict[int, dict] = {}
        for row in esc.itertuples():
            co = int(row.CO_ESCOLA)
            if co not in codigos:
                continue
            item = {
                js: _float_or_none(getattr(row, col, None))
                for col, js in NOTA_JS.items()
                if hasattr(row, col)
            }
            item["media"] = _float_or_none(row.media_geral)
            ano_map[co] = item
        if ano_map:
            out[ano] = ano_map
    return out


def _carregar_historico_aio(codigos: set[int]) -> pd.DataFrame:
    if not HISTORICO_CSV.exists():
        logger.warning("Historico ausente: %s", HISTORICO_CSV)
        return pd.DataFrame()
    hist = pd.read_csv(HISTORICO_CSV)
    hist["CO_INEP"] = pd.to_numeric(hist["CO_INEP"], errors="coerce")
    hist["NU_ANO"] = pd.to_numeric(hist["NU_ANO"], errors="coerce")
    hist = hist[
        hist["CO_INEP"].isin(codigos)
        & (hist["REDE"].astype(str).str.lower() == "estadual")
    ].copy()
    return hist.sort_values(["CO_INEP", "NU_ANO"])


def _historico_escola(
    co: int,
    hist: pd.DataFrame,
    pq_por_ano: dict[int, dict[int, dict]],
) -> dict | None:
    rows = hist[hist["CO_INEP"] == co]
    if rows.empty:
        return None

    out: dict[str, list] = {"anos": [], "LC": [], "CH": [], "CN": [], "MT": [], "RED": [], "media": []}
    for row in rows.itertuples():
        ano = int(row.NU_ANO)
        pq = pq_por_ano.get(ano, {}).get(co, {})
        areas: dict[str, float | None] = {}
        for col, js in NOTA_JS.items():
            if js in pq:
                areas[js] = pq[js]
            else:
                areas[js] = _float_or_none(getattr(row, col, None))

        vals = [v for v in areas.values() if v is not None]
        media = pq.get("media") if "media" in pq else (round(sum(vals) / len(vals), 1) if vals else None)

        out["anos"].append(ano)
        for js in ("LC", "CH", "CN", "MT", "RED"):
            out[js].append(areas[js])
        out["media"].append(media)

    return out if out["anos"] else None


def _carregar_base_aio() -> pd.DataFrame:
    if not RESUMO_CSV.exists():
        raise FileNotFoundError(f"Resumo ausente: {RESUMO_CSV}")
    resumo = pd.read_csv(RESUMO_CSV)
    resumo["CO_INEP"] = pd.to_numeric(resumo["CO_INEP"], errors="coerce")
    resumo = resumo[resumo["REDE"].astype(str).str.lower() == "estadual"].copy()
    return resumo


def _montar_tabela_ms() -> pd.DataFrame:
    aio = _carregar_base_aio()
    ms = _agregar_escolas_parquet(ANO, uf="MS", dependencia=2)
    br = _agregar_escolas_parquet(ANO, uf=None, dependencia=2)

    if ms.empty:
        raise RuntimeError("Nenhuma escola MS encontrada no parquet 2025")

    br = br.copy()
    br["rank_nacional_estadual_br"] = _rank_desc(br["media_geral"])
    br["total_nacional_estadual_br"] = len(br)
    br_lookup = br.set_index("CO_ESCOLA")[
        ["rank_nacional_estadual_br", "total_nacional_estadual_br"]
    ]

    df = aio.merge(ms, left_on="CO_INEP", right_on="CO_ESCOLA", how="inner")
    df = df[df["media_geral"].notna()].copy()
    df = df.merge(br_lookup, left_on="CO_INEP", right_index=True, how="left")

    df["rank_mun_estadual_ms"] = df.groupby("MUNICIPIO")["media_geral"].transform(_rank_desc)
    df["total_mun_estadual_ms"] = df.groupby("MUNICIPIO")["CO_INEP"].transform("count")
    df["rank_uf_estadual_ms"] = _rank_desc(df["media_geral"])
    df["total_uf_estadual_ms"] = len(df)

    logger.info(
        "Escolas MS: %s no cadastro, %s com metricas parquet, %s medias distintas",
        len(aio),
        len(df),
        df["media_geral"].nunique(),
    )
    return df


def montar_payload() -> dict:
    df = _montar_tabela_ms()
    codigos = set(df["CO_INEP"].astype(int))
    hist_aio = _carregar_historico_aio(codigos)
    pq_por_ano = _parquet_notas_por_ano(codigos)

    escolas = []
    for row in df.sort_values(["MUNICIPIO", "NOME_ESCOLA"]).itertuples():
        co = int(row.CO_INEP)
        notas = {
            js: _float_or_none(getattr(row, col, None))
            for col, js in NOTA_JS.items()
            if hasattr(row, col)
        }
        escolas.append(
            {
                "coInep": co,
                "nome": str(row.NOME_ESCOLA or "").strip(),
                "municipio": str(row.MUNICIPIO or "").strip(),
                "uf": str(row.UF or "MS").strip(),
                "mediaGeral": _float_or_none(row.media_geral),
                "participantes": _int_or_none(row.participantes),
                "notas": notas,
                "historico": _historico_escola(co, hist_aio, pq_por_ano),
                "todasRedes": {
                    "municipio": _int_or_none(getattr(row, "RANKING_MUNICIPIO", None)),
                    "uf": _int_or_none(getattr(row, "RANKING_UF", None)),
                    "brasil": _int_or_none(getattr(row, "RANKING_BRASIL", None)),
                },
                "estaduaisMs": {
                    "municipio": int(row.rank_mun_estadual_ms),
                    "totalMunicipio": int(row.total_mun_estadual_ms),
                    "uf": int(row.rank_uf_estadual_ms),
                    "totalUf": int(row.total_uf_estadual_ms),
                },
                "estaduaisBr": {
                    "brasil": _int_or_none(getattr(row, "rank_nacional_estadual_br", None)),
                    "totalBrasil": _int_or_none(getattr(row, "total_nacional_estadual_br", None)),
                },
            }
        )

    com_geral = sum(1 for e in escolas if e["todasRedes"]["uf"] is not None)
    com_part = sum(1 for e in escolas if e["participantes"] is not None)
    com_hist = sum(1 for e in escolas if e.get("historico"))

    anos_hist = sorted(hist_aio["NU_ANO"].dropna().unique().astype(int).tolist()) if not hist_aio.empty else []

    return {
        "ano": ANO,
        "fonte": "Microdados INEP / ENEM 2025",
        "fonteHistorico": "Microdados INEP / ENEM",
        "geradoEm": pd.Timestamp.now().isoformat(timespec="seconds"),
        "totalEscolas": len(escolas),
        "comRankingGeral": com_geral,
        "comParticipantes": com_part,
        "comHistorico": com_hist,
        "anosHistorico": anos_hist,
        "escolas": escolas,
        "municipios": sorted({e["municipio"] for e in escolas if e["municipio"]}),
    }


def salvar_js(payload: dict, destino: Path = SAIDA_JS) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    destino.write_text(f"window.RANKING_ESCOLAS_2025 = {body};\n", encoding="utf-8")
    logger.info("[ok] %s (%s escolas)", destino, payload["totalEscolas"])
    return destino


def main() -> int:
    payload = montar_payload()
    salvar_js(payload)
    meta_path = resolver_web_data() / "meta_ranking_escolas_2025.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
