"""Helpers compartilhados - pipeline ENEM MS."""
from __future__ import annotations

import gc
import re
import unicodedata

import numpy as np
import pandas as pd

from enem_config import (
    COLS_NOTAS,
    CONCLUINTES_CSV,
    CONCLUINTES_XLSX,
    CRE_CURTO_FIX,
    CRES_XLSX,
    DEP_MAP,
    NOTA_MAP,
    PRES_COLS,
)

COL_MUNICIPIO = "Munic\u00edpio"

_CRE_POLO_MAP: dict[str, str] | None = None


def normalizar_texto(texto) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _cre_codigo(cre) -> str:
    s = str(cre).strip().upper()
    if not s or s in ("SED", "CAMPO GRANDE CAPITAL", "NAN"):
        return "SED"
    return s.split(" - ", 1)[0].strip()


def _formatar_polo(nome: str) -> str:
    key = nome.strip().upper()
    return CRE_CURTO_FIX.get(key, nome.strip().title())


def _nome_cre_polo(polo: str) -> str:
    """Ex.: Aquidauana -> CRE Aquidauana."""
    return f"CRE {polo}"


def carregar_mapa_cre_polo() -> dict[str, str]:
    """CRE (ex. CRE 01) -> nome de exibicao (ex. CRE Aquidauana)."""
    if not CRES_XLSX.exists():
        return {"SED": _nome_cre_polo("Campo Grande")}

    polo: dict[str, str] = {}
    xl = pd.ExcelFile(CRES_XLSX)
    for sheet in xl.sheet_names:
        df = pd.read_excel(CRES_XLSX, sheet_name=sheet)
        if "CRE" not in df.columns:
            continue
        for raw in df["CRE"].dropna().unique():
            s = str(raw).strip()
            su = s.upper()
            if su in ("SED", "CAMPO GRANDE CAPITAL"):
                polo["SED"] = _nome_cre_polo("Campo Grande")
                continue
            if " - " not in s:
                continue
            code, name = s.split(" - ", 1)
            polo[code.strip().upper()] = _nome_cre_polo(_formatar_polo(name))

    polo.setdefault("SED", _nome_cre_polo("Campo Grande"))
    return polo


def _get_cre_polo_map() -> dict[str, str]:
    global _CRE_POLO_MAP
    if _CRE_POLO_MAP is None:
        _CRE_POLO_MAP = carregar_mapa_cre_polo()
    return _CRE_POLO_MAP


def cre_curto(cre) -> str:
    sed = _get_cre_polo_map().get("SED", _nome_cre_polo("Campo Grande"))
    if cre is None or (isinstance(cre, float) and np.isnan(cre)):
        return sed
    s = str(cre).strip()
    if not s:
        return sed

    code = _cre_codigo(cre)
    polo = _get_cre_polo_map()
    if code in polo:
        return polo[code]

    if " - " in s:
        return _nome_cre_polo(_formatar_polo(s.split(" - ", 1)[1]))

    return _nome_cre_polo(_formatar_polo(s))


def _col_por_prefixo(columns, prefixo: str) -> str | None:
    alvo = normalizar_texto(prefixo)
    for c in columns:
        if normalizar_texto(c).startswith(alvo):
            return c
    return None


def preparar_ano(df_ano: pd.DataFrame) -> pd.DataFrame:
    """Normaliza schema hibrido 2019-2023 vs 2024 antes dos agregados."""
    df = df_ano.copy()
    ano = int(df["NU_ANO"].iloc[0])

    if "CO_ESCOLA" not in df.columns:
        df["CO_ESCOLA"] = pd.NA
    if "TP_ST_CONCLUSAO" not in df.columns:
        df["TP_ST_CONCLUSAO"] = pd.NA

    if ano == 2024:
        if "NU_SEQUENCIAL" in df.columns:
            df["NU_INSCRICAO"] = df["NU_SEQUENCIAL"]
        elif "NU_INSCRICAO" not in df.columns:
            df["NU_INSCRICAO"] = pd.NA
    elif "NU_INSCRICAO" not in df.columns and "NU_SEQUENCIAL" in df.columns:
        df["NU_INSCRICAO"] = df["NU_SEQUENCIAL"]

    if "NU_SEQUENCIAL" not in df.columns:
        df["NU_SEQUENCIAL"] = pd.NA if ano < 2024 else df.get("NU_INSCRICAO", pd.NA)

    return df


