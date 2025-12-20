@echo off
setlocal
cd /d %~dp0\..

python scripts\missing_per_receipt_report.py

endlocal

