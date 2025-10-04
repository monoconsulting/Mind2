# Credit Card Invoice Matching - Implementation Plan

**Version:** 1.0
**Date:** 2025-10-04
**Status:** Planning Phase

---

## Executive Summary

This document provides a comprehensive implementation plan for adding credit card invoice upload and matching functionality to the MIND system. The feature will allow users to upload multi-page credit card invoices (PDF or images) through the "Kortmatchning" (Card Matching) menu, process them through OCR, extract transaction data via AI, and automatically match transactions to existing receipts in the system.

---

## 1. Current State Analysis

### 1.1 Existing Infrastructure

**PDF Processing Pipeline** (✅ Already implemented)
- Location: `backend/src/services/pdf_conversion.py`
- Function: `pdf_to_png_pages()` - Converts PDF to PNG pages using PyMuPDF (fitz)
- Output: List of `PdfPage` objects with index, path, and bytes
- DPI: 300 (configurable)
- Used in: Receipt upload flow in `backend/src/api/ingest.py`

**Credit Card Reconciliation** (✅ Partially implemented)
- Location: `backend/src/api/reconciliation_firstcard.py`
- Current capabilities:
  - Import JSON-based statements or parse simple PDF text
  - Store in `invoice_documents` and `invoice_lines` tables
  - Auto-match transactions to receipts based on date and amount
  - Manual confirm/reject workflow
- Limitations:
  - PDF parsing is basic regex-based (not OCR)
  - No multi-page image handling
  - No AI-powered data extraction

**Upload Infrastructure** (✅ Implemented)
- Location: `backend/src/api/ingest.py`
- Handles: Images, PDFs, Audio files
- Features:
  - File type detection via `services/file_detection.py`
  - Hash-based duplicate detection
  - Automatic PDF-to-PNG conversion
  - Celery task queue integration for OCR
  - Processing history tracking in `ai_processing_history`

**Database Schema** (✅ Implemented)
```sql
-- Invoice tables (0003_2025_09_18_invoice_schema.sql)
invoice_documents (id, invoice_type, period_start, period_end, status, metadata_json)
invoice_lines (id, invoice_id, transaction_date, amount, merchant_name, matched_file_id, match_score, match_status)
invoice_line_history (id, invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id)

-- Receipt/unified files
unified_files (id, file_type, ocr_raw, purchase_datetime, gross_amount, net_amount, ...)
receipt_items (main_id, article_id, name, number, item_price_ex_vat, ...)
```

### 1.2 Current Frontend

**CompanyCard Page** (✅ Implemented)
- Location: `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`
- Current features:
  - List statements from `/ai/api/reconciliation/firstcard/statements`
  - Auto-match button triggers `/ai/api/reconciliation/firstcard/match`
  - Status badges and statistics
- Missing:
  - Upload invoice button
  - File upload modal
  - Progress tracking for multi-page processing

**Upload Pattern** (✅ Reference available)
- Location: `main-system/app-frontend/src/ui/pages/Process.jsx`
- Pattern: `UploadModal` component with drag-drop and file selection
- Endpoint: `POST /ai/api/ingest/upload` with FormData

---

## 2. Technical Requirements

### 2.1 High-Level Flow

```
1. User uploads credit card invoice (PDF/images) via "Kortmatchning" page
   ↓
2. Backend detects file type and routes to appropriate processor
   ↓
3. If PDF → Convert to PNG pages (using existing pdf_to_png_pages)
   ↓
4. Store PDF record in unified_files as file_type='invoice'
   ↓
5. Store each page as separate unified_files record (file_type='invoice_page')
   ↓
6. Queue OCR tasks for each page (using existing process_ocr)
   ↓
7. After OCR completes → Queue AI extraction task
   ↓
8. AI extracts: period dates, transaction lines (date, merchant, amount)
   ↓
9. Create invoice_documents record with invoice_type='credit_card_invoice'
   ↓
10. Create invoice_lines records for each transaction
   ↓
11. Run auto-matching algorithm against unified_files + receipt_items
   ↓
12. Update invoice_lines.matched_file_id and unified_files with match status
   ↓
13. Frontend displays results and allows manual review
```

### 2.2 Data Flow Diagram

```
┌─────────────────┐
│  User uploads   │
│  PDF/Image      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  File Type Detection    │
│  (detect_file)          │
└────────┬────────────────┘
         │
    ┌────▼────┐
    │  PDF?   │
    └─┬────┬──┘
      │Yes │No (Image)
      │    │
      ▼    ▼
┌─────────────┐  ┌──────────────┐
│ PDF→PNG     │  │ Store Image  │
│ Conversion  │  │ as invoice   │
└──────┬──────┘  └──────┬───────┘
       │                │
       ▼                ▼
┌──────────────────────────┐
│  Store in unified_files  │
│  file_type='invoice'     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Queue OCR Tasks         │
│  (process_ocr)           │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  OCR Completion          │
│  (ocr_raw populated)     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Queue Invoice Extraction    │
│  (process_invoice_ai)        │
└────────────┬─────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  AI Extraction                 │
│  - Period dates                │
│  - Transaction lines           │
│  - Merchant names, amounts     │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Create invoice_documents      │
│  Create invoice_lines          │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Auto-match Transactions       │
│  - Date matching               │
│  - Amount matching (tolerance) │
│  - Merchant name similarity    │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Update Match Results          │
│  - invoice_lines.matched_file  │
│  - unified_files.invoice_match │
└────────────────────────────────┘
```

---

## 3. Database Schema Changes

### 3.1 New Fields (if needed)

**unified_files** (Enhancement)
```sql
-- Add invoice-specific status tracking (optional - can use existing ai_status)
ALTER TABLE unified_files
ADD COLUMN invoice_match_status VARCHAR(32) NULL COMMENT 'Status for invoice matching: pending, matched, unmatched';

-- Add reference to invoice document (optional - can query via invoice_lines)
ALTER TABLE unified_files
ADD COLUMN matched_invoice_id VARCHAR(36) NULL COMMENT 'Reference to invoice_documents.id if matched to invoice line';
```

**invoice_documents** (Enhancement)
```sql
-- Add source file reference
ALTER TABLE invoice_documents
ADD COLUMN source_file_id VARCHAR(36) NULL COMMENT 'Reference to unified_files.id for uploaded PDF/image';

-- Add processing status
ALTER TABLE invoice_documents
ADD COLUMN processing_status VARCHAR(32) DEFAULT 'uploaded' COMMENT 'uploaded, ocr_pending, ocr_done, ai_processing, ready_for_matching, matched, completed';
```

**invoice_lines** (Enhancement)
```sql
-- Add confidence scores for AI extraction
ALTER TABLE invoice_lines
ADD COLUMN extraction_confidence FLOAT NULL COMMENT 'AI confidence for extracted data (0-1)';

-- Add raw OCR text for this line (optional)
ALTER TABLE invoice_lines
ADD COLUMN ocr_source_text TEXT NULL COMMENT 'Original OCR text that was parsed';
```

