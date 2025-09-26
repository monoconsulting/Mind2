@echo off
REM ========================================
REM Rensningsskript för Mind2 System
REM Rensar databas, inbox och storage
REM ========================================

echo.
echo ========================================
echo    MIND2 SYSTEM - RENSNING
echo ========================================
echo.

REM Kontrollera att Docker körs
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo FEL: Docker är inte igång eller inte installerat!
    echo Starta Docker Desktop och försök igen.
    pause
    exit /b 1
)

echo [1/3] Rensar lokal inbox...
del /F /Q "inbox\*.jpg" 2>nul
del /F /Q "inbox\*.jpeg" 2>nul
del /F /Q "inbox\*.png" 2>nul
del /F /Q "inbox\*.gif" 2>nul
del /F /Q "inbox\*.pdf" 2>nul
del /F /Q "inbox\*.txt" 2>nul
del /F /Q "inbox\*.json" 2>nul
echo      Inbox rensad!

echo.
echo [2/3] Rensar Docker container inbox...
docker-compose exec -T ai-api rm -rf inbox/* 2>nul
if %errorlevel% equ 0 (
    echo      Container inbox rensad!
) else (
    echo      VARNING: Kunde inte rensa container inbox (kanske redan tom)
)

echo.
echo [3/3] Rensar databasen...
docker-compose exec -T mysql mysql -u root -proot mono_se_db_9 -e "SET FOREIGN_KEY_CHECKS = 0; TRUNCATE TABLE file_tags; TRUNCATE TABLE file_locations; TRUNCATE TABLE ai_processing_history; TRUNCATE TABLE ai_processing_queue; TRUNCATE TABLE ai_accounting_proposals; TRUNCATE TABLE invoice_line_history; TRUNCATE TABLE invoice_lines; TRUNCATE TABLE invoice_documents; TRUNCATE TABLE unified_files; SET FOREIGN_KEY_CHECKS = 1;" 2>nul
if %errorlevel% equ 0 (
    echo      Databastabeller rensade!
) else (
    echo      FEL: Kunde inte rensa databasen!
    echo      Kontrollera att MySQL container körs.
)

echo.
echo ========================================
echo    RENSNING KLAR!
echo ========================================
echo.
echo Följande har rensats:
echo   - Lokal inbox mapp
echo   - Docker container inbox
echo   - Alla databastabeller för filer
echo.
pause