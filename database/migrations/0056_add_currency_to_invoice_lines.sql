-- Add currency fields to invoice_lines for FirstCard reconciliation
-- Date: 2026-01-12

-- currency_original
SELECT IF(
  EXISTS(
    SELECT 1
      FROM information_schema.COLUMNS
     WHERE table_schema = DATABASE()
       AND table_name = 'invoice_lines'
       AND column_name = 'currency_original'
  ),
  'SELECT 1',
  'ALTER TABLE invoice_lines ADD COLUMN currency_original CHAR(3) NULL COMMENT ''Original currency code from FirstCard line'' AFTER amount'
) INTO @stmt;
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- amount_original
SELECT IF(
  EXISTS(
    SELECT 1
      FROM information_schema.COLUMNS
     WHERE table_schema = DATABASE()
       AND table_name = 'invoice_lines'
       AND column_name = 'amount_original'
  ),
  'SELECT 1',
  'ALTER TABLE invoice_lines ADD COLUMN amount_original DECIMAL(13,2) NULL COMMENT ''Original amount in foreign currency'' AFTER currency_original'
) INTO @stmt;
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- exchange_rate
SELECT IF(
  EXISTS(
    SELECT 1
      FROM information_schema.COLUMNS
     WHERE table_schema = DATABASE()
       AND table_name = 'invoice_lines'
       AND column_name = 'exchange_rate'
  ),
  'SELECT 1',
  'ALTER TABLE invoice_lines ADD COLUMN exchange_rate DECIMAL(18,6) NULL COMMENT ''Exchange rate applied by FirstCard'' AFTER amount_original'
) INTO @stmt;
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- amount_sek
SELECT IF(
  EXISTS(
    SELECT 1
      FROM information_schema.COLUMNS
     WHERE table_schema = DATABASE()
       AND table_name = 'invoice_lines'
       AND column_name = 'amount_sek'
  ),
  'SELECT 1',
  'ALTER TABLE invoice_lines ADD COLUMN amount_sek DECIMAL(13,2) NULL COMMENT ''Actual amount paid in SEK (incl. fees)'' AFTER exchange_rate'
) INTO @stmt;
PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
