"""Gera parquets agregados para o painel ENEM MS."""
from __future__ import annotations

import os
import sys
import time
import json
import datetime
import logging

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import ANOS, ANO_FINAL, AREA_KEYS, COLS_NOTAS, DEPENDENCIAS, NOTA_MAP, PARQUET, PASTA_AGREGADOS, PRES_COLS, WEB_DATA, configure_logging

logger = configure_logging(__name__)
from enem_helpers import (
    aplicar_flags,
    filtrar_valido_area,
    observacao_oferta_escola,
    COL_MUNICIPIO,
    carregar_concluintes_sed,
    carregar_cres,
    carregar_mapa_municipio_cre,
    cre_curto,
    enriquecer_ms,
    limpar,
    nome_exibicao_escola,
    normalizar_texto,
    preparar_ano,
    quantis_serie,
)

HIST_EDGES = [0, 200, 400, 500, 600, 800, 1000.0001]
HIST_POS_EDGES = [1, 200, 400, 500, 600, 800, 1000.0001]
PRES_AREA = {
    "CN": "TP_PRESENCA_CN",
    "CH": "TP_PRESENCA_CH",
    "LC": "TP_PRESENCA_LC",
    "MT": "TP_PRESENCA_MT",
}


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


def _area_detail_stats(val: pd.DataFrame, area: str, col: str) -> dict:
    n = len(val)
    empty = {
        "n": 0,
        "pct_sem_nota": 0.0,
        "pct_zero": 0.0,
        "moda": None,
        "min_pos": None,
        "h_sem": 0.0,
        "h_zero": 0.0,
        "h_1_200": 0.0,
        "h_200_400": 0.0,
        "h_400_500": 0.0,
        "h_500_600": 0.0,
        "h_600_800": 0.0,
        "h_800_1000": 0.0,
    }
    if n == 0:
        return empty

    s = pd.to_numeric(val[col], errors="coerce")
    if area == "RED":
        sem_mask = val["RED_BRANCO"] | s.isna()
    else:
        pres_col = PRES_AREA[area]
        sem_mask = (val[pres_col] != 1) | s.isna()

    zero_mask = (s == 0) & ~sem_mask
    pos = s[(s > 0) & ~sem_mask]

    scorable = s[~sem_mask].dropna()
    moda = round(float(scorable.round().mode().iloc[0]), 1) if not scorable.empty else None
    min_pos = round(float(pos.min()), 1) if not pos.empty else None

    score_counts = []
    for lo, hi in zip(HIST_POS_EDGES[:-1], HIST_POS_EDGES[1:]):
        if hi > 1000:
            score_counts.append(int(((pos >= lo) & (pos <= 1000)).sum()))
        else:
            score_counts.append(int(((pos >= lo) & (pos < hi)).sum()))

    counts = [int(sem_mask.sum()), int(zero_mask.sum()), *score_counts]
    pct = [round(100 * c / n, 1) for c in counts]
    pos_labels = ['1\u2013200', '200\u2013400', '400\u2013500', '500\u2013600', '600\u2013800', '800\u20131000']
    peak_i = max(range(len(score_counts)), key=lambda j: score_counts[j]) if score_counts else 0
    moda_faixa = pos_labels[peak_i] if score_counts and score_counts[peak_i] > 0 else None
    return {
        "n": n,
        "pct_sem_nota": pct[0],
        "pct_zero": pct[1],
        "moda": moda,
        "moda_faixa": moda_faixa,
        "min_pos": min_pos,
        "h_sem": pct[0],
        "h_zero": pct[1],
        "h_1_200": pct[2],
        "h_200_400": pct[3],
        "h_400_500": pct[4],
        "h_500_600": pct[5],
        "h_600_800": pct[6],
        "h_800_1000": pct[7],
        "c_sem": counts[0],
        "c_zero": counts[1],
        "c_1_200": counts[2],
        "c_200_400": counts[3],
        "c_400_500": counts[4],
        "c_500_600": counts[5],
        "c_600_800": counts[6],
        "c_800_1000": counts[7],
    }


