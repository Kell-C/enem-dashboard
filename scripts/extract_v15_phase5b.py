"""Gera módulos da fase 5b a partir do monolito v15."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboard_enem_v15.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
CHARTS = ROOT / "app" / "v15" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)


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
    PARTICIPATION_HEADER
    + slice_lines(2937, 2951),
    encoding="utf-8",
)
(ROOT / "app" / "v15" / "concluintes_data.py").write_text(
    CONCLUINTES_HEADER + slice_lines(282, 294),
    encoding="utf-8",
)
(ROOT / "app" / "v15" / "ms_enrich.py").write_text(
    MS_ENRICH_HEADER + slice_lines(779, 896),
    encoding="utf-8",
)

(ROOT / "app" / "v15" / "territory_data.py").write_text(
    TERRITORY_HEADER + slice_lines(5110, 5395),
    encoding="utf-8",
)

hub_body = slice_lines(1594, 1667) + slice_lines(2390, 2701) + slice_lines(3163, 4307)
(CHARTS / "hub.py").write_text(HUB_HEADER + hub_body, encoding="utf-8")
(CHARTS / "__init__.py").write_text(
    '"""Gráficos Plotly do painel v15."""\n',
    encoding="utf-8",
)

hub_charts_path = ROOT / "app" / "v15" / "hub_charts.py"
hub_charts = hub_charts_path.read_text(encoding="utf-8")
if "_cor_posicao_terco" not in hub_charts:
    cor_fn = slice_lines(677, 683)
    insert_at = hub_charts.find("def _aplicar_eixos_hub(")
    if insert_at == -1:
        raise SystemExit("_aplicar_eixos_hub not in hub_charts")
    hub_charts = hub_charts[:insert_at] + cor_fn + "\n\n" + hub_charts[insert_at:]
    hub_charts_path.write_text(hub_charts, encoding="utf-8")

print("Extracted phase 5b modules")
