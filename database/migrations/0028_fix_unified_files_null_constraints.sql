-- =====================================================
-- FIX unified_files NULL CONSTRAINTS
-- Migration to allow NULL on all columns except:
-- - id
-- - original_filename
-- - file_suffix
-- Generated: 2025-10-07
-- =====================================================

-- Change file_type to allow NULL
ALTER TABLE `unified_files`
  MODIFY COLUMN `file_type` varchar(32) DEFAULT NULL;

-- Change credit_card related columns to allow NULL
ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_number` varchar(44) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_last_4_digits` int DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_type` varchar(44) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_brand_full` varchar(22) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_brand_short` varchar(22) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_payment_variant` varchar(222) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_token` varchar(222) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `credit_card_entering_mode` varchar(222) DEFAULT NULL;

-- Change VAT columns to allow NULL
ALTER TABLE `unified_files`
  MODIFY COLUMN `total_vat_12` decimal(12,2) DEFAULT NULL;

ALTER TABLE `unified_files`
  MODIFY COLUMN `total_vat_6` decimal(12,2) DEFAULT NULL;

-- Change ocr_raw to allow NULL (remove DEFAULT_GENERATED)
ALTER TABLE `unified_files`
  MODIFY COLUMN `ocr_raw` text DEFAULT NULL;

-- Change other_data to allow NULL (remove DEFAULT_GENERATED)
ALTER TABLE `unified_files`
  MODIFY COLUMN `other_data` text DEFAULT NULL;

-- =====================================================
-- ENFORCE NOT NULL on required columns
-- =====================================================

-- Ensure original_filename does NOT allow NULL
ALTER TABLE `unified_files`
  MODIFY COLUMN `original_filename` varchar(255) NOT NULL;

-- Ensure file_suffix does NOT allow NULL
ALTER TABLE `unified_files`
  MODIFY COLUMN `file_suffix` varchar(32) NOT NULL;

-- =====================================================
-- VERIFICATION QUERY
-- Run this to verify the changes:
-- SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_DEFAULT
-- FROM information_schema.COLUMNS
-- WHERE TABLE_SCHEMA = 'mono_se_db_9'
-- AND TABLE_NAME = 'unified_files'
-- ORDER BY ORDINAL_POSITION;
-- =====================================================
