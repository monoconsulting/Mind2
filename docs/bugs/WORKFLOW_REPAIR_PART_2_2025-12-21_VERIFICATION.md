## Verification log (2025-12-21)

### Reports CSV helper (bat)

- `create_missing_per_receipt_csv.bat` runs from repo root and defaults to `--all` (includes receipts + fc-files + invoices + other imported file types).
- `reports/create_missing_per_receipt_csv.bat` delegates to the repo-root bat (single source of truth).

### DB / migrations (mojibake seed repair)

- Applied: `0048_repair_mojibake_seeded_prompts.sql`
  - Verified DB ledger update: `schema_migrations.filename='0048_repair_mojibake_seeded_prompts.sql'` exists (applied_at: `2025-12-21 13:08:54`).
  - Note: on apply, the migration runner warned that `0044..0047` checksums differ from the already-applied ledger; they were skipped (not changed as part of this task).

### Deterministic mojibake repair tooling

- Script (dry-run): `docker compose exec ai-api python -m scripts.repair_mojibake_db --tables ai_system_prompts`
  - Result: `rows_scanned=6`, `rows_updated=0`

### Playwright tests

- Spec: `web/tests/ai.spec.ts`
  - `@migrations` and `@mojibake-guard` pass.
- Report: `web/test-reports/2025-12-21_141127-mojibake-guard/html/index.html`
  - Artifacts include per-test `video.webm` and `test-finished-1.png` under `web/test-reports/2025-12-21_141127-mojibake-guard/_artifacts/`.

