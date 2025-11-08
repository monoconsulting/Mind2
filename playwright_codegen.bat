@echo off
REM Playwright Codegen - Generera tester genom att klicka runt i browsern
REM Usage: playwright_codegen.bat [URL]
REM Example: playwright_codegen.bat http://localhost:5169

echo ====================================
echo Playwright Codegen - Test Generator
echo ====================================
echo.

REM Kontrollera om URL angavs, annars använd default
if "%1"=="" (
    set TARGET_URL=http://localhost:5169
    echo Ingen URL angiven, använder default: %TARGET_URL%
) else (
    set TARGET_URL=%1
    echo Använder URL: %TARGET_URL%
)

echo.
echo INSTRUKTIONER:
echo 1. En webbläsare öppnas där du kan klicka runt
echo 2. Playwright Inspector öppnas med genererad kod
echo 3. Klicka, skriv, navigera som du vill testa
echo 4. Koden genereras automatiskt i Inspector-fönstret
echo 5. Kopiera koden när du är klar (Ctrl+A, Ctrl+C)
echo 6. Stäng webbläsaren för att avsluta
echo.
echo Startar Codegen...
echo.

npx playwright codegen %TARGET_URL% --viewport-size=3440,1440

echo.
echo Codegen avslutad!
echo Nästa steg: Berätta för Claude vilken test-fil du vill skapa och klistra in koden.
pause
