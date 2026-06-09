"""Gera app/v15/charts/detail.py a partir do monolito v15."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboard_enem_v15.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
CHARTS = ROOT / "app" / "v15" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)


def slice_lines(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


DETAIL_HEADER = '''\
"""Gráficos das abas detalhe — painel ENEM v15."""

from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from viz.chart_layout import (
    CHART_H_BOX_WIDE,
    CHART_H_EVOLUCAO,
    CHART_H_HIST,
    CHART_H_HIST_GRID,
    CHART_H_HIST_ROW,
    CHART_H_PARTICIPACAO,
    CHART_H_RANKING,
    CHART_H_STANDARD,
)

from app.v15.boxplots import (
    _add_box_series,
    _finalizar_boxplot,
    _finalizar_grafico,
)
from app.v15.formatting import fmt_delta, fmt_float, fmt_int, fmt_pct
from app.v15.hub_charts import _classificar_cor_media_referencia
from app.v15.plotly_theme import aplicar_tema
from app.v15.theme import *
from dados_agregados_loader import (
    media_nacional_ponderada,
    medias_br_serie_por_area,
    medias_referencia_por_ano,
    stats_box_quantis,
)


'''

detail_body = (
    slice_lines(993, 1072)
    + slice_lines(1271, 1456)
    + slice_lines(1477, 1791)
    + slice_lines(2043, 2430)
    + slice_lines(2446, 3324)
)
(CHARTS / "detail.py").write_text(DETAIL_HEADER + detail_body, encoding="utf-8")
print("Extracted app/v15/charts/detail.py")
