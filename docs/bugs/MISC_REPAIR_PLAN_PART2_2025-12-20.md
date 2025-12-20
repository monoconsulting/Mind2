
## Task plan (with subtasks)

### Task A – Create branch and baseline safety checks

A1. Create a dedicated branch (example): `fix/original-currency-amount-repair`.
A2. Confirm migrations framework is working and the migration ledger will pick up `0046_...sql`.
A3. Confirm the current DB schema for `unified_files` includes: `exchange_rate`, `gross_amount_sek`, `net_amount_sek`, `total_vat_25/12/6`, `gross_amount_original`, `net_amount_original`, `currency`.

**Acceptance for Task A:** branch exists, migration system will apply new migration.

---

### Task B – Apply DB migration (precision + defaults)

B1. Add migration file: `database/migrations/0046_fix_unified_files_amount_columns.sql` exactly as provided.
B2. Apply migrations in your environment.

**Verification queries (run after migration):**

* `SHOW COLUMNS FROM unified_files LIKE 'exchange_rate';` must show `decimal(12,6)` and default NULL.
* `SHOW COLUMNS FROM unified_files LIKE 'gross_amount_sek';` must show `decimal(12,2)` and default NULL.
* Check legacy zeros are removed:

  * `SELECT COUNT(*) FROM unified_files WHERE exchange_rate = 0;` must be 0.
  * `SELECT COUNT(*) FROM unified_files WHERE gross_amount_sek = 0;` must be 0.
  * `SELECT COUNT(*) FROM unified_files WHERE net_amount_sek = 0;` must be 0.
* SEK invariant:

  * `SELECT COUNT(*) FROM unified_files WHERE currency='SEK' AND exchange_rate IS NULL;` must be 0.

**Acceptance for Task B:** schema matches and the normalization updates completed.

---

### Task C – Backend: deterministic amount repairs during AI3 persist

C1. Patch `backend/src/api/ai_processing.py` with the provided diff.
C2. Confirm the helper functions:

* Parse VAT summary from `unified_files.other_data.vat_summary`
* Compute VAT totals for 25/12/6
* Repair missing net or gross only when deterministically computable:

  * If VAT summary contains exactly one row with `vat_amount` and `gross_amount`, compute net.
  * If gross+net present and VAT totals absent, compute VAT difference.
  * Allocate VAT difference to a bucket only if exactly one VAT rate is detected.
* Enforce SEK invariant:

  * `currency` defaults to `SEK` when missing
  * `exchange_rate` becomes `1.000000` for SEK
  * `gross_amount_sek/net_amount_sek` mirror original for SEK when missing
    C3. Ensure `_persist_extraction_result()` now updates:
* `total_vat_25`, `total_vat_12`, `total_vat_6`

**Acceptance for Task C:** When AI3 yields incomplete totals but enough info exists, DB rows get filled with no blanks left behind for gross/net/VAT totals (within deterministic rules).

---

### Task D – Backend: API returns original currency fields for list + detail

D1. Patch `backend/src/api/receipts.py` with the provided diff.
D2. Confirm `GET /api/v1/receipts` returns **additional fields** per row:

* `currency`
* `gross_amount_original`, `net_amount_original`
* `gross_amount_display`, `net_amount_display`
  D3. Confirm `GET /api/v1/receipts/{id}` returns the same additional fields.

**Acceptance for Task D:** API supports UI displaying original currency amounts without changing existing SEK-based fields used for matching/backward compatibility.

---

### Task E – Frontend: show original currency in Process + Receipts tables

E1. Patch:

* `main-system/app-frontend/src/ui/pages/Process.jsx`
* `main-system/app-frontend/src/ui/pages/Receipts.jsx`
  with the provided diffs.

E2. Confirm table cells display using:

* `gross_amount_display/net_amount_display` + `currency` (original currency)

E3. Confirm item rows in Receipts view format currency using `item.currency` (fallback to receipt currency).

**Acceptance for Task E:** Any receipt that has `currency != SEK` displays amounts in that currency in UI tables. SEK receipts remain SEK.

---

### Task F – SoT documentation updates

F1. Patch:

* `docs/source_of_truth/40_DATA_MODEL.md` (column types/defaults + legacy meaning)
* `docs/source_of_truth/50_PIPELINES_AND_JOBS.md` (persist-stage note + VAT summary mention)

**Acceptance for Task F:** SoT matches schema + persistence behavior.

---

