"""Extensao historica 2013-2018: medias MS estadual a partir do historico AIO por escola."""

from __future__ import annotations



from pathlib import Path



import pandas as pd



from enem_config import ANO_INICIAL, ANO_MICRO_INICIAL, ANOS, AREA_KEYS, NOTA_MAP, PASTA_DADOS



HISTORICO_CSV = PASTA_DADOS / "aio" / "enem_escolas_historico.csv"





def anos_extensao_aio() -> list[int]:

    return [a for a in ANOS if a < ANO_MICRO_INICIAL]





def _carregar_ms_estadual() -> pd.DataFrame:

    if not HISTORICO_CSV.exists():

        return pd.DataFrame()

    hist = pd.read_csv(HISTORICO_CSV)

    hist = hist[hist["REDE"].astype(str).str.lower() == "estadual"].copy()

    if "UF" in hist.columns:

        hist = hist[hist["UF"].astype(str).str.upper() == "MS"]

    hist["NU_ANO"] = pd.to_numeric(hist["NU_ANO"], errors="coerce")

    if "N_PARTICIPANTES" in hist.columns:

        hist["N_PARTICIPANTES"] = pd.to_numeric(hist["N_PARTICIPANTES"], errors="coerce")

    return hist.dropna(subset=["NU_ANO"])





def medias_ms_por_ano() -> dict[int, dict]:

    """{ano: {geral, CN, CH, LC, MT, RED, n_escolas}} para anos sem microdado."""

    hist = _carregar_ms_estadual()

    if hist.empty:

        return {}



    out: dict[int, dict] = {}

    for ano, grp in hist.groupby("NU_ANO"):

        ano = int(ano)

        if ano >= ANO_MICRO_INICIAL or ano < ANO_INICIAL:

            continue

        item = {

            "geral": round(float(grp["MEDIA_GERAL"].mean()), 1) if grp["MEDIA_GERAL"].notna().any() else None,

            "n_escolas": int(len(grp)),

        }

        for k, col in NOTA_MAP.items():

            if col in grp.columns and grp[col].notna().any():

                item[k] = round(float(grp[col].mean()), 1)

        out[ano] = item

    return out





def participantes_estadual_por_ano() -> dict[int, int]:

    """Soma N_PARTICIPANTES (AIO/login ou parquet) por ano, rede estadual MS."""

    hist = _carregar_ms_estadual()

    if hist.empty or "N_PARTICIPANTES" not in hist.columns:

        return {}

    out: dict[int, int] = {}

    for ano, grp in hist.groupby("NU_ANO"):

        ano = int(ano)

        if ano >= ANO_MICRO_INICIAL or ano < ANO_INICIAL:

            continue

        vals = grp["N_PARTICIPANTES"].dropna()

        if vals.empty:

            continue

        total = int(vals.sum())

        if total > 0:

            out[ano] = total

    return out





def area_detail_web_extensao() -> dict[str, dict[str, dict]]:

    """Registros areaDetail para 2013-2018 (fonte AIO, sem histograma individual)."""

    hist = _carregar_ms_estadual()

    out: dict[str, dict[str, dict]] = {k: {} for k in AREA_KEYS}

    if hist.empty:

        return out



    for ano in anos_extensao_aio():

        sub = hist[hist["NU_ANO"] == ano]

        if sub.empty:

            continue

        for area in AREA_KEYS:

            col = NOTA_MAP[area]

            valid = sub[sub[col].notna()]

            if valid.empty:

                continue

            n_part_vals = valid["N_PARTICIPANTES"].dropna() if "N_PARTICIPANTES" in valid.columns else pd.Series(dtype=float)

            n_part = int(n_part_vals.sum()) if not n_part_vals.empty else None

            out[area][str(ano)] = {

                "n": n_part if n_part and n_part > 0 else None,

                "nEscolas": int(len(valid)),

                "brN": None,

                "fonte": "aio_escolas",

                "pctSemNota": None,

                "pctZero": None,

                "moda": None,

                "modaFaixa": None,

                "modaTipo": "faixa",

                "minPos": round(float(valid[col].min()), 1),

                "minPosExact": False,

                "medianaEscolas": round(float(valid[col].median()), 1),

                "histPct": None,

                "histCounts": None,

                "brHistPct6": None,

                "brHistCounts6": None,

            }

    return out





def referencias_rows() -> list[dict]:

    """Linhas no formato referencias.parquet para merge no painel."""

    medias = medias_ms_por_ano()

    rows: list[dict] = []

    for ano, item in sorted(medias.items()):

        if item.get("geral") is not None:

            rows.append({

                "ano": ano,

                "area": "MEDIA_GERAL",

                "media_ms": item["geral"],

                "media_br": None,

                "media_ms_sem_zero": None,

                "media_br_sem_zero": None,

                "fonte": "aio_escolas",

            })

        for k, col in NOTA_MAP.items():

            if k in item:

                rows.append({

                    "ano": ano,

                    "area": col,

                    "media_ms": item[k],

                    "media_br": None,

                    "media_ms_sem_zero": None,

                    "media_br_sem_zero": None,

                    "fonte": "aio_escolas",

                })

    return rows