def aplicar_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["DEP_ADM"] = df["TP_DEPENDENCIA_ADM_ESC"].map(DEP_MAP)
    df["PRESENTE_2_DIAS"] = df[PRES_COLS].eq(1).all(axis=1)
    df["ELIM_OBJ"] = df[PRES_COLS].eq(2).any(axis=1)
    df["ELIM_RED"] = df["TP_STATUS_REDACAO"] == 2
    df["RED_BRANCO"] = df["TP_STATUS_REDACAO"] == 4

    if "CO_ESCOLA" in df.columns:
        df["COM_ESCOLA"] = df["CO_ESCOLA"].notna()
    else:
        df["COM_ESCOLA"] = False

    df["CONCLUINTE"] = False
    m_old = df["NU_ANO"] <= 2023
    df.loc[m_old, "CONCLUINTE"] = df.loc[m_old, "TP_ST_CONCLUSAO"] == 2
    m_24 = df["NU_ANO"] == 2024
    df.loc[m_24, "CONCLUINTE"] = df.loc[m_24, "COM_ESCOLA"]

    df["VALIDO"] = (
        df["CONCLUINTE"]
        & df["PRESENTE_2_DIAS"]
        & ~df["ELIM_OBJ"]
        & ~df["ELIM_RED"]
    )
    for c in COLS_NOTAS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["MEDIA_GERAL"] = df[COLS_NOTAS].mean(axis=1)
    return df


def carregar_cres() -> pd.DataFrame:
    if not CRES_XLSX.exists():
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])

    xl = pd.ExcelFile(CRES_XLSX)
    sheet = next((s for s in xl.sheet_names if "INEP" in s.upper()), xl.sheet_names[0])
    cres = pd.read_excel(CRES_XLSX, sheet_name=sheet)
    col_cod = next((c for c in cres.columns if "INEP" in str(c).upper()), None)
    if col_cod is None:
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])

    col_esc = "UNIDADE ESCOLAR " if "UNIDADE ESCOLAR " in cres.columns else "UNIDADE ESCOLAR"
    col_mun = _col_por_prefixo(cres.columns, "MUNICIPIO") or "MUNICIPIO"
    out = cres[[col_cod, "CRE", col_mun, col_esc]].copy()
    out[col_cod] = pd.to_numeric(out[col_cod], errors="coerce")
    out = out.dropna(subset=[col_cod]).drop_duplicates(subset=[col_cod])
    out = out.rename(columns={col_cod: "CO_ESCOLA", col_mun: "MUNICIPIO_CRES", col_esc: "NOME_ESCOLA"})
    return out


def carregar_mapa_municipio_cre() -> dict[str, str]:
    if not CRES_XLSX.exists():
        return {}
    try:
        df = pd.read_excel(CRES_XLSX, sheet_name="CREs")
    except ValueError:
        return {}
    col_mun = _col_por_prefixo(df.columns, "MUNICIPIO") or "MUNICIPIO"
    return {
        normalizar_texto(r[col_mun]): str(r["CRE"]).strip()
        for _, r in df.iterrows()
        if pd.notna(r.get(col_mun)) and pd.notna(r.get("CRE"))
    }


def enriquecer_ms(df: pd.DataFrame, cres: pd.DataFrame, mapa_muni: dict) -> pd.DataFrame:
    df = df.copy()
    for col, default in [
        ("NOME_ESCOLA", pd.NA),
        ("MUNICIPIO_CRES", df.get("NO_MUNICIPIO_ESC", pd.NA)),
        ("CRE", pd.NA),
    ]:
        if col not in df.columns:
            df[col] = default
    if not cres.empty and "CO_ESCOLA" in df.columns:
        m = df["CO_ESCOLA"].notna()
        if m.any():
            sub = df.loc[m, ["CO_ESCOLA"]].merge(cres, on="CO_ESCOLA", how="left", validate="m:1")
            df.loc[m, "NOME_ESCOLA"] = sub["NOME_ESCOLA"].values
            df.loc[m, "MUNICIPIO_CRES"] = sub["MUNICIPIO_CRES"].values
            df.loc[m, "CRE"] = sub["CRE"].values
    if mapa_muni and df["CRE"].isna().any():
        m = df["CRE"].isna()
        col = "MUNICIPIO_CRES" if "MUNICIPIO_CRES" in df.columns else "NO_MUNICIPIO_ESC"
        if col in df.columns:
            df.loc[m, "CRE"] = df.loc[m, col].map(
                lambda x: mapa_muni.get(normalizar_texto(x), pd.NA)
            )
    return df


