-- Add ocr_raw field to creditcard_invoices_main
-- Date: 2025-10-14
-- Purpose: Store merged OCR text from all invoice pages for AI6 processing

ALTER TABLE creditcard_invoices_main
  ADD COLUMN ocr_raw LONGTEXT NULL
  COMMENT 'Merged OCR text from all invoice pages'
  AFTER invoice_number;

-- Index for faster lookups by invoice_number
CREATE INDEX idx_creditcard_invoices_number
  ON creditcard_invoices_main(invoice_number);

-- Rollback guidance (manual):
-- To roll back, drop the column:
--   ALTER TABLE creditcard_invoices_main DROP COLUMN ocr_raw;
--   DROP INDEX idx_creditcard_invoices_number ON creditcard_invoices_main;
