"""
gerar_dados_agregados.py

Script para gerar dados agregados/resumidos para todas as abas do dashboard ENEM.
Elimina a necessidade de manter 26M de registros brutos na memória.

PADRÃO: Estudantes de escolas ESTADUAIS, CONCLUINTES do Ensino Médio
        (cursando o 3o ano e concluindo no ano da edicao -- TP_ST_CONCLUSAO == 2,
        NAO inclui egressos), presentes nos 2 dias de prova, não eliminados.
        EXCECAO 2024: o INEP nao divulga TP_ST_CONCLUSAO por escola (fica nulo nos
        resultados). Em vez disso, o INEP vincula cada participante a sua escola
        cruzando o CPF com a matricula no Censo Escolar 2024, filtrando as etapas de
        PROVAVEIS CONCLUINTES do EM (3o ano / series finais: 27,28,29,37,38,71,32,33,34).
        Logo, ter escola identificada em 2024 (CO_ESCOLA preenchido) JA EQUIVALE a ser
        provavel concluinte. Como todos os agregados (UF/nacional/rede/territorio)
        agrupam por dependencia/escola, a populacao de referencia de 2024 -- inclusive
        nas comparacoes entre MS, demais UFs e Brasil -- ja fica restrita aos provaveis
        concluintes presentes nos 2 dias e nao eliminados.

Uso:
    python gerar_dados_agregados.py

Saída: arquivos parquet em C:\\enem_analise\\dados_processados\\agregados\\
"""

import os
import gc
import pandas as pd
import numpy as np

# ============================================================
# CONFIGURAÇÃO
# ============================================================
ARQUIVO_ENTRADA = r"C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet"
PASTA_SAIDA = r"C:\enem_analise\dados_processados\agregados"
ARQUIVO_CRES = r"C:\enem_analise\scripts\V14\cres.xlsx"
ARQUIVO_CONCLUINTES = r"C:\enem_analise\dados_processados\concluintes_3ano_ms_2019_2024.csv"
ARQUIVO_CONCLUINTES_MUNICIPIO = r"C:\enem_analise\dados_processados\concluintes_por_municipio_ano.csv"

# Criar pasta de saída
os.makedirs(PASTA_SAIDA, exist_ok=True)

# Constantes do dashboard
COLS_NOTAS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
DEPENDENCIAS = ["Federal", "Estadual", "Municipal", "Privada"]

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    for a, b in [("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U"),
                 ("Â","A"),("Ê","E"),("Î","I"),("Ô","O"),("Û","U"),
                 ("Ã","A"),("Õ","O"),("Ç","C"),("À","A")]:
        texto = texto.replace(a, b)
    return texto


def _construir_mapa_cre_completo():
    return {
        "CRE 01": "CRE 01 - CAMPO GRANDE", "CRE 02": "CRE 02 - CAMPO GRANDE",
        "CRE 03": "CRE 03 - CAMPO GRANDE", "CRE 04": "CRE 04 - CAMPO GRANDE",
        "CRE 05": "CRE 05 - DOURADOS", "CRE 06": "CRE 06 - CORUMBÁ",
        "CRE 07": "CRE 07 - TRÊS LAGOAS", "CRE 08": "CRE 08 - PONTA PORÃ",
        "CRE 09": "CRE 09 - AQUIDAUANA", "CRE 10": "CRE 10 - PARANAÍBA",
        "CRE 11": "CRE 11 - NAVIRAÍ", "CRE 12": "CRE 12 - NOVA ANDRADINA",
        "CRE 13": "CRE 13 - CHAPADÃO DO SUL", "CRE 14": "CRE 14 - MARACAJU",
        "CRE 15": "CRE 15 - RIO BRILHANTE", "CRE 16": "CRE 16 - CAARAPÓ",
        "CRE 17": "CRE 17 - JARDIM", "CRE 18": "CRE 18 - BONITO",
        "CRE 19": "CRE 19 - MIRANDA", "CRE 20": "CRE 20 - COSTA RICA",
        "CRE 21": "CRE 21 - SÃO GABRIEL DO OESTE", "CRE 22": "CRE 22 - BATAGUASSU",
        "CRE 23": "CRE 23 - APOSTOLO", "CRE 24": "CRE 24 - ANASTÁCIO",
        "CRE 25": "CRE 25 - BELA VISTA", "CRE 26": "CRE 26 - COXIM",
        "CRE 27": "CRE 27 - PEDRO GOMES", "CRE 28": "CRE 28 - SONORA",
    }