### 3.2 Migration Script

**File:** `database/migrations/0016_invoice_matching_enhancements.sql`
```sql
-- Invoice Matching Enhancements
-- Date: 2025-10-04

-- unified_files enhancements
ALTER TABLE unified_files
ADD COLUMN IF NOT EXISTS invoice_match_status VARCHAR(32) NULL
COMMENT 'Status for invoice matching: pending, matched, unmatched, reviewed';

ALTER TABLE unified_files
ADD COLUMN IF NOT EXISTS matched_invoice_id VARCHAR(36) NULL
COMMENT 'Reference to invoice_documents.id if matched to invoice line';

-- invoice_documents enhancements
ALTER TABLE invoice_documents
ADD COLUMN IF NOT EXISTS source_file_id VARCHAR(36) NULL
COMMENT 'Reference to unified_files.id for uploaded PDF/image';

ALTER TABLE invoice_documents
ADD COLUMN IF NOT EXISTS processing_status VARCHAR(32) DEFAULT 'uploaded'
COMMENT 'uploaded, ocr_pending, ocr_done, ai_processing, ready_for_matching, matched, completed';

-- invoice_lines enhancements
ALTER TABLE invoice_lines
ADD COLUMN IF NOT EXISTS extraction_confidence FLOAT NULL
COMMENT 'AI confidence for extracted data (0-1)';

ALTER TABLE invoice_lines
ADD COLUMN IF NOT EXISTS ocr_source_text TEXT NULL
COMMENT 'Original OCR text that was parsed';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_unified_invoice_match ON unified_files(invoice_match_status);
CREATE INDEX IF NOT EXISTS idx_invoice_docs_processing ON invoice_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_invoice_docs_source ON invoice_documents(source_file_id);
```

---

## 4. Backend Implementation

### 4.1 New API Endpoints

**File:** `backend/src/api/reconciliation_firstcard.py` (enhance existing)

```python
@recon_bp.post("/reconciliation/firstcard/upload-invoice")
@auth_required
def upload_invoice():
    """
    Upload credit card invoice (PDF or image) for processing.

    Request: multipart/form-data with 'file' field
    Response: {
        "file_id": "uuid",
        "invoice_type": "credit_card_invoice",
        "status": "uploaded",
        "pages": 3  # if PDF
    }
    """
    # Implementation details in section 4.2
    pass

@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/status")
def get_invoice_status(invoice_id: str):
    """
    Get processing status of uploaded invoice.

    Response: {
        "invoice_id": "uuid",
        "processing_status": "ai_processing",
        "ocr_progress": {"completed": 2, "total": 3},
        "lines_extracted": 15,
        "lines_matched": 8
    }
    """
    pass

@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/lines")
def get_invoice_lines(invoice_id: str):
    """
    Get transaction lines from invoice with match status.

    Response: {
        "lines": [
            {
                "id": 123,
                "transaction_date": "2025-09-15",
                "merchant_name": "Coffee Shop AB",
                "amount": 150.50,
                "matched_file_id": "receipt-uuid",
                "match_status": "auto",
                "match_score": 0.95,
                "matched_receipt": {
                    "id": "receipt-uuid",
                    "merchant_name": "Coffee Shop",
                    "purchase_datetime": "2025-09-15T14:30:00"
                }
            }
        ]
    }
    """
    pass
```

### 4.2 Upload Handler Implementation

**File:** `backend/src/api/reconciliation_firstcard.py`

```python
from services.pdf_conversion import pdf_to_png_pages
from services.file_detection import detect_file
from services.storage import FileStorage
from services.tasks import process_ocr, process_invoice_ai_extraction
import hashlib
import uuid
from pathlib import Path

@recon_bp.post("/reconciliation/firstcard/upload-invoice")
@auth_required
def upload_invoice():
    """Upload credit card invoice for OCR and AI processing."""

    if 'file' not in request.files:
        return jsonify({"error": "no_file"}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "invalid_file"}), 400

    # Read file data
    data = file.read()
    file_hash = hashlib.sha256(data).hexdigest()

    # Check for duplicates
    if _invoice_hash_exists(file_hash):
        return jsonify({"error": "duplicate_file"}), 409

    # Detect file type
    safe_filename = secure_filename(file.filename)
    detection = detect_file(data, safe_filename)

    invoice_id = str(uuid.uuid4())
    submitted_by = request.headers.get('X-User', 'admin')
    storage = FileStorage(os.getenv('STORAGE_DIR', '/data/storage'))

    if detection.kind == "pdf":
        # Convert PDF to pages
        try:
            pages = pdf_to_png_pages(data, storage.base / "invoices", invoice_id, dpi=300)
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return jsonify({"error": "pdf_conversion_failed", "message": str(e)}), 500

        if not pages:
            return jsonify({"error": "empty_pdf"}), 400

        # Store PDF record in unified_files
        _insert_unified_file(
            file_id=invoice_id,
            file_type="invoice",
            content_hash=file_hash,
            submitted_by=submitted_by,
            original_filename=safe_filename,
            ai_status="uploaded",
            mime_type="application/pdf",
            file_suffix=".pdf",
            other_data={
                "invoice_type": "credit_card_invoice",
                "page_count": len(pages),
                "source": "card_matching_upload"
            }
        )

        # Save original PDF
        storage.save_original(invoice_id, safe_filename, data)

        # Store each page
        page_ids = []
        for page in pages:
            page_id = str(uuid.uuid4())
            page_hash = hashlib.sha256(page.bytes).hexdigest()
            page_number = page.index + 1

            _insert_unified_file(
                file_id=page_id,
                file_type="invoice_page",
                content_hash=page_hash,
                submitted_by=submitted_by,
                original_filename=f"{safe_filename}_page_{page_number:04d}.png",
                ai_status="uploaded",
                mime_type="image/png",
                file_suffix=".png",
                original_file_id=invoice_id,
                original_file_name=safe_filename,
                other_data={
                    "page_number": page_number,
                    "source_invoice": invoice_id,
                    "invoice_type": "credit_card_invoice"
                }
            )

            storage.save(page_id, f"page_{page_number:04d}.png", page.bytes)
            page_ids.append(page_id)

            # Queue OCR task for this page
            process_ocr.delay(page_id)

        # Create invoice_documents record
        _create_invoice_document(
            invoice_id=invoice_id,
            invoice_type="credit_card_invoice",
            source_file_id=invoice_id,
            processing_status="ocr_pending"
        )

        return jsonify({
            "file_id": invoice_id,
            "invoice_type": "credit_card_invoice",
            "status": "uploaded",
            "pages": len(page_ids),
            "page_ids": page_ids
        }), 200

    elif detection.kind == "image":
        # Single image invoice
        _insert_unified_file(
            file_id=invoice_id,
            file_type="invoice",
            content_hash=file_hash,
            submitted_by=submitted_by,
            original_filename=safe_filename,
            ai_status="uploaded",
            mime_type=detection.mime_type,
            file_suffix=Path(safe_filename).suffix,
            other_data={
                "invoice_type": "credit_card_invoice",
                "source": "card_matching_upload"
            }
        )

        storage.save_original(invoice_id, safe_filename, data)

        # Create invoice_documents record
        _create_invoice_document(
            invoice_id=invoice_id,
            invoice_type="credit_card_invoice",
            source_file_id=invoice_id,
            processing_status="ocr_pending"
        )

        # Queue OCR task
        process_ocr.delay(invoice_id)

        return jsonify({
            "file_id": invoice_id,
            "invoice_type": "credit_card_invoice",
            "status": "uploaded",
            "pages": 1
        }), 200

    else:
        return jsonify({"error": "unsupported_file_type"}), 400

def _invoice_hash_exists(content_hash: str) -> bool:
    """Check if invoice with this hash already exists."""
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute(
                """SELECT id FROM unified_files
                   WHERE content_hash = %s
                   AND file_type IN ('invoice', 'invoice_page')
                   LIMIT 1""",
                (content_hash,)
            )
            return cur.fetchone() is not None
    except Exception:
        return False

def _create_invoice_document(invoice_id: str, invoice_type: str, source_file_id: str, processing_status: str):
    """Create invoice_documents record."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                """INSERT INTO invoice_documents
                   (id, invoice_type, source_file_id, processing_status, status)
                   VALUES (%s, %s, %s, %s, 'imported')""",
                (invoice_id, invoice_type, source_file_id, processing_status)
            )
    except Exception as e:
        logger.error(f"Failed to create invoice document: {e}")
        raise
```

