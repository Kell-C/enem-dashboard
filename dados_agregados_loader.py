"""
Carregamento de dados agregados para o dashboard ENEM v15.

Fontes suportadas (variável de ambiente DATA_SOURCE):
  - local   : arquivos parquet em PASTA_AGREGADOS (padrão)
  - supabase: tabelas PostgreSQL no Supabase

Os agregados são produzidos por gerar_dados_agregados.py.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import numpy as np
import pandas as pd
import streamlit as st

COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]

TABELAS = {
    "sumario_executivo": "sumario_executivo.parquet",
    "participacao_ano": "participacao_ano.parquet",
    "participacao_cre": "participacao_cre.parquet",
    "participacao_uf": "participacao_uf.parquet",
    "desempenho": "desempenho.parquet",
    "desempenho_uf": "desempenho_uf.parquet",
    "escolas_2024": "escolas_2024.parquet",
    "territorial": "territorial.parquet",
    "municipios": "municipios.parquet",
    "panorama_nacional": "panorama_nacional.parquet",
    "referencias": "referencias.parquet",
    "evolucao_cre": "evolucao_cre.parquet",
    "evolucao_municipios": "evolucao_municipios.parquet",
    "distribuicao_ms": "distribuicao_ms.parquet",
    "distribuicao_cre": "distribuicao_cre.parquet",
    "distribuicao_municipio": "distribuicao_municipio.parquet",
    "histograma_ms": "histograma_ms.parquet",
}

NOTAS_INDIVIDUAIS_ARQUIVO = "notas_individuais_ms.parquet"
NOTAS_INDIVIDUAIS_ARQUIVO_LEGACY = "notas_individuais_2024_ms.parquet"
HIST_BIN_WIDTH = 50
HIST_BIN_MAX = 1000
HIST_BIN_EDGES = list(range(0, HIST_BIN_MAX + 1, HIST_BIN_WIDTH))
AREAS_HISTOGRAMA = COLS_NOTAS + ["MEDIA_GERAL"]

_MEDIA_MAP = {
    "NU_NOTA_CN": "media_nu_nota_cn",
    "NU_NOTA_CH": "media_nu_nota_ch",
    "NU_NOTA_LC": "media_nu_nota_lc",
    "NU_NOTA_MT": "media_nu_nota_mt",
    "NU_NOTA_REDACAO": "media_nu_nota_redacao",
    "MEDIA_GERAL": "media_media_geral",
}

# Médias nacionais (rede estadual MS vs BR) em sumario_executivo.parquet
_MEDIA_MAP_BR_SUMARIO = {
    "NU_NOTA_CN": "media_br_nu_nota_cn",
    "NU_NOTA_CH": "media_br_nu_nota_ch",
    "NU_NOTA_LC": "media_br_nu_nota_lc",
    "NU_NOTA_MT": "media_br_nu_nota_mt",
    "NU_NOTA_REDACAO": "media_br_nu_nota_redacao",
    "MEDIA_GERAL": "media_br_media_geral",
}


def get_pasta_agregados() -> str:
    return os.getenv(
        "PASTA_AGREGADOS",
        os.path.join(os.path.dirname(__file__), "data", "agregados"),
    )


def get_data_source() -> str:
    return os.getenv("DATA_SOURCE", "local").strip().lower()


def _normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "ano" in out.columns:
        out["ano"] = pd.to_numeric(out["ano"], errors="coerce")
        out = out.dropna(subset=["ano"])
        out["ano"] = out["ano"].astype(int)
    if "dependencia" in out.columns:
        out["dependencia"] = out["dependencia"].astype(str)
    if "uf" in out.columns:
        out["uf"] = out["uf"].astype(str).str.upper()
    return out


def _carregar_parquet_local(nome: str) -> pd.DataFrame:
    pasta = get_pasta_agregados()
    arquivo = TABELAS.get(nome, f"{nome}.parquet")
    caminho = os.path.join(pasta, arquivo)
    if not os.path.exists(caminho):
        return pd.DataFrame()
    return _normalizar_df(pd.read_parquet(caminho))


def _get_supabase_config() -> dict[str, str]:
    try:
        sec = st.secrets.get("supabase", st.secrets)
        return {
            "host": sec["host"],
            "port": str(sec.get("port", "6543")),
            "dbname": sec.get("db", "postgres"),
            "user": sec["user"],
            "password": sec["password"],
        }
    except (KeyError, FileNotFoundError, AttributeError):
        return {
            "host": os.getenv("SUPABASE_HOST", ""),
            "port": os.getenv("SUPABASE_PORT", "6543"),
            "dbname": os.getenv("SUPABASE_DB", "postgres"),
            "user": os.getenv("SUPABASE_USER", ""),
            "password": os.getenv("SUPABASE_PASS", ""),
        }


def _carregar_supabase(nome: str) -> pd.DataFrame:
    import psycopg2

    cfg = _get_supabase_config()
    if not cfg.get("host") or not cfg.get("password"):
        st.error(
            "Credenciais Supabase não configuradas. Defina secrets [supabase] ou "
            "variáveis SUPABASE_HOST / SUPABASE_PASS."
        )
        st.stop()

    conn = psycopg2.connect(**cfg, sslmode="require")
    try:
        df = pd.read_sql(f'SELECT * FROM "{nome}"', conn)
    finally:
        conn.close()
    return _normalizar_df(df)


@st.cache_data(show_spinner="Carregando dados agregados...", ttl=3600)
def carregar_tabela(nome: str) -> pd.DataFrame:
    if get_data_source() == "supabase":
        return _carregar_supabase(nome)
    return _carregar_parquet_local(nome)


@st.cache_data(show_spinner="Carregando conjunto agregado...", ttl=3600)
def carregar_todas_tabelas() -> dict[str, pd.DataFrame]:
    return {nome: carregar_tabela(nome) for nome in TABELAS}


def _medias_linha(
    row: pd.Series,
    col_map: Optional[dict[str, str]] = None,
) -> dict[str, float]:
    col_map = col_map or _MEDIA_MAP
    out: dict[str, float] = {}
    for col_nota, col_media in col_map.items():
        val = row.get(col_media, np.nan)
        if pd.isna(val) and col_nota == "MEDIA_GERAL":
            val = row.get("media_geral", np.nan)
        out[col_nota] = float(val) if pd.notna(val) else np.nan
    return out


def _expandir_contagem(
    n: int,
    ano: int,
    dep: str,
    uf: str,
    medias: dict[str, float],
    *,
    cre: Optional[str] = None,
    municipio: Optional[str] = None,
    co_escola: Optional[int] = None,
    nome_escola: Optional[str] = None,
    municipio_cres: Optional[str] = None,
    presente: bool = True,
) -> list[dict[str, Any]]:
    if n <= 0:
        return []
    base: dict[str, Any] = {
        "NU_ANO": int(ano),
        "SG_UF_ESC": uf,
        "SG_UF_PROVA": uf,
        "DEP_ADM": dep,
        "CATEGORIA_PARTICIPACAO": "presente_ambos_dias" if presente else "inscrito",
        "TP_ST_CONCLUSAO": 2,
        "IN_TREINEIRO": 0,
        **medias,
    }
    if cre is not None:
        base["CRE"] = cre
    if municipio is not None:
        base["NO_MUNICIPIO_ESC"] = municipio
    if co_escola is not None:
        base["CO_ESCOLA"] = co_escola
    if nome_escola is not None:
        base["NOME_ESCOLA"] = nome_escola
    if municipio_cres is not None:
        base["MUNICIPIO_CRES"] = municipio_cres
    return [base.copy() for _ in range(int(n))]


def _desempenho_lookup(df_desempenho: pd.DataFrame, ano: int, dep: str) -> dict[str, float]:
    """Médias nacionais por dependência (tabela desempenho — todas as UFs)."""
    sub = df_desempenho[
        (df_desempenho["ano"] == ano) & (df_desempenho["dependencia"] == dep)
    ]
    if sub.empty:
        return {c: np.nan for c in COLS_NOTAS + ["MEDIA_GERAL"]}
    return _medias_linha(sub.iloc[0])


def _sumario_lookup(
    df_sumario: pd.DataFrame,
    ano: int,
    *,
    br: bool = False,
) -> Optional[dict[str, float]]:
    """Médias MS (ou BR) da rede estadual em sumario_executivo.parquet."""
    sub = df_sumario[df_sumario["ano"] == ano]
    if sub.empty:
        return None
    col_map = _MEDIA_MAP_BR_SUMARIO if br else _MEDIA_MAP
    return _medias_linha(sub.iloc[0], col_map)


def _medias_ms_por_ano(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
    dep: str,
) -> dict[str, float]:
    """Médias atribuídas aos registros sintéticos de MS.

    Rede Estadual: sumario_executivo (médias de MS). Demais dependências:
    fallback em desempenho (média nacional da dependência).
    """
    df_sum = tabelas.get("sumario_executivo", pd.DataFrame())
    if dep == "Estadual" and not df_sum.empty:
        medias = _sumario_lookup(df_sum, ano, br=False)
        if medias is not None:
            return medias
    df_desemp = tabelas.get("desempenho", pd.DataFrame())
    return _desempenho_lookup(df_desemp, ano, dep)


def _finalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    for c in COLS_NOTAS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    if "MEDIA_GERAL" in df.columns:
        df["MEDIA_GERAL"] = pd.to_numeric(df["MEDIA_GERAL"], errors="coerce").astype("float32")
    return df


def reconstruir_participacao_ms(
    tabelas: dict[str, pd.DataFrame],
    anos_sel: list[int],
    deps: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Contagens MS (inscritos vs presentes) a partir de participacao_ano."""
    df_part = tabelas.get("participacao_ano", pd.DataFrame())
    bruta_rows: list[dict[str, Any]] = []
    filt_rows: list[dict[str, Any]] = []

    if df_part.empty:
        return pd.DataFrame(), pd.DataFrame()

    sub = df_part[df_part["ano"].isin(anos_sel) & df_part["dependencia"].isin(deps)]
    for _, r in sub.iterrows():
        medias = _medias_ms_por_ano(tabelas, int(r["ano"]), r["dependencia"])
        bruta_rows.extend(
            _expandir_contagem(
                int(r.get("inscritos", 0) or 0),
                int(r["ano"]),
                r["dependencia"],
                "MS",
                medias,
                presente=False,
            )
        )
        filt_rows.extend(
            _expandir_contagem(
                int(r.get("presentes_filt", r.get("presentes", 0)) or 0),
                int(r["ano"]),
                r["dependencia"],
                "MS",
                medias,
                presente=True,
            )
        )
    return _finalizar_df(pd.DataFrame(bruta_rows)), _finalizar_df(pd.DataFrame(filt_rows))


