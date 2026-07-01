#!/usr/bin/env bash
# Regeneração no notebook de casa (GitHub não inclui parquet 2025 completo).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV_PY="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"
fi

PARQUET_2025="$ROOT/dados/enem_completo_2019_2025_.parquet"
PARQUET_2024="$ROOT/dados/enem_completo_2019_2024_.parquet"

if [[ ! -f "$PARQUET_2025" && -f "$PARQUET_2024" ]]; then
  echo "Aviso: parquet 2025 ausente; usando link simbólico para 2019-2024."
  ln -sf enem_completo_2019_2024_.parquet "$PARQUET_2025"
fi

if [[ -f "$ROOT/dados/concluintes_3ano_ms_2019_2025.csv" ]]; then
  export CONCLUINTES_CSV="$ROOT/dados/concluintes_3ano_ms_2019_2025.csv"
fi

BACKUP="$ROOT/docs/data/painel_data.js"
if [[ -f "$BACKUP" ]]; then
  cp "$BACKUP" /tmp/painel_com_2025.js
fi

echo "=== Agregados ==="
"$VENV_PY" scripts/gerar_agregados.py

if "$VENV_PY" scripts/gerar_web_data.py 2>/dev/null; then
  echo "Painel completo gerado (parquet 2025 presente)."
else
  echo "Parcial: mesclando escPorArea novos com backup 2025..."
  "$VENV_PY" - <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, "scripts")
from gerar_web_data import build_painel_data, _sanitize

def load_js(path):
    raw = Path(path).read_text(encoding="utf-8")
    if raw.startswith("window.PAINEL_DATA="):
        raw = raw.replace("window.PAINEL_DATA=", "").rstrip(";")
    return json.loads(raw)

base = load_js("/tmp/painel_com_2025.js")
novo = _sanitize(build_painel_data())
base["escPorArea"] = novo.get("escPorArea", {})
novo_disp = {(r["nome"], r["mun"]): r for r in novo.get("dispersao", [])}
for row in base.get("dispersao", []):
    extra = novo_disp.get((row["nome"], row["mun"]))
    if extra:
        for k in ("notaPorArea", "nPorArea", "txPorArea", "notaPorAreaSemZero", "nPorAreaSemZero", "txPorAreaSemZero"):
            if k in extra:
                row[k] = extra[k]
for mun, schools in novo.get("escHist", {}).items():
    if mun not in base.get("escHist", {}):
        continue
    for sid, school in schools.items():
        if sid in base["escHist"][mun] and school.get("porArea"):
            base["escHist"][mun][sid]["porArea"] = school["porArea"]
base.setdefault("meta", {})["gerado_em"] = datetime.now().isoformat()
base["meta"]["regeneracao_local"] = "Agregados regenerados; 2025 do backup até parquet completo."
for name in ("data.json", "painel_data.js"):
    p = Path("docs/data") / name
    content = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    if name.endswith(".js"):
        p.write_text("window.PAINEL_DATA=" + content + ";", encoding="utf-8")
    else:
        p.write_text(content, encoding="utf-8")
print("Mesclado: medMs[2025] =", base["medMs"][-1])
PY
fi

echo "Concluído. Abra: bash $ROOT/abrir_painel.sh"
