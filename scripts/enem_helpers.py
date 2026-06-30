"""Helpers compartilhados - pipeline ENEM MS."""
from __future__ import annotations

import gc
import re
import unicodedata

import numpy as np
import pandas as pd

from enem_config import (
    AREA_KEYS,
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


def normalizar_nome_escola(texto) -> str:
    texto = normalizar_texto(texto)
    if not texto:
        return ""

    # Corrige variantes comuns de codificacao/abreviacao antes da canonizacao.
    texto = re.sub(r"\bPROF A\b|\bPROF O\b", "PROF", texto)
    texto = re.sub(r"\bPROFAS?\b|\bPROFS?\b", "PROF", texto)
    texto = re.sub(r"\bESCOLA CIVICO MILITAR\b", "ECIM", texto)
    texto = re.sub(r"\bESCOLA CIVICO\b\s+\bMILITAR\b", "ECIM", texto)
    texto = re.sub(r"\bCIVICO MILITAR\b", "ECIM", texto)

    # Canoniza expressoes comuns para aumentar a taxa de casamento
    # entre planilhas da SED e cadastro auxiliar.
    subs = [
        (r"\bESCOLA ESTADUAL\b", "EE"),
        (r"\bESC EST\b", "EE"),
        (r"\bESCOLA\b", "EE"),
        (r"\bCENTRO ESTADUAL DE EDUCACAO PROFISSIONAL\b", "CEEP"),
        (r"\bCENTRO DE EDUCACAO PROFISSIONAL\b", "CEEP"),
        (r"\bCENTRO ESTADUAL DE EDUCACAO DE JOVENS E ADULTOS\b", "CEEJA"),
        (r"\bCENTRO DE EDUCACAO DE JOVENS E ADULTOS\b", "CEEJA"),
        (r"\bPROFESSORA\b", "PROF"),
        (r"\bPROFESSOR\b", "PROF"),
        (r"\bPROFA\b", "PROF"),
        (r"\bPROF\b", "PROF"),
        (r"\bPADRE\b", "PE"),
        (r"\bPE\b", "PE"),
        (r"\bPRESIDENTE\b", "PRES"),
        (r"\bDEPUTADO\b", "DEP"),
        (r"\bDEP\b", "DEP"),
        (r"\bCORONEL\b", "CEL"),
        (r"\bCEL\b", "CEL"),
        (r"\bMARECHAL\b", "MAL"),
        (r"\bMAL\b", "MAL"),
        (r"\bDOUTORA\b", "DRA"),
        (r"\bDOUTOR\b", "DR"),
        (r"\bIRMA\b", "IRMA"),
        (r"\bIRMAO\b", "IRMA"),
        (r"\bDONA\b", "DONA"),
    ]
    for patt, repl in subs:
        texto = re.sub(patt, repl, texto)

    # Equaliza sufixos administrativos que aparecem numa base e na outra nao.
    texto = re.sub(r"\bEE\s+EE\b", "EE", texto)
    texto = re.sub(r"\bECIM\b", "EE", texto)
    texto = re.sub(r"\bEXTENSAO\b.*$", "", texto)
    texto = re.sub(r"\bANEXO\b.*$", "", texto)
    texto = re.sub(r"\bSALA\b.*$", "", texto)
    texto = re.sub(r"\bMS\b$", "", texto)

    # Remove stopwords pouco informativas que variam entre bases.
    texto = re.sub(r"\bDE\b|\bDO\b|\bDA\b|\bDOS\b|\bDAS\b", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


_ESCOLA_ALIAS_MANUAL = {
    (normalizar_texto("Dois Irmaos do Buriti"), normalizar_nome_escola("EE PROFª. ESTEFANA CENTURION GAMBARRA")): {
        "co_escola": 50002155,
        "nome_canonico": "EE ESTEFANA CENTURION GAMBARRA",
    },
    (normalizar_texto("Campo Grande"), normalizar_nome_escola("EE PROFª. IGNÊS DE LAMÔNICA GUIMARÃES")): {
        "co_escola": 50005340,
        "nome_canonico": "EE PROFª. IGNÊS DE LAMÔNICA GUIMARÃES",
    },
    (normalizar_texto("Campo Grande"), normalizar_nome_escola("CENTRO ESTADUAL DE EDUCAÇÃO PROFISSIONAL PE. JOÃO GREINER")): {
        "co_escola": 50006053,
        "nome_canonico": "EE PE. JOÃO GREINER",
    },
    (normalizar_texto("Jardim"), normalizar_nome_escola("EE PROF. ANTÔNIO PINTO PEREIRA")): {
        "co_escola": 50014625,
        "nome_canonico": "EE ANTÔNIO PINTO PEREIRA",
    },
    (normalizar_texto("Coxim"), normalizar_nome_escola("EE VIRIATO BANDEIRA")): {
        "co_escola": 50003542,
        "nome_canonico": "EE VIRIATO BANDEIRA",
    },
    (normalizar_texto("Navirai"), normalizar_nome_escola("EE JURACY ALVES CARDOSO")): {
        "co_escola": 50021354,
        "nome_canonico": "EE JURACY ALVES CARDOSO",
    },
    (normalizar_texto("Maracaju"), normalizar_nome_escola("EE PADRE CONSTANTINO DE MONTE")): {
        "co_escola": 50018035,
        "nome_canonico": "EE PADRE CONSTANTINO DE MONTE",
    },
    (normalizar_texto("Maracaju"), normalizar_nome_escola("EE CÍVICO-MILITAR CORONEL LIMA DE FIGUEIREDO")): {
        "co_escola": 50018019,
        "nome_canonico": "EE CEL. LIMA DE FIGUEIREDO",
    },
}

_ESCOLA_OBS_OFERTA = {
    50013378: "oferta apenas EJA e/ou Ensino Fundamental",
    50015770: "oferta apenas EJA e/ou Ensino Fundamental",
}

_ESCOLA_CADASTRO_MANUAL = {
    50003500: {
        "NOME_ESCOLA": "EE PEDRO MENDES FONTOURA",
        "MUNICIPIO_CRES": "Coxim",
        "CRE": pd.NA,
    },
    50004352: {
        "NOME_ESCOLA": "EE BERNARDINO FERREIRA DA CUNHA",
        "MUNICIPIO_CRES": "Sao Gabriel do Oeste",
        "CRE": pd.NA,
    },
    50005340: {
        "NOME_ESCOLA": "CENTRO DE EDUCACAO DE JOVENS E ADULTOS PROFª IGNES DE LAMONICA GUIMARAES - CEEJA-MS",
        "MUNICIPIO_CRES": "Campo Grande",
        "CRE": "SED",
    },
    50006355: {
        "NOME_ESCOLA": "EE 11 DE OUTUBRO",
        "MUNICIPIO_CRES": "Campo Grande",
        "CRE": "SED",
    },
    50015354: {
        "NOME_ESCOLA": "EE DR FERNANDO CORREA DA COSTA",
        "MUNICIPIO_CRES": "Aral Moreira",
        "CRE": pd.NA,
    },
    50018353: {
        "NOME_ESCOLA": "EE DEP. FERNANDO C. CAPIBERIBE SALDANHA",
        "MUNICIPIO_CRES": "Ponta Pora",
        "CRE": pd.NA,
    },
    50018035: {
        "NOME_ESCOLA": "EE PADRE CONSTANTINO DE MONTE",
        "MUNICIPIO_CRES": "Maracaju",
        "CRE": pd.NA,
    },
    50003542: {
        "NOME_ESCOLA": "EE VIRIATO BANDEIRA",
        "MUNICIPIO_CRES": "Coxim",
        "CRE": pd.NA,
    },
    50021354: {
        "NOME_ESCOLA": "EE JURACY ALVES CARDOSO",
        "MUNICIPIO_CRES": "Navirai",
        "CRE": pd.NA,
    },
}


def alias_manual_escola(municipio, nome_escola) -> dict | None:
    key = (normalizar_texto(municipio), normalizar_nome_escola(nome_escola))
    alias = _ESCOLA_ALIAS_MANUAL.get(key)
    if not alias:
        return None
    return {
        "co_escola": float(alias["co_escola"]),
        "nome_canonico": alias["nome_canonico"],
        "esc_norm_canon": normalizar_nome_escola(alias["nome_canonico"]),
    }


def observacao_oferta_escola(co_escola) -> str | None:
    try:
        codigo = int(float(co_escola))
    except (TypeError, ValueError):
        return None
    return _ESCOLA_OBS_OFERTA.get(codigo)


def nome_exibicao_escola(co_escola, nome_escola) -> str:
    if pd.isna(nome_escola):
        nome_base = ""
    else:
        nome_base = str(nome_escola).strip()
    obs = observacao_oferta_escola(co_escola)
    if obs and nome_base:
        return f"{nome_base} ({obs})"
    return nome_base


def _complementar_cadastro_manual(cres: pd.DataFrame) -> pd.DataFrame:
    manual = pd.DataFrame(
        [{"CO_ESCOLA": float(co_escola), **meta} for co_escola, meta in _ESCOLA_CADASTRO_MANUAL.items()]
    )
    if cres.empty:
        return manual
    base = pd.concat([cres, manual], ignore_index=True)
    return base.drop_duplicates(subset=["CO_ESCOLA"], keep="last")


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
        return {"SED": _nome_cre_polo("SED")}

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
                polo["SED"] = _nome_cre_polo("SED")
                continue
            if " - " not in s:
                continue
            code, name = s.split(" - ", 1)
            polo[code.strip().upper()] = _nome_cre_polo(_formatar_polo(name))

    polo.setdefault("SED", _nome_cre_polo("SED"))
    return polo


def _get_cre_polo_map() -> dict[str, str]:
    global _CRE_POLO_MAP
    if _CRE_POLO_MAP is None:
        _CRE_POLO_MAP = carregar_mapa_cre_polo()
    return _CRE_POLO_MAP


def cre_curto(cre) -> str:
    sed = _get_cre_polo_map().get("SED", _nome_cre_polo("SED"))
    if cre is None or (isinstance(cre, float) and np.isnan(cre)):
        return sed
    s = str(cre).strip()
    if not s:
        return sed
    if s.upper() == "CRE SED":
        return "CRE SED"

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
    """Normaliza schema hibrido 2019-2023 vs 2024+ antes dos agregados."""
    df = df_ano.copy()
    ano = int(df["NU_ANO"].iloc[0])

    if "CO_ESCOLA" not in df.columns:
        df["CO_ESCOLA"] = pd.NA
    if "TP_ST_CONCLUSAO" not in df.columns:
        df["TP_ST_CONCLUSAO"] = pd.NA

    if ano >= 2024:
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
    m_novo = df["NU_ANO"] >= 2024
    df.loc[m_novo, "CONCLUINTE"] = df.loc[m_novo, "COM_ESCOLA"]

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
        vazio = pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])
        return _complementar_cadastro_manual(vazio)

    xl = pd.ExcelFile(CRES_XLSX)
    sheet = next((s for s in xl.sheet_names if "INEP" in s.upper()), xl.sheet_names[0])
    cres = pd.read_excel(CRES_XLSX, sheet_name=sheet)
    col_cod = next((c for c in cres.columns if "INEP" in str(c).upper()), None)
    if col_cod is None:
        vazio = pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])
        return _complementar_cadastro_manual(vazio)

    col_esc = "UNIDADE ESCOLAR " if "UNIDADE ESCOLAR " in cres.columns else "UNIDADE ESCOLAR"
    col_mun = _col_por_prefixo(cres.columns, "MUNICIPIO") or "MUNICIPIO"
    out = cres[[col_cod, "CRE", col_mun, col_esc]].copy()
    out[col_cod] = pd.to_numeric(out[col_cod], errors="coerce")
    out = out.dropna(subset=[col_cod]).drop_duplicates(subset=[col_cod])
    out = out.rename(columns={col_cod: "CO_ESCOLA", col_mun: "MUNICIPIO_CRES", col_esc: "NOME_ESCOLA"})
    return _complementar_cadastro_manual(out)


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
    if "MUNICIPIO_CRES" in df.columns and "NO_MUNICIPIO_ESC" in df.columns:
        df["MUNICIPIO_CRES"] = df["MUNICIPIO_CRES"].fillna(df["NO_MUNICIPIO_ESC"])
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


