# Database Schema Audit Report
**Date**: 2025-09-30
**Source**: mono_se_db_9 (3).sql
**Target**: MySQL Database in mind2-mysql-1 container

## Executive Summary

This report documents ALL differences between the SQL dump file and the current database schema. The audit covered **19 tables in the database** and **21 tables in the SQL file**.

---

## 1. MISSING TABLES

These tables exist in the SQL file but are **completely missing** from the database:

### 1.1 file_categories
**Status**: MISSING - Table does not exist in database
**Expected Columns**:
- id (int, NOT NULL, AUTO_INCREMENT, PRIMARY KEY)
- name (varchar(222), NOT NULL)
- description (varchar(222), NOT NULL)
- created_at (datetime, NOT NULL, DEFAULT CURRENT_TIMESTAMP)

### 1.2 tags
**Status**: MISSING - Table does not exist in database
**Expected Columns**:
- id (int, NOT NULL, AUTO_INCREMENT, PRIMARY KEY)
- name (varchar(255), NOT NULL)
- description (varchar(500), NULL)
- tag_category (int, NOT NULL)
- created_at (timestamp, NOT NULL, DEFAULT CURRENT_TIMESTAMP)

### 1.3 tag_categories
**Status**: MISSING - Table does not exist in database
**Expected Columns**:
- id (int, NOT NULL, AUTO_INCREMENT, PRIMARY KEY)
- tag_category_name (varchar(50), NOT NULL)
- tag_category_description (varchar(255), NULL)
- created_at (timestamp, NOT NULL, DEFAULT CURRENT_TIMESTAMP)

---

## 2. TABLES WITH MISSING COLUMNS

### 2.1 ai_accounting_proposals
**Status**: Exists but missing columns

| Column | Status | Type | Details |
|--------|--------|------|---------|
| id | ✓ OK | bigint | |
| receipt_id | ✓ OK | varchar(36) | |
| **item_id** | **MISSING** | **int NOT NULL** | **Should be between receipt_id and account_code** |
| account_code | ✓ OK | varchar(32) | |
| debit | ✓ OK | decimal(12,2) | |
| credit | ✓ OK | decimal(12,2) | |
| vat_rate | ✓ OK | decimal(6,2) | |
| notes | ✓ OK | varchar(255) | |
| created_at | ✓ OK | timestamp | |

**Impact**: HIGH - Missing foreign key reference to item

---

### 2.2 companies
**Status**: Exists but missing columns and has NULL constraint differences

**Missing Columns**:
| Column | Status | Type | Details |
|--------|--------|------|---------|
| **created_at** | **MISSING** | **timestamp NOT NULL** | **Should be after www** |
| **updated_at** | **MISSING** | **timestamp NULL** | **Should be after created_at** |

**NULL Constraint Differences**:
| Column | SQL File | Current DB | Issue |
|--------|----------|------------|-------|
| address | NOT NULL (int type!) | NULL (varchar) | SQL file has WRONG TYPE (int instead of varchar) |
| address2 | NOT NULL | NULL | Less restrictive in DB |
| zip | NOT NULL | NULL | Less restrictive in DB |
| city | NOT NULL | NULL | Less restrictive in DB |
| country | NOT NULL | NULL | Less restrictive in DB |
| phone | NOT NULL | NULL | Less restrictive in DB |
| www | NOT NULL | NULL | Less restrictive in DB |

**Impact**: MEDIUM - Missing audit columns, but NULL constraints are actually more practical in DB

**Note**: The SQL file has a data type error for `address` (shows as INT instead of VARCHAR). Current DB schema is correct.

---

### 2.3 unified_files
**Status**: Exists but MANY missing columns

This is the most problematic table with **12+ missing columns**:

