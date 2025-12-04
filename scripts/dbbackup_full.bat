@echo off
REM ==============================================================================
REM MySQL single-database full dump (schema + data + routines + triggers + events)
REM Filename format: PROJECT_DB_YYYY-MM-DD_HH-mm.sql  (colon is illegal in Windows)
REM Configure your settings below and run this .bat
REM ==============================================================================

REM ---- User configuration -------------------------------------------------------
set "PROJECT=MCRM"
set "DB=crm_db"
set "PORT=3316"
set "USER=crm_user"
set "PASSWORD=crm_password_change_me"
set "TARGET_DIRECTORY=E:\projects\CRM\.dbbackup
REM ------------------------------------------------------------------------------

REM Create target directory if it doesn't exist
if not exist "%TARGET_DIRECTORY%" mkdir "%TARGET_DIRECTORY%"

REM Stable, locale-independent timestamp via PowerShell (avoids %DATE%/%TIME% quirks)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "TS=%%I"

REM Build safe filename (Windows forbids colon in filenames, so we use HH-mm)
set "FILENAME=%PROJECT%_%DB%_%TS%.sql"

REM Run mysqldump for the specific database with important options:
REM --single-transaction: consistent snapshot without locking (InnoDB)
REM --routines/--triggers/--events: include stored routines, triggers and events
REM --set-gtid-purged=OFF: safe for both GTID and non-GTID environments when importing
mysqldump ^
  --host=127.0.0.1 ^
  --port=%PORT% ^
  --user=%USER% ^
  --password=%PASSWORD% ^
  --single-transaction ^
  --routines ^
  --triggers ^
  --events ^
  --set-gtid-purged=OFF ^
  "%DB%" > "%TARGET_DIRECTORY%\%FILENAME%"

if errorlevel 1 (
  echo [ERROR] mysqldump failed. Check credentials, DB name, and that mysqldump is in PATH.
  exit /b 1
) else (
  echo [OK] Dump written to: "%TARGET_DIRECTORY%\%FILENAME%"
)
