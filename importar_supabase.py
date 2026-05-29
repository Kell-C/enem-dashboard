"""
Script para importar o arquivo parquet ENEM para o Supabase (PostgreSQL).
Execute localmente no seu computador.

PREENCHA SUA SENHA na linha 16 antes de executar.
"""

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm
import os
import pyarrow.parquet as pq

# ============================================================
# CONFIGURAÇÃO - PREENCHA SUA SENHA AQUI
# ============================================================
ARQUIVO_PARQUET = r"C:\enem_analise\dados_processados\enem_completo_2019_2024_.parquet"

# Credenciais do Supabase (já preenchidas, exceto a senha)
SUPABASE_HOST = "aws-1-us-east-2.pooler.supabase.com"
SUPABASE_PORT = "6543"
SUPABASE_DB   = "postgres"
SUPABASE_USER = "postgres.txfdpmelppfibftwwcty"
SUPABASE_PASS = "s@Ms@R@28mai"  # <-- DIGITE SUA SENHA AQUI

# Tamanho do batch para inserção (número de linhas)
BATCH_SIZE = 5000

# ============================================================
# VALIDAÇÃO
# ============================================================
if SUPABASE_PASS == "SUA_SENHA_AQUI":
    print("❌ ERRO: Você precisa preencher a SUPABASE_PASS no script antes de executar!")
    print("   Edite a linha 16 e substitua 'SUA_SENHA_AQUI' pela sua senha do Supabase.")
    exit(1)

if not os.path.exists(ARQUIVO_PARQUET):
    print(f"❌ ERRO: Arquivo não encontrado: {ARQUIVO_PARQUET}")
    exit(1)

# ============================================================
# CONEXÃO
# ============================================================
print(f"🔌 Conectando a: {SUPABASE_HOST}...")

try:
    conn = psycopg2.connect(
        host=SUPABASE_HOST,
        port=SUPABASE_PORT,
        dbname=SUPABASE_DB,
        user=SUPABASE_USER,
        password=SUPABASE_PASS,
        sslmode="require"  # Obrigatório no Supabase
    )
except Exception as e:
    print(f"❌ ERRO ao conectar: {e}")
    print("   Verifique se a senha está correta e se o projeto está ativo.")
    exit(1)

cursor = conn.cursor()
print("✅ Conectado com sucesso!")

# ============================================================
# CRIAR TABELA
# ============================================================
print("📋 Criando tabela enem_dados...")
cursor.execute("""
DROP TABLE IF EXISTS enem_dados;

CREATE TABLE enem_dados (
    id SERIAL PRIMARY KEY,
    NU_ANO INTEGER,
    NU_INSCRICAO BIGINT,
    SG_UF_ESC VARCHAR(2),
    SG_UF_PROVA VARCHAR(2),
    CO_MUNICIPIO_ESC BIGINT,
    NO_MUNICIPIO_ESC VARCHAR(100),
    TP_DEPENDENCIA_ADM_ESC INTEGER,
    DEP_ADM VARCHAR(20),
    TP_LOCALIZACAO_ESC INTEGER,
    CO_ESCOLA BIGINT,
    NO_ENTIDADE VARCHAR(200),
    CATEGORIA_PARTICIPACAO VARCHAR(50),
    TP_ST_CONCLUSAO INTEGER,
    IN_TREINEIRO INTEGER,
    NU_NOTA_CN NUMERIC(10,2),
    NU_NOTA_CH NUMERIC(10,2),
    NU_NOTA_LC NUMERIC(10,2),
    NU_NOTA_MT NUMERIC(10,2),
    NU_NOTA_REDACAO NUMERIC(10,2),
    MEDIA_GERAL NUMERIC(10,2),
    TP_COR_RACA INTEGER,
    TP_SEXO VARCHAR(1),
    Q001 VARCHAR(1),
    Q002 VARCHAR(1),
    Q006 VARCHAR(2),
    INTERNET VARCHAR(1)
);

-- Índices essenciais para performance das queries do dashboard
CREATE INDEX idx_enem_ano ON enem_dados(NU_ANO);
CREATE INDEX idx_enem_uf_esc ON enem_dados(SG_UF_ESC);
CREATE INDEX idx_enem_uf_prova ON enem_dados(SG_UF_PROVA);
CREATE INDEX idx_enem_dep_adm ON enem_dados(DEP_ADM);
CREATE INDEX idx_enem_categoria ON enem_dados(CATEGORIA_PARTICIPACAO);
CREATE INDEX idx_enem_municipio ON enem_dados(NO_MUNICIPIO_ESC);
CREATE INDEX idx_enem_escola ON enem_dados(CO_ESCOLA);
""")
conn.commit()
print("✅ Tabela e índices criados.")

