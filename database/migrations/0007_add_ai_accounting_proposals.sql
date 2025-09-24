-- Store generated accounting proposals per receipt
CREATE TABLE IF NOT EXISTS ai_accounting_proposals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  receipt_id VARCHAR(36) NOT NULL,
  account_code VARCHAR(32) NOT NULL,
  debit DECIMAL(12,2) NOT NULL DEFAULT 0,
  credit DECIMAL(12,2) NOT NULL DEFAULT 0,
  vat_rate DECIMAL(6,2) NULL,
  notes VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_accounting_proposals_receipt
  ON ai_accounting_proposals (receipt_id);
