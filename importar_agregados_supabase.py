"""
importar_agregados_supabase.py

Script para importar os dados agregados do dashboard ENEM para o Supabase.
Cria as tabelas necessárias e importa os dados dos arquivos parquet.

Uso:
    python importar_agregados_supabase.py
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ============================================================
# CONFIGURAÇÃO
# ============================================================
PASTA_AGREGADOS = r"C:\enem_analise\dados_processados\agregados"

# Credenciais do Supabase (atualizar conforme necessário)
SUPABASE_HOST = "aws-1-us-west-2.pooler.supabase.com"
SUPABASE_PORT = "6543"
SUPABASE_DB   = "postgres"
SUPABASE_USER = "postgres.ryomtlwpubcpzmhpnvjy"  # Atualizar com o usuário correto
SUPABASE_PASS = "s@Ms@R@28mai"  # <-- DIGITE SUA SENHA AQUI

# Mapeamento de arquivos para tabelas
TABELAS = {
    "sumario_executivo.parquet": "sumario_executivo",
    "participacao_ano.parquet": "participacao_ano",
    "participacao_cre.parquet": "participacao_cre",
    "desempenho.parquet": "desempenho",
    "escolas_2024.parquet": "escolas_2024",
    "territorial.parquet": "territorial",
    "municipios.parquet": "municipios",
    "panorama_nacional.parquet": "panorama_nacional",
    "referencias.parquet": "referencias",
    "evolucao_cre.parquet": "evolucao_cre",
    "evolucao_municipios.parquet": "evolucao_municipios",
}

# ============================================================
# CONEXÃO
# ============================================================
def conectar():
    return psycopg2.connect(
        host=SUPABASE_HOST,
        port=SUPABASE_PORT,
        dbname=SUPABASE_DB,
        user=SUPABASE_USER,
        password=SUPABASE_PASS,
        sslmode="require",
    )


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def inferir_tipo_sql(serie):
    """Infere o tipo SQL a partir de uma série pandas."""
    if pd.api.types.is_integer_dtype(serie):
        return "INTEGER"
    elif pd.api.types.is_float_dtype(serie):
        return "FLOAT"
    elif pd.api.types.is_bool_dtype(serie):
        return "BOOLEAN"
    else:
        max_len = serie.astype(str).str.len().max()
        return f"VARCHAR({max(255, int(max_len * 1.5))})"


def criar_tabela(conn, nome_tabela, df):
    """Cria uma tabela no Supabase baseada no DataFrame."""
    cursor = conn.cursor()

    # Dropar tabela se existir
    cursor.execute(f"DROP TABLE IF EXISTS {nome_tabela};")

    # Criar colunas
    colunas = []
    for col in df.columns:
        tipo = inferir_tipo_sql(df[col])
        colunas.append(f'"{col}" {tipo}')

    sql = f"CREATE TABLE {nome_tabela} (\n    " + ",\n    ".join(colunas) + "\n);"
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    print(f"   ✓ Tabela {nome_tabela} criada")


def importar_dados(conn, nome_tabela, df):
    """Importa dados do DataFrame para a tabela."""
    cursor = conn.cursor()

    # Preparar dados
    colunas = list(df.columns)
    valores = []
    for _, row in df.iterrows():
        valores.append(tuple(None if pd.isna(v) else v for v in row))

    if not valores:
        print(f"   ⚠️ Nenhum dado para importar em {nome_tabela}")
        return

    # Inserir em batch
    template = "(" + ", ".join(["%s"] * len(colunas)) + ")"
    sql = f'INSERT INTO {nome_tabela} ("' + '", "'.join(colunas) + '") VALUES %s'

    execute_values(cursor, sql, valores, template=template, page_size=1000)
    conn.commit()
    cursor.close()
    print(f"   ✓ {len(valores)} registros importados")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("IMPORTADOR DE DADOS AGREGADOS — Supabase")
    print("=" * 60)

    if SUPABASE_PASS == "sua_senha_aqui":
        print("\n❌ ERRO: Você precisa preencher a SUPABASE_PASS no script!")
        print("   Edite a linha 24 e substitua 'sua_senha_aqui' pela sua senha.")
        return

    print(f"\n🔌 Conectando a {SUPABASE_HOST}...")
    try:
        conn = conectar()
        print("   ✅ Conectado com sucesso!")
    except Exception as e:
        print(f"   ❌ Erro ao conectar: {e}")
        return

    # Verificar arquivos
    arquivos = [f for f in os.listdir(PASTA_AGREGADOS) if f.endswith(".parquet")]
    print(f"\n📂 {len(arquivos)} arquivos encontrados em {PASTA_AGREGADOS}")

    for arquivo in sorted(arquivos):
        nome_tabela = TABELAS.get(arquivo, arquivo.replace(".parquet", ""))
        caminho = os.path.join(PASTA_AGREGADOS, arquivo)

        print(f"\n📊 Processando {arquivo}...")
        df = pd.read_parquet(caminho)
        print(f"   {len(df)} registros, {len(df.columns)} colunas")

        criar_tabela(conn, nome_tabela, df)
        importar_dados(conn, nome_tabela, df)

        del df

    conn.close()

    print("\n" + "=" * 60)
    print("✅ TODOS OS DADOS IMPORTADOS!")
    print("=" * 60)


if __name__ == "__main__":
    main()