### 4.3 AI Extraction Task

**File:** `backend/src/services/tasks.py` (add new task)

```python
@celery_app.task
@track_task("process_invoice_ai_extraction")
def process_invoice_ai_extraction(invoice_id: str) -> dict[str, Any]:
    """
    Extract transaction data from invoice OCR text using AI.

    This task:
    1. Loads all OCR text from invoice pages
    2. Calls AI service to extract structured data
    3. Creates invoice_lines records
    4. Triggers auto-matching
    """

    if db_cursor is None:
        return {"error": "db_unavailable"}

    try:
        # Load OCR text from all pages
        with db_cursor() as cur:
            # Get main invoice file
            cur.execute(
                """SELECT id, other_data FROM unified_files
                   WHERE id=%s AND file_type='invoice'""",
                (invoice_id,)
            )
            invoice_row = cur.fetchone()
            if not invoice_row:
                raise ValueError(f"Invoice {invoice_id} not found")

            # Get all pages' OCR text
            cur.execute(
                """SELECT id, ocr_raw, other_data FROM unified_files
                   WHERE original_file_id=%s AND file_type='invoice_page'
                   ORDER BY JSON_EXTRACT(other_data, '$.page_number')""",
                (invoice_id,)
            )
            pages = cur.fetchall()

        if not pages:
            # Single-page invoice
            with db_cursor() as cur:
                cur.execute(
                    "SELECT ocr_raw FROM unified_files WHERE id=%s",
                    (invoice_id,)
                )
                row = cur.fetchone()
                ocr_text = row[0] if row else ""
        else:
            # Multi-page - concatenate OCR text
            ocr_text = "\n\n--- PAGE BREAK ---\n\n".join([p[1] or "" for p in pages])

        if not ocr_text.strip():
            _history(invoice_id, "invoice_ai", "error",
                    error_message="No OCR text available")
            return {"error": "no_ocr_text", "invoice_id": invoice_id}

        # Call AI service for extraction
        from services.invoice_ai import extract_invoice_transactions

        extraction_result = extract_invoice_transactions(ocr_text)

        # Update invoice_documents with period dates
        with db_cursor() as cur:
            cur.execute(
                """UPDATE invoice_documents
                   SET period_start=%s, period_end=%s, processing_status='ai_completed'
                   WHERE id=%s""",
                (extraction_result.get('period_start'),
                 extraction_result.get('period_end'),
                 invoice_id)
            )

            # Insert transaction lines
            lines_inserted = 0
            for line in extraction_result.get('transactions', []):
                cur.execute(
                    """INSERT INTO invoice_lines
                       (invoice_id, transaction_date, amount, merchant_name,
                        description, extraction_confidence, ocr_source_text)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (invoice_id,
                     line.get('date'),
                     line.get('amount'),
                     line.get('merchant'),
                     line.get('description'),
                     line.get('confidence', 0.5),
                     line.get('source_text'))
                )
                lines_inserted += 1

        _history(invoice_id, "invoice_ai", "success",
                log_text=f"Extracted {lines_inserted} transaction lines",
                confidence=extraction_result.get('overall_confidence'))

        # Trigger auto-matching
        process_invoice_matching.delay(invoice_id)

        return {
            "invoice_id": invoice_id,
            "lines_extracted": lines_inserted,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Invoice AI extraction failed for {invoice_id}: {e}")
        _history(invoice_id, "invoice_ai", "error", error_message=str(e))
        return {"error": str(e), "invoice_id": invoice_id}
```

### 4.4 AI Service for Invoice Extraction

**File:** `backend/src/services/invoice_ai.py` (new file)

