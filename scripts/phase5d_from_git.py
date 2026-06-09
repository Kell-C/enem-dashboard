"""Fase 5d: gera páginas com funções Python a partir do monolito git HEAD."""
from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "app" / "v15" / "pages"
SRC = ROOT / ".tmp_monolith_head.py"

if not SRC.exists():
    SRC.write_text(
        subprocess.check_output(
            ["git", "show", "HEAD:dashboard_enem_v15.py"],
            text=True,
            encoding="utf-8",
        ),
        encoding="utf-8",
    )

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

PAGE_SPECS: list[tuple[str, str, str, list[str]]] = [
    ("aba_sumario_executivo", "sumario_executivo", "render_sumario_executivo", []),
    ("aba_panorama_participacao", "panorama_participacao", "render_panorama_participacao", []),
    ("aba_desempenho", "desempenho", "render_desempenho", []),
    ("aba_escolas_2024", "escolas_2024", "render_escolas_2024", []),
    ("aba_territorial", "territorial", "render_territorial", []),
    ("aba_municipios", "municipios", "render_municipios", []),
    ("aba_contexto_nacional", "contexto_nacional", "render_contexto_nacional", []),
    (
        "aba_territorio_drilldown",
        "territorio_drilldown",
        "render_territorio_drilldown",
        [
            "from app.v15.pages.territorial import aba_territorial",
            "from app.v15.pages.municipios import aba_municipios",
            "from app.v15.pages.escolas_2024 import aba_escolas_2024",
        ],
    ),
    ("_render_metodologia_detalhe", "metodologia", "render_metodologia_detalhe", []),
    ("aba_metodologia", "metodologia", "render_aba_metodologia", []),
    (
        "aba_gestao_hub",
        "gestao_hub",
        "render_gestao_hub",
        ["from app.v15.pages.sumario_executivo import aba_sumario_executivo"],
    ),
]

EXTRA_BODY_IMPORTS: dict[str, str] = {
    "gestao_hub": "from app.v15.pages.sumario_executivo import aba_sumario_executivo\n",
    "territorio_drilldown": (
        "from app.v15.pages.escolas_2024 import aba_escolas_2024\n"
        "from app.v15.pages.municipios import aba_municipios\n"
        "from app.v15.pages.territorial import aba_territorial\n"
    ),
}


def is_top_level_boundary(ln: str) -> bool:
    return (ln.startswith("def ") or ln.startswith("@")) and not ln.startswith(" ")


def find_function(name: str) -> tuple[int, int]:
    pat = re.compile(rf"^def {re.escape(name)}\(")
    start = next((i for i, ln in enumerate(lines) if pat.match(ln)), None)
    if start is None:
        raise SystemExit(f"{name} not in monolith HEAD")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if is_top_level_boundary(lines[i]):
            end = i
            break
    return start, end


def split_signature_and_body(chunk: list[str]) -> tuple[str, str]:
    text = "".join(chunk)
    m = re.match(
        r"(def \w+\(.*?\)\s*(?:->[^\n:]*)?\s*:)",
        text,
        re.DOTALL,
    )
    if not m:
        raise SystemExit(f"signature not found in {text[:80]!r}")
    sig = m.group(1)
    if not sig.endswith("\n"):
        sig += "\n"
    return sig, text[m.end() :]


def strip_section_tail(body: str) -> str:
    out: list[str] = []
    for ln in body.splitlines(keepends=True):
        if ln.startswith("# ===="):
            break
        out.append(ln)
    return "".join(out).rstrip() + "\n"


def render_sig(sig: str, render_name: str) -> str:
    s = re.sub(r"^def \w+", f"def {render_name}", sig.rstrip(), count=1)
    if not s.endswith(":"):
        s += ":"
    return s


module_funcs: dict[str, list[tuple[str, str, str, str]]] = {}

for func_name, module, render_name, _extra in PAGE_SPECS:
    start, end = find_function(func_name)
    sig, body = split_signature_and_body(lines[start:end])
    body = strip_section_tail(body)
    module_funcs.setdefault(module, []).append((func_name, render_name, sig, body))

for module, funcs in module_funcs.items():
    body_chunks: list[str] = [
        f'"""Corpo das funções de `{module}` (fase 5d)."""\n\n',
        "from __future__ import annotations\n\n",
        EXTRA_BODY_IMPORTS.get(module, ""),
        "from app.v15.page_imports import *\n\n",
    ]
    wrapper_chunks: list[str] = [
        f'"""Páginas `{module}` — painel ENEM v15 (fase 5d)."""\n\n',
        "from __future__ import annotations\n\n",
    ]
    render_names = [r for _, r, _, _ in funcs]
    wrapper_chunks.append(
        f"from app.v15.pages.{module}_body import {', '.join(render_names)}\n\n"
    )
    for wrapper_name, render_name, sig, body in funcs:
        inner = textwrap.dedent(body).strip("\n")
        if wrapper_name == "aba_metodologia":
            inner = inner.replace(
                "_render_metodologia_detalhe()",
                "render_metodologia_detalhe()",
            )
        body_chunks.append(
            f"{render_sig(sig, render_name)}\n"
            + textwrap.indent(inner, "    ")
            + "\n\n"
        )
        wrapper_chunks.append(f"{sig.rstrip()}\n    {render_name}(**locals())\n\n")

    (PAGES / f"{module}_body.py").write_text("".join(body_chunks), encoding="utf-8")
    (PAGES / f"{module}.py").write_text("".join(wrapper_chunks), encoding="utf-8")
    print(f"  wrote {module}.py + {module}_body.py ({len(funcs)} fn)")

print("Phase 5d pages generated from git HEAD")
