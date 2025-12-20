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

-- 6) "Top reasons" summary (counts)
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

