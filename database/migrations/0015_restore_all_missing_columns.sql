-- =====================================================
-- COMPREHENSIVE DATABASE SCHEMA RESTORATION
-- This migration restores ALL missing columns and tables
-- Based on comparison between mono_se_db_9 (3).sql and current database
-- Generated: 2025-09-30
-- =====================================================

-- Set SQL mode to allow idempotent execution
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ALLOW_INVALID_DATES';
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

-- =====================================================
-- MISSING TABLES
-- =====================================================

-- Create file_categories table if it doesn't exist
CREATE TABLE IF NOT EXISTS `file_categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(222) NOT NULL,
  `description` varchar(222) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create tags table if it doesn't exist
CREATE TABLE IF NOT EXISTS `tags` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `description` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tag_category` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Create tag_categories table if it doesn't exist
CREATE TABLE IF NOT EXISTS `tag_categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tag_category_name` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `tag_category_description` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =====================================================
-- TABLE: ai_accounting_proposals
-- =====================================================
-- Missing: item_id column (should be between receipt_id and account_code)
-- Using procedure to check if column exists before adding
DELIMITER $$
CREATE PROCEDURE add_column_if_not_exists()
BEGIN
  IF NOT EXISTS(
    SELECT * FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'mono_se_db_9'
    AND TABLE_NAME = 'ai_accounting_proposals'
    AND COLUMN_NAME = 'item_id'
  ) THEN
    ALTER TABLE `ai_accounting_proposals` ADD COLUMN `item_id` int NOT NULL AFTER `receipt_id`;
  END IF;
END$$
DELIMITER ;
CALL add_column_if_not_exists();
DROP PROCEDURE add_column_if_not_exists;

-- =====================================================
-- TABLE: companies
-- =====================================================
-- Add missing timestamp columns
DELIMITER $$
CREATE PROCEDURE add_companies_created_at()
BEGIN
  IF NOT EXISTS(
    SELECT * FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'mono_se_db_9'
    AND TABLE_NAME = 'companies'
    AND COLUMN_NAME = 'created_at'
  ) THEN
    ALTER TABLE `companies` ADD COLUMN `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER `www`;
  END IF;
END$$
DELIMITER ;
CALL add_companies_created_at();
DROP PROCEDURE add_companies_created_at;

DELIMITER $$
CREATE PROCEDURE add_companies_updated_at()
BEGIN
  IF NOT EXISTS(
    SELECT * FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'mono_se_db_9'
    AND TABLE_NAME = 'companies'
    AND COLUMN_NAME = 'updated_at'
  ) THEN
    ALTER TABLE `companies` ADD COLUMN `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP AFTER `created_at`;
  END IF;
END$$
DELIMITER ;
CALL add_companies_updated_at();
DROP PROCEDURE add_companies_updated_at;

-- Note: The SQL file shows some fields as NOT NULL (address, address2, zip, city, country, phone, www)
-- but current DB has them as NULL. Keeping current DB schema to avoid data issues.
-- If you want to enforce NOT NULL, you'll need to update existing data first.

-- =====================================================
-- TABLE: receipt_items
-- =====================================================
-- Note: SQL file shows main_id as INT NOT NULL, article_id as varchar(222) NOT NULL
-- Current DB has main_id as varchar(36) NOT NULL, article_id as varchar(222) NULL
-- This suggests the schema evolved. Keeping current DB schema.
-- If you need to restore original schema, data migration is required.

-- Ensure all expected columns with proper NULL constraints match SQL file
-- The current DB schema appears more evolved, so we'll keep it as is.

-- =====================================================
-- TABLE: unified_files
-- =====================================================
-- This table has MANY missing columns. Adding them all using stored procedures

-- Helper procedure to add column only if it doesn't exist
DELIMITER $$
CREATE PROCEDURE add_unified_files_column(
  IN col_name VARCHAR(64),
  IN col_definition TEXT,
  IN after_col VARCHAR(64)
)
BEGIN
  SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'mono_se_db_9'
    AND TABLE_NAME = 'unified_files'
    AND COLUMN_NAME = col_name
  );

  IF @col_exists = 0 THEN
    SET @sql = CONCAT('ALTER TABLE `unified_files` ADD COLUMN `', col_name, '` ', col_definition);
    IF after_col IS NOT NULL AND after_col != '' THEN
      SET @sql = CONCAT(@sql, ' AFTER `', after_col, '`');
    END IF;
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END$$
DELIMITER ;

-- Add payment_type column
CALL add_unified_files_column('payment_type', 'varchar(255) NOT NULL DEFAULT \'\' COMMENT \'Enter "cash" or "card"\'', 'orgnr');

