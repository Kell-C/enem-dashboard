#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
DOCS="$ROOT/docs"
PORT="${PORT:-8765}"

if command -v ss >/dev/null 2>&1; then
  IN_USE=$(ss -tlnH "sport = :$PORT" 2>/dev/null | wc -l)
elif command -v lsof >/dev/null 2>&1; then
  IN_USE=$(lsof -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | wc -l)
else
  IN_USE=0
fi

echo "Painel ENEM MS — enem-dashboard/docs"
echo "Pasta: $DOCS"

if [[ "$IN_USE" -gt 0 ]]; then
  echo ""
  echo "Porta $PORT ja em uso — o painel provavelmente ja esta no ar."
  echo "Abra: http://127.0.0.1:$PORT/index.html"
  echo ""
  echo "Para usar outra porta: PORT=8766 bash abrir_painel.sh"
  echo "Para encerrar o servidor anterior: kill \$(lsof -t -iTCP:$PORT -sTCP:LISTEN)"
  exit 0
fi

cd "$DOCS"
echo "http://127.0.0.1:$PORT/index.html"
echo "(Execute a partir de enem-dashboard/, nao de docs/)"
python3 -m http.server "$PORT"
