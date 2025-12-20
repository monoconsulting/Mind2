# docs/source_of_truth/40_DATA_MODEL.md

# Mind – Data Model (Source of Truth)

> This file describes the canonical database schema used by Mind at **table + column level**.
>
> Version: 2025-12-14.2
> Schema snapshot source: `mind_db_dump.sql` (generated from MySQL) + `database/migrations/` (for change history)

## 1. Scope and Rules

- This document describes the **current target schema** (what the database must look like after all migrations are applied).
- If a table/column/index exists in the database or migrations, it **must** be documented here in the same pull request.
- This file avoids placeholders. If something is unknown, it is treated as a **defect** and must be resolved by reading schema/migrations.

## 2. Table Inventory (Canonical)

Mind currently uses **28** tables + **2** views (see detailed definitions below):

- `companies`
- `unified_files`
- `receipt_items`
- `invoice_documents`
- `invoice_lines`
- `invoice_line_history`
- `creditcard_invoices_main`
- `creditcard_invoice_items`
- `creditcard_receipt_matches`
- `ai_processing_history`
- `ai_processing_queue`
- `ai_accounting_proposals`
- `ai_system_prompts`
- `ai_llm`
- `ai_llm_model`
- `schema_migrations`
- `chart_of_accounts`
- `tags`
- `tag_categories`
- `file_tags`
- `file_categories`
- `file_locations`
- `file_suffix`
- plus backup/helper tables used for FC cleanup (`*_fc_backup`) and workflow tracking (`workflow_runs`, `workflow_stage_runs`).
- views used for workflow UI summaries (`v_workflow_overview`, `v_workflow_stages`).

## 3. Table Definitions

> Formatting:
> - **Nullable** is YES/NO from the schema.
> - **Default** is the literal default expression/value.

### `ai_accounting_proposals`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `receipt_id` | `varchar(36)` | NO |  |  |
| `item_id` | `int` | YES | `NULL` |  |
| `account_code` | `varchar(32)` | NO |  |  |
| `debit` | `decimal(12,2)` | NO | `'0.00'` |  |
| `credit` | `decimal(12,2)` | NO | `'0.00'` |  |
| `vat_rate` | `decimal(6,2)` | YES | `NULL` |  |
| `notes` | `varchar(255)` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_ai_accounting_proposals_receipt` (`receipt_id`)`

### `ai_accounting_proposals_fc_backup`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO | `'0'` |  |
| `receipt_id` | `varchar(36)` | NO |  |  |
| `item_id` | `int` | YES | `NULL` |  |
| `account_code` | `varchar(32)` | NO |  |  |
| `debit` | `decimal(12,2)` | NO | `'0.00'` |  |
| `credit` | `decimal(12,2)` | NO | `'0.00'` |  |
| `vat_rate` | `decimal(6,2)` | YES | `NULL` |  |
| `notes` | `varchar(255)` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

### `ai_llm`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `provider_name` | `varchar(100)` | NO |  |  |
| `own_name` | `varchar(255)` | YES | `NULL` |  |
| `api_key` | `text` | YES |  |  |
| `endpoint_url` | `text` | YES |  |  |
| `enabled` | `tinyint(1)` | YES | `'0'` |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_ai_llm_enabled` (`enabled`)`

