"""Fase 4: remove aba_* inline e reimporta de app/v15/pages/ antes de main()."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

NAMES = [
    "aba_gestao_hub",
    "aba_metodologia",
    "_render_metodologia_detalhe",
    "aba_territorio_drilldown",
    "aba_contexto_nacional",
    "aba_municipios",
    "aba_territorial",
    "aba_escolas_2024",
    "aba_desempenho",
    "aba_panorama_participacao",
    "aba_sumario_executivo",
]

IMPORT_BLOCK = (
    "\n# --- páginas (fase 4) ---\n"
    "from app.v15.pages import (\n"
    "    aba_contexto_nacional,\n"
    "    aba_desempenho,\n"
    "    aba_escolas_2024,\n"
    "    aba_gestao_hub,\n"
    "    aba_metodologia,\n"
    "    aba_municipios,\n"
    "    aba_panorama_participacao,\n"
    "    aba_sumario_executivo,\n"
    "    aba_territorial,\n"
    "    aba_territorio_drilldown,\n"
    ")\n"
    "from app.v15.pages.metodologia import _render_metodologia_detalhe\n"
)


def find_range(name: str) -> tuple[int, int]:
    pat = re.compile(rf"^def {re.escape(name)}\(")
    start = next(i for i, ln in enumerate(lines) if pat.match(ln))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("def ") and not lines[i][4:5].isspace():
            end = i
            break
    return start, end


for name in NAMES:
    start, end = find_range(name)
    del lines[start:end]

# Inserir imports imediatamente antes de def main():
main_idx = next(i for i, ln in enumerate(lines) if ln.startswith("def main("))
if "# --- páginas (fase 4) ---" not in "".join(lines):
    lines.insert(main_idx, IMPORT_BLOCK)

path.write_text("".join(lines), encoding="utf-8")
print(f"Phase 4 patched: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
