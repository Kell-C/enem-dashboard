"""Corpo das funções de `sumario_executivo` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_sumario_executivo(
    diag: dict,
    anos_sel: list,
    *,
    modo_hub: bool = False,
    tabelas: dict | None = None,
    df_bruta_ms: pd.DataFrame | None = None,
    df_filt_ms: pd.DataFrame | None = None,
):
    periodo = (
        f"{min(anos_sel)}–{max(anos_sel)}"
        if anos_sel and len(anos_sel) >= 2
        else (str(anos_sel[0]) if anos_sel else "—")
    )
    if modo_hub:
        _render_hub_panorama(
            diag, periodo,
            tabelas=tabelas,
            anos_sel=anos_sel,
            df_bruta_ms=df_bruta_ms,
            df_filt_ms=df_filt_ms,
        )
        return

    titulo_secao(
        "Sumário executivo",
        "Leitura rápida dos principais indicadores da rede estadual.",
    )
    _faixa_concluintes_participantes(diag, periodo)

    tx_part_ref = diag.get("tx_part_efetiva") or diag.get("tx_part", 0)
    status_part = classificar_participacao(tx_part_ref)
    status_var = classificar_tendencia(diag.get("variacao_inicio_fim", 0))
    status_pos = classificar_posicao(
        diag.get("pos_ms"), diag.get("total_ufs", 0))

    c1, c2 = st.columns(2)
    kpi_card(c1,
             "Média geral (período)",
             fmt_float(diag["media_estadual_ms"]),
             f"Ponderada · BR: {fmt_float(diag['media_estadual_br'])}")
    kpi_card(c2,
             "Variação no período",
             fmt_delta(diag.get("variacao_inicio_fim", 0)),
             f"{diag.get('ano_inicio', '—')} → {diag.get('ano_fim', '—')}",
             status=status_var)

    titulo_secao("Principais achados",
                 "Destaques das análises de participação, desempenho e posicionamento da rede estadual de MS.")

    medias_areas = diag.get("medias_areas", {})

    # ── Linha 1: Participação · Desempenho Geral · Ranking Nacional ────────
    c1, c2, c3 = st.columns(3)

    with c1:
        _titulos_part = {
            "positivo": "Alta participação",
            "atencao":  "Participação intermediária",
            "critico":  "Baixa participação",
        }
        n_base = diag.get("n_concluintes") or diag.get("n_inscritos")
        label_base = "concluintes" if diag.get("n_concluintes") else "inscritos"
        n_efet = diag.get("n_presentes_filt") or diag.get("n_part")
        tx_txt = fmt_pct(tx_part_ref)
        tx_insc_txt = fmt_pct(diag.get("tx_inscricao")) if diag.get("tx_inscricao") is not None else None
        sufixo_insc = (
            f" Tx inscrição no período: {tx_insc_txt} (inscritos ÷ concluintes)."
            if tx_insc_txt else ""
        )
        _txt_part = {
            "positivo": (
                f"{tx_txt} dos {label_base} são participantes efetivos "
                f"({fmt_int(n_efet)} de {fmt_int(n_base)} — presentes nos 2 dias, sem eliminação)."
                f"{sufixo_insc}"
            ),
            "atencao": (
                f"Taxa de participação efetiva de {tx_txt} "
                f"({fmt_int(n_efet)} de {fmt_int(n_base)} {label_base}) — margem para ampliar cobertura."
                f"{sufixo_insc}"
            ),
            "critico": (
                f"Apenas {tx_txt} dos {label_base} são participantes efetivos "
                f"({fmt_int(n_efet)} de {fmt_int(n_base)}); a maioria não integra a análise de notas."
                f"{sufixo_insc}"
            ),
        }
        achado(status_part, _titulos_part[status_part], _txt_part[status_part])

    with c2:
        diff = diag.get("diff_vs_nacional", float("nan"))
        media_ms_val = diag.get("media_estadual_ms", float("nan"))
        if pd.isna(diff) or pd.isna(media_ms_val):
            achado("neutro", "Desempenho geral",
                   "Dados insuficientes para o período selecionado.")
        else:
            if diff > 2:
                status_desemp, titulo_desemp = "positivo", "Acima da média nacional"
            elif diff >= -2:
                status_desemp, titulo_desemp = "atencao", "Próximo à média nacional"
            else:
                status_desemp, titulo_desemp = "critico", "Abaixo da média nacional"
            achado(
                status_desemp, titulo_desemp,
                f"Média ponderada de MS ({periodo}): {fmt_float(media_ms_val)} pts — "
                f"{fmt_delta(diff)} em relação à rede estadual brasileira no mesmo período.",
            )

    with c3:
        pos_r = diag.get("pos_ms_recente")
        total_r = diag.get("total_ufs_recente", 0)
        ano_r = diag.get("ano_referencia_pos")
        pos_h = diag.get("pos_ms")
        total_h = diag.get("total_ufs", 0)
        if pos_r is not None:
            status_rank = classificar_posicao(pos_r, total_r)
            label_rank = f"Posição nacional · {ano_r}" if ano_r else "Posição nacional"
            achado(
                status_rank, label_rank,
                f"MS ocupa a {pos_r}ª posição entre {total_r} UFs na rede estadual "
                f"(referência: {ano_r}).",
            )
        elif pos_h is not None:
            status_rank = classificar_posicao(pos_h, total_h)
            achado(
                status_rank, "Posição histórica média",
                f"MS ocupa a {pos_h}ª posição entre {total_h} UFs na rede estadual "
                f"(média do período selecionado).",
            )
        else:
            achado("neutro", "Ranking nacional",
                   "Dados de posicionamento não disponíveis para o período selecionado.")

    st.markdown(" ")

    # ── Linha 2: Área Forte · Área Fraca · Tendência do Período ───────────
    d1, d2, d3 = st.columns(3)

    with d1:
        area_forte = diag.get("area_mais_forte")
        if area_forte and area_forte in medias_areas:
            nome_forte = AREAS_COMPLETO.get(area_forte, area_forte)
            val_forte = medias_areas[area_forte]
            achado(
                "positivo", f"Destaque: {nome_forte}",
                f"Melhor desempenho da rede estadual em {nome_forte} "
                f"(média {fmt_float(val_forte)} pts).",
            )
        else:
            achado("neutro", "Área de destaque",
                   "Dados insuficientes para o período selecionado.")

    with d2:
        area_fraca = diag.get("area_mais_fraca")
        if area_fraca and area_fraca in medias_areas:
            nome_fraca = AREAS_COMPLETO.get(area_fraca, area_fraca)
            val_fraca = medias_areas[area_fraca]
            achado(
                "critico", f"Atenção: {nome_fraca}",
                f"Maior desafio em {nome_fraca} (média {fmt_float(val_fraca)} pts) "
                f"— alvo prioritário de intervenção pedagógica.",
            )
        else:
            achado("neutro", "Área de atenção",
                   "Dados insuficientes para o período selecionado.")

    with d3:
        var = diag.get("variacao_inicio_fim", float("nan"))
        if pd.isna(var):
            achado("neutro", "Tendência do período",
                   "Selecione mais de um ano para ver a variação do período.")
        else:
            status_tend = classificar_tendencia(var)
            _titulos_tend = {
                "positivo": "Crescimento no período",
                "atencao":  "Estabilidade no período",
                "critico":  "Queda no período",
                "neutro":   "Tendência do período",
            }
            ano_ini = diag.get("ano_inicio", "—")
            ano_fim_d = diag.get("ano_fim", "—")
            melhor_a = diag.get("melhor_ano", "—")
            val_melhor = diag.get("valor_melhor_ano")
            pior_a = diag.get("pior_ano", "—")
            val_pior = diag.get("valor_pior_ano")
            achado(
                status_tend, _titulos_tend.get(status_tend, "Tendência"),
                f"Variação de {fmt_delta(var)} de {ano_ini} a {ano_fim_d}. "
                f"Melhor resultado em {melhor_a} ({fmt_float(val_melhor)} pts); "
                f"menor em {pior_a} ({fmt_float(val_pior)} pts).",
            )