def carregar_cres():
    if not os.path.exists(ARQUIVO_CRES):
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])
    try:
        cres = pd.read_excel(ARQUIVO_CRES, sheet_name="Cód.INEP-CREs")
    except ValueError:
        cres = pd.read_excel(ARQUIVO_CRES, sheet_name=0)

    col_cod = None
    for possivel in ["CÓD INEP", "COD INEP", "CÓD.INEP", "COD.INEP"]:
        if possivel in cres.columns:
            col_cod = possivel
            break

    if col_cod is None:
        return pd.DataFrame(columns=["CO_ESCOLA", "CRE", "MUNICIPIO_CRES", "NOME_ESCOLA"])

    col_esc = "UNIDADE ESCOLAR " if "UNIDADE ESCOLAR " in cres.columns else "UNIDADE ESCOLAR"
    col_mun = "MUNICÍPIO" if "MUNICÍPIO" in cres.columns else "MUNICIPIO"

    cres[col_cod] = pd.to_numeric(cres[col_cod], errors="coerce").astype("Int64")
    cres = cres[[col_cod, "CRE", col_mun, col_esc]].dropna(subset=[col_cod])
    cres = cres.drop_duplicates(subset=[col_cod])

    mapa_cre_completo = _construir_mapa_cre_completo()
    cres["CRE"] = cres["CRE"].map(mapa_cre_completo).fillna(cres["CRE"])

    cres = cres.rename(columns={
        col_cod: "CO_ESCOLA", col_mun: "MUNICIPIO_CRES", col_esc: "NOME_ESCOLA",
    })
    return cres


def carregar_mapa_municipio_cre():
    if not os.path.exists(ARQUIVO_CRES):
        return {}
    try:
        df_cres = pd.read_excel(ARQUIVO_CRES, sheet_name="CREs")
    except ValueError:
        return {}

    mapa_cre_completo = _construir_mapa_cre_completo()
    mapa = {}
    for _, row in df_cres.iterrows():
        municipio = str(row.get("MUNICÍPIO", "")).strip().upper()
        cre = str(row.get("CRE", "")).strip()
        if municipio and cre:
            municipio_norm = normalizar_texto(municipio)
            cre_normalizado = mapa_cre_completo.get(cre, cre)
            mapa[municipio_norm] = cre_normalizado
    return mapa


def enriquecer_ms(df_ms, cres, mapa_muni_cre=None):
    df = df_ms
    if "NOME_ESCOLA" not in df.columns:
        df["NOME_ESCOLA"] = pd.NA
    if "MUNICIPIO_CRES" not in df.columns:
        df["MUNICIPIO_CRES"] = df.get("NO_MUNICIPIO_ESC", pd.NA)
    if "CRE" not in df.columns:
        df["CRE"] = pd.NA

    if cres is not None and not cres.empty and "CO_ESCOLA" in df.columns:
        mask_com_escola = df["CO_ESCOLA"].notna()
        if mask_com_escola.any():
            df_com_escola = df[mask_com_escola].merge(
                cres, on="CO_ESCOLA", how="left", validate="m:1", suffixes=("_old", ""),
            )
            for col in ["NOME_ESCOLA", "MUNICIPIO_CRES", "CRE"]:
                if col not in df_com_escola.columns:
                    df_com_escola[col] = pd.NA
            df.loc[mask_com_escola, "NOME_ESCOLA"] = df_com_escola["NOME_ESCOLA"].values
            df.loc[mask_com_escola, "MUNICIPIO_CRES"] = df_com_escola["MUNICIPIO_CRES"].values
            df.loc[mask_com_escola, "CRE"] = df_com_escola["CRE"].values
            del df_com_escola

    if mapa_muni_cre and df["CRE"].isna().any():
        mask_sem_cre = df["CRE"].isna()
        col_mun = "MUNICIPIO_CRES" if df["MUNICIPIO_CRES"].notna().any() else "NO_MUNICIPIO_ESC"
        if col_mun in df.columns:
            municipios_normalizados = df.loc[mask_sem_cre, col_mun].apply(normalizar_texto)
            df.loc[mask_sem_cre, "CRE"] = municipios_normalizados.map(mapa_muni_cre)

    mapa_cre_completo = _construir_mapa_cre_completo()
    cre_col = df["CRE"].astype(str).map(mapa_cre_completo).fillna(df["CRE"])
    df["CRE"] = cre_col

    return df


def carregar_concluintes():
    if not os.path.exists(ARQUIVO_CONCLUINTES):
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "Concluintes"])
    try:
        df = pd.read_csv(ARQUIVO_CONCLUINTES)
        df["NU_ANO"] = pd.to_numeric(df["NU_ANO"], errors="coerce").astype("int16")
        df["Concluintes"] = pd.to_numeric(df["Concluintes"], errors="coerce").fillna(0).astype(int)
        return df.dropna(subset=["CO_ESCOLA", "NU_ANO"]).drop_duplicates(subset=["CO_ESCOLA", "NU_ANO"])
    except Exception:
        return pd.DataFrame(columns=["CO_ESCOLA", "NU_ANO", "Concluintes"])