def participacao_ms_por_ano(
    tabelas: dict[str, pd.DataFrame],
    anos_sel: list[int],
    dependencia: str = "Estadual",
) -> pd.DataFrame:
    """Série anual MS: concluintes, inscritos, presentes e taxas."""
    df = tabelas.get("participacao_ano", pd.DataFrame())
    if df.empty or not anos_sel:
        return pd.DataFrame()
    sub = df[
        (df["ano"].isin([int(a) for a in anos_sel]))
        & (df["dependencia"] == dependencia)
    ].copy()
    if sub.empty:
        return sub
    sub["Concluintes"] = pd.to_numeric(sub.get("concluintes"), errors="coerce")
    sub["Inscritos"] = pd.to_numeric(sub.get("inscritos"), errors="coerce")
    sub["Presentes"] = pd.to_numeric(
        sub.get("presentes_filt", sub.get("presentes")), errors="coerce",
    )
    if "tx_inscricao" in sub.columns:
        sub["Tx_Inscrição"] = pd.to_numeric(sub["tx_inscricao"], errors="coerce")
    else:
        sub["Tx_Inscrição"] = sub["Inscritos"] / sub["Concluintes"].replace(0, pd.NA) * 100
    if "tx_part_efetiva" in sub.columns:
        sub["Tx_Part_Efetiva"] = pd.to_numeric(sub["tx_part_efetiva"], errors="coerce")
    else:
        sub["Tx_Part_Efetiva"] = sub["Presentes"] / sub["Concluintes"].replace(0, pd.NA) * 100
    sub["Tx_Inscrição"] = sub["Tx_Inscrição"].round(1)
    sub["Tx_Part_Efetiva"] = sub["Tx_Part_Efetiva"].round(1)
    return sub.sort_values("ano").reset_index(drop=True)


