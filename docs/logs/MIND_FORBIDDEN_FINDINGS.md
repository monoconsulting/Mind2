# Forbidden Findings: `MERCHANT_NAME` and Hardcoded Data

## CRITICAL: `MERCHANT_NAME` Found in Codebase

The string `MERCHANT_NAME` was found in numerous locations throughout the codebase, despite instructions that it should never be used. This is a critical issue that needs immediate attention.

### Dev Branch Analysis (2025-10-11)

**Total occurrences in dev branch: 90**

#### CRITICAL VIOLATIONS (Direct use of non-existent column):

The following queries attempt to SELECT `merchant_name` directly from `unified_files` table, which DOES NOT have this column:

1. **backend/src/api/receipts.py:179** - `_fetch_receipt_details()`
   ```sql
   SELECT id, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status,
   ai_confidence, expense_type, tags, ocr_raw FROM unified_files WHERE id=%s
   ```

2. **backend/src/api/receipts.py:838** - `get_receipt_validation()`
   ```sql
   SELECT id, merchant_name, purchase_datetime, gross_amount, net_amount, ai_confidence
   FROM unified_files WHERE id=%s
   ```

3. **backend/src/api/receipts.py:895** - `get_receipt_accounting_proposal()`
   ```sql
   SELECT id, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence
   FROM unified_files WHERE id=%s
   ```

4. **backend/src/services/db/files.py** - Database file operations

5. **backend/src/api/export.py** - Export functionality using merchant_name

#### CORRECT USAGE (Using JOIN to companies table):

These queries correctly use JOIN to get merchant name from companies table:

1. **backend/src/api/receipts.py:507** - `list_receipts()`
   ```sql
   SELECT u.id, u.original_filename, c.name as merchant_name, u.purchase_datetime, ...
   FROM unified_files u
   LEFT JOIN companies c ON c.id = u.company_id
   ```
   ✅ This is CORRECT - uses alias after JOIN

#### LEGITIMATE USES (Not related to unified_files):

The following uses are LEGITIMATE as they reference other tables or models:

- **models/ai_processing.py** - Pydantic models (CreditCardInvoiceItem.merchant_name)
- **models/company_card.py** - Company card models
- **models/receipts.py** - Receipt model with merchant_name field
- **services/tasks.py** - Comments explaining to use companies table
- **API reconciliation endpoints** - Using invoice_lines.merchant_name (correct table)

### Summary of Violations by Severity:

**🔴 CRITICAL (Must Fix Immediately):**
- 3 queries in `receipts.py` that will fail at runtime
- 1+ queries in `export.py`
- 1+ queries in `files.py`

**🟡 MEDIUM (Incorrect architecture but may work):**
- Write operations that attempt to set merchant_name in unified_files
- `_normalise_receipt_update()` accepting merchant_name parameter

**🟢 ACCEPTABLE:**
- Model definitions (Pydantic/dataclass with merchant_name field)
- References to invoice_lines.merchant_name or other tables
- Comments and documentation
- Test files (using mock data)

### Recommended Actions:

1. **Immediate:** Fix the 3-5 critical SQL queries in receipts.py, export.py, and files.py
2. **Short-term:** Remove all write operations trying to set merchant_name in unified_files
3. **Long-term:** Refactor Receipt model to not use merchant_name field, use company relationship instead

---

## Current Branch Status (feature/receipt-preview-modal-enhancements)

### ✅ FIXES IMPLEMENTED:

The current branch has **CORRECTED** the critical violations found in dev branch:

1. **receipts.py:_fetch_receipt_details()** - ✅ FIXED
   ```sql
   SELECT u.id, c.name, u.company_id, u.vat, u.purchase_datetime, ...
   FROM unified_files u
   LEFT JOIN companies c ON c.id = u.company_id
   WHERE u.id=%s
   ```
   - Properly uses JOIN to companies table
   - Gets merchant name from `c.name` not from unified_files
   - Includes company_id in result for reference

2. **receipts.py:_fetch_company_by_id()** - ✅ NEW FUNCTION
   - Separate function to fetch full company details
   - Used in modal endpoint to provide complete company information

3. **receipts.py:get_receipt_modal()** - ✅ ENHANCED
   - Now fetches company details separately
   - Returns both receipt and company data in structured format

### Comparison: Dev vs Current Branch

| Aspect | Dev Branch | Current Branch |
|--------|-----------|----------------|
| `_fetch_receipt_details()` | ❌ Uses non-existent merchant_name column | ✅ Uses JOIN to companies |
| Image display | ✅ Works (simple _storage_dir) | ✅ Works (after fix) |
| Database schema compliance | ❌ Critical violations | ✅ Fully compliant |
| Company data handling | ❌ Mixed merchant_name usage | ✅ Structured company object |