def carregar_concluintes_municipio():
    if not os.path.exists(ARQUIVO_CONCLUINTES_MUNICIPIO):
        return pd.DataFrame(columns=["MUNICIPIO", "NU_ANO", "Concluintes", "N_ESCOLAS"])
    try:
        df = pd.read_csv(ARQUIVO_CONCLUINTES_MUNICIPIO)
        df["NU_ANO"] = pd.to_numeric(df["NU_ANO"], errors="coerce").astype("int16")
        df["Concluintes"] = pd.to_numeric(df["Concluintes"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame(columns=["MUNICIPIO", "NU_ANO", "Concluintes", "N_ESCOLAS"])


def carregar_concluintes_cre():
    if not os.path.exists(ARQUIVO_CONCLUINTES):
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])
    try:
        df = pd.read_csv(ARQUIVO_CONCLUINTES)
        df["NU_ANO"] = pd.to_numeric(df["NU_ANO"], errors="coerce").astype("int16")
        df["Concluintes"] = pd.to_numeric(df["Concluintes"], errors="coerce").fillna(0).astype(int)

        if os.path.exists(ARQUIVO_CRES):
            cres = pd.read_excel(ARQUIVO_CRES, sheet_name="CREs")
            cres["MUN_NORM"] = cres["MUNICÍPIO"].apply(normalizar_texto)
            df["MUN_NORM"] = df["MUNICIPIO"].apply(normalizar_texto)
            df = df.merge(cres[["MUN_NORM", "CRE"]], on="MUN_NORM", how="left")
        else:
            df["CRE"] = pd.NA

        agg = df.groupby(["CRE", "NU_ANO"], observed=True)["Concluintes"].sum().reset_index()
        return agg.dropna(subset=["CRE", "NU_ANO"])
    except Exception:
        return pd.DataFrame(columns=["CRE", "NU_ANO", "Concluintes"])