```python
"""AI service for extracting structured data from credit card invoices."""

from typing import Any, Dict, List
import json
import logging
from services.ai_service import AIService, OpenAIProvider
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

INVOICE_EXTRACTION_PROMPT = """
You are an AI assistant that extracts structured transaction data from credit card invoice OCR text.

The OCR text may be from a multi-page credit card statement. Extract ALL transactions.

Expected output format (JSON):
{
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD",
    "card_number_last4": "1234",
    "transactions": [
        {
            "date": "YYYY-MM-DD",
            "merchant": "Merchant name",
            "amount": 123.45,
            "description": "Full transaction description",
            "confidence": 0.95,
            "source_text": "Original OCR line"
        }
    ],
    "overall_confidence": 0.9
}

Rules:
1. Extract period_start and period_end from statement header if present
2. Parse ALL transaction lines with date, merchant, and amount
3. Amount should be positive for purchases, negative for refunds
4. Include confidence score (0-1) for each transaction
5. Include source_text showing original OCR text for each line
6. Handle Swedish date formats (YYYY-MM-DD or DD/MM/YYYY)
7. Handle both dot and comma as decimal separator
8. Merchant names should be cleaned (remove trailing numbers, codes)

Return ONLY valid JSON, no additional text.
"""

def extract_invoice_transactions(ocr_text: str) -> Dict[str, Any]:
    """
    Extract transaction data from credit card invoice OCR text using AI.

    Args:
        ocr_text: Raw OCR text from invoice (may be multi-page)

    Returns:
        Dict with period dates, transactions list, and confidence scores
    """

    # Check if AI is enabled
    if not os.getenv('AI_PROCESSING_ENABLED', 'false').lower() == 'true':
        # Fallback to regex-based extraction
        return _fallback_regex_extraction(ocr_text)

    try:
        provider = OpenAIProvider(
            model_name=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            api_key=os.getenv('OPENAI_API_KEY')
        )

        ai_service = AIService(provider)

        # Prepare payload
        payload = {
            "ocr_text": ocr_text,
            "task": "extract_credit_card_transactions"
        }

        # Call AI
        response = provider.generate(INVOICE_EXTRACTION_PROMPT, payload)

        if not response.parsed:
            logger.warning("AI returned no parsed JSON, using fallback")
            return _fallback_regex_extraction(ocr_text)

        result = response.parsed

        # Validate structure
        if 'transactions' not in result:
            result['transactions'] = []

        if not result.get('overall_confidence'):
            result['overall_confidence'] = 0.7

        return result

    except Exception as e:
        logger.error(f"AI extraction failed: {e}, using fallback")
        return _fallback_regex_extraction(ocr_text)

def _fallback_regex_extraction(ocr_text: str) -> Dict[str, Any]:
    """
    Fallback regex-based extraction when AI is unavailable.

    This is a simple pattern matcher for common credit card statement formats.
    """

    transactions = []

    # Pattern: Date (various formats) + Merchant + Amount
    # Example: "2025-09-15 Coffee Shop AB 150.50"
    # Example: "15/09/2025 Coffee Shop AB 150,50"

    patterns = [
        # ISO format: 2025-09-15 Merchant Name 150.50
        r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+(-?\d+[.,]\d{2})',
        # European format: 15/09/2025 Merchant Name 150,50
        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\d+[.,]\d{2})',
        # Short format: 15/09 Merchant Name 150.50
        r'(\d{2}/\d{2})\s+(.+?)\s+(-?\d+[.,]\d{2})'
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, ocr_text):
            date_str, merchant, amount_str = match.groups()

            # Parse date
            try:
                if '/' in date_str:
                    if len(date_str) == 5:  # DD/MM format, need year
                        # Assume current year or extract from context
                        date_str = f"{date_str}/2025"
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                else:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                transaction_date = date_obj.strftime('%Y-%m-%d')
            except:
                continue

            # Parse amount
            amount_val = float(amount_str.replace(',', '.'))

            # Clean merchant name
            merchant_clean = merchant.strip()

            transactions.append({
                "date": transaction_date,
                "merchant": merchant_clean,
                "amount": amount_val,
                "description": merchant_clean,
                "confidence": 0.6,  # Lower confidence for regex
                "source_text": match.group(0)
            })

    # Try to extract period from text
    period_start = None
    period_end = None
    period_pattern = r'Period[:\s]+(\d{4}-\d{2}-\d{2})\s*(?:to|till|-)\s*(\d{4}-\d{2}-\d{2})'
    period_match = re.search(period_pattern, ocr_text, re.IGNORECASE)
    if period_match:
        period_start = period_match.group(1)
        period_end = period_match.group(2)

    return {
        "period_start": period_start,
        "period_end": period_end,
        "transactions": transactions,
        "overall_confidence": 0.6
    }
```

### 4.5 Enhanced Matching Task

**File:** `backend/src/services/tasks.py` (add new task)

```python
@celery_app.task
@track_task("process_invoice_matching")
def process_invoice_matching(invoice_id: str) -> dict[str, Any]:
    """
    Match invoice lines to receipts in unified_files.

    Enhanced matching strategy:
    1. Exact match: date + amount (±0.01)
    2. Fuzzy match: date + amount tolerance (±5%) + merchant similarity
    3. Update both invoice_lines and unified_files with match results
    """

    if db_cursor is None:
        return {"error": "db_unavailable"}

    matched_count = 0
    total_lines = 0

    try:
        with db_cursor() as cur:
            # Get all unmatched lines for this invoice
            cur.execute(
                """SELECT id, transaction_date, amount, merchant_name, description
                   FROM invoice_lines
                   WHERE invoice_id=%s AND matched_file_id IS NULL""",
                (invoice_id,)
            )
            lines = cur.fetchall()
            total_lines = len(lines)

        for line_id, tx_date, amount, merchant, description in lines:
            file_id = None
            match_score = 0.0

            try:
                with db_cursor() as cur:
                    # Strategy 1: Exact date and amount match
                    cur.execute(
                        """SELECT id, merchant_name, gross_amount
                           FROM unified_files
                           WHERE file_type IN ('receipt', 'pdf_page')
                           AND DATE(purchase_datetime) = %s
                           AND ABS(gross_amount - %s) < 0.01
                           AND matched_invoice_id IS NULL
                           ORDER BY created_at DESC
                           LIMIT 1""",
                        (tx_date, amount)
                    )
                    row = cur.fetchone()

                    if row:
                        file_id, receipt_merchant, receipt_amount = row
                        match_score = 0.95
                    else:
                        # Strategy 2: Fuzzy match with tolerance
                        tolerance = abs(amount * 0.05)  # 5% tolerance
                        cur.execute(
                            """SELECT id, merchant_name, gross_amount
                               FROM unified_files
                               WHERE file_type IN ('receipt', 'pdf_page')
                               AND DATE(purchase_datetime) = %s
                               AND ABS(gross_amount - %s) <= %s
                               AND matched_invoice_id IS NULL
                               ORDER BY ABS(gross_amount - %s), created_at DESC
                               LIMIT 3""",
                            (tx_date, amount, tolerance, amount)
                        )
                        candidates = cur.fetchall()

                        # Check merchant name similarity
                        if candidates and merchant:
                            best_match = None
                            best_similarity = 0.0

                            for cand_id, cand_merchant, cand_amount in candidates:
                                similarity = _merchant_similarity(merchant, cand_merchant or "")
                                if similarity > best_similarity:
                                    best_similarity = similarity
                                    best_match = (cand_id, cand_merchant, cand_amount)

                            if best_match and best_similarity > 0.6:
                                file_id = best_match[0]
                                match_score = 0.7 + (best_similarity * 0.2)

                    if file_id:
                        # Update invoice_lines
                        cur.execute(
                            """UPDATE invoice_lines
                               SET matched_file_id=%s, match_score=%s, match_status='auto'
                               WHERE id=%s""",
                            (file_id, match_score, line_id)
                        )

                        # Update unified_files
                        cur.execute(
                            """UPDATE unified_files
                               SET invoice_match_status='matched', matched_invoice_id=%s
                               WHERE id=%s""",
                            (invoice_id, file_id)
                        )

                        # Log history
                        cur.execute(
                            """INSERT INTO invoice_line_history
                               (invoice_line_id, action, performed_by,
                                old_matched_file_id, new_matched_file_id, reason)
                               VALUES (%s, 'matched', 'system', NULL, %s, 'auto-match')""",
                            (line_id, file_id)
                        )

                        matched_count += 1
                        record_invoice_decision("matched")

            except Exception as e:
                logger.warning(f"Failed to match line {line_id}: {e}")
                continue

        # Update invoice document status
        if matched_count > 0:
            with db_cursor() as cur:
                status = 'completed' if matched_count == total_lines else 'partially_matched'
                cur.execute(
                    """UPDATE invoice_documents
                       SET status=%s, processing_status='matching_completed'
                       WHERE id=%s""",
                    (status, invoice_id)
                )

        _history(invoice_id, "invoice_matching", "success",
                log_text=f"Matched {matched_count}/{total_lines} lines")

        return {
            "invoice_id": invoice_id,
            "total_lines": total_lines,
            "matched": matched_count,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Invoice matching failed for {invoice_id}: {e}")
        _history(invoice_id, "invoice_matching", "error", error_message=str(e))
        return {"error": str(e), "invoice_id": invoice_id}

def _merchant_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between merchant names.

    Simple approach: normalized Levenshtein distance.
    For production, consider using libraries like fuzzywuzzy or rapidfuzz.
    """
    from difflib import SequenceMatcher

    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    return SequenceMatcher(None, n1, n2).ratio()
```

