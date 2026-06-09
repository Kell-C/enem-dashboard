"""Sanity check de dependencias do painel ENEM."""
import importlib

MODULOS = (
    "pandas",
    "numpy",
    "pyarrow.parquet",
    "streamlit",
    "plotly.express",
    "openpyxl",
)

MODULOS_APP = (
    "app.data",
    "app.diagnostics",
    "app.charts",
    "app.styles",
    "app.hub",
    "app.territory",
    "app.detail",
    "app.v15.theme",
    "app.v15.styles",
    "app.v15.formatting",
    "app.v15.ui",
    "app.v15.plotly_theme",
    "app.v15.boxplots",
    "app.v15.hub_charts",
    "app.v15.nav_constants",
    "app.v15.constants",
    "app.v15.components",
    "app.v15.classifiers",
    "app.v15.charts_render",
    "app.v15.runtime",
    "app.v15.paths",
    "app.v15.participation",
    "app.v15.concluintes_data",
    "app.v15.ms_enrich",
    "app.v15.territory_data",
    "app.v15.charts.hub",
    "app.v15.charts.detail",
    "app.v15.page_helpers",
    "app.v15.page_imports",
    "app.v15.pages",
    "dashboard",
    "dashboard_enem_v15",
)


def main() -> int:
    falhas: list[tuple[str, str]] = []
    for mod in MODULOS:
        try:
            importlib.import_module(mod)
            print(f"  OK   {mod}")
        except ImportError as exc:
            falhas.append((mod, str(exc)))
            print(f"  FAIL {mod}: {exc}")

    for mod in MODULOS_APP:
        try:
            importlib.import_module(mod)
            print(f"  OK   {mod}")
        except ImportError as exc:
            falhas.append((mod, str(exc)))
            print(f"  FAIL {mod}: {exc}")

    if falhas:
        print(f"\n{len(falhas)} dependencia(s) ausente(s).")
        return 1
    print("\nTodas as dependencias OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
