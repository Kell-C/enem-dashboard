"""Gera módulos da fase 5 a partir do monolito v15."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboard_enem_v15.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


COMPONENTS_HEADER = '''\
"""Componentes de UI reutilizáveis — painel ENEM v15."""

from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import streamlit as st

from app.v15.formatting import fmt_int, fmt_float, fmt_pct
from app.v15.theme import AREAS, AREAS_COMPLETO
from app.v15.ui import _render_html


'''

CLASSIFIERS_HEADER = '''\
"""Classificadores semáforo (status KPI) — painel ENEM v15."""

from __future__ import annotations

from typing import Optional

import numpy as np


'''

CHARTS_RENDER_HEADER = '''\
"""Renderização Plotly no Streamlit — painel ENEM v15."""

from __future__ import annotations

import streamlit as st

from app.v15.boxplots import _preparar_hover_fig
from app.v15.constants import HUB_BUILD_ID
from viz.chart_layout import PLOTLY_HUB_CONFIG

_CK = [0]


'''

(ROOT / "app" / "v15" / "components.py").write_text(
    COMPONENTS_HEADER + slice_lines(1406, 1474), encoding="utf-8"
)
(ROOT / "app" / "v15" / "classifiers.py").write_text(
    CLASSIFIERS_HEADER + slice_lines(2390, 2416), encoding="utf-8"
)
(ROOT / "app" / "v15" / "charts_render.py").write_text(
    CHARTS_RENDER_HEADER + slice_lines(874, 898), encoding="utf-8"
)
print("Extracted components, classifiers, charts_render")
