-- Drop merchant_name column from unified_files
-- This column was populated by OCR which is incorrect
-- All company data should come from the companies table via company_id

-- Simplified: Just attempt to drop the column
-- Migration system will ignore "Unknown column" error if it doesn't exist
ALTER TABLE unified_files DROP COLUMN merchant_name;
