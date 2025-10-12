@echo off
echo Running Playwright Tests in Development Mode...
echo.
echo Tests will run against Vite dev server: http://localhost:5169
echo.
echo Prerequisites:
echo   1. Backend running: mind_docker_compose_up.bat
echo   2. Frontend dev server running: mind_frontend_dev.bat
echo.

REM Check if a test file was provided as argument
if "%1"=="" (
    echo Running all tests...
    npx playwright test --config=playwright.dev.config.ts --headed --reporter=list
) else (
    echo Running test file: %1
    npx playwright test %1 --config=playwright.dev.config.ts --headed --reporter=list
)

echo.
echo Test run complete.
pause
