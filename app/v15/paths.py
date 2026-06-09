"""Caminhos e assets do painel v15."""

from __future__ import annotations

import os
from pathlib import Path

from cres_loader import resolve_arquivo_cres

ROOT = Path(__file__).resolve().parents[2]

LOGO_MS_CANDIDATES = (
    ROOT / "assets" / "logo_governo_ms.png",
    ROOT / "assets" / "logo_governo_ms.svg",
    ROOT / "assets" / "logo_sed_ms.svg",
    ROOT / "assets" / "logo_sed_ms.png",
)

ARQUIVO_CRES = (
    os.getenv("ARQUIVO_CRES")
    or resolve_arquivo_cres()
    or str(ROOT / "cres.xlsx")
)
ARQUIVO_CONCLUINTES = os.getenv(
    "ARQUIVO_CONCLUINTES",
    str(ROOT / "data" / "Concluintes EM 2019 a 2024.xlsx"),
)
