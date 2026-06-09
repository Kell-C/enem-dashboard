"""Analisa dependências dos corpos exec das páginas v15."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "app" / "v15" / "pages"
MONO = ROOT / "dashboard_enem_v15.py"
V15 = ROOT / "app" / "v15"

SKIP = {
    "True", "False", "None", "int", "float", "str", "list", "dict", "set", "tuple",
    "len", "range", "sorted", "max", "min", "sum", "abs", "round", "print",
    "isinstance", "getattr", "hasattr", "zip", "enumerate", "any", "all",
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


def loads_in(code: str) -> set[str]:
    inner = textwrap.dedent(code).strip("\n")
    wrapped = "def __tmp():\n" + textwrap.indent(inner, "    ") + "\n"
    tree = ast.parse(wrapped)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            found.add(node.id)
    return found - SKIP


def defs_in_module(path: Path) -> set[str]:
    if not path.exists():
        return set()
    mod = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    names: set[str] = set()
    for node in mod.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[-1])
    return names


def monolith_exports() -> set[str]:
    return defs_in_module(MONO)


def v15_exports() -> dict[str, str]:
    """name -> module path"""
    mapping: dict[str, str] = {}
    for path in V15.rglob("*.py"):
        if path.name.endswith("_body.py") or path.name == "runtime.py":
            continue
        rel = path.relative_to(V15).with_suffix("").as_posix().replace("/", ".")
        mod = f"app.v15.{rel}" if rel != "__init__" else "app.v15"
        for name in defs_in_module(path):
            mapping.setdefault(name, mod)
    return mapping


def main() -> None:
    mono = monolith_exports()
    v15 = v15_exports()
    all_mono_only: set[str] = set()
    for path in sorted(PAGES.glob("*_body.py")):
        bodies = extract_bodies(path)
        print(path.name, "bodies", len(bodies))
        for label, code in bodies:
            try:
                used = loads_in(code)
            except SyntaxError as exc:
                print(f"  {label}: SYNTAX {exc}")
                continue
            mono_only = sorted(n for n in used if n in mono and n not in v15)
            all_mono_only.update(mono_only)
            print(f"  {label}: {len(used)} names, mono-only {len(mono_only)}")
            if mono_only:
                print("   ", ", ".join(mono_only[:15]))
    print("\nTotal mono-only symbols:", len(all_mono_only))
    for n in sorted(all_mono_only)[:80]:
        print(" ", n)
    if len(all_mono_only) > 80:
        print(f"  ... +{len(all_mono_only)-80} more")


if __name__ == "__main__":
    main()
