rem @echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === USER SETTINGS =========================================================
set "SOURCE=E:\projects\fasttranskript"
set "DEST=\\192.168.1.165\backup\fasttranskript"
set "STAGING_DIR=C:\Temp"

REM -- Network Credentials (if DEST is a password-protected UNC path)
set "NET_USER=mattias"
set "NET_PWD=M0N0F1L3w54lMqiu8.!"

REM -- MariaDB/MySQL (dump runs INSIDE the container)
set "MYSQL_CONTAINER=fasttranskript-mariadb"
set "MYSQL_USER=backup"
set "MYSQL_PWD=F0lsejijflillai"
set "MYSQL_DB=fasttranskript"
set "MYSQL_PORT=3308"

REM -- Qdrant (snapshot runs INSIDE the container)
set "QDRANT_ENABLED=true"
set "QDRANT_URL=http://localhost:6333"
set "QDRANT_CONTAINER=fasttranskript-qdrant"
set "QDRANT_COLLECTION=fasttranskript"

REM 7-Zip executable
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"
REM ==========================================================================
set "DUMP_SUBDIR=_dbdumps"

REM ---- Sanity checks (fail fast if anything is missing) --------------------
echo [INFO] Performing sanity checks...
if not exist "%STAGING_DIR%\" (echo [ERROR] Staging directory not found at "%STAGING_DIR%". Please create it. & exit /b 1)
if not exist "%SOURCE%\" (echo [ERROR] Source directory not found at "%SOURCE%". & exit /b 1)

REM Timestamp & Paths
for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%~I"
for %%A in ("%SOURCE%\.") do set "SRCNAME=%%~nxA"
set "DUMP_DIR=%SOURCE%\%DUMP_SUBDIR%"
set "SQL_FILE=%DUMP_DIR%\%MYSQL_DB%_%TS%.sql"
set "SQL_ZIP=%DUMP_DIR%\%MYSQL_DB%_%TS%.zip"
set "FINAL_ZIP=%DEST%\%SRCNAME%_%TS%.zip"

REM --- Directory Verification -----------------------------------------------
mkdir "%DUMP_DIR%" 2>nul
echo [INFO] Verifying destination directory: %DEST%
mkdir "%DEST%" 2>nul
if not exist "%DEST%\" (
    echo [ERROR] Destination directory "%DEST%" appears to be offline.
    exit /b 1
)
echo [INFO] Directories are ready.

REM --- 1) Full MariaDB/MySQL dump inside the container ----------------------
REM echo [INFO] Dumping database '%MYSQL_DB%' from container '%MYSQL_CONTAINER%'...
REM docker exec -e MYSQL_PWD=%MYSQL_PWD% -i "%MYSQL_CONTAINER%" mysqldump --no-defaults --protocol=TCP --host=127.0.0.1 --port="%MYSQL_PORT%" -u%MYSQL_USER% --databases %MYSQL_DB% --routines --events --triggers --single-transaction --quick > "%SQL_FILE%"
REM if %ERRORLEVEL% neq 0 (
REM    echo [ERROR] mysqldump failed. & del /q "%SQL_FILE%" 2>nul & exit /b 1
REM)
REM echo [INFO] Database dump successful.

REM --- 1) Full MariaDB/MySQL dump (running locally, connecting to container) ---
echo [INFO] Dumping database '%MYSQL_DB%' by connecting to port %MYSQL_PORT%...
mysqldump --no-defaults --column-statistics=0 --protocol=TCP --host=127.0.0.1 --port=%MYSQL_PORT% -u%MYSQL_USER% -p%MYSQL_PWD% --databases %MYSQL_DB% --routines --events --triggers --single-transaction --quick > "%SQL_FILE%"

REM --- 1.5) Qdrant Snapshot Backup ------------------------------------------
if /I "%QDRANT_ENABLED%"=="true" (
    echo [INFO] Creating Qdrant snapshot for collection '%QDRANT_COLLECTION%'...
    set "SNAPSHOT_FILENAME="
    for /f "tokens=4 delims=:{}\", " %%F in ('curl -s -X POST "%QDRANT_URL%/collections/%QDRANT_COLLECTION%/snapshots"') do (
        set "SNAPSHOT_FILENAME=%%~F"
    )

    if not defined SNAPSHOT_FILENAME (
        echo [ERROR] Failed to create Qdrant snapshot or parse filename. Check Qdrant URL and collection name.
        exit /b 1
    )
    echo [INFO] Snapshot created: %SNAPSHOT_FILENAME%

    echo [INFO] Copying snapshot from container '%QDRANT_CONTAINER%'...
    docker cp "%QDRANT_CONTAINER%:/qdrant/storage/snapshots/%SNAPSHOT_FILENAME%" "%DUMP_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to copy snapshot from Docker container. Check container name.
        exit /b 1
    )

    echo [INFO] Cleaning up snapshot from container...
    curl -s -X DELETE "%QDRANT_URL%/collections/%QDRANT_COLLECTION%/snapshots/%SNAPSHOT_FILENAME%" >nul
)

REM --- 2) Zip the SQL and remove the raw .sql --------------------------------
echo [INFO] Compressing SQL dump...
"%SEVENZIP%" a -tzip "%SQL_ZIP%" "%SQL_FILE%" >nul
del /q "%SQL_FILE%"

REM --- 3) Zip the entire SOURCE (incl. the new SQL zip) into DEST ------------
set "LOCAL_FINAL_ZIP=%STAGING_DIR%\%SRCNAME%_%TS%.zip"
echo [INFO] Staging final archive to: "%LOCAL_FINAL_ZIP%"

pushd "%SOURCE%"
echo [INFO] Creating temporary exclusion list...
(
    echo .git
    echo node_modules
    echo storage\app
    echo storage\framework
    echo storage\logs
) > exclude_list.txt

echo [INFO] Compressing source folder to local staging drive...
"%SEVENZIP%" a -tzip "%LOCAL_FINAL_ZIP%" . -r -ssw -x@exclude_list.txt >nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 7-Zip failed during local archive creation.
    del exclude_list.txt 2>nul & del "%LOCAL_FINAL_ZIP%" 2>nul & popd & exit /b 1
)
del exclude_list.txt
popd

REM CONNECT AND MOVE: Authenticate, transfer, and disconnect.
set "NET_SHARE=\\192.168.1.165\backup"
echo [INFO] Connecting to network share: %NET_SHARE%
net use "%NET_SHARE%" /user:%NET_USER% %NET_PWD% >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to authenticate to network share. Check credentials.
    echo [ERROR] The completed backup file is available at: "%LOCAL_FINAL_ZIP%"
    exit /b 1
)

echo [INFO] Moving completed archive to: "%FINAL_ZIP%"
move /Y "%LOCAL_FINAL_ZIP%" "%FINAL_ZIP%" >nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to move archive to the network destination.
    echo [ERROR] The completed backup file is available at: "%LOCAL_FINAL_ZIP%"
    net use "%NET_SHARE%" /delete >nul 2>&1
    exit /b 1
)

echo [INFO] Disconnecting from network share...
net use "%NET_SHARE%" /delete >nul 2>&1

echo.
echo [OK] Backup created successfully: "%FINAL_ZIP%"
endlocal