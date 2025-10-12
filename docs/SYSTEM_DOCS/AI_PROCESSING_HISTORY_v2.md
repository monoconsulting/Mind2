# Comprehensive AI Processing History Logging Plan

## Current State Analysis

### Existing Workflow Steps (Per MIND_WORKFLOW.md):
1. **FTP/Upload** - File import from FTP or manual upload
2. **PDF Conversion** - Convert PDF to images (only if PDF uploaded)
3. **OCR** - Text extraction from images
4. **AI1** - Document Classification (receipt/invoice/other)
5. **AI2** - Expense Classification (personal/corporate)
6. **AI3** - Data Extraction (amounts, dates, merchant, company, items)
7. **AI4** - Accounting Classification (BAS 2025 proposals)
8. **AI5** - Credit Card Matching
9. **Pipeline Complete** - Final status

### Current Logging Gaps:
- ✅ **AI1-AI5** have good logging in `tasks.py:_run_ai_pipeline()` (lines 353-657)
- ⚠️ **OCR** has minimal logging in `tasks.py:process_ocr()` (lines 786-822) - needs enhancement
- ❌ **FTP fetch** (`fetch_ftp.py`) has NO history logging at all
- ❌ **File upload** (`ingest.py`) has NO history logging at all
- ❌ **PDF conversion** has NO history logging at all
- ⚠️ **AI stage functions** in `api/ai_processing.py` don't log AI responses/reasoning

## Database Schema

The `ai_processing_history` table includes the following columns:

```sql
CREATE TABLE ai_processing_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  file_id VARCHAR(36) NOT NULL,
  job_type VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  ai_stage_name VARCHAR(64) NULL COMMENT 'Human-readable AI stage name',
  log_text TEXT NULL COMMENT 'Detailed log message explaining what happened',
  error_message TEXT NULL COMMENT 'Error message if the stage failed',
  confidence FLOAT NULL COMMENT 'Confidence score for this AI stage result',
  processing_time_ms INT NULL COMMENT 'Processing time in milliseconds',
  provider VARCHAR(64) NULL COMMENT 'AI provider used (rule-based, openai, azure, etc.)',
  model_name VARCHAR(128) NULL COMMENT 'Model name used for this stage',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_file_stage (file_id, ai_stage_name),
  INDEX idx_status (status)
);
```

## Implementation Plan

### Phase 1: Add Logging to FTP/Upload Steps

**File: `backend/src/services/fetch_ftp.py`**

Add history logging to:
- `_insert_unified_file()` function (line 138) - Log successful FTP fetch
- Error handling in `fetch_from_ftp()` (lines 455-457) - Log FTP errors per file
- Error handling in `fetch_from_local_inbox()` (lines 294-296) - Log local inbox errors

**Log format:**
- **Stage name**: `FTP-FileFetched` or `Upload-FileReceived`
- **Success log**: "File fetched from FTP: filename={name}, size={bytes}, hash={hash[:16]}..."
- **Error log**: "Failed to fetch file from FTP: {error details}"

**File: `backend/src/api/ingest.py`**

Add history logging to:
- Line 134 - After successful DB insert during upload
- Lines 138-140 - When duplicate detected
- Line 164 - When upload fails

**Log format:**
- **Stage name**: `Upload-FileReceived`
- **Success log**: "File uploaded successfully: filename={name}, size={bytes}, hash={hash[:16]}..."
- **Duplicate log**: "Skipped duplicate file: hash={hash[:16]}..."
- **Error log**: "Failed to upload file: {error details}"

### Phase 2: Add PDF Conversion Logging

**File: `backend/src/services/ocr.py` (or wherever PDF conversion happens)**

Add history logging to PDF conversion:
- Log when PDF is detected
- Log number of pages converted
- Log conversion success/failure per page
- Log total conversion time

**Log format:**
- **Stage name**: `PDF-Conversion`
- **Success log**: "PDF converted to {page_count} images: pages=[page-1.jpg, page-2.jpg, ...]; conversion_time={ms}ms"
- **Error log**: "Failed to convert PDF: {error details}"

### Phase 3: Enhance OCR Logging

**File: `backend/src/services/tasks.py`**

Enhance OCR logging (lines 786-822) to include:
- OCR provider details (PaddleOCR version)
- Text preview (first 100 chars)
- Detected merchant/amount snippets
- More detailed error context

