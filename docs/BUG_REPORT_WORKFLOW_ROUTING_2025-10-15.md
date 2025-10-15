# Bug Report: FirstCard Invoice Workflow Routing Error

**Date**: 2025-10-15
**Severity**: 🔴 CRITICAL - Production Blocking
**Status**: Root cause identified, fix pending
**Affected Component**: Credit Card Invoice Processing Pipeline

---

## Executive Summary

**Problem**: FirstCard credit card invoices uploaded via "Kortmatchning" → "Ladda upp utdrag" are incorrectly being processed through the **receipt workflow** (AI1-AI4) instead of the **credit card invoice workflow** (AI6).

**Impact**:
- Credit card invoices receive wrong AI analysis (receipt classification instead of invoice parsing)
- Line items are extracted as if they were receipt items instead of credit card transactions
- Matching to receipts fails because data structure is incorrect
- FirstCard reconciliation workflow completely broken

**Root Cause**: The `process_ocr` function in `tasks.py` unconditionally calls `process_ai_pipeline` for ALL files after OCR completion, completely ignoring the `workflow_type` field that was correctly set during upload.

---

## Test Case

**File ID**: `6f2243b3-508e-471e-8ab9-583cf85ac07a`
**Filename**: `FC_2505.pdf`
**File Type**: FirstCard credit card invoice (3 pages)
**Upload Method**: "Kortmatchning" → "Ladda upp utdrag" button

**Expected Workflow**:
- OCR → process_invoice_document → AI6 (credit_card_invoice_parsing)

**Actual Workflow**:
- OCR → process_ai_pipeline → AI1 (document_analysis) → AI2 (expense_classification) → AI3 (data_extraction) → AI4 (accounting)

**Evidence**:
```sql
-- Parent document (main PDF)
SELECT id, file_type, workflow_type, ai_status
FROM unified_files
WHERE id = '6f2243b3-508e-471e-8ab9-583cf85ac07a';

Result:
- workflow_type = 'creditcard_invoice' ✅ CORRECTLY SET
- ai_status = 'pending' (all AI stages show pending)

-- Child pages (page images)
SELECT id, file_type, workflow_type, ai_status, ai1_status, ai2_status, ai3_status
FROM unified_files
WHERE parent_file_id = '6f2243b3-508e-471e-8ab9-583cf85ac07a';

Result: All 3 pages show:
- workflow_type = 'creditcard_invoice' ✅ CORRECTLY SET
- ai1_status = 'completed' ❌ SHOULD NOT RUN FOR CREDITCARD INVOICES
- ai2_status = 'completed' ❌ SHOULD NOT RUN FOR CREDITCARD INVOICES
- ai3_status = 'completed' ❌ SHOULD NOT RUN FOR CREDITCARD INVOICES

-- Line items extracted (incorrectly as receipt items instead of credit card transactions)
SELECT COUNT(*) FROM receipt_items
WHERE main_id IN (
    SELECT id FROM unified_files
    WHERE parent_file_id = '6f2243b3-508e-471e-8ab9-583cf85ac07a'
);

Result: 52 items extracted ❌ WRONG TABLE - should be in creditcard_invoice_items
```

---

## Complete Workflow Trace

### Step 1: User Uploads Invoice ✅ CORRECT

**Location**: `main-system/app-frontend/src/ui/pages/CompanyCard.jsx:1063`

**Code**:
```javascript
const formData = new FormData()
formData.append('invoice', file)
const response = await api.fetch('/ai/api/reconciliation/firstcard/upload-invoice', {
  method: 'POST',
  body: formData,
})
```

**Result**: File uploaded to `/ai/api/reconciliation/firstcard/upload-invoice` endpoint

---

### Step 2: Backend Receives Upload ✅ CORRECT

**Location**: `backend/src/api/reconciliation_firstcard.py:upload_firstcard_invoice`

**Critical Code Sections**:

