@echo off
REM Test: Card Matching Auto-Match (Development Mode)
REM Runs against Vite dev server on port 5169 with hot-reload
REM Prerequisites: mind_docker_compose_up.bat running
REM Usage:
REM   2025-10-21_card_matching_auto_match_dev.bat          (headed mode)
REM   2025-10-21_card_matching_auto_match_dev.bat headless (headless mode)

if /i "%1"=="headless" (
    npx playwright test web/tests/2025-10-21_card_matching_auto_match.spec.ts --config=playwright.dev.config.ts
) else (
    npx playwright test web/tests/2025-10-21_card_matching_auto_match.spec.ts --config=playwright.dev.config.ts --headed
)
