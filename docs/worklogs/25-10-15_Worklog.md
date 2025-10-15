# Worklog 2025-10-15

## Session: FirstCard Workflow Error Investigation & Fixes

### Initial Task
Investigated Docker logs to identify and fix all errors preventing FirstCard (FC) workflow from functioning correctly.

---

## Critical Errors Found (Pre-Fix)

### 1. **OPENAI_API_KEY Configuration Error** ❌ CRITICAL
**Location**: `.env` file and `docker-compose.yml`

**Problem**:
- Line 42 of `.env` had placeholder: `OPENAI_API_KEY=your-openai-api-key`
- Line 77 had real API key but was commented out
- `docker-compose.yml` wasn't passing `OPENAI_API_KEY` to containers
- Result: AI6 (credit card invoice parsing) timing out after 300s and falling back to deterministic parser

**Evidence from logs**:
```
[2025-10-15 03:04:02,910: ERROR/ForkPoolWorker-1] OpenAI API error: HTTPSConnectionPool(host='api.openai.com', port=443): Read timed out. (read timeout=300)
[2025-10-15 03:04:02,910: ERROR/ForkPoolWorker-1] Provider call for credit_card_invoice_parsing failed (provider=OpenAI, model=gpt-5): OpenAI API call failed: HTTPSConnectionPool(host='api.openai.com', port=443): Read timed out. (read timeout=300)
```

**Fix Applied**:
1. Commented out placeholder on line 42 of `.env`
2. Uncommented real API key on line 77 of `.env`
3. Added to `docker-compose.yml` for both `ai-api` and `celery-worker` services:
   ```yaml
   - OPENAI_API_KEY=${OPENAI_API_KEY}
   - AI_PROVIDER=${AI_PROVIDER}
   - OLLAMA_HOST=${OLLAMA_HOST}
   ```

**Files Modified**:
- `E:\projects\Mind2\.env` (lines 42, 77)
- `E:\projects\Mind2\docker-compose.yml` (ai-api and celery-worker sections)

---

### 2. **Illegal State Transition Warning** ⚠️ MAJOR
**Location**: `backend/src/services/tasks.py` - `process_invoice_document` function

**Problem**:
```
[2025-10-15 03:17:51,554: WARNING/ForkPoolWorker-4] Illegal transition for processing_status id=087f60fd-f344-4d01-b6db-e783e0b8d053: current=ready_for_matching target=ai_processing
```

- Invoice document `087f60fd-f344-4d01-b6db-e783e0b8d053` was already processed (status=ready_for_matching)
- Duplicate task in queue tried to reprocess it, causing illegal transition attempt
- Function didn't check if document was already processed before attempting state transition

**Fix Applied**:
Added duplicate processing prevention check at start of `process_invoice_document` function (line 1908-1922):

```python
# Check if already processed - prevent duplicate processing
metadata = _load_invoice_metadata(document_id) or {}
current_status = metadata.get("processing_status")
if current_status in (
    InvoiceProcessingStatus.READY_FOR_MATCHING.value,
    InvoiceProcessingStatus.MATCHING_COMPLETED.value,
    InvoiceProcessingStatus.COMPLETED.value,
):
    logger.info(f"Skipping AI6 processing for {document_id} - already in state: {current_status}")
    return {
        "document_id": document_id,
        "status": current_status,
        "ok": True,
        "reason": "already_processed"
    }
```

**Files Modified**:
- `E:\projects\Mind2\backend\src\services\tasks.py` (function: process_invoice_document, lines 1908-1922)

---

### 3. **OpenAI API Timeout Too Short** ⚠️ MAJOR
**Location**: `backend/src/services/ai_service.py` - `OpenAIProvider.generate` method

**Problem**:
- Timeout was 300 seconds (5 minutes)
- Credit card invoice parsing with GPT-5 on large documents consistently timed out
- No retry logic for transient failures
- Evidence: Multiple timeout errors in celery logs at exactly 300s mark

**Fix Applied**:
Implemented robust retry logic with exponential backoff in `OpenAIProvider.generate` method:

1. **Increased timeout**: 300s → 600s (10 minutes)
2. **Added retry logic**: 3 attempts with exponential backoff (2s, 4s, 8s delays)
3. **Retry on**:
   - Timeout errors
   - 5xx server errors (500, 502, 503, 504)
   - Connection errors