## Test procedure (must do)

### 1) Regression: existing SEK receipts

* Pick 5 SEK receipts already processed.
* Confirm UI shows SEK amounts as before.
* Confirm matching workflows are unaffected (do not break AI5/FC matching).

### 2) Deterministic fill cases

Find receipts where one or more fields are missing:

* Case A: gross present, net missing, VAT summary has one row with vat_amount+gross_amount.

  * After re-run persist step (or reprocess receipt), net must be filled.
* Case B: gross and net present, VAT totals missing.

  * VAT difference should be computed and stored; bucket only if single VAT rate detected.
* Case C: currency missing in extraction.

  * Stored currency must be `SEK`, exchange_rate `1.000000`.

### 3) Foreign currency display

* Identify at least one foreign currency receipt (EUR/USD etc).
* Confirm UI table rows show currency symbol/code for that currency and values match `*_original`.

### 4) DB integrity spot checks

* Ensure no rows have `exchange_rate=0` anymore.
* Ensure `gross_amount_sek/net_amount_sek` are NULL unless deterministically computed.

---

## Deliverables the agent must produce

1. The new migration file added and applied.
2. Code changes exactly in the five files referenced above.
3. A short verification log (markdown) listing:

* Migration applied OK
* Example receipt IDs tested (SEK + foreign)
* Before/after values for one deterministic fill case

---
Finally, implement the script/view that lists "what is missing per receipt" (unified_files + related tables)
C) Minimal agent addendum (EN) to include the view/report

Lägg till detta som Task G i agentens instruktion:

Task G — Create view + report (no scope creep)
G1. Add migration: database/migrations/0047_create_view_v_receipt_missing_status.sql (provided).
G2. Apply migrations.
G3. Add report file: docs/reports/RECEIPT_MISSING_STATUS_REPORT.sql (provided).
G4. Verify view compiles:

SELECT COUNT(*) FROM v_receipt_missing_status;

SELECT * FROM v_receipt_missing_status LIMIT 3;

Acceptance: View returns rows for unified_files.file_type='receipt' and report queries execute.
-- 0047_create_view_v_receipt_missing_status.sql
--
-- Purpose
-- -------
-- Create a single view that the backend/UI (and operators) can query to see:
-- - Receipt amounts in original currency (display fields)
-- - Missing required fields (comma-separated list + count)
-- - Warnings (sanity checks)
-- - Receipt items aggregation + header vs items diffs
-- - Latest workflow_run + latest workflow_stage_run
-- - AI history row count (quick indicator)
--
-- MySQL: 8.x
-- Tables: unified_files, receipt_items, workflow_runs, workflow_stage_runs, ai_processing_history

