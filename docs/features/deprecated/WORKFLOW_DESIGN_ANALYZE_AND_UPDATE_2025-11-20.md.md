Okej, jag har gått igenom:

- Kodbasen (backend + frontend)
- Databas-migrationerna
- De centrala docs: framför allt `specs/001-mind-system-receipt/*` och `docs/SYSTEM_DOCS/MIND_TECHNICAL_PLAN_v2.0.md`
- De FC/FirstCard-relaterade task-dokumenten under `docs/tasks/*`
- Worklogs runt november (bl.a. 2025-11-19)

och fokuserat på **kvitton**, **FirstCard-fakturor** och **manuell matchning**.

------

## 1. Är designen “färdig” för kvitton, FC-fakturor och manuell matchning?

### 1.1 Kvitto-workflow (unified_files + AI1–AI7)

**Status: funktionellt och i stort sett färdigt**

- Datamodellen för kvitton följer MIND v2-planen:
  - `unified_files` + `ai_*`-tabeller + `receipt_items` osv (`database/migrations/0001…`, `0010…`, `0011…` etc).
  - Kvitton listas via `/ai/api/receipts` i `backend/src/api/receipts.py` och används i admin-UI:t.
- AI-pipelinen (OCR, klassificering, extraction, box-enrichment osv) är implementerad i:
  - `backend/src/api/ai_processing.py`
  - `backend/src/models/ai_processing.py`
  - `backend/src/services/ai_service.py`
  - Celery-tasks under `backend/src/services/tasks/*`
- Kreditkorts-metadata (brand, last_4, entering_mode osv) finns nu **både i modell och persist**:
  - Fälten finns i `unified_files` (se t.ex. `0028_fix_unified_files_null_constraints.sql`).
  - De finns i Pydantic-modellerna i `models/ai_processing.py` (t.ex. `credit_card_last_4_digits` etc).
  - Persist av match mot kvitton (AI5) uppdaterar både `creditcard_invoice_items`, `creditcard_receipt_matches` och `unified_files.credit_card_match` i `_persist_credit_card_match()` i `api/ai_processing.py`.

**Slutsats kvitton:**
 Arkitekturen är i princip klar och stämmer med det som beskrivs i `MIND_TECHNICAL_PLAN_v2.0.md` och `specs/001-mind-system-receipt`. De stora hålen kring kortfält (som tas upp i `MIND_MISSING_CARD_DETAILS*.md`) är i praktiken åtgärdade i nuvarande kod.

------

### 1.2 FirstCard-/company card-fakturor

**Arkitektur (nuvarande läge)**

Du har två “lager”:

1. **Äldre, FirstCard-specifik nivå**
   - `creditcard_invoices_main`, `creditcard_invoice_items`, `creditcard_receipt_matches`
   - Skapas i bl.a. `database/migrations/0010_expand_ai_schema.sql`, `0011_create_missing_tables.sql`.
   - Används i AI-steget för automatisk matchning (`_persist_credit_card_match` i `api/ai_processing.py`).
2. **Ny generell faktura-nivå (MIND v2)**
   - `invoice_documents` + `invoice_lines` (+ statusfält, processing_status etc)
   - Förstärkt i `0026_invoice_matching_enhancements.sql` och senare.
   - Workflow-tracking i `0031_create_workflow_tracking.sql`.
   - All “nya” FirstCard-logik (status, matchning, confirm) jobbar mot **`invoice_documents`/`invoice_lines`**:
     - `backend/src/services/invoice_status.py`
     - `backend/src/services/tasks/creditcard_tasks.py`
     - `backend/src/api/reconciliation_firstcard/...`

**Viktigt designbeslut:**
 De “moderna” FirstCard-endpointsen jobbar **kanoniskt mot `invoice_lines`**, inte direkt mot `creditcard_invoice_items`. Tabellerna `creditcard_*` används främst:

- vid initial import/AI-analys av fakturan (AI5)
- för historik och back-compat (matchingtabellen `creditcard_receipt_matches`).