4. **No retry on**: 4xx client errors (authentication, rate limits, etc.)

**Code Structure** (lines 93-177):
```python
max_retries = 3
base_delay = 2  # seconds
timeout = 600  # Increased from 300s to 600s (10 minutes)

for attempt in range(max_retries):
    try:
        response = requests.post(url, json=request_payload, headers=headers, timeout=timeout)
        # ... response processing ...
    except requests.exceptions.Timeout as exc:
        # Retry with exponential backoff
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            logger.warning(f"OpenAI API timeout (attempt {attempt + 1}/{max_retries}), retrying in {delay}s")
            time.sleep(delay)
            continue
    except requests.exceptions.RequestException as exc:
        # Check if retryable (5xx errors, connection errors)
        # ... retry logic ...
```

**Files Modified**:
- `E:\projects\Mind2\backend\src\services\ai_service.py` (class: OpenAIProvider, method: generate, lines 93-177)

---

### 4. **Database Schema Error - Currency Column** ✅ ALREADY FIXED
**Location**: Database migration

**Problem Found in Logs**:
```
[2025-10-15 03:04:02,941: ERROR/ForkPoolWorker-1] Failed to persist credit card invoice data for 087f60fd-f344-4d01-b6db-e783e0b8d053: 1054 (42S22): Unknown column 'currency' in 'field list'
```

**Investigation**:
- Checked migration `backend/migrations/0036_add_currency_column.sql`
- Verified migration was already applied successfully
- `creditcard_invoices_main` table has `currency` column with `idx_currency` index
- Error was historical - occurred before migration was run

**Status**: ✅ NO ACTION NEEDED - Already fixed by migration 0036

---

### 5. **AI4 Accounting Validation Errors** ⚠️ MINOR
**Location**: Multiple files failing AI4 accounting classification

**Problem**:
```
[2025-10-15 02:57:39,316: ERROR/ForkPoolWorker-4] Invalid AI4 payload for c7ebefac-c037-4fde-bdb5-d77cfab88efa: entries[1].item_id is missing
```

**Root Cause**:
- AI3 (data extraction) returned NO receipt_items for several files
- When AI4 tries to generate accounting proposals, it has no item_id to reference
- LLM returns proposals with `item_id: null`
- Validation correctly rejects these

**Examples**:
- File `c7ebefac-c037-4fde-bdb5-d77cfab88efa`: No receipt items extracted
- File `f4dbcbde-f60f-494c-808f-cae3db5ed9c1`: No receipt items extracted
- File `629aa92c-588c-43e7-b89c-f79699180b50`: No receipt items extracted
- File `1c0590c1-14cf-45e4-9342-0781312fb0e3`: No receipt items extracted

**Status**: ⚠️ DEFER - This is an AI3/LLM quality issue, not a critical bug. Files fall back to manual review.

---

### 6. **AI3 Missing Company Data** ℹ️ INFO
**Problem**:
```
[2025-10-15 02:56:17,293: WARNING/ForkPoolWorker-3] Cannot ensure company: both name and orgnr are empty
```

**Status**: ℹ️ INFO - LLM data extraction quality issue, not a bug

---

### 7. **Nginx 502 Bad Gateway** ❓ TRANSIENT
**User Reported Error**:
```
172.23.0.1 - - [15/Oct/2025:04:27:32 +0000] "GET /ai/api/receipts?page=1&page_size=25 HTTP/1.1" 502 157
connect() failed (111: Connection refused) while connecting to upstream
```

**Investigation**:
- Backend logs show successful query processing at exact same timestamp: `04:27:32`
- Backend was responding correctly: `"Query returned 13 rows"`
- Likely a transient connection issue, not persistent

**Status**: ⏳ MONITOR - May have been transient. Will re-check after rebuild.

---

### 8. **Celery Security Warning** ⚠️ LOW PRIORITY
**Warning**:
```
SecurityWarning: You're running the worker with superuser privileges: this is absolutely not recommended!
Please specify a different user using the --uid option.
```

**Status**: ⏳ DEFER - Development environment only, not critical for functionality. Requires Dockerfile changes.

---

## Summary of Changes

### Files Modified: 4

1. **E:\projects\Mind2\.env**
   - Line 42: Commented out placeholder API key
   - Line 77: Uncommented real OPENAI_API_KEY

