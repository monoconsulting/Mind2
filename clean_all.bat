@echo off
REM ========================================
REM Mind2 System Cleanup Script
REM Clears database, inbox and storage
REM ========================================

echo.
echo ========================================
echo    MIND2 SYSTEM - CLEANUP
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running or not installed!
    echo Start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/4] Cleaning local inbox...
del /F /Q "inbox\*.jpg" 2>nul
del /F /Q "inbox\*.jpeg" 2>nul
del /F /Q "inbox\*.png" 2>nul
del /F /Q "inbox\*.gif" 2>nul
del /F /Q "inbox\*.pdf" 2>nul
del /F /Q "inbox\*.txt" 2>nul
del /F /Q "inbox\*.json" 2>nul
echo      Local inbox cleaned!

echo.
echo [2/4] Cleaning Docker container inbox...
docker-compose exec -T ai-api rm -rf /data/inbox/* 2>nul
if %errorlevel% equ 0 (
    echo      Container inbox cleaned!
) else (
    echo      WARNING: Could not clean container inbox (maybe already empty)
)

echo.
echo [3/4] Cleaning storage folder...
rmdir /S /Q "storage" 2>nul
mkdir "storage" 2>nul
mkdir "storage\line_items" 2>nul
echo      Storage folder cleaned and recreated!

echo.
echo [4/5] Cleaning Celery task queue...
docker restart mind2-celery-worker-1 >nul 2>&1
docker exec mind2-redis-1 redis-cli FLUSHDB >nul 2>&1
if %errorlevel% equ 0 (
    echo      Task queue cleared!
) else (
    echo      WARNING: Could not clear task queue completely
)

echo.
echo [5/5] Cleaning database...
docker-compose exec -T mysql mysql -u root -proot mono_se_db_9 -e "SET FOREIGN_KEY_CHECKS = 0; TRUNCATE TABLE file_tags; TRUNCATE TABLE file_locations; TRUNCATE TABLE ai_processing_history; TRUNCATE TABLE ai_processing_queue; TRUNCATE TABLE ai_accounting_proposals; TRUNCATE TABLE receipt_items; TRUNCATE TABLE invoice_line_history; TRUNCATE TABLE invoice_lines; TRUNCATE TABLE invoice_documents; TRUNCATE TABLE unified_files; SET FOREIGN_KEY_CHECKS = 1;" 2>nul
if %errorlevel% equ 0 (
    echo      Database tables cleaned!
) else (
    echo      ERROR: Could not clean database!
    echo      Check that MySQL container is running.
)

echo.
echo ========================================
echo    CLEANUP COMPLETE!
echo ========================================
echo.
echo The following have been cleaned:
echo   - Local inbox folder
echo   - Docker container inbox
echo   - Storage folder (all files and folders)
echo   - Celery task queue (Redis)
echo   - All database tables for files
echo.
pause