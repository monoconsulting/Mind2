-- AI pipeline schema alignment migration
START TRANSACTION;

ALTER TABLE unified_files
    ADD COLUMN IF NOT EXISTS payment_type VARCHAR(255) NULL DEFAULT 'cash' AFTER orgnr,
    ADD COLUMN IF NOT EXISTS purchase_datetime DATETIME NULL AFTER payment_type,
    ADD COLUMN IF NOT EXISTS expense_type VARCHAR(255) NULL DEFAULT 'personal' AFTER purchase_datetime,
    ADD COLUMN IF NOT EXISTS gross_amount_original DECIMAL(12,2) NULL AFTER expense_type,
    ADD COLUMN IF NOT EXISTS net_amount_original DECIMAL(12,2) NULL AFTER gross_amount_original,
    ADD COLUMN IF NOT EXISTS exchange_rate DECIMAL(12,6) NULL DEFAULT 1 AFTER net_amount_original,
    ADD COLUMN IF NOT EXISTS currency VARCHAR(222) NULL DEFAULT 'SEK' AFTER exchange_rate,
    ADD COLUMN IF NOT EXISTS gross_amount_sek DECIMAL(12,2) NULL AFTER currency,
    ADD COLUMN IF NOT EXISTS net_amount_sek DECIMAL(12,2) NULL AFTER gross_amount_sek,
    ADD COLUMN IF NOT EXISTS ocr_raw LONGTEXT NULL AFTER mime_type,
    ADD COLUMN IF NOT EXISTS company_id INT NULL AFTER ocr_raw,
    ADD COLUMN IF NOT EXISTS receipt_number VARCHAR(255) NULL AFTER company_id,
    ADD COLUMN IF NOT EXISTS other_data LONGTEXT NULL AFTER receipt_number,
    ADD COLUMN IF NOT EXISTS credit_card_match TINYINT(1) NOT NULL DEFAULT 0 AFTER other_data;

CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(234) NOT NULL,
    orgnr VARCHAR(22) NOT NULL UNIQUE,
    address VARCHAR(222) NULL,
    address2 VARCHAR(222) NULL,
    zip VARCHAR(123) NULL,
    city VARCHAR(234) NULL,
    country VARCHAR(234) NULL,
    phone VARCHAR(234) NULL,
    www VARCHAR(234) NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS receipt_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_id VARCHAR(36) NOT NULL,
    article_id VARCHAR(222) NULL,
    name VARCHAR(222) NOT NULL,
    number INT NOT NULL,
    item_price_ex_vat DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    item_price_inc_vat DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    item_total_price_ex_vat DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    item_total_price_inc_vat DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(11) NOT NULL DEFAULT 'SEK',
    vat DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    vat_percentage DECIMAL(7,6) NOT NULL DEFAULT 0.000000,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_receipt_items_main (main_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ai_accounting_proposals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    receipt_id VARCHAR(36) NOT NULL,
    item_id INT NULL,
    account_code VARCHAR(32) NOT NULL,
    debit DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    credit DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    vat_rate DECIMAL(7,2) NULL,
    notes VARCHAR(255) NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ai_proposals_receipt (receipt_id),
    INDEX idx_ai_proposals_item (item_id),
    FOREIGN KEY (item_id) REFERENCES receipt_items(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS creditcard_invoice_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    main_id BIGINT UNSIGNED NULL,
    line_no INT NULL,
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
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_invoice_items_purchase_date (purchase_date),
    INDEX idx_invoice_items_merchant (merchant_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS creditcard_receipt_matches (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    receipt_id VARCHAR(36) NOT NULL,
    invoice_item_id BIGINT UNSIGNED NOT NULL,
    matched_amount DECIMAL(13,2) NULL,
    matched_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_receipt_invoice (receipt_id, invoice_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

COMMIT;
