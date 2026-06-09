"""Diagnóstico executivo a partir dos agregados."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dados_agregados_loader import (
    medias_referencia_por_ano,
    participacao_ms_por_ano,
    tabela_ranking_uf,
)

from app.theme import DEP_PADRAO


def _anos_validos(tabelas: dict) -> list[int]:
    df = tabelas.get("sumario_executivo", pd.DataFrame())
    if df.empty or "ano" not in df.columns:
        df = tabelas.get("desempenho", pd.DataFrame())
    if df.empty:
        return list(range(2019, 2025))
    return sorted(int(a) for a in df["ano"].dropna().unique())


def posicoes_ms_por_ano(
    tabelas: dict,
    anos_sel: list[int],
) -> tuple[dict[int, int], dict[int, int], int]:
    part_map: dict[int, int] = {}
    des_map: dict[int, int] = {}
    n_total = 27
    for ano in anos_sel:
        rank = tabela_ranking_uf(tabelas, int(ano), DEP_PADRAO)
        if rank.empty:
            continue
        rank_d = rank.sort_values("MEDIA_GERAL", ascending=False).reset_index(drop=True)
        n_total = max(n_total, len(rank_d))
        ms_idx = rank_d.index[rank_d["UF"] == "MS"]
        if len(ms_idx):
            des_map[int(ano)] = int(ms_idx[0]) + 1
        if "Tx_Participação" in rank.columns:
            rank_p = (
                rank.dropna(subset=["Tx_Participação"])
                .sort_values("Tx_Participação", ascending=False)
                .reset_index(drop=True)
            )
            ms_p = rank_p.index[rank_p["UF"] == "MS"]
            if len(ms_p):
                part_map[int(ano)] = int(ms_p[0]) + 1
    return part_map, des_map, n_total


def build_diag(tabelas: dict, anos_sel: list[int] | None = None) -> dict:
    anos_sel = sorted(int(a) for a in (anos_sel or _anos_validos(tabelas)))
    df_des = tabelas.get("desempenho", pd.DataFrame())
    df_part = tabelas.get("participacao_ano", pd.DataFrame())

    sub_des = df_des[
        (df_des["dependencia"] == DEP_PADRAO) & (df_des["ano"].isin(anos_sel))
    ].sort_values("ano")

    serie_ms = (
        sub_des.set_index("ano")["media_media_geral"]
        if not sub_des.empty and "media_media_geral" in sub_des.columns
        else pd.Series(dtype=float)
    )

    w = sub_des["estudantes"].astype(float) if not sub_des.empty else pd.Series(dtype=float)
    media_ms = (
        float(np.average(sub_des["media_media_geral"], weights=w))
        if not sub_des.empty and w.sum() > 0
        else np.nan
    )

    br_num, br_den = 0.0, 0.0
    for _, row in sub_des.iterrows():
        ano = int(row["ano"])
        ref = medias_referencia_por_ano(tabelas, ano)
        br = ref.get("MEDIA_GERAL", {}).get("br")
        est = float(row["estudantes"])
        if br is not None and pd.notna(br) and est > 0:
            br_num += float(br) * est
            br_den += est
    media_br = br_num / br_den if br_den > 0 else np.nan

    sub_part = df_part[
        (df_part["dependencia"] == DEP_PADRAO) & (df_part["ano"].isin(anos_sel))
    ]
    n_conc = (
        int(sub_part["concluintes"].fillna(0).sum())
        if not sub_part.empty and "concluintes" in sub_part.columns
        else None
    )
    n_insc = (
        int(sub_part["inscritos"].fillna(0).sum())
        if not sub_part.empty and "inscritos" in sub_part.columns
        else None
    )
    n_pres = (
        int(sub_part["presentes_filt"].fillna(0).sum())
        if not sub_part.empty and "presentes_filt" in sub_part.columns
        else None
    )
    tx_efet = round(100 * n_pres / n_conc, 1) if n_conc and n_pres else None
    tx_insc = round(100 * n_insc / n_conc, 1) if n_conc and n_insc else None

    part_serie = participacao_ms_por_ano(tabelas, anos_sel, DEP_PADRAO)
    serie_tx = (
        part_serie.set_index(part_serie["ano"].astype(int))["Tx_Part_Efetiva"]
        if not part_serie.empty
        else pd.Series(dtype=float)
    )

    delta_map: dict[int, float] = {}
    for ano in anos_sel:
        ref = medias_referencia_por_ano(tabelas, int(ano))
        ms_row = sub_des[sub_des["ano"] == ano]
        if ms_row.empty:
            continue
        ms_v = float(ms_row.iloc[0]["media_media_geral"])
        br_v = ref.get("MEDIA_GERAL", {}).get("br")
        if br_v is not None and pd.notna(br_v):
            delta_map[int(ano)] = ms_v - float(br_v)
    serie_delta = pd.Series(delta_map).sort_index()

    ano_ref = anos_sel[-1] if anos_sel else 2024
    rank = tabela_ranking_uf(tabelas, ano_ref, DEP_PADRAO)
    pos_ms_recente = None
    total_ufs_recente = None
    if not rank.empty and "MEDIA_GERAL" in rank.columns:
        rank_d = rank.sort_values("MEDIA_GERAL", ascending=False).reset_index(drop=True)
        total_ufs_recente = len(rank_d)
        ms_rows = rank_d[rank_d["UF"] == "MS"]
        if not ms_rows.empty:
            pos_ms_recente = int(ms_rows.index[0]) + 1

    part_map, des_map, n_total = posicoes_ms_por_ano(tabelas, anos_sel)

    return {
        "anos_sel": anos_sel,
        "media_estadual_ms": media_ms,
        "media_estadual_br": media_br,
        "diff_vs_nacional": (
            media_ms - media_br
            if pd.notna(media_ms) and pd.notna(media_br)
            else np.nan
        ),
        "serie_medias": serie_ms,
        "serie_tx_part_efetiva": serie_tx,
        "serie_delta_br": serie_delta,
        "n_concluintes": n_conc,
        "n_inscritos": n_insc,
        "n_presentes_filt": n_pres,
        "n_part": n_pres,
        "tx_part_efetiva": tx_efet,
        "tx_inscricao": tx_insc,
        "variacao_inicio_fim": (
            float(serie_ms.iloc[-1] - serie_ms.iloc[0])
            if len(serie_ms) >= 2
            else np.nan
        ),
        "ano_inicio": int(serie_ms.index[0]) if len(serie_ms) >= 1 else None,
        "ano_fim": int(serie_ms.index[-1]) if len(serie_ms) >= 1 else None,
        "pos_ms_recente": pos_ms_recente,
        "pos_ms": pos_ms_recente,
        "total_ufs_recente": total_ufs_recente,
        "total_ufs": total_ufs_recente or n_total,
        "ano_referencia_pos": ano_ref,
        "rank_part_map": part_map,
        "rank_des_map": des_map,
        "rank_n_total": n_total,
    }
