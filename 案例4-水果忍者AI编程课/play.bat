@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ========================================
echo   Fruit Ninja - Local Server
echo   URL: http://localhost:8123
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel%==0 goto run_python

where py >nul 2>&1
if %errorlevel%==0 goto run_py

echo [ERROR] Python 3 not found.
echo Please install Python from https://www.python.org/downloads/
echo During install, check "Add Python to PATH".
echo.
pause
exit /b 1

:run_python
echo Starting server with python...
start "FruitNinja Server" cmd /k python -m http.server 8123
goto open_browser

:run_py
echo Starting server with py...
start "FruitNinja Server" cmd /k py -3 -m http.server 8123
goto open_browser

:open_browser
timeout /t 2 >nul
start "" http://localhost:8123
echo.
echo Browser opened. Keep "FruitNinja Server" window open while playing.
echo Close that window to stop the server.
echo.
pause
