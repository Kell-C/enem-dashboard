"""CSS institucional do painel ENEM v15."""

import streamlit as st

from app.v15.theme import (  # noqa: F401 — used in f-string CSS below
    AZUL_CLARO,
    AZUL_ESCURO,
    AZUL_PRINCIPAL,
    AZUL_SED,
    COR_ATENCAO,
    COR_CRITICO,
    COR_NEUTRO,
    COR_POSITIVO,
    COR_TEXTO_DENTRO_BARRA,
    DOURADO_MS,
    LARANJA_DESTAQUE,
    TEMA,
    VERDE_MS,
)


def inject_v15_filter_styles() -> None:
    st.markdown(
"""
<style>
/* Container do selectbox */
div[data-testid="stSelectbox"] {
    background: linear-gradient(135deg, rgba(27, 127, 214, 0.08), rgba(27, 127, 214, 0.03));
    border: 1px solid rgba(10, 77, 140, 0.18);
    border-radius: 10px;
    padding: 8px 12px 4px 12px;
    margin-bottom: 12px;
}
/* Label do selectbox */
div[data-testid="stSelectbox"] label {
    color: #0A4D8C !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600 !important;
}
/* Container do multiselect */
div[data-testid="stMultiSelect"] {
    background: linear-gradient(135deg, rgba(27, 127, 214, 0.08), rgba(27, 127, 214, 0.03));
    border: 1px solid rgba(10, 77, 140, 0.18);
    border-radius: 10px;
    padding: 8px 12px 4px 12px;
    margin-bottom: 12px;
}
/* Label do multiselect */
div[data-testid="stMultiSelect"] label {
    color: #0A4D8C !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600 !important;
}
/* Container do slider */
div[data-testid="stSlider"] {
    background: linear-gradient(135deg, rgba(27, 127, 214, 0.08), rgba(27, 127, 214, 0.03));
    border: 1px solid rgba(10, 77, 140, 0.18);
    border-radius: 10px;
    padding: 8px 12px 4px 12px;
    margin-bottom: 12px;
}
/* Label do slider */
div[data-testid="stSlider"] label {
    color: #0A4D8C !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_v15_styles() -> None:
    css = f"""
<style>
  /* Fontes institucionais: Plus Jakarta Sans (display) + Source Sans 3 (corpo) */
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap');

  :root {{
    --ms-navy: {AZUL_ESCURO};
    --ms-sed: {AZUL_SED};
    --ms-azul-2: {AZUL_PRINCIPAL};
    --ms-azul-3: {AZUL_CLARO};
    --ms-verde: {VERDE_MS};
    --ms-laranja: {LARANJA_DESTAQUE};
    --ms-dourado: {DOURADO_MS};
    --ms-surface: {TEMA['bg_card']};
    --ms-tint: {TEMA['insight_bg']};
    --texto:     {TEMA['texto']};
    --texto-sec: {TEMA['texto_secundario']};
    --texto-mut: {TEMA['texto_muted']};
    --bg-app:    {TEMA['bg_app']};
    --bg-card:   {TEMA['bg_card']};
    --borda:     {TEMA['borda']};
  }}

  html, body, [class*="css"], .stApp, .stMarkdown, .stMarkdown p, .stMarkdown li {{
    font-family: 'Source Sans 3', system-ui, -apple-system, Segoe UI, sans-serif;
    color: {TEMA['texto']} !important;
  }}

  h1, h2, h3, h4, h5, h6,
  .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {{
    font-family: 'Plus Jakarta Sans', 'Source Sans 3', sans-serif;
    color: {TEMA['texto']} !important;
    letter-spacing: -0.01em;
    font-weight: 700;
  }}

  /* Corpo de texto: mínimo 16px e entrelinha confortável (legibilidade/AA) */
  .stMarkdown p, .stMarkdown li {{
    font-size: 1rem;
    line-height: 1.55;
  }}

  .stApp {{
    background: {TEMA['bg_app']} !important;
    color: {TEMA['texto']} !important;
    margin-top: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    height: auto !important;
    min-height: 100vh;
  }}
  /* Faixa decorativa / reserva de topo do Streamlit */
  [data-testid="stDecoration"],
  [data-testid="stStatusWidget"] {{
      display: none !important;
      height: 0 !important;
      min-height: 0 !important;
  }}
  [data-testid="stMain"] {{
      padding-top: 1 !important;
      margin-top: 1 !important;
  }}
  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"] {{
      display: none !important;
  }}
  .main .block-container {{
      padding: 0 0 0.25rem 0 !important;
      max-width: 100% !important;
  }}
  .appview-container .main .block-container {{
      padding-top: 0 !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
  }}
  /* Streamlit reserva padding-top em section.main para o header fixo — zerar */
  section.main,
  .stApp [data-testid="stAppViewContainer"] > section.main {{
      padding-top: 0 !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
      margin-top: 0 !important;
  }}
  .stApp [data-testid="stAppViewContainer"] {{
      padding-top: 0 !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
      margin-top: 0 !important;
      overflow-x: hidden !important;
      overflow-y: auto !important;
      height: auto !important;
      min-height: 100vh;
  }}
  .stApp [data-testid="stAppViewContainer"] > .main {{
      padding-top: 0 !important;
      overflow: visible !important;
      height: auto !important;
      min-height: 100vh;
  }}
  section.main {{
      overflow: visible !important;
      height: auto !important;
  }}
  section.main > div {{
      padding-left: 0 !important;
      padding-right: 0 !important;
      padding-top: 0 !important;
      margin-top: 0 !important;
  }}
  [data-testid="stMainBlockContainer"] {{
      padding-top: 0 !important;
      padding-left: 0.35rem !important;
      padding-right: 0.35rem !important;
      padding-bottom: 2.5rem !important;
      max-width: 100% !important;
      margin-top: 0 !important;
      overflow: visible !important;
      height: auto !important;
  }}
  [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] {{
      gap: 0.2rem !important;
      padding-top: 0 !important;
      margin-top: 0 !important;
  }}
  [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] > div {{
      padding-top: 0 !important;
      margin-top: 0 !important;
  }}
  /* Header nativo: colapsar altura; menu permanece clicável no canto */
  header[data-testid="stHeader"] {{
      background: transparent !important;
      height: 0 !important;
      min-height: 0 !important;
      max-height: 0 !important;
      overflow: visible;
      visibility: hidden;
      pointer-events: none;
      border: none !important;
      box-shadow: none !important;
  }}
  header[data-testid="stHeader"] [data-testid="stToolbar"],
  header[data-testid="stHeader"] [data-testid="stToolbarActions"] {{
      visibility: visible;
      pointer-events: auto;
  }}
  [data-testid="stToolbar"] {{
      position: fixed;
      top: 0.35rem;
      right: 0.5rem;
      z-index: 999;
  }}
  [data-testid="stVerticalBlockBorderWrapper"] {{
      gap: 0.1rem !important;
      padding-top: 0 !important;
  }}
  [data-testid="stElementContainer"] {{
      margin: 0 !important;
  }}
  div[data-testid="stMarkdownContainer"]:first-child {{
      margin-top: 0 !important;
      padding-top: 0 !important;
  }}
  [data-testid="column"] {{
      padding: 0 2px !important;
      overflow: visible !important;
  }}
  [data-testid="stHorizontalBlock"] {{
      overflow: visible !important;
      gap: 0.35rem !important;
  }}
  [data-testid="stVerticalBlock"] > div:first-child {{
      gap: 0.15rem;
  }}
  [data-testid="stVerticalBlock"] > div:first-child > div:first-child {{
      margin-top: 0 !important;
      padding-top: 0 !important;
  }}

  /* ── Cabeçalho principal — colado ao topo, marca em destaque ── */
  .cab-claro {{
      background: linear-gradient(135deg, {TEMA['bg_card']} 0%, #F1F5F9 100%);
      border: 1px solid {TEMA['borda']};
      border-top: none;
      border-left: none;
      border-right: none;
      border-radius: 0 0 12px 12px;
      padding: 8px 14px 9px 14px;
      margin: 0 -0.35rem 4px -0.35rem;
      box-shadow: 0 3px 14px rgba(15, 23, 42, 0.08);
      border-bottom: 3px solid {DOURADO_MS};
      position: relative;
      z-index: 2;
  }}
  .cab-claro::before {{
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 6px;
      background: linear-gradient(180deg, {AZUL_SED} 0%, {AZUL_PRINCIPAL} 100%);
      border-radius: 0 2px 2px 0;
  }}
  .cab-claro--com-kpis {{
      padding-right: 2.5rem;
  }}
  .cab-claro-row {{
      display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
      padding-left: 10px;
  }}
  .cab-claro--com-kpis .cab-claro-row {{
      flex-wrap: nowrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding-left: 10px;
      padding-right: 4px;
      min-height: 62px;
  }}
  .cab-claro-brand {{
      display: flex;
      align-items: center;
      gap: 16px;
      flex: 0 0 auto;
      min-width: 0;
      max-width: 42%;
  }}
  .cab-claro--com-kpis .cab-claro-brand {{
      max-width: min(360px, 34vw);
      flex-shrink: 0;
  }}
  .cab-claro-kpis {{
      display: flex;
      flex-wrap: wrap;
      align-items: stretch;
      justify-content: flex-end;
      gap: 6px;
      flex: 1 1 auto;
      min-width: 0;
  }}
  .cab-claro-kpis .kpi-claro {{
      flex: 0 0 auto;
      width: max-content;
      min-width: max-content;
      max-width: none;
      padding: 4px 9px 3px 9px;
      border-radius: 6px;
  }}
  .cab-claro-kpis .kpi-claro-val {{
      font-size: 1.05rem;
      line-height: 1.05;
  }}
  .cab-claro-kpis .kpi-claro-lbl {{
      font-size: 0.6875rem;
      letter-spacing: 0.05em;
      white-space: normal;
      line-height: 1.2;
  }}
  .cab-claro-kpis .kpi-claro-sub {{
      font-size: 0.6875rem;
      max-width: none;
      overflow: visible;
      text-overflow: clip;
      white-space: normal;
      line-height: 1.3;
  }}
  .cab-claro-kpis .kpi-delta-br {{
      min-width: max-content;
  }}
  .cab-claro-kpis .kpi-funil-inline {{
      min-width: 248px;
      max-width: none;
      flex: 1 1 248px;
      padding: 4px 9px 3px 9px;
  }}
  .cab-claro-kpis .kpi-funil-inline .fk-line {{
      grid-template-columns: minmax(7.25rem, auto) 4.2rem minmax(52px, 1fr);
      gap: 4px;
  }}
  .cab-claro-kpis .kpi-funil-inline .fk-l {{
      font-size: 0.625rem;
      white-space: nowrap;
  }}
  @media (max-width: 1100px) {{
      .cab-claro--com-kpis .cab-claro-row {{
          flex-wrap: wrap;
      }}
      .cab-claro-brand, .cab-claro--com-kpis .cab-claro-brand {{
          max-width: 100%;
          flex: 1 1 100%;
      }}
      .cab-claro-kpis {{
          justify-content: flex-start;
          flex: 1 1 100%;
      }}
  }}
  .cab-claro-logo {{
      height: 64px; width: auto; max-width: min(300px, 38vw);
      object-fit: contain; flex-shrink: 0;
      filter: drop-shadow(0 1px 2px rgba(15, 23, 42, 0.06));
  }}
  .cab-claro-brand .cab-claro-text {{
      flex: 1 1 auto;
      min-width: 0;
  }}
  .cab-claro-text h1 {{
      margin: 0; padding: 0;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 1.55rem; font-weight: 800;
      color: {AZUL_ESCURO} !important;
      letter-spacing: -0.03em; line-height: 1.1;
  }}
  .cab-claro-text p {{
      margin: 4px 0 0 0; padding: 0;
      font-size: 0.9rem; line-height: 1.35;
      color: {TEMA['texto_secundario']} !important;
      font-weight: 600;
  }}
  .cab-claro--com-kpis .cab-claro-logo {{
      height: 58px;
      max-width: min(280px, 32vw);
  }}
  .cab-claro--com-kpis .cab-claro-text h1 {{
      font-size: 1.42rem;
      letter-spacing: -0.028em;
  }}
  .cab-claro--com-kpis .cab-claro-text p {{
      font-size: 0.84rem;
      margin-top: 3px;
      font-weight: 600;
  }}

  /* População de referência — faixa compacta abaixo do cabeçalho */
  .ref-pop-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 5px 10px;
      padding: 7px 12px 8px 14px;
      margin: 14px 0 14px 0;
      background: linear-gradient(135deg, #F8FAFC 0%, {TEMA['insight_bg']} 100%);
      border: 1px solid {TEMA['borda']};
      border-left: 4px solid {AZUL_SED};
      border-radius: 8px;
      font-size: 0.875rem;
      line-height: 1.5;
      color: {TEMA['texto_secundario']} !important;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }}
  .ref-pop-bar .ref-pop-tag {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-weight: 800;
      font-size: 0.8125rem;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: {AZUL_ESCURO} !important;
      white-space: nowrap;
      background: rgba(0, 63, 127, 0.08);
      padding: 2px 8px;
      border-radius: 4px;
  }}
  .ref-pop-bar .ref-pop-item {{
      color: {TEMA['texto']} !important;
      font-weight: 500;
  }}
  .ref-pop-bar .ref-pop-item strong {{
      color: {AZUL_ESCURO} !important;
      font-weight: 700;
  }}
  .ref-pop-bar .ref-pop-sep {{
      color: {TEMA['texto_muted']} !important;
      user-select: none;
  }}
  .ref-pop-bar code {{
      font-size: 0.75rem;
      background: rgba(46, 173, 110, 0.1);
      color: {COR_TEXTO_DENTRO_BARRA} !important;
      padding: 0 4px;
      border-radius: 3px;
  }}

  /* KPIs — largura conforme conteúdo */
  .kpi-strip-claro {{
      display: flex;
      flex-wrap: wrap;
      align-items: stretch;
      gap: 4px;
      margin-bottom: 3px;
  }}
  .kpi-strip-claro .kpi-claro {{
      flex: 0 0 auto;
      width: max-content;
      max-width: 100%;
  }}
  .kpi-strip-tight .kpi-claro {{
      padding: 4px 8px 3px 8px;
      border-radius: 6px;
  }}
  .kpi-funil-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: stretch;
      gap: 5px;
      margin-bottom: 4px;
  }}
  .kpi-funil-row .kpi-claro {{
      flex: 0 0 auto;
      width: max-content;
  }}
  .kpi-funil-inline {{
      min-width: 248px;
      max-width: none;
      border-top-color: {AZUL_PRINCIPAL};
  }}
  .kpi-funil-inline .fk-lines {{
      margin-top: 2px;
      display: flex;
      flex-direction: column;
      gap: 2px;
  }}
  .kpi-funil-inline .fk-line {{
      display: grid;
      grid-template-columns: minmax(7.25rem, auto) 4.2rem minmax(52px, 1fr);
      align-items: center;
      gap: 4px;
      line-height: 1;
  }}
  .kpi-funil-inline .fk-l {{
      font-size: 0.6875rem;
      font-weight: 600;
      color: {TEMA['texto_secundario']} !important;
      white-space: nowrap;
  }}
  .kpi-funil-inline .fk-n {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 0.75rem;
      font-weight: 800;
      color: {AZUL_ESCURO} !important;
      text-align: right;
      font-variant-numeric: tabular-nums;
  }}
  .kpi-funil-inline .fk-track {{
      position: relative;
      height: 12px;
      background: {TEMA['bg_subtle']};
      border-radius: 2px;
      overflow: hidden;
  }}
  .kpi-funil-inline .fk-fill {{
      position: absolute;
      left: 0; top: 0; bottom: 0;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding-right: 3px;
      border-radius: 2px;
      min-width: 2px;
  }}
  .kpi-funil-inline .fk-fill.azul {{ background: {AZUL_SED}; }}
  .kpi-funil-inline .fk-fill.laranja {{ background: {LARANJA_DESTAQUE}; }}
  .kpi-funil-inline .fk-fill.verde {{ background: {VERDE_MS}; }}
  .kpi-funil-inline .fk-pct {{
      font-size: 0.6875rem;
      font-weight: 700;
      color: #FFFFFF !important;
      line-height: 1;
      white-space: nowrap;
  }}
  .kpi-funil-inline .fk-pct-out {{
      position: absolute;
      right: 3px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 0.6875rem;
      font-weight: 700;
      color: {TEMA['texto_secundario']} !important;
  }}
  .hub-col-graficos {{
      display: flex;
      flex-direction: column;
      gap: 4px;
  }}
  .funil-estreito.widget-card .widget-head {{
      font-size: 0.5rem;
      padding: 4px 6px;
      letter-spacing: 0.05em;
  }}
  .funil-estreito .widget-body {{
      padding: 4px 6px 5px 6px;
  }}
  .funil-estreito .funil-v-row {{
      margin-bottom: 3px;
  }}
  .funil-estreito .fv-top {{
      gap: 4px;
  }}
  .funil-estreito .fv-lbl {{
      font-size: 0.58rem !important;
      line-height: 1.15;
  }}
  .funil-estreito .fv-val {{
      font-size: 0.78rem !important;
  }}
  .funil-estreito .fv-tx {{
      font-size: 0.56rem !important;
      margin: 0 0 2px 0;
  }}
  .funil-estreito .fv-bar {{
      height: 4px;
  }}
  .kpi-claro {{
      background: {TEMA['bg_card']};
      border: 1px solid {TEMA['borda']};
      border-radius: 6px;
      padding: 5px 10px 4px 10px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
      border-top: 2px solid {AZUL_SED};
  }}
  .kpi-claro-lbl {{
      display: block; font-size: 0.75rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.06em;
      color: {TEMA['texto_muted']} !important;
      white-space: nowrap;
  }}
  .kpi-claro-val {{
      display: block; margin-top: 1px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 1.22rem; font-weight: 800;
      color: {AZUL_ESCURO} !important;
      letter-spacing: -0.03em; line-height: 1.05;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
  }}
  .kpi-claro-sub {{
      display: block; margin-top: 1px;
      font-size: 0.8125rem;
      color: {TEMA['texto_secundario']} !important;
      white-space: nowrap;
  }}
  .kpi-claro.positivo {{ border-top-color: {COR_POSITIVO}; }}
  .kpi-claro.positivo .kpi-claro-val {{ color: {COR_POSITIVO} !important; }}
  .kpi-claro.atencao  {{ border-top-color: {COR_ATENCAO}; }}
  .kpi-claro.atencao .kpi-claro-val  {{ color: {COR_ATENCAO} !important; }}
  .kpi-claro.critico  {{ border-top-color: {COR_CRITICO}; }}
  .kpi-claro.critico .kpi-claro-val  {{ color: {COR_CRITICO} !important; }}

  /* Widget card — faixa cinza no topo (Opsview) */
  .widget-card {{
      background: {TEMA['bg_card']};
      border: 1px solid {TEMA['borda']};
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      height: 100%;
  }}
  .widget-head {{
      background: linear-gradient(135deg, {AZUL_ESCURO} 0%, {AZUL_PRINCIPAL} 100%);
      padding: 5px 8px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 0.72rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.03em;
      color: #FFFFFF !important;
      border-bottom: 2px solid {DOURADO_MS};
      line-height: 1.35;
      white-space: normal;
      word-break: break-word;
      overflow: visible;
  }}
  .widget-body {{ padding: 6px 8px 8px 8px; }}
  .chart-legenda-delta.hub-mini {{
      margin: 0; padding: 2px 6px 4px 6px;
      font-size: 0.75rem; line-height: 1.3;
      color: {TEMA['texto_secundario']} !important;
      border-top: none;
  }}
  .widget-chart-zone {{
      margin-bottom: 4px;
      margin-top: 0;
      background: {TEMA['bg_card']};
      border: 1px solid {TEMA['borda']};
      border-radius: 6px;
      overflow: visible;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      position: relative;
      z-index: 1;
  }}
  .widget-chart-body {{
      overflow: visible;
      border-radius: 0 0 6px 6px;
  }}
  .widget-chart-nota {{
      padding: 8px 12px 10px;
      font-family: 'Source Sans 3', sans-serif;
      font-size: 0.82rem;
      line-height: 1.5;
      color: {TEMA['texto_secundario']} !important;
      text-align: center;
      border-top: 1px solid {TEMA['borda']};
      background: {TEMA['bg_subtle']};
  }}
  .hub-legenda-linha .leg-traces,
  .widget-chart-nota .leg-traces {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 16px;
      justify-content: center;
      align-items: center;
      margin-bottom: 2px;
  }}
  .hub-legenda-linha .leg-trace,
  .widget-chart-nota .leg-trace {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      white-space: nowrap;
      font-size: 0.8rem;
      font-weight: 500;
  }}
  .widget-chart-nota .leg-nota {{
      margin-top: 6px;
      font-size: 0.72rem;
      color: {TEMA['texto_muted']} !important;
  }}
  .widget-chart-zone [data-testid="stPlotlyChart"] iframe {{
      pointer-events: auto !important;
  }}
  div[data-testid="stMarkdownContainer"]:has(.ref-pop-bar) {{
      margin-bottom: 0 !important;
      padding-bottom: 0 !important;
  }}
  div[data-testid="stMarkdownContainer"]:has(.ref-pop-bar) + div {{
      margin-top: 0 !important;
      padding-top: 0 !important;
  }}
  .hub-panorama-grid {{
      padding-top: 0 !important;
      margin-top: 0 !important;
      padding-bottom: 48px;
      overflow: visible;
  }}
  .hub-panorama-grid [data-testid="stHorizontalBlock"] {{
      align-items: flex-start !important;
      overflow: visible !important;
      height: auto !important;
      min-height: 0 !important;
  }}
  .hub-panorama-grid [data-testid="column"] {{
      overflow: visible !important;
      height: auto !important;
      align-self: flex-start !important;
  }}
  .hub-panorama-grid [data-testid="stVerticalBlock"] {{
      overflow: visible !important;
      height: auto !important;
  }}
  .hub-panorama-grid [data-testid="stPlotlyChart"] {{
      overflow: visible !important;
  }}
  .widget-chart-zone [data-testid="stPlotlyChart"],
  .widget-chart-zone [data-testid="stPlotlyChart"] > div,
  .widget-chart-zone .js-plotly-plot,
  .widget-chart-zone .plotly {{
      overflow: visible !important;
  }}
  .widget-chart-zone [data-testid="stPlotlyChart"] {{
      border-radius: 0 !important;
      border: none !important;
      border-top: none !important;
      margin-top: 0 !important;
      margin-bottom: 0 !important;
      padding: 0 !important;
      box-shadow: none !important;
  }}
  .stAppDeployButton, [data-testid="stAppDeployButton"] {{
      display: none !important;
  }}
  .widget-chart-zone .widget-head {{
      border-radius: 8px 8px 0 0;
  }}
  .hub-delta-anos-grid {{
      padding: 0 4px 2px 4px;
  }}
  .hub-delta-anos-grid [data-testid="stPlotlyChart"] {{
      margin: 0 !important;
      padding: 0 !important;
      min-height: 0 !important;
  }}

  /* Funil vertical compacto */
  .funil-v-row {{ margin-bottom: 6px; }}
  .funil-v-row:last-child {{ margin-bottom: 0; }}
  .fv-top {{
      display: flex; justify-content: space-between; align-items: baseline;
      gap: 8px;
  }}
  .fv-lbl {{
      font-size: 0.72rem; font-weight: 600;
      color: {TEMA['texto_secundario']} !important;
  }}
  .fv-val {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 0.98rem; font-weight: 800;
      color: {AZUL_ESCURO} !important;
      font-variant-numeric: tabular-nums;
  }}

  /* Ranking UF compacto (Opsview) */
  .rank-panel {{ margin-top: 8px; }}
  .rank-scroll {{
      max-height: 228px; overflow-y: auto;
      margin: 0 -2px; padding-right: 2px;
  }}
  .rank-tbl {{
      width: 100%; border-collapse: collapse;
      font-size: 0.72rem; line-height: 1.3;
  }}
  .rank-tbl th {{
      position: sticky; top: 0; z-index: 1;
      background: {TEMA['bg_subtle']};
      color: {TEMA['texto_secundario']} !important;
      font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.05em; font-size: 0.6rem;
      padding: 5px 6px; text-align: left;
      border-bottom: 1px solid {TEMA['borda']};
  }}
  .rank-tbl td {{
      padding: 4px 6px; border-bottom: 1px solid {TEMA['borda_sutil']};
      color: {TEMA['texto']} !important;
      vertical-align: middle;
  }}
  .rank-tbl tr.rank-ms td {{
      background: rgba(27, 127, 214, 0.12);
      font-weight: 700;
  }}
  .rank-tbl tr.rank-ms td.uf {{
      color: {AZUL_ESCURO} !important;
  }}
  .rank-tbl .pos {{
      width: 26px; color: {TEMA['texto_muted']} !important;
      font-variant-numeric: tabular-nums;
  }}
  .rank-tbl .uf {{ width: 30px; font-weight: 700; }}
  .rank-tbl .tx {{
      width: 42px; text-align: right;
      font-variant-numeric: tabular-nums; font-weight: 700;
  }}
  .rank-bar-cell {{ width: 38%; }}
  .rank-bar {{
      height: 6px; background: {TEMA['bg_subtle']};
      border-radius: 3px; overflow: hidden;
  }}
  .rank-bar > span {{
      display: block; height: 100%;
      background: {AZUL_SED}; border-radius: 3px;
  }}
  .rank-tbl tr.rank-ms .rank-bar > span {{ background: {AZUL_PRINCIPAL}; }}
  .rank-ms-badge {{
      display: inline-block; margin-top: 6px; padding: 4px 8px;
      background: {TEMA['bg_subtle']}; border-radius: 6px;
      font-size: 0.7rem; font-weight: 700;
      color: {AZUL_ESCURO} !important;
      border: 1px solid {TEMA['borda']};
  }}
  .fv-tx {{
      font-size: 0.68rem; font-weight: 700; margin-top: 2px;
  }}
  .fv-bar {{
      height: 4px; background: {TEMA['bg_subtle']};
      border-radius: 2px; margin-top: 4px; overflow: hidden;
  }}
  .fv-fill {{ height: 100%; border-radius: 2px; }}
  .fv-fill.azul {{ background: {AZUL_SED}; }}
  .fv-fill.laranja {{ background: {LARANJA_DESTAQUE}; }}
  .fv-fill.verde {{ background: {VERDE_MS}; }}
  .fv-tx.insc {{ color: {LARANJA_DESTAQUE} !important; }}
  .fv-tx.insc.atencao {{ color: {COR_ATENCAO} !important; }}
  .fv-tx.insc.critico {{ color: {COR_CRITICO} !important; }}
  .fv-tx.insc.positivo {{ color: {COR_POSITIVO} !important; }}
  .fv-tx.efet {{ color: {AZUL_PRINCIPAL} !important; }}
  .fv-tx.efet.atencao {{ color: {COR_ATENCAO} !important; }}
  .fv-tx.efet.critico {{ color: {COR_CRITICO} !important; }}
  .fv-tx.efet.positivo {{ color: {COR_POSITIVO} !important; }}

  /* Card shell unificado */
  .dash-card {{
      background: {TEMA['bg_card']};
      border: 1px solid {TEMA['borda']};
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  }}
  .hub-sep {{
      border: none; border-top: 1px solid {TEMA['borda']};
      margin: 8px 0 10px 0;
  }}
  .secao-head {{
      margin: 0 0 14px 0;
  }}
  .secao-eyebrow {{
      display: block;
      font-size: 0.68rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.11em;
      color: {TEMA['texto_muted']} !important;
      margin-bottom: 2px;
  }}
  .secao-nome {{
      display: block;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 1rem; font-weight: 700;
      color: {AZUL_ESCURO} !important;
      letter-spacing: -0.01em;
  }}

  /* Bloco de título de seção */
  .bloco-titulo {{
      border-left: 5px solid {AZUL_PRINCIPAL};
      padding: 10px 16px; margin: 24px 0 16px 0;
      background: {TEMA['bg_card']};
      border-radius: 0 10px 10px 0;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }}
  .bloco-titulo h3 {{
      color: {AZUL_PRINCIPAL} !important;
      margin: 0; font-weight: 700; font-size: 1.18rem;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .bloco-titulo p {{
      color: {TEMA['texto_secundario']} !important;
      margin: 5px 0 0 0; font-size: 0.95rem; line-height: 1.5;
  }}
  /* Cards KPI (demais abas) */
  .kpi-card {{
      position: relative; overflow: hidden;
      background: {TEMA['bg_card']};
      padding: 18px 18px 16px 18px; border-radius: 14px;
      border: 1px solid {TEMA['borda']};
      box-shadow: 0 2px 10px rgba(5, 59, 113, 0.05);
      height: 100%;
  }}
  .kpi-card::before {{
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: {AZUL_SED};
      border-radius: 14px 14px 0 0;
  }}
  .kpi-card .rotulo {{
      color: {TEMA['texto_secundario']} !important;
      font-size: 0.7rem; text-transform: uppercase;
      letter-spacing: 0.08em; font-weight: 700;
  }}
  .kpi-card .valor {{
      color: {AZUL_PRINCIPAL} !important;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 1.85rem; font-weight: 800;
      line-height: 1.15; margin-top: 6px;
      letter-spacing: -0.02em;
  }}
  .kpi-card .sub {{
      color: {TEMA['texto_muted']} !important;
      font-size: 0.8rem; margin-top: 4px;
  }}
  .kpi-card.positivo::before {{ background: linear-gradient(90deg, {COR_POSITIVO}, #3CB88A); }}
  .kpi-card.positivo .valor {{ color: {COR_POSITIVO} !important; }}
  .kpi-card.atencao::before  {{ background: linear-gradient(90deg, {COR_ATENCAO}, #F5B041); }}
  .kpi-card.atencao .valor {{ color: {COR_ATENCAO} !important; }}
  .kpi-card.critico::before  {{ background: linear-gradient(90deg, {COR_CRITICO}, #E85D4C); }}
  .kpi-card.critico .valor {{ color: {COR_CRITICO} !important; }}

  /* Boxes de achado */
  .achado {{
      padding: 14px 18px; border-radius: 10px;
      margin: 10px 0; font-size: 0.94rem;
      line-height: 1.45;
      color: {TEMA['texto']} !important;
      border-left: 5px solid;
      background: {TEMA['bg_card']};
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }}
  .achado .titulo {{ font-weight: 700; margin-bottom: 4px; font-size: 0.96rem; }}
  .achado .corpo  {{ color: {TEMA['texto']} !important; }}
  .achado-positivo {{ border-left-color: {COR_POSITIVO}; }}
  .achado-positivo .titulo {{ color: {COR_POSITIVO} !important; }}
  .achado-atencao  {{ border-left-color: {COR_ATENCAO}; }}
  .achado-atencao .titulo {{ color: {COR_ATENCAO} !important; }}
  .achado-critico  {{ border-left-color: {COR_CRITICO}; }}
  .achado-critico .titulo {{ color: {COR_CRITICO} !important; }}
  .achado-neutro   {{ border-left-color: {COR_NEUTRO}; }}
  .achado-neutro .titulo {{ color: {COR_NEUTRO} !important; }}

  /* Insight box */
  .insight {{
      border-left: 5px solid {AZUL_CLARO};
      background: {TEMA['insight_bg']};
      color: {TEMA['texto']} !important;
      padding: 12px 16px; border-radius: 8px;
      margin: 8px 0 16px 0; font-size: 0.94rem;
      line-height: 1.45;
  }}
  .insight strong {{ color: {AZUL_PRINCIPAL} !important; }}

  /* Faixa participação — funil em etapas */
  .faixa-populacao {{
      padding: 16px 18px 14px 18px;
      margin: 0 0 16px 0;
  }}
  .faixa-populacao.dash-card {{
      border-radius: 14px;
  }}
  .faixa-populacao .fp-steps {{
      display: flex; flex-wrap: wrap; align-items: stretch;
      gap: 6px; justify-content: space-between;
  }}
  .faixa-populacao .fp-step {{
      flex: 1 1 140px; min-width: 120px;
      background: {TEMA['bg_card']};
      border: 1px solid {TEMA['borda']};
      border-left-width: 3px;
      border-radius: 10px; padding: 14px 16px;
      text-align: left;
  }}
  .faixa-populacao .fp-step-conc {{ border-left-color: {AZUL_SED}; }}
  .faixa-populacao .fp-step-insc {{ border-left-color: {LARANJA_DESTAQUE}; }}
  .faixa-populacao .fp-step-efet {{ border-left-color: {VERDE_MS}; }}
  .faixa-populacao .fp-step-val {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-weight: 800; font-size: 1.42rem; line-height: 1.1;
      letter-spacing: -0.02em;
  }}
  .faixa-populacao .fp-step-val.azul {{ color: {AZUL_PRINCIPAL} !important; }}
  .faixa-populacao .fp-step-val.laranja {{ color: {LARANJA_DESTAQUE} !important; }}
  .faixa-populacao .fp-step-val.verde {{ color: {COR_POSITIVO} !important; }}
  .faixa-populacao .fp-step-lbl {{
      color: {TEMA['texto_secundario']} !important;
      font-size: 0.78rem; margin-top: 4px; font-weight: 600;
  }}
  .faixa-populacao .fp-step-tx {{
      font-size: 0.76rem; font-weight: 700; margin-top: 6px;
  }}
  .faixa-populacao .fp-step-tx.insc {{ color: {LARANJA_DESTAQUE} !important; }}
  .faixa-populacao .fp-step-tx.insc.atencao {{ color: {COR_ATENCAO} !important; }}
  .faixa-populacao .fp-step-tx.insc.critico {{ color: {COR_CRITICO} !important; }}
  .faixa-populacao .fp-step-tx.insc.positivo {{ color: {COR_POSITIVO} !important; }}
  .faixa-populacao .fp-step-tx.efet {{ color: {AZUL_PRINCIPAL} !important; }}
  .faixa-populacao .fp-step-tx.efet.atencao {{ color: {COR_ATENCAO} !important; }}
  .faixa-populacao .fp-step-tx.efet.critico {{ color: {COR_CRITICO} !important; }}
  .faixa-populacao .fp-step-tx.efet.positivo {{ color: {COR_POSITIVO} !important; }}
  .faixa-populacao .fp-arrow {{
      display: flex; align-items: center; justify-content: center;
      color: {TEMA['texto_muted']} !important; font-size: 1.4rem;
      font-weight: 300; opacity: 0.55; flex: 0 0 20px;
      align-self: center;
  }}

  /* Gráficos Plotly em card */
  [data-testid="stPlotlyChart"] {{
      background: {TEMA['bg_card']};
      border: 1px solid {TEMA['borda']};
      border-radius: 12px;
      padding: 2px 0 0 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      margin-bottom: 3px;
  }}
  .stCaption {{
      color: {TEMA['texto_secundario']} !important;
      font-size: 0.8125rem !important;
      line-height: 1.45 !important;
  }}
  .chart-legenda-delta {{
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      margin: 4px 2px 14px 2px; padding: 8px 0 0 0;
      border-top: 1px solid {TEMA['borda_sutil']};
      font-size: 0.8125rem; color: {TEMA['texto_secundario']} !important;
      line-height: 1.45;
  }}
  .chart-legenda-delta strong {{
      color: {AZUL_PRINCIPAL} !important; font-weight: 800;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .chart-legenda-delta .delta-pos {{ color: {COR_POSITIVO} !important; font-weight: 700; }}
  .chart-legenda-delta .delta-neg {{ color: {COR_CRITICO} !important; font-weight: 700; }}

  /* Rodapé */
  .rodape {{
      color: {TEMA['texto_secundario']} !important;
      font-size: 0.8125rem; line-height: 1.45;
      margin-top: 28px; text-align: center;
      padding-top: 14px; border-top: 1px solid {TEMA['borda_sutil']};
  }}

  /* Radio horizontal — abas com sublinhado */
  div[data-testid="stRadio"] {{
      margin-bottom: 0 !important;
  }}
  div[data-testid="stRadio"] > div[role="radiogroup"] {{
      gap: 4px !important;
      background: {TEMA['bg_card']} !important;
      border: 1px solid {TEMA['borda']} !important;
      border-radius: 8px !important;
      padding: 3px !important;
      box-shadow: none !important;
      margin-bottom: 4px !important;
  }}
  div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
      background: transparent !important;
      border-radius: 6px !important;
      padding: 6px 14px !important;
      font-weight: 600 !important;
      font-family: 'Plus Jakarta Sans', sans-serif !important;
      font-size: 0.8rem !important;
      color: {TEMA['texto_secundario']} !important;
      border-bottom: none !important;
      margin-bottom: 0 !important;
  }}
  div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {{
      background: #DBEAFE !important;
      color: {AZUL_ESCURO} !important;
      border: 1px solid {AZUL_SED} !important;
      box-shadow: none !important;
  }}
  div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked),
  div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) * {{
      color: {AZUL_ESCURO} !important;
  }}

  /* Tabs do Streamlit */
  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
  .stTabs [data-baseweb="tab"] {{
      padding: 10px 18px; font-weight: 600;
      color: {TEMA['texto_secundario']} !important;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 0.88rem;
  }}
  .stTabs [aria-selected="true"] {{
      color: {AZUL_PRINCIPAL} !important;
      border-bottom-color: {AZUL_PRINCIPAL} !important;
  }}

  /* Sidebar institucional */
  [data-testid="stSidebar"] {{
      background: linear-gradient(180deg, {TEMA['bg_sidebar']} 0%, #EEF3FA 100%) !important;
      border-right: 1px solid {TEMA['borda']};
  }}
  [data-testid="stSidebar"] .stMarkdown,
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] label {{
      color: {TEMA['texto']} !important;
  }}
  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 {{
      color: {AZUL_PRINCIPAL} !important;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}

  /* Componentes nativos: dataframe, selectbox, etc. */
  .stDataFrame, .stDataFrame [role="grid"] {{
      color: {TEMA['texto']} !important;
  }}
  [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
      color: {TEMA['texto']} !important;
  }}

  /* Inputs / select / multiselect: garantir contraste */
  .stSelectbox label, .stMultiSelect label, .stSlider label, .stRadio label,
  .stTextInput label, .stNumberInput label, .stCheckbox label {{
      color: {TEMA['texto']} !important;
      font-weight: 600;
  }}

  /* Mensagens informativas (st.info, st.warning, st.error) — manter
     o estilo nativo, apenas garantir cor de texto legível */
  [data-testid="stAlert"] {{ color: {TEMA['texto']}; }}

  /* Plotly embutido no DOM principal (hover + roda do mouse) */
  .hub-plotly-embed {{
      width: 100%;
      overflow: visible;
      pointer-events: auto !important;
  }}
  .hub-plotly-embed .plotly-graph-div,
  .hub-plotly-embed .js-plotly-plot {{
      width: 100% !important;
      pointer-events: auto !important;
  }}
  .js-plotly-plot,
  .plotly-graph-div,
  [data-testid="stPlotlyChart"],
  [data-testid="stPlotlyChart"] iframe {{
      touch-action: pan-y;
      pointer-events: auto !important;
  }}
"""
    st.markdown(css, unsafe_allow_html=True)
