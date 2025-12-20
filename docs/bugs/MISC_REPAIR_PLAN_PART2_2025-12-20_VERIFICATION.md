## Verification log (2025-12-20)

Branch: `fix/original-currency-amount-repair`

### Migrations

- Applied: `0046_fix_unified_files_amount_columns.sql`
  - `unified_files.exchange_rate`: `decimal(12,6)` default `NULL`
  - `unified_files.gross_amount_sek`: `decimal(12,2)` default `NULL`
  - Post-migration checks:
    - `COUNT(exchange_rate = 0) = 0`
    - `COUNT(gross_amount_sek = 0) = 0`
    - `COUNT(net_amount_sek = 0) = 0`
    - `COUNT(currency='SEK' AND exchange_rate IS NULL) = 0`
- Applied: `0047_create_view_v_receipt_missing_status.sql`
  - View compiles and returns rows: `SELECT COUNT(*) FROM v_receipt_missing_status;` → `14`

### Deterministic fill (Case B)

- Receipt ID: `81c5c6e9-7664-4603-855e-d74870fed7c0` (SEK)
  - Before: `total_vat_25=NULL`, `total_vat_12=NULL`, `total_vat_6=NULL`
  - Source data: `other_data.vat_summary[0].vat_rate_percent = 25`, `vat_amount = 145.42`
  - After AI3 persist: `total_vat_25=145.42` (buckets 12/6 remain NULL)
  - Verified DB update: `unified_files.total_vat_25` updated for this receipt.

### Foreign currency UI display

- Receipt ID: `ef2023c0-ab16-4845-a182-e83d5affc698` (USD, merchant "Midjourney Inc")
- Verified via Playwright: Receipts + Process tables display `gross_amount_display/net_amount_display` using `currency` (USD) rather than SEK conversions.

### Playwright test

- Spec: `web/tests/2025-10-12_receipts_and_process_check.spec.ts`
  - Fail (before fix): missing `currency` field in `GET /ai/api/receipts`
  - Pass (after fix): original-currency amounts shown in both tables
- Report: `web/test-reports/2025-12-20_211805/html/index.html`

