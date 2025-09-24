@echo off
REM =====================================================================
REM File: docker_build_GPT_pull_nocache.bat
REM Purpose: Generic Docker Compose build script (reusable across projects)
REM Version: 1.6
REM Author: GPT-5 Thinking
REM Notes:
REM   - Edit only the EDIT ME section below for reuse.
REM   - Works with Docker Compose v2 ("docker compose") and v1 fallback.
REM   - Validates compose file before building.
REM   - Uses a fixed project name to avoid "disappearing" containers.
REM   - v1.5: Added AUTO_UP flag + early "up"/"down" fast-path commands.
REM   - v1.6: Added RUN_MODE to run without CLI params (BUILD/UP/DOWN).
REM =====================================================================

chcp 65001 >nul
setlocal ENABLEEXTENSIONS

REM =========================== EDIT ME ==================================
REM [OBLIGATORISKT] Namn på compose-fil (ligger i repo-roten du pekar ut).
set "COMPOSE_FILE=docker-compose.yml"

REM [OBLIGATORISKT] Stabilt projektnamn (använd ett kort, unikt, utan mellanslag).
set "COMPOSE_PROJECT_NAME=transkript2"

REM [OBLIGATORISKT] Relativ väg från denna .bat till katalogen där compose-filen ligger.
REM Exempel: om .bat ligger i /scripts och compose i repo-roten: set "REPO_ROOT_REL=.."
set "REPO_ROOT_REL=."

REM [VALFRITT] Byggläge: 1 = --no-cache, 0 = tillåt cache
set "BUILD_NO_CACHE=1"

REM [VALFRITT] Hämta senaste basbilder: 1 = --pull, 0 = hoppa över
set "BUILD_PULL=0"

REM [VALFRITT] Begränsa build till specifika services (blank = alla). Ex: "api worker"
set "TARGET_SERVICES="

REM [NYTT] Körläge när du dubbelklickar (inga CLI-parametrar behövs):
REM   BUILD = Bygg (validera + build). Kombinera med AUTO_UP=1 för automatisk start.
REM   UP    = Starta bara stacken (skippar build).
REM   DOWN  = Stäng ner stacken (skippar build).
set "RUN_MODE=BUILD"

REM [VALFRITT] Auto-start stack efter lyckad build: 1 = "up -d", 0 = starta inte
set "AUTO_UP=0"
REM ======================================================================

REM --- Lokala variabler (rör ej) ---------------------------------------
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%\%REPO_ROOT_REL%") do set "REPO_ROOT=%%~fI"

REM --- Hitta docker compose-kommandot -----------------------------------
set "DOCKER_COMPOSE_CMD=docker compose"
%DOCKER_COMPOSE_CMD% version >nul 2>&1
if errorlevel 1 (
  set "DOCKER_COMPOSE_CMD=docker-compose"
  %DOCKER_COMPOSE_CMD% version >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Neither "docker compose" nor "docker-compose" is available.
    echo         Install Docker Desktop or docker-compose and retry.
    exit /b 1
  )
)

REM --- Grundkontroller ---------------------------------------------------
where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker CLI not found in PATH.
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker daemon is not running or not accessible.
  exit /b 1
)

if not exist "%REPO_ROOT%\%COMPOSE_FILE%" (
  echo [ERROR] Compose file "%COMPOSE_FILE%" not found at "%REPO_ROOT%".
  exit /b 1
)

pushd "%REPO_ROOT%" >nul

REM =====================================================================
REM EARLY CONTROL COMMANDS
REM ---------------------------------------------------------------------
REM (Frivilligt) CLI override om man ändå kör i terminal:
REM   script.bat up   -> starta stacken direkt (skippar build)
REM   script.bat down -> stäng stacken direkt (skippar build)
REM OBS: Du BEHÖVER INTE använda detta; RUN_MODE hanterar normalfallet.
REM =====================================================================
if /I "%~1"=="up"   goto :EARLY_UP
if /I "%~1"=="down" goto :EARLY_DOWN

REM ===========================================================
REM RUN_MODE-styrning (dubbelklick-scenario, inga CLI-parametrar)
REM ===========================================================
if /I "%RUN_MODE%"=="UP"   goto :EARLY_UP
if /I "%RUN_MODE%"=="DOWN" goto :EARLY_DOWN
REM Fortsätt till BUILD-vägen om RUN_MODE=BUILD (default)
goto :CONTINUE_BUILD

:EARLY_UP
echo [INFO] RUN_MODE/CLI: bringing project "%COMPOSE_PROJECT_NAME%" UP.
if "%TARGET_SERVICES%"=="" (
  %DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" up -d
) else (
  %DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" up -d %TARGET_SERVICES%
)
if errorlevel 1 (
  echo [ERROR] Failed to start containers.
  popd >nul
  exit /b 1
)
echo [SUCCESS] Stack is up.
popd >nul
exit /b 0

:EARLY_DOWN
echo [INFO] RUN_MODE/CLI: bringing project "%COMPOSE_PROJECT_NAME%" DOWN (volumes are kept).
%DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" down
if errorlevel 1 (
  echo [ERROR] Failed to bring stack down.
  popd >nul
  exit /b 1
)
echo [SUCCESS] Stack is down.
popd >nul
exit /b 0

:CONTINUE_BUILD
REM --- Validera Compose --------------------------------------------------
%DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" config -q
if errorlevel 1 (
  echo [ERROR] Compose validation failed. Fix YAML and retry.
  popd >nul
  exit /b 1
)

REM --- Byggflaggor -------------------------------------------------------
set "BUILD_FLAGS="
if "%BUILD_NO_CACHE%"=="1" set "BUILD_FLAGS=%BUILD_FLAGS% --no-cache"
if "%BUILD_PULL%"=="1"     set "BUILD_FLAGS=%BUILD_FLAGS% --pull"

echo [INFO] Building images for project "%COMPOSE_PROJECT_NAME%" using "%COMPOSE_FILE%".
if "%TARGET_SERVICES%"=="" (
  %DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" build %BUILD_FLAGS%
) else (
  %DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" build %BUILD_FLAGS% %TARGET_SERVICES%
)

if errorlevel 1 (
  echo [ERROR] Build failed.
  popd >nul
  exit /b 1
)

echo [SUCCESS] Build completed.

REM --- Optional auto-up after successful build --------------------------
if "%AUTO_UP%"=="1" (
  echo [INFO] AUTO_UP=1 -> starting stack with "up -d".
  if "%TARGET_SERVICES%"=="" (
    %DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" up -d
  ) else (
    %DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" up -d %TARGET_SERVICES%
  )
  if errorlevel 1 (
    echo [ERROR] Auto-start failed. Inspect logs and run "up" manually.
    popd >nul
    exit /b 1
  )
  echo [SUCCESS] Auto-start completed.
)

echo.
echo [INFO] Images in this project:
%DOCKER_COMPOSE_CMD% -f "%COMPOSE_FILE%" -p "%COMPOSE_PROJECT_NAME%" images
echo.

popd >nul
exit /b 0
