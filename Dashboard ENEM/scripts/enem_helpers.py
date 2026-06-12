"""Helpers compartilhados — pipeline ENEM MS."""
from __future__ import annotations

import gc
import re
import unicodedata

import numpy as np
import pandas as pd

from enem_config import (
    COLS_NOTAS,
    CRE_CURTO_FIX,
    CRES_XLSX,
    DEP_MAP,
    NOTA_MAP,
    PRES_COLS,
)


def normalizar_texto(texto) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def cre_curto(cre) -> str:
    if cre is None or (isinstance(cre, float) and np.isnan(cre)):
        return "SED"
    s = str(cre).strip()
    if not s or s.upper() == "SED":
        return "SED"
    city = s.split(" - ", 1)[1].strip().upper() if " - " in s else s.upper()
    return CRE_CURTO_FIX.get(city, city.title())


def aplicar_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["DEP_ADM"] = df["TP_DEPENDENCIA_ADM_ESC"].map(DEP_MAP)
    df["PRESENTE_2_DIAS"] = df[PRES_COLS].eq(1).all(axis=1)
    df["ELIM_OBJ"] = df[PRES_COLS].eq(2).any(axis=1)
    df["ELIM_RED"] = df["TP_STATUS_REDACAO"] == 2
    df["RED_BRANCO"] = df["TP_STATUS_REDACAO"] == 4
    df["COM_ESCOLA"] = df["CO_ESCOLA"].notna() | df["SG_UF_ESC"].notna()
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
    cres = pd.read_excel(CRES_XLSX, sheet_name="Cód.INEP-CREs")
    col_cod = next((c for c in cres.columns if "INEP" in str(c).upper()), None)
    if col_cod is None:
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])
    col_esc = "UNIDADE ESCOLAR " if "UNIDADE ESCOLAR " in cres.columns else "UNIDADE ESCOLAR"
    col_mun = "MUNICÍPIO" if "MUNICÍPIO" in cres.columns else "MUNICIPIO"
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
    col_mun = "MUNICÍPIO" if "MUNICÍPIO" in df.columns else "MUNICIPIO"
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


def carregar_concluintes_sed() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (totais por ano, por escola com CO_ESCOLA quando possível)."""
    from enem_config import CONCLUINTES_XLSX

    raw = pd.read_excel(CONCLUINTES_XLSX, sheet_name="2024-2019")
    raw["NU_ANO"] = pd.to_numeric(raw["NU_ANO"], errors="coerce").astype("Int64")
    raw["Concluintes"] = pd.to_numeric(raw["Concluintes"], errors="coerce").fillna(0).astype(int)
    totais = raw.groupby("NU_ANO", observed=True)["Concluintes"].sum().reset_index()
    totais.columns = ["NU_ANO", "Concluintes"]

    cres = carregar_cres()
    raw["MUN_NORM"] = raw["Município"].map(normalizar_texto)
    raw["ESC_NORM"] = raw["Unidade Escolar"].map(normalizar_texto)
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
        por_esc.groupby(["NU_ANO", "CO_ESCOLA", "Município", "Unidade Escolar"], observed=True)["Concluintes"]
        .sum()
        .reset_index()
    )
    return totais, agg


def quantis_serie(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"min": 0, "q1": 0, "med": 0, "q3": 0, "max": 0, "outliers": []}
    q = s.quantile([0, 0.25, 0.5, 0.75, 1.0])
    return {
        "min": round(float(q.iloc[0]), 1),
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
