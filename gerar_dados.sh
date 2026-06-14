#!/usr/bin/env bash
# Regenera agregados + painel_data.js usando o venv local (evita ModuleNotFoundError).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PY="$ROOT/.venv/bin/python"
SCRIPTS="$ROOT/scripts"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Criando venv em $ROOT/.venv ..."
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"
fi

export PYTHONUNBUFFERED=1
cd "$SCRIPTS"

echo "=== Agregados ==="
"$VENV_PY" gerar_agregados.py

echo ""
echo "=== Export web (painel_data.js) ==="
"$VENV_PY" gerar_web_data.py

echo ""
echo "Concluido. Abra o painel:"
echo "  bash $ROOT/abrir_painel.sh"
echo "  http://127.0.0.1:8765/index.html"
