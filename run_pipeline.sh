#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$ROOT/scripts"
export PYTHONUNBUFFERED=1
cd "$SCRIPTS"

echo "=== 1/3 ETL microdados ==="
python3 processar_enem.py

echo ""
echo "=== 2/3 Agregados ==="
python3 gerar_agregados.py

echo ""
echo "=== 3/3 Export web ==="
python3 gerar_web_data.py

echo ""
echo "Concluido. Abra o painel:"
echo "  cd $ROOT/web && python3 -m http.server 8765"
echo "  http://127.0.0.1:8765/index.html"