Detta **avviker från vissa äldre docs** (t.ex. `MIND_FIRST_CARD_MATCH_IMPLEMENTATION.md`) där `creditcard_invoice_items`/`creditcard_receipt_matches` beskrivs som primära. Koden har sprungit förbi dokumentationen här.

**Slutsats FC-fakturor:**
 Designen är i praktiken färdig och konsekvent kring att:

- **Business-lagret** = `invoice_documents`/`invoice_lines`
- **AI/legacy-lagret** = `creditcard_*` + `creditcard_receipt_matches`

men dokumentationen behöver uppdateras så att den speglar detta.

------

### 1.3 Manuell matchning (ManualMatch.jsx + FirstCard-API)

**Frontend**

- `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`:
  - Hämtar statements: `GET /ai/api/reconciliation/firstcard/statements`
  - För varje statement hämtas fakturans rader:
    - `GET /ai/api/reconciliation/firstcard/invoices/<statement.id>`
    - Tar `data.items` eller `data.lines` (backend returnerar båda).
  - Höger sida hämtar kvitton:
    - `GET /ai/api/receipts?from=YYYY-MM-DD&to=YYYY-MM-DD&page=...`
    - Filtrerar bort `workflow_type='creditcard_invoice'` och `file_type` som börjar med `cc_`/`credit_card`.
  - Matchknappen:
    - `POST /ai/api/reconciliation/firstcard/match` med `{ line_id, receipt_id, invoice_id? }`
- Modal för kvitto (`ReceiptPreviewModal`) används för att öppna/redigera kvitto direkt från matchningsvyn. Det hänger ihop med:
  - `/ai/api/receipts/<id>/modal` och `/ai/api/receipts/<id>` i `backend/src/api/receipts.py`.

**Backend**

- Blueprint `recon_bp` i `backend/src/api/reconciliation_firstcard/__init__.py`, registrerad i `api/app.py`.
- Centrala endpoints:
  - `routes/statements.py`
    - `/reconciliation/firstcard/statements` – listar statements per invoice_document.
    - `/reconciliation/firstcard/statements/<sid>/confirm` – säkerställer att alla rader är matchade, sätter processing_status till `COMPLETED` via `transition_processing_status`.
  - `routes/status.py`
    - `/reconciliation/firstcard/invoices/<invoice_id>` – returnerar:
      - `invoice` (payload med period, status, summary, kortdetaljer m.m.)
      - `lines` (eller `items`) med transaktioner (från `invoice_lines` + join mot `unified_files` för matchat kvitto).
  - `routes/matching.py`
    - `/reconciliation/firstcard/match` – högre nivå för auto/manuell match.
    - `/reconciliation/firstcard/lines/<line_id>` (PUT) – uppdaterar `invoice_lines.match_status`, `match_score`, `matched_file_id` via `transition_line_status_and_link`.
    - Anropar `refresh_invoice_match_state(document_id)` (i `services/tasks/creditcard_tasks.py`) som räknar om total/matchade rader och uppdaterar `invoice_documents.status/processing_status`.

**Slutsats manuell matchning:**
 UI + backend hänger ihop och följer i stort sett den refaktorerade FirstCard-designen.
 **Match-flödet är funktionellt färdigt** för v1: du kan:

- välja statement (månad)
- se alla dess rader
- se alla kvitton samma månad
- matcha 1 rad ↔ 1 kvitto
- bekräfta statement när allt är matchat.

------

## 2. Större brister / saker jag skulle klassa som “akuta”

### 2.1 Dokumentation vs verklighet (FirstCard-lagret)

**Problem:**
 Dokument under `docs/tasks/MIND_FIRST_CARD_MATCH_IMPLEMENTATION.md` m.fl. pratar fortfarande som om:

- `creditcard_invoice_items` + `creditcard_receipt_matches` vore kanonisk modell för FC-matchningen.

Men koden (framför allt `routes/matching.py`, `routes/status.py`, `invoice_status.py`, `creditcard_tasks.py`) har flyttat upp “sanningen” till:

- `invoice_documents` / `invoice_lines`
- och använder `creditcard_*` mer som underlag/legacy.

**Risk:**

