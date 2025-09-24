-- Invoice schema (per MIND v2.0) – company card and supplier invoices

-- invoice_documents: container for statements/documents
CREATE TABLE IF NOT EXISTS invoice_documents (
  id VARCHAR(36) PRIMARY KEY,
  invoice_type VARCHAR(32) NOT NULL, -- 'company_card' | 'supplier'
  period_start DATE NULL,
  period_end DATE NULL,
  uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(32) NOT NULL DEFAULT 'imported',
  metadata_json JSON NULL
);

-- Indexes are defined inline or added separately in controlled migrations if needed

-- invoice_lines: individual transactions/lines
CREATE TABLE IF NOT EXISTS invoice_lines (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  invoice_id VARCHAR(36) NOT NULL,
  transaction_date DATE NULL,
  amount DECIMAL(12,2) NULL,
  merchant_name VARCHAR(255) NULL,
  description VARCHAR(1024) NULL,
  matched_file_id VARCHAR(36) NULL,
  match_score FLOAT NULL,
  match_status VARCHAR(16) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_invoice_lines_doc FOREIGN KEY (invoice_id) REFERENCES invoice_documents(id)
);

-- Consider adding indexes in a follow-up migration if required for performance

-- invoice_line_history: audit trail for matching decisions
CREATE TABLE IF NOT EXISTS invoice_line_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  invoice_line_id BIGINT NOT NULL,
  action VARCHAR(16) NOT NULL, -- 'matched' | 'unmatched' | 'rejected' | 'confirmed'
  performed_by VARCHAR(64) NULL,
  old_matched_file_id VARCHAR(36) NULL,
  new_matched_file_id VARCHAR(36) NULL,
  reason VARCHAR(1024) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_line_history_line FOREIGN KEY (invoice_line_id) REFERENCES invoice_lines(id)
);

-- Consider adding indexes in a follow-up migration if required for performance
