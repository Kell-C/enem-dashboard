"""
Cadastro CRE — 1ª aba da planilha mapeia código INEP (CO_ESCOLA) → escola, município e CRE.
"""

from __future__ import annotations

import os
import unicodedata

import re

import pandas as pd

_ROOT = os.path.dirname(os.path.abspath(__file__))

_CRE_NUMERO_RE = re.compile(r"CRE\s*(\d+)", re.IGNORECASE)

MAP_CRE_COMPLETO = {
    "CRE 01": "CRE 01 - CAMPO GRANDE",
    "CRE 02": "CRE 02 - CAMPO GRANDE",
    "CRE 03": "CRE 03 - CAMPO GRANDE",
    "CRE 04": "CRE 04 - CAMPO GRANDE",
    "CRE 05": "CRE 05 - DOURADOS",
    "CRE 06": "CRE 06 - CORUMBÁ",
    "CRE 07": "CRE 07 - TRÊS LAGOAS",
    "CRE 08": "CRE 08 - PONTA PORÃ",
    "CRE 09": "CRE 09 - AQUIDAUANA",
    "CRE 10": "CRE 10 - PARANAÍBA",
    "CRE 11": "CRE 11 - NAVIRAÍ",
    "CRE 12": "CRE 12 - NOVA ANDRADINA",
    "CRE 13": "CRE 13 - CHAPADÃO DO SUL",
    "CRE 14": "CRE 14 - MARACAJU",
    "CRE 15": "CRE 15 - RIO BRILHANTE",
    "CRE 16": "CRE 16 - CAARAPÓ",
    "CRE 17": "CRE 17 - JARDIM",
    "CRE 18": "CRE 18 - BONITO",
    "CRE 19": "CRE 19 - MIRANDA",
    "CRE 20": "CRE 20 - COSTA RICA",
    "CRE 21": "CRE 21 - SÃO GABRIEL DO OESTE",
    "CRE 22": "CRE 22 - BATAGUASSU",
    "CRE 23": "CRE 23 - APOSTOLO",
    "CRE 24": "CRE 24 - ANASTÁCIO",
    "CRE 25": "CRE 25 - BELA VISTA",
    "CRE 26": "CRE 26 - COXIM",
    "CRE 27": "CRE 27 - PEDRO GOMES",
    "CRE 28": "CRE 28 - SONORA",
}


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


def resolve_arquivo_cres(explicit: str | None = None) -> str | None:
    if explicit and os.path.exists(explicit):
        return explicit
    env = os.getenv("ARQUIVO_CRES")
    if env and os.path.exists(env):
        return env
    for name in ("cres.xlsx", "cres__.xlsx", os.path.join("data", "cres.xlsx")):
        path = os.path.join(_ROOT, name)
        if os.path.exists(path):
            return path
    return None


def _find_col_cod(columns) -> str | None:
    for possivel in ["CÓD INEP", "COD INEP", "CÓD.INEP", "COD.INEP", "CO_ESCOLA", "INEP"]:
        if possivel in columns:
            return possivel
    return None


def nome_cre_curto(cre) -> str:
    """Exibe apenas o código: 'CRE 01', 'CRE 02', …"""
    if cre is None or (isinstance(cre, float) and pd.isna(cre)):
        return "—"
    texto = str(cre).strip()
    if not texto or texto.lower() in ("nan", "none", "<na>"):
        return "—"
    if " - " in texto:
        texto = texto.split(" - ", 1)[0].strip()
    m = _CRE_NUMERO_RE.search(texto)
    if m:
        return f"CRE {int(m.group(1)):02d}"
    return texto


