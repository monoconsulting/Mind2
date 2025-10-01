# AI Processing History - Enhanced Logging

## Overview

The `ai_processing_history` table has been enhanced to provide detailed logging for all AI stages (AI1-AI5) and OCR processing. This addresses the need for better visibility into what happened during AI processing and why certain stages may have failed.

## Changes Made

### 1. Database Schema Enhancement (Migration 0014)

**File**: `database/migrations/0014_enhance_ai_processing_history.sql`

New columns added to `ai_processing_history`:

| Column | Type | Description |
|--------|------|-------------|
| `ai_stage_name` | VARCHAR(64) | Human-readable AI stage name (e.g., "AI1-DocumentClassification") |
| `log_text` | TEXT | Detailed explanation of what happened in this stage |
| `error_message` | TEXT | Full error message if the stage failed |
| `confidence` | FLOAT | Confidence score for this AI stage result |
| `processing_time_ms` | INT | Processing time in milliseconds |
| `provider` | VARCHAR(64) | AI provider used (rule-based, openai, azure, paddleocr, etc.) |
| `model_name` | VARCHAR(128) | Model name used for this stage |

**Indexes added**:
- `idx_file_stage` on `(file_id, ai_stage_name)` for efficient querying
- `idx_status` on `(status)` for status filtering

### 2. Enhanced _history() Function

**File**: `backend/src/services/tasks.py`

The `_history()` function now accepts detailed parameters:

```python
def _history(
    file_id: str,
    job: str,
    status: str,
    ai_stage_name: str | None = None,
    log_text: str | None = None,
    error_message: str | None = None,
    confidence: float | None = None,
    processing_time_ms: int | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> None:
```

### 3. AI Stage Names and Status Values

Each AI stage has both a descriptive name (for logging) and a status value (for database):

| Stage | Log Name | Status Value | Description |
|-------|----------|--------------|-------------|
| FTP | `FTP-FileFetched` | `ftp_fetched` | File fetched from FTP server |
| OCR | `OCR-TextExtraction` | `ocr_done` | Text extraction from receipt images |
| AI1 | `AI1-DocumentClassification` | `ai1_completed` | Classify document type (receipt, invoice, other) |
| AI2 | `AI2-ExpenseClassification` | `ai2_completed` | Classify expense type (personal, corporate) |
| AI3 | `AI3-DataExtraction` | `ai3_completed` | Extract structured data (amounts, dates, merchant, etc.) |
| AI4 | `AI4-AccountingClassification` | `ai4_completed` | Generate accounting proposals |
| AI5 | `AI5-CreditCardMatching` | `ai5_completed` / `ai5_no_match` | Match receipts to credit card transactions |
| DONE | `Pipeline-Complete` | `proc_completed` | All processing completed |

**Note:** The `ai_status` column in `unified_files` uses the "Status Value" (e.g., `ai4_completed`), while the `ai_stage_name` column in `ai_processing_history` uses the "Log Name" (e.g., `AI4-AccountingClassification`).

### 4. Detailed Log Messages

Each stage now logs comprehensive information:

#### OCR Stage Example:
```
Success: "OCR completed successfully, extracted 342 characters; merchant: ICA Supermarket; amount: 125.50"
Error: "OCR processing failed or returned no results" + error_message: "FileNotFoundError: Image file not found"
```

#### AI1 (Document Classification) Example:
```
Success: "Classified document as 'receipt'; OCR text length: 342 characters; Reasoning: Receipt keywords detected"
Error: "Failed to classify document type from OCR text (342 chars)" + error_message: "KeyError: 'ocr_text'"
```

#### AI2 (Expense Classification) Example:
```
Success: "Classified expense as 'corporate'; Document type: receipt; Card identifier: visa; Reasoning: Detected card keyword 'visa'"
Error: "Failed to classify expense type for document_type='receipt'" + error_message: "ValueError: Invalid document_type"
```

