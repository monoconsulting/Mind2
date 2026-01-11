-- Unmatch invoice lines linked to personal receipts
-- Date: 2025-12-26

UPDATE invoice_lines il
JOIN unified_files uf ON uf.id = il.matched_file_id
SET il.matched_file_id = NULL,
    il.match_status = 'pending',
    il.match_score = NULL
WHERE uf.file_type = 'receipt'
  AND uf.expense_type = 'personal'
  AND il.matched_file_id IS NOT NULL;

UPDATE unified_files
SET credit_card_match = 0,
    updated_at = NOW()
WHERE file_type = 'receipt'
  AND expense_type = 'personal'
  AND credit_card_match = 1;
