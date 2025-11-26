ALTER TABLE creditcard_invoice_items
    ADD COLUMN matched TINYINT(1) NOT NULL DEFAULT 0 AFTER project_code;

ALTER TABLE unified_files
    ADD COLUMN matched TINYINT(1) NOT NULL DEFAULT 0 AFTER credit_card_match;

UPDATE creditcard_invoice_items AS ci
LEFT JOIN creditcard_receipt_matches AS crm ON crm.invoice_item_id = ci.id
SET ci.matched = IF(crm.invoice_item_id IS NULL, 0, 1);

UPDATE unified_files
SET matched = IF(credit_card_match IS NULL, 0, credit_card_match);