### `ai_llm_model`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `llm_id` | `int` | NO |  |  |
| `model_name` | `varchar(255)` | NO |  |  |
| `display_name` | `varchar(255)` | YES | `NULL` |  |
| `is_active` | `tinyint(1)` | YES | `'1'` |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `unique_llm_model` (`llm_id`,`model_name`)`
- `KEY `idx_ai_llm_model_llm_id` (`llm_id`)`
- `KEY `idx_ai_llm_model_active` (`is_active`)`
- `CONSTRAINT `ai_llm_model_ibfk_1` FOREIGN KEY (`llm_id`) REFERENCES `ai_llm` (`id`) ON DELETE CASCADE`

### `ai_processing_history`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `file_id` | `varchar(36)` | NO |  |  |
| `job_type` | `varchar(64)` | NO |  |  |
| `status` | `varchar(32)` | NO |  |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |
| `ai_stage_name` | `varchar(64)` | YES | `NULL` | Human-readable AI stage name (AI1-DocumentClassification, AI2-ExpenseClassification, etc.) |
| `log_text` | `text` | YES |  | Short human-readable summary of the step (never includes prompt or response payloads) |
| `error_message` | `text` | YES |  | Error message if the stage failed |
| `confidence` | `float` | YES | `NULL` | Confidence score for this AI stage result |
| `processing_time_ms` | `int` | YES | `NULL` | Processing time in milliseconds |
| `provider` | `varchar(64)` | YES | `NULL` | AI provider used (rule-based, openai, azure, etc.) |
| `model_name` | `varchar(128)` | YES | `NULL` | Model name used for this stage |
| `prompt_text` | `longtext` | YES | `NULL` | Full prompt text used for this AI call (snapshot) |
| `response_text` | `longtext` | YES | `NULL` | Full raw AI response text returned by the provider (snapshot) |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_file_stage` (`file_id`,`ai_stage_name`)`
- `KEY `idx_status` (`status`)`

### `ai_processing_history_fc_backup`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO | `'0'` |  |
| `file_id` | `varchar(36)` | NO |  |  |
| `job_type` | `varchar(64)` | NO |  |  |
| `status` | `varchar(32)` | NO |  |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |
| `ai_stage_name` | `varchar(64)` | YES | `NULL` | Human-readable AI stage name (AI1-DocumentClassification, AI2-ExpenseClassification, etc.) |
| `log_text` | `text` | YES |  | Detailed log message explaining what happened in this stage |
| `error_message` | `text` | YES |  | Error message if the stage failed |
| `confidence` | `float` | YES | `NULL` | Confidence score for this AI stage result |
| `processing_time_ms` | `int` | YES | `NULL` | Processing time in milliseconds |
| `provider` | `varchar(64)` | YES | `NULL` | AI provider used (rule-based, openai, azure, etc.) |
| `model_name` | `varchar(128)` | YES | `NULL` | Model name used for this stage |

### `ai_processing_queue`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `file_id` | `varchar(36)` | NO |  |  |
| `job_type` | `varchar(64)` | NO |  |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`

### `ai_system_prompts`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `prompt_key` | `varchar(100)` | NO |  |  |
| `title` | `varchar(255)` | NO |  |  |
| `description` | `text` | YES |  |  |
| `prompt_content` | `mediumtext` | YES |  |  |
| `selected_model_id` | `int` | YES | `NULL` |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `prompt_key` (`prompt_key`)`
- `KEY `selected_model_id` (`selected_model_id`)`
- `CONSTRAINT `ai_system_prompts_ibfk_1` FOREIGN KEY (`selected_model_id`) REFERENCES `ai_llm_model` (`id`) ON DELETE SET NULL`

### `chart_of_accounts`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `main_account` | `varchar(10)` | YES | `NULL` |  |
| `main_account_description` | `varchar(255)` | YES | `NULL` |  |
| `no_k2` | `tinyint(1)` | YES | `NULL` |  |
| `simple_account` | `varchar(10)` | YES | `NULL` |  |
| `sub_account` | `varchar(10)` | YES | `NULL` |  |
| `sub_account_description` | `varchar(255)` | YES | `NULL` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_main_account` (`main_account`)`
- `KEY `idx_sub_account` (`sub_account`)`

### `companies`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `name` | `varchar(234)` | NO |  |  |
| `orgnr` | `varchar(22)` | YES | `NULL` |  |
| `address` | `varchar(222)` | YES | `NULL` |  |
| `address2` | `varchar(222)` | YES | `NULL` |  |
| `zip` | `varchar(123)` | YES | `NULL` |  |
| `city` | `varchar(234)` | YES | `NULL` |  |
| `country` | `varchar(234)` | YES | `NULL` |  |
| `phone` | `varchar(234)` | YES | `NULL` |  |
| `www` | `varchar(234)` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `timestamp` | YES | `NULL` |  |
| `email` | `varchar(234)` | YES | `NULL` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `ux_companies_orgnr` (`orgnr`)`

