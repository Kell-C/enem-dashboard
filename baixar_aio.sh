#!/usr/bin/env bash
# Baixa histórico ENEM por escola (AIO) e exporta aio_data.js para o painel.
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

DELAY="${AIO_DELAY:-1.0}"
EXTRA_ARGS=("$@")
if [[ ${#EXTRA_ARGS[@]} -eq 0 ]]; then
  EXTRA_ARGS=(--resume --delay "$DELAY")
fi

echo "=== 1/2 Scraping AIO (escolas MS) ==="
"$VENV_PY" baixar_aio_escolas.py "${EXTRA_ARGS[@]}"

echo ""
echo "=== 2/2 Export aio_data.js ==="
"$VENV_PY" gerar_aio_web_data.py

echo ""
echo "Concluído. Abra o painel e expanda 'ENEM por Escola (AIO)':"
echo "  bash $ROOT/abrir_painel.sh"