**Enhanced log format:**
```
Success: "OCR completed: extracted {chars} characters; preview: '{text[:100]}...'; detected patterns: merchant={merchant_hint}, amount={amount_hint}"
Error: "OCR failed: {detailed_error_with_stack_trace}"
```

### Phase 4: Log AI Response Details

**File: `backend/src/services/tasks.py`**

Enhance existing AI logging in `_run_ai_pipeline()` to capture:
- **AI1** (lines 362-379): Add full reasoning text to log
- **AI2** (lines 413-432): Add card detection details
- **AI3** (lines 493-512): Add ALL extracted fields (currently missing many)
- **AI4** (lines 551-569): Add BAS account details
- **AI5** (lines 611-632): Add match scoring details

**New comprehensive AI3 log format:**
```
"Extracted data: company_name='{name}', orgnr='{orgnr}', gross={gross}, net={net}, vat={vat}, currency={curr}, purchase_date={date}, payment_type={type}, receipt_number={num}, items_count={count}; Company details: address='{addr}', city='{city}', zip='{zip}'; Items: [{item1_name}@{price}, {item2_name}@{price}, ...]"
```

### Phase 5: Create History Helper Function

**File: `backend/src/services/fetch_ftp.py` and `backend/src/api/ingest.py`**

Add a shared `_history()` helper function (import from tasks.py or create local wrapper):
```python
from services.tasks import _history

# Use in fetch_ftp.py after line 141:
_history(
    file_id=file_id,
    job="ftp_fetch",
    status="success",
    ai_stage_name="FTP-FileFetched",
    log_text=f"File fetched from FTP: filename={filename}, size={len(data)} bytes, hash={content_hash[:16]}...",
    provider="ftp",
)

# Use in ingest.py after line 134:
_history(
    file_id=receipt_id,
    job="upload",
    status="success",
    ai_stage_name="Upload-FileReceived",
    log_text=f"File uploaded: filename={safe_filename}, size={len(data)} bytes, hash={file_hash[:16]}...",
    provider="web_upload",
)
```

### Phase 6: Validation & Testing

After implementation, every file should have exactly **8-10 history records**:

1. FTP-FileFetched OR Upload-FileReceived
2. PDF-Conversion (only for PDF files)
3. OCR-TextExtraction
4. AI1-DocumentClassification
5. AI2-ExpenseClassification
6. AI3-DataExtraction
7. AI4-AccountingClassification (or skipped)
8. AI5-CreditCardMatching (or skipped)
9. Pipeline-Complete

**Note:** Image files (JPG, PNG) will have 8 records, PDF files will have 9 records (with PDF-Conversion step).

**Validation Query:**
```sql
-- Check for files with too few processing steps
SELECT
    file_id,
    COUNT(*) as stage_count,
    GROUP_CONCAT(ai_stage_name ORDER BY created_at) as stages
FROM ai_processing_history
GROUP BY file_id
HAVING stage_count < 7
ORDER BY MAX(created_at) DESC;

-- Count files by processing step count
SELECT
    stage_count,
    COUNT(*) as file_count
FROM (
    SELECT file_id, COUNT(*) as stage_count
    FROM ai_processing_history
    GROUP BY file_id
) counts
GROUP BY stage_count
ORDER BY stage_count;
```

## Stage Naming Convention

All `ai_stage_name` values must follow this exact format:

| Stage | ai_stage_name | job_type | status |
|-------|---------------|----------|---------|
| FTP Fetch | `FTP-FileFetched` | `ftp_fetch` | `success`/`error` |
| Upload | `Upload-FileReceived` | `upload` | `success`/`error` |
| PDF Conv | `PDF-Conversion` | `pdf_convert` | `success`/`error` |
| OCR | `OCR-TextExtraction` | `ocr` | `success`/`error` |
| AI1 | `AI1-DocumentClassification` | `ai1` | `success`/`error` |
| AI2 | `AI2-ExpenseClassification` | `ai2` | `success`/`error` |
| AI3 | `AI3-DataExtraction` | `ai3` | `success`/`error` |
| AI4 | `AI4-AccountingClassification` | `ai4` | `success`/`error`/`skipped` |
| AI5 | `AI5-CreditCardMatching` | `ai5` | `success`/`error`/`skipped` |
| Pipeline | `Pipeline-Complete` | `ai_pipeline` | `success`/`error` |
| Pipeline | `Pipeline-Initialization` | `ai_pipeline` | `error` |

