# docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md

# Mind – AI Prompts and Roles (Source of Truth)

> This file defines the AI roles used in Mind (AI1–AI6), their responsibilities, and the prompts they use. If AI behavior in code differs from what is written here, this file must be updated.
>
> Version: 2025-12-04
> Source: `backend/src/services/ai_service.py`, `backend/src/services/tasks/ai_pipeline_tasks.py`, `MIND_STATUS_DEFINITIONS.md`

## 1. Overview

Mind uses a chain of AI steps to process documents. Each step has a specific role:

| AI Role | Stage Key | Responsibility | Workflow |
|---------|-----------|----------------|----------|
| AI1 | `detect_type` | Document Type Classification | WF1 |
| AI2 | (inactive) | Expense Classification | WF1 |
| AI3 | `r_ai3` | Data Extraction | WF1 |
| AI4 | `r_ai4` | Accounting Classification | WF1 |
| AI5 | `ai5` | Credit Card Matching | WF1, WF3 |
| AI6 | `fc_parse` | FirstCard Invoice Parsing | WF3 |

## 2. AI1 – Document Type Classification

### 2.1 Identifier

- **Stage Key:** `detect_type`
- **Task:** `classify_and_route_receipt_v3()`
- **Location:** `backend/src/services/tasks.py` (lines 3832-3904)

### 2.2 Responsibility

Classify incoming documents to determine their type and route them appropriately.

### 2.3 Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ocr_text` | string | Yes | Extracted OCR text |
| `file_type` | string | Yes | MIME type |
| `filename` | string | No | Original filename |

### 2.4 Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `document_type` | enum | `receipt`, `invoice`, `creditcard_statement`, `other` |
| `confidence` | float | 0.0 - 1.0 |
| `route` | string | Next processing step |

### 2.5 Classification Types

| Type | Description | Next Step |
|------|-------------|-----------|
| `receipt` | Standard purchase receipt | AI3 extraction |
| `invoice` | Supplier invoice | Invoice processing |
| `creditcard_statement` | Credit card statement | WF3 |
| `other` | Unclassified | Manual review |

### 2.6 Model / Provider

- **Primary:** OpenAI GPT-4 / GPT-4-turbo
- **Fallback:** Manual review queue

## 3. AI2 – Expense Classification (Inactive)

### 3.1 Status

Currently not active in production pipeline.

### 3.2 Original Responsibility

Classify expenses as personal or corporate.

## 4. AI3 – Data Extraction

### 4.1 Identifier

- **Stage Key:** `r_ai3`
- **Task:** `extract_receipt_data_ai3()`
- **Location:** `backend/src/services/tasks.py` (lines 3979-4110)

### 4.2 Responsibility

Extract structured data from receipt OCR text.

### 4.3 Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ocr_text` | string | Yes | Full OCR text |
| `document_type` | string | Yes | From AI1 |
| `company_context` | object | No | Company info |

### 4.4 Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `merchant_name` | string | Seller/store name |
| `purchase_date` | date | Transaction date |
| `purchase_time` | time | Transaction time |
| `gross_amount` | decimal | Total including VAT |
| `net_amount` | decimal | Total excluding VAT |
| `vat_amount` | decimal | VAT amount |
| `vat_rate` | decimal | VAT percentage |
| `currency` | string | Currency code (SEK, EUR) |
| `items` | array | Line items if available |
| `org_number` | string | Seller's org number |

### 4.5 Item Schema

```json
{
  "name": "string",
  "quantity": "number",
  "unit_price": "decimal",
  "total_price": "decimal",
  "vat_rate": "decimal"
}
```

### 4.6 Model / Provider

- **Primary:** OpenAI GPT-4 / GPT-4-turbo
- **Fallback:** Manual data entry

## 5. AI4 – Accounting Classification

### 5.1 Identifier

- **Stage Key:** `r_ai4`
- **Task:** `normalize_receipt_data_ai4()`
- **Location:** `backend/src/services/tasks.py` (lines 4120-4226)

### 5.2 Responsibility

Generate accounting proposals according to Swedish BAS 2025 chart of accounts.

### 5.3 Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `extracted_data` | object | Yes | From AI3 |
| `company_id` | uuid | Yes | Company context |
| `bas_kontoplan` | object | No | Account mappings |

### 5.4 Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `proposals` | array | Accounting entries |
| `confidence` | float | Overall confidence |

### 5.5 Proposal Schema

```json
{
  "account_code": "4010",
  "account_name": "Kontorsmaterial",
  "debit": 100.00,
  "credit": 0.00,
  "vat_code": "I25",
  "description": "string",
  "confidence": 0.95
}
```

### 5.6 VAT Codes

| Code | Rate | Description |
|------|------|-------------|
| `I25` | 25% | Standard rate |
| `I12` | 12% | Food, hotels |
| `I6` | 6% | Books, culture |
| `I0` | 0% | Exempt |

### 5.7 Model / Provider

- **Primary:** OpenAI GPT-4 / GPT-4-turbo
- **Context:** Swedish BAS 2025 kontoplan

## 6. AI5 – Credit Card Matching

### 6.1 Identifier

- **Stage Key:** `ai5`
- **Task:** Auto-matching logic
- **Location:** `backend/src/services/tasks.py` (lines 3702-3722)

### 6.2 Responsibility

Match receipts to credit card transaction lines.

### 6.3 Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `receipt` | object | Yes | Receipt with extracted data |
| `transaction_lines` | array | Yes | Credit card lines to match |

