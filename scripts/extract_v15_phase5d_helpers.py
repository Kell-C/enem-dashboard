"""Gera app/v15/page_helpers.py e estende ui.py a partir do monolito."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboard_enem_v15.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


HELPERS_HEADER = '''\
"""Helpers compartilhados pelas páginas v15 (extraídos do monolito)."""

from __future__ import annotations

import html as _html
import os
import unicodedata
from typing import Optional

import pandas as pd
import streamlit as st

from app.v15.classifiers import classificar_participacao
from app.v15.formatting import fmt_int, fmt_pct
from app.v15.paths import ARQUIVO_CONCLUINTES
from app.v15.theme import (
    AREAS,
    AZUL_PRINCIPAL,
    COR_HIST_NA,
    CORES_AREA,
    CORES_DEP,
    TEMA,
)
from app.v15.ui import _render_html


'''

LEGENDA_INLINE = slice_lines(1196, 1212)

UI_PATH = ROOT / "app" / "v15" / "ui.py"
ui = UI_PATH.read_text(encoding="utf-8")
if "_legenda_inline" not in ui:
    ui = ui.rstrip() + "\n\n\nfrom app.v15.theme import TEMA\n\n" + LEGENDA_INLINE
    UI_PATH.write_text(ui, encoding="utf-8")

helpers_body = (
    slice_lines(248, 295)
    + slice_lines(301, 334)
    + slice_lines(473, 531)
    + slice_lines(680, 739)
    + slice_lines(773, 997)
    + slice_lines(1461, 1586)
)
(ROOT / "app" / "v15" / "page_helpers.py").write_text(
    HELPERS_HEADER + helpers_body,
    encoding="utf-8",
)
print("Extracted app/v15/page_helpers.py and updated ui.py")