2. **E:\projects\Mind2\docker-compose.yml**
   - Added OPENAI_API_KEY, AI_PROVIDER, OLLAMA_HOST to ai-api service
   - Added OPENAI_API_KEY, AI_PROVIDER, OLLAMA_HOST to celery-worker service

3. **E:\projects\Mind2\backend\src\services\tasks.py**
   - Function: `process_invoice_document` (lines 1908-1922)
   - Added duplicate processing prevention check

4. **E:\projects\Mind2\backend\src\services\ai_service.py**
   - Class: `OpenAIProvider`, Method: `generate` (lines 93-177)
   - Increased timeout from 300s to 600s
   - Added retry logic with exponential backoff (3 attempts, 2s/4s/8s delays)
   - Retry on timeout, 5xx errors, connection errors

---

## Expected Results After Restart

### ✅ Should Be Fixed:
1. ✅ OpenAI API key now properly configured
2. ✅ AI6 credit card invoice parsing should work with GPT-5
3. ✅ Illegal state transition warnings eliminated
4. ✅ API timeouts reduced with 600s timeout + retry logic
5. ✅ Currency column error already fixed (migration 0036)

### ⏳ To Monitor:
1. ⏳ Nginx 502 errors (check if transient)
2. ⏳ AI4 validation errors (LLM quality issue, not critical)

### ⏳ Deferred:
1. ⏳ Celery security warning (non-critical, dev environment)

---

## Next Steps

1. **User Action**: Rebuild Docker containers, clean database, clean logs
2. **My Action**: Investigate all container logs after rebuild
3. **Test**: End-to-end FirstCard workflow with real FC file
4. **Verify**: File `087f60fd-f344-4d01-b6db-e783e0b8d053` can be reprocessed successfully

---

## Technical Notes

### FirstCard Workflow Overview
1. **Upload**: FC PDF uploaded → `workflow_type='creditcard_invoice'` set
2. **OCR**: Each page processed → text extracted
3. **AI6**: All pages combined → GPT-5 parses invoice structure
4. **Storage**: Data saved to `creditcard_invoices_main` + `creditcard_invoice_items`
5. **Matching**: Invoice lines matched to receipts in `unified_files`

### Key Discovery
The root cause of FC workflow failure was **missing OpenAI API key configuration**, not code bugs. The code was correct but couldn't execute because:
- Environment variable not passed to containers
- API calls timing out without proper credentials
- Falling back to deterministic parser (which has limited capability)

---

## Session 2: Workflow Routing Bug Investigation

### Task
Investigate why file `6f2243b3-508e-471e-8ab9-583cf85ac07a` (FC_2505.pdf) was processed through receipt workflow (AI1-AI4) instead of credit card invoice workflow (AI6) despite being uploaded via "Kortmatchning" → "Ladda upp utdrag".

---

### Investigation Results

#### File Details
- **File ID**: `6f2243b3-508e-471e-8ab9-583cf85ac07a`
- **Filename**: `FC_2505.pdf`
- **Type**: FirstCard credit card invoice (3 pages)
- **Upload Method**: "Kortmatchning" → "Ladda upp utdrag" button

#### Database State
```sql
-- Parent document
workflow_type = 'creditcard_invoice'  ✅ CORRECTLY SET
ai_status = 'pending'

-- Child pages (3 page images)
workflow_type = 'creditcard_invoice'  ✅ CORRECTLY SET
ai1_status = 'completed'  ❌ SHOULD NOT RUN
ai2_status = 'completed'  ❌ SHOULD NOT RUN
ai3_status = 'completed'  ❌ SHOULD NOT RUN

-- Extracted data
52 items in receipt_items table  ❌ WRONG TABLE (should be creditcard_invoice_items)
0 items in creditcard_invoice_items table  ❌ MISSING DATA
```

---

### Root Cause: Workflow Routing Bug 🔴 CRITICAL

#### Summary
`workflow_type` field IS being set correctly during upload, but the `process_ocr` function IGNORES it and unconditionally routes ALL files through the receipt workflow (AI1-AI4).

#### Complete Workflow Trace

**Step 1: Upload (✅ CORRECT)**
- Location: `CompanyCard.jsx:1063`
- Action: POST to `/ai/api/reconciliation/firstcard/upload-invoice`

