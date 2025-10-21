@echo off
REM Complete Gävle Föreningsregister Web Scraper
REM This script scrapes ALL data including details from each association page

echo ==========================================
echo Gävle Föreningsregister COMPLETE Scraper
echo ==========================================
echo.
echo This will:
echo  1. Scrape all 600+ associations from the register
echo  2. Fix homepage URLs to complete URLs (http://...)
echo  3. Visit EACH association's detail page
echo  4. Extract all detailed information
echo.
echo WARNING: This will take 10-20 minutes to complete!
echo Output: web/test-results/scraped-data/
echo.

REM Ask for confirmation
set /p confirm="Start complete scraping? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo Starting complete scraper...
echo Please be patient - visiting 600+ pages takes time!
echo.

REM Run the complete scraper test
npx playwright test web/tests/2025-10-20_gavle_forening_scraper_complete.spec.ts --headed --project=chromium-ultrawide

echo.
echo ==========================================
echo Complete scraping finished!
echo ==========================================
echo.
echo Check the output in: web/test-results/scraped-data/
echo Look for: gavle-foreningar-complete-*.json
echo.
pause