def inscritos_estadual_ms(
    tabelas: dict[str, pd.DataFrame],
    anos_sel: list[int],
) -> int:
    """Soma inscritos estaduais MS (coluna participacao_ano.inscritos).

    Regras por ano (gerar_dados_agregados): 2019–2023 concluintes EM
    (TP_ST_CONCLUSAO == 2); 2024 todos os inscritos em escolas estaduais de MS.
    """
    df_part = tabelas.get("participacao_ano", pd.DataFrame())
    if df_part.empty:
        return 0
    sub = df_part[
        (df_part["ano"].isin(anos_sel)) & (df_part["dependencia"] == "Estadual")
    ]
    return int(sub["inscritos"].sum())


def reconstruir_ms_enriquecido(
    tabelas: dict[str, pd.DataFrame],
    anos_sel: list[int],
    deps: list[str],
) -> pd.DataFrame:
    """Base MS com CRE/município/escola para abas territoriais e escolas."""
    rows: list[dict[str, Any]] = []
    df_evol_cre = tabelas.get("evolucao_cre", pd.DataFrame())
    df_evol_muni = tabelas.get("evolucao_municipios", pd.DataFrame())
    df_escolas = tabelas.get("escolas_2024", pd.DataFrame())

    if not df_evol_cre.empty:
        sub = df_evol_cre[
            df_evol_cre["ano"].isin(anos_sel) & df_evol_cre["dependencia"].isin(deps)
        ]
        for _, r in sub.iterrows():
            cre = r.get("CRE", r.get("cre"))
            rows.extend(
                _expandir_contagem(
                    int(r.get("estudantes", 0) or 0),
                    int(r["ano"]),
                    r["dependencia"],
                    "MS",
                    _medias_linha(r),
                    cre=str(cre) if pd.notna(cre) else None,
                    presente=True,
                )
            )

    if not df_evol_muni.empty:
        sub = df_evol_muni[
            df_evol_muni["ano"].isin(anos_sel) & df_evol_muni["dependencia"].isin(deps)
        ]
        for _, r in sub.iterrows():
            muni = r.get("NO_MUNICIPIO_ESC", r.get("municipio"))
            rows.extend(
                _expandir_contagem(
                    int(r.get("estudantes", 0) or 0),
                    int(r["ano"]),
                    r["dependencia"],
                    "MS",
                    _medias_linha(r),
                    municipio=str(muni) if pd.notna(muni) else None,
                    presente=True,
                )
            )

    if rows:
        return _finalizar_df(pd.DataFrame(rows))

    _, df_filt = reconstruir_participacao_ms(tabelas, anos_sel, deps)
    return df_filt


def reconstruir_escolas_2024_ms(
    tabelas: dict[str, pd.DataFrame],
    deps: list[str],
) -> pd.DataFrame:
    """Base MS por escola (2024) a partir de escolas_2024.parquet — evita duplicar CRE/município."""
    df_escolas = tabelas.get("escolas_2024", pd.DataFrame())
    if df_escolas.empty:
        return pd.DataFrame()

    sub = df_escolas[df_escolas["dependencia"].isin(deps)].copy()
    rows: list[dict[str, Any]] = []
    for _, r in sub.iterrows():
        medias = {
            "NU_NOTA_CN": r.get("media_cn", np.nan),
            "NU_NOTA_CH": r.get("media_ch", np.nan),
            "NU_NOTA_LC": r.get("media_lc", np.nan),
            "NU_NOTA_MT": r.get("media_mt", np.nan),
            "NU_NOTA_REDACAO": r.get("media_redacao", np.nan),
            "MEDIA_GERAL": r.get("media_geral", np.nan),
        }
        co = r.get("CO_ESCOLA")
        rows.extend(
            _expandir_contagem(
                int(r.get("estudantes", 0) or 0),
                2024,
                r["dependencia"],
                "MS",
                medias,
                co_escola=int(co) if pd.notna(co) else None,
                nome_escola=r.get("NOME_ESCOLA"),
                municipio=str(r.get("municipio", "")) or None,
                municipio_cres=str(r.get("municipio", "")) or None,
                cre=str(r.get("cre", "")) or None,
                presente=True,
            )
        )
    return _finalizar_df(pd.DataFrame(rows))


def linha_escola_2024(
    tabelas: dict[str, pd.DataFrame],
    co_escola: int,
    dep: str = "Estadual",
) -> Optional[pd.Series]:
    """Linha de escolas_2024.parquet com quantis pré-calculados (boxplots)."""
    df_escolas = tabelas.get("escolas_2024", pd.DataFrame())
    if df_escolas.empty:
        return None
    co = pd.to_numeric(co_escola, errors="coerce")
    if pd.isna(co):
        return None
    sub = df_escolas[
        (pd.to_numeric(df_escolas["CO_ESCOLA"], errors="coerce") == int(co))
        & (df_escolas["dependencia"] == dep)
    ]
    if sub.empty:
        return None
    return sub.iloc[0]


