# Data Model — Mind system feature

Entities and key fields per MIND v2.0 canonical migration order:

## Migration 1: Base Schema (unified-migration-fixed.sql)

### unified_files
**Purpose**: Core file metadata for all document types (receipts, invoices, etc.)
- id (UUID, PK), file_type ('receipt'|'invoice'|'other')
- created_at, updated_at, file_hash
- original_filename, file_size_bytes
- metadata_json (JSON column for flexible fields)
- ai_status ('pending'|'processing'|'completed'|'failed')
- ai_confidence (float 0..1)
- ai_extracted_data (JSON column for OCR results)

### file_tags  
**Purpose**: Tag associations for categorization
- id (auto-increment, PK), file_id (FK to unified_files)
- tag (varchar), created_at
- INDEX(file_id), INDEX(tag)

## Migration 2: AI Processing Schema (ai_schema_extension.sql)

### ai_processing_queue
**Purpose**: Celery task queue for AI processing
- id (UUID, PK), file_id (FK to unified_files)  
- task_type ('ocr'|'classification'|'validation')
- status ('pending'|'running'|'completed'|'failed')
- created_at, started_at, completed_at
- error_message, retry_count

### ai_processing_history
**Purpose**: Audit trail of AI processing steps
- id (UUID, PK), file_id (FK to unified_files)
- processing_step, status, confidence_score
- processing_time_ms, model_version
- created_at, details_json

### ai_models
**Purpose**: AI model configuration and versioning
- id (auto-increment, PK), model_name, model_version
- model_type ('ocr'|'classification'|'validation')
- config_json, is_active, created_at

## Migration 3: Invoice Schema (2025_09_18_invoice_schema.sql)

### invoice_documents
**Purpose**: Company card/invoice statements for matching
- id (UUID, PK), invoice_type ('company_card'|'supplier')
- period_start, period_end, uploaded_at
- status ('imported'|'matched'|'completed')
- metadata_json

### invoice_lines  
**Purpose**: Individual line items from company card statements
- id (UUID, PK), invoice_id (FK to invoice_documents)
- transaction_date, amount, merchant_name, description
- matched_file_id (FK to unified_files, nullable)
- match_score (float 0..1), match_status ('auto'|'manual'|'rejected')

### invoice_line_history
**Purpose**: Audit trail for matching decisions
- id (UUID, PK), invoice_line_id (FK to invoice_lines)
- action ('matched'|'unmatched'|'rejected'), performed_by
- old_matched_file_id, new_matched_file_id
- reason, created_at

## Derived Views/Virtual Entities

These map to the unified schema for backward compatibility:

### Receipt (VIEW or application layer)
Maps to: `unified_files WHERE file_type='receipt'`
- Extracted fields from ai_extracted_data JSON:
  - merchant_name, orgnr, purchase_datetime
  - gross_amount, net_amount, vat_breakdown
  - line_items, validation_status

### CompanyCardInvoice (alias)
Maps to: `invoice_documents WHERE invoice_type='company_card'`

### CompanyCardLine (alias)  
Maps to: `invoice_lines` with invoice_documents join

## Key Principles (MIND v2.0)

- **Unified storage**: All files in `unified_files` regardless of type
- **JSON flexibility**: Extensible metadata without schema changes  
- **Canonical order**: unified → ai → invoice migrations
- **Idempotent DDL**: `IF NOT EXISTS` for safe re-runs
- **Foreign key integrity**: Proper cascading and constraints
- **Audit trails**: History tables for critical operations