def construir_mapa_cre_completo(arquivo: str | None = None) -> dict[str, str]:
    """Mapeia 'CRE 12' → 'CRE 12 - TRÊS LAGOAS' (ou nome completo equivalente)."""
    mapa = dict(MAP_CRE_COMPLETO)
    arquivo = resolve_arquivo_cres(arquivo)
    if not arquivo:
        return mapa

    try:
        xl = pd.ExcelFile(arquivo)
        for sh in xl.sheet_names:
            df = pd.read_excel(arquivo, sheet_name=sh)
            if "CRE" not in df.columns:
                continue
            for val in df["CRE"].dropna().unique():
                val = str(val).strip()
                if " - " in val:
                    codigo = val.split(" - ")[0].strip()
                    mapa[codigo] = val
                    mapa[val] = val
                elif val.startswith("CRE ") and val not in mapa:
                    mapa[val] = val
    except Exception:
        pass
    return mapa


def carregar_cres_escolas(arquivo: str | None = None) -> pd.DataFrame:
    """1ª aba: CO_ESCOLA, CRE, MUNICIPIO_CRES, NOME_ESCOLA (chave = código INEP)."""
    empty = pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])
    arquivo = resolve_arquivo_cres(arquivo)
    if not arquivo:
        return empty

    cres = pd.read_excel(arquivo, sheet_name=0)
    col_cod = _find_col_cod(cres.columns)
    if col_cod is None:
        return empty

    col_esc = "UNIDADE ESCOLAR " if "UNIDADE ESCOLAR " in cres.columns else "UNIDADE ESCOLAR"
    if col_esc not in cres.columns:
        return empty
    col_mun = "MUNICÍPIO" if "MUNICÍPIO" in cres.columns else "MUNICIPIO"
    if col_mun not in cres.columns:
        return empty
    if "CRE" not in cres.columns:
        return empty

    cres[col_cod] = pd.to_numeric(cres[col_cod], errors="coerce").astype("Int64")
    cres = cres[[col_cod, "CRE", col_mun, col_esc]].dropna(subset=[col_cod])
    cres = cres.drop_duplicates(subset=[col_cod])

    mapa_cre = construir_mapa_cre_completo(arquivo)
    cres["CRE"] = cres["CRE"].astype(str).str.strip().map(mapa_cre).fillna(cres["CRE"])

    return cres.rename(columns={
        col_cod: "CO_ESCOLA",
        col_mun: "MUNICIPIO_CRES",
        col_esc: "NOME_ESCOLA",
    })


def carregar_mapa_municipio_cre(arquivo: str | None = None) -> dict[str, str]:
    """Município normalizado → CRE (nome completo quando disponível)."""
    arquivo = resolve_arquivo_cres(arquivo)
    if not arquivo:
        return {}

    mapa_cre = construir_mapa_cre_completo(arquivo)
    mapa: dict[str, str] = {}

    try:
        xl = pd.ExcelFile(arquivo)
        sheets: list[pd.DataFrame] = []
        if "CREs" in xl.sheet_names:
            sheets.append(pd.read_excel(arquivo, sheet_name="CREs"))
        sheets.append(pd.read_excel(arquivo, sheet_name=0))

        for df in sheets:
            col_mun = "MUNICÍPIO" if "MUNICÍPIO" in df.columns else "MUNICIPIO"
            if col_mun not in df.columns or "CRE" not in df.columns:
                continue
            for _, row in df.iterrows():
                municipio = str(row.get(col_mun, "")).strip()
                cre = str(row.get("CRE", "")).strip()
                if municipio and cre:
                    cre_norm = mapa_cre.get(cre, mapa_cre.get(cre.split(" - ")[0].strip(), cre))
                    mapa[normalizar_texto(municipio)] = cre_norm
    except Exception:
        pass
    return mapa


def mapa_inep_por_nome_escola(arquivo: str | None = None) -> pd.DataFrame:
    """Fallback: nome normalizado da escola → CO_ESCOLA (via cadastro CRE)."""
    cres = carregar_cres_escolas(arquivo)
    if cres.empty:
        return pd.DataFrame(columns=["esc_norm", "CO_ESCOLA"])
    out = cres[["NOME_ESCOLA", "CO_ESCOLA"]].dropna(subset=["CO_ESCOLA"]).copy()
    out["esc_norm"] = out["NOME_ESCOLA"].map(normalizar_texto)
    return out.drop_duplicates(subset=["esc_norm"])[["esc_norm", "CO_ESCOLA"]]
