"""Enriquecimento MS com CRE e município — painel ENEM v15."""

from __future__ import annotations

from typing import Optional

import os

import pandas as pd
import streamlit as st

from cres_loader import (
    carregar_cres_escolas,
    carregar_mapa_municipio_cre as _carregar_mapa_municipio_cre,
    construir_mapa_cre_completo,
)
from app.v15.paths import ARQUIVO_CRES


def carregar_cres() -> pd.DataFrame:
    cres = carregar_cres_escolas(ARQUIVO_CRES)
    if cres.empty and ARQUIVO_CRES and os.path.exists(ARQUIVO_CRES):
        st.error(
            "Coluna de código INEP não encontrada na 1ª aba do arquivo CRES. "
            "Use cres.xlsx (aba Cód.INEP-CREs) ou defina ARQUIVO_CRES."
        )
    return cres


@st.cache_data(show_spinner=False, ttl=3600)
def _mapa_cre_completo_cached() -> dict:
    return construir_mapa_cre_completo(ARQUIVO_CRES)


@st.cache_data(show_spinner=False, ttl=3600)
def carregar_mapa_municipio_cre() -> dict:
    mapa = _carregar_mapa_municipio_cre(ARQUIVO_CRES)
    if not mapa and ARQUIVO_CRES and os.path.exists(ARQUIVO_CRES):
        st.warning(
            "Mapeamento município → CRE indisponível na planilha CRES. "
            "Verifique a 1ª aba ou a aba 'CREs'."
        )
    return mapa


def normalizar_texto(texto: str) -> str:
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = (texto
             .replace("Á", "A").replace("É", "E").replace("Í", "I")
             .replace("Ó", "O").replace("Ú", "U").replace("Â", "A")
             .replace("Ê", "E").replace("Î", "I").replace("Ô", "O")
             .replace("Û", "U").replace("Ã", "A").replace("Õ", "O")
             .replace("Ç", "C").replace("À", "A"))
    return texto


def enriquecer_ms(df_ms: pd.DataFrame, cres: pd.DataFrame, mapa_muni_cre: dict = None) -> pd.DataFrame:
    df = df_ms.copy()
    if "NOME_ESCOLA" not in df.columns:
        df["NOME_ESCOLA"] = pd.NA
    if "MUNICIPIO_CRES" not in df.columns:
        df["MUNICIPIO_CRES"] = df.get("NO_MUNICIPIO_ESC", pd.NA)
    if "CRE" not in df.columns:
        df["CRE"] = pd.NA

    if cres is not None and not cres.empty and "CO_ESCOLA" in df.columns:
        mask_com_escola = df["CO_ESCOLA"].notna()
        if mask_com_escola.any():
            df_com_escola = df[mask_com_escola].merge(
                cres, on="CO_ESCOLA", how="left", validate="m:1", suffixes=("_old", ""),
            )
            for col in ["NOME_ESCOLA", "MUNICIPIO_CRES", "CRE"]:
                if col not in df_com_escola.columns:
                    df_com_escola[col] = pd.NA
            df.loc[mask_com_escola,
                "NOME_ESCOLA"] = df_com_escola["NOME_ESCOLA"].values
            df.loc[mask_com_escola,
                "MUNICIPIO_CRES"] = df_com_escola["MUNICIPIO_CRES"].values
            df.loc[mask_com_escola, "CRE"] = df_com_escola["CRE"].values

    if mapa_muni_cre and df["CRE"].isna().any():
        mask_sem_cre = df["CRE"].isna()
        col_mun = "MUNICIPIO_CRES" if df["MUNICIPIO_CRES"].notna(
        ).any() else "NO_MUNICIPIO_ESC"
        if col_mun in df.columns:
            municipios_normalizados = df.loc[mask_sem_cre, col_mun].apply(
                normalizar_texto)
            df.loc[mask_sem_cre, "CRE"] = municipios_normalizados.map(
                mapa_muni_cre)

    # Normalizar nomes curtos de CRE para nomes completos
    mapa_cre_completo = _mapa_cre_completo_cached()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df


def _coluna_municipio(df: pd.DataFrame) -> Optional[str]:
    """Primeira coluna de município disponível e preenchida."""
    for col in ("MUNICIPIO_CRES", "NO_MUNICIPIO_ESC", "municipio"):
        if col in df.columns and df[col].notna().any():
            return col
    return None


def _mapa_municipio_por_escola(df: pd.DataFrame) -> pd.Series:
    col = _coluna_municipio(df)
    if col is None or "CO_ESCOLA" not in df.columns:
        return pd.Series(dtype=object)
    return (
        df[["CO_ESCOLA", col]]
        .drop_duplicates(subset=["CO_ESCOLA"])
        .set_index("CO_ESCOLA")[col]
    )


def aplicar_cre_por_municipio(df: pd.DataFrame, mapa_muni_cre: dict) -> pd.DataFrame:
    df = df.copy()
    if "CRE" not in df.columns:
        df["CRE"] = pd.NA
    col_mun = _coluna_municipio(df)
    if col_mun and mapa_muni_cre:
        mask_sem_cre = df["CRE"].isna()
        municipios_normalizados = df.loc[mask_sem_cre, col_mun].apply(
            normalizar_texto)
        df.loc[mask_sem_cre, "CRE"] = municipios_normalizados.map(
            mapa_muni_cre)

    # Normalizar nomes curtos de CRE para nomes completos
    mapa_cre_completo = _mapa_cre_completo_cached()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df