def _concluintes_de_csv() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(CONCLUINTES_CSV)
    raw["NU_ANO"] = pd.to_numeric(raw["NU_ANO"], errors="coerce").astype("Int64")
    raw["Concluintes"] = pd.to_numeric(raw["Concluintes"], errors="coerce").fillna(0).astype(int)
    raw["CO_ESCOLA"] = pd.to_numeric(raw["CO_ESCOLA"], errors="coerce")
    raw = raw.rename(columns={"MUNICIPIO": COL_MUNICIPIO, "NOME_ESCOLA": "Unidade Escolar"})
    totais = raw.groupby("NU_ANO", observed=True)["Concluintes"].sum().reset_index()
    agg = (
        raw.groupby(["NU_ANO", "CO_ESCOLA", COL_MUNICIPIO, "Unidade Escolar"], observed=True)["Concluintes"]
        .sum()
        .reset_index()
    )
    return totais, agg


def _concluintes_de_xlsx() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_excel(CONCLUINTES_XLSX, sheet_name="2024-2019")
    raw["NU_ANO"] = pd.to_numeric(raw["NU_ANO"], errors="coerce").astype("Int64")
    raw["Concluintes"] = pd.to_numeric(raw["Concluintes"], errors="coerce").fillna(0).astype(int)
    totais = raw.groupby("NU_ANO", observed=True)["Concluintes"].sum().reset_index()
    totais.columns = ["NU_ANO", "Concluintes"]

    col_mun = _col_por_prefixo(raw.columns, "MUNICIPIO") or COL_MUNICIPIO
    col_esc = "Unidade Escolar"

    cres = carregar_cres()
    raw["MUN_NORM"] = raw[col_mun].map(normalizar_texto)
    raw["ESC_NORM"] = raw[col_esc].map(normalizar_texto)
    if not cres.empty:
        cres = cres.copy()
        cres["MUN_NORM"] = cres["MUNICIPIO_CRES"].map(normalizar_texto)
        cres["ESC_NORM"] = cres["NOME_ESCOLA"].map(normalizar_texto)
        por_esc = raw.merge(
            cres[["CO_ESCOLA", "MUN_NORM", "ESC_NORM", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"]],
            on=["MUN_NORM", "ESC_NORM"],
            how="left",
        )
    else:
        por_esc = raw.copy()
        por_esc["CO_ESCOLA"] = pd.NA
    agg = (
        por_esc.groupby(["NU_ANO", "CO_ESCOLA", col_mun, col_esc], observed=True)["Concluintes"]
        .sum()
        .reset_index()
        .rename(columns={col_mun: COL_MUNICIPIO})
    )
    return totais, agg


def carregar_concluintes_sed() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (totais por ano, por escola). Usa XLSX SED ou CSV local."""
    if CONCLUINTES_XLSX.exists():
        return _concluintes_de_xlsx()
    if CONCLUINTES_CSV.exists():
        return _concluintes_de_csv()
    raise FileNotFoundError(
        f"Planilha de concluintes nao encontrada. Coloque em {CONCLUINTES_XLSX} "
        f"ou use {CONCLUINTES_CSV}"
    )


def quantis_serie(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"min": 0, "min_pos": None, "q1": 0, "med": 0, "q3": 0, "max": 0, "outliers": []}
    q = s.quantile([0, 0.25, 0.5, 0.75, 1.0])
    pos = s[s > 0]
    min_pos = round(float(pos.min()), 1) if not pos.empty else None
    return {
        "min": round(float(q.iloc[0]), 1),
        "min_pos": min_pos,
        "q1": round(float(q.iloc[1]), 1),
        "med": round(float(q.iloc[2]), 1),
        "q3": round(float(q.iloc[3]), 1),
        "max": round(float(q.iloc[4]), 1),
        "outliers": [],
    }


def medias_por_area(df: pd.DataFrame) -> dict[str, float]:
    out = {}
    for k, col in NOTA_MAP.items():
        if col in df.columns:
            v = df[col].mean()
            if pd.notna(v):
                out[k] = round(float(v), 1)
    if "MEDIA_GERAL" in df.columns:
        v = df["MEDIA_GERAL"].mean()
        if pd.notna(v):
            out["GERAL"] = round(float(v), 1)
    return out


def limpar():
    gc.collect()
