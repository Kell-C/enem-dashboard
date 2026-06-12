@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Painel ENEM MS - servidor local
echo  URL: http://127.0.0.1:8765/index.html
echo  Feche esta janela ou pressione Ctrl+C para encerrar.
echo.
start "" "http://127.0.0.1:8765/index.html"
py -m http.server 8765 2>nul || python -m http.server 8765
