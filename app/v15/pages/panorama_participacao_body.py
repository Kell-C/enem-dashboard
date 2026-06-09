"""Corpo das funções de `panorama_participacao` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_panorama_participacao(df_bruta_ms, df_filt_ms, anos_sel,
                              df_bruta_ms_enriq=None, df_filt_ms_enriq=None,
                              df_bruta_nacional=None, df_filt_nacional=None,
                              df_concluintes=None, tabelas=None):
    titulo_secao(
        "Participação em relação aos demais estados",
        "Posição de Mato Grosso do Sul no ranking nacional da taxa de participação "
        "efetiva (presentes nos 2 dias ÷ concluintes do 3º ano, rede estadual). "
        "O funil e as taxas por ano estão no panorama geral acima.",
    )

    posicoes_ms: list[dict] = []
    if df_bruta_nacional is not None and df_filt_nacional is not None:
        col_uf_nac = "SG_UF_ESC" if "SG_UF_ESC" in df_bruta_nacional.columns else "SG_UF_PROVA"
        for ano in sorted(anos_sel):
            df_br_ano = df_bruta_nacional[(df_bruta_nacional["NU_ANO"] == ano) & (
                df_bruta_nacional["DEP_ADM"] == "Estadual")]
            df_fi_ano = df_filt_nacional[(df_filt_nacional["NU_ANO"] == ano) & (
                df_filt_nacional["DEP_ADM"] == "Estadual")]
            taxas_uf = []
            for uf in df_br_ano[col_uf_nac].dropna().unique():
                if len(str(uf)) != 2:
                    continue
                insc = len(df_br_ano[df_br_ano[col_uf_nac] == uf])
                part = len(df_fi_ano[df_fi_ano[col_uf_nac] == uf])
                pct = round(100 * part / insc, 1) if insc else 0.0
                taxas_uf.append(dict(UF=uf, Taxa=pct))
            taxas_uf.sort(key=lambda x: x["Taxa"], reverse=True)
            ranking = [t["UF"] for t in taxas_uf]
            insc_ms = len(df_bruta_ms[(df_bruta_ms["NU_ANO"] == ano) & (
                df_bruta_ms["DEP_ADM"] == "Estadual")])
            part_ms = len(df_filt_ms[(df_filt_ms["NU_ANO"] == ano) & (
                df_filt_ms["DEP_ADM"] == "Estadual")])
            taxa_ms = round(100 * part_ms / insc_ms, 1) if insc_ms else 0.0
            if "MS" in ranking:
                posicoes_ms.append(
                    dict(Ano=ano, Posição=ranking.index("MS") + 1,
                         Total=len(ranking), Taxa=taxa_ms))
    elif tabelas is not None:
        posicoes_ms = _posicoes_ms_participacao_uf(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms)

    if tabelas is not None and not df_bruta_ms.empty and not df_filt_ms.empty:
        fig_pos = _fig_posicao_ms_nacional(
            tabelas, anos_sel, df_bruta_ms, df_filt_ms, altura=400,
        )
        if fig_pos is not None:
            _chart(fig_pos)
            st.caption(
                "Versão ampliada do gráfico da capa. "
                "1º lugar = melhor posição entre as UFs (rede estadual)."
            )
        else:
            st.info("Não foi possível calcular a posição nacional do MS.")
    elif posicoes_ms:
        st.info("Dados de posição disponíveis apenas via agregados participacao_uf.")
    else:
        st.info("Não foi possível calcular a posição nacional do MS.")

