@echo off
REM Mind2 Documentation Server (mind-docs) Startup Script
REM This script starts the mind-docs web server automatically

cd /d "%~dp0"
echo Starting Mind2 Documentation Server (mind-docs)...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher and try again.
    pause
    exit /b 1
)

REM Start the server
echo Starting server on http://localhost:9091
echo Press Ctrl+C to stop the server
echo.
python server.py

REM If server stops, pause to show any error messages
pause