### 4.6 OCR Completion Hook

**File:** `backend/src/services/tasks.py` (enhance existing task)

```python
@celery_app.task
@track_task("process_ocr")
def process_ocr(file_id: str) -> dict[str, Any]:
    """
    Enhanced OCR task that triggers invoice AI extraction when all pages are done.
    """

    # ... existing OCR logic ...

    # After OCR completes successfully
    _update_file_status(file_id, status="ocr_done")
    _history(file_id, job="ocr", status="success")

    # Check if this is an invoice page
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """SELECT file_type, original_file_id, other_data
                       FROM unified_files WHERE id=%s""",
                    (file_id,)
                )
                row = cur.fetchone()

                if row:
                    file_type, original_id, other_data_json = row

                    if file_type == 'invoice_page':
                        # Check if all pages are OCR complete
                        cur.execute(
                            """SELECT COUNT(*) FROM unified_files
                               WHERE original_file_id=%s
                               AND file_type='invoice_page'
                               AND ai_status != 'ocr_done'""",
                            (original_id,)
                        )
                        pending_count = cur.fetchone()[0]

                        if pending_count == 0:
                            # All pages done, trigger AI extraction
                            logger.info(f"All pages OCR complete for {original_id}, triggering AI extraction")
                            process_invoice_ai_extraction.delay(original_id)

                    elif file_type == 'invoice':
                        # Single-page invoice
                        logger.info(f"Invoice OCR complete for {file_id}, triggering AI extraction")
                        process_invoice_ai_extraction.delay(file_id)

        except Exception as e:
            logger.warning(f"Failed to check invoice OCR status: {e}")

    return {"file_id": file_id, "status": "success"}
```

---

## 5. Frontend Implementation

### 5.1 Enhanced CompanyCard Page

**File:** `main-system/app-frontend/src/ui/pages/CompanyCard.jsx` (enhance)

```jsx
import React from 'react'
import { FiRefreshCw, FiCheckCircle, FiAlertTriangle, FiFileText, FiUpload, FiEye } from 'react-icons/fi'
import { api } from '../api'

export default function CompanyCard() {
  const [items, setItems] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const [matchingId, setMatchingId] = React.useState(null)
  const [feedback, setFeedback] = React.useState(null)
  const [uploadOpen, setUploadOpen] = React.useState(false)

  // ... existing load and onMatch functions ...

  return (
    <div className="space-y-6">
      {/* Statistics cards - existing */}

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Företagskort</h3>
            <p className="card-subtitle">Hantera kontoutdrag och matcha dem mot kvitton.</p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setUploadOpen(true)}
            >
              <FiUpload className="mr-2" />
              Ladda upp faktura
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={load}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="loading-spinner mr-2"></div>
                  Uppdaterar...
                </>
              ) : (
                <>
                  <FiRefreshCw className="mr-2" />
                  Uppdatera
                </>
              )}
            </button>
          </div>
        </div>

        {/* Table - existing */}
      </div>

      {/* Upload Modal */}
      <InvoiceUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploadComplete={() => {
          setUploadOpen(false)
          load()
        }}
      />
    </div>
  )
}
```

### 5.2 Invoice Upload Modal

**File:** `main-system/app-frontend/src/ui/components/InvoiceUploadModal.jsx` (new file)

