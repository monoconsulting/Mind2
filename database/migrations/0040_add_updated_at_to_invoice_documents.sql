-- Migration 0038: Add updated_at column to invoice_documents if missing
-- Date: 2025-10-25
-- Purpose: Ensure invoice_documents has updated_at column for tracking changes

-- Check if updated_at column exists
SET @col_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'invoice_documents'
    AND COLUMN_NAME = 'updated_at'
);

-- Add updated_at if it doesn't exist
SET @sql = IF(
  @col_exists = 0,
  'ALTER TABLE invoice_documents ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER uploaded_at',
  'SELECT ''Column updated_at already exists'' AS Info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verify
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'invoice_documents'
  AND COLUMN_NAME IN ('uploaded_at', 'updated_at');

