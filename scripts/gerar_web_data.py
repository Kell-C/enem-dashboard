"""
Exporta data.json e painel_data.js para pipeline_dashboard/web/data/.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
import logging

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import ANOS, ANO_FINAL, AREA_KEYS, NOTA_MAP, PASTA_AGREGADOS, POP_REF_PARTICIPANTES, POP_REF_RESUMO, WEB_DATA, configure_logging

logger = configure_logging(__name__)
from enem_helpers import COL_MUNICIPIO, carregar_concluintes_sed, cre_curto, normalizar_texto, quantis_serie

REF_AREAS = {
    "CN": "NU_NOTA_CN",
    "CH": "NU_NOTA_CH",
    "LC": "NU_NOTA_LC",
    "MT": "NU_NOTA_MT",
    "RED": "NU_NOTA_REDACAO",
}


def _ler(name: str) -> pd.DataFrame:
    p = PASTA_AGREGADOS / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def _rank_school_name(row: pd.Series, nome_col: str) -> str:
    nome = row.get(nome_col)
    if pd.notna(nome) and str(nome).strip():
        return str(nome).strip()
    nome_base = row.get("NOME_ESCOLA")
    if pd.notna(nome_base) and str(nome_base).strip():
        return str(nome_base).strip()
    codigo = row.get("CO_ESCOLA")
    if pd.notna(codigo):
        try:
            return str(int(float(codigo)))
        except (TypeError, ValueError):
            return str(codigo).strip()
    return ""


def _school_id(value) -> str:
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def _serie_por_ano(df: pd.DataFrame, dep: str, col: str, anos=ANOS) -> list:
    out = []
    for a in anos:
        sub = df[(df["ano"] == a) & (df["dependencia"] == dep)]
        out.append(round(float(sub.iloc[0][col]), 1) if not sub.empty and pd.notna(sub.iloc[0][col]) else None)
    return out


def _areas_serie(evol_cre: pd.DataFrame, cre_name: str, dep: str = "Estadual") -> dict:
    areas = {}
    sub = evol_cre[(evol_cre["cre_curto"] == cre_name) & (evol_cre["dependencia"] == dep)]
    for k in AREA_KEYS:
        col = f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao"
        if col not in sub.columns:
            col = f"media_{NOTA_MAP[k].lower()}"
        areas[k] = []
        for a in ANOS:
            row = sub[sub["ano"] == a]
            areas[k].append(
                round(float(row.iloc[0][col]), 1)
                if not row.empty and col in row.columns and pd.notna(row.iloc[0][col])
                else None
            )
    return areas


def _serie_refs(refs: pd.DataFrame, area: str, col: str) -> list:
    out = []
    for a in ANOS:
        row = refs[(refs["ano"] == a) & (refs["area"] == area)]
        if row.empty or col not in row.columns or pd.isna(row.iloc[0][col]):
            out.append(None)
        else:
            out.append(round(float(row.iloc[0][col]), 1))
    return out


def _weighted_mean(df: pd.DataFrame, value_col: str, weight_col: str) -> float | None:
    if df.empty or value_col not in df.columns or weight_col not in df.columns:
        return None
    sub = df[[value_col, weight_col]].copy()
    sub[value_col] = pd.to_numeric(sub[value_col], errors="coerce")
    sub[weight_col] = pd.to_numeric(sub[weight_col], errors="coerce")
    sub = sub.dropna(subset=[value_col, weight_col])
    sub = sub[sub[weight_col] > 0]
    if sub.empty:
        return None
    return float(np.average(sub[value_col], weights=sub[weight_col]))


def _school_history_by_municipality(evol_esc: pd.DataFrame) -> dict:
    out = {}
    if evol_esc.empty:
        return out

    nome_col = "nome_exibicao" if "nome_exibicao" in evol_esc.columns else "NOME_ESCOLA"
    col_map = {
        "CN": "media_nu_nota_cn",
        "CH": "media_nu_nota_ch",
        "LC": "media_nu_nota_lc",
        "MT": "media_nu_nota_mt",
        "RED": "media_nu_nota_redacao",
    }
    col_map_sem_zero = {k: f"{col}_sem_zero" for k, col in col_map.items()}

    for mname, grp_m in evol_esc.groupby("NO_MUNICIPIO_ESC"):
        muni_hist = {}
        for school_id, grp in grp_m.groupby("CO_ESCOLA"):
            grp = grp.sort_values("ano")
            sid = _school_id(school_id)
            if not sid:
                continue
            sample = grp.iloc[0]
            obs = None
            if "observacao" in grp.columns:
                for value in grp["observacao"]:
                    if pd.notna(value) and str(value).strip():
                        obs = str(value)
                        break
            item = {
                "id": sid,
                "nome": _rank_school_name(sample, nome_col),
                "mun": str(mname),
                "cre": str(cre_curto(sample.get("CRE"))) if pd.notna(sample.get("CRE")) else None,
                "obs": obs,
                "anos": ANOS,
                "part": [],
                "concl": [],
                "tx": [],
                "geral": [],
                "areas": {k: [] for k in AREA_KEYS},
                "semZero": {
                    "part": [],
                    "tx": [],
                    "geral": [],
                    "areas": {k: [] for k in AREA_KEYS},
                },
            }
            for ano in ANOS:
                row = grp[grp["ano"] == ano]
                if row.empty:
                    item["part"].append(0)
                    item["concl"].append(0)
                    item["tx"].append(None)
                    item["geral"].append(None)
                    item["semZero"]["part"].append(0)
                    item["semZero"]["tx"].append(None)
                    item["semZero"]["geral"].append(None)
                    for k in AREA_KEYS:
                        item["areas"][k].append(None)
                        item["semZero"]["areas"][k].append(None)
                    continue
                r = row.iloc[0]
                item["part"].append(int(r.get("estudantes", 0) or 0))
                item["concl"].append(int(r.get("Concluintes", 0) or 0))
                item["tx"].append(round(float(r["tx_part"]), 1) if pd.notna(r.get("tx_part")) else None)
                item["geral"].append(round(float(r["media_geral"]), 1) if pd.notna(r.get("media_geral")) else None)
                item["semZero"]["part"].append(int(r.get("estudantes_sem_zero", 0) or 0))
                item["semZero"]["tx"].append(round(float(r["tx_part_sem_zero"]), 1) if pd.notna(r.get("tx_part_sem_zero")) else None)
                item["semZero"]["geral"].append(
                    round(float(r["media_geral_sem_zero"]), 1) if pd.notna(r.get("media_geral_sem_zero")) else None
                )
                for k, col in col_map.items():
                    item["areas"][k].append(round(float(r[col]), 1) if pd.notna(r.get(col)) else None)
                    col_zero = col_map_sem_zero[k]
                    item["semZero"]["areas"][k].append(
                        round(float(r[col_zero]), 1) if pd.notna(r.get(col_zero)) else None
                    )
            muni_hist[sid] = item
        out[str(mname)] = muni_hist
    return out


def _uf_rank_por_ano(des_uf: pd.DataFrame, col: str = "media_geral") -> dict:
    out = {}
    for a in ANOS:
        sub = des_uf[(des_uf["ano"] == a) & (des_uf["dependencia"] == "Estadual")].sort_values(
            col, ascending=False
        )
        if col not in sub.columns:
            out[str(a)] = []
            continue
        sub = sub[sub[col].notna()]
        out[str(a)] = [[str(row["UF"]), round(float(row[col]), 0)] for _, row in sub.iterrows()]
    return out


def _rank_ms_por_ano(des_uf: pd.DataFrame, col: str = "media_geral") -> list:
    ranks = []
    for a in ANOS:
        sub = des_uf[(des_uf["ano"] == a) & (des_uf["dependencia"] == "Estadual")].copy()
        if sub.empty or "UF" not in sub.columns or col not in sub.columns:
            ranks.append(None)
            continue
        sub = sub[sub[col].notna()].sort_values(col, ascending=False).reset_index(drop=True)
        if "MS" not in sub["UF"].values:
            ranks.append(None)
            continue
        ranks.append(int(sub.index[sub["UF"] == "MS"].tolist()[0]) + 1)
    return ranks


def _muni_areas(grp: pd.DataFrame) -> dict:
    areas = {}
    for k in AREA_KEYS:
        col = f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao"
        serie = []
        for a in ANOS:
            row = grp[grp["ano"] == a]
            if row.empty or col not in row.columns or pd.isna(row.iloc[0][col]):
                serie.append(None)
            else:
                serie.append(round(float(row.iloc[0][col]), 1))
        areas[k] = serie
    return areas


def _histograma_bins(df_quantis, area: str) -> dict:
    out = {}
    for a in ANOS:
        row = df_quantis[(df_quantis["ano"] == a) & (df_quantis["area"] == area)]
        out[str(a)] = row.iloc[0].to_dict() if not row.empty else quantis_serie(pd.Series(dtype=float))
    return out


def _histograma_faixas(df_hist, area: str) -> dict:
    out = {}
    for a in ANOS:
        row = df_hist[(df_hist["ano"] == a) & (df_hist["area"] == area)]
        if row.empty:
            out[str(a)] = {"ms": [0.0] * 6, "br": [0.0] * 6}
        else:
            r = row.iloc[0]
            out[str(a)] = {"ms": list(r["ms"]), "br": list(r["br"])}
    return out


def _area_detail_web(df_detail, area: str, br_n_by_ano: dict[int, int], hist_df) -> dict:
    out = {}
    hist_cols = [
        "h_sem", "h_zero", "h_1_200", "h_200_400",
        "h_400_500", "h_500_600", "h_600_800", "h_800_1000",
    ]
    count_cols = [
        "c_sem", "c_zero", "c_1_200", "c_200_400",
        "c_400_500", "c_500_600", "c_600_800", "c_800_1000",
    ]
    for a in ANOS:
        row = df_detail[(df_detail["ano"] == a) & (df_detail["area"] == area)]
        if row.empty:
            continue
        r = row.iloc[0]
        br_n = int(br_n_by_ano.get(a, 0))
        br_row = hist_df[(hist_df["ano"] == a) & (hist_df["area"] == area)]
        br6 = list(br_row.iloc[0]["br"]) if not br_row.empty else [0.0] * 6
        br_counts6 = [int(round(br_n * p / 100.0)) for p in br6]
        out[str(a)] = {
            "n": int(r["n"]),
            "brN": br_n,
            "pctSemNota": float(r["pct_sem_nota"]),
            "pctZero": float(r["pct_zero"]),
            "moda": float(r["moda"]) if pd.notna(r.get("moda")) else None,
            "modaFaixa": str(r["moda_faixa"]) if pd.notna(r.get("moda_faixa")) else None,
            "modaTipo": "nota",
            "minPos": float(r["min_pos"]) if pd.notna(r.get("min_pos")) else None,
            "minPosExact": True,
            "histPct": [float(r[c]) for c in hist_cols],
            "histCounts": [int(r[c]) for c in count_cols],
            "brHistPct6": [float(p) for p in br6],
            "brHistCounts6": br_counts6,
        }
    return out


def _serie_desvio_cv(df: pd.DataFrame, area: str, col: str) -> tuple[list, list]:
    desvio, cv = [], []
    for a in ANOS:
        row = df[(df["ano"] == a) & (df["area"] == area)]
        if row.empty:
            desvio.append(None)
            cv.append(None)
        else:
            desvio.append(float(row.iloc[0][col]) if pd.notna(row.iloc[0][col]) else None)
            cv.append(float(row.iloc[0]["cv"]) if pd.notna(row.iloc[0]["cv"]) else None)
    return desvio, cv


def _integ_territorial(df: pd.DataFrame, key_col: str, cre_col: str | None = None) -> dict:
    out = {}
    if df.empty or key_col not in df.columns:
        return out
    for name, grp in df.groupby(key_col, observed=True):
        item = {
            "filt": [],
            "et": [],
            "em": [],
            "zm": [],
            "sm": [],
            "txE": [],
            "txS": [],
        }
        if cre_col and cre_col in grp.columns:
            item["cre"] = str(grp.iloc[0][cre_col])
        for a in ANOS:
            row = grp[grp["ano"] == a]
            if row.empty:
                item["filt"].append(0)
                item["et"].append(0)
                item["em"].append(0)
                item["zm"].append(0)
                item["sm"].append(0)
                item["txE"].append(None)
                item["txS"].append(None)
            else:
                r = row.iloc[0]
                item["filt"].append(int(r["filt"]))
                item["et"].append(int(r["elim_redacao"]))
                item["em"].append(int(r.get("em", 0)))
                item["zm"].append(int(r.get("zm", 0)))
                item["sm"].append(int(r.get("sm", 0)))
                item["txE"].append(float(r["tx_elim"]) if pd.notna(r["tx_elim"]) else None)
                item["txS"].append(float(r["tx_sem_nota"]) if pd.notna(r["tx_sem_nota"]) else None)
        out[str(name)] = item
    return out


def build_painel_data() -> dict:
    part = _ler("participacao_ano")
    des = _ler("desempenho")
    des_uf = _ler("desempenho_uf")
    evol_cre = _ler("evolucao_cre")
    evol_muni = _ler("evolucao_muni")
    evol_esc = _ler("evolucao_escolas")
    esc24 = _ler("escolas_2024")
    refs = _ler("referencias")
    quantis = _ler("quantis")
    quantis_sem_zero = _ler("quantis_sem_zero")
    integ_df = _ler("integridade")
    integ_cre_df = _ler("integridade_cre")
    integ_muni_df = _ler("integridade_muni")
    hist_df = _ler("histograma")
    hist_sem_zero_df = _ler("histograma_sem_zero")
    detail_df = _ler("area_detail")
    detail_sem_zero_df = _ler("area_detail_sem_zero")
    desvio_df = _ler("desvio_cv")
    _, conc_esc = carregar_concluintes_sed()

    ms_part = part[part["dependencia"] == "Estadual"].sort_values("ano")
    br_part = part[part["dependencia"] == "Brasil-Estadual"].sort_values("ano")
    estadual_n = [int(r["presentes_filt"]) for _, r in ms_part.iterrows()]
    br_estadual_n = [int(r["presentes_filt"]) for _, r in br_part.iterrows()]
    estadual_n_sem_zero = [int(r.get("presentes_filt_sem_zero", 0)) for _, r in ms_part.iterrows()]
    br_estadual_n_sem_zero = [int(r.get("presentes_filt_sem_zero", 0)) for _, r in br_part.iterrows()]
    br_n_by_ano = {int(r["ano"]): int(r["presentes_filt"]) for _, r in br_part.iterrows()}
    br_n_sem_zero_by_ano = {int(r["ano"]): int(r.get("presentes_filt_sem_zero", 0)) for _, r in br_part.iterrows()}
    estadual_concl = [int(r["concluintes"]) for _, r in ms_part.iterrows()]
    tx_ms = [round(100 * n / c, 1) if c else None for n, c in zip(estadual_n, estadual_concl)]
    tx_ms_sem_zero = [round(100 * n / c, 1) if c and n else None for n, c in zip(estadual_n_sem_zero, estadual_concl)]

    med_ms = _serie_refs(refs, "MEDIA_GERAL", "media_ms")
    if not any(v is not None for v in med_ms):
        med_ms = [
            round(float(des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].iloc[0]["media_media_geral"]), 1)
            if not des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].empty
            else None
            for a in ANOS
        ]
    med_br = _serie_refs(refs, "MEDIA_GERAL", "media_br")
    med_ms_sem_zero = _serie_refs(refs, "MEDIA_GERAL", "media_ms_sem_zero")
    med_br_sem_zero = _serie_refs(refs, "MEDIA_GERAL", "media_br_sem_zero")
    if not any(v is not None for v in med_ms_sem_zero):
        med_ms_sem_zero = [
            round(float(des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].iloc[0]["media_media_geral_sem_zero"]), 1)
            if not des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].empty and "media_media_geral_sem_zero" in des.columns and pd.notna(des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].iloc[0]["media_media_geral_sem_zero"])
            else None
            for a in ANOS
        ]
    if not any(v is not None for v in med_br_sem_zero):
        med_br_sem_zero = [
            round(float(des[(des["ano"] == a) & (des["dependencia"] == "Brasil-Estadual")].iloc[0]["media_media_geral_sem_zero"]), 1)
            if not des[(des["ano"] == a) & (des["dependencia"] == "Brasil-Estadual")].empty and "media_media_geral_sem_zero" in des.columns and pd.notna(des[(des["ano"] == a) & (des["dependencia"] == "Brasil-Estadual")].iloc[0]["media_media_geral_sem_zero"])
            else None
            for a in ANOS
        ]
    rank_ms = _rank_ms_por_ano(des_uf)
    uf_rank = _uf_rank_por_ano(des_uf)
    rank_ms_sem_zero = _rank_ms_por_ano(des_uf, "media_geral_sem_zero")
    uf_rank_sem_zero = _uf_rank_por_ano(des_uf, "media_geral_sem_zero")

    funil2024 = {}
    for dep in ["Federal", "Estadual", "Municipal", "Privada"]:
        row = part[(part["ano"] == ANO_FINAL) & (part["dependencia"] == dep)]
        if row.empty:
            continue
        r = row.iloc[0]
        funil2024[dep] = {
            "inscritos": int(r["inscritos"]),
            "presentes": int(r["presentes"]),
            "eliminados": int(r.get("eliminados_redacao", 0)),
            "redacao_branco": int(r.get("redacao_branco", 0)),
            "concluintes": int(r["concluintes"]) if pd.notna(r.get("concluintes")) else None,
            "presfilt": int(r["presentes_filt"]),
        }

    redes = {}
    for dep in ["Estadual", "Municipal", "Federal", "Privada"]:
        redes[dep] = {
            "med": _serie_por_ano(des, dep, "media_media_geral"),
            "n": _serie_por_ano(part, dep, "presentes_filt"),
            "areas": {
                k: _serie_por_ano(des, dep, f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao")
                for k in AREA_KEYS
            },
        }

    cre_names = sorted(evol_cre[evol_cre["dependencia"] == "Estadual"]["cre_curto"].dropna().unique())
    cre = {}
    for name in cre_names:
        sub = evol_cre[(evol_cre["cre_curto"] == name) & (evol_cre["dependencia"] == "Estadual")]
        med, n, tx = [], [], []
        for a in ANOS:
            row = sub[sub["ano"] == a]
            if row.empty:
                med.append(None)
                n.append(0)
                tx.append(None)
            else:
                med.append(round(float(row.iloc[0]["media_geral"]), 1))
                n.append(int(row.iloc[0]["estudantes"]))
                tx.append(
                    round(float(row.iloc[0]["tx_part_efetiva"]), 1)
                    if "tx_part_efetiva" in row.columns and pd.notna(row.iloc[0]["tx_part_efetiva"])
                    else None
                )
        cre[name] = {"med": med, "tx": tx, "n": n, "areas": _areas_serie(evol_cre, name)}

    mun = {}
    if not evol_muni.empty:
        for mname, grp in evol_muni[evol_muni["dependencia"] == "Estadual"].groupby("NO_MUNICIPIO_ESC"):
            med, n, tx = [], [], []
            a2024 = {}
            for a in ANOS:
                row = grp[grp["ano"] == a]
                if row.empty:
                    med.append(None)
                    n.append(0)
                    tx.append(None)
                else:
                    med.append(round(float(row.iloc[0]["media_geral"]), 1))
                    n.append(int(row.iloc[0]["estudantes"]))
                    conc = conc_esc[
                        (conc_esc["NU_ANO"] == a)
                        & (conc_esc[COL_MUNICIPIO].map(normalizar_texto) == normalizar_texto(mname))
                    ]["Concluintes"].sum()
                    tx.append(round(100 * row.iloc[0]["estudantes"] / conc, 1) if conc else None)
                    if a == ANO_FINAL:
                        for k in AREA_KEYS:
                            col = f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao"
                            if col in row.columns and pd.notna(row.iloc[0][col]):
                                a2024[k] = round(float(row.iloc[0][col]), 1)
            conc24 = conc_esc[
                (conc_esc["NU_ANO"] == ANO_FINAL)
                & (conc_esc[COL_MUNICIPIO].map(normalizar_texto) == normalizar_texto(mname))
            ]["Concluintes"].sum()
            part24 = int(grp[grp["ano"] == ANO_FINAL]["estudantes"].sum()) if ANO_FINAL in grp["ano"].values else 0
            mun[str(mname)] = {
                "cre": cre_curto(grp["CRE"].iloc[0]) if "CRE" in grp.columns else "SED",
                "med": med,
                "tx": tx,
                "n": n,
                "concl": int(conc24),
                "part2024": part24,
                "a2024": a2024,
                "areas": _muni_areas(grp),
            }

    esc = {}
    esc_hist = _school_history_by_municipality(evol_esc)
    dispersao = []
    if not esc24.empty:
        for mname, grp in esc24.groupby("NO_MUNICIPIO_ESC"):
            rows = []
            for _, r in grp.sort_values("media_geral").iterrows():
                conc = int(r["Concluintes"]) if pd.notna(r.get("Concluintes")) else 0
                part_n = int(r["estudantes"])
                part_n_sem_zero = int(r.get("estudantes_sem_zero", 0)) if pd.notna(r.get("estudantes_sem_zero")) else 0
                tx = round(100 * part_n / conc, 1) if conc else None
                tx_sem_zero = round(100 * part_n_sem_zero / conc, 1) if conc and part_n_sem_zero else None
                nome_exib = _rank_school_name(r, "nome_exibicao" if "nome_exibicao" in esc24.columns else "NOME_ESCOLA")
                obs = r.get("observacao")
                if pd.isna(obs):
                    obs = None
                item = {
                    "id": _school_id(r.get("CO_ESCOLA")),
                    "nome": str(nome_exib),
                    "obs": obs,
                    "part": part_n,
                    "concl": conc,
                    "tx": tx,
                    "cn": round(float(r["media_nu_nota_cn"]), 1),
                    "ch": round(float(r["media_nu_nota_ch"]), 1),
                    "lc": round(float(r["media_nu_nota_lc"]), 1),
                    "mt": round(float(r["media_nu_nota_mt"]), 1),
                    "red": round(float(r["media_nu_nota_redacao"]), 1),
                    "geral": round(float(r["media_geral"]), 1),
                    "semZero": {
                        "part": part_n_sem_zero,
                        "tx": tx_sem_zero,
                        "cn": round(float(r["media_nu_nota_cn_sem_zero"]), 1) if pd.notna(r.get("media_nu_nota_cn_sem_zero")) else None,
                        "ch": round(float(r["media_nu_nota_ch_sem_zero"]), 1) if pd.notna(r.get("media_nu_nota_ch_sem_zero")) else None,
                        "lc": round(float(r["media_nu_nota_lc_sem_zero"]), 1) if pd.notna(r.get("media_nu_nota_lc_sem_zero")) else None,
                        "mt": round(float(r["media_nu_nota_mt_sem_zero"]), 1) if pd.notna(r.get("media_nu_nota_mt_sem_zero")) else None,
                        "red": round(float(r["media_nu_nota_redacao_sem_zero"]), 1) if pd.notna(r.get("media_nu_nota_redacao_sem_zero")) else None,
                        "geral": round(float(r["media_geral_sem_zero"]), 1) if pd.notna(r.get("media_geral_sem_zero")) else None,
                    },
                }
                rows.append(item)
                dispersao.append({
                    "nome": item["nome"],
                    "obs": obs,
                    "mun": str(mname),
                    "cre": cre_curto(r.get("CRE")),
                    "nota": item["geral"],
                    "n": part_n,
                    "tx": tx,
                    "notaSemZero": item["semZero"]["geral"],
                    "nSemZero": part_n_sem_zero,
                    "txSemZero": tx_sem_zero,
                })
            esc[str(mname)] = rows

    integ = {"rede": {}, "cre": {}, "mun": {}}
    for escopo in ["Estadual", "Federal", "Municipal", "Privada", "Brasil-Estadual"]:
        sub = integ_df[integ_df["escopo"] == escopo] if "escopo" in integ_df.columns else pd.DataFrame()
        if sub.empty:
            continue
        integ["rede"][escopo] = {
            "comp": [int(sub[sub["ano"] == a].iloc[0]["compareceu_2d"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
            "filt": [int(sub[sub["ano"] == a].iloc[0]["filt"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
            "et": [int(sub[sub["ano"] == a].iloc[0]["elim_redacao"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
            "er": [int(sub[sub["ano"] == a].iloc[0]["elim_redacao"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
            "txE": [float(sub[sub["ano"] == a].iloc[0]["tx_elim"]) if not sub[sub["ano"] == a].empty else None for a in ANOS],
            "txS": [float(sub[sub["ano"] == a].iloc[0]["tx_sem_nota"]) if not sub[sub["ano"] == a].empty else None for a in ANOS],
            "areaElim": {
                "CN": [int(sub[sub["ano"] == a].iloc[0]["elim_cn"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
                "CH": [int(sub[sub["ano"] == a].iloc[0]["elim_ch"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
                "LC": [int(sub[sub["ano"] == a].iloc[0]["elim_lc"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
                "MT": [int(sub[sub["ano"] == a].iloc[0]["elim_mt"]) if not sub[sub["ano"] == a].empty else 0 for a in ANOS],
            },
            "em": [int(sub[sub["ano"] == a].iloc[0]["em"]) if not sub[sub["ano"] == a].empty and "em" in sub.columns else 0 for a in ANOS],
            "zm": [int(sub[sub["ano"] == a].iloc[0]["zm"]) if not sub[sub["ano"] == a].empty and "zm" in sub.columns else 0 for a in ANOS],
            "sm": [int(sub[sub["ano"] == a].iloc[0]["sm"]) if not sub[sub["ano"] == a].empty and "sm" in sub.columns else 0 for a in ANOS],
            "sn": [0] * len(ANOS),
        }
    integ["cre"] = _integ_territorial(integ_cre_df, "cre_curto")
    integ["mun"] = _integ_territorial(integ_muni_df, "NO_MUNICIPIO_ESC", cre_col="cre_curto")

    boxplot = {k: _histograma_bins(quantis, k) for k in AREA_KEYS}
    boxplot_sem_zero = {k: _histograma_bins(quantis_sem_zero, k) for k in AREA_KEYS}
    histograma = {k: _histograma_faixas(hist_df, k) for k in AREA_KEYS}
    histograma_sem_zero = {k: _histograma_faixas(hist_sem_zero_df, k) for k in AREA_KEYS}
    areaDetail = {k: _area_detail_web(detail_df, k, br_n_by_ano, hist_df) for k in AREA_KEYS}
    areaDetailSemZero = {k: _area_detail_web(detail_sem_zero_df, k, br_n_sem_zero_by_ano, hist_sem_zero_df) for k in AREA_KEYS}
    desvio_padrao = {}
    cv = {}
    for k in AREA_KEYS:
        desvio_padrao[k], cv[k] = _serie_desvio_cv(desvio_df, k, "desvio")
    esc_rank = {k: [] for k in AREA_KEYS}
    esc_rank_sem_zero = {k: [] for k in AREA_KEYS}
    if not esc24.empty:
        col_map = {
            "CN": "media_nu_nota_cn", "CH": "media_nu_nota_ch", "LC": "media_nu_nota_lc",
            "MT": "media_nu_nota_mt", "RED": "media_nu_nota_redacao",
        }
        for k, col in col_map.items():
            nome_col = "nome_exibicao" if "nome_exibicao" in esc24.columns else "NOME_ESCOLA"
            tmp = esc24[[c for c in [nome_col, "NOME_ESCOLA", "CO_ESCOLA", "estudantes", col] if c in esc24.columns]].dropna(subset=[col]).copy()
            if "NO_MUNICIPIO_ESC" in esc24.columns:
                tmp["mun"] = esc24.loc[tmp.index, "NO_MUNICIPIO_ESC"].astype(str)
            if "CRE" in esc24.columns:
                tmp["cre"] = esc24.loc[tmp.index, "CRE"].map(cre_curto)
            if "estudantes" in tmp.columns:
                tmp = tmp[tmp["estudantes"] >= 10]
            tmp["nome_rank"] = tmp.apply(lambda r: _rank_school_name(r, nome_col), axis=1)
            tmp = tmp[tmp["nome_rank"].str.strip() != ""].sort_values(col, ascending=False)
            for _, r in tmp.head(10).iterrows():
                esc_rank[k].append({
                    "nome": r["nome_rank"],
                    "nota": round(float(r[col]), 1),
                    "mun": str(r["mun"]) if pd.notna(r.get("mun")) else None,
                    "cre": str(r["cre"]) if pd.notna(r.get("cre")) else None,
                })
            for _, r in tmp.tail(10).sort_values(col).iterrows():
                esc_rank[k].append({
                    "nome": r["nome_rank"],
                    "nota": round(float(r[col]), 1),
                    "mun": str(r["mun"]) if pd.notna(r.get("mun")) else None,
                    "cre": str(r["cre"]) if pd.notna(r.get("cre")) else None,
                })
            col_sem_zero = f"{col}_sem_zero"
            if col_sem_zero in esc24.columns:
                tmp_sem_zero = esc24[[c for c in [nome_col, "NOME_ESCOLA", "CO_ESCOLA", "estudantes_sem_zero", col_sem_zero] if c in esc24.columns]].dropna(subset=[col_sem_zero]).copy()
                if "NO_MUNICIPIO_ESC" in esc24.columns:
                    tmp_sem_zero["mun"] = esc24.loc[tmp_sem_zero.index, "NO_MUNICIPIO_ESC"].astype(str)
                if "CRE" in esc24.columns:
                    tmp_sem_zero["cre"] = esc24.loc[tmp_sem_zero.index, "CRE"].map(cre_curto)
                tmp_sem_zero = tmp_sem_zero[tmp_sem_zero["estudantes_sem_zero"] >= 10]
                tmp_sem_zero["nome_rank"] = tmp_sem_zero.apply(lambda r: _rank_school_name(r, nome_col), axis=1)
                tmp_sem_zero = tmp_sem_zero[tmp_sem_zero["nome_rank"].str.strip() != ""].sort_values(col_sem_zero, ascending=False)
                for _, r in tmp_sem_zero.head(10).iterrows():
                    esc_rank_sem_zero[k].append({
                        "nome": r["nome_rank"],
                        "nota": round(float(r[col_sem_zero]), 1),
                        "mun": str(r["mun"]) if pd.notna(r.get("mun")) else None,
                        "cre": str(r["cre"]) if pd.notna(r.get("cre")) else None,
                    })
                for _, r in tmp_sem_zero.tail(10).sort_values(col_sem_zero).iterrows():
                    esc_rank_sem_zero[k].append({
                        "nome": r["nome_rank"],
                        "nota": round(float(r[col_sem_zero]), 1),
                        "mun": str(r["mun"]) if pd.notna(r.get("mun")) else None,
                        "cre": str(r["cre"]) if pd.notna(r.get("cre")) else None,
                    })

    ms_area_2024 = {}
    ms_area_2024_sem_zero = {}
    d24 = des[(des["ano"] == ANO_FINAL) & (des["dependencia"] == "Estadual")]
    if not d24.empty:
        for k in AREA_KEYS:
            col = f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao"
            if col in d24.columns:
                ms_area_2024[k] = round(float(d24.iloc[0][col]), 1)
    if not esc24.empty and "estudantes_sem_zero" in esc24.columns:
        col_map = {
            "CN": "media_nu_nota_cn_sem_zero",
            "CH": "media_nu_nota_ch_sem_zero",
            "LC": "media_nu_nota_lc_sem_zero",
            "MT": "media_nu_nota_mt_sem_zero",
            "RED": "media_nu_nota_redacao_sem_zero",
        }
        for k, col in col_map.items():
            val = _weighted_mean(esc24, col, "estudantes_sem_zero")
            if val is not None:
                ms_area_2024_sem_zero[k] = round(val, 1)
        ms_geral_2024_sem_zero = _weighted_mean(esc24, "media_geral_sem_zero", "estudantes_sem_zero")
        ms_geral_2024_sem_zero = round(ms_geral_2024_sem_zero, 1) if ms_geral_2024_sem_zero is not None else None
    else:
        ms_geral_2024_sem_zero = None

    index_areas = {k: _serie_refs(refs, REF_AREAS[k], "media_ms") for k in AREA_KEYS}
    index_areas_sem_zero = {k: _serie_refs(refs, REF_AREAS[k], "media_ms_sem_zero") for k in AREA_KEYS}
    ms_area_series = {
        k: {"ms": _serie_refs(refs, REF_AREAS[k], "media_ms"), "br": _serie_refs(refs, REF_AREAS[k], "media_br")}
        for k in AREA_KEYS
    }
    ms_area_series_sem_zero = {
        k: {"ms": _serie_refs(refs, REF_AREAS[k], "media_ms_sem_zero"), "br": _serie_refs(refs, REF_AREAS[k], "media_br_sem_zero")}
        for k in AREA_KEYS
    }

    tx_elim = [
        float(ms_part[ms_part["ano"] == a].iloc[0]["eliminados_redacao"])
        / float(ms_part[ms_part["ano"] == a].iloc[0]["presentes"])
        * 100
        if not ms_part[ms_part["ano"] == a].empty and ms_part[ms_part["ano"] == a].iloc[0]["presentes"]
        else None
        for a in ANOS
    ]
    tx_elim = [round(x, 2) if x is not None else None for x in tx_elim]

    meta = {
        "filtros": {
            "populacao_referencia": POP_REF_PARTICIPANTES,
            "areas_objetivas": POP_REF_RESUMO,
            "concluintes_2019_2023": "TP_ST_CONCLUSAO = 2",
            "concluintes_2024": "CO_ESCOLA preenchido (RESULTADOS; pode incluir EJA/outras modalidades)",
            "presentes": "TP_PRESENCA = 1 em ao menos uma area objetiva (CN, CH, LC ou MT)",
            "eliminados": "TP_PRESENCA = 2 ou TP_STATUS_REDACAO = 2",
            "redacao_branco": "incluidos (TP_STATUS_REDACAO = 4)",
            "concluintes_denominador": "Concluintes 3o ano EM regular (SED)",
            "aviso_2024": "Sem merge PARTICIPANTES+RESULTADOS; taxa vs SED nao homogenea com 2019-2023",
            "concluintes_pos_2024": "Para 2024+ o painel usa RESULTADOS com CO_ESCOLA preenchido como proxy de concluintes vinculados a escola.",
            "media_por_area": "Nota da area considerada apenas se TP_PRESENCA = 1 na area; media geral = media das notas disponiveis.",
        },
        "gerado_em": pd.Timestamp.now().isoformat(),
        "pipeline": "pipeline_dashboard",
    }

    return {
        "meta": meta,
        "anos": ANOS,
        "medMs": med_ms,
        "medBr": med_br,
        "medMsSemZero": med_ms_sem_zero,
        "medBrSemZero": med_br_sem_zero,
        "txMs": tx_ms,
        "txMsSemZero": tx_ms_sem_zero,
        "rankMs": rank_ms,
        "rankMsSemZero": rank_ms_sem_zero,
        "ufRankByYear": uf_rank,
        "ufRankByYearSemZero": uf_rank_sem_zero,
        "msArea2024": ms_area_2024,
        "msGeral2024": med_ms[-1] if med_ms else None,
        "msArea2024SemZero": ms_area_2024_sem_zero,
        "msGeral2024SemZero": ms_geral_2024_sem_zero,
        "indexAreas": index_areas,
        "indexAreasSemZero": index_areas_sem_zero,
        "cre": cre,
        "creMuns": {
            c: sorted(m for m, v in mun.items() if v.get("cre") == c)
            for c in {v.get("cre") for v in mun.values() if v.get("cre")}
        },
        "mun": mun,
        "esc": esc,
        "escHist": esc_hist,
        "msArea": ms_area_series,
        "redes": redes,
        "funil2024": funil2024,
        "estadualN": estadual_n,
        "brEstadualN": br_estadual_n,
        "estadualNSemZero": estadual_n_sem_zero,
        "brEstadualNSemZero": br_estadual_n_sem_zero,
        "estadualConcl": estadual_concl,
        "integ": integ,
        "escRank": esc_rank,
        "escRankSemZero": esc_rank_sem_zero,
        "boxplot": boxplot,
        "boxplotSemZero": boxplot_sem_zero,
        "histograma": histograma,
        "histogramaSemZero": histograma_sem_zero,
        "areaDetail": areaDetail,
        "areaDetailSemZero": areaDetailSemZero,
        "msAreaSemZero": ms_area_series_sem_zero,
        "dispersao": dispersao,
        "desvio_padrao": desvio_padrao,
        "cv": cv,
        "txElim": tx_elim,
    }


def _sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if pd.isna(obj):
        return None
    return obj


def main():
    t0 = time.time()
    if not PASTA_AGREGADOS.exists():
        raise SystemExit("Rode primeiro: python gerar_agregados.py")

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    painel = _sanitize(build_painel_data())

    json_path = WEB_DATA / "data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(painel, f, ensure_ascii=False, separators=(",", ":"))

    js_path = WEB_DATA / "painel_data.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.PAINEL_DATA=")
        json.dump(painel, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";")

    logger.info("Gerado: %s (%s KB)", json_path, json_path.stat().st_size // 1024)
    logger.info("Gerado: %s", js_path)
    f24 = painel["funil2024"]["Estadual"]
    logger.info(
        "MS %s: %s validos / %s concluintes SED = %.1f%%",
        ANO_FINAL,
        f24["presfilt"],
        f24["concluintes"],
        100 * f24["presfilt"] / f24["concluintes"],
    )

    try:
        meta = {
            "script": "gerar_web_data.py",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "duration_seconds": round(time.time() - t0, 1),
            "json_bytes": json_path.stat().st_size,
            "js_bytes": js_path.stat().st_size,
        }
        meta_path = WEB_DATA / "meta_gerar_web_data.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[meta] gravado: %s", meta_path)
    except Exception as e:
        logger.warning("[aviso] nao foi possivel gravar meta: %s", e)


if __name__ == "__main__":
    main()
