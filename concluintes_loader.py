"""
Carrega concluintes do 3º ano (rede estadual MS) a partir da planilha INEP/SED.

Planilha padrão: data/Concluintes EM 2019 a 2024.xlsx (aba 2024-2019).
CO_ESCOLA é preenchido via cruzamento com cres.xlsx quando ausente na planilha.
"""

from __future__ import annotations

import os
import unicodedata

import pandas as pd

_ROOT = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_ROOT, "data")

from cres_loader import mapa_inep_por_nome_escola, resolve_arquivo_cres

ARQUIVO_CONCLUINTES_PADRAO = os.path.join(_DATA, "Concluintes EM 2019 a 2024.xlsx")
ARQUIVO_CRES_PADRAO = resolve_arquivo_cres() or os.path.join(_ROOT, "cres.xlsx")


def normalizar_texto(texto) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    for a, b in [
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
        ("Â", "A"), ("Ê", "E"), ("Î", "I"), ("Ô", "O"), ("Û", "U"),
        ("Ã", "A"), ("Õ", "O"), ("Ç", "C"), ("À", "A"),
    ]:
        texto = texto.replace(a, b)
    return " ".join(texto.split())


def _mapa_inep_por_nome_escola(arquivo_cres: str) -> pd.DataFrame:
    return mapa_inep_por_nome_escola(arquivo_cres)


def _ler_planilha_concluintes(arquivo: str, arquivo_cres: str | None = None) -> pd.DataFrame:
    if not os.path.exists(arquivo):
        return pd.DataFrame()

    xl = pd.ExcelFile(arquivo)
    if "2024-2019" in xl.sheet_names:
        df = pd.read_excel(arquivo, sheet_name="2024-2019")
    else:
        frames = []
        for sh in xl.sheet_names:
            if not str(sh).isdigit():
                continue
            raw = pd.read_excel(arquivo, sheet_name=sh, header=None)
            hdr = raw.iloc[0].tolist()
            body = raw.iloc[1:].copy()
            body.columns = hdr
            body["NU_ANO"] = int(sh)
            frames.append(body)
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    col_conc = None
    for c in df.columns:
        up = str(c).strip().upper()
        if up in {"CONCLUINTES", "MATRÍCULA FINAL", "MATRICULA FINAL", "MATRICULA_FINAL"}:
            col_conc = c
            break
    if col_conc is None:
        return pd.DataFrame()

    rename = {
        col_conc: "Concluintes",
    }
    for c in df.columns:
        up = str(c).strip().upper()
        if up in {"MUNICÍPIO", "MUNICIPIO"}:
            rename[c] = "MUNICIPIO"
        elif up in {"UNIDADE ESCOLAR", "ESCOLA", "NOME_ESCOLA"}:
            rename[c] = "NOME_ESCOLA"
        elif up in {"NU_ANO", "ANO"}:
            rename[c] = "NU_ANO"
        elif up in {"CO_ESCOLA", "COD INEP", "CÓD INEP", "INEP"}:
            rename[c] = "CO_ESCOLA"
        elif up in {"TURNO", "TURNOS"}:
            rename[c] = "TURNOS"
    df = df.rename(columns=rename)

    if "NU_ANO" not in df.columns:
        return pd.DataFrame()

    fase = df.get("Ano/Fase", df.get("Ano_Fase", pd.Series(dtype=object)))
    mask_3 = fase.astype(str).str.strip().str.upper().str.startswith("3")
    df = df[mask_3].copy()

    df["NU_ANO"] = pd.to_numeric(df["NU_ANO"], errors="coerce")
    df["Concluintes"] = pd.to_numeric(df["Concluintes"], errors="coerce").fillna(0)
    df = df.dropna(subset=["NU_ANO"])

    if "CO_ESCOLA" in df.columns:
        df["CO_ESCOLA"] = pd.to_numeric(df["CO_ESCOLA"], errors="coerce")
    else:
        df["CO_ESCOLA"] = pd.NA

    if "NOME_ESCOLA" in df.columns:
        df["esc_norm"] = df["NOME_ESCOLA"].map(normalizar_texto)
        mapa = _mapa_inep_por_nome_escola(
            arquivo_cres or os.getenv("ARQUIVO_CRES", ARQUIVO_CRES_PADRAO)
        )
        if not mapa.empty:
            df = df.merge(mapa, on="esc_norm", how="left", suffixes=("", "_cres"))
            df["CO_ESCOLA"] = df["CO_ESCOLA"].fillna(df.get("CO_ESCOLA_cres"))
            df = df.drop(columns=["CO_ESCOLA_cres", "esc_norm"], errors="ignore")

    if "MUNICIPIO" not in df.columns:
        df["MUNICIPIO"] = pd.NA

    return df


