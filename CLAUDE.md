# Riktlinjer för Claude-agenter

```
Version: 2.1
Datum: 2025-10-07
```
*** CRITICAL RULES ***
** NO MOCKDATA IS ALLOWED. EVER. THIS MESSES UP EVERYTHING AND STOPS THE WORK **
**⚠️ MERCHANT_NAME IS NEVER EVER ALLOWED TO BE USED ANYWHERE **

Detta dokument specificerar de primära uppgifterna och reglerna för agenter baserade på Anthropic's Claude-modeller.


## Kärnregler

Utöver de allmänna reglerna i `AGENTS.md` gäller följande specifikt för Claude:

-   **Ingen Mock-data:** Denna regel är särskilt viktig. Claude-agenter får under inga omständigheter hitta på eller hårdkoda data. All data måste baseras på den kontext som tillhandahålls (t.ex. filer, OCR-data, databasfrågor). Att bryta mot denna regel leder oundvikligen till fel senare i processen.
-   **Inga SQLLITE-databaser:** Implementeras detta kommer saker gå sönder


## KRITISKA DATABASE SCHEMA-REGLER

### ⚠️ MERCHANT_NAME FÅR ALDRIG ANVÄNDAS I UNIFIED_FILES

**EXTREMT VIKTIGT:** Kolumnen `merchant_name` finns INTE i `unified_files` tabellen och FÅR ALDRIG användas!

-   **RÄTT:** Företagsnamn hämtas ALLTID via `companies.name` genom JOIN på `company_id`
-   **FEL:** `SELECT merchant_name FROM unified_files` - DEN KOLUMNEN FINNS INTE!
-   **RÄTT:** `SELECT c.name FROM unified_files u LEFT JOIN companies c ON c.id = u.company_id`

Om du ser någon kod som försöker läsa eller skriva `merchant_name` från/till `unified_files` är det ett KRITISKT FEL som MÅSTE fixas omedelbart.

### Database Schema - Faktisk struktur

**unified_files:**
- ✅ HAR: `id`, `company_id` (FK till companies), `purchase_datetime`, `gross_amount`, `net_amount`, etc.
- ❌ HAR INTE: `merchant_name` - använd companies.name via JOIN!

**companies:**
- ✅ HAR: `id`, `name`, `orgnr`, `address`, `address2`, `zip`, `city`, `country`, `phone`, `www`, `email`

**receipt_items:**
- ✅ HAR: `id` (PK), `main_id` (FK till unified_files.id), `article_id`, `name`, etc.

**ai_accounting_proposals:**
- ✅ HAR: `id` (PK), `receipt_id` (FK till unified_files.id), `item_id` (FK till receipt_items.id), `account_code`, `debit`, `credit`, etc.
- ✅ `item_id` refererar till `receipt_items.id` och används för att koppla kontering till specifik artikel
