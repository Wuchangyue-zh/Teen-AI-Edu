@echo off
cd /d "%~dp0"
set "PY=C:\Users\73415\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PY%" set "PY=python"
echo Starting Fruit Ninja server on http://localhost:8123 ...
start "FruitNinja Server" "%PY%" -m http.server 8123
timeout /t 2 >nul
start "" http://localhost:8123
echo.
echo Browser opened. Keep the "FruitNinja Server" window open while playing.
echo Close that window to stop the server.
timeout /t 5 >nul