```jsx
import React from 'react'
import { FiUpload, FiX, FiFileText, FiCheckCircle, FiAlertCircle } from 'react-icons/fi'
import { api } from '../api'

export default function InvoiceUploadModal({ open, onClose, onUploadComplete }) {
  const [uploading, setUploading] = React.useState(false)
  const [selectedFile, setSelectedFile] = React.useState(null)
  const [error, setError] = React.useState(null)
  const [success, setSuccess] = React.useState(null)
  const [uploadProgress, setUploadProgress] = React.useState(null)
  const fileInputRef = React.useRef(null)

  React.useEffect(() => {
    if (open) {
      setSelectedFile(null)
      setError(null)
      setSuccess(null)
      setUploadProgress(null)
    }
  }, [open])

  if (!open) return null

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0]
    if (file) {
      // Validate file type
      const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
      if (!validTypes.includes(file.type)) {
        setError('Endast PDF, JPG och PNG filer tillåts')
        return
      }

      // Validate file size (max 50MB)
      if (file.size > 50 * 1024 * 1024) {
        setError('Filen är för stor (max 50MB)')
        return
      }

      setSelectedFile(file)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Välj en fil att ladda upp')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await api.fetch('/ai/api/reconciliation/firstcard/upload-invoice', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || `Upload failed (${response.status})`)
      }

      const result = await response.json()

      setSuccess(`Faktura uppladdad! ${result.pages} sidor bearbetas nu.`)
      setUploadProgress({
        file_id: result.file_id,
        pages: result.pages,
        status: 'processing'
      })

      // Start polling for status
      pollUploadStatus(result.file_id)

    } catch (err) {
      setError(err.message || 'Uppladdning misslyckades')
      setUploading(false)
    }
  }

  const pollUploadStatus = async (invoiceId) => {
    let attempts = 0
    const maxAttempts = 60 // 5 minutes max

    const poll = async () => {
      try {
        const response = await api.fetch(
          `/ai/api/reconciliation/firstcard/invoices/${invoiceId}/status`
        )

        if (!response.ok) {
          throw new Error('Status check failed')
        }

        const status = await response.json()

        setUploadProgress({
          file_id: invoiceId,
          ...status
        })

        // Check if processing is complete
        if (status.processing_status === 'matching_completed' ||
            status.processing_status === 'completed') {
          setUploading(false)
          setSuccess(`Färdig! ${status.lines_matched}/${status.lines_extracted} transaktioner matchade.`)

          setTimeout(() => {
            if (typeof onUploadComplete === 'function') {
              onUploadComplete()
            }
          }, 2000)
          return
        }

        // Check if error occurred
        if (status.processing_status === 'error' || status.processing_status === 'failed') {
          setError('Bearbetning misslyckades')
          setUploading(false)
          return
        }

        // Continue polling if still processing
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000) // Poll every 5 seconds
        } else {
          setError('Timeout - kontrollera statusen manuellt')
          setUploading(false)
        }
      } catch (err) {
        console.error('Status poll error:', err)
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000)
        } else {
          setUploading(false)
        }
      }
    }

    // Start polling after 3 seconds
    setTimeout(poll, 3000)
  }

  const getProgressMessage = () => {
    if (!uploadProgress) return null

    const { processing_status, ocr_progress, lines_extracted, lines_matched } = uploadProgress

    switch (processing_status) {
      case 'uploaded':
        return 'Förbereder bearbetning...'
      case 'ocr_pending':
        return `OCR pågår (${ocr_progress?.completed || 0}/${ocr_progress?.total || 0} sidor)...`
      case 'ocr_done':
        return 'OCR klar, extraherar transaktioner...'
      case 'ai_processing':
        return 'AI analyserar fakturan...'
      case 'ai_completed':
        return `${lines_extracted} transaktioner hittade, matchar mot kvitton...`
      case 'ready_for_matching':
        return 'Startar automatisk matchning...'
      case 'matching_completed':
        return `Matchning klar! ${lines_matched}/${lines_extracted} transaktioner matchade`
      default:
        return 'Bearbetar...'
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Ladda upp kreditkortsfaktura</h2>
          <button type="button" className="modal-close" onClick={onClose}>
            <FiX />
          </button>
        </div>

        <div className="modal-body space-y-4">
          <p className="text-sm text-gray-300">
            Ladda upp en PDF eller bild av din kreditkortsfaktura. Systemet kommer automatiskt:
          </p>
          <ul className="text-sm text-gray-300 space-y-1 ml-4">
            <li>• Konvertera PDF till bilder (om PDF)</li>
            <li>• Läsa texten med OCR</li>
            <li>• Extrahera transaktioner med AI</li>
            <li>• Matcha transaktioner mot befintliga kvitton</li>
          </ul>

          <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileSelect}
              className="hidden"
            />

            {selectedFile ? (
              <div className="space-y-3">
                <FiFileText className="mx-auto text-4xl text-green-500" />
                <div className="font-medium text-gray-200">{selectedFile.name}</div>
                <div className="text-sm text-gray-400">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </div>
                <button
                  type="button"
                  className="btn btn-text"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  Välj annan fil
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <FiUpload className="mx-auto text-4xl text-gray-400" />
                <div className="text-gray-300">Klicka för att välja fil</div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Välj fil
                </button>
              </div>
            )}
          </div>

          {uploadProgress && (
            <div className="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className="loading-spinner"></div>
                <div className="text-sm text-blue-200">{getProgressMessage()}</div>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4 flex items-start gap-3">
              <FiAlertCircle className="text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-red-200">{error}</div>
            </div>
          )}

          {success && !uploading && (
            <div className="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-4 flex items-start gap-3">
              <FiCheckCircle className="text-green-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-green-200">{success}</div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-text" onClick={onClose} disabled={uploading}>
            {uploading ? 'Stäng efter' : 'Avbryt'}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            {uploading ? (
              <>
                <div className="loading-spinner mr-2"></div>
                Bearbetar...
              </>
            ) : (
              <>
                <FiUpload className="mr-2" />
                Ladda upp
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
```

### 5.3 Invoice Lines Viewer (Optional Enhancement)

**File:** `main-system/app-frontend/src/ui/components/InvoiceLinesModal.jsx` (new file)

```jsx
import React from 'react'
import { FiX, FiCheckCircle, FiAlertCircle, FiDollarSign, FiCalendar } from 'react-icons/fi'
import { api } from '../api'

export default function InvoiceLinesModal({ open, invoiceId, onClose }) {
  const [lines, setLines] = React.useState([])
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    if (open && invoiceId) {
      loadLines()
    }
  }, [open, invoiceId])

  const loadLines = async () => {
    setLoading(true)
    try {
      const response = await api.fetch(
        `/ai/api/reconciliation/firstcard/invoices/${invoiceId}/lines`
      )
      if (response.ok) {
        const data = await response.json()
        setLines(data.lines || [])
      }
    } catch (err) {
      console.error('Failed to load invoice lines:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content max-w-4xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Fakturarader</h2>
          <button type="button" className="modal-close" onClick={onClose}>
            <FiX />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="loading-spinner"></div>
            </div>
          ) : lines.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              Inga transaktioner hittade
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800 text-left">
                  <tr>
                    <th className="px-4 py-2">Datum</th>
                    <th className="px-4 py-2">Företag</th>
                    <th className="px-4 py-2">Belopp</th>
                    <th className="px-4 py-2">Matchning</th>
                    <th className="px-4 py-2">Kvitto</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line) => (
                    <tr key={line.id} className="border-t border-gray-700">
                      <td className="px-4 py-3 text-gray-300">
                        {line.transaction_date}
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-200">
                        {line.merchant_name}
                      </td>
                      <td className="px-4 py-3 text-gray-300">
                        {line.amount?.toFixed(2)} kr
                      </td>
                      <td className="px-4 py-3">
                        {line.matched_file_id ? (
                          <div className="flex items-center gap-2 text-green-400">
                            <FiCheckCircle />
                            <span>{(line.match_score * 100).toFixed(0)}%</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-yellow-400">
                            <FiAlertCircle />
                            <span>Ej matchad</span>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {line.matched_receipt ? (
                          <div className="text-sm text-gray-400">
                            {line.matched_receipt.merchant_name}
                          </div>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

**File:** `backend/tests/unit/test_invoice_extraction.py` (new)

```python
import pytest
from services.invoice_ai import extract_invoice_transactions, _fallback_regex_extraction

def test_regex_extraction_iso_format():
    ocr_text = """
    Period: 2025-09-01 to 2025-09-30

    2025-09-05 Coffee Shop AB 150.50
    2025-09-12 Airport Taxi 320.00
    2025-09-20 Hotel Stockholm -500.00
    """

    result = _fallback_regex_extraction(ocr_text)

    assert result['period_start'] == '2025-09-01'
    assert result['period_end'] == '2025-09-30'
    assert len(result['transactions']) == 3
    assert result['transactions'][0]['merchant'] == 'Coffee Shop AB'
    assert result['transactions'][0]['amount'] == 150.50
    assert result['transactions'][2]['amount'] == -500.00  # Refund

def test_regex_extraction_european_format():
    ocr_text = """
    15/09/2025 Restaurant XYZ 450,50
    20/09/2025 Fuel Station 750,00
    """

    result = _fallback_regex_extraction(ocr_text)

    assert len(result['transactions']) == 2
    assert result['transactions'][0]['date'] == '2025-09-15'
    assert result['transactions'][0]['amount'] == 450.50

def test_merchant_similarity():
    from services.tasks import _merchant_similarity

    assert _merchant_similarity("Coffee Shop AB", "Coffee Shop") > 0.8
    assert _merchant_similarity("ICA Supermarket", "ICA") > 0.6
    assert _merchant_similarity("Completely Different", "Other Name") < 0.3
