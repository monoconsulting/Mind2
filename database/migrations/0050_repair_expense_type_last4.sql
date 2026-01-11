-- Repair expense_type based on deterministic last4 rules
-- Date: 2025-12-26

UPDATE unified_files
SET expense_type = 'personal', updated_at = NOW()
WHERE file_type = 'receipt'
  AND credit_card_last_4_digits = 9995
  AND (expense_type IS NULL OR expense_type <> 'personal');

UPDATE unified_files
SET expense_type = 'corporate', updated_at = NOW()
WHERE file_type = 'receipt'
  AND credit_card_last_4_digits IN (6779, 4668)
  AND (expense_type IS NULL OR expense_type <> 'corporate');
