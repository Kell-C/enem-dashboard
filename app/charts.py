"""Gráficos do hub executivo."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dados_agregados_loader import (
    filtrar_distribuicao,
    medias_referencia_por_ano,
    stats_box_quantis,
)

from app.components import nome_cre_curto
from app.theme import (
    AREAS,
    AREAS_COMPLETO,
    AZUL_ESCURO,
    AZUL_PRINCIPAL,
    COLS_NOTAS,
    CORES_AREAS,
    CORES_DEP,
    COR_BRASIL,
    COR_CRITICO,
    COR_POSITIVO,
    COR_TEXTO_BARRA,
    DEP_PADRAO,
    LARANJA_DESTAQUE,
    ORDEM_DEP,
    TEMA,
)
from viz.chart_layout import CHART_H_HUB, margem_hub


def _hub_layout(fig: go.Figure, *, height: int = CHART_H_HUB, rank: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=margem_hub(rank=rank, topo=True),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=TEMA["bg_card"],
        font=dict(size=11, color=TEMA["texto_secundario"]),
        title=dict(text=""),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=TEMA["borda"])
    fig.update_yaxes(showgrid=True, gridcolor=TEMA.get("bg_subtle", "#E8EDF3"), zeroline=False)
    return fig


def fig_combo_media_participacao(diag: dict) -> go.Figure | None:
    serie_ms = diag.get("serie_medias", pd.Series(dtype=float))
    if serie_ms.empty:
        return None
    anos = sorted(int(a) for a in serie_ms.index)
    media_map = {int(k): float(v) for k, v in serie_ms.items() if pd.notna(v)}
    tx_map = {
        int(k): float(v)
        for k, v in diag.get("serie_tx_part_efetiva", pd.Series(dtype=float)).items()
        if pd.notna(v)
    }
    delta_map = {
        int(k): float(v)
        for k, v in diag.get("serie_delta_br", pd.Series(dtype=float)).items()
        if pd.notna(v)
    }

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    y_media = [media_map.get(a, np.nan) for a in anos]
    y_valid = [v for v in y_media if pd.notna(v)]
    y_span = max(max(y_valid) - min(y_valid), 12) if y_valid else 12
    y_min = max(0, min(y_valid) - y_span * 0.45) if y_valid else 0
    y_max = min(1000, max(y_valid) + y_span * 0.85) if y_valid else 1000

    if tx_map:
        fig.add_trace(
            go.Bar(
                x=anos,
                y=[tx_map.get(a, np.nan) for a in anos],
                name="Participação efetiva",
                marker=dict(color="rgba(46, 173, 110, 0.42)", line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5)),
                text=[f"<b>{tx_map.get(a, 0):.0f}%</b>" if pd.notna(tx_map.get(a)) else "" for a in anos],
                textposition="outside",
                textfont=dict(size=10, color=COR_TEXTO_BARRA),
                hovertemplate="<b>%{x}</b><br>Participação: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.add_trace(
        go.Scatter(
            x=anos,
            y=y_media,
            name="Média estadual",
            mode="lines+markers+text",
            text=[f"<b>{v:.0f}</b>" if pd.notna(v) else "" for v in y_media],
            textposition="top center",
            textfont=dict(size=10, color=AZUL_ESCURO),
            line=dict(color=AZUL_PRINCIPAL, width=2.5),
            marker=dict(size=8, color=AZUL_PRINCIPAL, line=dict(width=1.5, color="white")),
            hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
        ),
        secondary_y=False,
    )

    for ano in anos:
        d = delta_map.get(ano, np.nan)
        m = media_map.get(ano, np.nan)
        if pd.notna(d) and pd.notna(m):
            cor = COR_POSITIVO if d >= 0 else COR_CRITICO
            fig.add_annotation(
                x=ano, y=m, text=f"<b>{d:+.0f}</b>", showarrow=False,
                yshift=18, font=dict(size=9, color=cor),
            )

    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, max(max(tx_map.values()) * 1.25, 40) if tx_map else 60], secondary_y=True)
    fig.update_xaxes(tickmode="linear", dtick=1)
    return _hub_layout(fig)


def fig_ranking_uf(diag: dict) -> go.Figure | None:
    part_map = diag.get("rank_part_map", {})
    des_map = diag.get("rank_des_map", {})
    if not part_map and not des_map:
        return None
    anos = sorted(set(part_map) | set(des_map))
    n_total = diag.get("rank_n_total", 27)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    y_des = [float(des_map.get(a, np.nan)) for a in anos]
    y_part = [int(part_map.get(a, 0)) for a in anos]
    y_bar = [float(n_total + 1 - p) for p in y_part]

    fig.add_trace(
        go.Scatter(
            x=anos, y=y_des, name="Posição na média",
            mode="lines+markers+text",
            text=[f"<b>{int(v)}º</b>" if pd.notna(v) else "" for v in y_des],
            textposition="top center",
            textfont=dict(size=10, color=AZUL_ESCURO),
            line=dict(color=AZUL_PRINCIPAL, width=2.5),
            marker=dict(size=8, color=AZUL_PRINCIPAL, line=dict(width=1.5, color="white")),
            hovertemplate="<b>%{x}</b><br>Posição média: %{y:.0f}º<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=anos, y=y_bar, name="Posição participação",
            marker=dict(color="rgba(46, 173, 110, 0.42)", line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5)),
            text=[f"<b>{p}º</b>" for p in y_part],
            textposition="outside",
            textfont=dict(size=10, color=COR_TEXTO_BARRA),
            hovertemplate="<b>%{x}</b><br>Posição participação: %{customdata}º<extra></extra>",
            customdata=y_part,
        ),
        secondary_y=True,
    )
    y_valid = [v for v in y_des if pd.notna(v)]
    if y_valid:
        fig.update_yaxes(range=[max(0.5, min(y_valid) - 2), min(n_total + 0.5, max(y_valid) + 2)], secondary_y=False)
    fig.update_yaxes(range=[0, n_total * 1.25], secondary_y=True)
    fig.update_xaxes(tickmode="linear", dtick=1)
    return _hub_layout(fig, rank=True)


def fig_evolucao_areas(tabelas: dict, anos_sel: list[int]) -> go.Figure | None:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    tem_dados = False
    y_obj, y_red = [], []

    for key in COLS_NOTAS:
        xs, ys = [], []
        for ano in anos_sel:
            ref = medias_referencia_por_ano(tabelas, int(ano))
            val = ref.get(key, {}).get("ms")
            if val is not None and pd.notna(val):
                xs.append(int(ano))
                ys.append(float(val))
        if not xs:
            continue
        tem_dados = True
        sec = key == "NU_NOTA_REDACAO"
        (y_red if sec else y_obj).extend(ys)
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                name=AREAS.get(key, key),
                line=dict(color=CORES_AREAS.get(key, AZUL_PRINCIPAL), width=2),
                marker=dict(size=7, color=CORES_AREAS.get(key, AZUL_PRINCIPAL)),
                hovertemplate=f"<b>{AREAS_COMPLETO.get(key, key)}</b><br>Ano: %{{x}}<br>Média: %{{y:.1f}}<extra></extra>",
            ),
            secondary_y=sec,
        )
    if not tem_dados:
        return None
    if y_obj:
        lo, hi = min(y_obj), max(y_obj)
        pad = max((hi - lo) * 0.15, 8)
        fig.update_yaxes(range=[lo - pad, hi + pad], showticklabels=False, secondary_y=False)
    if y_red:
        lo, hi = min(y_red), max(y_red)
        pad = max((hi - lo) * 0.15, 20)
        fig.update_yaxes(range=[lo - pad, hi + pad], showticklabels=False, secondary_y=True)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.28, x=0, font=dict(size=9)))
    fig.update_xaxes(tickmode="linear", dtick=1)
    return _hub_layout(fig)


def fig_delta_br_areas(tabelas: dict, anos_sel: list[int]) -> go.Figure | None:
    df_ref = tabelas.get("referencias", pd.DataFrame())
    if df_ref.empty:
        return None
    sub = df_ref[df_ref["ano"].isin(anos_sel) & df_ref["area"].isin(COLS_NOTAS)].copy()
    if sub.empty:
        return None
    sub["delta"] = sub["media_ms"] - sub["media_br"]
    sub["abbr"] = sub["area"].map(AREAS)
    sub = sub.sort_values(["ano", "area"])

    xs, ys, cores, custom = [], [], [], []
    area_order = {a: i for i, a in enumerate(COLS_NOTAS)}
    idx = 0
    for ano in sorted(sub["ano"].unique()):
        chunk = sub[sub["ano"] == ano].sort_values("area", key=lambda s: s.map(area_order))
        for _, row in chunk.iterrows():
            xs.append(idx)
            ys.append(float(row["delta"]))
            cores.append(CORES_AREAS.get(row["area"], AZUL_PRINCIPAL))
            custom.append([row["abbr"], int(ano), float(row["media_ms"]), float(row["media_br"])])
            idx += 1

    fig = go.Figure(go.Bar(
        x=xs, y=ys, marker_color=cores,
        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>Δ: %{y:+.1f} pts<br>MS: %{customdata[2]:.1f} · BR: %{customdata[3]:.1f}<extra></extra>",
        customdata=custom,
    ))
    fig.add_hline(y=0, line_color=TEMA["texto_muted"], line_width=1.5)
    max_abs = max(abs(v) for v in ys) if ys else 10
    fig.update_yaxes(range=[-max_abs * 1.2, max_abs * 1.2])
    anos_unicos = sorted(sub["ano"].unique())
    n_por = len(COLS_NOTAS)
    for j, ano in enumerate(anos_unicos):
        fig.add_annotation(
            x=(j * n_por + (n_por - 1) / 2), y=-max_abs * 1.15,
            text=f"<b>{int(ano)}</b>", showarrow=False,
            font=dict(size=9, color=AZUL_ESCURO), xref="x", yref="y",
        )
    fig.update_xaxes(showticklabels=False)
    return _hub_layout(fig)


def fig_cre_combo(tabelas: dict, ano_ref: int) -> go.Figure | None:
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    df_part = tabelas.get("participacao_cre", pd.DataFrame())
    if df_evol.empty:
        return None
    sub = df_evol[(df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == DEP_PADRAO)].copy()
    if sub.empty or "media_geral" not in sub.columns:
        return None
    if not df_part.empty and "tx_part_efetiva" in df_part.columns:
        part = df_part[(df_part["ano"] == ano_ref) & (df_part["dependencia"] == DEP_PADRAO)][["CRE", "tx_part_efetiva"]]
        sub = sub.merge(part, on="CRE", how="left")
    elif "tx_part_efetiva" not in sub.columns:
        return None
    sub = sub.dropna(subset=["media_geral"]).copy()
    sub["_lbl"] = sub["CRE"].map(nome_cre_curto)
    sub = sub.sort_values("media_geral")
    if sub.empty:
        return None

    refs = medias_referencia_por_ano(tabelas, ano_ref)
    mg = refs.get("MEDIA_GERAL", {})
    media_ms, media_br = mg.get("ms"), mg.get("br")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    labels = sub["_lbl"].tolist()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=sub["tx_part_efetiva"].astype(float),
            name="Participação",
            marker=dict(color="rgba(46, 173, 110, 0.42)", line=dict(color="rgba(15, 100, 62, 0.55)", width=0.5)),
            text=[f"<b>{v:.0f}%</b>" for v in sub["tx_part_efetiva"]],
            textposition="outside",
            textfont=dict(size=9, color=COR_TEXTO_BARRA),
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=labels, y=sub["media_geral"].astype(float),
            mode="lines+markers+text", name="Média",
            text=[f"<b>{v:.0f}</b>" for v in sub["media_geral"]],
            textposition="top center",
            textfont=dict(size=9, color=AZUL_ESCURO),
            line=dict(color=AZUL_PRINCIPAL, width=2.5),
            marker=dict(size=7, color=AZUL_PRINCIPAL),
        ),
        secondary_y=False,
    )
    if media_ms is not None:
        fig.add_hline(y=float(media_ms), line_dash="dash", line_color=LARANJA_DESTAQUE, line_width=2)
    if media_br is not None:
        fig.add_hline(y=float(media_br), line_dash="dot", line_color=COR_BRASIL, line_width=2)

    meds = sub["media_geral"].astype(float)
    y_min = max(0, float(meds.min()) - 15)
    y_max = min(1000, float(meds.max()) + 25)
    fig.update_yaxes(range=[y_min, y_max], secondary_y=False)
    fig.update_yaxes(range=[0, max(float(sub["tx_part_efetiva"].max()) * 1.25, 40)], secondary_y=True)
    fig.update_xaxes(tickangle=-40, tickfont=dict(size=8))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.35, x=0, font=dict(size=9)))
    altura = max(CHART_H_HUB, 300 if len(labels) > 8 else CHART_H_HUB)
    return _hub_layout(fig, height=altura)


def fig_medias_dependencia(tabelas: dict, ano_ref: int) -> go.Figure | None:
    df = tabelas.get("desempenho", pd.DataFrame())
    if df.empty:
        return None
    sub = df[df["ano"] == ano_ref]
    registros = []
    for dep in ORDEM_DEP:
        row = sub[sub["dependencia"] == dep]
        if row.empty:
            continue
        col = "media_media_geral" if "media_media_geral" in row.columns else "media_geral"
        registros.append({"Dep": dep, "Média": round(float(row.iloc[0][col]), 1)})
    if not registros:
        return None
    g = pd.DataFrame(registros)
    fig = go.Figure(go.Bar(
        x=g["Dep"], y=g["Média"],
        marker_color=[CORES_DEP.get(d, AZUL_PRINCIPAL) for d in g["Dep"]],
        text=g["Média"].apply(lambda x: f"{x:.0f}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<extra></extra>",
    ))
    fig.update_yaxes(range=[0, min(1000, float(g["Média"].max()) * 1.14)])
    fig.update_xaxes(tickangle=-18)
    return _hub_layout(fig)


def fig_box_media_geral(tabelas: dict, anos_sel: list[int]) -> go.Figure | None:
    df_dist = filtrar_distribuicao(
        tabelas.get("distribuicao_ms", pd.DataFrame()),
        anos=anos_sel,
        dependencia=DEP_PADRAO,
    )
    if df_dist.empty:
        return None
    xs, stats_list = [], []
    for ano in sorted(int(a) for a in df_dist["ano"].unique()):
        row = df_dist[df_dist["ano"] == ano]
        if row.empty:
            continue
        stats = stats_box_quantis(row.iloc[0], "MEDIA_GERAL")
        if stats is None:
            continue
        xs.append(str(ano))
        stats_list.append(stats)
    if not xs:
        return None

    fig = go.Figure()
    for x, st in zip(xs, stats_list):
        fig.add_trace(go.Box(
            q1=[st["q1"]], median=[st["median"]], q3=[st["q3"]],
            lowerfence=[st.get("lower", st["q1"])],
            upperfence=[st.get("upper", st["q3"])],
            mean=[st["mean"]], x=[x], name=x,
            marker_color=AZUL_PRINCIPAL, line=dict(color=AZUL_ESCURO),
            boxmean=False, showlegend=False,
            hovertemplate=f"<b>{x}</b><br>Mediana: {st['median']:.1f}<br>Média: {st['mean']:.1f}<extra></extra>",
        ))
    vals = [s["median"] for s in stats_list]
    pad = max((max(vals) - min(vals)) * 0.2, 20) if vals else 20
    fig.update_yaxes(range=[min(vals) - pad, max(vals) + pad])
    fig.update_xaxes(type="category")
    return _hub_layout(fig)
