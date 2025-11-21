@echo off
SETLOCAL ENABLEEXTENSIONS
echo ============================================
echo Mind2 Docker Build Script - No Cache
echo ============================================
echo.

cd /d E:\projects\Mind2
if errorlevel 1 (
    echo ERROR: Could not change to E:\projects\Mind2
    pause
    exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 (
    echo ERROR: docker not found in PATH
    pause
    exit /b 1
)

REM Build backend
echo.
echo [1/3] Building backend...
docker build --no-cache -t mind2-ai-api:dev -f backend\Dockerfile .
if errorlevel 1 (
    echo ERROR: Backend build failed
    pause
    exit /b 1
)
echo Backend OK

REM Build production frontend
echo.
echo [2/3] Building production frontend...
docker build --no-cache -t mind2-admin-frontend:dev -f main-system\app-frontend\Dockerfile .
if errorlevel 1 (
    echo ERROR: Production frontend build failed
    pause
    exit /b 1
)
echo Production frontend OK

REM Build dev frontend with hot-reload
echo.
echo [3/3] Building dev frontend (hot-reload)...
docker build --no-cache -t mind2-admin-frontend:dev-hotreload -f main-system\app-frontend\Dockerfile.dev .
if errorlevel 1 (
    echo ERROR: Dev frontend build failed
    pause
    exit /b 1
)
echo Dev frontend OK

REM Start containers
echo.
echo Starting containers...
docker-compose --profile main --profile monitoring up -d
if errorlevel 1 (
    echo ERROR: Failed to start containers
    pause
    exit /b 1
)

echo.
echo ============================================
echo SUCCESS - All services running
echo ============================================
echo.
echo Services:
echo   Production:  http://localhost:8008/
echo   Development: http://localhost:5169/
echo   Manual Match: http://localhost:5169/manual-match
echo   phpMyAdmin:  http://localhost:8087/
echo.
docker-compose ps
echo.
pause
ENDLOCAL
