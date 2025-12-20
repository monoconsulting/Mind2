-- Migration 0047: Create view v_receipt_missing_status
-- Date: 2025-12-20
-- Purpose:
-- Create a single view that operators (and backend/UI) can query to see:
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
  COALESCE(NULLIF(uf.original_filename, ''), NULLIF(uf.original_file_name, ''), uf.id) AS file_name,

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
  wr_latest.workflow_key AS latest_workflow_name,
  wr_latest.status AS latest_workflow_status,
  wr_latest.created_at AS latest_workflow_started_at,
  wr_latest.updated_at AS latest_workflow_completed_at,

  /* Latest stage within latest workflow run */
  wsr_latest.stage_key AS latest_stage_name,
  wsr_latest.status AS latest_stage_status,
  wsr_latest.started_at AS latest_stage_started_at,
  wsr_latest.finished_at AS latest_stage_completed_at,

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
    SELECT file_id, MAX(created_at) AS max_started_at
    FROM workflow_runs
    GROUP BY file_id
  ) w2
    ON w2.file_id = w1.file_id
   AND w2.max_started_at = w1.created_at
  INNER JOIN (
    SELECT file_id, created_at AS started_at, MAX(id) AS max_id
    FROM workflow_runs
    GROUP BY file_id, created_at
  ) w3
    ON w3.file_id = w1.file_id
   AND w3.started_at = w1.created_at
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