### `creditcard_invoice_items`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `main_id` | `bigint` | NO |  |  |
| `line_no` | `int` | NO |  |  |
| `transaction_id` | `varchar(64)` | YES | `NULL` |  |
| `purchase_date` | `date` | YES | `NULL` |  |
| `posting_date` | `date` | YES | `NULL` |  |
| `merchant_name` | `varchar(200)` | YES | `NULL` |  |
| `merchant_city` | `varchar(100)` | YES | `NULL` |  |
| `merchant_country` | `char(2)` | YES | `NULL` |  |
| `mcc` | `varchar(4)` | YES | `NULL` |  |
| `description` | `text` | YES |  |  |
| `currency_original` | `char(3)` | YES | `NULL` |  |
| `amount_original` | `decimal(13,2)` | YES | `NULL` |  |
| `exchange_rate` | `decimal(18,6)` | YES | `NULL` |  |
| `amount_sek` | `decimal(13,2)` | YES | `NULL` |  |
| `vat_rate` | `decimal(5,2)` | YES | `NULL` |  |
| `vat_amount` | `decimal(13,2)` | YES | `NULL` |  |
| `net_amount` | `decimal(13,2)` | YES | `NULL` |  |
| `gross_amount` | `decimal(13,2)` | YES | `NULL` |  |
| `cost_center_override` | `varchar(100)` | YES | `NULL` |  |
| `project_code` | `varchar(100)` | YES | `NULL` |  |
| `matched` | `tinyint(1)` | NO | `'0'` |  |
| `updated_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `ux_creditcard_invoice_line` (`main_id`,`line_no`)`
- `KEY `ix_creditcard_invoice_purchase_date` (`purchase_date`)`
- `KEY `ix_creditcard_invoice_merchant` (`merchant_name`)`
- `CONSTRAINT `fk_creditcard_items_main` FOREIGN KEY (`main_id`) REFERENCES `creditcard_invoices_main` (`id`) ON DELETE CASCADE ON UPDATE CASCADE`

