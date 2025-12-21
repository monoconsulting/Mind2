@echo off
setlocal
call "%~dp0..\\create_missing_per_receipt_csv.bat" %*
endlocal

