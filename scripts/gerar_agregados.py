"""Gera parquets agregados para o painel ENEM MS."""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import ANOS, COLS_NOTAS, DEPENDENCIAS, PARQUET, PASTA_AGREGADOS, PRES_COLS
from enem_helpers import (
    aplicar_flags,
    carregar_concluintes_sed,
    carregar_cres,
    carregar_mapa_municipio_cre,
    cre_curto,
    enriquecer_ms,
    limpar,
    preparar_ano,
    quantis_serie,
)


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
        "integridade": [],
    }

    ms = df[df["SG_UF_ESC"] == "MS"]
    valido = df[df["VALIDO"]]
    ms_valido = ms[ms["VALIDO"]]

    for dep in DEPENDENCIAS:
        base = ms[(ms["DEP_ADM"] == dep) & ms["CONCLUINTE"]]
        val = ms_valido[ms_valido["DEP_ADM"] == dep]
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
        })

        if len(val):
            row = {"ano": ano, "dependencia": dep, "estudantes": len(val)}
            for c in COLS_NOTAS + ["MEDIA_GERAL"]:
                row[f"media_{c.lower()}"] = val[c].mean()
            out["desempenho"].append(row)

        comp = int(base["PRESENTE_2_DIAS"].sum())
        out["integridade"].append({
            "ano": ano,
            "escopo": dep,
            "compareceu_2d": comp,
            "filt": len(val),
            "elim_redacao": elim_red,
            "elim_cn": int((base["TP_PRESENCA_CN"] == 2).sum()),
            "elim_ch": int((base["TP_PRESENCA_CH"] == 2).sum()),
            "elim_lc": int((base["TP_PRESENCA_LC"] == 2).sum()),
            "elim_mt": int((base["TP_PRESENCA_MT"] == 2).sum()),
            "red_branco": branco,
            "tx_elim": round(100 * elim_red / comp, 2) if comp else 0,
            "tx_sem_nota": round(100 * branco / comp, 2) if comp else 0,
        })

    br_val = valido[valido["DEP_ADM"] == "Estadual"]
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
        })
        out["integridade"].append({
            "ano": ano,
            "escopo": "Brasil-Estadual",
            "compareceu_2d": comp_br,
            "filt": len(br_val),
            "elim_redacao": elim_br,
            "elim_cn": int((br_base["TP_PRESENCA_CN"] == 2).sum()),
            "elim_ch": int((br_base["TP_PRESENCA_CH"] == 2).sum()),
            "elim_lc": int((br_base["TP_PRESENCA_LC"] == 2).sum()),
            "elim_mt": int((br_base["TP_PRESENCA_MT"] == 2).sum()),
            "red_branco": branco_br,
            "tx_elim": round(100 * elim_br / comp_br, 2) if comp_br else 0,
            "tx_sem_nota": round(100 * branco_br / comp_br, 2) if comp_br else 0,
        })

    if not br_val.empty:
        uf = br_val.groupby("SG_UF_ESC").agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
        ).reset_index()
        uf["ano"] = ano
        uf["dependencia"] = "Estadual"
        out["desempenho_uf"].extend(uf.rename(columns={"SG_UF_ESC": "UF"}).to_dict("records"))

    ms_val = enriquecer_ms(ms_valido, cres, mapa_muni)
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
            if dep == "Estadual" and ano == 2024 and "CO_ESCOLA" in sub.columns:
                conc_cre = conc_esc[conc_esc["NU_ANO"] == ano].copy()
                if not conc_cre.empty:
                    esc_conc = conc_cre.groupby("CO_ESCOLA")["Concluintes"].sum().reset_index()
                    sub_c = sub.merge(esc_conc, on="CO_ESCOLA", how="left")
                    sub_c["Concluintes"] = sub_c["Concluintes"].fillna(0)
                    cc = sub_c.groupby("CRE", observed=True)["Concluintes"].sum().reset_index()
                    cre_g = cre_g.merge(cc, on="CRE", how="left")
                    cre_g["Concluintes"] = cre_g["Concluintes"].fillna(0).astype(int)
                    tx = cre_g["estudantes"] / cre_g["Concluintes"].replace(0, pd.NA) * 100
                    cre_g["tx_part_efetiva"] = pd.to_numeric(tx, errors="coerce").round(1)
            out["participacao_cre"].append(cre_g)
            out["evolucao_cre"].append(cre_g)

        muni_g = ms_val.groupby("NO_MUNICIPIO_ESC", observed=True).agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
        ).reset_index()
        muni_g["ano"] = ano
        muni_g["dependencia"] = "Estadual"
        muni_g["CRE"] = ms_val.groupby("NO_MUNICIPIO_ESC")["CRE"].agg(
            lambda s: s.mode().iloc[0] if len(s.mode()) else pd.NA
        ).values
        muni_g["cre_curto"] = muni_g["CRE"].map(cre_curto)
        out["participacao_municipios"].append(muni_g)
        out["evolucao_muni"].append(muni_g)

    if ano == 2024:
        sub24 = enriquecer_ms(ms_valido[ms_valido["DEP_ADM"] == "Estadual"], cres, mapa_muni)
        if not sub24.empty and sub24["CO_ESCOLA"].notna().any():
            esc = sub24.groupby("CO_ESCOLA", observed=True).agg(
                estudantes=("NU_INSCRICAO", "count"),
                media_geral=("MEDIA_GERAL", "mean"),
                **{f"media_{c.lower()}": (c, "mean") for c in COLS_NOTAS},
                NOME_ESCOLA=("NOME_ESCOLA", "first"),
                NO_MUNICIPIO_ESC=("NO_MUNICIPIO_ESC", "first"),
                CRE=("CRE", "first"),
            ).reset_index()
            esc["ano"] = 2024
            esc["dependencia"] = "Estadual"
            esc["cre_curto"] = esc["CRE"].map(cre_curto)
            ce = conc_esc[conc_esc["NU_ANO"] == 2024][["CO_ESCOLA", "Concluintes"]]
            esc = esc.merge(ce, on="CO_ESCOLA", how="left")
            esc["Concluintes"] = esc["Concluintes"].fillna(0).astype(int)
            tx_esc = esc["estudantes"] / esc["Concluintes"].replace(0, pd.NA) * 100
            esc["tx_part"] = pd.to_numeric(tx_esc, errors="coerce").round(1)
            out["escolas_2024"].append(esc)

    ms_est_val = ms_valido[ms_valido["DEP_ADM"] == "Estadual"]
    ms_est_base = ms[(ms["DEP_ADM"] == "Estadual") & ms["CONCLUINTE"]]
    if len(ms_est_val):
        srow = {
            "ano": ano,
            "total_inscritos": len(ms_est_base),
            "total_presentes": int(ms_est_base["PRESENTE_2_DIAS"].sum()),
            "total_eliminados_redacao": int((ms_est_base["PRESENTE_2_DIAS"] & ms_est_base["ELIM_RED"]).sum()),
            "total_redacao_branco": int((ms_est_base["PRESENTE_2_DIAS"] & ms_est_base["RED_BRANCO"]).sum()),
            "total_concluintes_sed": conc_ano,
            "total_validos": len(ms_est_val),
        }
        for c in COLS_NOTAS + ["MEDIA_GERAL"]:
            srow[f"media_{c.lower()}"] = ms_est_val[c].mean()
            srow[f"media_br_{c.lower()}"] = br_val[c].mean() if len(br_val) else None
        out["sumario"].append(srow)

    for c in COLS_NOTAS + ["MEDIA_GERAL"]:
        out["referencias"].append({
            "ano": ano,
            "area": c,
            "media_ms": ms_est_val[c].mean() if len(ms_est_val) else None,
            "media_br": br_val[c].mean() if len(br_val) else None,
        })

    for area, col in zip(["CN", "CH", "LC", "MT", "RED"], COLS_NOTAS):
        q = quantis_serie(ms_est_val[col]) if len(ms_est_val) else quantis_serie(pd.Series(dtype=float))
        q.update({"ano": ano, "area": area, "escopo": "MS-Estadual"})
        out.setdefault("quantis", []).append(q)

    del df, ms, valido, ms_valido
    limpar()
    return out


