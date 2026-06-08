"""
dashboard_enem_supabase.py

Dashboard ENEM v14 - Versão Supabase
Lê dados agregados do Supabase em vez de parquet local.

Para rodar localmente:
    streamlit run dashboard_enem_supabase.py

Para publicar no Streamlit Cloud:
    1. Criar repo GitHub com este arquivo
    2. Adicionar secrets no Streamlit Cloud (SUPABASE_HOST, SUPABASE_DB, etc.)
    3. Fazer deploy
"""

import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import psycopg2

# ============================================================
# CONFIGURAÇÃO DO TEMA
# ============================================================
TEMA = {
    "bg_principal": "#FFFFFF",
    "bg_secundario": "#F8F9FA",
    "bg_subtle": "#E9ECEF",
    "texto": "#212529",
    "texto_secundario": "#6C757D",
    "borda": "#DEE2E6",
    "borda_sutil": "#E9ECEF",
    "insight_bg": "#FFF3CD",
    "insight_border": "#FFC107",
}

AZUL_PRINCIPAL = "#003F7F"
COR_POSITIVO = "#0F8A5F"
COR_CRITICO = "#C03A2B"
COR_NEUTRO = "#6C757D"

CORES_AREAS = {
    "NU_NOTA_CN": "#28A745",
    "NU_NOTA_CH": "#FD7E14",
    "NU_NOTA_LC": "#007BFF",
    "NU_NOTA_MT": "#DC3545",
    "NU_NOTA_REDACAO": "#FFC107",
    "MEDIA_GERAL": "#6F42C1",
}

AREAS = {
    "MEDIA_GERAL": "Média Geral",
    "NU_NOTA_CN": "CN",
    "NU_NOTA_CH": "CH",
    "NU_NOTA_LC": "LC",
    "NU_NOTA_MT": "Mat.",
    "NU_NOTA_REDACAO": "Redação",
}

DEPENDENCIAS = ["Federal", "Estadual", "Municipal", "Privada"]

# Colunas geradas por gerar_dados_agregados.py (sumário executivo)
COLS_MEDIA_MS_SUMARIO = [
    "media_nu_nota_cn", "media_nu_nota_ch", "media_nu_nota_lc",
    "media_nu_nota_mt", "media_nu_nota_redacao", "media_media_geral",
]
COLS_MEDIA_BR_SUMARIO = [
    "media_br_nu_nota_cn", "media_br_nu_nota_ch", "media_br_nu_nota_lc",
    "media_br_nu_nota_mt", "media_br_nu_nota_redacao", "media_br_media_geral",
]
NOMES_AREAS_SUMARIO = ["CN", "CH", "LC", "Mat.", "Redação", "Média Geral"]

# ============================================================
# CONEXÃO COM SUPABASE
# ============================================================
@st.cache_data(ttl=3600)
def carregar_tabela(nome_tabela):
    """Carrega uma tabela do Supabase em um DataFrame usando cursor manual."""
    try:
        host = st.secrets["SUPABASE_HOST"]
        port = st.secrets["SUPABASE_PORT"]
        db = st.secrets["SUPABASE_DB"]
        user = st.secrets["SUPABASE_USER"]
        password = st.secrets["SUPABASE_PASS"]
    except Exception:
        host = os.getenv("SUPABASE_HOST", "aws-1-us-west-2.pooler.supabase.com")
        port = os.getenv("SUPABASE_PORT", "6543")
        db = os.getenv("SUPABASE_DB", "postgres")
        user = os.getenv("SUPABASE_USER", "postgres.ryomtlwpubcpzmhpnvjy")
        password = os.getenv("SUPABASE_PASS", "s@Ms@R@28mai")

    conn = psycopg2.connect(
        host=host, port=port, dbname=db, user=user, password=password,
        sslmode="require",
    )
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM "{nome_tabela}"')
        colunas = [desc[0] for desc in cursor.description]
        dados = cursor.fetchall()
        df = pd.DataFrame(dados, columns=colunas)
        cursor.close()
    finally:
        conn.close()
    return preparar_dataframe(df)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def preparar_dataframe(df):
    """Normaliza tipos vindos do Postgres (ano numérico, métricas numéricas)."""
    if df.empty:
        return df
    df = df.copy()
    if "ano" in df.columns:
        df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
        df = df.dropna(subset=["ano"])
        df = df[df["ano"].astype(str) != "ano"]
        df["ano"] = df["ano"].astype(int)
    texto_cols = {
        "dependencia", "cre", "CRE", "municipio", "NO_MUNICIPIO_ESC",
        "area", "MUNICIPIO", "NOME_ESCOLA",
    }
    for col in df.columns:
        if col in texto_cols or col.lower() in {c.lower() for c in texto_cols}:
            continue
        convertido = pd.to_numeric(df[col], errors="coerce")
        if convertido.notna().any():
            df[col] = convertido
    return df


