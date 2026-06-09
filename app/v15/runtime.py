"""Namespace centralizado para exec das páginas v15."""

from __future__ import annotations

import sys
import textwrap
from types import ModuleType


def _monolith_module() -> ModuleType:
    """Retorna o módulo ativo do painel (Streamlit usa ``__main__``, não o submódulo cacheado)."""
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", "") or ""
    if main is not None and main_file.replace("\\", "/").endswith("dashboard_enem_v15.py"):
        return main
    import dashboard_enem_v15 as mod

    return mod


def page_globals(**locals_: object) -> dict:
    """Mescla namespace do monolito com argumentos da função da página."""
    g = vars(_monolith_module()).copy()
    g.update(locals_)
    return g


def exec_page_body(body: str, module_name: str, ns: dict | None = None, **locals_: object) -> None:
    """Executa corpo de aba extraído do monolito (dedent + suporte a `return`)."""
    inner = textwrap.dedent(body).strip("\n")
    wrapped = "def __page_body():\n" + textwrap.indent(inner, "    ") + "\n__page_body()\n"
    g = ns if ns is not None else page_globals(**locals_)
    exec(compile(wrapped, module_name, "exec"), g)
