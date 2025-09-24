-- Create unified_files and file_tags if not exists
CREATE TABLE IF NOT EXISTS unified_files (
  id VARCHAR(36) PRIMARY KEY,
  file_type VARCHAR(32) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL,
  merchant_name VARCHAR(255) NULL,
  orgnr VARCHAR(32) NULL,
  purchase_datetime DATETIME NULL,
  gross_amount DECIMAL(12,2) NULL,
  net_amount DECIMAL(12,2) NULL
);

CREATE TABLE IF NOT EXISTS file_tags (
  file_id VARCHAR(36) NOT NULL,
  tag VARCHAR(64) NOT NULL,
  PRIMARY KEY (file_id, tag)
);