def main():
    if not PARQUET.exists():
        raise SystemExit(f"Parquet nao encontrado. Rode: python processar_enem.py\n  {PARQUET}")

    print("=" * 60)
    print("GERADOR DE AGREGADOS - pipeline_dashboard")
    PASTA_AGREGADOS.mkdir(parents=True, exist_ok=True)

    cres = carregar_cres()
    mapa_muni = carregar_mapa_municipio_cre()
    conc_totais, conc_esc = carregar_concluintes_sed()
    print("Concluintes SED por ano:")
    print(conc_totais.to_string(index=False))
    print(f"CREs carregados: {len(cres)} escolas")

    acumulado: dict[str, list] = {
        k: [] for k in [
            "participacao_ano", "participacao_cre", "participacao_municipios",
            "desempenho", "desempenho_uf", "escolas_2024", "sumario",
            "referencias", "evolucao_cre", "evolucao_muni", "integridade", "quantis",
        ]
    }

    cols = _cols_parquet()
    for ano in ANOS:
        print(f"\nProcessando {ano}...")
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
        print(f"  {path.name}: {len(df_out)} linhas")

    pa = pd.read_parquet(PASTA_AGREGADOS / "participacao_ano.parquet")
    ms = pa[(pa["dependencia"] == "Estadual") & (pa["ano"] == 2024)].iloc[0]
    print("\nMS Estadual 2024:")
    print(f"  concluintes SED: {int(ms['concluintes'])}")
    print(f"  potenciais concluintes (CO_ESCOLA): {int(ms['inscritos'])}")
    print(f"  validos (filtro): {int(ms['presentes_filt'])}")
    if ms["concluintes"]:
        print(f"  taxa efetiva: {100 * ms['presentes_filt'] / ms['concluintes']:.1f}%")


if __name__ == "__main__":
    main()
