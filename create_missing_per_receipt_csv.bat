@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  python scripts\missing_per_receipt_report.py --all
) else (
  python scripts\missing_per_receipt_report.py %*
)

endlocal
