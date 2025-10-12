@echo off
echo Starting Mind2 Frontend Dev Server (Vite with Hot-Reload)...
echo.
echo Frontend will be available at: http://localhost:5169
echo API requests will proxy to: http://localhost:8008/ai/api
echo.
echo Make sure backend services are running (mind_docker_compose_up.bat)
echo.
echo Press Ctrl+C to stop the dev server
echo.

cd main-system\app-frontend
npm run dev