### Remaining Work:

Even though current branch fixes receipts.py, other files still need attention:
- ❌ `api/export.py` - Still needs merchant_name fixes
- ❌ `services/db/files.py` - Still needs merchant_name fixes
- ❌ Model definitions still reference merchant_name (acceptable for now)

---

## Complete Analysis of Current Branch (feature/receipt-preview-modal-enhancements)

### 📊 Statistics:
- **Total merchant_name occurrences:** 90 (same as dev)
- **Critical violations found:** 2 files with direct SELECT on unified_files
- **Mock data locations:** 2 instances found

### 🔴 CRITICAL: Direct SELECT merchant_name FROM unified_files

These queries will FAIL at runtime because merchant_name column does NOT exist:

#### 1. **backend/src/api/export.py:218**
```python
"SELECT id, merchant_name, purchase_datetime, gross_amount, net_amount, ai_status, submitted_by "
f"FROM unified_files WHERE id IN ({placeholders})"
```
**Status:** ❌ CRITICAL - Will cause runtime error
**Function:** Export receipts for reconciliation
**Impact:** Export functionality broken

#### 2. **backend/src/services/db/files.py:34**
```python
"SELECT id, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence "
"FROM unified_files WHERE id=%s"
```
**Status:** ❌ CRITICAL - Will cause runtime error
**Function:** `get_receipt()` - Load single receipt
**Impact:** Receipt loading broken in certain flows

### 🟢 CORRECT: Using JOIN to companies table

These queries are CORRECT:

#### 1. **backend/src/api/receipts.py:787** ✅
```sql
SELECT u.id, u.original_filename, c.name as merchant_name, ...
FROM unified_files u
LEFT JOIN companies c ON c.id = u.company_id
```
**Status:** ✅ CORRECT

#### 2. **backend/src/api/receipts.py:352** ✅
```sql
SELECT u.id, c.name, u.company_id, u.vat, ...
FROM unified_files u
LEFT JOIN companies c ON c.id = u.company_id
```
**Status:** ✅ CORRECT - Uses proper JOIN and gets merchant from companies table

### 🟡 LEGITIMATE: Other tables with merchant_name column

These are ACCEPTABLE as they reference other tables that DO have merchant_name:

- **api/ai_processing.py:471** - `invoice_lines.merchant_name` ✅
- **api/reconciliation_firstcard.py:484, 916** - `invoice_lines.merchant_name` ✅
- **api/export.py:173** - `invoice_lines.merchant_name` ✅

---

## 🎭 MOCK DATA VIOLATIONS

### Instance 1: OCR Fallback Data (CRITICAL)

**File:** `backend/src/services/ocr.py:342-350`

```python
if not ocr_result.get("text"):
    return {
        "merchant_name": "Demo Shop",  # ❌ HARDCODED MOCK DATA
        "purchase_datetime": None,
        "gross_amount": 123.45,  # ❌ HARDCODED MOCK DATA
        "net_amount": 98.76,  # ❌ HARDCODED MOCK DATA
        "confidence": 0.5,
        "boxes_saved": True,
        "vat_breakdown": {25: 24.69},  # ❌ HARDCODED MOCK DATA
        "line_items": [],
    }
```

**Severity:** 🔴 CRITICAL
**Issue:** When OCR fails to extract text, returns fake demo data instead of None/empty
**Impact:** Database polluted with fake receipts
**Fix Required:** Return None or empty values, DO NOT return demo data

**Correct Implementation:**
```python
if not ocr_result.get("text"):
    return {
        "merchant_name": None,
        "purchase_datetime": None,
        "gross_amount": None,
        "net_amount": None,
        "confidence": 0.0,
        "boxes_saved": True,
        "vat_breakdown": {},
        "line_items": [],
    }
```

### Instance 2: Database Migration Seed Data

**File:** `backend/src/services/db/migrations.py:100-102`

```python
INSERT INTO unified_files
  (id, file_type, created_at, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence)
VALUES
  ('demo-0001','receipt', NOW(), 'Demo Cafe', '556677-8899', NOW(), 89.00, 71.20, 'new', 0.42),
  ('demo-0002','receipt', NOW(), 'Grocer AB', '112233-4455', NOW(), 245.50, 196.40, 'processed', 0.93),
  ('demo-0003','receipt', NOW(), 'Tools & Co', '998877-6655', NOW(), 1299.00, 1039.20, 'error', 0.12)
```

