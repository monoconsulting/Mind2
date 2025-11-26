-- Migration: Add item_id column to ai_accounting_proposals
-- This column links accounting proposals to specific receipt line items

START TRANSACTION;

-- Add item_id column if it doesn't exist
ALTER TABLE ai_accounting_proposals
    ADD COLUMN IF NOT EXISTS item_id INT NULL AFTER receipt_id;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_proposals_item ON ai_accounting_proposals(item_id);

-- Add foreign key constraint (will fail silently if already exists)
-- Note: MySQL doesn't support IF NOT EXISTS for foreign keys, so we use a stored procedure
DELIMITER $$

CREATE PROCEDURE AddForeignKeyIfNotExists()
BEGIN
    DECLARE CONTINUE HANDLER FOR SQLSTATE '42000' BEGIN END;

    -- Try to add foreign key - will fail if it already exists
    ALTER TABLE ai_accounting_proposals
        ADD CONSTRAINT fk_ai_proposals_item
        FOREIGN KEY (item_id) REFERENCES receipt_items(id) ON DELETE SET NULL;
END$$

DELIMITER ;

CALL AddForeignKeyIfNotExists();
DROP PROCEDURE AddForeignKeyIfNotExists;

COMMIT;