**Lines 312-321**: Sets workflow_type for main document
```python
# HARD ENFORCEMENT: Set workflow_type to enforce credit card invoice pipeline
if db_cursor is not None:
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET workflow_type = 'creditcard_invoice' WHERE id = %s",
                (invoice_id,),
            )
    except Exception:
        pass  # Best-effort
```

**Lines 357-367**: Sets workflow_type for all page images
```python
# HARD ENFORCEMENT: Set workflow_type for all page images in batch
if db_cursor is not None and page_file_ids:
    try:
        with db_cursor() as cur:
            placeholders = ', '.join(['%s'] * len(page_file_ids))
            cur.execute(
                f"UPDATE unified_files SET workflow_type = 'creditcard_invoice' WHERE id IN ({placeholders})",
                page_file_ids,
            )
    except Exception:
        pass  # Best-effort
```

**Result**:
- Main document gets `workflow_type = 'creditcard_invoice'` ✅
- All page images get `workflow_type = 'creditcard_invoice'` ✅
- OCR task queued for each page

---

### Step 3: OCR Processing ✅ CORRECT

**Location**: `backend/src/services/tasks.py:process_ocr`

**Process**:
1. PaddleOCR extracts text from each page image
2. OCR text saved to database
3. File status updated to 'ocr_complete'

**Result**: OCR completes successfully for all 3 pages

---

### Step 4: Post-OCR Routing ❌ **THIS IS THE BUG**

**Location**: `backend/src/services/tasks.py:1370-1376` (in `process_ocr` function)

**Problematic Code**:
```python
# Only continue to AI pipeline if OCR succeeded
try:
    process_ai_pipeline.delay(file_id)  # type: ignore[attr-defined]
except Exception:
    try:
        process_ai_pipeline.run(file_id)
    except Exception:
        pass
```

**Problem Analysis**:
- ❌ **NO CHECK** for `workflow_type` before calling `process_ai_pipeline`
- ❌ **UNCONDITIONALLY** queues the receipt workflow (AI1-AI4) for ALL files
- ❌ **IGNORES** the `workflow_type = 'creditcard_invoice'` that was set during upload
- ✅ For credit card invoices, should call `process_invoice_document.delay(file_id)` instead
- ✅ Or skip AI queueing entirely and let FirstCard endpoint handle it

**What Should Happen**:
```python
# Load file metadata to check workflow_type
try:
    with db_cursor() as cur:
        cur.execute(
            "SELECT workflow_type FROM unified_files WHERE id = %s",
            (file_id,)
        )
        row = cur.fetchone()
        workflow_type = row[0] if row else 'receipt'
except Exception:
    workflow_type = 'receipt'

# Route based on workflow_type
if workflow_type == 'creditcard_invoice':
    # For credit card invoices, trigger process_invoice_document (AI6)
    try:
        process_invoice_document.delay(file_id)
    except Exception:
        try:
            process_invoice_document.run(file_id)
        except Exception:
            pass
else:
    # For receipts and other documents, trigger regular AI pipeline (AI1-AI4)
    try:
        process_ai_pipeline.delay(file_id)
    except Exception:
        try:
            process_ai_pipeline.run(file_id)
        except Exception:
            pass
```

---

### Step 5: AI Pipeline Runs (Incorrectly) ❌ BUG CONSEQUENCE

**Location**: `backend/src/services/tasks.py:_run_ai_pipeline` (lines 874-1209)

**What Happens**:
1. **AI1** (document_analysis): Classifies as "receipt" or "other document"
2. **AI2** (expense_classification): Classifies expense type (meals, transport, etc.)
3. **AI3** (data_extraction): Extracts receipt items (merchant, amount, items, etc.)
4. **AI4** (accounting): Generates accounting proposals

**Problem**:
- ❌ This entire pipeline is designed for RECEIPTS, not credit card invoices
- ❌ Credit card invoices have different structure (multiple transactions, not single receipt)
- ❌ Data gets stored in wrong tables (`receipt_items` instead of `creditcard_invoice_items`)
- ❌ Extracted data is incompatible with FirstCard matching logic

