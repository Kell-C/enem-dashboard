"""
Exporta data.json e painel_data.js para pipeline_dashboard/web/data/.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import ANOS, AREA_KEYS, NOTA_MAP, PASTA_AGREGADOS, WEB_DATA
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


def _uf_rank_por_ano(des_uf: pd.DataFrame) -> dict:
    out = {}
    for a in ANOS:
        sub = des_uf[(des_uf["ano"] == a) & (des_uf["dependencia"] == "Estadual")].sort_values(
            "media_geral", ascending=False
        )
        out[str(a)] = [[str(row["UF"]), round(float(row["media_geral"]), 0)] for _, row in sub.iterrows()]
    return out


def _rank_ms_por_ano(des_uf: pd.DataFrame) -> list:
    ranks = []
    for a in ANOS:
        sub = des_uf[(des_uf["ano"] == a) & (des_uf["dependencia"] == "Estadual")].copy()
        if sub.empty or "UF" not in sub.columns:
            ranks.append(None)
            continue
        sub = sub.sort_values("media_geral", ascending=False).reset_index(drop=True)
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


def build_painel_data() -> dict:
    part = _ler("participacao_ano")
    des = _ler("desempenho")
    des_uf = _ler("desempenho_uf")
    evol_cre = _ler("evolucao_cre")
    evol_muni = _ler("evolucao_muni")
    esc24 = _ler("escolas_2024")
    refs = _ler("referencias")
    quantis = _ler("quantis")
    integ_df = _ler("integridade")
    _, conc_esc = carregar_concluintes_sed()

    ms_part = part[part["dependencia"] == "Estadual"].sort_values("ano")
    estadual_n = [int(r["presentes_filt"]) for _, r in ms_part.iterrows()]
    estadual_concl = [int(r["concluintes"]) for _, r in ms_part.iterrows()]
    tx_ms = [round(100 * n / c, 1) if c else None for n, c in zip(estadual_n, estadual_concl)]

    med_ms = _serie_refs(refs, "MEDIA_GERAL", "media_ms")
    if not any(v is not None for v in med_ms):
        med_ms = [
            round(float(des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].iloc[0]["media_media_geral"]), 1)
            if not des[(des["ano"] == a) & (des["dependencia"] == "Estadual")].empty
            else None
            for a in ANOS
        ]
    med_br = _serie_refs(refs, "MEDIA_GERAL", "media_br")
    rank_ms = _rank_ms_por_ano(des_uf)
    uf_rank = _uf_rank_por_ano(des_uf)

    funil2024 = {}
    for dep in ["Federal", "Estadual", "Municipal", "Privada"]:
        row = part[(part["ano"] == 2024) & (part["dependencia"] == dep)]
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
                    if a == 2024:
                        for k in AREA_KEYS:
                            col = f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao"
                            if col in row.columns and pd.notna(row.iloc[0][col]):
                                a2024[k] = round(float(row.iloc[0][col]), 1)
            conc24 = conc_esc[
                (conc_esc["NU_ANO"] == 2024)
                & (conc_esc[COL_MUNICIPIO].map(normalizar_texto) == normalizar_texto(mname))
            ]["Concluintes"].sum()
            part24 = int(grp[grp["ano"] == 2024]["estudantes"].sum()) if 2024 in grp["ano"].values else 0
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
    dispersao = []
    if not esc24.empty:
        for mname, grp in esc24.groupby("NO_MUNICIPIO_ESC"):
            rows = []
            for _, r in grp.sort_values("media_geral").iterrows():
                conc = int(r["Concluintes"]) if pd.notna(r.get("Concluintes")) else 0
                part_n = int(r["estudantes"])
                tx = round(100 * part_n / conc, 1) if conc else None
                item = {
                    "nome": str(r.get("NOME_ESCOLA", r["CO_ESCOLA"])),
                    "part": part_n,
                    "concl": conc,
                    "tx": tx,
                    "cn": round(float(r["media_nu_nota_cn"]), 1),
                    "ch": round(float(r["media_nu_nota_ch"]), 1),
                    "lc": round(float(r["media_nu_nota_lc"]), 1),
                    "mt": round(float(r["media_nu_nota_mt"]), 1),
                    "red": round(float(r["media_nu_nota_redacao"]), 1),
                    "geral": round(float(r["media_geral"]), 1),
                }
                rows.append(item)
                dispersao.append({
                    "nome": item["nome"],
                    "mun": str(mname),
                    "cre": cre_curto(r.get("CRE")),
                    "nota": item["geral"],
                    "n": part_n,
                    "tx": tx,
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
            "em": [0] * len(ANOS),
            "zm": [0] * len(ANOS),
            "sm": [0] * len(ANOS),
            "sn": [0] * len(ANOS),
        }

    boxplot = {k: _histograma_bins(quantis, k) for k in AREA_KEYS}
    esc_rank = {k: [] for k in AREA_KEYS}
    if not esc24.empty:
        col_map = {
            "CN": "media_nu_nota_cn", "CH": "media_nu_nota_ch", "LC": "media_nu_nota_lc",
            "MT": "media_nu_nota_mt", "RED": "media_nu_nota_redacao",
        }
        for k, col in col_map.items():
            tmp = esc24[["NOME_ESCOLA", col]].dropna().sort_values(col, ascending=False)
            for _, r in tmp.head(10).iterrows():
                esc_rank[k].append({"nome": str(r["NOME_ESCOLA"]), "nota": round(float(r[col]), 1)})
            for _, r in tmp.tail(10).sort_values(col).iterrows():
                esc_rank[k].append({"nome": str(r["NOME_ESCOLA"]), "nota": round(float(r[col]), 1)})

    ms_area_2024 = {}
    d24 = des[(des["ano"] == 2024) & (des["dependencia"] == "Estadual")]
    if not d24.empty:
        for k in AREA_KEYS:
            col = f"media_nu_nota_{k.lower()}" if k != "RED" else "media_nu_nota_redacao"
            if col in d24.columns:
                ms_area_2024[k] = round(float(d24.iloc[0][col]), 1)

    index_areas = {k: _serie_refs(refs, REF_AREAS[k], "media_ms") for k in AREA_KEYS}
    ms_area_series = {
        k: {"ms": _serie_refs(refs, REF_AREAS[k], "media_ms"), "br": _serie_refs(refs, REF_AREAS[k], "media_br")}
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
            "concluintes_2019_2023": "TP_ST_CONCLUSAO = 2",
            "concluintes_2024": "CO_ESCOLA preenchido (RESULTADOS; pode incluir EJA/outras modalidades)",
            "presentes": "TP_PRESENCA = 1 em CN, CH, LC, MT",
            "eliminados": "TP_PRESENCA = 2 ou TP_STATUS_REDACAO = 2",
            "redacao_branco": "incluidos (TP_STATUS_REDACAO = 4)",
            "concluintes_denominador": "Concluintes 3o ano EM regular (SED)",
            "aviso_2024": "Sem merge PARTICIPANTES+RESULTADOS; taxa vs SED nao homogenea com 2019-2023",
        },
        "gerado_em": pd.Timestamp.now().isoformat(),
        "pipeline": "pipeline_dashboard",
    }

    return {
        "meta": meta,
        "anos": ANOS,
        "medMs": med_ms,
        "medBr": med_br,
        "txMs": tx_ms,
        "rankMs": rank_ms,
        "ufRankByYear": uf_rank,
        "msArea2024": ms_area_2024,
        "msGeral2024": med_ms[-1] if med_ms else None,
        "indexAreas": index_areas,
        "cre": cre,
        "creMuns": {k: v["cre"] for k, v in mun.items()},
        "mun": mun,
        "esc": esc,
        "msArea": ms_area_series,
        "redes": redes,
        "funil2024": funil2024,
        "estadualN": estadual_n,
        "estadualConcl": estadual_concl,
        "integ": integ,
        "escRank": esc_rank,
        "boxplot": boxplot,
        "histograma": boxplot.copy(),
        "dispersao": dispersao,
        "desvio_padrao": {k: {} for k in AREA_KEYS},
        "cv": {k: {} for k in AREA_KEYS},
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

    print(f"Gerado: {json_path} ({json_path.stat().st_size // 1024} KB)")
    print(f"Gerado: {js_path}")
    f24 = painel["funil2024"]["Estadual"]
    print(
        f"MS 2024: {f24['presfilt']} validos / {f24['concluintes']} concluintes SED "
        f"= {100 * f24['presfilt'] / f24['concluintes']:.1f}%"
    )


if __name__ == "__main__":
    main()
