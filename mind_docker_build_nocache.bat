@echo off
echo ============================================
echo Mind2 Docker Build Script (No Cache)
echo ============================================
echo.
echo Frontend structure:
echo - mobile-capture-frontend/   : Static HTML/JS for mobile receipt capture (served by nginx, no Docker)
echo - main-system/app-frontend/  : Current admin frontend (v0.2.0) with React - NEEDS DOCKER BUILD
echo.
echo ============================================
echo.

REM Build backend image without cache
echo [1/2] Building backend image...
docker build --no-cache -t mind2-backend:latest -f backend/Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Backend build failed!
    pause
    exit /b %errorlevel%
)
echo Backend build successful!
echo.

REM Build main-system app-frontend image without cache
echo [2/2] Building main-system app-frontend image...
cd main-system\app-frontend
docker build --no-cache -t mind2-admin-frontend:dev .
if %errorlevel% neq 0 (
    echo ERROR: Frontend build failed!
    cd ..\..
    pause
    exit /b %errorlevel%
)
cd ..\..
echo Frontend build successful!
echo.

echo ============================================
echo All Docker images built successfully!
echo ============================================
echo.
echo Starting all containers (main + monitoring profiles)...
docker-compose --profile main --profile monitoring up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start containers!
    pause
    exit /b %errorlevel%
)
echo.
docker-compose --profile main --profile monitoring ps
pause