### `creditcard_invoices_main`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `invoice_number` | `varchar(50)` | NO |  |  |
| `ocr_raw` | `longtext` | YES |  | Merged OCR text from all invoice pages |
| `invoice_print_time` | `datetime` | YES | `NULL` |  |
| `card_type` | `varchar(50)` | YES | `NULL` |  |
| `card_name` | `varchar(100)` | YES | `NULL` |  |
| `card_number_masked` | `varchar(32)` | YES | `NULL` |  |
| `card_holder` | `varchar(100)` | YES | `NULL` |  |
| `cost_center` | `varchar(100)` | YES | `NULL` |  |
| `customer_name` | `varchar(150)` | YES | `NULL` |  |
| `co` | `varchar(150)` | YES | `NULL` |  |
| `address` | `text` | YES |  |  |
| `bank_name` | `varchar(100)` | YES | `NULL` |  |
| `bank_org_no` | `varchar(50)` | YES | `NULL` |  |
| `bank_vat_no` | `varchar(50)` | YES | `NULL` |  |
| `bank_fi_no` | `varchar(50)` | YES | `NULL` |  |
| `invoice_date` | `date` | YES | `NULL` |  |
| `customer_number` | `varchar(50)` | YES | `NULL` |  |
| `invoice_number_long` | `varchar(100)` | YES | `NULL` |  |
| `due_date` | `date` | YES | `NULL` |  |
| `invoice_total` | `decimal(13,2)` | YES | `NULL` |  |
| `payment_plusgiro` | `varchar(30)` | YES | `NULL` |  |
| `payment_bankgiro` | `varchar(30)` | YES | `NULL` |  |
| `payment_iban` | `varchar(34)` | YES | `NULL` |  |
| `payment_bic` | `varchar(11)` | YES | `NULL` |  |
| `payment_ocr` | `varchar(50)` | YES | `NULL` |  |
| `payment_due` | `date` | YES | `NULL` |  |
| `card_total` | `decimal(13,2)` | YES | `NULL` |  |
| `sum` | `decimal(13,2)` | YES | `NULL` |  |
| `vat_25` | `decimal(13,2)` | YES | `NULL` |  |
| `vat_12` | `decimal(13,2)` | YES | `NULL` |  |
| `vat_6` | `decimal(13,2)` | YES | `NULL` |  |
| `vat_0` | `decimal(13,2)` | YES | `NULL` |  |
| `amount_to_pay` | `decimal(13,2)` | YES | `NULL` |  |
| `reported_vat` | `decimal(13,2)` | YES | `NULL` |  |
| `next_invoice` | `date` | YES | `NULL` |  |
| `note_1` | `text` | YES |  |  |
| `note_2` | `text` | YES |  |  |
| `note_3` | `text` | YES |  |  |
| `note_4` | `text` | YES |  |  |
| `note_5` | `text` | YES |  |  |
| `currency` | `varchar(3)` | YES | `NULL` | Currency code (SEK, EUR, USD, etc.) |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `ux_creditcard_invoices_number` (`invoice_number`)`
- `KEY `ix_creditcard_invoices_date` (`invoice_date`)`
- `KEY `ix_creditcard_invoices_number_long` (`invoice_number_long`)`
- `KEY `idx_creditcard_invoices_number` (`invoice_number`)`
- `KEY `idx_currency` (`currency`)`

### `creditcard_receipt_matches`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `receipt_id` | `varchar(36)` | NO |  |  |
| `invoice_item_id` | `bigint` | NO |  |  |
| `matched_amount` | `decimal(13,2)` | YES | `NULL` |  |
| `matched_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `ux_receipt_invoice_item` (`receipt_id`,`invoice_item_id`)`
- `KEY `fk_receipt_matches_item` (`invoice_item_id`)`
- `CONSTRAINT `fk_receipt_matches_item` FOREIGN KEY (`invoice_item_id`) REFERENCES `creditcard_invoice_items` (`id`) ON DELETE CASCADE`

### `file_categories`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `name` | `varchar(222)` | NO |  |  |
| `description` | `varchar(222)` | NO |  |  |
| `created_at` | `datetime` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`

### `file_locations`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `file_id` | `varchar(36)` | NO |  |  |
| `lat` | `double` | YES | `NULL` |  |
| `lon` | `double` | YES | `NULL` |  |
| `acc` | `double` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_file_locations_file` (`file_id`)`

### `file_suffix`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `file_ending` | `varchar(255)` | NO |  |  |
| `file_type` | `int` | NO |  |  |
| `created_at` | `datetime` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`

### `file_tags`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `file_id` | `varchar(36)` | NO |  |  |
| `tag` | `varchar(64)` | NO |  |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`file_id`,`tag`)`

### `invoice_documents`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `varchar(36)` | NO |  |  |
| `invoice_type` | `varchar(32)` | NO |  |  |
| `source_file_id` | `varchar(36)` | YES | `NULL` | Reference to unified_files.id for uploaded PDF/image |
| `period_start` | `date` | YES | `NULL` |  |
| `period_end` | `date` | YES | `NULL` |  |
| `uploaded_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |
| `status` | `varchar(32)` | NO | `'imported'` |  |
| `processing_status` | `varchar(32)` | YES | `NULL` | Current processing stage of the invoice |
| `metadata_json` | `json` | YES | `NULL` |  |
| `deleted_at` | `timestamp` | YES | `NULL` | Timestamp when the invoice was soft deleted |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_invoice_documents_deleted_at` (`deleted_at`)`
- `KEY `idx_invoice_docs_processing` (`processing_status`)`
- `KEY `idx_invoice_docs_source` (`source_file_id`)`

### `invoice_line_history`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `invoice_line_id` | `bigint` | NO |  |  |
| `action` | `varchar(16)` | NO |  |  |
| `performed_by` | `varchar(64)` | YES | `NULL` |  |
| `old_matched_file_id` | `varchar(36)` | YES | `NULL` |  |
| `new_matched_file_id` | `varchar(36)` | YES | `NULL` |  |
| `reason` | `varchar(1024)` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `fk_line_history_line` (`invoice_line_id`)`
- `CONSTRAINT `fk_line_history_line` FOREIGN KEY (`invoice_line_id`) REFERENCES `invoice_lines` (`id`)`

