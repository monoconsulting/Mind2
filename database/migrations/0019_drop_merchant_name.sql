-- Drop merchant_name column from unified_files
-- This column was populated by OCR which is incorrect
-- All company data should come from the companies table via company_id

-- MySQL doesn't support DROP COLUMN IF EXISTS before 8.0.29, use procedure instead
DELIMITER $$
CREATE PROCEDURE drop_merchant_name()
BEGIN
  IF EXISTS(
    SELECT * FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'unified_files'
    AND COLUMN_NAME = 'merchant_name'
  ) THEN
    ALTER TABLE unified_files DROP COLUMN merchant_name;
  END IF;
END$$
DELIMITER ;
CALL drop_merchant_name();
DROP PROCEDURE drop_merchant_name;
