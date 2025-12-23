@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==============================================================================
REM Mind2 MySQL Database Backup Script
REM
REM IMPORTANT: Creates dump INSIDE the container and copies it out to avoid
REM PowerShell text pipeline encoding issues (mojibake). This ensures proper
REM UTF-8 encoding for Swedish characters (ö, ä, å, etc).
REM
REM Filename format: {DB_NAME}_YYYY-MM-DD_HH-mm.sql
REM ==============================================================================

REM ---- Configuration ----------------------------------------------------------
set "PROJECT=Mind2"
set "DB=mono_se_db_9"
set "MYSQL_USER=root"
set "MYSQL_PWD=root"
set "CONTAINER_NAME=mind2-mysql-1"
set "TARGET_DIRECTORY=E:\projects\Mind2\.dbbackup"
REM -----------------------------------------------------------------------------

REM Create target directory if it doesn't exist
if not exist "%TARGET_DIRECTORY%" mkdir "%TARGET_DIRECTORY%"

REM Generate timestamp (locale-independent)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "TS=%%I"

REM Build filename
set "FILENAME=%DB%_%TS%.sql"
set "CONTAINER_PATH=/tmp/%FILENAME%"

echo [INFO] Starting Mind2 database backup...
echo [INFO] Database: %DB%
echo [INFO] Container: %CONTAINER_NAME%
echo [INFO] Target: %TARGET_DIRECTORY%\%FILENAME%

REM Step 1: Create dump INSIDE the container (avoids PowerShell encoding issues)
echo [INFO] Creating dump inside container...
docker compose exec -T mysql sh -c "mysqldump --default-character-set=utf8mb4 -u%MYSQL_USER% -p%MYSQL_PWD% --single-transaction --routines --triggers --events --set-gtid-purged=OFF %DB% > %CONTAINER_PATH%"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] mysqldump failed inside container. Check that container is running.
    exit /b 1
)

REM Step 2: Copy the dump file from container to host
echo [INFO] Copying dump from container to host...
for /f %%C in ('docker compose ps -q mysql') do set "CID=%%C"

if not defined CID (
    echo [ERROR] Could not find MySQL container ID.
    exit /b 1
)

docker cp %CID%:%CONTAINER_PATH% "%TARGET_DIRECTORY%\%FILENAME%"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to copy dump from container.
    exit /b 1
)

REM Step 3: Clean up the dump file inside the container
echo [INFO] Cleaning up temporary file in container...
docker compose exec -T mysql sh -c "rm -f %CONTAINER_PATH%"

REM Step 4: Verify the file was created and show size
for %%F in ("%TARGET_DIRECTORY%\%FILENAME%") do set "FILESIZE=%%~zF"
echo.
echo [OK] Backup completed successfully!
echo [OK] File: %TARGET_DIRECTORY%\%FILENAME%
echo [OK] Size: %FILESIZE% bytes

endlocal
