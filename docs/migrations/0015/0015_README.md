# Database Schema Restoration - Complete Guide

## Overview
This migration restores ALL missing columns and tables identified during the comprehensive database schema audit comparing `mono_se_db_9 (3).sql` with the current database.

## Files in This Migration

1. **0015_restore_all_missing_columns.sql** - The actual migration script
2. **0015_audit_report.md** - Detailed audit report with all findings
3. **0015_README.md** - This file with execution instructions

## What This Migration Does

### Creates Missing Tables
- `file_categories` - File categorization table
- `tags` - Tag definitions table
- `tag_categories` - Tag category definitions table

### Adds Missing Columns to Existing Tables

#### ai_accounting_proposals
- `item_id` (int NOT NULL) - Foreign key reference to item

#### companies
- `created_at` (timestamp NOT NULL) - Record creation timestamp
- `updated_at` (timestamp NULL) - Record update timestamp

#### unified_files (12+ columns)
- `payment_type` - Payment method (cash/card)
- `expense_type` - Expense classification (personal/corporate)
- `gross_amount_original` - Original gross amount
- `net_amount_original` - Original net amount
- `exchange_rate` - Currency exchange rate
- `currency` - Transaction currency
- `gross_amount_sek` - Gross amount in SEK
- `net_amount_sek` - Net amount in SEK
- `ocr_raw` - Raw OCR text data
- `company_id` - Foreign key to companies
- `receipt_number` - Unique receipt identifier
- `approved_by` - User who approved the receipt
- `other_data` - Additional receipt metadata
- `credit_card_match` - Credit card matching flag

## Pre-Migration Checklist

- [ ] **BACKUP YOUR DATABASE FIRST**
  ```bash
  docker exec mind2-mysql-1 mysqldump -u root -proot mono_se_db_9 > backup_before_0015_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] Verify the database is accessible
  ```bash
  docker exec mind2-mysql-1 mysql -u root -proot mono_se_db_9 -e "SELECT DATABASE();"
  ```

- [ ] Stop application services if running
  ```bash
  docker-compose stop backend frontend
  ```

- [ ] Review the audit report (`0015_audit_report.md`)

## Running the Migration

### Option 1: Execute via Docker (Recommended)

```bash
# Copy the SQL file into the container
docker cp "E:\projects\Mind2\database\migrations\0015_restore_all_missing_columns.sql" mind2-mysql-1:/tmp/

# Execute the migration
docker exec mind2-mysql-1 mysql -u root -proot mono_se_db_9 < /tmp/0015_restore_all_missing_columns.sql

# Or execute from outside the container
docker exec -i mind2-mysql-1 mysql -u root -proot mono_se_db_9 < "E:\projects\Mind2\database\migrations\0015_restore_all_missing_columns.sql"
```

### Option 2: Execute via mysql client

```bash
mysql -u root -proot mono_se_db_9 < "E:\projects\Mind2\database\migrations\0015_restore_all_missing_columns.sql"
```

## Post-Migration Verification

### 1. Verify New Tables Exist
```sql
-- Check file_categories table
SELECT COUNT(*) as table_exists FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mono_se_db_9' AND TABLE_NAME = 'file_categories';

-- Check tags table
SELECT COUNT(*) as table_exists FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mono_se_db_9' AND TABLE_NAME = 'tags';

-- Check tag_categories table
SELECT COUNT(*) as table_exists FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mono_se_db_9' AND TABLE_NAME = 'tag_categories';
```

### 2. Verify ai_accounting_proposals
```sql
DESCRIBE ai_accounting_proposals;
-- Should show item_id column

-- Check column exists
SELECT COUNT(*) FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'ai_accounting_proposals'
AND COLUMN_NAME = 'item_id';
-- Should return 1
```

### 3. Verify companies Table
```sql
DESCRIBE companies;
-- Should show created_at and updated_at columns

-- Check columns exist
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'companies'
AND COLUMN_NAME IN ('created_at', 'updated_at');
-- Should return 2 rows
```

### 4. Verify unified_files Table
```sql
-- Get all columns
SELECT COLUMN_NAME FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'unified_files'
ORDER BY ORDINAL_POSITION;

-- Check specific new columns
SELECT COUNT(*) as new_columns_count FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'unified_files'
AND COLUMN_NAME IN (
  'payment_type', 'expense_type', 'gross_amount_original', 'net_amount_original',
  'exchange_rate', 'currency', 'gross_amount_sek', 'net_amount_sek',
  'ocr_raw', 'company_id', 'receipt_number', 'approved_by',
  'other_data', 'credit_card_match'
);
-- Should return 14
```

### 5. Run Complete Verification Script
```bash
docker exec mind2-mysql-1 mysql -u root -proot mono_se_db_9 << 'EOF'
-- Summary Report
SELECT 'VERIFICATION SUMMARY' as '';

