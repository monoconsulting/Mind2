-- Create missing tables for AI pipeline

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
  vat_percentage DECIMAL(7,6) NULL,
  KEY idx_receipt_items_main (main_id)
);

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
  note_5 TEXT NULL,
  UNIQUE KEY ux_creditcard_invoices_number (invoice_number),
  KEY ix_creditcard_invoices_date (invoice_date),
  KEY ix_creditcard_invoices_number_long (invoice_number_long)
);

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
  UNIQUE KEY ux_creditcard_invoice_line (main_id, line_no),
  KEY ix_creditcard_invoice_purchase_date (purchase_date),
  KEY ix_creditcard_invoice_merchant (merchant_name),
  CONSTRAINT fk_creditcard_items_main FOREIGN KEY (main_id)
    REFERENCES creditcard_invoices_main(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS creditcard_receipt_matches (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  receipt_id VARCHAR(36) NOT NULL,
  invoice_item_id BIGINT UNSIGNED NOT NULL,
  matched_amount DECIMAL(13,2) NULL,
  matched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY ux_receipt_invoice_item (receipt_id, invoice_item_id),
  CONSTRAINT fk_receipt_matches_item FOREIGN KEY (invoice_item_id)
    REFERENCES creditcard_invoice_items(id) ON DELETE CASCADE
);