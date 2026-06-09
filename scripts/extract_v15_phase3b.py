"""Gera app/v15/boxplots.py e app/v15/hub_charts.py a partir do monolito v15."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboard_enem_v15.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    """Intervalo 1-based inclusive."""
    return "".join(lines[start - 1 : end])


BOXPLOTS_HEADER = '''\
"""Boxplots, hover e finalização de gráficos de detalhe — painel ENEM v15."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from viz.chart_layout import (
    CHART_H_BOX_WIDE,
    CHART_H_STANDARD,
    hover_padrao,
    legenda_inferior,
    margem_detalhe,
    texto_hover_box,
)

from app.v15.theme import (  # noqa: F401
    AZUL_ESCURO,
    AZUL_PRINCIPAL,
    FONT_AXIS,
    FONT_CHART,
    FONT_HOVER,
    FONT_HUB_DATA,
    FONT_LEGEND,
    TEMA,
)
from app.v15.plotly_theme import aplicar_tema


'''

HUB_HEADER = '''\
"""Eixos hub, legendas e fechamento de figuras hub — painel ENEM v15."""

from __future__ import annotations

import html as _html

import pandas as pd
import plotly.graph_objects as go

from viz.chart_layout import CHART_H_HUB

from app.v15.theme import (  # noqa: F401
    AREAS,
    AZUL_PRINCIPAL,
    COLS_NOTAS,
    CORES_AREAS,
    CORES_DEP,
    COR_ATENCAO,
    COR_BAR_NEUTRA,
    COR_BRASIL,
    COR_CRITICO,
    COR_POSITIVO,
    FONT_HUB_AXIS,
    FONT_HUB_LEGEND,
    FONT_HUB_LEGEND_WIDE,
    HUB_CHART_MARGIN,
    LARANJA_DESTAQUE,
    TEMA,
)


'''

box_body = slice_lines(1454, 1874) + "\n\n" + slice_lines(2064, 2070)
(ROOT / "app" / "v15" / "boxplots.py").write_text(
    BOXPLOTS_HEADER + box_body, encoding="utf-8"
)

hub_body = (
    slice_lines(2073, 2179)
    + "\n\n"
    + slice_lines(2868, 2882)
    + "\n\n"
    + slice_lines(2885, 3562)
)
(ROOT / "app" / "v15" / "hub_charts.py").write_text(
    HUB_HEADER + hub_body, encoding="utf-8"
)

print("Extracted app/v15/boxplots.py and app/v15/hub_charts.py")