**Severity:** 🟡 MEDIUM
**Issue:** Demo seed data with fake receipts, ALSO uses non-existent merchant_name column
**Impact:**
- Migration will FAIL because merchant_name column doesn't exist
- Demo data violates "no mock data" rule
**Context:** Only runs when `seed_demo=True` flag is set
**Fix Required:**
1. Remove merchant_name column from INSERT
2. Either remove demo data entirely OR properly create companies first and link via company_id

---

## Summary of All Violations in Current Branch

### By Severity:

**🔴 CRITICAL (3 violations):**
1. `api/export.py:218` - SELECT merchant_name FROM unified_files
2. `services/db/files.py:34` - SELECT merchant_name FROM unified_files
3. `services/ocr.py:342` - Returns hardcoded "Demo Shop" mock data

**🟡 MEDIUM (1 violation):**
1. `services/db/migrations.py:100` - INSERT with merchant_name + demo data

**🟢 FIXED (3 improvements):**
1. `api/receipts.py:_fetch_receipt_details()` - Now uses JOIN ✅
2. `api/receipts.py:_fetch_company_by_id()` - New function for company data ✅
3. `api/receipts.py:get_receipt_modal()` - Structured company/receipt separation ✅

### Required Actions (Priority Order):

1. **IMMEDIATE** - Fix `services/ocr.py:342` mock data fallback
2. **IMMEDIATE** - Fix `api/export.py:218` SELECT query
3. **IMMEDIATE** - Fix `services/db/files.py:34` SELECT query
4. **SHORT-TERM** - Fix `services/db/migrations.py:100` demo seed data
5. **LONG-TERM** - Audit all model definitions for merchant_name usage

### Files Containing `MERCHANT_NAME`:

*   `CLAUDE.md`
*   `backend/src/api/ai_processing.py`
*   `backend/src/api/export.py`
*   `backend/src/api/receipts.py`
*   `backend/src/api/reconciliation_firstcard.py`
*   `backend/src/models/ai_processing.py`
*   `backend/src/models/company_card.py`
*   `backend/src/models/receipts.py`
*   `backend/src/services/accounting.py`
*   `backend/src/services/ai_service.py`
*   `backend/src/services/db/files.py`
*   `backend/src/services/db/migrations.py`
*   `backend/src/services/fetch_ftp_enhanced.py`
*   `backend/src/services/fetch_ftp_updated.py`
*   `backend/src/services/ocr.py`
*   `backend/src/services/tasks.py`
*   `backend/src/services/validation.py`
*   `backend/test_file_information.py`
*   `backend/tests/contract/test_export_api.py`
*   `backend/tests/contract/test_receipt_update.py`
*   `backend/tests/integration/test_company_card_manual_edit_and_export.py`
*   `backend/tests/integration/test_firstcard_invoice_flow.py`
*   `backend/tests/integration/test_firstcard_pdf_import.py`
*   `backend/tests/integration/test_full_flow.py`
*   `backend/tests/integration/test_invoice_upload_status.py`
*   `backend/tests/integration/test_receipt_images_and_boxes.py`
*   `backend/tests/integration/test_receipt_validation_proposal.py`
*   `backend/tests/unit/test_accounting_service.py`
*   `backend/tests/unit/test_accounting_vat_multi_rate.py`
*   `backend/tests/unit/test_enrichment_service.py`
*   `backend/tests/unit/test_receipt_modal_api.py`
*   `backend/tests/unit/test_tasks_invoice_pipeline.py`
*   `backend/tests/unit/test_validation_service.py`
*   `database/migrations/0015_audit_report.md`
*   `docs/SYSTEM_DOCS/MIND_AI_v.1.0.md`
*   `docs/SYSTEM_DOCS/MIND_API_DOCS.md`
*   `docs/SYSTEM_DOCS/MIND_DB_DESIGN.md`
*   `docs/SYSTEM_DOCS/MIND_INVOICE_MATCH_IMPLEMENTATION_PLAN.md`
*   `docs/SYSTEM_DOCS/MIND_OCR.md`
*   `docs/SYSTEM_DOCS/MIND_WORKFLOW.md`
*   `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`
*   `specs/001-mind-system-receipt/data-model.md`
*   `specs/001-mind-system-receipt/tasks.md`

## Other Hardcoded Data

Further investigation is required to identify other hardcoded data. This will be documented in `/docs/SYSTEM_DOCS/MIND_MOCK_HARDCODED_PLAN.md` as per the original request.
