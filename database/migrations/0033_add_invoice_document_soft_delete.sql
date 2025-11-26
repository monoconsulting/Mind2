-- Soft delete support for FirstCard invoice documents
-- Date: 2025-11-06

ALTER TABLE invoice_documents
  ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL
    COMMENT 'Timestamp when the invoice was soft deleted' AFTER metadata_json;

CREATE INDEX idx_invoice_documents_deleted_at
  ON invoice_documents (deleted_at);