### 6.4 Output Contract

| Field | Type | Description |
|-------|------|-------------|
| `match_found` | boolean | Whether match was found |
| `matched_line_id` | int | Matched line ID |
| `confidence` | float | Match confidence |
| `match_factors` | object | Scoring breakdown |

### 6.5 Matching Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| `amount` | 40% | Amount similarity |
| `date` | 30% | Date proximity |
| `merchant` | 30% | Merchant name match |

### 6.6 Matching Rules

1. Amount must match within tolerance (default 1%)
2. Date must be within range (default 7 days)
3. Merchant name similarity threshold (default 70%)

## 7. AI6 – FirstCard Invoice Parsing

### 7.1 Identifier

- **Stage Key:** `fc_parse`
- **Task:** `parse_credit_card_invoice_ai6()`
- **Location:** `backend/src/services/tasks.py` (lines 3491-3543)

### 7.2 Responsibility

Parse FirstCard credit card statements to extract header and line items.

### 7.3 Input Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ocr_text` | string | Yes | Full OCR text from statement |
| `page_count` | int | Yes | Number of pages |

### 7.4 Output Contract

**Header:**
| Field | Type | Description |
|-------|------|-------------|
| `card_holder` | string | Card holder name |
| `card_number` | string | Last 4 digits |
| `statement_date` | date | Statement date |
| `due_date` | date | Payment due date |
| `total_amount` | decimal | Total to pay |
| `period_start` | date | Period start |
| `period_end` | date | Period end |

**Lines:**
| Field | Type | Description |
|-------|------|-------------|
| `transaction_date` | date | Transaction date |
| `posting_date` | date | Posting date |
| `merchant_name` | string | Merchant |
| `amount` | decimal | Transaction amount |
| `currency` | string | Currency |
| `original_amount` | decimal | Original currency amount |
| `original_currency` | string | Original currency code |

### 7.5 Tables Updated

- `creditcard_invoices_main` – Header data
- `creditcard_invoices_lines` – Transaction lines
- `invoice_documents` – Document metadata
- `invoice_lines` – For matching

### 7.6 Model / Provider

- **Primary:** OpenAI GPT-4 / GPT-4-turbo
- **Prompt stored in:** `ai_system_prompts` table (key: `credit_card_invoice_parsing`)

## 8. Prompt Storage and Versioning

### 8.1 Storage Location

- Prompts stored in `ai_system_prompts` database table
- Migration: `0020_insert_ai_prompts.sql`, `0030_insert_ai6_credit_card_invoice_prompt.sql`
- Schema update: `0043_expand_prompt_content_to_mediumtext.sql`

### 8.2 Prompt Table Schema

```sql
CREATE TABLE ai_system_prompts (
  id INT PRIMARY KEY AUTO_INCREMENT,
  prompt_key VARCHAR(100) UNIQUE NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  prompt_content MEDIUMTEXT,          -- Supports prompts up to 16 MB
  selected_model_id INT,              -- FK to ai_llm_model
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 8.3 Related Tables

```sql
-- LLM Providers (OpenAI, Anthropic, etc.)
CREATE TABLE ai_llm (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  api_key_env_var VARCHAR(100),
  base_url VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE
);

-- LLM Models (gpt-4, claude-3, etc.)
CREATE TABLE ai_llm_model (
  id INT PRIMARY KEY AUTO_INCREMENT,
  llm_id INT,                         -- FK to ai_llm
  model_name VARCHAR(100) NOT NULL,
  display_name VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE
);
```

### 8.4 Prompt Keys

| Key | AI Role | Description |
|-----|---------|-------------|
| `document_analysis` | AI1 | Document type classification |
| `data_extraction` | AI3 | Data extraction from receipts |
| `expense_classification` | AI2 | Expense categorization |
| `accounting_classification` | AI4 | Accounting proposal generation |
| `credit_card_matching` | AI5 | Credit card transaction matching |
| `credit_card_invoice_parsing` | AI6 | FirstCard statement parsing |

## 9. AI Processing History

All AI calls are logged to `ai_processing_history` table.

### 9.1 Table Schema

```sql
CREATE TABLE ai_processing_history (
  id BIGINT PRIMARY KEY,
  file_id VARCHAR(36),
  ai_stage_name VARCHAR(64),
  request_payload JSON,
  response_payload JSON,
  status VARCHAR(32),
  confidence DECIMAL(5,4),
  error_message TEXT,
  processing_time_ms INT,
  created_at TIMESTAMP
);
```

### 9.2 Logging Function

```python
# backend/src/services/ai_logging.py
log_ai_call(
    file_id=file_id,
    ai_stage_name='AI3',
    request_payload=request,
    response_payload=response,
    status='success',
    confidence=0.95
)
```

## 10. Error Handling and Guardrails

### 10.1 Invalid Response Detection

- JSON schema validation for all AI outputs
- Required field checks
- Type validation

### 10.2 Retry Logic

- Max 3 retries for transient errors
- Exponential backoff
- Different model fallback on persistent failure

### 10.3 Guardrails

- Confidence threshold (default 0.7 for auto-accept)
- Low confidence triggers manual review
- Invalid responses logged and flagged

## 11. Governance

- New AI roles must be added here before implementation
- Prompt changes require version bump
- Deprecated roles should be marked with migration path
- All AI outputs must be logged to `ai_processing_history`
