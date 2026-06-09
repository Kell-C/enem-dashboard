"""Regenera módulos da fase 5b corrompidos a partir do monolito em git HEAD."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".tmp_monolith_head.py"
if not SRC.exists():
    text = subprocess.check_output(
        ["git", "show", "HEAD:dashboard_enem_v15.py"],
        text=True,
        encoding="utf-8",
    )
    SRC.write_text(text, encoding="utf-8")

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


PARTICIPATION_HEADER = '''\
"""Taxas de participação em tabelas agregadas — painel ENEM v15."""

from __future__ import annotations

import pandas as pd

from app.v15.formatting import _pct_taxa


'''

CONCLUINTES_HEADER = '''\
"""Carregamento de concluintes por CRE — painel ENEM v15."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from app.v15.paths import ARQUIVO_CONCLUINTES, ARQUIVO_CRES


'''

MS_ENRICH_HEADER = '''\
"""Enriquecimento MS com CRE e município — painel ENEM v15."""

from __future__ import annotations

from typing import Optional

import os

import pandas as pd
import streamlit as st

from cres_loader import (
    carregar_cres_escolas,
    carregar_mapa_municipio_cre as _carregar_mapa_municipio_cre,
    construir_mapa_cre_completo,
)
from app.v15.paths import ARQUIVO_CRES


'''

TERRITORY_HEADER = '''\
"""Helpers territoriais (CRE, município, estado) — painel ENEM v15."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cres_loader import nome_cre_curto
from dados_agregados_loader import (
    filtrar_participacao_cre,
    filtrar_participacao_municipio,
    reconstruir_ms_enriquecido,
)

from app.v15.components import titulo_secao
from app.v15.concluintes_data import carregar_concluintes_cre
from app.v15.formatting import fmt_float
from app.v15.ms_enrich import (
    aplicar_cre_por_municipio,
    carregar_cres,
    carregar_mapa_municipio_cre,
    enriquecer_ms,
)
from app.v15.participation import _enriquecer_participacao_taxas
from app.v15.theme import ANOS_DISPONIVEIS


'''

HUB_HEADER = '''\
"""Gráficos e layout do hub denso — painel ENEM v15."""

from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from viz.chart_layout import CHART_H_HUB, CHART_H_HUB_DELTA_ROW, CHART_H_HUB_EVOL, CHART_H_HUB_RANK

from app.v15.boxplots import _anotacao_hub, _aplicar_hover_hub
from app.v15.charts_render import _chart_hub
from app.v15.constants import HUB_BUILD_ID
from app.v15.formatting import fmt_delta, fmt_float, fmt_int, fmt_pct
from app.v15.hub_charts import (
    _aplicar_eixos_hub,
    _aplicar_legenda_interna_combo_ms,
    _altura_hub_ranking,
    _classificar_cor_media_referencia,
    _cor_posicao_terco,
    _cores_ranking_presentes,
    _fechar_fig_hub,
    _legenda_fig,
    _margem_hub,
    _texto_posicao_barra,
)
from app.v15.plotly_theme import _legenda_padrao, aplicar_tema
from app.v15.territory_data import _participacao_cre_tabela
from app.v15.theme import *
from app.v15.ui import _render_html


'''

(ROOT / "app" / "v15" / "participation.py").write_text(
    PARTICIPATION_HEADER + slice_lines(5729, 5743),
    encoding="utf-8",
)
(ROOT / "app" / "v15" / "concluintes_data.py").write_text(
    CONCLUINTES_HEADER + slice_lines(281, 293),
    encoding="utf-8",
)
(ROOT / "app" / "v15" / "ms_enrich.py").write_text(
    MS_ENRICH_HEADER + slice_lines(2059, 2177),
    encoding="utf-8",
)

territory_body = slice_lines(9228, 9470) + slice_lines(12040, 12082)
(ROOT / "app" / "v15" / "territory_data.py").write_text(
    TERRITORY_HEADER + territory_body,
    encoding="utf-8",
)

HUB_RANGES = [
    (3636, 3717),
    (5182, 5493),
    (5955, 6881),
    (7079, 7257),
]
hub_body = "".join(slice_lines(a, b) for a, b in HUB_RANGES)
CHARTS = ROOT / "app" / "v15" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)
(CHARTS / "hub.py").write_text(HUB_HEADER + hub_body, encoding="utf-8")

print("Recovered phase 5b modules from git HEAD monolith")
