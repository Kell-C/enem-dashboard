"""
Microdados ENEM agregados por escola (2005-2015) — INEP MICRODADOS_ENEM_ESCOLA.csv.

Fonte: medias, matriculados, participantes e taxa por escola/ano (nao ha registro individual).
Alimenta agregados do painel para 2013-2015 (matriculados, participantes, taxa).
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from enem_config import (
    ANOS_MICRO_HISTORICO,
    AREA_KEYS,
    BRASIL_REFERENCIA,
    COLS_NOTAS,
    DEPENDENCIAS,
    DEP_MAP,
    NOTA_MAP,
    PASTA_DADOS,
    REDE_REFERENCIA,
    CSV_ESCOLA_HISTORICO,
    PARQUET_ESCOLA_HISTORICO,
)
from enem_helpers import (
    COL_MUNICIPIO,
    cre_curto,
    enriquecer_ms,
    nome_exibicao_escola,
    normalizar_texto,
    observacao_oferta_escola,
    quantis_serie,
)

logger = logging.getLogger(__name__)

HIST_EDGES = [0, 200, 400, 500, 600, 800, 1000.0001]
HIST_POS_EDGES = [1, 200, 400, 500, 600, 800, 1000.0001]

COL_MAP = {
    "SG_UF_ESCOLA": "SG_UF_ESC",
    "NO_MUNICIPIO_ESCOLA": "NO_MUNICIPIO_ESC",
    "CO_ESCOLA_EDUCACENSO": "CO_ESCOLA",
    "NO_ESCOLA_EDUCACENSO": "NOME_ESCOLA",
    "TP_DEPENDENCIA_ADM_ESCOLA": "TP_DEPENDENCIA_ADM_ESC",
    "NU_MEDIA_CN": "NU_NOTA_CN",
    "NU_MEDIA_CH": "NU_NOTA_CH",
    "NU_MEDIA_LP": "NU_NOTA_LC",
    "NU_MEDIA_MT": "NU_NOTA_MT",
    "NU_MEDIA_RED": "NU_NOTA_REDACAO",
}


def _sum_col(df: pd.DataFrame, col: str, default: int = 0) -> int:
    if df.empty or col not in df.columns:
        return default
    return int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _taxa_participacao(
    matriculados: pd.Series,
    participantes: pd.Series,
    taxa_oficial: pd.Series | None = None,
) -> pd.Series:
    calc = (participantes / matriculados.replace(0, np.nan) * 100).round(2)
    if taxa_oficial is None:
        return calc
    return taxa_oficial.where(taxa_oficial.notna(), calc)


def _concluintes_ms_ano(ano: int, ms_est: pd.DataFrame, conc_totais: pd.DataFrame) -> int:
    conc = 0
    if not conc_totais.empty:
        rows = conc_totais.loc[conc_totais["NU_ANO"] == ano, "Concluintes"]
        if not rows.empty and pd.notna(rows.iloc[0]):
            conc = int(rows.iloc[0])
    if conc <= 0:
        conc = _sum_col(ms_est, "NU_MATRICULAS")
    return conc


def _concluintes_grupo(
    ano: int,
    grp: pd.DataFrame,
    conc_esc: pd.DataFrame,
    *,
    co_escola: int | None = None,
    cre: str | None = None,
    municipio: str | None = None,
) -> int:
    mat = _sum_col(grp, "NU_MATRICULAS")
    if conc_esc.empty:
        return mat
    sub = conc_esc[conc_esc["NU_ANO"] == ano]
    if co_escola is not None and "CO_ESCOLA" in sub.columns:
        val = sub.loc[sub["CO_ESCOLA"] == co_escola, "Concluintes"]
        if not val.empty and pd.notna(val.iloc[0]) and int(val.iloc[0]) > 0:
            return int(val.iloc[0])
    if cre and "CRE" in sub.columns:
        val = sub.loc[sub["CRE"] == cre, "Concluintes"].sum()
        if val > 0:
            return int(val)
    if municipio and COL_MUNICIPIO in sub.columns:
        val = sub.loc[
            sub[COL_MUNICIPIO].map(normalizar_texto) == normalizar_texto(municipio),
            "Concluintes",
        ].sum()
        if val > 0:
            return int(val)
    return mat


def participacao_ms_estadual(df: pd.DataFrame | None = None, anos: list[int] | None = None) -> pd.DataFrame:
    """Matriculados, participantes e taxa por escola estadual MS (exportacao/pipeline)."""
    base = df if df is not None else carregar_escola_historico()
    if base.empty:
        return pd.DataFrame()
    ms = base[(base["SG_UF_ESC"] == "MS") & (base["TP_DEPENDENCIA_ADM_ESC"] == 2)].copy()
    if anos:
        ms = ms[ms["NU_ANO"].isin(anos)]
    ms["matriculados"] = pd.to_numeric(ms["NU_MATRICULAS"], errors="coerce")
    ms["participantes"] = pd.to_numeric(ms["NU_PARTICIPANTES"], errors="coerce")
    taxa_oficial = pd.to_numeric(ms["NU_TAXA_PARTICIPACAO"], errors="coerce")
    ms["taxa_participacao"] = _taxa_participacao(ms["matriculados"], ms["participantes"], taxa_oficial)
    out = ms.rename(columns={
        "NU_ANO": "ano",
        "CO_ESCOLA": "co_inep_escola",
        "NO_MUNICIPIO_ESC": "municipio",
        "NOME_ESCOLA": "unidade_escolar",
    })
    cols = [
        "ano", "co_inep_escola", "municipio", "unidade_escolar",
        "matriculados", "participantes", "taxa_participacao",
    ]
    return out[[c for c in cols if c in out.columns]].sort_values(
        ["ano", "municipio", "unidade_escolar"], kind="stable",
    )


def _media_pond(df: pd.DataFrame, col: str, peso: str = "NU_PARTICIPANTES") -> float | None:
    sub = df[[col, peso]].dropna(subset=[col])
    if sub.empty:
        return None
    w = pd.to_numeric(sub[peso], errors="coerce").fillna(0)
    v = pd.to_numeric(sub[col], errors="coerce")
    total = w.sum()
    if total <= 0:
        return round(float(v.mean()), 4)
    return round(float((v * w).sum() / total), 4)


def _hist_pct(s: pd.Series) -> list[float]:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return [0.0] * 6
    counts = []
    for lo, hi in zip(HIST_EDGES[:-1], HIST_EDGES[1:]):
        if hi > 1000:
            counts.append(int(((s >= lo) & (s <= 1000)).sum()))
        else:
            counts.append(int(((s >= lo) & (s < hi)).sum()))
    total = len(s)
    return [round(100 * c / total, 1) for c in counts]


def _area_detail_escolas(df: pd.DataFrame, area: str, col: str) -> dict:
    """Estatisticas por area usando medias das escolas (proxy)."""
    n_part = int(pd.to_numeric(df["NU_PARTICIPANTES"], errors="coerce").fillna(0).sum())
    s = pd.to_numeric(df[col], errors="coerce")
    valid = df[s.notna()].copy()
    if valid.empty:
        return {
            "n": 0, "pct_sem_nota": 0.0, "pct_zero": 0.0, "moda": None, "moda_faixa": None,
            "min_pos": None, "h_sem": 0.0, "h_zero": 0.0, "h_1_200": 0.0, "h_200_400": 0.0,
            "h_400_500": 0.0, "h_500_600": 0.0, "h_600_800": 0.0, "h_800_1000": 0.0,
        }
    sv = pd.to_numeric(valid[col], errors="coerce")
    pos = sv[sv > 0]
    n_esc = len(valid)
    pct_sem = round(100 * (len(df) - n_esc) / len(df), 1) if len(df) else 0.0
    pct_zero = round(100 * (sv == 0).sum() / len(df), 1) if len(df) else 0.0
    moda = round(float(pos.round().mode().iloc[0]), 1) if not pos.empty else None
    min_pos = round(float(pos.min()), 1) if not pos.empty else None
    hp = _hist_pct(pos)
    pos_labels = ["1\u2013200", "200\u2013400", "400\u2013500", "500\u2013600", "600\u2013800", "800\u20131000"]
    peak_i = max(range(len(hp)), key=lambda j: hp[j]) if hp else 0
    moda_faixa = pos_labels[peak_i] if hp and hp[peak_i] > 0 else None
    return {
        "n": n_part if n_part else n_esc,
        "pct_sem_nota": pct_sem,
        "pct_zero": pct_zero,
        "moda": moda,
        "moda_faixa": moda_faixa,
        "min_pos": min_pos,
        "h_sem": pct_sem,
        "h_zero": pct_zero,
        "h_1_200": hp[0] if len(hp) > 0 else 0.0,
        "h_200_400": hp[1] if len(hp) > 1 else 0.0,
        "h_400_500": hp[2] if len(hp) > 2 else 0.0,
        "h_500_600": hp[3] if len(hp) > 3 else 0.0,
        "h_600_800": hp[4] if len(hp) > 4 else 0.0,
        "h_800_1000": hp[5] if len(hp) > 5 else 0.0,
    }


def normalizar_escola_historico(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={k: v for k, v in COL_MAP.items() if k in df.columns}).copy()
    out["NU_ANO"] = pd.to_numeric(out["NU_ANO"], errors="coerce").astype("Int64")
    out["CO_ESCOLA"] = pd.to_numeric(out.get("CO_ESCOLA"), errors="coerce")
    out["TP_DEPENDENCIA_ADM_ESC"] = pd.to_numeric(out.get("TP_DEPENDENCIA_ADM_ESC"), errors="coerce")
    out["NU_PARTICIPANTES"] = pd.to_numeric(out.get("NU_PARTICIPANTES"), errors="coerce").fillna(0).astype(int)
    out["DEP_ADM"] = out["TP_DEPENDENCIA_ADM_ESC"].map(DEP_MAP)
    for c in COLS_NOTAS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if "NU_MEDIA_TOT" in df.columns:
        tot = pd.to_numeric(df["NU_MEDIA_TOT"], errors="coerce")
        out["MEDIA_GERAL"] = tot.where(tot.notna(), out[COLS_NOTAS].mean(axis=1, skipna=True))
    else:
        out["MEDIA_GERAL"] = out[COLS_NOTAS].mean(axis=1, skipna=True)
    out["SEM_ZERO"] = (out[COLS_NOTAS] > 0).all(axis=1)
    out["COM_MEDIA"] = out[COLS_NOTAS].notna().any(axis=1)
    return out


def carregar_escola_historico(
    csv_path: Path | None = None,
    anos: list[int] | None = None,
) -> pd.DataFrame:
    csv_path = Path(csv_path or CSV_ESCOLA_HISTORICO)
    if PARQUET_ESCOLA_HISTORICO.exists() and csv_path.stat().st_mtime <= PARQUET_ESCOLA_HISTORICO.stat().st_mtime:
        df = pd.read_parquet(PARQUET_ESCOLA_HISTORICO)
        logger.info("[cache] escola historico: %s (%s linhas)", PARQUET_ESCOLA_HISTORICO, len(df))
    elif csv_path.exists():
        logger.info("Lendo %s ...", csv_path)
        df = pd.read_csv(csv_path, sep=";", encoding="latin-1", low_memory=False)
        df = normalizar_escola_historico(df)
        PARQUET_ESCOLA_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(PARQUET_ESCOLA_HISTORICO, index=False)
        logger.info("[salvo] %s (%s linhas, anos %s)", PARQUET_ESCOLA_HISTORICO, len(df), sorted(df["NU_ANO"].dropna().unique()))
    else:
        logger.warning("CSV escola historico nao encontrado: %s", csv_path)
        return pd.DataFrame()

    if anos is not None:
        df = df[df["NU_ANO"].isin(anos)]
    return df


def anos_escola_disponiveis() -> list[int]:
    df = carregar_escola_historico()
    if df.empty:
        return []
    return sorted(int(a) for a in df["NU_ANO"].dropna().unique())


def processar_ano_escola(
    df_ano: pd.DataFrame,
    cres: pd.DataFrame,
    mapa_muni: dict,
    conc_totais: pd.DataFrame,
    conc_esc: pd.DataFrame,
) -> dict:
    """Gera blocos de agregados para um ano a partir de medias por escola."""
    ano = int(df_ano["NU_ANO"].iloc[0])
    df_all = df_ano.copy()
    df = df_ano[df_ano["COM_MEDIA"]].copy()

    out: dict = {
        "participacao_ano": [],
        "participacao_cre": [],
        "participacao_municipios": [],
        "desempenho": [],
        "desempenho_uf": [],
        "escolas_2024": [],
        "sumario": [],
        "referencias": [],
        "evolucao_cre": [],
        "evolucao_muni": [],
        "evolucao_escolas": [],
        "histograma": [],
        "histograma_sem_zero": [],
        "desvio_cv": [],
        "area_detail": [],
        "area_detail_sem_zero": [],
        "quantis": [],
        "quantis_sem_zero": [],
    }

    ms_all = df_all[df_all["SG_UF_ESC"] == "MS"]
    br_est_all = df_all[df_all["DEP_ADM"] == REDE_REFERENCIA]
    ms = df[df["SG_UF_ESC"] == "MS"]
    br_est = df[df["DEP_ADM"] == REDE_REFERENCIA]
    ms_est = ms_all[ms_all["DEP_ADM"] == REDE_REFERENCIA]
    ms_est_med = ms[ms["DEP_ADM"] == REDE_REFERENCIA]
    ms_est_sz = ms_est_med[ms_est_med["SEM_ZERO"]] if not ms_est_med.empty else ms_est_med
    br_sem = br_est[br_est["SEM_ZERO"]] if not br_est.empty else br_est
    conc_ano = _concluintes_ms_ano(ano, ms_est, conc_totais)
    mat_ano = _sum_col(ms_est, "NU_MATRICULAS")

    for dep in DEPENDENCIAS:
        sub = ms_all[ms_all["DEP_ADM"] == dep]
        sub_sem = ms[ms["DEP_ADM"] == dep]
        sub_sem = sub_sem[sub_sem["SEM_ZERO"]] if not sub_sem.empty else sub_sem
        n_part = _sum_col(sub, "NU_PARTICIPANTES")
        n_part_sz = _sum_col(sub_sem, "NU_PARTICIPANTES")
        n_mat = _sum_col(sub, "NU_MATRICULAS")
        conc = conc_ano if dep == REDE_REFERENCIA else None
        if dep == REDE_REFERENCIA and (conc is None or conc <= 0):
            conc = n_mat

        out["participacao_ano"].append({
            "ano": ano,
            "dependencia": dep,
            "inscritos": n_part,
            "presentes": n_part,
            "presentes_area": n_part,
            "presentes_2d": n_part,
            "eliminados_redacao": 0,
            "eliminados_objetiva": 0,
            "eliminados_total": 0,
            "redacao_branco": 0,
            "matriculados": n_mat if dep == REDE_REFERENCIA else None,
            "concluintes": conc,
            "presentes_filt": n_part,
            "presentes_filt_sem_zero": n_part_sz,
            "fonte": "inep_escola",
        })

        sub_med = ms[ms["DEP_ADM"] == dep]
        sub_med_sem = sub_med[sub_med["SEM_ZERO"]] if not sub_med.empty else sub_med

        if not sub_med.empty:
            row = {"ano": ano, "dependencia": dep, "estudantes": _sum_col(sub_med, "NU_PARTICIPANTES"), "fonte": "inep_escola"}
            for c in COLS_NOTAS + ["MEDIA_GERAL"]:
                row[f"media_{c.lower()}"] = _media_pond(sub_med, c)
                row[f"media_{c.lower()}_sem_zero"] = _media_pond(sub_med_sem, c) if not sub_med_sem.empty else None
            row["estudantes_sem_zero"] = _sum_col(sub_med_sem, "NU_PARTICIPANTES") if not sub_med_sem.empty else 0
            out["desempenho"].append(row)

    n_br = _sum_col(br_est_all, "NU_PARTICIPANTES")
    n_br_sz = _sum_col(br_sem, "NU_PARTICIPANTES") if not br_sem.empty else 0
    out["participacao_ano"].append({
        "ano": ano,
        "dependencia": BRASIL_REFERENCIA,
        "inscritos": n_br,
        "presentes": n_br,
        "presentes_area": n_br,
        "presentes_2d": n_br,
        "eliminados_redacao": 0,
        "eliminados_objetiva": 0,
        "eliminados_total": 0,
        "redacao_branco": 0,
        "concluintes": None,
        "presentes_filt": n_br,
        "presentes_filt_sem_zero": n_br_sz,
        "fonte": "inep_escola",
    })

    if not br_est.empty:
        uf_rows = []
        for uf, grp in br_est.groupby("SG_UF_ESC", observed=True):
            grp_all = br_est_all[br_est_all["SG_UF_ESC"] == uf]
            grp_sz = grp[grp["SEM_ZERO"]]
            rec = {
                "UF": uf,
                "ano": ano,
                "dependencia": REDE_REFERENCIA,
                "estudantes": _sum_col(grp_all, "NU_PARTICIPANTES"),
                "estudantes_sem_zero": _sum_col(grp_sz, "NU_PARTICIPANTES") if not grp_sz.empty else 0,
                "fonte": "inep_escola",
            }
            for c in COLS_NOTAS + ["MEDIA_GERAL"]:
                rec[f"media_{c.lower()}"] = _media_pond(grp, c)
                rec[f"media_{c.lower()}_sem_zero"] = _media_pond(grp_sz, c) if not grp_sz.empty else None
            uf_rows.append(rec)
        out["desempenho_uf"].extend(uf_rows)

    if not ms_est.empty:
        ms_enr = enriquecer_ms(
            ms_est.rename(columns={"NOME_ESCOLA": "NOME_ESCOLA"}),
            cres,
            mapa_muni,
        )
        ms_enr_med = enriquecer_ms(
            ms_est_med.rename(columns={"NOME_ESCOLA": "NOME_ESCOLA"}),
            cres,
            mapa_muni,
        ) if not ms_est_med.empty else ms_est_med
        if "CRE" in ms_enr.columns:
            for cre, grp in ms_enr.groupby("CRE", observed=True):
                if pd.isna(cre):
                    continue
                grp_sz = grp[grp["SEM_ZERO"]]
                mat_cre = _sum_col(grp, "NU_MATRICULAS")
                part_cre = _sum_col(grp, "NU_PARTICIPANTES")
                conc_cre = _concluintes_grupo(ano, grp, conc_esc, cre=str(cre))
                out["evolucao_cre"].append({
                    "ano": ano,
                    "CRE": cre,
                    "cre_curto": cre_curto(cre),
                    "dependencia": REDE_REFERENCIA,
                    "estudantes": part_cre,
                    "media_geral": _media_pond(grp, "MEDIA_GERAL"),
                    "tx_part_efetiva": round(100 * part_cre / conc_cre, 1) if conc_cre else None,
                    "fonte": "inep_escola",
                })
                out["participacao_cre"].append({
                    "ano": ano,
                    "cre_curto": cre_curto(cre),
                    "dependencia": REDE_REFERENCIA,
                    "presentes_filt": part_cre,
                    "matriculados": mat_cre,
                    "concluintes": conc_cre,
                    "fonte": "inep_escola",
                })

        for mun, grp in ms_enr.groupby("NO_MUNICIPIO_ESC", observed=True):
            mat_mun = _sum_col(grp, "NU_MATRICULAS")
            part_mun = _sum_col(grp, "NU_PARTICIPANTES")
            conc_mun = _concluintes_grupo(ano, grp, conc_esc, municipio=str(mun))
            out["evolucao_muni"].append({
                "ano": ano,
                "NO_MUNICIPIO_ESC": mun,
                "dependencia": REDE_REFERENCIA,
                "estudantes": part_mun,
                "media_geral": _media_pond(grp, "MEDIA_GERAL"),
                "fonte": "inep_escola",
            })
            out["participacao_municipios"].append({
                "ano": ano,
                "NO_MUNICIPIO_ESC": mun,
                "dependencia": REDE_REFERENCIA,
                "presentes_filt": part_mun,
                "matriculados": mat_mun,
                "concluintes": conc_mun,
                "fonte": "inep_escola",
            })

        esc = ms_enr.groupby("CO_ESCOLA", observed=True).agg(
            estudantes=("NU_PARTICIPANTES", "sum"),
            matriculados=("NU_MATRICULAS", "sum"),
            NOME_ESCOLA=("NOME_ESCOLA", "first"),
            NO_MUNICIPIO_ESC=("NO_MUNICIPIO_ESC", "first"),
            CRE=("CRE", "first"),
        ).reset_index()
        med_esc = ms_enr_med.groupby("CO_ESCOLA", observed=True).agg(
            media_geral=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
        ).reset_index() if not ms_enr_med.empty else pd.DataFrame(columns=["CO_ESCOLA"])
        if not med_esc.empty:
            esc = esc.merge(med_esc, on="CO_ESCOLA", how="left")
        esc_sem = ms_enr_med[ms_enr_med["SEM_ZERO"]].groupby("CO_ESCOLA", observed=True).agg(
            estudantes_sem_zero=("NU_PARTICIPANTES", "sum"),
            media_geral_sem_zero=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}_sem_zero": (c, "mean") for c in COLS_NOTAS},
        ).reset_index()
        if not esc_sem.empty:
            esc = esc.merge(esc_sem, on="CO_ESCOLA", how="left")
        esc["ano"] = ano
        esc["dependencia"] = REDE_REFERENCIA
        esc["cre_curto"] = esc["CRE"].map(cre_curto)
        if not conc_esc.empty:
            ce = conc_esc[conc_esc["NU_ANO"] == ano][["CO_ESCOLA", "Concluintes"]]
            esc = esc.merge(ce, on="CO_ESCOLA", how="left")
        if "Concluintes" not in esc.columns:
            esc["Concluintes"] = esc["matriculados"]
        else:
            esc["Concluintes"] = esc["Concluintes"].fillna(esc["matriculados"]).astype(int)
            zero_mask = esc["Concluintes"] <= 0
            esc.loc[zero_mask, "Concluintes"] = esc.loc[zero_mask, "matriculados"].fillna(0).astype(int)
        esc["tx_part"] = (esc["estudantes"] / esc["Concluintes"].replace(0, np.nan) * 100).round(1)
        esc["observacao"] = esc["CO_ESCOLA"].map(observacao_oferta_escola)
        esc["nome_exibicao"] = esc.apply(
            lambda r: nome_exibicao_escola(r["CO_ESCOLA"], r["NOME_ESCOLA"]),
            axis=1,
        )
        esc["fonte"] = "inep_escola"
        out["evolucao_escolas"].append(esc)

        n_ms = _sum_col(ms_est, "NU_PARTICIPANTES")
        n_ms_sz = _sum_col(ms_est_sz, "NU_PARTICIPANTES")
        srow = {
            "ano": ano,
            "total_inscritos": n_ms,
            "total_validos": n_ms,
            "total_validos_sem_zero": n_ms_sz,
            "total_matriculados": mat_ano,
            "fonte": "inep_escola",
        }
        for c in COLS_NOTAS + ["MEDIA_GERAL"]:
            srow[f"media_{c.lower()}"] = _media_pond(ms_est_med, c) if not ms_est_med.empty else None
            srow[f"media_br_{c.lower()}"] = _media_pond(br_est, c) if not br_est.empty else None
            srow[f"media_{c.lower()}_sem_zero"] = _media_pond(ms_est_sz, c) if not ms_est_sz.empty else None
            srow[f"media_br_{c.lower()}_sem_zero"] = _media_pond(br_sem, c) if not br_sem.empty else None
        out["sumario"].append(srow)

    for c in COLS_NOTAS + ["MEDIA_GERAL"]:
        out["referencias"].append({
            "ano": ano,
            "area": c,
            "media_ms": _media_pond(ms_est_med, c) if not ms_est_med.empty else None,
            "media_br": _media_pond(br_est, c) if not br_est.empty else None,
            "media_ms_sem_zero": _media_pond(ms_est_sz, c) if not ms_est_sz.empty else None,
            "media_br_sem_zero": _media_pond(br_sem, c) if not br_sem.empty else None,
            "fonte": "inep_escola",
        })

    for area, col in zip(AREA_KEYS, COLS_NOTAS):
        ms_s = ms_est_med[col].dropna() if not ms_est_med.empty else pd.Series(dtype=float)
        br_s = br_est[col].dropna() if not br_est.empty else pd.Series(dtype=float)
        ms_s_sz = ms_est_sz[col].dropna() if not ms_est_sz.empty else pd.Series(dtype=float)
        br_s_sz = br_sem[col].dropna() if not br_sem.empty else pd.Series(dtype=float)
        out["histograma"].append({
            "ano": ano, "area": area, "ms": _hist_pct(ms_s), "br": _hist_pct(br_s), "fonte": "inep_escola",
        })
        out["histograma_sem_zero"].append({
            "ano": ano, "area": area, "ms": _hist_pct(ms_s_sz), "br": _hist_pct(br_s_sz), "fonte": "inep_escola",
        })
        std = ms_s.std()
        mean = ms_s.mean()
        out["desvio_cv"].append({
            "ano": ano,
            "area": area,
            "desvio": round(float(std), 1) if pd.notna(std) else None,
            "cv": round(100 * float(std) / float(mean), 1) if pd.notna(std) and mean else None,
            "fonte": "inep_escola",
        })
        q = quantis_serie(ms_s) if not ms_s.empty else quantis_serie(pd.Series(dtype=float))
        q.update({"ano": ano, "area": area, "escopo": "MS-Estadual", "fonte": "inep_escola"})
        out["quantis"].append(q)
        qsz = quantis_serie(ms_s_sz) if not ms_s_sz.empty else quantis_serie(pd.Series(dtype=float))
        qsz.update({"ano": ano, "area": area, "escopo": "MS-Estadual-sem-zero", "fonte": "inep_escola"})
        out["quantis_sem_zero"].append(qsz)
        detail = _area_detail_escolas(ms_est_med, area, col)
        detail.update({"ano": ano, "area": area, "fonte": "inep_escola"})
        out["area_detail"].append(detail)
        detail_sz = _area_detail_escolas(ms_est_sz, area, col) if not ms_est_sz.empty else detail.copy()
        detail_sz.update({"ano": ano, "area": area, "fonte": "inep_escola"})
        out["area_detail_sem_zero"].append(detail_sz)

    return out
