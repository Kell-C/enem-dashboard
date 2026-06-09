"""Páginas Streamlit do painel ENEM v15."""

from app.v15.pages.sumario_executivo import aba_sumario_executivo
from app.v15.pages.panorama_participacao import aba_panorama_participacao
from app.v15.pages.desempenho import aba_desempenho
from app.v15.pages.escolas_2024 import aba_escolas_2024
from app.v15.pages.territorial import aba_territorial
from app.v15.pages.municipios import aba_municipios
from app.v15.pages.contexto_nacional import aba_contexto_nacional
from app.v15.pages.territorio_drilldown import aba_territorio_drilldown
from app.v15.pages.metodologia import aba_metodologia
from app.v15.pages.gestao_hub import aba_gestao_hub

from app.v15.pages.metodologia import _render_metodologia_detalhe

__all__ = [
    "aba_sumario_executivo",
    "aba_panorama_participacao",
    "aba_desempenho",
    "aba_escolas_2024",
    "aba_territorial",
    "aba_municipios",
    "aba_contexto_nacional",
    "aba_territorio_drilldown",
    "aba_metodologia",
    "aba_gestao_hub",
    "_render_metodologia_detalhe",
]
