-- Expand unified_files with AI ingestion columns and supporting tables
-- Derived from mono_se_db_9 (3).sql dump (2025-09-29)

ALTER TABLE unified_files
  ADD COLUMN IF NOT EXISTS payment_type VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Enter "cash" or "card"',
  ADD COLUMN IF NOT EXISTS purchase_datetime DATETIME NULL COMMENT 'Date and time on the receipt',
  ADD COLUMN IF NOT EXISTS expense_type VARCHAR(255) NULL COMMENT 'personal or corporate classification',
  ADD COLUMN IF NOT EXISTS gross_amount_original DECIMAL(12,2) NULL COMMENT 'amount including VAT',
  ADD COLUMN IF NOT EXISTS net_amount_original DECIMAL(12,2) NULL COMMENT 'amount excluding VAT',
  ADD COLUMN IF NOT EXISTS exchange_rate DECIMAL(12,6) NULL COMMENT 'Exchange rate example: 1 USD=11.33 SEK',
  ADD COLUMN IF NOT EXISTS currency VARCHAR(222) NOT NULL DEFAULT 'SEK' COMMENT 'Currency used for purchase',
  ADD COLUMN IF NOT EXISTS gross_amount_sek DECIMAL(12,2) NULL COMMENT 'Gross amount converted to SEK',
  ADD COLUMN IF NOT EXISTS net_amount_sek DECIMAL(12,2) NULL COMMENT 'Net amount converted to SEK',
  ADD COLUMN IF NOT EXISTS ocr_raw LONGTEXT NULL COMMENT 'Raw OCR text without coordinates',
  ADD COLUMN IF NOT EXISTS company_id INT NULL COMMENT 'companies.id that sold the product',
  ADD COLUMN IF NOT EXISTS receipt_number VARCHAR(255) NULL COMMENT 'Unique receipt number',
  ADD COLUMN IF NOT EXISTS submitted_by VARCHAR(64) NULL COMMENT 'User that submitted the file',
  ADD COLUMN IF NOT EXISTS file_suffix VARCHAR(32) NULL COMMENT 'File extension without dot',
  ADD COLUMN IF NOT EXISTS file_category INT NULL COMMENT 'Reference to file_categories.id',
  ADD COLUMN IF NOT EXISTS approved_by INT NULL COMMENT 'User id that approved the receipt',
  ADD COLUMN IF NOT EXISTS other_data LONGTEXT NULL COMMENT 'Any additional receipt metadata',
  ADD COLUMN IF NOT EXISTS credit_card_match TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 when receipt matched to credit card invoice';

CREATE INDEX IF NOT EXISTS idx_unified_files_company ON unified_files(company_id);
CREATE INDEX IF NOT EXISTS idx_unified_files_receipt_number ON unified_files(receipt_number);

-- Ensure ai_accounting_proposals table exists with correct structure
CREATE TABLE IF NOT EXISTS ai_accounting_proposals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  receipt_id VARCHAR(36) NOT NULL,
  account_code VARCHAR(32) NOT NULL,
  debit DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  credit DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  vat_rate DECIMAL(6,2) NULL,
  notes VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_accounting_proposals_receipt ON ai_accounting_proposals(receipt_id);

-- Receipt items extracted from OCR/AI
CREATE TABLE IF NOT EXISTS receipt_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  main_id VARCHAR(36) NOT NULL COMMENT 'References unified_files.id',
  article_id VARCHAR(222) NULL,
  name VARCHAR(222) NOT NULL,
  number INT NOT NULL,
  item_price_ex_vat DECIMAL(10,2) NULL,
  item_price_inc_vat DECIMAL(10,2) NULL,
  item_total_price_ex_vat DECIMAL(10,2) NULL,
  item_total_price_inc_vat DECIMAL(10,2) NULL,
  currency VARCHAR(11) NOT NULL DEFAULT 'SEK',
  vat DECIMAL(10,2) NULL,
  vat_percentage DECIMAL(7,6) NULL
);
CREATE INDEX IF NOT EXISTS idx_receipt_items_main ON receipt_items(main_id);

-- Vendor directory populated by AI
CREATE TABLE IF NOT EXISTS companies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(234) NOT NULL,
  orgnr VARCHAR(22) NOT NULL,
  address VARCHAR(222) NULL,
  address2 VARCHAR(222) NULL,
  zip VARCHAR(123) NULL,
  city VARCHAR(234) NULL,
  country VARCHAR(234) NULL,
  phone VARCHAR(234) NULL,
  www VARCHAR(234) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY ux_companies_orgnr (orgnr)
);

