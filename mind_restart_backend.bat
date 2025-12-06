@echo off
echo Restarting backend services (for code changes in backend/src/)...
docker-compose restart ai-api celery-worker celery-worker-wf1 celery-worker-wf2
echo.
echo Done! Backend services restarted.
pause