| Column | Status | Type | Details |
|--------|--------|------|---------|
| id | ✓ OK | varchar(36) | |
| file_type | ✓ OK | varchar(32) | |
| created_at | ✓ OK | timestamp | |
| updated_at | ✓ OK | timestamp | |
| **merchant_name** | ✓ OK | varchar(255) | Already exists in DB |
| orgnr | ✓ OK | varchar(32) | |
| **payment_type** | **MISSING** | **varchar(255) NOT NULL** | cash or card |
| purchase_datetime | ✓ OK | datetime | |
| **expense_type** | **MISSING** | **varchar(255) NOT NULL** | personal or corporate |
| **gross_amount_original** | **MISSING** | **decimal(12,2) NULL** | amount inc VAT |
| **net_amount_original** | **MISSING** | **decimal(12,2) NULL** | amount ex VAT |
| **exchange_rate** | **MISSING** | **decimal(12,0) NOT NULL** | exchange rate |
| **currency** | **MISSING** | **varchar(222) NOT NULL** | DEFAULT 'SEK' |
| **gross_amount_sek** | **MISSING** | **decimal(10,0) NOT NULL** | gross in SEK |
| **net_amount_sek** | **MISSING** | **decimal(10,0) NOT NULL** | net in SEK |
| gross_amount | ✓ OK | decimal(12,2) | |
| net_amount | ✓ OK | decimal(12,2) | |
| ai_status | ✓ OK | varchar(32) | |
| ai_confidence | ✓ OK | float | |
| submitted_by | ✓ OK | varchar(64) | |
| original_filename | ✓ OK | varchar(255) | |
| original_file_id | ✓ OK | varchar(36) | |
| original_file_name | ✓ OK | varchar(222) | |
| file_creation_timestamp | ✓ OK | timestamp | |
| original_file_size | ✓ OK | int | |
| mime_type | ✓ OK | varchar(222) | |
| **ocr_raw** | **MISSING** | **text NOT NULL** | Raw OCR text |
| file_suffix | ✓ OK | varchar(32) | |
| file_category | ✓ OK | int | |
| **company_id** | **MISSING** | **int NOT NULL** | FK to companies.id |
| **receipt_number** | **MISSING** | **varchar(255) NOT NULL** | unique receipt number |
| **approved_by** | **MISSING** | **int NOT NULL** | user id that approved |
| **other_data** | **MISSING** | **text NOT NULL** | other receipt data |
| **credit_card_match** | **MISSING** | **tinyint(1) NOT NULL** | DEFAULT 0, matching flag |

**Impact**: CRITICAL - This table is missing core receipt processing columns

---

## 3. EXTRA COLUMNS IN DATABASE (Schema Evolution)

### 3.1 ai_processing_history
**Status**: Database has EXTRA columns not in SQL file (evolution features)

**Extra Columns in DB**:
- ai_stage_name (varchar(64), NULL)
- log_text (text, NULL)
- error_message (text, NULL)
- confidence (float, NULL)
- processing_time_ms (int, NULL)
- provider (varchar(64), NULL)
- model_name (varchar(128), NULL)

**SQL File Columns**:
- id, file_id, job_type, status, created_at

**Impact**: NONE - These are evolution features and should be kept

---

## 4. EXTRA TABLES IN DATABASE

### 4.1 creditcard_receipt_matches
**Status**: Exists in database but NOT in SQL file

**Current Schema**:
- id (bigint, NOT NULL, AUTO_INCREMENT, PRIMARY KEY)
- receipt_id (varchar(36), NOT NULL)
- invoice_item_id (bigint unsigned, NOT NULL)
- matched_amount (decimal(13,2), NULL)
- matched_at (timestamp, NOT NULL, DEFAULT CURRENT_TIMESTAMP)

**Impact**: NONE - This is evolution and should be kept

---

## 5. DATA TYPE DIFFERENCES (Not Changed)

These differences exist but are NOT changed in the migration to avoid data corruption:

| Table | Column | SQL File | Current DB | Reason Not Changed |
|-------|--------|----------|------------|-------------------|
| ai_llm | id | bigint UNSIGNED | int | Risk of breaking auto_increment |
| ai_llm_model | id | bigint UNSIGNED | int | Risk of breaking auto_increment |
| ai_system_prompts | id | bigint UNSIGNED | int | Risk of breaking auto_increment |
| receipt_items | main_id | int | varchar(36) | Schema evolved to use UUIDs |
| receipt_items | article_id | NOT NULL | NULL | More flexible in current schema |

---

## 6. TABLES IDENTICAL BETWEEN SQL FILE AND DATABASE