-- Credit card invoice import tables (production naming uses creditcard_ prefix)
CREATE TABLE IF NOT EXISTS creditcard_invoices_main (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  invoice_number VARCHAR(50) NOT NULL,
  invoice_print_time DATETIME NULL,
  card_type VARCHAR(50) NULL,
  card_name VARCHAR(100) NULL,
  card_number_masked VARCHAR(32) NULL,
  card_holder VARCHAR(100) NULL,
  cost_center VARCHAR(100) NULL,
  customer_name VARCHAR(150) NULL,
  co VARCHAR(150) NULL,
  address TEXT NULL,
  bank_name VARCHAR(100) NULL,
  bank_org_no VARCHAR(50) NULL,
  bank_vat_no VARCHAR(50) NULL,
  bank_fi_no VARCHAR(50) NULL,
  invoice_date DATE NULL,
  customer_number VARCHAR(50) NULL,
  invoice_number_long VARCHAR(100) NULL,
  due_date DATE NULL,
  invoice_total DECIMAL(13,2) NULL,
  payment_plusgiro VARCHAR(30) NULL,
  payment_bankgiro VARCHAR(30) NULL,
  payment_iban VARCHAR(34) NULL,
  payment_bic VARCHAR(11) NULL,
  payment_ocr VARCHAR(50) NULL,
  payment_due DATE NULL,
  card_total DECIMAL(13,2) NULL,
  `sum` DECIMAL(13,2) NULL,
  vat_25 DECIMAL(13,2) NULL,
  vat_12 DECIMAL(13,2) NULL,
  vat_6 DECIMAL(13,2) NULL,
  vat_0 DECIMAL(13,2) NULL,
  amount_to_pay DECIMAL(13,2) NULL,
  reported_vat DECIMAL(13,2) NULL,
  next_invoice DATE NULL,
  note_1 TEXT NULL,
  note_2 TEXT NULL,
  note_3 TEXT NULL,
  note_4 TEXT NULL,
  note_5 TEXT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_creditcard_invoices_number ON creditcard_invoices_main(invoice_number);
CREATE INDEX IF NOT EXISTS ix_creditcard_invoices_date ON creditcard_invoices_main(invoice_date);
CREATE INDEX IF NOT EXISTS ix_creditcard_invoices_number_long ON creditcard_invoices_main(invoice_number_long);

CREATE TABLE IF NOT EXISTS creditcard_invoice_items (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  main_id BIGINT UNSIGNED NOT NULL,
  line_no INT NOT NULL,
  transaction_id VARCHAR(64) NULL,
  purchase_date DATE NULL,
  posting_date DATE NULL,
  merchant_name VARCHAR(200) NULL,
  merchant_city VARCHAR(100) NULL,
  merchant_country CHAR(2) NULL,
  mcc VARCHAR(4) NULL,
  description TEXT NULL,
  currency_original CHAR(3) NULL,
  amount_original DECIMAL(13,2) NULL,
  exchange_rate DECIMAL(18,6) NULL,
  amount_sek DECIMAL(13,2) NULL,
  vat_rate DECIMAL(5,2) NULL,
  vat_amount DECIMAL(13,2) NULL,
  net_amount DECIMAL(13,2) NULL,
  gross_amount DECIMAL(13,2) NULL,
  cost_center_override VARCHAR(100) NULL,
  project_code VARCHAR(100) NULL,
  CONSTRAINT fk_creditcard_items_main FOREIGN KEY (main_id) REFERENCES creditcard_invoices_main(id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_creditcard_invoice_line ON creditcard_invoice_items(main_id, line_no);
CREATE INDEX IF NOT EXISTS ix_creditcard_invoice_purchase_date ON creditcard_invoice_items(purchase_date);
CREATE INDEX IF NOT EXISTS ix_creditcard_invoice_merchant ON creditcard_invoice_items(merchant_name);

CREATE TABLE IF NOT EXISTS creditcard_receipt_matches (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  receipt_id VARCHAR(36) NOT NULL,
  invoice_item_id BIGINT UNSIGNED NOT NULL,
  matched_amount DECIMAL(13,2) NULL,
  matched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY ux_receipt_invoice_item (receipt_id, invoice_item_id),
  CONSTRAINT fk_receipt_matches_item FOREIGN KEY (invoice_item_id) REFERENCES creditcard_invoice_items(id) ON DELETE CASCADE
);