def _integridade_row(base: pd.DataFrame, val: pd.DataFrame, extra: dict) -> dict:
    comp = int(base["PRESENTE_2_DIAS"].sum())
    present = base[base["PRESENTE_2_DIAS"]]
    elim_red = int((base["PRESENTE_2_DIAS"] & base["ELIM_RED"]).sum())
    branco = int((base["PRESENTE_2_DIAS"] & base["RED_BRANCO"]).sum())
    em = zm = sm = 0
    if len(present):
        em = int(((present[PRES_COLS] == 2).sum(axis=1) >= 2).sum())
        obj_cols = COLS_NOTAS[:4]
        zm = int(((present[obj_cols] == 0).sum(axis=1) >= 2).sum())
        sm = int(((present[PRES_COLS] == 0).sum(axis=1) >= 2).sum())
    row = {
        "compareceu_2d": comp,
        "filt": len(val),
        "elim_redacao": elim_red,
        "elim_cn": int((base["TP_PRESENCA_CN"] == 2).sum()),
        "elim_ch": int((base["TP_PRESENCA_CH"] == 2).sum()),
        "elim_lc": int((base["TP_PRESENCA_LC"] == 2).sum()),
        "elim_mt": int((base["TP_PRESENCA_MT"] == 2).sum()),
        "em": em,
        "zm": zm,
        "sm": sm,
        "red_branco": branco,
        "tx_elim": round(100 * elim_red / comp, 2) if comp else 0,
        "tx_sem_nota": round(100 * branco / comp, 2) if comp else 0,
    }
    row.update(extra)
    return row


def _cols_parquet() -> list[str]:
    return [
        "NU_ANO",
        "NU_INSCRICAO",
        "NU_SEQUENCIAL",
        "SG_UF_ESC",
        "NO_MUNICIPIO_ESC",
        "TP_DEPENDENCIA_ADM_ESC",
        "CO_ESCOLA",
        "TP_ST_CONCLUSAO",
        *PRES_COLS,
        "TP_STATUS_REDACAO",
        *COLS_NOTAS,
    ]


