@echo off
REM ==============================================================================
REM MySQL single-database full dump (schema + data + routines + triggers + events)
REM Filename format: PROJECT_DB_YYYY-MM-DD_HH-mm.sql  (colon is illegal in Windows)
REM Configure your settings below and run this .bat
REM ==============================================================================

REM ---- User configuration -------------------------------------------------------
set "PROJECT=Mind2"
set "DB=mono_se_db_9"
set "PORT=3310"
set "USER=root"
set "PASSWORD=root"
set "TARGET_DIRECTORY=E:\projects\Mind2\.dbbackup"
REM ------------------------------------------------------------------------------

REM Create target directory if it doesn't exist
if not exist "%TARGET_DIRECTORY%" mkdir "%TARGET_DIRECTORY%"

REM Stable, locale-independent timestamp via PowerShell (avoids %DATE%/%TIME% quirks)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "TS=%%I"

REM Build safe filename (Windows forbids colon in filenames, so we use HH-mm)
set "FILENAME=%PROJECT%_%DB%_%TS%.sql"

REM Run mysqldump via Docker exec for the specific database with important options:
REM --single-transaction: consistent snapshot without locking (InnoDB)
REM --routines/--triggers/--events: include stored routines, triggers and events
REM --set-gtid-purged=OFF: safe for both GTID and non-GTID environments when importing
REM Note: Password warning is expected and can be ignored (does not affect backup)
echo Running database backup for %DB%...
docker exec mind2-mysql-1 mysqldump ^
  -u %USER% ^
  -p%PASSWORD% ^
  --single-transaction ^
  --routines ^
  --triggers ^
  --events ^
  --set-gtid-purged=OFF ^
  "%DB%" > "%TARGET_DIRECTORY%\%FILENAME%" 2>nul

REM Check if backup file was created successfully
if exist "%TARGET_DIRECTORY%\%FILENAME%" (
  echo [OK] Dump written to: "%TARGET_DIRECTORY%\%FILENAME%"
  for %%A in ("%TARGET_DIRECTORY%\%FILENAME%") do echo [OK] File size: %%~zA bytes
) else (
  echo [ERROR] mysqldump failed. Check that:
  echo   - Docker container 'mind2-mysql-1' is running (docker ps)
  echo   - Credentials are correct (USER=%USER%, DB=%DB%)
  echo   - Database exists in MySQL
  exit /b 1
)