def linha_por_ano(df, ano):
    """Retorna a linha do ano (comparação tolerante int/str)."""
    if df.empty or "ano" not in df.columns:
        return None
    ano_int = int(ano)
    sub = df[df["ano"] == ano_int]
    if sub.empty:
        sub = df[df["ano"].astype(str) == str(ano)]
    return sub.iloc[0] if not sub.empty else None


def valor_numerico(linha, *colunas, default=0):
    """Lê valor numérico da linha tentando nomes alternativos de coluna."""
    for col in colunas:
        if col not in linha.index:
            continue
        val = linha[col]
        if pd.isna(val):
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return default


def coluna_existente(linha, *candidatos):
    for col in candidatos:
        if col in linha.index and pd.notna(linha[col]):
            return col
    return candidatos[0]


def titulo_secao(texto):
    st.markdown(f"""
    <div style="background-color:{TEMA['bg_subtle']}; padding:12px 20px; border-radius:8px; margin:20px 0 15px 0;">
        <h3 style="color:{AZUL_PRINCIPAL}; margin:0; font-size:20px;">{texto}</h3>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(titulo, valor, cor=AZUL_PRINCIPAL, subtitulo=""):
    st.markdown(f"""
    <div style="background-color:{TEMA['bg_principal']}; border:1px solid {TEMA['borda']}; border-radius:10px; padding:15px; text-align:center;">
        <p style="color:{TEMA['texto_secundario']}; font-size:12px; margin:0; text-transform:uppercase; letter-spacing:1px;">{titulo}</p>
        <h2 style="color:{cor}; margin:5px 0; font-size:28px; font-weight:700;">{valor}</h2>
        <p style="color:{TEMA['texto_secundario']}; font-size:11px; margin:0;">{subtitulo}</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# ABAS
# ============================================================
def aba_sumario_executivo():
    st.header("📊 Sumário Executivo")

    df = carregar_tabela("sumario_executivo")
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    ano = st.selectbox(
        "Ano de referência",
        sorted(df["ano"].unique(), reverse=True),
        key="sumario_ano",
    )
    dados = linha_por_ano(df, ano)
    if dados is None:
        st.warning(f"Nenhum registro para o ano {ano}.")
        return

    total_inscritos = int(valor_numerico(dados, "total_inscritos"))
    total_presentes = int(valor_numerico(dados, "total_presentes"))
    total_concluintes = int(valor_numerico(dados, "total_concluintes"))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Inscritos", f"{total_inscritos:,}", AZUL_PRINCIPAL, "MS Estadual")
    with col2:
        kpi_card("Presentes", f"{total_presentes:,}", COR_POSITIVO)
    with col3:
        kpi_card("Concluintes", f"{total_concluintes:,}", "#FFC107")
    with col4:
        taxa = (total_presentes / max(total_inscritos, 1)) * 100
        kpi_card("Taxa de Presença", f"{taxa:.1f}%", COR_POSITIVO)

    # Gráfico de médias
    titulo_secao("Médias por Área — MS vs BR")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="MS", x=NOMES_AREAS_SUMARIO,
        y=[valor_numerico(dados, c) for c in COLS_MEDIA_MS_SUMARIO],
        marker_color=AZUL_PRINCIPAL,
    ))
    fig.add_trace(go.Bar(
        name="BR", x=NOMES_AREAS_SUMARIO,
        y=[valor_numerico(dados, c) for c in COLS_MEDIA_BR_SUMARIO],
        marker_color=COR_NEUTRO,
    ))
    fig.update_layout(barmode="group", title=f"Médias por Área — {ano}", yaxis_range=[0, 800])
    st.plotly_chart(fig, use_container_width=True)


def aba_participacao():
    st.header("📈 Participação")

    df = carregar_tabela("participacao_ano")
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    dep = st.multiselect(
        "Dependências", DEPENDENCIAS, default=["Estadual"], key="participacao_dep",
    )
    df_filt = df[df["dependencia"].isin(dep)]

    col_media = coluna_existente(df_filt.iloc[0], "presentes_filt", "presentes") if not df_filt.empty else "presentes_filt"

    # Evolução temporal
    fig = px.line(df_filt, x="ano", y=col_media, color="dependencia",
                  title="Evolução de Presentes por Dependência",
                  labels={col_media: "Presentes", "ano": "Ano"})
    st.plotly_chart(fig, use_container_width=True)

    # Tabela
    st.dataframe(df_filt.sort_values(["ano", "dependencia"]), use_container_width=True)