**Step 2: Backend Processes Upload (✅ CORRECT)**
- Location: `reconciliation_firstcard.py:312-321` and `357-367`
- Action: Sets `workflow_type = 'creditcard_invoice'` for both main document and all page images
- Result: ✅ Database correctly shows `workflow_type = 'creditcard_invoice'`

**Step 3: OCR Processing (✅ CORRECT)**
- Location: `tasks.py:process_ocr`
- Action: PaddleOCR extracts text from all 3 pages
- Result: ✅ OCR completes successfully

**Step 4: Post-OCR Routing (❌ THIS IS THE BUG)**
- Location: `tasks.py:1370-1376` (in `process_ocr` function)
- **Problematic Code**:
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

**Problem**:
- ❌ NO CHECK for `workflow_type` before calling `process_ai_pipeline`
- ❌ UNCONDITIONALLY queues receipt workflow (AI1-AI4) for ALL files
- ❌ IGNORES the `workflow_type = 'creditcard_invoice'` set during upload

**What Should Happen**:
- Check `workflow_type` from database
- If `workflow_type = 'creditcard_invoice'` → call `process_invoice_document` (AI6 pipeline)
- If `workflow_type = 'receipt'` (or NULL) → call `process_ai_pipeline` (AI1-AI4 pipeline)

**Step 5: Wrong AI Pipeline Runs (❌ BUG CONSEQUENCE)**
- Location: `tasks.py:_run_ai_pipeline` (lines 874-1209)
- Action: Runs AI1 → AI2 → AI3 → AI4 (receipt workflow)
- Result: Credit card invoice data extracted as receipt items and stored in wrong table

---

### Impact Assessment

**🔴 COMPLETELY BROKEN**:
- FirstCard credit card invoice processing
- All invoices uploaded via "Kortmatchning" go through wrong workflow
- Data stored in wrong database tables
- Matching to receipts fails due to incorrect data structure

**Data Corruption**:
- Credit card invoice line items incorrectly stored in `receipt_items` table
- Missing data in `creditcard_invoice_items` table where it should be
- Accounting proposals generated for wrong document type

---

### Solution

**Detailed Bug Report Created**: `docs/BUG_REPORT_WORKFLOW_ROUTING_2025-10-15.md`

**Proposed Fix**: Add workflow routing logic in `process_ocr` function (tasks.py:1370-1376)

```python
# After OCR completes, route to appropriate workflow based on workflow_type

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
        process_invoice_document.delay(file_id)
    except Exception:
        try:
            process_invoice_document.run(file_id)
        except Exception:
            pass
else:
    # Receipts and other documents → AI1-AI4 pipeline
    logger.info(f"Routing {file_id} to receipt workflow (AI1-AI4)")
    try:
        process_ai_pipeline.delay(file_id)
    except Exception:
        try:
            process_ai_pipeline.run(file_id)
        except Exception:
            pass
```

**Additional Safeguard**: Add validation in `_run_ai_pipeline` to skip processing if `workflow_type = 'creditcard_invoice'` (defense in depth)

---

### Files Involved

**Frontend**:
- `main-system/app-frontend/src/ui/pages/CompanyCard.jsx:1063` - Upload button

**Backend**:
- `backend/src/api/reconciliation_firstcard.py:312-321, 357-367` - Sets workflow_type ✅
- `backend/src/services/tasks.py:1370-1376` - Missing workflow_type check ❌
- `backend/src/services/tasks.py:874-1209` - _run_ai_pipeline (should validate workflow_type)

---

### Next Steps

1. **Implement Fix**: Add workflow routing logic in `process_ocr`
2. **Add Validation**: Add workflow_type check in `_run_ai_pipeline`
3. **Add Logging**: Log workflow routing decisions
4. **Clean Up Data**: Delete incorrect receipt_items for affected credit card invoices
5. **Reprocess**: Trigger AI6 for existing credit card invoices
6. **Test**: Upload new FirstCard invoice and verify correct workflow
7. **Update Docs**: Document workflow routing in system docs

---

### Status

- ✅ Root cause identified and documented
- ✅ Detailed bug report created
- ❌ Fix not yet implemented
- ❌ Existing credit card invoices need cleanup and reprocessing

**Priority**: 🔴 CRITICAL - Blocks FirstCard reconciliation workflow

**Documentation**: See `docs/BUG_REPORT_WORKFLOW_ROUTING_2025-10-15.md` for complete technical details

---

**End of Worklog 2025-10-15**