These tables match perfectly:

1. ✓ ai_processing_queue
2. ✓ chart_of_accounts
3. ✓ creditcard_invoice_items
4. ✓ creditcard_invoices_main
5. ✓ file_locations
6. ✓ file_suffix
7. ✓ file_tags
8. ✓ invoice_documents
9. ✓ invoice_line_history
10. ✓ invoice_lines

---

## 7. SUMMARY OF ISSUES

### Critical Issues (Require Immediate Action)
1. **unified_files** - Missing 12+ essential columns for receipt processing
2. **Missing tables** - file_categories, tags, tag_categories

### High Priority Issues
3. **ai_accounting_proposals** - Missing item_id foreign key column

### Medium Priority Issues
4. **companies** - Missing created_at and updated_at audit columns

### Low Priority (Documentation Only)
5. Data type differences in ID columns (kept as-is for safety)
6. NULL constraint differences (current DB is more practical)

---

## 8. MIGRATION SCRIPT

The migration script `0015_restore_all_missing_columns.sql` has been created to:

1. ✓ Create missing tables (file_categories, tags, tag_categories)
2. ✓ Add missing column to ai_accounting_proposals (item_id)
3. ✓ Add missing columns to companies (created_at, updated_at)
4. ✓ Add all 12+ missing columns to unified_files
5. ✓ Use IF NOT EXISTS and ADD COLUMN IF NOT EXISTS for idempotent execution

**NOT included in migration** (intentionally):
- ID type changes (risk of data corruption)
- NULL constraint changes on companies (current schema is better)
- receipt_items schema changes (evolved schema is better)
- Removal of evolution features in ai_processing_history

---

## 9. POST-MIGRATION VERIFICATION

After running the migration, verify with:

```sql
-- Check new tables exist
SELECT COUNT(*) FROM file_categories;
SELECT COUNT(*) FROM tags;
SELECT COUNT(*) FROM tag_categories;

-- Check unified_files has all columns
DESCRIBE unified_files;
SHOW COLUMNS FROM unified_files LIKE '%payment_type%';
SHOW COLUMNS FROM unified_files LIKE '%expense_type%';
SHOW COLUMNS FROM unified_files LIKE '%ocr_raw%';

-- Check ai_accounting_proposals has item_id
DESCRIBE ai_accounting_proposals;

-- Check companies has timestamps
DESCRIBE companies;
```

---

## 10. RECOMMENDATIONS

1. **Run the migration script** - Execute `0015_restore_all_missing_columns.sql` immediately
2. **Update application code** - Ensure all new columns in unified_files are populated
3. **Data migration needed** - Some columns have NOT NULL constraints but no data
4. **Consider default values** - May need to update default values for existing rows
5. **Test thoroughly** - Run full test suite after migration
6. **Backup first** - Create backup before running migration

---

## 11. COLUMN COUNT COMPARISON

| Table | SQL File Columns | DB Columns | Difference |
|-------|-----------------|------------|------------|
| ai_accounting_proposals | 9 | 8 | -1 |
| ai_llm | 7 | 8 | +1 |
| ai_llm_model | 6 | 6 | 0 |
| ai_processing_history | 5 | 12 | +7 |
| ai_processing_queue | 4 | 4 | 0 |
| ai_system_prompts | 8 | 8 | 0 |
| chart_of_accounts | 7 | 7 | 0 |
| companies | 12 | 10 | -2 |
| creditcard_invoice_items | 21 | 21 | 0 |
| creditcard_invoices_main | 42 | 42 | 0 |
| file_categories | 4 | N/A | Table missing |
| file_locations | 6 | 6 | 0 |
| file_suffix | 4 | 4 | 0 |
| file_tags | 3 | 3 | 0 |
| invoice_documents | 7 | 7 | 0 |
| invoice_line_history | 7 | 7 | 0 |
| invoice_lines | 9 | 9 | 0 |
| receipt_items | 11 | 11 | 0 |
| tags | 5 | N/A | Table missing |
| tag_categories | 4 | N/A | Table missing |
| unified_files | 32 | 20 | -12 |
| creditcard_receipt_matches | N/A | 5 | Table added |

---

**End of Audit Report**
