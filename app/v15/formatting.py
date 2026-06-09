"""Formatação numérica — painel v15."""

import numpy as np
import pandas as pd


def fmt_int(n) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    return f"{int(n):,}".replace(",", ".")


def fmt_float(n, casas: int = 1) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    s = f"{n:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(n, casas: int = 1) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    return f"{fmt_float(n, casas)}%"


def fmt_delta(n, casas: int = 1, unidade: str = " pts") -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    sinal = "+" if n >= 0 else "−"
    return f"{sinal}{fmt_float(abs(n), casas)}{unidade}"


def safe_int_val(n, default: int = 0) -> int:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return default
    v = pd.to_numeric(n, errors="coerce")
    return int(v) if pd.notna(v) else default


def pct_taxa(numerador: pd.Series, concluintes: pd.Series, casas: int = 1) -> pd.Series:
    denom = pd.to_numeric(concluintes, errors="coerce").replace(0, pd.NA)
    tx = numerador / denom * 100
    return tx.apply(lambda x: round(x, casas) if pd.notna(x) else pd.NA)

# Aliases legados (compatibilidade com dashboard_enem_v15.py)
_safe_int_val = safe_int_val
_pct_taxa = pct_taxa
