-- Repair missing columns required by:
-- - FirstCard invoice matching (invoice_lines.extraction_confidence, invoice_lines.ocr_source_text)
-- - AI4 accounting proposals (ai_accounting_proposals.item_id)
--
-- This migration is idempotent on MySQL by using information_schema checks + dynamic DDL.

SET @schema := DATABASE();

-- -------------------------------------------------------------------
-- invoice_lines.extraction_confidence
-- -------------------------------------------------------------------
SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema
    AND table_name   = 'invoice_lines'
    AND column_name  = 'extraction_confidence'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE invoice_lines ADD COLUMN extraction_confidence FLOAT NULL COMMENT ''AI extraction confidence for this line'' AFTER match_score',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------------
-- invoice_lines.ocr_source_text
-- -------------------------------------------------------------------
SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema
    AND table_name   = 'invoice_lines'
    AND column_name  = 'ocr_source_text'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE invoice_lines ADD COLUMN ocr_source_text TEXT NULL COMMENT ''Excerpt of OCR text around this transaction'' AFTER extraction_confidence',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------------
-- ai_accounting_proposals.item_id
-- -------------------------------------------------------------------
SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema
    AND table_name   = 'ai_accounting_proposals'
    AND column_name  = 'item_id'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE ai_accounting_proposals ADD COLUMN item_id VARCHAR(36) NULL AFTER unified_file_id',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
