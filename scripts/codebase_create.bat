@echo off
setlocal enabledelayedexpansion

REM ========================================
REM Configuration - Set your paths here
REM ========================================
set PROJECT_PATH=E:\projects\CRM
set SOURCE_PATH=E:\projects\CRM
set TARGET_PATH=E:\projects\CRM\.codebasebackup

REM ========================================
REM Exclusion Lists
REM ========================================
REM Directories to exclude (full paths or relative to SOURCE_PATH)
REM Add more directories by appending to the EXCLUDE_DIRS variable
REM Example: set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\another_folder"
set EXCLUDE_DIRS="%SOURCE_PATH%\crm-app\storage"
set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\.dbbackup"
set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\.codebasebackup"
set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\crm-app\node_modules"
set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\scraping\json"
set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\node_modules"
REM set EXCLUDE_DIRS=%EXCLUDE_DIRS% "%SOURCE_PATH%\logs"

REM Files to exclude (wildcard patterns supported)
REM Add more patterns by appending to the EXCLUDE_FILES variable
REM Example: set EXCLUDE_FILES=%EXCLUDE_FILES% *.bak
set EXCLUDE_FILES=codebase.zip
set EXCLUDE_FILES=%EXCLUDE_FILES% *.tmp
set EXCLUDE_FILES=%EXCLUDE_FILES% "%SOURCE_PATH%\crm-app\node_modules\@next\swc-win32-x64-msvc\next-swc.win32-x64-msvc.node"
set EXCLUDE_FILES=%EXCLUDE_FILES% *.log
REM set EXCLUDE_FILES=%EXCLUDE_FILES% secret.env
REM set EXCLUDE_FILES=%EXCLUDE_FILES% credentials.json

echo ========================================
echo CRM Codebase Backup Script
echo ========================================
echo Project Path: %PROJECT_PATH%
echo Source Path: %SOURCE_PATH%
echo Target Path: %TARGET_PATH%
echo.
echo Excluded Directories:
echo   %EXCLUDE_DIRS%
echo Excluded Files:
echo   %EXCLUDE_FILES%
echo.

REM Clean up any NUL/nul files from the codebase first
echo Cleaning up NUL/nul files from codebase...
cd /d "%SOURCE_PATH%"
for /f "delims=" %%f in ('dir /s /b /a-d 2^>nul ^| findstr /i "\nul$"') do (
    echo Deleting: %%f
    del /f "%%f" 2>nul
)
echo NUL file cleanup completed.
echo.

REM Get timestamp in YYYY-MM-DD_HH-MM format
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set YEAR=%datetime:~0,4%
set MONTH=%datetime:~4,2%
set DAY=%datetime:~6,2%
set HOUR=%datetime:~8,2%
set MINUTE=%datetime:~10,2%
set TIMESTAMP=%YEAR%-%MONTH%-%DAY%_%HOUR%-%MINUTE%

REM Create backup directory if it doesn't exist
if not exist "%TARGET_PATH%" (
    echo Creating target directory: %TARGET_PATH%
    mkdir "%TARGET_PATH%"
)

REM Step 1: Run database backup
echo Step 1: Running database backup...
echo.
call "%PROJECT_PATH%\scripts\dbbackup_full.bat"
if errorlevel 1 (
    echo ERROR: Database backup failed!
    exit /b 1
)
echo.
echo Database backup completed successfully.
echo.

REM Step 2: Prepare temporary directory for copying files
echo Step 2: Preparing files for backup...
echo.

set TEMP_DIR=%TEMP%\codebase_backup_%TIMESTAMP%
set BACKUP_FILE=%TARGET_PATH%\codebasebackup_%TIMESTAMP%.zip
set DB_BACKUP_DIR=%PROJECT_PATH%\.dbbackup

echo Creating temporary directory: %TEMP_DIR%
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

REM Copy all project files to temp directory, excluding specific folders and files
echo Copying project files (this may take a moment)...
robocopy "%SOURCE_PATH%" "%TEMP_DIR%" /E /NFL /NDL /NJH /NJS ^
    /XD node_modules .next .git out dist build ^
    "%SOURCE_PATH%\crm-app\storage\prod\mysql" ^
    "%SOURCE_PATH%\crm-app\storage\dev\mysql" ^
    "%SOURCE_PATH%\storage\prod\mysql" ^
    "%SOURCE_PATH%\storage\dev\mysql" ^
    %EXCLUDE_DIRS% ^
    /XF *.sock *.lock *.pid %EXCLUDE_FILES%

if errorlevel 8 (
    echo ERROR: Failed to copy files!
    rmdir /s /q "%TEMP_DIR%"
    exit /b 1
)

REM Copy the latest SQL dump to temp directory root
echo Copying SQL dump to backup...
for /f "delims=" %%f in ('dir /b /o-d "%DB_BACKUP_DIR%\*.sql" 2^>nul') do (
    set LATEST_SQL=%%f
    goto :found_sql
)
:found_sql
if not defined LATEST_SQL (
    echo WARNING: No SQL dump found in %DB_BACKUP_DIR%
) else (
    copy "%DB_BACKUP_DIR%\%LATEST_SQL%" "%TEMP_DIR%\database_backup.sql" >nul
    echo Added: database_backup.sql
)
echo.

REM Step 3: Create zip archive from temp directory
echo Step 3: Creating archive...

REM Define 7-Zip path
set SEVENZIP_PATH=C:\Program Files\7-Zip\7z.exe

REM Check if 7-Zip is available
if exist "%SEVENZIP_PATH%" (
    echo Using 7-Zip to create archive...
    "%SEVENZIP_PATH%" a -tzip "%BACKUP_FILE%" "%TEMP_DIR%\*" -r

    if errorlevel 1 (
        echo ERROR: Failed to create zip archive with 7-Zip!
        rmdir /s /q "%TEMP_DIR%"
        exit /b 1
    )
    goto :backup_success
)

REM Fallback to tar if available (built-in on Windows 10+)
where tar >nul 2>nul
if not errorlevel 1 (
    echo Using tar to create archive...
    cd /d "%TEMP_DIR%"
    tar -a -cf "%BACKUP_FILE%" *

    if errorlevel 1 (
        echo ERROR: Failed to create archive with tar!
        rmdir /s /q "%TEMP_DIR%"
        exit /b 1
    )
    goto :backup_success
)

REM No suitable tool found
echo ERROR: Neither 7-Zip nor tar found!
echo Please install 7-Zip from https://www.7-zip.org/
echo Or use Windows 10+ which includes tar by default.
rmdir /s /q "%TEMP_DIR%"
exit /b 1

:backup_success
REM Clean up temporary directory
echo Cleaning up temporary files...
rmdir /s /q "%TEMP_DIR%"

echo.
echo ========================================
echo Backup completed successfully!
echo ========================================
echo Database backup: Completed
echo Codebase archive: %BACKUP_FILE%
echo SQL dump included: database_backup.sql (in zip root)
echo.

endlocal