def carregar_concluintes_escola(
    arquivo: str | None = None,
    arquivo_cres: str | None = None,
) -> pd.DataFrame:
    """CO_ESCOLA, NU_ANO, Concluintes (+ MUNICIPIO, NOME_ESCOLA, TURNOS quando existirem)."""
    arquivo = arquivo or os.getenv("ARQUIVO_CONCLUINTES", ARQUIVO_CONCLUINTES_PADRAO)
    arquivo_cres = arquivo_cres or os.getenv("ARQUIVO_CRES", ARQUIVO_CRES_PADRAO)
    df = _ler_planilha_concluintes(arquivo, arquivo_cres)
    if df.empty:
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "Concluintes"])

    agg_cols = ["CO_ESCOLA", "NU_ANO"]
    extra = [c for c in ("MUNICIPIO", "NOME_ESCOLA", "TURNOS") if c in df.columns]
    grouped = (
        df.dropna(subset=["CO_ESCOLA"])
        .groupby(agg_cols, as_index=False)
        .agg(Concluintes=("Concluintes", "sum"), **{c: (c, "first") for c in extra})
    )
    grouped["CO_ESCOLA"] = grouped["CO_ESCOLA"].astype("Int64")
    grouped["NU_ANO"] = grouped["NU_ANO"].astype("int16")
    grouped["Concluintes"] = grouped["Concluintes"].astype(int)
    return grouped.drop_duplicates(subset=["CO_ESCOLA", "NU_ANO"])


def carregar_concluintes_municipio(arquivo: str | None = None) -> pd.DataFrame:
    arquivo = arquivo or os.getenv("ARQUIVO_CONCLUINTES", ARQUIVO_CONCLUINTES_PADRAO)
    df = _ler_planilha_concluintes(arquivo)
    if df.empty or "MUNICIPIO" not in df.columns:
        return pd.DataFrame(columns=["MUNICIPIO", "NU_ANO", "Concluintes", "N_ESCOLAS"])

    agg = (
        df.groupby(["MUNICIPIO", "NU_ANO"], as_index=False)
        .agg(Concluintes=("Concluintes", "sum"), N_ESCOLAS=("CO_ESCOLA", "nunique"))
    )
    agg["NU_ANO"] = agg["NU_ANO"].astype("int16")
    agg["Concluintes"] = agg["Concluintes"].astype(int)
    return agg


def carregar_concluintes_cre(arquivo: str | None = None, arquivo_cres: str | None = None) -> pd.DataFrame:
    """Concluintes por CRE e ano via cadastro de escolas (CO_ESCOLA → CRE).

    Usa a 1ª aba do cres.xlsx (código INEP), não o mapeamento município → CRE.
    """
    from cres_loader import carregar_cres_escolas, construir_mapa_cre_completo

    df_esc = carregar_concluintes_escola(arquivo=arquivo, arquivo_cres=arquivo_cres)
    if df_esc.empty:
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])

    arquivo_cres = arquivo_cres or os.getenv("ARQUIVO_CRES", ARQUIVO_CRES_PADRAO)
    cres = carregar_cres_escolas(arquivo_cres)
    if cres.empty:
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])

    mapa_cre_completo = construir_mapa_cre_completo(arquivo_cres)
    df = df_esc.merge(
        cres[["CO_ESCOLA", "CRE"]].drop_duplicates(subset=["CO_ESCOLA"]),
        on="CO_ESCOLA",
        how="left",
    )
    df["CRE"] = df["CRE"].astype(str).str.strip().map(mapa_cre_completo).fillna(df["CRE"])
    df = df.dropna(subset=["CRE", "NU_ANO"])
    agg = df.groupby(["CRE", "NU_ANO"], observed=True)["Concluintes"].sum().reset_index()
    agg["NU_ANO"] = agg["NU_ANO"].astype("int16")
    agg["Concluintes"] = agg["Concluintes"].astype(int)
    return agg
