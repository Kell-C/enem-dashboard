"""Gera app/v15/pages/*.py a partir das funções aba_* do monolito v15."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Usar cópia em pages/*.py se monolito já patchado — preferir reconstruir do patch reverso.
# Para re-extrair: restaurar monolito do git ou mesclar pages body de volta.
SRC = ROOT / "dashboard_enem_v15.py"
PAGES = ROOT / "app" / "v15" / "pages"

PAGE_SPECS: list[tuple[str, str, list[str]]] = [
    ("aba_sumario_executivo", "sumario_executivo", []),
    ("aba_panorama_participacao", "panorama_participacao", []),
    ("aba_desempenho", "desempenho", []),
    ("aba_escolas_2024", "escolas_2024", []),
    ("aba_territorial", "territorial", []),
    ("aba_municipios", "municipios", []),
    ("aba_contexto_nacional", "contexto_nacional", []),
    (
        "aba_territorio_drilldown",
        "territorio_drilldown",
        [
            "from app.v15.pages.territorial import aba_territorial",
            "from app.v15.pages.municipios import aba_municipios",
            "from app.v15.pages.escolas_2024 import aba_escolas_2024",
        ],
    ),
    ("_render_metodologia_detalhe", "metodologia", []),
    ("aba_metodologia", "metodologia", []),
    (
        "aba_gestao_hub",
        "gestao_hub",
        ["from app.v15.pages.sumario_executivo import aba_sumario_executivo"],
    ],
]

# Corpo das páginas ainda presente nos .py gerados na 1ª tentativa (monolito já patchado).
# Reconstruímos a partir dos arquivos quebrados + merge com monolito residual.
# Se SRC não contém aba_*, lemos bodies dos módulos _body embutidos.

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)


def is_top_level_boundary(ln: str) -> bool:
    return (ln.startswith("def ") or ln.startswith("@")) and not ln.startswith(" ")


def find_function(name: str) -> tuple[int, int]:
    pat = re.compile(rf"^def {re.escape(name)}\(")
    start = next((i for i, ln in enumerate(lines) if pat.match(ln)), None)
    if start is None:
        raise SystemExit(f"{name} not in monolith — restore from git before re-extract")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if is_top_level_boundary(lines[i]):
            end = i
            break
    return start, end


def split_signature_and_body(chunk: list[str]) -> tuple[str, str]:
    """Retorna (assinatura completa, corpo indentado)."""
    i = 0
    sig_parts: list[str] = []
    while i < len(chunk):
        sig_parts.append(chunk[i])
        if "):" in chunk[i] or chunk[i].rstrip().endswith("):"):
            i += 1
            break
        i += 1
    body = "".join(chunk[i:])
    return "".join(sig_parts), body


def make_wrapper(
    func_name: str,
    signature: str,
    body: str,
    extra_bindings: list[str],
) -> str:
    body = textwrap.dedent(body) if body else "pass\n"
    extra = "\n".join(f"    {b}" for b in extra_bindings)
    extra_block = f"\n{extra}" if extra else ""
    return f"""{signature.rstrip()}
    import dashboard_enem_v15 as _d
    _g = vars(_d).copy()
    _g.update(locals()){extra_block}
    for _k, _v in _g.items():
        if _k not in _g.get("__builtins__", {{}}):
            pass
    exec(compile({body!r}, {func_name!r}, "exec"), _g)
"""


PAGES.mkdir(parents=True, exist_ok=True)
file_parts: dict[str, list[str]] = {}

for func_name, module_name, extra in PAGE_SPECS:
    start, end = find_function(func_name)
    chunk = lines[start:end]
    signature, body = split_signature_and_body(chunk)
    wrapped = make_wrapper(func_name, signature, body, extra)
    if module_name not in file_parts:
        file_parts[module_name] = [
            f'"""Páginas `{module_name}` — painel ENEM v15 (fase 4)."""\n\n'
            f"from __future__ import annotations\n\n"
        ]
    else:
        file_parts[module_name].append("\n")
    file_parts[module_name].append(wrapped)

for module_name, parts in file_parts.items():
    (PAGES / f"{module_name}.py").write_text("".join(parts), encoding="utf-8")
    print(f"  wrote app/v15/pages/{module_name}.py")

init_exports = [
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
]
mod_map = {
    "aba_sumario_executivo": "sumario_executivo",
    "aba_panorama_participacao": "panorama_participacao",
    "aba_desempenho": "desempenho",
    "aba_escolas_2024": "escolas_2024",
    "aba_territorial": "territorial",
    "aba_municipios": "municipios",
    "aba_contexto_nacional": "contexto_nacional",
    "aba_territorio_drilldown": "territorio_drilldown",
    "aba_metodologia": "metodologia",
    "aba_gestao_hub": "gestao_hub",
}
init = ['"""Páginas Streamlit do painel ENEM v15."""\n\n']
for name in init_exports:
    init.append(f"from app.v15.pages.{mod_map[name]} import {name}\n")
init.append("\nfrom app.v15.pages.metodologia import _render_metodologia_detalhe\n\n__all__ = [\n")
for name in init_exports:
    init.append(f'    "{name}",\n')
init.append('    "_render_metodologia_detalhe",\n]\n')
(PAGES / "__init__.py").write_text("".join(init), encoding="utf-8")
print("  wrote app/v15/pages/__init__.py")
