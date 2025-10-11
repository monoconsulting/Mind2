@echo off
:: ------------------------------------------------------------
:: rename.bat - Byter prefix på alla filer som börjar med XXXX_
:: Användning:  rename.bat NYTT_PREFIX
:: Exempel:     rename.bat CRAWL4AI
:: ------------------------------------------------------------

:: Kontrollera att argument har angetts
if "%~1"=="" (
    echo Användning: rename.bat NYTT_PREFIX
    echo Exempel: rename.bat CRAWL4AI
    exit /b
)

set "newprefix=%~1"

:: Aktivera variabelersättning i loopar
setlocal enabledelayedexpansion

echo Byter prefix "XXXX_" till "%newprefix%_" i alla filer...

for %%f in (XXXX_*) do (
    set "name=%%~nxf"
    set "newname=!name:XXXX_=%newprefix%_!"
    echo Byter "%%f" till "!newname!"
    ren "%%f" "!newname!"
)

endlocal

echo.
echo Klart!
pause
