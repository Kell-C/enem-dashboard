# -*- coding: utf-8 -*-
"""
gerar_integridade.py — gerador rapido (standalone) dos agregados de INTEGRIDADE.

Produz, em data/agregados/, sem reprocessar todo o ETL principal:
  integridade_rede.parquet        (ano x dependencia: MS + referencia Brasil estadual)
  integridade_cre.parquet         (ano x CRE, estadual MS)
  integridade_municipio.parquet   (ano x municipio, estadual MS)
  integridade_escola_2024.parquet (escola, estadual MS, somente 2024)

A logica e a mesma da funcao canonica gerar_dados_agregados.gerar_integridade();
aqui apenas direcionamos a saida para a pasta do projeto.
"""

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import gerar_dados_agregados as G  # noqa: E402

PASTA_SAIDA = os.path.join(_RAIZ, "data", "agregados")


if __name__ == "__main__":
    G.gerar_integridade(PASTA_SAIDA)
    print("OK ->", PASTA_SAIDA)
