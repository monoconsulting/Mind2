@echo off
REM Test: Card Matching Auto-Match (Production Mode)
REM Runs against production build on port 8008
REM Prerequisites: mind_docker_build_nocache.bat + mind_docker_compose_up.bat
REM Usage:
REM   2025-10-21_card_matching_auto_match_prod.bat          (headed mode)
REM   2025-10-21_card_matching_auto_match_prod.bat headless (headless mode)

if /i "%1"=="headless" (
    npx playwright test web/tests/2025-10-21_card_matching_auto_match.spec.ts
) else (
    npx playwright test web/tests/2025-10-21_card_matching_auto_match.spec.ts --headed
)