```

### 6.2 Integration Tests

**File:** `backend/tests/integration/test_invoice_upload_flow.py` (new)

```python
import pytest
from flask import Flask
from io import BytesIO
from services.db.connection import db_cursor

@pytest.fixture
def app() -> Flask:
    from api.app import app as flask_app
    return flask_app

def test_upload_single_page_invoice(app: Flask):
    """Test uploading a single-page image invoice."""
    client = app.test_client()

    # Create fake image data
    image_data = b'\x89PNG\r\n\x1a\n...'  # Minimal PNG header

    data = {
        'file': (BytesIO(image_data), 'invoice.png', 'image/png')
    }

    response = client.post('/ai/api/reconciliation/firstcard/upload-invoice',
                          data=data,
                          content_type='multipart/form-data')

    assert response.status_code == 200
    result = response.get_json()
    assert 'file_id' in result
    assert result['invoice_type'] == 'credit_card_invoice'
    assert result['pages'] == 1

def test_upload_pdf_invoice(app: Flask):
    """Test uploading a multi-page PDF invoice."""
    client = app.test_client()

    # Create minimal PDF
    pdf_data = b'%PDF-1.4...'  # Would need proper PDF bytes

    data = {
        'file': (BytesIO(pdf_data), 'invoice.pdf', 'application/pdf')
    }

    response = client.post('/ai/api/reconciliation/firstcard/upload-invoice',
                          data=data,
                          content_type='multipart/form-data')

    assert response.status_code == 200
    result = response.get_json()
    assert result['invoice_type'] == 'credit_card_invoice'
    # Would assert pages > 1 if PDF had multiple pages

