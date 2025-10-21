@echo off
REM Run Gävle Föreningsregister Web Scraper
REM This script scrapes all associations from https://fri.gavle.se/forening/

echo ==========================================
echo Gävle Föreningsregister Web Scraper
echo ==========================================
echo.
echo This will scrape all associations from the Gävle association register
echo Output will be saved to: web/test-results/scraped-data/
echo.

REM Ask for confirmation
set /p confirm="Start scraping? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo Starting scraper...
echo.

REM Run the main scraper test
npx playwright test web/tests/2025-10-20_gavle_forening_scraper.spec.ts --headed --project=chromium-ultrawide

echo.
echo ==========================================
echo Scraping complete!
echo ==========================================
echo.
echo Check the output in: web/test-results/scraped-data/
echo.

REM Ask if user wants to scrape detailed information
echo.
set /p detailed="Do you want to scrape detailed information for each association? (Y/N): "
if /i "%detailed%"=="Y" (
    echo.
    echo Starting detailed scraper...
    echo WARNING: This will take much longer as it visits each association's page.
    echo.
    npx playwright test web/tests/2025-10-20_gavle_forening_scraper.spec.ts:67 --headed --project=chromium-ultrawide
)

echo.
echo All done!
pause