# ============================================================
# FUNÇÕES DE AGREGAÇÃO POR ANO (para economizar memória)
# ============================================================
def processar_ano(df_ano, cres, mapa_muni_cre, df_concluintes, df_concluintes_cre, df_concluintes_muni):
    """Processa um ano específico e retorna todos os agregados."""
    ano = df_ano["NU_ANO"].iloc[0]

    # Criar colunas auxiliares
    dep_map = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
    df_ano["DEP_ADM"] = df_ano["TP_DEPENDENCIA_ADM_ESC"].map(dep_map)
    df_ano["PRESENTE_2_DIAS"] = (
        (df_ano["TP_PRESENCA_CN"] == 1) &
        (df_ano["TP_PRESENCA_CH"] == 1) &
        (df_ano["TP_PRESENCA_LC"] == 1) &
        (df_ano["TP_PRESENCA_MT"] == 1)
    )
    df_ano["ELIMINADO"] = df_ano["TP_STATUS_REDACAO"] == 4
    # CONCLUINTE estrito = cursando o 3o ano e concluira o EM no ano da edicao.
    # 2019-2023: autodeclaracao do participante (TP_ST_CONCLUSAO == 2), NAO inclui
    #            egressos (codigo 1 = "ja conclui o EM").
    # 2024: o INEP nao divulga TP_ST_CONCLUSAO por escola (fica nulo). Mas a escola so
    #       foi atribuida a quem o INEP cruzou no Censo Escolar (CPF x matricula) nas
    #       etapas de provaveis concluintes do EM. Logo, escola identificada
    #       (CO_ESCOLA preenchido) EQUIVALE a provavel concluinte. Isso garante que as
    #       comparacoes por rede entre MS, demais UFs e Brasil usem so a populacao de
    #       referencia tambem em 2024.
    if ano == 2024:
        df_ano["CONCLUINTE"] = df_ano["CO_ESCOLA"].notna()
    else:
        df_ano["CONCLUINTE"] = (df_ano["TP_ST_CONCLUSAO"] == 2)

    # Calcular média geral
    if "MEDIA_GERAL" not in df_ano.columns:
        df_ano["MEDIA_GERAL"] = df_ano[COLS_NOTAS].mean(axis=1)

    # Enriquecer com CRE
    df_ano = enriquecer_ms(df_ano, cres, mapa_muni_cre)

    # Separar brutos e filtrados
    mask_filt = df_ano["PRESENTE_2_DIAS"] & ~df_ano["ELIMINADO"]
    df_bruta_ano = df_ano
    df_filt_ano = df_ano[mask_filt]

    resultados = {
        "sumario": [],
        "participacao_ano": [],
        "participacao_cre": [],
        "desempenho": [],
        "escolas_2024": [],
        "territorial": [],
        "municipios": [],
        "panorama": [],
        "referencias": [],
        "evolucao_cre": [],
        "evolucao_muni": [],
    }

    # --- Sumário Executivo ---
    ms_bruta = df_bruta_ano[(df_bruta_ano["SG_UF_ESC"] == "MS") & (df_bruta_ano["DEP_ADM"] == "Estadual") & df_bruta_ano["CONCLUINTE"]]
    ms_filt = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == "Estadual") & df_filt_ano["CONCLUINTE"]]
    br_filt = df_filt_ano[(df_filt_ano["DEP_ADM"] == "Estadual") & df_filt_ano["CONCLUINTE"]]

    medias_ms = {f"media_{k.lower()}": ms_filt[k].mean() for k in COLS_NOTAS + ["MEDIA_GERAL"]}
    medias_br = {f"media_br_{k.lower()}": br_filt[k].mean() for k in COLS_NOTAS + ["MEDIA_GERAL"]}

    resultados["sumario"].append({
        "ano": ano,
        "total_inscritos": len(ms_bruta),
        "total_presentes": ms_bruta["PRESENTE_2_DIAS"].sum(),
        "total_eliminados": ms_bruta["ELIMINADO"].sum(),
        "total_concluintes": ms_bruta["CONCLUINTE"].sum(),
        **medias_ms, **medias_br,
    })

    # --- Participação por ano ---
    for dep in DEPENDENCIAS:
        ms_bruta_dep = df_bruta_ano[(df_bruta_ano["SG_UF_ESC"] == "MS") & (df_bruta_ano["DEP_ADM"] == dep) & df_bruta_ano["CONCLUINTE"]]
        ms_filt_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]

        resultados["participacao_ano"].append({
            "ano": ano, "dependencia": dep,
            "inscritos": len(ms_bruta_dep),
            "presentes": ms_bruta_dep["PRESENTE_2_DIAS"].sum(),
            "eliminados": ms_bruta_dep["ELIMINADO"].sum(),
            "concluintes": ms_bruta_dep["CONCLUINTE"].sum(),
            "presentes_filt": len(ms_filt_dep),
        })

    # --- Participação por CRE ---
    for dep in DEPENDENCIAS:
        ms_filt_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]
        if "CRE" in ms_filt_dep.columns and not ms_filt_dep.empty:
            cre_agg = ms_filt_dep.groupby("CRE").agg(
                estudantes=("NU_INSCRICAO", "count"),
                media_geral=("MEDIA_GERAL", "mean"),
            ).reset_index()
            cre_agg["ano"] = ano
            cre_agg["dependencia"] = dep

            if dep == "Estadual" and not df_concluintes_cre.empty:
                conc_ano = df_concluintes_cre[df_concluintes_cre["NU_ANO"] == ano]
                cre_agg = cre_agg.merge(conc_ano[["CRE", "Concluintes"]], on="CRE", how="left")
                cre_agg["Concluintes"] = cre_agg["Concluintes"].fillna(0).astype(int)
                tx_part = cre_agg["estudantes"] / cre_agg["Concluintes"].replace(0, pd.NA) * 100
                cre_agg["tx_part_efetiva"] = pd.to_numeric(tx_part, errors="coerce").round(2)
            else:
                cre_agg["Concluintes"] = pd.NA
                cre_agg["tx_part_efetiva"] = pd.NA

            resultados["participacao_cre"].append(cre_agg)

    # --- Desempenho ---
    for dep in DEPENDENCIAS:
        subset = df_filt_ano[(df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]
        if len(subset) == 0:
            continue
        row = {"ano": ano, "dependencia": dep, "estudantes": len(subset)}
        for col in COLS_NOTAS + ["MEDIA_GERAL"]:
            row[f"media_{col.lower()}"] = subset[col].mean()
        resultados["desempenho"].append(row)

    # --- Escolas 2024 ---
    if ano == 2024:
        for dep in DEPENDENCIAS:
            # 2024: a escola so existe para provaveis concluintes (vinculo INEP/Censo),
            # entao filtrar por escola estadual MS ja seleciona a populacao de referencia.
            df_2024_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep)]
            if df_2024_dep.empty:
                continue

            agg_dict = {
                "estudantes": ("NU_SEQUENCIAL" if ano == 2024 else "NU_INSCRICAO", "count"),
                "media_geral": ("MEDIA_GERAL", "mean"),
                "media_cn": ("NU_NOTA_CN", "mean"),
                "media_ch": ("NU_NOTA_CH", "mean"),
                "media_lc": ("NU_NOTA_LC", "mean"),
                "media_mt": ("NU_NOTA_MT", "mean"),
                "media_redacao": ("NU_NOTA_REDACAO", "mean"),
            }
            df_escolas = df_2024_dep.groupby("CO_ESCOLA").agg(**agg_dict).reset_index()
            df_escolas["dependencia"] = dep

            muni_map = df_2024_dep.groupby("CO_ESCOLA")["NO_MUNICIPIO_ESC"].first().to_dict()
            cre_map = df_2024_dep.groupby("CO_ESCOLA")["CRE"].first().to_dict()
            nome_map = df_2024_dep.groupby("CO_ESCOLA")["NOME_ESCOLA"].first().to_dict()
            df_escolas["municipio"] = df_escolas["CO_ESCOLA"].map(muni_map)
            df_escolas["cre"] = df_escolas["CO_ESCOLA"].map(cre_map)
            df_escolas["NOME_ESCOLA"] = df_escolas["CO_ESCOLA"].map(nome_map)

            if dep == "Estadual" and not df_concluintes.empty:
                conc_2024 = df_concluintes[df_concluintes["NU_ANO"] == 2024][["CO_ESCOLA", "NOME_ESCOLA", "MUNICIPIO", "Concluintes"]].copy()
                # Merge por CO_ESCOLA (ambos usam 8 digitos)
                df_escolas = df_escolas.merge(conc_2024[["CO_ESCOLA", "Concluintes"]], on="CO_ESCOLA", how="left")
                # Para escolas nao encontradas, tentar merge por nome + municipio
                sem_match = df_escolas["Concluintes"].isna()
                if sem_match.any():
                    # Criar chave nome+municipio nos dois dataframes
                    df_escolas["_key"] = df_escolas["NOME_ESCOLA"].astype(str).str.strip().str.upper() + "|" + df_escolas["municipio"].astype(str).str.strip().str.upper()
                    conc_2024["_key"] = conc_2024["NOME_ESCOLA"].astype(str).str.strip().str.upper() + "|" + conc_2024["MUNICIPIO"].astype(str).str.strip().str.upper()
                    # Merge por chave
                    df_escolas = df_escolas.merge(conc_2024[["_key", "Concluintes"]], on="_key", how="left", suffixes=("", "_nome"))
                    # Preencher Concluintes faltantes com o valor do merge por nome
                    df_escolas["Concluintes"] = df_escolas["Concluintes"].fillna(df_escolas["Concluintes_nome"])
                    df_escolas = df_escolas.drop(columns=["_key", "Concluintes_nome"])
                df_escolas["Concluintes"] = df_escolas["Concluintes"].fillna(0).astype(int)
                tx_part = df_escolas["estudantes"] / df_escolas["Concluintes"].replace(0, pd.NA) * 100
                df_escolas["tx_part_efetiva"] = pd.to_numeric(tx_part, errors="coerce").round(2)
            else:
                df_escolas["Concluintes"] = pd.NA
                df_escolas["tx_part_efetiva"] = pd.NA

            resultados["escolas_2024"].append(df_escolas)

    # --- Territorial ---
    for dep in DEPENDENCIAS:
        ms_filt_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]
        if "CRE" not in ms_filt_dep.columns or ms_filt_dep.empty:
            continue

        cre_agg = ms_filt_dep.groupby("CRE").agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            media_cn=("NU_NOTA_CN", "mean"),
            media_ch=("NU_NOTA_CH", "mean"),
            media_lc=("NU_NOTA_LC", "mean"),
            media_mt=("NU_NOTA_MT", "mean"),
            media_redacao=("NU_NOTA_REDACAO", "mean"),
        ).reset_index()
        cre_agg["ano"] = ano
        cre_agg["dependencia"] = dep

        if dep == "Estadual" and not df_concluintes_cre.empty:
            conc_ano = df_concluintes_cre[df_concluintes_cre["NU_ANO"] == ano]
            cre_agg = cre_agg.merge(conc_ano[["CRE", "Concluintes"]], on="CRE", how="left")
            cre_agg["Concluintes"] = cre_agg["Concluintes"].fillna(0).astype(int)
            tx_part = cre_agg["estudantes"] / cre_agg["Concluintes"].replace(0, pd.NA) * 100
            cre_agg["tx_part_efetiva"] = pd.to_numeric(tx_part, errors="coerce").round(2)
        else:
            cre_agg["Concluintes"] = pd.NA
            cre_agg["tx_part_efetiva"] = pd.NA

        resultados["territorial"].append(cre_agg)

    # --- Municípios ---
    for dep in DEPENDENCIAS:
        ms_filt_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]
        if ms_filt_dep.empty:
            continue

        muni_agg = ms_filt_dep.groupby("NO_MUNICIPIO_ESC").agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            media_cn=("NU_NOTA_CN", "mean"),
            media_ch=("NU_NOTA_CH", "mean"),
            media_lc=("NU_NOTA_LC", "mean"),
            media_mt=("NU_NOTA_MT", "mean"),
            media_redacao=("NU_NOTA_REDACAO", "mean"),
        ).reset_index()
        muni_agg["ano"] = ano
        muni_agg["dependencia"] = dep

        if dep == "Estadual" and not df_concluintes_muni.empty:
            conc_ano = df_concluintes_muni[df_concluintes_muni["NU_ANO"] == ano].copy()
            # Merge por nome normalizado (sem acento/caixa) para casar "Corumbá"x"Corumba",
            # "Ladário"x"Ladario", "Anastácio"x"Anastacio" etc.
            conc_ano["_mnorm"] = conc_ano["MUNICIPIO"].map(normalizar_texto)
            conc_ano = conc_ano.groupby("_mnorm", as_index=False)["Concluintes"].sum()
            muni_agg["_mnorm"] = muni_agg["NO_MUNICIPIO_ESC"].map(normalizar_texto)
            muni_agg = muni_agg.merge(conc_ano, on="_mnorm", how="left")
            muni_agg["Concluintes"] = muni_agg["Concluintes"].fillna(0).astype(int)
            tx_part = muni_agg["estudantes"] / muni_agg["Concluintes"].replace(0, pd.NA) * 100
            muni_agg["tx_part_efetiva"] = pd.to_numeric(tx_part, errors="coerce").round(2)
            muni_agg = muni_agg.drop(columns=["MUNICIPIO", "_mnorm"], errors="ignore")
        else:
            muni_agg["Concluintes"] = pd.NA
            muni_agg["tx_part_efetiva"] = pd.NA

        resultados["municipios"].append(muni_agg)

    # --- Panorama Nacional ---
    for dep in DEPENDENCIAS:
        subset_bruta = df_bruta_ano[(df_bruta_ano["DEP_ADM"] == dep) & df_bruta_ano["CONCLUINTE"]]
        subset_filt = df_filt_ano[(df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]

        if len(subset_bruta) == 0 and len(subset_filt) == 0:
            continue

        row = {
            "ano": ano, "dependencia": dep,
            "inscritos": len(subset_bruta),
            "presentes": subset_bruta["PRESENTE_2_DIAS"].sum(),
            "presentes_filt": len(subset_filt),
        }
        for col in COLS_NOTAS + ["MEDIA_GERAL"]:
            row[f"media_{col.lower()}"] = subset_filt[col].mean()
        resultados["panorama"].append(row)

    # --- Referências ---
    ms_filt_ref = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == "Estadual") & df_filt_ano["CONCLUINTE"]]
    br_filt_ref = df_filt_ano[(df_filt_ano["DEP_ADM"] == "Estadual") & df_filt_ano["CONCLUINTE"]]
    for col in COLS_NOTAS + ["MEDIA_GERAL"]:
        resultados["referencias"].append({
            "ano": ano, "area": col,
            "media_ms": ms_filt_ref[col].mean(),
            "media_br": br_filt_ref[col].mean(),
        })

    # --- Evolução CRE ---
    for dep in DEPENDENCIAS:
        ms_filt_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]
        if "CRE" not in ms_filt_dep.columns or ms_filt_dep.empty:
            continue

        cre_agg = ms_filt_dep.groupby("CRE").agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            media_cn=("NU_NOTA_CN", "mean"),
            media_ch=("NU_NOTA_CH", "mean"),
            media_lc=("NU_NOTA_LC", "mean"),
            media_mt=("NU_NOTA_MT", "mean"),
            media_redacao=("NU_NOTA_REDACAO", "mean"),
        ).reset_index()
        cre_agg["ano"] = ano
        cre_agg["dependencia"] = dep
        resultados["evolucao_cre"].append(cre_agg)

    # --- Evolução Municípios ---
    for dep in DEPENDENCIAS:
        ms_filt_dep = df_filt_ano[(df_filt_ano["SG_UF_ESC"] == "MS") & (df_filt_ano["DEP_ADM"] == dep) & df_filt_ano["CONCLUINTE"]]
        if ms_filt_dep.empty:
            continue

        muni_agg = ms_filt_dep.groupby("NO_MUNICIPIO_ESC").agg(
            estudantes=("NU_INSCRICAO", "count"),
            media_geral=("MEDIA_GERAL", "mean"),
            media_cn=("NU_NOTA_CN", "mean"),
            media_ch=("NU_NOTA_CH", "mean"),
            media_lc=("NU_NOTA_LC", "mean"),
            media_mt=("NU_NOTA_MT", "mean"),
            media_redacao=("NU_NOTA_REDACAO", "mean"),
        ).reset_index()
        muni_agg["ano"] = ano
        muni_agg["dependencia"] = dep
        resultados["evolucao_muni"].append(muni_agg)

    # Limpar memória
    del df_bruta_ano, df_filt_ano, ms_bruta, ms_filt, br_filt
    gc.collect()

    # Converter listas de dicts para DataFrames
    for chave in ["sumario", "participacao_ano", "desempenho", "panorama", "referencias"]:
        if resultados[chave]:
            resultados[chave] = [pd.DataFrame(resultados[chave])]

    return resultados