def inscritos_por_escola_2024(
    tabelas: dict[str, pd.DataFrame],
    dep: str = "Estadual",
) -> pd.DataFrame:
    """Inscritos por CO_ESCOLA (2024) a partir do agregado escolas_2024."""
    df_escolas = tabelas.get("escolas_2024", pd.DataFrame())
    if df_escolas.empty or "inscritos" not in df_escolas.columns:
        return pd.DataFrame(columns=["CO_ESCOLA", "Inscritos"])
    sub = df_escolas[df_escolas["dependencia"] == dep][["CO_ESCOLA", "inscritos"]].copy()
    sub = sub.rename(columns={"inscritos": "Inscritos"})
    sub["CO_ESCOLA"] = pd.to_numeric(sub["CO_ESCOLA"], errors="coerce")
    return sub.dropna(subset=["CO_ESCOLA"])


def reconstruir_bases_nacionais(
    tabelas: dict[str, pd.DataFrame],
    anos_sel: list[int],
    deps: Optional[list[str]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bases nacionais (UF) para panorama, referências BR e ranking."""
    df_part_uf = tabelas.get("participacao_uf", pd.DataFrame())
    df_desemp_uf = tabelas.get("desempenho_uf", pd.DataFrame())
    bruta_rows: list[dict[str, Any]] = []
    filt_rows: list[dict[str, Any]] = []

    if not df_part_uf.empty:
        sub = df_part_uf[df_part_uf["ano"].isin(anos_sel)]
        if deps:
            sub = sub[sub["dependencia"].isin(deps)]
        for _, r in sub.iterrows():
            uf = str(r.get("uf", r.get("UF", ""))).upper()
            if len(uf) != 2:
                continue
            dsub = df_desemp_uf[
                (df_desemp_uf["ano"] == int(r["ano"]))
                & (df_desemp_uf["dependencia"] == r["dependencia"])
                & (df_desemp_uf["uf"].astype(str).str.upper() == uf)
            ] if not df_desemp_uf.empty else pd.DataFrame()
            medias = _medias_linha(dsub.iloc[0]) if not dsub.empty else {
                c: np.nan for c in COLS_NOTAS + ["MEDIA_GERAL"]
            }
            bruta_rows.extend(
                _expandir_contagem(
                    int(r.get("inscritos", 0) or 0),
                    int(r["ano"]),
                    r["dependencia"],
                    uf,
                    medias,
                    presente=False,
                )
            )
            filt_rows.extend(
                _expandir_contagem(
                    int(r.get("presentes_filt", r.get("presentes", 0)) or 0),
                    int(r["ano"]),
                    r["dependencia"],
                    uf,
                    medias,
                    presente=True,
                )
            )
    elif not df_desemp_uf.empty:
        sub = df_desemp_uf[df_desemp_uf["ano"].isin(anos_sel)]
        if deps:
            sub = sub[sub["dependencia"].isin(deps)]
        for _, r in sub.iterrows():
            uf = str(r.get("uf", r.get("UF", ""))).upper()
            medias = _medias_linha(r)
            n = int(r.get("estudantes", 0) or 0)
            filt_rows.extend(
                _expandir_contagem(n, int(r["ano"]), r["dependencia"], uf, medias, presente=True)
            )
            bruta_rows.extend(
                _expandir_contagem(n, int(r["ano"]), r["dependencia"], uf, medias, presente=False)
            )

    return _finalizar_df(pd.DataFrame(bruta_rows)), _finalizar_df(pd.DataFrame(filt_rows))


_AREA_TO_STEM = {
    "NU_NOTA_CN": "nu_nota_cn",
    "NU_NOTA_CH": "nu_nota_ch",
    "NU_NOTA_LC": "nu_nota_lc",
    "NU_NOTA_MT": "nu_nota_mt",
    "NU_NOTA_REDACAO": "nu_nota_redacao",
    "MEDIA_GERAL": "media_geral",
}


def quantis_area(row: pd.Series, area: str) -> dict[str, float]:
    """Extrai Q1, mediana, Q3, média e n de uma linha de distribuicao_*.parquet."""
    stem = _AREA_TO_STEM.get(area, area.lower())
    q1 = row.get(f"q1_{stem}", row.get(f"q25_{stem}", np.nan))
    med = row.get(f"median_{stem}", row.get(f"q50_{stem}", np.nan))
    q3 = row.get(f"q3_{stem}", row.get(f"q75_{stem}", np.nan))
    mean = row.get(f"mean_{stem}", row.get(_MEDIA_MAP.get(area, ""), np.nan))
    n = row.get(f"n_{stem}", np.nan)
    std = row.get(f"std_{stem}", np.nan)
    return {
        "q1": float(q1) if pd.notna(q1) else np.nan,
        "median": float(med) if pd.notna(med) else np.nan,
        "q3": float(q3) if pd.notna(q3) else np.nan,
        "mean": float(mean) if pd.notna(mean) else np.nan,
        "std": float(std) if pd.notna(std) else np.nan,
        "n": int(n) if pd.notna(n) else 0,
    }


def stats_box_quantis(row: pd.Series, area: str) -> Optional[dict[str, float]]:
    """Estatísticas de boxplot (Tukey) a partir de quantis agregados."""
    q = quantis_area(row, area)
    if any(pd.isna(q[k]) for k in ("q1", "median", "q3")):
        return None
    iqr = q["q3"] - q["q1"]
    mean = q["mean"] if pd.notna(q["mean"]) else q["median"]
    return {
        "q1": q["q1"],
        "median": q["median"],
        "q3": q["q3"],
        "mean": mean,
        "std": q.get("std", np.nan),
        "n": q["n"],
        "low": max(0.0, q["q1"] - 1.5 * iqr),
        "up": min(1000.0, q["q3"] + 1.5 * iqr),
    }


def medias_referencia_por_ano(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
) -> dict[str, dict[str, float]]:
    """Médias MS e BR (rede estadual) por área a partir de referencias.parquet.

    População: concluintes EM quando disponível (2019–2023), presentes nos
    2 dias, não eliminados — conforme gerar_dados_agregados.py.
    """
    df_ref = tabelas.get("referencias", pd.DataFrame())
    out: dict[str, dict[str, float]] = {}
    if df_ref.empty:
        return out
    sub = df_ref[df_ref["ano"] == int(ano)]
    for _, r in sub.iterrows():
        area = str(r.get("area", ""))
        out[area] = {
            "ms": float(r["media_ms"]) if pd.notna(r.get("media_ms")) else np.nan,
            "br": float(r["media_br"]) if pd.notna(r.get("media_br")) else np.nan,
        }
    return out


COLS_NOTAS_ALL = COLS_NOTAS + ["MEDIA_GERAL"]


def medias_br_serie_por_area(
    tabelas: dict[str, pd.DataFrame],
    anos: list[int],
) -> dict[str, dict[int, float]]:
    """Série ano→média BR por área (referencias.parquet, rede estadual)."""
    df_ref = tabelas.get("referencias", pd.DataFrame())
    out: dict[str, dict[int, float]] = {a: {} for a in COLS_NOTAS_ALL}
    if df_ref.empty or not anos:
        return out
    sub = df_ref[df_ref["ano"].isin([int(a) for a in anos])]
    for _, r in sub.iterrows():
        area = str(r.get("area", ""))
        if area in out and pd.notna(r.get("media_br")):
            out[area][int(r["ano"])] = float(r["media_br"])
    return out


def media_nacional_ponderada(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
    area: str,
    dependencia: str = "Estadual",
) -> float:
    """Média nacional ponderada por estudantes (desempenho_uf ou panorama_nacional)."""
    col = _MEDIA_MAP.get(area, area)
    df = tabelas.get("desempenho_uf", pd.DataFrame())
    if not df.empty:
        sub = df[(df["ano"] == int(ano)) & (df["dependencia"] == dependencia)]
        if not sub.empty and col in sub.columns:
            w = sub["estudantes"].astype(float)
            if w.sum() > 0:
                return float(np.average(sub[col], weights=w))
    pn = tabelas.get("panorama_nacional", pd.DataFrame())
    if not pn.empty:
        row = pn[(pn["ano"] == int(ano)) & (pn["dependencia"] == dependencia)]
        if not row.empty and col in row.columns:
            v = row.iloc[0][col]
            return float(v) if pd.notna(v) else float("nan")
    return float("nan")


def serie_media_nacional_dep(
    tabelas: dict[str, pd.DataFrame],
    anos: list[int],
    area: str,
    dependencia: str = "Estadual",
) -> pd.Series:
    """Série anual da média nacional para uma dependência."""
    vals = {
        int(a): media_nacional_ponderada(tabelas, int(a), area, dependencia)
        for a in anos
    }
    s = pd.Series(vals, dtype=float).dropna()
    return s.sort_index()


def anos_com_desempenho_uf(
    tabelas: dict[str, pd.DataFrame],
    anos_sel: list[int],
) -> list[int]:
    df = tabelas.get("desempenho_uf", pd.DataFrame())
    if df.empty:
        return []
    disp = set(int(a) for a in df["ano"].dropna().unique())
    return sorted(a for a in anos_sel if int(a) in disp)


def tabela_ranking_uf(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
    dependencia: Optional[str] = "Estadual",
) -> pd.DataFrame:
    """Ranking por UF a partir de desempenho_uf + participacao_uf (sem sintético)."""
    df_d = tabelas.get("desempenho_uf", pd.DataFrame())
    df_p = tabelas.get("participacao_uf", pd.DataFrame())
    if df_d.empty:
        return pd.DataFrame()
    sub = df_d[df_d["ano"] == int(ano)]
    if dependencia not in (None, "Todas", ""):
        sub = sub[sub["dependencia"] == dependencia]
    rows: list[dict[str, Any]] = []
    for uf, g in sub.groupby("uf", observed=True):
        uf_s = str(uf).upper()
        if len(uf_s) != 2:
            continue
        w = g["estudantes"].astype(float)
        row: dict[str, Any] = {"UF": uf_s, "Presentes": int(w.sum())}
        for area, col in _MEDIA_MAP.items():
            if col in g.columns and w.sum() > 0:
                row[area] = round(float(np.average(g[col], weights=w)), 2)
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    g_out = pd.DataFrame(rows)
    g_out["MEDIA_GERAL"] = g_out[[c for c in COLS_NOTAS if c in g_out.columns]].mean(axis=1).round(2)

    if not df_p.empty:
        psub = df_p[df_p["ano"] == int(ano)]
        dep_part = dependencia if dependencia and dependencia != "Todas" else "Estadual"
        psub = psub[psub["dependencia"] == dep_part]
        if not psub.empty:
            part = psub.rename(columns={"uf": "UF"})[["UF", "inscritos", "presentes_filt"]].copy()
            part["UF"] = part["UF"].astype(str).str.upper()
            part = part.rename(columns={
                "inscritos": "Inscritos",
                "presentes_filt": "Presentes_Est",
            })
            g_out = g_out.merge(part, on="UF", how="left")
            g_out["Inscritos"] = pd.to_numeric(g_out["Inscritos"], errors="coerce").fillna(0).astype(int)
            g_out["Presentes_Est"] = pd.to_numeric(
                g_out["Presentes_Est"], errors="coerce"
            ).fillna(g_out["Presentes"]).astype(int)
            g_out["Tx_Participação"] = (
                g_out["Presentes_Est"] / g_out["Inscritos"].replace(0, pd.NA) * 100
            ).round(1)
    if "Inscritos" not in g_out.columns:
        g_out["Inscritos"] = 0
        g_out["Presentes_Est"] = g_out.get("Presentes", 0)
        g_out["Tx_Participação"] = pd.NA
    return g_out


def filtrar_participacao_cre(
    tabelas: dict[str, pd.DataFrame],
    *,
    anos: Optional[list[int]] = None,
    dependencia: Optional[str] = None,
) -> pd.DataFrame:
    """Participação por CRE (presentes, concluintes, tx_part_efetiva)."""
    df = tabelas.get("participacao_cre", pd.DataFrame())
    if df.empty:
        return df
    out = df.copy()
    if anos:
        out = out[out["ano"].isin(anos)]
    if dependencia:
        out = out[out["dependencia"] == dependencia]
    return out


def filtrar_participacao_municipio(
    tabelas: dict[str, pd.DataFrame],
    *,
    anos: Optional[list[int]] = None,
    dependencia: Optional[str] = None,
) -> pd.DataFrame:
    """Participação por município (presentes, concluintes, tx_part_efetiva)."""
    df = tabelas.get("municipios", pd.DataFrame())
    if df.empty:
        return df
    out = df.copy()
    if anos:
        out = out[out["ano"].isin(anos)]
    if dependencia:
        out = out[out["dependencia"] == dependencia]
    return out


def media_ms_area_ano(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
    area: str,
    dependencia: str = "Estadual",
) -> Optional[float]:
    """Média MS por área/ano via distribuicao_ms (rede estadual)."""
    df = tabelas.get("distribuicao_ms", pd.DataFrame())
    row = linha_distribuicao(df, ano=int(ano), dependencia=dependencia)
    if row is None:
        refs = medias_referencia_por_ano(tabelas, ano)
        ref = refs.get(area, {})
        ms = ref.get("ms")
        return float(ms) if ms is not None and pd.notna(ms) else None
    stats = stats_box_quantis(row, area)
    if stats is None:
        return None
    return float(stats["mean"])


def filtrar_distribuicao(
    df: pd.DataFrame,
    *,
    anos: Optional[list[int]] = None,
    dependencia: Optional[str] = None,
    cre: Optional[str] = None,
    municipio: Optional[str] = None,
) -> pd.DataFrame:
    """Filtra tabela distribuicao_* por recorte."""
    if df.empty:
        return df
    out = df.copy()
    if anos is not None and "ano" in out.columns:
        out = out[out["ano"].isin([int(a) for a in anos])]
    if dependencia is not None and "dependencia" in out.columns:
        out = out[out["dependencia"] == dependencia]
    if cre is not None and "cre" in out.columns:
        out = out[out["cre"].astype(str) == str(cre)]
    if municipio is not None and "municipio" in out.columns:
        out = out[out["municipio"].astype(str) == str(municipio)]
    return out


def linha_distribuicao(
    df: pd.DataFrame,
    *,
    ano: int,
    dependencia: str,
    cre: Optional[str] = None,
    municipio: Optional[str] = None,
) -> Optional[pd.Series]:
    """Retorna uma linha de distribuicao_* com correspondência tolerante de nomes."""
    sub = filtrar_distribuicao(
        df, anos=[int(ano)], dependencia=dependencia, cre=cre, municipio=municipio,
    )
    if not sub.empty:
        return sub.iloc[0]
    base = filtrar_distribuicao(df, anos=[int(ano)], dependencia=dependencia)
    if base.empty:
        return None
    if cre is not None and "cre" in base.columns:
        alvo = str(cre).strip().upper()
        hit = base[base["cre"].astype(str).str.strip().str.upper() == alvo]
        if not hit.empty:
            return hit.iloc[0]
    if municipio is not None and "municipio" in base.columns:
        alvo = str(municipio).strip().upper()
        hit = base[base["municipio"].astype(str).str.strip().str.upper() == alvo]
        if not hit.empty:
            return hit.iloc[0]
    return None


def _normalizar_df_notas_individuais(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "CO_ESCOLA" in out.columns:
        out["CO_ESCOLA"] = pd.to_numeric(out["CO_ESCOLA"], errors="coerce")
    if "NU_ANO" in out.columns:
        out["NU_ANO"] = pd.to_numeric(out["NU_ANO"], errors="coerce").astype("Int16")
    elif "ano" in out.columns:
        out["NU_ANO"] = pd.to_numeric(out["ano"], errors="coerce").astype("Int16")
    else:
        out["NU_ANO"] = 2024
    if "municipio" in out.columns and "MUNICIPIO_CRES" not in out.columns:
        out["MUNICIPIO_CRES"] = out["municipio"]
    if "municipio" in out.columns and "NO_MUNICIPIO_ESC" not in out.columns:
        out["NO_MUNICIPIO_ESC"] = out["municipio"]
    if "dependencia" in out.columns and "DEP_ADM" not in out.columns:
        out["DEP_ADM"] = out["dependencia"].astype(str)
    out["SG_UF_ESC"] = "MS"
    out["CATEGORIA_PARTICIPACAO"] = "presente_ambos_dias"
    for c in COLS_NOTAS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("float32")
    if "MEDIA_GERAL" in out.columns:
        out["MEDIA_GERAL"] = pd.to_numeric(out["MEDIA_GERAL"], errors="coerce").astype("float32")
    return out


def _caminho_notas_individuais_local() -> Optional[str]:
    pasta = get_pasta_agregados()
    caminho = os.path.join(pasta, NOTAS_INDIVIDUAIS_ARQUIVO)
    if os.path.exists(caminho):
        return caminho
    legado = os.path.join(pasta, NOTAS_INDIVIDUAIS_ARQUIVO_LEGACY)
    if os.path.exists(legado):
        return legado
    return None


@st.cache_data(show_spinner="Carregando notas individuais...", ttl=3600)
def carregar_notas_individuais(anos: Optional[list[int] | tuple[int, ...]] = None) -> pd.DataFrame:
    """Notas por estudante (MS estadual, 2019–2024) para boxplot/histograma/std.

    Use ``anos`` para pushdown no parquet (menos RAM e I/O).
    """
    if anos is not None:
        anos = [int(a) for a in anos]
    if get_data_source() == "supabase":
        try:
            df = _carregar_supabase("notas_individuais")
        except Exception:
            try:
                df = _carregar_supabase("notas_individuais_2024")
            except Exception:
                return pd.DataFrame()
    else:
        caminho = _caminho_notas_individuais_local()
        if not caminho:
            return pd.DataFrame()
        filtros = None
        if anos:
            filtros = [("NU_ANO", "in", [int(a) for a in anos])]
        try:
            df = pd.read_parquet(caminho, filters=filtros) if filtros else pd.read_parquet(caminho)
        except Exception:
            df = pd.read_parquet(caminho)
            if anos and "NU_ANO" in df.columns:
                df = df[df["NU_ANO"].isin([int(a) for a in anos])]

    return _normalizar_df_notas_individuais(df)


@st.cache_data(show_spinner="Carregando notas individuais 2024...", ttl=3600)
def carregar_notas_individuais_2024() -> pd.DataFrame:
    """Atalho: apenas ano 2024 (compatibilidade)."""
    return carregar_notas_individuais(anos=[2024])


def anos_com_notas_individuais(df: pd.DataFrame) -> list[int]:
    if df.empty or "NU_ANO" not in df.columns:
        return []
    return sorted(int(a) for a in df["NU_ANO"].dropna().unique())


def tem_notas_individuais_ano(df: pd.DataFrame, ano: int) -> bool:
    return int(ano) in anos_com_notas_individuais(df)


def filtrar_notas_individuais(
    df: pd.DataFrame,
    *,
    ano: Optional[int] = None,
    co_escola: Optional[int] = None,
    cre: Optional[str] = None,
    municipio: Optional[str] = None,
    dependencia: str = "Estadual",
    area: Optional[str] = None,
) -> pd.DataFrame:
    """Filtra notas individuais por ano, escola, CRE ou município."""
    if df.empty:
        return df
    out = df.copy()
    if ano is not None and "NU_ANO" in out.columns:
        out = out[pd.to_numeric(out["NU_ANO"], errors="coerce") == int(ano)]
    if dependencia and "dependencia" in out.columns:
        out = out[out["dependencia"] == dependencia]
    elif dependencia and "DEP_ADM" in out.columns:
        out = out[out["DEP_ADM"] == dependencia]
    if co_escola is not None and "CO_ESCOLA" in out.columns:
        co = pd.to_numeric(co_escola, errors="coerce")
        out = out[pd.to_numeric(out["CO_ESCOLA"], errors="coerce") == int(co)]
    if cre is not None and "CRE" in out.columns:
        alvo = str(cre).strip().upper()
        out = out[out["CRE"].astype(str).str.strip().str.upper() == alvo]
    if municipio is not None:
        col_m = "municipio" if "municipio" in out.columns else "MUNICIPIO_CRES"
        if col_m in out.columns:
            alvo = str(municipio).strip().upper()
            out = out[out[col_m].astype(str).str.strip().str.upper() == alvo]
    if area and area in out.columns:
        notas = pd.to_numeric(out[area], errors="coerce")
        out = out[notas > 0]
    return out.reset_index(drop=True)


def base_populacao_histograma(df: pd.DataFrame) -> pd.DataFrame:
    """População dos histogramas: presentes 2 dias, não eliminados (presentes_filt)."""
    from gerar_dados_agregados import _base_populacao_histograma

    return _base_populacao_histograma(df)


def notas_area(df: pd.DataFrame, area: str) -> pd.Series:
    """Série de notas válidas (≥ 0, inclui zero) de uma área; NA excluído."""
    if df.empty or area not in df.columns:
        return pd.Series(dtype=float)
    s = pd.to_numeric(df[area], errors="coerce")
    return s[s.notna() & (s >= 0) & (s <= HIST_BIN_MAX)]


def serie_media_geral(df: pd.DataFrame) -> pd.Series:
    """Média geral por estudante (5 notas válidas, zero permitido)."""
    if df.empty:
        return pd.Series(dtype=float)
    notas = df[COLS_NOTAS].apply(pd.to_numeric, errors="coerce")
    mask = notas.notna().all(axis=1)
    return notas.loc[mask].mean(axis=1)


def contagem_feixas_notas(
    notas: pd.Series,
    bin_edges: Optional[list[int]] = None,
) -> pd.DataFrame:
    """Histograma real: contagem por faixa (NA, Zero, >0–50, …, 950–1000)."""
    from gerar_dados_agregados import _contagem_feixas

    rows = _contagem_feixas(notas, bin_edges)
    if not rows:
        return pd.DataFrame(columns=["bin_lo", "bin_hi", "count"])
    return pd.DataFrame(rows)


def filtrar_histograma_ms(
    df: pd.DataFrame,
    *,
    ano: int,
    area: str,
    dependencia: str = "Estadual",
) -> pd.DataFrame:
    """Filtra histograma_ms.parquet por ano, área e dependência."""
    if df.empty:
        return df
    sub = df[
        (df["ano"] == int(ano))
        & (df["dependencia"] == dependencia)
        & (df["area"] == area)
    ]
    cols = ["bin_lo", "bin_hi", "count"]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    return sub[cols].sort_values("bin_lo").reset_index(drop=True)


def _caminho_microdados_enem() -> str:
    return os.getenv(
        "ENEM_ARQUIVO_ENTRADA",
        os.path.join(os.path.dirname(__file__), "data", "enem_completo_2019_2024_.parquet"),
    )


def presentes_filt_estadual_ano(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
) -> Optional[int]:
    """Tamanho da população de referência (presentes_filt) — rede estadual MS."""
    df_part = tabelas.get("participacao_ano", pd.DataFrame())
    if df_part.empty:
        return None
    sub = df_part[
        (df_part["ano"] == int(ano)) & (df_part["dependencia"] == "Estadual")
    ]
    if sub.empty:
        return None
    val = sub.iloc[0].get("presentes_filt", sub.iloc[0].get("presentes"))
    return int(val) if pd.notna(val) else None


@st.cache_data(show_spinner=False, ttl=3600)
def _carregar_notas_microdado_ms_estadual(ano: int) -> pd.DataFrame:
    """Fallback: microdado ENEM filtrado (MS estadual, mesmas regras do agregador)."""
    from gerar_dados_agregados import filtrar_ms_estadual_analise

    caminho = _caminho_microdados_enem()
    if not os.path.exists(caminho):
        return pd.DataFrame()
    try:
        df = pd.read_parquet(
            caminho,
            filters=[("NU_ANO", "==", int(ano)), ("SG_UF_ESC", "==", "MS")],
        )
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    return filtrar_ms_estadual_analise(df, int(ano)).reset_index(drop=True)


def _serie_area_histograma(df: pd.DataFrame, area: str) -> pd.Series:
    """Notas por área para histograma (NA incluído; população presentes_filt)."""
    from gerar_dados_agregados import serie_area_histograma

    return serie_area_histograma(df, area)


def _parquet_histograma_atualizado(bins: pd.DataFrame) -> bool:
    """Parquet legado (sem faixa NA) deve ser ignorado em favor do microdado."""
    if bins.empty:
        return False
    return bool((bins["bin_lo"] == -1.0).any())


def histograma_area_subset(df: pd.DataFrame, area: str) -> pd.DataFrame:
    """Histograma por faixa a partir de notas individuais (CRE, município, escola, MS)."""
    if df.empty:
        return pd.DataFrame(columns=["bin_lo", "bin_hi", "count"])
    serie = _serie_area_histograma(df, area)
    return contagem_feixas_notas(serie)


def histograma_area_ano(
    tabelas: dict[str, pd.DataFrame],
    ano: int,
    area: str,
    *,
    dependencia: str = "Estadual",
    df_notas_individuais: Optional[pd.DataFrame] = None,
    df_notas_2024: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, str]:
    """Histograma real por faixa (NA, Zero, >0–50, …). Retorna (bins, origem_dados)."""
    ano = int(ano)
    df_ind = df_notas_individuais if df_notas_individuais is not None else df_notas_2024

    if df_ind is not None and not df_ind.empty and tem_notas_individuais_ano(df_ind, ano):
        sub = filtrar_notas_individuais(df_ind, ano=ano, dependencia=dependencia)
        if not sub.empty:
            bins = histograma_area_subset(sub, area)
            if not bins.empty:
                return bins, f"notas_individuais_ms.parquet ({ano})"

    df_micro = _carregar_notas_microdado_ms_estadual(ano)
    if not df_micro.empty:
        serie = _serie_area_histograma(df_micro, area)
        bins = contagem_feixas_notas(serie)
        if not bins.empty:
            return bins, f"enem_completo_2019_2024_.parquet ({ano})"

    df_hist = tabelas.get("histograma_ms", pd.DataFrame())
    bins_parquet = filtrar_histograma_ms(
        df_hist, ano=ano, area=area, dependencia=dependencia,
    )
    parquet_ok = not bins_parquet.empty and _parquet_histograma_atualizado(bins_parquet)
    if parquet_ok:
        return bins_parquet, "histograma_ms.parquet"

    return pd.DataFrame(columns=["bin_lo", "bin_hi", "count"]), ""


def series_from_quantis(row: pd.Series, area: str, n_pontos: int = 120) -> pd.Series:
    """Gera série sintética a partir de quantis para boxplots."""
    col_map = {
        "NU_NOTA_CN": "nu_nota_cn",
        "NU_NOTA_CH": "nu_nota_ch",
        "NU_NOTA_LC": "nu_nota_lc",
        "NU_NOTA_MT": "nu_nota_mt",
        "NU_NOTA_REDACAO": "nu_nota_redacao",
        "MEDIA_GERAL": "media_geral",
    }
    stem = col_map.get(area, area.lower())
    q1 = row.get(f"q1_{stem}", row.get(f"q25_{stem}", np.nan))
    med = row.get(f"median_{stem}", row.get(f"q50_{stem}", np.nan))
    q3 = row.get(f"q3_{stem}", row.get(f"q75_{stem}", np.nan))
    if pd.isna(q1) or pd.isna(med) or pd.isna(q3):
        mean = row.get(f"mean_{stem}", row.get(_MEDIA_MAP.get(area, ""), np.nan))
        if pd.isna(mean):
            return pd.Series(dtype=float)
        return pd.Series([float(mean)] * max(n_pontos // 4, 10))
    rng = np.random.default_rng(42)
    lower = np.linspace(float(q1), float(med), n_pontos // 3)
    upper = np.linspace(float(med), float(q3), n_pontos // 3)
    mid = rng.normal(float(med), max(float(q3 - q1) / 6, 1.0), n_pontos // 3)
    return pd.Series(np.concatenate([lower, mid, upper]))


def verificar_dados_disponiveis() -> bool:
    if get_data_source() == "supabase":
        return bool(_get_supabase_config().get("host"))
    pasta = get_pasta_agregados()
    if not os.path.isdir(pasta):
        return False
    return any(f.endswith(".parquet") for f in os.listdir(pasta))
