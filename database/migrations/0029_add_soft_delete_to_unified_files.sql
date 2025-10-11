-- =====================================================
-- ADD SOFT DELETE SUPPORT TO unified_files
-- Migration to add deleted_at column for soft delete functionality
-- Generated: 2025-10-11
-- =====================================================

-- Add deleted_at column to unified_files for soft delete
ALTER TABLE `unified_files`
  ADD COLUMN `deleted_at` TIMESTAMP NULL DEFAULT NULL
  COMMENT 'Timestamp when the record was soft deleted. NULL means not deleted.';

-- Create index on deleted_at for efficient filtering
CREATE INDEX `idx_deleted_at` ON `unified_files` (`deleted_at`);

-- =====================================================
-- VERIFICATION QUERY
-- Run this to verify the changes:
-- SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_DEFAULT
-- FROM information_schema.COLUMNS
-- WHERE TABLE_SCHEMA = DATABASE()
-- AND TABLE_NAME = 'unified_files'
-- AND COLUMN_NAME = 'deleted_at';
-- =====================================================
