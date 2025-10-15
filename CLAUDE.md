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
- ✅ HAR: `workflow_type` VARCHAR(32) DEFAULT 'receipt' - KRITISKT för routing till rätt pipeline
  - `'receipt'` - Normal kvitto-workflow (AI1-AI4)
  - `'creditcard_invoice'` - FirstCard kreditkortsutdrag-workflow (AI6)
  - **HARD ENFORCEMENT:** `workflow_type` har ALLTID prioritet över `file_type` vid routing
- ❌ HAR INTE: `merchant_name` - använd companies.name via JOIN!

**companies:**
- ✅ HAR: `id`, `name`, `orgnr`, `address`, `address2`, `zip`, `city`, `country`, `phone`, `www`, `email`

**receipt_items:**
- ✅ HAR: `id` (PK), `main_id` (FK till unified_files.id), `article_id`, `name`, etc.

**ai_accounting_proposals:**
- ✅ HAR: `id` (PK), `receipt_id` (FK till unified_files.id), `item_id` (FK till receipt_items.id), `account_code`, `debit`, `credit`, etc.
- ✅ `item_id` refererar till `receipt_items.id` och används för att koppla kontering till specifik artikel


## UTVECKLINGS- OCH TESTMILJÖ

### Frontend Utvecklingslägen

**Produktionsläge (Port 8008):**
- Byggd frontend via Docker + Nginx
- Kräver ombyggnad vid kodändringar
- Används för slutlig testning

**Utvecklingsläge (Port 5169) - HOT-RELOAD:**
- Vite dev-server med instant hot-reload
- **Startar AUTOMATISKT med `mind_docker_compose_up.bat`**
- Ingen ombyggnad behövs - ändringar syns direkt
- Två alternativ:
  1. **Docker-läge (Rekommenderat)**: `mind-web-main-frontend-dev` service
  2. **Lokalt läge**: `mind_frontend_dev.bat`

### Testningsflöden

**För Utvecklingstestning (med hot-reload):**
1. Starta: `mind_docker_compose_up.bat`
2. Frontend på: `http://localhost:5169` (startar automatiskt)
3. Redigera kod → instant reload
4. Testa: `npx playwright test --config=playwright.dev.config.ts --headed`

**För Produktionstestning:**
1. Bygg: `mind_docker_build_nocache.bat`
2. Starta: `mind_docker_compose_up.bat`
3. Testa: `npx playwright test --headed`

**VIKTIGT vid rapportering:** När arbete rapporteras som klart, se till att ombyggnader är utförda om produktionstestning krävs. För utvecklingstestning räcker det att använda dev-servern på port 5169.

### Porttilldelningar (FÅR EJ ÄNDRAS)
- **8008** - Produktions frontend + API (via nginx)
- **5169** - Dev frontend med hot-reload
- **5000** - Backend API (intern)
- **3310** - MySQL
- **6380** - Redis
- **8087** - phpMyAdmin

### Fullständig Dokumentation
Se `@docs/SYSTEM_DOCS/MIND_TASK_IMPLEMENTATION_REVIEW.md` för detaljer om frontend-testning och hot-reload setup.