### `invoice_lines`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `invoice_id` | `varchar(36)` | NO |  |  |
| `transaction_date` | `date` | YES | `NULL` |  |
| `amount` | `decimal(12,2)` | YES | `NULL` |  |
| `merchant_name` | `varchar(255)` | YES | `NULL` |  |
| `description` | `varchar(1024)` | YES | `NULL` |  |
| `extraction_confidence` | `float` | YES | `NULL` |  |
| `ocr_source_text` | `text` | YES |  |  |
| `matched_file_id` | `varchar(36)` | YES | `NULL` |  |
| `match_score` | `float` | YES | `NULL` |  |
| `match_status` | `varchar(16)` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `fk_invoice_lines_doc` (`invoice_id`)`
- `CONSTRAINT `fk_invoice_lines_doc` FOREIGN KEY (`invoice_id`) REFERENCES `invoice_documents` (`id`)`

### `receipt_items`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `main_id` | `varchar(36)` | NO |  | References unified_files.id |
| `article_id` | `varchar(222)` | YES | `NULL` |  |
| `name` | `varchar(222)` | NO |  |  |
| `number` | `int` | NO |  |  |
| `item_price_ex_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `item_price_inc_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `item_total_price_ex_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `item_total_price_inc_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `currency` | `varchar(11)` | NO | `'SEK'` |  |
| `vat` | `decimal(10,2)` | YES | `NULL` |  |
| `vat_percentage` | `decimal(7,6)` | YES | `NULL` |  |
| `item_vat_total` | `decimal(10,2)` | YES | `NULL` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_receipt_items_main` (`main_id`)`

### `receipt_items_fc_backup`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO | `'0'` |  |
| `main_id` | `varchar(36)` | NO |  | References unified_files.id |
| `article_id` | `varchar(222)` | YES | `NULL` |  |
| `name` | `varchar(222)` | NO |  |  |
| `number` | `int` | NO |  |  |
| `item_price_ex_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `item_price_inc_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `item_total_price_ex_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `item_total_price_inc_vat` | `decimal(10,2)` | YES | `NULL` |  |
| `currency` | `varchar(11)` | NO | `'SEK'` |  |
| `vat` | `decimal(10,2)` | YES | `NULL` |  |
| `vat_percentage` | `decimal(7,6)` | YES | `NULL` |  |

### `tag_categories`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `tag_category_name` | `varchar(50)` | NO |  |  |
| `tag_category_description` | `varchar(255)` | YES | `NULL` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`

### `tags`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `int` | NO |  |  |
| `name` | `varchar(255)` | NO |  |  |
| `description` | `varchar(500)` | YES | `NULL` |  |
| `tag_category` | `int` | NO |  |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`