#### AI3 (Data Extraction) Example:
```
Success: "Extracted structured data: gross=125.50, orgnr=556123-4567, purchase_date=2025-09-30T14:23:00, currency=SEK; Receipt items: 3; Company: ICA Supermarket AB"
Error: "Failed to extract structured data from document_type='receipt', expense_type='corporate'" + error_message: "AttributeError: 'NoneType' object has no attribute 'get'"
```

#### AI4 (Accounting Classification) Example:
```
Success: "Generated 3 accounting proposals; Vendor: ICA Supermarket AB; Amounts: gross=125.50, net=100.40, vat=25.10; Based on BAS 2025 chart of accounts"
Skipped: "Skipped: No accounting inputs available (missing gross_amount_sek, net_amount_sek, or company_id)"
Error: "Failed to classify accounting for vendor='ICA Supermarket AB', gross=125.50, net=100.40, vat=25.10" + error_message: "DatabaseError: Connection lost"
```

#### AI5 (Credit Card Matching) Example:
```
Success: "Match result: matched; Search criteria: merchant='ICA Supermarket', amount=125.50, date=2025-09-30 14:23:00; Matched to invoice item ID: 12345"
Success (no match): "Match result: not matched; Search criteria: merchant='ICA Supermarket', amount=125.50, date=2025-09-30 14:23:00; Reason: No transaction met the criteria"
Skipped: "Skipped: No purchase_datetime available for matching"
Error: "Failed to match credit card transaction for merchant='ICA Supermarket', amount=125.50" + error_message: "ConnectionError: Database timeout"
```

## Usage

### Running the Migration

```bash
# Connect to your MySQL database
mysql -h 127.0.0.1 -P 3310 -u mind -p mono_se_db_9 < database/migrations/0014_enhance_ai_processing_history.sql
```

### Querying the Enhanced Logs

#### Get all AI stages for a specific file:
```sql
SELECT
    ai_stage_name,
    status,
    log_text,
    error_message,
    confidence,
    processing_time_ms,
    provider,
    model_name,
    created_at
FROM ai_processing_history
WHERE file_id = 'your-file-id'
ORDER BY created_at;
```

#### Find all failed AI stages:
```sql
SELECT
    file_id,
    ai_stage_name,
    log_text,
    error_message,
    created_at
FROM ai_processing_history
WHERE status = 'error'
ORDER BY created_at DESC
LIMIT 50;
```

#### Get processing times by stage:
```sql
SELECT
    ai_stage_name,
    AVG(processing_time_ms) as avg_time_ms,
    MIN(processing_time_ms) as min_time_ms,
    MAX(processing_time_ms) as max_time_ms,
    COUNT(*) as count
FROM ai_processing_history
WHERE processing_time_ms IS NOT NULL
GROUP BY ai_stage_name
ORDER BY avg_time_ms DESC;
```

#### Get confidence scores by stage:
```sql
SELECT
    ai_stage_name,
    AVG(confidence) as avg_confidence,
    MIN(confidence) as min_confidence,
    MAX(confidence) as max_confidence,
    COUNT(*) as count
FROM ai_processing_history
WHERE confidence IS NOT NULL
GROUP BY ai_stage_name;
```

#### Find files that failed at specific stages:
```sql
SELECT DISTINCT file_id, log_text, error_message
FROM ai_processing_history
WHERE ai_stage_name = 'AI3-DataExtraction'
  AND status = 'error'
ORDER BY created_at DESC;
```

## Benefits

1. **Clear Stage Identification**: Each AI stage has a human-readable name making it easy to understand the pipeline flow
2. **Detailed Logging**: Comprehensive log messages explain exactly what was processed and what the results were
3. **Error Tracking**: Full error messages with context help diagnose issues quickly
4. **Performance Monitoring**: Processing times help identify bottlenecks
5. **Confidence Tracking**: Confidence scores per stage help assess AI quality
6. **Provider/Model Tracking**: Know which provider and model processed each stage

## Next Steps

After running the migration, the next time files are processed through the AI pipeline, you will see detailed logging in the `ai_processing_history` table with all the new information.