# ============================================================
# INTEGRIDADE / QUALIDADE DA PARTICIPACAO
# ============================================================
_INTEG_AREAS = ["CN", "CH", "LC", "MT"]
_INTEG_DEP_MAP = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
_INTEG_COLS = [
    "NU_ANO", "SG_UF_ESC", "TP_DEPENDENCIA_ADM_ESC", "CO_ESCOLA", "NO_MUNICIPIO_ESC",
    "TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT",
    "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT",
    "TP_STATUS_REDACAO", "NU_NOTA_REDACAO",
]
_INTEG_MET = (
    ["compareceu", "presentes_filt", "elim_total", "elim_redacao", "elim_multi", "zeros_multi", "semnota_multi"]
    + [f"elim_{a.lower()}" for a in _INTEG_AREAS]
    + [f"zeros_{a.lower()}" for a in _INTEG_AREAS]
    + ["zeros_redacao", "semnota_redacao"]
)


def integ_indicadores(df):
    """Cria colunas indicadoras (0/1) das metricas de integridade para somar."""
    pres = {a: (df[f"TP_PRESENCA_{a}"] == 1) for a in _INTEG_AREAS}
    elim_area = {a: (df[f"TP_PRESENCA_{a}"] == 2) for a in _INTEG_AREAS}
    elim_red = df["TP_STATUS_REDACAO"] == 4
    p2 = pres["CN"] & pres["CH"] & pres["LC"] & pres["MT"]
    filt = p2 & ~elim_red
    comp = pres["CN"] | pres["CH"] | pres["LC"] | pres["MT"]
    elim_total = elim_area["CN"] | elim_area["CH"] | elim_area["LC"] | elim_area["MT"] | elim_red
    # eliminacao em >=2 areas objetivas (exclui redacao)
    elim_count = sum(elim_area[a].astype(int) for a in _INTEG_AREAS)
    elim_multi = elim_count >= 2
    # zeros em >=2 areas (entre presentes_filt)
    zero_area = {a: (filt & (df[f"NU_NOTA_{a}"] == 0)) for a in _INTEG_AREAS}
    zero_count = sum(zero_area[a].astype(int) for a in _INTEG_AREAS)
    zeros_multi = zero_count >= 2
    # sem nota em >=2 areas objetivas (entre presentes_filt)
    sem_area = {a: (filt & df[f"NU_NOTA_{a}"].isna()) for a in _INTEG_AREAS}
    sem_count = sum(sem_area[a].astype(int) for a in _INTEG_AREAS)
    semnota_multi = sem_count >= 2
    df = df.copy()
    df["compareceu"] = comp.astype("int32")
    df["presentes_filt"] = filt.astype("int32")
    df["elim_total"] = elim_total.astype("int32")
    df["elim_redacao"] = elim_red.astype("int32")
    df["elim_multi"] = elim_multi.astype("int32")
    df["zeros_multi"] = zeros_multi.astype("int32")
    df["semnota_multi"] = semnota_multi.astype("int32")
    for a in _INTEG_AREAS:
        df[f"elim_{a.lower()}"] = elim_area[a].astype("int32")
        df[f"zeros_{a.lower()}"] = zero_area[a].astype("int32")
    df["zeros_redacao"] = (filt & (df["NU_NOTA_REDACAO"] == 0)).astype("int32")
    df["semnota_redacao"] = (filt & (df["NU_NOTA_REDACAO"].isna())).astype("int32")
    return df


