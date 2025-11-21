-- =====================================================
-- COMPREHENSIVE DATABASE SCHEMA RESTORATION
-- This migration restores ALL missing columns and tables
-- Based on comparison between mono_se_db_9 (3).sql and current database
-- Generated: 2025-09-30
-- SIMPLIFIED: Removed stored procedures - idempotency handled by migration system
-- =====================================================

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
ALTER TABLE `ai_accounting_proposals` ADD COLUMN `item_id` int NOT NULL;

-- =====================================================
-- TABLE: companies
-- =====================================================
ALTER TABLE `companies` ADD COLUMN `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE `companies` ADD COLUMN `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP;

-- =====================================================
-- TABLE: unified_files
-- =====================================================
-- Add columns (AFTER clauses removed to avoid schema dependency errors)
ALTER TABLE `unified_files` ADD COLUMN `payment_type` varchar(255) NOT NULL DEFAULT '' COMMENT 'Enter "cash" or "card"';
ALTER TABLE `unified_files` ADD COLUMN `expense_type` varchar(255) NOT NULL DEFAULT '' COMMENT 'If this is bought using a private card or cash (personal) or if it is corporate card (corporate)';
ALTER TABLE `unified_files` ADD COLUMN `gross_amount_original` decimal(12,2) DEFAULT NULL COMMENT 'amount inc vat';
ALTER TABLE `unified_files` ADD COLUMN `net_amount_original` decimal(12,2) DEFAULT NULL COMMENT 'amount ex vat';
ALTER TABLE `unified_files` ADD COLUMN `exchange_rate` decimal(12,0) NOT NULL DEFAULT 0 COMMENT 'exchange rate example: 1 USD=11.33 SEK';
ALTER TABLE `unified_files` ADD COLUMN `currency` varchar(222) NOT NULL DEFAULT 'SEK' COMMENT 'currency that was bought in';
ALTER TABLE `unified_files` ADD COLUMN `gross_amount_sek` decimal(10,0) NOT NULL DEFAULT 0 COMMENT 'only used for foreign currency - shows the gross amount in sek';
ALTER TABLE `unified_files` ADD COLUMN `net_amount_sek` decimal(10,0) NOT NULL DEFAULT 0 COMMENT 'The net amount in SEK after exchange conversion';
ALTER TABLE `unified_files` ADD COLUMN `ocr_raw` text NOT NULL DEFAULT ('') COMMENT 'The raw ocr-text without coordinates from the picture';
ALTER TABLE `unified_files` ADD COLUMN `company_id` int NOT NULL DEFAULT 0 COMMENT 'companies.id - refering to the company that sold the product';
ALTER TABLE `unified_files` ADD COLUMN `receipt_number` varchar(255) NOT NULL DEFAULT '' COMMENT 'the unique receipt number';
ALTER TABLE `unified_files` ADD COLUMN `approved_by` int NOT NULL DEFAULT 0 COMMENT 'user id that approved the receipt';
ALTER TABLE `unified_files` ADD COLUMN `other_data` text NOT NULL DEFAULT ('') COMMENT 'This is for all other data available on the receipt that doesnt have a specified column';
ALTER TABLE `unified_files` ADD COLUMN `credit_card_match` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'When matching receipt is available set 1';

-- =====================================================
-- POST-MIGRATION NOTES
-- =====================================================
-- All columns will be added if they don't exist
-- Duplicate column errors are automatically ignored by the migration system
-- =====================================================
-- END OF MIGRATION
-- =====================================================
