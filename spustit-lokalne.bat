@echo off
cd /d "%~dp0"
echo Spoustim lokalni server na http://localhost:5715 ...
start "Enoteka - lokalni server (nezavirej dokud testujes)" cmd /k npx http-server -p 5715 -c-1 .
timeout /t 2 /nobreak >nul
start "" http://localhost:5715/index.html