- Förvirring vid felsökning och vidareutveckling.
- Stor risk att framtida fixar riktas mot fel tabeller eller fel API-lager.

**Åtgärd (högt prio):**

1. Uppdatera docs **så att kanonisk modell för FC-matching är `invoice_documents`/`invoice_lines`**.
2. Förklara tydligt:
   - att `creditcard_invoice_items` + `creditcard_receipt_matches` är “AI/legacy storage”,
   - vad som fortfarande läser därifrån (AI5), och
   - att UI/rapportering ska läsa `invoice_lines`.

------

### 2.2 Inkonsekvent användning av `creditcard_receipt_matches` vid manuell match

**Nuvarande läge:**

- AI-match (via `match_credit_card_internal` i `api/ai_processing.py`) gör:
  - `UPDATE creditcard_invoice_items.matched`
  - `INSERT/UPDATE creditcard_receipt_matches`
  - `UPDATE unified_files.credit_card_match/matched`
- **Manuell match** (`/reconciliation/firstcard/match` → `update_line_match()` i `routes/matching.py`) gör:
  - uppdaterar `invoice_lines.matched_file_id`, `match_status`, `match_score`.
  - räknar om status via `refresh_invoice_match_state`.
  - **men uppdaterar inte `creditcard_invoice_items`/`creditcard_receipt_matches`.**

**Frågan är:**
 Behöver du `creditcard_receipt_matches` till något i UI/rapporter?
 I nuvarande kod används tabellen i:

- AI-pipelinen (`_persist_credit_card_match`)
- tester och docs, men inte i FirstCard-UI:t.

Så det är **inte ett akut funktionsfel**, men:

- det bryter mot dokumentationen som säger att tabellen är “source of truth”,
- och det kan ge inkonsekvens mellan AI-matchningar och manuella matchningar om du någon gång vill rapportera mot `creditcard_receipt_matches`.

**Rekommendation:**

- Bestäm:
  - **A)** Kanonisk sanning = `invoice_lines` → uppdatera docs, och låt `creditcard_receipt_matches` vara internt/legacy (ingen åtgärd nu),
  - **B)** Kanonisk sanning = `creditcard_receipt_matches` → då behöver manuell match också skriva/ta bort rader där, på samma sätt som `_persist_credit_card_match`.

Jag skulle rekommendera **A)** (en datakälla, `invoice_lines`) och att du bara dokumenterar `creditcard_receipt_matches` som historik/AI-lager.

------

### 2.3 Operativa saker som kan stoppa hela systemet

Här är de största “starta-systemet”-riskerna:

1. **Migrationsnivå vs dump**
   - `database/migrations` går upp till minst `0033_add_invoice_document_soft_delete.sql`.
   - `.dbbackup/Mind2_mono_se_db_9_2025-11-11_*.sql` är en snapshot som troligen inte har alla senaste migrations.
   - Om du kör mot en dump utan att köra migrations riskerar du:
     - saknade kolumner (`workflow_runs`, `matched`, nya credit_card_field-kolumner osv),
     - och då kommer flera endpoints (bl.a. receipts-listan med `workflow_runs.source_channel`) att fallera.
2. **docker-compose.yml är hårt knutet till din Windows-miljö**
   - Volymer: `G:\Dropbox\MINDUPLOAD:/data/upload` finns på flera ställen (ai-api, workers).
   - På annan maskin / Linux måste dessa **bytas** mot lokala paths (t.ex. `./upload:/data/upload`).
   - Om volymerna inte finns kommer ingestion/FTP-fetch osv att bete sig konstigt eller inte fungera alls.
3. **Auto-migrationer**
   - `api/app.py` har `_maybe_apply_migrations()` som kan köra SQL-migrations automatiskt om `DB_AUTO_MIGRATE` är satt.
   - Om den är avslagen och du bara kör mot gammal struktur → samma problem: endpoints kraschar på saknade kolumner.

------

## 3. Konkreta rekommendationer

### 3.1 Steg 1 – Få igång systemet “rent”

Det här skulle jag göra i ordning:

1. **Ställ in miljövariabler**

   - Skapa `.env` i projektroten (om du inte redan har) med minst:
     - `DB_NAME`, `DB_USER`, `DB_PASS`
     - `OPENAI_API_KEY` eller motsvarande för din nuvarande provider
     - `ENABLE_REAL_OCR`, `OCR_LANG`, `OCR_USE_ANGLE_CLS` enligt dina behov.
   - Säkerställ att `DB_AUTO_MIGRATE=1` om du vill låta backend sköta migrations automatiskt.

2. **Justera docker-compose för aktuell maskin**

   - Öppna `docker-compose.yml`:
     - Byt ut `G:\Dropbox\MINDUPLOAD:/data/upload` mot en path som finns på maskinen (t.ex. `./upload:/data/upload`).
     - Om du kör på Linux/Hyper-V: säkerställ att `./storage` och `./inbox` finns och är skrivbara.
   - Om du kör separat frontend (t.ex. via `npm run dev`) kan du tillfälligt deaktivera frontend-containern.

3. **Starta bas-stacken**

   - Starta MySQL + Redis:

     ```bash
     docker compose up -d mysql redis
     ```

   - Kontrollera att MySQL accepterar anslutningar (t.ex. via Adminer eller mysql-cli).

4. **Applicera migrations**
    Två vägar:

   - **Auto**: Se till att `DB_AUTO_MIGRATE=1` och starta `ai-api`:

     ```bash
     docker compose up -d ai-api
     ```

     Kolla logg:

     ```bash
     docker logs ai-api
     ```

     och verifiera att `apply_migrations` inte spottar ut fel.

   - **Manuellt**: Kör SQL-filerna i `database/migrations` i ordning mot databasen (antingen via script eller Adminer).

5. **Starta workers**

   - Minst `celery-worker-ai` och `celery-worker-wf1`:

     ```bash
     docker compose up -d celery-worker-ai celery-worker-wf1
     ```

   - Kontrollera att de kopplar mot Redis och DB utan fel.

6. **Starta admin-frontend**

   - Antingen via Docker:

     ```bash
     docker compose up -d mind-web-main-frontend
     ```

   - eller lokalt:

     ```bash
     cd main-system/app-frontend
     npm install
     npm run dev
     ```

     med `VITE_API_PROXY_TARGET=http://localhost:5000` (eller motsvarande).

7. **Kör “quickstart”-flödet från `specs/001-mind-system-receipt/quickstart.md`**

   - Ladda upp ett kvitto → se status i kvittolistan.
   - Ladda upp FirstCard-faktura (via `POST /ai/api/reconciliation/firstcard/import` eller det GUI du har) → kör igenom OCR/AI.
   - Öppna **Manual Match**–vyn:
     - Verifiera att:
       - Statement-listan laddas (vänster topp).
       - Vänstersidan visar fakturarader.
       - Högersidan visar kvitton i samma månad.
       - Matchning fungerar och att `confirm` går igenom när alla rader är matchade.

------

### 3.2 Steg 2 – Anpassa till krav i docs (och nya “krav” jag föreslår)

Här är vad jag skulle göra för att “städa klar” mot dokumentationen:

#### A. Lås kanonisk modell för FirstCard-matching

1. **Beslut:**

   - Skriv in i `docs/SYSTEM_DOCS/MIND_TECHNICAL_PLAN_v2.0.md` + `specs/001-mind-system-receipt/data-model.md` att:
     - **Kanonisk FC-matchning** = `invoice_documents` + `invoice_lines`.
     - `creditcard_invoice_items` + `creditcard_receipt_matches` = AI/legacy-lager, används främst av AI5.

2. Justera `docs/tasks/MIND_FIRST_CARD_MATCH_IMPLEMENTATION.md` så att dess “Gaps to close” inte längre kräver att **all** matchning går via `creditcard_receipt_matches`, utan förklarar nya strat:

   > Auto-match (AI) fyller både `invoice_lines` och `creditcard_receipt_matches`.
   >  Manuell matchning måste **minst** uppdatera `invoice_lines` och livscykelstatus.
   >  Om vi i framtiden vill använda `creditcard_receipt_matches` för rapporter får vi lägga ett synchroniseringssteg där.

