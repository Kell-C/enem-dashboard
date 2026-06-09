"""Converte *_body.py de strings exec para funções Python normais."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "app" / "v15" / "pages"

PAGE_IMPORTS = "from app.v15.page_imports import *\n"

EXTRA_IMPORTS: dict[str, str] = {
    "gestao_hub_body.py": (
        "from app.v15.pages.sumario_executivo import aba_sumario_executivo\n"
    ),
    "territorio_drilldown_body.py": (
        "from app.v15.pages.escolas_2024 import aba_escolas_2024\n"
        "from app.v15.pages.municipios import aba_municipios\n"
        "from app.v15.pages.territorial import aba_territorial\n"
    ),
}

RENDER_BY_BODY: dict[str, str] = {
    "_CONTEXTO_NACIONAL_BODY": "render_contexto_nacional",
    "_DESEMPENHO_BODY": "render_desempenho",
    "_ESCOLAS_2024_BODY": "render_escolas_2024",
    "_GESTAO_HUB_BODY": "render_gestao_hub",
    "_RENDER_METODOLOGIA_BODY": "render_metodologia_detalhe",
    "_ABA_METODOLOGIA_BODY": "render_aba_metodologia",
    "_MUNICIPIOS_BODY": "render_municipios",
    "_PANORAMA_PARTICIPACAO_BODY": "render_panorama_participacao",
    "_SUMARIO_EXECUTIVO_BODY": "render_sumario_executivo",
    "_TERRITORIAL_BODY": "render_territorial",
    "_TERRITORIO_DRILLDOWN_BODY": "render_territorio_drilldown",
}

RENDER_BY_WRAPPER: dict[str, str] = {
    "aba_contexto_nacional": "render_contexto_nacional",
    "aba_desempenho": "render_desempenho",
    "aba_escolas_2024": "render_escolas_2024",
    "aba_gestao_hub": "render_gestao_hub",
    "_render_metodologia_detalhe": "render_metodologia_detalhe",
    "aba_metodologia": "render_aba_metodologia",
    "aba_municipios": "render_municipios",
    "aba_panorama_participacao": "render_panorama_participacao",
    "aba_sumario_executivo": "render_sumario_executivo",
    "aba_territorial": "render_territorial",
    "aba_territorio_drilldown": "render_territorio_drilldown",
}


def extract_bodies(path: Path) -> list[tuple[str, str]]:
    mod = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    for node in mod.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name) or not tgt.id.endswith("_BODY"):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            out.append((tgt.id, node.value.value))
    return out


def wrapper_functions(wrapper_path: Path) -> list[ast.FunctionDef]:
    mod = ast.parse(wrapper_path.read_text(encoding="utf-8"))
    return [
        node
        for node in mod.body
        if isinstance(node, ast.FunctionDef)
        and (node.name.startswith("aba_") or node.name == "_render_metodologia_detalhe")
    ]


def convert_body_file(body_path: Path, wrapper_path: Path) -> list[str]:
    bodies = extract_bodies(body_path)
    if not bodies:
        return []
    wrapper_src = wrapper_path.read_text(encoding="utf-8")
    wrappers = wrapper_functions(wrapper_path)
    code_by_const = dict(bodies)
    render_names: list[str] = []
    func_chunks: list[str] = []

    for wrapper in wrappers:
        rn = RENDER_BY_WRAPPER[wrapper.name]
        const = next(k for k, v in RENDER_BY_BODY.items() if v == rn)
        render_names.append(rn)
        sig = ast.get_source_segment(wrapper_src, wrapper).split(":", 1)[0]
        sig = sig.replace(f"def {wrapper.name}", f"def {rn}", 1)
        inner = textwrap.dedent(code_by_const[const]).strip("\n")
        func_chunks.append(f"{sig}:\n" + textwrap.indent(inner, "    "))

    header = (
        f'"""Corpo das funções de `{body_path.stem.replace("_body", "")}` (fase 5d)."""\n\n'
        "from __future__ import annotations\n\n"
        + EXTRA_IMPORTS.get(body_path.name, "")
        + PAGE_IMPORTS
        + "\n\n"
    )
    body_path.write_text(header + "\n\n".join(func_chunks) + "\n", encoding="utf-8")
    return render_names


def rewrite_wrapper(wrapper_path: Path, render_names: list[str]) -> None:
    text = wrapper_path.read_text(encoding="utf-8")
    mod = ast.parse(text)
    stem = wrapper_path.stem
    out = [
        f'"""Páginas `{stem}` — painel ENEM v15 (fase 5d)."""',
        "",
        "from __future__ import annotations",
        "",
        f"from app.v15.pages.{stem}_body import {', '.join(render_names)}",
        "",
    ]
    for node in mod.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not (node.name.startswith("aba_") or node.name == "_render_metodologia_detalhe"):
            continue
        seg = ast.get_source_segment(text, node)
        header = seg.split(":", 1)[0] + ":"
        rn = RENDER_BY_WRAPPER[node.name]
        out.append(f"{header}\n    {rn}(**locals())\n")
    wrapper_path.write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    for body_path in sorted(PAGES.glob("*_body.py")):
        stem = body_path.stem.replace("_body", "")
        wrapper_path = PAGES / f"{stem}.py"
        if not wrapper_path.exists():
            continue
        names = convert_body_file(body_path, wrapper_path)
        rewrite_wrapper(wrapper_path, names)
        print(f"converted {body_path.name} -> {', '.join(names)}")


if __name__ == "__main__":
    main()
