@echo off
echo Rebuilding Mind2 Frontend...

npm install --prefix main-system/app-frontend && npm run build --prefix main-system/app-frontend

echo.
echo Frontend rebuild complete.
pause
