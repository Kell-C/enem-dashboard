"""Atualiza wrappers das páginas v15 para usar exec_page_body."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "app" / "v15" / "pages"

PATTERN = re.compile(
    r"    from app\.v15\.runtime import page_globals(?:, exec_page_body)?\n"
    r"(?:    _g = page_globals\(\*\*locals\(\)\)\n"
    r"(?:    .+\n)*?"
    r"    exec_page_body\([^)]+\)\n"
    r"|    exec\(compile\([^)]+\), (?:page_globals\(\*\*locals\(\)\)|_g)\)\n)",
    re.MULTILINE,
)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "exec(compile(" not in text:
        return False

    # gestao / drilldown / metodologia com namespace extra
    if path.name == "gestao_hub.py":
        new = text.replace(
            "exec(compile(_GESTAO_HUB_BODY, __name__, 'exec'), _g)",
            'exec_page_body(_GESTAO_HUB_BODY, __name__, ns=_g)',
        )
        new = new.replace(
            "from app.v15.runtime import page_globals",
            "from app.v15.runtime import page_globals, exec_page_body",
        )
    elif path.name == "territorio_drilldown.py":
        new = text.replace(
            "exec(compile(_TERRITORIO_DRILLDOWN_BODY, __name__, 'exec'), _g)",
            "exec_page_body(_TERRITORIO_DRILLDOWN_BODY, __name__, ns=_g)",
        )
        new = new.replace(
            "from app.v15.runtime import page_globals",
            "from app.v15.runtime import page_globals, exec_page_body",
        )
    elif path.name == "metodologia.py":
        new = text  # manual
        return False
    else:
        new = re.sub(
            r"    from app\.v15\.runtime import page_globals\n"
            r"    exec\(compile\(([^,]+), __name__, ['\"]exec['\"]\), page_globals\(\*\*locals\(\)\)\)",
            r"    from app.v15.runtime import exec_page_body\n\n    exec_page_body(\1, __name__, **locals())",
            text,
        )

    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


for path in PAGES.glob("*.py"):
    if path.name.endswith("_body.py") or path.name == "__init__.py":
        continue
    if patch_file(path):
        print(f"patched {path.name}")
