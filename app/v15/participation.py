"""Taxas de participação em tabelas agregadas — painel ENEM v15."""

from __future__ import annotations

import pandas as pd

from app.v15.formatting import _pct_taxa


def _enriquecer_participacao_taxas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante Inscritos e Tx_Inscrição em tabelas de participação."""
    out = df.copy()
    if "inscritos" in out.columns and "Inscritos" not in out.columns:
        out["Inscritos"] = pd.to_numeric(out["inscritos"], errors="coerce").fillna(0).astype(int)
    if "Inscritos" not in out.columns:
        out["Inscritos"] = pd.NA
    if "tx_inscricao" in out.columns and "Tx_Inscrição" not in out.columns:
        out["Tx_Inscrição"] = pd.to_numeric(out["tx_inscricao"], errors="coerce")
    if "Tx_Inscrição" not in out.columns or out["Tx_Inscrição"].isna().all():
        out["Tx_Inscrição"] = _pct_taxa(out["Inscritos"], out.get("Concluintes", pd.NA), casas=1)
    if "Tx_Part_Efetiva" not in out.columns:
        pres = out.get("Presentes", out.get("Estudantes", pd.NA))
        out["Tx_Part_Efetiva"] = _pct_taxa(pres, out.get("Concluintes", pd.NA), casas=1)
    return out