-- Count new tables
SELECT 'New Tables Created' as Category, COUNT(*) as Count
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME IN ('file_categories', 'tags', 'tag_categories');

-- Check ai_accounting_proposals
SELECT 'ai_accounting_proposals.item_id' as Category,
       IF(COUNT(*) > 0, 'EXISTS', 'MISSING') as Status
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'ai_accounting_proposals'
AND COLUMN_NAME = 'item_id';

-- Check companies timestamps
SELECT 'companies timestamps' as Category,
       COUNT(*) as Count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'companies'
AND COLUMN_NAME IN ('created_at', 'updated_at');

-- Check unified_files new columns
SELECT 'unified_files new columns' as Category,
       COUNT(*) as Count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mono_se_db_9'
AND TABLE_NAME = 'unified_files'
AND COLUMN_NAME IN (
  'payment_type', 'expense_type', 'gross_amount_original', 'net_amount_original',
  'exchange_rate', 'currency', 'gross_amount_sek', 'net_amount_sek',
  'ocr_raw', 'company_id', 'receipt_number', 'approved_by',
  'other_data', 'credit_card_match'
);

SELECT 'VERIFICATION COMPLETE' as '';
EOF
```

## Expected Results

After successful migration:
- 3 new tables created
- 1 column added to ai_accounting_proposals
- 2 columns added to companies
- 14 columns added to unified_files
- **Total: 3 tables, 17 columns added**

## Rollback Instructions

If you need to rollback the migration:

```sql
-- Drop new tables
DROP TABLE IF EXISTS `file_categories`;
DROP TABLE IF EXISTS `tags`;
DROP TABLE IF EXISTS `tag_categories`;

-- Remove columns from ai_accounting_proposals
ALTER TABLE `ai_accounting_proposals` DROP COLUMN IF EXISTS `item_id`;

-- Remove columns from companies
ALTER TABLE `companies` DROP COLUMN IF EXISTS `created_at`;
ALTER TABLE `companies` DROP COLUMN IF EXISTS `updated_at`;

-- Remove columns from unified_files
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `payment_type`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `expense_type`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `gross_amount_original`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `net_amount_original`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `exchange_rate`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `currency`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `gross_amount_sek`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `net_amount_sek`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `ocr_raw`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `company_id`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `receipt_number`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `approved_by`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `other_data`;
ALTER TABLE `unified_files` DROP COLUMN IF EXISTS `credit_card_match`;
```

Or restore from backup:
```bash
docker exec -i mind2-mysql-1 mysql -u root -proot mono_se_db_9 < backup_before_0015_TIMESTAMP.sql
```

## Post-Migration Tasks

1. **Update Application Code**
   - Modify code to populate new `unified_files` columns
   - Update receipt processing logic to use new fields
   - Add validation for `payment_type` and `expense_type`

2. **Data Migration for Existing Records**
   - Populate `payment_type` for existing records
   - Populate `expense_type` for existing records
   - Extract and populate `ocr_raw` if available
   - Set appropriate defaults for other new fields

3. **Test Application**
   - Test receipt upload functionality
   - Test AI processing pipeline
   - Test accounting proposals
   - Verify company CRUD operations

4. **Restart Services**
   ```bash
   docker-compose up -d backend frontend
   ```

## Troubleshooting

### Error: "Column already exists"
This is normal if you run the migration multiple times. The migration is idempotent and will skip columns that already exist.

### Error: "Cannot add NOT NULL column"
If you have existing rows in `unified_files`, you may need to:
1. First add columns as NULL
2. Populate data
3. Then modify to NOT NULL

### Error: "Procedure already exists"
Drop the procedures manually:
```sql
DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_companies_created_at;
DROP PROCEDURE IF EXISTS add_companies_updated_at;
DROP PROCEDURE IF EXISTS add_unified_files_column;
```

## Notes

1. **TEXT DEFAULT VALUES**: MySQL 8.4 requires TEXT columns with NOT NULL to use DEFAULT ('') syntax with parentheses.

2. **Column Order**: New columns are added in logical positions but may not match the exact order in the SQL file. This is acceptable as column order doesn't affect functionality.

3. **NOT Changed**: The following differences were intentionally NOT changed:
   - ID type differences (int vs bigint UNSIGNED) - risk of data corruption
   - receipt_items.main_id type - schema evolved to use UUIDs
   - NULL constraints on companies - current schema is more practical

4. **Evolution Features**: Extra columns in ai_processing_history and the creditcard_receipt_matches table are preserved as they represent schema evolution.

## Support

For issues or questions:
1. Review the audit report: `0015_audit_report.md`
2. Check verification queries above
3. Review migration script: `0015_restore_all_missing_columns.sql`

---
**Migration Version**: 0015
**Date Created**: 2025-09-30
**Status**: Ready for execution
