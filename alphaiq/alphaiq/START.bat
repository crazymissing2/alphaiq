@echo off
title AlphaIQ — AI Trading Academy
color 0A
echo.
echo  =============================================
echo   AlphaIQ — AI Trading Academy v1.0
echo  =============================================
echo.
echo  Starting backend server...
echo  Open http://127.0.0.1:8765 for the API
echo  Open frontend/index.html in your browser
echo.

cd /d "%~dp0backend"

if not exist "venv\Scripts\activate.bat" (
    echo  [SETUP] Creating Python environment...
    python -m venv venv
    call venv\Scripts\activate
    echo  [SETUP] Installing dependencies...
    pip install -r requirements.txt
    echo  [SETUP] Done!
    echo.
) else (
    call venv\Scripts\activate
)

:: Create data directory
if not exist "data" mkdir data

echo  Server running at: http://127.0.0.1:8765
echo  Open frontend\index.html in Chrome to use AlphaIQ
echo  Press Ctrl+C to stop
echo.

python main.py
pause
