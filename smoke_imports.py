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


def main() -> int:
    falhas: list[tuple[str, str]] = []
    for mod in MODULOS:
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
