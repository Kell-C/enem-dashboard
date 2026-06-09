"""Reconstrói pages/*.py com BODY em arquivo separado + exec (fase 4 corrigida)."""
from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "app" / "v15" / "pages"

EXTRA: dict[str, list[str]] = {
    "territorio_drilldown": [
        "from app.v15.pages.territorial import aba_territorial",
        "from app.v15.pages.municipios import aba_municipios",
        "from app.v15.pages.escolas_2024 import aba_escolas_2024",
    ],
    "gestao_hub": [
        "from app.v15.pages.sumario_executivo import aba_sumario_executivo",
    ],
}

MODULES: dict[str, list[str]] = {
    "sumario_executivo": ["aba_sumario_executivo"],
    "panorama_participacao": ["aba_panorama_participacao"],
    "desempenho": ["aba_desempenho"],
    "escolas_2024": ["aba_escolas_2024"],
    "territorial": ["aba_territorial"],
    "municipios": ["aba_municipios"],
    "contexto_nacional": ["aba_contexto_nacional"],
    "territorio_drilldown": ["aba_territorio_drilldown"],
    "metodologia": ["_render_metodologia_detalhe", "aba_metodologia"],
    "gestao_hub": ["aba_gestao_hub"],
}


def strip_section_tail(body: str) -> str:
    lines = body.splitlines(keepends=True)
    out: list[str] = []
    for ln in lines:
        if ln.startswith("# ===="):
            break
        out.append(ln)
    return "".join(out).rstrip() + "\n"


def extract_compile_body(text: str, func_name: str) -> str | None:
    pat = rf"exec\(compile\((.+?),\s*['\"]{re.escape(func_name)}['\"],\s*['\"]exec['\"]\)"
    m = re.search(pat, text, re.DOTALL)
    if not m:
        return None
    try:
        return ast.literal_eval(m.group(1))
    except Exception:
        return None


def extract_signature_and_prefix(text: str, func_name: str) -> tuple[str, str]:
    """Assinatura + linhas do corpo antes de wrapper quebrado."""
    pat = rf"^def {re.escape(func_name)}\("
    m = re.search(pat, text, re.MULTILINE)
    if not m:
        raise ValueError(func_name)
    start = m.start()
    rest = text[start:]
    lines = rest.splitlines(keepends=True)
    sig: list[str] = []
    i = 0
    while i < len(lines):
        sig.append(lines[i])
        if "):" in lines[i] or lines[i].rstrip().endswith("):"):
            i += 1
            break
        i += 1
    prefix: list[str] = []
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("import dashboard_enem_v15") or s.startswith("from app.v15.pages"):
            break
        if s.startswith("exec(compile("):
            break
        if ln.startswith("def ") and not ln.startswith("    def "):
            break
        if ln.startswith("@") and not ln.startswith("    @"):
            break
        prefix.append(ln)
        i += 1
    return "".join(sig), "".join(prefix)


def build_body(text: str, func_name: str) -> str:
    compiled = extract_compile_body(text, func_name)
    _, prefix = extract_signature_and_prefix(text, func_name)
    if compiled:
        body = prefix + compiled
    else:
        body = prefix
    body = textwrap.dedent(body)
    return strip_section_tail(body)


def write_module(module: str, func_names: list[str]) -> None:
    src_path = PAGES / f"{module}.py"
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    text = src_path.read_text(encoding="utf-8")

    body_parts: list[str] = []
    sig_parts: list[str] = []
    for fn in func_names:
        sig, _ = extract_signature_and_prefix(text, fn)
        body_parts.append(build_body(text, fn))
        sig_parts.append((fn, sig))

    body_name = f"_{module.upper()}_BODY"
    if len(body_parts) == 1:
        body_const = f'{body_name} = {body_parts[0]!r}\n'
        body_ref = body_name
    else:
        chunks = ",\n".join(repr(p) for p in body_parts)
        body_const = f"{body_name} = [\n{chunks},\n]\n"
        body_ref = None

    body_file = PAGES / f"{module}_body.py"
    body_file.write_text(
        f'"""Corpo das funções de `{module}` (fase 4)."""\n\nfrom __future__ import annotations\n\n{body_const}',
        encoding="utf-8",
    )

    out: list[str] = [
        f'"""Páginas `{module}` — painel ENEM v15 (fase 4)."""\n\n',
        "from __future__ import annotations\n\n",
        f"from app.v15.pages.{module}_body import {body_name}\n\n",
    ]

    for idx, (fn, sig) in enumerate(sig_parts):
        inject_lines: list[str] = []
        if fn == "aba_territorio_drilldown":
            extra = EXTRA["territorio_drilldown"]
        elif fn == "aba_gestao_hub":
            extra = EXTRA["gestao_hub"]
        else:
            extra = []
        for imp in extra:
            inject_lines.append(f"    {imp}")
            sym = imp.split(" import ")[-1].strip()
            inject_lines.append(f"    _g[{sym!r}] = {sym}")
        inject_block = "\n" + "\n".join(inject_lines) if inject_lines else ""
        body_expr = body_name if len(body_parts) == 1 else f"{body_name}[{idx}]"
        out.append(f"{sig.rstrip()}\n")
        out.append(
            f"    import dashboard_enem_v15 as _d\n"
            f"    _g = vars(_d).copy()\n"
            f"    _g.update(locals()){inject_block}\n"
            f"    exec(compile({body_expr}, __name__, 'exec'), _g)\n"
        )
        if idx < len(sig_parts) - 1:
            out.append("\n")

    src_path.write_text("".join(out), encoding="utf-8")
    print(f"  rebuilt {module}.py + {module}_body.py")


for mod, fns in MODULES.items():
    write_module(mod, fns)

print("Done.")
