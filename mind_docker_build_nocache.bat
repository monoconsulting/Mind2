@echo off
REM ============================================================================
REM Mind2 Docker Build Script (No Cache)
REM This script builds backend and frontend Docker images and brings up profiles.
REM Changes from original:
REM  - Use "cd /d" to switch drive and directory reliably (prevents wrong C:\ path).
REM  - Added SETLOCAL and simple PATH checks for docker / docker-compose.
REM  - Kept original commands; where an alternative exists it is commented, not removed.
REM ============================================================================

SETLOCAL ENABLEEXTENSIONS
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

REM --- Ensure we are in the project root on the correct drive ---
REM ORIGINAL:  cd e:\projects\Mind2
REM PROBLEM:   Without /d, drive does not switch if started on C:
REM FIXED:
cd /d E:\projects\Mind2
if errorlevel 1 (
    echo ERROR: Could not change directory to E:\projects\Mind2
    pause
    exit /b 1
)

REM --- Quick check that docker CLI is available ---
where docker >nul 2>&1
if errorlevel 1 (
    echo ERROR: "docker" not found in PATH. Start Docker Desktop or fix PATH.
    pause
    exit /b 1
)

REM If you prefer the new CLI, you can use "docker compose" instead of docker-compose.
REM We keep docker-compose as in your original file.
where docker-compose >nul 2>&1
if errorlevel 1 (
    echo WARNING: "docker-compose" not found in PATH. If you use the v2 CLI, enable the docker-compose v1 shim or switch to:
    echo   docker compose --profile main --profile monitoring up -d
    echo Continuing anyway...
)

REM --- Build backend image without cache ---
echo [1/2] Building backend image...
docker build --no-cache -t mind2-ai-api:dev -f E:\projects\Mind2\backend\Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Backend build failed!
    pause
    exit /b %errorlevel%
)
echo Backend build successful!
echo.

REM --- Build main-system app-frontend image without cache ---
echo [2/2] Building main-system app-frontend image...
REM ORIGINAL:  cd E:\projects\Mind2\main-system\app-frontend
REM FIXED: also ensure drive switch with /d (even though already on E:, this is safe)
cd /d E:\projects\Mind2\main-system\app-frontend
if errorlevel 1 (
    echo ERROR: Could not change directory to E:\projects\Mind2\main-system\app-frontend
    cd /d E:\projects\Mind2
    pause
    exit /b 1
)
docker build --no-cache -t mind2-admin-frontend:dev .
if %errorlevel% neq 0 (
    echo ERROR: Frontend build failed!
    cd /d E:\projects\Mind2
    pause
    exit /b %errorlevel%
)
echo Frontend build successful!
echo.

REM --- Start all containers (main + monitoring profiles) ---
echo ============================================
echo All Docker images built successfully!
echo ============================================
echo.
echo Starting all containers (main + monitoring profiles)...
cd /d E:\projects\Mind2

REM ORIGINAL:
docker-compose --profile main --profile monitoring up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start containers with docker-compose.
    echo If you are on Docker CLI v2, the equivalent is:
    echo   docker compose --profile main --profile monitoring up -d
    pause
    exit /b %errorlevel%
)

echo.
docker-compose --profile main --profile monitoring ps

echo.
echo Done.
pause
ENDLOCAL