def integ_agg(df, chaves):
    """Soma as metricas por `chaves` e calcula as taxas (%)."""
    import numpy as _np
    g = df.groupby(chaves, observed=True)[_INTEG_MET].sum().reset_index()
    comp = g["compareceu"].replace(0, _np.nan)
    filt = g["presentes_filt"].replace(0, _np.nan)
    g["tx_elim"] = (g["elim_total"] / comp * 100).round(2)
    g["tx_elim_redacao"] = (g["elim_redacao"] / comp * 100).round(2)
    g["tx_semnota_redacao"] = (g["semnota_redacao"] / filt * 100).round(2)
    return g


def gerar_integridade(pasta_saida, cres=None, mapa_muni_cre=None):
    """Gera os 4 parquets de integridade a partir do arquivo completo de microdados.

    - integridade_rede.parquet      (ano x dependencia, MS + referencia Brasil estadual)
    - integridade_cre.parquet       (ano x CRE, estadual MS)
    - integridade_municipio.parquet (ano x municipio, estadual MS)
    - integridade_escola_2024.parquet (escola, estadual MS, somente 2024)
    """
    import pyarrow.parquet as _pq
    os.makedirs(pasta_saida, exist_ok=True)
    if cres is None:
        cres = carregar_cres()
    if mapa_muni_cre is None:
        mapa_muni_cre = carregar_mapa_municipio_cre()

    print("   [integridade] lendo microdados MS...")
    ms = _pq.read_table(ARQUIVO_ENTRADA, columns=_INTEG_COLS,
                        filters=[("SG_UF_ESC", "=", "MS")]).to_pandas()
    ms["DEP_ADM"] = ms["TP_DEPENDENCIA_ADM_ESC"].map(_INTEG_DEP_MAP)
    ms = integ_indicadores(ms)
    ms = enriquecer_ms(ms, cres, mapa_muni_cre)
    ms["MUNICIPIO"] = ms["NO_MUNICIPIO_ESC"]
    ms["CRE"] = ms["CRE"].fillna("Sem CRE").replace("", "Sem CRE")
    ms["MUNICIPIO"] = ms["MUNICIPIO"].fillna("Sem municipio").replace("", "Sem municipio")
    ms["NOME_ESCOLA"] = ms["NOME_ESCOLA"].fillna("").astype(str)

    rede = integ_agg(ms.dropna(subset=["DEP_ADM"]), ["NU_ANO", "DEP_ADM"])
    rede = rede.rename(columns={"NU_ANO": "ano", "DEP_ADM": "dependencia"})
    rede["escopo"] = "MS"

    print("   [integridade] lendo Brasil estadual (referencia)...")
    br = _pq.read_table(ARQUIVO_ENTRADA, columns=_INTEG_COLS,
                        filters=[("TP_DEPENDENCIA_ADM_ESC", "=", 2)]).to_pandas()
    br = integ_indicadores(br)
    br_rede = integ_agg(br, ["NU_ANO"]).rename(columns={"NU_ANO": "ano"})
    br_rede["dependencia"] = "Estadual"
    br_rede["escopo"] = "Brasil"
    rede = pd.concat([rede, br_rede], ignore_index=True)
    rede.to_parquet(os.path.join(pasta_saida, "integridade_rede.parquet"), index=False)

    est = ms[ms["DEP_ADM"] == "Estadual"].copy()
    cre = integ_agg(est, ["NU_ANO", "CRE"]).rename(columns={"NU_ANO": "ano"})
    cre.to_parquet(os.path.join(pasta_saida, "integridade_cre.parquet"), index=False)
    mun = integ_agg(est, ["NU_ANO", "MUNICIPIO", "CRE"]).rename(columns={"NU_ANO": "ano"})
    mun.to_parquet(os.path.join(pasta_saida, "integridade_municipio.parquet"), index=False)
    est24 = est[(est["NU_ANO"] == 2024) & est["CO_ESCOLA"].notna()].copy()
    esc = integ_agg(est24, ["CO_ESCOLA", "NOME_ESCOLA", "MUNICIPIO", "CRE"])
    esc["ano"] = 2024
    esc.to_parquet(os.path.join(pasta_saida, "integridade_escola_2024.parquet"), index=False)
    print(f"   [integridade] OK: rede={rede.shape[0]} cre={cre.shape[0]} mun={mun.shape[0]} esc24={esc.shape[0]}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("GERADOR DE DADOS AGREGADOS — Dashboard ENEM")
    print("=" * 60)
    print("\nPadrão: Escolas ESTADUAIS | Concluintes EM | Presentes 2 dias")

    # Carregar dados auxiliares
    print("\n[LOAD] Carregando dados auxiliares...")
    cres = carregar_cres()
    mapa_muni_cre = carregar_mapa_municipio_cre()
    df_concluintes = carregar_concluintes()
    df_concluintes_cre = carregar_concluintes_cre()
    df_concluintes_muni = carregar_concluintes_municipio()

    print(f"   CREs: {len(cres)} escolas mapeadas")
    print(f"   Concluintes escola: {len(df_concluintes)} registros")
    print(f"   Concluintes CRE: {len(df_concluintes_cre)} registros")
    print(f"   Concluintes município: {len(df_concluintes_muni)} registros")

    # Processar por ano (economia de memoria)
    print(f"\n[LOAD] Carregando {ARQUIVO_ENTRADA} por ano...")

    todos_resultados = {
        "sumario": [],
        "participacao_ano": [],
        "participacao_cre": [],
        "desempenho": [],
        "escolas_2024": [],
        "territorial": [],
        "municipios": [],
        "panorama": [],
        "referencias": [],
        "evolucao_cre": [],
        "evolucao_muni": [],
    }

    anos = pd.read_parquet(ARQUIVO_ENTRADA, columns=["NU_ANO"])["NU_ANO"].unique()
    print(f"   Anos encontrados: {sorted(anos)}")

    for ano in sorted(anos):
        print(f"\n[PROCESS] Ano {ano}...")

        # Carregar apenas o ano atual
        df_ano = pd.read_parquet(ARQUIVO_ENTRADA, filters=[("NU_ANO", "==", ano)])
        print(f"   Registros: {len(df_ano):,}")

        resultados_ano = processar_ano(df_ano, cres, mapa_muni_cre, df_concluintes, df_concluintes_cre, df_concluintes_muni)

        for chave, valor in resultados_ano.items():
            if valor:
                todos_resultados[chave].extend(valor)

        del df_ano, resultados_ano
        gc.collect()

    # Salvar todos os resultados
    print("\n[SAVE] Salvando arquivos agregados...")

    arquivos = {
        "sumario_executivo.parquet": todos_resultados["sumario"],
        "participacao_ano.parquet": todos_resultados["participacao_ano"],
        "participacao_cre.parquet": todos_resultados["participacao_cre"],
        "desempenho.parquet": todos_resultados["desempenho"],
        "escolas_2024.parquet": todos_resultados["escolas_2024"],
        "territorial.parquet": todos_resultados["territorial"],
        "municipios.parquet": todos_resultados["municipios"],
        "panorama_nacional.parquet": todos_resultados["panorama"],
        "referencias.parquet": todos_resultados["referencias"],
        "evolucao_cre.parquet": todos_resultados["evolucao_cre"],
        "evolucao_municipios.parquet": todos_resultados["evolucao_muni"],
    }

    total_mb = 0
    for nome, dados in arquivos.items():
        # Filtrar apenas DataFrames (ignorar dicts ou outros tipos)
        dfs = [d for d in dados if isinstance(d, pd.DataFrame) and not d.empty]
        if dfs:
            df_out = pd.concat(dfs, ignore_index=True)
            caminho = os.path.join(PASTA_SAIDA, nome)
            df_out.to_parquet(caminho, index=False)
            size_mb = os.path.getsize(caminho) / (1024 * 1024)
            total_mb += size_mb
            print(f"   [OK] {nome} ({size_mb:.2f} MB) — {len(df_out)} registros")
            del df_out
        else:
            print(f"   [WARN] {nome} — nenhum dado")

    print("\n" + "=" * 60)
    print("[OK] TODOS OS DADOS AGREGADOS GERADOS!")
    print(f"[DIR] Pasta: {PASTA_SAIDA}")
    print(f"[SIZE] Total: {total_mb:.2f} MB")
    print("=" * 60)

    # Integridade / qualidade da participacao (eliminados, zeros, sem nota)
    print("\n[INFO] Gerando agregados de integridade...")
    try:
        gerar_integridade(PASTA_SAIDA, cres, mapa_muni_cre)
    except Exception as e:  # nao quebra o ETL principal
        print(f"   [WARN] integridade falhou: {e}")


if __name__ == "__main__":
    main()
