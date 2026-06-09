"""CSS institucional do painel (subset do v15)."""

import streamlit as st

from app.theme import (
    AZUL_ESCURO,
    AZUL_PRINCIPAL,
    AZUL_SED,
    COR_CRITICO,
    COR_POSITIVO,
    COR_TEXTO_BARRA,
    DOURADO_MS,
    LARANJA_DESTAQUE,
    TEMA,
    VERDE_MS,
)


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap');
        html, body, [class*="css"], .stApp, .stMarkdown {{
            font-family: 'Source Sans 3', system-ui, sans-serif;
            color: {TEMA['texto']} !important;
        }}
        .stApp {{
            background: {TEMA['bg_app']} !important;
        }}
        .main .block-container {{
            padding: 0 0 0.5rem 0 !important;
            max-width: 100% !important;
        }}
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}
        h1, h2, h3 {{
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }}

        .cab-claro {{
            background: linear-gradient(135deg, {TEMA['bg_card']} 0%, #F1F5F9 100%);
            border-bottom: 3px solid {DOURADO_MS};
            border-radius: 0 0 12px 12px;
            padding: 8px 14px 9px 14px;
            margin: 0 0 4px 0;
            box-shadow: 0 3px 14px rgba(15, 23, 42, 0.08);
            position: relative;
        }}
        .cab-claro::before {{
            content: "";
            position: absolute; left: 0; top: 0; bottom: 0; width: 6px;
            background: linear-gradient(180deg, {AZUL_SED} 0%, {AZUL_PRINCIPAL} 100%);
        }}
        .cab-claro-row {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 12px; flex-wrap: nowrap; padding-left: 10px; min-height: 62px;
        }}
        .cab-claro-brand {{ flex: 0 0 auto; max-width: min(360px, 34vw); }}
        .cab-claro-text h1 {{
            margin: 0; font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.42rem; font-weight: 800; color: {AZUL_ESCURO} !important;
        }}
        .cab-claro-text p {{
            margin: 3px 0 0 0; font-size: 0.84rem; font-weight: 600;
            color: {TEMA['texto_secundario']} !important;
        }}
        .cab-claro-kpis {{
            display: flex; flex-wrap: wrap; align-items: stretch;
            justify-content: flex-end; gap: 6px; flex: 1 1 auto;
        }}
        .kpi-claro {{
            background: {TEMA['bg_card']}; border: 1px solid {TEMA['borda']};
            border-radius: 6px; padding: 4px 9px 3px 9px;
            border-top: 2px solid {AZUL_SED}; min-width: max-content;
        }}
        .kpi-claro-lbl {{
            display: block; font-size: 0.6875rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.05em;
            color: {TEMA['texto_muted']} !important; line-height: 1.2;
        }}
        .kpi-claro-val {{
            display: block; margin-top: 1px;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.05rem; font-weight: 800; color: {AZUL_ESCURO} !important;
            font-variant-numeric: tabular-nums; line-height: 1.05;
        }}
        .kpi-claro-sub {{
            display: block; margin-top: 1px; font-size: 0.6875rem;
            color: {TEMA['texto_secundario']} !important; line-height: 1.3;
        }}
        .kpi-claro.positivo {{ border-top-color: {COR_POSITIVO}; }}
        .kpi-claro.positivo .kpi-claro-val {{ color: {COR_POSITIVO} !important; }}
        .kpi-claro.critico {{ border-top-color: {COR_CRITICO}; }}
        .kpi-claro.critico .kpi-claro-val {{ color: {COR_CRITICO} !important; }}

        .kpi-funil-inline {{ min-width: 248px; flex: 1 1 248px; }}
        .fk-lines {{ margin-top: 4px; }}
        .fk-line {{
            display: grid; grid-template-columns: minmax(7rem, auto) 4rem minmax(52px, 1fr);
            gap: 4px; align-items: center; margin-bottom: 3px;
        }}
        .fk-l {{ font-size: 0.625rem; color: {TEMA['texto_muted']}; white-space: nowrap; }}
        .fk-n {{ font-size: 0.72rem; font-weight: 700; color: {AZUL_ESCURO}; text-align: right; }}
        .fk-track {{
            display: block; height: 10px; background: {TEMA['bg_subtle']};
            border-radius: 4px; overflow: hidden; position: relative;
        }}
        .fk-fill {{
            display: flex; align-items: center; justify-content: flex-end;
            height: 100%; border-radius: 4px; min-width: 2px;
        }}
        .fk-fill.azul {{ background: {AZUL_PRINCIPAL}; }}
        .fk-fill.laranja {{ background: {LARANJA_DESTAQUE}; }}
        .fk-fill.verde {{ background: {VERDE_MS}; }}
        .fk-pct {{ font-size: 0.55rem; color: white; padding-right: 3px; font-weight: 700; }}
        .fk-pct-out {{
            position: absolute; right: 0; top: -14px; font-size: 0.58rem;
            color: {COR_TEXTO_BARRA}; font-weight: 700;
        }}

        .ref-pop-bar {{
            display: flex; flex-wrap: wrap; align-items: baseline; gap: 5px 10px;
            padding: 7px 12px 8px 14px; margin: 10px 0 12px 0;
            background: linear-gradient(135deg, #F8FAFC 0%, {TEMA['insight_bg']} 100%);
            border: 1px solid {TEMA['borda']}; border-left: 4px solid {AZUL_SED};
            border-radius: 8px; font-size: 0.875rem; color: {TEMA['texto_secundario']} !important;
        }}
        .ref-pop-tag {{
            font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800;
            font-size: 0.8125rem; text-transform: uppercase; letter-spacing: 0.07em;
            color: {AZUL_ESCURO} !important; background: rgba(0, 63, 127, 0.08);
            padding: 2px 8px; border-radius: 4px;
        }}
        .ref-pop-sep {{ color: {TEMA['texto_muted']}; }}

        .widget-chart-zone {{
            background: {TEMA['bg_card']}; border: 1px solid {TEMA['borda']};
            border-radius: 6px; overflow: hidden; margin-bottom: 8px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        }}
        .widget-head {{
            background: linear-gradient(135deg, {AZUL_ESCURO} 0%, {AZUL_PRINCIPAL} 100%);
            padding: 5px 8px; font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.03em; color: #FFFFFF !important;
            border-bottom: 2px solid {DOURADO_MS}; line-height: 1.35;
        }}
        .widget-chart-nota {{
            padding: 6px 10px; font-size: 0.75rem;
            color: {TEMA['texto_secundario']} !important;
            border-top: 1px solid {TEMA['borda']}; background: {TEMA['bg_subtle']};
            text-align: center;
        }}
        .hub-panorama-grid [data-testid="stHorizontalBlock"] {{
            gap: 0.4rem !important;
        }}
        .hub-toolbar {{
            display: flex; align-items: center; gap: 12px; margin: 8px 0 10px 0;
            padding: 0 4px;
        }}
        @media (max-width: 1100px) {{
            .cab-claro-row {{ flex-wrap: wrap; }}
            .cab-claro-brand {{ max-width: 100%; }}
            .cab-claro-kpis {{ justify-content: flex-start; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