# ============================================================
# LER PARQUET EM CHUNKS E INSERIR
# ============================================================
print(f"📂 Lendo {ARQUIVO_PARQUET}...")

# Ler só o schema para saber as colunas existentes (sem carregar dados na memória)
pf = pq.ParquetFile(ARQUIVO_PARQUET)
colunas_parquet = pf.schema.names
print(f"   Colunas disponíveis: {colunas_parquet}")

# Mapeamento de colunas do parquet para a tabela
COLUNAS_TABELA = [
    "NU_ANO", "NU_INSCRICAO", "SG_UF_ESC", "SG_UF_PROVA",
    "CO_MUNICIPIO_ESC", "NO_MUNICIPIO_ESC", "TP_DEPENDENCIA_ADM_ESC",
    "DEP_ADM", "TP_LOCALIZACAO_ESC", "CO_ESCOLA", "NO_ENTIDADE",
    "CATEGORIA_PARTICIPACAO", "TP_ST_CONCLUSAO", "IN_TREINEIRO",
    "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT",
    "NU_NOTA_REDACAO", "MEDIA_GERAL", "TP_COR_RACA", "TP_SEXO",
    "Q001", "Q002", "Q006", "INTERNET"
]

# Ver quais colunas existem no parquet
cols_para_ler = [c for c in COLUNAS_TABELA if c in colunas_parquet]
print(f"   Colunas a importar: {cols_para_ler}")

if "MEDIA_GERAL" not in cols_para_ler:
    print("   ℹ️ Coluna MEDIA_GERAL será calculada após a importação.")

# Contar total de registros para a barra de progresso
total_estimado = pf.metadata.num_rows
print(f"   Total estimado de registros: {total_estimado:,}")

# Inserir dados em batches usando PyArrow diretamente
inserted = 0

for batch in tqdm(pf.iter_batches(columns=cols_para_ler, batch_size=BATCH_SIZE), 
                  total=(total_estimado // BATCH_SIZE) + 1, 
                  desc="Inserindo"):
    
    # Converter RecordBatch para pandas DataFrame
    chunk = batch.to_pandas()
    
    # Converter colunas numéricas inteiras para tipos padrão (evita pd.NA)
    for col in ["NU_ANO", "TP_ST_CONCLUSAO", "IN_TREINEIRO", "TP_COR_RACA", "TP_DEPENDENCIA_ADM_ESC", "TP_LOCALIZACAO_ESC"]:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce").astype("float64").astype("Int64")
    
    # Converter todas as colunas para object e substituir pd.NA/NaN/None por None nativo do Python
    chunk = chunk.astype(object)
    chunk = chunk.where(chunk.notna(), None)
    
    # Garantir que não haja pd.NA remanescente em nenhuma célula
    values = []
    for row in chunk.itertuples(index=False, name=None):
        values.append(tuple(None if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)) else v for v in row))
    
    col_names = ", ".join(chunk.columns)
    
    execute_values(
        cursor,
        f"INSERT INTO enem_dados ({col_names}) VALUES %s",
        values,
        page_size=BATCH_SIZE
    )
    conn.commit()
    inserted += len(chunk)

print(f"\n✅ Importação concluída! {inserted:,} registros inseridos.")

# Calcular MEDIA_GERAL se não existia no parquet
if "MEDIA_GERAL" not in cols_para_ler:
    print("🧮 Calculando MEDIA_GERAL para registros existentes...")
    cursor.execute("""
        UPDATE enem_dados 
        SET MEDIA_GERAL = (
            COALESCE(NU_NOTA_CN, 0) + COALESCE(NU_NOTA_CH, 0) + 
            COALESCE(NU_NOTA_LC, 0) + COALESCE(NU_NOTA_MT, 0) + 
            COALESCE(NU_NOTA_REDACAO, 0)
        ) / NULLIF(
            (CASE WHEN NU_NOTA_CN IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN NU_NOTA_CH IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN NU_NOTA_LC IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN NU_NOTA_MT IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN NU_NOTA_REDACAO IS NOT NULL THEN 1 ELSE 0 END)
        , 0)
        WHERE MEDIA_GERAL IS NULL;
    """)
    conn.commit()
    print("✅ MEDIA_GERAL calculada.")

# Estatísticas finais
cursor.execute("SELECT COUNT(*) FROM enem_dados")
total = cursor.fetchone()[0]
print(f"📊 Total de registros na tabela: {total:,}")

cursor.close()
conn.close()
print("\n🔒 Conexão fechada. Importação finalizada!")
