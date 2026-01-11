-- Unmatch invoice_lines pointing to non-receipt files (FirstCard matches must target receipts only)
UPDATE invoice_lines AS il
JOIN unified_files AS uf ON uf.id = il.matched_file_id
SET il.matched_file_id = NULL,
    il.match_status = 'pending',
    il.match_score = NULL
WHERE il.matched_file_id IS NOT NULL
  AND uf.file_type <> 'receipt';
