-- Migration 0046: Fix unified_files currency/FX amount columns (precision + defaults)
-- Date: 2025-12-20
-- Purpose:
-- - Remove legacy 0-defaults for FX fields (treat as NULL = unknown)
-- - Increase precision for exchange_rate and SEK mirror amounts
-- - Enforce SEK invariant: currency='SEK' must have exchange_rate=1.000000

ALTER TABLE unified_files
  MODIFY COLUMN exchange_rate DECIMAL(12,6) NULL DEFAULT NULL,
  MODIFY COLUMN gross_amount_sek DECIMAL(12,2) NULL DEFAULT NULL,
  MODIFY COLUMN net_amount_sek DECIMAL(12,2) NULL DEFAULT NULL;

-- Normalize empty currency values to SEK (deterministic fallback)
UPDATE unified_files
SET currency = 'SEK'
WHERE currency IS NULL OR TRIM(currency) = '';

-- Remove legacy placeholder zeros (defaults previously wrote 0)
UPDATE unified_files
SET exchange_rate = NULL
WHERE exchange_rate = 0;

UPDATE unified_files
SET gross_amount_sek = NULL
WHERE gross_amount_sek = 0;

UPDATE unified_files
SET net_amount_sek = NULL
WHERE net_amount_sek = 0;

-- SEK invariant: exchange_rate must exist and be 1.000000 for SEK rows
UPDATE unified_files
SET exchange_rate = 1.000000
WHERE currency = 'SEK' AND exchange_rate IS NULL;

-- For SEK, mirror original/legacy amounts into SEK mirror fields if missing (deterministic)
UPDATE unified_files
SET gross_amount_sek = COALESCE(gross_amount_original, gross_amount)
WHERE currency = 'SEK'
  AND gross_amount_sek IS NULL
  AND COALESCE(gross_amount_original, gross_amount) IS NOT NULL;

UPDATE unified_files
SET net_amount_sek = COALESCE(net_amount_original, net_amount)
WHERE currency = 'SEK'
  AND net_amount_sek IS NULL
  AND COALESCE(net_amount_original, net_amount) IS NOT NULL;

