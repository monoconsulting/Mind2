@echo off
REM =================================================================
REM MIND OCR Batch Processing Script
REM =================================================================
REM This script triggers OCR processing for all receipts in the system.
REM Make sure the backend services are running before executing this.
REM =================================================================

echo.
echo =================================================================
echo MIND OCR Batch Processing
echo =================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher and add it to your PATH
    pause
    exit /b 1
)

REM Check if requests module is installed
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing required Python packages...
    pip install requests
    if errorlevel 1 (
        echo ERROR: Failed to install required packages
        pause
        exit /b 1
    )
)

REM Check if backend is running
curl -s http://localhost:8008/ai/api/health >nul 2>&1
if errorlevel 1 (
    echo WARNING: Backend API might not be running on http://localhost:8008
    echo Make sure to start the backend services with: docker-compose up
    echo.
    set /p continue="Do you want to continue anyway? (y/n): "
    if /i not "%continue%"=="y" (
        echo Operation cancelled.
        pause
        exit /b 0
    )
)

REM Run the OCR trigger script
echo Starting OCR processing...
echo.
python scripts\trigger_ocr_all.py

echo.
echo Process completed.
pause