(Om du vill kan vi i nästa steg även lägga in uppdatering av `creditcard_receipt_matches` i `routes/matching.py`, men det är inte ett krav för funktion idag.)

#### B. Säkerställ att kvittolistan och ManualMatch följer samma regler

Krav i docs (och i din logg) är ungefär:

- Kvitton ska kunna filtreras per period (månad).
- FirstCard-kvitton ska **inte** dyka upp som “vanliga kvitton” i listor där det inte är relevant.
- Källa (`source_channel` / `workflow_runs.source_channel`) ska fungera för både kvitto- och FC-flöden.

Koden ligger rätt i stort:

- `/receipts`:
  - Filtrerar bort `workflow_type='creditcard_invoice'` och `file_type='cc_*'/'credit_card'` när `include_credit` inte är satt.
  - Läser `source_channel` via JOIN mot `workflow_runs` (se worklog 2025-11-19).
- ManualMatch:
  - Filtrerar kvitton i frontend på samma sätt (skippar `workflow_type='creditcard_invoice'` osv).

Jag skulle bara:

1. Dubbelkolla att **alla** ställen där kvitton listas för “vanligt” admin-flöde använder samma include/exclude-logik som i `/receipts`.

2. Dokumentera detta i `MIND_STATUS_DEFINITIONS.md` eller motsv, t.ex.:

   > “Kvitto med `workflow_type='creditcard_invoice'` visas endast i FC-relaterade vyer, inte i generella kvittolistor.”

#### C. Städa upp runt workflow_tracking och source_channel

Krav enligt `MIND_TECHNICAL_PLAN_v2.0`:

- All ingestion (kvitto, FC, övriga dokument) ska ha:
  - `workflow_runs` (rad per fil)
  - `workflow_stage_runs` (delsteg)
  - `source_channel` satt (`upload_portal`, `ftp`, `mobile_capture`, etc)

Koden:

- Tabellen finns (`0031_create_workflow_tracking.sql`).
- Helpers i `services/workflow_runs.py`.
- Worklog 2025-11-19 visar att receipts-listan nu läser `source_channel` från `workflow_runs`.

Mitt förslag:

1. Validera att alla ingest-paths (FTP, upload API, ev. mobilflödet) verkligen:
   - Skapar `workflow_run`.
   - Sätter `source_channel`.
2. Lägg en liten checklista i docs (en tabell: “för varje kanal → vilken `source_channel` används”).

------

## 4. Kort svar på dina frågor

**Är designen färdig?**
 Ja, för **version 1** av:

- kvittoflödet (capture → AI → admin → export),
- FirstCard-flödet (import → OCR/AI → matchning → confirm),
- manuell matchning (ManualMatch-vyn + motsvarande API),

är designen **i praktiken färdig och implementerad**.

**Har vi stora fel / brister som är akuta?**

- Inget fundamentalt arkitekturfel i just dessa tre flöden.
- De kritiska grejerna är:
  - Att databasen verkligen har alla migrations (annars faller mycket).
  - Att docker-volymer och paths stämmer i den miljö du kör.
  - Att dokumentationen uppdateras till att säga:
     **“Kanonisk FirstCard-modell = invoice_documents/invoice_lines”**, inte `creditcard_invoice_items`.

**Hur kommer vi vidare?**

1. **Få igång systemet** – enligt checklistan i 3.1 (env → docker-volymer → migrations → starta ai-api/worker/frontend → köra quickstart).
2. **Synka kod & docs** – enligt 3.2:
   - klargör canonical modell för FC,
   - justera docs för kvitto/FC-filtrering,
   - säkerställ workflow/source_channel-spåret.

När du vill gå vidare kan vi ta nästa steg väldigt konkret, t.ex.:

- “Uppdatera `routes/matching.py` så att manuell match också uppdaterar `creditcard_receipt_matches` enligt strategi X”,
- eller “Se över ManualMatch.jsx för att lägga till Unmatch-knapp på ett säkert sätt”.