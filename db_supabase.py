"""
Módulo de conexão com Supabase (PostgreSQL) para o dashboard ENEM.
Coloque este arquivo na mesma pasta do dashboard.
"""

import os
import pandas as pd
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# ============================================================
# CONFIGURAÇÃO - Use st.secrets no Streamlit Cloud
# ============================================================
# Localmente (desenvolvimento), use variáveis de ambiente:
#   $env:SUPABASE_HOST="db.xxxxxxxxxx.supabase.co"
#   $env:SUPABASE_PASS="sua_senha"
#
# No Streamlit Cloud (Secrets):
#   [supabase]
#   host = "db.xxxxxxxxxx.supabase.co"
#   port = "5432"
#   db = "postgres"
#   user = "postgres"
#   password = "sua_senha"

def get_db_config():
    """Lê configuração do banco de secrets ou variáveis de ambiente."""
    try:
        # Streamlit Cloud
        return {
            "host": st.secrets["supabase"]["host"],  # ex: aws-1-us-east-2.pooler.supabase.com
            "port": st.secrets["supabase"].get("port", "5432"),
            "dbname": st.secrets["supabase"].get("db", "postgres"),
            "user": st.secrets["supabase"]["user"],
            "password": st.secrets["supabase"]["password"],
        }
    except (KeyError, FileNotFoundError):
        # Local/Windows
        return {
            "host": os.getenv("SUPABASE_HOST", "aws-1-us-east-2.pooler.supabase.com"),
            "port": os.getenv("SUPABASE_PORT", "5432"),
            "dbname": os.getenv("SUPABASE_DB", "postgres"),
            "user": os.getenv("SUPABASE_USER", "postgres"),
            "password": os.getenv("SUPABASE_PASS", ""),
        }

@contextmanager
def get_connection():
    """Context manager para conexão com o banco."""
    cfg = get_db_config()
    conn = psycopg2.connect(
        **cfg,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()

# ============================================================
# FUNÇÕES DE CARREGAMENTO (substituem as antigas)
# ============================================================

@st.cache_data(ttl=3600)
def carregar_base_bruta_db(anos=None, dep_adm=None) -> pd.DataFrame:
    """
    Carrega a base filtrada do banco.
    Retorna apenas estudantes presentes ambos dias, não treineiros, concluintes.
    
    Parameters:
        anos: lista de anos para filtrar (ex: [2022, 2023, 2024])
        dep_adm: lista de dependências (ex: ["Estadual"])
    """
    query = """
        SELECT 
            NU_ANO, NU_INSCRICAO, SG_UF_ESC, SG_UF_PROVA,
            CO_MUNICIPIO_ESC, NO_MUNICIPIO_ESC, TP_DEPENDENCIA_ADM_ESC,
            DEP_ADM, TP_LOCALIZACAO_ESC, CO_ESCOLA, NO_ENTIDADE,
            CATEGORIA_PARTICIPACAO, TP_ST_CONCLUSAO, IN_TREINEIRO,
            NU_NOTA_CN, NU_NOTA_CH, NU_NOTA_LC, NU_NOTA_MT, NU_NOTA_REDACAO,
            MEDIA_GERAL, TP_COR_RACA, TP_SEXO, Q001, Q002, Q006, INTERNET
        FROM enem_dados
        WHERE CATEGORIA_PARTICIPACAO = 'presente_ambos_dias'
          AND (TP_ST_CONCLUSAO = 2 OR TP_ST_CONCLUSAO IS NULL)
          AND (IN_TREINEIRO = 0 OR IN_TREINEIRO IS NULL)
    """
    params = []
    
    if anos:
        placeholders = ", ".join(["%s"] * len(anos))
        query += f" AND NU_ANO IN ({placeholders})"
        params.extend(anos)
    
    if dep_adm:
        placeholders = ", ".join(["%s"] * len(dep_adm))
        query += f" AND DEP_ADM IN ({placeholders})"
        params.extend(dep_adm)
    
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=params)
    
    # Garantir tipos numéricos
    for col in ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO", "MEDIA_GERAL"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df