CREATE OR REPLACE VIEW v_receipt_missing_status AS
SELECT
  uf.id AS file_id,
  uf.file_type,
  uf.file_name,

  /* Display currency + amounts: always prefer *_original */
  COALESCE(NULLIF(TRIM(uf.currency), ''), 'SEK') AS currency,
  COALESCE(uf.gross_amount_original, uf.gross_amount) AS gross_amount_display,
  COALESCE(uf.net_amount_original, uf.net_amount)     AS net_amount_display,

  uf.purchase_datetime,
  uf.payment_type,
  uf.expense_type,

  /* Card info */
  uf.credit_card_brand_short,
  uf.credit_card_last_4_digits,

  /* VAT header breakdown */
  uf.total_vat_25,
  uf.total_vat_12,
  uf.total_vat_6,

  /* FX / SEK mirror fields */
  uf.exchange_rate,
  uf.gross_amount_sek,
  uf.net_amount_sek,

  /* Optional FX metadata (if other_data is valid JSON; otherwise NULL) */
  CASE
    WHEN uf.other_data IS NOT NULL AND JSON_VALID(uf.other_data)
      THEN JSON_UNQUOTE(JSON_EXTRACT(uf.other_data, '$.fx_source'))
    ELSE NULL
  END AS fx_source,
  CASE
    WHEN uf.other_data IS NOT NULL AND JSON_VALID(uf.other_data)
      THEN JSON_UNQUOTE(JSON_EXTRACT(uf.other_data, '$.fx_rate_date'))
    ELSE NULL
  END AS fx_rate_date,

  /* Items aggregate */
  COALESCE(ri_agg.item_count, 0) AS item_count,
  ri_agg.gross_items_sum,
  ri_agg.net_items_sum,
  ri_agg.vat_items_sum,

  /* Header vs items diffs */
  CASE
    WHEN COALESCE(uf.gross_amount_original, uf.gross_amount) IS NULL THEN NULL
    WHEN ri_agg.gross_items_sum IS NULL THEN NULL
    ELSE (COALESCE(uf.gross_amount_original, uf.gross_amount) - ri_agg.gross_items_sum)
  END AS diff_gross_header_minus_items,

  CASE
    WHEN COALESCE(uf.net_amount_original, uf.net_amount) IS NULL THEN NULL
    WHEN ri_agg.net_items_sum IS NULL THEN NULL
    ELSE (COALESCE(uf.net_amount_original, uf.net_amount) - ri_agg.net_items_sum)
  END AS diff_net_header_minus_items,

  /* Missing fields list */
  CONCAT_WS(',',
    IF(uf.purchase_datetime IS NULL, 'purchase_datetime', NULL),
    IF(uf.payment_type IS NULL OR uf.payment_type = '', 'payment_type', NULL),
    IF(uf.expense_type IS NULL OR uf.expense_type = '', 'expense_type', NULL),

    IF(uf.currency IS NULL OR TRIM(uf.currency) = '', 'currency', NULL),

    IF(COALESCE(uf.gross_amount_original, uf.gross_amount) IS NULL, 'gross_amount', NULL),
    IF(COALESCE(uf.net_amount_original, uf.net_amount) IS NULL, 'net_amount', NULL),

    IF(
      (uf.total_vat_25 IS NULL AND uf.total_vat_12 IS NULL AND uf.total_vat_6 IS NULL),
      'vat_breakdown(total_vat_25/12/6)',
      NULL
    ),

    IF(
      (COALESCE(NULLIF(TRIM(uf.currency), ''), 'SEK') <> 'SEK')
      AND (uf.gross_amount_sek IS NULL OR uf.net_amount_sek IS NULL),
      'sek_amounts(gross_amount_sek/net_amount_sek)',
      NULL
    ),

    IF(
      (COALESCE(NULLIF(TRIM(uf.currency), ''), 'SEK') <> 'SEK')
      AND (uf.exchange_rate IS NULL),
      'exchange_rate',
      NULL
    ),

    IF(
      (uf.payment_type = 'card')
      AND (uf.credit_card_brand_short IS NULL OR uf.credit_card_brand_short = ''),
      'credit_card_brand_short',
      NULL
    ),

    IF(
      (uf.payment_type = 'card')
      AND (uf.credit_card_last_4_digits IS NULL),
      'credit_card_last_4_digits',
      NULL
    ),

    IF(COALESCE(ri_agg.item_count, 0) = 0, 'receipt_items', NULL)
  ) AS missing_fields,

  /* Missing count (numeric) */
  (
    (uf.purchase_datetime IS NULL)
    + (uf.payment_type IS NULL OR uf.payment_type = '')
    + (uf.expense_type IS NULL OR uf.expense_type = '')
    + (uf.currency IS NULL OR TRIM(uf.currency) = '')
    + (COALESCE(uf.gross_amount_original, uf.gross_amount) IS NULL)
    + (COALESCE(uf.net_amount_original, uf.net_amount) IS NULL)
    + ((uf.total_vat_25 IS NULL AND uf.total_vat_12 IS NULL AND uf.total_vat_6 IS NULL))
    + ((COALESCE(NULLIF(TRIM(uf.currency), ''), 'SEK') <> 'SEK') AND (uf.gross_amount_sek IS NULL OR uf.net_amount_sek IS NULL))
    + ((COALESCE(NULLIF(TRIM(uf.currency), ''), 'SEK') <> 'SEK') AND (uf.exchange_rate IS NULL))
    + ((uf.payment_type = 'card') AND (uf.credit_card_brand_short IS NULL OR uf.credit_card_brand_short = ''))
    + ((uf.payment_type = 'card') AND (uf.credit_card_last_4_digits IS NULL))
    + (COALESCE(ri_agg.item_count, 0) = 0)
  ) AS missing_count,

  /* Warnings list */
  CONCAT_WS(',',
    IF(
      COALESCE(uf.gross_amount_original, uf.gross_amount) IS NOT NULL
      AND COALESCE(uf.net_amount_original, uf.net_amount) IS NOT NULL
      AND COALESCE(uf.gross_amount_original, uf.gross_amount) < COALESCE(uf.net_amount_original, uf.net_amount),
      'gross_lt_net',
      NULL
    ),

    IF(
      COALESCE(uf.gross_amount_original, uf.gross_amount) IS NOT NULL
      AND COALESCE(uf.net_amount_original, uf.net_amount) IS NOT NULL
      AND ABS(COALESCE(uf.gross_amount_original, uf.gross_amount) - COALESCE(uf.net_amount_original, uf.net_amount)) < 0.01
      AND (uf.total_vat_25 IS NOT NULL OR uf.total_vat_12 IS NOT NULL OR uf.total_vat_6 IS NOT NULL),
      'vat_present_but_gross_equals_net',
      NULL
    ),

    IF(
      COALESCE(ri_agg.item_count, 0) > 0
      AND COALESCE(uf.gross_amount_original, uf.gross_amount) IS NOT NULL
      AND ri_agg.gross_items_sum IS NOT NULL
      AND ABS(COALESCE(uf.gross_amount_original, uf.gross_amount) - ri_agg.gross_items_sum) > 2.00,
      'gross_header_items_mismatch_gt_2',
      NULL
    ),

    IF(
      COALESCE(ri_agg.item_count, 0) > 0
      AND COALESCE(uf.net_amount_original, uf.net_amount) IS NOT NULL
      AND ri_agg.net_items_sum IS NOT NULL
      AND ABS(COALESCE(uf.net_amount_original, uf.net_amount) - ri_agg.net_items_sum) > 2.00,
      'net_header_items_mismatch_gt_2',
      NULL
    )
  ) AS warnings,

  /* Latest workflow run */
  wr_latest.id AS latest_workflow_run_id,
  wr_latest.workflow_name AS latest_workflow_name,
  wr_latest.status AS latest_workflow_status,
  wr_latest.started_at AS latest_workflow_started_at,
  wr_latest.completed_at AS latest_workflow_completed_at,

  /* Latest stage within latest workflow run */
  wsr_latest.stage_name AS latest_stage_name,
  wsr_latest.status AS latest_stage_status,
  wsr_latest.started_at AS latest_stage_started_at,
  wsr_latest.completed_at AS latest_stage_completed_at,

  /* AI history count */
  COALESCE(ai_agg.ai_history_rows, 0) AS ai_history_rows

