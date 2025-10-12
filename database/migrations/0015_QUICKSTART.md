# Migration 0015 - Quick Start Guide

## What This Does
Restores **17 missing columns** and **3 missing tables** to your database.

## Critical Missing Items
- **unified_files**: 14 columns for receipt processing (payment_type, expense_type, ocr_raw, etc.)
- **ai_accounting_proposals**: 1 column (item_id)
- **companies**: 2 columns (created_at, updated_at)
- **3 tables**: file_categories, tags, tag_categories

## 30-Second Execution

```bash
# 1. Backup (REQUIRED!)
docker exec mind2-mysql-1 mysqldump -u root -proot mono_se_db_9 > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Run migration
docker exec -i mind2-mysql-1 mysql -u root -proot mono_se_db_9 < "E:\projects\Mind2\database\migrations\0015_restore_all_missing_columns.sql"

# 3. Verify
docker exec mind2-mysql-1 mysql -u root -proot mono_se_db_9 -e "
SELECT COUNT(*) FROM information_schema.TABLES
WHERE TABLE_SCHEMA='mono_se_db_9' AND TABLE_NAME IN ('file_categories','tags','tag_categories');
"
# Should return: 3
```

## Expected Output
```
3 new tables created
17 columns added
Migration complete
```

## If Something Goes Wrong
```bash
# Restore from backup
docker exec -i mind2-mysql-1 mysql -u root -proot mono_se_db_9 < backup_TIMESTAMP.sql
```

## Full Documentation
- **Detailed audit**: `0015_audit_report.md`
- **Complete guide**: `0015_README.md`
- **Executive summary**: `0015_SUMMARY.txt`
- **Migration script**: `0015_restore_all_missing_columns.sql`

## After Migration
1. Update application code to populate new unified_files columns
2. Test receipt upload and processing
3. Restart application: `docker-compose restart backend`

---
**Safe to run multiple times** - Migration is idempotent and won't duplicate changes.