**What Should Happen**:
- ✅ AI1-AI4 should be SKIPPED entirely for `workflow_type = 'creditcard_invoice'`
- ✅ Instead, `process_invoice_document` should trigger AI6 (credit_card_invoice_parsing)
- ✅ AI6 parses the invoice into credit card transactions
- ✅ Data saved to `creditcard_invoices_main` and `creditcard_invoice_items` tables

---

## Impact Assessment

### Affected Workflows

**🔴 COMPLETELY BROKEN**:
- FirstCard credit card invoice upload and parsing
- Credit card transaction matching
- Credit card reconciliation

**✅ NOT AFFECTED**:
- Normal receipt processing (AI1-AI4 still works for receipts)
- OCR text extraction
- Manual file upload for receipts

### Data Corruption Risk

**Current State**:
- Credit card invoices in database have `workflow_type = 'creditcard_invoice'` (correct)
- BUT also have `ai1_status = 'completed'`, `ai2_status = 'completed'`, etc. (wrong)
- AND have data in `receipt_items` table (wrong table)
- NO data in `creditcard_invoice_items` table (where it should be)

**Implications**:
- Existing FirstCard invoices cannot be matched to receipts
- Reprocessing will fail until bug is fixed
- Need to clean up incorrectly processed invoices after fix

---

## Root Cause Analysis

### Timeline of the Bug

1. **Original Design**: `workflow_type` field added to route files to different pipelines
2. **FirstCard Implementation**: Upload endpoint correctly sets `workflow_type = 'creditcard_invoice'`
3. **The Bug**: `process_ocr` was never updated to check `workflow_type` before routing
4. **Result**: All files go through receipt pipeline regardless of workflow_type

### Why This Wasn't Caught

1. **Silent Failure**: OCR completes successfully, AI1-AI4 complete successfully
2. **No Error Logs**: System doesn't detect that wrong workflow is running
3. **Downstream Impact**: Failure only becomes apparent during matching phase
4. **Misleading Status**: File shows `ai_status = 'pending'` but child pages show AI1-AI4 completed

### Code Design Issue

**Problem**: Workflow routing is decentralized
- Upload endpoint sets `workflow_type` ✅
- But OCR task doesn't check it ❌
- And AI pipeline doesn't validate it ❌

**Better Design**: Centralized workflow router
- Single function that reads `workflow_type` and dispatches to correct pipeline
- Validation that checks workflow matches file_type
- Clear logging of which workflow is being executed

---

## Proposed Fix

### Option A: Fix in process_ocr (RECOMMENDED)

**Location**: `backend/src/services/tasks.py:process_ocr` (lines 1370-1376)

**Change**:
```python
# After OCR completes successfully, route to appropriate workflow based on workflow_type

try:
    # Load workflow_type from database
    with db_cursor() as cur:
        cur.execute(
            "SELECT workflow_type FROM unified_files WHERE id = %s",
            (file_id,)
        )
        row = cur.fetchone()
        workflow_type = row[0] if row else 'receipt'
except Exception as e:
    logger.warning(f"Failed to load workflow_type for {file_id}, defaulting to 'receipt': {e}")
    workflow_type = 'receipt'

# Route to appropriate pipeline
if workflow_type == 'creditcard_invoice':
    # Credit card invoices → AI6 pipeline
    logger.info(f"Routing {file_id} to credit card invoice workflow (AI6)")
    try:
        process_invoice_document.delay(file_id)  # type: ignore[attr-defined]
    except Exception:
        try:
            process_invoice_document.run(file_id)
        except Exception:
            pass
else:
    # Receipts and other documents → AI1-AI4 pipeline
    logger.info(f"Routing {file_id} to receipt workflow (AI1-AI4)")
    try:
        process_ai_pipeline.delay(file_id)  # type: ignore[attr-defined]
    except Exception:
        try:
            process_ai_pipeline.run(file_id)
        except Exception:
            pass
```