### `unified_files`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `varchar(36)` | NO |  |  |
| `company_id` | `int` | YES | `NULL` |  |
| `vat` | `varchar(32)` | YES | `NULL` | VAT/Organization number |
| `file_type` | `varchar(32)` | YES | `NULL` |  |
| `ocr_raw` | `text` | YES |  |  |
| `created_at` | `timestamp` | YES | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `timestamp` | YES | `NULL` |  |
| `purchase_datetime` | `datetime` | YES | `NULL` |  |
| `receipt_number` | `varchar(255)` | YES | `NULL` | the unique receipt number - could be named "Ordernummer", "Kvittonummer" |
| `payment_type` | `varchar(255)` | YES | `NULL` | Payment type: card, cash, swish, or other |
| `expense_type` | `varchar(255)` | YES | `NULL` | If this is bought using a private card or cash (personal) or if it is corporate card (corporate) |
| `credit_card_number` | `varchar(44)` | YES | `NULL` |  |
| `credit_card_last_4_digits` | `int` | YES | `NULL` |  |
| `credit_card_type` | `varchar(44)` | YES | `NULL` |  |
| `credit_card_brand_full` | `varchar(22)` | YES | `NULL` |  |
| `credit_card_brand_short` | `varchar(22)` | YES | `NULL` |  |
| `credit_card_payment_variant` | `varchar(222)` | YES | `NULL` |  |
| `credit_card_token` | `varchar(222)` | YES | `NULL` |  |
| `credit_card_entering_mode` | `varchar(222)` | YES | `NULL` |  |
| `gross_amount_original` | `decimal(12,2)` | YES | `NULL` | amount inc vat |
| `net_amount_original` | `decimal(12,2)` | YES | `NULL` | amount ex vat |
| `total_vat_25` | `decimal(12,2)` | YES | `NULL` | total vat amount 25% |
| `total_vat_12` | `decimal(12,2)` | YES | `NULL` |  |
| `total_vat_6` | `decimal(12,2)` | YES | `NULL` |  |
| `exchange_rate` | `decimal(12,6)` | YES | `NULL` | Exchange rate to SEK (SEK invariant: `1.000000` for SEK; NULL means unknown/unused) |
| `currency` | `varchar(222)` | YES | `'SEK'` | currency that was bought in |
| `gross_amount_sek` | `decimal(12,2)` | YES | `NULL` | SEK mirror amount (for SEK mirrors original; for foreign only when deterministically known) |
| `net_amount_sek` | `decimal(12,2)` | YES | `NULL` | SEK mirror amount (for SEK mirrors original; for foreign only when deterministically known) |
| `gross_amount` | `decimal(12,2)` | YES | `NULL` | Legacy mirror (SEK) for backward compatibility (do not use for foreign-currency display) |
| `net_amount` | `decimal(12,2)` | YES | `NULL` | Legacy mirror (SEK) for backward compatibility (do not use for foreign-currency display) |
| `ai_status` | `varchar(32)` | YES | `NULL` |  |
| `ai_confidence` | `float` | YES | `NULL` |  |
| `submitted_by` | `varchar(64)` | YES | `NULL` |  |
| `original_filename` | `varchar(255)` | NO |  |  |
| `original_file_id` | `varchar(36)` | YES | `NULL` | Original file ID from FTP source |
| `original_file_name` | `varchar(222)` | YES | `NULL` | Original filename from FTP source |
| `file_creation_timestamp` | `timestamp` | YES | `NULL` | File creation timestamp from FTP metadata |
| `original_file_size` | `int` | YES | `NULL` | Original file size in bytes |
| `mime_type` | `varchar(222)` | YES | `NULL` | MIME type of the original file |
| `file_suffix` | `varchar(32)` | NO |  |  |
| `file_category` | `int` | YES | `NULL` | Reference to file_categories.id |
| `approved_by` | `int` | YES | `'0'` | user id that approved the receipt |
| `other_data` | `text` | YES |  |  |
| `credit_card_match` | `tinyint(1)` | YES | `'0'` | When matching receipt is available set 1 |
| `invoice_match_status` | `varchar(32)` | YES | `NULL` | Status for invoice matching: pending, matched, unmatched, reviewed |
| `matched_invoice_id` | `varchar(36)` | YES | `NULL` | Reference to invoice_documents.id if matched to invoice line |
| `matched` | `tinyint(1)` | NO | `'0'` |  |
| `content_hash` | `varchar(64)` | YES | `NULL` |  |
| `deleted_at` | `timestamp` | YES | `NULL` | Timestamp when the record was soft deleted. NULL means not deleted. |
| `workflow_type` | `varchar(32)` | YES | `'receipt'` | Determines which processing pipeline: receipt or creditcard_invoice |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_content_hash` (`content_hash`)`
- `KEY `idx_unified_files_creation_timestamp` (`file_creation_timestamp`)`
- `KEY `idx_unified_files_original_file_id` (`original_file_id`)`
- `KEY `idx_deleted_at` (`deleted_at`)`
- `KEY `idx_workflow_type` (`workflow_type`)`
- `KEY `idx_unified_files_company` (`company_id`)`
- `KEY `idx_unified_files_receipt_number` (`receipt_number`)`
- `KEY `idx_unified_invoice_match` (`invoice_match_status`)`
- `KEY `idx_unified_files_matched_invoice` (`matched_invoice_id`)`

