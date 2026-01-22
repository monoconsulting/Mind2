@echo off
setlocal enableextensions enabledelayedexpansion

REM =============================================================================
REM create_codebase.bat
REM Creates an audit ZIP snapshot with required structure:
REM   /code, /dbbackup, /dockerlogs, /manifest
REM Output filename:
REM   MIND_codebase_YYYY-MM-DD_HH-mm.zip
REM =============================================================================

REM Resolve repo root (directory of this .bat)
set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

REM System prefix (mandatory)
set "SYSTEM_PREFIX=MIND"

REM Output directories
set "ARTIFACTS_DIR=%REPO_ROOT%\artifacts"
set "TOOLS_DIR=%REPO_ROOT%\tools\audit"

REM Staging directory (unique)
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd_HH-mm-ss')"`) do set "TS_FULL=%%I"
set "STAGING_DIR=%REPO_ROOT%\.audit_staging\%SYSTEM_PREFIX%_%TS_FULL%"

REM Timestamp for ZIP filename
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd_HH-mm')"`) do set "TS_ZIP=%%I"
set "ZIP_NAME=%SYSTEM_PREFIX%_codebase_%TS_ZIP%.zip"
set "ZIP_PATH=%ARTIFACTS_DIR%\%ZIP_NAME%"

REM Create folders
if not exist "%ARTIFACTS_DIR%" mkdir "%ARTIFACTS_DIR%"
if exist "%STAGING_DIR%" rmdir /s /q "%STAGING_DIR%"
mkdir "%STAGING_DIR%"
mkdir "%STAGING_DIR%\code"
mkdir "%STAGING_DIR%\dbbackup"
mkdir "%STAGING_DIR%\dockerlogs"
mkdir "%STAGING_DIR%\manifest"

REM -----------------------------------------------------------------------------
REM 1) Copy code into staging\code with exclusions
REM -----------------------------------------------------------------------------
echo [1/6] Copying code to staging...
REM Use robocopy for reliable copy + exclusions
robocopy "%REPO_ROOT%" "%STAGING_DIR%\code" /E ^
  /XD ".git" "node_modules" "venv" ".venv" "__pycache__" ".pytest_cache" ".mypy_cache" ".next" "dist" "build" "out" ".cache" "tmp" "temp" ".audit_staging" "artifacts" ^
  /XF ".env" ".env.*" "*.pem" "id_rsa" "kubeconfig" "*.pfx" "*.key" ^
  /NFL /NDL /NJH /NJS /NC /NS /NP >nul

REM -----------------------------------------------------------------------------
REM 2) Create DB backup into staging\dbbackup
REM -----------------------------------------------------------------------------
echo [2/6] Creating DB backup...
REM Prefer repo-provided scripts if they exist. Otherwise, capture a docker-based dump.
if exist "%REPO_ROOT%\dbbackup_full.bat" (
  call "%REPO_ROOT%\dbbackup_full.bat"
  REM If script produces a known file, copy it into staging\dbbackup
  REM Otherwise, copy any *.sql from repo root artifacts/log location if that is repo policy.
) else (
  REM Try docker-based dump (container/service names must match repo)
  REM The agent MUST ensure this command works in their environment and produces db_dump.sql.
  docker compose ps > "%STAGING_DIR%\dockerlogs\docker_compose_ps.txt" 2>nul
  docker compose logs --no-color > "%STAGING_DIR%\dockerlogs\docker_compose_logs.txt" 2>nul
  REM Attempt a mysqldump from a mysql container if present (agent may adjust container name, but must document in manifest)
  REM This file is a placeholder; agent must ensure it gets populated correctly.
  echo NOTE: DB dump command must be executed by the agent and documented in manifest.> "%STAGING_DIR%\dbbackup\README_DB_DUMP_REQUIRED.txt"
)

REM -----------------------------------------------------------------------------
REM 3) Capture docker logs into staging\dockerlogs (always)
REM -----------------------------------------------------------------------------
echo [3/6] Capturing Docker logs...
docker compose ps > "%STAGING_DIR%\dockerlogs\docker_compose_ps.txt" 2>nul
docker compose logs --no-color > "%STAGING_DIR%\dockerlogs\docker_compose_logs.txt" 2>nul

REM -----------------------------------------------------------------------------
REM 4) Create manifest files
REM -----------------------------------------------------------------------------
echo [4/6] Creating manifest...
if not exist "%TOOLS_DIR%\create_manifest.ps1" (
  echo ERROR: Missing tools\audit\create_manifest.ps1
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TOOLS_DIR%\create_manifest.ps1" ^
  -RepoRoot "%REPO_ROOT%" ^
  -StagingDir "%STAGING_DIR%" ^
  -ZipName "%ZIP_NAME%"

REM Create file inventory (pre-zip inventory of staging contents)
if not exist "%TOOLS_DIR%\write_file_inventory.py" (
  echo ERROR: Missing tools\audit\write_file_inventory.py
  exit /b 1
)
python "%TOOLS_DIR%\write_file_inventory.py" "%STAGING_DIR%" "%STAGING_DIR%\manifest\file_inventory_prezip.txt"

REM -----------------------------------------------------------------------------
REM 5) Create ZIP
REM -----------------------------------------------------------------------------
echo [5/6] Creating ZIP: %ZIP_PATH%
if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"

powershell -NoProfile -Command ^
  "Compress-Archive -Path '%STAGING_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force" || exit /b 1

REM -----------------------------------------------------------------------------
REM 6) Post-check ZIP for secrets (.env etc)
REM -----------------------------------------------------------------------------
echo [6/6] Verifying ZIP does not contain secrets...
powershell -NoProfile -Command ^
  "$z='%ZIP_PATH%';" ^
  "$bad=@(); " ^
  "Add-Type -AssemblyName System.IO.Compression.FileSystem; " ^
  "$zip=[System.IO.Compression.ZipFile]::OpenRead($z); " ^
  "foreach($e in $zip.Entries){ $n=$e.FullName; if($n -match '(^|/)\\.env($|/)' -or $n -match '\\.pem -or $n -match 'id_rsa' -or $n -match 'kubeconfig'){ $bad+=$n } } " ^
  "$zip.Dispose(); " ^
  "if($bad.Count -gt 0){ Write-Host 'ERROR: Secrets found in ZIP:'; $bad | ForEach-Object { Write-Host $_ }; exit 2 }" || exit /b 2

echo SUCCESS: Created audit ZIP: %ZIP_PATH%
exit /b 0
