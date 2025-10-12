@echo off
cd /d %~dp0\..\..
npx playwright test web/tests/2025-10-12_receipts_and_process_check.spec.ts --ui --ui-port=9338