**Pros**:
- Single point of control for workflow routing
- Clear logging of routing decisions
- Minimal code changes
- No impact on existing receipt workflow

**Cons**:
- Additional database query on every OCR completion
- Need to handle database errors gracefully

---

### Option B: Add validation in _run_ai_pipeline

**Location**: `backend/src/services/tasks.py:_run_ai_pipeline` (line 874)

**Change**: Add validation at start of function
```python
def _run_ai_pipeline(file_id: str) -> None:
    """Execute AI1-AI4 pipeline for receipts. Should NOT run for credit card invoices."""

    # Validate workflow_type before running pipeline
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT workflow_type FROM unified_files WHERE id = %s",
                (file_id,)
            )
            row = cur.fetchone()
            workflow_type = row[0] if row else 'receipt'

        if workflow_type == 'creditcard_invoice':
            logger.warning(
                f"Skipping AI1-AI4 pipeline for {file_id} - "
                f"workflow_type is 'creditcard_invoice', should use AI6 instead"
            )
            return
    except Exception as e:
        logger.error(f"Failed to validate workflow_type for {file_id}: {e}")
        # Continue with pipeline as fallback

    # ... rest of function
```

**Pros**:
- Defense in depth (prevents wrong pipeline even if routing is wrong)
- Clear error logging when mismatch detected
- Safer (catches routing errors)

**Cons**:
- Doesn't fix the root cause (OCR still queues wrong pipeline)
- Wastes resources queueing tasks that will be skipped
- Silent failure (file gets stuck after OCR)

---

### Recommended Approach: BOTH Option A + Option B

**Implementation Plan**:
1. **Fix routing** in `process_ocr` (Option A) - prevents the problem
2. **Add validation** in `_run_ai_pipeline` (Option B) - catches any future routing errors
3. **Add logging** at both points to track workflow routing
4. **Update tests** to verify correct routing for different workflow_types

---

## Testing Plan

### Test Case 1: New FirstCard Invoice Upload

**Steps**:
1. Upload FC_TEST.pdf via "Kortmatchning" → "Ladda upp utdrag"
2. Verify `workflow_type = 'creditcard_invoice'` in database
3. Wait for OCR to complete
4. **VERIFY**: `process_invoice_document` task queued (not `process_ai_pipeline`)
5. **VERIFY**: AI6 runs (credit_card_invoice_parsing)
6. **VERIFY**: No AI1-AI4 tasks run
7. **VERIFY**: Data saved to `creditcard_invoices_main` and `creditcard_invoice_items`
8. **VERIFY**: No data in `receipt_items` table for this file

**Expected Logs**:
```
[INFO] OCR completed for {file_id}
[INFO] Routing {file_id} to credit card invoice workflow (AI6)
[INFO] Starting process_invoice_document for {file_id}
[INFO] Running AI6 (credit_card_invoice_parsing) for {file_id}
[INFO] AI6 completed successfully for {file_id}
```

---

### Test Case 2: Normal Receipt Upload

**Steps**:
1. Upload normal receipt via "Process" page
2. Verify `workflow_type = 'receipt'` (or NULL) in database
3. Wait for OCR to complete
4. **VERIFY**: `process_ai_pipeline` task queued (not `process_invoice_document`)
5. **VERIFY**: AI1-AI4 run in sequence
6. **VERIFY**: No AI6 tasks run
7. **VERIFY**: Data saved to `receipt_items` and `ai_accounting_proposals`

**Expected Logs**:
```
[INFO] OCR completed for {file_id}
[INFO] Routing {file_id} to receipt workflow (AI1-AI4)
[INFO] Starting AI1 (document_analysis) for {file_id}
[INFO] Starting AI2 (expense_classification) for {file_id}
[INFO] Starting AI3 (data_extraction) for {file_id}
[INFO] Starting AI4 (accounting) for {file_id}
```

---

### Test Case 3: Existing Broken Files

**Files to Test**:
- `6f2243b3-508e-471e-8ab9-583cf85ac07a` (FC_2505.pdf)