-- Add expense_type column
CALL add_unified_files_column('expense_type', 'varchar(255) NOT NULL DEFAULT \'\' COMMENT \'If this is bought using a private card or cash (personal) or if it is corporate card (corporate)\'', 'purchase_datetime');

-- Add gross_amount_original column
CALL add_unified_files_column('gross_amount_original', 'decimal(12,2) DEFAULT NULL COMMENT \'amount inc vat\'', 'expense_type');

-- Add net_amount_original column
CALL add_unified_files_column('net_amount_original', 'decimal(12,2) DEFAULT NULL COMMENT \'amount ex vat\'', 'gross_amount_original');

-- Add exchange_rate column
CALL add_unified_files_column('exchange_rate', 'decimal(12,0) NOT NULL DEFAULT 0 COMMENT \'exchange rate example: 1 USD=11.33 SEK\'', 'net_amount_original');

-- Add currency column
CALL add_unified_files_column('currency', 'varchar(222) NOT NULL DEFAULT \'SEK\' COMMENT \'currency that was bought in\'', 'exchange_rate');

-- Add gross_amount_sek column
CALL add_unified_files_column('gross_amount_sek', 'decimal(10,0) NOT NULL DEFAULT 0 COMMENT \'only used for foreign currency - shows the gross amount in sek\'', 'currency');

-- Add net_amount_sek column
CALL add_unified_files_column('net_amount_sek', 'decimal(10,0) NOT NULL DEFAULT 0 COMMENT \'The net amount in SEK after exchange conversion\'', 'gross_amount_sek');

-- Add ocr_raw column (after mime_type)
CALL add_unified_files_column('ocr_raw', 'text NOT NULL DEFAULT (\'\') COMMENT \'The raw ocr-text without coordinates from the picture\'', 'mime_type');

-- Add company_id column
CALL add_unified_files_column('company_id', 'int NOT NULL DEFAULT 0 COMMENT \'companies.id - refering to the company that sold the product\'', 'ocr_raw');

-- Add receipt_number column
CALL add_unified_files_column('receipt_number', 'varchar(255) NOT NULL DEFAULT \'\' COMMENT \'the unique receipt number\'', 'company_id');

-- Add approved_by column (after file_category)
CALL add_unified_files_column('approved_by', 'int NOT NULL DEFAULT 0 COMMENT \'user id that approved the receipt\'', 'file_category');

-- Add other_data column
CALL add_unified_files_column('other_data', 'text NOT NULL DEFAULT (\'\') COMMENT \'This is for all other data available on the receipt that doesnt have a specified column\'', 'approved_by');

-- Add credit_card_match column
CALL add_unified_files_column('credit_card_match', 'tinyint(1) NOT NULL DEFAULT 0 COMMENT \'When matching receipt is available set 1\'', 'other_data');

-- Drop the helper procedure
DROP PROCEDURE add_unified_files_column;

-- =====================================================
-- RESTORE PROPER COLUMN ORDERING FOR unified_files
-- =====================================================
-- Note: MySQL doesn't easily support reordering without data loss risk.
-- The columns are added, but may not be in the exact order as the SQL file.
-- This is generally acceptable as column order doesn't affect functionality.

-- =====================================================
-- POST-MIGRATION NOTES
-- =====================================================
-- 1. The following type mismatches exist but are NOT changed to avoid data issues:
--    - ai_llm.id: int in DB vs bigint UNSIGNED in SQL file
--    - ai_llm_model.id: int in DB vs bigint UNSIGNED in SQL file
--    - ai_system_prompts.id: int in DB vs bigint UNSIGNED in SQL file
--    - receipt_items.main_id: varchar(36) in DB vs int in SQL file
--
-- 2. NULL constraint differences on companies table are preserved to avoid data issues
--
-- 3. ai_processing_history has additional columns in DB that don't exist in SQL file:
--    - ai_stage_name, log_text, error_message, confidence, processing_time_ms, provider, model_name
--    These are evolution features and are kept.
--
-- 4. creditcard_receipt_matches table exists in DB but not in SQL file - this is evolution
--
-- 5. To verify the migration was successful, run:
--    SELECT COUNT(*) FROM file_categories;
--    SELECT COUNT(*) FROM tags;
--    SELECT COUNT(*) FROM tag_categories;
--    DESCRIBE unified_files;
--    DESCRIBE ai_accounting_proposals;
--    DESCRIBE companies;

-- Restore SQL mode
SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;

-- =====================================================
-- END OF MIGRATION
-- =====================================================