FROM unified_files uf

/* Items aggregate */
LEFT JOIN (
  SELECT
    main_id,
    COUNT(*) AS item_count,
    SUM(item_total_price_inc_vat) AS gross_items_sum,
    SUM(item_total_price_ex_vat)  AS net_items_sum,
    SUM(vat)                      AS vat_items_sum
  FROM receipt_items
  GROUP BY main_id
) ri_agg
  ON ri_agg.main_id = uf.id

/* Latest workflow run per file: max(started_at), tie-break by max(id) */
LEFT JOIN (
  SELECT w1.*
  FROM workflow_runs w1
  INNER JOIN (
    SELECT file_id, MAX(started_at) AS max_started_at
    FROM workflow_runs
    GROUP BY file_id
  ) w2
    ON w2.file_id = w1.file_id
   AND w2.max_started_at = w1.started_at
  INNER JOIN (
    SELECT file_id, started_at, MAX(id) AS max_id
    FROM workflow_runs
    GROUP BY file_id, started_at
  ) w3
    ON w3.file_id = w1.file_id
   AND w3.started_at = w1.started_at
   AND w3.max_id = w1.id
) wr_latest
  ON wr_latest.file_id = uf.id

/* Latest stage run per workflow_run: max(started_at), tie-break by max(id) */
LEFT JOIN (
  SELECT s1.*
  FROM workflow_stage_runs s1
  INNER JOIN (
    SELECT workflow_run_id, MAX(started_at) AS max_started_at
    FROM workflow_stage_runs
    GROUP BY workflow_run_id
  ) s2
    ON s2.workflow_run_id = s1.workflow_run_id
   AND s2.max_started_at = s1.started_at
  INNER JOIN (
    SELECT workflow_run_id, started_at, MAX(id) AS max_id
    FROM workflow_stage_runs
    GROUP BY workflow_run_id, started_at
  ) s3
    ON s3.workflow_run_id = s1.workflow_run_id
   AND s3.started_at = s1.started_at
   AND s3.max_id = s1.id
) wsr_latest
  ON wsr_latest.workflow_run_id = wr_latest.id

