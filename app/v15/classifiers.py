"""Classificadores semáforo (status KPI) — painel ENEM v15."""

from __future__ import annotations

from typing import Optional

import numpy as np


def classificar_tendencia(variacao: float) -> str:
    if variacao is None or np.isnan(variacao):
        return "neutro"
    if variacao >= 5:
        return "positivo"
    if variacao > -5:
        return "atencao"
    return "critico"


def classificar_participacao(pct: float) -> str:
    if pct >= 80:
        return "positivo"
    if pct >= 60:
        return "atencao"
    return "critico"


def classificar_posicao(pos: Optional[int], total: int) -> str:
    if pos is None or total <= 0:
        return "neutro"
    pct = pos / total
    if pct <= 0.33:
        return "positivo"
    if pct <= 0.66:
        return "atencao"
    return "critico"
