"""Helpers territoriais (CRE, município, estado) — painel ENEM v15."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cres_loader import nome_cre_curto
from dados_agregados_loader import (
    filtrar_participacao_cre,
    filtrar_participacao_municipio,
    reconstruir_ms_enriquecido,
)

from app.v15.components import titulo_secao
from app.v15.concluintes_data import carregar_concluintes_cre
from app.v15.formatting import fmt_float
from app.v15.ms_enrich import (
    aplicar_cre_por_municipio,
    carregar_cres,
    carregar_mapa_municipio_cre,
    enriquecer_ms,
)
from app.v15.participation import _enriquecer_participacao_taxas
from app.v15.theme import ANOS_DISPONIVEIS


def _df_base_territorial(
    df_ms_enriq: pd.DataFrame,
    df_filt_ms_full: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Série temporal completa (todos os anos) quando carregada; senão recorte lateral."""
    if (
        df_filt_ms_full is not None
        and not df_filt_ms_full.empty
        and "DEP_ADM" in df_filt_ms_full.columns
    ):
        return df_filt_ms_full
    if df_ms_enriq is not None and not df_ms_enriq.empty and "DEP_ADM" in df_ms_enriq.columns:
        return df_ms_enriq
    return pd.DataFrame()


def _linhas_nivel_cre(df: pd.DataFrame) -> pd.DataFrame:
    """Registros agregados por CRE (evolucao_cre) — sem duplicata municipal."""
    if df.empty:
        return df.copy()
    if "NO_MUNICIPIO_ESC" in df.columns:
        return df[df["CRE"].notna() & df["NO_MUNICIPIO_ESC"].isna()].copy()
    return df[df["CRE"].notna()].copy()


def _linhas_nivel_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """Registros agregados por município (evolucao_municipios) com CRE atribuída."""
    if df.empty or "NO_MUNICIPIO_ESC" not in df.columns:
        return pd.DataFrame()
    return df[df["NO_MUNICIPIO_ESC"].notna() & df["CRE"].notna()].copy()


def _presentes_cre_ano(
    tabelas: dict,
    cre: str,
    ano: int,
    dependencia: str,
) -> int:
    """Presentes nos 2 dias na CRE (participacao_cre.parquet)."""
    df = filtrar_participacao_cre(tabelas, anos=[int(ano)], dependencia=dependencia)
    hit = df[df["CRE"] == cre]
    if hit.empty:
        return 0
    return int(pd.to_numeric(hit.iloc[0]["estudantes"], errors="coerce") or 0)


def _inscritos_cre_ano(
    tabelas: dict,
    cre: str,
    ano: int,
    dependencia: str,
) -> int:
    """Inscritos na CRE (participacao_cre.parquet, coluna inscritos)."""
    df = filtrar_participacao_cre(tabelas, anos=[int(ano)], dependencia=dependencia)
    hit = df[df["CRE"] == cre]
    if hit.empty or "inscritos" not in hit.columns:
        return 0
    return int(pd.to_numeric(hit.iloc[0]["inscritos"], errors="coerce") or 0)