### `schema_migrations`

Migration ledger used to ensure each SQL file in `database/migrations/` is applied only once per database.

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `filename` | `varchar(255)` | NO |  | Primary key: migration filename. Reserved marker value: `__baseline__` (baseline completed). |
| `checksum` | `char(64)` | YES | `NULL` | SHA-256 checksum of the migration file bytes (hex). |
| `applied_at` | `datetime` | NO |  | Timestamp when the migration was marked applied. |

### `workflow_runs`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `workflow_key` | `varchar(40)` | NO |  | e.g., WF1_RECEIPT, WF2_PDF_SPLIT |
| `source_channel` | `varchar(40)` | YES | `NULL` | upload_portal, ftp, api, ... |
| `file_id` | `varchar(36)` | YES | `NULL` | FK to unified_files.id (root file) |
| `content_hash` | `varchar(64)` | YES | `NULL` |  |
| `current_stage` | `varchar(40)` | NO | `'queued'` |  |
| `status` | `enum('queued','running','succeeded','failed','canceled')` | NO | `'queued'` |  |
| `created_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `timestamp` | NO | `CURRENT_TIMESTAMP` |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_wfr_workflow` (`workflow_key`)`
- `KEY `idx_wfr_file` (`file_id`)`
- `KEY `idx_wfr_hash` (`content_hash`)`

### `workflow_stage_runs`

| Column | Type | Nullable | Default | Comment |
|---|---|---|---|---|
| `id` | `bigint` | NO |  |  |
| `workflow_run_id` | `bigint` | NO |  |  |
| `stage_key` | `varchar(40)` | NO |  | e.g., dispatch, ocr, merge_ocr |
| `status` | `enum('queued','running','succeeded','failed','skipped')` | NO | `'queued'` |  |
| `started_at` | `timestamp` | YES | `NULL` |  |
| `finished_at` | `timestamp` | YES | `NULL` |  |
| `message` | `text` | YES |  |  |

**Indexes / Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_wfs_workflow_run` (`workflow_run_id`)`
- `CONSTRAINT `fk_wfs_wfr` FOREIGN KEY (`workflow_run_id`) REFERENCES `workflow_runs` (`id`) ON DELETE CASCADE`

## 4. Key Relationships (High-Level)

- `unified_files.company_id` → `companies.id` (logical link; schema uses indexes and/or FK depending on migration state)
- Receipts:
  - `receipt_items.receipt_id` → `unified_files.id` (receipt header is stored in `unified_files`, items in `receipt_items`)
- FirstCard:
  - `creditcard_invoices_main.unified_file_id` → `unified_files.id`
  - `creditcard_invoice_items.main_id` → `creditcard_invoices_main.id`
  - `creditcard_receipt_matches.invoice_item_id` → `creditcard_invoice_items.id`
  - `creditcard_receipt_matches.receipt_id` → `unified_files.id`
- Workflow tracking:
  - `workflow_stage_runs.workflow_run_id` → `workflow_runs.id`

## 5. Critical Fields for Receipt Preview / Matching

The following `unified_files` fields are treated as **authoritative** for receipt preview and downstream matching:

- Amounts: `gross_amount_original`, `net_amount_original`, `total_vat_25`, `total_vat_12`, `total_vat_6`, `currency`, `exchange_rate`, `gross_amount_sek`, `net_amount_sek`
- Receipt metadata: `purchase_datetime`, `receipt_number`, `payment_type`, `expense_type`
- Card metadata (must not be dropped from extraction):  
  `credit_card_number`, `credit_card_last_4_digits`, `credit_card_type`, `credit_card_brand_full`, `credit_card_brand_short`,  
  `credit_card_payment_variant`, `credit_card_token`, `credit_card_entering_mode`

## 6. Prompt Storage Table (Authoritative)

Prompts are stored in `ai_system_prompts`. The **prompt_key** is stable and must not be changed without a full migration plan.

See `70_AI_PROMPTS_AND_ROLES.md` for prompt keys and behavioral contracts.