def aba_desempenho():
    st.header("🎓 Desempenho")

    df = carregar_tabela("desempenho")
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    dep = st.multiselect(
        "Dependências", DEPENDENCIAS, default=["Estadual"], key="desempenho_dep",
    )
    df_filt = df[df["dependencia"].isin(dep)]

    col_media = coluna_existente(
        df_filt.iloc[0], "media_media_geral", "media_geral",
    ) if not df_filt.empty else "media_media_geral"

    # Gráfico de médias
    fig = px.line(df_filt, x="ano", y=col_media, color="dependencia",
                  title="Evolução da Média Geral",
                  labels={col_media: "Média Geral", "ano": "Ano"})
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_filt, use_container_width=True)


def aba_escolas():
    st.header("🏫 Escolas — 2024")

    df = carregar_tabela("escolas_2024")
    if df.empty:
        st.warning("Nenhum dado disponível para 2024.")
        return

    dep = st.multiselect(
        "Dependência", DEPENDENCIAS, default=["Estadual"], key="escolas_dep",
    )
    df_filt = df[df["dependencia"].isin(dep)]

    col_media = coluna_existente(
        df_filt.iloc[0], "media_geral", "media_media_geral",
    ) if not df_filt.empty else "media_geral"

    # Tabela com estilização
    st.dataframe(df_filt.sort_values(col_media, ascending=False),
                 use_container_width=True, hide_index=True)


def aba_territorial():
    st.header("🗺️ Análise Territorial")

    df = carregar_tabela("territorial")
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    dep = st.multiselect("Dependência", DEPENDENCIAS, default=["Estadual"], key="territorial_dep")
    df_filt = df[df["dependencia"].isin(dep)]

    ano = st.selectbox("Ano", sorted(df_filt["ano"].unique(), reverse=True), key="territorial_ano")
    df_ano = df_filt[df_filt["ano"] == ano]

    col_media = coluna_existente(
        df_ano.iloc[0], "media_geral", "media_media_geral",
    ) if not df_ano.empty else "media_geral"

    # Tabela completa
    st.dataframe(df_ano.sort_values(col_media, ascending=False),
                 use_container_width=True, hide_index=True)


def aba_municipios():
    st.header("🏘️ Municípios")

    df = carregar_tabela("municipios")
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    dep = st.multiselect("Dependência", DEPENDENCIAS, default=["Estadual"], key="municipios_dep")
    df_filt = df[df["dependencia"].isin(dep)]

    ano = st.selectbox("Ano", sorted(df_filt["ano"].unique(), reverse=True), key="municipios_ano")
    df_ano = df_filt[df_filt["ano"] == ano]

    col_media = coluna_existente(
        df_ano.iloc[0], "media_geral", "media_media_geral",
    ) if not df_ano.empty else "media_geral"

    st.dataframe(df_ano.sort_values(col_media, ascending=False),
                 use_container_width=True, hide_index=True)


def aba_panorama_nacional():
    st.header("🇧🇷 Panorama Nacional")

    df = carregar_tabela("panorama_nacional")
    if df.empty:
        st.warning("Nenhum dado disponível.")
        return

    dep = st.multiselect("Dependências", DEPENDENCIAS, default=DEPENDENCIAS, key="panorama_dep")
    df_filt = df[df["dependencia"].isin(dep)]

    # Evolução
    fig = px.line(df_filt, x="ano", y="presentes_filt", color="dependencia",
                  title="Evolução de Presentes — Panorama Nacional",
                  labels={"presentes_filt": "Presentes", "ano": "Ano"})
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_filt, use_container_width=True)


# ============================================================
# MAIN
# ============================================================
def main():
    st.set_page_config(
        page_title="Dashboard ENEM — MS",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Header
    st.markdown(f"""
    <div style="background:linear-gradient(90deg, {AZUL_PRINCIPAL} 0%, #0056b3 100%); padding:20px; border-radius:10px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:32px;">📊 Dashboard ENEM — Mato Grosso do Sul</h1>
        <p style="color:rgba(255,255,255,0.8); margin:5px 0 0 0; font-size:14px;">Análise de desempenho dos estudantes de escolas públicas estaduais</p>
    </div>
    """, unsafe_allow_html=True)

    # Abas
    abas = st.tabs([
        "📊 Sumário Executivo",
        "📈 Participação",
        "🎓 Desempenho",
        "🏫 Escolas (2024)",
        "🗺️ Territorial",
        "🏘️ Municípios",
        "🇧🇷 Panorama Nacional",
    ])

    with abas[0]:
        aba_sumario_executivo()
    with abas[1]:
        aba_participacao()
    with abas[2]:
        aba_desempenho()
    with abas[3]:
        aba_escolas()
    with abas[4]:
        aba_territorial()
    with abas[5]:
        aba_municipios()
    with abas[6]:
        aba_panorama_nacional()


if __name__ == "__main__":
    main()
