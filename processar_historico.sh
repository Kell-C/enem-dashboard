#!/usr/bin/env bash
# Processa MICRODADOS_ENEM_ESCOLA.csv (2005-2015), regenera agregados e painel.
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

echo "=== 1/3 Cache escola historico (2005-2015) ==="
"$VENV_PY" processar_enem.py --escola-historico

echo ""
echo "=== 2/3 Agregados ==="
"$VENV_PY" gerar_agregados.py

echo ""
echo "=== 3/3 Export web ==="
"$VENV_PY" gerar_web_data.py

echo ""
echo "Concluido. Abra o painel:"
echo "  bash $ROOT/abrir_painel.sh"
