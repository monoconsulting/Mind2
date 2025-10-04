-- Invoice Matching Enhancements
-- Date: 2025-10-04
-- Adds status tracking columns for invoices and links unified files to invoice documents.

-- -----------------------------------------------------
-- unified_files invoice matching columns
-- -----------------------------------------------------
ALTER TABLE unified_files
  ADD COLUMN IF NOT EXISTS invoice_match_status VARCHAR(32) NULL COMMENT 'Status for invoice matching: pending, matched, unmatched, reviewed' AFTER credit_card_match,
  ADD COLUMN IF NOT EXISTS matched_invoice_id VARCHAR(36) NULL COMMENT 'Reference to invoice_documents.id if matched to invoice line' AFTER invoice_match_status;

CREATE INDEX IF NOT EXISTS idx_unified_invoice_match ON unified_files(invoice_match_status);
CREATE INDEX IF NOT EXISTS idx_unified_files_matched_invoice ON unified_files(matched_invoice_id);

-- -----------------------------------------------------
-- invoice_documents processing metadata
-- -----------------------------------------------------
ALTER TABLE invoice_documents
  ADD COLUMN IF NOT EXISTS source_file_id VARCHAR(36) NULL COMMENT 'Reference to unified_files.id for uploaded PDF/image' AFTER invoice_type,
  ADD COLUMN IF NOT EXISTS processing_status VARCHAR(32) NOT NULL DEFAULT 'uploaded' COMMENT 'uploaded, ocr_pending, ocr_done, ai_processing, ready_for_matching, matched, completed' AFTER status;

CREATE INDEX IF NOT EXISTS idx_invoice_docs_processing ON invoice_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_invoice_docs_source ON invoice_documents(source_file_id);

-- -----------------------------------------------------
-- invoice_lines AI metadata
-- -----------------------------------------------------
ALTER TABLE invoice_lines
  ADD COLUMN IF NOT EXISTS extraction_confidence FLOAT NULL COMMENT 'AI confidence for extracted data (0-1)' AFTER match_score,
  ADD COLUMN IF NOT EXISTS ocr_source_text TEXT NULL COMMENT 'Original OCR text that was parsed' AFTER extraction_confidence;

-- -----------------------------------------------------
-- Rollback guidance (manual)
-- -----------------------------------------------------
-- To roll back, drop the new columns and indexes in reverse order:
--   ALTER TABLE invoice_lines DROP COLUMN ocr_source_text;
--   ALTER TABLE invoice_lines DROP COLUMN extraction_confidence;
--   DROP INDEX idx_invoice_docs_source ON invoice_documents;
--   DROP INDEX idx_invoice_docs_processing ON invoice_documents;
--   ALTER TABLE invoice_documents DROP COLUMN processing_status;
--   ALTER TABLE invoice_documents DROP COLUMN source_file_id;
--   DROP INDEX idx_unified_files_matched_invoice ON unified_files;
--   DROP INDEX idx_unified_invoice_match ON unified_files;
--   ALTER TABLE unified_files DROP COLUMN matched_invoice_id;
--   ALTER TABLE unified_files DROP COLUMN invoice_match_status;
