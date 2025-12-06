@echo off
echo Rebuilding backend image (for Dockerfile/entrypoint changes)...
docker-compose build ai-api
if %errorlevel% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo.
echo Restarting backend services...
docker-compose up -d ai-api celery-worker celery-worker-wf1 celery-worker-wf2
echo.
echo Done! Backend rebuilt and restarted.
pause
