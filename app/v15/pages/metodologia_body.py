"""Corpo das funções de `metodologia` (fase 5d)."""

from __future__ import annotations

from app.v15.page_imports import *

def render_metodologia_detalhe() -> None:
    """Conteúdo técnico completo (expander no rodapé)."""
    st.markdown(
        f"""
        <div class="insight">
        <strong>Público-alvo:</strong> Secretário de Educação (panorama e evolução comparativa),
        Coordenadoria do Ensino Médio e assessoramento pedagógico (diagnóstico e priorização),
        equipe técnica SED (detalhamento e auditoria de dados).
        </div>
        """,
        unsafe_allow_html=True,
    )
    titulo_secao("População de referência")
    st.markdown(
        """
        - **Concluintes do Ensino Médio** na rede estadual de MS (planilha SED / `participacao_ano`).
        - **Presentes nos 2 dias** de prova e **não eliminados** em qualquer área ou redação (`presentes_filt`).
        - **2019–2023:** concluintes EM (`TP_ST_CONCLUSAO == 2`).
        - **2024:** todos os inscritos estaduais (microdado sem distinção de concluinte).
        - **Taxa de participação efetiva:** presentes filtrados ÷ concluintes × 100 — indicador central do painel.
        """
    )
    titulo_secao("Período analítico")
    st.markdown(
        """
        - **Recorte temporal:** 2019–2024 (evolução comparativa da rede estadual no ENEM).
        - **Marco institucional:** a gestão do secretário atual teve início em **2023**; o painel não atribui
          causalmente resultados a gestões específicas, mas permite comparar períodos antes e depois desse ano.
        - **Desempenho:** calculado apenas sobre **participantes efetivos** (não sobre o total de concluintes).
        """
    )
    titulo_secao("Fontes de dados")
    st.markdown(
        """
        | Camada | Fonte | Uso |
        |--------|-------|-----|
        | Agregados | `gerar_dados_agregados.py` → parquets em `data/agregados/` | KPIs, evolução, participação, quantis |
        | Notas individuais | `gerar_notas_individuais.py` → `notas_individuais_ms.parquet` | Boxplot, histograma, desvio por CRE/município/escola |
        | Microdado bruto | `enem_completo_2019_2024_.parquet` (offline) | Geração dos agregados; não carregado no painel em produção |
        | Cadastro | `cres.xlsx` | CRE, município, nome de escola |
        """
    )
    titulo_secao("Estrutura do painel (Modelo B)")
    st.markdown(
        """
        1. **Camada Status** — KPIs e principais achados (aba Gestão, topo).
        2. **Camada Contexto** — sub-abas Participação, Desempenho, Território, Nacional.
        3. **Camada Detalhe** — expanders, tabelas completas, histogramas e boxplots finos.

        **Território (Modelo C):** drill-down Estado → CRE → Município → Escola (2024).
        """
    )
    titulo_secao("Performance e atualização")
    st.markdown(
        f"""
        - Dados locais: `PASTA_AGREGADOS` (padrão `data/agregados/`).
        - Após regerar parquets: **Clear cache → Rerun** no Streamlit (cache TTL 1h).
        - Modo Supabase: variável `DATA_SOURCE=supabase` e credenciais configuradas.
        - Versão do painel: **v15 · dados agregados** · fonte: **{get_data_source().upper()}**.
        """
    )

def render_aba_metodologia():
    """Referência técnica: população, fontes, camadas e limitações."""
    titulo_secao(
        "Metodologia e fontes",
        "Definições analíticas, população de referência e estrutura do painel.",
    )
    render_metodologia_detalhe()