def _ler_ano(ano: int, cols: list[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq

    schema = pq.read_schema(PARQUET).names
    cols_ok = [c for c in cols if c in schema]
    df = pd.read_parquet(PARQUET, columns=cols_ok, filters=[("NU_ANO", "==", ano)])
    return preparar_ano(df)


def _agregar_escolas_ano(sub: pd.DataFrame, conc_esc: pd.DataFrame, ano: int) -> pd.DataFrame:
    if sub.empty or "CO_ESCOLA" not in sub.columns or not sub["CO_ESCOLA"].notna().any():
        return pd.DataFrame()

    esc = sub.groupby("CO_ESCOLA", observed=True).agg(
        estudantes=("NU_INSCRICAO", "count"),
        media_geral=("MEDIA_GERAL", "mean"),
        **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
        NOME_ESCOLA=("NOME_ESCOLA", "first"),
        NO_MUNICIPIO_ESC=("NO_MUNICIPIO_ESC", "first"),
        CRE=("CRE", "first"),
    ).reset_index()

    sem_zero = sub[(sub[COLS_NOTAS] > 0).all(axis=1)]
    if not sem_zero.empty:
        esc_sem_zero = sem_zero.groupby("CO_ESCOLA", observed=True).agg(
            estudantes_sem_zero=("NU_INSCRICAO", "count"),
            media_geral_sem_zero=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}_sem_zero": (c, "mean") for c in COLS_NOTAS},
        ).reset_index()
        esc = esc.merge(esc_sem_zero, on="CO_ESCOLA", how="left")
    else:
        esc["estudantes_sem_zero"] = 0
        esc["media_geral_sem_zero"] = pd.NA
        for c in COLS_NOTAS:
            esc[f"media_{c.lower()}_sem_zero"] = pd.NA

    esc["ano"] = ano
    esc["dependencia"] = "Estadual"
    esc["cre_curto"] = esc["CRE"].map(cre_curto)
    ce = conc_esc[conc_esc["NU_ANO"] == ano][["CO_ESCOLA", "Concluintes"]]
    esc = esc.merge(ce, on="CO_ESCOLA", how="left")
    esc["Concluintes"] = esc["Concluintes"].fillna(0).astype(int)
    esc["estudantes_sem_zero"] = esc["estudantes_sem_zero"].fillna(0).astype(int)
    tx_esc = esc["estudantes"] / esc["Concluintes"].replace(0, pd.NA) * 100
    esc["tx_part"] = pd.to_numeric(tx_esc, errors="coerce").round(1)
    tx_esc_sem_zero = esc["estudantes_sem_zero"] / esc["Concluintes"].replace(0, pd.NA) * 100
    esc["tx_part_sem_zero"] = pd.to_numeric(tx_esc_sem_zero, errors="coerce").round(1)
    esc["observacao"] = esc["CO_ESCOLA"].map(observacao_oferta_escola)
    esc["nome_exibicao"] = esc.apply(
        lambda r: nome_exibicao_escola(r["CO_ESCOLA"], r["NOME_ESCOLA"]),
        axis=1,
    )
    return esc


def processar_ano(df_ano: pd.DataFrame, cres, mapa_muni, conc_totais, conc_esc) -> dict:
    ano = int(df_ano["NU_ANO"].iloc[0])
    df = aplicar_flags(df_ano)
    conc_ano = int(conc_totais.loc[conc_totais["NU_ANO"] == ano, "Concluintes"].sum())

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
        "integridade": [],
        "integridade_cre": [],
        "integridade_muni": [],
        "histograma": [],
        "histograma_sem_zero": [],
        "desvio_cv": [],
        "area_detail": [],
        "area_detail_sem_zero": [],
        "quantis_sem_zero": [],
        "quantis_por_area": [],
        "quantis_por_area_sem_zero": [],
        "histograma_por_area": [],
        "histograma_por_area_sem_zero": [],
        "desvio_cv_por_area": [],
        "area_detail_por_area": [],
        "area_detail_por_area_sem_zero": [],
        "referencias_por_area": [],
        "participacao_por_area": [],
        "evolucao_cre_por_area": [],
        "evolucao_muni_por_area": [],
    }

    ms = df[df["SG_UF_ESC"] == "MS"]
    valido = df[df["VALIDO"]]
    ms_valido = ms[ms["VALIDO"]]

    for dep in DEPENDENCIAS:
        base = ms[(ms["DEP_ADM"] == dep) & ms["CONCLUINTE"]]
        val = ms_valido[ms_valido["DEP_ADM"] == dep]
        val_sem_zero = val[(val[COLS_NOTAS] > 0).all(axis=1)] if len(val) else val
        presentes = int(base["PRESENTE_2_DIAS"].sum())
        elim_red = int((base["PRESENTE_2_DIAS"] & base["ELIM_RED"]).sum())
        branco = int((base["PRESENTE_2_DIAS"] & base["RED_BRANCO"]).sum())
        conc = conc_ano if dep == "Estadual" else None

        out["participacao_ano"].append({
            "ano": ano,
            "dependencia": dep,
            "inscritos": len(base),
            "presentes": presentes,
            "eliminados_redacao": elim_red,
            "eliminados_objetiva": int(base["ELIM_OBJ"].sum()),
            "redacao_branco": branco,
            "concluintes": conc,
            "presentes_filt": len(val),
            "presentes_filt_sem_zero": len(val_sem_zero),
        })

        if len(val):
            row = {"ano": ano, "dependencia": dep, "estudantes": len(val)}
            for c in COLS_NOTAS + ["MEDIA_GERAL"]:
                row[f"media_{c.lower()}"] = val[c].mean()
                row[f"media_{c.lower()}_sem_zero"] = val_sem_zero[c].mean() if len(val_sem_zero) else None
            row["estudantes_sem_zero"] = len(val_sem_zero)
            out["desempenho"].append(row)

        out["integridade"].append(_integridade_row(base, val, {"ano": ano, "escopo": dep}))

    br_val = valido[valido["DEP_ADM"] == "Estadual"]
    br_val_sem_zero = br_val[(br_val[COLS_NOTAS] > 0).all(axis=1)] if len(br_val) else br_val
    br_base = df[(df["DEP_ADM"] == "Estadual") & df["CONCLUINTE"]]
    if len(br_base) or len(br_val):
        comp_br = int(br_base["PRESENTE_2_DIAS"].sum())
        elim_br = int((br_base["PRESENTE_2_DIAS"] & br_base["ELIM_RED"]).sum())
        branco_br = int((br_base["PRESENTE_2_DIAS"] & br_base["RED_BRANCO"]).sum())
        out["participacao_ano"].append({
            "ano": ano,
            "dependencia": "Brasil-Estadual",
            "inscritos": len(br_base),
            "presentes": comp_br,
            "eliminados_redacao": elim_br,
            "eliminados_objetiva": int(br_base["ELIM_OBJ"].sum()),
            "redacao_branco": branco_br,
            "concluintes": None,
            "presentes_filt": len(br_val),
            "presentes_filt_sem_zero": len(br_val_sem_zero),
        })
        out["integridade"].append(
            _integridade_row(br_base, br_val, {"ano": ano, "escopo": "Brasil-Estadual"})
        )

    if not br_val.empty:
        uf = br_val.groupby("SG_UF_ESC").agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
        ).reset_index()
        uf_sem_zero = br_val_sem_zero.groupby("SG_UF_ESC").agg(
            estudantes_sem_zero=("NU_INSCRICAO", "count"),
            media_geral_sem_zero=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}_sem_zero": (c, "mean") for c in COLS_NOTAS},
        ).reset_index() if not br_val_sem_zero.empty else pd.DataFrame(columns=["SG_UF_ESC", "estudantes_sem_zero", "media_geral_sem_zero", *[f"media_{c.lower()}_sem_zero" for c in COLS_NOTAS]])
        if not uf_sem_zero.empty:
            uf = uf.merge(uf_sem_zero, on="SG_UF_ESC", how="left")
        else:
            uf["estudantes_sem_zero"] = 0
            uf["media_geral_sem_zero"] = pd.NA
            for c in COLS_NOTAS:
                uf[f"media_{c.lower()}_sem_zero"] = pd.NA
        uf["ano"] = ano
        uf["dependencia"] = "Estadual"
        out["desempenho_uf"].extend(uf.rename(columns={"SG_UF_ESC": "UF"}).to_dict("records"))

    ms_val = enriquecer_ms(ms_valido, cres, mapa_muni)
    ms_val_est = enriquecer_ms(ms_valido[ms_valido["DEP_ADM"] == "Estadual"], cres, mapa_muni)
    if not ms_val.empty and "CRE" in ms_val.columns:
        for dep in DEPENDENCIAS:
            sub = ms_val[ms_val["DEP_ADM"] == dep]
            if sub.empty:
                continue
            cre_g = sub.groupby("CRE", observed=True).agg(
                estudantes=("NU_INSCRICAO", "count"),
                media_geral=("MEDIA_GERAL", "mean"),
                **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
            ).reset_index()
            cre_g["ano"] = ano
            cre_g["dependencia"] = dep
            cre_g["cre_curto"] = cre_g["CRE"].map(cre_curto)
            if dep == "Estadual":
                conc_esc_ano = conc_esc[conc_esc["NU_ANO"] == ano].copy()
                if not conc_esc_ano.empty:
                    if not cres.empty and "CO_ESCOLA" in conc_esc_ano.columns:
                        conc_esc_ano = conc_esc_ano.merge(
                            cres[["CO_ESCOLA", "CRE"]].drop_duplicates(),
                            on="CO_ESCOLA",
                            how="left",
                        )
                    if mapa_muni and "CRE" in conc_esc_ano.columns and COL_MUNICIPIO in conc_esc_ano.columns:
                        m = conc_esc_ano["CRE"].isna()
                        if m.any():
                            conc_esc_ano.loc[m, "CRE"] = conc_esc_ano.loc[m, COL_MUNICIPIO].map(
                                lambda x: mapa_muni.get(normalizar_texto(x), pd.NA)
                            )
                    if "CRE" in conc_esc_ano.columns:
                        cc = conc_esc_ano.groupby("CRE", observed=True)["Concluintes"].sum().reset_index()
                        cre_g = cre_g.merge(cc, on="CRE", how="left")
                        cre_g["Concluintes"] = cre_g["Concluintes"].fillna(0).astype(int)
                        tx = cre_g["estudantes"] / cre_g["Concluintes"].replace(0, pd.NA) * 100
                        cre_g["tx_part_efetiva"] = pd.to_numeric(tx, errors="coerce").round(1)
            out["participacao_cre"].append(cre_g)
            out["evolucao_cre"].append(cre_g)

        if not ms_val_est.empty and "CRE" in ms_val_est.columns:
            muni_g = ms_val_est.groupby("NO_MUNICIPIO_ESC", observed=True).agg(
                estudantes=("NU_INSCRICAO", "count"),
                media_geral=("MEDIA_GERAL", "mean"),
                **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
            ).reset_index()
            muni_g["ano"] = ano
            muni_g["dependencia"] = "Estadual"
            muni_g["CRE"] = ms_val_est.groupby("NO_MUNICIPIO_ESC")["CRE"].agg(
                lambda s: s.mode().iloc[0] if len(s.mode()) else pd.NA
            ).values
            muni_g["cre_curto"] = muni_g["CRE"].map(cre_curto)
            out["participacao_municipios"].append(muni_g)
            out["evolucao_muni"].append(muni_g)

    ms_base_est = ms[(ms["DEP_ADM"] == "Estadual") & ms["CONCLUINTE"]]
    ms_val_est = ms_valido[ms_valido["DEP_ADM"] == "Estadual"]
    if not ms_base_est.empty:
        base_e = enriquecer_ms(ms_base_est, cres, mapa_muni)
        val_e = enriquecer_ms(ms_val_est, cres, mapa_muni)
        if "CRE" in base_e.columns:
            base_e = base_e.copy()
            base_e["cre_curto"] = base_e["CRE"].map(cre_curto)
            val_e = val_e.copy()
            val_e["cre_curto"] = val_e["CRE"].map(cre_curto)
            for cname, grp in base_e.groupby("cre_curto", observed=True):
                val_g = val_e[val_e["cre_curto"] == cname]
                out["integridade_cre"].append(
                    _integridade_row(grp, val_g, {"ano": ano, "cre_curto": str(cname)})
                )
            for mname, grp in base_e.groupby("NO_MUNICIPIO_ESC", observed=True):
                val_g = val_e[val_e["NO_MUNICIPIO_ESC"] == mname]
                cre_nm = cre_curto(grp["CRE"].mode().iloc[0]) if len(grp["CRE"].mode()) else "SED"
                out["integridade_muni"].append(
                    _integridade_row(
                        grp,
                        val_g,
                        {"ano": ano, "NO_MUNICIPIO_ESC": str(mname), "cre_curto": str(cre_nm)},
                    )
                )

    ms_est_val = ms_valido[ms_valido["DEP_ADM"] == "Estadual"]
    ms_est_val_sem_zero = ms_est_val[(ms_est_val[COLS_NOTAS] > 0).all(axis=1)] if len(ms_est_val) else ms_est_val
    ms_est_base = ms[(ms["DEP_ADM"] == "Estadual") & ms["CONCLUINTE"]]
    esc_hist = pd.DataFrame()
    if len(ms_est_val):
        esc_hist = _agregar_escolas_ano(enriquecer_ms(ms_est_val, cres, mapa_muni), conc_esc, ano)
        if not esc_hist.empty:
            out["evolucao_escolas"].append(esc_hist)
    if ano == ANO_FINAL and not esc_hist.empty:
        out["escolas_2024"].append(esc_hist.copy())
    if len(ms_est_val):
        srow = {
            "ano": ano,
            "total_inscritos": len(ms_est_base),
            "total_presentes": int(ms_est_base["PRESENTE_2_DIAS"].sum()),
            "total_eliminados_redacao": int((ms_est_base["PRESENTE_2_DIAS"] & ms_est_base["ELIM_RED"]).sum()),
            "total_redacao_branco": int((ms_est_base["PRESENTE_2_DIAS"] & ms_est_base["RED_BRANCO"]).sum()),
            "total_concluintes_sed": conc_ano,
            "total_validos": len(ms_est_val),
            "total_validos_sem_zero": len(ms_est_val_sem_zero),
        }
        for c in COLS_NOTAS + ["MEDIA_GERAL"]:
            srow[f"media_{c.lower()}"] = ms_est_val[c].mean()
            srow[f"media_br_{c.lower()}"] = br_val[c].mean() if len(br_val) else None
            srow[f"media_{c.lower()}_sem_zero"] = ms_est_val_sem_zero[c].mean() if len(ms_est_val_sem_zero) else None
            srow[f"media_br_{c.lower()}_sem_zero"] = br_val_sem_zero[c].mean() if len(br_val_sem_zero) else None
        out["sumario"].append(srow)

    for c in COLS_NOTAS + ["MEDIA_GERAL"]:
        out["referencias"].append({
            "ano": ano,
            "area": c,
            "media_ms": ms_est_val[c].mean() if len(ms_est_val) else None,
            "media_br": br_val[c].mean() if len(br_val) else None,
            "media_ms_sem_zero": ms_est_val_sem_zero[c].mean() if len(ms_est_val_sem_zero) else None,
            "media_br_sem_zero": br_val_sem_zero[c].mean() if len(br_val_sem_zero) else None,
        })

    for area, col in zip(AREA_KEYS, COLS_NOTAS):
        q = quantis_serie(ms_est_val[col]) if len(ms_est_val) else quantis_serie(pd.Series(dtype=float))
        q.update({"ano": ano, "area": area, "escopo": "MS-Estadual"})
        out.setdefault("quantis", []).append(q)
        q_sem_zero = quantis_serie(ms_est_val_sem_zero[col]) if len(ms_est_val_sem_zero) else quantis_serie(pd.Series(dtype=float))
        q_sem_zero.update({"ano": ano, "area": area, "escopo": "MS-Estadual-sem-zero"})
        out["quantis_sem_zero"].append(q_sem_zero)
        ms_s = ms_est_val[col] if len(ms_est_val) else pd.Series(dtype=float)
        br_s = br_val[col] if len(br_val) else pd.Series(dtype=float)
        ms_s_sem_zero = ms_est_val_sem_zero[col] if len(ms_est_val_sem_zero) else pd.Series(dtype=float)
        br_s_sem_zero = br_val_sem_zero[col] if len(br_val_sem_zero) else pd.Series(dtype=float)
        out["histograma"].append({
            "ano": ano,
            "area": area,
            "ms": _hist_pct(ms_s),
            "br": _hist_pct(br_s),
        })
        out["histograma_sem_zero"].append({
            "ano": ano,
            "area": area,
            "ms": _hist_pct(ms_s_sem_zero),
            "br": _hist_pct(br_s_sem_zero),
        })
        std = ms_s.std()
        mean = ms_s.mean()
        out["desvio_cv"].append({
            "ano": ano,
            "area": area,
            "desvio": round(float(std), 1) if pd.notna(std) else None,
            "cv": round(100 * float(std) / float(mean), 1) if pd.notna(std) and mean else None,
        })
        detail = _area_detail_stats(ms_est_val, area, col)
        detail.update({"ano": ano, "area": area})
        out["area_detail"].append(detail)
        detail_sem_zero = _area_detail_stats(ms_est_val_sem_zero, area, col)
        detail_sem_zero.update({"ano": ano, "area": area})
        out["area_detail_sem_zero"].append(detail_sem_zero)

    for area, col in zip(AREA_KEYS, COLS_NOTAS):
        ms_est_area = filtrar_valido_area(ms[ms["DEP_ADM"] == "Estadual"], area)
        br_area = filtrar_valido_area(df[df["DEP_ADM"] == "Estadual"], area)
        ms_est_area_sem_zero = (
            ms_est_area[ms_est_area[col] > 0] if len(ms_est_area) else ms_est_area
        )
        br_area_sem_zero = (
            br_area[br_area[col] > 0] if len(br_area) else br_area
        )

        out["participacao_por_area"].append({
            "ano": ano,
            "area": area,
            "n_ms": len(ms_est_area),
            "n_br": len(br_area),
            "n_ms_sem_zero": len(ms_est_area_sem_zero),
            "n_br_sem_zero": len(br_area_sem_zero),
        })

        out["referencias_por_area"].append({
            "ano": ano,
            "area": col,
            "media_ms": ms_est_area[col].mean() if len(ms_est_area) else None,
            "media_br": br_area[col].mean() if len(br_area) else None,
            "media_ms_sem_zero": ms_est_area_sem_zero[col].mean() if len(ms_est_area_sem_zero) else None,
            "media_br_sem_zero": br_area_sem_zero[col].mean() if len(br_area_sem_zero) else None,
        })

        q_pa = quantis_serie(ms_est_area[col]) if len(ms_est_area) else quantis_serie(pd.Series(dtype=float))
        q_pa.update({"ano": ano, "area": area, "escopo": "MS-Estadual"})
        out.setdefault("quantis_por_area", []).append(q_pa)

        q_pa_sz = quantis_serie(ms_est_area_sem_zero[col]) if len(ms_est_area_sem_zero) else quantis_serie(pd.Series(dtype=float))
        q_pa_sz.update({"ano": ano, "area": area, "escopo": "MS-Estadual-sem-zero"})
        out["quantis_por_area_sem_zero"].append(q_pa_sz)

        ms_s_pa = ms_est_area[col] if len(ms_est_area) else pd.Series(dtype=float)
        br_s_pa = br_area[col] if len(br_area) else pd.Series(dtype=float)
        ms_s_pa_sz = ms_est_area_sem_zero[col] if len(ms_est_area_sem_zero) else pd.Series(dtype=float)
        br_s_pa_sz = br_area_sem_zero[col] if len(br_area_sem_zero) else pd.Series(dtype=float)

        out["histograma_por_area"].append({
            "ano": ano,
            "area": area,
            "ms": _hist_pct(ms_s_pa),
            "br": _hist_pct(br_s_pa),
        })
        out["histograma_por_area_sem_zero"].append({
            "ano": ano,
            "area": area,
            "ms": _hist_pct(ms_s_pa_sz),
            "br": _hist_pct(br_s_pa_sz),
        })

        std_pa = ms_s_pa.std()
        mean_pa = ms_s_pa.mean()
        out["desvio_cv_por_area"].append({
            "ano": ano,
            "area": area,
            "desvio": round(float(std_pa), 1) if pd.notna(std_pa) else None,
            "cv": round(100 * float(std_pa) / float(mean_pa), 1) if pd.notna(std_pa) and mean_pa else None,
        })

        detail_pa = _area_detail_stats(ms_est_area, area, col)
        detail_pa.update({"ano": ano, "area": area})
        out["area_detail_por_area"].append(detail_pa)

        detail_pa_sz = _area_detail_stats(ms_est_area_sem_zero, area, col)
        detail_pa_sz.update({"ano": ano, "area": area})
        out["area_detail_por_area_sem_zero"].append(detail_pa_sz)

        ms_est_area_enr = enriquecer_ms(ms_est_area, cres, mapa_muni)
        if not ms_est_area_enr.empty and "CRE" in ms_est_area_enr.columns:
            cre_pa = ms_est_area_enr.groupby("CRE", observed=True).agg(
                estudantes=("NU_INSCRICAO", "count"),
                **{f"media_{col.lower()}": (col, "mean")},
            ).reset_index()
            cre_pa["ano"] = ano
            cre_pa["area"] = area
            cre_pa["dependencia"] = "Estadual"
            cre_pa["cre_curto"] = cre_pa["CRE"].map(cre_curto)
            out["evolucao_cre_por_area"].append(cre_pa)

            muni_pa = ms_est_area_enr.groupby("NO_MUNICIPIO_ESC", observed=True).agg(
                estudantes=("NU_INSCRICAO", "count"),
                **{f"media_{col.lower()}": (col, "mean")},
            ).reset_index()
            muni_pa["ano"] = ano
            muni_pa["area"] = area
            muni_pa["dependencia"] = "Estadual"
            muni_pa["CRE"] = ms_est_area_enr.groupby("NO_MUNICIPIO_ESC")["CRE"].agg(
                lambda s: s.mode().iloc[0] if len(s.mode()) else pd.NA
            ).values
            muni_pa["cre_curto"] = muni_pa["CRE"].map(cre_curto)
            out["evolucao_muni_por_area"].append(muni_pa)

    del df, ms, valido, ms_valido
    limpar()
    return out


