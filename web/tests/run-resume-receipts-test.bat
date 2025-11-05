@echo off
echo ================================================
echo Running Resume Receipts Playwright Test
echo ================================================
echo.

cd /d "%~dp0.."

echo Running test: resume-receipts.spec.ts
echo.

npx playwright test tests/resume-receipts.spec.ts --headed

echo.
echo ================================================
echo Test completed
echo ================================================
pause