@st.cache_data(ttl=3600)
def carregar_resumo_uf_db(ano: int, dep_adm: str = None) -> pd.DataFrame:
    """
    Retorna médias por UF já agregadas pelo banco.
    Muito mais rápido que carregar tudo na memória.
    """
    query = """
        SELECT 
            COALESCE(SG_UF_ESC, SG_UF_PROVA) AS UF,
            COUNT(*) AS presentes,
            ROUND(AVG(NU_NOTA_CN)::numeric, 2) AS CN,
            ROUND(AVG(NU_NOTA_CH)::numeric, 2) AS CH,
            ROUND(AVG(NU_NOTA_LC)::numeric, 2) AS LC,
            ROUND(AVG(NU_NOTA_MT)::numeric, 2) AS MT,
            ROUND(AVG(NU_NOTA_REDACAO)::numeric, 2) AS Redacao,
            ROUND(AVG(MEDIA_GERAL)::numeric, 2) AS Media_Geral
        FROM enem_dados
        WHERE NU_ANO = %s
          AND CATEGORIA_PARTICIPACAO = 'presente_ambos_dias'
          AND (TP_ST_CONCLUSAO = 2 OR TP_ST_CONCLUSAO IS NULL)
          AND (IN_TREINEIRO = 0 OR IN_TREINEIRO IS NULL)
    """
    params = [ano]
    
    if dep_adm:
        query += " AND DEP_ADM = %s"
        params.append(dep_adm)
    
    query += " GROUP BY COALESCE(SG_UF_ESC, SG_UF_PROVA) ORDER BY Media_Geral DESC"
    
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)

@st.cache_data(ttl=3600)
def carregar_resumo_municipio_db(ano: int, uf: str = "MS", dep_adm: str = None) -> pd.DataFrame:
    """Retorna médias por município (para MS)."""
    query = """
        SELECT 
            NO_MUNICIPIO_ESC AS municipio,
            COUNT(*) AS presentes,
            ROUND(AVG(NU_NOTA_CN)::numeric, 2) AS CN,
            ROUND(AVG(NU_NOTA_CH)::numeric, 2) AS CH,
            ROUND(AVG(NU_NOTA_LC)::numeric, 2) AS LC,
            ROUND(AVG(NU_NOTA_MT)::numeric, 2) AS MT,
            ROUND(AVG(NU_NOTA_REDACAO)::numeric, 2) AS Redacao,
            ROUND(AVG(MEDIA_GERAL)::numeric, 2) AS Media_Geral
        FROM enem_dados
        WHERE NU_ANO = %s
          AND COALESCE(SG_UF_ESC, SG_UF_PROVA) = %s
          AND CATEGORIA_PARTICIPACAO = 'presente_ambos_dias'
          AND (TP_ST_CONCLUSAO = 2 OR TP_ST_CONCLUSAO IS NULL)
          AND (IN_TREINEIRO = 0 OR IN_TREINEIRO IS NULL)
    """
    params = [ano, uf]
    
    if dep_adm:
        query += " AND DEP_ADM = %s"
        params.append(dep_adm)
    
    query += " GROUP BY NO_MUNICIPIO_ESC ORDER BY Media_Geral DESC"
    
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)

@st.cache_data(ttl=3600)
def carregar_resumo_escola_db(ano: int, municipio: str, dep_adm: str = None) -> pd.DataFrame:
    """Retorna médias por escola para um município específico."""
    query = """
        SELECT 
            CO_ESCOLA,
            COALESCE(NO_ENTIDADE, CO_ESCOLA::text) AS escola,
            COUNT(*) AS presentes,
            ROUND(AVG(NU_NOTA_CN)::numeric, 2) AS CN,
            ROUND(AVG(NU_NOTA_CH)::numeric, 2) AS CH,
            ROUND(AVG(NU_NOTA_LC)::numeric, 2) AS LC,
            ROUND(AVG(NU_NOTA_MT)::numeric, 2) AS MT,
            ROUND(AVG(NU_NOTA_REDACAO)::numeric, 2) AS Redacao,
            ROUND(AVG(MEDIA_GERAL)::numeric, 2) AS Media_Geral
        FROM enem_dados
        WHERE NU_ANO = %s
          AND NO_MUNICIPIO_ESC = %s
          AND CATEGORIA_PARTICIPACAO = 'presente_ambos_dias'
          AND (TP_ST_CONCLUSAO = 2 OR TP_ST_CONCLUSAO IS NULL)
          AND (IN_TREINEIRO = 0 OR IN_TREINEIRO IS NULL)
    """
    params = [ano, municipio]
    
    if dep_adm:
        query += " AND DEP_ADM = %s"
        params.append(dep_adm)
    
    query += " GROUP BY CO_ESCOLA, NO_ENTIDADE ORDER BY Media_Geral DESC"
    
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)

@st.cache_data(ttl=3600)
def carregar_inscritos_por_uf_db(ano: int) -> pd.DataFrame:
    """Retorna total de inscritos por UF (da base bruta, sem filtros de presentes)."""
    # Nota: no Supabase você precisará de uma tabela separada ou usar dados brutos
    # Aqui usamos uma estimativa simples do próprio ENEM
    query = """
        SELECT 
            COALESCE(SG_UF_ESC, SG_UF_PROVA) AS UF,
            COUNT(*) AS total_inscritos
        FROM enem_dados
        WHERE NU_ANO = %s
        GROUP BY COALESCE(SG_UF_ESC, SG_UF_PROVA)
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=[ano])