def main():
    t0 = time.time()
    if not PARQUET.exists():
        raise SystemExit(f"Parquet nao encontrado. Rode: python processar_enem.py\n  {PARQUET}")

    logger.info("%s", "=" * 60)
    logger.info("GERADOR DE AGREGADOS - pipeline_dashboard")
    PASTA_AGREGADOS.mkdir(parents=True, exist_ok=True)

    cres = carregar_cres()
    mapa_muni = carregar_mapa_municipio_cre()
    conc_totais, conc_esc = carregar_concluintes_sed()
    logger.info("Concluintes SED por ano:")
    logger.info("%s", conc_totais.to_string(index=False))
    logger.info("CREs carregados: %s escolas", len(cres))

    acumulado: dict[str, list] = {
        k: [] for k in [
            "participacao_ano", "participacao_cre", "participacao_municipios",
            "desempenho", "desempenho_uf", "escolas_2024", "sumario",
            "referencias", "evolucao_cre", "evolucao_muni", "evolucao_escolas", "integridade",
            "integridade_cre", "integridade_muni", "histograma", "histograma_sem_zero",
            "desvio_cv", "quantis", "quantis_sem_zero", "area_detail", "area_detail_sem_zero",
            "quantis_por_area", "quantis_por_area_sem_zero",
            "histograma_por_area", "histograma_por_area_sem_zero",
            "desvio_cv_por_area", "area_detail_por_area", "area_detail_por_area_sem_zero",
            "referencias_por_area", "participacao_por_area",
            "evolucao_cre_por_area", "evolucao_muni_por_area",
        ]
    }

    cols = _cols_parquet()
    for ano in ANOS:
        logger.info("Processando %s...", ano)
        df_ano = _ler_ano(ano, cols)
        res = processar_ano(df_ano, cres, mapa_muni, conc_totais, conc_esc)
        for k, v in res.items():
            if k in acumulado:
                acumulado[k].extend(v)
        del df_ano
        limpar()

    for nome, rows in acumulado.items():
        if not rows:
            continue
        if isinstance(rows[0], pd.DataFrame):
            df_out = pd.concat(rows, ignore_index=True)
        else:
            df_out = pd.DataFrame(rows)
        path = PASTA_AGREGADOS / f"{nome}.parquet"
        df_out.to_parquet(path, index=False)
        logger.info("%s: %s linhas", path.name, len(df_out))

    pa = pd.read_parquet(PASTA_AGREGADOS / "participacao_ano.parquet")
    ms = pa[(pa["dependencia"] == "Estadual") & (pa["ano"] == ANO_FINAL)].iloc[0]
    logger.info("MS Estadual %s:", ANO_FINAL)
    logger.info("  concluintes SED: %s", int(ms['concluintes']))
    logger.info("  potenciais concluintes (CO_ESCOLA): %s", int(ms['inscritos']))
    logger.info("  validos (filtro): %s", int(ms['presentes_filt']))
    if ms["concluintes"]:
        logger.info("  taxa efetiva: %.1f%%", 100 * ms['presentes_filt'] / ms['concluintes'])

    # Escrever metadados do gerador
    try:
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        dur = time.time() - t0
        meta = {
            "script": "gerar_agregados.py",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "duration_seconds": round(dur, 1),
            "agregados_folder": str(PASTA_AGREGADOS),
        }
        mpath = WEB_DATA / "meta_gerar_agregados.json"
        mpath.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        logger.info("[meta] gravado: %s", mpath)
    except Exception as e:
        logger.warning("[aviso] nao foi possivel gravar meta: %s", e)


if __name__ == "__main__":
    main()