## Key Implementation Rules

1. **Never use mock data** - All logged data must come from actual processing
2. **Log everything AI returns** - Include reasoning, confidence, extracted fields
3. **Consistent stage names** - Use exact names from the table above
4. **Best-effort logging** - Never fail the main process if logging fails
5. **Include context** - Log enough detail to debug issues without reading code
6. **Log ALL extracted fields** - Don't skip fields in AI3; log everything the AI returned
7. **Preserve error context** - Include full error type and message in error_message column

## Files to Modify

1. `backend/src/services/fetch_ftp.py` - Add FTP logging (3 locations)
2. `backend/src/api/ingest.py` - Add upload logging (3 locations)
3. `backend/src/services/ocr.py` - Add PDF conversion logging (2 locations)
4. `backend/src/services/tasks.py` - Enhance OCR & AI logging (8 locations)

## Expected Outcome

- Image files (JPG/PNG) will have 8 detailed history records
- PDF files will have 9 detailed history records (includes PDF-Conversion)
- Each record includes comprehensive log_text with all relevant data
- AI responses, reasoning, and extracted fields are fully logged
- Easy to audit, debug, and count successful processing steps
- Performance metrics available via processing_time_ms
- Can easily identify which files are PDFs vs images by presence of PDF-Conversion stage

## Example Complete Log Sequences

### Example 1: Image File (JPG/PNG) - 8 records
```
file_id: abc-123
1. FTP-FileFetched (ftp_fetch, success): "File fetched from FTP: filename=receipt.jpg, size=45231 bytes, hash=a3f2..."
2. OCR-TextExtraction (ocr, success): "OCR completed: extracted 452 characters; preview: 'ICA MAXI Stockholm...'"
3. AI1-DocumentClassification (ai1, success): "Classified document as 'receipt'; Reasoning: Contains merchant name, item list, and total amount"
4. AI2-ExpenseClassification (ai2, success): "Classified expense as 'personal'; Document type: receipt"
5. AI3-DataExtraction (ai3, success): "Extracted data: company_name='ICA Maxi AB', orgnr='5566778899', gross=125.50, net=100.40, vat=25.10..."
6. AI4-AccountingClassification (ai4, success): "Generated 3 accounting proposals; Vendor: ICA Maxi AB; Amounts: gross=125.50, net=100.40..."
7. AI5-CreditCardMatching (ai5, success): "Match result: matched; Matched to invoice item ID: 4521; merchant='ICA MAXI', amount=125.50..."
8. Pipeline-Complete (ai_pipeline, success): "Completed 7 AI stages successfully: AI1, AI2, AI3, AI4, AI5"
```

### Example 2: PDF File - 9 records
```
file_id: def-456
1. Upload-FileReceived (upload, success): "File uploaded successfully: filename=invoice.pdf, size=128456 bytes, hash=b7e4..."
2. PDF-Conversion (pdf_convert, success): "PDF converted to 3 images: pages=[page-1.jpg, page-2.jpg, page-3.jpg]; conversion_time=1523ms"
3. OCR-TextExtraction (ocr, success): "OCR completed: extracted 1847 characters across 3 pages; preview: 'FAKTURA Invoice Number...'"
4. AI1-DocumentClassification (ai1, success): "Classified document as 'invoice'; Reasoning: Contains invoice number, due date, and payment terms"
5. AI2-ExpenseClassification (ai2, success): "Classified expense as 'corporate'; Document type: invoice"
6. AI3-DataExtraction (ai3, success): "Extracted data: company_name='Acme Supplier AB', orgnr='1122334455', gross=5420.00, net=4336.00..."
7. AI4-AccountingClassification (ai4, success): "Generated 4 accounting proposals; Vendor: Acme Supplier AB; Amounts: gross=5420.00..."
8. AI5-CreditCardMatching (ai5, skipped): "Skipped: No purchase_datetime available for matching"
9. Pipeline-Complete (ai_pipeline, success): "Completed 6 AI stages successfully: AI1, AI2, AI3, AI4"
```