def _reconstruir_bases_territoriais(
    tabelas: dict,
    anos_sel: list,
    dep_selecionadas: list,
    df_ms_enriq: pd.DataFrame,
    df_filt_ms_full: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconstrói bases territoriais se o contexto cacheado chegou vazio."""
    df_base = _df_base_territorial(df_ms_enriq, df_filt_ms_full)
    if "DEP_ADM" in df_base.columns and not df_base.empty:
        full = df_filt_ms_full if (
            df_filt_ms_full is not None
            and not df_filt_ms_full.empty
            and "DEP_ADM" in df_filt_ms_full.columns
        ) else df_ms_enriq
        return df_ms_enriq, full

    if not tabelas:
        return df_ms_enriq, df_filt_ms_full or pd.DataFrame()

    deps = list(dep_selecionadas)
    anos_list = [int(a) for a in anos_sel]
    cres = carregar_cres()
    mapa = carregar_mapa_municipio_cre()
    df_todos = aplicar_cre_por_municipio(
        reconstruir_ms_enriquecido(tabelas, ANOS_DISPONIVEIS, deps), mapa,
    )
    df_recorte = reconstruir_ms_enriquecido(tabelas, anos_list, deps)
    return (
        enriquecer_ms(df_recorte, cres, mapa),
        enriquecer_ms(df_todos, cres, mapa),
    )


def _concluintes_cre_por_ano(
    cres: list[str],
    ano_ref: int | str,
) -> pd.DataFrame:
    """Concluintes por CRE a partir da planilha (escola → CRE via cres.xlsx)."""
    df_conc = carregar_concluintes_cre()
    if df_conc.empty or not cres:
        return pd.DataFrame(columns=["CRE", "Concluintes"])
    sub = df_conc[df_conc["CRE"].isin(cres)].copy()
    if ano_ref != "Todos os anos":
        sub = sub[sub["NU_ANO"] == int(ano_ref)]
    else:
        sub = sub.groupby("CRE", observed=True)["Concluintes"].sum().reset_index()
        return sub
    return sub[["CRE", "Concluintes"]].copy()


def _participacao_cre_tabela(
    tabelas: dict,
    cres: list[str],
    ano_ref: int | str,
    dependencia: str,
) -> pd.DataFrame:
    """CRE × presentes (agregados ENEM) + concluintes (planilha escola → CRE)."""
    if not cres:
        return pd.DataFrame()
    if ano_ref == "Todos os anos":
        df = filtrar_participacao_cre(tabelas, dependencia=dependencia)
    else:
        df = filtrar_participacao_cre(tabelas, anos=[int(ano_ref)], dependencia=dependencia)
    if df.empty:
        out = pd.DataFrame({"CRE": cres})
        out["Presentes"] = 0
    else:
        df = df[df["CRE"].isin(cres)].copy()
        if ano_ref == "Todos os anos":
            out = (
                df.groupby("CRE", observed=True)
                .agg(Presentes=("estudantes", "sum"))
                .reset_index()
            )
        else:
            out = df[["CRE", "estudantes"]].rename(columns={"estudantes": "Presentes"})
    out = out[out["CRE"].isin(cres)].copy()
    conc = _concluintes_cre_por_ano(cres, ano_ref)
    if not conc.empty:
        out = out.drop(columns=["Concluintes"], errors="ignore").merge(conc, on="CRE", how="left")
    else:
        out["Concluintes"] = pd.NA
    out["Presentes"] = pd.to_numeric(out["Presentes"], errors="coerce").fillna(0).astype(int)
    out["Concluintes"] = pd.to_numeric(out["Concluintes"], errors="coerce")
    if not df.empty and "inscritos" in df.columns:
        if ano_ref == "Todos os anos":
            insc = (
                df[df["CRE"].isin(cres)]
                .groupby("CRE", observed=True)["inscritos"]
                .sum()
                .reset_index()
            )
        else:
            insc = df[df["CRE"].isin(cres)][["CRE", "inscritos"]].copy()
        out = out.drop(columns=["Inscritos"], errors="ignore").merge(
            insc.rename(columns={"inscritos": "Inscritos"}), on="CRE", how="left",
        )
    else:
        out["Inscritos"] = pd.NA
    out = _enriquecer_participacao_taxas(out)
    return out.sort_values("CRE").reset_index(drop=True)


def _taxa_part_efetiva_ms(
    tabelas: dict,
    ano: int,
    dependencia: str,
) -> float | None:
    """Taxa de participação efetiva do estado (presentes ÷ concluintes).

    Usa participacao_ano.parquet; fallback na soma de participacao_cre.
    Não usa contagem de linhas sintéticas (evita duplicar CRE + município).
    """
    df_ano = tabelas.get("participacao_ano", pd.DataFrame())
    if not df_ano.empty:
        hit = df_ano[(df_ano["ano"] == int(ano)) & (df_ano["dependencia"] == dependencia)]
        if not hit.empty:
            row = hit.iloc[0]
            conc = pd.to_numeric(row.get("concluintes"), errors="coerce")
            part = pd.to_numeric(row.get("presentes_filt", row.get("presentes")), errors="coerce")
            if pd.notna(conc) and float(conc) > 0 and pd.notna(part):
                return round(100 * float(part) / float(conc), 1)
    df_cre = filtrar_participacao_cre(tabelas, anos=[int(ano)], dependencia=dependencia)
    if not df_cre.empty:
        pres = pd.to_numeric(df_cre["estudantes"], errors="coerce").sum()
        conc = pd.to_numeric(df_cre["Concluintes"], errors="coerce").sum()
        if conc > 0:
            return round(100 * pres / conc, 1)
    return None


def _participacao_municipio_tabela(
    tabelas: dict,
    municipios: list[str],
    ano_ref: int | str,
    dependencia: str,
    col_municipio: str = "NO_MUNICIPIO_ESC",
) -> pd.DataFrame:
    """Monta município × presentes/concluintes/taxas a partir de municipios.parquet."""
    if not municipios:
        return pd.DataFrame()
    if ano_ref == "Todos os anos":
        df = filtrar_participacao_municipio(tabelas, dependencia=dependencia)
    else:
        df = filtrar_participacao_municipio(tabelas, anos=[int(ano_ref)], dependencia=dependencia)
    if df.empty or col_municipio not in df.columns:
        return pd.DataFrame()
    df = df[df[col_municipio].isin(municipios)].copy()
    if df.empty:
        return pd.DataFrame()
    agg_cols = {"Presentes": ("estudantes", "sum"), "Concluintes": ("Concluintes", "sum")}
    if "inscritos" in df.columns:
        agg_cols["Inscritos"] = ("inscritos", "sum")
    if ano_ref == "Todos os anos":
        out = (
            df.groupby(col_municipio, observed=True)
            .agg(**agg_cols)
            .reset_index()
            .rename(columns={col_municipio: "Município"})
        )
    else:
        cols = [col_municipio, "estudantes", "Concluintes", "tx_part_efetiva"]
        if "inscritos" in df.columns:
            cols.append("inscritos")
        if "tx_inscricao" in df.columns:
            cols.append("tx_inscricao")
        out = df[cols].rename(
            columns={col_municipio: "Município", "estudantes": "Presentes", "inscritos": "Inscritos"},
        )
    out["Concluintes"] = pd.to_numeric(out["Concluintes"], errors="coerce").fillna(0).astype(int)
    out["Presentes"] = pd.to_numeric(out["Presentes"], errors="coerce").fillna(0).astype(int)
    if "Inscritos" in out.columns:
        out["Inscritos"] = pd.to_numeric(out["Inscritos"], errors="coerce").fillna(0).astype(int)
    out = _enriquecer_participacao_taxas(out.rename(columns={"Taxa_Efetiva": "Tx_Part_Efetiva"}))
    if "Taxa_Efetiva" not in out.columns and "Tx_Part_Efetiva" in out.columns:
        out["Taxa_Efetiva"] = out["Tx_Part_Efetiva"]
    return out


# ============================================================
# ABA 5 - TERRITORIAL (REORDENADA E CORRIGIDA)
# ============================================================
def _vista_territorio_estado(tabelas: dict, anos_sel: list) -> None:
    """Nível Estado: ranking de CREs no ano mais recente do recorte."""
    titulo_secao(
        "Visão estadual — CREs",
        "Ranking das Coordenadorias Regionais de Educação (rede estadual). "
        "Selecione CRE, Município ou Escola no seletor acima para detalhar.",
    )
    df_evol = tabelas.get("evolucao_cre", pd.DataFrame())
    if df_evol.empty or "CRE" not in df_evol.columns:
        st.info(
            "Dados de evolução por CRE indisponíveis. "
            "Regenere agregados com: `python gerar_dados_agregados.py`."
        )
        return
    anos_validos = sorted(int(a) for a in anos_sel if int(a) in df_evol["ano"].unique())
    if not anos_validos:
        st.info("Nenhum ano do recorte possui dados por CRE.")
        return
    ano_ref = anos_validos[-1]
    sub = df_evol[
        (df_evol["ano"] == ano_ref) & (df_evol["dependencia"] == "Estadual")
    ].copy()
    if sub.empty:
        st.info(f"Sem dados de CRE estadual para {ano_ref}.")
        return
    col_media = "media_geral" if "media_geral" in sub.columns else None
    if col_media is None:
        st.info("Coluna de média geral não encontrada em evolucao_cre.")
        return
    sub = sub.dropna(subset=[col_media]).sort_values(col_media, ascending=False)
    exibir = sub[["CRE", col_media, "estudantes"]].copy()
    exibir.columns = ["CRE", "Média geral", "Estudantes"]
    exibir["CRE"] = exibir["CRE"].map(nome_cre_curto)
    exibir["Média geral"] = exibir["Média geral"].round(1)
    st.caption(f"Ano de referência: **{ano_ref}** · Rede estadual · ordenado por média geral.")
    st.dataframe(exibir.reset_index(drop=True), width="stretch", hide_index=True)
    if len(sub) >= 2:
        st.markdown(
            f"<div class='insight'><strong>Extremos:</strong> maior média — "
            f"<b>{nome_cre_curto(sub.iloc[0]['CRE'])}</b> ({fmt_float(sub.iloc[0][col_media])}); "
            f"menor — <b>{nome_cre_curto(sub.iloc[-1]['CRE'])}</b> ({fmt_float(sub.iloc[-1][col_media])}).</div>",
            unsafe_allow_html=True,
        )