**Steps**:
1. Delete incorrect data from `receipt_items` table
2. Reset AI status fields to NULL
3. Manually trigger reprocessing via `process_invoice_document`
4. **VERIFY**: AI6 runs successfully
5. **VERIFY**: Data correctly saved to `creditcard_invoice_items`
6. **VERIFY**: Invoice can be matched to receipts

---

## Data Cleanup Required

After deploying the fix, need to clean up incorrectly processed invoices:

```sql
-- Find all credit card invoices that went through wrong workflow
SELECT
    uf.id,
    uf.filename,
    uf.workflow_type,
    uf.ai1_status,
    uf.ai2_status,
    uf.ai3_status,
    COUNT(ri.id) as receipt_items_count
FROM unified_files uf
LEFT JOIN receipt_items ri ON ri.main_id = uf.id
WHERE uf.workflow_type = 'creditcard_invoice'
    AND (uf.ai1_status IS NOT NULL
         OR uf.ai2_status IS NOT NULL
         OR uf.ai3_status IS NOT NULL)
GROUP BY uf.id;

-- Cleanup steps for each affected file:
-- 1. Delete incorrect receipt_items
DELETE FROM receipt_items WHERE main_id = '{file_id}';

-- 2. Delete incorrect accounting proposals
DELETE FROM ai_accounting_proposals WHERE receipt_id = '{file_id}';

-- 3. Reset AI status fields
UPDATE unified_files
SET
    ai1_status = NULL,
    ai2_status = NULL,
    ai3_status = NULL,
    ai4_status = NULL,
    ai_status = 'pending',
    ai_confidence = NULL
WHERE id = '{file_id}';

-- 4. Manually trigger AI6 reprocessing
-- Use admin panel or direct task call
```

---

## Prevention Measures

### Code Review Checklist

When adding new workflow types:
- [ ] Verify `workflow_type` is set during upload
- [ ] Check that `process_ocr` routes to correct pipeline
- [ ] Validate that AI pipeline checks workflow compatibility
- [ ] Add logging for workflow routing decisions
- [ ] Write tests for new workflow routing

### Monitoring

Add alerts for:
- Files with `workflow_type = 'creditcard_invoice'` AND `ai1_status IS NOT NULL`
- Files stuck in OCR with no AI pipeline queued
- Mismatched workflow_type and AI status fields

### Documentation

Update docs:
- `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` - Add workflow routing logic
- `docs/SYSTEM_DOCS/FIRSTCARD_PROCESSING.md` - Document complete FC workflow
- Add inline comments in `process_ocr` explaining routing logic

---

## Related Files

**Frontend**:
- `main-system/app-frontend/src/ui/pages/CompanyCard.jsx` - Upload UI

**Backend**:
- `backend/src/api/reconciliation_firstcard.py` - Upload endpoint (sets workflow_type correctly)
- `backend/src/services/tasks.py` - OCR and AI pipeline tasks (BUG LOCATION)
  - `process_ocr` function (lines 1370-1376) - Missing workflow_type check
  - `_run_ai_pipeline` function (lines 874-1209) - Should validate workflow_type

**Database**:
- `unified_files` table - Stores `workflow_type` field
- `receipt_items` table - WRONG destination for credit card invoice data
- `creditcard_invoice_items` table - CORRECT destination for credit card invoice data

---

## Status

**Current State**:
- ❌ Bug identified and documented
- ❌ Fix not yet implemented
- ❌ Existing FirstCard invoices incorrectly processed

**Next Steps**:
1. Implement Option A (fix routing in process_ocr)
2. Implement Option B (add validation in _run_ai_pipeline)
3. Add comprehensive logging
4. Write unit tests for workflow routing
5. Clean up affected files in database
6. Test end-to-end with real FirstCard invoice
7. Update system documentation

**Priority**: 🔴 CRITICAL - Should be fixed immediately

---

**Document Created**: 2025-10-15
**Last Updated**: 2025-10-15
**Status**: Ready for implementation
