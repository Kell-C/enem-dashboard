"""Aplica Fase 1 no dashboard_enem_v15.py: remove theme/CSS inline, usa app/v15/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "dashboard_enem_v15.py"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

# Substituir bloco filter CSS (146-198) por chamada
if "# CSS customizado para destacar os filtros" not in lines[145]:
    raise SystemExit("Filter CSS block not at expected line")
lines[145:198] = ["inject_v15_filter_styles()\n", "\n"]

# Remover theme + CSS institucional
start = end_css = None
for i, ln in enumerate(lines):
    if start is None and "# IDENTIDADE INSTITUCIONAL" in ln:
        start = i - 3
    if start is not None and end_css is None and "CSS INSTITUCIONAL" in ln:
        pass
    if start is not None and end_css is None and i > start and ln.strip() == ")":
        # closing of st.markdown(..., unsafe_allow_html=True,) block after </style>
        prev = "".join(lines[max(0, i - 5): i])
        if "</style>" in prev and "unsafe_allow_html=True" in prev:
            end_css = i + 1

if start is None or end_css is None:
    raise SystemExit(f"theme/css block not found: start={start} end={end_css}")

lines[start:end_css] = ["inject_v15_styles()\n", "\n"]

path.write_text("".join(lines), encoding="utf-8")
print(f"Patched {path.name}: {sum(1 for _ in open(path, encoding='utf-8'))} lines")
