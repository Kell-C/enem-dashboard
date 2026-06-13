#!/usr/bin/env bash
cd "$(dirname "$0")/web"
echo "Painel ENEM MS — pipeline_dashboard"
echo "http://127.0.0.1:8765/index.html"
python3 -m http.server 8765
