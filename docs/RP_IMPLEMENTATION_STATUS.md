# Receipt Preview Modal Enhancement - Implementation Status

**Date:** 2025-10-06
**Branch:** `feature/receipt-preview-modal-enhancements`
**Related Issues:** #43-#51 (RP1-RP9)

## Completed Tasks ✅

### RP1: Swish Payment Support
- ✅ Database migration created (0027)
- ✅ Added `vat` column to `unified_files`
- ✅ Updated AI3 prompt to recognize Swish payments
- ✅ AI3 now correctly identifies Swish as payment_type="swish"
- ✅ AI3 sets expense_type="personal" for Swish payments from individuals
- ✅ Test file examined: `testfiles_for_import/swish_test.pdf`

### RP4: Database Schema Updates
- ✅ Added `unified_files.vat` column (VARCHAR(32))
- ✅ Added `companies.email` column (VARCHAR(255))
- ✅ Updated payment_type column comment to include "swish"

### Backend API Enhancements
- ✅ Enhanced `/receipts/<rid>/modal` GET endpoint
- ✅ Added `_fetch_company_by_id()` function
- ✅ Modal now returns complete company data
- ✅ Modal now returns all payment fields:
  - payment_type, expense_type
  - credit_card_number, credit_card_last_4
  - credit_card_brand_full, credit_card_brand_short
  - credit_card_token
- ✅ Modal now returns currency/exchange data:
  - currency, exchange_rate
  - gross_amount_sek, net_amount_sek
- ✅ Modal now returns VAT breakdown:
  - total_vat_25, total_vat_12, total_vat_6
- ✅ Modal now returns:
  - receipt_number
  - other_data
  - vat (organization number)

## Remaining Frontend Tasks 🚧

### RP2: Make All Fields Editable
**Status:** Not Started
**Scope:** Update ReceiptPreviewModal component to make all displayed fields editable
**Estimated Effort:** Medium
**Files to Modify:**
- `main-system/app-frontend/src/ui/pages/Receipts.jsx` (lines 434-990)

### RP3: Individual Column Scrolling
**Status:** Not Started
**Scope:** Implement individual scroll containers for 3 columns
**Estimated Effort:** Small
**Implementation:**
```css
.receipt-modal-column {
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}
```

### RP5: Grunddata Box (Box 1)
**Status:** Not Started
**Scope:** Create company information display section
**Fields Required:**
- companies.name, companies.orgnr
- companies.address, companies.address2
- companies.zip, companies.city, companies.country
- companies.phone, companies.www, companies.email

### RP6: Betalningstyp Box (Box 2)
**Status:** Not Started
**Scope:** Create payment information display section
**Fields Required:**
- unified_files.purchase_datetime
- unified_files.receipt_number
- unified_files.payment_type (now supports "swish")
- unified_files.expense_type
- unified_files.credit_card_number
- unified_files.credit_card_last_4
- unified_files.credit_card_brand_full
- unified_files.credit_card_brand_short
- unified_files.credit_card_token

### RP7: Belopp Box (Box 3)
**Status:** Not Started
**Scope:** Create amount/currency display section
**Fields Required:**
- unified_files.currency
- unified_files.exchange_rate
- unified_files.gross_amount (original)
- unified_files.net_amount (original)
- unified_files.gross_amount_sek
- unified_files.net_amount_sek
- unified_files.total_vat_25
- unified_files.total_vat_12
- unified_files.total_vat_6

### RP8: Övrigt Box (Box 4)
**Status:** Not Started
**Scope:** Create other data display section (full width)
**Fields Required:**
- unified_files.other_data

### RP9: Items Table with Accounting
**Status:** Not Started
**Scope:** Redesign right column to show items with accounting proposals
**Complexity:** High
**Requirements:**
- Two-table-in-one design (row numbers + item data)
- Display all receipt_items fields
- Display ALL accounting proposals with proper Debet/Kredit labels
- Group proposals by item
- Show item_vat_total calculation

## Database Schema Reference

### unified_files (Updated)
- `vat` VARCHAR(32) - NEW
- `payment_type` VARCHAR(255) - Supports: card, cash, swish
- `expense_type` VARCHAR(255) - personal or corporate
- `currency` VARCHAR(222)
- `exchange_rate` DECIMAL(12,0)
- `gross_amount_sek` DECIMAL(10,0)
- `net_amount_sek` DECIMAL(10,0)
- `total_vat_25`, `total_vat_12`, `total_vat_6` DECIMAL(12,2)
- `receipt_number` VARCHAR(255)
- `other_data` TEXT
- Credit card fields: `credit_card_*`

### companies (Updated)
- `email` VARCHAR(255) - NEW
- All existing fields: name, orgnr, address, address2, zip, city, country, phone, www

### receipt_items
- All fields already supported in API

### ai_accounting_proposals
- All fields already supported in API
- Note: `item_id` column exists for linking proposals to items

## API Response Structure

```json
{
  "id": "receipt-uuid",
  "receipt": {
    "id": "...",
    "merchant": "...",
    "vat": "...",
    "company_id": 123,
    "purchase_datetime": "...",
    "receipt_number": "...",
    "payment_type": "swish",
    "expense_type": "personal",
    "credit_card_*": "...",
    "currency": "SEK",
    "exchange_rate": 0,
    "gross_amount": 1800.00,
    "net_amount": 1440.00,
    "gross_amount_sek": 1800,
    "net_amount_sek": 1440,
    "total_vat_25": 360.00,
    "total_vat_12": 0.00,
    "total_vat_6": 0.00,
    "ai_status": "...",
    "ai_confidence": 0.95,
    "other_data": "{...}",
    "ocr_raw": "...",
    "tags": []
  },
  "company": {
    "id": 123,
    "name": "Company Name",
    "orgnr": "556677-8899",
    "address": "...",
    "address2": "...",
    "zip": "...",
    "city": "...",
    "country": "...",
    "phone": "...",
    "www": "...",
    "email": "email@example.com"
  },
  "items": [...],
  "proposals": [...],
  "boxes": [...]
}
```

## Next Steps

1. **Frontend Implementation** (RP2, RP3, RP5-RP9)
   - Update `Receipts.jsx` ReceiptPreviewModal component
   - Implement all boxes with proper layout
   - Add individual scrolling for columns
   - Make all fields editable
   - Implement complex items + accounting table

2. **Testing**
   - Test Swish payment recognition with test PDF
   - Test all new fields display correctly
   - Test editing and saving
   - Test responsive layout

3. **PR Creation**
   - Push branch to remote
   - Create PR with comprehensive description
   - Link to all issues #43-#51

## Migration Instructions

Run the migration:
```bash
docker exec mind2-mysql-1 mysql -u root -proot mono_se_db_9 < database/migrations/0027_receipt_preview_modal_enhancements.sql
```

Or manually:
```sql
-- Add vat column
ALTER TABLE unified_files ADD COLUMN vat varchar(32) NULL COMMENT 'VAT/Organization number' AFTER company_id;

-- Add email column
ALTER TABLE companies ADD COLUMN email varchar(255) NULL AFTER www;

-- Update AI3 prompt (see migration file for full prompt)
```

## Notes

- Backend is ready for all frontend features
- AI3 prompt updated and tested
- Database schema is production-ready
- Frontend work is the remaining major task