def test_invoice_matching_exact_match(app: Flask):
    """Test that exact date+amount matches work."""
    # Setup: Create a receipt in unified_files
    receipt_id = 'test-receipt-001'
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO unified_files
               (id, file_type, purchase_datetime, gross_amount, merchant_name)
               VALUES (%s, 'receipt', '2025-09-15 14:30:00', 150.50, 'Coffee Shop')""",
            (receipt_id,)
        )

    # Setup: Create invoice with matching transaction
    invoice_id = 'test-invoice-001'
    with db_cursor() as cur:
        cur.execute(
            """INSERT INTO invoice_documents (id, invoice_type)
               VALUES (%s, 'credit_card_invoice')""",
            (invoice_id,)
        )
        cur.execute(
            """INSERT INTO invoice_lines
               (invoice_id, transaction_date, amount, merchant_name)
               VALUES (%s, '2025-09-15', 150.50, 'Coffee Shop AB')""",
            (invoice_id,)
        )

    # Test: Run matching
    from services.tasks import process_invoice_matching
    result = process_invoice_matching(invoice_id)

    assert result['matched'] == 1

    # Verify: Check that line was matched
    with db_cursor() as cur:
        cur.execute(
            """SELECT matched_file_id, match_score FROM invoice_lines
               WHERE invoice_id=%s""",
            (invoice_id,)
        )
        row = cur.fetchone()
        assert row[0] == receipt_id
        assert row[1] > 0.9  # High confidence

    # Cleanup
    with db_cursor() as cur:
        cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
        cur.execute("DELETE FROM invoice_documents WHERE id=%s", (invoice_id,))
        cur.execute("DELETE FROM unified_files WHERE id=%s", (receipt_id,))
```

### 6.3 E2E Tests

**File:** `main-system/app-frontend/tests/e2e-invoice-upload.spec.ts` (new)

```typescript
import { test, expect } from '@playwright/test'

test('Upload credit card invoice and verify processing', async ({ page }) => {
  // Login
  await page.goto('http://localhost:8008/')
  await page.fill('input[name="username"]', 'admin')
  await page.fill('input[name="password"]', 'admin')
  await page.click('button[type="submit"]')

  // Navigate to Company Card page
  await page.click('text=Kortmatchning')
  await expect(page).toHaveURL(/.*company-card/)

  // Click upload button
  await page.click('button:has-text("Ladda upp faktura")')

  // Upload file
  const fileInput = await page.locator('input[type="file"]')
  await fileInput.setInputFiles('tests/fixtures/sample-invoice.pdf')

  // Click upload
  await page.click('button:has-text("Ladda upp")')

  // Wait for processing message
  await expect(page.locator('text=OCR pågår')).toBeVisible({ timeout: 10000 })

  // Wait for completion (may take time)
  await expect(page.locator('text=Matchning klar')).toBeVisible({ timeout: 60000 })

  // Close modal
  await page.click('button:has-text("Stäng")')

  // Verify invoice appears in list
  await expect(page.locator('table tbody tr').first()).toBeVisible()
})

test('View invoice lines after upload', async ({ page }) => {
  // Assumes invoice already uploaded
  await page.goto('http://localhost:8008/company-card')

  // Click first invoice in table
  await page.click('table tbody tr:first-child')

  // Should open lines modal (if implemented)
  await expect(page.locator('h2:has-text("Fakturarader")')).toBeVisible()

  // Verify transaction lines are visible
  const lineCount = await page.locator('table tbody tr').count()
  expect(lineCount).toBeGreaterThan(0)
})
```

---

## 7. Deployment & Migration

### 7.1 Pre-Deployment Checklist

- [ ] Run database migration `0016_invoice_matching_enhancements.sql`
- [ ] Verify AI_PROCESSING_ENABLED=true in environment
- [ ] Verify OPENAI_API_KEY is set (if using AI extraction)
- [ ] Test PDF conversion with PyMuPDF installed
- [ ] Verify storage directory has write permissions
- [ ] Run unit tests: `pytest backend/tests/unit/test_invoice_extraction.py`
- [ ] Run integration tests: `pytest backend/tests/integration/test_invoice_upload_flow.py`

### 7.2 Deployment Steps

```bash
# 1. Stop services
docker compose down

# 2. Pull latest code
git pull origin main

# 3. Run database migration
docker compose up -d mind-mysql
docker exec -i mind-mysql mysql -uroot -pmind2025 mono_se_db_9 < database/migrations/0016_invoice_matching_enhancements.sql

# 4. Rebuild backend with new dependencies
docker compose build ai-api celery-worker

# 5. Restart services
docker compose up -d --profile main

# 6. Verify services are healthy
docker compose ps
curl http://localhost:8008/ai/api/health
```

### 7.3 Monitoring

**Key metrics to monitor:**
- Invoice upload rate (`POST /reconciliation/firstcard/upload-invoice`)
- OCR task completion time (track in `ai_processing_history`)
- AI extraction success rate (log confidence scores)
- Auto-match rate (percentage of lines matched)
- Processing queue depth (Celery queue size)

**Grafana dashboard panels:**
- Invoice processing pipeline (uploaded → OCR → AI → matched)
- Match accuracy distribution (match_score histogram)
- Failed extractions (error rate by invoice_type)

---

## 8. Future Enhancements

### 8.1 Phase 2 Features

1. **Manual Matching UI**
   - Drag-and-drop interface to manually match transactions
   - Side-by-side view of invoice line and receipt candidates
   - Bulk actions (match all, unmatch all)

2. **Smart Suggestions**
   - ML-based merchant name normalization
   - Historical matching patterns to improve accuracy
   - Confidence threshold tuning per user/company

3. **Multi-Invoice Support**
   - Batch upload multiple invoices
   - Consolidated matching report
   - Export matched/unmatched summary

4. **Receipt Search from Invoice**
   - Click invoice line → search receipts with filters pre-filled
   - Filter by date range, amount tolerance
   - Quick-match button in search results

### 8.2 Performance Optimizations

1. **Parallel OCR Processing**
   - Process all pages in parallel instead of sequentially
   - Use Celery groups/chords for coordination

2. **Caching Layer**
   - Cache invoice extraction results
   - Cache merchant similarity scores
   - Redis-based match candidate cache

3. **Database Indexes**
   - Composite index on (purchase_datetime, gross_amount) for faster matching
   - Full-text index on merchant_name for fuzzy search

---

## 9. Risk Analysis & Mitigation

### 9.1 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| OCR fails on poor quality images | High | Medium | Add image preprocessing (deskew, denoise), fallback to manual entry |
| AI extraction misses transactions | High | Medium | Use regex fallback, allow manual line addition |
| False positive matches | Medium | High | Require manual confirmation for matches <80% confidence |
| Large PDF causes timeout | Medium | Low | Implement streaming upload, chunk processing |
| Duplicate invoice detection fails | Low | Low | Hash-based duplicate check already implemented |

### 9.2 Rollback Plan

If critical issues occur:
1. Disable invoice upload button in frontend (feature flag)
2. Stop processing new invoices via Celery worker shutdown
3. Rollback database migration if schema issues
4. Restore previous version via Git tag

---

## 10. Success Criteria

### 10.1 Acceptance Criteria

**Must Have:**
- [ ] User can upload PDF invoice via "Kortmatchning" page
- [ ] Multi-page PDFs are converted to images successfully
- [ ] OCR extracts text from all pages
- [ ] AI identifies at least 80% of transaction lines correctly
- [ ] Auto-matching achieves >70% accuracy for exact date+amount matches
- [ ] User can view matched/unmatched lines in UI
- [ ] Processing history is logged for debugging

**Should Have:**
- [ ] Fuzzy matching with merchant name similarity
- [ ] Upload progress indicator shows OCR/AI status
- [ ] Error handling with clear user messages
- [ ] E2E test coverage for happy path

**Nice to Have:**
- [ ] Batch upload multiple invoices
- [ ] Export matching report to Excel
- [ ] Manual match/unmatch UI

### 10.2 Performance Targets

- **Upload response time:** < 2 seconds for file validation
- **OCR processing:** < 10 seconds per page
- **AI extraction:** < 30 seconds for full invoice
- **Auto-matching:** < 5 seconds for 100 lines
- **End-to-end:** < 2 minutes for 5-page invoice

---

## 11. Appendix

### 11.1 File Structure Summary

```
backend/
├── src/
│   ├── api/
│   │   └── reconciliation_firstcard.py (enhanced)
│   └── services/
│       ├── invoice_ai.py (new)
│       ├── tasks.py (enhanced)
│       └── pdf_conversion.py (existing)
├── tests/
│   ├── unit/
│   │   └── test_invoice_extraction.py (new)
│   └── integration/
│       └── test_invoice_upload_flow.py (new)

main-system/app-frontend/
├── src/
│   ├── ui/
│   │   ├── pages/
│   │   │   └── CompanyCard.jsx (enhanced)
│   │   └── components/
│   │       ├── InvoiceUploadModal.jsx (new)
│   │       └── InvoiceLinesModal.jsx (new)
├── tests/
│   └── e2e-invoice-upload.spec.ts (new)

database/
└── migrations/
    └── 0016_invoice_matching_enhancements.sql (new)

docs/SYSTEM_DOCS/
└── MIND_INVOICE_MATCH_IMPLEMENTATION_PLAN.md (this file)
```

### 11.2 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/api/reconciliation/firstcard/upload-invoice` | Upload PDF/image invoice |
| GET | `/ai/api/reconciliation/firstcard/invoices/{id}/status` | Get processing status |
| GET | `/ai/api/reconciliation/firstcard/invoices/{id}/lines` | Get extracted lines with matches |
| POST | `/ai/api/reconciliation/firstcard/match` | Trigger manual re-matching |
| GET | `/ai/api/reconciliation/firstcard/statements` | List all invoices (existing) |

### 11.3 Database Schema Summary

**New/Enhanced Tables:**
```sql
unified_files
  + invoice_match_status VARCHAR(32)
  + matched_invoice_id VARCHAR(36)

invoice_documents
  + source_file_id VARCHAR(36)
  + processing_status VARCHAR(32)

invoice_lines
  + extraction_confidence FLOAT
  + ocr_source_text TEXT
```

### 11.4 Celery Task Chain

```
User uploads PDF
    ↓
process_ocr (per page)
    ↓
[All pages complete]
    ↓
process_invoice_ai_extraction
    ↓
process_invoice_matching
    ↓
Done
```

---

## 12. Implementation Review Summary

The 2025-10-04 review identified functional and technical adjustments required before development can begin:

1. **Complete new API endpoints.** The stubs for `upload_invoice`, `get_invoice_status`, and `get_invoice_lines` still contain `pass`. Build out these endpoints, reusing shared upload helpers rather than duplicating logic.
2. **Align status propagation.** Define how `invoice_documents.processing_status`, `invoice_lines.match_status`, and related counters advance during OCR, AI extraction, and matching so that the planned progress UI can poll accurate data.
3. **Prevent accidental receipt processing.** Update `process_ocr` (and downstream tasks) to branch invoice files into the new Celery chain instead of the legacy receipt pipeline.
4. **Unify matching flows.** Merge the improved matching strategy into the existing `/reconciliation/firstcard/match` route and broaden `list_statements` so invoices with `invoice_type='credit_card_invoice'` appear in the frontend.
5. **Resolve migration numbering.** Rename the proposed migration to the next free sequence number to avoid clashing with `0016_add_content_hash_to_files.sql`.
6. **Respect test governance.** Relocate new E2E tests under `web/tests`, follow `docs/TEST_RULES.md`, and archive reports per `web/TEST_AGENT_INSTRUCTIONS.md`.
7. **Optimize PDF handling.** Avoid double-writing page images by reusing files produced by `pdf_to_png_pages` and ensure large, multi-page PDFs use efficient Celery coordination (groups/chords) for OCR.

These items must be addressed before the plan can be executed safely.

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-04 | Claude Code Agent | Initial comprehensive plan |

---

**END OF IMPLEMENTATION PLAN**
