# UTF8_VERIFICATION (å/ä/ö)
Date: 2025-12-21

## Goal
Find an existing receipt whose vendor name or item text contains å/ä/ö, then verify UTF-8 survives DB → API → UI.

## Searches performed (DB)
### Companies (vendor name)
```sql
SELECT id, name
FROM companies
WHERE name LIKE '%å%' OR name LIKE '%ä%' OR name LIKE '%ö%'
LIMIT 10;
```
**Result:** 0 rows.

### Receipt items (item text)
```sql
SELECT main_id, name
FROM receipt_items
WHERE name LIKE '%å%' OR name LIKE '%ä%' OR name LIKE '%ö%'
LIMIT 10;
```
**Result:** 0 rows.

## Blocker
No existing receipt in the current DB contains å/ä/ö in vendor name or item text, so the required UTF-8 end-to-end verification cannot be completed.

## Needed to proceed
Provide or ingest a receipt that includes å/ä/ö in the vendor name or item text.