def _sheet_concluintes_consolidada(xls: pd.ExcelFile) -> str:
    candidatos = []
    for name in xls.sheet_names:
        m = re.fullmatch(r"(\d{4})-2019", str(name).strip())
        if m:
            candidatos.append((int(m.group(1)), name))
    if candidatos:
        return max(candidatos)[1]
    return xls.sheet_names[0]


def _concluintes_de_xlsx() -> tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.ExcelFile(CONCLUINTES_XLSX)
    sheet_name = _sheet_concluintes_consolidada(xl)
    raw = pd.read_excel(CONCLUINTES_XLSX, sheet_name=sheet_name)
    raw["NU_ANO"] = pd.to_numeric(raw["NU_ANO"], errors="coerce").astype("Int64")
    raw["Concluintes"] = pd.to_numeric(raw["Concluintes"], errors="coerce").fillna(0).astype(int)
    if "CO_ESCOLA" in raw.columns:
        raw["CO_ESCOLA"] = pd.to_numeric(raw["CO_ESCOLA"], errors="coerce")
    else:
        raw["CO_ESCOLA"] = pd.NA
    totais = raw.groupby("NU_ANO", observed=True)["Concluintes"].sum().reset_index()
    totais.columns = ["NU_ANO", "Concluintes"]

    col_mun = _col_por_prefixo(raw.columns, "MUNICIPIO") or COL_MUNICIPIO
    col_esc = "Unidade Escolar"

    cres = carregar_cres()
    raw["MUN_NORM"] = raw[col_mun].map(normalizar_texto)
    raw["ESC_NORM"] = raw[col_esc].map(normalizar_nome_escola)
    aliases = raw.apply(lambda r: alias_manual_escola(r[col_mun], r[col_esc]), axis=1)
    raw["CO_ESCOLA_ALIAS"] = aliases.map(lambda x: x["co_escola"] if isinstance(x, dict) else pd.NA)
    raw["NOME_ESCOLA_ALIAS"] = aliases.map(lambda x: x["nome_canonico"] if isinstance(x, dict) else pd.NA)
    raw["ESC_NORM_MERGE"] = aliases.map(lambda x: x["esc_norm_canon"] if isinstance(x, dict) else pd.NA)
    raw["ESC_NORM_MERGE"] = raw["ESC_NORM_MERGE"].fillna(raw["ESC_NORM"])
    if not cres.empty:
        cres = cres.copy()
        cres["MUN_NORM"] = cres["MUNICIPIO_CRES"].map(normalizar_texto)
        cres["ESC_NORM"] = cres["NOME_ESCOLA"].map(normalizar_nome_escola)
        cols_merge = ["CO_ESCOLA", "MUN_NORM", "ESC_NORM", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"]
        por_esc = raw.merge(
            cres[cols_merge].rename(columns={"ESC_NORM": "ESC_NORM_MERGE"}),
            on=["MUN_NORM", "ESC_NORM_MERGE"],
            how="left",
            suffixes=("", "_CRES"),
        )
        por_esc["CO_ESCOLA"] = (
            por_esc["CO_ESCOLA"]
            .fillna(por_esc["CO_ESCOLA_ALIAS"])
            .fillna(por_esc.get("CO_ESCOLA_CRES"))
        )
        if "NOME_ESCOLA" in por_esc.columns:
            por_esc[col_esc] = por_esc[col_esc].fillna(por_esc["NOME_ESCOLA"])
        m_alias = por_esc["NOME_ESCOLA_ALIAS"].notna()
        if m_alias.any():
            por_esc.loc[m_alias, col_esc] = por_esc.loc[m_alias, "NOME_ESCOLA_ALIAS"]
        if "MUNICIPIO_CRES" in por_esc.columns:
            por_esc[col_mun] = por_esc[col_mun].fillna(por_esc["MUNICIPIO_CRES"])
    else:
        por_esc = raw.copy()
        por_esc["CO_ESCOLA"] = por_esc["CO_ESCOLA_ALIAS"]
    com_codigo = por_esc[por_esc["CO_ESCOLA"].notna()].copy()
    sem_codigo = por_esc[por_esc["CO_ESCOLA"].isna()].copy()

    partes = []
    if not com_codigo.empty:
        agg_cod = (
            com_codigo.groupby(["NU_ANO", "CO_ESCOLA"], observed=True, dropna=False)
            .agg(
                Concluintes=("Concluintes", "sum"),
                **{
                    col_mun: (col_mun, lambda s: s.dropna().iloc[0] if not s.dropna().empty else pd.NA),
                    col_esc: (col_esc, lambda s: s.dropna().iloc[0] if not s.dropna().empty else pd.NA),
                },
            )
            .reset_index()
        )
        partes.append(agg_cod)

    if not sem_codigo.empty:
        agg_sem = (
            sem_codigo.groupby(["NU_ANO", "CO_ESCOLA", col_mun, col_esc], observed=True, dropna=False)["Concluintes"]
            .sum()
            .reset_index()
        )
        partes.append(agg_sem)

    agg = pd.concat(partes, ignore_index=True) if partes else por_esc.iloc[0:0].copy()
    agg = agg.rename(columns={col_mun: COL_MUNICIPIO})
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


_PRES_AREA_MAP = {
    "CN": "TP_PRESENCA_CN",
    "CH": "TP_PRESENCA_CH",
    "LC": "TP_PRESENCA_LC",
    "MT": "TP_PRESENCA_MT",
}


def filtrar_valido_area(df: pd.DataFrame, area_key: str) -> pd.DataFrame:
    """Retorna o subconjunto de concluintes que realizaram a prova da área."""
    if area_key == "RED":
        mask = df["CONCLUINTE"] & ~df["ELIM_RED"]
    else:
        pres_col = _PRES_AREA_MAP[area_key]
        mask = df["CONCLUINTE"] & (df[pres_col] == 1)
    return df[mask]


def limpar():
    gc.collect()
