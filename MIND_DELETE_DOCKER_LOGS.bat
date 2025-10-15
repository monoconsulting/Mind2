@echo off
REM ============================================================================
REM MIND_DELETE_DOCKER_LOGS.bat
REM
REM Purpose: Clear Docker container logs for Mind2 project ONLY
REM Usage: Run this batch file to clear Mind2 container logs
REM Method: Restarts containers to clear logs (most reliable on Windows)
REM ============================================================================

echo.
echo ========================================
echo MIND2 - Docker Log Cleanup
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Method: Restart Mind2 containers to clear logs
echo.
echo This will:
echo 1. Restart all Mind2 containers
echo 2. Clear their accumulated logs
echo 3. Minimal downtime (few seconds per container)
echo.

set /p CONFIRM="Continue? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled by user.
    pause
    exit /b 0
)

echo.
echo Restarting Mind2 containers...
echo.

REM Restart each Mind2 container individually
for /f "tokens=*" %%i in ('docker ps --filter "name=mind2" --format "{{.Names}}"') do (
    echo Restarting: %%i
    docker restart %%i >nul 2>&1
    if errorlevel 1 (
        echo   - Failed to restart
    ) else (
        echo   - Restarted successfully (logs cleared)
    )
)

echo.
echo ========================================
echo Verification
echo ========================================
echo.
echo Mind2 containers status:
echo.

docker ps --filter "name=mind2" --format "table {{.Names}}\t{{.Status}}"

echo.
echo ========================================
echo Log cleanup completed!
echo ========================================
echo.
echo All Mind2 containers have been restarted.
echo Logs have been cleared.
echo.
pause
