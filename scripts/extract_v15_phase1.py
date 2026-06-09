"""Extrai theme e CSS do dashboard_enem_v15.py para app/v15/ (Fase 1)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lines = (ROOT / "dashboard_enem_v15.py").read_text(encoding="utf-8").splitlines(keepends=True)

theme_lines = lines[304:434]
(ROOT / "app" / "v15").mkdir(parents=True, exist_ok=True)

theme_header = '''"""Constantes visuais e de domínio — painel ENEM v15."""

from viz.chart_layout import (
    CHART_H_HUB,
    CHART_H_HUB_DELTA_ROW,
    CHART_H_HUB_EVOL,
    CHART_H_HUB_RANK,
)

'''
(ROOT / "app" / "v15" / "theme.py").write_text(theme_header + "".join(theme_lines), encoding="utf-8")

filter_css = "".join(lines[144:194]).strip()
main_css = "".join(ln[4:] if ln.startswith("    ") else ln for ln in lines[440:1527]).strip()

styles_py = f'''"""CSS institucional do painel ENEM v15."""

import streamlit as st

from app.v15.theme import (
    AZUL_ESCURO,
    AZUL_PRINCIPAL,
    AZUL_SED,
    AZUL_CLARO,
    COR_CRITICO,
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
{filter_css}
""",
        unsafe_allow_html=True,
    )


def inject_v15_styles() -> None:
    css = f"""
{main_css}
"""
    st.markdown(css, unsafe_allow_html=True)
'''
(ROOT / "app" / "v15" / "styles.py").write_text(styles_py, encoding="utf-8")
(ROOT / "app" / "v15" / "__init__.py").write_text(
    '"""Pacote modular do dashboard ENEM v15."""\n', encoding="utf-8"
)
print("OK: app/v15/theme.py, app/v15/styles.py")