/* AI history aggregate */
LEFT JOIN (
  SELECT file_id, COUNT(*) AS ai_history_rows
  FROM ai_processing_history
  GROUP BY file_id
) ai_agg
  ON ai_agg.file_id = uf.id

WHERE uf.file_type = 'receipt';

---
/* -------------------------------------------------------------------------
RECEIPT_MISSING_STATUS_REPORT.sql

Requires:
- View: v_receipt_missing_status
------------------------------------------------------------------------- */

-- 1) Queue/Process style list: what is most broken right now?
SELECT
  file_id,
  file_name,
  currency,
  gross_amount_display,
  net_amount_display,
  missing_count,
  missing_fields,
  warnings,
  latest_workflow_status,
  latest_stage_name,
  latest_stage_status,
  ai_history_rows
FROM v_receipt_missing_status
ORDER BY
  (latest_workflow_status IN ('failed','error')) DESC,
  (latest_workflow_status IN ('running','queued')) DESC,
  missing_count DESC,
  latest_workflow_started_at DESC,
  file_id DESC;

-- 2) Receipts missing VAT breakdown but have amounts (common AI4 blocker)
SELECT
  file_id,
  file_name,
  currency,
  gross_amount_display,
  net_amount_display,
  total_vat_25, total_vat_12, total_vat_6,
  missing_fields,
  warnings
FROM v_receipt_missing_status
WHERE
  (gross_amount_display IS NOT NULL OR net_amount_display IS NOT NULL)
  AND (total_vat_25 IS NULL AND total_vat_12 IS NULL AND total_vat_6 IS NULL)
ORDER BY file_id DESC;

-- 3) Missing receipt items (common reason header-vs-items validation fails)
SELECT
  file_id,
  file_name,
  currency,
  gross_amount_display,
  net_amount_display,
  item_count,
  missing_fields,
  latest_workflow_status,
  latest_stage_name,
  latest_stage_status
FROM v_receipt_missing_status
WHERE item_count = 0
ORDER BY latest_workflow_started_at DESC, file_id DESC;

-- 4) Header vs items mismatch (potential OCR/item parsing issues)
SELECT
  file_id,
  file_name,
  currency,
  gross_amount_display,
  gross_items_sum,
  diff_gross_header_minus_items,
  net_amount_display,
  net_items_sum,
  diff_net_header_minus_items,
  warnings
FROM v_receipt_missing_status
WHERE
  warnings LIKE '%_mismatch_gt_2%'
ORDER BY
  ABS(COALESCE(diff_gross_header_minus_items, 0)) DESC,
  ABS(COALESCE(diff_net_header_minus_items, 0)) DESC;

-- 5) Foreign currency receipts missing SEK conversion fields (should remain NULL unless deterministic conversion exists)
SELECT
  file_id,
  file_name,
  currency,
  gross_amount_display,
  net_amount_display,
  exchange_rate,
  gross_amount_sek,
  net_amount_sek,
  missing_fields
FROM v_receipt_missing_status
WHERE currency <> 'SEK'
ORDER BY
  (exchange_rate IS NULL) DESC,
  (gross_amount_sek IS NULL OR net_amount_sek IS NULL) DESC,
  file_id DESC;

-- 6) “Top reasons” summary (counts)
SELECT reason, cnt
FROM (
  SELECT 'missing_purchase_datetime' AS reason, SUM(purchase_datetime IS NULL) AS cnt
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'missing_payment_type', SUM(payment_type IS NULL OR payment_type = '')
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'missing_expense_type', SUM(expense_type IS NULL OR expense_type = '')
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'missing_gross', SUM(gross_amount_display IS NULL)
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'missing_net', SUM(net_amount_display IS NULL)
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'missing_vat_breakdown', SUM(total_vat_25 IS NULL AND total_vat_12 IS NULL AND total_vat_6 IS NULL)
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'missing_receipt_items', SUM(item_count = 0)
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'foreign_missing_exchange_rate', SUM(currency <> 'SEK' AND exchange_rate IS NULL)
  FROM v_receipt_missing_status

  UNION ALL
  SELECT 'foreign_missing_sek_amounts', SUM(currency <> 'SEK' AND (gross_amount_sek IS NULL OR net_amount_sek IS NULL))
  FROM v_receipt_missing_status
) t
ORDER BY cnt DESC, reason ASC;
---


- Create a batfile that creates the lists for all receipts in as a csv-file
- Store this csv-file in the folder reports with name "missing_per_receipt_{date-time}.csv"


