-- Migration 0036: Add currency column to creditcard_invoices_main
-- Date: 2025-10-15
-- Purpose: Fix schema mismatch - AI6 processing tries to insert currency but column doesn't exist

-- Add currency column
ALTER TABLE creditcard_invoices_main
ADD COLUMN currency VARCHAR(3) DEFAULT NULL COMMENT 'Currency code (SEK, EUR, USD, etc.)';

-- Add index for fast lookups by currency
CREATE INDEX idx_currency ON creditcard_invoices_main(currency);

-- Show table structure to verify
SHOW COLUMNS FROM creditcard_invoices_main;

