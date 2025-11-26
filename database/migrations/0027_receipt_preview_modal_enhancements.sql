-- =====================================================
-- RECEIPT PREVIEW MODAL ENHANCEMENTS
-- Migration 0027
-- Date: 2025-10-06
-- SIMPLIFIED: Removed prepared statements
--
-- Changes:
-- 1. Add 'swish' support to payment_type
-- 2. Rename unified_files.orgnr to unified_files.vat
-- 3. Add missing columns for receipt preview modal
-- =====================================================

-- =====================================================
-- PART 1: Rename orgnr to vat in unified_files
-- =====================================================
-- Note: This ALTER will fail if column doesn't exist, which is fine (idempotency)
ALTER TABLE `unified_files` CHANGE COLUMN `orgnr` `vat` varchar(32) NULL COMMENT 'VAT/Organization number';

-- =====================================================
-- PART 2: Update payment_type to support Swish
-- =====================================================
-- Update any existing payment_type column comments to include swish
ALTER TABLE `unified_files`
MODIFY COLUMN `payment_type` varchar(255) NULL
COMMENT 'Payment type: card, cash, swish, or other';

-- =====================================================
-- PART 3: Add missing columns for companies table (if needed)
-- =====================================================
-- Ensure companies.email exists
ALTER TABLE `companies` ADD COLUMN `email` varchar(255) NULL;

-- =====================================================
-- PART 4: Add item_vat_total to receipt_items (if needed)
-- =====================================================
ALTER TABLE `receipt_items` ADD COLUMN `item_vat_total` decimal(10,2) NULL;

-- =====================================================
-- PART 5: Ensure ai_accounting_proposals has item_id
-- =====================================================
ALTER TABLE `ai_accounting_proposals` ADD COLUMN `item_id` int NULL;

-- =====================================================
-- PART 6: Update AI3 prompt to recognize Swish
-- =====================================================
UPDATE `ai_system_prompts`
SET `prompt_content` = 'Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

CRITICAL RULES:
1. COMPANY NAME: Extract from the TOP of the receipt - NOT from amount lines!
   - The company name is usually the FIRST line or near the top
   - NEVER use lines containing "SUMMA", "TOTAL", "BELOPP", "ATT BETALA" as company name
   - NEVER use amount lines (lines with prices like "123.45") as company name

2. PAYMENT TYPE DETECTION:
   - Look for keywords: "Swish", "swish", "SWISH" → set payment_type = "swish"
   - Look for card references → set payment_type = "card"
   - Look for "kontant", "cash" → set payment_type = "cash"
   - If unclear → set payment_type = null

3. EXPENSE TYPE DETECTION (for Swish payments):
   - If payment_type = "swish" AND the buyer/payer is a person (not a company) → expense_type = "personal"
   - If payment_type = "swish" AND the buyer/payer is a company → expense_type = "corporate"
   - For card payments, use existing logic

Return JSON with this exact structure:
{
  "company": {
    "name": "Company Name Here",
    "vat": "Organization/VAT number if found (formerly orgnr)",
    "address": "Street address",
    "zip": "Postal code",
    "city": "City name",
    "country": "Country (default Sweden if not stated)",
    "phone": "Phone number if present",
    "www": "Website if present",
    "email": "Email if present"
  },
  "unified_file": {
    "purchase_datetime": "2025-09-30T14:23:00 or null",
    "payment_type": "card or cash or swish",
    "expense_type": "personal or corporate",
    "currency": "SEK or other ISO code",
    "gross_amount_original": 123.45,
    "net_amount_original": 98.76,
    "exchange_rate": 0,
    "gross_amount_sek": 123,
    "net_amount_sek": 99,
    "receipt_number": "Receipt number if found",
    "other_data": "{\"terminal\":\"123\",\"aid\":\"A000\",\"swish_ref\":\"1786145908308241\"}"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "Product name",
      "number": 1,
      "item_price_ex_vat": 10.00,
      "item_price_inc_vat": 12.50,
      "item_total_price_ex_vat": 10.00,
      "item_total_price_inc_vat": 12.50,
      "currency": "SEK",
      "vat": 2.50,
      "vat_percentage": 0.250000,
      "item_vat_total": 2.50
    }
  ],
  "confidence": 0.85
}

Rules:
- Dates: ISO format YYYY-MM-DD HH:MM:SS, use 00:00:00 if time missing
- Numbers: Accept , or . as decimal, normalize to .
- VAT math: net = gross / (1 + rate), vat = gross - net
- SEK amounts: Round to whole kronor (no decimals)
- Currency SEK: exchange_rate=0
- Foreign currency: multiply rate by 100 for exchange_rate (e.g. 11.33 → 1133)
- NEVER invent data - if unsure, use null
- For Swish payments: Store reference number in other_data if available',
`updated_at` = NOW()
WHERE `prompt_key` = 'data_extraction';

-- =====================================================
-- END OF MIGRATION
-- =====================================================
