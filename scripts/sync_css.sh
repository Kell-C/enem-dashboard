#!/usr/bin/env bash
# Re-embebe docs/style.css no docs/index.html (bloco <style> inline)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 << PY
from pathlib import Path
root = Path("$ROOT/docs")
html = root / "index.html"
css = (root / "style.css").read_text(encoding="utf-8")
text = html.read_text(encoding="utf-8")
body_idx = text.find("<body>")
if body_idx < 0:
    raise SystemExit("tag <body> nao encontrada")
head_end = '''<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Painel ENEM MS � 2019-2024</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230A4D8C'/%3E%3Ctext x='16' y='22' text-anchor='middle' font-size='14' font-family='Segoe UI,sans-serif' fill='white'%3EMS%3C/text%3E%3C/svg%3E" />
<link rel="stylesheet" href="style.css?v=3">
<style>
''' + css + '''
</style>
</head>
'''
start = text.find("<!doctype")
head_inner_start = text.find("<head>") + len("<head>")
new_doc = text[start:head_inner_start] + "\n" + head_end + text[body_idx:]
html.write_text(new_doc, encoding="utf-8")
print("CSS sincronizado em", html)
PY
